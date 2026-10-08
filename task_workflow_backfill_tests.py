import copy
import json
import tempfile
import unittest
from pathlib import Path

from migration.task_workflow_backfill import (
    ALREADY_CANONICAL,
    AMBIGUOUS,
    INVALID_EXISTING_ROUTING,
    SAFE_TO_BACKFILL,
    UNRESOLVED,
    TaskWorkflowBackfillError,
    build_task_workflow_backfill_plan,
    run_task_workflow_backfill,
)


class TaskWorkflowBackfillTests(unittest.TestCase):
    def permissions(self, user):
        return list(user.get("permissions") or [])

    def user(self, user_id, username, permissions, **overrides):
        record = {
            "id": user_id,
            "username": username,
            "organization_id": "org_a",
            "role": "custom",
            "status": "active",
            "is_active": True,
            "permissions": list(permissions),
        }
        record.update(overrides)
        return record

    def task(self, task_id="task_1", **overrides):
        record = {
            "id": task_id,
            "name": task_id,
            "assignee_username": "assignee",
            "status": "not_started",
            "submitted_at": "",
            "validated_at": "",
            "approved_at": "",
            "activity_log": [],
        }
        record.update(overrides)
        return record

    def snapshot(self, tasks=None, users=None, assignments=None):
        users = users or [
            self.user("user_assignee", "assignee", ["UPDATE_TASK_PROGRESS", "SUBMIT_EVIDENCE"]),
            self.user("user_validator", "validator", ["VALIDATE_EVIDENCE"]),
            self.user("user_approver", "approver", ["APPROVE_TASKS"]),
        ]
        assignments = assignments or [
            {
                "id": f"assignment_{user['id']}",
                "project_id": "project_a",
                "organization_id": "org_a",
                "user_id": user["id"],
                "status": "active",
            }
            for user in users
            if user.get("organization_id") == "org_a"
        ]
        return {
            "organizations": [{"id": "org_a"}],
            "projects": [
                {
                    "id": "project_a",
                    "organization_id": "org_a",
                    "team_assignments": assignments,
                }
            ],
            "users": users,
            "ops_by_project": {
                "project_a": {
                    "activities": [
                        {"id": "activity_a", "organization_id": "org_a", "tasks": tasks or [self.task()]}
                    ]
                }
            },
            "audit_events": [{"id": "audit_unchanged"}],
        }

    def result(self, plan, task_id="task_1"):
        return next(item for item in plan.report["tasks"] if item["task_id"] == task_id)

    def canonical_task(self, **overrides):
        task = self.task(
            assignee_user_id="user_assignee",
            review_mode="validation_and_approval",
            validator_user_id="user_validator",
            approver_user_id="user_approver",
            evidence_required=False,
            review_stage="execution",
        )
        task.update(overrides)
        return task

    def test_unique_legacy_route_is_safe_with_approved_defaults(self):
        source = self.snapshot()
        plan = build_task_workflow_backfill_plan(source, self.permissions)
        result = self.result(plan)
        self.assertEqual(result["classification"], SAFE_TO_BACKFILL)
        self.assertEqual(
            result["proposed_fields"],
            {
                "review_mode": "validation_and_approval",
                "evidence_required": False,
                "assignee_user_id": "user_assignee",
                "validator_user_id": "user_validator",
                "approver_user_id": "user_approver",
                "review_stage": "execution",
            },
        )

    def test_zero_inactive_cross_org_and_nonmember_assignees_are_unresolved(self):
        cases = {
            "zero": self.snapshot(tasks=[self.task(assignee_username="missing")]),
            "inactive": self.snapshot(users=[
                self.user("user_assignee", "assignee", ["UPDATE_TASK_PROGRESS"], is_active=False),
                self.user("user_validator", "validator", ["VALIDATE_EVIDENCE"]),
                self.user("user_approver", "approver", ["APPROVE_TASKS"]),
            ]),
            "cross_org": self.snapshot(users=[
                self.user("user_assignee", "assignee", ["UPDATE_TASK_PROGRESS"], organization_id="org_b"),
                self.user("user_validator", "validator", ["VALIDATE_EVIDENCE"]),
                self.user("user_approver", "approver", ["APPROVE_TASKS"]),
            ]),
        }
        nonmember = self.snapshot()
        nonmember["projects"][0]["team_assignments"] = [
            item for item in nonmember["projects"][0]["team_assignments"] if item["user_id"] != "user_assignee"
        ]
        cases["nonmember"] = nonmember
        for label, snapshot in cases.items():
            with self.subTest(label=label):
                result = self.result(build_task_workflow_backfill_plan(snapshot, self.permissions))
                self.assertEqual(result["classification"], UNRESOLVED)
                self.assertIn("ASSIGNEE_USERNAME_NOT_RESOLVED", result["reason_codes"])

    def test_multiple_same_scope_assignee_matches_are_ambiguous(self):
        users = [
            self.user("user_assignee", "assignee", ["UPDATE_TASK_PROGRESS"]),
            self.user("user_assignee_2", "assignee", ["UPDATE_TASK_PROGRESS"]),
            self.user("user_validator", "validator", ["VALIDATE_EVIDENCE"]),
            self.user("user_approver", "approver", ["APPROVE_TASKS"]),
        ]
        result = self.result(build_task_workflow_backfill_plan(self.snapshot(users=users), self.permissions))
        self.assertEqual(result["classification"], AMBIGUOUS)
        self.assertIn("ASSIGNEE_USERNAME_AMBIGUOUS", result["reason_codes"])

    def test_deterministic_reviewer_identity_is_capability_based(self):
        plan = build_task_workflow_backfill_plan(self.snapshot(), self.permissions)
        proposed = self.result(plan)["proposed_fields"]
        self.assertEqual(proposed["validator_user_id"], "user_validator")
        self.assertEqual(proposed["approver_user_id"], "user_approver")

        role_only = self.snapshot(users=[
            self.user("user_assignee", "assignee", ["UPDATE_TASK_PROGRESS"]),
            self.user("user_validator", "validator", [], role="meal_officer"),
            self.user("user_approver", "approver", [], role="programme_manager"),
        ])
        result = self.result(build_task_workflow_backfill_plan(role_only, self.permissions))
        self.assertEqual(result["classification"], UNRESOLVED)
        self.assertIn("VALIDATOR_NOT_RESOLVED", result["reason_codes"])

    def test_ambiguous_reviewer_identity_is_not_guessed(self):
        users = self.snapshot()["users"] + [self.user("user_validator_2", "validator2", ["VALIDATE_EVIDENCE"])]
        result = self.result(build_task_workflow_backfill_plan(self.snapshot(users=users), self.permissions))
        self.assertEqual(result["classification"], AMBIGUOUS)
        self.assertIn("VALIDATOR_AMBIGUOUS", result["reason_codes"])
        self.assertEqual(result["proposed_fields"], {})

    def test_existing_reviewer_capability_and_scope_are_validated(self):
        cases = [
            self.task(validator_user_id="user_approver"),
            self.task(validator_user_id="missing"),
        ]
        for task in cases:
            with self.subTest(task=task):
                result = self.result(build_task_workflow_backfill_plan(self.snapshot(tasks=[task]), self.permissions))
                self.assertEqual(result["classification"], INVALID_EXISTING_ROUTING)
                self.assertIn("CANONICAL_VALIDATOR_NOT_ELIGIBLE", result["reason_codes"])

    def test_cross_org_and_nonmember_existing_reviewers_are_invalid(self):
        base_users = self.snapshot()['users']
        cases = {
            'cross_org': self.user(
                'foreign_validator',
                'foreign.validator',
                ['VALIDATE_EVIDENCE'],
                organization_id='org_b',
            ),
            'nonmember': self.user(
                'nonmember_validator',
                'nonmember.validator',
                ['VALIDATE_EVIDENCE'],
            ),
        }
        for label, reviewer in cases.items():
            with self.subTest(label=label):
                task = self.task(validator_user_id=reviewer['id'])
                snapshot = self.snapshot(tasks=[task], users=[*base_users, reviewer])
                snapshot['projects'][0]['team_assignments'] = [
                    item
                    for item in snapshot['projects'][0]['team_assignments']
                    if item['user_id'] != reviewer['id']
                ]
                result = self.result(build_task_workflow_backfill_plan(snapshot, self.permissions))
                self.assertEqual(result['classification'], INVALID_EXISTING_ROUTING)
                self.assertIn('CANONICAL_VALIDATOR_NOT_ELIGIBLE', result['reason_codes'])

    def test_separation_of_duties_conflicts_are_invalid(self):
        cases = {
            "self_validator": self.task(validator_user_id="user_assignee"),
            "self_approver": self.task(approver_user_id="user_assignee"),
            "same_reviewer": self.task(
                validator_user_id="user_validator",
                approver_user_id="user_validator",
            ),
        }
        users = self.snapshot()["users"]
        users[1]["permissions"].append("APPROVE_TASKS")
        for label, task in cases.items():
            with self.subTest(label=label):
                result = self.result(build_task_workflow_backfill_plan(self.snapshot(tasks=[task], users=users), self.permissions))
                self.assertEqual(result["classification"], INVALID_EXISTING_ROUTING)

    def test_review_stage_derives_deterministically_from_history(self):
        tasks = [
            self.task("open"),
            self.task("validation", status="pending_validation", submitted_at="2026-01-01T00:00:00Z"),
            self.task(
                "approval",
                status="pending_validation",
                submitted_at="2026-01-01T00:00:00Z",
                validated_at="2026-01-02T00:00:00Z",
            ),
            self.task(
                "complete",
                status="completed",
                submitted_at="2026-01-01T00:00:00Z",
                validated_at="2026-01-02T00:00:00Z",
                approved_at="2026-01-03T00:00:00Z",
            ),
        ]
        plan = build_task_workflow_backfill_plan(self.snapshot(tasks=tasks), self.permissions)
        stages = {item["task_id"]: item["proposed_fields"]["review_stage"] for item in plan.report["tasks"]}
        self.assertEqual(stages, {"open": "execution", "validation": "validation", "approval": "approval", "complete": "complete"})

    def test_contradictory_historical_state_is_invalid(self):
        tasks = [
            self.task("open_with_submission", submitted_at="2026-01-01T00:00:00Z"),
            self.task("pending_without_submission", status="pending_validation"),
            self.task("complete_without_history", status="completed"),
        ]
        plan = build_task_workflow_backfill_plan(self.snapshot(tasks=tasks), self.permissions)
        self.assertTrue(all(item["classification"] == INVALID_EXISTING_ROUTING for item in plan.report["tasks"]))

    def test_already_canonical_is_skipped(self):
        plan = build_task_workflow_backfill_plan(self.snapshot(tasks=[self.canonical_task()]), self.permissions)
        result = self.result(plan)
        self.assertEqual(result["classification"], ALREADY_CANONICAL)
        self.assertEqual(plan.source_snapshot, plan.proposed_snapshot)

    def test_invalid_canonical_routing_is_reported_not_repaired(self):
        task = self.canonical_task(validator_user_id="user_assignee")
        plan = build_task_workflow_backfill_plan(self.snapshot(tasks=[task]), self.permissions)
        result = self.result(plan)
        self.assertEqual(result["classification"], INVALID_EXISTING_ROUTING)
        self.assertEqual(result["proposed_fields"], {})
        self.assertEqual(plan.source_snapshot, plan.proposed_snapshot)

    def test_dry_run_is_byte_for_byte_non_mutating_and_reports_exact_fields(self):
        snapshot = self.snapshot()
        source = json.dumps(snapshot, separators=(",", ":"), sort_keys=True).encode()
        before = bytes(source)
        result = run_task_workflow_backfill(lambda: source, self.permissions)
        self.assertEqual(source, before)
        self.assertFalse(result["canonical_mutated"])
        self.assertFalse(result["projection_mutated"])
        self.assertEqual(result["counts"][SAFE_TO_BACKFILL], 1)
        self.assertEqual(result["tasks"][0]["proposed_fields"]["assignee_user_id"], "user_assignee")

    def test_apply_changes_only_safe_records_and_preserves_unsafe_records(self):
        safe = self.task("safe")
        unsafe = self.task("unsafe", assignee_username="missing")
        snapshot = self.snapshot(tasks=[safe, unsafe])
        source = json.dumps(snapshot, sort_keys=True).encode()
        unsafe_before = copy.deepcopy(unsafe)
        saved = []
        projection = []
        backup = {}
        events = []

        def write_backup(path, content):
            events.append("backup")
            backup[path] = content

        def save(proposed):
            events.append("save")
            saved.append(proposed)

        result = run_task_workflow_backfill(
            lambda: source,
            self.permissions,
            apply=True,
            expected_source_sha256=__import__("hashlib").sha256(source).hexdigest(),
            backup_path="isolated.bak",
            server_stopped_confirmed=True,
            write_backup=write_backup,
            read_backup=lambda path: backup[path],
            save_snapshot=save,
            rebuild_projection=lambda proposed: projection.append(proposed) or {"ok": True},
        )
        self.assertEqual(events, ["backup", "save"])
        self.assertEqual(result["changed_task_ids"], ["safe"])
        saved_tasks = saved[0]["ops_by_project"]["project_a"]["activities"][0]["tasks"]
        self.assertEqual(saved_tasks[1], unsafe_before)
        self.assertEqual(saved_tasks[0]["assignee_user_id"], "user_assignee")
        self.assertTrue(result["backup_created"])
        self.assertEqual(result["backup_sha256"], result["source_sha256"])
        self.assertEqual(len(projection), 1)

    def test_backup_failure_prevents_canonical_mutation(self):
        source = json.dumps(self.snapshot(), sort_keys=True).encode()
        saved = []
        with self.assertRaises(TaskWorkflowBackfillError):
            run_task_workflow_backfill(
                lambda: source,
                self.permissions,
                apply=True,
                expected_source_sha256=__import__("hashlib").sha256(source).hexdigest(),
                backup_path="isolated.bak",
                server_stopped_confirmed=True,
                write_backup=lambda path, content: None,
                read_backup=lambda path: b"corrupt",
                save_snapshot=saved.append,
                rebuild_projection=lambda proposed: {},
            )
        self.assertEqual(saved, [])

    def test_changed_source_hash_prevents_backup_and_mutation(self):
        source = json.dumps(self.snapshot(), sort_keys=True).encode()
        writes = []
        with self.assertRaises(TaskWorkflowBackfillError):
            run_task_workflow_backfill(
                lambda: source,
                self.permissions,
                apply=True,
                expected_source_sha256="0" * 64,
                backup_path="isolated.bak",
                server_stopped_confirmed=True,
                write_backup=lambda path, content: writes.append(path),
                read_backup=lambda path: source,
                save_snapshot=lambda proposed: writes.append("save"),
                rebuild_projection=lambda proposed: {},
            )
        self.assertEqual(writes, [])

    def test_apply_is_idempotent(self):
        initial = json.dumps(self.snapshot(), sort_keys=True).encode()
        saved = []
        backups = {}
        first = run_task_workflow_backfill(
            lambda: initial,
            self.permissions,
            apply=True,
            expected_source_sha256=__import__("hashlib").sha256(initial).hexdigest(),
            backup_path="first.bak",
            server_stopped_confirmed=True,
            write_backup=lambda path, content: backups.setdefault(path, content),
            read_backup=lambda path: backups[path],
            save_snapshot=saved.append,
            rebuild_projection=lambda proposed: {"ok": True},
        )
        canonical = json.dumps(saved[0], sort_keys=True).encode()
        second = run_task_workflow_backfill(
            lambda: canonical,
            self.permissions,
            apply=True,
            expected_source_sha256=__import__("hashlib").sha256(canonical).hexdigest(),
            backup_path="second.bak",
            server_stopped_confirmed=True,
            write_backup=lambda path, content: backups.setdefault(path, content),
            read_backup=lambda path: backups[path],
            save_snapshot=saved.append,
            rebuild_projection=lambda proposed: {"ok": True},
        )
        self.assertEqual(first["changed_task_ids"], ["task_1"])
        self.assertEqual(second["changed_task_ids"], [])
        self.assertFalse(second["backup_created"])
        self.assertEqual(len(saved), 1)

    def test_projection_failure_does_not_replace_or_rollback_canonical_snapshot(self):
        source = json.dumps(self.snapshot(), sort_keys=True).encode()
        saved = []
        backup = {}
        result = run_task_workflow_backfill(
            lambda: source,
            self.permissions,
            apply=True,
            expected_source_sha256=__import__("hashlib").sha256(source).hexdigest(),
            backup_path="isolated.bak",
            server_stopped_confirmed=True,
            write_backup=lambda path, content: backup.setdefault(path, content),
            read_backup=lambda path: backup[path],
            save_snapshot=saved.append,
            rebuild_projection=lambda proposed: (_ for _ in ()).throw(RuntimeError("projection failed")),
        )
        self.assertTrue(result["canonical_mutated"])
        self.assertFalse(result["projection_mutated"])
        self.assertEqual(result["projection_error"], "projection failed")
        self.assertEqual(saved[0]["ops_by_project"]["project_a"]["activities"][0]["tasks"][0]["assignee_user_id"], "user_assignee")

    def test_cli_style_isolated_apply_creates_verified_backup_before_save(self):
        source_snapshot = self.snapshot()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            canonical_path = root / "canonical.json"
            backup_path = root / "canonical.json.test.assignment-routing.bak"
            canonical_path.write_text(json.dumps(source_snapshot), encoding="utf-8")
            original = canonical_path.read_bytes()
            events = []

            def write_backup(path, content):
                events.append("backup")
                Path(path).write_bytes(content)

            def save_snapshot(snapshot):
                events.append("save")
                canonical_path.write_text(json.dumps(snapshot), encoding="utf-8")

            result = run_task_workflow_backfill(
                canonical_path.read_bytes,
                self.permissions,
                apply=True,
                expected_source_sha256=__import__("hashlib").sha256(original).hexdigest(),
                backup_path=str(backup_path),
                server_stopped_confirmed=True,
                write_backup=write_backup,
                read_backup=lambda path: Path(path).read_bytes(),
                save_snapshot=save_snapshot,
                rebuild_projection=lambda proposed: {"rebuilt": True},
            )
            self.assertEqual(events, ["backup", "save"])
            self.assertEqual(backup_path.read_bytes(), original)
            self.assertTrue(result["projection"]["rebuilt"])


if __name__ == "__main__":
    unittest.main()
