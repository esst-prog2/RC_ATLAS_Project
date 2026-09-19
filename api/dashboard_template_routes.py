from typing import Any, Dict, Optional

from api.common import header_default, raise_http_error
from services.errors import ServiceError


def register_dashboard_template_routes(
    app: Any,
    service: Any,
    header_factory: Any = None,
    http_exception_cls: Optional[type[Exception]] = None,
) -> None:
    @app.get("/v1/dashboard_templates")
    def v1_dashboard_templates(dataset_id: Optional[str] = None):
        try:
            return service.list_templates(dataset_id=dataset_id)
        except ServiceError as exc:
            raise_http_error(exc, http_exception_cls)

    @app.post("/v1/dashboard_templates")
    def v1_save_dashboard_template(
        payload: Dict[str, Any],
        x_api_key: Optional[str] = header_default(header_factory, "X-API-Key"),
        x_auth_token: Optional[str] = header_default(header_factory, "X-Auth-Token"),
    ):
        try:
            return service.save_template(payload, x_api_key, x_auth_token)
        except ServiceError as exc:
            raise_http_error(exc, http_exception_cls)
