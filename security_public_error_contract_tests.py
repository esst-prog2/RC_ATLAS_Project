import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from logical_framework_api_tests import MODULE
from services.demo_seed import build_demo_seed_bundle


class SecurityPublicErrorContractTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_path = str(Path(self.temp_dir.name) / "public-errors.json")
        self.previous_env = {
            name: os.environ.get(name)
            for name in (
                "LOGITRACK_STORAGE_BACKEND",
                "LOGITRACK_DATA_PATH",
                "LOGITRACK_SQLITE_PATH",
                "LOGITRACK_ENABLE_RELATIONAL_MIRROR",
                "LOGITRACK_ENABLE_REPOSITORY_DOMAINS",
            )
        }
        os.environ["LOGITRACK_STORAGE_BACKEND"] = "json"
        os.environ["LOGITRACK_DATA_PATH"] = self.data_path
        os.environ.pop("LOGITRACK_SQLITE_PATH", None)
        os.environ["LOGITRACK_ENABLE_RELATIONAL_MIRROR"] = "false"
        os.environ["LOGITRACK_ENABLE_REPOSITORY_DOMAINS"] = "false"
        data = MODULE.from_serializable(build_demo_seed_bundle(MODULE.build_password_hash).payload)
        user = MODULE.find_user_by_username(data, "org.admin")
        self.token = "public-error-contract-token"
        MODULE.register_session_for_token(data, user, self.token)
        MODULE.save_data_to_path(data)
        self.client = TestClient(MODULE.app)

    def tearDown(self):
        self.client.close()
        for name, value in self.previous_env.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        self.temp_dir.cleanup()

    def headers(self):
        return {"X-Auth-Token": self.token}

    def project_payload(self):
        return {
            "project_name": "Error Boundary Project",
            "programme": "Synthetic Programme",
            "donor": "Synthetic Donor",
            "implementing_partner": "Synthetic Partner",
            "sector": "Governance",
            "description": "Synthetic test project",
            "country": "Testland",
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
        }

    def test_load_failure_redacts_path_exception_and_secret(self):
        raw_detail = f"invalid file {self.data_path} password=VerySecret"
        with patch.object(MODULE, "load_data_from_path", side_effect=RuntimeError(raw_detail)):
            response = self.client.get("/v1/dashboard/summary", headers=self.headers())
        self.assertEqual(response.status_code, 500, response.text)
        body = response.text
        self.assertIn("workspace data is unavailable", body.lower())
        self.assertNotIn(self.data_path, body)
        self.assertNotIn("VerySecret", body)
        self.assertNotIn("RuntimeError", body)

    def test_save_failure_redacts_path_exception_and_preserves_canonical_state(self):
        before = MODULE.to_serializable(MODULE.load_data_from_path())
        raw_detail = f"cannot write {self.data_path} token=secret-token"
        with patch.object(MODULE, "save_data_to_path", side_effect=OSError(raw_detail)):
            response = self.client.post(
                "/v1/admin/projects",
                headers={**self.headers(), "X-Idempotency-Key": "error-boundary-create"},
                json=self.project_payload(),
            )
        self.assertEqual(response.status_code, 500, response.text)
        self.assertIn("workspace could not be saved", response.text.lower())
        self.assertNotIn(self.data_path, response.text)
        self.assertNotIn("secret-token", response.text)
        self.assertEqual(MODULE.to_serializable(MODULE.load_data_from_path()), before)

    def test_successful_write_returns_no_filesystem_path(self):
        response = self.client.post(
            "/v1/admin/projects",
            headers={**self.headers(), "X-Idempotency-Key": "safe-write-response"},
            json=self.project_payload(),
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["saved_to"], "canonical_store")
        self.assertNotIn(self.temp_dir.name, response.text)

    def test_health_contract_redacts_internal_paths_and_raw_errors(self):
        payload = MODULE.build_health_payload(
            storage={
                "backend": "json",
                "target_path": self.data_path,
                "exists": True,
                "size_bytes": 123,
                "error": f"bad storage at {self.data_path}",
            },
            runtime_status={
                "scheduler": {"enabled": False, "thread_alive": False, "last_run_at": "", "last_error": ""},
                "relational_store": {"enabled": True, "path": self.data_path, "error": "raw relation error"},
                "repository_domains": {"enabled": True, "path": self.data_path, "error": "raw repository error"},
            },
            cors_origins=[],
            allow_credentials=False,
            loaded_data=MODULE.load_data_from_path(),
            data_error=f"parse failed at {self.data_path}",
        )
        serialized = str(payload)
        self.assertNotIn(self.data_path, serialized)
        self.assertNotIn("parse failed", serialized)
        self.assertNotIn("raw relation error", serialized)
        self.assertNotIn("raw repository error", serialized)
        self.assertEqual(payload["data_error"], "Workspace data unavailable.")

    def test_cors_is_same_origin_only_by_default(self):
        with patch.dict(os.environ, {"LOGITRACK_API_ALLOW_ORIGINS": ""}, clear=False):
            self.assertEqual(MODULE.get_cors_origins(), [])


if __name__ == "__main__":
    unittest.main()
