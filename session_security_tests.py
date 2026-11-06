import os
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from logical_framework_api_tests import MODULE
from services.demo_seed import build_demo_seed_bundle


class SessionSecurityTests(unittest.TestCase):
    ENV_NAMES = (
        "LOGITRACK_STORAGE_BACKEND",
        "LOGITRACK_DATA_PATH",
        "LOGITRACK_SQLITE_PATH",
        "LOGITRACK_ENABLE_RELATIONAL_MIRROR",
        "LOGITRACK_ENABLE_REPOSITORY_DOMAINS",
        "LOGITRACK_SESSION_IDLE_MINUTES",
        "LOGITRACK_SESSION_ABSOLUTE_HOURS",
        "LOGITRACK_ENVIRONMENT",
        "LOGITRACK_SESSION_COOKIE_SECURE",
        "LOGITRACK_SESSION_COOKIE_SAMESITE",
        "LOGITRACK_API_TOKEN_LOGIN_ENABLED",
        "LOGITRACK_PUBLIC_ORIGIN",
    )

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_path = str(Path(self.temp_dir.name) / "sessions.json")
        self.previous_env = {name: os.environ.get(name) for name in self.ENV_NAMES}
        os.environ.update({
            "LOGITRACK_STORAGE_BACKEND": "json",
            "LOGITRACK_DATA_PATH": self.data_path,
            "LOGITRACK_ENABLE_RELATIONAL_MIRROR": "false",
            "LOGITRACK_ENABLE_REPOSITORY_DOMAINS": "false",
            "LOGITRACK_SESSION_IDLE_MINUTES": "30",
            "LOGITRACK_SESSION_ABSOLUTE_HOURS": "8",
            "LOGITRACK_ENVIRONMENT": "development",
            "LOGITRACK_SESSION_COOKIE_SECURE": "false",
            "LOGITRACK_SESSION_COOKIE_SAMESITE": "lax",
            "LOGITRACK_API_TOKEN_LOGIN_ENABLED": "false",
        })
        os.environ.pop("LOGITRACK_SQLITE_PATH", None)
        os.environ.pop("LOGITRACK_PUBLIC_ORIGIN", None)
        self.bundle = build_demo_seed_bundle(MODULE.build_password_hash)
        MODULE.save_data_to_path(MODULE.from_serializable(self.bundle.payload))
        self.client = TestClient(MODULE.app)

    def tearDown(self):
        self.client.close()
        for name, value in self.previous_env.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        self.temp_dir.cleanup()

    def credential(self, username="org.admin"):
        return next(item for item in self.bundle.credentials if item.username == username)

    def login(self, username="org.admin"):
        credential = self.credential(username)
        response = self.client.post(
            "/v1/auth/login",
            json={"username": credential.username, "password": credential.password},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertNotIn("token", response.json())
        self.assertNotIn("csrf_token", response.json())
        self.assertTrue(self.csrf_token())
        return response

    def cookie_token(self):
        return self.client.cookies.get("rcatlas_session_dev")

    def csrf_token(self):
        return (
            self.client.cookies.get("rcatlas_csrf_dev")
            or self.client.cookies.get("__Host-rcatlas_csrf")
        )

    def test_browser_login_uses_httponly_host_cookie_and_hashed_secrets(self):
        login = self.login()
        cookie = login.headers.get("set-cookie", "")
        self.assertIn("rcatlas_session_dev=", cookie)
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=lax", cookie)
        self.assertIn("Path=/", cookie)
        self.assertNotIn("Domain=", cookie)
        self.assertNotIn("Secure", cookie)

        token = self.cookie_token()
        csrf_token = self.csrf_token()
        self.assertTrue(token)
        identity = self.client.get("/v1/auth/me")
        self.assertEqual(identity.status_code, 200, identity.text)

        serialized = Path(self.data_path).read_text(encoding="utf-8")
        self.assertNotIn(token, serialized)
        self.assertNotIn(csrf_token, serialized)
        persisted = MODULE.load_data_from_path()
        self.assertEqual(len(persisted.sessions), 1)
        self.assertTrue(persisted.sessions[0].csrf_token_hash)
        self.assertEqual(MODULE.find_user_by_username(persisted, "org.admin").api_token_hash, "")

    def test_csrf_is_required_rotated_and_origin_bound_for_cookie_writes(self):
        login = self.login()
        csrf_token = self.csrf_token()
        payload = {"contact_person": "Synthetic Session Test"}

        missing = self.client.patch("/v1/admin/organization", json=payload)
        self.assertEqual(missing.status_code, 403, missing.text)
        invalid = self.client.patch(
            "/v1/admin/organization",
            headers={"X-CSRF-Token": "invalid"},
            json=payload,
        )
        self.assertEqual(invalid.status_code, 403, invalid.text)
        cross_origin = self.client.patch(
            "/v1/admin/organization",
            headers={"X-CSRF-Token": csrf_token, "Origin": "https://attacker.invalid"},
            json=payload,
        )
        self.assertEqual(cross_origin.status_code, 403, cross_origin.text)

        refreshed = self.client.get("/v1/auth/csrf")
        self.assertEqual(refreshed.status_code, 200, refreshed.text)
        rotated = self.csrf_token()
        self.assertNotEqual(rotated, csrf_token)
        stale = self.client.patch(
            "/v1/admin/organization",
            headers={"X-CSRF-Token": csrf_token},
            json=payload,
        )
        self.assertEqual(stale.status_code, 403, stale.text)
        accepted = self.client.patch(
            "/v1/admin/organization",
            headers={"X-CSRF-Token": rotated, "Origin": "http://testserver"},
            json=payload,
        )
        self.assertEqual(accepted.status_code, 200, accepted.text)

    def test_logout_requires_csrf_revokes_session_and_clears_cookie(self):
        login = self.login()
        token = self.cookie_token()
        denied = self.client.post("/v1/auth/logout")
        self.assertEqual(denied.status_code, 403, denied.text)
        logout = self.client.post(
            "/v1/auth/logout",
            headers={"X-CSRF-Token": self.csrf_token()},
        )
        self.assertEqual(logout.status_code, 200, logout.text)
        self.assertIn("Max-Age=0", logout.headers.get("set-cookie", ""))
        self.assertEqual(self.client.get("/v1/auth/me").status_code, 401)

        probe = TestClient(MODULE.app)
        try:
            self.assertEqual(probe.get("/v1/auth/me", headers={"X-Auth-Token": token}).status_code, 401)
        finally:
            probe.close()
        reloaded = MODULE.load_data_from_path()
        self.assertTrue(reloaded.sessions[0].revoked_at)
        self.assertEqual(reloaded.sessions[0].revocation_reason, "logout")

    def test_login_rotates_an_existing_browser_session(self):
        self.login()
        old_token = self.cookie_token()
        self.login()
        new_token = self.cookie_token()
        self.assertNotEqual(new_token, old_token)
        data = MODULE.load_data_from_path()
        old_session = MODULE.find_session_by_token(data, old_token)
        self.assertEqual(old_session.revocation_reason, "login_rotation")

        probe = TestClient(MODULE.app)
        try:
            self.assertEqual(probe.get("/v1/auth/me", headers={"X-Auth-Token": old_token}).status_code, 401)
            self.assertEqual(probe.get("/v1/auth/me", headers={"X-Auth-Token": new_token}).status_code, 200)
        finally:
            probe.close()

    def test_idle_absolute_and_tenant_binding_fail_closed(self):
        self.login()
        token = self.cookie_token()
        data = MODULE.load_data_from_path()
        session = MODULE.find_session_by_token(data, token)
        session.idle_expires_at = (MODULE.utc_now() - timedelta(seconds=1)).isoformat()
        MODULE.save_data_to_path(data)
        self.assertEqual(self.client.get("/v1/auth/me").status_code, 401)

        self.client.cookies.clear()
        self.login()
        token = self.cookie_token()
        data = MODULE.load_data_from_path()
        session = MODULE.find_session_by_token(data, token)
        session.absolute_expires_at = (MODULE.utc_now() - timedelta(seconds=1)).isoformat()
        MODULE.save_data_to_path(data)
        self.assertEqual(self.client.get("/v1/auth/me").status_code, 401)

        self.client.cookies.clear()
        self.login()
        token = self.cookie_token()
        data = MODULE.load_data_from_path()
        session = MODULE.find_session_by_token(data, token)
        session.organization_id = "org_other"
        MODULE.save_data_to_path(data)
        self.assertEqual(self.client.get("/v1/auth/me").status_code, 401)

    def test_legacy_user_token_hash_is_not_an_authentication_source(self):
        data = MODULE.load_data_from_path()
        user = MODULE.find_user_by_username(data, "org.admin")
        legacy_token = "legacy-user-token"
        user.api_token_hash = MODULE.hash_with_sha256(legacy_token)
        MODULE.save_data_to_path(data)
        self.assertEqual(
            self.client.get("/v1/auth/me", headers={"X-Auth-Token": legacy_token}).status_code,
            401,
        )

    def test_revocation_survives_client_restart(self):
        login = self.login()
        token = self.cookie_token()
        self.assertEqual(
            self.client.post("/v1/auth/logout", headers={"X-CSRF-Token": self.csrf_token()}).status_code,
            200,
        )
        self.client.close()
        self.client = TestClient(MODULE.app)
        self.client.cookies.set("rcatlas_session_dev", token)
        self.assertEqual(self.client.get("/v1/auth/me").status_code, 401)

    def test_production_cookie_is_secure_and_insecure_production_fails_closed(self):
        self.client.close()
        os.environ["LOGITRACK_ENVIRONMENT"] = "production"
        os.environ["LOGITRACK_SESSION_COOKIE_SECURE"] = "true"
        self.client = TestClient(MODULE.app, base_url="https://testserver")
        login = self.login()
        cookie = login.headers.get("set-cookie", "")
        self.assertIn("__Host-rcatlas_session=", cookie)
        self.assertIn("Secure", cookie)
        self.assertIn("HttpOnly", cookie)
        self.assertNotIn("Domain=", cookie)

        self.client.close()
        os.environ["LOGITRACK_SESSION_COOKIE_SECURE"] = "false"
        self.client = TestClient(MODULE.app)
        credential = self.credential()
        rejected = self.client.post(
            "/v1/auth/login",
            json={"username": credential.username, "password": credential.password},
        )
        self.assertEqual(rejected.status_code, 503, rejected.text)

    def test_api_token_login_is_explicit_disabled_by_default_and_csrf_independent(self):
        credential = self.credential()
        payload = {"username": credential.username, "password": credential.password}
        disabled = self.client.post(
            "/v1/auth/login",
            headers={"X-Auth-Transport": "api-token"},
            json=payload,
        )
        self.assertEqual(disabled.status_code, 403, disabled.text)

        os.environ["LOGITRACK_API_TOKEN_LOGIN_ENABLED"] = "true"
        enabled = self.client.post(
            "/v1/auth/login",
            headers={"X-Auth-Transport": "api-token"},
            json=payload,
        )
        self.assertEqual(enabled.status_code, 200, enabled.text)
        token = enabled.json().get("token")
        self.assertTrue(token)
        self.assertNotIn("csrf_token", enabled.json())
        self.assertNotIn("rcatlas_session", enabled.headers.get("set-cookie", ""))
        self.assertEqual(self.client.get("/v1/auth/me", headers={"X-Auth-Token": token}).status_code, 200)
        self.assertEqual(self.client.post("/v1/auth/logout", headers={"X-Auth-Token": token}).status_code, 200)

    def test_cross_site_login_is_rejected(self):
        credential = self.credential()
        response = self.client.post(
            "/v1/auth/login",
            headers={"Origin": "https://attacker.invalid", "Sec-Fetch-Site": "cross-site"},
            json={"username": credential.username, "password": credential.password},
        )
        self.assertEqual(response.status_code, 403, response.text)
        self.assertEqual(MODULE.load_data_from_path().sessions, [])


if __name__ == "__main__":
    unittest.main()
