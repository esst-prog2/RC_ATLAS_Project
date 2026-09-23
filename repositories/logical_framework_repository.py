from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional, Protocol, runtime_checkable

from shared import IndicatorResultLink, ResultNode


class LogicalFrameworkRepositoryError(ValueError):
    pass


class LogicalFrameworkNotFoundError(LogicalFrameworkRepositoryError):
    pass


class LogicalFrameworkScopeError(LogicalFrameworkRepositoryError):
    pass


class LogicalFrameworkConflictError(LogicalFrameworkRepositoryError):
    pass


class LogicalFrameworkPersistenceError(RuntimeError):
    pass


class LogicalFrameworkCanonicalPersistenceError(LogicalFrameworkPersistenceError):
    pass


class LogicalFrameworkProjectionError(LogicalFrameworkPersistenceError):
    def __init__(self, message: str, *, canonical_path: str = ""):
        super().__init__(message)
        self.canonical_path = canonical_path


class LogicalFrameworkConcurrentWriteError(LogicalFrameworkPersistenceError):
    """Reserved for adapters with explicit optimistic-lock or locking support."""


@dataclass(frozen=True)
class LogicalFrameworkScope:
    organization_id: str
    project_id: str

    def __post_init__(self) -> None:
        if not str(self.organization_id or "").strip():
            raise ValueError("organization_id is required.")
        if not str(self.project_id or "").strip():
            raise ValueError("project_id is required.")


@dataclass(frozen=True)
class LogicalFrameworkProject:
    id: str
    organization_id: str
    status: str


@runtime_checkable
class LogicalFrameworkRepository(Protocol):
    @property
    def scope(self) -> LogicalFrameworkScope:
        ...

    def ensure_project(self) -> LogicalFrameworkProject:
        ...

    def list_results(self, *, include_archived: bool = True) -> List[ResultNode]:
        ...

    def get_result(self, result_id: str) -> Optional[ResultNode]:
        ...

    def require_result(self, result_id: str) -> ResultNode:
        ...

    def save_result(self, node: ResultNode) -> ResultNode:
        ...

    def delete_result(self, result_id: str) -> None:
        ...

    def list_indicators(self) -> List[Any]:
        ...

    def require_indicator(self, indicator_id: str) -> Any:
        ...

    def list_indicator_links(self) -> List[IndicatorResultLink]:
        ...

    def get_indicator_link(self, indicator_id: str) -> Optional[IndicatorResultLink]:
        ...

    def save_indicator_link(self, link: IndicatorResultLink) -> IndicatorResultLink:
        ...

    def delete_indicator_link(self, indicator_id: str) -> None:
        ...
