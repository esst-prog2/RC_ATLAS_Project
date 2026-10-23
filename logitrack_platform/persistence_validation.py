"""Lossless aggregate validation and relational ownership mapping.

No inference or repair: invalid historical records block the complete transaction.
"""
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import re


DOMAINS = (
    'organizations', 'teams', 'projects', 'logical_framework_results',
    'indicator_result_links', 'tidy_datasets', 'reporting_records',
    'semantic_mappings', 'dashboard_templates', 'notification_rules', 'users',
    'audit_events', 'sessions', 'idempotency_records',
)


class SnapshotInvalid(ValueError):
    def __init__(self, issues):
        self.issues = issues
        super().__init__('Workspace ownership or relationships are invalid.')


def fingerprint(payload):
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


@dataclass
class IntegrityGraph:
    organizations: list
    entities: list
    relationships: list

    @property
    def counts(self):
        return dict(sorted(Counter(row[0] for row in self.entities).items())) | {
            'relationships': len(self.relationships)}


def validate_snapshot(payload, *, complete=False):
    issues, entities, edges, seen = [], [], [], {}

    def issue(path, code):
        issues.append({'path': path, 'code': code})

    if not isinstance(payload, dict):
        raise SnapshotInvalid([{'path': '/', 'code': 'INVALID_DOCUMENT'}])
    allowed = set(DOMAINS) | {'ops_by_project', 'workspace_version'}
    for key in payload.keys() - allowed:
        issue(key, 'UNMAPPED_FIELD')
    if complete:
        for key in allowed - payload.keys():
            issue(key, 'MISSING_DOMAIN_REQUIRES_RECONCILIATION')
    version = payload.get('workspace_version', 0)
    if type(version) is not int or version < 0:
        issue('workspace_version', 'INVALID_VERSION')

    def items(value, path):
        if not isinstance(value, list):
            issue(path, 'INVALID_COLLECTION')
            return []
        return value

    def add(kind, row, path, project=None):
        if not isinstance(row, dict):
            issue(path, 'INVALID_RECORD')
            return
        identifier = row.get('id')
        if not isinstance(identifier, str) or not identifier or identifier != identifier.strip():
            issue(path, 'INVALID_ID')
            return
        org = row.get('organization_id') or None
        if kind == 'organizations':
            org = identifier
        if org is not None and (not isinstance(org, str) or org != org.strip()):
            issue(path, 'INVALID_OWNER')
            return
        global_record = (kind == 'dashboard_templates' and row.get('scope') == 'builtin') or (
            kind == 'audit_events' and not row.get('actor_id'))
        if not org and not global_record:
            issue(path, 'BLANK_OWNER_REQUIRES_APPROVAL' if kind == 'activities' else 'MISSING_OWNER')
        if (kind, identifier, org) in seen:
            issue(path, 'DUPLICATE_OR_AMBIGUOUS_ID')
            return
        declared_project = row.get('project_id') or None
        if project and declared_project and declared_project != project:
            issue(path, 'CONFLICTING_PROJECT')
        project = project or declared_project
        # Nested collections are represented separately in this integrity index.
        attributes = {k: v for k, v in row.items() if k not in
                      {'indicators', 'team_assignments', 'activities', 'tasks', 'rows'}}
        record = (kind, identifier, org, project, attributes)
        entities.append(record)
        seen[(kind, identifier, org)] = record
        if project and kind != 'projects':
            edges.append((kind, identifier, org, 'project', 'projects', project))
        return record

    for kind in DOMAINS:
        for i, row in enumerate(items(payload.get(kind, []), kind)):
            path = f'{kind}/{i}'
            record = add(kind, row, path)
            if kind == 'projects' and record:
                for child_kind, key in [('indicators', 'indicators'), ('assignments', 'team_assignments')]:
                    for j, child in enumerate(items(row.get(key, []), path+'/'+key)):
                        add(child_kind, child, f'{path}/{key}/{j}', row['id'])
    ops = payload.get('ops_by_project', {})
    if not isinstance(ops, dict):
        issue('ops_by_project', 'INVALID_COLLECTION')
        ops = {}
    for project_id, group in ops.items():
        if not any(k == 'projects' and i == project_id for k, i, o in seen):
            issue(f'ops_by_project/{project_id}', 'ORPHAN_PROJECT')
        if not isinstance(group, dict) or set(group) - {'activities'}:
            issue(f'ops_by_project/{project_id}', 'INVALID_OPS_GROUP')
            continue
        for i, activity in enumerate(items(group.get('activities', []), project_id)):
            path = f'ops_by_project/{project_id}/activities/{i}'
            record = add('activities', activity, path, project_id)
            if record:
                for j, task in enumerate(items(activity.get('tasks', []), path+'/tasks')):
                    child = add('tasks', task, f'{path}/tasks/{j}', project_id)
                    if child:
                        edges.append(('tasks', child[1], child[2], 'activity', 'activities', record[1]))

    references = {
        'teams': {'team_lead_user_id': 'users'},
        'users': {'team_id': 'teams'},
        'projects': {'created_by_user_id': 'users', 'cloned_from_project_id': 'projects'},
        'assignments': {'user_id': 'users', 'team_id': 'teams', 'assigned_by_user_id': 'users'},
        'tasks': {'assignee_user_id': 'users', 'validator_user_id': 'users',
                  'approver_user_id': 'users', 'linked_indicator_id': 'indicators'},
        'logical_framework_results': {'parent_id': 'logical_framework_results'},
        'indicator_result_links': {'indicator_id': 'indicators', 'result_id': 'logical_framework_results'},
        'semantic_mappings': {'dataset_id': 'tidy_datasets'},
        'reporting_records': {'indicator_id': 'indicators', 'source_dataset_id': 'tidy_datasets'},
        'notification_rules': {'indicator_id': 'indicators', 'dataset_id': 'tidy_datasets'},
        'sessions': {'user_id': 'users'},
        'idempotency_records': {'actor_user_id': 'users'},
        'audit_events': {'actor_id': 'users'},
    }
    required = {'users': ('username',), 'sessions': ('user_id', 'token_hash'),
                'idempotency_records': ('actor_user_id', 'operation', 'key_hash', 'request_hash'),
                'assignments': ('user_id',), 'semantic_mappings': ('dataset_id',),
                'indicator_result_links': ('indicator_id', 'result_id')}
    unique_values = set()
    for kind, identifier, org, project, row in entities:
        if kind in {'sessions', 'idempotency_records'}:
            timestamp_fields = ('created_at','expires_at') if kind == 'idempotency_records' else (
                'created_at','last_seen_at','idle_expires_at','absolute_expires_at')
            for field in timestamp_fields:
                try:
                    value = datetime.fromisoformat(row[field].replace('Z','+00:00'))
                    if value.tzinfo is None:
                        raise ValueError('Timezone required')
                except (KeyError, AttributeError, ValueError, TypeError):
                    issue(f'{kind}/{identifier}/{field}', 'INVALID_TIMESTAMP')
            hash_fields = ('key_hash','request_hash') if kind == 'idempotency_records' else ('token_hash',)
            if row.get('csrf_token_hash'):
                hash_fields += ('csrf_token_hash',)
            for field in hash_fields:
                if not isinstance(row.get(field),str) or not re.fullmatch('[a-f0-9]{64}',row[field]):
                    issue(f'{kind}/{identifier}/{field}', 'INVALID_SECRET_HASH')
        uniqueness = None
        if kind == 'users' and isinstance(row.get('username'),str):
            uniqueness = (kind, row['username'].lower())
        elif kind == 'sessions' and isinstance(row.get('token_hash'),str):
            uniqueness = (kind, row['token_hash'])
        elif kind == 'projects' and row.get('project_code'):
            uniqueness = (kind, org, str(row['project_code']).lower())
        elif kind == 'idempotency_records':
            try:
                if datetime.fromisoformat(row['expires_at'].replace('Z','+00:00')) > datetime.now(timezone.utc):
                    uniqueness = (kind, org, row.get('actor_user_id'),row.get('operation'),row.get('key_hash'))
            except (KeyError, ValueError, TypeError, AttributeError):
                pass  # Already reported as invalid timestamp above.
            if row.get('operation') in {'POST:/v1/projects','POST:/v1/admin/projects'}:
                if row.get('resource_id'):
                    edges.append((kind,identifier,org,'resource_id','projects',row['resource_id']))
                else:
                    issue(f'{kind}/{identifier}/resource_id','MISSING_REQUIRED_FIELD')
        if uniqueness is not None:
            try:
                if uniqueness in unique_values:
                    issue(f'{kind}/{identifier}', 'DUPLICATE_UNIQUE_KEY')
                unique_values.add(uniqueness)
            except TypeError:
                issue(f'{kind}/{identifier}', 'INVALID_UNIQUE_KEY')
        for field in required.get(kind, ()):
            if not isinstance(row.get(field), str) or not row[field].strip():
                issue(f'{kind}/{identifier}/{field}', 'MISSING_REQUIRED_FIELD')
        if org and ('organizations', org, org) not in seen:
            issue(f'{kind}/{identifier}', 'ORPHAN_ORGANIZATION')
        for field, target_kind in references.get(kind, {}).items():
            if row.get(field):
                edges.append((kind, identifier, org, field, target_kind, row[field]))
        if kind == 'activities':
            for target in items(row.get('linked_indicator_ids', []), f'activities/{identifier}/links'):
                edges.append((kind, identifier, org, 'indicator', 'indicators', target))

    for source_kind, source_id, org, field, target_kind, target_id in edges:
        if not isinstance(target_id, str):
            issue(f'{source_kind}/{source_id}/{field}', 'INVALID_REFERENCE')
            continue
        target = seen.get((target_kind, target_id, org))
        source = seen[(source_kind, source_id, org)]
        if target is None:
            collision = any(k == target_kind and i == target_id for k, i, o in seen)
            issue(f'{source_kind}/{source_id}/{field}', 'CONFLICTING_OWNERSHIP' if collision else 'ORPHAN_REFERENCE')
        elif not org or target[2] != org:
            issue(f'{source_kind}/{source_id}/{field}', 'CONFLICTING_OWNERSHIP')
        elif source[3] and target[3] and source[3] != target[3]:
            issue(f'{source_kind}/{source_id}/{field}', 'CONFLICTING_PROJECT')
    try:
        fingerprint(payload)  # Also rejects NaN/Infinity and non-JSON data.
    except (ValueError, TypeError):
        issue('/', 'INVALID_JSON_VALUE')
    if issues:
        raise SnapshotInvalid(issues)
    return IntegrityGraph([row[1] for row in entities if row[0] == 'organizations'],
                          entities, sorted(set(edges)))
