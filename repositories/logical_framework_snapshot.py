from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from repositories.logical_framework_repository import (
    LogicalFrameworkCanonicalPersistenceError,
    LogicalFrameworkConflictError,
    LogicalFrameworkNotFoundError,
    LogicalFrameworkProject,
    LogicalFrameworkProjectionError,
    LogicalFrameworkRepository,
    LogicalFrameworkScope,
    LogicalFrameworkScopeError,
)
from services.logical_framework_application import LogicalFrameworkAuditRequest
from services.logical_framework_service import LogicalFrameworkService
from shared import IndicatorResultLink, ResultNode


class SnapshotLogicalFrameworkRepository:
    """Scoped adapter over the private request-local application snapshot."""

    def __init__(self, snapshot: Any, scope: LogicalFrameworkScope):
        self.__snapshot = snapshot
        self._scope = scope

    @property
    def scope(self) -> LogicalFrameworkScope:
        return self._scope

    def _project_matches(self) -> List[Any]:
        return [
            project
            for project in self.__snapshot.projects
            if str(getattr(project, "id", "")) == self.scope.project_id
        ]

    def _project(self) -> Any:
        matches = self._project_matches()
        if not matches:
            raise LogicalFrameworkNotFoundError(
                f"Project '{self.scope.project_id}' was not found."
            )
        if len(matches) > 1:
            raise LogicalFrameworkConflictError(
                f"Project ID '{self.scope.project_id}' is not unique."
            )
        project = matches[0]
        if str(getattr(project, "organization_id", "")) != self.scope.organization_id:
            raise LogicalFrameworkScopeError("Project belongs to another organization.")
        return project

    def ensure_project(self) -> LogicalFrameworkProject:
        project = self._project()
        return LogicalFrameworkProject(
            id=str(getattr(project, "id", "")),
            organization_id=str(getattr(project, "organization_id", "")),
            status=str(getattr(project, "status", "")),
        )

    def list_results(self, *, include_archived: bool = True) -> List[ResultNode]:
        self.ensure_project()
        results = [
            node
            for node in self.__snapshot.logical_framework_results
            if node.organization_id == self.scope.organization_id
            and node.project_id == self.scope.project_id
        ]
        if not include_archived:
            results = [node for node in results if node.status != "archived"]
        return sorted(
            results,
            key=lambda node: (node.display_order, node.result_type, node.id),
        )

    def get_result(self, result_id: str) -> Optional[ResultNode]:
        matches = [
            node
            for node in self.__snapshot.logical_framework_results
            if node.id == result_id
        ]
        if not matches:
            return None
        if len(matches) > 1:
            raise LogicalFrameworkConflictError(
                f"Result ID '{result_id}' is not globally unique."
            )
        node = matches[0]
        if (
            node.organization_id != self.scope.organization_id
            or node.project_id != self.scope.project_id
        ):
            raise LogicalFrameworkScopeError(
                "Result belongs to another organization or project."
            )
        return node

    def require_result(self, result_id: str) -> ResultNode:
        node = self.get_result(result_id)
        if node is None:
            raise LogicalFrameworkNotFoundError(f"Result '{result_id}' was not found.")
        return node

    def save_result(self, node: ResultNode) -> ResultNode:
        self.ensure_project()
        if (
            node.organization_id != self.scope.organization_id
            or node.project_id != self.scope.project_id
        ):
            raise LogicalFrameworkScopeError(
                "Result belongs to another organization or project."
            )
        matches = [
            (index, current)
            for index, current in enumerate(self.__snapshot.logical_framework_results)
            if current.id == node.id
        ]
        if len(matches) > 1:
            raise LogicalFrameworkConflictError(
                f"Result ID '{node.id}' is not globally unique."
            )
        if matches:
            index, current = matches[0]
            if (
                current.organization_id != self.scope.organization_id
                or current.project_id != self.scope.project_id
            ):
                raise LogicalFrameworkScopeError(
                    "Result ID is already owned by another organization or project."
                )
            self.__snapshot.logical_framework_results[index] = node
            return node
        self.__snapshot.logical_framework_results.append(node)
        return node

    def delete_result(self, result_id: str) -> None:
        self.require_result(result_id)
        if any(
            node.parent_id == result_id
            and node.organization_id == self.scope.organization_id
            and node.project_id == self.scope.project_id
            for node in self.__snapshot.logical_framework_results
        ):
            raise LogicalFrameworkConflictError(
                "A result with child results cannot be deleted."
            )
        if any(
            link.result_id == result_id
            and link.organization_id == self.scope.organization_id
            and link.project_id == self.scope.project_id
            for link in self.__snapshot.indicator_result_links
        ):
            raise LogicalFrameworkConflictError(
                "A result with indicator links cannot be deleted."
            )
        self.__snapshot.logical_framework_results = [
            node
            for node in self.__snapshot.logical_framework_results
            if not (
                node.id == result_id
                and node.organization_id == self.scope.organization_id
                and node.project_id == self.scope.project_id
            )
        ]

    def list_indicators(self) -> List[Any]:
        project = self._project()
        return list(getattr(project, "indicators", []) or [])

    def require_indicator(self, indicator_id: str) -> Any:
        matches = []
        for project in self.__snapshot.projects:
            for indicator in getattr(project, "indicators", []) or []:
                if str(getattr(indicator, "id", "")) != indicator_id:
                    continue
                owner_organization_id = str(
                    getattr(indicator, "organization_id", "")
                    or getattr(project, "organization_id", "")
                )
                owner_project_id = str(
                    getattr(indicator, "project_id", "")
                    or getattr(project, "id", "")
                )
                matches.append(
                    (indicator, owner_organization_id, owner_project_id)
                )
        if not matches:
            raise LogicalFrameworkNotFoundError(
                f"Indicator '{indicator_id}' was not found."
            )
        if len(matches) > 1:
            raise LogicalFrameworkConflictError(
                f"Indicator ID '{indicator_id}' is not globally unique."
            )
        indicator, owner_organization_id, owner_project_id = matches[0]
        if (
            owner_organization_id != self.scope.organization_id
            or owner_project_id != self.scope.project_id
        ):
            raise LogicalFrameworkScopeError(
                "Indicator belongs to another organization or project."
            )
        return indicator

    def list_indicator_links(self) -> List[IndicatorResultLink]:
        self.ensure_project()
        return [
            link
            for link in self.__snapshot.indicator_result_links
            if link.organization_id == self.scope.organization_id
            and link.project_id == self.scope.project_id
        ]

    def get_indicator_link(
        self, indicator_id: str
    ) -> Optional[IndicatorResultLink]:
        matches = [
            link
            for link in self.__snapshot.indicator_result_links
            if link.indicator_id == indicator_id
        ]
        if not matches:
            return None
        if len(matches) > 1:
            raise LogicalFrameworkConflictError(
                f"Indicator '{indicator_id}' has more than one canonical result link."
            )
        link = matches[0]
        if (
            link.organization_id != self.scope.organization_id
            or link.project_id != self.scope.project_id
        ):
            raise LogicalFrameworkScopeError(
                "Indicator link belongs to another organization or project."
            )
        return link

    def save_indicator_link(
        self, link: IndicatorResultLink
    ) -> IndicatorResultLink:
        if (
            link.organization_id != self.scope.organization_id
            or link.project_id != self.scope.project_id
        ):
            raise LogicalFrameworkScopeError(
                "Indicator link belongs to another organization or project."
            )
        self.require_indicator(link.indicator_id)
        result = self.require_result(link.result_id)
        if (
            result.result_type not in {"outcome", "output"}
            or result.result_type != link.result_type
        ):
            raise LogicalFrameworkConflictError(
                "Indicator link target must be its declared Outcome or Output."
            )
        scoped_id_matches = [
            current
            for current in self.__snapshot.indicator_result_links
            if current.id == link.id
            and current.organization_id == self.scope.organization_id
            and current.project_id == self.scope.project_id
        ]
        if len(scoped_id_matches) > 1:
            raise LogicalFrameworkConflictError(
                f"Indicator link ID '{link.id}' is not unique in this project."
            )
        if (
            scoped_id_matches
            and scoped_id_matches[0].indicator_id != link.indicator_id
        ):
            raise LogicalFrameworkConflictError(
                f"Indicator link ID '{link.id}' is already used by another indicator "
                "in this project."
            )
        matches = [
            (index, current)
            for index, current in enumerate(self.__snapshot.indicator_result_links)
            if current.indicator_id == link.indicator_id
        ]
        if len(matches) > 1:
            raise LogicalFrameworkConflictError(
                f"Indicator '{link.indicator_id}' has more than one canonical result link."
            )
        if matches:
            index, current = matches[0]
            if (
                current.organization_id != self.scope.organization_id
                or current.project_id != self.scope.project_id
            ):
                raise LogicalFrameworkScopeError(
                    "Indicator link is already owned by another organization or project."
                )
            self.__snapshot.indicator_result_links[index] = link
            return link
        self.__snapshot.indicator_result_links.append(link)
        return link

    def delete_indicator_link(self, indicator_id: str) -> None:
        link = self.get_indicator_link(indicator_id)
        if link is None:
            return
        self.__snapshot.indicator_result_links = [
            current
            for current in self.__snapshot.indicator_result_links
            if not (
                current.id == link.id
                and current.organization_id == self.scope.organization_id
                and current.project_id == self.scope.project_id
                and current.indicator_id == indicator_id
            )
        ]


