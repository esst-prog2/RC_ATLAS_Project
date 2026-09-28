from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Iterable, Optional


def _text(value: Any) -> str:
    return str(value or '').strip()


@dataclass(frozen=True)
class AuthenticatedTenantContext:
    actor_id: str
    username: str
    organization_id: str
    role: str
    effective_permissions: tuple[str, ...]
    full_name: str = ''
    email: str = ''
    team_id: str = ''

    def __post_init__(self) -> None:
        if not _text(self.actor_id) or not _text(self.organization_id):
            raise ValueError('Authenticated tenant context requires actor and organization IDs.')

    @property
    def id(self) -> str:
        return self.actor_id

    @property
    def permissions(self) -> tuple[str, ...]:
        return self.effective_permissions

    @classmethod
    def from_user(cls, user: Any, permissions: Iterable[str]) -> 'AuthenticatedTenantContext':
        return cls(
            actor_id=_text(getattr(user, 'id', '')),
            username=_text(getattr(user, 'username', '')),
            organization_id=_text(getattr(user, 'organization_id', '')),
            role=_text(getattr(user, 'role', '')),
            effective_permissions=tuple(sorted({_text(item) for item in permissions if _text(item)})),
            full_name=_text(getattr(user, 'full_name', '')),
            email=_text(getattr(user, 'email', '')),
            team_id=_text(getattr(user, 'team_id', '')),
        )


def _organization_id(value: Any) -> str:
    return _text(getattr(value, 'organization_id', ''))


def find_scoped_project(data: Any, organization_id: str, project_id: str) -> Optional[Any]:
    return next(
        (
            project
            for project in getattr(data, 'projects', [])
            if _text(getattr(project, 'id', '')) == _text(project_id)
            and _organization_id(project) == _text(organization_id)
        ),
        None,
    )


def find_scoped_user(data: Any, organization_id: str, user_id: str) -> Optional[Any]:
    return next(
        (
            user
            for user in getattr(data, 'users', [])
            if _text(getattr(user, 'id', '')) == _text(user_id)
            and _organization_id(user) == _text(organization_id)
        ),
        None,
    )


def find_scoped_team(data: Any, organization_id: str, team_id: str) -> Optional[Any]:
    return next(
        (
            team
            for team in getattr(data, 'teams', [])
            if _text(getattr(team, 'id', '')) == _text(team_id)
            and _organization_id(team) == _text(organization_id)
        ),
        None,
    )


def find_scoped_dataset(data: Any, organization_id: str, dataset_id: str) -> Optional[Any]:
    return next(
        (
            dataset
            for dataset in getattr(data, 'tidy_datasets', [])
            if _text(getattr(dataset, 'id', '')) == _text(dataset_id)
            and dataset_organization_id(data, dataset) == _text(organization_id)
        ),
        None,
    )


def _resolve_organization_id(explicit: str, parent_owner_sets: Iterable[set[str]]) -> str:
    candidates = {explicit} if explicit else None
    for owners in parent_owner_sets:
        valid_owners = {owner for owner in owners if owner}
        candidates = valid_owners if candidates is None else candidates.intersection(valid_owners)
    if candidates is None:
        return explicit
    return next(iter(candidates)) if len(candidates) == 1 else ''


def _project_organization_ids(data: Any, project_id: str) -> set[str]:
    return {
        _organization_id(project)
        for project in getattr(data, 'projects', [])
        if _text(getattr(project, 'id', '')) == _text(project_id) and _organization_id(project)
    }


def project_organization_id(data: Any, project_id: str) -> str:
    owners = _project_organization_ids(data, project_id)
    return next(iter(owners)) if len(owners) == 1 else ''


def dataset_organization_id(data: Any, dataset: Any) -> str:
    explicit = _organization_id(dataset)
    project_id = _text(getattr(dataset, 'project_id', ''))
    parent_owner_sets = [_project_organization_ids(data, project_id)] if project_id else []
    return _resolve_organization_id(explicit, parent_owner_sets)


def _dataset_organization_ids(data: Any, dataset_id: str) -> set[str]:
    return {
        owner
        for dataset in getattr(data, 'tidy_datasets', [])
        if _text(getattr(dataset, 'id', '')) == _text(dataset_id)
        for owner in [dataset_organization_id(data, dataset)]
        if owner
    }


def reporting_record_organization_id(data: Any, record: Any) -> str:
    explicit = _organization_id(record)
    parent_owner_sets = []
    project_id = _text(getattr(record, 'project_id', ''))
    dataset_id = _text(getattr(record, 'source_dataset_id', ''))
    if project_id:
        parent_owner_sets.append(_project_organization_ids(data, project_id))
    if dataset_id:
        parent_owner_sets.append(_dataset_organization_ids(data, dataset_id))
    return _resolve_organization_id(explicit, parent_owner_sets)


