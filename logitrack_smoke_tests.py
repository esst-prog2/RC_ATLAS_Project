import os
import tempfile
import unittest
from contextlib import contextmanager
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from logitrack_platform.relational_store import (
    get_relational_store_status,
    sync_snapshot_to_relational_store,
)
from logitrack_platform.runtime import RepeatingRuntimeWorker


MODULE_PATH = Path(__file__).with_name("LogiTrackRC v4.4.py")
SPEC = spec_from_file_location("logitrack_rc_v4_4_source_tests", MODULE_PATH)
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


class LogiTrackSmokeTests(unittest.TestCase):
    def test_json_storage_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            json_path = str(Path(tmp_dir) / "logitrack_data.json")
            data = MODULE.LogiTrackData(
                users=[
                    MODULE.UserAccount(
                        id="user_admin",
                        username="admin",
                        role="admin",
                        created_at=MODULE.now_iso_utc(),
                        updated_at=MODULE.now_iso_utc(),
                    )
                ]
            )
            with patched_env(
                LOGITRACK_STORAGE_BACKEND="json",
                LOGITRACK_DATA_PATH=json_path,
                LOGITRACK_SQLITE_PATH=None,
            ):
                saved_to = MODULE.save_data_to_path(data)
                loaded = MODULE.load_data_from_path()
                status = MODULE.get_storage_status()

            self.assertEqual(saved_to, json_path)
            self.assertEqual(len(loaded.users), 1)
            self.assertEqual(loaded.users[0].username, "admin")
            self.assertEqual(status["backend"], "json")
            self.assertTrue(status["exists"])

    def test_sqlite_storage_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            sqlite_path = str(Path(tmp_dir) / "logitrack_data.sqlite3")
            data = MODULE.LogiTrackData(
                users=[
                    MODULE.UserAccount(
                        id="user_manager",
                        username="manager",
                        role="manager",
                        created_at=MODULE.now_iso_utc(),
                        updated_at=MODULE.now_iso_utc(),
                    )
                ]
            )
            with patched_env(
                LOGITRACK_STORAGE_BACKEND="sqlite",
                LOGITRACK_SQLITE_PATH=sqlite_path,
                LOGITRACK_DATA_PATH=str(Path(tmp_dir) / "legacy.json"),
            ):
                saved_to = MODULE.save_data_to_path(data)
                loaded = MODULE.load_data_from_path()
                status = MODULE.get_storage_status()

            self.assertEqual(saved_to, sqlite_path)
            self.assertEqual(len(loaded.users), 1)
            self.assertEqual(loaded.users[0].role, "manager")
            self.assertEqual(status["backend"], "sqlite")
            self.assertTrue(status["exists"])
            self.assertGreaterEqual(status["revisions"], 1)

    def test_dashboard_layout_generation(self):
        visuals = [
            {"chart_type": "kpi_cards", "title": "Overview"},
            {"chart_type": "line_trend", "title": "Trend"},
            {"chart_type": "heatmap", "title": "Heatmap"},
        ]
        layout = MODULE.build_dashboard_layout_from_visuals(visuals)

        self.assertEqual(len(layout), 3)
        self.assertEqual(layout[1]["column_span"], 2)
        self.assertEqual(layout[2]["row_span"], 2)

    def test_relational_store_sync(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            json_path = str(Path(tmp_dir) / "logitrack_data.json")
            relational_path = str(Path(tmp_dir) / "logitrack_relational.sqlite3")
            data = MODULE.LogiTrackData(
                projects=[
                    MODULE.Project(
                        id="proj_1",
                        name="Water Access",
                        objective="Improve rural coverage",
                        indicators=[
                            MODULE.Indicator(
                                id="ind_1",
                                name="Coverage",
                                unit="%",
                                frequency="monthly",
                                direction="up",
                                level="outcome",
                                target=80,
                                baseline=40,
                                locations=[],
                            )
                        ],
                    )
                ],
                users=[
                    MODULE.UserAccount(
                        id="user_1",
                        username="admin",
                        role="admin",
                        created_at=MODULE.now_iso_utc(),
                        updated_at=MODULE.now_iso_utc(),
                    )
                ],
            )
            with patched_env(
                LOGITRACK_STORAGE_BACKEND="json",
                LOGITRACK_DATA_PATH=json_path,
                LOGITRACK_ENABLE_RELATIONAL_MIRROR="true",
                LOGITRACK_RELATIONAL_STORE_PATH=relational_path,
            ):
                MODULE.save_data_to_path(data)
                status = get_relational_store_status(relational_path)

            self.assertTrue(status["exists"])
            self.assertEqual(status["counts"]["projects"], 1)
            self.assertEqual(status["counts"]["indicators"], 1)
            self.assertEqual(status["counts"]["users"], 1)

    def test_runtime_worker_run_once(self):
        runs = {"count": 0}

        def handler():
            runs["count"] += 1
            return {"runs": runs["count"]}

        worker = RepeatingRuntimeWorker("test-worker", handler=handler, interval_seconds=1, enabled=True)
        result = worker.run_once()
        status = worker.status()

        self.assertEqual(result["runs"], 1)
        self.assertEqual(status["last_result"]["runs"], 1)
        self.assertTrue(status["last_run_at"])


if __name__ == "__main__":
    unittest.main()
