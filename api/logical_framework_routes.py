from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Tuple

from api.common import header_default
from repositories.logical_framework_repository import LogicalFrameworkRepository
from services.logical_framework_service import (
    LogicalFrameworkConflictValidationError,
    LogicalFrameworkNotFoundValidationError,
    LogicalFrameworkScopeValidationError,
    LogicalFrameworkService,
    LogicalFrameworkValidationError,
)


@dataclass(frozen=True)
class LogicalFrameworkRouteDependencies:
    load_data: Callable[[], Any]
    save_data: Callable[[Any], str]
    authorize_request: Callable[..., Any]
    append_audit_event: Callable[..., Any]
    find_project: Callable[[Any, str], Any]
    ensure_project_scope: Callable[[Any, Any], None]
    normalize_project_status: Callable[[Optional[str], str], str]


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

    def context(
        project_id: str,
        permission: str,
        x_api_key: Optional[str],
        x_auth_token: Optional[str],
        *,
        mutation: bool = False,
    ) -> Tuple[Any, Any, Any, LogicalFrameworkService]:
        data = deps.load_data()
        actor = deps.authorize_request(
            data,
            x_api_key,
            x_auth_token,
            required_permission=permission,
        )
        if actor is None:
            fail(401, "Logical Framework endpoints require an authenticated user.")
        project = deps.find_project(data, project_id)
        if project is None:
            fail(404, "Project not found.")
        deps.ensure_project_scope(actor, project)
        if mutation and deps.normalize_project_status(
            getattr(project, "status", ""), "draft"
        ) == "archived":
            fail(409, "Archived projects are read-only.")
        service = LogicalFrameworkService(LogicalFrameworkRepository(data))
        return data, actor, project, service

    def reject_fields(payload: Dict[str, Any], forbidden: set[str]) -> None:
        supplied = sorted(field for field in forbidden if field in payload)
        if supplied:
            fail(400, f"Fields cannot be changed through this endpoint: {', '.join(supplied)}.")

    def audit_and_save(
        data: Any,
        actor: Any,
        *,
        action: str,
        target_type: str,
        target_id: str,
        endpoint: str,
        details: Dict[str, Any],
    ) -> None:
        deps.append_audit_event(
            data,
            action=action,
            target_type=target_type,
            target_id=target_id,
            actor=actor,
            endpoint=endpoint,
            details=details,
        )
        deps.save_data(data)

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
        _, actor, _, service = context(
            project_id,
            "VIEW_LOGICAL_FRAMEWORK",
            x_api_key,
            x_auth_token,
        )
        try:
            return service.get_project_logical_framework(actor.organization_id, project_id)
        except LogicalFrameworkValidationError as exc:
            map_service_error(exc)

    @app.post("/v1/projects/{project_id}/logical-framework/results")
    def create_result(
        project_id: str,
        payload: Dict[str, Any],
        x_api_key: Optional[str] = header_default(header_factory, "X-API-Key"),
        x_auth_token: Optional[str] = header_default(header_factory, "X-Auth-Token"),
    ):
        data, actor, _, service = context(
            project_id,
            "MANAGE_LOGICAL_FRAMEWORK",
            x_api_key,
            x_auth_token,
            mutation=True,
        )
        reject_fields(
            payload,
            {"id", "result_id", "organization_id", "project_id", "created_at", "updated_at"},
        )
        result_type = str(payload.get("result_type", "") or "").strip().lower()
        parent_id = str(payload.get("parent_id", "") or "").strip()
        try:
            result = service.create_result(
                actor.organization_id,
                project_id,
                result_type,
                str(payload.get("title", "") or ""),
                description=str(payload.get("description", "") or ""),
                parent_id=parent_id,
                display_order=payload.get("display_order", 0),
                status=result_status(payload),
            )
        except LogicalFrameworkValidationError as exc:
            map_service_error(exc)
        action = f"logical_framework.{result.result_type}_created"
        endpoint = f"/v1/projects/{project_id}/logical-framework/results"
        audit_and_save(
            data,
            actor,
            action=action,
            target_type="logical_framework_result",
            target_id=result.id,
            endpoint=endpoint,
            details={
                "organization_id": actor.organization_id,
                "project_id": project_id,
                "result_id": result.id,
                "result_type": result.result_type,
                "parent_id": result.parent_id,
            },
        )
        return {"ok": True, "result": service.serialize_result(result)}

    @app.put("/v1/projects/{project_id}/logical-framework/indicators/{indicator_id}/link")
    def link_indicator(
        project_id: str,
        indicator_id: str,
        payload: Dict[str, Any],
        x_api_key: Optional[str] = header_default(header_factory, "X-API-Key"),
        x_auth_token: Optional[str] = header_default(header_factory, "X-Auth-Token"),
    ):
        data, actor, _, service = context(
            project_id,
            "LINK_RESULT_INDICATORS",
            x_api_key,
            x_auth_token,
            mutation=True,
        )
        result_id = str(payload.get("result_id", "") or "").strip()
        if not result_id:
            fail(400, "result_id is required.")
        try:
            link = service.link_indicator(
                actor.organization_id, project_id, indicator_id, result_id
            )
        except LogicalFrameworkValidationError as exc:
            map_service_error(exc)
        endpoint = (
            f"/v1/projects/{project_id}/logical-framework/indicators/{indicator_id}/link"
        )
        audit_and_save(
            data,
            actor,
            action="logical_framework.indicator_linked",
            target_type="indicator",
            target_id=indicator_id,
            endpoint=endpoint,
            details={
                "organization_id": actor.organization_id,
                "project_id": project_id,
                "indicator_id": indicator_id,
                "result_id": link.result_id,
                "result_type": link.result_type,
            },
        )
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
        data, actor, _, service = context(
            project_id,
            "LINK_RESULT_INDICATORS",
            x_api_key,
            x_auth_token,
            mutation=True,
        )
        try:
            removed = service.unlink_indicator(
                actor.organization_id, project_id, indicator_id
            )
        except LogicalFrameworkValidationError as exc:
            map_service_error(exc)
        endpoint = (
            f"/v1/projects/{project_id}/logical-framework/indicators/{indicator_id}/link"
        )
        audit_and_save(
            data,
            actor,
            action="logical_framework.indicator_unlinked",
            target_type="indicator",
            target_id=indicator_id,
            endpoint=endpoint,
            details={
                "organization_id": actor.organization_id,
                "project_id": project_id,
                "indicator_id": indicator_id,
                "result_id": removed.result_id,
                "result_type": removed.result_type,
            },
        )
        return {"ok": True, "unlinked_indicator_id": indicator_id}

    @app.post("/v1/projects/{project_id}/logical-framework/reorder")
    def reorder_results(
        project_id: str,
        payload: Dict[str, Any],
        x_api_key: Optional[str] = header_default(header_factory, "X-API-Key"),
        x_auth_token: Optional[str] = header_default(header_factory, "X-Auth-Token"),
    ):
        data, actor, _, service = context(
            project_id,
            "MANAGE_LOGICAL_FRAMEWORK",
            x_api_key,
            x_auth_token,
            mutation=True,
        )
        ordered_result_ids = payload.get("ordered_result_ids", [])
        if not isinstance(ordered_result_ids, list):
            fail(400, "ordered_result_ids must be a list.")
        try:
            results = service.reorder_siblings(
                actor.organization_id, project_id, ordered_result_ids
            )
        except LogicalFrameworkValidationError as exc:
            map_service_error(exc)
        endpoint = f"/v1/projects/{project_id}/logical-framework/reorder"
        audit_and_save(
            data,
            actor,
            action="logical_framework.result_reordered",
            target_type="logical_framework_result",
            target_id=results[0].parent_id or project_id,
            endpoint=endpoint,
            details={
                "organization_id": actor.organization_id,
                "project_id": project_id,
                "result_type": results[0].result_type,
                "parent_id": results[0].parent_id,
                "ordered_result_ids": [result.id for result in results],
            },
        )
        return {
            "ok": True,
            "results": [service.serialize_result(result) for result in results],
        }

    @app.post("/v1/projects/{project_id}/logical-framework/results/{result_id}/archive")
    def archive_result(
        project_id: str,
        result_id: str,
        x_api_key: Optional[str] = header_default(header_factory, "X-API-Key"),
        x_auth_token: Optional[str] = header_default(header_factory, "X-Auth-Token"),
    ):
        data, actor, _, service = context(
            project_id,
            "MANAGE_LOGICAL_FRAMEWORK",
            x_api_key,
            x_auth_token,
            mutation=True,
        )
        try:
            result = service.archive_result(actor.organization_id, project_id, result_id)
        except LogicalFrameworkValidationError as exc:
            map_service_error(exc)
        endpoint = (
            f"/v1/projects/{project_id}/logical-framework/results/{result_id}/archive"
        )
        audit_and_save(
            data,
            actor,
            action="logical_framework.result_archived",
            target_type="logical_framework_result",
            target_id=result.id,
            endpoint=endpoint,
            details={
                "organization_id": actor.organization_id,
                "project_id": project_id,
                "result_id": result.id,
                "result_type": result.result_type,
                "parent_id": result.parent_id,
            },
        )
        return {"ok": True, "result": service.serialize_result(result)}

    @app.delete("/v1/projects/{project_id}/logical-framework/results/{result_id}")
    def delete_result(
        project_id: str,
        result_id: str,
        x_api_key: Optional[str] = header_default(header_factory, "X-API-Key"),
        x_auth_token: Optional[str] = header_default(header_factory, "X-Auth-Token"),
    ):
        data, actor, _, service = context(
            project_id,
            "MANAGE_LOGICAL_FRAMEWORK",
            x_api_key,
            x_auth_token,
            mutation=True,
        )
        try:
            result = service.get_result(actor.organization_id, project_id, result_id)
            service.delete_result(actor.organization_id, project_id, result_id)
        except LogicalFrameworkValidationError as exc:
            map_service_error(exc)
        endpoint = f"/v1/projects/{project_id}/logical-framework/results/{result_id}"
        audit_and_save(
            data,
            actor,
            action="logical_framework.result_deleted",
            target_type="logical_framework_result",
            target_id=result.id,
            endpoint=endpoint,
            details={
                "organization_id": actor.organization_id,
                "project_id": project_id,
                "result_id": result.id,
                "result_type": result.result_type,
                "parent_id": result.parent_id,
            },
        )
        return {"ok": True, "deleted_result_id": result.id}

    @app.patch("/v1/projects/{project_id}/logical-framework/results/{result_id}")
    def update_result(
        project_id: str,
        result_id: str,
        payload: Dict[str, Any],
        x_api_key: Optional[str] = header_default(header_factory, "X-API-Key"),
        x_auth_token: Optional[str] = header_default(header_factory, "X-Auth-Token"),
    ):
        data, actor, _, service = context(
            project_id,
            "MANAGE_LOGICAL_FRAMEWORK",
            x_api_key,
            x_auth_token,
            mutation=True,
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
        try:
            result = service.update_result(
                actor.organization_id,
                project_id,
                result_id,
                title=payload.get("title"),
                description=payload.get("description"),
                status=result_status(payload) if "status" in payload else None,
            )
        except LogicalFrameworkValidationError as exc:
            map_service_error(exc)
        endpoint = f"/v1/projects/{project_id}/logical-framework/results/{result_id}"
        audit_and_save(
            data,
            actor,
            action="logical_framework.result_updated",
            target_type="logical_framework_result",
            target_id=result.id,
            endpoint=endpoint,
            details={
                "organization_id": actor.organization_id,
                "project_id": project_id,
                "result_id": result.id,
                "result_type": result.result_type,
                "parent_id": result.parent_id,
                "fields": sorted(payload),
            },
        )
        return {"ok": True, "result": service.serialize_result(result)}
