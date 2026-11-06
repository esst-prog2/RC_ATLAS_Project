import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from logical_framework_api_tests import MODULE


class SecureInitializationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_path = str(Path(self.temp_dir.name) / "secure-setup.json")
        self.previous_env = {
            name: os.environ.get(name)
            for name in (
                "LOGITRACK_STORAGE_BACKEND",
                "LOGITRACK_DATA_PATH",
                "LOGITRACK_SQLITE_PATH",
                "LOGITRACK_ENABLE_RELATIONAL_MIRROR",
                "LOGITRACK_ENABLE_REPOSITORY_DOMAINS",
                "LOGITRACK_SETUP_ENABLED",
                "LOGITRACK_SETUP_TOKEN",
                "LOGITRACK_DEMO_SETUP_ENABLED",
            )
        }
        os.environ["LOGITRACK_STORAGE_BACKEND"] = "json"
        os.environ["LOGITRACK_DATA_PATH"] = self.data_path
        os.environ.pop("LOGITRACK_SQLITE_PATH", None)
        os.environ["LOGITRACK_ENABLE_RELATIONAL_MIRROR"] = "false"
        os.environ["LOGITRACK_ENABLE_REPOSITORY_DOMAINS"] = "false"
        os.environ["LOGITRACK_SETUP_ENABLED"] = "true"
        os.environ["LOGITRACK_SETUP_TOKEN"] = "synthetic-one-time-setup-token"
        os.environ["LOGITRACK_DEMO_SETUP_ENABLED"] = "false"
        self.client = TestClient(MODULE.app)

    def tearDown(self):
        self.client.close()
        for name, value in self.previous_env.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        self.temp_dir.cleanup()

    @staticmethod
    def bootstrap_payload():
        return {
            "organization_id": "org_secure_setup",
            "organization_name": "Secure Setup Organization",
            "username": "secure.admin",
            "email": "secure.admin@example.test",
            "full_name": "Secure Admin",
            "password": "SyntheticPassword!123",
        }

    def test_failed_login_telemetry_does_not_block_one_time_setup(self):
        failed = self.client.post(
            "/v1/auth/login",
            json={"username": "unknown", "password": "WrongPassword!123"},
        )
        self.assertEqual(failed.status_code, 401, failed.text)
        telemetry = MODULE.load_data_from_path()
        self.assertEqual(len(telemetry.audit_events), 1)
        self.assertTrue(MODULE.workspace_is_uninitialized(telemetry))

        setup = self.client.post(
            "/v1/auth/bootstrap",
            headers={"X-Setup-Token": "synthetic-one-time-setup-token"},
            json=self.bootstrap_payload(),
        )
        self.assertEqual(setup.status_code, 200, setup.text)
        self.assertNotIn("token", setup.json())
        self.assertNotIn("saved_to", setup.json())
        self.assertNotIn("password", setup.text.lower())
        initialized = MODULE.load_data_from_path()
        self.assertEqual(len(initialized.organizations), 1)
        self.assertEqual(len(initialized.users), 1)
        self.assertEqual(len(initialized.sessions), 0)

        repeated = self.client.post(
            "/v1/auth/bootstrap",
            headers={"X-Setup-Token": "synthetic-one-time-setup-token"},
            json=self.bootstrap_payload(),
        )
        self.assertEqual(repeated.status_code, 409, repeated.text)
        self.assertEqual(len(MODULE.load_data_from_path().users), 1)

    def test_setup_and_demo_seed_are_denied_by_default_without_mutation(self):
        os.environ["LOGITRACK_SETUP_ENABLED"] = "false"
        os.environ["LOGITRACK_DEMO_SETUP_ENABLED"] = "false"
        bootstrap = self.client.post("/v1/auth/bootstrap", json=self.bootstrap_payload())
        demo = self.client.post("/v1/demo/seed")
        self.assertEqual(bootstrap.status_code, 403, bootstrap.text)
        self.assertEqual(demo.status_code, 403, demo.text)
        self.assertFalse(Path(self.data_path).exists())

    def test_setup_requires_out_of_band_authorization_and_configuration(self):
        missing = self.client.post("/v1/auth/bootstrap", json=self.bootstrap_payload())
        wrong = self.client.post(
            "/v1/auth/bootstrap",
            headers={"X-Setup-Token": "wrong-token"},
            json=self.bootstrap_payload(),
        )
        self.assertEqual(missing.status_code, 403, missing.text)
        self.assertEqual(wrong.status_code, 403, wrong.text)
        self.assertFalse(Path(self.data_path).exists())

        os.environ.pop("LOGITRACK_SETUP_TOKEN", None)
        unconfigured = self.client.post("/v1/auth/bootstrap", json=self.bootstrap_payload())
        self.assertEqual(unconfigured.status_code, 503, unconfigured.text)
        self.assertFalse(Path(self.data_path).exists())

    def test_setup_ui_is_hidden_unless_trusted_mode_is_fully_configured(self):
        configured = self.client.get("/studio")
        self.assertEqual(configured.status_code, 200, configured.text)
        self.assertIn('data-trusted-setup="enabled"', configured.text)
        self.assertNotIn('hidden data-trusted-setup="disabled"', configured.text)

        os.environ.pop("LOGITRACK_SETUP_TOKEN", None)
        hidden = self.client.get("/studio")
        self.assertEqual(hidden.status_code, 200, hidden.text)
        self.assertIn('hidden data-trusted-setup="disabled"', hidden.text)

    def test_demo_seed_requires_the_same_out_of_band_setup_authorization(self):
        os.environ["LOGITRACK_DEMO_SETUP_ENABLED"] = "true"
        missing = self.client.post("/v1/demo/seed")
        wrong = self.client.post(
            "/v1/demo/seed",
            headers={"X-Setup-Token": "wrong-token"},
        )
        self.assertEqual(missing.status_code, 403, missing.text)
        self.assertEqual(wrong.status_code, 403, wrong.text)
        self.assertFalse(Path(self.data_path).exists())

    def test_authorized_demo_seed_never_returns_credentials_token_or_path(self):
        os.environ["LOGITRACK_DEMO_SETUP_ENABLED"] = "true"
        response = self.client.post(
            "/v1/demo/seed",
            headers={"X-Setup-Token": "synthetic-one-time-setup-token"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertNotIn("credentials", body)
        self.assertNotIn("login", body)
        self.assertNotIn("token", response.text.lower())
        self.assertNotIn("password", response.text.lower())
        self.assertNotIn("saved_to", body)
        self.assertNotIn(self.temp_dir.name, response.text)


if __name__ == "__main__":
    unittest.main()
