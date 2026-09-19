from typing import Any, Dict, Optional

from api.common import header_default, raise_http_error
from services.errors import ServiceError


def register_reporting_routes(
    app: Any,
    service: Any,
    header_factory: Any = None,
    http_exception_cls: Optional[type[Exception]] = None,
) -> None:
    @app.get("/v1/reporting_records")
    def v1_reporting_records(project_id: Optional[str] = None, indicator_id: Optional[str] = None, limit: int = 500):
        try:
            return service.list_reporting_records(project_id=project_id, indicator_id=indicator_id, limit=limit)
        except ServiceError as exc:
            raise_http_error(exc, http_exception_cls)

    @app.get("/v1/trends/portfolio")
    def v1_portfolio_trends():
        try:
            return service.portfolio_trends()
        except ServiceError as exc:
            raise_http_error(exc, http_exception_cls)

    @app.get("/v1/narratives/portfolio")
    def v1_portfolio_narrative():
        try:
            return service.portfolio_narrative()
        except ServiceError as exc:
            raise_http_error(exc, http_exception_cls)

    @app.get("/v1/projects/{project_id}/trends")
    def v1_project_trends(project_id: str):
        try:
            return service.project_trends(project_id)
        except ServiceError as exc:
            raise_http_error(exc, http_exception_cls)

    @app.get("/v1/projects/{project_id}/narrative")
    def v1_project_narrative(project_id: str):
        try:
            return service.project_narrative(project_id)
        except ServiceError as exc:
            raise_http_error(exc, http_exception_cls)

    @app.get("/v1/projects/{project_id}/indicators/{indicator_id}/trends")
    def v1_indicator_trends(project_id: str, indicator_id: str):
        try:
            return service.indicator_trends(project_id, indicator_id)
        except ServiceError as exc:
            raise_http_error(exc, http_exception_cls)

    @app.get("/v1/tidy_datasets")
    def v1_tidy_datasets():
        try:
            return service.list_tidy_datasets()
        except ServiceError as exc:
            raise_http_error(exc, http_exception_cls)

    @app.get("/v1/tidy_datasets/{dataset_id}")
    def v1_tidy_dataset_detail(dataset_id: str):
        try:
            return service.get_tidy_dataset_detail(dataset_id)
        except ServiceError as exc:
            raise_http_error(exc, http_exception_cls)

    @app.get("/v1/tidy_datasets/{dataset_id}/semantic_mapping")
    def v1_tidy_dataset_semantic_mapping(dataset_id: str):
        try:
            return service.get_tidy_dataset_semantic_mapping(dataset_id)
        except ServiceError as exc:
            raise_http_error(exc, http_exception_cls)

    @app.post("/v1/tidy_datasets/{dataset_id}/semantic_mapping")
    def v1_save_tidy_dataset_semantic_mapping(
        dataset_id: str,
        payload: Dict[str, Any],
        x_api_key: Optional[str] = header_default(header_factory, "X-API-Key"),
        x_auth_token: Optional[str] = header_default(header_factory, "X-Auth-Token"),
    ):
        try:
            return service.save_tidy_dataset_semantic_mapping(dataset_id, payload, x_api_key, x_auth_token)
        except ServiceError as exc:
            raise_http_error(exc, http_exception_cls)

    @app.get("/v1/tidy_datasets/{dataset_id}/quality")
    def v1_tidy_dataset_quality(dataset_id: str):
        try:
            return service.get_tidy_dataset_quality(dataset_id)
        except ServiceError as exc:
            raise_http_error(exc, http_exception_cls)

    @app.get("/v1/tidy_datasets/{dataset_id}/narrative")
    def v1_tidy_dataset_narrative(dataset_id: str):
        try:
            return service.get_tidy_dataset_narrative(dataset_id)
        except ServiceError as exc:
            raise_http_error(exc, http_exception_cls)

    @app.get("/v1/tidy_datasets/{dataset_id}/dashboard_blueprint")
    def v1_tidy_dataset_dashboard_blueprint(dataset_id: str, template_id: Optional[str] = None):
        try:
            return service.get_tidy_dataset_dashboard_blueprint(dataset_id, template_id=template_id)
        except ServiceError as exc:
            raise_http_error(exc, http_exception_cls)

    @app.get("/v1/tidy_datasets/{dataset_id}/history_mapping")
    def v1_tidy_dataset_history_mapping(dataset_id: str):
        try:
            return service.get_tidy_dataset_history_mapping(dataset_id)
        except ServiceError as exc:
            raise_http_error(exc, http_exception_cls)

    @app.get("/v1/tidy_datasets/{dataset_id}/dashboard_suggestions")
    def v1_tidy_dataset_dashboard_suggestions(dataset_id: str):
        try:
            return service.get_tidy_dataset_dashboard_suggestions(dataset_id)
        except ServiceError as exc:
            raise_http_error(exc, http_exception_cls)

    @app.post("/v1/tidy_datasets/import")
    def v1_import_tidy_dataset(
        payload: Dict[str, Any],
        x_api_key: Optional[str] = header_default(header_factory, "X-API-Key"),
        x_auth_token: Optional[str] = header_default(header_factory, "X-Auth-Token"),
    ):
        try:
            return service.import_tidy_dataset(payload, x_api_key, x_auth_token)
        except ServiceError as exc:
            raise_http_error(exc, http_exception_cls)

    @app.post("/v1/tidy_datasets/{dataset_id}/materialize_history")
    def v1_materialize_history(
        dataset_id: str,
        x_api_key: Optional[str] = header_default(header_factory, "X-API-Key"),
        x_auth_token: Optional[str] = header_default(header_factory, "X-Auth-Token"),
    ):
        try:
            return service.materialize_history(dataset_id, x_api_key, x_auth_token)
        except ServiceError as exc:
            raise_http_error(exc, http_exception_cls)

    @app.post("/v1/reporting_records/import")
    def v1_import_reporting_records(
        payload: Dict[str, Any],
        x_api_key: Optional[str] = header_default(header_factory, "X-API-Key"),
        x_auth_token: Optional[str] = header_default(header_factory, "X-Auth-Token"),
    ):
        try:
            return service.import_reporting_records(payload, x_api_key, x_auth_token)
        except ServiceError as exc:
            raise_http_error(exc, http_exception_cls)
