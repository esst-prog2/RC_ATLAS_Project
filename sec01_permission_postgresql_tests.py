"""SEC-01 policy durability on an independently verified disposable PostgreSQL."""
import os
import unittest

import methodology_postgresql_tests as fixture
from methodology_fixtures import PASSWORD


@unittest.skipUnless(os.getenv('RCATLAS_PG_TEST_BIN') and os.getenv('RCATLAS_PG_TEST_ROOT'),
                     'Disposable PostgreSQL binaries and root required.')
class PermissionPostgreSQLTests(unittest.TestCase):
    setUpClass = classmethod(fixture.MethodologyPostgreSQLTests.setUpClass.__func__)
    setUp = fixture.MethodologyPostgreSQLTests.setUp

    def test_versioned_and_legacy_grants_survive_jsonb_reload(self):
        raw = self.store.load()
        user = raw['users'][0]
        for version, grants in ((0, []), (1, None), (1, []), (1, ['VIEW_REPORTS'])):
            with self.subTest(version=version, grants=grants):
                raw = self.store.load()
                user = raw['users'][0]
                user.update(permission_policy_version=version, permissions=grants)
                self.store.save(raw, raw['workspace_version'])
                loaded = self.module.load_data_from_path().users[0]
                self.assertEqual(getattr(loaded, 'permission_policy_version', 0), version)
                expected = self.module.role_permissions(user['role']) if version == 0 or grants is None else grants
                self.assertEqual(self.module.effective_permissions(loaded), expected)
                self.module.save_data_to_path(self.module.load_data_from_path())
                stored = self.store.load()['users'][0]
                self.assertEqual(stored['permissions'], grants)
                self.assertEqual(stored.get('permission_policy_version', 0), version)

    def test_created_denial_and_update_remain_effective_after_database_restart(self):
        created = self.client.post('/v1/admin/users', headers=self.headers, json={
            'id': 'sec01_pg', 'username': 'sec01.pg', 'password': PASSWORD,
            'role': 'organization_admin', 'permissions': [],
        })
        self.assertEqual(created.status_code, 200, created.text)
        self.assertEqual(created.json()['user']['permissions'], [])
        data = self.module.load_data_from_path()
        user = next(u for u in data.users if u.id == 'sec01_pg')
        self.module.register_session_for_token(data, user, 'synthetic-sec01-pg-session')
        self.module.save_data_to_path(data)
        self.cluster.stop()
        self.cluster.start()
        headers = {'X-Auth-Token': 'synthetic-sec01-pg-session'}
        self.assertEqual(self.client.get('/v1/indicators', headers=headers).status_code, 403)
        updated = self.client.patch('/v1/admin/users/sec01_pg', headers=self.headers,
                                    json={'permissions': ['VIEW_INDICATORS']})
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(self.client.get('/v1/indicators', headers=headers).status_code, 200)
        self.assertEqual(self.client.get('/v1/kpi/indicator', headers=headers).status_code, 403)
        foreign = {'X-Auth-Token': 'token-method.b.organization_admin'}
        self.assertEqual(self.client.get('/v1/projects/project_method/dashboard', headers=foreign).status_code, 404)
        self.assertFalse(list(self.cluster.root.glob('forbidden-*')))
