"""Consumer reads against actual PostgreSQL, including restart and immutable history."""
import copy
import os
import unittest

import methodology_postgresql_tests as fixture
from methodology_fixtures import AS_OF


@unittest.skipUnless(os.getenv('RCATLAS_PG_TEST_BIN') and os.getenv('RCATLAS_PG_TEST_ROOT'),
                     'Actual disposable PostgreSQL required; no mock substitute.')
class AnalyticalPostgreSQLTests(unittest.TestCase):
    setUpClass = classmethod(fixture.MethodologyPostgreSQLTests.setUpClass.__func__)
    setUp = fixture.MethodologyPostgreSQLTests.setUp
    publish_and_save = fixture.MethodologyPostgreSQLTests.publish_and_save

    def outputs(self):
        query = dict(start='2026-09-01', end='2026-09-30', as_of=AS_OF, locale='EN',
                     methodology_id='change-achievement', version='1.0.0', project_id='project_method', indicator_id='indicator_method')
        result = []
        for path in ['/v1/kpi/indicator', '/v1/projects/project_method/dashboard',
                     '/v1/tidy_datasets/dataset_method/quality', '/v1/tidy_datasets/dataset_method/narrative']:
            response = self.client.get(path, params=query, headers=self.headers)
            self.assertEqual(response.status_code, 200, response.text)
            result.append(response.json())
        return result

    def test_all_consumers_reconcile_to_persisted_instance_without_writes(self):
        saved = self.publish_and_save()
        before = self.store.load()
        rows, dashboard, quality, narrative = self.outputs()
        for envelope in [rows[0]['calculation'], dashboard['kpi_indicator'][0]['calculation'], quality['calculation'], narrative['calculation']]:
            self.assertEqual(envelope['result'], saved)
        self.assertEqual(saved['display_value'], '50.00')
        self.assertEqual(before, self.store.load())
        self.assertFalse(list(self.cluster.root.glob('forbidden-*')))

    def test_restart_recovers_identical_consumers_and_source_revision(self):
        self.publish_and_save()
        before = self.outputs()
        self.cluster.stop(); self.cluster.start()
        after = self.outputs()
        for outputs in (before, after):
            # Same complete calculations; the surrounding operational dashboard
            # contains generated_at metadata and deferred operational clocks.
            outputs[1] = outputs[1]['kpi_indicator']
            outputs[3] = outputs[3]['quality']
        self.assertEqual(before, after)

    def test_foreign_reads_and_source_change_leave_saved_history_immutable(self):
        saved = self.publish_and_save()
        query = dict(start='2026-09-01', end='2026-09-30', as_of=AS_OF, methodology_id='change-achievement',
                     version='1.0.0', project_id='project_method', indicator_id='indicator_method')
        foreign = {'X-Auth-Token': 'token-method.b.organization_admin'}
        for path in ['/v1/kpi/indicator', '/v1/projects/project_method/dashboard', '/v1/tidy_datasets/dataset_method/quality']:
            response = self.client.get(path, params=query, headers=foreign)
            self.assertEqual(response.status_code, 404)
        data = self.module.load_data_from_path()
        data.tidy_datasets[0].rows = [{'actual': 100, 'period': '2026-09-30'}]
        self.module.save_data_to_path(data)
        changed = self.outputs()[0][0]['calculation']['result']
        self.assertEqual(changed['display_value'], '100.00')
        self.assertNotEqual(saved['source']['revision'], changed['source']['revision'])
        self.assertEqual(self.store.load()['projects'][0]['indicators'][0]['methodology']['instances'][0]['result'], saved)
