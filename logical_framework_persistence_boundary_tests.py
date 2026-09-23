import inspect
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from logical_framework_api_tests import MODULE
from repositories.logical_framework_repository import (
    LogicalFrameworkCanonicalPersistenceError,
    LogicalFrameworkConflictError,
    LogicalFrameworkNotFoundError,
    LogicalFrameworkProjectionError,
    LogicalFrameworkScope,
    LogicalFrameworkScopeError,
)
from repositories.logical_framework_snapshot import (
    SnapshotLogicalFrameworkRepository,
    SnapshotLogicalFrameworkUnitOfWork,
    validate_snapshot_logical_framework,
)
from services.demo_seed import build_demo_seed_bundle
from services.logical_framework_application import (
    LogicalFrameworkActorContext,
    LogicalFrameworkApplication,
    LogicalFrameworkAuditRequest,
)
from services.logical_framework_service import (
    LogicalFrameworkService,
    LogicalFrameworkValidationError,
)
from shared import IndicatorResultLink, ResultNode


RESULT_FIELDS = {
    "id", "organization_id", "project_id", "result_type", "title",
    "description", "parent_id", "display_order", "status", "created_at", "updated_at",
}
INDICATOR_FIELDS = {
    "id", "name", "unit", "frequency", "direction", "level", "target", "baseline",
    "organization_id", "project_id", "result_id", "result_type", "link_id",
}
LINK_FIELDS = {
    "id", "organization_id", "project_id", "indicator_id", "result_id",
    "result_type", "created_at", "updated_at",
}


class LogicalFrameworkHttpCharacterizationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_path = str(Path(self.temp_dir.name) / "logframe_contract.json")
        self.previous_env = {
            name: os.environ.get(name)
            for name in (
                "LOGITRACK_STORAGE_BACKEND", "LOGITRACK_DATA_PATH", "LOGITRACK_SQLITE_PATH",
                "LOGITRACK_ENABLE_RELATIONAL_MIRROR", "LOGITRACK_ENABLE_REPOSITORY_DOMAINS",
                "LOGITRACK_RELATIONAL_SYNC_STRICT", "LOGITRACK_API_KEY",
            )
        }
        os.environ["LOGITRACK_STORAGE_BACKEND"] = "json"
        os.environ["LOGITRACK_DATA_PATH"] = self.data_path
        os.environ.pop("LOGITRACK_SQLITE_PATH", None)
        os.environ["LOGITRACK_ENABLE_RELATIONAL_MIRROR"] = "true"
        os.environ["LOGITRACK_ENABLE_REPOSITORY_DOMAINS"] = "false"
        os.environ["LOGITRACK_RELATIONAL_SYNC_STRICT"] = "false"
        os.environ.pop("LOGITRACK_API_KEY", None)

        data = MODULE.from_serializable(
            build_demo_seed_bundle(MODULE.build_password_hash).payload
        )
        self.tokens = {}
        for user in data.users:
            token = f"contract-token-{user.username}"
            user.api_token_hash = MODULE.hash_with_sha256(token)
            self.tokens[user.username] = token
        MODULE.save_data_to_path(data)
        self.client = TestClient(MODULE.app)
        self.project_id = "proj_resilience"
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

    def create_result(self, result_type, title, parent_id="", username="teresa.mbanze"):
        response = self.client.post(
            f"/v1/projects/{self.project_id}/logical-framework/results",
            headers=self.headers(username),
            json={"result_type": result_type, "title": title, "parent_id": parent_id},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(set(response.json()), {"ok", "result"})
        self.assertEqual(set(response.json()["result"]), RESULT_FIELDS)
        return response.json()["result"]

    def test_methods_paths_success_shapes_ordering_audits_and_projection(self):
        expected_methods = {
            "/v1/projects/{project_id}/logical-framework": {"GET"},
            "/v1/projects/{project_id}/logical-framework/results": {"POST"},
            "/v1/projects/{project_id}/logical-framework/indicators/{indicator_id}/link": {
                "PUT", "DELETE",
            },
            "/v1/projects/{project_id}/logical-framework/reorder": {"POST"},
            "/v1/projects/{project_id}/logical-framework/results/{result_id}/archive": {
                "POST"
            },
            "/v1/projects/{project_id}/logical-framework/results/{result_id}": {
                "PATCH", "DELETE",
            },
        }
        actual_methods = {}
        for route in MODULE.app.routes:
            path = getattr(route, "path", "")
            if path in expected_methods:
                actual_methods.setdefault(path, set()).update(
                    method for method in route.methods if method != "HEAD"
                )
        self.assertEqual(actual_methods, expected_methods)

        goal = self.create_result("goal", "Contract Goal")
        second_goal = self.create_result("goal", "Second Contract Goal")
        outcome = self.create_result("outcome", "Contract Outcome", goal["id"])
        output = self.create_result("output", "Contract Output", outcome["id"])

        updated = self.client.patch(
            f"/v1/projects/{self.project_id}/logical-framework/results/{goal['id']}",
            headers=self.headers("teresa.mbanze"),
            json={"description": "Updated contract description"},
        )
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(set(updated.json()), {"ok", "result"})
        self.assertEqual(set(updated.json()["result"]), RESULT_FIELDS)

        reordered = self.client.post(
            f"/v1/projects/{self.project_id}/logical-framework/reorder",
            headers=self.headers("teresa.mbanze"),
            json={"ordered_result_ids": [second_goal["id"], goal["id"]]},
        )
        self.assertEqual(reordered.status_code, 200, reordered.text)
        self.assertEqual(set(reordered.json()), {"ok", "results"})
        self.assertEqual(
            [item["id"] for item in reordered.json()["results"]],
            [second_goal["id"], goal["id"]],
        )
        self.assertTrue(
            all(set(item) == RESULT_FIELDS for item in reordered.json()["results"])
        )

        link_path = (
            f"/v1/projects/{self.project_id}/logical-framework/indicators/"
            f"{self.indicator_id}/link"
        )
        linked = self.client.put(
            link_path,
            headers=self.headers("raimundo.cumba"),
            json={"result_id": output["id"]},
        )
        self.assertEqual(linked.status_code, 200, linked.text)
        self.assertEqual(set(linked.json()), {"ok", "link"})
        self.assertEqual(set(linked.json()["link"]), LINK_FIELDS)

        read = self.client.get(
            f"/v1/projects/{self.project_id}/logical-framework",
            headers=self.headers("executive.director"),
        )
        self.assertEqual(read.status_code, 200, read.text)
        payload = read.json()
        self.assertEqual(
            set(payload), {"project_id", "organization_id", "goals", "unassigned_indicators"}
        )
        self.assertEqual(
            [item["id"] for item in payload["goals"]],
            [second_goal["id"], goal["id"]],
        )
        self.assertTrue(
            all(set(item) == INDICATOR_FIELDS for item in payload["unassigned_indicators"])
        )

        unlinked = self.client.delete(link_path, headers=self.headers("raimundo.cumba"))
        self.assertEqual(unlinked.status_code, 200, unlinked.text)
        self.assertEqual(set(unlinked.json()), {"ok", "unlinked_indicator_id"})

        archived = self.client.post(
            f"/v1/projects/{self.project_id}/logical-framework/results/{output['id']}/archive",
            headers=self.headers("teresa.mbanze"),
        )
        self.assertEqual(archived.status_code, 200, archived.text)
        self.assertEqual(set(archived.json()), {"ok", "result"})

        disposable = self.create_result("goal", "Disposable Contract Goal")
        deleted = self.client.delete(
            f"/v1/projects/{self.project_id}/logical-framework/results/{disposable['id']}",
            headers=self.headers("teresa.mbanze"),
        )
        self.assertEqual(deleted.status_code, 200, deleted.text)
        self.assertEqual(set(deleted.json()), {"ok", "deleted_result_id"})

        reloaded = MODULE.load_data_from_path(self.data_path)
        actions = {
            event.action
            for event in reloaded.audit_events
            if event.action.startswith("logical_framework.")
        }
        expected_actions = {
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
        self.assertTrue(expected_actions.issubset(actions))
        relational_path = MODULE.get_relational_store_path(self.data_path)
        conn = sqlite3.connect(relational_path)
        try:
            result_ids = {
                row[0]
                for row in conn.execute(
                    "SELECT result_id FROM logical_framework_results WHERE project_id = ?",
                    (self.project_id,),
                ).fetchall()
            }
            audit_actions = {
                row[0]
                for row in conn.execute(
                    "SELECT action FROM audit_events WHERE action LIKE 'logical_framework.%'"
                ).fetchall()
            }
        finally:
            conn.close()
        self.assertIn(goal["id"], result_ids)
        self.assertTrue(expected_actions.issubset(audit_actions))

    def test_error_structure_and_complete_permission_matrix(self):
        path = f"/v1/projects/{self.project_id}/logical-framework/results"
        unauthenticated = self.client.post(
            path, json={"result_type": "goal", "title": "Denied"}
        )
        self.assertEqual(unauthenticated.status_code, 401)
        self.assertEqual(set(unauthenticated.json()), {"detail"})

        manage_status = {
            "org.admin": 200,
            "teresa.mbanze": 200,
            "raimundo.cumba": 403,
            "aline.duarte": 403,
            "executive.director": 403,
        }
        for username, expected_status in manage_status.items():
            with self.subTest(operation="manage", username=username):
                response = self.client.post(
                    path,
                    headers=self.headers(username),
                    json={"result_type": "goal", "title": f"Role Goal {username}"},
                )
                self.assertEqual(response.status_code, expected_status, response.text)
                if expected_status != 200:
                    self.assertEqual(set(response.json()), {"detail"})

        goal = self.create_result("goal", "Permission Goal")
        outcome = self.create_result("outcome", "Permission Outcome", goal["id"])
        link_path = (
            f"/v1/projects/{self.project_id}/logical-framework/indicators/"
            f"{self.indicator_id}/link"
        )
        link_status = {
            "org.admin": 200,
            "teresa.mbanze": 200,
            "raimundo.cumba": 200,
            "aline.duarte": 403,
            "executive.director": 403,
        }
        for username, expected_status in link_status.items():
            with self.subTest(operation="link", username=username):
                response = self.client.put(
                    link_path,
                    headers=self.headers(username),
                    json={"result_id": outcome["id"]},
                )
                self.assertEqual(response.status_code, expected_status, response.text)
                if expected_status != 200:
                    self.assertEqual(set(response.json()), {"detail"})

        for username in manage_status:
            with self.subTest(operation="read", username=username):
                response = self.client.get(
                    f"/v1/projects/{self.project_id}/logical-framework",
                    headers=self.headers(username),
                )
                self.assertEqual(response.status_code, 200, response.text)

        unknown = self.client.post(
            path,
            headers=self.headers("teresa.mbanze"),
            json={"result_type": "outcome", "title": "Unknown", "parent_id": "missing"},
        )
        self.assertEqual(unknown.status_code, 404)
        self.assertEqual(set(unknown.json()), {"detail"})

        invalid = self.client.post(
            path,
            headers=self.headers("teresa.mbanze"),
            json={"result_type": "output", "title": "Invalid", "parent_id": goal["id"]},
        )
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(set(invalid.json()), {"detail"})

        dependency = self.client.delete(
            f"/v1/projects/{self.project_id}/logical-framework/results/{goal['id']}",
            headers=self.headers("teresa.mbanze"),
        )
        self.assertEqual(dependency.status_code, 409)
        self.assertEqual(set(dependency.json()), {"detail"})

    def test_two_writer_snapshot_loss_remains_a_documented_compatibility_limit(self):
        first = MODULE.load_data_from_path(self.data_path)
        second = MODULE.load_data_from_path(self.data_path)
        first.logical_framework_results.append(
            ResultNode(
                id="goal_first_writer",
                organization_id="org_blue_delta",
                project_id=self.project_id,
                result_type="goal",
                title="First writer",
            )
        )
        second.logical_framework_results.append(
            ResultNode(
                id="goal_second_writer",
                organization_id="org_blue_delta",
                project_id=self.project_id,
                result_type="goal",
                title="Second writer",
            )
        )
        MODULE.save_data_to_path(first)
        MODULE.save_data_to_path(second)
        reloaded = MODULE.load_data_from_path(self.data_path)
        ids = {item.id for item in reloaded.logical_framework_results}
        self.assertNotIn("goal_first_writer", ids)
        self.assertIn("goal_second_writer", ids)

    def test_projection_failure_preserves_canonical_state_and_supports_reconciliation(self):
        path = f"/v1/projects/{self.project_id}/logical-framework/results"
        with patch.object(
            MODULE,
            "sync_snapshot_to_relational_store",
            side_effect=RuntimeError("forced non-strict projection failure"),
        ):
            non_strict = self.client.post(
                path,
                headers=self.headers("teresa.mbanze"),
                json={"result_type": "goal", "title": "Non-strict projection goal"},
            )
        self.assertEqual(non_strict.status_code, 200, non_strict.text)
        non_strict_id = non_strict.json()["result"]["id"]
        self.assertIn("forced non-strict", MODULE.RELATIONAL_SYNC_STATE["last_error"])

        os.environ["LOGITRACK_RELATIONAL_SYNC_STRICT"] = "true"
        with patch.object(
            MODULE,
            "sync_snapshot_to_relational_store",
            side_effect=RuntimeError("forced strict projection failure"),
        ):
            strict = self.client.post(
                path,
                headers=self.headers("teresa.mbanze"),
                json={"result_type": "goal", "title": "Strict projection goal"},
            )
        self.assertEqual(strict.status_code, 500, strict.text)
        self.assertEqual(set(strict.json()), {"detail"})
        self.assertIn("Canonical data was committed", strict.json()["detail"])

        canonical = MODULE.load_data_from_path(self.data_path)
        goals = {
            node.title: node.id
            for node in canonical.logical_framework_results
            if node.project_id == self.project_id
        }
        self.assertEqual(goals["Non-strict projection goal"], non_strict_id)
        self.assertIn("Strict projection goal", goals)
        strict_id = goals["Strict projection goal"]
        audited_ids = {
            event.target_id
            for event in canonical.audit_events
            if event.action == "logical_framework.goal_created"
        }
        self.assertIn(non_strict_id, audited_ids)
        self.assertIn(strict_id, audited_ids)

        os.environ["LOGITRACK_RELATIONAL_SYNC_STRICT"] = "false"
        MODULE.update_relational_store_from_data(canonical, source_path=self.data_path)
        relational_path = MODULE.get_relational_store_path(self.data_path)
        conn = sqlite3.connect(relational_path)
        try:
            projected_ids = {
                row[0]
                for row in conn.execute(
                    "SELECT result_id FROM logical_framework_results WHERE project_id = ?",
                    (self.project_id,),
                ).fetchall()
            }
        finally:
            conn.close()
        self.assertIn(non_strict_id, projected_ids)
        self.assertIn(strict_id, projected_ids)

    def test_clone_failure_does_not_persist_partial_project_hierarchy_or_audit(self):
        source_goal = self.create_result("goal", "Clone failure source goal")
        before = MODULE.load_data_from_path(self.data_path)
        before_project_ids = {project.id for project in before.projects}
        before_clone_audits = sum(
            event.action == "project.cloned" for event in before.audit_events
        )

        with patch.object(
            MODULE.LogicalFrameworkService,
            "clone_hierarchy",
            side_effect=LogicalFrameworkValidationError("forced hierarchy clone failure"),
        ):
            response = self.client.post(
                f"/v1/admin/projects/{self.project_id}/clone",
                headers=self.headers("org.admin"),
            )
        self.assertEqual(response.status_code, 400, response.text)
        self.assertEqual(set(response.json()), {"detail"})

        after = MODULE.load_data_from_path(self.data_path)
        self.assertEqual({project.id for project in after.projects}, before_project_ids)
        self.assertEqual(
            sum(event.action == "project.cloned" for event in after.audit_events),
            before_clone_audits,
        )
        self.assertEqual(
            [node.id for node in after.logical_framework_results],
            [node.id for node in before.logical_framework_results],
        )
        self.assertIn(
            source_goal["id"],
            {node.id for node in after.logical_framework_results},
        )

    def test_application_boundary_preserves_sqlite_snapshot_and_unrelated_records(self):
        sqlite_path = str(Path(self.temp_dir.name) / "logical-framework-state.sqlite3")
        original = MODULE.load_data_from_path(self.data_path)
        indicator_ids = {
            indicator.id for project in original.projects for indicator in project.indicators
        }
        reporting_ids = {record.id for record in original.reporting_records}

        os.environ["LOGITRACK_STORAGE_BACKEND"] = "sqlite"
        os.environ["LOGITRACK_SQLITE_PATH"] = sqlite_path
        MODULE.save_data_to_path(original)
        response = self.client.post(
            f"/v1/projects/{self.project_id}/logical-framework/results",
            headers=self.headers("teresa.mbanze"),
            json={"result_type": "goal", "title": "SQLite boundary goal"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        result_id = response.json()["result"]["id"]

        reloaded = MODULE.load_data_from_path(sqlite_path)
        self.assertIn(result_id, {node.id for node in reloaded.logical_framework_results})
        self.assertEqual(
            {indicator.id for project in reloaded.projects for indicator in project.indicators},
            indicator_ids,
        )
        self.assertEqual({record.id for record in reloaded.reporting_records}, reporting_ids)
        conn = sqlite3.connect(sqlite_path)
        try:
            app_state_count = conn.execute("SELECT COUNT(*) FROM app_state").fetchone()[0]
        finally:
            conn.close()
        self.assertEqual(app_state_count, 1)

    def test_reads_and_archived_project_rejections_do_not_commit(self):
        data = MODULE.load_data_from_path(self.data_path)
        project = next(project for project in data.projects if project.id == self.project_id)
        project.status = "archived"
        MODULE.save_data_to_path(data)

        with patch.object(
            MODULE,
            "save_canonical_data_to_path",
            wraps=MODULE.save_canonical_data_to_path,
        ) as canonical_save:
            read = self.client.get(
                f"/v1/projects/{self.project_id}/logical-framework",
                headers=self.headers("executive.director"),
            )
            rejected = self.client.post(
                f"/v1/projects/{self.project_id}/logical-framework/results",
                headers=self.headers("teresa.mbanze"),
                json={"result_type": "goal", "title": "Must not persist"},
            )
        self.assertEqual(read.status_code, 200, read.text)
        self.assertEqual(rejected.status_code, 409, rejected.text)
        self.assertEqual(canonical_save.call_count, 0)
        reloaded = MODULE.load_data_from_path(self.data_path)
        self.assertFalse(
            any(
                node.title == "Must not persist"
                for node in reloaded.logical_framework_results
            )
        )


class LogicalFrameworkRepositoryContract:
    def make_repository(self, scope):
        raise NotImplementedError

    def test_scoped_crud_ordering_indicators_links_and_dependencies(self):
        repository = self.make_repository(self.primary_scope)
        self.assertFalse(hasattr(repository, "state"))
        self.assertEqual(repository.ensure_project().id, self.primary_scope.project_id)
        self.assertEqual(
            [indicator.id for indicator in repository.list_indicators()],
            ["indicator_a"],
        )
        service = LogicalFrameworkService(
            repository,
            now=lambda: "2026-09-23T10:00:00Z",
            id_factory=lambda prefix: f"{prefix}_contract",
        )
        goal = service.create_goal(
            self.primary_scope.organization_id,
            self.primary_scope.project_id,
            "Goal",
            result_id="goal_contract",
            display_order=4,
        )
        outcome = service.create_outcome(
            self.primary_scope.organization_id,
            self.primary_scope.project_id,
            goal.id,
            "Outcome",
            result_id="outcome_contract",
        )
        second_goal = service.create_goal(
            self.primary_scope.organization_id,
            self.primary_scope.project_id,
            "Second Goal",
            result_id="goal_second_contract",
            display_order=1,
        )
        self.assertEqual(
            [node.id for node in repository.list_results() if node.result_type == "goal"],
            [second_goal.id, goal.id],
        )
        link = service.link_indicator(
            self.primary_scope.organization_id,
            self.primary_scope.project_id,
            "indicator_a",
            outcome.id,
        )
        self.assertEqual(repository.require_indicator("indicator_a").id, "indicator_a")
        self.assertEqual(repository.get_indicator_link("indicator_a").id, link.id)
        with self.assertRaises(LogicalFrameworkConflictError):
            repository.delete_result(goal.id)
        service.unlink_indicator(
            self.primary_scope.organization_id,
            self.primary_scope.project_id,
            "indicator_a",
        )
        self.assertIsNone(repository.get_indicator_link("indicator_a"))
        service.delete_result(
            self.primary_scope.organization_id,
            self.primary_scope.project_id,
            outcome.id,
        )
        self.assertIsNone(repository.get_result(outcome.id))
        with self.assertRaises(LogicalFrameworkNotFoundError):
            repository.require_result("missing")

    def test_every_identifier_operation_enforces_scope_and_conflicts(self):
        repository = self.make_repository(self.primary_scope)
        foreign_results_before = list(self.data.logical_framework_results)
        foreign_links_before = list(self.data.indicator_result_links)
        with self.assertRaises(LogicalFrameworkScopeError):
            repository.get_result("goal_foreign")
        with self.assertRaises(LogicalFrameworkScopeError):
            repository.require_indicator("indicator_foreign")
        with self.assertRaises(LogicalFrameworkScopeError):
            repository.get_indicator_link("indicator_foreign")
        with self.assertRaises(LogicalFrameworkScopeError):
            repository.delete_result("outcome_foreign")
        with self.assertRaises(LogicalFrameworkScopeError):
            repository.delete_indicator_link("indicator_foreign")
        self.assertEqual(self.data.logical_framework_results, foreign_results_before)
        self.assertEqual(self.data.indicator_result_links, foreign_links_before)
        with self.assertRaises(LogicalFrameworkScopeError):
            repository.save_result(
                ResultNode(
                    id="goal_wrong_scope",
                    organization_id=self.foreign_scope.organization_id,
                    project_id=self.foreign_scope.project_id,
                    result_type="goal",
                    title="Wrong scope",
                )
            )
        with self.assertRaises(LogicalFrameworkScopeError):
            repository.save_indicator_link(
                IndicatorResultLink(
                    id="link_wrong_scope",
                    organization_id=self.foreign_scope.organization_id,
                    project_id=self.foreign_scope.project_id,
                    indicator_id="indicator_foreign",
                    result_id="goal_foreign",
                    result_type="outcome",
                )
            )

        self.data.logical_framework_results.append(
            ResultNode(
                id="goal_foreign",
                organization_id=self.primary_scope.organization_id,
                project_id=self.primary_scope.project_id,
                result_type="goal",
                title="Duplicate",
            )
        )
        with self.assertRaises(LogicalFrameworkConflictError):
            repository.get_result("goal_foreign")
        with self.assertRaises(LogicalFrameworkConflictError):
            repository.delete_result("goal_foreign")
        self.assertEqual(
            sum(
                node.id == "goal_foreign"
                for node in self.data.logical_framework_results
            ),
            2,
        )


class SnapshotLogicalFrameworkRepositoryContractTests(
    LogicalFrameworkRepositoryContract, unittest.TestCase
):
    def setUp(self):
        self.primary_scope = LogicalFrameworkScope("org_a", "project_a")
        self.foreign_scope = LogicalFrameworkScope("org_b", "project_b")
        self.data = MODULE.LogiTrackData(
            projects=[
                MODULE.Project(
                    id="project_a",
                    name="Project A",
                    objective="Contract",
                    organization_id="org_a",
                    indicators=[
                        MODULE.Indicator(
                            id="indicator_a",
                            name="Indicator A",
                            unit="people",
                            frequency="monthly",
                            direction="up",
                            level="outcome",
                            target=1,
                            baseline=0,
                            organization_id="org_a",
                            project_id="project_a",
                        )
                    ],
                ),
                MODULE.Project(
                    id="project_b",
                    name="Project B",
                    objective="Foreign",
                    organization_id="org_b",
                    indicators=[
                        MODULE.Indicator(
                            id="indicator_foreign",
                            name="Foreign indicator",
                            unit="people",
                            frequency="monthly",
                            direction="up",
                            level="outcome",
                            target=1,
                            baseline=0,
                            organization_id="org_b",
                            project_id="project_b",
                        )
                    ],
                ),
            ],
            logical_framework_results=[
                ResultNode(
                    id="goal_foreign",
                    organization_id="org_b",
                    project_id="project_b",
                    result_type="goal",
                    title="Foreign goal",
                ),
                ResultNode(
                    id="outcome_foreign",
                    organization_id="org_b",
                    project_id="project_b",
                    result_type="outcome",
                    title="Foreign outcome",
                    parent_id="goal_foreign",
                )
            ],
            indicator_result_links=[
                IndicatorResultLink(
                    id="link_foreign",
                    organization_id="org_b",
                    project_id="project_b",
                    indicator_id="indicator_foreign",
                    result_id="outcome_foreign",
                    result_type="outcome",
                )
            ],
        )

    def make_repository(self, scope):
        return SnapshotLogicalFrameworkRepository(self.data, scope)

    def test_delete_indicator_link_is_safe_when_link_ids_collide_across_tenants(self):
        repository = self.make_repository(self.primary_scope)
        service = LogicalFrameworkService(repository)
        goal = service.create_goal(
            self.primary_scope.organization_id,
            self.primary_scope.project_id,
            "Local goal",
            result_id="goal_local",
        )
        outcome = service.create_outcome(
            self.primary_scope.organization_id,
            self.primary_scope.project_id,
            goal.id,
            "Local outcome",
            result_id="outcome_local",
        )
        self.data.indicator_result_links[0].id = "shared_link_id"
        repository.save_indicator_link(
            IndicatorResultLink(
                id="shared_link_id",
                organization_id=self.primary_scope.organization_id,
                project_id=self.primary_scope.project_id,
                indicator_id="indicator_a",
                result_id=outcome.id,
                result_type="outcome",
            )
        )

        validate_snapshot_logical_framework(self.data)
        repository.delete_indicator_link("indicator_a")

        self.assertIsNone(repository.get_indicator_link("indicator_a"))
        self.assertEqual(len(self.data.indicator_result_links), 1)
        surviving = self.data.indicator_result_links[0]
        self.assertEqual(
            (
                surviving.id,
                surviving.organization_id,
                surviving.project_id,
                surviving.indicator_id,
                surviving.result_id,
            ),
            (
                "shared_link_id",
                self.foreign_scope.organization_id,
                self.foreign_scope.project_id,
                "indicator_foreign",
                "outcome_foreign",
            ),
        )
        reloaded = MODULE.from_serializable(MODULE.to_serializable(self.data))
        self.assertEqual(
            [
                (
                    link.id,
                    link.organization_id,
                    link.project_id,
                    link.indicator_id,
                )
                for link in reloaded.indicator_result_links
            ],
            [
                (
                    "shared_link_id",
                    self.foreign_scope.organization_id,
                    self.foreign_scope.project_id,
                    "indicator_foreign",
                )
            ],
        )

    def test_duplicate_indicator_link_ids_conflict_only_within_project_scope(self):
        repository = self.make_repository(self.primary_scope)
        service = LogicalFrameworkService(repository)
        goal = service.create_goal(
            self.primary_scope.organization_id,
            self.primary_scope.project_id,
            "Local goal",
            result_id="goal_local",
        )
        outcome = service.create_outcome(
            self.primary_scope.organization_id,
            self.primary_scope.project_id,
            goal.id,
            "Local outcome",
            result_id="outcome_local",
        )
        first_link = IndicatorResultLink(
            id="duplicate_scoped_link",
            organization_id=self.primary_scope.organization_id,
            project_id=self.primary_scope.project_id,
            indicator_id="indicator_a",
            result_id=outcome.id,
            result_type="outcome",
        )
        repository.save_indicator_link(first_link)
        self.data.projects[0].indicators.append(
            MODULE.Indicator(
                id="indicator_a2",
                name="Indicator A2",
                unit="people",
                frequency="monthly",
                direction="up",
                level="output",
                target=1,
                baseline=0,
                organization_id=self.primary_scope.organization_id,
                project_id=self.primary_scope.project_id,
            )
        )
        duplicate_link = IndicatorResultLink(
            id=first_link.id,
            organization_id=self.primary_scope.organization_id,
            project_id=self.primary_scope.project_id,
            indicator_id="indicator_a2",
            result_id=outcome.id,
            result_type="outcome",
        )

        with self.assertRaises(LogicalFrameworkConflictError):
            repository.save_indicator_link(duplicate_link)
        self.assertIsNone(repository.get_indicator_link("indicator_a2"))

        self.data.indicator_result_links.append(duplicate_link)
        with self.assertRaisesRegex(
            ValueError,
            "Duplicate Logical Framework indicator-link ID",
        ):
            validate_snapshot_logical_framework(self.data)


class LogicalFrameworkUnitOfWorkTests(unittest.TestCase):
    def setUp(self):
        seeded = MODULE.from_serializable(
            build_demo_seed_bundle(MODULE.build_password_hash).payload
        )
        self.durable_payload = MODULE.to_serializable(seeded)
        self.scope = LogicalFrameworkScope("org_blue_delta", "proj_resilience")
        self.actor = LogicalFrameworkActorContext(
            id="user_pm",
            username="teresa.mbanze",
            role="programme_manager",
            organization_id="org_blue_delta",
        )
        self.save_attempts = 0
        self.projection_attempts = 0
        self.fail_audit = False
        self.fail_save = False
        self.fail_projection = False
        self.last_uow = None

    def load_snapshot(self):
        return MODULE.from_serializable(self.durable_payload)

    def save_canonical(self, snapshot):
        self.save_attempts += 1
        if self.fail_save:
            raise RuntimeError("forced canonical save failure")
        self.durable_payload = MODULE.to_serializable(snapshot)
        return "memory://logical-framework-snapshot"

    def synchronize_projection(self, _snapshot, _canonical_path):
        self.projection_attempts += 1
        if self.fail_projection:
            raise RuntimeError("forced projection synchronization failure")

    def append_audit(self, snapshot, request):
        if self.fail_audit:
            raise RuntimeError("forced audit staging failure")
        MODULE.append_audit_event(
            snapshot,
            action=request.action,
            target_type=request.target_type,
            target_id=request.target_id,
            endpoint=request.endpoint,
            actor=request.actor,
            details=request.details,
        )

    def make_uow(self):
        self.last_uow = SnapshotLogicalFrameworkUnitOfWork(
            load_snapshot=self.load_snapshot,
            save_canonical=self.save_canonical,
            synchronize_projection=self.synchronize_projection,
            append_audit=self.append_audit,
        )
        return self.last_uow

    def make_application(self):
        return LogicalFrameworkApplication(
            self.make_uow,
            normalize_project_status=MODULE.normalize_project_status,
        )

    def create_goal(self, title="Atomic goal"):
        return self.make_application().create_result(
            self.scope,
            self.actor,
            result_type="goal",
            title=title,
            description="",
            parent_id="",
            display_order=0,
            status="active",
            endpoint="/contract/results",
        )

    def persisted(self):
        return MODULE.from_serializable(self.durable_payload)

    def test_success_commits_domain_and_audit_once_and_reads_without_commit(self):
        goal = self.create_goal()
        self.assertEqual(self.save_attempts, 1)
        self.assertEqual(self.projection_attempts, 1)
        self.assertTrue(self.last_uow.committed)
        durable = self.persisted()
        self.assertIn(goal.id, {node.id for node in durable.logical_framework_results})
        matching_audits = [
            event
            for event in durable.audit_events
            if event.action == "logical_framework.goal_created"
            and event.target_id == goal.id
        ]
        self.assertEqual(len(matching_audits), 1)

        payload = self.make_application().read(self.scope)
        self.assertEqual(payload["project_id"], self.scope.project_id)
        self.assertEqual(self.save_attempts, 1)
        self.assertEqual(self.projection_attempts, 1)

    def test_unit_of_work_rejects_a_repeated_commit(self):
        unit_of_work = self.make_uow()
        with unit_of_work:
            service = LogicalFrameworkService(unit_of_work.repository(self.scope))
            goal = service.create_goal(
                self.scope.organization_id,
                self.scope.project_id,
                "Single commit goal",
            )
            unit_of_work.stage_audit(
                LogicalFrameworkAuditRequest(
                    actor=self.actor,
                    action="logical_framework.goal_created",
                    target_type="logical_framework_result",
                    target_id=goal.id,
                    endpoint="/contract/results",
                    details={"project_id": self.scope.project_id},
                )
            )
            unit_of_work.commit()
            with self.assertRaises(RuntimeError):
                unit_of_work.commit()
        self.assertEqual(self.save_attempts, 1)
        self.assertEqual(self.projection_attempts, 1)

    def test_validation_and_unexpected_failures_discard_without_a_save(self):
        with self.assertRaises(LogicalFrameworkValidationError):
            self.make_application().create_result(
                self.scope,
                self.actor,
                result_type="outcome",
                title="Invalid outcome",
                description="",
                parent_id="missing-goal",
                display_order=0,
                status="active",
                endpoint="/contract/results",
            )
        self.assertEqual(self.save_attempts, 0)
        self.assertFalse(
            any(node.title == "Invalid outcome" for node in self.persisted().logical_framework_results)
        )

        with self.assertRaisesRegex(RuntimeError, "forced unexpected failure"):
            with self.make_uow() as unit_of_work:
                service = LogicalFrameworkService(unit_of_work.repository(self.scope))
                service.create_goal(
                    self.scope.organization_id,
                    self.scope.project_id,
                    "Discarded goal",
                )
                raise RuntimeError("forced unexpected failure")
        self.assertEqual(self.save_attempts, 0)
        self.assertFalse(
            any(node.title == "Discarded goal" for node in self.persisted().logical_framework_results)
        )

    def test_audit_staging_and_canonical_save_failures_persist_neither_side(self):
        self.fail_audit = True
        with self.assertRaisesRegex(RuntimeError, "forced audit staging failure"):
            self.create_goal("Audit failure goal")
        self.assertEqual(self.save_attempts, 0)
        durable = self.persisted()
        self.assertFalse(
            any(node.title == "Audit failure goal" for node in durable.logical_framework_results)
        )

        self.fail_audit = False
        self.fail_save = True
        with self.assertRaises(LogicalFrameworkCanonicalPersistenceError):
            self.create_goal("Canonical failure goal")
        self.assertEqual(self.save_attempts, 1)
        durable = self.persisted()
        self.assertFalse(
            any(node.title == "Canonical failure goal" for node in durable.logical_framework_results)
        )
        self.assertFalse(
            any(
                event.action == "logical_framework.goal_created"
                and event.details.get("project_id") == self.scope.project_id
                for event in durable.audit_events
            )
        )

    def test_projection_failure_reports_committed_canonical_domain_and_audit(self):
        self.fail_projection = True
        with self.assertRaises(LogicalFrameworkProjectionError) as raised:
            self.create_goal("Projection failure goal")
        self.assertEqual(self.save_attempts, 1)
        self.assertEqual(self.projection_attempts, 1)
        self.assertEqual(
            raised.exception.canonical_path,
            "memory://logical-framework-snapshot",
        )
        self.assertTrue(self.last_uow.committed)
        durable = self.persisted()
        goal = next(
            node
            for node in durable.logical_framework_results
            if node.title == "Projection failure goal"
        )
        self.assertTrue(
            any(
                event.action == "logical_framework.goal_created"
                and event.target_id == goal.id
                for event in durable.audit_events
            )
        )

    def test_public_boundary_does_not_expose_the_application_aggregate(self):
        repository = SnapshotLogicalFrameworkRepository(
            self.load_snapshot(), self.scope
        )
        unit_of_work = self.make_uow()
        self.assertFalse(hasattr(repository, "state"))
        self.assertFalse(hasattr(repository, "snapshot"))
        self.assertFalse(hasattr(unit_of_work, "state"))
        self.assertFalse(hasattr(unit_of_work, "snapshot"))
        application_source = inspect.getsource(LogicalFrameworkApplication)
        service_source = inspect.getsource(LogicalFrameworkService)
        self.assertNotIn("LogiTrackData", application_source)
        self.assertNotIn("LogiTrackData", service_source)


if __name__ == "__main__":
    unittest.main()
