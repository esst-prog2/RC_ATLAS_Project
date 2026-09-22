import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from demo_smoke_tests import (
    MODULE,
    TestClient,
    build_demo_service,
    issue_token_for_user,
    patched_env,
)


class CourseMvpWorkflowTests(unittest.TestCase):
    project_id = "proj_resilience"

    def setUp(self):
        if TestClient is None or MODULE.app is None:
            self.skipTest("FastAPI TestClient is unavailable.")
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_path = str(Path(self.temp_dir.name) / "course_mvp.json")
        self.environment = patched_env(
            LOGITRACK_STORAGE_BACKEND="json",
            LOGITRACK_DATA_PATH=self.data_path,
            LOGITRACK_SQLITE_PATH=None,
            LOGITRACK_ENABLE_RELATIONAL_MIRROR="false",
            LOGITRACK_ENABLE_REPOSITORY_DOMAINS="false",
            LOGITRACK_API_KEY=None,
        )
        self.environment.__enter__()
        self.service = build_demo_service()
        self.service.seed_workspace(None, None)
        data = MODULE.load_data_from_path()
        self.tokens = {}
        for username in (
            "teresa.mbanze",
            "aline.duarte",
            "raimundo.cumba",
            "executive.director",
        ):
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

    def create_task(self, title="Finalize Buzi monitoring report", **overrides):
        payload = {
            "project_id": self.project_id,
            "title": title,
            "description": "Complete the fictional monitoring report and attach the evidence note.",
            "assignee_username": "aline.duarte",
            "assignee_name": "Incorrect client display value",
            "owner": "Incorrect client owner value",
            "due_date": (date.today() + timedelta(days=21)).isoformat(),
            "priority": "high",
            "category": "reporting",
            "status": "completed",
        }
        payload.update(overrides)
        return self.client.post(
            "/v1/demo/tasks",
            headers=self.headers("teresa.mbanze"),
            json=payload,
        )

    def persisted_task(self, task_id):
        data = MODULE.load_data_from_path()
        for ops in data.ops_by_project.values():
            for activity in ops.activities:
                for task in activity.tasks:
                    if task.id == task_id:
                        return data, task
        self.fail(f"Task '{task_id}' was not persisted.")

    def task_row(self, task_id, username="teresa.mbanze"):
        response = self.client.get(
            f"/v1/demo/projects/{self.project_id}/workplan",
            headers=self.headers(username),
        )
        self.assertEqual(response.status_code, 200, response.text)
        return next(item for item in response.json()["tasks"] if item["task_id"] == task_id)

    def submit_new_task(self, title):
        created = self.create_task(title=title)
        self.assertEqual(created.status_code, 200, created.text)
        task_id = created.json()["task"]["task_id"]
        started = self.client.post(
            f"/v1/demo/tasks/{task_id}/update",
            headers=self.headers("aline.duarte"),
            json={"status": "in_progress", "progress_pct": 25},
        )
        self.assertEqual(started.status_code, 200, started.text)
        submitted = self.client.post(
            f"/v1/demo/tasks/{task_id}/update",
            headers=self.headers("aline.duarte"),
            json={
                "progress_pct": 90,
                "comment": "Field delivery is ready for review.",
                "evidence_note": "Fictional signed monitoring checklist",
                "submit_for_validation": True,
            },
        )
        self.assertEqual(submitted.status_code, 200, submitted.text)
        return task_id

    def test_workplan_exposes_only_eligible_project_assignees(self):
        response = self.client.get(
            f"/v1/demo/projects/{self.project_id}/workplan",
            headers=self.headers("teresa.mbanze"),
        )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        usernames = {item["username"] for item in payload["eligible_assignees"]}
        self.assertEqual(
            usernames,
            {"teresa.mbanze", "raimundo.cumba", "aline.duarte", "executive.director"},
        )
        self.assertNotIn("org.admin", usernames)
        self.assertIn("tasks", payload)
        self.assertIn("task_board", payload)

    def test_canonical_assignment_ignores_client_display_identity(self):
        response = self.create_task()
        self.assertEqual(response.status_code, 200, response.text)
        task = response.json()["task"]
        self.assertEqual(task["assignee_username"], "aline.duarte")
        self.assertEqual(task["assignee_name"], "Aline Duarte")
        self.assertEqual(task["owner"], "Aline Duarte")
        self.assertEqual(task["status"], "not_started")

    def test_ineligible_assignees_are_rejected_without_success_side_effects(self):
        def counts():
            data = MODULE.load_data_from_path()
            tasks = sum(
                len(activity.tasks)
                for ops in data.ops_by_project.values()
                for activity in ops.activities
            )
            assignments = sum(
                1 for event in data.audit_events
                if event.action == "demo.task.created"
            )
            return tasks, assignments

        baseline = counts()
        unknown = self.create_task(title="Unknown assignee", assignee_username="missing.user")
        self.assertEqual(unknown.status_code, 400, unknown.text)
        self.assertEqual(counts(), baseline)

        non_member = self.create_task(title="Non-member assignee", assignee_username="org.admin")
        self.assertEqual(non_member.status_code, 400, non_member.text)
        self.assertEqual(counts(), baseline)

        data = MODULE.load_data_from_path()
        aline = MODULE.find_user_by_username(data, "aline.duarte")
        aline.is_active = False
        MODULE.save_data_to_path(data)
        inactive = self.create_task(title="Inactive assignee")
        self.assertEqual(inactive.status_code, 400, inactive.text)
        self.assertEqual(counts(), baseline)

        data = MODULE.load_data_from_path()
        aline = MODULE.find_user_by_username(data, "aline.duarte")
        aline.is_active = True
        aline.organization_id = "org_other"
        MODULE.save_data_to_path(data)
        cross_org = self.create_task(title="Cross-organization assignee")
        self.assertEqual(cross_org.status_code, 400, cross_org.text)
        self.assertEqual(counts(), baseline)

    def test_field_execution_scope_and_manager_updates_are_enforced(self):
        created = self.create_task(title="Field scope contract")
        self.assertEqual(created.status_code, 200, created.text)
        task_id = created.json()["task"]["task_id"]

        manager_update = self.client.post(
            f"/v1/demo/tasks/{task_id}/update",
            headers=self.headers("teresa.mbanze"),
            json={"priority": "critical", "due_date": (date.today() + timedelta(days=30)).isoformat()},
        )
        self.assertEqual(manager_update.status_code, 200, manager_update.text)
        self.assertEqual(manager_update.json()["task"]["priority"], "critical")

        before_data, before_task = self.persisted_task(task_id)
        before_task_payload = MODULE.to_serializable(before_task)
        before_audits = len(before_data.audit_events)
        prohibited = self.client.post(
            f"/v1/demo/tasks/{task_id}/update",
            headers=self.headers("aline.duarte"),
            json={
                "assignee_username": "teresa.mbanze",
                "due_date": (date.today() + timedelta(days=1)).isoformat(),
                "priority": "low",
                "category": "coordination",
                "linked_indicator_id": "ind_res_income",
                "project_id": "proj_health",
                "organization_id": "org_other",
                "status": "completed",
            },
        )
        self.assertEqual(prohibited.status_code, 403, prohibited.text)
        after_data, after_task = self.persisted_task(task_id)
        self.assertEqual(MODULE.to_serializable(after_task), before_task_payload)
        self.assertEqual(len(after_data.audit_events), before_audits)

        started = self.client.post(
            f"/v1/demo/tasks/{task_id}/update",
            headers=self.headers("aline.duarte"),
            json={"status": "in_progress", "progress_pct": 25},
        )
        self.assertEqual(started.status_code, 200, started.text)
        updated = self.client.post(
            f"/v1/demo/tasks/{task_id}/update",
            headers=self.headers("aline.duarte"),
            json={
                "progress_pct": 65,
                "comment": "Implementation update",
                "evidence_note": "Fictional attendance evidence",
            },
        )
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(updated.json()["task"]["progress_pct"], 65)

        wrong_owner = self.client.post(
            "/v1/demo/tasks/task_res_2/update",
            headers=self.headers("aline.duarte"),
            json={"progress_pct": 60},
        )
        self.assertEqual(wrong_owner.status_code, 403, wrong_owner.text)

        submitted = self.client.post(
            f"/v1/demo/tasks/{task_id}/update",
            headers=self.headers("aline.duarte"),
            json={"submit_for_validation": True},
        )
        self.assertEqual(submitted.status_code, 200, submitted.text)
        blocked_after_submit = self.client.post(
            f"/v1/demo/tasks/{task_id}/update",
            headers=self.headers("aline.duarte"),
            json={"progress_pct": 75},
        )
        self.assertEqual(blocked_after_submit.status_code, 409, blocked_after_submit.text)

        executive_update = self.client.post(
            f"/v1/demo/tasks/{task_id}/update",
            headers=self.headers("executive.director"),
            json={"progress_pct": 80},
        )
        self.assertEqual(executive_update.status_code, 403, executive_update.text)

    def test_meal_return_and_approval_guards_are_atomic(self):
        unsubmitted = self.create_task(title="Out-of-order MEAL review")
        self.assertEqual(unsubmitted.status_code, 200, unsubmitted.text)
        unsubmitted_id = unsubmitted.json()["task"]["task_id"]
        early_validation = self.client.post(
            f"/v1/demo/tasks/{unsubmitted_id}/validate",
            headers=self.headers("raimundo.cumba"),
            json={"decision": "validated"},
        )
        self.assertEqual(early_validation.status_code, 409, early_validation.text)

        task_id = self.submit_new_task("Return-path workflow")
        before_data, before_task = self.persisted_task(task_id)
        before_payload = MODULE.to_serializable(before_task)
        before_audits = len(before_data.audit_events)

        early_approval = self.client.post(
            f"/v1/demo/tasks/{task_id}/validate",
            headers=self.headers("teresa.mbanze"),
            json={"decision": "approved"},
        )
        self.assertEqual(early_approval.status_code, 409, early_approval.text)
        after_data, after_task = self.persisted_task(task_id)
        self.assertEqual(MODULE.to_serializable(after_task), before_payload)
        self.assertEqual(len(after_data.audit_events), before_audits)

        returned = self.client.post(
            f"/v1/demo/tasks/{task_id}/validate",
            headers=self.headers("raimundo.cumba"),
            json={"decision": "rejected", "comment": "Please clarify the evidence reference."},
        )
        self.assertEqual(returned.status_code, 200, returned.text)
        returned_task = returned.json()["task"]
        self.assertEqual(returned_task["status"], "in_progress")
        self.assertEqual(returned_task["assignee_username"], "aline.duarte")
        self.assertFalse(returned_task["validated_at"])
        returned_data, returned_record = self.persisted_task(task_id)
        self.assertEqual(returned_record.activity_log[-1]["event_type"], "returned_for_rework")
        returned_audit = next(
            item for item in reversed(returned_data.audit_events)
            if item.target_id == task_id and item.action == "demo.task.returned"
        )
        self.assertEqual(returned_audit.actor_username, "raimundo.cumba")

        resumed = self.client.post(
            f"/v1/demo/tasks/{task_id}/update",
            headers=self.headers("aline.duarte"),
            json={"progress_pct": 92, "comment": "Evidence reference clarified."},
        )
        self.assertEqual(resumed.status_code, 200, resumed.text)
        resubmitted = self.client.post(
            f"/v1/demo/tasks/{task_id}/update",
            headers=self.headers("aline.duarte"),
            json={"submit_for_validation": True},
        )
        self.assertEqual(resubmitted.status_code, 200, resubmitted.text)

        validated = self.client.post(
            f"/v1/demo/tasks/{task_id}/validate",
            headers=self.headers("raimundo.cumba"),
            json={"decision": "validated"},
        )
        self.assertEqual(validated.status_code, 200, validated.text)
        validated_task = validated.json()["task"]
        self.assertEqual(validated_task["status"], "pending_validation")
        self.assertTrue(validated_task["validated_at"])

        validated_data, validated_record = self.persisted_task(task_id)
        validated_payload = MODULE.to_serializable(validated_record)
        validated_audits = len(validated_data.audit_events)
        repeated = self.client.post(
            f"/v1/demo/tasks/{task_id}/validate",
            headers=self.headers("raimundo.cumba"),
            json={"decision": "validated"},
        )
        self.assertEqual(repeated.status_code, 409, repeated.text)
        late_return = self.client.post(
            f"/v1/demo/tasks/{task_id}/validate",
            headers=self.headers("raimundo.cumba"),
            json={"decision": "rejected"},
        )
        self.assertEqual(late_return.status_code, 409, late_return.text)
        final_data, final_record = self.persisted_task(task_id)
        self.assertEqual(MODULE.to_serializable(final_record), validated_payload)
        self.assertEqual(len(final_data.audit_events), validated_audits)

    def test_exact_course_workflow_persists_across_role_handoffs(self):
        created = self.create_task()
        self.assertEqual(created.status_code, 200, created.text)
        task_id = created.json()["task"]["task_id"]
        self.assertEqual(created.json()["task"]["assignee_username"], "aline.duarte")

        started = self.client.post(
            f"/v1/demo/tasks/{task_id}/update",
            headers=self.headers("aline.duarte"),
            json={"status": "in_progress", "progress_pct": 30},
        )
        self.assertEqual(started.status_code, 200, started.text)
        updated = self.client.post(
            f"/v1/demo/tasks/{task_id}/update",
            headers=self.headers("aline.duarte"),
            json={
                "progress_pct": 88,
                "comment": "Buzi report narrative completed.",
                "evidence_note": "Fictional Buzi monitoring evidence pack",
            },
        )
        self.assertEqual(updated.status_code, 200, updated.text)
        submitted = self.client.post(
            f"/v1/demo/tasks/{task_id}/update",
            headers=self.headers("aline.duarte"),
            json={"submit_for_validation": True},
        )
        self.assertEqual(submitted.status_code, 200, submitted.text)
        self.assertEqual(submitted.json()["task"]["status"], "pending_validation")
        self.assertTrue(submitted.json()["task"]["submitted_at"])

        meal_view = self.task_row(task_id, "raimundo.cumba")
        self.assertFalse(meal_view["validated_at"])
        validated = self.client.post(
            f"/v1/demo/tasks/{task_id}/validate",
            headers=self.headers("raimundo.cumba"),
            json={"decision": "validated", "comment": "MEAL evidence review passed."},
        )
        self.assertEqual(validated.status_code, 200, validated.text)
        self.assertEqual(validated.json()["task"]["status"], "pending_validation")
        self.assertTrue(validated.json()["task"]["validated_at"])

        manager_view = self.task_row(task_id, "teresa.mbanze")
        self.assertEqual(manager_view["status"], "pending_validation")
        self.assertTrue(manager_view["validated_at"])
        self.assertFalse(manager_view["approved_at"])

        approved = self.client.post(
            f"/v1/demo/tasks/{task_id}/validate",
            headers=self.headers("teresa.mbanze"),
            json={"decision": "approved", "comment": "Final Programme Manager approval."},
        )
        self.assertEqual(approved.status_code, 200, approved.text)
        self.assertEqual(approved.json()["task"]["status"], "completed")
        self.assertEqual(approved.json()["task"]["progress_pct"], 100)

        completed_data, completed_task = self.persisted_task(task_id)
        completed_payload = MODULE.to_serializable(completed_task)
        completed_audits = len(completed_data.audit_events)
        blocked_completed_update = self.client.post(
            f"/v1/demo/tasks/{task_id}/update",
            headers=self.headers("aline.duarte"),
            json={"progress_pct": 99},
        )
        self.assertEqual(blocked_completed_update.status_code, 409, blocked_completed_update.text)

        reloaded_data, reloaded_task = self.persisted_task(task_id)
        self.assertEqual(MODULE.to_serializable(reloaded_task), completed_payload)
        self.assertEqual(len(reloaded_data.audit_events), completed_audits)
        self.assertEqual(reloaded_task.assignee_username, "aline.duarte")
        self.assertEqual(reloaded_task.assignee_name, "Aline Duarte")
        self.assertEqual(reloaded_task.due_date.isoformat(), (date.today() + timedelta(days=21)).isoformat())
        self.assertEqual(reloaded_task.status, "completed")
        self.assertEqual(reloaded_task.progress_pct, 100)
        self.assertTrue(reloaded_task.submitted_at)
        self.assertTrue(reloaded_task.validated_at)
        self.assertTrue(reloaded_task.approved_at)
        event_types = [item["event_type"] for item in reloaded_task.activity_log]
        self.assertEqual(
            event_types,
            [
                "task_assigned",
                "task_started",
                "task_updated",
                "submitted_for_validation",
                "validated",
                "approved",
            ],
        )
        audit_events = [
            item for item in reloaded_data.audit_events
            if item.target_id == task_id
        ]
        self.assertEqual(
            [item.action for item in audit_events],
            [
                "demo.task.created",
                "demo.task.started",
                "demo.task.updated",
                "demo.task.submitted",
                "demo.task.validated",
                "demo.task.approved",
            ],
        )
        self.assertEqual(
            [item.actor_username for item in audit_events],
            [
                "teresa.mbanze",
                "aline.duarte",
                "aline.duarte",
                "aline.duarte",
                "raimundo.cumba",
                "teresa.mbanze",
            ],
        )
        self.assertTrue(all(item.occurred_at for item in audit_events))
        self.assertTrue(all(item.details.get("project_id") == self.project_id for item in audit_events))
        self.assertTrue(all(item.details.get("task_id") == task_id for item in audit_events))
        reloaded_http_task = self.task_row(task_id)
        self.assertEqual(
            [item["event_type"] for item in reloaded_http_task["activity_log"]],
            event_types,
        )
        self.assertIn(
            "Fictional Buzi monitoring evidence pack",
            reloaded_http_task["evidence_placeholders"],
        )


if __name__ == "__main__":
    unittest.main()