class SnapshotLogicalFrameworkUnitOfWork:
    """Transitional UoW over the canonical whole-application snapshot."""

    def __init__(
        self,
        *,
        load_snapshot: Optional[Callable[[], Any]] = None,
        save_canonical: Optional[Callable[[Any], str]] = None,
        synchronize_projection: Optional[Callable[[Any, str], Any]] = None,
        append_audit: Optional[
            Callable[[Any, LogicalFrameworkAuditRequest], Any]
        ] = None,
        existing_snapshot: Any = None,
    ):
        if load_snapshot is None and existing_snapshot is None:
            raise ValueError("A snapshot loader or existing snapshot is required.")
        self._load_snapshot = load_snapshot
        self._save_canonical = save_canonical
        self._synchronize_projection = synchronize_projection
        self._append_audit = append_audit
        self.__snapshot = existing_snapshot
        self._repositories: Dict[
            LogicalFrameworkScope, SnapshotLogicalFrameworkRepository
        ] = {}
        self._entered = False
        self._commit_attempted = False
        self._committed = False
        self._discarded = False
        self.canonical_path = ""
        self.projection_error: Optional[Exception] = None

    @classmethod
    def from_existing_snapshot(
        cls, snapshot: Any
    ) -> "SnapshotLogicalFrameworkUnitOfWork":
        return cls(existing_snapshot=snapshot)

    @property
    def committed(self) -> bool:
        return self._committed

    @property
    def commit_attempted(self) -> bool:
        return self._commit_attempted

    def __enter__(self) -> "SnapshotLogicalFrameworkUnitOfWork":
        if self._entered:
            raise RuntimeError("Logical Framework unit of work is already active.")
        self._entered = True
        if self.__snapshot is None:
            self.__snapshot = self._load_snapshot()
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> Optional[bool]:
        if exc_type is not None and not self._committed:
            self.discard()
        self._repositories.clear()
        self.__snapshot = None
        self._entered = False
        return None

    def _require_active(self) -> None:
        if not self._entered or self.__snapshot is None:
            raise RuntimeError("Logical Framework unit of work is not active.")
        if self._discarded:
            raise RuntimeError("Logical Framework unit of work was discarded.")

    def repository(
        self, scope: LogicalFrameworkScope
    ) -> LogicalFrameworkRepository:
        self._require_active()
        repository = self._repositories.get(scope)
        if repository is None:
            repository = SnapshotLogicalFrameworkRepository(self.__snapshot, scope)
            self._repositories[scope] = repository
        return repository

    def stage_audit(self, request: LogicalFrameworkAuditRequest) -> None:
        self._require_active()
        if self._commit_attempted:
            raise RuntimeError("Audit cannot be staged after commit begins.")
        if self._append_audit is None:
            raise RuntimeError("This unit of work does not support audit staging.")
        self._append_audit(self.__snapshot, request)

    def commit(self) -> str:
        self._require_active()
        if self._commit_attempted:
            raise RuntimeError(
                "Logical Framework unit of work may be committed only once."
            )
        self._commit_attempted = True
        if self._save_canonical is None:
            raise RuntimeError(
                "This unit of work participates in an outer commit and cannot commit independently."
            )
        try:
            self.canonical_path = self._save_canonical(self.__snapshot)
        except Exception as exc:
            self._discarded = True
            raise LogicalFrameworkCanonicalPersistenceError(str(exc)) from exc
        self._committed = True
        if self._synchronize_projection is not None:
            try:
                self._synchronize_projection(self.__snapshot, self.canonical_path)
            except Exception as exc:
                self.projection_error = exc
                raise LogicalFrameworkProjectionError(
                    str(exc), canonical_path=self.canonical_path
                ) from exc
        return self.canonical_path

    def discard(self) -> None:
        if self._committed:
            return
        self._discarded = True
        self._repositories.clear()
        self.__snapshot = None


