"""Actual PostgreSQL transaction/ownership/recovery coverage; no mock backend."""
import copy
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from logitrack_platform.persistence_validation import SnapshotInvalid
from logitrack_platform.postgresql_store import PostgreSQLStore, VersionConflict, connection, migrate_schema
from methodology_fixtures import AS_OF, SCOPE, definition_payload, seed
from services import methodology as m

PREFIX = '/v1/projects/project_method/indicators/indicator_method'


@unittest.skipUnless(os.getenv('RCATLAS_PG_TEST_BIN') and os.getenv('RCATLAS_PG_TEST_ROOT'),
                     'Actual disposable PostgreSQL must be configured; no substitution.')
class MethodologyPostgreSQLTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from postgresql_test_support import DisposablePostgres
        cls.cluster = DisposablePostgres()
        cls.cluster.start()
        cls.addClassCleanup(cls.cluster.stop)
        print('Methodology PostgreSQL evidence: ' + str(cls.cluster.root), flush=True)

    def setUp(self):
        self.database = self.cluster.create_database()
        self.env = patch.dict(os.environ, self.cluster.app_environment(self.database), clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        with patch.dict(os.environ, {'LOGITRACK_DATABASE_URL': self.cluster.dsn(self.database, owner=True)}):
            self.assertEqual(migrate_schema(), ['001_canonical.sql', '002_postgis.sql'])
        self.cluster.grant_application(self.database)
        from logical_framework_api_tests import MODULE
        self.module = MODULE
        self.data = seed(MODULE)
        self.store = PostgreSQLStore()
        self.client = TestClient(MODULE.app)
        self.addCleanup(self.client.close)
        self.headers = {'X-Auth-Token': 'token-method.a.organization_admin'}

    def publish_and_save(self):
        response = self.client.post(PREFIX + '/methodology', headers=self.headers, json={
            'definition': definition_payload(), 'expected_workspace_version': self.store.load()['workspace_version']})
        self.assertEqual(response.status_code, 200, response.text)
        query = {'methodology_id': 'change-achievement', 'version': '1.0.0', 'start': '2026-09-01', 'end': '2026-09-30',
                 'as_of': AS_OF, 'locale': 'EN', 'expected_workspace_version': self.store.load()['workspace_version']}
        response = self.client.post(PREFIX + '/calculation-instances', headers=self.headers, json=query)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['result']['display_value'], '50.00')
        return response.json()['result']

    def test_lossless_jsonb_and_same_transaction_dataset_integrity_edge(self):
        result = self.publish_and_save()
        payload = self.store.load()
        restored = self.module.to_serializable(self.module.from_serializable(payload))
        self.assertEqual(restored, payload)
        self.assertEqual(payload['projects'][0]['indicators'][0]['methodology']['instances'][0]['result'], result)
        with connection() as conn:
            self.assertEqual(conn.execute("SELECT target_id FROM rcatlas.relationships WHERE field='methodology_source'").fetchall(), [('dataset_method',)])
        self.assertFalse(list(self.cluster.root.glob('forbidden-*')))

    def test_cross_tenant_source_and_scope_rejected_atomically(self):
        self.publish_and_save()
        original = self.store.load()
        for change in ('source', 'scope'):
            bad = copy.deepcopy(original)
            ind = bad['projects'][0]['indicators'][0]
            payload = definition_payload(source_dataset_id='dataset_foreign') if change == 'source' else definition_payload()
            scope = SCOPE if change == 'source' else dict(SCOPE, organization_id='org_method_b')
            ind['methodology'] = {'schema_version': 1, 'definitions': [m.definition(payload, scope)], 'instances': []}
            with self.assertRaises(SnapshotInvalid):
                self.store.save(bad, bad['workspace_version'])
            self.assertEqual(self.store.load(), original)

    def test_append_only_history_even_through_other_aggregate_writers(self):
        self.publish_and_save()
        original = self.store.load()
        bad = copy.deepcopy(original)
        bad['projects'][0]['indicators'][0]['methodology'] = {}
        with self.assertRaises(m.MethodologyError):
            self.store.save(bad, bad['workspace_version'])
        self.assertEqual(self.store.load(), original)

    def test_stale_writer_cannot_erase_methodology(self):
        stale = self.store.load()
        self.publish_and_save()
        current = self.store.load()
        with self.assertRaises(VersionConflict):
            self.store.save(stale, stale['workspace_version'])
        self.assertEqual(self.store.load(), current)

    def test_database_restart_preserves_exact_instance_and_tenant_boundary(self):
        result = self.publish_and_save()
        original = self.store.load()
        self.cluster.stop()
        self.cluster.start()
        self.assertEqual(self.store.load(), original)
        response = self.client.get(PREFIX + '/calculation-instances/' + result['calculation_id'], headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['result'], result)
        foreign = self.client.get(PREFIX + '/calculation-instances/' + result['calculation_id'],
                                  headers={'X-Auth-Token': 'token-method.b.organization_admin'})
        self.assertEqual(foreign.status_code, 404)

    def test_instance_corruption_and_schema_mutation_rollback(self):
        self.publish_and_save()
        original = self.store.load()
        bad = copy.deepcopy(original)
        bad['projects'][0]['indicators'][0]['methodology']['instances'][0]['result']['display_value'] = '999.00'
        with self.assertRaises(SnapshotInvalid):
            self.store.save(bad, bad['workspace_version'])
        self.assertEqual(self.store.load(), original)
        with patch.dict(os.environ, {'LOGITRACK_DATABASE_URL': self.cluster.dsn(self.database, owner=True)}):
            self.assertEqual(migrate_schema(), [])


if __name__ == '__main__':
    unittest.main()
