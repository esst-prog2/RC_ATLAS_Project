"""Synthetic, paired-route regressions for SEC-01 executive snapshot disclosure."""
import json
import os
from copy import deepcopy
from dataclasses import replace
from datetime import date, datetime, timezone
from pathlib import Path
import unittest
from unittest.mock import patch

import methodology_api_tests as fixture
from services.demo_seed import build_demo_seed_bundle


SNAPSHOT = '/v1/demo/projects/proj_health/executive_snapshot'
DASHBOARD = '/v1/projects/proj_health/dashboard'
DETAIL = ['VIEW_EXECUTIVE_SNAPSHOT', 'VIEW_INDICATORS', 'VIEW_REPORTS',
          'VIEW_WORKPLAN', 'VIEW_NOTIFICATIONS']
CLOCK = datetime(2026, 10, 28, 12, tzinfo=timezone.utc)


def stable_snapshot(value):
    # Notification IDs use datetime.now directly, outside the fixture's clock.
    # Compare every other field, including source IDs, timestamps and values.
    if isinstance(value, dict):
        return {key: '<generated-notification-id>' if key == 'id' and isinstance(item, str)
                and item.startswith('notif_') else stable_snapshot(item) for key, item in value.items()}
    if isinstance(value, list):
        return [stable_snapshot(item) for item in value]
    return value


