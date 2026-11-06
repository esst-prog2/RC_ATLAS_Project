"""Independent arithmetic and full-result reconciliation across real API adapters."""
import copy
import csv
from pathlib import Path
import unittest
from unittest.mock import patch

import methodology_api_tests as api_fixture
from methodology_fixtures import SCOPE, definition_payload, AS_OF
from services import methodology as core
from services import analytical_consumers as consumers


PREFIX = api_fixture.PREFIX


class AnalyticalConsumerTests(unittest.TestCase):
    setUp = api_fixture.MethodologyApiTests.setUp
    headers = api_fixture.MethodologyApiTests.headers
    version = api_fixture.MethodologyApiTests.version
    publish = api_fixture.MethodologyApiTests.publish
    params = api_fixture.MethodologyApiTests.params

    def set_rows(self, rows):
        data = self.module.load_data_from_path()
        data.tidy_datasets[0].rows = rows
        self.module.save_data_to_path(data)

    def reconcile(self, params=None):
        params = params or self.params()
        query = dict(params, project_id=SCOPE['project_id'], indicator_id=SCOPE['indicator_id'])
        paths = [PREFIX + '/calculation', '/v1/kpi/indicator', '/v1/projects/project_method/dashboard',
                 '/v1/tidy_datasets/dataset_method/quality', '/v1/tidy_datasets/dataset_method/narrative']
        bodies = []
        for path in paths:
            r = self.client.get(path, headers=self.headers(), params=params if path == paths[0] else query)
            self.assertEqual(r.status_code, 200, path + ': ' + r.text)
            bodies.append(r.json())
        reference = bodies[0]
        for envelope in (bodies[1][0]['calculation'], bodies[2]['kpi_indicator'][0]['calculation'],
                         bodies[3]['calculation'], bodies[4]['calculation']):
            self.assertEqual(envelope, reference)
        result = reference['result']
        if reference['definition']:
            rows = self.module.load_data_from_path().tidy_datasets[0].rows
            independent_engine_call = core.calculate(reference['definition'], rows, core.context(
                params['start'], params['end'], params['as_of'], params['locale']))
            self.assertEqual(result, independent_engine_call)
            self.assertEqual(bodies[3]['profile'], result['quality'])
            self.assertEqual(bodies[3]['coverage'], result['coverage'])
            self.assertEqual(bodies[3]['period_exclusions'], result['period_exclusions'])
        self.assertIsNone(bodies[1][0]['progress_mean_pct'])
        self.assertIsNone(bodies[1][0]['progress_weighted_pct'])
        self.assertIsNone(bodies[3]['overall_score'])
        self.assertNotIn('FOREIGN_SENTINEL', str(bodies))
        return result, bodies

    def test_independent_oc_a02_and_exact_explanations_all_consumers(self):
        self.publish(quality_rules={'required_fields': ['actual', 'period']})
        result, _ = self.reconcile()
        self.assertEqual(result['exact_value'], {'numerator': '50', 'denominator': '1'})
        self.assertEqual(result['display_value'], '50.00')
        self.assertEqual(result['numerator']['numerator'], '40')
        self.assertEqual(result['denominator']['numerator'], '80')
        self.assertEqual(result['quality']['dimensions']['completeness']['display_percent'], '100.00')

    def test_missing_zero_invalid_na_and_provisional_remain_distinct(self):
        self.publish(profile='TARGET_RATIO', baseline=None)
        cases = [(0, {}, 'VALID', '0.00'), (None, {}, 'MISSING', None),
                 ('bad', {}, 'INVALID', None), ({'state': 'NOT_APPLICABLE'}, {}, 'NOT_APPLICABLE', None),
                 (5, {'flags': ['PROVISIONAL']}, 'INVALID', None)]
        # Explicit flags mapping in a separate approved version is required.
        data = self.module.load_data_from_path()
        original = copy.deepcopy(data.projects[0].indicators[0].methodology)
        for value, extra, state, display in cases[:-1]:
            with self.subTest(state=state):
                self.set_rows([{'actual': value, 'period': '2026-09-30', **extra}])
                r, _ = self.reconcile()
                self.assertEqual((r['state'], r['display_value']), (state, display))
        self.assertEqual(self.module.load_data_from_path().projects[0].indicators[0].methodology, original)

    def test_provisional_and_invalid_unit_exclusions_propagate(self):
        self.publish(source_fields={'value': 'actual', 'period': 'period', 'flags': 'flags', 'unit': 'unit'})
        for extra, reason in [({'flags': ['PROVISIONAL'], 'unit': 'people'}, 'FLAG_POLICY_NOT_APPROVED'),
                              ({'unit': 'km'}, 'UNIT')]:
            self.set_rows([{'actual': 60, 'period': '2026-09-30', **extra}])
            r, _ = self.reconcile()
            self.assertIsNone(r['display_value'])
            self.assertEqual(r['coverage']['included'], 0)
            self.assertTrue(any(reason in key for key in r['exclusions']), r['exclusions'])
            if extra.get('flags'):
                self.assertEqual(r['coverage']['flags']['PROVISIONAL'], 1)

    def test_zero_denominator_no_numeric_fallback(self):
        self.publish(target=20)
        r, _ = self.reconcile()
        self.assertEqual(r['state'], 'INVALID')
        self.assertIsNone(r['display_value'])
        self.assertIn('ZERO_DENOMINATOR', r['warnings'])

    def test_downward_profile_and_uncapped_achievement(self):
        data = self.module.load_data_from_path()
        data.projects[0].indicators[0].direction = 'down'
        self.module.save_data_to_path(data)
        self.publish(direction='down', baseline=100, target=20)
        r, _ = self.reconcile()
        self.assertEqual(r['display_value'], '50.00')
        self.set_rows([{'actual': -20, 'period': '2026-09-30'}])
        r, _ = self.reconcile()
        self.assertEqual(r['state'], 'INVALID')

    def test_uncapped_target_ratio_and_separate_schedule_meaning(self):
        self.publish(profile='TARGET_RATIO', baseline=None)
        self.set_rows([{'actual': 150, 'period': '2026-09-30'}])
        r, _ = self.reconcile()
        self.assertEqual(r['display_value'], '150.00')
        self.publish(methodology_id='schedule', profile='TIME_PHASED', planned_targets={'2026-09-30': 150})
        schedule, _ = self.reconcile(self.params(methodology_id='schedule'))
        self.assertEqual(schedule['display_value'], '100.00')
        self.assertEqual(schedule['metric_kind'], 'schedule_attainment')
        self.assertNotEqual(schedule['calculation_id'], r['calculation_id'])

    def test_oc_a03_mean_and_coverage_with_independent_expected_values(self):
        self.publish(profile='TARGET_RATIO', baseline=None, aggregation='mean',
                     aggregation_rationale='Fictional comparable observations, equal eligibility.',
                     quality_rules={'required_fields': ['actual']})
        values = [0, 5, None, 'bad', {'state': 'NOT_APPLICABLE'}]
        self.set_rows([{'actual': v, 'period': '2026-09-30'} for v in values])
        r, _ = self.reconcile()
        self.assertEqual(r['actual'], {'numerator': '5', 'denominator': '2'})
        self.assertEqual(r['display_value'], '2.50')
        self.assertEqual((r['coverage']['source_total'], r['coverage']['applicable'], r['coverage']['included']), (5, 4, 2))
        self.assertIn('PARTIAL_COVERAGE', r['warnings'])
        self.assertEqual(r['quality']['dimensions']['completeness']['display_percent'], '50.00')

    def test_period_boundaries_and_as_of_filter_are_identical(self):
        self.publish(aggregation='mean', aggregation_rationale='Synthetic equal population.')
        self.set_rows([{'actual': 60, 'period': period} for period in ['2026-08-31', '2026-09-01', '2026-09-30', '2026-10-01']])
        r, _ = self.reconcile()
        self.assertEqual(r['coverage']['included'], 2)
        self.assertEqual(r['period_exclusions'], {'OUTSIDE_REPORTING_PERIOD': 2})
        early, _ = self.reconcile(self.params(as_of='2026-09-15T00:00:00Z'))
        self.assertEqual(early['coverage']['included'], 1)
        self.assertEqual(early['period_exclusions']['AFTER_AS_OF'], 1)
        self.assertNotEqual(early['calculation_id'], r['calculation_id'])

    def test_versions_and_source_revision_preserve_lineage_and_identity(self):
        self.publish(effective_to='2026-10-01')
        first, _ = self.reconcile()
        self.publish(version='2.0.0', effective_from='2026-10-01', effective_to='2027-01-01', target=180)
        second, _ = self.reconcile(self.params(version='2.0.0', as_of='2026-10-01T00:00:00Z'))
        self.assertEqual(second['display_value'], '25.00')
        self.assertNotEqual(second['definition_hash'], first['definition_hash'])
        self.set_rows([{'actual': 100, 'period': '2026-09-30'}])
        changed, _ = self.reconcile()
        self.assertEqual(changed['display_value'], '100.00')
        self.assertNotEqual(first['source']['revision'], changed['source']['revision'])

    def test_unsupported_profile_and_unconfigured_consumers(self):
        r, _ = self.reconcile(self.params(methodology_id='', version=''))
        self.assertEqual(r['state'], 'UNCONFIGURED')
        self.publish(profile='MILESTONE')
        r, _ = self.reconcile()
        self.assertEqual(r['state'], 'NOT_ASSESSED')
        self.assertIsNone(r['display_value'])
        self.assertIn('MILESTONE_EVIDENCE_CONTRACT_NOT_IMPLEMENTED', r['warnings'])

    def test_context_free_calls_cannot_infer_methods_scores_or_change_after_registration(self):
        before = self.client.get('/v1/kpi/indicator', headers=self.headers()).json()
        self.publish()
        self.assertEqual(self.client.get('/v1/kpi/indicator', headers=self.headers()).json(), before)
        self.assertEqual(before[0]['calculation_state'], 'UNCONFIGURED')
        quality = self.client.get('/v1/tidy_datasets/dataset_method/quality', headers=self.headers()).json()
        self.assertIsNone(quality['overall_score'])
        self.assertEqual({d['state'] for d in quality['profile']['dimensions'].values()}, {'NOT_ASSESSED'})
        self.assertIsNone(quality['data_freshness_days'])

    def test_query_cannot_certify_deferred_legacy_response(self):
        for path in ['/v1/kpi/project', '/v1/kpi/district']:
            response = self.client.get(path, headers=self.headers(), params={'as_of': AS_OF})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers['X-RCAtlas-Methodology-State'], 'LEGACY_UNVALIDATED')
            self.assertIn('Legacy analytics', response.headers['Warning'])

    def test_tenant_project_source_and_permission_boundaries(self):
        self.publish()
        params = dict(self.params(), project_id=SCOPE['project_id'], indicator_id=SCOPE['indicator_id'])
        for path in ['/v1/kpi/indicator', '/v1/projects/project_method/dashboard', '/v1/tidy_datasets/dataset_method/quality']:
            self.assertEqual(self.client.get(path, params=params).status_code, 401)
            foreign = self.client.get(path, params=params, headers=self.headers('method.b.organization_admin'))
            self.assertEqual(foreign.status_code, 404, foreign.text)
            self.assertNotIn('dataset_method', str(foreign.json()).replace("Tidy dataset 'dataset_method' not found.", ''))
        data = self.module.load_data_from_path()
        user = next(u for u in data.users if u.username == 'method.a.executive_viewer')
        user.permissions = ['VIEW_INDICATORS']
        self.module.save_data_to_path(data)
        for path in ['/v1/kpi/indicator', '/v1/projects/project_method/dashboard', '/v1/tidy_datasets/dataset_method/quality']:
            self.assertEqual(self.client.get(path, params=params, headers=self.headers(user.username)).status_code, 403)

    def test_unsupported_filters_partial_context_and_dataset_binding_rejected(self):
        self.publish()
        params = dict(self.params(), project_id=SCOPE['project_id'], indicator_id=SCOPE['indicator_id'])
        for extra in [{'district': 'X'}, {'start': ''}, {'as_of': '2026-09-30'}, {'version': ''}]:
            self.assertEqual(self.client.get('/v1/kpi/indicator', params=params | extra, headers=self.headers()).status_code, 400)
        r = self.client.get('/v1/projects/project_method/dashboard', params=params | {'project_id': 'other'}, headers=self.headers())
        self.assertEqual(r.status_code, 400)
        r = self.client.get('/v1/kpi/indicator', params=params | {'project_id': 'other'}, headers=self.headers())
        self.assertEqual(r.status_code, 404)

    def test_no_writes_or_hidden_clock_in_selected_result(self):
        self.publish()
        before = self.module.load_data_from_path()
        first, _ = self.reconcile()
        with patch.object(self.module, 'utc_now', return_value=self.module.datetime(2040, 1, 1, tzinfo=self.module.timezone.utc)):
            # Direct adapter: excludes existing auth/session audit clocks entirely.
            second = consumers.calculate_indicator(before, **SCOPE, selected=consumers.selection(**self.params()))
        self.assertEqual(first, second['result'])
        after = self.module.load_data_from_path()
        self.assertEqual(after.projects, before.projects)
        self.assertEqual(after.tidy_datasets, before.tidy_datasets)
        self.assertEqual(after.projects[0].indicators[0].methodology['instances'], [])

    def test_legacy_input_and_aggregate_guardrails_do_not_invent_zero(self):
        data = self.module.load_data_from_path()
        indicator = data.projects[0].indicators[0]
        indicator.locations = [self.module.LocationEntry(country='X', province='Y', district='Z', latitude=0,
            longitude=0, actual_local=60, target_local=100, budget_local=None, currency='USD')]
        payload = self.module.build_bi_payload(data)
        for key in ['kpi_project', 'kpi_district']:
            self.assertIsNone(payload[key][0]['progress_weighted_pct'])
            self.assertEqual(payload[key][0]['calculation_state'], 'NOT_ASSESSED')
        self.assertIsNone(payload['indicator_locations'][0]['progress_pct'])
        self.assertEqual(payload['indicator_locations'][0]['actual_local'], 60)

    def test_unresolved_indicator_ownership_is_blocked_without_repair(self):
        data = self.module.load_data_from_path()
        indicator = data.projects[0].indicators[0]
        indicator.organization_id = ''
        before = copy.deepcopy(data)
        row = consumers.indicator_kpi(data, data.projects[0], indicator)
        self.assertEqual(row['calculation_state'], 'BLOCKED')
        self.assertIn('UNRESOLVED_OWNERSHIP', row['calculation']['result']['warnings'])
        self.assertIsNone(row['calculated_value'])
        self.assertEqual(data, before)

    def test_csv_projection_keeps_unsupported_state_and_original_columns(self):
        data = self.module.load_data_from_path()
        out = Path(self.temp.name) / 'synthetic-csv'
        self.module.export_bi_csv(data, str(out))
        with (out / 'kpi_indicator.csv').open(encoding='utf-8', newline='') as file:
            rows = list(csv.DictReader(file))
        self.assertEqual(rows[0]['indicator_id'], 'indicator_method')
        self.assertEqual(rows[0]['progress_weighted_pct'], '')
        self.assertEqual(rows[0]['calculation_state'], 'UNCONFIGURED')
        self.assertEqual(rows[0]['aggregation_state'], 'NOT_ASSESSED')


if __name__ == '__main__':
    unittest.main()
