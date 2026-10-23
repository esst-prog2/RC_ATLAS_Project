import copy
import hashlib
import json
import unittest

from migration.activity_ownership_backfill import (
    ALREADY_CORRECT,
    AMBIGUOUS_PROJECT,
    CONFLICTING_OWNERSHIP,
    ORPHAN_PROJECT,
    SAFE_TO_BACKFILL,
    ActivityOwnershipBackfillError,
    build_activity_ownership_backfill_plan,
    run_activity_ownership_backfill,
)


class ActivityOwnershipBackfillTests(unittest.TestCase):
    def snapshot(self):
        return {
            "organizations": [
                {"id": "org-a"},
                {"id": "org-b"},
            ],
            "projects": [
                {"id": "project-safe", "organization_id": "org-a"},
                {"id": "project-correct", "organization_id": "org-a"},
                {"id": "project-conflict", "organization_id": "org-a"},
                {"id": "project-ambiguous", "organization_id": "org-a"},
                {"id": "project-ambiguous", "organization_id": "org-b"},
            ],
            "ops_by_project": {
                "project-safe": {"activities": [{"id": "activity-safe", "organization_id": ""}]},
                "project-correct": {"activities": [{"id": "activity-correct", "organization_id": "org-a"}]},
                "project-conflict": {"activities": [{"id": "activity-conflict", "organization_id": "org-b"}]},
                "project-ambiguous": {"activities": [{"id": "activity-ambiguous", "organization_id": ""}]},
                "project-orphan": {"activities": [{"id": "activity-orphan", "organization_id": ""}]},
            },
        }

    def test_dry_run_classifies_without_mutating_source(self):
        snapshot = self.snapshot()
        before = copy.deepcopy(snapshot)

        plan = build_activity_ownership_backfill_plan(snapshot)

        self.assertEqual(snapshot, before)
        self.assertEqual(plan.report["counts"][SAFE_TO_BACKFILL], 1)
        self.assertEqual(plan.report["counts"][ALREADY_CORRECT], 1)
        self.assertEqual(plan.report["counts"][CONFLICTING_OWNERSHIP], 1)
        self.assertEqual(plan.report["counts"][AMBIGUOUS_PROJECT], 1)
        self.assertEqual(plan.report["counts"][ORPHAN_PROJECT], 1)
        self.assertFalse(plan.report["canonical_mutated"])
        self.assertEqual(
            plan.proposed_snapshot["ops_by_project"]["project-safe"]["activities"][0]["organization_id"],
            "org-a",
        )
        self.assertEqual(
            plan.proposed_snapshot["ops_by_project"]["project-conflict"]["activities"][0]["organization_id"],
            "org-b",
        )

    def test_repeat_plan_is_idempotent(self):
        first = build_activity_ownership_backfill_plan(self.snapshot())
        second = build_activity_ownership_backfill_plan(first.proposed_snapshot)

        self.assertEqual(second.report["counts"][SAFE_TO_BACKFILL], 0)
        self.assertEqual(second.report["counts"][ALREADY_CORRECT], 2)
        self.assertEqual(second.proposed_snapshot, first.proposed_snapshot)

    def test_apply_requires_explicit_approval_and_reviewed_hash(self):
        source = json.dumps(self.snapshot(), sort_keys=True).encode("utf-8")
        digest = hashlib.sha256(source).hexdigest()

        with self.assertRaisesRegex(ActivityOwnershipBackfillError, "approved migration reference"):
            run_activity_ownership_backfill(
                lambda: source,
                apply=True,
                expected_source_sha256=digest,
                server_stopped_confirmed=True,
            )

    def test_synthetic_apply_changes_only_safe_activity_and_repeat_is_noop(self):
        snapshot = self.snapshot()
        source = json.dumps(snapshot, sort_keys=True).encode("utf-8")
        digest = hashlib.sha256(source).hexdigest()
        backups = {}
        saved = []
        projections = []

        result = run_activity_ownership_backfill(
            lambda: source,
            apply=True,
            expected_source_sha256=digest,
            approval_reference="SYNTHETIC-TEST-ONLY",
            server_stopped_confirmed=True,
            backup_path="synthetic-backup.json",
            write_backup=lambda path, content: backups.__setitem__(path, content),
            read_backup=lambda path: backups[path],
            save_snapshot=lambda value: saved.append(copy.deepcopy(value)),
            rebuild_projection=lambda value: projections.append(copy.deepcopy(value)) or {"ok": True},
        )

        self.assertEqual(result["changed_activity_ids"], ["activity-safe"])
        self.assertTrue(result["backup_created"])
        self.assertTrue(result["canonical_mutated"])
        self.assertTrue(result["projection_mutated"])
        self.assertEqual(
            saved[0]["ops_by_project"]["project-safe"]["activities"][0]["organization_id"],
            "org-a",
        )
        self.assertEqual(
            saved[0]["ops_by_project"]["project-conflict"]["activities"][0]["organization_id"],
            "org-b",
        )

        rerun_source = json.dumps(saved[0], sort_keys=True).encode("utf-8")
        rerun = run_activity_ownership_backfill(
            lambda: rerun_source,
            apply=True,
            expected_source_sha256=hashlib.sha256(rerun_source).hexdigest(),
            approval_reference="SYNTHETIC-TEST-ONLY",
            server_stopped_confirmed=True,
            backup_path="unused.json",
            write_backup=lambda path, content: self.fail("repeat run must not create a backup"),
            read_backup=lambda path: b"",
            save_snapshot=lambda value: self.fail("repeat run must not save"),
            rebuild_projection=lambda value: self.fail("repeat run must not rebuild"),
        )
        self.assertEqual(rerun["changed_activity_ids"], [])
        self.assertFalse(rerun["backup_created"])


if __name__ == "__main__":
    unittest.main()
