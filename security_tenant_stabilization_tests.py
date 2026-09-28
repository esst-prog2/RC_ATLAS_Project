import inspect
import os
import tempfile
import unittest
from copy import deepcopy
from datetime import date
from pathlib import Path
from unittest.mock import Mock

from fastapi.testclient import TestClient

from logical_framework_api_tests import MODULE
from services.demo_seed import build_demo_seed_bundle


class SecurityTenantStabilizationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_path = str(Path(self.temp_dir.name) / 'security.json')
        self.previous_env = {
            name: os.environ.get(name)
            for name in (
                'LOGITRACK_STORAGE_BACKEND',
                'LOGITRACK_DATA_PATH',
                'LOGITRACK_SQLITE_PATH',
                'LOGITRACK_ENABLE_RELATIONAL_MIRROR',
                'LOGITRACK_ENABLE_REPOSITORY_DOMAINS',
                'LOGITRACK_API_KEY',
            )
        }
        os.environ['LOGITRACK_STORAGE_BACKEND'] = 'json'
        os.environ['LOGITRACK_DATA_PATH'] = self.data_path
        os.environ.pop('LOGITRACK_SQLITE_PATH', None)
        os.environ['LOGITRACK_ENABLE_RELATIONAL_MIRROR'] = 'false'
        os.environ['LOGITRACK_ENABLE_REPOSITORY_DOMAINS'] = 'false'
        os.environ['LOGITRACK_API_KEY'] = 'technical-key'

        data = MODULE.from_serializable(build_demo_seed_bundle(MODULE.build_password_hash).payload)
        data.organizations.append(MODULE.OrganizationAccount(id='org_other', organization_name='Other Org'))
        data.projects.append(MODULE.Project(
            id='proj_other',
            name='Other Project',
            objective='Foreign tenant fixture',
            organization_id='org_other',
            project_code='OTHER-001',
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            status='active',
            indicators=[MODULE.Indicator(
                id='ind_other',
                name='Other indicator',
                unit='people',
                frequency='monthly',
                direction='up',
                level='outcome',
                target=100,
                baseline=0,
                organization_id='org_other',
                project_id='proj_other',
            )],
        ))
        data.users.extend([
            MODULE.UserAccount(
                id='user_other_manager', username='other.manager', organization_id='org_other',
                full_name='Other Manager', email='other.manager@example.test', role='programme_manager',
                status='active', is_active=True,
            ),
            MODULE.UserAccount(
                id='user_collision', username='local.collision', organization_id='org_blue_delta',
                full_name='Local Collision', email='local.collision@example.test', role='field_coordinator',
                status='active', is_active=True,
            ),
            MODULE.UserAccount(
                id='user_collision', username='foreign.collision', organization_id='org_other',
                full_name='Foreign Collision', email='foreign.collision@example.test', role='field_coordinator',
                status='active', is_active=True,
            ),
        ])
        data.teams.extend([
            MODULE.TeamAccount(id='team_collision', organization_id='org_blue_delta', team_name='Local Team'),
            MODULE.TeamAccount(id='team_collision', organization_id='org_other', team_name='Foreign Team'),
        ])
        data.tidy_datasets.extend([
            MODULE.TidyDataset(id='ds_local_security', name='Local Dataset', organization_id='org_blue_delta', rows=[{'value': 1}]),
            MODULE.TidyDataset(id='ds_foreign_security', name='Foreign Dataset', organization_id='org_other', rows=[{'value': 2}]),
        ])
        data.dashboard_templates.extend([
            MODULE.DashboardTemplate(id='tpl_local', name='Local', organization_id='org_blue_delta', scope='custom'),
            MODULE.DashboardTemplate(id='tpl_foreign', name='Foreign', organization_id='org_other', scope='custom'),
            MODULE.DashboardTemplate(id='tpl_ambiguous', name='Ambiguous', organization_id='', scope='custom'),
        ])
        data.notification_rules.extend([
            MODULE.NotificationRule(id='rule_collision', name='Local Rule', organization_id='org_blue_delta', channel='webhook'),
            MODULE.NotificationRule(id='rule_collision', name='Foreign Rule', organization_id='org_other', channel='webhook'),
        ])
        data.audit_events.extend([
            MODULE.AuditEvent(
                id='audit_local_collision', occurred_at=MODULE.now_iso_utc(), organization_id='org_blue_delta',
                actor_id='user_collision', actor_username='local.collision', action='security.local',
            ),
            MODULE.AuditEvent(
                id='audit_foreign_collision', occurred_at=MODULE.now_iso_utc(), organization_id='org_other',
                actor_id='user_collision', actor_username='foreign.collision', action='security.foreign',
            ),
            MODULE.AuditEvent(id='audit_ambiguous', occurred_at=MODULE.now_iso_utc(), action='security.ambiguous'),
        ])
        self.tokens = {}
        for user in data.users:
            token = f'security-token-{user.username}'
            user.api_token_hash = MODULE.hash_with_sha256(token)
            self.tokens[user.username] = token
        MODULE.save_data_to_path(data)
        self.client = TestClient(MODULE.app)

    def tearDown(self):
        self.client.close()
        for name, value in self.previous_env.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        self.temp_dir.cleanup()

    def headers(self, username='teresa.mbanze', include_key=False):
        result = {'X-Auth-Token': self.tokens[username]}
        if include_key:
            result['X-API-Key'] = 'technical-key'
        return result

    def load(self):
        return MODULE.load_data_from_path(self.data_path)

    def serialized(self):
        return MODULE.to_serializable(self.load())

    def test_real_actor_is_required_and_token_wins_over_api_key(self):
        self.assertEqual(self.client.get('/v1/projects').status_code, 401)
        self.assertEqual(self.client.get('/v1/projects', headers={'X-API-Key': 'technical-key'}).status_code, 401)
        response = self.client.get('/v1/projects', headers=self.headers(include_key=True))
        self.assertEqual(response.status_code, 200, response.text)
        self.assertNotIn('proj_other', {item['project_id'] for item in response.json()})
        invalid = self.client.get('/v1/projects', headers={'X-Auth-Token': 'invalid', 'X-API-Key': 'technical-key'})
        self.assertEqual(invalid.status_code, 401)
        self.assertEqual(self.client.get('/v1/admin/users', headers=self.headers('aline.duarte')).status_code, 403)

    def test_tenant_read_route_families_reject_anonymous_requests(self):
        paths = (
            '/v1/projects',
            '/v1/indicators',
            '/v1/indicator_locations',
            '/v1/activities',
            '/v1/tasks',
            '/v1/activity_indicator_links',
            '/v1/kpi/project',
            '/v1/kpi/indicator',
            '/v1/kpi/district',
            '/v1/kpi/workplan',
            '/v1/projects/proj_resilience/dashboard',
            '/v1/dashboard/summary',
            '/v1/reporting_records',
            '/v1/trends/portfolio',
            '/v1/narratives/portfolio',
            '/v1/projects/proj_resilience/trends',
            '/v1/projects/proj_resilience/narrative',
            '/v1/projects/proj_resilience/indicators/ind_res_households/trends',
            '/v1/tidy_datasets',
            '/v1/tidy_datasets/ds_demo_portfolio',
            '/v1/tidy_datasets/ds_demo_portfolio/semantic_mapping',
            '/v1/tidy_datasets/ds_demo_portfolio/quality',
            '/v1/tidy_datasets/ds_demo_portfolio/narrative',
            '/v1/tidy_datasets/ds_demo_portfolio/dashboard_blueprint',
            '/v1/tidy_datasets/ds_demo_portfolio/history_mapping',
            '/v1/tidy_datasets/ds_demo_portfolio/dashboard_suggestions',
            '/v1/notification_channels',
            '/v1/notifications',
            '/v1/notification_rules',
            '/v1/dashboard_templates?dataset_id=ds_demo_portfolio',
            '/v1/admin/organization',
            '/v1/admin/users',
            '/v1/admin/teams',
            '/v1/admin/projects',
            '/v1/admin/permissions',
            '/v1/admin/audit',
            '/v1/users',
            '/v1/audit_events',
            '/v1/demo/workspace',
            '/v1/demo/projects/proj_resilience/executive_snapshot',
            '/v1/demo/projects/proj_resilience/risks',
            '/v1/demo/projects/proj_resilience/workplan',
            '/v1/demo/data_quality',
            '/v1/demo/narrative_summary',
            '/v1/demo/report_preview',
            '/v1/projects/proj_resilience/logical-framework',
        )
        for path in paths:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 401)

    def test_all_data_bearing_v1_routes_accept_the_auth_token_header(self):
        anonymous_exemptions = {
            '/v1/auth/login',
            '/v1/auth/bootstrap',
            '/v1/data/template',
        }
        missing = []
        for route in MODULE.app.routes:
            path = getattr(route, 'path', '')
            if not path.startswith('/v1') or path in anonymous_exemptions:
                continue
            if 'x_auth_token' not in inspect.signature(route.endpoint).parameters:
                missing.append(path)
        self.assertEqual(missing, [])

    def test_collection_detail_and_write_isolation_are_side_effect_free(self):
        before = self.serialized()
        self.assertEqual(self.client.get('/v1/projects/proj_other/dashboard', headers=self.headers()).status_code, 404)
        denied = self.client.post(
            '/v1/projects/proj_other/indicators',
            headers=self.headers('raimundo.cumba'),
            json={'id': 'hostile', 'name': 'Hostile', 'unit': '#', 'frequency': 'monthly', 'direction': 'up'},
        )
        self.assertEqual(denied.status_code, 404, denied.text)
        self.assertEqual(self.serialized(), before)

    def test_task_id_collision_updates_only_the_actor_tenant(self):
        data = self.load()
        local_ops = data.ops_by_project['proj_resilience']
        local_task = next(
            task
            for activity in local_ops.activities
            for task in activity.tasks
            if task.assignee_username == 'aline.duarte'
        )
        local_task.status = 'in_progress'
        local_task.progress_pct = 10
        foreign_ops = deepcopy(local_ops)
        foreign_task = next(
            task
            for activity in foreign_ops.activities
            for task in activity.tasks
            if task.id == local_task.id
        )
        foreign_task.progress_pct = 77
        data.ops_by_project['proj_other'] = foreign_ops
        MODULE.save_data_to_path(data)

        response = self.client.post(
            f'/v1/demo/tasks/{local_task.id}/update',
            headers=self.headers('aline.duarte'),
            json={'progress_pct': 33},
        )
        self.assertEqual(response.status_code, 200, response.text)
        reloaded = self.load()
        local_after = next(
            task
            for activity in reloaded.ops_by_project['proj_resilience'].activities
            for task in activity.tasks
            if task.id == local_task.id
        )
        foreign_after = next(
            task
            for activity in reloaded.ops_by_project['proj_other'].activities
            for task in activity.tasks
            if task.id == local_task.id
        )
        self.assertEqual(local_after.progress_pct, 33)
        self.assertEqual(foreign_after.progress_pct, 77)

    def test_admin_id_collisions_update_only_the_actor_tenant(self):
        response = self.client.patch(
            '/v1/admin/users/user_collision',
            headers=self.headers('org.admin'),
            json={'full_name': 'Local Updated'},
        )
        self.assertEqual(response.status_code, 200, response.text)
        users = [item for item in self.load().users if item.id == 'user_collision']
        self.assertEqual(next(item for item in users if item.organization_id == 'org_blue_delta').full_name, 'Local Updated')
        self.assertEqual(next(item for item in users if item.organization_id == 'org_other').full_name, 'Foreign Collision')

        team = self.client.patch(
            '/v1/admin/teams/team_collision',
            headers=self.headers('org.admin'),
            json={'team_name': 'Local Team Updated'},
        )
        self.assertEqual(team.status_code, 200, team.text)
        teams = [item for item in self.load().teams if item.id == 'team_collision']
        self.assertEqual(next(item for item in teams if item.organization_id == 'org_other').team_name, 'Foreign Team')

    def test_global_login_identity_uniqueness_remains_global(self):
        response = self.client.post(
            '/v1/admin/users',
            headers=self.headers('org.admin'),
            json={
                'id': 'new-local-user', 'username': 'other.manager', 'email': 'unique@example.test',
                'full_name': 'Duplicate Login', 'role': 'field_coordinator', 'password': 'CoursePass!123',
            },
        )
        self.assertEqual(response.status_code, 409)
        self.assertNotIn('other.manager@example.test', response.text)

    def test_bootstrap_global_operations_and_health_contract(self):
        before = self.serialized()
        denied_bootstrap = self.client.post('/v1/auth/bootstrap', json={
            'organization_name': 'Claimed', 'full_name': 'Claimed Admin',
            'email': 'claimed@example.test', 'password': 'CoursePass!123',
        })
        self.assertEqual(denied_bootstrap.status_code, 409)
        self.assertEqual(self.serialized(), before)
        self.assertEqual(self.client.post('/v1/system/relational_sync').status_code, 401)
        self.assertEqual(self.client.post('/v1/system/relational_sync', headers={'X-API-Key': 'technical-key'}).status_code, 401)
        self.assertEqual(self.client.post('/v1/system/relational_sync', headers=self.headers('org.admin')).status_code, 403)
        for path in ('/v1/system/runtime', '/v1/system/relational_store', '/v1/system/repositories'):
            self.assertEqual(self.client.get(path).status_code, 401)
            self.assertEqual(self.client.get(path, headers={'X-API-Key': 'technical-key'}).status_code, 401)
            self.assertEqual(self.client.get(path, headers=self.headers('org.admin')).status_code, 403)
        self.assertEqual(
            self.client.post('/v1/data/import', headers={'X-API-Key': 'technical-key'}, json={}).status_code,
            401,
        )
        self.assertEqual(self.client.post('/v1/data/import', headers=self.headers('org.admin'), json={}).status_code, 403)
        self.assertEqual(
            self.client.post('/v1/demo/seed', headers={'X-API-Key': 'technical-key'}).status_code,
            401,
        )
        self.assertEqual(self.client.post('/v1/demo/seed', headers=self.headers('org.admin')).status_code, 403)
        self.assertEqual(self.serialized(), before)
        self.assertEqual(set(self.client.get('/health').json()), {'ok', 'system', 'version'})

    def test_bootstrap_rejects_tenant_data_even_when_users_are_empty(self):
        data = self.load()
        data.users = []
        MODULE.save_data_to_path(data)
        before = self.serialized()
        response = self.client.post('/v1/auth/bootstrap', json={
            'organization_name': 'Claim Attempt',
            'full_name': 'Claimed Admin',
            'email': 'claim.attempt@example.test',
            'password': 'CoursePass!123',
        })
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(self.serialized(), before)

    def test_bootstrap_succeeds_only_for_a_pristine_workspace(self):
        MODULE.save_data_to_path(MODULE.LogiTrackData())
        response = self.client.post('/v1/auth/bootstrap', json={
            'organization_name': 'First Organization', 'organization_id': 'org_first',
            'full_name': 'First Admin', 'email': 'first.admin@example.test',
            'username': 'first.admin', 'password': 'CoursePass!123',
        })
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(len(self.load().users), 1)

    def test_dataset_and_template_reads_are_tenant_scoped(self):
        response = self.client.get('/v1/tidy_datasets', headers=self.headers())
        self.assertEqual(response.status_code, 200, response.text)
        ids = {item['dataset_id'] for item in response.json()}
        self.assertIn('ds_local_security', ids)
        self.assertNotIn('ds_foreign_security', ids)
        self.assertEqual(self.client.get('/v1/tidy_datasets/ds_foreign_security', headers=self.headers()).status_code, 404)
        templates = self.client.get('/v1/dashboard_templates?dataset_id=ds_local_security', headers=self.headers())
        self.assertEqual(templates.status_code, 200, templates.text)
        custom_ids = {item['id'] for item in templates.json()['custom']}
        self.assertIn('tpl_local', custom_ids)
        self.assertNotIn('tpl_foreign', custom_ids)
        self.assertNotIn('tpl_ambiguous', custom_ids)
        self.assertTrue(templates.json()['builtin'])

    def test_dashboard_summary_is_built_from_the_actor_tenant(self):
        response = self.client.get('/v1/dashboard/summary', headers=self.headers())
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload['counts']['projects'], 3)
        self.assertNotIn('proj_other', {item['project_id'] for item in payload['projects']})

    def test_dataset_id_collision_preserves_explicit_local_linked_reads(self):
        data = self.load()
        shared_dataset_id = 'ds_shared_tenant_collision'
        data.tidy_datasets.extend([
            MODULE.TidyDataset(id=shared_dataset_id, name='Local Shared Dataset', organization_id='org_blue_delta'),
            MODULE.TidyDataset(id=shared_dataset_id, name='Foreign Shared Dataset', organization_id='org_other'),
        ])
        data.reporting_records.extend([
            MODULE.ReportingPeriodRecord(
                id='report_local_shared', reporting_period='2026-03-01', project_name='Shared Project',
                indicator_name='Shared Indicator', organization_id='org_blue_delta',
                source_dataset_id=shared_dataset_id, actual_value=10,
            ),
            MODULE.ReportingPeriodRecord(
                id='report_foreign_shared', reporting_period='2026-03-01', project_name='Shared Project',
                indicator_name='Shared Indicator', organization_id='org_other',
                source_dataset_id=shared_dataset_id, actual_value=90,
            ),
        ])
        data.semantic_mappings.extend([
            MODULE.SemanticMapping(
                id='mapping_local_shared', dataset_id=shared_dataset_id,
                organization_id='org_blue_delta', fields={'reporting_period': 'local_period'},
            ),
            MODULE.SemanticMapping(
                id='mapping_foreign_shared', dataset_id=shared_dataset_id,
                organization_id='org_other', fields={'reporting_period': 'foreign_period'},
            ),
        ])
        data.notification_rules.extend([
            MODULE.NotificationRule(
                id='rule_local_shared', name='Local Shared Rule', organization_id='org_blue_delta',
                dataset_id=shared_dataset_id,
            ),
            MODULE.NotificationRule(
                id='rule_foreign_shared', name='Foreign Shared Rule', organization_id='org_other',
                dataset_id=shared_dataset_id,
            ),
        ])
        other_manager = next(item for item in data.users if item.username == 'other.manager')
        other_manager.permissions = ['VIEW_REPORTS', 'MANAGE_NOTIFICATIONS']
        MODULE.save_data_to_path(data)

        local_reports = self.client.get('/v1/reporting_records', headers=self.headers('raimundo.cumba'))
        foreign_reports = self.client.get('/v1/reporting_records', headers=self.headers('other.manager'))
        self.assertEqual(local_reports.status_code, 200, local_reports.text)
        self.assertEqual(foreign_reports.status_code, 200, foreign_reports.text)
        local_report_ids = {item['record_id'] for item in local_reports.json()}
        foreign_report_ids = {item['record_id'] for item in foreign_reports.json()}
        self.assertIn('report_local_shared', local_report_ids)
        self.assertNotIn('report_foreign_shared', local_report_ids)
        self.assertIn('report_foreign_shared', foreign_report_ids)
        self.assertNotIn('report_local_shared', foreign_report_ids)

        local_mapping = self.client.get(
            f'/v1/tidy_datasets/{shared_dataset_id}/semantic_mapping',
            headers=self.headers('raimundo.cumba'),
        )
        foreign_mapping = self.client.get(
            f'/v1/tidy_datasets/{shared_dataset_id}/semantic_mapping',
            headers=self.headers('other.manager'),
        )
        self.assertEqual(local_mapping.status_code, 200, local_mapping.text)
        self.assertEqual(foreign_mapping.status_code, 200, foreign_mapping.text)
        self.assertEqual(local_mapping.json()['id'], 'mapping_local_shared')
        self.assertEqual(foreign_mapping.json()['id'], 'mapping_foreign_shared')

        local_rules = self.client.get('/v1/notification_rules', headers=self.headers('org.admin'))
        foreign_rules = self.client.get('/v1/notification_rules', headers=self.headers('other.manager'))
        self.assertEqual(local_rules.status_code, 200, local_rules.text)
        self.assertEqual(foreign_rules.status_code, 200, foreign_rules.text)
        self.assertIn('rule_local_shared', {item['id'] for item in local_rules.json()})
        self.assertNotIn('rule_foreign_shared', {item['id'] for item in local_rules.json()})
        self.assertIn('rule_foreign_shared', {item['id'] for item in foreign_rules.json()})
        self.assertNotIn('rule_local_shared', {item['id'] for item in foreign_rules.json()})

    def test_dataset_id_collision_reporting_upsert_updates_only_local_record(self):
        data = self.load()
        shared_dataset_id = 'ds_reporting_collision'
        data.tidy_datasets.extend([
            MODULE.TidyDataset(id=shared_dataset_id, name='Local Reporting Dataset', organization_id='org_blue_delta'),
            MODULE.TidyDataset(id=shared_dataset_id, name='Foreign Reporting Dataset', organization_id='org_other'),
        ])
        data.reporting_records.extend([
            MODULE.ReportingPeriodRecord(
                id='report_local_collision', reporting_period='2026-04-01',
                project_name='Collision Project', indicator_name='Collision Metric',
                organization_id='org_blue_delta', source_dataset_id=shared_dataset_id,
                country='Shared Country', actual_value=10, target_value=100,
            ),
            MODULE.ReportingPeriodRecord(
                id='report_foreign_collision', reporting_period='2026-04-01',
                project_name='Collision Project', indicator_name='Collision Metric',
                organization_id='org_other', source_dataset_id=shared_dataset_id,
                country='Shared Country', actual_value=90, target_value=100,
            ),
        ])
        foreign_before = MODULE.to_serializable(data.reporting_records[-1])
        MODULE.save_data_to_path(data)

        response = self.client.post(
            '/v1/reporting_records/import',
            headers=self.headers('raimundo.cumba'),
            json={
                'source_dataset_id': shared_dataset_id,
                'records': [{
                    'reporting_period': '2026-04',
                    'project_name': 'Collision Project',
                    'indicator_name': 'Collision Metric',
                    'country': 'Shared Country',
                    'actual_value': 20,
                    'target_value': 100,
                }],
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['summary']['updated'], 1)
        records = [
            item for item in self.load().reporting_records
            if item.source_dataset_id == shared_dataset_id
            and item.reporting_period == '2026-04-01'
        ]
        self.assertEqual(len(records), 2)
        local_after = next(item for item in records if item.organization_id == 'org_blue_delta')
        foreign_after = next(item for item in records if item.organization_id == 'org_other')
        self.assertEqual(local_after.id, 'report_local_collision')
        self.assertEqual(local_after.actual_value, 20)
        self.assertEqual(MODULE.to_serializable(foreign_after), foreign_before)

    def test_reporting_natural_key_collision_updates_only_local_tenant(self):
        data = self.load()
        data.reporting_records.append(MODULE.ReportingPeriodRecord(
            id='foreign-reporting-collision',
            reporting_period='2026-01-01',
            project_name='Shared Legacy Project',
            organization_id='org_other',
            indicator_name='Shared Metric',
            country='Shared Country',
            actual_value=9,
            target_value=100,
        ))
        MODULE.save_data_to_path(data)

        response = self.client.post(
            '/v1/reporting_records/import',
            headers=self.headers('raimundo.cumba'),
            json={'records': [{
                'reporting_period': '2026-01',
                'project_name': 'Shared Legacy Project',
                'indicator_name': 'Shared Metric',
                'country': 'Shared Country',
                'actual_value': 20,
                'target_value': 100,
            }]},
        )
        self.assertEqual(response.status_code, 200, response.text)
        records = [
            item for item in self.load().reporting_records
            if item.reporting_period == '2026-01-01'
            and item.project_name == 'Shared Legacy Project'
            and item.indicator_name == 'Shared Metric'
        ]
        self.assertEqual(len(records), 2)
        self.assertEqual(next(item for item in records if item.organization_id == 'org_other').actual_value, 9)
        self.assertEqual(next(item for item in records if item.organization_id == 'org_blue_delta').actual_value, 20)

    def test_foreign_dataset_reporting_import_is_denied_without_side_effects(self):
        data = self.load()
        data.reporting_records.append(MODULE.ReportingPeriodRecord(
            id='foreign_dataset_report', reporting_period='2026-05-01',
            project_name='Foreign Dataset Project', indicator_name='Foreign Dataset Metric',
            organization_id='org_other', source_dataset_id='ds_foreign_security',
            actual_value=90, target_value=100,
        ))
        MODULE.save_data_to_path(data)
        before = self.serialized()

        response = self.client.post(
            '/v1/reporting_records/import',
            headers=self.headers('raimundo.cumba'),
            json={'records': [{
                'reporting_period': '2026-05',
                'project_name': 'Foreign Dataset Project',
                'indicator_name': 'Foreign Dataset Metric',
                'source_dataset_id': 'ds_foreign_security',
                'actual_value': 10,
                'target_value': 100,
            }]},
        )
        self.assertEqual(response.status_code, 404, response.text)
        self.assertEqual(self.serialized(), before)

    def test_reporting_name_resolution_stays_inside_actor_tenant(self):
        data = self.load()
        local_project = next(item for item in data.projects if item.id == 'proj_resilience')
        foreign_project = next(item for item in data.projects if item.id == 'proj_other')
        foreign_project.name = local_project.name
        foreign_project.indicators[0].name = local_project.indicators[0].name
        data.projects = [foreign_project] + [item for item in data.projects if item is not foreign_project]
        MODULE.save_data_to_path(data)

        response = self.client.post(
            '/v1/reporting_records/import',
            headers=self.headers('raimundo.cumba'),
            json={'records': [{
                'reporting_period': '2026-02',
                'project_name': local_project.name,
                'indicator_name': local_project.indicators[0].name,
                'actual_value': 30,
                'target_value': 100,
            }]},
        )
        self.assertEqual(response.status_code, 200, response.text)
        record = next(
            item for item in self.load().reporting_records
            if item.organization_id == 'org_blue_delta' and item.reporting_period == '2026-02-01'
        )
        self.assertEqual(record.project_id, local_project.id)
        self.assertEqual(record.indicator_id, local_project.indicators[0].id)

    def test_ambiguous_and_conflicting_reporting_ownership_fail_closed(self):
        data = self.load()
        shared_dataset_id = 'ds_ambiguous_reporting'
        foreign_dataset_id = 'ds_foreign_parent_reporting'
        data.tidy_datasets.extend([
            MODULE.TidyDataset(id=shared_dataset_id, name='Local Ambiguous Dataset', organization_id='org_blue_delta'),
            MODULE.TidyDataset(id=shared_dataset_id, name='Foreign Ambiguous Dataset', organization_id='org_other'),
            MODULE.TidyDataset(id=foreign_dataset_id, name='Foreign Parent Dataset', organization_id='org_other'),
        ])
        data.reporting_records.extend([
            MODULE.ReportingPeriodRecord(
                id='report_ambiguous_legacy', reporting_period='2026-06-01',
                project_name='Ambiguous Project', indicator_name='Ambiguous Metric',
                organization_id='', source_dataset_id=shared_dataset_id,
            ),
            MODULE.ReportingPeriodRecord(
                id='report_explicit_parent_conflict', reporting_period='2026-06-01',
                project_name='Conflict Project', indicator_name='Conflict Metric',
                organization_id='org_blue_delta', source_dataset_id=foreign_dataset_id,
            ),
        ])
        MODULE.save_data_to_path(data)

        local = self.client.get('/v1/reporting_records', headers=self.headers('raimundo.cumba'))
        foreign = self.client.get('/v1/reporting_records', headers=self.headers('other.manager'))
        self.assertEqual(local.status_code, 200, local.text)
        self.assertEqual(foreign.status_code, 200, foreign.text)
        hidden_ids = {'report_ambiguous_legacy', 'report_explicit_parent_conflict'}
        self.assertTrue(hidden_ids.isdisjoint({item['record_id'] for item in local.json()}))
        self.assertTrue(hidden_ids.isdisjoint({item['record_id'] for item in foreign.json()}))

    def test_ambiguous_and_conflicting_mapping_and_rule_ownership_fail_closed(self):
        data = self.load()
        shared_dataset_id = 'ds_ambiguous_linked'
        foreign_dataset_id = 'ds_foreign_parent_linked'
        data.tidy_datasets.extend([
            MODULE.TidyDataset(id=shared_dataset_id, name='Local Linked Dataset', organization_id='org_blue_delta'),
            MODULE.TidyDataset(id=shared_dataset_id, name='Foreign Linked Dataset', organization_id='org_other'),
            MODULE.TidyDataset(id=foreign_dataset_id, name='Foreign Only Linked Dataset', organization_id='org_other'),
        ])
        data.semantic_mappings.extend([
            MODULE.SemanticMapping(
                id='mapping_ambiguous_legacy', dataset_id=shared_dataset_id,
                organization_id='', fields={'reporting_period': 'ambiguous_period'},
            ),
            MODULE.SemanticMapping(
                id='mapping_explicit_parent_conflict', dataset_id=foreign_dataset_id,
                organization_id='org_blue_delta', fields={'reporting_period': 'conflict_period'},
            ),
        ])
        data.notification_rules.extend([
            MODULE.NotificationRule(
                id='rule_ambiguous_legacy', name='Ambiguous Legacy Rule',
                organization_id='', dataset_id=shared_dataset_id,
            ),
            MODULE.NotificationRule(
                id='rule_explicit_parent_conflict', name='Conflicting Parent Rule',
                organization_id='org_blue_delta', dataset_id=foreign_dataset_id,
            ),
        ])
        other_manager = next(item for item in data.users if item.username == 'other.manager')
        other_manager.permissions = ['VIEW_REPORTS', 'MANAGE_NOTIFICATIONS']
        MODULE.save_data_to_path(data)

        local_mapping = self.client.get(
            f'/v1/tidy_datasets/{shared_dataset_id}/semantic_mapping',
            headers=self.headers('raimundo.cumba'),
        )
        foreign_mapping = self.client.get(
            f'/v1/tidy_datasets/{shared_dataset_id}/semantic_mapping',
            headers=self.headers('other.manager'),
        )
        conflicting_mapping = self.client.get(
            f'/v1/tidy_datasets/{foreign_dataset_id}/semantic_mapping',
            headers=self.headers('other.manager'),
        )
        self.assertEqual(local_mapping.status_code, 200, local_mapping.text)
        self.assertEqual(foreign_mapping.status_code, 200, foreign_mapping.text)
        self.assertEqual(conflicting_mapping.status_code, 200, conflicting_mapping.text)
        hidden_mapping_ids = {'mapping_ambiguous_legacy', 'mapping_explicit_parent_conflict'}
        self.assertNotIn(local_mapping.json()['id'], hidden_mapping_ids)
        self.assertNotIn(foreign_mapping.json()['id'], hidden_mapping_ids)
        self.assertNotIn(conflicting_mapping.json()['id'], hidden_mapping_ids)
        self.assertEqual(
            self.client.get(
                f'/v1/tidy_datasets/{foreign_dataset_id}/semantic_mapping',
                headers=self.headers('raimundo.cumba'),
            ).status_code,
            404,
        )

        local_rules = self.client.get('/v1/notification_rules', headers=self.headers('org.admin'))
        foreign_rules = self.client.get('/v1/notification_rules', headers=self.headers('other.manager'))
        self.assertEqual(local_rules.status_code, 200, local_rules.text)
        self.assertEqual(foreign_rules.status_code, 200, foreign_rules.text)
        hidden_rule_ids = {'rule_ambiguous_legacy', 'rule_explicit_parent_conflict'}
        self.assertTrue(hidden_rule_ids.isdisjoint({item['id'] for item in local_rules.json()}))
        self.assertTrue(hidden_rule_ids.isdisjoint({item['id'] for item in foreign_rules.json()}))

    def test_semantic_mapping_collision_updates_only_local_tenant(self):
        data = self.load()
        data.tidy_datasets.extend([
            MODULE.TidyDataset(id='ds_mapping_collision', name='Local Collision Dataset', organization_id='org_blue_delta'),
            MODULE.TidyDataset(id='ds_mapping_collision', name='Foreign Collision Dataset', organization_id='org_other'),
        ])
        data.semantic_mappings.extend([
            MODULE.SemanticMapping(
                id='map_collision', dataset_id='ds_mapping_collision',
                organization_id='org_blue_delta', fields={'reporting_period': 'local_period'},
            ),
            MODULE.SemanticMapping(
                id='map_collision', dataset_id='ds_mapping_collision',
                organization_id='org_other', fields={'reporting_period': 'foreign_period'},
            ),
        ])
        MODULE.save_data_to_path(data)

        response = self.client.post(
            '/v1/tidy_datasets/ds_mapping_collision/semantic_mapping',
            headers=self.headers('raimundo.cumba'),
            json={'id': 'map_collision', 'fields': {'reporting_period': 'updated_local_period'}},
        )
        self.assertEqual(response.status_code, 200, response.text)
        mappings = [item for item in self.load().semantic_mappings if item.id == 'map_collision']
        self.assertEqual(
            next(item for item in mappings if item.organization_id == 'org_blue_delta').fields['reporting_period'],
            'updated_local_period',
        )
        self.assertEqual(
            next(item for item in mappings if item.organization_id == 'org_other').fields['reporting_period'],
            'foreign_period',
        )

    def test_notification_rule_collision_updates_only_local_tenant(self):
        response = self.client.post(
            '/v1/notification_rules',
            headers=self.headers('org.admin'),
            json={'id': 'rule_collision', 'name': 'Local Rule Updated', 'channel': 'webhook'},
        )
        self.assertEqual(response.status_code, 200, response.text)
        rules = [item for item in self.load().notification_rules if item.id == 'rule_collision']
        self.assertEqual(
            next(item for item in rules if item.organization_id == 'org_blue_delta').name,
            'Local Rule Updated',
        )
        self.assertEqual(
            next(item for item in rules if item.organization_id == 'org_other').name,
            'Foreign Rule',
        )

    def test_authorized_notification_rule_evaluates_only_tenant_data(self):
        endpoint = next(
            route.endpoint for route in MODULE.app.routes
            if getattr(route, 'path', '') == '/v1/notification_rules/{rule_id}/run'
        )
        service = inspect.getclosurevars(endpoint).nonlocals['service']
        original = service.deps.evaluate_notification_rule
        evaluator = Mock(return_value=[])
        object.__setattr__(service.deps, 'evaluate_notification_rule', evaluator)
        try:
            response = self.client.post(
                '/v1/notification_rules/rule_collision/run',
                headers=self.headers('org.admin'),
                json={},
            )
            self.assertEqual(response.status_code, 200, response.text)
            evaluated_data = evaluator.call_args.args[0]
            self.assertTrue(evaluated_data.projects)
            self.assertEqual(
                {item.organization_id for item in evaluated_data.projects},
                {'org_blue_delta'},
            )
        finally:
            object.__setattr__(service.deps, 'evaluate_notification_rule', original)

    def test_demo_notification_default_project_is_tenant_scoped(self):
        data = self.load()
        foreign = next(item for item in data.projects if item.organization_id == 'org_other')
        data.projects = [foreign] + [item for item in data.projects if item is not foreign]
        MODULE.save_data_to_path(data)
        response = self.client.post(
            '/v1/demo/notifications/simulate',
            headers=self.headers('org.admin'),
            json={'scenario': 'overdue_alerts'},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertNotEqual(response.json()['project_id'], 'proj_other')

    def test_notification_denials_occur_before_external_dispatch(self):
        endpoint = next(
            route.endpoint for route in MODULE.app.routes
            if getattr(route, 'path', '') == '/v1/notifications/dispatch'
        )
        service = inspect.getclosurevars(endpoint).nonlocals['service']
        original = service.deps.dispatch_notifications_to_webhook
        dispatcher = Mock(return_value={'ok': True})
        object.__setattr__(service.deps, 'dispatch_notifications_to_webhook', dispatcher)
        try:
            before = self.serialized()
            denied = self.client.post(
                '/v1/notifications/dispatch',
                headers={'X-API-Key': 'technical-key'},
                json={'channel': 'webhook', 'webhook_url': 'https://example.invalid'},
            )
            self.assertEqual(denied.status_code, 401)
            dispatcher.assert_not_called()
            self.assertEqual(self.serialized(), before)

            data = self.load()
            data.notification_rules.append(MODULE.NotificationRule(
                id='foreign_only_rule',
                name='Foreign Only Rule',
                organization_id='org_other',
                channel='webhook',
            ))
            MODULE.save_data_to_path(data)
            foreign_before = self.serialized()
            foreign = self.client.post(
                '/v1/notification_rules/foreign_only_rule/run',
                headers=self.headers('org.admin'),
                json={'webhook_url': 'https://example.invalid'},
            )
            self.assertEqual(foreign.status_code, 404, foreign.text)
            dispatcher.assert_not_called()
            self.assertEqual(self.serialized(), foreign_before)
        finally:
            object.__setattr__(service.deps, 'dispatch_notifications_to_webhook', original)

    def test_audit_visibility_and_actor_enrichment_are_tenant_scoped(self):
        response = self.client.get('/v1/admin/audit', headers=self.headers('org.admin'))
        self.assertEqual(response.status_code, 200, response.text)
        items = response.json()['items']
        ids = {item['id'] for item in items}
        self.assertIn('audit_local_collision', ids)
        self.assertNotIn('audit_foreign_collision', ids)
        self.assertNotIn('audit_ambiguous', ids)
        item = next(value for value in items if value['id'] == 'audit_local_collision')
        self.assertEqual(item['actor_full_name'], 'Local Collision')

    def test_same_tenant_business_errors_remain_400_and_409(self):
        invalid = self.client.post('/v1/reporting_records/import', headers=self.headers('raimundo.cumba'), json={'records': 'not-a-list'})
        self.assertEqual(invalid.status_code, 400, invalid.text)
        task_id = next(
            task.id
            for project_id, ops in self.load().ops_by_project.items()
            if project_id == 'proj_resilience'
            for activity in ops.activities
            for task in activity.tasks
        )
        conflict = self.client.post(
            f'/v1/demo/tasks/{task_id}/validate',
            headers=self.headers('teresa.mbanze'),
            json={'decision': 'approved'},
        )
        self.assertEqual(conflict.status_code, 409, conflict.text)

    def test_suspended_actor_cannot_establish_tenant_context(self):
        data = self.load()
        user = next(item for item in data.users if item.username == 'teresa.mbanze')
        user.status = 'suspended'
        MODULE.save_data_to_path(data)
        self.assertEqual(self.client.get('/v1/projects', headers=self.headers()).status_code, 401)
        login = self.client.post('/v1/auth/login', json={
            'username': 'teresa.mbanze',
            'password': 'TeresaPM!2026',
        })
        self.assertEqual(login.status_code, 401, login.text)

    def test_actor_without_existing_organization_fails_closed(self):
        data = self.load()
        user = next(item for item in data.users if item.username == 'teresa.mbanze')
        user.organization_id = 'org_missing'
        MODULE.save_data_to_path(data)
        response = self.client.get('/v1/projects', headers=self.headers())
        self.assertEqual(response.status_code, 401, response.text)
        login = self.client.post('/v1/auth/login', json={
            'username': 'teresa.mbanze',
            'password': 'TeresaPM!2026',
        })
        self.assertEqual(login.status_code, 401, login.text)


if __name__ == '__main__':
    unittest.main()
