"""SEC-01 regression oracles: versioned grants and capability-scoped BI reads."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import methodology_api_tests as api_fixture
from methodology_fixtures import PASSWORD


BI_CAPABILITIES = {
    '/v1/projects': ['VIEW_EXECUTIVE_SNAPSHOT'],
    '/v1/indicators': ['VIEW_INDICATORS'],
    '/v1/indicator_locations': ['VIEW_INDICATORS'],
    '/v1/activities': ['VIEW_WORKPLAN'],
    '/v1/tasks': ['VIEW_WORKPLAN'],
    '/v1/activity_indicator_links': ['VIEW_WORKPLAN'],
    '/v1/kpi/project': ['VIEW_REPORTS'],
    '/v1/kpi/indicator': ['VIEW_INDICATORS', 'VIEW_REPORTS'],
    '/v1/kpi/district': ['VIEW_REPORTS'],
    '/v1/kpi/workplan': ['VIEW_WORKPLAN'],
    '/v1/projects/project_method/dashboard': [
        'VIEW_EXECUTIVE_SNAPSHOT', 'VIEW_INDICATORS', 'VIEW_REPORTS',
        'VIEW_WORKPLAN', 'VIEW_NOTIFICATIONS',
    ],
}


class PermissionSemanticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from logical_framework_api_tests import MODULE
        cls.module = MODULE

    def raw_user(self, **changes):
        return dict(id='sec01_user', username='sec01.synthetic', organization_id='org_method_a',
                    role='organization_admin', status='active', is_active=True, **changes)

    def decode(self, raw):
        return self.module.from_serializable({'users': [raw]}).users[0]

    def test_unversioned_missing_null_empty_and_explicit_preserve_legacy(self):
        defaults = self.module.role_permissions('organization_admin')
        for fields in ({}, {'permissions': None}, {'permissions': []}, {'permissions': ['unknown']}):
            with self.subTest(fields=fields):
                user = self.decode(self.raw_user(**fields))
                self.assertEqual(self.module.effective_permissions(user), defaults)
                self.assertEqual(getattr(user, 'permission_policy_version', 0), 0)
        self.assertEqual(self.module.effective_permissions(self.decode(
            self.raw_user(permissions=['reporting.view']))), ['VIEW_REPORTS'])

    def test_new_explicit_empty_does_not_restore_role_defaults(self):
        user = self.module.build_user_account_from_payload(self.raw_user(password=PASSWORD, permissions=[]))
        self.assertEqual(self.module.effective_permissions(user), [])
        self.assertEqual(user.permission_policy_version, 1)

    def test_new_missing_and_null_inherit_with_version_marker(self):
        for fields in ({}, {'permissions': None}):
            with self.subTest(fields=fields):
                user = self.module.build_user_account_from_payload(self.raw_user(password=PASSWORD, **fields))
                self.assertIsNone(user.permissions)
                self.assertEqual(user.permission_policy_version, 1)
                self.assertEqual(self.module.effective_permissions(user), self.module.role_permissions(user.role))

    def test_explicit_list_normalizes_known_aliases_without_union(self):
        user = self.module.build_user_account_from_payload(self.raw_user(
            password=PASSWORD, permissions=['reporting.view', 'VIEW_REPORTS', 'view_indicators']))
        self.assertEqual(self.module.effective_permissions(user), ['VIEW_REPORTS', 'VIEW_INDICATORS'])

    def test_invalid_grants_rejected_instead_of_discarded(self):
        for grants in (['UNKNOWN'], ['VIEW_REPORTS', 'UNKNOWN'], [''], [False], [1],
                       'VIEW_REPORTS', {}, 0):
            with self.subTest(grants=grants), self.assertRaises(ValueError):
                self.module.build_user_account_from_payload(self.raw_user(password=PASSWORD, permissions=grants))

    def test_updates_preserve_legacy_unless_permissions_are_explicitly_written(self):
        legacy = self.decode(self.raw_user(permissions=[]))
        unchanged = self.module.build_user_account_from_payload({'full_name': 'Synthetic rename'}, legacy)
        self.assertEqual(getattr(unchanged, 'permission_policy_version', 0), 0)
        self.assertEqual(self.module.effective_permissions(unchanged), self.module.role_permissions(legacy.role))
        denied = self.module.build_user_account_from_payload({'permissions': []}, legacy)
        self.assertEqual(self.module.effective_permissions(denied), [])
        edited = self.module.build_user_account_from_payload({'role': 'meal_officer'}, denied)
        self.assertEqual(self.module.effective_permissions(edited), [])
        inherited = self.module.build_user_account_from_payload({'permissions': None}, edited)
        self.assertEqual(self.module.effective_permissions(inherited), self.module.role_permissions('meal_officer'))

    def test_json_roundtrip_preserves_all_versioned_states(self):
        for grants in (None, [], ['VIEW_REPORTS']):
            with self.subTest(grants=grants):
                raw = self.raw_user(permissions=grants, permission_policy_version=1)
                user = self.decode(raw)
                result = self.module.to_serializable(user)
                self.assertEqual(result['permissions'], grants)
                self.assertEqual(result.get('permission_policy_version'), 1)
                restored = self.decode(json.loads(json.dumps(result)))
                expected = self.module.role_permissions(user.role) if grants is None else grants
                self.assertEqual(self.module.effective_permissions(restored), expected)

    def test_invalid_versioned_storage_and_api_version_downgrades_fail_closed(self):
        for version, grants in ((2, []), (True, []), ('1', []), (1, ['UNKNOWN']), (1, 'VIEW_REPORTS')):
            with self.subTest(version=version, grants=grants), self.assertRaises(ValueError):
                self.decode(self.raw_user(permissions=grants, permission_policy_version=version))
        for version in (0, 1, None, 2):
            with self.subTest(api_version=version), self.assertRaises(ValueError):
                self.module.build_user_account_from_payload(self.raw_user(
                    password=PASSWORD, permissions=[], permission_policy_version=version))

    def test_repository_and_projection_roundtrips_preserve_policy(self):
        from repositories.users import upsert_user, replace_all_users, get_user_by_id
        from logitrack_platform.relational_store import sync_snapshot_to_relational_store
        with tempfile.TemporaryDirectory(prefix='sec01_repo_') as directory:
            for operation in ('upsert', 'replace', 'projection'):
                for index, grants in enumerate((None, [], ['VIEW_REPORTS'])):
                    with self.subTest(operation=operation, grants=grants):
                        path = str(Path(directory) / f'{operation}-{index}.sqlite3')
                        raw = self.raw_user(permissions=grants, permission_policy_version=1)
                        if operation == 'upsert':
                            upsert_user(raw, db_path=path)
                        elif operation == 'replace':
                            replace_all_users([raw], db_path=path)
                        else:
                            sync_snapshot_to_relational_store({'users': [raw]}, db_path=path)
                        loaded = get_user_by_id(raw['id'], db_path=path)
                        self.assertEqual(loaded.get('permission_policy_version'), 1)
                        self.assertEqual(loaded['permissions'], grants)
                        expected = self.module.role_permissions(raw['role']) if grants is None else grants
                        self.assertEqual(self.module.effective_permissions(self.decode(loaded)), expected)

    def test_corrupt_versioned_policies_never_restore_defaults(self):
        from shared.permission_policy import decode_permission_policy, encode_permission_policy
        with self.assertRaises(ValueError):
            self.decode(self.raw_user(permission_policy_version=1))
        for raw in ('{broken', '{"permission_policy_version":2,"permissions":[]}',
                    '{"permission_policy_version":1}',
                    '{"permission_policy_version":1,"permissions":false}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                decode_permission_policy(raw)
        with self.assertRaises(ValueError):
            encode_permission_policy(self.raw_user(permission_policy_version=1))
        user = self.decode(self.raw_user(permissions=[], permission_policy_version=1))
        for version, grants in ((1, ['UNKNOWN']), (1, False), (2, None), (True, None)):
            with self.subTest(version=version, grants=grants):
                user.permission_policy_version, user.permissions = version, grants
                self.assertEqual(self.module.effective_permissions(user), [])

    def test_legacy_repository_records_keep_their_original_interpretation(self):
        from repositories.users import upsert_user, get_user_by_id
        from shared.permission_policy import decode_permission_policy
        for raw in ('[]', 'null', '["VIEW_REPORTS"]'):
            self.assertEqual(decode_permission_policy(raw)['permission_policy_version'], 0)
        with tempfile.TemporaryDirectory(prefix='sec01_legacy_repo_') as directory:
            path = str(Path(directory) / 'legacy.sqlite3')
            for grants in (None, [], ['VIEW_REPORTS']):
                with self.subTest(grants=grants):
                    upsert_user(self.raw_user(permissions=grants), db_path=path)
                    loaded = self.decode(get_user_by_id('sec01_user', db_path=path))
                    self.assertEqual(loaded.permission_policy_version, 0)
                    self.assertEqual(self.module.effective_permissions(loaded),
                                     grants or self.module.role_permissions(loaded.role))


class PermissionApiTests(unittest.TestCase):
    setUp = api_fixture.MethodologyApiTests.setUp
    headers = api_fixture.MethodologyApiTests.headers

    def set_grants(self, grants):
        data = self.module.load_data_from_path()
        user = next(u for u in data.users if u.username == 'method.a.executive_viewer')
        user.permissions = grants
        user.permission_policy_version = 1
        self.module.save_data_to_path(data)
        return self.headers(user.username)

    def test_create_update_reload_and_invalid_request_are_atomic(self):
        response = self.client.post('/v1/admin/users', headers=self.headers(), json={
            'id': 'sec01_created', 'username': 'sec01.created', 'password': PASSWORD,
            'role': 'organization_admin', 'permissions': [],
        })
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['user']['permissions'], [])
        data = self.module.load_data_from_path()
        user = next(u for u in data.users if u.id == 'sec01_created')
        self.assertEqual(user.permission_policy_version, 1)
        self.assertEqual(user.permissions, [])
        response = self.client.patch('/v1/admin/users/sec01_created', headers=self.headers(),
                                     json={'permissions': ['VIEW_REPORTS']})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['user']['permissions'], ['VIEW_REPORTS'])
        before = self.module.to_serializable(self.module.load_data_from_path())
        for payload in ({'permissions': ['WRONG']}, {'permission_policy_version': 0}):
            result = self.client.patch('/v1/admin/users/sec01_created', headers=self.headers(), json=payload)
            self.assertEqual(result.status_code, 400, result.text)
            self.assertEqual(self.module.to_serializable(self.module.load_data_from_path()), before)

    def test_minimum_capabilities_preserve_authorized_bi_values(self):
        keys = ['projects', 'indicators', 'indicator_locations', 'activities', 'tasks',
                'activity_indicator_links', 'kpi_project', 'kpi_indicator', 'kpi_district', 'kpi_workplan']
        for (route, capabilities), key in zip(BI_CAPABILITIES.items(), keys):
            with self.subTest(route=route):
                reference = self.client.get(route, headers=self.headers())
                self.assertEqual(reference.status_code, 200)
                actual = self.client.get(route, headers=self.set_grants(capabilities))
                self.assertEqual(actual.status_code, 200, actual.text)
                self.assertEqual(actual.json(), reference.json())
        route = '/v1/projects/project_method/dashboard'
        reference = self.client.get(route, headers=self.headers()).json()
        actual = self.client.get(route, headers=self.set_grants(BI_CAPABILITIES[route]))
        self.assertEqual(actual.status_code, 200)
        for key in ('project', 'kpi_project', 'kpi_indicator', 'kpi_district', 'kpi_workplan', 'activities', 'tasks', 'reporting_records'):
            self.assertEqual(actual.json()[key], reference[key])

    def test_explicit_empty_denies_bi_and_admin_without_changing_other_accounts(self):
        headers = self.set_grants([])
        for route in (*BI_CAPABILITIES, '/v1/admin/users'):
            with self.subTest(route=route):
                self.assertEqual(self.client.get(route, headers=headers).status_code, 403)
        self.assertEqual(self.client.get('/v1/admin/users', headers=self.headers()).status_code, 200)
        self.assertEqual(self.client.get('/v1/projects/project_method/dashboard',
                         headers=self.headers('method.b.organization_admin')).status_code, 404)

    def test_cookie_csrf_precedes_permission_mutation_and_denial_survives_reload(self):
        login = self.client.post('/v1/auth/login', json={'username': 'method.a.organization_admin', 'password': PASSWORD})
        self.assertEqual(login.status_code, 200)
        route = '/v1/admin/users/user_a_executive_viewer'
        self.assertEqual(self.client.patch(route, json={'permissions': []}).status_code, 403)
        csrf = self.client.cookies.get('rcatlas_csrf_dev')
        result = self.client.patch(route, json={'permissions': []}, headers={'X-CSRF-Token': csrf})
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.json()['user']['permissions'], [])
        self.client.cookies.clear()
        self.assertEqual(self.client.get('/v1/projects', headers=self.headers('method.a.executive_viewer')).status_code, 403)

    def test_legacy_account_api_preserves_inheritance_and_explicit_denial(self):
        created = self.client.post('/v1/users', headers=self.headers(), json={
            'id': 'sec01_legacy_api', 'username': 'sec01.legacy.api', 'password': PASSWORD,
            'role': 'meal_officer', 'organization_id': 'org_method_b',
        })
        self.assertEqual(created.status_code, 200, created.text)
        self.assertEqual(created.json()['user']['permission_mode'], 'inherit')
        self.assertEqual(created.json()['user']['organization_id'], 'org_method_a')
        for fields, mode in (({'permissions': []}, 'explicit'), ({'full_name': 'Changed'}, 'explicit'),
                             ({'permissions': None}, 'inherit')):
            with self.subTest(fields=fields):
                response = self.client.post('/v1/users', headers=self.headers(),
                    json=dict(id='sec01_legacy_api', **fields))
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json()['user']['permission_mode'], mode)
                expected = [] if mode == 'explicit' else self.module.role_permissions('meal_officer')
                self.assertEqual(response.json()['user']['permissions'], expected)
        before = self.module.to_serializable(self.module.load_data_from_path())
        invalid = self.client.post('/v1/users', headers=self.headers(),
            json={'id': 'sec01_legacy_api', 'permissions': ['UNKNOWN']})
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(self.module.to_serializable(self.module.load_data_from_path()), before)

    def test_bootstrap_rejects_invalid_grants_without_partial_persistence(self):
        self.module.save_data_to_path(self.module.LogiTrackData())
        before = self.module.to_serializable(self.module.load_data_from_path())
        with patch.dict(os.environ, {'LOGITRACK_SETUP_ENABLED': 'true',
                                    'LOGITRACK_SETUP_TOKEN': 'synthetic-sec01-setup'}):
            response = self.client.post('/v1/auth/bootstrap', headers={'X-Setup-Token': 'synthetic-sec01-setup'},
                json={'username': 'sec01.bootstrap', 'password': PASSWORD, 'permissions': ['UNKNOWN']})
        self.assertEqual(response.status_code, 400, response.text)
        self.assertEqual(self.module.to_serializable(self.module.load_data_from_path()), before)

    def test_bi_requires_a_session_and_keeps_foreign_collection_rows_out(self):
        for route in BI_CAPABILITIES:
            with self.subTest(route=route):
                self.assertEqual(self.client.get(route).status_code, 401)
                self.assertEqual(self.client.get(route, headers={'X-API-Key': 'synthetic-only'}).status_code, 401)
                if route.endswith('/dashboard'):
                    continue
                response = self.client.get(route, headers=self.headers())
                self.assertEqual(response.status_code, 200, response.text)
                self.assertNotIn('project_foreign', response.text)
                self.assertNotIn('dataset_foreign', response.text)


def denied_case(route, capabilities):
    def test(self):
        # Omit one required capability at a time; a valid unrelated grant avoids
        # conflating this BI defect with the legacy empty-list fallback.
        for missing in capabilities:
            grants = ['WORKSPACE_VIEW'] + [p for p in capabilities if p != missing]
            response = self.client.get(route, headers=self.set_grants(grants))
            self.assertEqual(response.status_code, 403, f'{route} without {missing}: {response.status_code}')
    return test


for index, (route, capabilities) in enumerate(BI_CAPABILITIES.items()):
    setattr(PermissionApiTests, f'test_bi_capability_denial_{index:02d}', denied_case(route, capabilities))
