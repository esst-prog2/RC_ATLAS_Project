"""Actual PostgreSQL/PostGIS integration tests; never substitute SQLite or mocks.

Set RCATLAS_PG_TEST_BIN and RCATLAS_PG_TEST_ROOT to run. The harness creates a
new verified loopback cluster and unique synthetic database for every test.
"""
import copy
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from logitrack_platform.persistence_validation import SnapshotInvalid, validate_snapshot
from logitrack_platform.postgresql_store import (
    ConfigurationError, PersistenceUnavailable, PostgreSQLStore, VersionConflict,
    connection, migrate_schema, migration_files,
)


@unittest.skipUnless(os.getenv('RCATLAS_PG_TEST_BIN') and os.getenv('RCATLAS_PG_TEST_ROOT'),
                     'Actual disposable PostgreSQL binaries/root not configured; no backend substitution.')
class PostgreSQLPersistenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from postgresql_test_support import DisposablePostgres
        cls.cluster = DisposablePostgres()
        cls.cluster.start()
        cls.addClassCleanup(cls.cluster.stop)
        print('PostgreSQL disposable evidence root: '+str(cls.cluster.root),flush=True)

    def setUp(self):
        self.database = self.cluster.create_database()
        env = self.cluster.app_environment(self.database)
        env.update(LOGITRACK_ENVIRONMENT='development', LOGITRACK_SESSION_COOKIE_SECURE='false')
        self.environment = patch.dict(os.environ,env,clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        with patch.dict(os.environ,{'LOGITRACK_DATABASE_URL':self.cluster.dsn(self.database,owner=True)}):
            self.assertEqual(migrate_schema(),['001_canonical.sql','002_postgis.sql'])
        self.cluster.grant_application(self.database)
        from logical_framework_api_tests import MODULE
        from services.demo_seed import build_demo_seed_bundle
        self.module = MODULE
        self.bundle = build_demo_seed_bundle(MODULE.build_password_hash)
        self.data = MODULE.from_serializable(self.bundle.payload)
        self.data.organizations.append(MODULE.OrganizationAccount(id='org_pg_other',organization_name='Synthetic B'))
        self.data.users.append(MODULE.UserAccount(id='user_pg_other',organization_id='org_pg_other',
                                                  username='pg.other',role='organization_admin',status='active'))
        MODULE.register_session_for_token(self.data,MODULE.find_user_by_username(self.data,'org.admin'),'pg-token-a')
        MODULE.register_session_for_token(self.data,MODULE.find_user_by_username(self.data,'pg.other'),'pg-token-b')
        # Synthetic fixture uses the application's established canonical shape.
        self.data = MODULE.from_serializable(MODULE.to_serializable(self.data))
        self.store = PostgreSQLStore()
        self.client = TestClient(MODULE.app)
        self.addCleanup(self.client.close)

    def seed(self):
        self.module.save_data_to_path(self.data)
        return self.module.to_serializable(self.data)

    def headers(self,token='pg-token-a',key=None,version=None):
        headers={'X-Auth-Token':token}
        if key: headers['X-Idempotency-Key']=key
        if version is not None: headers['X-Workspace-Version']=str(version)
        return headers

    def project(self,name='PG Project'):
        return {'project_name':name,'programme':'Synthetic','donor':'Synthetic','implementing_partner':'Synthetic',
                'sector':'Education','description':'Synthetic PG test','country':'Testland',
                'start_date':'2026-01-01','end_date':'2026-12-31'}

    def login(self):
        credential=next(c for c in self.bundle.credentials if c.username=='org.admin')
        response=self.client.post('/v1/auth/login',json={'username':credential.username,'password':credential.password})
        self.assertEqual(response.status_code,200,response.text)
        return response

    def test_schema_rerun_versions_and_application_role(self):
        with patch.dict(os.environ,{'LOGITRACK_DATABASE_URL':self.cluster.dsn(self.database,owner=True)}):
            self.assertEqual(migrate_schema(),[])
        self.assertEqual(self.store.status()['server_version'],170011)
        self.assertEqual(self.store.status()['postgis_version'],'3.6.2')
        with self.assertRaises(PersistenceUnavailable):
            with connection() as conn: conn.execute('CREATE TABLE rcatlas.forbidden(id int)')

    def test_failed_schema_upgrade_rolls_back_and_checksum_mismatch_blocks(self):
        real=migration_files()
        bad=('003_failure.sql','0'*64,'CREATE TABLE rcatlas.rollback_probe(id int); SELECT 1/0;')
        with patch.dict(os.environ,{'LOGITRACK_DATABASE_URL':self.cluster.dsn(self.database,owner=True)}):
            with patch('logitrack_platform.postgresql_store.migration_files',return_value=real+[bad]):
                with self.assertRaises(PersistenceUnavailable): migrate_schema()
            with connection(migrator=True) as conn:
                self.assertIsNone(conn.execute("SELECT to_regclass('rcatlas.rollback_probe')").fetchone()[0])
                conn.execute("UPDATE rcatlas.schema_migrations SET sha256='tampered' WHERE name='001_canonical.sql'")
        with self.assertRaises(ConfigurationError): self.store.load()
        with self.assertRaises(ConfigurationError):
            with TestClient(self.module.app): pass

    def test_lossless_canonical_roundtrip_without_sqlite_or_json(self):
        payload=self.seed()
        self.assertEqual(self.store.load(),payload)
        with patch.object(self.module,'_sqlite_connect',side_effect=AssertionError('SQLite accessed')), \
             patch.object(self.module,'_load_json_snapshot',side_effect=AssertionError('JSON accessed')):
            self.assertEqual(self.module.to_serializable(self.module.load_data_from_path()),payload)
            loaded=self.module.load_data_from_path()
            loaded.projects[0].objective='Persisted PostgreSQL objective'
            self.module.save_data_to_path(loaded)
        self.assertFalse(list(self.cluster.root.glob('forbidden-*')))
        self.assertEqual(self.store.load()['projects'][0]['objective'],'Persisted PostgreSQL objective')

    def test_database_foreign_keys_prevent_cross_tenant_relations_atomically(self):
        self.seed()
        before=self.store.load()
        with self.assertRaises(PersistenceUnavailable):
            with connection() as conn:
                conn.execute("INSERT INTO rcatlas.relationships VALUES ('users','user_pg_other',"
                             "'org_pg_other','illegal','projects','proj_resilience')")
                conn.execute("UPDATE rcatlas.workspace SET payload=jsonb_set(payload,'{workspace_version}','999'),version=999")
        self.assertEqual(self.store.load(),before)

    def test_raw_validation_rejects_orphans_conflicts_and_blank_activity_owner(self):
        p=self.module.to_serializable(self.data)
        p['ops_by_project']['proj_resilience']['activities'][0]['organization_id']=''
        p['users'][0]['organization_id']='missing_org'
        p['semantic_mappings'][0]['dataset_id']='missing_dataset'
        p['teams'][0]['team_lead_user_id']='user_pg_other'
        with self.assertRaises(SnapshotInvalid) as caught: validate_snapshot(p,complete=True)
        codes={x['code'] for x in caught.exception.issues}
        self.assertTrue({'BLANK_OWNER_REQUIRES_APPROVAL','ORPHAN_ORGANIZATION',
                         'ORPHAN_REFERENCE','CONFLICTING_OWNERSHIP'} <= codes)
        self.assertEqual(self.store.load(),{'workspace_version':0})

    def test_scoped_duplicate_ids_are_supported_but_duplicate_login_is_not(self):
        p=self.module.to_serializable(self.data)
        duplicate=copy.deepcopy(p['tidy_datasets'][0])
        duplicate['organization_id']='org_pg_other'
        p['tidy_datasets'].append(duplicate)
        self.store.save(p,0)
        self.assertEqual(len(self.store.load()['tidy_datasets']),3)
        bad=self.store.load()
        bad['users'][-1]['username']=bad['users'][0]['username'].upper()
        with self.assertRaises(SnapshotInvalid): self.store.save(bad,bad['workspace_version'])
        self.assertNotEqual(self.store.load()['users'][-1]['username'],bad['users'][-1]['username'])
        with self.assertRaises(PersistenceUnavailable):
            with connection() as conn:
                conn.execute("INSERT INTO rcatlas.entities(kind,id,organization_id,attributes) "
                             "SELECT kind,'duplicate-user',organization_id,attributes FROM rcatlas.entities "
                             "WHERE kind='users' LIMIT 1")

    def test_dry_run_detects_duplicate_unique_keys_and_duplicate_identifiers(self):
        from migration.postgresql_import import migrate_source
        payload=self.module.to_serializable(self.data)
        payload['users'][-1]['username']=payload['users'][0]['username'].upper()
        payload['projects'].append(copy.deepcopy(payload['projects'][0]))
        path=self.cluster.root/(self.database+'.json')
        path.write_text(json.dumps(payload),encoding='utf-8')
        with self.assertRaises(SnapshotInvalid) as caught: migrate_source(path,'json')
        codes={x['code'] for x in caught.exception.issues}
        self.assertTrue({'DUPLICATE_UNIQUE_KEY','DUPLICATE_OR_AMBIGUOUS_ID'} <= codes)
        self.assertEqual(self.store.load(),{'workspace_version':0})

    def test_concurrent_database_writes_have_one_winner_and_no_lost_update(self):
        p=self.seed()
        def save(i):
            candidate=copy.deepcopy(p)
            candidate['projects'][0]['objective']=f'concurrent-{i}'
            try: return self.store.save(candidate,p['workspace_version'])
            except VersionConflict: return 'conflict'
        with ThreadPoolExecutor(max_workers=2) as pool: outcomes=list(pool.map(save,range(2)))
        self.assertEqual(outcomes.count('conflict'),1,outcomes)
        self.assertEqual(self.store.load()['workspace_version'],p['workspace_version']+1)

    def test_api_concurrent_idempotency_replay_and_stale_versions(self):
        p=self.seed()
        headers=self.headers(key='pg-concurrent-intent',version=p['workspace_version'])
        def create(_):
            with TestClient(self.module.app) as client:
                return client.post('/v1/admin/projects',headers=headers,json=self.project())
        with ThreadPoolExecutor(max_workers=2) as pool: responses=list(pool.map(create,range(2)))
        self.assertEqual([r.status_code for r in responses],[200,200],[r.text for r in responses])
        self.assertEqual(responses[0].json(),responses[1].json())
        self.assertEqual(len(self.store.load()['idempotency_records']),1)
        conflict=self.client.post('/v1/admin/projects',headers=headers,json=self.project('different'))
        self.assertEqual(conflict.status_code,409)
        stale=self.client.post('/v1/admin/projects',headers=self.headers(key='new',version=p['workspace_version']),json=self.project('stale'))
        self.assertEqual(stale.status_code,409)

    def test_api_tenant_reads_writes_and_idempotency_scope(self):
        self.seed()
        a=self.client.post('/v1/admin/projects',headers=self.headers(key='shared-key'),json=self.project('Tenant A'))
        b=self.client.post('/v1/admin/projects',headers=self.headers('pg-token-b',key='shared-key'),json=self.project('Tenant B'))
        self.assertEqual([a.status_code,b.status_code],[200,200],[a.text,b.text])
        foreign=a.json()['project']['id']
        denied=self.client.patch('/v1/admin/projects/'+foreign,headers=self.headers('pg-token-b'),json={'description':'forbidden'})
        self.assertIn(denied.status_code,(403,404))
        listing=self.client.get('/v1/admin/projects',headers=self.headers('pg-token-b'))
        self.assertEqual(listing.status_code,200,listing.text)
        self.assertNotIn('Tenant A',listing.text)
        self.assertIn('Tenant B',listing.text)
        self.assertEqual(len(self.store.load()['idempotency_records']),2)

    def test_expired_idempotency_key_can_be_reused_without_losing_history(self):
        self.seed()
        first=self.client.post('/v1/admin/projects',headers=self.headers(key='expires'),json=self.project('Before expiry'))
        self.assertEqual(first.status_code,200,first.text)
        data=self.module.load_data_from_path()
        data.idempotency_records[0].expires_at=(self.module.utc_now()-timedelta(days=1)).isoformat()
        self.module.save_data_to_path(data)
        second=self.client.post('/v1/admin/projects',headers=self.headers(key='expires'),json=self.project('After expiry'))
        self.assertEqual(second.status_code,200,second.text)
        self.assertNotEqual(first.json()['project']['id'],second.json()['project']['id'])
        self.assertEqual(len(self.store.load()['idempotency_records']),2)

    def test_cookie_csrf_origin_rotation_and_durable_logout(self):
        self.seed()
        login=self.login()
        token=self.client.cookies.get('rcatlas_session_dev')
        csrf=self.client.cookies.get('rcatlas_csrf_dev')
        self.assertNotIn('token',login.json())
        self.assertIn('HttpOnly',login.headers['set-cookie'])
        self.assertNotIn(token,json.dumps(self.store.load()))
        self.assertNotIn(csrf,json.dumps(self.store.load()))
        endpoint='/v1/admin/organization'
        self.assertEqual(self.client.patch(endpoint,json={'contact_person':'X'}).status_code,403)
        self.assertEqual(self.client.patch(endpoint,headers={'X-CSRF-Token':csrf,'Origin':'https://evil.invalid'},json={'contact_person':'X'}).status_code,403)
        self.assertEqual(self.client.patch(endpoint,headers={'X-CSRF-Token':csrf},json={'contact_person':'PG contact'}).status_code,200)
        self.login()
        with TestClient(self.module.app) as copied:
            copied.cookies.set('rcatlas_session_dev',token)
            self.assertEqual(copied.get('/v1/auth/me').status_code,401)
        csrf=self.client.cookies.get('rcatlas_csrf_dev')
        logout=self.client.post('/v1/auth/logout',headers={'X-CSRF-Token':csrf})
        self.assertEqual(logout.status_code,200,logout.text)
        self.assertTrue(any(s['revocation_reason']=='logout' for s in self.store.load()['sessions']))

    def test_session_idle_absolute_expiry_and_tenant_binding(self):
        self.seed()
        for field in ('idle_expires_at','absolute_expires_at'):
            self.login()
            data=self.module.load_data_from_path()
            session=self.module.find_session_by_token(data,self.client.cookies.get('rcatlas_session_dev'))
            setattr(session,field,(self.module.utc_now()-timedelta(days=1)).isoformat())
            self.module.save_data_to_path(data)
            self.assertEqual(self.client.get('/v1/auth/me').status_code,401)
        data=self.module.load_data_from_path()
        data.sessions[0].organization_id='org_pg_other'
        with self.assertRaises(SnapshotInvalid): self.module.save_data_to_path(data)

    def test_offline_json_import_dry_run_apply_rerun_and_changed_target(self):
        from migration.postgresql_import import migrate_source
        path=self.cluster.root/(self.database+'.json')
        payload=self.module.to_serializable(self.data)
        path.write_text(json.dumps(payload),encoding='utf-8')
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        dry=migrate_source(path,'json')
        self.assertEqual(dry['status'],'DRY_RUN_PASS')
        self.assertEqual(self.store.load(),{'workspace_version':0})
        with patch.dict(os.environ,{'LOGITRACK_ENVIRONMENT':'test'}):
            with self.assertRaises(ValueError): migrate_source(path,'json',apply=True,synthetic=True,reviewed_sha256='bad')
            applied=migrate_source(path,'json',apply=True,synthetic=True,reviewed_sha256=digest)
            rerun=migrate_source(path,'json',apply=True,synthetic=True,reviewed_sha256=digest)
            self.assertEqual([applied['status'],rerun['status']],['IMPORTED','UNCHANGED'])
            self.store.save(payload,0)
            with self.assertRaises(VersionConflict): migrate_source(path,'json',apply=True,synthetic=True,reviewed_sha256=digest)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),digest)
        (self.cluster.root/'json-import-evidence.json').write_text(json.dumps([dry,applied,rerun],indent=2),encoding='utf-8')

    def test_offline_sqlite_import_and_real_data_gate(self):
        from migration.postgresql_import import migrate_source
        path=self.cluster.root/(self.database+'.sqlite3')
        payload=self.module.to_serializable(self.data)
        with closing(sqlite3.connect(path)) as conn:
            conn.execute('CREATE TABLE app_state(state_key text,payload_json text)')
            conn.execute('INSERT INTO app_state VALUES (?,?)',('primary',json.dumps(payload)))
            conn.commit()
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        self.assertEqual(migrate_source(path,'sqlite')['status'],'DRY_RUN_PASS')
        with self.assertRaises(ValueError): migrate_source(path,'sqlite',apply=True,reviewed_sha256=digest)
        with patch.dict(os.environ,{'LOGITRACK_ENVIRONMENT':'test'}):
            result=migrate_source(path,'sqlite',apply=True,synthetic=True,reviewed_sha256=digest)
        self.assertEqual(result['status'],'IMPORTED')
        self.assertEqual(self.store.load(),payload)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),digest)

    def test_import_refuses_silent_application_conversion(self):
        from migration.postgresql_import import migrate_source, read_source
        payload=self.module.to_serializable(self.data)
        payload['projects'][0]['unmapped_field']='must not disappear'
        path=self.cluster.root/(self.database+'.json')
        path.write_text(json.dumps(payload),encoding='utf-8')
        with self.assertRaises(SnapshotInvalid): migrate_source(path,'json')
        del payload['projects'][0]['unmapped_field']
        payload['users'][0]['is_active']=1
        path.write_text(json.dumps(payload),encoding='utf-8')
        with self.assertRaises(SnapshotInvalid): migrate_source(path,'json')
        path.write_text('{"projects":[],"projects":[{}]}',encoding='utf-8')
        with self.assertRaises(ValueError): read_source(path,'json')
        ambiguous=self.cluster.root/(self.database+'-ambiguous.sqlite3')
        with closing(sqlite3.connect(ambiguous)) as conn:
            conn.execute('CREATE TABLE app_state(state_key text,payload_json text)')
            conn.executemany('INSERT INTO app_state VALUES (?,?)',[('primary','{}'),('primary','{}')])
            conn.commit()
        with self.assertRaises(ValueError): read_source(ambiguous,'sqlite')
        self.assertEqual(self.store.load(),{'workspace_version':0})

    def test_postgis_types_srid_distance_transform_rls_and_project_scope(self):
        self.seed()
        self.store.save_point(organization_id='org_blue_delta',project_id='proj_resilience',point_id='p1',longitude=19,latitude=47)
        self.assertEqual(self.store.list_points('org_blue_delta')[0],('p1','proj_resilience',19.0,47.0,4326))
        self.assertEqual(self.store.list_points('org_pg_other'),[])
        with self.assertRaises(PersistenceUnavailable):
            self.store.save_point(organization_id='org_pg_other',project_id='proj_resilience',point_id='x',longitude=19,latitude=47)
        with self.assertRaises(ValueError):
            self.store.save_point(organization_id='org_blue_delta',project_id='proj_resilience',point_id='x',longitude=181,latitude=47)
        with connection() as conn:
            self.assertEqual(conn.execute('SELECT count(*) FROM rcatlas.geographic_points').fetchone()[0],0)
            conn.execute("SELECT set_config('rcatlas.tenant_id','org_blue_delta',true)")
            self.assertEqual(conn.execute('SELECT count(*) FROM rcatlas.geographic_points').fetchone()[0],1)
            distance,srid=conn.execute('SELECT ST_Distance(location::geography,ST_SetSRID(ST_Point(19,47.001),4326)::geography),'
                                       'ST_SRID(ST_Transform(location,3857)) FROM rcatlas.geographic_points').fetchone()
            self.assertTrue(100<distance<120,distance)
            self.assertEqual(srid,3857)
        with self.assertRaises(PersistenceUnavailable):
            with connection() as conn:
                conn.execute("SELECT set_config('rcatlas.tenant_id','org_blue_delta',true)")
                conn.execute("UPDATE rcatlas.geographic_points SET location=ST_SetSRID(ST_Point(19,47),3857)")
        # Full canonical save preserves spatial records and their deferred FKs.
        current=self.module.load_data_from_path()
        self.module.save_data_to_path(current)
        self.assertEqual(len(self.store.list_points('org_blue_delta')),1)

    def test_database_outage_recovery_preserves_state_and_returns_503(self):
        before=self.seed()
        self.login()
        before=self.store.load()
        self.cluster.stop()
        try:
            response=self.client.get('/v1/auth/me')
            self.assertEqual(response.status_code,503,response.text)
            self.assertNotIn('password',response.text.lower())
            with self.assertRaises(PersistenceUnavailable): self.store.save(before,before['workspace_version'])
        finally:
            self.cluster.start()
        self.assertEqual(self.store.load(),before)
        self.assertEqual(self.client.get('/v1/auth/me').status_code,200)
        self.assertFalse(list(self.cluster.root.glob('forbidden-*')))

    def test_invalid_configuration_has_no_fallback_and_no_secret_error(self):
        from logitrack_platform.postgresql_store import configuration
        for environment,url in [('production',self.cluster.dsn(self.database)),
                                ('development','postgresql://invalid')]:
            with patch.dict(os.environ,{'LOGITRACK_ENVIRONMENT':environment,'LOGITRACK_DATABASE_URL':url}):
                with self.assertRaises(ConfigurationError) as caught: configuration()
                self.assertNotIn(self.cluster.password,str(caught.exception))
        with patch.dict(os.environ,{'LOGITRACK_STORAGE_BACKEND':'typo'}):
            with self.assertRaises(ConfigurationError): self.module.get_storage_backend()
        with patch.dict(os.environ,{'LOGITRACK_DATABASE_URL':self.cluster.dsn(self.database,owner=True)}):
            with self.assertRaises(ConfigurationError): self.store.load()

    def test_project_update_logical_framework_and_dataset_import_persist(self):
        self.seed()
        response=self.client.patch('/v1/admin/projects/proj_resilience',headers=self.headers(),
                                   json={'name':self.data.projects[0].name,'description':'PG updated'})
        self.assertEqual(response.status_code,200,response.text)
        result=self.client.post('/v1/projects/proj_resilience/logical-framework/results',headers=self.headers(),
                                json={'result_type':'goal','title':'PG canonical goal'})
        self.assertEqual(result.status_code,200,result.text)
        imported=self.client.post('/v1/tidy_datasets/import',headers=self.headers(),
                                  json={'name':'PG imported data','rows':[{'period':'2026-01','value':12}]})
        self.assertEqual(imported.status_code,200,imported.text)
        stored=self.store.load()
        self.assertEqual(stored['projects'][0]['description'],'PG updated')
        self.assertEqual(stored['logical_framework_results'][0]['title'],'PG canonical goal')
        self.assertTrue(any(x['name']=='PG imported data' and x['rows'][0]['value']==12 for x in stored['tidy_datasets']))


if __name__ == '__main__':
    unittest.main(verbosity=2)