def semantic_mapping_organization_id(data: Any, mapping: Any) -> str:
    explicit = _organization_id(mapping)
    dataset_id = _text(getattr(mapping, 'dataset_id', ''))
    if not dataset_id:
        return ''
    return _resolve_organization_id(explicit, [_dataset_organization_ids(data, dataset_id)])


def notification_rule_organization_id(data: Any, rule: Any) -> str:
    explicit = _organization_id(rule)
    parent_owner_sets = []
    project_id = _text(getattr(rule, 'project_id', ''))
    dataset_id = _text(getattr(rule, 'dataset_id', ''))
    if project_id:
        parent_owner_sets.append(_project_organization_ids(data, project_id))
    if dataset_id:
        parent_owner_sets.append(_dataset_organization_ids(data, dataset_id))
    return _resolve_organization_id(explicit, parent_owner_sets)


def audit_event_organization_id(data: Any, event: Any) -> str:
    explicit = _organization_id(event)
    if explicit:
        return explicit
    target_type = _text(getattr(event, 'target_type', '')).lower()
    target_id = _text(getattr(event, 'target_id', ''))
    if target_type == 'project':
        return project_organization_id(data, target_id)
    if target_type == 'dataset':
        matches = [item for item in getattr(data, 'tidy_datasets', []) if _text(getattr(item, 'id', '')) == target_id]
        owners = {dataset_organization_id(data, item) for item in matches}
        owners.discard('')
        return next(iter(owners)) if len(owners) == 1 else ''
    return ''


def scope_snapshot_for_tenant(
    data: Any,
    context: Optional[AuthenticatedTenantContext],
    *,
    operational_projects_only: bool = False,
) -> Any:
    if context is None:
        return deepcopy(data)
    scoped = deepcopy(data)
    organization_id = context.organization_id
    scoped.organizations = [item for item in getattr(scoped, 'organizations', []) if _text(getattr(item, 'id', '')) == organization_id]
    scoped.users = [item for item in getattr(scoped, 'users', []) if _organization_id(item) == organization_id]
    scoped.teams = [item for item in getattr(scoped, 'teams', []) if _organization_id(item) == organization_id]
    scoped.projects = [
        item
        for item in getattr(scoped, 'projects', [])
        if _organization_id(item) == organization_id
        and (
            not operational_projects_only
            or _text(getattr(item, 'lifecycle_status', '') or getattr(item, 'status', '')).lower() not in {'draft', 'archived'}
        )
    ]
    project_ids = {_text(getattr(item, 'id', '')) for item in scoped.projects}
    scoped.ops_by_project = {
        key: value for key, value in getattr(scoped, 'ops_by_project', {}).items() if _text(key) in project_ids
    }
    scoped.logical_framework_results = [
        item
        for item in getattr(scoped, 'logical_framework_results', [])
        if _organization_id(item) == organization_id and _text(getattr(item, 'project_id', '')) in project_ids
    ]
    scoped.indicator_result_links = [
        item
        for item in getattr(scoped, 'indicator_result_links', [])
        if _organization_id(item) == organization_id and _text(getattr(item, 'project_id', '')) in project_ids
    ]
    scoped.tidy_datasets = [
        item for item in getattr(scoped, 'tidy_datasets', []) if dataset_organization_id(data, item) == organization_id
    ]
    dataset_ids = {_text(getattr(item, 'id', '')) for item in scoped.tidy_datasets}
    scoped.reporting_records = [
        item
        for item in getattr(scoped, 'reporting_records', [])
        if reporting_record_organization_id(data, item) == organization_id
    ]
    scoped.semantic_mappings = [
        item
        for item in getattr(scoped, 'semantic_mappings', [])
        if semantic_mapping_organization_id(data, item) == organization_id
        and _text(getattr(item, 'dataset_id', '')) in dataset_ids
    ]
    scoped.dashboard_templates = [
        item for item in getattr(scoped, 'dashboard_templates', []) if _organization_id(item) == organization_id
    ]
    scoped.notification_rules = [
        item for item in getattr(scoped, 'notification_rules', []) if notification_rule_organization_id(data, item) == organization_id
    ]
    scoped.audit_events = [
        item for item in getattr(scoped, 'audit_events', []) if audit_event_organization_id(data, item) == organization_id
    ]
    return scoped


def workspace_is_uninitialized(data: Any) -> bool:
    collection_names = (
        'organizations',
        'users',
        'teams',
        'projects',
        'logical_framework_results',
        'indicator_result_links',
        'tidy_datasets',
        'reporting_records',
        'semantic_mappings',
        'dashboard_templates',
        'notification_rules',
        'audit_events',
    )
    return not any(getattr(data, name, None) for name in collection_names) and not bool(getattr(data, 'ops_by_project', {}))
