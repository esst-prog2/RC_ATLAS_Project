import os
import sqlite3
import tempfile
import unittest
from contextlib import contextmanager
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from logitrack_platform.relational_store import sync_snapshot_to_relational_store
from repositories.logical_framework_repository import LogicalFrameworkScope
from repositories.logical_framework_snapshot import SnapshotLogicalFrameworkRepository
from services.demo_seed import build_demo_seed_bundle
from services.logical_framework_service import (
    LogicalFrameworkService,
    LogicalFrameworkValidationError,
)
from shared import ResultNode


MODULE_PATH = Path(__file__).with_name("LogiTrackRC v4.4.py")
SPEC = spec_from_file_location("logitrack_rc_v4_4_logframe_tests", MODULE_PATH)
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


class StableIdFactory:
    def __init__(self):
        self.counts = {}

    def __call__(self, prefix):
        self.counts[prefix] = self.counts.get(prefix, 0) + 1
        return f"{prefix}_test_{self.counts[prefix]}"


class LogicalFrameworkFoundationTests(unittest.TestCase):
    def setUp(self):
        self.organization_id = "org_a"
        self.project_id = "project_a"
        self.other_project_id = "project_b"
        self.other_organization_id = "org_b"
        self.external_project_id = "project_c"
        self.timestamp = "2026-09-19T12:00:00Z"
        projects = [
            MODULE.Project(
                id=self.project_id,
                name="Project A",
                objective="Test project A",
                organization_id=self.organization_id,
                indicators=[
                    MODULE.Indicator(
                        id="indicator_a",
                        name="Indicator A",
                        unit="people",
                        frequency="monthly",
                        direction="up",
                        level="outcome",
                        target=100,
                        baseline=0,
                        organization_id=self.organization_id,
                        project_id=self.project_id,
                    ),
                    MODULE.Indicator(
                        id="indicator_a2",
                        name="Indicator A2",
                        unit="sites",
                        frequency="quarterly",
                        direction="up",
                        level="output",
                        target=10,
                        baseline=0,
                        organization_id=self.organization_id,
                        project_id=self.project_id,
                    ),
                ],
            ),
            MODULE.Project(
                id=self.other_project_id,
                name="Project B",
                objective="Test project B",
                organization_id=self.organization_id,
                indicators=[
                    MODULE.Indicator(
                        id="indicator_b",
                        name="Indicator B",
                        unit="people",
                        frequency="monthly",
                        direction="up",
                        level="outcome",
                        target=50,
                        baseline=0,
                        organization_id=self.organization_id,
                        project_id=self.other_project_id,
                    )
                ],
            ),
            MODULE.Project(
                id=self.external_project_id,
                name="Project C",
                objective="Test project C",
                organization_id=self.other_organization_id,
                indicators=[
                    MODULE.Indicator(
                        id="indicator_c",
                        name="Indicator C",
                        unit="people",
                        frequency="monthly",
                        direction="up",
                        level="outcome",
                        target=25,
                        baseline=0,
                        organization_id=self.other_organization_id,
                        project_id=self.external_project_id,
                    )
                ],
            ),
        ]
        self.data = MODULE.LogiTrackData(projects=projects)
        self.repository = SnapshotLogicalFrameworkRepository(
            self.data,
            LogicalFrameworkScope(self.organization_id, self.project_id),
        )
        self.service = LogicalFrameworkService(
            self.repository,
            now=lambda: self.timestamp,
            id_factory=StableIdFactory(),
        )

    def create_hierarchy(self):
        goal = self.service.create_goal(
            self.organization_id,
            self.project_id,
            "Improved wellbeing",
            result_id="goal_a",
            display_order=2,
        )
        outcome = self.service.create_outcome(
            self.organization_id,
            self.project_id,
            goal.id,
            "Households adopt improved practices",
            result_id="outcome_a",
            display_order=3,
        )
        output = self.service.create_output(
            self.organization_id,
            self.project_id,
            outcome.id,
            "Training delivered",
            result_id="output_a",
            display_order=4,
        )
        return goal, outcome, output

    def test_goal_outcome_output_persist_with_correct_hierarchy(self):
        goal, outcome, output = self.create_hierarchy()
        self.assertEqual(outcome.parent_id, goal.id)
        self.assertEqual(output.parent_id, outcome.id)
        self.assertEqual(
            [node.result_type for node in self.repository.list_results()],
            ["goal", "outcome", "output"],
        )
        tree = self.service.get_hierarchy(self.organization_id, self.project_id)
        self.assertEqual(tree[0]["outcomes"][0]["outputs"][0].id, output.id)

    def test_multiple_goals_are_supported(self):
        first = self.service.create_goal(
            self.organization_id, self.project_id, "First Goal", result_id="goal_1"
        )
        second = self.service.create_goal(
            self.organization_id, self.project_id, "Second Goal", result_id="goal_2"
        )
        self.assertNotEqual(first.id, second.id)
        self.assertEqual(len(self.repository.list_results()), 2)

    def test_duplicate_result_id_is_rejected(self):
        self.service.create_goal(
            self.organization_id, self.project_id, "Original Goal", result_id="goal_duplicate"
        )
        with self.assertRaises(LogicalFrameworkValidationError):
            self.service.create_goal(
                self.organization_id, self.project_id, "Replacement Goal", result_id="goal_duplicate"
            )

    def test_goal_cannot_have_result_parent(self):
        with self.assertRaises(LogicalFrameworkValidationError):
            self.service.create_result(
                self.organization_id,
                self.project_id,
                "goal",
                "Invalid Goal",
                result_id="goal_invalid",
                parent_id="some_parent",
            )
        with self.assertRaises(ValueError):
            ResultNode(
                id="goal_invalid_domain",
                organization_id=self.organization_id,
                project_id=self.project_id,
                result_type="goal",
                title="Invalid Goal",
                parent_id="some_parent",
            )

    def test_invalid_parent_levels_are_rejected(self):
        goal, outcome, output = self.create_hierarchy()
        with self.assertRaises(LogicalFrameworkValidationError):
            self.service.create_outcome(
                self.organization_id,
                self.project_id,
                outcome.id,
                "Outcome cannot parent Outcome",
            )
        with self.assertRaises(LogicalFrameworkValidationError):
            self.service.create_outcome(
                self.organization_id,
                self.project_id,
                output.id,
                "Output cannot parent Outcome",
            )
        with self.assertRaises(LogicalFrameworkValidationError):
            self.service.create_output(
                self.organization_id,
                self.project_id,
                goal.id,
                "Goal cannot directly parent Output",
            )

    def test_unknown_and_self_parent_are_rejected(self):
        with self.assertRaises(LogicalFrameworkValidationError):
            self.service.create_outcome(
                self.organization_id,
                self.project_id,
                "missing_goal",
                "Unknown parent",
            )
        with self.assertRaises(LogicalFrameworkValidationError):
            self.service.create_result(
                self.organization_id,
                self.project_id,
                "outcome",
                "Self parent",
                result_id="outcome_self",
                parent_id="outcome_self",
            )

    def test_cross_project_parenting_is_rejected(self):
        goal = self.service.create_goal(
            self.organization_id, self.project_id, "Project A Goal", result_id="goal_project_a"
        )
        with self.assertRaises(LogicalFrameworkValidationError):
            self.service.create_outcome(
                self.organization_id,
                self.other_project_id,
                goal.id,
                "Cross-project Outcome",
            )

    def test_cross_organization_parenting_is_rejected(self):
        goal = self.service.create_goal(
            self.organization_id, self.project_id, "Organization A Goal", result_id="goal_org_a"
        )
        with self.assertRaises(LogicalFrameworkValidationError):
            self.service.create_outcome(
                self.other_organization_id,
                self.external_project_id,
                goal.id,
                "Cross-organization Outcome",
            )

    def test_result_level_transition_is_rejected(self):
        goal = self.service.create_goal(
            self.organization_id, self.project_id, "Stable Goal", result_id="goal_stable"
        )
        with self.assertRaises(LogicalFrameworkValidationError):
            self.service.update_result(
                self.organization_id,
                self.project_id,
                goal.id,
                result_type="outcome",
            )

    def test_indicators_link_to_one_outcome_or_output(self):
        _, outcome, output = self.create_hierarchy()
        outcome_link = self.service.link_indicator(
            self.organization_id, self.project_id, "indicator_a", outcome.id
        )
        output_link = self.service.link_indicator(
            self.organization_id, self.project_id, "indicator_a2", output.id
        )
        self.assertEqual(outcome_link.result_type, "outcome")
        self.assertEqual(output_link.result_type, "output")

        relinked = self.service.link_indicator(
            self.organization_id, self.project_id, "indicator_a", output.id
        )
        self.assertEqual(relinked.id, outcome_link.id)
        self.assertEqual(relinked.result_id, output.id)
        self.assertEqual(len(self.repository.list_indicator_links()), 2)

    def test_indicator_may_remain_unassigned_and_cannot_link_to_goal(self):
        goal = self.service.create_goal(
            self.organization_id, self.project_id, "Goal", result_id="goal_unassigned"
        )
        self.assertIsNone(
            self.repository.get_indicator_link("indicator_a")
        )
        with self.assertRaises(LogicalFrameworkValidationError):
            self.service.link_indicator(
                self.organization_id, self.project_id, "indicator_a", goal.id
            )

    def test_cross_project_indicator_link_is_rejected(self):
        other_service = LogicalFrameworkService(
            SnapshotLogicalFrameworkRepository(
                self.data,
                LogicalFrameworkScope(
                    self.organization_id, self.other_project_id
                ),
            ),
            now=lambda: self.timestamp,
            id_factory=StableIdFactory(),
        )
        goal = other_service.create_goal(
            self.organization_id, self.other_project_id, "Project B Goal", result_id="goal_b"
        )
        outcome = other_service.create_outcome(
            self.organization_id,
            self.other_project_id,
            goal.id,
            "Project B Outcome",
            result_id="outcome_b",
        )
        with self.assertRaises(LogicalFrameworkValidationError):
            other_service.link_indicator(
                self.organization_id, self.other_project_id, "indicator_a", outcome.id
            )

    def test_cross_organization_indicator_link_is_rejected(self):
        external_service = LogicalFrameworkService(
            SnapshotLogicalFrameworkRepository(
                self.data,
                LogicalFrameworkScope(
                    self.other_organization_id, self.external_project_id
                ),
            ),
            now=lambda: self.timestamp,
            id_factory=StableIdFactory(),
        )
        goal = external_service.create_goal(
            self.other_organization_id,
            self.external_project_id,
            "Organization B Goal",
            result_id="goal_c",
        )
        outcome = external_service.create_outcome(
            self.other_organization_id,
            self.external_project_id,
            goal.id,
            "Organization B Outcome",
            result_id="outcome_c",
        )
        with self.assertRaises(LogicalFrameworkValidationError):
            external_service.link_indicator(
                self.other_organization_id,
                self.external_project_id,
                "indicator_a",
                outcome.id,
            )

    def test_legacy_indicator_ownership_is_backfilled_without_id_change(self):
        payload = {
            "projects": [
                {
                    "id": "legacy_project",
                    "name": "Legacy Project",
                    "objective": "Legacy objective",
                    "organization_id": "legacy_org",
                    "indicators": [
                        {
                            "id": "legacy_indicator",
                            "name": "Legacy Indicator",
                            "unit": "%",
                            "frequency": "monthly",
                            "direction": "up",
                            "level": "outcome",
                            "target": 80,
                            "baseline": 40,
                            "locations": [],
                        }
                    ],
                }
            ]
        }
        loaded = MODULE.from_serializable(payload)
        indicator = loaded.projects[0].indicators[0]
        self.assertEqual(indicator.id, "legacy_indicator")
        self.assertEqual(indicator.organization_id, "legacy_org")
        self.assertEqual(indicator.project_id, "legacy_project")
        self.assertEqual(loaded.indicator_result_links, [])

    def test_conflicting_explicit_indicator_ownership_is_rejected(self):
        payload = {
            "projects": [
                {
                    "id": "project_owner",
                    "name": "Owned Project",
                    "objective": "Ownership check",
                    "organization_id": "org_owner",
                    "indicators": [
                        {
                            "id": "indicator_conflict",
                            "name": "Conflicting Indicator",
                            "unit": "%",
                            "frequency": "monthly",
                            "direction": "up",
                            "level": "outcome",
                            "target": 80,
                            "baseline": 40,
                            "locations": [],
                            "organization_id": "org_other",
                            "project_id": "project_owner",
                        }
                    ],
                }
            ]
        }
        with self.assertRaises(ValueError):
            MODULE.from_serializable(payload)

    def test_old_snapshot_without_logframe_loads_as_empty(self):
        loaded = MODULE.from_serializable({"projects": []})
        self.assertEqual(loaded.logical_framework_results, [])
        self.assertEqual(loaded.indicator_result_links, [])

    def test_hierarchy_survives_json_and_sqlite_snapshot_roundtrips(self):
        goal, outcome, output = self.create_hierarchy()
        self.service.link_indicator(
            self.organization_id, self.project_id, "indicator_a", outcome.id
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            for backend in ("json", "sqlite"):
                with self.subTest(backend=backend):
                    path = str(Path(tmp_dir) / f"state.{backend}")
                    if backend == "json":
                        MODULE.save_json(self.data, path)
                        loaded = MODULE.load_json(path)
                    else:
                        MODULE.save_sqlite(self.data, path)
                        loaded = MODULE.load_sqlite(path)
                    self.assertEqual(
                        [node.id for node in loaded.logical_framework_results],
                        [goal.id, outcome.id, output.id],
                    )
                    self.assertEqual(loaded.indicator_result_links[0].result_id, outcome.id)
                    self.assertEqual(loaded.logical_framework_results[2].created_at, self.timestamp)

    def test_relational_projection_preserves_hierarchy_links_and_ownership(self):
        goal, outcome, output = self.create_hierarchy()
        self.service.link_indicator(
            self.organization_id, self.project_id, "indicator_a", output.id
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = str(Path(tmp_dir) / "warehouse.sqlite3")
            result = sync_snapshot_to_relational_store(
                MODULE.to_serializable(self.data),
                db_path=db_path,
            )
            self.assertEqual(result["counts"]["logical_framework_results"], 3)
            self.assertEqual(result["counts"]["indicator_result_links"], 1)
            conn = sqlite3.connect(db_path)
            try:
                rows = conn.execute(
                    "SELECT result_id, result_type, parent_result_id, display_order FROM logical_framework_results ORDER BY display_order"
                ).fetchall()
                link = conn.execute(
                    "SELECT organization_id, project_id, indicator_id, result_id FROM indicator_result_links"
                ).fetchone()
                indicator_owner = conn.execute(
                    "SELECT organization_id, project_id FROM indicators WHERE indicator_id = ?",
                    ("indicator_a",),
                ).fetchone()
            finally:
                conn.close()
        self.assertEqual(rows, [
            (goal.id, "goal", None, 2),
            (outcome.id, "outcome", goal.id, 3),
            (output.id, "output", outcome.id, 4),
        ])
        self.assertEqual(link, (self.organization_id, self.project_id, "indicator_a", output.id))
        self.assertEqual(indicator_owner, (self.organization_id, self.project_id))

    def test_ordering_and_timestamps_survive_updates(self):
        goal = self.service.create_goal(
            self.organization_id,
            self.project_id,
            "Ordered Goal",
            result_id="goal_ordered",
            display_order=8,
        )
        updated = self.service.reorder_result(
            self.organization_id, self.project_id, goal.id, 1
        )
        self.assertEqual(updated.display_order, 1)
        self.assertEqual(updated.created_at, self.timestamp)
        self.assertEqual(updated.updated_at, self.timestamp)

    def test_malformed_persisted_hierarchy_is_rejected(self):
        payload = {
            "projects": [
                {
                    "id": self.project_id,
                    "name": "Project A",
                    "objective": "Objective",
                    "organization_id": self.organization_id,
                    "indicators": [],
                }
            ],
            "logical_framework_results": [
                {
                    "id": "orphan_outcome",
                    "organization_id": self.organization_id,
                    "project_id": self.project_id,
                    "result_type": "outcome",
                    "title": "Orphan Outcome",
                    "parent_id": "missing_goal",
                }
            ],
        }
        with self.assertRaises(LogicalFrameworkValidationError):
            MODULE.from_serializable(payload)

    def test_demo_indicator_and_reporting_contract_remains_intact(self):
        bundle = build_demo_seed_bundle(MODULE.build_password_hash)
        loaded = MODULE.from_serializable(bundle.payload)
        indicator_ids = [indicator.id for project in loaded.projects for indicator in project.indicators]
        record_ids = [record.id for record in loaded.reporting_records]
        self.assertEqual(len(loaded.projects), 3)
        self.assertEqual(len(indicator_ids), 9)
        self.assertEqual(len(record_ids), 108)
        self.assertEqual(len(set(indicator_ids)), 9)
        self.assertEqual(len(set(record_ids)), 108)
        self.assertTrue(MODULE.build_project_trend_series(loaded, loaded.projects[0].id))
        self.assertEqual(loaded.logical_framework_results, [])
        self.assertEqual(loaded.indicator_result_links, [])


if __name__ == "__main__":
    unittest.main()
