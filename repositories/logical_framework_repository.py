from __future__ import annotations

from typing import Any, List, Optional, Protocol

from shared import IndicatorResultLink, ResultNode


class LogicalFrameworkRepositoryError(ValueError):
    pass


class LogicalFrameworkNotFoundError(LogicalFrameworkRepositoryError):
    pass


class LogicalFrameworkScopeError(LogicalFrameworkRepositoryError):
    pass


class LogicalFrameworkConflictError(LogicalFrameworkRepositoryError):
    pass


class LogicalFrameworkState(Protocol):
    projects: List[Any]
    logical_framework_results: List[ResultNode]
    indicator_result_links: List[IndicatorResultLink]


class LogicalFrameworkRepository:
    """Organization- and project-scoped access to canonical snapshot state."""

    def __init__(self, state: LogicalFrameworkState):
        self.state = state

    def require_project(self, organization_id: str, project_id: str) -> Any:
        matches = [project for project in self.state.projects if str(getattr(project, "id", "")) == project_id]
        if not matches:
            raise LogicalFrameworkNotFoundError(f"Project '{project_id}' was not found.")
        project = matches[0]
        if str(getattr(project, "organization_id", "")) != organization_id:
            raise LogicalFrameworkScopeError("Project belongs to another organization.")
        return project

    def list_results(self, organization_id: str, project_id: str, *, include_archived: bool = True) -> List[ResultNode]:
        self.require_project(organization_id, project_id)
        results = [
            node
            for node in self.state.logical_framework_results
            if node.organization_id == organization_id and node.project_id == project_id
        ]
        if not include_archived:
            results = [node for node in results if node.status != "archived"]
        return sorted(results, key=lambda node: (node.display_order, node.result_type, node.id))

    def get_result(self, organization_id: str, project_id: str, result_id: str) -> Optional[ResultNode]:
        matches = [node for node in self.state.logical_framework_results if node.id == result_id]
        if not matches:
            return None
        node = matches[0]
        if node.organization_id != organization_id or node.project_id != project_id:
            raise LogicalFrameworkScopeError("Result belongs to another organization or project.")
        return node

    def require_result(self, organization_id: str, project_id: str, result_id: str) -> ResultNode:
        node = self.get_result(organization_id, project_id, result_id)
        if node is None:
            raise LogicalFrameworkNotFoundError(f"Result '{result_id}' was not found.")
        return node

    def save_result(self, node: ResultNode) -> ResultNode:
        self.require_project(node.organization_id, node.project_id)
        for index, current in enumerate(self.state.logical_framework_results):
            if current.id != node.id:
                continue
            if current.organization_id != node.organization_id or current.project_id != node.project_id:
                raise LogicalFrameworkScopeError("Result ID is already owned by another organization or project.")
            self.state.logical_framework_results[index] = node
            return node
        self.state.logical_framework_results.append(node)
        return node

    def delete_result(self, organization_id: str, project_id: str, result_id: str) -> None:
        self.require_result(organization_id, project_id, result_id)
        if any(node.parent_id == result_id for node in self.state.logical_framework_results):
            raise LogicalFrameworkConflictError("A result with child results cannot be deleted.")
        if any(link.result_id == result_id for link in self.state.indicator_result_links):
            raise LogicalFrameworkConflictError("A result with indicator links cannot be deleted.")
        self.state.logical_framework_results = [
            node for node in self.state.logical_framework_results if node.id != result_id
        ]

    def require_indicator(self, organization_id: str, project_id: str, indicator_id: str) -> Any:
        matches = []
        for project in self.state.projects:
            for indicator in getattr(project, "indicators", []) or []:
                if str(getattr(indicator, "id", "")) != indicator_id:
                    continue
                owner_organization_id = str(
                    getattr(indicator, "organization_id", "") or getattr(project, "organization_id", "")
                )
                owner_project_id = str(getattr(indicator, "project_id", "") or getattr(project, "id", ""))
                matches.append((indicator, owner_organization_id, owner_project_id))
        if not matches:
            raise LogicalFrameworkNotFoundError(f"Indicator '{indicator_id}' was not found.")
        if len(matches) > 1:
            raise LogicalFrameworkConflictError(f"Indicator ID '{indicator_id}' is not globally unique.")
        indicator, owner_organization_id, owner_project_id = matches[0]
        if owner_organization_id != organization_id or owner_project_id != project_id:
            raise LogicalFrameworkScopeError("Indicator belongs to another organization or project.")
        return indicator

    def list_indicator_links(self, organization_id: str, project_id: str) -> List[IndicatorResultLink]:
        self.require_project(organization_id, project_id)
        return [
            link
            for link in self.state.indicator_result_links
            if link.organization_id == organization_id and link.project_id == project_id
        ]

    def get_indicator_link(self, organization_id: str, project_id: str, indicator_id: str) -> Optional[IndicatorResultLink]:
        matches = [link for link in self.state.indicator_result_links if link.indicator_id == indicator_id]
        if not matches:
            return None
        link = matches[0]
        if link.organization_id != organization_id or link.project_id != project_id:
            raise LogicalFrameworkScopeError("Indicator link belongs to another organization or project.")
        return link

    def save_indicator_link(self, link: IndicatorResultLink) -> IndicatorResultLink:
        self.require_indicator(link.organization_id, link.project_id, link.indicator_id)
        result = self.require_result(link.organization_id, link.project_id, link.result_id)
        if result.result_type not in {"outcome", "output"} or result.result_type != link.result_type:
            raise LogicalFrameworkConflictError("Indicator link target must be its declared Outcome or Output.")
        for index, current in enumerate(self.state.indicator_result_links):
            if current.indicator_id != link.indicator_id:
                continue
            if current.organization_id != link.organization_id or current.project_id != link.project_id:
                raise LogicalFrameworkScopeError("Indicator link is already owned by another organization or project.")
            self.state.indicator_result_links[index] = link
            return link
        self.state.indicator_result_links.append(link)
        return link

    def delete_indicator_link(self, organization_id: str, project_id: str, indicator_id: str) -> None:
        link = self.get_indicator_link(organization_id, project_id, indicator_id)
        if link is None:
            return
        self.state.indicator_result_links = [
            current for current in self.state.indicator_result_links if current.id != link.id
        ]
