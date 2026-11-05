import unittest
from types import SimpleNamespace
from unittest.mock import patch

from services.notifications import NotificationService


class NotificationIntegrationTests(unittest.TestCase):
    def test_sendgrid_service_uses_adapter_keyword_contract(self):
        calls = []

        def fake_sendgrid_adapter(
            notifications,
            api_key,
            sender_email,
            recipients,
            subject=None,
        ):
            calls.append({
                "notifications": notifications,
                "api_key": api_key,
                "sender_email": sender_email,
                "recipients": recipients,
                "subject": subject,
            })
            return {"accepted": len(recipients)}

        dependencies = SimpleNamespace(
            optional_text_field=lambda payload, field, default="": str(payload.get(field, default) or ""),
            dispatch_notifications_to_sendgrid_email=fake_sendgrid_adapter,
        )
        service = NotificationService(dependencies)

        with patch.dict("os.environ", {
            "LOGITRACK_SENDGRID_API_KEY": "synthetic-test-key",
            "LOGITRACK_SENDGRID_FROM": "sender@example.test",
        }):
            result, provider = service._dispatch_email(
                notifications=[{"id": "notice-1"}],
                payload={
                    "sendgrid_api_key": "untrusted-request-key",
                    "sendgrid_from": "untrusted@example.test",
                    "subject": "Synthetic notice",
                },
                recipients=["recipient@example.test"],
                provider="sendgrid",
            )

        self.assertEqual(provider, "sendgrid")
        self.assertEqual(result, {"accepted": 1})
        self.assertEqual(calls[0]["sender_email"], "sender@example.test")
        self.assertEqual(calls[0]["api_key"], "synthetic-test-key")


if __name__ == "__main__":
    unittest.main()
