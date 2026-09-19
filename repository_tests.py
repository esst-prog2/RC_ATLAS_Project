import tempfile
import unittest
from pathlib import Path

from migration.sync_helpers import (
    hydrate_snapshot_with_repository_domains,
    sync_repository_backed_domains_from_snapshot,
)
from repositories.notification_rules import list_notification_rules, upsert_notification_rule
from repositories.reporting_records import list_reporting_records, upsert_reporting_records
from repositories.users import get_user_by_username, list_users, upsert_user


class RepositoryTests(unittest.TestCase):
    def test_users_repository_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = str(Path(tmp_dir) / "repo.sqlite3")
            user = {
                "id": "user_admin",
                "organization_id": "org_demo",
                "team_id": "team_demo",
                "username": "admin",
                "full_name": "Admin User",
                "email": "admin@example.org",
                "role": "admin",
                "password_salt": "salt",
                "password_hash": "hash",
                "api_token_hash": "tokenhash",
                "is_active": True,
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
                "last_login_at": "",
            }
            action = upsert_user(user, db_path=db_path)
            loaded = get_user_by_username("admin", db_path=db_path)

            self.assertEqual(action, "created")
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded["role"], "admin")
            self.assertEqual(loaded["team_id"], "team_demo")
            self.assertEqual(loaded["api_token_hash"], "tokenhash")

    def test_notification_rules_repository_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = str(Path(tmp_dir) / "repo.sqlite3")
            rule = {
                "id": "rule_1",
                "name": "Weekly KPI Alert",
                "is_active": True,
                "schedule": "weekly",
                "channel": "email",
                "provider": "smtp",
                "min_severity": "high",
                "condition_type": "progress_below",
                "threshold": 60,
                "project_id": "proj_1",
                "indicator_id": "",
                "dataset_id": "",
                "recipients": ["pm@example.org"],
                "webhook_url": "",
                "notes": "",
                "last_run_at": "",
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
            }
            upsert_notification_rule(rule, db_path=db_path)
            loaded = list_notification_rules(db_path=db_path)

            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0]["provider"], "smtp")
            self.assertEqual(loaded[0]["recipients"], ["pm@example.org"])

    def test_reporting_records_repository_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = str(Path(tmp_dir) / "repo.sqlite3")
            records = [
                {
                    "id": "rep_1",
                    "reporting_period": "2026-05-01",
                    "project_id": "proj_1",
                    "project_name": "Water Access",
                    "indicator_id": "ind_1",
                    "indicator_name": "Coverage",
                    "country": "Mozambique",
                    "province": "Nampula",
                    "district": "Mecuburi",
                    "actual_value": 52,
                    "target_value": 80,
                    "progress_value": 65,
                    "budget_value": 150000,
                    "currency": "MZN",
                    "status": "ongoing",
                    "owner": "MEAL",
                    "notes": "",
                    "source_dataset_id": "ds_1",
                    "created_at": "2026-05-02T00:00:00Z",
                    "updated_at": "2026-05-02T00:00:00Z",
                }
            ]
            result = upsert_reporting_records(records, db_path=db_path)
            loaded = list_reporting_records(db_path=db_path, project_id="proj_1")

            self.assertEqual(result["count"], 1)
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0]["indicator_name"], "Coverage")

    def test_sync_helpers_hydrate_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = str(Path(tmp_dir) / "repo.sqlite3")
            snapshot = {
                "users": [
                    {
                        "id": "user_1",
                        "username": "admin",
                        "full_name": "Admin",
                        "email": "admin@example.org",
                        "role": "admin",
                        "password_salt": "salt",
                        "password_hash": "hash",
                        "api_token_hash": "token",
                        "is_active": True,
                        "created_at": "2026-01-01T00:00:00Z",
                        "updated_at": "2026-01-01T00:00:00Z",
                        "last_login_at": "",
                    }
                ],
                "notification_rules": [],
                "reporting_records": [],
            }
            sync_repository_backed_domains_from_snapshot(snapshot, db_path=db_path)
            hydrated = hydrate_snapshot_with_repository_domains(
                {"users": [], "notification_rules": [], "reporting_records": []},
                db_path=db_path,
            )

            self.assertEqual(len(list_users(db_path=db_path)), 1)
            self.assertEqual(hydrated["users"][0]["username"], "admin")


if __name__ == "__main__":
    unittest.main()
