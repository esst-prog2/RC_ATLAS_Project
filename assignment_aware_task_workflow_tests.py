import copy
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from demo_smoke_tests import MODULE, TestClient, issue_token_for_user, patched_env


class AssignmentAwareTaskWorkflowTests(unittest.TestCase):
    project_id = "proj_resilience"
    ids = {"teresa.mbanze": "user_demo_2", "raimundo.cumba": "user_demo_3", "aline.duarte": "user_demo_4"}

    def setUp(self):
        if TestClient is None or MODULE.app is None:
            self.skipTest("FastAPI TestClient is unavailable.")
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_path = str(Path(self.temp_dir.name) / "assignment_aware.json")
        self.environment = patched_env(
            LOGITRACK_STORAGE_BACKEND="json",
            LOGITRACK_DATA_PATH=self.data_path,
            LOGITRACK_SQLITE_PATH=None,
            LOGITRACK_ENABLE_RELATIONAL_MIRROR="false",
            LOGITRACK_ENABLE_REPOSITORY_DOMAINS="false",
            LOGITRACK_API_KEY=None,
        )
        self.environment.__enter__()
        MODULE.demo_workspace_service.seed_workspace(None, None)
        data = MODULE.load_data_from_path()
        self.tokens = {}
        for username in ("org.admin", "teresa.mbanze", "aline.duarte", "raimundo.cumba", "executive.director"):
            _, self.tokens[username] = issue_token_for_user(data, username)
        MODULE.save_data_to_path(data)
        self.client = TestClient(MODULE.app)

    def tearDown(self):
        if hasattr(self, "client"):
            self.client.close()
        if hasattr(self, "environment"):
            self.environment.__exit__(None, None, None)
        if hasattr(self, "temp_dir"):
            self.temp_dir.cleanup()

    def headers(self, username):
        return {"X-Auth-Token": self.tokens[username]}

    def create_task(self, title, assignee="aline.duarte", mode="validation_and_approval", evidence=False, **overrides):
        payload = {
            "project_id": self.project_id,
            "title": title,
            "assignee_user_id": self.ids[assignee],
            "assignee_username": assignee,
            "review_mode": mode,
            "evidence_required": evidence,
            "due_date": (date.today() + timedelta(days=10)).isoformat(),
        }
        if mode in {"validation", "validation_and_approval"}:
            payload["validator_user_id"] = self.ids["raimundo.cumba"]
        if mode in {"approval", "validation_and_approval"}:
            payload["approver_user_id"] = self.ids["teresa.mbanze"]
        payload.update(overrides)
        return self.client.post("/v1/demo/tasks", headers=self.headers("teresa.mbanze"), json=payload)

    def update(self, task_id, actor, **payload):
        return self.client.post(f"/v1/demo/tasks/{task_id}/update", headers=self.headers(actor), json=payload)

    def review(self, task_id, actor, decision):
        return self.client.post(
            f"/v1/demo/tasks/{task_id}/validate",
            headers=self.headers(actor),
            json={"decision": decision},
        )

    def task_record(self, task_id):
        data = MODULE.load_data_from_path()
        for ops in data.ops_by_project.values():
            for activity in ops.activities:
                for task in activity.tasks:
                    if task.id == task_id:
                        return data, activity, task
        self.fail(f"Task '{task_id}' was not persisted.")

    def start(self, title, assignee="aline.duarte", **kwargs):
        created = self.create_task(title, assignee=assignee, **kwargs)
        self.assertEqual(created.status_code, 200, created.text)
        task_id = created.json()["task"]["task_id"]
        started = self.update(task_id, assignee, status="in_progress", progress_pct=25)
        self.assertEqual(started.status_code, 200, started.text)
        return task_id

    def test_pm_direct_completion_without_evidence_permission(self):
        task_id = self.start("PM direct", assignee="teresa.mbanze", mode="direct_completion")
        self.assertEqual(self.update(task_id, "teresa.mbanze", evidence_note="optional").status_code, 403)
        completed = self.update(task_id, "teresa.mbanze", complete_execution=True)
        self.assertEqual(completed.status_code, 200, completed.text)
        self.assertEqual((completed.json()["task"]["status"], completed.json()["task"]["review_stage"]), ("completed", "complete"))

    def test_meal_execution_with_approval(self):
        task_id = self.start("MEAL execution", assignee="raimundo.cumba", mode="approval")
        submitted = self.update(task_id, "raimundo.cumba", complete_execution=True)
        self.assertEqual(submitted.status_code, 200, submitted.text)
        self.assertEqual((submitted.json()["task"]["status"], submitted.json()["task"]["review_stage"]), ("pending_validation", "approval"))
        self.assertEqual(self.review(task_id, "teresa.mbanze", "approved").json()["task"]["status"], "completed")

    def test_validation_only(self):
        task_id = self.start("Validation only", mode="validation")
        submitted = self.update(task_id, "aline.duarte", complete_execution=True)
        self.assertEqual(submitted.status_code, 200, submitted.text)
        validated = self.review(task_id, "raimundo.cumba", "validated")
        self.assertEqual((validated.json()["task"]["status"], validated.json()["task"]["review_stage"]), ("completed", "complete"))

    def test_two_stage_golden_journey(self):
        task_id = self.start("Golden Journey")
        submitted = self.update(task_id, "aline.duarte", evidence_note="Field evidence", submit_for_validation=True)
        self.assertEqual((submitted.status_code, submitted.json()["task"]["review_stage"]), (200, "validation"))
        validated = self.review(task_id, "raimundo.cumba", "validated")
        self.assertEqual((validated.json()["task"]["status"], validated.json()["task"]["review_stage"]), ("pending_validation", "approval"))
        approved = self.review(task_id, "teresa.mbanze", "approved")
        self.assertEqual(approved.json()["task"]["status"], "completed")

    def test_non_assignee_is_rejected_without_mutation(self):
        created = self.create_task("Ownership")
        task_id = created.json()["task"]["task_id"]
        before_data, _, before_task = self.task_record(task_id)
        before = MODULE.to_serializable(before_task), len(before_data.audit_events)
        denied = self.update(task_id, "teresa.mbanze", progress_pct=50)
        self.assertEqual(denied.status_code, 403, denied.text)
        after_data, _, after_task = self.task_record(task_id)
        self.assertEqual((MODULE.to_serializable(after_task), len(after_data.audit_events)), before)

    def test_capable_but_non_designated_reviewers_are_rejected(self):
        data = MODULE.load_data_from_path()
        teresa = MODULE.find_user_by_username(data, "teresa.mbanze")
        teresa.permissions = [*MODULE.role_permissions(teresa.role), "VALIDATE_EVIDENCE"]
        raimundo = MODULE.find_user_by_username(data, "raimundo.cumba")
        raimundo.permissions = [*MODULE.role_permissions(raimundo.role), "APPROVE_TASKS"]
        MODULE.save_data_to_path(data)
        task_id = self.start("Designated reviewers")
        self.assertEqual(self.update(task_id, "aline.duarte", complete_execution=True).status_code, 200)
        self.assertEqual(self.review(task_id, "teresa.mbanze", "validated").status_code, 403)
        self.assertEqual(self.review(task_id, "raimundo.cumba", "validated").status_code, 200)
        self.assertEqual(self.review(task_id, "raimundo.cumba", "approved").status_code, 403)

    def test_invalid_reviewer_configurations_are_atomic(self):
        def counts():
            data = MODULE.load_data_from_path()
            tasks = sum(len(a.tasks) for ops in data.ops_by_project.values() for a in ops.activities)
            return tasks, len(data.audit_events)

        cases = [
            ("Self validation", {"assignee": "raimundo.cumba", "mode": "validation", "validator_user_id": self.ids["raimundo.cumba"], "approver_user_id": None}),
            ("Self approval", {"assignee": "teresa.mbanze", "mode": "approval", "validator_user_id": None, "approver_user_id": self.ids["teresa.mbanze"]}),
            ("Same reviewer", {"validator_user_id": self.ids["raimundo.cumba"], "approver_user_id": self.ids["raimundo.cumba"]}),
            ("Lacks capability", {"mode": "validation", "validator_user_id": "user_demo_5", "approver_user_id": None}),
            ("Non-member", {"mode": "approval", "validator_user_id": None, "approver_user_id": "user_demo_1"}),
        ]
        for title, kwargs in cases:
            with self.subTest(title=title):
                before = counts()
                response = self.create_task(title, **kwargs)
                self.assertEqual(response.status_code, 400, response.text)
                self.assertEqual(counts(), before)

        data = MODULE.load_data_from_path()
        executive = MODULE.find_user_by_username(data, "executive.director")
        executive.organization_id = "org_foreign"
        executive.permissions = ["VALIDATE_EVIDENCE"]
        MODULE.save_data_to_path(data)
        before = counts()
        response = self.create_task("Cross-org", mode="validation", validator_user_id=executive.id, approver_user_id=None)
        self.assertEqual(response.status_code, 400, response.text)
        self.assertEqual(counts(), before)

    def test_evidence_gate_and_optional_completion(self):
        task_id = self.start("Evidence required", mode="validation", evidence=True)
        self.assertEqual(self.update(task_id, "aline.duarte", complete_execution=True).status_code, 409)
        self.assertEqual(self.update(task_id, "aline.duarte", evidence_note="Signed checklist").status_code, 200)
        self.assertEqual(self.update(task_id, "aline.duarte", complete_execution=True).status_code, 200)
        optional_id = self.start("Evidence optional", assignee="teresa.mbanze", mode="direct_completion")
        self.assertEqual(self.update(optional_id, "teresa.mbanze", complete_execution=True).status_code, 200)

    def test_evidence_required_rejects_assignee_without_evidence_capability(self):
        before_data = MODULE.load_data_from_path()
        before_count = sum(len(a.tasks) for ops in before_data.ops_by_project.values() for a in ops.activities)
        response = self.create_task(
            "PM evidence required",
            assignee="teresa.mbanze",
            mode="direct_completion",
            evidence=True,
        )
        self.assertEqual(response.status_code, 400, response.text)
        after_data = MODULE.load_data_from_path()
        self.assertEqual(
            sum(len(a.tasks) for ops in after_data.ops_by_project.values() for a in ops.activities),
            before_count,
        )

    def test_review_order_alias_and_error_contract(self):
        task_id = self.start("Approval alias", assignee="raimundo.cumba", mode="approval")
        before = MODULE.to_serializable(self.task_record(task_id)[2])
        alias_denied = self.update(task_id, "raimundo.cumba", submit_for_validation=True)
        self.assertEqual(alias_denied.status_code, 409, alias_denied.text)
        self.assertEqual(MODULE.to_serializable(self.task_record(task_id)[2]), before)

        two_stage_id = self.start("Review order")
        early_validator = self.review(two_stage_id, "raimundo.cumba", "validated")
        self.assertEqual(early_validator.status_code, 409, early_validator.text)
        self.assertEqual(self.update(two_stage_id, "aline.duarte", complete_execution=True).status_code, 200)
        early_approver = self.review(two_stage_id, "teresa.mbanze", "approved")
        self.assertEqual(early_approver.status_code, 409, early_approver.text)
        malformed = self.review(two_stage_id, "raimundo.cumba", "unsupported")
        self.assertEqual(malformed.status_code, 400, malformed.text)
    def test_approval_return_restarts_the_configured_sequence(self):
        task_id = self.start("Approval return")
        self.assertEqual(self.update(task_id, "aline.duarte", complete_execution=True).status_code, 200)
        self.assertEqual(self.review(task_id, "raimundo.cumba", "validated").status_code, 200)
        returned = self.review(task_id, "teresa.mbanze", "rejected")
        self.assertEqual(returned.status_code, 200, returned.text)
        task = returned.json()["task"]
        self.assertEqual((task["status"], task["review_stage"]), ("in_progress", "execution"))
        self.assertFalse(task["submitted_at"])
        self.assertFalse(task["validated_at"])
        self.assertFalse(task["approved_at"])
        resubmitted = self.update(task_id, "aline.duarte", complete_execution=True)
        self.assertEqual((resubmitted.status_code, resubmitted.json()["task"]["review_stage"]), (200, "validation"))

    def test_creation_time_evidence_requires_assignee_evidence_capability(self):
        before_data = MODULE.load_data_from_path()
        before_count = sum(len(a.tasks) for ops in before_data.ops_by_project.values() for a in ops.activities)
        response = self.create_task("Injected creation evidence", evidence_placeholders=["Not authorized"])
        self.assertEqual(response.status_code, 403, response.text)
        after_data = MODULE.load_data_from_path()
        after_count = sum(len(a.tasks) for ops in after_data.ops_by_project.values() for a in ops.activities)
        self.assertEqual(after_count, before_count)

    def test_omitted_defaults_are_persisted(self):
        response = self.client.post(
            "/v1/demo/tasks",
            headers=self.headers("teresa.mbanze"),
            json={
                "project_id": self.project_id,
                "title": "Defaults",
                "assignee_user_id": self.ids["aline.duarte"],
                "assignee_username": "aline.duarte",
                "validator_user_id": self.ids["raimundo.cumba"],
                "approver_user_id": self.ids["teresa.mbanze"],
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["task"]["review_mode"], "validation_and_approval")
        self.assertFalse(response.json()["task"]["evidence_required"])

    def test_legacy_assignee_resolution_is_non_mutating_and_fail_closed(self):
        created = self.create_task("Legacy")
        task_id = created.json()["task"]["task_id"]
        data, _, task = self.task_record(task_id)
        task.assignee_user_id = ""
        task.review_mode = ""
        task.validator_user_id = ""
        task.approver_user_id = ""
        MODULE.save_data_to_path(data)
        response = self.client.get(f"/v1/demo/projects/{self.project_id}/workplan", headers=self.headers("aline.duarte"))
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.task_record(task_id)[2].assignee_user_id, "")
        self.assertEqual(self.update(task_id, "aline.duarte", status="in_progress").status_code, 200)
        self.assertEqual(self.task_record(task_id)[2].assignee_user_id, "")

        bad = self.create_task("Unresolved legacy")
        bad_id = bad.json()["task"]["task_id"]
        data, _, task = self.task_record(bad_id)
        task.assignee_user_id = ""
        task.assignee_username = "missing.user"
        task.review_mode = ""
        task.validator_user_id = ""
        task.approver_user_id = ""
        MODULE.save_data_to_path(data)
        before = MODULE.to_serializable(task)
        denied = self.update(bad_id, "aline.duarte", status="in_progress")
        self.assertEqual(denied.status_code, 409, denied.text)
        self.assertEqual(MODULE.to_serializable(self.task_record(bad_id)[2]), before)

    def test_ambiguous_legacy_reviewer_fails_closed(self):
        task_id = self.create_task("Ambiguous legacy reviewer").json()["task"]["task_id"]
        data, _, task = self.task_record(task_id)
        task.review_mode = ""
        task.validator_user_id = ""
        task.approver_user_id = ""
        teresa = MODULE.find_user_by_username(data, "teresa.mbanze")
        teresa.permissions = [*MODULE.role_permissions(teresa.role), "VALIDATE_EVIDENCE"]
        MODULE.save_data_to_path(data)
        denied = self.update(task_id, "aline.duarte", status="in_progress")
        self.assertEqual(denied.status_code, 409, denied.text)

    def test_ambiguous_legacy_assignee_fails_closed(self):
        task_id = self.create_task("Ambiguous legacy").json()["task"]["task_id"]
        data, _, task = self.task_record(task_id)
        task.assignee_user_id = ""
        task.review_mode = ""
        task.validator_user_id = ""
        task.approver_user_id = ""
        aline = MODULE.find_user_by_username(data, "aline.duarte")
        duplicate = copy.deepcopy(aline)
        duplicate.id = "user_duplicate_aline"
        data.users.append(duplicate)
        project = MODULE.find_project(data, self.project_id)
        assignment = copy.deepcopy(next(item for item in project.team_assignments if item.user_id == aline.id))
        assignment.id = "assignment_duplicate_aline"
        assignment.user_id = duplicate.id
        project.team_assignments.append(assignment)
        MODULE.save_data_to_path(data)
        self.assertEqual(self.update(task_id, "aline.duarte", status="in_progress").status_code, 409)

    def test_legacy_project_activity_creation_route_uses_routing_contract(self):
        data = MODULE.load_data_from_path()
        activity_id = data.ops_by_project[self.project_id].activities[0].id
        route = f"/v1/projects/{self.project_id}/activities/{activity_id}/tasks"
        before_tasks = sum(
            len(activity.tasks)
            for ops in data.ops_by_project.values()
            for activity in ops.activities
        )

        rejected = self.client.post(
            route,
            headers=self.headers("teresa.mbanze"),
            json={
                "id": "task_legacy_route_rejected",
                "name": "Missing default reviewers",
                "assignee_user_id": self.ids["teresa.mbanze"],
                "assignee_username": "teresa.mbanze",
            },
        )
        self.assertEqual(rejected.status_code, 400, rejected.text)
        data = MODULE.load_data_from_path()
        self.assertEqual(
            sum(len(activity.tasks) for ops in data.ops_by_project.values() for activity in ops.activities),
            before_tasks,
        )

        created = self.client.post(
            route,
            headers=self.headers("teresa.mbanze"),
            json={
                "id": "task_legacy_route_direct",
                "name": "Legacy route direct completion",
                "assignee_user_id": self.ids["teresa.mbanze"],
                "assignee_username": "teresa.mbanze",
                "review_mode": "direct_completion",
                "evidence_required": False,
            },
        )
        self.assertEqual(created.status_code, 200, created.text)
        self.assertEqual(created.json()["task_id"], "task_legacy_route_direct")
        _, activity, task = self.task_record("task_legacy_route_direct")
        self.assertEqual(activity.id, activity_id)
        self.assertEqual(
            (task.assignee_user_id, task.review_mode, task.evidence_required, task.review_stage),
            (self.ids["teresa.mbanze"], "direct_completion", False, "execution"),
        )
    def test_escalation_preserves_routing(self):
        task_id = self.start("Escalation")
        before = self.task_record(task_id)[2]
        routing = (before.assignee_user_id, before.review_mode, before.validator_user_id, before.approver_user_id, before.review_stage)
        escalated = self.update(task_id, "aline.duarte", escalate=True)
        self.assertEqual(escalated.status_code, 200, escalated.text)
        after = self.task_record(task_id)[2]
        self.assertEqual(after.status, "escalated")
        self.assertEqual((after.assignee_user_id, after.review_mode, after.validator_user_id, after.approver_user_id, after.review_stage), routing)

    def test_routing_changes_only_before_execution(self):
        created = self.create_task("Routing", mode="validation")
        task_id = created.json()["task"]["task_id"]
        changed = self.client.patch(
            f"/v1/demo/tasks/{task_id}/routing",
            headers=self.headers("teresa.mbanze"),
            json={
                "assignee_user_id": self.ids["teresa.mbanze"],
                "assignee_username": "teresa.mbanze",
                "review_mode": "direct_completion",
                "evidence_required": False,
            },
        )
        self.assertEqual(changed.status_code, 200, changed.text)
        self.assertEqual(self.update(task_id, "teresa.mbanze", status="in_progress").status_code, 200)
        denied = self.client.patch(
            f"/v1/demo/tasks/{task_id}/routing",
            headers=self.headers("teresa.mbanze"),
            json={
                "assignee_user_id": self.ids["aline.duarte"],
                "assignee_username": "aline.duarte",
                "review_mode": "validation",
                "validator_user_id": self.ids["raimundo.cumba"],
                "evidence_required": False,
            },
        )
        self.assertEqual(denied.status_code, 409, denied.text)

    def test_nested_activity_tasks_use_routing_contract_atomically(self):
        data = MODULE.load_data_from_path()
        project = MODULE.find_project(data, self.project_id)
        indicator_id = project.indicators[0].id
        before_ops = MODULE.to_serializable(data.ops_by_project[self.project_id])
        before_audits = MODULE.to_serializable(data.audit_events)
        invalid = self.client.post(
            f"/v1/projects/{self.project_id}/activities",
            headers=self.headers("teresa.mbanze"),
            json={
                "id": "activity_nested_atomic_failure",
                "name": "Nested atomic failure",
                "linked_indicator_ids": [indicator_id],
                "tasks": [
                    {
                        "id": "task_nested_would_be_valid",
                        "name": "Valid first task",
                        "assignee_user_id": self.ids["teresa.mbanze"],
                        "assignee_username": "teresa.mbanze",
                        "review_mode": "direct_completion",
                    },
                    {
                        "id": "task_nested_missing_reviewers",
                        "name": "Default routing without reviewers",
                        "assignee_user_id": self.ids["aline.duarte"],
                        "assignee_username": "aline.duarte",
                    },
                ],
            },
        )
        self.assertEqual(invalid.status_code, 400, invalid.text)
        after = MODULE.load_data_from_path()
        self.assertEqual(MODULE.to_serializable(after.ops_by_project[self.project_id]), before_ops)
        self.assertEqual(MODULE.to_serializable(after.audit_events), before_audits)

        created = self.client.post(
            f"/v1/projects/{self.project_id}/activities",
            headers=self.headers("teresa.mbanze"),
            json={
                "id": "activity_nested_assignment_aware",
                "name": "Nested assignment aware",
                "linked_indicator_ids": [indicator_id],
                "tasks": [{
                    "id": "task_nested_assignment_aware",
                    "name": "Nested configured task",
                    "assignee_user_id": self.ids["aline.duarte"],
                    "assignee_username": "aline.duarte",
                    "validator_user_id": self.ids["raimundo.cumba"],
                    "approver_user_id": self.ids["teresa.mbanze"],
                }],
            },
        )
        self.assertEqual(created.status_code, 200, created.text)
        self.assertEqual(created.json()["tasks_total"], 1)
        _, activity, task = self.task_record("task_nested_assignment_aware")
        self.assertEqual(activity.id, "activity_nested_assignment_aware")
        self.assertEqual(
            (task.assignee_user_id, task.review_mode, task.validator_user_id, task.approver_user_id, task.evidence_required),
            (self.ids["aline.duarte"], "validation_and_approval", self.ids["raimundo.cumba"], self.ids["teresa.mbanze"], False),
        )

    def test_direct_completion_timestamps_and_audit_routing_context(self):
        direct_id = self.start("Direct timestamp semantics", assignee="teresa.mbanze", mode="direct_completion")
        completed = self.update(direct_id, "teresa.mbanze", complete_execution=True)
        self.assertEqual(completed.status_code, 200, completed.text)
        direct = completed.json()["task"]
        self.assertEqual((direct["submitted_at"], direct["validated_at"], direct["approved_at"]), ("", "", ""))

        reviewed_id = self.start("Audit routing context")
        self.assertEqual(self.update(reviewed_id, "aline.duarte", complete_execution=True).status_code, 200)
        self.assertEqual(self.review(reviewed_id, "raimundo.cumba", "validated").status_code, 200)
        self.assertEqual(self.review(reviewed_id, "teresa.mbanze", "approved").status_code, 200)
        data = MODULE.load_data_from_path()
        events = {
            event.action: event
            for event in data.audit_events
            if event.target_id == reviewed_id
            and event.action in {"demo.task.submitted", "demo.task.validated", "demo.task.approved"}
        }
        self.assertEqual(set(events), {"demo.task.submitted", "demo.task.validated", "demo.task.approved"})
        for event in events.values():
            self.assertEqual(event.details["assignee_user_id"], self.ids["aline.duarte"])
            self.assertEqual(event.details["review_mode"], "validation_and_approval")
        self.assertEqual(events["demo.task.validated"].details["reviewer_user_id"], self.ids["raimundo.cumba"])
        self.assertEqual(events["demo.task.approved"].details["reviewer_user_id"], self.ids["teresa.mbanze"])

    def test_canonical_assignee_identity_overrides_stale_display_cache(self):
        task_id = self.create_task("Canonical display identity").json()["task"]["task_id"]
        data, _, task = self.task_record(task_id)
        task.assignee_username = "teresa.mbanze"
        task.assignee_name = "Stale Teresa Cache"
        task.owner = "Stale Teresa Cache"
        MODULE.save_data_to_path(data)
        response = self.client.get(f"/v1/demo/projects/{self.project_id}/workplan", headers=self.headers("aline.duarte"))
        self.assertEqual(response.status_code, 200, response.text)
        row = next(item for item in response.json()["tasks"] if item["task_id"] == task_id)
        self.assertEqual(row["assignee_user_id"], self.ids["aline.duarte"])
        self.assertEqual(row["assignee_username"], "aline.duarte")
        self.assertEqual(row["assignee_name"], "Aline Duarte")
        persisted = self.task_record(task_id)[2]
        self.assertEqual((persisted.assignee_username, persisted.assignee_name), ("teresa.mbanze", "Stale Teresa Cache"))
        before = MODULE.to_serializable(persisted)
        self.assertEqual(self.update(task_id, "teresa.mbanze", status="in_progress").status_code, 403)
        self.assertEqual(MODULE.to_serializable(self.task_record(task_id)[2]), before)
        self.assertEqual(self.update(task_id, "aline.duarte", status="in_progress").status_code, 200)

    def test_execution_structural_fields_are_rejected_atomically(self):
        task_id = self.create_task("Structural protection").json()["task"]["task_id"]
        data, _, task = self.task_record(task_id)
        before_task = MODULE.to_serializable(task)
        before_audits = MODULE.to_serializable(data.audit_events)
        response = self.update(
            task_id,
            "aline.duarte",
            progress_pct=50,
            priority="critical",
            due_date=(date.today() + timedelta(days=1)).isoformat(),
            category="reporting",
            linked_indicator_id="foreign_indicator",
        )
        self.assertEqual(response.status_code, 403, response.text)
        after_data, _, after_task = self.task_record(task_id)
        self.assertEqual(MODULE.to_serializable(after_task), before_task)
        self.assertEqual(MODULE.to_serializable(after_data.audit_events), before_audits)

    def test_inactive_routing_identities_are_rejected_without_mutation(self):
        def task_and_audit_counts():
            current = MODULE.load_data_from_path()
            return (
                sum(len(activity.tasks) for ops in current.ops_by_project.values() for activity in ops.activities),
                len(current.audit_events),
            )

        data = MODULE.load_data_from_path()
        aline = MODULE.find_user_by_username(data, "aline.duarte")
        aline.is_active = False
        aline.status = "suspended"
        MODULE.save_data_to_path(data)
        before = task_and_audit_counts()
        rejected = self.create_task("Inactive assignee")
        self.assertEqual(rejected.status_code, 400, rejected.text)
        self.assertEqual(task_and_audit_counts(), before)

        data = MODULE.load_data_from_path()
        aline = MODULE.find_user_by_username(data, "aline.duarte")
        aline.is_active = True
        aline.status = "active"
        raimundo = MODULE.find_user_by_username(data, "raimundo.cumba")
        raimundo.is_active = False
        raimundo.status = "suspended"
        MODULE.save_data_to_path(data)
        before = task_and_audit_counts()
        rejected = self.create_task("Inactive validator")
        self.assertEqual(rejected.status_code, 400, rejected.text)
        self.assertEqual(task_and_audit_counts(), before)

    def test_routing_failures_and_direct_irrelevant_reviewers_are_atomic(self):
        direct = self.create_task(
            "Direct with irrelevant reviewer",
            assignee="teresa.mbanze",
            mode="direct_completion",
            validator_user_id=self.ids["raimundo.cumba"],
        )
        self.assertEqual(direct.status_code, 400, direct.text)

        task_id = self.create_task("Persisted invalid direct", assignee="teresa.mbanze", mode="direct_completion").json()["task"]["task_id"]
        data, _, task = self.task_record(task_id)
        task.validator_user_id = self.ids["raimundo.cumba"]
        MODULE.save_data_to_path(data)
        before_task = MODULE.to_serializable(task)
        before_audits = MODULE.to_serializable(data.audit_events)
        self.assertEqual(self.update(task_id, "teresa.mbanze", status="in_progress").status_code, 409)
        after_data, _, after_task = self.task_record(task_id)
        self.assertEqual(MODULE.to_serializable(after_task), before_task)
        self.assertEqual(MODULE.to_serializable(after_data.audit_events), before_audits)

        routing_id = self.create_task("Routing atomicity", mode="validation").json()["task"]["task_id"]
        self.assertEqual(self.update(routing_id, "aline.duarte", status="in_progress").status_code, 200)
        data, _, routing_task = self.task_record(routing_id)
        before_task = MODULE.to_serializable(routing_task)
        before_audits = MODULE.to_serializable(data.audit_events)
        denied = self.client.patch(
            f"/v1/demo/tasks/{routing_id}/routing",
            headers=self.headers("teresa.mbanze"),
            json={
                "assignee_user_id": self.ids["teresa.mbanze"],
                "assignee_username": "teresa.mbanze",
                "review_mode": "direct_completion",
                "evidence_required": False,
            },
        )
        self.assertEqual(denied.status_code, 409, denied.text)
        after_data, _, after_task = self.task_record(routing_id)
        self.assertEqual(MODULE.to_serializable(after_task), before_task)
        self.assertEqual(MODULE.to_serializable(after_data.audit_events), before_audits)

    def test_escalated_task_completes_through_original_routing(self):
        task_id = self.start("Escalated routing sequence")
        _, _, before = self.task_record(task_id)
        routing = (before.assignee_user_id, before.review_mode, before.validator_user_id, before.approver_user_id)
        escalated = self.update(task_id, "aline.duarte", escalate=True)
        self.assertEqual(escalated.status_code, 200, escalated.text)
        submitted = self.update(task_id, "aline.duarte", complete_execution=True)
        self.assertEqual((submitted.status_code, submitted.json()["task"]["review_stage"]), (200, "validation"))
        validated = self.review(task_id, "raimundo.cumba", "validated")
        self.assertEqual((validated.status_code, validated.json()["task"]["review_stage"]), (200, "approval"))
        approved = self.review(task_id, "teresa.mbanze", "approved")
        self.assertEqual((approved.status_code, approved.json()["task"]["status"]), (200, "completed"))
        _, _, after = self.task_record(task_id)
        self.assertEqual((after.assignee_user_id, after.review_mode, after.validator_user_id, after.approver_user_id), routing)
    def test_model_and_alias_verification_contracts(self):
        raw = MODULE.to_serializable(MODULE.load_data_from_path())
        legacy_task = raw["ops_by_project"][self.project_id]["activities"][0]["tasks"][0]
        for field_name in (
            "assignee_user_id",
            "review_mode",
            "validator_user_id",
            "approver_user_id",
            "evidence_required",
            "review_stage",
        ):
            legacy_task.pop(field_name, None)
        before_raw = copy.deepcopy(raw)
        hydrated = MODULE.from_serializable(raw)
        self.assertEqual(raw, before_raw)
        hydrated_task = hydrated.ops_by_project[self.project_id].activities[0].tasks[0]
        self.assertEqual(
            (
                hydrated_task.assignee_user_id,
                hydrated_task.review_mode,
                hydrated_task.validator_user_id,
                hydrated_task.approver_user_id,
                hydrated_task.evidence_required,
                hydrated_task.review_stage,
            ),
            ("", "", "", "", False, ""),
        )

        before_data = MODULE.load_data_from_path()
        before_counts = (
            sum(len(activity.tasks) for ops in before_data.ops_by_project.values() for activity in ops.activities),
            len(before_data.audit_events),
        )
        unknown = self.create_task("Unknown review mode", mode="unknown_mode")
        self.assertEqual(unknown.status_code, 400, unknown.text)
        after_data = MODULE.load_data_from_path()
        self.assertEqual(
            (
                sum(len(activity.tasks) for ops in after_data.ops_by_project.values() for activity in ops.activities),
                len(after_data.audit_events),
            ),
            before_counts,
        )

        direct_id = self.start("Direct alias rejection", assignee="teresa.mbanze", mode="direct_completion")
        data, _, direct_task = self.task_record(direct_id)
        before_task = MODULE.to_serializable(direct_task)
        before_audits = MODULE.to_serializable(data.audit_events)
        rejected = self.update(direct_id, "teresa.mbanze", submit_for_validation=True)
        self.assertEqual(rejected.status_code, 409, rejected.text)
        after_data, _, after_task = self.task_record(direct_id)
        self.assertEqual(MODULE.to_serializable(after_task), before_task)
        self.assertEqual(MODULE.to_serializable(after_data.audit_events), before_audits)

        routing_id = self.create_task("Routing audit", mode="validation").json()["task"]["task_id"]
        changed = self.client.patch(
            f"/v1/demo/tasks/{routing_id}/routing",
            headers=self.headers("teresa.mbanze"),
            json={
                "assignee_user_id": self.ids["teresa.mbanze"],
                "assignee_username": "teresa.mbanze",
                "review_mode": "direct_completion",
                "evidence_required": False,
            },
        )
        self.assertEqual(changed.status_code, 200, changed.text)
        data = MODULE.load_data_from_path()
        event = next(
            event for event in data.audit_events
            if event.target_id == routing_id and event.action == "demo.task.routing_updated"
        )
        self.assertEqual(event.details["assignee_user_id"], self.ids["teresa.mbanze"])
        self.assertEqual(event.details["review_mode"], "direct_completion")
    def test_invalid_persisted_review_stage_fails_closed(self):
        task_id = self.create_task("Invalid review stage").json()["task"]["task_id"]
        data, _, task = self.task_record(task_id)
        task.review_stage = "unknown_stage"
        MODULE.save_data_to_path(data)
        before_task = MODULE.to_serializable(task)
        before_audits = MODULE.to_serializable(data.audit_events)
        denied = self.update(task_id, "aline.duarte", status="in_progress")
        self.assertEqual(denied.status_code, 409, denied.text)
        after_data, _, after_task = self.task_record(task_id)
        self.assertEqual(MODULE.to_serializable(after_task), before_task)
        self.assertEqual(MODULE.to_serializable(after_data.audit_events), before_audits)

if __name__ == "__main__":
    unittest.main()