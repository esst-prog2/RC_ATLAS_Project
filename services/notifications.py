import os
import smtplib
from dataclasses import asdict, dataclass
from typing import Any, Callable, Dict, List, Optional
from urllib import error as urlerror

from .errors import ServiceError
from .tenant_security import (
    find_scoped_dataset,
    find_scoped_project,
    notification_rule_organization_id,
    scope_snapshot_for_tenant,
)


SUPPORTED_V1_CHANNELS = frozenset({"in_app", "email"})
DEFERRED_CHANNELS = frozenset({"webhook", "whatsapp", "sms"})
REQUEST_SECRET_FIELDS = frozenset({
    "smtp_password",
    "smtp_username",
    "sendgrid_api_key",
    "twilio_account_sid",
    "twilio_auth_token",
    "meta_whatsapp_token",
})


@dataclass(frozen=True)
class NotificationServiceDependencies:
    load_data: Callable[[], Any]
    save_data: Callable[[Any], str]
    authorize_request: Callable[[Any, Optional[str], Optional[str], str], Any]
    append_audit_event: Callable[..., None]
    find_notification_rule: Callable[[Any, str], Any]
    build_notification_rule_from_payload: Callable[[Dict[str, Any], Optional[Any]], Any]
    upsert_notification_rule: Callable[[Any, Any], str]
    is_notification_rule_due: Callable[[Any, Optional[Any]], bool]
    evaluate_notification_rule: Callable[[Any, Any], List[Dict[str, Any]]]
    build_current_notifications: Callable[[Any], List[Dict[str, Any]]]
    filter_notifications: Callable[[List[Dict[str, Any]], str, Optional[int]], List[Dict[str, Any]]]
    optional_text_field: Callable[..., str]
    parse_recipients: Callable[[Any], List[str]]
    now_iso_utc: Callable[[], str]
    utc_now: Callable[[], Any]
    dispatch_notifications_to_webhook: Callable[[List[Dict[str, Any]], str], Dict[str, Any]]
    dispatch_notifications_to_email: Callable[..., Dict[str, Any]]
    dispatch_notifications_to_sendgrid_email: Callable[..., Dict[str, Any]]
    dispatch_notifications_to_whatsapp_webhook: Callable[..., Dict[str, Any]]
    dispatch_notifications_to_twilio_whatsapp: Callable[..., Dict[str, Any]]
    dispatch_notifications_to_meta_whatsapp: Callable[..., Dict[str, Any]]
    notification_channels_status: Callable[[], Dict[str, Any]]


