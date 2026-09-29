import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from demo_smoke_tests import (
    MODULE,
    TestClient,
    build_demo_service,
    issue_token_for_user,
    patched_env,
)
from migration.coordination_activity_repair import (
    CoordinationActivityRepairConfig,
    CoordinationActivityRepairError,
    build_coordination_activity_repair_plan,
    run_coordination_activity_repair,
)
from services.demo_seed import build_demo_seed_bundle


class CoordinationActivityReliabilityTests(unittest.TestCase):
    project_id = "proj_resilience"

    def setUp(self):
        if TestClient is None or MODULE.app is None:
            self.skipTest("FastAPI TestClient is unavailable.")
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_path = str(Path(self.temp_dir.name) / "workflow_reliability.json")
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
        _, self.manager_token = issue_token_for_user(data, "teresa.mbanze")
        MODULE.save_data_to_path(data)
        self.client = TestClient(MODULE.app)

    def tearDown(self):
        if hasattr(self, "client"):
            self.client.close()
        if hasattr(self, "environment"):
            self.environment.__exit__(None, None, None)
        if hasattr(self, "temp_dir"):
            self.temp_dir.cleanup()

    def headers(self):
        return {"X-Auth-Token": self.manager_token}

    def create_task(self, title, project_id=None, **overrides):
        payload = {
            "project_id": project_id or self.project_id,
            "title": title,
            "assignee_username": "aline.duarte",
            "priority": "medium",
        }
        payload.update(overrides)
        return self.client.post("/v1/demo/tasks", headers=self.headers(), json=payload)

    def serialized_state(self):
        return MODULE.to_serializable(MODULE.load_data_from_path())

    def activity_occurrences(self, activity_id):
        data = MODULE.load_data_from_path()
        return [
            (project_id, activity)
            for project_id, ops in data.ops_by_project.items()
            for activity in ops.activities
            if activity.id == activity_id
        ]

    def test_repeated_implicit_tasks_reuse_one_project_coordination_activity(self):
        first = self.create_task("Browser reliability task one")
        second = self.create_task("Browser reliability task two")

        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(second.status_code, 200, second.text)
        occurrences = self.activity_occurrences("act_proj_resilience_coordination")
        self.assertEqual(len(occurrences), 1)
        self.assertEqual(occurrences[0][0], self.project_id)
        task_ids = {task.id for task in occurrences[0][1].tasks}
        self.assertIn(first.json()["task"]["task_id"], task_ids)
        self.assertIn(second.json()["task"]["task_id"], task_ids)

    def test_implicit_coordination_activities_are_project_local(self):
        resilience = self.create_task("Resilience coordination task")
        health = self.create_task("Health coordination task", project_id="proj_health")

        self.assertEqual(resilience.status_code, 200, resilience.text)
        self.assertEqual(health.status_code, 200, health.text)
        self.assertEqual(len(self.activity_occurrences("act_proj_resilience_coordination")), 1)
        self.assertEqual(len(self.activity_occurrences("act_proj_health_coordination")), 1)

    def test_duplicate_default_activity_fails_without_persisted_side_effects(self):
        data = MODULE.load_data_from_path()
        ops = data.ops_by_project[self.project_id]
        template = copy.deepcopy(ops.activities[0])
        template.id = "act_proj_resilience_coordination"
        template.organization_id = "org_blue_delta"
        template.tasks = []
        ops.activities.extend([copy.deepcopy(template), copy.deepcopy(template)])
        MODULE.save_data_to_path(data)
        before = self.serialized_state()

        response = self.create_task("Must not partially persist")

        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(self.serialized_state(), before)

    def test_foreign_default_activity_collision_fails_without_mutation(self):
        data = MODULE.load_data_from_path()
        foreign_ops = data.ops_by_project["proj_health"]
        foreign = copy.deepcopy(foreign_ops.activities[0])
        foreign.id = "act_proj_resilience_coordination"
        foreign.tasks = []
        foreign_ops.activities.append(foreign)
        MODULE.save_data_to_path(data)
        before = self.serialized_state()

        response = self.create_task("Foreign collision must fail")

        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(self.serialized_state(), before)

    def test_explicit_foreign_activity_id_fails_without_mutation(self):
        data = MODULE.load_data_from_path()
        foreign_activity_id = data.ops_by_project["proj_health"].activities[0].id
        before = self.serialized_state()

        response = self.create_task(
            "Explicit foreign activity must fail",
            activity_id=foreign_activity_id,
        )

        self.assertEqual(response.status_code, 404, response.text)
        self.assertEqual(self.serialized_state(), before)

    def test_explicit_local_activity_is_reused_and_duplicate_task_id_is_rejected(self):
        data = MODULE.load_data_from_path()
        local_activity = data.ops_by_project[self.project_id].activities[0]
        first = self.create_task(
            "Explicit local activity",
            id="task_explicit_local_activity",
            activity_id=local_activity.id,
        )
        self.assertEqual(first.status_code, 200, first.text)
        before = self.serialized_state()

        duplicate = self.create_task(
            "Duplicate task identifier",
            id="task_explicit_local_activity",
            activity_id=local_activity.id,
        )

        self.assertEqual(duplicate.status_code, 409, duplicate.text)
        self.assertEqual(self.serialized_state(), before)

    def test_structurally_incompatible_default_activity_fails_closed(self):
        data = MODULE.load_data_from_path()
        ops = data.ops_by_project[self.project_id]
        incompatible = copy.deepcopy(ops.activities[0])
        incompatible.id = "act_proj_resilience_coordination"
        incompatible.organization_id = "org_blue_delta"
        incompatible.tasks = []
        incompatible.linked_indicator_ids = None
        ops.activities.append(incompatible)
        MODULE.save_data_to_path(data)
        before = self.serialized_state()

        response = self.create_task("Malformed coordination activity")

        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(self.serialized_state(), before)


