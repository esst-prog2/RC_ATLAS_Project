import os
import tempfile
import unittest
from datetime import date
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from fastapi.testclient import TestClient

from services.demo_seed import build_demo_seed_bundle
from shared import ResultNode


MODULE_PATH = Path(__file__).with_name("LogiTrackRC v4.4.py")
SPEC = spec_from_file_location("logitrack_rc_v4_4_logframe_api_tests", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load module from {MODULE_PATH}")
MODULE = module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class LogicalFrameworkApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_path = str(Path(self.temp_dir.name) / "logical_framework_api.json")
        self.previous_env = {
            name: os.environ.get(name)
            for name in (
                "LOGITRACK_STORAGE_BACKEND",
                "LOGITRACK_DATA_PATH",
                "LOGITRACK_SQLITE_PATH",
                "LOGITRACK_ENABLE_RELATIONAL_MIRROR",
                "LOGITRACK_ENABLE_REPOSITORY_DOMAINS",
                "LOGITRACK_API_KEY",
            )
        }
        os.environ["LOGITRACK_STORAGE_BACKEND"] = "json"
        os.environ["LOGITRACK_DATA_PATH"] = self.data_path
        os.environ.pop("LOGITRACK_SQLITE_PATH", None)
        os.environ["LOGITRACK_ENABLE_RELATIONAL_MIRROR"] = "false"
        os.environ["LOGITRACK_ENABLE_REPOSITORY_DOMAINS"] = "false"
        os.environ.pop("LOGITRACK_API_KEY", None)

        bundle = build_demo_seed_bundle(MODULE.build_password_hash)
        data = MODULE.from_serializable(bundle.payload)
        data.organizations.append(
            MODULE.OrganizationAccount(
                id="org_other",
                organization_name="Other Fictional Organization",
                created_at=MODULE.now_iso_utc(),
                updated_at=MODULE.now_iso_utc(),
            )
        )
        data.projects.append(
            MODULE.Project(
                id="proj_other",
                name="Other Organization Project",
                objective="Tenant isolation fixture",
                organization_id="org_other",
                project_code="OTHER-001",
                start_date=date(2026, 1, 1),
                end_date=date(2026, 12, 31),
                status="active",
                indicators=[
                    MODULE.Indicator(
                        id="ind_other",
                        name="Other organization indicator",
                        unit="people",
                        frequency="monthly",
                        direction="up",
                        level="outcome",
                        target=100,
                        baseline=0,
                        organization_id="org_other",
                        project_id="proj_other",
                    )
                ],
            )
        )
        data.users.append(
            MODULE.UserAccount(
                id="user_other_manager",
                username="other.manager",
                organization_id="org_other",
                full_name="Other Manager",
                email="other.manager@example.test",
                role="programme_manager",
                status="active",
                is_active=True,
                created_at=MODULE.now_iso_utc(),
                updated_at=MODULE.now_iso_utc(),
            )
        )
        self.tokens = {}
        for user in data.users:
            token = f"test-token-{user.username}"
            user.api_token_hash = MODULE.hash_with_sha256(token)
            self.tokens[user.username] = token
        MODULE.save_data_to_path(data)
        self.client = TestClient(MODULE.app)
        self.project_id = "proj_resilience"
        self.second_project_id = "proj_health"
        self.indicator_id = "ind_res_households"

    def tearDown(self):
        self.client.close()
        for name, value in self.previous_env.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        self.temp_dir.cleanup()

    def headers(self, username):
        return {"X-Auth-Token": self.tokens[username]}

    def load(self):
        return MODULE.load_data_from_path(self.data_path)

    def save(self, data):
        MODULE.save_data_to_path(data)

    def create_result(
        self,
        result_type,
        title,
        *,
        parent_id="",
        project_id=None,
        username="teresa.mbanze",
        expected_status=200,
    ):
        response = self.client.post(
            f"/v1/projects/{project_id or self.project_id}/logical-framework/results",
            headers=self.headers(username),
            json={
                "result_type": result_type,
                "title": title,
                "parent_id": parent_id,
            },
        )
        self.assertEqual(response.status_code, expected_status, response.text)
        return response

    def create_hierarchy(self, username="teresa.mbanze", project_id=None):
        target_project = project_id or self.project_id
        goal = self.create_result(
            "goal", "Improved resilience", project_id=target_project, username=username
        ).json()["result"]
        outcome = self.create_result(
            "outcome",
            "Households adopt resilient practices",
            parent_id=goal["id"],
            project_id=target_project,
            username=username,
        ).json()["result"]
        output = self.create_result(
            "output",
            "Community training delivered",
            parent_id=outcome["id"],
            project_id=target_project,
            username=username,
        ).json()["result"]
        return goal, outcome, output

    def audit_actions(self):
        return [event.action for event in self.load().audit_events]

    def test_permission_templates_match_role_separation(self):
        self.assertIn("MANAGE_LOGICAL_FRAMEWORK", MODULE.role_permissions("organization_admin"))
        self.assertIn("MANAGE_LOGICAL_FRAMEWORK", MODULE.role_permissions("programme_manager"))
        self.assertNotIn("MANAGE_LOGICAL_FRAMEWORK", MODULE.role_permissions("meal_officer"))
        self.assertIn("LINK_RESULT_INDICATORS", MODULE.role_permissions("meal_officer"))
        self.assertNotIn("LINK_RESULT_INDICATORS", MODULE.role_permissions("field_coordinator"))
        self.assertIn("VIEW_LOGICAL_FRAMEWORK", MODULE.role_permissions("executive_viewer"))

    def test_read_requires_authentication(self):
        response = self.client.get(
            f"/v1/projects/{self.project_id}/logical-framework"
        )
        self.assertEqual(response.status_code, 401)

    def test_every_demo_role_can_read_an_organization_project(self):
        for username in (
            "org.admin",
            "teresa.mbanze",
            "raimundo.cumba",
            "aline.duarte",
            "executive.director",
        ):
            with self.subTest(username=username):
                response = self.client.get(
                    f"/v1/projects/{self.project_id}/logical-framework",
                    headers=self.headers(username),
                )
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json()["project_id"], self.project_id)

    def test_manager_creates_nested_hierarchy_and_read_returns_unassigned_indicators(self):
        goal, outcome, output = self.create_hierarchy()
        response = self.client.get(
            f"/v1/projects/{self.project_id}/logical-framework",
            headers=self.headers("teresa.mbanze"),
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["organization_id"], "org_blue_delta")
        self.assertEqual(payload["goals"][0]["id"], goal["id"])
        self.assertEqual(payload["goals"][0]["outcomes"][0]["id"], outcome["id"])
        self.assertEqual(
            payload["goals"][0]["outcomes"][0]["outputs"][0]["id"], output["id"]
        )
        self.assertIn(
            self.indicator_id,
            {indicator["id"] for indicator in payload["unassigned_indicators"]},
        )

    def test_organization_admin_can_create_structure(self):
        response = self.create_result(
            "goal", "Admin-created Goal", username="org.admin"
        )
        self.assertEqual(response.json()["result"]["result_type"], "goal")

    def test_invalid_hierarchy_and_unknown_parent_are_rejected(self):
        goal = self.create_result("goal", "Goal").json()["result"]
        invalid_parent = self.create_result(
            "output",
            "Output cannot sit under Goal",
            parent_id=goal["id"],
            expected_status=400,
        )
        self.assertIn("Outcome parent", invalid_parent.json()["detail"])
        unknown_parent = self.create_result(
            "outcome",
            "Unknown parent Outcome",
            parent_id="missing_goal",
            expected_status=404,
        )
        self.assertEqual(
            unknown_parent.json()["detail"], "Logical Framework resource not found."
        )

    def test_cross_project_and_cross_organization_parenting_are_hidden(self):
        goal = self.create_result("goal", "Project A Goal").json()["result"]
        cross_project = self.create_result(
            "outcome",
            "Cross-project Outcome",
            parent_id=goal["id"],
            project_id=self.second_project_id,
            expected_status=404,
        )
        self.assertEqual(
            cross_project.json()["detail"], "Logical Framework resource not found."
        )

        data = self.load()
        data.logical_framework_results.append(
            ResultNode(
                id="goal_other_org",
                organization_id="org_other",
                project_id="proj_other",
                result_type="goal",
                title="Other organization Goal",
            )
        )
        self.save(data)
        cross_org = self.create_result(
            "outcome",
            "Cross-organization Outcome",
            parent_id="goal_other_org",
            expected_status=404,
        )
        self.assertEqual(cross_org.json()["detail"], "Logical Framework resource not found.")

    def test_result_update_rejects_identity_parent_and_order_mutation(self):
        goal = self.create_result("goal", "Original title").json()["result"]
        endpoint = (
            f"/v1/projects/{self.project_id}/logical-framework/results/{goal['id']}"
        )
        updated = self.client.patch(
            endpoint,
            headers=self.headers("teresa.mbanze"),
            json={"title": "Updated title", "description": "Updated safely"},
        )
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(updated.json()["result"]["title"], "Updated title")
        for payload in (
            {"parent_id": "another"},
            {"organization_id": "org_other"},
            {"project_id": self.second_project_id},
            {"result_type": "outcome"},
            {"display_order": 12},
        ):
            with self.subTest(payload=payload):
                rejected = self.client.patch(
                    endpoint,
                    headers=self.headers("teresa.mbanze"),
                    json=payload,
                )
                self.assertEqual(rejected.status_code, 400, rejected.text)

    def test_sibling_reorder_is_branch_scoped_and_complete(self):
        first = self.create_result("goal", "First").json()["result"]
        second = self.create_result("goal", "Second").json()["result"]
        response = self.client.post(
            f"/v1/projects/{self.project_id}/logical-framework/reorder",
            headers=self.headers("teresa.mbanze"),
            json={"ordered_result_ids": [second["id"], first["id"]]},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            [(item["id"], item["display_order"]) for item in response.json()["results"]],
            [(second["id"], 0), (first["id"], 1)],
        )
        incomplete = self.client.post(
            f"/v1/projects/{self.project_id}/logical-framework/reorder",
            headers=self.headers("teresa.mbanze"),
            json={"ordered_result_ids": [first["id"]]},
        )
        self.assertEqual(incomplete.status_code, 400)

    def test_archive_is_explicit_and_dependency_delete_is_protected(self):
        goal, outcome, _ = self.create_hierarchy()
        archive = self.client.post(
            f"/v1/projects/{self.project_id}/logical-framework/results/{outcome['id']}/archive",
            headers=self.headers("teresa.mbanze"),
        )
        self.assertEqual(archive.status_code, 200, archive.text)
        self.assertEqual(archive.json()["result"]["status"], "archived")
        blocked = self.client.delete(
            f"/v1/projects/{self.project_id}/logical-framework/results/{goal['id']}",
            headers=self.headers("teresa.mbanze"),
        )
        self.assertEqual(blocked.status_code, 409)
        self.assertIn("child results", blocked.json()["detail"])

    def test_leaf_result_can_be_deleted(self):
        goal = self.create_result("goal", "Disposable Goal").json()["result"]
        response = self.client.delete(
            f"/v1/projects/{self.project_id}/logical-framework/results/{goal['id']}",
            headers=self.headers("teresa.mbanze"),
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertNotIn(
            goal["id"], {node.id for node in self.load().logical_framework_results}
        )

    def test_field_executive_and_meal_cannot_mutate_structure(self):
        for username in ("aline.duarte", "executive.director", "raimundo.cumba"):
            with self.subTest(username=username):
                response = self.create_result(
                    "goal",
                    f"Forbidden for {username}",
                    username=username,
                    expected_status=403,
                )
                self.assertIn("Missing required permission", response.json()["detail"])

    def test_programme_manager_and_admin_can_mutate_structure(self):
        manager = self.create_result(
            "goal", "Manager Goal", username="teresa.mbanze"
        )
        admin = self.create_result("goal", "Admin Goal", username="org.admin")
        self.assertEqual(manager.status_code, 200)
        self.assertEqual(admin.status_code, 200)

    def test_meal_can_link_relink_and_unlink_but_field_cannot(self):
        goal, outcome, output = self.create_hierarchy()
        endpoint = (
            f"/v1/projects/{self.project_id}/logical-framework/indicators/"
            f"{self.indicator_id}/link"
        )
        linked = self.client.put(
            endpoint,
            headers=self.headers("raimundo.cumba"),
            json={"result_id": outcome["id"]},
        )
        self.assertEqual(linked.status_code, 200, linked.text)
        first_link_id = linked.json()["link"]["id"]
        relinked = self.client.put(
            endpoint,
            headers=self.headers("raimundo.cumba"),
            json={"result_id": output["id"]},
        )
        self.assertEqual(relinked.status_code, 200, relinked.text)
        self.assertEqual(relinked.json()["link"]["id"], first_link_id)
        self.assertEqual(relinked.json()["link"]["result_id"], output["id"])
        self.assertEqual(
            len(
                [
                    link
                    for link in self.load().indicator_result_links
                    if link.indicator_id == self.indicator_id
                ]
            ),
            1,
        )
        field_attempt = self.client.delete(
            endpoint, headers=self.headers("aline.duarte")
        )
        self.assertEqual(field_attempt.status_code, 403)
        unlinked = self.client.delete(
            endpoint, headers=self.headers("raimundo.cumba")
        )
        self.assertEqual(unlinked.status_code, 200, unlinked.text)
        self.assertEqual(self.load().indicator_result_links, [])

    def test_indicator_links_appear_in_nested_read_response(self):
        _, outcome, _ = self.create_hierarchy()
        self.client.put(
            f"/v1/projects/{self.project_id}/logical-framework/indicators/{self.indicator_id}/link",
            headers=self.headers("raimundo.cumba"),
            json={"result_id": outcome["id"]},
        )
        payload = self.client.get(
            f"/v1/projects/{self.project_id}/logical-framework",
            headers=self.headers("executive.director"),
        ).json()
        attached = payload["goals"][0]["outcomes"][0]["indicators"]
        self.assertEqual(attached[0]["id"], self.indicator_id)
        self.assertEqual(attached[0]["result_id"], outcome["id"])
        self.assertNotIn(
            self.indicator_id,
            {item["id"] for item in payload["unassigned_indicators"]},
        )

    def test_goal_indicator_link_is_rejected_and_not_audited(self):
        goal = self.create_result("goal", "Goal").json()["result"]
        before = self.audit_actions()
        response = self.client.put(
            f"/v1/projects/{self.project_id}/logical-framework/indicators/{self.indicator_id}/link",
            headers=self.headers("raimundo.cumba"),
            json={"result_id": goal["id"]},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Outcome or Output", response.json()["detail"])
        self.assertEqual(self.audit_actions(), before)

    def test_cross_project_and_cross_organization_indicator_links_are_hidden(self):
        _, outcome, _ = self.create_hierarchy()
        cross_project_indicator = self.client.put(
            f"/v1/projects/{self.project_id}/logical-framework/indicators/ind_health_coverage/link",
            headers=self.headers("raimundo.cumba"),
            json={"result_id": outcome["id"]},
        )
        self.assertEqual(cross_project_indicator.status_code, 404)

        _, second_outcome, _ = self.create_hierarchy(
            project_id=self.second_project_id
        )
        cross_project_result = self.client.put(
            f"/v1/projects/{self.project_id}/logical-framework/indicators/{self.indicator_id}/link",
            headers=self.headers("raimundo.cumba"),
            json={"result_id": second_outcome["id"]},
        )
        self.assertEqual(cross_project_result.status_code, 404)
        cross_org_indicator = self.client.put(
            f"/v1/projects/{self.project_id}/logical-framework/indicators/ind_other/link",
            headers=self.headers("raimundo.cumba"),
            json={"result_id": outcome["id"]},
        )
        self.assertEqual(cross_org_indicator.status_code, 404)

    def test_linked_result_cannot_be_deleted(self):
        goal = self.create_result("goal", "Goal").json()["result"]
        outcome = self.create_result(
            "outcome", "Outcome", parent_id=goal["id"]
        ).json()["result"]
        self.client.put(
            f"/v1/projects/{self.project_id}/logical-framework/indicators/{self.indicator_id}/link",
            headers=self.headers("raimundo.cumba"),
            json={"result_id": outcome["id"]},
        )
        response = self.client.delete(
            f"/v1/projects/{self.project_id}/logical-framework/results/{outcome['id']}",
            headers=self.headers("teresa.mbanze"),
        )
        self.assertEqual(response.status_code, 409)

    def test_archived_project_is_readable_but_all_mutations_are_blocked(self):
        goal, outcome, _ = self.create_hierarchy()
        data = self.load()
        MODULE.find_project(data, self.project_id).status = "archived"
        self.save(data)

        readable = self.client.get(
            f"/v1/projects/{self.project_id}/logical-framework",
            headers=self.headers("teresa.mbanze"),
        )
        self.assertEqual(readable.status_code, 200)
        create = self.create_result(
            "goal", "Blocked Goal", expected_status=409
        )
        update = self.client.patch(
            f"/v1/projects/{self.project_id}/logical-framework/results/{goal['id']}",
            headers=self.headers("teresa.mbanze"),
            json={"title": "Blocked"},
        )
        reorder = self.client.post(
            f"/v1/projects/{self.project_id}/logical-framework/reorder",
            headers=self.headers("teresa.mbanze"),
            json={"ordered_result_ids": [goal["id"]]},
        )
        link = self.client.put(
            f"/v1/projects/{self.project_id}/logical-framework/indicators/{self.indicator_id}/link",
            headers=self.headers("raimundo.cumba"),
            json={"result_id": outcome["id"]},
        )
        delete = self.client.delete(
            f"/v1/projects/{self.project_id}/logical-framework/results/{goal['id']}",
            headers=self.headers("teresa.mbanze"),
        )
        self.assertEqual(
            [response.status_code for response in (update, reorder, link, delete)],
            [409, 409, 409, 409],
        )

    def test_organization_isolation_applies_to_reads_and_writes(self):
        blue_read = self.client.get(
            "/v1/projects/proj_other/logical-framework",
            headers=self.headers("teresa.mbanze"),
        )
        blue_write = self.client.post(
            "/v1/projects/proj_other/logical-framework/results",
            headers=self.headers("teresa.mbanze"),
            json={"result_type": "goal", "title": "Forbidden"},
        )
        other_read = self.client.get(
            "/v1/projects/proj_other/logical-framework",
            headers=self.headers("other.manager"),
        )
        other_to_blue = self.client.post(
            f"/v1/projects/{self.project_id}/logical-framework/results",
            headers=self.headers("other.manager"),
            json={"result_type": "goal", "title": "Forbidden"},
        )
        self.assertEqual(blue_read.status_code, 403)
        self.assertEqual(blue_write.status_code, 403)
        self.assertEqual(other_read.status_code, 200)
        self.assertEqual(other_to_blue.status_code, 403)
        self.assertNotIn("Other organization Goal", blue_read.text)

    def test_successful_mutations_emit_complete_audit_action_set(self):
        goal, outcome, output = self.create_hierarchy()
        second_goal = self.create_result("goal", "Second Goal").json()["result"]
        self.client.patch(
            f"/v1/projects/{self.project_id}/logical-framework/results/{goal['id']}",
            headers=self.headers("teresa.mbanze"),
            json={"description": "Updated description"},
        )
        self.client.post(
            f"/v1/projects/{self.project_id}/logical-framework/reorder",
            headers=self.headers("teresa.mbanze"),
            json={"ordered_result_ids": [second_goal["id"], goal["id"]]},
        )
        link_endpoint = (
            f"/v1/projects/{self.project_id}/logical-framework/indicators/"
            f"{self.indicator_id}/link"
        )
        self.client.put(
            link_endpoint,
            headers=self.headers("raimundo.cumba"),
            json={"result_id": output["id"]},
        )
        self.client.delete(
            link_endpoint, headers=self.headers("raimundo.cumba")
        )
        self.client.post(
            f"/v1/projects/{self.project_id}/logical-framework/results/{output['id']}/archive",
            headers=self.headers("teresa.mbanze"),
        )
        disposable = self.create_result("goal", "Disposable").json()["result"]
        self.client.delete(
            f"/v1/projects/{self.project_id}/logical-framework/results/{disposable['id']}",
            headers=self.headers("teresa.mbanze"),
        )
        actions = set(self.audit_actions())
        expected = {
            "logical_framework.goal_created",
            "logical_framework.outcome_created",
            "logical_framework.output_created",
            "logical_framework.result_updated",
            "logical_framework.result_reordered",
            "logical_framework.result_archived",
            "logical_framework.result_deleted",
            "logical_framework.indicator_linked",
            "logical_framework.indicator_unlinked",
        }
        self.assertTrue(expected.issubset(actions))
        logframe_events = [
            event
            for event in self.load().audit_events
            if event.action.startswith("logical_framework.")
        ]
        self.assertTrue(
            all(
                event.organization_id == "org_blue_delta"
                and event.actor_id
                and event.details.get("project_id") == self.project_id
                for event in logframe_events
            )
        )

    def test_failed_and_forbidden_mutations_do_not_emit_success_audit(self):
        before = list(self.audit_actions())
        forbidden = self.create_result(
            "goal",
            "Field cannot create",
            username="aline.duarte",
            expected_status=403,
        )
        invalid = self.create_result(
            "outcome",
            "Missing parent",
            parent_id="missing",
            expected_status=404,
        )
        self.assertEqual(forbidden.status_code, 403)
        self.assertEqual(invalid.status_code, 404)
        self.assertEqual(self.audit_actions(), before)

    def test_api_key_without_user_session_cannot_access_logframe(self):
        os.environ["LOGITRACK_API_KEY"] = "test-service-key"
        response = self.client.get(
            f"/v1/projects/{self.project_id}/logical-framework",
            headers={"X-API-Key": "test-service-key"},
        )
        self.assertEqual(response.status_code, 401)

    def test_project_clone_creates_independent_hierarchy_without_indicator_links(self):
        source_goal, source_outcome, source_output = self.create_hierarchy()
        link_endpoint = (
            f"/v1/projects/{self.project_id}/logical-framework/indicators/"
            f"{self.indicator_id}/link"
        )
        link_response = self.client.put(
            link_endpoint,
            headers=self.headers("raimundo.cumba"),
            json={"result_id": source_output["id"]},
        )
        self.assertEqual(link_response.status_code, 200, link_response.text)
        before = self.load()
        source_ids = {
            node.id
            for node in before.logical_framework_results
            if node.project_id == self.project_id
        }
        source_parents = {
            node.id: node.parent_id
            for node in before.logical_framework_results
            if node.project_id == self.project_id
        }
        source_links = [
            (link.indicator_id, link.result_id)
            for link in before.indicator_result_links
            if link.project_id == self.project_id
        ]
        reporting_ids = [record.id for record in before.reporting_records]

        response = self.client.post(
            f"/v1/admin/projects/{self.project_id}/clone",
            headers=self.headers("org.admin"),
        )
        self.assertEqual(response.status_code, 200, response.text)
        clone_id = response.json()["project"]["project_id"]
        reloaded = self.load()
        destination = MODULE.find_project(reloaded, clone_id)
        destination_nodes = [
            node for node in reloaded.logical_framework_results if node.project_id == clone_id
        ]
        destination_ids = {node.id for node in destination_nodes}
        self.assertEqual(len(destination_nodes), 3)
        self.assertTrue(source_ids.isdisjoint(destination_ids))
        cloned_goal = next(node for node in destination_nodes if node.result_type == "goal")
        cloned_outcome = next(
            node for node in destination_nodes if node.result_type == "outcome"
        )
        cloned_output = next(
            node for node in destination_nodes if node.result_type == "output"
        )
        self.assertEqual(cloned_outcome.parent_id, cloned_goal.id)
        self.assertEqual(cloned_output.parent_id, cloned_outcome.id)
        self.assertTrue(
            all(
                node.organization_id == "org_blue_delta"
                and node.project_id == clone_id
                for node in destination_nodes
            )
        )
        self.assertEqual(destination.indicators, [])
        self.assertFalse(
            [link for link in reloaded.indicator_result_links if link.project_id == clone_id]
        )
        self.assertEqual(
            {
                node.id: node.parent_id
                for node in reloaded.logical_framework_results
                if node.project_id == self.project_id
            },
            source_parents,
        )
        self.assertEqual(
            [
                (link.indicator_id, link.result_id)
                for link in reloaded.indicator_result_links
                if link.project_id == self.project_id
            ],
            source_links,
        )
        self.assertEqual([record.id for record in reloaded.reporting_records], reporting_ids)
        clone_event = next(
            event
            for event in reversed(reloaded.audit_events)
            if event.action == "project.cloned" and event.target_id == clone_id
        )
        self.assertEqual(clone_event.details["logical_framework_results_cloned"], 3)
        self.assertEqual(
            clone_event.details["logical_framework_indicator_links_cloned"], 0
        )

    def test_archived_source_clone_remains_allowed_by_existing_project_policy(self):
        self.create_hierarchy()
        data = self.load()
        MODULE.find_project(data, self.project_id).status = "archived"
        self.save(data)
        response = self.client.post(
            f"/v1/admin/projects/{self.project_id}/clone",
            headers=self.headers("org.admin"),
        )
        self.assertEqual(response.status_code, 200, response.text)
        clone_id = response.json()["project"]["project_id"]
        reloaded = self.load()
        self.assertEqual(MODULE.find_project(reloaded, clone_id).status, "draft")
        self.assertEqual(
            len(
                [
                    node
                    for node in reloaded.logical_framework_results
                    if node.project_id == clone_id
                ]
            ),
            3,
        )

    def test_project_clone_enforces_existing_organization_scope(self):
        response = self.client.post(
            "/v1/admin/projects/proj_other/clone",
            headers=self.headers("org.admin"),
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            [
                project
                for project in self.load().projects
                if project.cloned_from_project_id == "proj_other"
            ]
        )