class NotificationService:
    def __init__(self, deps: NotificationServiceDependencies):
        self.deps = deps

    def _tenant_data(self, x_api_key: Optional[str], x_auth_token: Optional[str], permission: str) -> tuple[Any, Any]:
        data = self.deps.load_data()
        actor = self.deps.authorize_request(data, x_api_key, x_auth_token, required_permission=permission)
        return data, actor

    def _find_scoped_rule(self, data: Any, organization_id: str, rule_id: str) -> Any:
        return next(
            (
                rule for rule in data.notification_rules
                if str(rule.id) == str(rule_id)
                and notification_rule_organization_id(data, rule) == organization_id
            ),
            None,
        )

    @staticmethod
    def _email_enabled() -> bool:
        return str(os.getenv("LOGITRACK_EMAIL_ENABLED", "false") or "false").strip().lower() in {"1", "true", "yes", "on"}

    def _require_dispatchable_channel(self, channel: str) -> None:
        normalized = str(channel or "").strip().lower()
        if normalized not in SUPPORTED_V1_CHANNELS:
            raise ServiceError(400, "Unsupported notification channel for v1. Use 'in_app' or 'email'.")
        if normalized == "email" and not self._email_enabled():
            raise ServiceError(503, "Email delivery is disabled until the approved provider sandbox gate passes.")

    @staticmethod
    def _reject_request_secrets(payload: Dict[str, Any]) -> None:
        supplied = sorted(key for key in REQUEST_SECRET_FIELDS if payload.get(key) not in (None, ""))
        if supplied:
            raise ServiceError(400, "Provider credentials must be supplied through deployment configuration, not request bodies.")

    def channel_status(self, x_api_key: Optional[str], x_auth_token: Optional[str]) -> Dict[str, Any]:
        self._tenant_data(x_api_key, x_auth_token, "VIEW_NOTIFICATIONS")
        return self.deps.notification_channels_status()

    def list_notifications(self, min_severity: str = "info", max_items: int = 50, x_api_key: Optional[str] = None, x_auth_token: Optional[str] = None) -> Dict[str, Any]:
        data, actor = self._tenant_data(x_api_key, x_auth_token, "VIEW_NOTIFICATIONS")
        notifications = self.deps.build_current_notifications(scope_snapshot_for_tenant(data, actor))
        return {
            "generated_at": self.deps.now_iso_utc(),
            "count": len(notifications),
            "items": self.deps.filter_notifications(notifications, min_severity=min_severity, max_items=max_items),
        }

    def list_rules(self, x_api_key: Optional[str], x_auth_token: Optional[str]) -> List[Dict[str, Any]]:
        data = self.deps.load_data()
        actor = self.deps.authorize_request(data, x_api_key, x_auth_token, required_permission="MANAGE_NOTIFICATIONS")
        items = []
        for rule in data.notification_rules:
            if notification_rule_organization_id(data, rule) != actor.organization_id:
                continue
            item = asdict(rule)
            channel = str(rule.channel or "").strip().lower()
            item["dispatch_enabled"] = channel == "in_app" or (channel == "email" and self._email_enabled())
            item["migration_required"] = channel not in SUPPORTED_V1_CHANNELS
            items.append(item)
        return items

    def save_rule(
        self,
        payload: Dict[str, Any],
        x_api_key: Optional[str],
        x_auth_token: Optional[str],
    ) -> Dict[str, Any]:
        data = self.deps.load_data()
        actor = self.deps.authorize_request(data, x_api_key, x_auth_token, required_permission="MANAGE_NOTIFICATIONS")
        requested_id = str(payload.get("id") or '').strip()
        existing = self._find_scoped_rule(data, actor.organization_id, requested_id) if requested_id else None
        if requested_id and self.deps.find_notification_rule(data, requested_id) is not None and existing is None:
            raise ServiceError(404, f"Notification rule '{requested_id}' not found.")
        project_id = str(payload.get('project_id') or (existing.project_id if existing else '')).strip()
        dataset_id = str(payload.get('dataset_id') or (existing.dataset_id if existing else '')).strip()
        if project_id and find_scoped_project(data, actor.organization_id, project_id) is None:
            raise ServiceError(404, f"Project '{project_id}' not found.")
        if dataset_id and find_scoped_dataset(data, actor.organization_id, dataset_id) is None:
            raise ServiceError(404, f"Tidy dataset '{dataset_id}' not found.")
        try:
            rule = self.deps.build_notification_rule_from_payload(payload, existing=existing)
        except ValueError as exc:
            raise ServiceError(400, str(exc)) from exc

        rule.organization_id = actor.organization_id
        action = self.deps.upsert_notification_rule(data, rule)
        self.deps.append_audit_event(
            data,
            action=f"notification_rule.{action}",
            target_type="notification_rule",
            target_id=rule.id,
            actor=actor,
            endpoint="/v1/notification_rules",
            details={"name": rule.name, "channel": rule.channel, "provider": rule.provider, "schedule": rule.schedule},
        )
        saved_path = self.deps.save_data(data)
        return {
            "ok": True,
            "action": action,
            "saved_to": saved_path,
            "rule": asdict(rule),
        }

    def run_rule(
        self,
        rule_id: str,
        payload: Dict[str, Any],
        x_api_key: Optional[str],
        x_auth_token: Optional[str],
    ) -> Dict[str, Any]:
        data = self.deps.load_data()
        actor = self.deps.authorize_request(data, x_api_key, x_auth_token, required_permission="MANAGE_NOTIFICATIONS")
        rule = self._find_scoped_rule(data, actor.organization_id, rule_id)
        if rule is None:
            raise ServiceError(404, f"Notification rule '{rule_id}' not found.")
        result = self.execute_rule(
            data=data,
            rule=rule,
            payload=payload,
            actor=actor,
            endpoint=f"/v1/notification_rules/{rule_id}/run",
            update_when_empty=False,
            evaluation_data=scope_snapshot_for_tenant(data, actor),
        )
        self.deps.save_data(data)
        return result

    def run_due_rules(
        self,
        payload: Dict[str, Any],
        x_api_key: Optional[str],
        x_auth_token: Optional[str],
    ) -> Dict[str, Any]:
        data = self.deps.load_data()
        actor = self.deps.authorize_request(data, x_api_key, x_auth_token, required_permission="MANAGE_NOTIFICATIONS")
        batch_result = self.run_due_rules_batch(
            data=data,
            payload=payload,
            actor=actor,
            endpoint="/v1/notification_rules/run_due",
            organization_id=actor.organization_id,
        )
        self.deps.append_audit_event(
            data,
            action="notification_rule.run_due",
            target_type="notification_rule",
            target_id="batch",
            actor=actor,
            endpoint="/v1/notification_rules/run_due",
            details={"checked_rules": batch_result["checked_rules"], "ran_rules": batch_result["ran_rules"]},
        )
        self.deps.save_data(data)
        return {
            "ok": True,
            "checked_rules": batch_result["checked_rules"],
            "due_rules": batch_result["due_rules"],
            "ran_rules": batch_result["ran_rules"],
            "results": batch_result["results"],
        }

    def dispatch_notifications(
        self,
        payload: Dict[str, Any],
        x_api_key: Optional[str],
        x_auth_token: Optional[str],
    ) -> Dict[str, Any]:
        data = self.deps.load_data()
        actor = self.deps.authorize_request(data, x_api_key, x_auth_token, required_permission="MANAGE_NOTIFICATIONS")
        min_severity = self.deps.optional_text_field(payload, "min_severity", "medium") or "medium"
        max_items_raw = payload.get("max_items", 20)
        try:
            max_items = int(max_items_raw)
        except Exception as exc:
            raise ServiceError(400, "'max_items' must be an integer.") from exc

        notifications = self.deps.filter_notifications(
            self.deps.build_current_notifications(scope_snapshot_for_tenant(data, actor)),
            min_severity=min_severity,
            max_items=max_items,
        )
        if not notifications:
            self.deps.append_audit_event(
                data,
                action="notifications.dispatch",
                target_type="notification_batch",
                target_id="current",
                actor=actor,
                endpoint="/v1/notifications/dispatch",
                details={"matched_notifications": 0, "channel": payload.get("channel", "webhook")},
            )
            self.deps.save_data(data)
            return {
                "ok": True,
                "dispatched": False,
                "reason": "No notifications matched the requested severity filter.",
                "items": [],
            }

        result = self.dispatch_by_channel(notifications, payload)
        self.deps.append_audit_event(
            data,
            action="notifications.dispatch",
            target_type="notification_batch",
            target_id="current",
            actor=actor,
            endpoint="/v1/notifications/dispatch",
            details={"matched_notifications": len(notifications), "channel": result.get("channel"), "provider": result.get("provider")},
        )
        self.deps.save_data(data)
        return result

    def build_dispatch_payload_for_rule(self, rule: Any, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        supplied = dict(payload or {})
        forbidden = {
            "channel", "provider", "email_to", "whatsapp_to", "webhook_url", "whatsapp_webhook_url",
            *REQUEST_SECRET_FIELDS,
        }
        if forbidden.intersection(supplied):
            raise ServiceError(400, "Stored notification routing cannot be overridden when a rule is executed.")
        dispatch_payload = {"channel": rule.channel, "provider": rule.provider}
        if rule.channel == "email":
            dispatch_payload["email_to"] = list(rule.recipients or [])
        return dispatch_payload

    def execute_rule(
        self,
        data: Any,
        rule: Any,
        payload: Optional[Dict[str, Any]] = None,
        actor: Optional[Any] = None,
        endpoint: str = "",
        update_when_empty: bool = False,
        evaluation_data: Optional[Any] = None,
    ) -> Dict[str, Any]:
        self._require_dispatchable_channel(str(rule.channel or ""))
        notifications = self.deps.evaluate_notification_rule(evaluation_data or data, rule)
        if not notifications:
            if update_when_empty:
                rule.last_run_at = self.deps.now_iso_utc()
                rule.updated_at = self.deps.now_iso_utc()
                self.deps.upsert_notification_rule(data, rule)
            self.deps.append_audit_event(
                data,
                action="notification_rule.run",
                target_type="notification_rule",
                target_id=rule.id,
                actor=actor,
                endpoint=endpoint,
                details={"matched_notifications": 0},
            )
            return {
                "ok": True,
                "rule_id": rule.id,
                "dispatched": False,
                "reason": "No notifications matched the rule conditions.",
                "items": [],
            }

        dispatch_payload = self.build_dispatch_payload_for_rule(rule, payload)
        result = self.dispatch_by_channel(notifications, dispatch_payload)
        rule.last_run_at = self.deps.now_iso_utc()
        rule.updated_at = self.deps.now_iso_utc()
        self.deps.upsert_notification_rule(data, rule)
        self.deps.append_audit_event(
            data,
            action="notification_rule.run",
            target_type="notification_rule",
            target_id=rule.id,
            actor=actor,
            endpoint=endpoint,
            details={"matched_notifications": len(notifications), "channel": result.get("channel"), "provider": result.get("provider")},
        )
        result["rule_id"] = rule.id
        return result

    def run_due_rules_batch(
        self,
        data: Any,
        payload: Optional[Dict[str, Any]] = None,
        actor: Optional[Any] = None,
        endpoint: str = "/v1/notification_rules/run_due",
        organization_id: str = "",
    ) -> Dict[str, Any]:
        now_dt = self.deps.utc_now()
        ran = []
        due_rules = 0
        checked_rules = 0
        evaluation_data = scope_snapshot_for_tenant(data, actor) if actor is not None else data
        for rule in data.notification_rules:
            if organization_id and notification_rule_organization_id(data, rule) != organization_id:
                continue
            checked_rules += 1
            if not self.deps.is_notification_rule_due(rule, now_dt=now_dt):
                continue
            due_rules += 1
            try:
                ran.append(
                    self.execute_rule(
                        data=data,
                        rule=rule,
                        payload=payload,
                        actor=actor,
                        endpoint=endpoint,
                        update_when_empty=True,
                        evaluation_data=evaluation_data,
                    )
                )
            except Exception as exc:
                rule.last_run_at = self.deps.now_iso_utc()
                rule.updated_at = self.deps.now_iso_utc()
                self.deps.upsert_notification_rule(data, rule)
                reason = exc.detail if isinstance(exc, ServiceError) else str(exc)
                self.deps.append_audit_event(
                    data,
                    action="notification_rule.run",
                    target_type="notification_rule",
                    target_id=rule.id,
                    actor=actor,
                    endpoint=endpoint,
                    outcome="failure",
                    details={"error": reason},
                )
                ran.append({
                    "ok": False,
                    "rule_id": rule.id,
                    "dispatched": False,
                    "reason": reason,
                })
        return {
            "checked_rules": checked_rules,
            "due_rules": due_rules,
            "ran_rules": len(ran),
            "results": ran,
        }

    def dispatch_by_channel(self, notifications: List[Dict[str, Any]], payload: Dict[str, Any]) -> Dict[str, Any]:
        self._reject_request_secrets(payload)
        channel = (self.deps.optional_text_field(payload, "channel", "in_app") or "in_app").strip().lower()
        self._require_dispatchable_channel(channel)
        provider = (self.deps.optional_text_field(payload, "provider") or "").strip().lower()
        email_to = self.deps.parse_recipients(payload.get("email_to")) or self.deps.parse_recipients(os.getenv("LOGITRACK_NOTIFY_EMAIL_TO", ""))

        if channel == "in_app":
            return {
                "ok": True,
                "dispatched": True,
                "items_sent": len(notifications),
                "channel": "in_app",
                "provider": "internal",
                "result": {"available_in_authenticated_feed": True},
            }

        try:
            if channel == "email":
                dispatch_result, provider = self._dispatch_email(notifications, payload, email_to, provider)
        except ServiceError:
            raise
        except urlerror.URLError as exc:
            raise ServiceError(502, "Notification provider request failed.") from exc
        except smtplib.SMTPException as exc:
            raise ServiceError(502, "Email delivery failed.") from exc
        except ValueError as exc:
            raise ServiceError(400, str(exc)) from exc
        except Exception as exc:
            raise ServiceError(500, "Notification delivery failed.") from exc

        return {
            "ok": True,
            "dispatched": True,
            "items_sent": len(notifications),
            "channel": channel,
            "provider": provider,
            "result": dispatch_result,
        }

    def _dispatch_email(
        self,
        notifications: List[Dict[str, Any]],
        payload: Dict[str, Any],
        recipients: List[str],
        provider: str,
    ) -> tuple[Dict[str, Any], str]:
        smtp_host = (os.getenv("LOGITRACK_SMTP_HOST", "") or "").strip()
        smtp_port_raw = os.getenv("LOGITRACK_SMTP_PORT", "587")
        smtp_from = (os.getenv("LOGITRACK_SMTP_FROM", "") or "").strip()
        smtp_username = (os.getenv("LOGITRACK_SMTP_USERNAME", "") or "").strip()
        smtp_password = os.getenv("LOGITRACK_SMTP_PASSWORD", "")
        sendgrid_api_key = (os.getenv("LOGITRACK_SENDGRID_API_KEY", "") or "").strip()
        sendgrid_from = (os.getenv("LOGITRACK_SENDGRID_FROM", "") or "").strip()
        smtp_subject = self.deps.optional_text_field(payload, "subject") or None
        use_tls_raw = payload.get("use_tls", os.getenv("LOGITRACK_SMTP_USE_TLS", "true"))
        use_tls = str(use_tls_raw).strip().lower() not in {"0", "false", "no"}

        if not provider:
            if smtp_host and smtp_from:
                provider = "smtp"
            elif sendgrid_api_key and sendgrid_from:
                provider = "sendgrid"
            else:
                provider = "smtp"

        if provider == "smtp":
            if not smtp_host or not smtp_from:
                return {
                    "ok": True,
                    "dispatched": False,
                    "reason": "Email channel requires SMTP configuration. Set LOGITRACK_SMTP_HOST and LOGITRACK_SMTP_FROM or choose provider 'sendgrid'.",
                    "items": notifications,
                }, provider
            try:
                smtp_port = int(smtp_port_raw)
            except Exception as exc:
                raise ServiceError(400, "'smtp_port' must be an integer.") from exc
            return self.deps.dispatch_notifications_to_email(
                notifications=notifications,
                smtp_host=smtp_host,
                smtp_port=smtp_port,
                smtp_from=smtp_from,
                recipients=recipients,
                smtp_username=smtp_username,
                smtp_password=smtp_password,
                use_tls=use_tls,
                subject=smtp_subject,
            ), provider

        if provider == "sendgrid":
            if not sendgrid_api_key or not sendgrid_from:
                return {
                    "ok": True,
                    "dispatched": False,
                    "reason": "SendGrid email requires LOGITRACK_SENDGRID_API_KEY and LOGITRACK_SENDGRID_FROM or request body equivalents.",
                    "items": notifications,
                }, provider
            return self.deps.dispatch_notifications_to_sendgrid_email(
                notifications=notifications,
                api_key=sendgrid_api_key,
                sender_email=sendgrid_from,
                recipients=recipients,
                subject=smtp_subject,
            ), provider

        raise ServiceError(400, "Unsupported email provider. Use 'smtp' or 'sendgrid'.")

    def _dispatch_whatsapp(
        self,
        notifications: List[Dict[str, Any]],
        payload: Dict[str, Any],
        recipients: List[str],
        webhook_url: str,
        provider: str,
    ) -> tuple[Dict[str, Any], str]:
        twilio_account_sid = (self.deps.optional_text_field(payload, "twilio_account_sid") or os.getenv("LOGITRACK_TWILIO_ACCOUNT_SID", "")).strip()
        twilio_auth_token = self.deps.optional_text_field(payload, "twilio_auth_token") or os.getenv("LOGITRACK_TWILIO_AUTH_TOKEN", "")
        twilio_from = (self.deps.optional_text_field(payload, "twilio_from") or os.getenv("LOGITRACK_TWILIO_WHATSAPP_FROM", "")).strip()
        meta_token = self.deps.optional_text_field(payload, "meta_whatsapp_token") or os.getenv("LOGITRACK_META_WHATSAPP_TOKEN", "")
        meta_phone_number_id = (self.deps.optional_text_field(payload, "meta_whatsapp_phone_number_id") or os.getenv("LOGITRACK_META_WHATSAPP_PHONE_NUMBER_ID", "")).strip()

        if not provider:
            if webhook_url:
                provider = "webhook"
            elif twilio_account_sid and twilio_auth_token and twilio_from:
                provider = "twilio"
            elif meta_token and meta_phone_number_id:
                provider = "meta_cloud"
            else:
                provider = "webhook"

        if provider == "webhook":
            if not webhook_url:
                return {
                    "ok": True,
                    "dispatched": False,
                    "reason": "WhatsApp webhook dispatch requires LOGITRACK_WHATSAPP_WEBHOOK_URL or whatsapp_webhook_url.",
                    "items": notifications,
                }, provider
            return self.deps.dispatch_notifications_to_whatsapp_webhook(
                notifications=notifications,
                webhook_url=webhook_url,
                recipients=recipients,
            ), provider

        if provider == "twilio":
            if not twilio_account_sid or not twilio_auth_token or not twilio_from:
                return {
                    "ok": True,
                    "dispatched": False,
                    "reason": "Twilio WhatsApp requires account SID, auth token, and from number.",
                    "items": notifications,
                }, provider
            return self.deps.dispatch_notifications_to_twilio_whatsapp(
                notifications=notifications,
                account_sid=twilio_account_sid,
                auth_token=twilio_auth_token,
                from_number=twilio_from,
                recipients=recipients,
            ), provider

        if provider in {"meta", "meta_cloud"}:
            provider = "meta_cloud"
            if not meta_token or not meta_phone_number_id:
                return {
                    "ok": True,
                    "dispatched": False,
                    "reason": "Meta WhatsApp Cloud requires access token and phone number id.",
                    "items": notifications,
                }, provider
            return self.deps.dispatch_notifications_to_meta_whatsapp(
                notifications=notifications,
                access_token=meta_token,
                phone_number_id=meta_phone_number_id,
                recipients=recipients,
            ), provider

        raise ServiceError(400, "Unsupported WhatsApp provider. Use 'webhook', 'twilio', or 'meta_cloud'.")