class ProjectionAuthorityReliabilityTests(unittest.TestCase):
    def setUp(self):
        if TestClient is None or MODULE.app is None:
            self.skipTest("FastAPI TestClient is unavailable.")
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_path = str(Path(self.temp_dir.name) / "projection_authority.json")
        self.relational_path = str(Path(self.temp_dir.name) / "projection.sqlite3")
        self.environment = patched_env(
            LOGITRACK_STORAGE_BACKEND="json",
            LOGITRACK_DATA_PATH=self.data_path,
            LOGITRACK_SQLITE_PATH=None,
            LOGITRACK_RELATIONAL_DB_PATH=self.relational_path,
            LOGITRACK_ENABLE_RELATIONAL_MIRROR="true",
            LOGITRACK_ENABLE_REPOSITORY_DOMAINS="true",
            LOGITRACK_RELATIONAL_SYNC_STRICT="false",
            LOGITRACK_API_KEY=None,
        )
        self.environment.__enter__()
        self.bundle = build_demo_seed_bundle(MODULE.build_password_hash)
        data = MODULE.from_serializable(self.bundle.payload)
        MODULE.save_data_to_path(data)
        self.client = TestClient(MODULE.app)

    def tearDown(self):
        if hasattr(self, "client"):
            self.client.close()
        if hasattr(self, "environment"):
            self.environment.__exit__(None, None, None)
        if hasattr(self, "temp_dir"):
            self.temp_dir.cleanup()

    def test_broad_projection_failure_still_attempts_repository_sync(self):
        data = MODULE.load_data_from_path()
        with patch.object(
            MODULE,
            "sync_snapshot_to_relational_store",
            side_effect=RuntimeError("activity projection failed"),
        ), patch.object(
            MODULE,
            "sync_repository_backed_domains_from_snapshot",
            wraps=MODULE.sync_repository_backed_domains_from_snapshot,
        ) as repository_sync:
            result = MODULE.update_relational_store_from_data(data, source_path=self.data_path)

        self.assertIsNone(result)
        repository_sync.assert_called_once()
        self.assertIn("activity projection failed", MODULE.RELATIONAL_SYNC_STATE["last_error"])
        self.assertEqual(MODULE.REPOSITORY_SYNC_STATE["last_error"], "")

    def test_login_token_survives_unrelated_projection_failure(self):
        credential = next(item for item in self.bundle.credentials if item.username == "aline.duarte")
        with patch.object(
            MODULE,
            "sync_snapshot_to_relational_store",
            side_effect=RuntimeError("activity projection failed"),
        ):
            login = self.client.post(
                "/v1/auth/login",
                json={"username": credential.username, "password": credential.password},
            )

        self.assertEqual(login.status_code, 200, login.text)
        token = login.json()["token"]
        identity = self.client.get("/v1/auth/me", headers={"X-Auth-Token": token})
        self.assertEqual(identity.status_code, 200, identity.text)
        self.assertEqual(identity.json()["user"]["username"], "aline.duarte")

    def test_production_loader_distinguishes_present_empty_from_absent_users(self):
        canonical = MODULE.to_serializable(MODULE.load_json(self.data_path))
        present_empty = copy.deepcopy(canonical)
        present_empty["users"] = []
        Path(self.data_path).write_text(json.dumps(present_empty), encoding="utf-8")

        loaded_empty = MODULE.load_data_from_path()
        self.assertEqual(loaded_empty.users, [])

        absent = copy.deepcopy(canonical)
        absent.pop("users", None)
        Path(self.data_path).write_text(json.dumps(absent), encoding="utf-8")
        loaded_legacy = MODULE.load_data_from_path()

        self.assertGreater(len(loaded_legacy.users), 0)
        self.assertIsNotNone(MODULE.find_user_by_username(loaded_legacy, "aline.duarte"))

    def test_repository_failure_keeps_canonical_state_and_separate_diagnostics(self):
        data = MODULE.load_data_from_path()
        user = MODULE.find_user_by_username(data, "aline.duarte")
        user.api_token_hash = "canonical-token-hash"
        with patch.object(
            MODULE,
            "sync_repository_backed_domains_from_snapshot",
            side_effect=RuntimeError("repository users failed"),
        ):
            MODULE.save_data_to_path(data)

        canonical = MODULE.load_json(self.data_path)
        self.assertEqual(
            MODULE.find_user_by_username(canonical, "aline.duarte").api_token_hash,
            "canonical-token-hash",
        )
        self.assertEqual(MODULE.RELATIONAL_SYNC_STATE["last_error"], "")
        self.assertIn("repository users failed", MODULE.REPOSITORY_SYNC_STATE["last_error"])

    def test_strict_combined_failure_attempts_both_and_surfaces_broad_error(self):
        data = MODULE.load_data_from_path()
        with patched_env(LOGITRACK_RELATIONAL_SYNC_STRICT="true"), patch.object(
            MODULE,
            "sync_snapshot_to_relational_store",
            side_effect=RuntimeError("broad projection failed"),
        ) as broad_sync, patch.object(
            MODULE,
            "sync_repository_backed_domains_from_snapshot",
            side_effect=RuntimeError("repository projection failed"),
        ) as repository_sync:
            with self.assertRaisesRegex(RuntimeError, "broad projection failed"):
                MODULE.update_relational_store_from_data(data, source_path=self.data_path)

        broad_sync.assert_called_once()
        repository_sync.assert_called_once()
        self.assertIn("broad projection failed", MODULE.RELATIONAL_SYNC_STATE["last_error"])
        self.assertIn("repository projection failed", MODULE.REPOSITORY_SYNC_STATE["last_error"])


