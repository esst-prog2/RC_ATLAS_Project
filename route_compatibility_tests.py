import tempfile
import unittest
from pathlib import Path

from api.dashboard_template_routes import register_dashboard_template_routes
from api.demo_routes import register_demo_routes
from api.notification_routes import register_notification_routes
from api.reporting_routes import register_reporting_routes


class FakeApp:
    def __init__(self):
        self.routes = []

    def get(self, path, **kwargs):
        return self._register("GET", path)

    def post(self, path, **kwargs):
        return self._register("POST", path)

    def _register(self, method, path):
        def decorator(func):
            self.routes.append((method, path, func.__name__))
            return func
        return decorator


class StubService:
    pass


class RouteCompatibilityTests(unittest.TestCase):
    def test_reporting_routes_register_expected_paths(self):
        app = FakeApp()
        register_reporting_routes(app, StubService(), header_factory=lambda **kwargs: None)

        expected = {
            ("GET", "/v1/reporting_records"),
            ("GET", "/v1/trends/portfolio"),
            ("GET", "/v1/narratives/portfolio"),
            ("GET", "/v1/projects/{project_id}/trends"),
            ("GET", "/v1/projects/{project_id}/narrative"),
            ("GET", "/v1/projects/{project_id}/indicators/{indicator_id}/trends"),
            ("GET", "/v1/tidy_datasets"),
            ("GET", "/v1/tidy_datasets/{dataset_id}"),
            ("GET", "/v1/tidy_datasets/{dataset_id}/semantic_mapping"),
            ("POST", "/v1/tidy_datasets/{dataset_id}/semantic_mapping"),
            ("GET", "/v1/tidy_datasets/{dataset_id}/quality"),
            ("GET", "/v1/tidy_datasets/{dataset_id}/narrative"),
            ("GET", "/v1/tidy_datasets/{dataset_id}/dashboard_blueprint"),
            ("GET", "/v1/tidy_datasets/{dataset_id}/history_mapping"),
            ("GET", "/v1/tidy_datasets/{dataset_id}/dashboard_suggestions"),
            ("POST", "/v1/tidy_datasets/import"),
            ("POST", "/v1/tidy_datasets/{dataset_id}/materialize_history"),
            ("POST", "/v1/reporting_records/import"),
        }
        actual = {(method, path) for method, path, _ in app.routes}
        self.assertEqual(actual, expected)

    def test_notification_routes_register_expected_paths(self):
        app = FakeApp()
        register_notification_routes(app, StubService(), header_factory=lambda **kwargs: None)

        expected = {
            ("GET", "/v1/notification_channels"),
            ("GET", "/v1/notifications"),
            ("GET", "/v1/notification_rules"),
            ("POST", "/v1/notification_rules"),
            ("POST", "/v1/notification_rules/{rule_id}/run"),
            ("POST", "/v1/notification_rules/run_due"),
            ("POST", "/v1/notifications/dispatch"),
        }
        actual = {(method, path) for method, path, _ in app.routes}
        self.assertEqual(actual, expected)

    def test_dashboard_template_routes_register_expected_paths(self):
        app = FakeApp()
        register_dashboard_template_routes(app, StubService(), header_factory=lambda **kwargs: None)

        expected = {
            ("GET", "/v1/dashboard_templates"),
            ("POST", "/v1/dashboard_templates"),
        }
        actual = {(method, path) for method, path, _ in app.routes}
        self.assertEqual(actual, expected)

    def test_demo_routes_register_expected_paths(self):
        app = FakeApp()
        register_demo_routes(app, StubService(), header_factory=lambda **kwargs: None)

        expected = {
            ("POST", "/v1/demo/seed"),
            ("GET", "/v1/demo/workspace"),
            ("GET", "/v1/demo/projects/{project_id}/executive_snapshot"),
            ("GET", "/v1/demo/projects/{project_id}/risks"),
            ("GET", "/v1/demo/projects/{project_id}/workplan"),
            ("GET", "/v1/demo/data_quality"),
            ("GET", "/v1/demo/narrative_summary"),
            ("POST", "/v1/demo/notifications/simulate"),
            ("GET", "/v1/demo/report_preview"),
            ("POST", "/v1/demo/tasks"),
            ("POST", "/v1/demo/tasks/{task_id}/update"),
            ("POST", "/v1/demo/tasks/{task_id}/validate"),
        }
        actual = {(method, path) for method, path, _ in app.routes}
        self.assertEqual(actual, expected)

    def test_health_payload_builder(self):
        from importlib.util import module_from_spec, spec_from_file_location

        module_path = Path(__file__).with_name("LogiTrackRC v4.4.py")
        spec = spec_from_file_location("logitrack_rc_health_test", module_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Unable to load module from {module_path}")
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory() as tmp_dir:
            data = module.LogiTrackData(
                tidy_datasets=[module.TidyDataset(id="ds_1", name="Dataset")],
                reporting_records=[module.ReportingPeriodRecord(id="rep_1", reporting_period="2026-05-01")],
                semantic_mappings=[module.SemanticMapping(id="map_1", dataset_id="ds_1")],
                dashboard_templates=[module.DashboardTemplate(id="tpl_1", name="Executive")],
                notification_rules=[module.NotificationRule(id="rule_1", name="Notify")],
                users=[module.UserAccount(id="user_1", username="admin")],
                audit_events=[module.AuditEvent(id="audit_1", occurred_at="2026-05-16T00:00:00Z")],
            )
            payload = module.build_health_payload(
                storage={"target_path": str(Path(tmp_dir) / "data.json"), "exists": True},
                runtime_status={
                    "scheduler": {"enabled": True, "thread_alive": False, "last_run_at": "", "last_error": ""},
                    "relational_store": {"enabled": True},
                    "repository_domains": {"enabled": True},
                },
                cors_origins=["http://localhost:3000"],
                allow_credentials=True,
                loaded_data=data,
                data_error=None,
            )

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["tidy_dataset_count"], 1)
        self.assertEqual(payload["dashboard_template_count"], 1)
        self.assertEqual(payload["notification_rule_count"], 1)

    def test_root_route_is_studio_first_in_source(self):
        source = Path(__file__).with_name("LogiTrackRC v4.4.py").read_text(encoding="utf-8")

        self.assertIn('@app.get("/", include_in_schema=False)', source)
        self.assertIn('return Response(status_code=307, headers={"Location": "/studio"})', source)

    def test_admin_routes_are_present_in_source(self):
        source = Path(__file__).with_name("LogiTrackRC v4.4.py").read_text(encoding="utf-8")

        expected_routes = [
            '@app.get("/v1/admin/organization")',
            '@app.patch("/v1/admin/organization")',
            '@app.get("/v1/admin/users")',
            '@app.post("/v1/admin/users")',
            '@app.patch("/v1/admin/users/{user_id}")',
            '@app.post("/v1/admin/users/{user_id}/suspend")',
            '@app.post("/v1/admin/users/{user_id}/reactivate")',
            '@app.post("/v1/admin/users/{user_id}/archive")',
            '@app.get("/v1/admin/teams")',
            '@app.post("/v1/admin/teams")',
            '@app.patch("/v1/admin/teams/{team_id}")',
            '@app.post("/v1/admin/teams/{team_id}/archive")',
            '@app.get("/v1/admin/projects")',
            '@app.post("/v1/admin/projects")',
            '@app.patch("/v1/admin/projects/{project_id}")',
            '@app.post("/v1/admin/projects/{project_id}/publish")',
            '@app.post("/v1/admin/projects/{project_id}/activate")',
            '@app.post("/v1/admin/projects/{project_id}/deactivate")',
            '@app.post("/v1/admin/projects/{project_id}/complete")',
            '@app.post("/v1/admin/projects/{project_id}/archive")',
            '@app.post("/v1/admin/projects/{project_id}/restore")',
            '@app.post("/v1/admin/projects/{project_id}/clone")',
            '@app.get("/v1/admin/permissions")',
            '@app.get("/v1/admin/audit")',
        ]
        for route in expected_routes:
            self.assertIn(route, source)


if __name__ == "__main__":
    unittest.main()
