from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

from repositories.logical_framework_repository import (
    LogicalFrameworkConflictError,
    LogicalFrameworkNotFoundError,
    LogicalFrameworkRepository,
    LogicalFrameworkRepositoryError,
    LogicalFrameworkScopeError,
)
from shared import IndicatorResultLink, ResultNode


class LogicalFrameworkValidationError(ValueError):
    pass


class LogicalFrameworkNotFoundValidationError(LogicalFrameworkValidationError):
    pass


class LogicalFrameworkScopeValidationError(LogicalFrameworkValidationError):
    pass


class LogicalFrameworkConflictValidationError(LogicalFrameworkValidationError):
    pass


_UNSET = object()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


class LogicalFrameworkService:
    def __init__(
        self,
        repository: LogicalFrameworkRepository,
        *,
        now: Callable[[], str] = _utc_now_iso,
        id_factory: Callable[[str], str] = _new_id,
    ):
        self.repository = repository
        self.now = now
        self.id_factory = id_factory

    def _repository_call(self, operation: Callable[[], Any]) -> Any:
        try:
            return operation()
        except LogicalFrameworkNotFoundError as exc:
            raise LogicalFrameworkNotFoundValidationError(str(exc)) from exc
        except LogicalFrameworkScopeError as exc:
            raise LogicalFrameworkScopeValidationError(str(exc)) from exc
        except LogicalFrameworkConflictError as exc:
            raise LogicalFrameworkConflictValidationError(str(exc)) from exc
        except LogicalFrameworkRepositoryError as exc:
            raise LogicalFrameworkValidationError(str(exc)) from exc

    def _validate_parent(
        self,
        organization_id: str,
        project_id: str,
        result_id: str,
        result_type: str,
        parent_id: str,
    ) -> Optional[ResultNode]:
        if parent_id and parent_id == result_id:
            raise LogicalFrameworkValidationError("A result cannot parent itself.")
        if result_type == "goal":
            if parent_id:
                raise LogicalFrameworkValidationError("A Goal cannot have a parent result.")
            return None
        expected_parent_type = (
            "goal" if result_type == "outcome" else "outcome" if result_type == "output" else ""
        )
        if not expected_parent_type:
            raise LogicalFrameworkValidationError(f"Unsupported result type: '{result_type}'.")
        if not parent_id:
            raise LogicalFrameworkValidationError(f"A {result_type.title()} requires a parent result.")
        parent = self._repository_call(
            lambda: self.repository.require_result(organization_id, project_id, parent_id)
        )
        if parent.result_type != expected_parent_type:
            raise LogicalFrameworkValidationError(
                f"A {result_type.title()} must have a {expected_parent_type.title()} parent."
            )
        return parent

    def create_result(
        self,
        organization_id: str,
        project_id: str,
        result_type: str,
        title: str,
        *,
        description: str = "",
        parent_id: str = "",
        display_order: int = 0,
        status: str = "active",
        result_id: Optional[str] = None,
    ) -> ResultNode:
        result_type = str(result_type or "").strip().lower()
        result_id = str(result_id or self.id_factory(result_type or "result")).strip()
        self._repository_call(lambda: self.repository.require_project(organization_id, project_id))
        existing = self._repository_call(
            lambda: self.repository.get_result(organization_id, project_id, result_id)
        )
        if existing is not None:
            raise LogicalFrameworkValidationError(f"Result ID '{result_id}' already exists.")
        self._validate_parent(
            organization_id, project_id, result_id, result_type, str(parent_id or "").strip()
        )
        timestamp = self.now()
        try:
            node = ResultNode(
                id=result_id,
                organization_id=organization_id,
                project_id=project_id,
                result_type=result_type,
                title=title,
                description=description,
                parent_id=parent_id,
                display_order=display_order,
                status=status,
                created_at=timestamp,
                updated_at=timestamp,
            )
        except ValueError as exc:
            raise LogicalFrameworkValidationError(str(exc)) from exc
        return self._repository_call(lambda: self.repository.save_result(node))

    def create_goal(self, organization_id: str, project_id: str, title: str, **kwargs: Any) -> ResultNode:
        return self.create_result(organization_id, project_id, "goal", title, **kwargs)

    def create_outcome(
        self, organization_id: str, project_id: str, goal_id: str, title: str, **kwargs: Any
    ) -> ResultNode:
        return self.create_result(
            organization_id, project_id, "outcome", title, parent_id=goal_id, **kwargs
        )

    def create_output(
        self, organization_id: str, project_id: str, outcome_id: str, title: str, **kwargs: Any
    ) -> ResultNode:
        return self.create_result(
            organization_id, project_id, "output", title, parent_id=outcome_id, **kwargs
        )

    def update_result(
        self,
        organization_id: str,
        project_id: str,
        result_id: str,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        parent_id: Any = _UNSET,
        display_order: Optional[int] = None,
        status: Optional[str] = None,
        result_type: Optional[str] = None,
    ) -> ResultNode:
        current = self._repository_call(
            lambda: self.repository.require_result(organization_id, project_id, result_id)
        )
        if result_type is not None and str(result_type).strip().lower() != current.result_type:
            raise LogicalFrameworkValidationError("Changing a result's level is not supported.")
        next_parent_id = current.parent_id if parent_id is _UNSET else str(parent_id or "").strip()
        self._validate_parent(
            organization_id, project_id, current.id, current.result_type, next_parent_id
        )
        try:
            updated = replace(
                current,
                title=current.title if title is None else title,
                description=current.description if description is None else description,
                parent_id=next_parent_id,
                display_order=current.display_order if display_order is None else display_order,
                status=current.status if status is None else status,
                updated_at=self.now(),
            )
        except ValueError as exc:
            raise LogicalFrameworkValidationError(str(exc)) from exc
        return self._repository_call(lambda: self.repository.save_result(updated))

    def reorder_result(
        self, organization_id: str, project_id: str, result_id: str, display_order: int
    ) -> ResultNode:
        return self.update_result(
            organization_id, project_id, result_id, display_order=display_order
        )

    def reorder_siblings(
        self,
        organization_id: str,
        project_id: str,
        ordered_result_ids: List[str],
    ) -> List[ResultNode]:
        ordered_ids = [str(result_id or "").strip() for result_id in ordered_result_ids]
        if not ordered_ids or any(not result_id for result_id in ordered_ids):
            raise LogicalFrameworkValidationError("ordered_result_ids must contain result IDs.")
        if len(set(ordered_ids)) != len(ordered_ids):
            raise LogicalFrameworkValidationError("ordered_result_ids cannot contain duplicates.")

        requested = [
            self._repository_call(
                lambda result_id=result_id: self.repository.require_result(
                    organization_id, project_id, result_id
                )
            )
            for result_id in ordered_ids
        ]
        branch_type = requested[0].result_type
        branch_parent_id = requested[0].parent_id
        if any(
            node.result_type != branch_type or node.parent_id != branch_parent_id
            for node in requested
        ):
            raise LogicalFrameworkValidationError(
                "Only sibling results from the same hierarchy branch may be reordered together."
            )

        siblings = [
            node
            for node in self._repository_call(
                lambda: self.repository.list_results(organization_id, project_id)
            )
            if node.result_type == branch_type and node.parent_id == branch_parent_id
        ]
        if set(ordered_ids) != {node.id for node in siblings}:
            raise LogicalFrameworkValidationError(
                "A reorder request must include every sibling in the hierarchy branch."
            )

        timestamp = self.now()
        reordered = [
            replace(node, display_order=index, updated_at=timestamp)
            for index, node in enumerate(requested)
        ]
        for node in reordered:
            self._repository_call(lambda node=node: self.repository.save_result(node))
        return reordered

    def archive_result(self, organization_id: str, project_id: str, result_id: str) -> ResultNode:
        return self.update_result(organization_id, project_id, result_id, status="archived")

    def delete_result(self, organization_id: str, project_id: str, result_id: str) -> None:
        self._repository_call(
            lambda: self.repository.delete_result(organization_id, project_id, result_id)
        )

    def get_result(
        self, organization_id: str, project_id: str, result_id: str
    ) -> ResultNode:
        return self._repository_call(
            lambda: self.repository.require_result(organization_id, project_id, result_id)
        )

    def link_indicator(
        self, organization_id: str, project_id: str, indicator_id: str, result_id: str
    ) -> IndicatorResultLink:
        self._repository_call(
            lambda: self.repository.require_indicator(organization_id, project_id, indicator_id)
        )
        result = self._repository_call(
            lambda: self.repository.require_result(organization_id, project_id, result_id)
        )
        if result.result_type not in {"outcome", "output"}:
            raise LogicalFrameworkValidationError("Indicators may link only to an Outcome or Output.")
        existing = self._repository_call(
            lambda: self.repository.get_indicator_link(organization_id, project_id, indicator_id)
        )
        timestamp = self.now()
        link = IndicatorResultLink(
            id=existing.id if existing else self.id_factory("indicator_result_link"),
            organization_id=organization_id,
            project_id=project_id,
            indicator_id=indicator_id,
            result_id=result.id,
            result_type=result.result_type,
            created_at=existing.created_at if existing else timestamp,
            updated_at=timestamp,
        )
        return self._repository_call(lambda: self.repository.save_indicator_link(link))

    def unlink_indicator(
        self, organization_id: str, project_id: str, indicator_id: str
    ) -> IndicatorResultLink:
        existing = self._repository_call(
            lambda: self.repository.get_indicator_link(
                organization_id, project_id, indicator_id
            )
        )
        if existing is None:
            raise LogicalFrameworkNotFoundValidationError(
                f"Indicator '{indicator_id}' does not have a canonical result link."
            )
        self._repository_call(
            lambda: self.repository.delete_indicator_link(organization_id, project_id, indicator_id)
        )
        return existing

    def clone_hierarchy(
        self,
        source_organization_id: str,
        source_project_id: str,
        destination_organization_id: str,
        destination_project_id: str,
    ) -> Dict[str, Any]:
        self._repository_call(
            lambda: self.repository.require_project(source_organization_id, source_project_id)
        )
        self._repository_call(
            lambda: self.repository.require_project(
                destination_organization_id, destination_project_id
            )
        )
        if source_organization_id != destination_organization_id:
            raise LogicalFrameworkScopeValidationError(
                "Logical Framework cloning across organizations is not supported."
            )
        if self._repository_call(
            lambda: self.repository.list_results(
                destination_organization_id, destination_project_id
            )
        ):
            raise LogicalFrameworkConflictValidationError(
                "The destination project already has a Logical Framework."
            )

        source_nodes = self._repository_call(
            lambda: self.repository.list_results(source_organization_id, source_project_id)
        )
        id_map: Dict[str, str] = {}
        cloned_nodes: List[ResultNode] = []
        for result_type in ("goal", "outcome", "output"):
            for source in [node for node in source_nodes if node.result_type == result_type]:
                parent_id = id_map.get(source.parent_id, "")
                if source.parent_id and not parent_id:
                    raise LogicalFrameworkValidationError(
                        f"Cannot clone result '{source.id}' because its parent was not cloned."
                    )
                clone = self.create_result(
                    destination_organization_id,
                    destination_project_id,
                    result_type,
                    source.title,
                    description=source.description,
                    parent_id=parent_id,
                    display_order=source.display_order,
                    status=source.status,
                )
                id_map[source.id] = clone.id
                cloned_nodes.append(clone)
        return {
            "id_map": id_map,
            "results": cloned_nodes,
            "indicator_links_cloned": 0,
        }

    def validate_integrity(self) -> None:
        seen_result_ids = set()
        for node in self.repository.state.logical_framework_results:
            if node.id in seen_result_ids:
                raise LogicalFrameworkValidationError(f"Duplicate result ID: '{node.id}'.")
            seen_result_ids.add(node.id)
            self._repository_call(
                lambda node=node: self.repository.require_project(node.organization_id, node.project_id)
            )
            self._validate_parent(
                node.organization_id,
                node.project_id,
                node.id,
                node.result_type,
                node.parent_id,
            )

        seen_indicator_ids = set()
        for link in self.repository.state.indicator_result_links:
            if link.indicator_id in seen_indicator_ids:
                raise LogicalFrameworkValidationError(
                    f"Indicator '{link.indicator_id}' has more than one canonical result link."
                )
            seen_indicator_ids.add(link.indicator_id)
            self._repository_call(
                lambda link=link: self.repository.require_indicator(
                    link.organization_id, link.project_id, link.indicator_id
                )
            )
            result = self._repository_call(
                lambda link=link: self.repository.require_result(
                    link.organization_id, link.project_id, link.result_id
                )
            )
            if result.result_type not in {"outcome", "output"} or link.result_type != result.result_type:
                raise LogicalFrameworkValidationError(
                    "Indicator link target must be its declared Outcome or Output."
                )

    def get_hierarchy(self, organization_id: str, project_id: str) -> List[Dict[str, Any]]:
        nodes = self._repository_call(
            lambda: self.repository.list_results(organization_id, project_id)
        )
        outcomes_by_goal: Dict[str, List[ResultNode]] = {}
        outputs_by_outcome: Dict[str, List[ResultNode]] = {}
        for node in nodes:
            if node.result_type == "outcome":
                outcomes_by_goal.setdefault(node.parent_id, []).append(node)
            elif node.result_type == "output":
                outputs_by_outcome.setdefault(node.parent_id, []).append(node)
        return [
            {
                "result": goal,
                "outcomes": [
                    {"result": outcome, "outputs": outputs_by_outcome.get(outcome.id, [])}
                    for outcome in outcomes_by_goal.get(goal.id, [])
                ],
            }
            for goal in nodes
            if goal.result_type == "goal"
        ]

    @staticmethod
    def serialize_result(node: ResultNode) -> Dict[str, Any]:
        return {
            "id": node.id,
            "organization_id": node.organization_id,
            "project_id": node.project_id,
            "result_type": node.result_type,
            "title": node.title,
            "description": node.description,
            "parent_id": node.parent_id,
            "display_order": node.display_order,
            "status": node.status,
            "created_at": node.created_at,
            "updated_at": node.updated_at,
        }

    @staticmethod
    def serialize_indicator(indicator: Any, link: Optional[IndicatorResultLink]) -> Dict[str, Any]:
        return {
            "id": str(getattr(indicator, "id", "")),
            "name": str(getattr(indicator, "name", "")),
            "unit": str(getattr(indicator, "unit", "")),
            "frequency": str(getattr(indicator, "frequency", "")),
            "direction": str(getattr(indicator, "direction", "")),
            "level": str(getattr(indicator, "level", "")),
            "target": getattr(indicator, "target", None),
            "baseline": getattr(indicator, "baseline", None),
            "organization_id": str(getattr(indicator, "organization_id", "")),
            "project_id": str(getattr(indicator, "project_id", "")),
            "result_id": link.result_id if link else "",
            "result_type": link.result_type if link else "",
            "link_id": link.id if link else "",
        }

    def get_project_logical_framework(
        self, organization_id: str, project_id: str
    ) -> Dict[str, Any]:
        project = self._repository_call(
            lambda: self.repository.require_project(organization_id, project_id)
        )
        hierarchy = self.get_hierarchy(organization_id, project_id)
        links = self._repository_call(
            lambda: self.repository.list_indicator_links(organization_id, project_id)
        )
        links_by_result: Dict[str, List[IndicatorResultLink]] = {}
        links_by_indicator = {link.indicator_id: link for link in links}
        for link in links:
            links_by_result.setdefault(link.result_id, []).append(link)
        indicators = {
            str(getattr(indicator, "id", "")): indicator
            for indicator in getattr(project, "indicators", []) or []
        }

        def attached_indicators(result_id: str) -> List[Dict[str, Any]]:
            return [
                self.serialize_indicator(indicators[link.indicator_id], link)
                for link in links_by_result.get(result_id, [])
                if link.indicator_id in indicators
            ]

        goals: List[Dict[str, Any]] = []
        for goal_branch in hierarchy:
            goal = self.serialize_result(goal_branch["result"])
            outcomes: List[Dict[str, Any]] = []
            for outcome_branch in goal_branch["outcomes"]:
                outcome = self.serialize_result(outcome_branch["result"])
                outcome["indicators"] = attached_indicators(outcome["id"])
                outputs: List[Dict[str, Any]] = []
                for output_node in outcome_branch["outputs"]:
                    output = self.serialize_result(output_node)
                    output["indicators"] = attached_indicators(output["id"])
                    outputs.append(output)
                outcome["outputs"] = outputs
                outcomes.append(outcome)
            goal["outcomes"] = outcomes
            goals.append(goal)

        return {
            "project_id": project_id,
            "organization_id": organization_id,
            "goals": goals,
            "unassigned_indicators": [
                self.serialize_indicator(indicator, None)
                for indicator_id, indicator in indicators.items()
                if indicator_id not in links_by_indicator
            ],
        }