class CoordinationActivityRepairTests(unittest.TestCase):
    def build_fixture(self):
        snapshot = copy.deepcopy(build_demo_seed_bundle(MODULE.build_password_hash).payload)
        activities = snapshot["ops_by_project"]["proj_resilience"]["activities"]
        first = copy.deepcopy(activities[0])
        second = copy.deepcopy(activities[0])
        first["id"] = "act_proj_resilience_coordination"
        second["id"] = "act_proj_resilience_coordination"
        first["name"] = "Operational Coordination Queue"
        second["name"] = "Operational Coordination Queue"
        first["organization_id"] = "org_blue_delta"
        second["organization_id"] = "org_blue_delta"
        first["linked_indicator_ids"] = ["ind_res_committees", "ind_res_households"]
        second["linked_indicator_ids"] = ["ind_res_households", "ind_res_agriculture"]
        first_task = copy.deepcopy(first["tasks"][0])
        second_task = copy.deepcopy(first["tasks"][1])
        first_task["id"] = "task_proj_resilience_test"
        first_task["name"] = "Browser-created test task"
        second_task["id"] = "task_proj_resilience_test2"
        second_task["name"] = "Second browser-created test task"
        first["tasks"] = [first_task]
        second["tasks"] = [second_task]
        activities.extend([first, second])
        return snapshot

    def config(self):
        return CoordinationActivityRepairConfig(
            organization_id="org_blue_delta",
            project_id="proj_resilience",
            activity_id="act_proj_resilience_coordination",
            expected_activity_count=11,
            expected_task_count=20,
            expected_task_ids=("task_proj_resilience_test", "task_proj_resilience_test2"),
        )

    def test_repair_fixture_and_dry_run_are_lossless_and_non_mutating(self):
        snapshot = self.build_fixture()
        before = copy.deepcopy(snapshot)
        result = run_coordination_activity_repair(
            config=self.config(),
            load_snapshot=lambda: snapshot,
            rehearse_projection=lambda staged: {
                "activities": sum(len(ops["activities"]) for ops in staged["ops_by_project"].values()),
                "ok": True,
            },
            backup_path="workspace.timestamped.bak",
        )

        self.assertEqual(snapshot, before)
        self.assertEqual(result["activities_before"], 11)
        self.assertEqual(result["activities_after"], 10)
        self.assertEqual(result["tasks_before"], 20)
        self.assertEqual(result["tasks_after"], 20)
        self.assertEqual(result["rehearsal"], {"activities": 10, "ok": True})
        self.assertFalse(result["canonical_mutated"])
        self.assertFalse(result["projection_mutated"])

    def test_repair_plan_preserves_tasks_and_stable_deduplicates_links(self):
        snapshot = self.build_fixture()
        original_tasks = {
            task["id"]: copy.deepcopy(task)
            for ops in snapshot["ops_by_project"].values()
            for activity in ops["activities"]
            for task in activity["tasks"]
        }

        plan = build_coordination_activity_repair_plan(snapshot, self.config())
        target = [
            activity
            for activity in plan.repaired_snapshot["ops_by_project"]["proj_resilience"]["activities"]
            if activity["id"] == "act_proj_resilience_coordination"
        ]
        repaired_tasks = {
            task["id"]: task
            for ops in plan.repaired_snapshot["ops_by_project"].values()
            for activity in ops["activities"]
            for task in activity["tasks"]
        }

        self.assertEqual(len(target), 1)
        self.assertEqual(
            target[0]["linked_indicator_ids"],
            ["ind_res_committees", "ind_res_households", "ind_res_agriculture"],
        )
        self.assertEqual(repaired_tasks, original_tasks)

    def test_repair_apply_requires_confirmation_and_reports_projection_failure(self):
        snapshot = self.build_fixture()
        with self.assertRaisesRegex(CoordinationActivityRepairError, "server is stopped"):
            run_coordination_activity_repair(
                config=self.config(),
                load_snapshot=lambda: snapshot,
                rehearse_projection=lambda staged: {"ok": True},
                backup_path="workspace.timestamped.bak",
                apply=True,
            )

        calls = []
        result = run_coordination_activity_repair(
            config=self.config(),
            load_snapshot=lambda: snapshot,
            rehearse_projection=lambda staged: {"ok": True},
            backup_path="workspace.timestamped.bak",
            apply=True,
            server_stopped_confirmed=True,
            write_backup=lambda path: calls.append(("backup", path)),
            save_canonical=lambda staged: calls.append(("save", staged)),
            rebuild_projection=lambda staged: (_ for _ in ()).throw(RuntimeError("projection rebuild failed")),
        )

        self.assertEqual([item[0] for item in calls], ["backup", "save"])
        self.assertTrue(result["canonical_mutated"])
        self.assertFalse(result["projection_mutated"])
        self.assertIn("projection rebuild failed", result["projection_error"])

    def test_repair_apply_calls_backup_save_and_rebuild_once(self):
        snapshot = self.build_fixture()
        calls = []
        result = run_coordination_activity_repair(
            config=self.config(),
            load_snapshot=lambda: snapshot,
            rehearse_projection=lambda staged: {"ok": True},
            backup_path="workspace.timestamped.bak",
            apply=True,
            server_stopped_confirmed=True,
            write_backup=lambda path: calls.append(("backup", path)),
            save_canonical=lambda staged: calls.append(("save", staged)),
            rebuild_projection=lambda staged: calls.append(("rebuild", staged)) or {"ok": True},
        )

        self.assertEqual([item[0] for item in calls], ["backup", "save", "rebuild"])
        self.assertEqual(result["mode"], "apply")
        self.assertTrue(result["canonical_mutated"])
        self.assertTrue(result["projection_mutated"])
        self.assertEqual(result["projection"], {"ok": True})

    def test_repair_precondition_or_rehearsal_failure_never_saves(self):
        snapshot = self.build_fixture()
        invalid_config = CoordinationActivityRepairConfig(
            organization_id="org_blue_delta",
            project_id="proj_resilience",
            activity_id="act_proj_resilience_coordination",
            expected_activity_count=12,
            expected_task_count=20,
            expected_task_ids=("task_proj_resilience_test", "task_proj_resilience_test2"),
        )
        saves = []
        with self.assertRaises(CoordinationActivityRepairError):
            run_coordination_activity_repair(
                config=invalid_config,
                load_snapshot=lambda: snapshot,
                rehearse_projection=lambda staged: {"ok": True},
                backup_path="workspace.timestamped.bak",
                apply=True,
                server_stopped_confirmed=True,
                write_backup=lambda path: None,
                save_canonical=lambda staged: saves.append(staged),
                rebuild_projection=lambda staged: {"ok": True},
            )
        self.assertEqual(saves, [])

        backups = []
        with self.assertRaisesRegex(RuntimeError, "rehearsal failed"):
            run_coordination_activity_repair(
                config=self.config(),
                load_snapshot=lambda: snapshot,
                rehearse_projection=lambda staged: (_ for _ in ()).throw(RuntimeError("rehearsal failed")),
                backup_path="workspace.timestamped.bak",
                apply=True,
                server_stopped_confirmed=True,
                write_backup=lambda path: backups.append(path),
                save_canonical=lambda staged: saves.append(staged),
                rebuild_projection=lambda staged: {"ok": True},
            )
        self.assertEqual(backups, ["workspace.timestamped.bak"])
        self.assertEqual(saves, [])

    def test_repair_postcondition_failure_leaves_source_unchanged(self):
        snapshot = self.build_fixture()
        before = copy.deepcopy(snapshot)
        activities = snapshot["ops_by_project"]["proj_health"]["activities"]
        activities[1]["id"] = activities[0]["id"]

        with self.assertRaisesRegex(CoordinationActivityRepairError, "Activity IDs remain duplicated"):
            build_coordination_activity_repair_plan(snapshot, self.config())

        expected = copy.deepcopy(before)
        expected["ops_by_project"]["proj_health"]["activities"][1]["id"] = activities[0]["id"]
        self.assertEqual(snapshot, expected)


if __name__ == "__main__":
    unittest.main()
