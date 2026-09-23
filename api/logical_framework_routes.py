from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from api.common import header_default
from repositories.logical_framework_repository import (
    LogicalFrameworkPersistenceError,
    LogicalFrameworkProjectionError,
    LogicalFrameworkScope,
)
from services.logical_framework_application import (
    LogicalFrameworkActorContext,
    LogicalFrameworkApplication,
)
from services.logical_framework_service import (
    LogicalFrameworkConflictValidationError,
    LogicalFrameworkNotFoundValidationError,
    LogicalFrameworkScopeValidationError,
    LogicalFrameworkService,
    LogicalFrameworkValidationError,
)


@dataclass(frozen=True)
class LogicalFrameworkRouteDependencies:
    authorize_scope: Callable[..., LogicalFrameworkActorContext]
    application: LogicalFrameworkApplication


def register_logical_framework_routes(
    app: Any,
    deps: LogicalFrameworkRouteDependencies,
    header_factory: Any = None,
    http_exception_cls: Optional[type[Exception]] = None,
) -> None:
    def fail(status_code: int, detail: str) -> None:
        if http_exception_cls is None:
            raise RuntimeError(detail)
        raise http_exception_cls(status_code=status_code, detail=detail)

    def map_service_error(exc: LogicalFrameworkValidationError) -> None:
        if isinstance(exc, (LogicalFrameworkNotFoundValidationError, LogicalFrameworkScopeValidationError)):
            fail(404, "Logical Framework resource not found.")
        if isinstance(exc, LogicalFrameworkConflictValidationError):
            fail(409, str(exc))
        fail(400, str(exc))

    def map_persistence_error(exc: LogicalFrameworkPersistenceError) -> None:
        if isinstance(exc, LogicalFrameworkProjectionError):
            fail(
                500,
                "Canonical data was committed, but relational projection "
                f"synchronization failed: {exc}",
            )
        fail(500, f"Failed to save data: {exc}")

    def context(
        project_id: str,
        permission: str,
        x_api_key: Optional[str],
        x_auth_token: Optional[str],
    ):
        actor = deps.authorize_scope(
            project_id=project_id,
            permission=permission,
            x_api_key=x_api_key,
            x_auth_token=x_auth_token,
        )
        if actor is None:
            fail(401, "Logical Framework endpoints require an authenticated user.")
        return actor, LogicalFrameworkScope(actor.organization_id, project_id)

    def reject_fields(payload: Dict[str, Any], forbidden: set[str]) -> None:
        supplied = sorted(field for field in forbidden if field in payload)
        if supplied:
            fail(400, f"Fields cannot be changed through this endpoint: {', '.join(supplied)}.")

    def result_status(payload: Dict[str, Any], default: str = "active") -> str:
        status = str(payload.get("status", default) or default).strip().lower()
        if status not in {"active", "draft"}:
            fail(400, "Result status must be 'active' or 'draft'; use the archive endpoint to archive.")
        return status

    @app.get("/v1/projects/{project_id}/logical-framework")
    def get_logical_framework(
        project_id: str,
        x_api_key: Optional[str] = header_default(header_factory, "X-API-Key"),
        x_auth_token: Optional[str] = header_default(header_factory, "X-Auth-Token"),
    ):
        _, scope = context(
            project_id,
            "VIEW_LOGICAL_FRAMEWORK",
            x_api_key,
            x_auth_token,
        )
        try:
            return deps.application.read(scope)
        except LogicalFrameworkValidationError as exc:
            map_service_error(exc)

    @app.post("/v1/projects/{project_id}/logical-framework/results")
    def create_result(
        project_id: str,
        payload: Dict[str, Any],
        x_api_key: Optional[str] = header_default(header_factory, "X-API-Key"),
        x_auth_token: Optional[str] = header_default(header_factory, "X-Auth-Token"),
    ):
        actor, scope = context(
            project_id,
            "MANAGE_LOGICAL_FRAMEWORK",
            x_api_key,
            x_auth_token,
        )
        reject_fields(
            payload,
            {"id", "result_id", "organization_id", "project_id", "created_at", "updated_at"},
        )
        result_type = str(payload.get("result_type", "") or "").strip().lower()
        parent_id = str(payload.get("parent_id", "") or "").strip()
        endpoint = f"/v1/projects/{project_id}/logical-framework/results"
        try:
            result = deps.application.create_result(
                scope,
                actor,
                result_type=result_type,
                title=str(payload.get("title", "") or ""),
                description=str(payload.get("description", "") or ""),
                parent_id=parent_id,
                display_order=payload.get("display_order", 0),
                status=result_status(payload),
                endpoint=endpoint,
            )
        except LogicalFrameworkValidationError as exc:
            map_service_error(exc)
        except LogicalFrameworkPersistenceError as exc:
            map_persistence_error(exc)
        return {"ok": True, "result": LogicalFrameworkService.serialize_result(result)}

    @app.put("/v1/projects/{project_id}/logical-framework/indicators/{indicator_id}/link")
    def link_indicator(
        project_id: str,
        indicator_id: str,
        payload: Dict[str, Any],
        x_api_key: Optional[str] = header_default(header_factory, "X-API-Key"),
        x_auth_token: Optional[str] = header_default(header_factory, "X-Auth-Token"),
    ):
        actor, scope = context(
            project_id,
            "LINK_RESULT_INDICATORS",
            x_api_key,
            x_auth_token,
        )
        result_id = str(payload.get("result_id", "") or "").strip()
        if not result_id:
            fail(400, "result_id is required.")
        endpoint = (
            f"/v1/projects/{project_id}/logical-framework/indicators/{indicator_id}/link"
        )
        try:
            link = deps.application.link_indicator(
                scope,
                actor,
                indicator_id,
                result_id,
                endpoint=endpoint,
            )
        except LogicalFrameworkValidationError as exc:
            map_service_error(exc)
        except LogicalFrameworkPersistenceError as exc:
            map_persistence_error(exc)
        return {
            "ok": True,
            "link": {
                "id": link.id,
                "organization_id": link.organization_id,
                "project_id": link.project_id,
                "indicator_id": link.indicator_id,
                "result_id": link.result_id,
                "result_type": link.result_type,
                "created_at": link.created_at,
                "updated_at": link.updated_at,
            },
        }

    @app.delete("/v1/projects/{project_id}/logical-framework/indicators/{indicator_id}/link")
    def unlink_indicator(
        project_id: str,
        indicator_id: str,
        x_api_key: Optional[str] = header_default(header_factory, "X-API-Key"),
        x_auth_token: Optional[str] = header_default(header_factory, "X-Auth-Token"),
    ):
        actor, scope = context(
            project_id,
            "LINK_RESULT_INDICATORS",
            x_api_key,
            x_auth_token,
        )
        endpoint = (
            f"/v1/projects/{project_id}/logical-framework/indicators/{indicator_id}/link"
        )
        try:
            deps.application.unlink_indicator(
                scope,
                actor,
                indicator_id,
                endpoint=endpoint,
            )
        except LogicalFrameworkValidationError as exc:
            map_service_error(exc)
        except LogicalFrameworkPersistenceError as exc:
            map_persistence_error(exc)
        return {"ok": True, "unlinked_indicator_id": indicator_id}

    @app.post("/v1/projects/{project_id}/logical-framework/reorder")
    def reorder_results(
        project_id: str,
        payload: Dict[str, Any],
        x_api_key: Optional[str] = header_default(header_factory, "X-API-Key"),
        x_auth_token: Optional[str] = header_default(header_factory, "X-Auth-Token"),
    ):
        actor, scope = context(
            project_id,
            "MANAGE_LOGICAL_FRAMEWORK",
            x_api_key,
            x_auth_token,
        )
        ordered_result_ids = payload.get("ordered_result_ids", [])
        if not isinstance(ordered_result_ids, list):
            fail(400, "ordered_result_ids must be a list.")
        endpoint = f"/v1/projects/{project_id}/logical-framework/reorder"
        try:
            results = deps.application.reorder_results(
                scope,
                actor,
                ordered_result_ids,
                endpoint=endpoint,
            )
        except LogicalFrameworkValidationError as exc:
            map_service_error(exc)
        except LogicalFrameworkPersistenceError as exc:
            map_persistence_error(exc)
        return {
            "ok": True,
            "results": [
                LogicalFrameworkService.serialize_result(result) for result in results
            ],
        }

    @app.post("/v1/projects/{project_id}/logical-framework/results/{result_id}/archive")
    def archive_result(
        project_id: str,
        result_id: str,
        x_api_key: Optional[str] = header_default(header_factory, "X-API-Key"),
        x_auth_token: Optional[str] = header_default(header_factory, "X-Auth-Token"),
    ):
        actor, scope = context(
            project_id,
            "MANAGE_LOGICAL_FRAMEWORK",
            x_api_key,
            x_auth_token,
        )
        endpoint = (
            f"/v1/projects/{project_id}/logical-framework/results/{result_id}/archive"
        )
        try:
            result = deps.application.archive_result(
                scope,
                actor,
                result_id,
                endpoint=endpoint,
            )
        except LogicalFrameworkValidationError as exc:
            map_service_error(exc)
        except LogicalFrameworkPersistenceError as exc:
            map_persistence_error(exc)
        return {"ok": True, "result": LogicalFrameworkService.serialize_result(result)}

    @app.delete("/v1/projects/{project_id}/logical-framework/results/{result_id}")
    def delete_result(
        project_id: str,
        result_id: str,
        x_api_key: Optional[str] = header_default(header_factory, "X-API-Key"),
        x_auth_token: Optional[str] = header_default(header_factory, "X-Auth-Token"),
    ):
        actor, scope = context(
            project_id,
            "MANAGE_LOGICAL_FRAMEWORK",
            x_api_key,
            x_auth_token,
        )
        endpoint = f"/v1/projects/{project_id}/logical-framework/results/{result_id}"
        try:
            result = deps.application.delete_result(
                scope,
                actor,
                result_id,
                endpoint=endpoint,
            )
        except LogicalFrameworkValidationError as exc:
            map_service_error(exc)
        except LogicalFrameworkPersistenceError as exc:
            map_persistence_error(exc)
        return {"ok": True, "deleted_result_id": result.id}

    @app.patch("/v1/projects/{project_id}/logical-framework/results/{result_id}")
    def update_result(
        project_id: str,
        result_id: str,
        payload: Dict[str, Any],
        x_api_key: Optional[str] = header_default(header_factory, "X-API-Key"),
        x_auth_token: Optional[str] = header_default(header_factory, "X-Auth-Token"),
    ):
        actor, scope = context(
            project_id,
            "MANAGE_LOGICAL_FRAMEWORK",
            x_api_key,
            x_auth_token,
        )
        reject_fields(
            payload,
            {
                "id",
                "result_id",
                "result_type",
                "organization_id",
                "project_id",
                "parent_id",
                "display_order",
                "created_at",
                "updated_at",
            },
        )
        unknown = sorted(set(payload) - {"title", "description", "status"})
        if unknown:
            fail(400, f"Unsupported result fields: {', '.join(unknown)}.")
        endpoint = f"/v1/projects/{project_id}/logical-framework/results/{result_id}"
        try:
            result = deps.application.update_result(
                scope,
                actor,
                result_id,
                title=payload.get("title"),
                description=payload.get("description"),
                status=result_status(payload) if "status" in payload else None,
                fields=sorted(payload),
                endpoint=endpoint,
            )
        except LogicalFrameworkValidationError as exc:
            map_service_error(exc)
        except LogicalFrameworkPersistenceError as exc:
            map_persistence_error(exc)
        return {"ok": True, "result": LogicalFrameworkService.serialize_result(result)}
