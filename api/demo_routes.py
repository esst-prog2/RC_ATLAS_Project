from typing import Any, Dict, Optional

from api.common import header_default, raise_http_error
from services.errors import ServiceError


def register_demo_routes(
    app: Any,
    service: Any,
    header_factory: Any = None,
    http_exception_cls: Optional[type[Exception]] = None,
) -> None:
    @app.post("/v1/demo/seed")
    def v1_demo_seed(
        x_api_key: Optional[str] = header_default(header_factory, "X-API-Key"),
        x_auth_token: Optional[str] = header_default(header_factory, "X-Auth-Token"),
    ):
        try:
            return service.seed_workspace(x_api_key, x_auth_token)
        except ServiceError as exc:
            raise_http_error(exc, http_exception_cls)

    @app.get("/v1/demo/workspace")
    def v1_demo_workspace(
        x_api_key: Optional[str] = header_default(header_factory, "X-API-Key"),
        x_auth_token: Optional[str] = header_default(header_factory, "X-Auth-Token"),
    ):
        try:
            return service.workspace_overview(x_api_key, x_auth_token)
        except ServiceError as exc:
            raise_http_error(exc, http_exception_cls)

    @app.get("/v1/demo/projects/{project_id}/executive_snapshot")
    def v1_demo_project_executive_snapshot(
        project_id: str,
        template_id: Optional[str] = None,
        x_api_key: Optional[str] = header_default(header_factory, "X-API-Key"),
        x_auth_token: Optional[str] = header_default(header_factory, "X-Auth-Token"),
    ):
        try:
            return service.project_executive_snapshot(project_id, template_id=template_id, x_api_key=x_api_key, x_auth_token=x_auth_token)
        except ServiceError as exc:
            raise_http_error(exc, http_exception_cls)

    @app.get("/v1/demo/projects/{project_id}/risks")
    def v1_demo_project_risks(
        project_id: str,
        x_api_key: Optional[str] = header_default(header_factory, "X-API-Key"),
        x_auth_token: Optional[str] = header_default(header_factory, "X-Auth-Token"),
    ):
        try:
            return service.project_risks(project_id, x_api_key=x_api_key, x_auth_token=x_auth_token)
        except ServiceError as exc:
            raise_http_error(exc, http_exception_cls)

    @app.get("/v1/demo/projects/{project_id}/workplan")
    def v1_demo_project_workplan(
        project_id: str,
        x_api_key: Optional[str] = header_default(header_factory, "X-API-Key"),
        x_auth_token: Optional[str] = header_default(header_factory, "X-Auth-Token"),
    ):
        try:
            return service.project_workplan_snapshot(project_id, x_api_key=x_api_key, x_auth_token=x_auth_token)
        except ServiceError as exc:
            raise_http_error(exc, http_exception_cls)

    @app.get("/v1/demo/data_quality")
    def v1_demo_data_quality(
        x_api_key: Optional[str] = header_default(header_factory, "X-API-Key"),
        x_auth_token: Optional[str] = header_default(header_factory, "X-Auth-Token"),
    ):
        try:
            return service.data_quality_overview(x_api_key, x_auth_token)
        except ServiceError as exc:
            raise_http_error(exc, http_exception_cls)

    @app.get("/v1/demo/narrative_summary")
    def v1_demo_narrative_summary(
        project_id: Optional[str] = None,
        x_api_key: Optional[str] = header_default(header_factory, "X-API-Key"),
        x_auth_token: Optional[str] = header_default(header_factory, "X-Auth-Token"),
    ):
        try:
            return service.narrative_summary(project_id=project_id, x_api_key=x_api_key, x_auth_token=x_auth_token)
        except ServiceError as exc:
            raise_http_error(exc, http_exception_cls)

    @app.post("/v1/demo/notifications/simulate")
    def v1_demo_notifications_simulate(
        payload: Dict[str, Any],
        x_api_key: Optional[str] = header_default(header_factory, "X-API-Key"),
        x_auth_token: Optional[str] = header_default(header_factory, "X-Auth-Token"),
    ):
        try:
            return service.simulate_notifications(payload, x_api_key, x_auth_token)
        except ServiceError as exc:
            raise_http_error(exc, http_exception_cls)

    @app.post("/v1/demo/tasks")
    def v1_demo_tasks_create(
        payload: Dict[str, Any],
        x_api_key: Optional[str] = header_default(header_factory, "X-API-Key"),
        x_auth_token: Optional[str] = header_default(header_factory, "X-Auth-Token"),
    ):
        try:
            return service.create_task(payload, x_api_key, x_auth_token)
        except ServiceError as exc:
            raise_http_error(exc, http_exception_cls)

    @app.post("/v1/demo/tasks/{task_id}/update")
    def v1_demo_tasks_update(
        task_id: str,
        payload: Dict[str, Any],
        x_api_key: Optional[str] = header_default(header_factory, "X-API-Key"),
        x_auth_token: Optional[str] = header_default(header_factory, "X-Auth-Token"),
    ):
        try:
            return service.update_task(task_id, payload, x_api_key, x_auth_token)
        except ServiceError as exc:
            raise_http_error(exc, http_exception_cls)

    @app.post("/v1/demo/tasks/{task_id}/validate")
    def v1_demo_tasks_validate(
        task_id: str,
        payload: Dict[str, Any],
        x_api_key: Optional[str] = header_default(header_factory, "X-API-Key"),
        x_auth_token: Optional[str] = header_default(header_factory, "X-Auth-Token"),
    ):
        try:
            return service.validate_task(task_id, payload, x_api_key, x_auth_token)
        except ServiceError as exc:
            raise_http_error(exc, http_exception_cls)

    @app.get("/v1/demo/report_preview")
    def v1_demo_report_preview(
        audience: str = "donor",
        project_id: Optional[str] = None,
        x_api_key: Optional[str] = header_default(header_factory, "X-API-Key"),
        x_auth_token: Optional[str] = header_default(header_factory, "X-Auth-Token"),
    ):
        try:
            return service.report_preview(audience=audience, project_id=project_id, x_api_key=x_api_key, x_auth_token=x_auth_token)
        except ServiceError as exc:
            raise_http_error(exc, http_exception_cls)
