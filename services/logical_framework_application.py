from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Protocol, TypeVar

from repositories.logical_framework_repository import (
    LogicalFrameworkRepository,
    LogicalFrameworkScope,
)
from services.logical_framework_service import (
    LogicalFrameworkConflictValidationError,
    LogicalFrameworkService,
)


@dataclass(frozen=True)
class LogicalFrameworkActorContext:
    id: str
    username: str
    role: str
    organization_id: str


@dataclass(frozen=True)
class LogicalFrameworkAuditRequest:
    actor: LogicalFrameworkActorContext
    action: str
    target_type: str
    target_id: str
    endpoint: str
    details: Dict[str, Any]


class LogicalFrameworkUnitOfWork(Protocol):
    def __enter__(self) -> "LogicalFrameworkUnitOfWork":
        ...

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> Optional[bool]:
        ...

    def repository(self, scope: LogicalFrameworkScope) -> LogicalFrameworkRepository:
        ...

    def stage_audit(self, request: LogicalFrameworkAuditRequest) -> None:
        ...

    def commit(self) -> str:
        ...

    def discard(self) -> None:
        ...


T = TypeVar("T")


class LogicalFrameworkApplication:
    """Coordinates one Logical Framework operation and its persistence boundary."""

    def __init__(
        self,
        unit_of_work_factory: Callable[[], LogicalFrameworkUnitOfWork],
        *,
        normalize_project_status: Callable[[Optional[str], str], str],
    ):
        self.unit_of_work_factory = unit_of_work_factory
        self.normalize_project_status = normalize_project_status

    def _service(
        self,
        unit_of_work: LogicalFrameworkUnitOfWork,
        scope: LogicalFrameworkScope,
        *,
        mutation: bool,
    ) -> LogicalFrameworkService:
        repository = unit_of_work.repository(scope)
        project = repository.ensure_project()
        if mutation and self.normalize_project_status(project.status, "draft") == "archived":
            raise LogicalFrameworkConflictValidationError("Archived projects are read-only.")
        return LogicalFrameworkService(repository)

    def read(self, scope: LogicalFrameworkScope) -> Dict[str, Any]:
        with self.unit_of_work_factory() as unit_of_work:
            service = self._service(unit_of_work, scope, mutation=False)
            return service.get_project_logical_framework(
                scope.organization_id, scope.project_id
            )

    def _write(
        self,
        scope: LogicalFrameworkScope,
        operation: Callable[[LogicalFrameworkService], T],
        audit_request: Callable[[T], LogicalFrameworkAuditRequest],
    ) -> T:
        with self.unit_of_work_factory() as unit_of_work:
            service = self._service(unit_of_work, scope, mutation=True)
            result = operation(service)
            unit_of_work.stage_audit(audit_request(result))
            unit_of_work.commit()
            return result

    def create_result(
        self,
        scope: LogicalFrameworkScope,
        actor: LogicalFrameworkActorContext,
        *,
        result_type: str,
        title: str,
        description: str,
        parent_id: str,
        display_order: Any,
        status: str,
        endpoint: str,
    ):
        return self._write(
            scope,
            lambda service: service.create_result(
                scope.organization_id,
                scope.project_id,
                result_type,
                title,
                description=description,
                parent_id=parent_id,
                display_order=display_order,
                status=status,
            ),
            lambda result: LogicalFrameworkAuditRequest(
                actor=actor,
                action=f"logical_framework.{result.result_type}_created",
                target_type="logical_framework_result",
                target_id=result.id,
                endpoint=endpoint,
                details={
                    "organization_id": scope.organization_id,
                    "project_id": scope.project_id,
                    "result_id": result.id,
                    "result_type": result.result_type,
                    "parent_id": result.parent_id,
                },
            ),
        )

    def update_result(
        self,
        scope: LogicalFrameworkScope,
        actor: LogicalFrameworkActorContext,
        result_id: str,
        *,
        title: Optional[str],
        description: Optional[str],
        status: Optional[str],
        fields: List[str],
        endpoint: str,
    ):
        return self._write(
            scope,
            lambda service: service.update_result(
                scope.organization_id,
                scope.project_id,
                result_id,
                title=title,
                description=description,
                status=status,
            ),
            lambda result: LogicalFrameworkAuditRequest(
                actor=actor,
                action="logical_framework.result_updated",
                target_type="logical_framework_result",
                target_id=result.id,
                endpoint=endpoint,
                details={
                    "organization_id": scope.organization_id,
                    "project_id": scope.project_id,
                    "result_id": result.id,
                    "result_type": result.result_type,
                    "parent_id": result.parent_id,
                    "fields": fields,
                },
            ),
        )

    def reorder_results(
        self,
        scope: LogicalFrameworkScope,
        actor: LogicalFrameworkActorContext,
        ordered_result_ids: List[str],
        *,
        endpoint: str,
    ):
        return self._write(
            scope,
            lambda service: service.reorder_siblings(
                scope.organization_id, scope.project_id, ordered_result_ids
            ),
            lambda results: LogicalFrameworkAuditRequest(
                actor=actor,
                action="logical_framework.result_reordered",
                target_type="logical_framework_result",
                target_id=results[0].parent_id or scope.project_id,
                endpoint=endpoint,
                details={
                    "organization_id": scope.organization_id,
                    "project_id": scope.project_id,
                    "result_type": results[0].result_type,
                    "parent_id": results[0].parent_id,
                    "ordered_result_ids": [result.id for result in results],
                },
            ),
        )

    def archive_result(
        self,
        scope: LogicalFrameworkScope,
        actor: LogicalFrameworkActorContext,
        result_id: str,
        *,
        endpoint: str,
    ):
        return self._write(
            scope,
            lambda service: service.archive_result(
                scope.organization_id, scope.project_id, result_id
            ),
            lambda result: LogicalFrameworkAuditRequest(
                actor=actor,
                action="logical_framework.result_archived",
                target_type="logical_framework_result",
                target_id=result.id,
                endpoint=endpoint,
                details={
                    "organization_id": scope.organization_id,
                    "project_id": scope.project_id,
                    "result_id": result.id,
                    "result_type": result.result_type,
                    "parent_id": result.parent_id,
                },
            ),
        )

    def delete_result(
        self,
        scope: LogicalFrameworkScope,
        actor: LogicalFrameworkActorContext,
        result_id: str,
        *,
        endpoint: str,
    ):
        def delete(service: LogicalFrameworkService):
            result = service.get_result(
                scope.organization_id, scope.project_id, result_id
            )
            service.delete_result(scope.organization_id, scope.project_id, result_id)
            return result

        return self._write(
            scope,
            delete,
            lambda result: LogicalFrameworkAuditRequest(
                actor=actor,
                action="logical_framework.result_deleted",
                target_type="logical_framework_result",
                target_id=result.id,
                endpoint=endpoint,
                details={
                    "organization_id": scope.organization_id,
                    "project_id": scope.project_id,
                    "result_id": result.id,
                    "result_type": result.result_type,
                    "parent_id": result.parent_id,
                },
            ),
        )

    def link_indicator(
        self,
        scope: LogicalFrameworkScope,
        actor: LogicalFrameworkActorContext,
        indicator_id: str,
        result_id: str,
        *,
        endpoint: str,
    ):
        return self._write(
            scope,
            lambda service: service.link_indicator(
                scope.organization_id, scope.project_id, indicator_id, result_id
            ),
            lambda link: LogicalFrameworkAuditRequest(
                actor=actor,
                action="logical_framework.indicator_linked",
                target_type="indicator",
                target_id=indicator_id,
                endpoint=endpoint,
                details={
                    "organization_id": scope.organization_id,
                    "project_id": scope.project_id,
                    "indicator_id": indicator_id,
                    "result_id": link.result_id,
                    "result_type": link.result_type,
                },
            ),
        )

    def unlink_indicator(
        self,
        scope: LogicalFrameworkScope,
        actor: LogicalFrameworkActorContext,
        indicator_id: str,
        *,
        endpoint: str,
    ):
        return self._write(
            scope,
            lambda service: service.unlink_indicator(
                scope.organization_id, scope.project_id, indicator_id
            ),
            lambda link: LogicalFrameworkAuditRequest(
                actor=actor,
                action="logical_framework.indicator_unlinked",
                target_type="indicator",
                target_id=indicator_id,
                endpoint=endpoint,
                details={
                    "organization_id": scope.organization_id,
                    "project_id": scope.project_id,
                    "indicator_id": indicator_id,
                    "result_id": link.result_id,
                    "result_type": link.result_type,
                },
            ),
        )
