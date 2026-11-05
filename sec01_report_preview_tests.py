"""Synthetic paired-route and response-contract tests for report notification access."""
from dataclasses import replace
from datetime import date
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import sec01_snapshot_tests as fixture


REPORT = '/v1/demo/report_preview'
NOTIFICATIONS = '/v1/notifications'
AUDIENCES = ('donor', 'management', 'meal')


class ReportPreviewAuthorizationTests(unittest.TestCase):
    # Keep the local calendar day of the immutable six-report capture.
    calendar_day = date(2026, 10, 30)
    setUp = fixture.SnapshotAuthorizationTests.setUp
    grants = fixture.SnapshotAuthorizationTests.grants

    def report(self, headers=None, project_id=None, audience='management'):
        params = {'audience': audience}
        if project_id is not None:
            params['project_id'] = project_id
        response = self.client.get(REPORT, headers=headers or self.admin, params=params)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_fully_authorized_reports_match_before_golden(self):
        reports = {f'{scope}:{audience}': self.report(project_id=project, audience=audience)
                   for scope, project in (('portfolio', None), ('project', 'proj_health'))
                   for audience in AUDIENCES}
        for report in reports.values():
            self.assertTrue(report['sections'][-1]['bullets'])
            self.assertNotIn('restricted_sections', report)
        golden = Path(os.environ.get('SEC01_REPORT_GOLDEN',
            Path(__file__).resolve().parent / 'test_fixtures' / 'sec01' / 'report_previews.json'))
        if os.environ.get('SEC01_CAPTURE_REPORT') == 'true':
            if golden.exists():
                raise AssertionError('Never overwrite the pre-correction report baseline.')
            golden.write_text(json.dumps(reports, indent=2), encoding='utf-8')
        else:
            self.assertEqual(reports, json.loads(golden.read_text(encoding='utf-8')))

    def test_portfolio_notification_detail_matches_protected_route(self):
        for grants in (['VIEW_PORTFOLIO', 'VIEW_REPORTS'],
                       ['VIEW_PORTFOLIO', 'VIEW_REPORTS', 'GENERATE_REPORTS']):
            for audience in AUDIENCES:
                with self.subTest(grants=grants, audience=audience):
                    reference = self.report(audience=audience)
                    headers = self.grants(grants, role='organization_admin')
                    self.assertEqual(self.client.get(NOTIFICATIONS, headers=headers).status_code, 403)
                    report = self.report(headers, audience=audience)
                    self.assertEqual(report['highlights'], reference['highlights'])
                    self.assertEqual(report['sections'][:2], reference['sections'][:2])
                    for title in reference['sections'][-1]['bullets']:
                        self.assertNotIn(title, json.dumps(report))
                    self.assertEqual(report['sections'][-1]['bullets'], [])
                    self.assertIn('restricted', report['sections'][-1]['body'].lower())
                    self.assertIn('notifications', report['restricted_sections'])
                    allowed = self.grants(grants + ['VIEW_NOTIFICATIONS'])
                    self.assertEqual(self.client.get(NOTIFICATIONS, headers=allowed).status_code, 200)
                    self.assertEqual(self.report(allowed, audience=audience), reference)

    def test_project_redaction_metadata_and_aggregate_are_preserved(self):
        reference = self.report(project_id='proj_health')
        headers = self.grants([p for p in fixture.DETAIL if p != 'VIEW_NOTIFICATIONS'])
        self.assertEqual(self.client.get(NOTIFICATIONS, headers=headers).status_code, 403)
        for audience in AUDIENCES:
            with self.subTest(audience=audience):
                report = self.report(headers, project_id='proj_health', audience=audience)
                self.assertEqual(report['highlights'], reference['highlights'])
                self.assertIn('notifications', report.get('restricted_sections', []))
                self.assertEqual(report['sections'][-1]['bullets'], [])
                self.assertIn('restricted', report['sections'][-1]['body'].lower())
                for title in reference['sections'][-1]['bullets']:
                    self.assertNotIn(title, json.dumps(report))

    def test_no_notifications_is_distinct_from_restricted_notifications(self):
        service = self.module.demo_workspace_service
        with patch.object(service, 'deps', replace(service.deps, build_current_notifications=lambda _: [])), \
             patch.object(service, '_operational_notifications', return_value=[]):
            for project in (None, 'proj_health'):
                with self.subTest(project=project):
                    authorized = self.report(project_id=project)
                    self.assertEqual(authorized['sections'][-1]['bullets'], [])
                    self.assertNotIn('restricted_sections', authorized)
                    self.assertNotIn('restricted', authorized['sections'][-1]['body'].lower())
                    headers = self.grants(['VIEW_PORTFOLIO', 'VIEW_REPORTS', 'VIEW_EXECUTIVE_SNAPSHOT'])
                    restricted = self.report(headers, project_id=project)
                    self.assertEqual(restricted['highlights'], authorized['highlights'])
                    self.assertIn('notifications', restricted.get('restricted_sections', []))
                    if project:
                        self.assertIn('0 current alerts require follow-up.', restricted['highlights'])
                        self.assertIn('NOT_ASSESSED', json.dumps(restricted))

    def test_explicit_denial_and_tenant_scope(self):
        data = self.module.load_data_from_path()
        foreign = self.module.Project(id='foreign_preview_project', name='FOREIGN_PREVIEW_SENTINEL',
                                      objective='Synthetic foreign tenant fixture', organization_id='org_method_b')
        data.projects.append(foreign)
        self.module.save_data_to_path(data)
        for project in (None, 'proj_health'):
            params = {} if project is None else {'project_id': project}
            self.assertEqual(self.client.get(REPORT, params=params).status_code, 401)
            headers = self.grants([], role='organization_admin')
            self.assertEqual(self.client.get(REPORT, headers=headers, params=params).status_code, 403)
            self.assertNotIn('FOREIGN_PREVIEW_SENTINEL', json.dumps(self.report(project_id=project)))
        self.assertEqual(self.client.get(REPORT, headers=self.admin,
                         params={'project_id': foreign.id}).status_code, 404)
        foreign_headers = {'X-Auth-Token': 'token-method.b.organization_admin'}
        self.assertEqual(self.client.get(REPORT, headers=foreign_headers,
                         params={'project_id': 'proj_health'}).status_code, 404)
        foreign_report = self.report(foreign_headers)
        self.assertIn('FOREIGN_PREVIEW_SENTINEL', json.dumps(foreign_report))
        self.assertNotIn('proj_health', json.dumps(foreign_report))
