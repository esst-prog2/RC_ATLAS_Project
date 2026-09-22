import os
import tempfile
import unittest
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from services.demo_seed import build_demo_seed_bundle
from services.errors import ServiceError

try:
    from fastapi.testclient import TestClient
except Exception:
    TestClient = None


MODULE_PATH = Path(__file__).with_name("LogiTrackRC v4.4.py")
SPEC = spec_from_file_location("logitrack_rc_v4_4_demo_tests", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load module from {MODULE_PATH}")
MODULE = module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


@contextmanager
def patched_env(**values):
    previous = {key: os.environ.get(key) for key in values}
    try:
        for key, value in values.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = str(value)
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def build_demo_service():
    def authorize_request(
        data,
        x_api_key,
        x_auth_token,
        required_role="analyst",
        required_permission=None,
        required_permissions=None,
        require_all_permissions=False,
    ):
        if (x_api_key or "").strip():
            return None

        token = (x_auth_token or "").strip()
        if token:
            user = MODULE.find_user_by_token(data, token)
            if user is None or not user.is_active:
                raise RuntimeError("Invalid or inactive X-Auth-Token.")
            requested_permissions = MODULE.normalize_permission_ids(required_permissions or [])
            if required_permission:
                normalized_permission = MODULE.normalize_permission_id(required_permission)
                if normalized_permission:
                    requested_permissions = MODULE.normalize_permission_ids([*requested_permissions, normalized_permission])
            if requested_permissions:
                allowed = (
                    MODULE.user_has_all_permissions(user, requested_permissions)
                    if require_all_permissions
                    else MODULE.user_has_any_permission(user, requested_permissions)
                )
                if not allowed:
                    raise RuntimeError("Current user does not have the required permissions.")
            elif not MODULE.role_allows(user.role, required_role):
                raise RuntimeError(f"Role '{user.role}' is not allowed to perform this action.")
            return user

        if data.users:
            raise RuntimeError("Provide a valid X-Auth-Token.")
        return None

    return MODULE.DemoWorkspaceService(
        MODULE.DemoWorkspaceServiceDependencies(
            load_data=MODULE.load_data_from_path,
            save_data=MODULE.save_data_to_path,
            authorize_request=authorize_request,
            append_audit_event=MODULE.append_audit_event,
            from_serializable=MODULE.from_serializable,
            find_user_by_username=MODULE.find_user_by_username,
            sanitize_user=MODULE.sanitize_user,
            build_password_hash=MODULE.build_password_hash,
            hash_with_sha256=MODULE.hash_with_sha256,
            new_api_token=MODULE.new_api_token,
            now_iso_utc=MODULE.now_iso_utc,
            build_dashboard_summary=MODULE.build_dashboard_summary,
            build_bi_payload=MODULE.build_bi_payload,
            build_portfolio_narrative_summary=MODULE.build_portfolio_narrative_summary,
            build_project_narrative_summary=MODULE.build_project_narrative_summary,
            build_current_notifications=MODULE.build_current_notifications,
            filter_notifications=MODULE.filter_notifications,
            build_tidy_dataset_quality_report=MODULE.build_tidy_dataset_quality_report,
            build_project_trend_series=MODULE.build_project_trend_series,
            find_project=MODULE.find_project,
            find_tidy_dataset=MODULE.find_tidy_dataset,
            find_dashboard_template=MODULE.find_dashboard_template,
            parse_date_like_value=MODULE.parse_date_like_value,
        )
    )


def build_in_memory_demo_service(data):
    return MODULE.DemoWorkspaceService(
        MODULE.DemoWorkspaceServiceDependencies(
            load_data=lambda: data,
            save_data=lambda _: "memory://demo",
            authorize_request=lambda *args, **kwargs: None,
            append_audit_event=lambda *args, **kwargs: None,
            from_serializable=MODULE.from_serializable,
            find_user_by_username=MODULE.find_user_by_username,
            sanitize_user=MODULE.sanitize_user,
            build_password_hash=MODULE.build_password_hash,
            hash_with_sha256=MODULE.hash_with_sha256,
            new_api_token=MODULE.new_api_token,
            now_iso_utc=MODULE.now_iso_utc,
            build_dashboard_summary=MODULE.build_dashboard_summary,
            build_bi_payload=MODULE.build_bi_payload,
            build_portfolio_narrative_summary=MODULE.build_portfolio_narrative_summary,
            build_project_narrative_summary=MODULE.build_project_narrative_summary,
            build_current_notifications=MODULE.build_current_notifications,
            filter_notifications=MODULE.filter_notifications,
            build_tidy_dataset_quality_report=MODULE.build_tidy_dataset_quality_report,
            build_project_trend_series=MODULE.build_project_trend_series,
            find_project=MODULE.find_project,
            find_tidy_dataset=MODULE.find_tidy_dataset,
            find_dashboard_template=MODULE.find_dashboard_template,
            parse_date_like_value=MODULE.parse_date_like_value,
        )
    )


def issue_token_for_user(data, username):
    user = MODULE.find_user_by_username(data, username)
    if user is None:
        raise AssertionError(f"User '{username}' is missing from the demo workspace.")
    token = MODULE.new_api_token()
    user.api_token_hash = MODULE.hash_with_sha256(token)
    user.last_login_at = MODULE.now_iso_utc()
    user.updated_at = MODULE.now_iso_utc()
    return user, token


class DemoSmokeTests(unittest.TestCase):
    def test_permission_templates_seed_real_workspace_access(self):
        bundle = build_demo_seed_bundle(MODULE.build_password_hash)
        data = MODULE.from_serializable(bundle.payload)
        service = build_in_memory_demo_service(data)

        self.assertIn("VIEW_PORTFOLIO", MODULE.role_permissions("programme_manager"))
        self.assertIn("VALIDATE_EVIDENCE", MODULE.role_permissions("meal_officer"))
        self.assertIn("UPDATE_TASK_PROGRESS", MODULE.role_permissions("field_coordinator"))
        self.assertNotIn("MANAGE_USERS", MODULE.role_permissions("executive_viewer"))

        overview = service.workspace_overview(None, None)
        self.assertTrue(overview["project_cards"])

    def test_normalize_datetime_utc_handles_mixed_inputs(self):
        samples = [
            "2026-05-01T00:00:00Z",
            "2026-05-01T00:00:00+00:00",
            "2026-05-01",
            datetime(2026, 5, 1, 0, 0, 0),
            datetime(2026, 5, 1, 0, 0, 0, tzinfo=timezone.utc),
            date(2026, 5, 1),
        ]

        normalized = [MODULE.normalize_datetime_utc(item) for item in samples]

        for item in normalized:
            self.assertIsNotNone(item)
            self.assertEqual(item.tzinfo, timezone.utc)
            self.assertEqual(item.year, 2026)
            self.assertEqual(item.month, 5)
            self.assertEqual(item.day, 1)

        self.assertIsNone(MODULE.normalize_datetime_utc(None))
        self.assertIsNone(MODULE.normalize_datetime_utc(""))
        self.assertIsNone(MODULE.normalize_datetime_utc("not-a-date"))

    def test_demo_startup_instructions_present(self):
        instructions_path = Path(__file__).with_name("demo_startup_instructions.md")
        content = instructions_path.read_text(encoding="utf-8")

        self.assertIn("uvicorn logitrack_rc_v4_4_api:app", content)
        self.assertIn("/studio", content)
        self.assertIn("Seed Demo Workspace", content)

    def test_demo_seed_bundle_hydrates_realistic_workspace(self):
        bundle = build_demo_seed_bundle(MODULE.build_password_hash)
        data = MODULE.from_serializable(bundle.payload)

        self.assertGreaterEqual(len(data.projects), 3)
        self.assertGreaterEqual(len(data.tidy_datasets), 2)
        self.assertGreaterEqual(len(data.reporting_records), 24)
        self.assertGreaterEqual(len(data.dashboard_templates), 3)
        self.assertGreaterEqual(len(data.notification_rules), 3)
        self.assertEqual(len(data.organizations), 1)
        self.assertGreaterEqual(len(data.teams), 4)
        self.assertGreaterEqual(len(data.users), 5)
        self.assertTrue(MODULE.find_user_by_username(data, "aline.duarte"))
        self.assertEqual(data.organizations[0].organization_name, "Blue Delta Consortium")
        self.assertEqual(data.organizations[0].country, "Mozambique")
        self.assertEqual(data.organizations[0].timezone, "Africa/Maputo")
        self.assertTrue(all(getattr(project, "organization_id", "") == "org_blue_delta" for project in data.projects))

        status_values = {
            str(row.get("status") or "").strip().lower()
            for dataset in data.tidy_datasets
            for row in dataset.rows
            if str(row.get("status") or "").strip()
        }
        risk_values = {
            str(row.get("risk_level") or "").strip().lower()
            for dataset in data.tidy_datasets
            for row in dataset.rows
            if str(row.get("risk_level") or "").strip()
        }
        overdue_tasks = [
            task
            for ops in data.ops_by_project.values()
            for activity in ops.activities
            for task in activity.tasks
            if task.due_date and task.due_date < date.today() and (task.status or "").lower() != "done"
        ]
        enriched_tasks = [
            task
            for ops in data.ops_by_project.values()
            for activity in ops.activities
            for task in activity.tasks
            if getattr(task, "assignee_username", "") and getattr(task, "activity_log", None)
        ]

        self.assertGreaterEqual(len(status_values), 3)
        self.assertGreaterEqual(len(risk_values), 3)
        self.assertTrue(overdue_tasks)
        self.assertTrue(enriched_tasks)
        self.assertEqual(bundle.default_project_id, "proj_resilience")
        self.assertEqual(bundle.default_dataset_id, "ds_demo_portfolio")

    def test_demo_seed_task_contract_matches_identity_and_workflow(self):
        bundle = build_demo_seed_bundle(MODULE.build_password_hash)
        data = MODULE.from_serializable(bundle.payload)
        tasks = [
            task
            for ops in data.ops_by_project.values()
            for activity in ops.activities
            for task in activity.tasks
        ]
        demo_names = {credential.username: credential.full_name for credential in bundle.credentials}
        statuses = {MODULE.normalize_task_status(task.status) for task in tasks}
        assignees = {task.assignee_username for task in tasks}
        pending_validation = [
            task for task in tasks
            if MODULE.normalize_task_status(task.status) == "pending_validation"
        ]

        self.assertTrue(tasks)
        self.assertTrue(all(task.assignee_username in demo_names for task in tasks))
        self.assertTrue(all(task.owner == task.assignee_name == demo_names[task.assignee_username] for task in tasks))
        self.assertIn("aline.duarte", assignees)
        self.assertGreater(len(assignees), 1)
        self.assertNotIn("executive.director", assignees)
        self.assertTrue({"not_started", "in_progress", "overdue", "pending_validation", "completed"}.issubset(statuses))
        self.assertTrue(pending_validation)
        self.assertTrue(any(task.evidence_placeholders for task in pending_validation))

        service = build_in_memory_demo_service(data)
        admin_profile = service._role_profile_for_user(MODULE.find_user_by_username(data, "org.admin"))
        self.assertEqual(admin_profile["id"], "organization_admin")
        meal_queue = [
            task
            for project in data.projects
            for task in service.project_workplan_snapshot(project.id, None, None)["tasks"]
            if MODULE.normalize_task_status(task["status"]) == "pending_validation"
        ]
        self.assertTrue(meal_queue)

    def test_task_mutation_authorization_enforces_role_scope(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            json_path = str(Path(tmp_dir) / "logitrack_demo.json")
            demo_service = build_demo_service()
            with patched_env(
                LOGITRACK_STORAGE_BACKEND="json",
                LOGITRACK_DATA_PATH=json_path,
                LOGITRACK_SQLITE_PATH=None,
                LOGITRACK_ENABLE_RELATIONAL_MIRROR="false",
                LOGITRACK_ENABLE_REPOSITORY_DOMAINS="false",
                LOGITRACK_API_KEY=None,
            ):
                demo_service.seed_workspace(None, None)
                data = MODULE.load_data_from_path()
                _, field_token = issue_token_for_user(data, "aline.duarte")
                _, meal_token = issue_token_for_user(data, "raimundo.cumba")
                _, manager_token = issue_token_for_user(data, "teresa.mbanze")
                _, executive_token = issue_token_for_user(data, "executive.director")
                MODULE.save_data_to_path(data)

                if TestClient is not None and MODULE.app is not None:
                    client = TestClient(MODULE.app)
                    denied_response = client.post(
                        "/v1/demo/tasks/task_res_2/update",
                        headers={"X-Auth-Token": field_token},
                        json={"progress_pct": 60},
                    )
                    self.assertEqual(denied_response.status_code, 403)

                assigned_update = demo_service.update_task(
                    "task_res_5",
                    {"progress_pct": 82, "evidence_note": "Fictional follow-up evidence note"},
                    None,
                    field_token,
                )
                self.assertEqual(assigned_update["task"]["assignee_username"], "aline.duarte")

                with self.assertRaises(ServiceError) as field_denial:
                    demo_service.update_task(
                        "task_res_2",
                        {"progress_pct": 60},
                        None,
                        field_token,
                    )
                self.assertEqual(field_denial.exception.status_code, 403)

                validated = demo_service.validate_task(
                    "task_res_1",
                    {"decision": "validated", "comment": "Fictional MEAL validation note"},
                    None,
                    meal_token,
                )
                self.assertTrue(validated["task"]["validated_at"])

                approved = demo_service.validate_task(
                    "task_res_1",
                    {"decision": "approved", "comment": "Fictional manager approval note"},
                    None,
                    manager_token,
                )
                self.assertEqual(approved["task"]["status"], "completed")

                with self.assertRaisesRegex(RuntimeError, "required permissions"):
                    demo_service.update_task(
                        "task_res_2",
                        {"progress_pct": 70},
                        None,
                        executive_token,
                    )

    def test_demo_workspace_service_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            json_path = str(Path(tmp_dir) / "logitrack_demo.json")
            demo_service = build_demo_service()
            with patched_env(
                LOGITRACK_STORAGE_BACKEND="json",
                LOGITRACK_DATA_PATH=json_path,
                LOGITRACK_SQLITE_PATH=None,
                LOGITRACK_ENABLE_RELATIONAL_MIRROR="false",
                LOGITRACK_ENABLE_REPOSITORY_DOMAINS="false",
                LOGITRACK_API_KEY=None,
            ):
                seeded = demo_service.seed_workspace(None, None)
                loaded = MODULE.load_data_from_path()
                overview = demo_service.workspace_overview(None, seeded["login"]["token"])
                snapshot = demo_service.project_executive_snapshot(overview["default_project_id"], x_auth_token=seeded["login"]["token"])
                report = demo_service.report_preview("donor", overview["default_project_id"], x_auth_token=seeded["login"]["token"])
                simulation = demo_service.simulate_notifications(
                    {"scenario": "overdue_alerts", "project_id": overview["default_project_id"]},
                    None,
                    seeded["login"]["token"],
                )

            self.assertEqual(seeded["login"]["email"], "amina.duarte@bluedelta.org")
            self.assertEqual(seeded["login"]["username"], "org.admin")
            self.assertTrue(seeded["login"]["token"])
            self.assertGreaterEqual(len(loaded.projects), 3)
            self.assertTrue(overview["demo_ready"])
            self.assertGreaterEqual(len(overview["project_cards"]), 3)
            self.assertGreaterEqual(len(overview["data_quality"]["datasets"]), 2)
            self.assertEqual(overview["organization"]["organization_name"], "Blue Delta Consortium")
            self.assertEqual(snapshot["project"]["project_id"], overview["default_project_id"])
            self.assertTrue(snapshot["dashboard"]["widgets"])
            chart_types = {item["chart_type"] for item in snapshot["dashboard"]["widgets"]}
            self.assertIn("map_placeholder", chart_types)
            self.assertIn("narrative_panel", chart_types)
            self.assertEqual(report["audience"], "donor")
            self.assertTrue(report["sections"])
            self.assertGreaterEqual(simulation["count"], 1)

    def test_permission_engine_protects_routes_by_permission(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            json_path = str(Path(tmp_dir) / "logitrack_demo.json")
            demo_service = build_demo_service()
            with patched_env(
                LOGITRACK_STORAGE_BACKEND="json",
                LOGITRACK_DATA_PATH=json_path,
                LOGITRACK_SQLITE_PATH=None,
                LOGITRACK_ENABLE_RELATIONAL_MIRROR="false",
                LOGITRACK_ENABLE_REPOSITORY_DOMAINS="false",
                LOGITRACK_API_KEY=None,
            ):
                demo_service.seed_workspace(None, None)
                data = MODULE.load_data_from_path()
                _, meal_token = issue_token_for_user(data, "raimundo.cumba")
                _, field_token = issue_token_for_user(data, "aline.duarte")
                _, executive_token = issue_token_for_user(data, "executive.director")
                MODULE.save_data_to_path(data)

                meal_workspace = demo_service.workspace_overview(None, meal_token)
                meal_quality = demo_service.data_quality_overview(None, meal_token)

                self.assertTrue(meal_workspace["project_cards"])
                self.assertGreaterEqual(len(meal_quality["datasets"]), 1)

                with self.assertRaisesRegex(RuntimeError, "required permissions"):
                    demo_service.data_quality_overview(None, field_token)

                with self.assertRaisesRegex(RuntimeError, "required permissions"):
                    demo_service.project_workplan_snapshot("proj_health", x_auth_token=executive_token)

    def test_admin_routes_are_org_scoped_and_permission_protected(self):
        if TestClient is None or MODULE.app is None:
            self.skipTest("FastAPI TestClient is not available in this environment.")
        with tempfile.TemporaryDirectory() as tmp_dir:
            json_path = str(Path(tmp_dir) / "logitrack_demo.json")
            demo_service = build_demo_service()
            with patched_env(
                LOGITRACK_STORAGE_BACKEND="json",
                LOGITRACK_DATA_PATH=json_path,
                LOGITRACK_SQLITE_PATH=None,
                LOGITRACK_ENABLE_RELATIONAL_MIRROR="false",
                LOGITRACK_ENABLE_REPOSITORY_DOMAINS="false",
                LOGITRACK_API_KEY=None,
            ):
                demo_service.seed_workspace(None, None)
                data = MODULE.load_data_from_path()
                data.organizations.append(MODULE.OrganizationAccount(
                    id="org_other",
                    organization_name="Other Tenant",
                    status="active",
                    subscription_plan="foundation",
                    created_at=MODULE.now_iso_utc(),
                    updated_at=MODULE.now_iso_utc(),
                ))
                salt, password_hash = MODULE.build_password_hash("OtherUser!2026")
                data.users.append(MODULE.UserAccount(
                    id="user_other_org",
                    username="other.user",
                    organization_id="org_other",
                    team_id="",
                    full_name="Other User",
                    email="other.user@other.org",
                    role="executive_viewer",
                    status="active",
                    permissions=[],
                    password_salt=salt,
                    password_hash=password_hash,
                    api_token_hash="",
                    is_active=True,
                    created_at=MODULE.now_iso_utc(),
                    updated_at=MODULE.now_iso_utc(),
                    last_login_at="",
                ))
                data.projects.append(MODULE.Project(
                    id="proj_other_001",
                    name="Other Tenant Project",
                    objective="Operational project that must stay invisible to Blue Delta users.",
                    organization_id="org_other",
                    project_code="OTHER-001",
                    programme="Other Programme",
                    donor="Other Donor",
                    implementing_partner="Other Partner",
                    sector="Governance",
                    description="Tenant isolation validation project.",
                    country="Otherland",
                    province_coverage=["Capital Province"],
                    district_coverage=["Capital District"],
                    start_date=date(2026, 1, 1),
                    end_date=date(2026, 12, 31),
                    status="active",
                    created_by_user_id="user_other_org",
                    created_by_name="Other User",
                    created_at=MODULE.now_iso_utc(),
                    updated_at=MODULE.now_iso_utc(),
                    published_at=MODULE.now_iso_utc(),
                    status_before_archive="",
                    team_assignments=[],
                    workspace_shell={},
                    cloned_from_project_id="",
                    indicators=[],
                ))
                _, admin_token = issue_token_for_user(data, "org.admin")
                _, manager_token = issue_token_for_user(data, "teresa.mbanze")
                MODULE.save_data_to_path(data)
                client = TestClient(MODULE.app)
                admin_headers = {"X-Auth-Token": admin_token}
                manager_headers = {"X-Auth-Token": manager_token}

                self.assertEqual(client.get("/v1/admin/organization", headers=admin_headers).status_code, 200)
                self.assertEqual(client.get("/v1/admin/users", headers=manager_headers).status_code, 403)
                project_registry_response = client.get("/v1/admin/projects", headers=manager_headers)
                self.assertEqual(project_registry_response.status_code, 200)
                visible_codes = {item["project_code"] for item in project_registry_response.json()["items"]}
                self.assertNotIn("OTHER-001", visible_codes)
                self.assertIn("CHAI-002", visible_codes)

                users_response = client.get("/v1/admin/users", headers=admin_headers)
                self.assertEqual(users_response.status_code, 200)
                usernames = {item["username"] for item in users_response.json()["items"]}
                self.assertIn("org.admin", usernames)
                self.assertNotIn("other.user", usernames)

                team_response = client.post(
                    "/v1/admin/teams",
                    headers=admin_headers,
                    json={
                        "team_name": "Country Delivery",
                        "description": "Programme delivery coordination for the active grants.",
                        "team_lead_user_id": "user_demo_2",
                        "status": "active",
                        "member_user_ids": ["user_demo_2", "user_demo_4"],
                    },
                )
                self.assertEqual(team_response.status_code, 200)
                created_team_id = team_response.json()["team"]["team_id"]

                user_response = client.post(
                    "/v1/admin/users",
                    headers=admin_headers,
                    json={
                        "full_name": "Marta Chongo",
                        "email": "marta.chongo@bluedelta.org",
                        "password": "MartaOps!2026",
                        "role": "field_coordinator",
                        "team_id": created_team_id,
                        "status": "active",
                    },
                )
                self.assertEqual(user_response.status_code, 200)
                created_user = user_response.json()["user"]
                self.assertEqual(created_user["organization_id"], "org_blue_delta")
                self.assertEqual(created_user["team_id"], created_team_id)

                updated_user = client.patch(
                    f"/v1/admin/users/{created_user['id']}",
                    headers=admin_headers,
                    json={"role": "meal_officer", "status": "active"},
                )
                self.assertEqual(updated_user.status_code, 200)
                self.assertEqual(updated_user.json()["user"]["role"], "meal_officer")

                self.assertEqual(client.post(f"/v1/admin/users/{created_user['id']}/suspend", headers=admin_headers).status_code, 200)
                self.assertEqual(client.post(f"/v1/admin/users/{created_user['id']}/reactivate", headers=admin_headers).status_code, 200)

                permissions_response = client.get("/v1/admin/permissions", headers=admin_headers)
                self.assertEqual(permissions_response.status_code, 200)
                self.assertTrue(permissions_response.json()["groups"])
                self.assertTrue(permissions_response.json()["roles"])

                org_update = client.patch(
                    "/v1/admin/organization",
                    headers=admin_headers,
                    json={"contact_person": "Teresa Mbanze", "timezone": "Africa/Maputo"},
                )
                self.assertEqual(org_update.status_code, 200)
                self.assertEqual(org_update.json()["organization"]["contact_person"], "Teresa Mbanze")

                project_create = client.post(
                    "/v1/admin/projects",
                    headers=admin_headers,
                    json={
                        "project_name": "Northern Resilience Accelerator",
                        "project_code": "NRA-004",
                        "programme": "Resilience Acceleration Window",
                        "donor": "Climate Action Facility",
                        "implementing_partner": "Blue Delta Consortium",
                        "sector": "Resilience",
                        "description": "Project registry foundation validation through the administration UI route layer.",
                        "country": "Mozambique",
                        "province_coverage": ["Nampula", "Zambezia"],
                        "district_coverage": ["Mogovolas", "Ile"],
                        "start_date": "2026-06-01",
                        "end_date": "2027-12-31",
                        "status": "draft",
                        "team_assignments": [
                            {"user_id": "user_demo_2", "role": "programme_manager", "team_id": "team_programme_ops"},
                            {"user_id": "user_demo_3", "role": "meal_officer", "team_id": "team_meal"},
                            {"user_id": "user_demo_4", "role": "field_coordinator", "team_id": "team_field_ops"},
                            {"user_id": "user_demo_5", "role": "executive_viewer", "team_id": "team_management"},
                        ],
                    },
                )
                self.assertEqual(project_create.status_code, 200)
                created_project = project_create.json()["project"]
                self.assertEqual(created_project["organization_id"], "org_blue_delta")
                self.assertEqual(created_project["status"], "draft")
                self.assertEqual(created_project["assigned_users_total"], 4)

                project_update = client.patch(
                    f"/v1/admin/projects/{created_project['project_id']}",
                    headers=admin_headers,
                    json={
                        "project_name": "Northern Resilience Accelerator",
                        "project_code": "NRA-004",
                        "programme": "Resilience Acceleration Window",
                        "donor": "Climate Action Facility II",
                        "implementing_partner": "Blue Delta Consortium",
                        "sector": "Resilience",
                        "description": "Updated registry metadata for governance testing.",
                        "country": "Mozambique",
                        "province_coverage": ["Nampula", "Zambezia"],
                        "district_coverage": ["Mogovolas", "Ile"],
                        "start_date": "2026-06-01",
                        "end_date": "2027-12-31",
                        "status": "draft",
                        "team_assignments": [
                            {"user_id": "user_demo_2", "role": "programme_manager", "team_id": "team_programme_ops"},
                            {"user_id": "user_demo_3", "role": "meal_officer", "team_id": "team_meal"},
                            {"user_id": "user_demo_4", "role": "field_coordinator", "team_id": "team_field_ops"},
                            {"user_id": "user_demo_5", "role": "executive_viewer", "team_id": "team_management"},
                        ],
                    },
                )
                self.assertEqual(project_update.status_code, 200)
                self.assertEqual(project_update.json()["project"]["donor"], "Climate Action Facility II")

                project_publish = client.post(f"/v1/admin/projects/{created_project['project_id']}/publish", headers=admin_headers)
                self.assertEqual(project_publish.status_code, 200)
                self.assertEqual(project_publish.json()["project"]["status"], "published")
                self.assertTrue(project_publish.json()["project"]["workspace_ready"])

                project_activate = client.post(f"/v1/admin/projects/{created_project['project_id']}/activate", headers=admin_headers)
                self.assertEqual(project_activate.status_code, 200)
                self.assertEqual(project_activate.json()["project"]["status"], "active")

                project_pause = client.post(f"/v1/admin/projects/{created_project['project_id']}/deactivate", headers=admin_headers)
                self.assertEqual(project_pause.status_code, 200)
                self.assertEqual(project_pause.json()["project"]["status"], "paused")

                cloned_project = client.post(f"/v1/admin/projects/{created_project['project_id']}/clone", headers=admin_headers)
                self.assertEqual(cloned_project.status_code, 200)
                self.assertEqual(cloned_project.json()["project"]["status"], "draft")
                self.assertEqual(cloned_project.json()["project"]["cloned_from_project_id"], created_project["project_id"])
                self.assertFalse(cloned_project.json()["project"]["workspace_ready"])

                project_archive = client.post(f"/v1/admin/projects/{created_project['project_id']}/archive", headers=admin_headers)
                self.assertEqual(project_archive.status_code, 200)
                self.assertEqual(project_archive.json()["project"]["status"], "archived")

                project_restore = client.post(f"/v1/admin/projects/{created_project['project_id']}/restore", headers=admin_headers)
                self.assertEqual(project_restore.status_code, 200)
                self.assertEqual(project_restore.json()["project"]["status"], "paused")

                audit_response = client.get("/v1/admin/audit?action=user.created", headers=admin_headers)
                self.assertEqual(audit_response.status_code, 200)
                self.assertTrue(any(item["action"] == "user.created" for item in audit_response.json()["items"]))

                project_audit = client.get("/v1/admin/audit?search=project.", headers=admin_headers)
                self.assertEqual(project_audit.status_code, 200)
                project_actions = {item["action"] for item in project_audit.json()["items"]}
                self.assertTrue({
                    "project.created",
                    "project.updated",
                    "project.published",
                    "project.activated",
                    "project.paused",
                    "project.archived",
                    "project.restored",
                    "project.cloned",
                }.issubset(project_actions))

    def test_demo_workspace_routes_stay_stable_with_mixed_datetime_inputs(self):
        bundle = build_demo_seed_bundle(MODULE.build_password_hash)
        data = MODULE.from_serializable(bundle.payload)
        service = build_in_memory_demo_service(data)

        mixed_period_values = [
            "2026-05-01T00:00:00Z",
            "2026-05-01T00:00:00+00:00",
            "2026-05-01",
            datetime(2026, 4, 1, 0, 0, 0),
            datetime(2026, 3, 1, 0, 0, 0, tzinfo=timezone.utc),
            None,
            "invalid-date-value",
        ]
        project_records = [record for record in data.reporting_records if record.project_id == "proj_health"]
        self.assertGreaterEqual(len(project_records), len(mixed_period_values))
        for record, value in zip(project_records, mixed_period_values):
            record.reporting_period = value

        executive = service.project_executive_snapshot("proj_health")
        workplan = service.project_workplan_snapshot("proj_health")
        report = service.report_preview("management", "proj_health")
        narrative = service.narrative_summary("proj_health")

        self.assertEqual(executive["project"]["project_id"], "proj_health")
        self.assertIn("reporting_records", executive)
        self.assertEqual(workplan["project_id"], "proj_health")
        self.assertIn("sections", report)
        self.assertIn("project", narrative)

    def test_operational_task_workflow_loop_updates_posture_and_feed(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            json_path = str(Path(tmp_dir) / "logitrack_demo.json")
            demo_service = build_demo_service()
            with patched_env(
                LOGITRACK_STORAGE_BACKEND="json",
                LOGITRACK_DATA_PATH=json_path,
                LOGITRACK_SQLITE_PATH=None,
                LOGITRACK_ENABLE_RELATIONAL_MIRROR="false",
                LOGITRACK_ENABLE_REPOSITORY_DOMAINS="false",
                LOGITRACK_API_KEY=None,
            ):
                demo_service.seed_workspace(None, None)
                data = MODULE.load_data_from_path()
                _, manager_token = issue_token_for_user(data, "teresa.mbanze")
                _, analyst_token = issue_token_for_user(data, "raimundo.cumba")
                _, field_token = issue_token_for_user(data, "aline.duarte")
                MODULE.save_data_to_path(data)

                project_id = "proj_health"
                baseline = demo_service.project_workplan_snapshot(project_id, None, manager_token)
                baseline_total = baseline["summary"]["tasks_total"]
                baseline_overdue = baseline["summary"]["tasks_overdue"]

                created = demo_service.create_task(
                    {
                        "project_id": project_id,
                        "title": "Validate district coverage evidence",
                        "description": "Confirm the latest district evidence pack before the management review.",
                        "assignee_username": "aline.duarte",
                        "assignee_name": "Aline Duarte",
                        "due_date": (date.today() - timedelta(days=2)).isoformat(),
                        "priority": "high",
                        "category": "validation",
                        "linked_indicator_id": "ind_health_coverage",
                    },
                    None,
                    manager_token,
                )
                task_id = created["task"]["task_id"]
                after_create = created["workflow"]

                self.assertEqual(after_create["summary"]["tasks_total"], baseline_total + 1)
                self.assertGreaterEqual(after_create["summary"]["tasks_overdue"], baseline_overdue + 1)
                self.assertEqual(created["task"]["assignee_username"], "aline.duarte")

                updated = demo_service.update_task(
                    task_id,
                    {
                        "status": "in_progress",
                        "progress_pct": 45,
                        "comment": "Field coordinator updated delivery evidence.",
                        "evidence_note": "Evidence pack placeholder uploaded",
                    },
                    None,
                    field_token,
                )
                self.assertEqual(updated["task"]["status"], "overdue")
                self.assertGreaterEqual(updated["task"]["evidence_count"], 1)
                self.assertGreaterEqual(updated["task"]["comment_count"], 1)

                submitted = demo_service.update_task(
                    task_id,
                    {
                        "progress_pct": 90,
                        "comment": "Submitted for validation after district follow-up.",
                        "submit_for_validation": True,
                    },
                    None,
                    field_token,
                )
                pending_snapshot = demo_service.project_executive_snapshot(project_id, None, manager_token)
                self.assertEqual(submitted["task"]["status"], "pending_validation")
                self.assertGreaterEqual(submitted["workflow"]["task_board"]["pending_validation"], 1)
                self.assertTrue(
                    any(
                        "validation" in f"{item.get('title', '')} {item.get('message', '')}".lower()
                        for item in pending_snapshot["notifications"]
                    )
                )

                validated = demo_service.validate_task(
                    task_id,
                    {"decision": "validated", "comment": "Evidence quality is sufficient for closure."},
                    None,
                    analyst_token,
                )
                self.assertEqual(validated["task"]["status"], "pending_validation")

                approved = demo_service.validate_task(
                    task_id,
                    {"decision": "approved", "comment": "Manager approved closure."},
                    None,
                    manager_token,
                )
                final_snapshot = demo_service.project_executive_snapshot(project_id, None, manager_token)
                final_workplan = demo_service.project_workplan_snapshot(project_id, None, manager_token)

                self.assertEqual(approved["task"]["status"], "completed")
                self.assertEqual(final_workplan["summary"]["tasks_total"], baseline_total + 1)
                self.assertLess(final_workplan["summary"]["tasks_overdue"], after_create["summary"]["tasks_overdue"])
                self.assertGreaterEqual(
                    final_snapshot["executive"]["reporting_confidence_score"],
                    pending_snapshot["executive"]["reporting_confidence_score"],
                )
                titles = {item.get("title", "") for item in final_snapshot["activity_feed"]}
                self.assertIn("Task assigned", titles)
                self.assertIn("Approval completed", titles)
                self.assertTrue(final_snapshot["activity_feed"])
                self.assertTrue(final_workplan["activity_feed"])


if __name__ == "__main__":
    unittest.main()