def validate_snapshot_logical_framework(snapshot: Any) -> None:
    result_ids = [node.id for node in snapshot.logical_framework_results]
    if len(result_ids) != len(set(result_ids)):
        raise ValueError("Duplicate Logical Framework result ID.")
    indicator_ids = [
        link.indicator_id for link in snapshot.indicator_result_links
    ]
    if len(indicator_ids) != len(set(indicator_ids)):
        raise ValueError("An indicator has more than one canonical result link.")
    scoped_link_ids = [
        (link.organization_id, link.project_id, link.id)
        for link in snapshot.indicator_result_links
    ]
    if len(scoped_link_ids) != len(set(scoped_link_ids)):
        raise ValueError(
            "Duplicate Logical Framework indicator-link ID within "
            "organization/project scope."
        )

    scopes = {
        LogicalFrameworkScope(
            str(getattr(project, "organization_id", "")),
            str(getattr(project, "id", "")),
        )
        for project in snapshot.projects
        if str(getattr(project, "organization_id", "")).strip()
        and str(getattr(project, "id", "")).strip()
    }
    scopes.update(
        LogicalFrameworkScope(node.organization_id, node.project_id)
        for node in snapshot.logical_framework_results
    )
    scopes.update(
        LogicalFrameworkScope(link.organization_id, link.project_id)
        for link in snapshot.indicator_result_links
    )
    for scope in scopes:
        LogicalFrameworkService(
            SnapshotLogicalFrameworkRepository(snapshot, scope)
        ).validate_integrity()
