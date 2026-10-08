import copy
import tempfile
import unittest
from pathlib import Path

from demo_smoke_tests import MODULE, TestClient, issue_token_for_user, patched_env


class WorkplanProjectMembersContractTests(unittest.TestCase):
    project_id = "proj_resilience"

    def setUp(self):
        if TestClient is None or MODULE.app is None:
            self.skipTest("FastAPI TestClient is unavailable.")
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_path = str(Path(self.temp_dir.name) / "workplan_members.json")
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
        _, self.token = issue_token_for_user(data, "teresa.mbanze")
        MODULE.save_data_to_path(data)
        self.client = TestClient(MODULE.app)

    def tearDown(self):
        if hasattr(self, "client"):
            self.client.close()
        if hasattr(self, "environment"):
            self.environment.__exit__(None, None, None)
        if hasattr(self, "temp_dir"):
            self.temp_dir.cleanup()

    def workplan(self):
        response = self.client.get(
            f"/v1/demo/projects/{self.project_id}/workplan",
            headers={"X-Auth-Token": self.token},
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_project_members_are_scoped_minimal_and_additive(self):
        payload = self.workplan()
        self.assertIn("eligible_assignees", payload)
        self.assertIn("project_members", payload)
        self.assertTrue(payload["project_members"])

        member_ids = {member["user_id"] for member in payload["project_members"]}
        self.assertTrue({"user_demo_2", "user_demo_3", "user_demo_4"}.issubset(member_ids))
        self.assertEqual(
            {key for member in payload["project_members"] for key in member},
            {"user_id", "display_name", "permissions"},
        )
        for member in payload["project_members"]:
            self.assertTrue(member["user_id"])
            self.assertTrue(member["display_name"])
            self.assertIsInstance(member["permissions"], list)

    def test_project_members_exclude_non_member_foreign_and_inactive_users(self):
        data = MODULE.load_data_from_path()
        project = next(item for item in data.projects if item.id == self.project_id)
        member_template = next(item for item in data.users if item.username == "aline.duarte")

        non_member = copy.deepcopy(member_template)
        non_member.id = "user_non_member"
        non_member.username = "not.on.project"
        non_member.full_name = "Not On Project"
        non_member.permissions = ["VALIDATE_EVIDENCE"]

        foreign = copy.deepcopy(member_template)
        foreign.id = "user_foreign"
        foreign.username = "foreign.member"
        foreign.full_name = "Foreign Member"
        foreign.organization_id = "org_foreign"
        foreign.permissions = ["APPROVE_TASKS"]

        inactive = copy.deepcopy(member_template)
        inactive.id = "user_inactive"
        inactive.username = "inactive.member"
        inactive.full_name = "Inactive Member"
        inactive.is_active = False
        inactive.status = "suspended"
        inactive.permissions = ["VALIDATE_EVIDENCE"]

        data.users.extend([non_member, foreign, inactive])
        for user in (foreign, inactive):
            assignment = copy.deepcopy(project.team_assignments[0])
            assignment.id = f"assignment_{user.id}"
            assignment.user_id = user.id
            project.team_assignments.append(assignment)
        MODULE.save_data_to_path(data)

        member_ids = {member["user_id"] for member in self.workplan()["project_members"]}
        self.assertNotIn(non_member.id, member_ids)
        self.assertNotIn(foreign.id, member_ids)
        self.assertNotIn(inactive.id, member_ids)

    def test_project_members_expose_reviewers_without_execution_capability(self):
        data = MODULE.load_data_from_path()
        validator = MODULE.find_user_by_username(data, "raimundo.cumba")
        approver = MODULE.find_user_by_username(data, "teresa.mbanze")
        validator.permissions = ["VALIDATE_EVIDENCE"]
        approver.permissions = ["APPROVE_TASKS", "VIEW_WORKPLAN", "VIEW_EXECUTIVE_SNAPSHOT"]
        MODULE.save_data_to_path(data)

        payload = self.workplan()
        members = {member["user_id"]: member for member in payload["project_members"]}
        assignee_ids = {member["user_id"] for member in payload["eligible_assignees"]}

        self.assertIn("user_demo_3", members)
        self.assertIn("VALIDATE_EVIDENCE", members["user_demo_3"]["permissions"])
        self.assertNotIn("user_demo_3", assignee_ids)
        self.assertIn("user_demo_2", members)
        self.assertIn("APPROVE_TASKS", members["user_demo_2"]["permissions"])
        self.assertNotIn("user_demo_2", assignee_ids)


if __name__ == "__main__":
    unittest.main()
