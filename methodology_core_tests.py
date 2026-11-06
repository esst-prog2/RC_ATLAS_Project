import copy
from fractions import Fraction
import unittest

from services import methodology as m
from methodology_fixtures import AS_OF, SCOPE, definition_payload, rows


class MethodologyCoreTests(unittest.TestCase):
    def result(self, observations=None, **overrides):
        return m.calculate(m.definition(definition_payload(**overrides), SCOPE), rows() if observations is None else observations,
                           m.context('2026-09-01', '2026-09-30', AS_OF))

    def test_approved_change_fixture_exact_intermediates(self):
        r = self.result()
        self.assertEqual(r['exact_value'], {'numerator': '50', 'denominator': '1'})
        self.assertEqual(r['numerator'], {'numerator': '40', 'denominator': '1'})
        self.assertEqual(r['denominator'], {'numerator': '80', 'denominator': '1'})
        self.assertEqual(r['display_value'], '50.00')
        self.assertEqual(r['metric_kind'], 'final_target_achievement')

    def test_schedule_is_separate_approved_exact_point(self):
        r = self.result(profile='TIME_PHASED', planned_targets={'2026-09-30': 60})
        self.assertEqual(r['display_value'], '100.00')
        self.assertEqual(r['metric_kind'], 'schedule_attainment')
        self.assertEqual(self.result(profile='TIME_PHASED', planned_targets={'2026-09-29': 60})['state'], 'UNCONFIGURED')

    def test_downward_change_matches_direction(self):
        self.assertEqual(self.result(baseline=100, target=20, direction='down')['display_value'], '50.00')
        self.assertEqual(self.result(direction='down')['state'], 'INVALID')

    def test_downward_ratio_not_invented(self):
        r = self.result(profile='TARGET_RATIO', direction='down')
        self.assertEqual(r['state'], 'UNCONFIGURED')
        self.assertIsNone(r['exact_value'])

    def test_overachievement_and_negative_change_uncapped(self):
        self.assertEqual(self.result(rows(150), profile='TARGET_RATIO')['display_value'], '150.00')
        self.assertEqual(self.result(rows(10))['display_value'], '-12.50')

    def test_zero_denominators_explicit_invalid(self):
        for overrides in ({'baseline': 100, 'target': 100}, {'profile': 'TARGET_RATIO', 'target': 0},
                          {'profile': 'TIME_PHASED', 'planned_targets': {'2026-09-30': 0}}):
            with self.subTest(overrides=overrides):
                r = self.result(**overrides)
                self.assertEqual(r['state'], 'INVALID')
                self.assertIn('ZERO_DENOMINATOR', r['warnings'])
                self.assertIsNone(r['display_value'])

    def test_legitimate_zero_and_missing_remain_distinct(self):
        self.assertEqual(self.result(rows(0), profile='TARGET_RATIO')['display_value'], '0.00')
        self.assertEqual(self.result(rows(None), profile='TARGET_RATIO')['state'], 'MISSING')
        self.assertIsNone(self.result(rows(None))['display_value'])

    def test_invalid_na_and_boolean_observations(self):
        self.assertEqual(self.result(rows('bad'))['state'], 'INVALID')
        self.assertEqual(self.result(rows(True))['state'], 'INVALID')
        self.assertEqual(self.result(rows({'state': 'NOT_APPLICABLE', 'value': None}))['state'], 'NOT_APPLICABLE')

    def test_nonfinite_values_and_malformed_state_flags_are_invalid(self):
        for value in (float('nan'), float('inf'), float('-inf'), {'state': [], 'value': 2}):
            self.assertEqual(self.result(rows(value))['state'], 'INVALID')
        r = self.result([{'actual': 60, 'period': '2026-09-30', 'flags': [{}]}],
                        source_fields={'value': 'actual', 'period': 'period', 'flags': 'flags'})
        self.assertEqual(r['state'], 'INVALID')

    def test_approved_state_fixture_mean_and_coverage(self):
        observations = [dict(period='2026-09-30', actual=v) for v in
                        [0, 5, None, {'state': 'INVALID', 'value': 'bad'}, {'state': 'NOT_APPLICABLE', 'value': None}]]
        r = self.result(observations, profile='TARGET_RATIO', target=100, aggregation='mean', aggregation_rationale='OC-A03 valid-value mean')
        self.assertEqual(r['actual'], {'numerator': '5', 'denominator': '2'})
        self.assertEqual({k: r['coverage'][k] for k in ('in_period', 'included', 'applicable', 'excluded')},
                         {'in_period': 5, 'included': 2, 'applicable': 4, 'excluded': 3})
        self.assertEqual(r['display_value'], '2.50')

    def test_incomparable_units_and_currencies_excluded(self):
        for field, value, reason in [('unit', 'km', 'INCOMPATIBLE_UNIT'), ('currency', 'USD', 'INCOMPATIBLE_CURRENCY')]:
            r = self.result([dict(actual=60, period='2026-09-30', **{field: value})],
                            source_fields={'value': 'actual', 'period': 'period', field: field})
            self.assertEqual(r['coverage']['included'], 0)
            self.assertEqual(r['exclusions'][reason], 1)

    def test_flags_never_erase_underlying_state_or_enter_calculation(self):
        r = self.result([dict(actual=60, period='2026-09-30', flags=['PROVISIONAL'])],
                        source_fields={'value': 'actual', 'period': 'period', 'flags': 'flags'})
        self.assertEqual(r['coverage']['states']['VALID'], 1)
        self.assertEqual(r['coverage']['flags']['PROVISIONAL'], 1)
        self.assertEqual(r['coverage']['included'], 0)
        r = self.result([dict(actual=60, period='2026-09-30', flags=['IMPUTED'], original='MISSING')],
                        source_fields={'value': 'actual', 'period': 'period', 'flags': 'flags', 'original_state': 'original'})
        self.assertEqual(r['inputs'][0]['original_state'], 'MISSING')
        self.assertIn('FLAG_POLICY_NOT_APPROVED', r['exclusions'])

    def test_duplicate_identity_excludes_all_members_without_arbitrary_winner(self):
        observations = [dict(actual=v, period='2026-09-30', id='duplicate') for v in (10, 20)]
        r = self.result(observations, quality_rules={'identity_fields': ['id']})
        self.assertEqual(r['exclusions'], {'DUPLICATE_IDENTITY': 2})

    def test_period_boundaries_and_future_cutoff(self):
        observations = [dict(actual=60, period=p) for p in ('2026-08-31', '2026-09-01', '2026-09-30', '2026-10-01', 'invalid')]
        r = self.result(observations, aggregation='mean', aggregation_rationale='Fictional equal observations')
        self.assertEqual(r['coverage']['included'], 2)
        self.assertEqual(r['period_exclusions'], {'OUTSIDE_REPORTING_PERIOD': 2, 'INVALID_OR_MISSING_PERIOD': 1})
        d = m.definition(definition_payload(), SCOPE)
        r = m.calculate(d, rows(), m.context('2026-09-01', '2026-09-30', '2026-09-29T23:59:59Z'))
        self.assertEqual(r['period_exclusions'], {'AFTER_AS_OF': 1})

    def test_context_requires_real_dates_order_and_timezone(self):
        for start, end, stamp in [('2026-02-30', '2026-09-30', AS_OF), ('2026-09-30', '2026-09-01', AS_OF),
                                  ('2026-09-01', '2026-09-30', '2026-09-30T12:00:00')]:
            with self.assertRaises(m.MethodologyError):
                m.context(start, end, stamp)
        self.assertEqual(m.context('2026-09-01', '2026-09-30', '2026-10-01T01:59:59+02:00')['as_of'], AS_OF)

    def test_effective_period_is_start_inclusive_end_exclusive(self):
        self.assertEqual(self.result(effective_from='2026-09-30')['state'], 'VALID')
        self.assertEqual(self.result(effective_to='2026-09-30')['state'], 'NOT_ASSESSED')

    def test_band_boundaries_no_arbitrary_score(self):
        d = m.definition(definition_payload(profile='MAINTENANCE_BAND', direction='maintain', band={'lower': 10, 'upper': 20}), SCOPE)
        self.assertIsNone(d['numerator_definition'])
        self.assertIsNone(d['denominator_definition'])
        self.assertEqual(d['target_semantics'], 'approved inclusive lower and upper bounds')
        for value, expected in [(9, 'BELOW_BAND'), (10, 'IN_BAND'), (20, 'IN_BAND'), (21, 'ABOVE_BAND')]:
            r = self.result(rows(value), profile='MAINTENANCE_BAND', direction='maintain', band={'lower': 10, 'upper': 20})
            self.assertEqual(r['band_state'], expected)
            self.assertIsNone(r['exact_value'])

    def test_unsupported_or_unapproved_methods_unavailable(self):
        for overrides, expected in [({'profile': 'MILESTONE'}, 'NOT_ASSESSED'),
                                    ({'profile': 'NO_AUTOMATIC_PROGRESS'}, 'NOT_ASSESSED'),
                                    ({'status': 'UNCONFIGURED'}, 'UNCONFIGURED'),
                                    ({'target': None}, 'UNCONFIGURED'),
                                    ({'profile': 'TARGET_RATIO', 'scale': 'ordinal'}, 'UNCONFIGURED')]:
            self.assertEqual(self.result(**overrides)['state'], expected)

    def test_multiple_observations_do_not_infer_sum_or_mean(self):
        r = self.result(rows() + rows(80))
        self.assertEqual(r['state'], 'BLOCKED')
        self.assertIsNone(r['actual'])

    def test_exact_fraction_separate_from_display(self):
        r = self.result(rows(1), profile='TARGET_RATIO', target=3)
        self.assertEqual(r['exact_value'], {'numerator': '100', 'denominator': '3'})
        self.assertEqual(r['display_value'], '33.33')

    def test_completeness_independent_45_of_50_fixture(self):
        observations = [{f'f{j}': 0 if i < 9 else None for j in range(5)} for i in range(10)]
        q = m.quality_profile(observations, {'required_fields': [f'f{j}' for j in range(5)]}, AS_OF, 'Synthetic declared use')
        d = q['dimensions']['completeness']
        self.assertEqual((d['numerator'], d['denominator'], d['display_percent']), (45, 50, '90.00'))
        self.assertNotIn('overall_score', q)
        self.assertEqual(q['fitness'], 'FITNESS_NOT_CONFIGURED')

    def test_uniqueness_independent_seven_of_eight_fixture(self):
        observations = [{'id': i} for i in [1, 2, 3, 4, 5, 6, 7, 7, None, None]]
        d = m.quality_profile(observations, {'identity_fields': ['id']}, AS_OF, 'Synthetic')['dimensions']['uniqueness']
        self.assertEqual((d['numerator'], d['denominator'], d['display_percent']), (7, 8, '87.50'))
        self.assertEqual(d['exclusions']['UNASSESSABLE_KEY'], 2)

    def test_conformance_timeliness_traceability_explicit_rules(self):
        observations = [dict(value=0, observed='2026-09-30', source='s', revision='r'),
                        dict(value=-1, observed='2026-09-20', source='s'),
                        dict(value=None, observed='bad'), dict(value=True, observed='2026-10-01')]
        q = m.quality_profile(observations, {'conformance': {'value': {'type': 'number', 'min': 0}},
            'timeliness': {'field': 'observed', 'max_age_days': 5}, 'traceability_fields': ['source', 'revision']}, AS_OF, 'Synthetic')['dimensions']
        self.assertEqual((q['conformance']['numerator'], q['conformance']['denominator']), (1, 3))
        self.assertEqual((q['timeliness']['numerator'], q['timeliness']['denominator']), (1, 3))
        self.assertEqual((q['traceability']['numerator'], q['traceability']['denominator']), (1, 4))

    def test_quality_missing_rules_empty_population_and_na(self):
        q = m.quality_profile([], {}, AS_OF, 'Synthetic')
        self.assertTrue(all(d['state'] == 'NOT_ASSESSED' for d in q['dimensions'].values()))
        q = m.quality_profile([{'x': {'state': 'NOT_APPLICABLE'}}], {'required_fields': ['x']}, AS_OF, 'Synthetic')
        self.assertEqual(q['dimensions']['completeness']['denominator'], 0)
        self.assertIsNone(q['dimensions']['completeness']['display_percent'])

    def test_quality_respects_mapped_observation_state_and_domain(self):
        r = self.result([{'actual': 60, 'period': '2026-09-30', 'state': 'INVALID'}],
                        source_fields={'value': 'actual', 'period': 'period', 'state': 'state'},
                        quality_rules={'required_fields': ['actual'], 'conformance': {'actual': {'type': 'number'}}})
        self.assertEqual(r['quality']['dimensions']['completeness']['numerator'], 0)
        self.assertEqual(r['quality']['dimensions']['conformance']['numerator'], 0)
        self.assertEqual(r['coverage']['states']['INVALID'], 1)
        r = self.result(rows(-1))
        self.assertEqual(r['coverage']['states']['INVALID'], 1)
        self.assertEqual(r['exclusions'], {'OUTSIDE_DOMAIN': 1})

    def test_reproducibility_row_order_and_changed_source_identity(self):
        overrides = {'aggregation': 'mean', 'aggregation_rationale': 'Synthetic valid-value mean'}
        first = self.result(rows(10) + rows(20), **overrides)
        self.assertEqual(first, self.result(rows(20) + rows(10), **overrides))
        self.assertNotEqual(first['calculation_id'], self.result(rows(10) + rows(21), **overrides)['calculation_id'])

    def test_definition_version_and_scope_change_identity(self):
        self.assertNotEqual(self.result()['calculation_id'], self.result(version='1.0.1')['calculation_id'])
        d = m.definition(definition_payload(), dict(SCOPE, organization_id='another_org'))
        r = m.calculate(d, rows(), m.context('2026-09-01', '2026-09-30', AS_OF))
        self.assertNotEqual(self.result()['calculation_id'], r['calculation_id'])

    def test_immutable_versions_idempotency_and_overlap(self):
        definitions = []
        first = m.definition(definition_payload(), SCOPE)
        self.assertTrue(m.register(definitions, first))
        self.assertFalse(m.register(definitions, first))
        for overrides in ({'target': 200}, {'version': '2.0.0'}):
            with self.assertRaises(m.MethodologyError):
                m.register(definitions, m.definition(definition_payload(**overrides), SCOPE))
        self.assertTrue(m.register(definitions, m.definition(definition_payload(version='2.0.0',
                             effective_from='2027-01-01', effective_to='2028-01-01'), SCOPE)))

    def test_corrupt_definition_and_unapproved_config_rejected(self):
        d = m.definition(definition_payload(), SCOPE)
        d['target'] = 1000
        with self.assertRaises(m.MethodologyError):
            m.calculate(d, rows(), m.context('2026-09-01', '2026-09-30', AS_OF))
        for overrides in ({'version': 'latest'}, {'owner_decision': ''}, {'domain': {}},
                          {'aggregation': 'mean'}, {'formula': 'eval'}, {'quality_rules': {'score': 100}}):
            with self.assertRaises(m.MethodologyError):
                m.definition(definition_payload(**overrides), SCOPE)

    def test_explicit_guardrails_and_source_data_minimization(self):
        r = self.result([dict(actual=60, period='2026-09-30', secret='SENSITIVE_SENTINEL')])
        self.assertNotIn('SENSITIVE_SENTINEL', str(r))
        self.assertEqual(r['statistical_trend'], 'NOT_ASSESSED')
        self.assertEqual(r['portfolio_aggregation'], 'NOT_ASSESSED')


if __name__ == '__main__':
    unittest.main()
