import copy
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from methodology_fixtures import AS_OF, PASSWORD, SCOPE, definition_payload, seed
from services.methodology import MethodologyError

PREFIX = '/v1/projects/project_method/indicators/indicator_method'


class MethodologyApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='rcatlas_method_')
        self.addCleanup(self.temp.cleanup)
        env = {k: v for k, v in os.environ.items() if not k.startswith(('LOGITRACK_', 'PG'))}
        env.update(LOGITRACK_STORAGE_BACKEND='json', LOGITRACK_DATA_PATH=str(Path(self.temp.name) / 'synthetic.json'),
                   LOGITRACK_ENVIRONMENT='development', LOGITRACK_SESSION_COOKIE_SECURE='false',
                   LOGITRACK_ENABLE_RELATIONAL_MIRROR='false', LOGITRACK_ENABLE_REPOSITORY_DOMAINS='false',
                   LOGITRACK_RUN_SCHEDULER='false', LOGITRACK_EMAIL_ENABLED='false')
        self.environment = patch.dict(os.environ, env, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        from logical_framework_api_tests import MODULE
        self.module = MODULE
        self.data = seed(MODULE)
        self.client = TestClient(MODULE.app)
        self.addCleanup(self.client.close)

    def headers(self, actor='method.a.organization_admin'):
        return {'X-Auth-Token': 'token-' + actor}

    def version(self):
        return self.module.load_data_from_path().workspace_version

    def publish(self, expected=200, actor='method.a.organization_admin', **overrides):
        response = self.client.post(PREFIX + '/methodology', headers=self.headers(actor), json={
            'definition': definition_payload(**overrides), 'expected_workspace_version': self.version()})
        self.assertEqual(response.status_code, expected, response.text)
        return response.json()

    def params(self, **overrides):
        return {'methodology_id': 'change-achievement', 'version': '1.0.0', 'start': '2026-09-01', 'end': '2026-09-30',
                'as_of': AS_OF, 'locale': 'EN', **overrides}

    def calculate(self, **overrides):
        response = self.client.get(PREFIX + '/calculation', headers=self.headers(), params=self.params(**overrides))
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_unconfigured_indicator_does_not_infer_legacy_formula(self):
        r = self.calculate(methodology_id='', version='')['result']
        self.assertEqual(r['state'], 'UNCONFIGURED')
        self.assertIsNone(r['display_value'])

    def test_authorized_calculation_explanation_and_legacy_api_compatibility(self):
        legacy = self.client.get('/v1/kpi/indicator', headers=self.headers())
        self.assertEqual(legacy.status_code, 200)
        before = legacy.json()
        self.publish()
        result = self.calculate()['result']
        self.assertEqual(result['display_value'], '50.00')
        self.assertEqual(result['numerator'], {'numerator': '40', 'denominator': '1'})
        self.assertEqual(result['methodology_version'], '1.0.0')
        self.assertEqual(self.client.get('/v1/kpi/indicator', headers=self.headers()).json(), before)
        self.assertEqual(legacy.headers['X-RCAtlas-Methodology-State'], 'LEGACY_UNVALIDATED')
        self.assertNotIn('FOREIGN_SENTINEL', str(result))

    def test_authentication_and_foreign_tenant_read_write_denial(self):
        self.publish()
        for suffix in ('/methodology', '/calculation'):
            response = self.client.get(PREFIX + suffix, params=self.params())
            self.assertEqual(response.status_code, 401)
            response = self.client.get(PREFIX + suffix, headers=self.headers('method.b.organization_admin'), params=self.params())
            self.assertEqual(response.status_code, 404)
            self.assertNotIn('dataset_method', response.text)
        self.publish(expected=404, actor='method.b.organization_admin')

    def test_viewer_cannot_register_or_save_calculation(self):
        self.publish(expected=403, actor='method.a.executive_viewer')
        response = self.client.post(PREFIX + '/calculation-instances', headers=self.headers('method.a.executive_viewer'), json={})
        self.assertEqual(response.status_code, 403)

    def test_read_requires_both_indicator_and_reporting_permission(self):
        data = self.module.load_data_from_path()
        user = next(u for u in data.users if u.username == 'method.a.executive_viewer')
        user.permissions = ['VIEW_INDICATORS']
        self.module.save_data_to_path(data)
        response = self.client.get(PREFIX + '/methodology', headers=self.headers(user.username))
        self.assertEqual(response.status_code, 403)

    def test_source_scope_and_caller_ownership_cannot_be_overridden(self):
        foreign = self.publish(expected=404, source_dataset_id='dataset_foreign')
        absent = self.publish(expected=404, source_dataset_id='dataset_absent')
        self.assertEqual(foreign, absent)
        self.publish(expected=400, scope={'organization_id': 'org_method_b'})
        self.publish(expected=400, unit='km')

    def test_method_immutability_overlap_idempotency_and_stale_write(self):
        first = self.publish()
        self.assertTrue(first['created'])
        self.assertFalse(self.publish()['created'])
        self.publish(expected=409, target=500)
        self.publish(expected=409, version='2.0.0')
        response = self.client.post(PREFIX + '/methodology', headers=self.headers(), json={
            'definition': definition_payload(version='2.0.0', effective_from='2027-01-01', effective_to='2028-01-01'),
            'expected_workspace_version': 0})
        self.assertEqual(response.status_code, 409)
        second = self.publish(version='2.0.0', effective_from='2027-01-01', effective_to='2028-01-01')
        self.assertTrue(second['created'])
        self.assertEqual(self.calculate()['result']['display_value'], '50.00')

    def test_saved_instance_retry_source_revision_and_historical_read(self):
        self.publish()
        payload = dict(self.params(), expected_workspace_version=self.version())
        first = self.client.post(PREFIX + '/calculation-instances', headers=self.headers(), json=payload)
        self.assertEqual(first.status_code, 200, first.text)
        original = first.json()['result']
        replay = self.client.post(PREFIX + '/calculation-instances', headers=self.headers(), json=payload)
        self.assertEqual(replay.status_code, 200)
        self.assertFalse(replay.json()['created'])
        data = self.module.load_data_from_path()
        data.tidy_datasets[0].rows[0]['actual'] = 100
        self.module.save_data_to_path(data)
        fresh = self.calculate()['result']
        self.assertEqual(fresh['display_value'], '100.00')
        self.assertNotEqual(original['calculation_id'], fresh['calculation_id'])
        historical = self.client.get(PREFIX + '/calculation-instances/' + original['calculation_id'], headers=self.headers())
        self.assertEqual(historical.json()['result'], original)
        self.assertTrue(historical.json()['historical'])
        foreign = self.client.get(PREFIX + '/calculation-instances/' + original['calculation_id'], headers=self.headers('method.b.organization_admin'))
        self.assertEqual(foreign.status_code, 404)

    def test_canonical_roundtrip_and_append_only_history(self):
        self.publish()
        data = self.module.load_data_from_path()
        clone = self.module.from_serializable(self.module.to_serializable(data))
        self.assertEqual(data.projects[0].indicators[0].methodology, clone.projects[0].indicators[0].methodology)
        clone.projects[0].indicators[0].methodology = {}
        with self.assertRaises(MethodologyError):
            self.module.save_data_to_path(clone)
        self.assertEqual(self.calculate()['result']['display_value'], '50.00')

    def test_cookie_session_csrf_and_no_token_regression(self):
        self.client.headers.clear()
        login = self.client.post('/v1/auth/login', json={'username': 'method.a.organization_admin', 'password': PASSWORD})
        self.assertEqual(login.status_code, 200, login.text)
        self.assertNotIn('token', login.json())
        payload = {'definition': definition_payload(), 'expected_workspace_version': self.version()}
        self.assertEqual(self.client.post(PREFIX + '/methodology', json=payload).status_code, 403)
        csrf = self.client.cookies.get(self.module.csrf_cookie_name_setting())
        response = self.client.post(PREFIX + '/methodology', headers={'X-CSRF-Token': csrf}, json=payload)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.client.get(PREFIX + '/calculation', params=self.params()).status_code, 200)

    def test_bad_context_and_malformed_configuration_are_controlled(self):
        self.publish()
        for changes in ({'as_of': 'today'}, {'end': '2026-02-31'}, {'start': '2026-10-01'}, {'locale': 'unknown'}):
            response = self.client.get(PREFIX + '/calculation', headers=self.headers(), params=self.params(**changes))
            self.assertEqual(response.status_code, 400, response.text)
        for changes in ({'status': {}}, {'profile': []}, {'direction': {}}, {'quality_rules': {'conformance': {'a': {'type': {}}}}}):
            self.publish(expected=400, **changes)

    def test_exact_context_is_reproducible_across_auth_workspace_changes(self):
        self.publish()
        first = self.calculate()
        data = self.module.load_data_from_path()
        data.organizations[1].organization_name = 'Changed foreign metadata'
        self.module.save_data_to_path(data)
        self.assertEqual(first, self.calculate())


if __name__ == '__main__':
    unittest.main()