class SnapshotAuthorizationTests(unittest.TestCase):
    # The original snapshot used this local calendar day, independently of UTC.
    calendar_day = date(2026, 10, 29)

    def setUp(self):
        fixture.MethodologyApiTests.setUp(self)
        with patch('services.demo_seed._utc_now', return_value=CLOCK):
            # Only synthetic fixture identities; no passwords are used by these
            # header-session tests, so avoid expensive unrelated credential work.
            data = self.module.from_serializable(build_demo_seed_bundle(
                lambda _: ('synthetic-salt', 'synthetic-unused-hash')).payload)
        data.users.extend(self.data.users)
        data.organizations.extend(self.data.organizations)
        for user in data.users:
            if user.username.startswith('method.a.'):
                user.organization_id = 'org_blue_delta'
        data.sessions = []
        for user in data.users:
            if user.username.startswith('method.'):
                self.module.register_session_for_token(data, user, 'token-' + user.username)
        data.audit_events.append(self.module.AuditEvent(
            id='sec01_audit', organization_id='org_blue_delta', actor_username='AUDIT_DETAIL_SENTINEL',
            action='sec01.synthetic', target_id='proj_health', occurred_at='2026-10-28T12:00:00Z',
            details={'project_id': 'proj_health', 'message': 'AUDIT_MESSAGE_SENTINEL'}))
        self.module.save_data_to_path(data)
        service = self.module.demo_workspace_service
        original = service.deps
        service.deps = replace(original, now_iso_utc=lambda: '2026-10-28T12:00:00Z')
        self.addCleanup(setattr, service, 'deps', original)
        self.admin = {'X-Auth-Token': 'token-method.a.organization_admin'}
        # The service's copied clock function and main global clock are both fixed.
        clock_patch = patch.object(self.module, 'utc_now', return_value=CLOCK)
        clock_patch.start()
        self.addCleanup(clock_patch.stop)
        # Legacy workplan/deadline calculations also use date.today(). Freeze
        # that source without normalizing away changed counts or due dates.
        day = self.calendar_day
        class DateMeta(type):
            def __instancecheck__(cls, value):
                return isinstance(value, date)
        class CalendarDate(date, metaclass=DateMeta):
            @classmethod
            def today(cls):
                return day
        date_patch = patch.object(self.module, 'date', CalendarDate)
        date_patch.start()
        self.addCleanup(date_patch.stop)

    def grants(self, grants, role='executive_viewer'):
        data = self.module.load_data_from_path()
        user = next(u for u in data.users if u.username == 'method.a.executive_viewer')
        user.permissions, user.permission_policy_version, user.role = grants, 1, role
        self.module.save_data_to_path(data)
        return {'X-Auth-Token': 'token-' + user.username}

    def snapshot(self, headers=None, **params):
        result = self.client.get(SNAPSHOT, headers=headers or self.admin, params=params)
        self.assertEqual(result.status_code, 200, result.text)
        return stable_snapshot(result.json())

    def test_full_access_response_matches_pre_rework_golden(self):
        body = self.snapshot()
        self.assertTrue(body['indicators'])
        self.assertTrue(body['tasks'])
        self.assertTrue(body['reporting_records'])
        self.assertTrue(body['dashboard']['widgets'])
        self.assertIn('AUDIT_DETAIL_SENTINEL', json.dumps(body))
        golden = Path(os.environ['SEC01_SNAPSHOT_GOLDEN'])
        if os.environ.get('SEC01_CAPTURE_SNAPSHOT') == 'true':
            if golden.exists():
                raise AssertionError('Never overwrite captured baseline.')
            golden.write_text(json.dumps(body, indent=2), encoding='utf-8')
        else:
            self.assertEqual(body, stable_snapshot(json.loads(golden.read_text(encoding='utf-8'))))

    def test_summary_survives_but_restricted_data_cannot_use_alternative_route(self):
        reference = self.snapshot()
        headers = self.grants(['VIEW_EXECUTIVE_SNAPSHOT'])
        self.assertEqual(self.client.get(DASHBOARD, headers=headers).status_code, 403)
        self.assertEqual(self.client.get('/v1/kpi/indicator', headers=headers).status_code, 403)
        body = self.snapshot(headers)
        self.assertEqual(body['project'], reference['project'])
        self.assertEqual(body['executive'], reference['executive'])
        self.assertEqual(body['analytical_contract'], reference['analytical_contract'])
        for key in ('indicators', 'activities', 'tasks', 'overdue_tasks', 'notifications',
                    'reporting_records', 'districts', 'trend', 'activity_feed'):
            with self.subTest(section=key):
                self.assertEqual(body[key], [])
        self.assertEqual(body['workflow'], {})
        self.assertEqual(body['narrative'].get('notifications', []), [])
        self.assertEqual(body['narrative'].get('trend', []), [])
        self.assertEqual(body['dashboard']['available_templates'], [])
        self.assertTrue(body['dashboard']['widgets'], 'Keep an authorized executive summary.')
        self.assertIn('restricted_sections', body)
        text = json.dumps(body)
        self.assertNotIn('AUDIT_DETAIL_SENTINEL', text)
        for task in reference['tasks']:
            self.assertNotIn(task['task_id'], text)

    def test_each_missing_capability_removes_all_copies(self):
        for missing, fields, denied_route in (
            ('VIEW_INDICATORS', ['indicators'], '/v1/kpi/indicator'),
            ('VIEW_REPORTS', ['indicators', 'reporting_records', 'districts', 'trend'], '/v1/kpi/project'),
            ('VIEW_WORKPLAN', ['activities', 'tasks', 'overdue_tasks'], '/v1/tasks'),
            ('VIEW_NOTIFICATIONS', ['notifications'], '/v1/notifications'),
        ):
            with self.subTest(missing=missing):
                headers = self.grants([p for p in DETAIL if p != missing])
                self.assertEqual(self.client.get(denied_route, headers=headers).status_code, 403)
                self.assertEqual(self.client.get(DASHBOARD, headers=headers).status_code, 403)
                body = self.snapshot(headers)
                for field in fields:
                    self.assertEqual(body[field], [], field)
                if missing == 'VIEW_NOTIFICATIONS':
                    self.assertEqual(body['narrative'].get('notifications', []), [])
                if missing == 'VIEW_REPORTS':
                    self.assertEqual(body['narrative'].get('trend', []), [])
                for widget in body['dashboard']['widgets']:
                    if missing == 'VIEW_WORKPLAN':
                        self.assertNotEqual(widget['chart_type'], 'activity_progress')
                    if missing == 'VIEW_NOTIFICATIONS':
                        self.assertNotEqual(widget['chart_type'], 'notification_summary')
                    if missing == 'VIEW_INDICATORS':
                        self.assertNotEqual(widget['chart_type'], 'status_donut')

    def test_detail_grants_preserve_authorized_sections_without_audit_access(self):
        reference = self.snapshot()
        headers = self.grants(DETAIL)
        body = self.snapshot(headers)
        self.assertEqual(self.client.get(DASHBOARD, headers=headers).status_code, 200)
        for key in reference.keys() - {'activity_feed'}:
            self.assertEqual(body[key], reference[key], key)
        self.assertEqual(body['activity_feed'], [item for item in reference['activity_feed']
                                               if item['action'].startswith('workflow.')])
        self.assertNotIn('AUDIT_DETAIL_SENTINEL', json.dumps(body))
        body = self.snapshot(self.grants(DETAIL + ['VIEW_AUDIT_LOG']))
        self.assertEqual(body, reference)

    def test_single_category_grant_does_not_expose_sibling_categories(self):
        reference = self.snapshot()
        for capability, field in (('VIEW_WORKPLAN', 'tasks'), ('VIEW_REPORTS', 'reporting_records'),
                                  ('VIEW_NOTIFICATIONS', 'notifications'), ('VIEW_AUDIT_LOG', 'activity_feed')):
            with self.subTest(capability=capability):
                body = self.snapshot(self.grants(['VIEW_EXECUTIVE_SNAPSHOT', capability]))
                self.assertEqual(body[field], reference[field])
                self.assertEqual(body['indicators'], [])
                for other in {'tasks', 'reporting_records', 'notifications', 'activity_feed'} - {field}:
                    if other == 'activity_feed' and capability == 'VIEW_WORKPLAN':
                        self.assertEqual(body[other], [item for item in reference[other]
                                                     if item['action'].startswith('workflow.')])
                    else:
                        self.assertEqual(body[other], [])

    def test_empty_grants_role_and_tenant_cannot_bypass(self):
        for grants, role in (([], 'organization_admin'), (['VIEW_REPORTS'], 'organization_admin')):
            headers = self.grants(grants, role)
            self.assertEqual(self.client.get(SNAPSHOT, headers=headers).status_code, 403)
            self.assertEqual(self.client.get(DASHBOARD, headers=headers).status_code, 403)
        self.assertEqual(self.client.get(SNAPSHOT).status_code, 401)
        foreign = {'X-Auth-Token': 'token-method.b.organization_admin'}
        self.assertEqual(self.client.get(SNAPSHOT, headers=foreign).status_code, 404)
        self.assertEqual(self.client.get(DASHBOARD, headers=foreign).status_code, 404)
        self.assertEqual(self.client.get(SNAPSHOT.replace('proj_health', 'missing'), headers=self.admin).status_code, 404)

    def test_every_template_keeps_restricted_details_out_of_widgets(self):
        reference = self.snapshot()
        headers = self.grants(['VIEW_EXECUTIVE_SNAPSHOT'])
        for template in reference['dashboard']['available_templates']:
            with self.subTest(template=template['id']):
                body = self.snapshot(headers, template_id=template['id'])
                self.assertEqual(body['dashboard']['selected_template'], {})
                self.assertEqual(body['dashboard']['available_templates'], [])
                self.assertEqual([w['chart_type'] for w in body['dashboard']['widgets']], ['kpi_cards'])
                self.assertNotIn('AUDIT_DETAIL_SENTINEL', json.dumps(body))

    def test_operational_feed_retains_task_events_but_not_arbitrary_audit(self):
        data = self.module.load_data_from_path()
        actions = ['demo.task.' + suffix for suffix in ('created', 'started', 'completed', 'updated',
                   'submitted', 'validated', 'approved', 'returned', 'escalated', 'routing_updated')]
        for index, action in enumerate(actions):
            data.audit_events.append(self.module.AuditEvent(
                id='sec01_task_event_' + str(index), organization_id='org_blue_delta', actor_username='SYNTHETIC_TASK_ACTOR',
                action=action, target_id='synthetic-task', occurred_at='2026-10-28T12:00:00Z',
                details={'project_id': 'proj_health', 'task_name': 'SYNTHETIC_TASK_EVENT'}))
        data.audit_events.append(self.module.AuditEvent(
            id='unknown_event', organization_id='org_blue_delta', actor_username='UNKNOWN_EVENT_SENTINEL',
            action='demo.task.future_unclassified', target_id='proj_health', occurred_at='2026-10-28T12:00:00Z'))
        self.module.save_data_to_path(data)
        headers = self.grants(['VIEW_EXECUTIVE_SNAPSHOT', 'VIEW_WORKPLAN'])
        body = self.snapshot(headers)
        self.assertIn('SYNTHETIC_TASK_EVENT', json.dumps(body['activity_feed']))
        self.assertNotIn('AUDIT_DETAIL_SENTINEL', json.dumps(body))
        self.assertNotIn('UNKNOWN_EVENT_SENTINEL', json.dumps(body))
        self.assertTrue(set(actions) <= {event['action'] for event in body['activity_feed']})
        workplan = self.client.get('/v1/demo/projects/proj_health/workplan', headers=headers)
        self.assertEqual(workplan.status_code, 200, workplan.text)
        self.assertIn('SYNTHETIC_TASK_EVENT', json.dumps(workplan.json()['activity_feed']))

    def test_projection_is_non_mutating_and_unknown_widgets_fail_closed(self):
        from services.analytical_authorization import project_snapshot_for_permissions
        original = self.snapshot()
        original['dashboard']['widgets'].append({'chart_type': 'future_unclassified',
                                                'content': {'secret': 'UNCLASSIFIED_WIDGET_SENTINEL'}})
        before = deepcopy(original)
        result = project_snapshot_for_permissions(original, ['VIEW_EXECUTIVE_SNAPSHOT', 'VIEW_REPORTS'])
        self.assertEqual(original, before)
        self.assertNotIn('UNCLASSIFIED_WIDGET_SENTINEL', json.dumps(result))
        self.assertEqual(result['trend'], before['trend'])
        self.assertEqual(result['indicators'], [])

    def test_report_preview_does_not_turn_redaction_into_zero(self):
        headers = self.grants(['VIEW_EXECUTIVE_SNAPSHOT', 'VIEW_REPORTS'])
        report = self.client.get('/v1/demo/report_preview', headers=headers,
                                 params={'project_id': 'proj_health', 'audience': 'management'})
        self.assertEqual(report.status_code, 200, report.text)
        self.assertNotIn('0 tracked indicator rows', report.text)
        self.assertIn('restricted indicator detail', report.text)
        self.assertNotIn('0 current alerts', report.text)
