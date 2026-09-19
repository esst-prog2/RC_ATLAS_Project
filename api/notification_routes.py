from typing import Any, Dict, Optional

from api.common import header_default, raise_http_error
from services.errors import ServiceError


def register_notification_routes(
    app: Any,
    service: Any,
    header_factory: Any = None,
    http_exception_cls: Optional[type[Exception]] = None,
) -> None:
    @app.get("/v1/notification_channels")
    def v1_notification_channels():
        try:
            return service.channel_status()
        except ServiceError as exc:
            raise_http_error(exc, http_exception_cls)

    @app.get("/v1/notifications")
    def v1_notifications(min_severity: str = "info", max_items: int = 50):
        try:
            return service.list_notifications(min_severity=min_severity, max_items=max_items)
        except ServiceError as exc:
            raise_http_error(exc, http_exception_cls)

    @app.get("/v1/notification_rules")
    def v1_notification_rules(
        x_api_key: Optional[str] = header_default(header_factory, "X-API-Key"),
        x_auth_token: Optional[str] = header_default(header_factory, "X-Auth-Token"),
    ):
        try:
            return service.list_rules(x_api_key, x_auth_token)
        except ServiceError as exc:
            raise_http_error(exc, http_exception_cls)

    @app.post("/v1/notification_rules")
    def v1_save_notification_rule(
        payload: Dict[str, Any],
        x_api_key: Optional[str] = header_default(header_factory, "X-API-Key"),
        x_auth_token: Optional[str] = header_default(header_factory, "X-Auth-Token"),
    ):
        try:
            return service.save_rule(payload, x_api_key, x_auth_token)
        except ServiceError as exc:
            raise_http_error(exc, http_exception_cls)

    @app.post("/v1/notification_rules/{rule_id}/run")
    def v1_run_notification_rule(
        rule_id: str,
        payload: Dict[str, Any],
        x_api_key: Optional[str] = header_default(header_factory, "X-API-Key"),
        x_auth_token: Optional[str] = header_default(header_factory, "X-Auth-Token"),
    ):
        try:
            return service.run_rule(rule_id, payload, x_api_key, x_auth_token)
        except ServiceError as exc:
            raise_http_error(exc, http_exception_cls)

    @app.post("/v1/notification_rules/run_due")
    def v1_run_due_notification_rules(
        payload: Dict[str, Any],
        x_api_key: Optional[str] = header_default(header_factory, "X-API-Key"),
        x_auth_token: Optional[str] = header_default(header_factory, "X-Auth-Token"),
    ):
        try:
            return service.run_due_rules(payload, x_api_key, x_auth_token)
        except ServiceError as exc:
            raise_http_error(exc, http_exception_cls)

    @app.post("/v1/notifications/dispatch")
    def v1_dispatch_notifications(
        payload: Dict[str, Any],
        x_api_key: Optional[str] = header_default(header_factory, "X-API-Key"),
        x_auth_token: Optional[str] = header_default(header_factory, "X-Auth-Token"),
    ):
        try:
            return service.dispatch_notifications(payload, x_api_key, x_auth_token)
        except ServiceError as exc:
            raise_http_error(exc, http_exception_cls)
