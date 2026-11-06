import inspect
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from fastapi.testclient import TestClient

from logical_framework_api_tests import MODULE
from services.demo_seed import build_demo_seed_bundle


class NotificationChannelScopeTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_path = str(Path(self.temp_dir.name) / "notifications.json")
        self.previous_env = {
            name: os.environ.get(name)
            for name in (
                "LOGITRACK_STORAGE_BACKEND",
                "LOGITRACK_DATA_PATH",
                "LOGITRACK_SQLITE_PATH",
                "LOGITRACK_ENABLE_RELATIONAL_MIRROR",
                "LOGITRACK_ENABLE_REPOSITORY_DOMAINS",
                "LOGITRACK_EMAIL_ENABLED",
                "LOGITRACK_SMTP_HOST",
                "LOGITRACK_SMTP_FROM",
            )
        }
        os.environ["LOGITRACK_STORAGE_BACKEND"] = "json"
        os.environ["LOGITRACK_DATA_PATH"] = self.data_path
        os.environ.pop("LOGITRACK_SQLITE_PATH", None)
        os.environ["LOGITRACK_ENABLE_RELATIONAL_MIRROR"] = "false"
        os.environ["LOGITRACK_ENABLE_REPOSITORY_DOMAINS"] = "false"
        os.environ["LOGITRACK_EMAIL_ENABLED"] = "false"
        data = MODULE.from_serializable(build_demo_seed_bundle(MODULE.build_password_hash).payload)
        user = MODULE.find_user_by_username(data, "org.admin")
        self.token = "notification-channel-token"
        MODULE.register_session_for_token(data, user, self.token)
        MODULE.save_data_to_path(data)
        self.client = TestClient(MODULE.app)
        endpoint = next(
            route.endpoint
            for route in MODULE.app.routes
            if getattr(route, "path", "") == "/v1/notifications/dispatch"
        )
        self.service = inspect.getclosurevars(endpoint).nonlocals["service"]

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

    def test_deferred_channels_are_rejected_before_provider_dispatch(self):
        dispatcher = Mock(return_value={"ok": True})
        original = self.service.deps.dispatch_notifications_to_webhook
        object.__setattr__(self.service.deps, "dispatch_notifications_to_webhook", dispatcher)
        try:
            for channel in ("webhook", "whatsapp", "sms"):
                response = self.client.post(
                    "/v1/notifications/dispatch",
                    headers=self.headers(),
                    json={"channel": channel, "webhook_url": "https://example.invalid"},
                )
                self.assertEqual(response.status_code, 400, response.text)
            dispatcher.assert_not_called()
        finally:
            object.__setattr__(self.service.deps, "dispatch_notifications_to_webhook", original)

    def test_deferred_rule_cannot_be_created_and_legacy_rule_is_marked(self):
        rejected = self.client.post(
            "/v1/notification_rules",
            headers=self.headers(),
            json={"name": "Deferred webhook", "channel": "webhook"},
        )
        self.assertEqual(rejected.status_code, 400, rejected.text)

        data = MODULE.load_data_from_path()
        data.notification_rules.append(MODULE.NotificationRule(
            id="legacy_webhook_rule",
            name="Legacy Webhook",
            organization_id="org_blue_delta",
            channel="webhook",
        ))
        MODULE.save_data_to_path(data)
        rules = self.client.get("/v1/notification_rules", headers=self.headers())
        self.assertEqual(rules.status_code, 200, rules.text)
        legacy = next(item for item in rules.json() if item["id"] == "legacy_webhook_rule")
        self.assertTrue(legacy["migration_required"])
        self.assertFalse(legacy["dispatch_enabled"])
        run = self.client.post(
            "/v1/notification_rules/legacy_webhook_rule/run",
            headers=self.headers(),
            json={},
        )
        self.assertEqual(run.status_code, 400, run.text)

    def test_email_is_disabled_and_request_credentials_are_rejected(self):
        os.environ["LOGITRACK_SMTP_HOST"] = "smtp.example.test"
        os.environ["LOGITRACK_SMTP_FROM"] = "noreply@example.test"
        email_dispatcher = Mock(return_value={"ok": True})
        original = self.service.deps.dispatch_notifications_to_email
        object.__setattr__(self.service.deps, "dispatch_notifications_to_email", email_dispatcher)
        try:
            disabled = self.client.post(
                "/v1/notifications/dispatch",
                headers=self.headers(),
                json={"channel": "email", "email_to": ["sandbox@example.test"]},
            )
            self.assertEqual(disabled.status_code, 503, disabled.text)
            secret = self.client.post(
                "/v1/notifications/dispatch",
                headers=self.headers(),
                json={"channel": "email", "smtp_password": "request-secret"},
            )
            self.assertEqual(secret.status_code, 400, secret.text)
            self.assertNotIn("request-secret", secret.text)
            email_dispatcher.assert_not_called()
        finally:
            object.__setattr__(self.service.deps, "dispatch_notifications_to_email", original)

    def test_in_app_channel_uses_no_external_adapter(self):
        webhook = Mock(return_value={"ok": True})
        email = Mock(return_value={"ok": True})
        original_webhook = self.service.deps.dispatch_notifications_to_webhook
        original_email = self.service.deps.dispatch_notifications_to_email
        object.__setattr__(self.service.deps, "dispatch_notifications_to_webhook", webhook)
        object.__setattr__(self.service.deps, "dispatch_notifications_to_email", email)
        try:
            response = self.client.post(
                "/v1/notifications/dispatch",
                headers=self.headers(),
                json={"channel": "in_app", "min_severity": "info"},
            )
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()["channel"], "in_app")
            webhook.assert_not_called()
            email.assert_not_called()
        finally:
            object.__setattr__(self.service.deps, "dispatch_notifications_to_webhook", original_webhook)
            object.__setattr__(self.service.deps, "dispatch_notifications_to_email", original_email)


if __name__ == "__main__":
    unittest.main()
