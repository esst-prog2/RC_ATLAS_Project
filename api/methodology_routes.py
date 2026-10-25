"""Narrow tenant-scoped methodology API using the existing aggregate transaction."""
from copy import deepcopy
from typing import Any, Dict, Optional

from services import methodology as core
from services.tenant_security import find_scoped_project, find_scoped_dataset


PREFIX = '/v1/projects/{project_id}/indicators/{indicator_id}'


def register_methodology_routes(app, *, load, save, authorize, audit, now, header, error):
    def fail(code, message):
        raise error(status_code=code, detail=message)

    def scope(project_id, indicator_id, api_key, token, *, write=False):
        data = load()
        actor = authorize(data, api_key, token, required_permissions=['VIEW_INDICATORS', 'VIEW_REPORTS'], require_all_permissions=True)
        if write and (actor.role != 'organization_admin' or 'MANAGE_ORGANIZATION' not in actor.permissions):
            fail(403, 'Methodology registration requires an organization administrator.')
        project = find_scoped_project(data, actor.organization_id, project_id)
        indicator = next((i for i in project.indicators if i.id == indicator_id), None) if project else None
        if indicator is None or indicator.organization_id != actor.organization_id or indicator.project_id != project_id:
            fail(404, 'Indicator methodology resource not found.')
        identity = {'organization_id': actor.organization_id, 'project_id': project_id, 'indicator_id': indicator_id}
        try:
            core.validate_history(indicator.methodology, identity)
        except core.MethodologyError:
            fail(409, 'Methodology history is unavailable or invalid.')
        return data, actor, indicator, identity

    def history(indicator):
        return indicator.methodology or {'schema_version': 1, 'definitions': [], 'instances': []}

    def version_check(data, payload):
        version = payload.get('expected_workspace_version')
        if type(version) is not int or version < 0:
            fail(400, 'An expected_workspace_version is required.')
        if version != data.workspace_version:
            fail(409, 'The workspace changed. Reload and retry.')

    def compute(data, actor, indicator, method_id, version, start, end, as_of, locale):
        try:
            ctx = core.context(start, end, as_of, locale)
        except core.MethodologyError as exc:
            fail(400, str(exc))
        d = next((d for d in history(indicator)['definitions'] if d['methodology_id'] == method_id and d['version'] == version), None)
        if d is None:
            if method_id or version:
                fail(404, 'Methodology version not found.')
            return {'definition': None, 'result': {'state': 'UNCONFIGURED', 'display_value': None,
                    'methodology_version': None, 'formula': None, 'context': ctx,
                    'warnings': ['APPROVED_INDICATOR_DEFINITION_REQUIRED'],
                    'limitations': ['No method or target is inferred from legacy indicator values.']}, 'historical': False}
        dataset = find_scoped_dataset(data, actor.organization_id, d['source_dataset_id'])
        if dataset is None:
            fail(404, 'Calculation source is unavailable.')
        try:
            result = core.calculate(d, dataset.rows, ctx)
        except core.MethodologyError:
            fail(409, 'Methodology calculation is unavailable or invalid.')
        return {'definition': deepcopy(d), 'result': result, 'historical': False}

    @app.get(PREFIX + '/methodology')
    def get_methodology(project_id: str, indicator_id: str,
                        x_api_key: Optional[str] = header(default=None, alias='X-API-Key'),
                        x_auth_token: Optional[str] = header(default=None, alias='X-Auth-Token')):
        data, actor, indicator, _ = scope(project_id, indicator_id, x_api_key, x_auth_token)
        h = history(indicator)
        return {'workspace_version': data.workspace_version, 'definitions': deepcopy(h['definitions']),
                'instances': [{'calculation_id': x['result']['calculation_id'], 'saved_at': x['saved_at'],
                               'methodology_version': x['result']['methodology_version']} for x in h['instances']],
                'state': 'AVAILABLE' if h['definitions'] else 'UNCONFIGURED'}

    @app.post(PREFIX + '/methodology')
    def add_methodology(project_id: str, indicator_id: str, payload: Dict[str, Any],
                        x_api_key: Optional[str] = header(default=None, alias='X-API-Key'),
                        x_auth_token: Optional[str] = header(default=None, alias='X-Auth-Token')):
        data, actor, indicator, identity = scope(project_id, indicator_id, x_api_key, x_auth_token, write=True)
        if set(payload) != {'definition', 'expected_workspace_version'}:
            fail(400, 'Supply a definition and expected_workspace_version only.')
        try:
            d = core.definition(payload['definition'], identity)
        except core.MethodologyError as exc:
            fail(400, str(exc))
        if find_scoped_dataset(data, actor.organization_id, d['source_dataset_id']) is None:
            fail(404, 'Calculation source is unavailable.')
        if d['unit'] != indicator.unit or (d['direction'] in {'up', 'down'} and d['direction'] != indicator.direction):
            fail(400, 'Methodology unit and direction must match the indicator.')
        h = deepcopy(history(indicator))
        try:
            changed = core.register(h['definitions'], d)
        except core.MethodologyError as exc:
            fail(409, str(exc))
        if not changed:
            return {'definition': d, 'workspace_version': data.workspace_version, 'created': False}
        version_check(data, payload)
        indicator.methodology = h
        audit(data, action='methodology.registered', target_type='indicator', target_id=indicator.id,
              actor=actor, details={'methodology_id': d['methodology_id'], 'version': d['version'], 'definition_hash': d['definition_hash']})
        save(data)
        return {'definition': d, 'workspace_version': data.workspace_version, 'created': True}

    @app.get(PREFIX + '/calculation')
    def get_calculation(project_id: str, indicator_id: str, start: str, end: str, as_of: str,
                        methodology_id: str = '', version: str = '', locale: str = 'EN',
                        x_api_key: Optional[str] = header(default=None, alias='X-API-Key'),
                        x_auth_token: Optional[str] = header(default=None, alias='X-Auth-Token')):
        data, actor, indicator, _ = scope(project_id, indicator_id, x_api_key, x_auth_token)
        return compute(data, actor, indicator, methodology_id, version, start, end, as_of, locale)

    @app.post(PREFIX + '/calculation-instances')
    def save_calculation(project_id: str, indicator_id: str, payload: Dict[str, Any],
                         x_api_key: Optional[str] = header(default=None, alias='X-API-Key'),
                         x_auth_token: Optional[str] = header(default=None, alias='X-Auth-Token')):
        data, actor, indicator, _ = scope(project_id, indicator_id, x_api_key, x_auth_token, write=True)
        if set(payload) != {'methodology_id', 'version', 'start', 'end', 'as_of', 'locale', 'expected_workspace_version'}:
            fail(400, 'An explicit method, reporting period, as_of, locale and workspace version are required.')
        envelope = compute(data, actor, indicator, *[payload[k] for k in ('methodology_id', 'version', 'start', 'end', 'as_of', 'locale')])
        if envelope['definition'] is None:
            fail(409, 'A methodology definition is required before saving an instance.')
        result = envelope['result']
        h = deepcopy(history(indicator))
        existing = next((x for x in h['instances'] if x['result']['calculation_id'] == result['calculation_id']), None)
        if existing:
            return {'result': deepcopy(existing['result']), 'saved_at': existing['saved_at'], 'historical': True, 'created': False}
        version_check(data, payload)
        record = {'result': result, 'saved_at': now()}
        h['instances'].append(record)
        indicator.methodology = h
        audit(data, action='calculation.saved', target_type='indicator', target_id=indicator.id, actor=actor,
              details={'calculation_id': result['calculation_id'], 'methodology_version': result['methodology_version']})
        save(data)
        return {**record, 'historical': True, 'created': True}

    @app.get(PREFIX + '/calculation-instances/{calculation_id}')
    def historical_calculation(project_id: str, indicator_id: str, calculation_id: str,
                               x_api_key: Optional[str] = header(default=None, alias='X-API-Key'),
                               x_auth_token: Optional[str] = header(default=None, alias='X-Auth-Token')):
        data, actor, indicator, _ = scope(project_id, indicator_id, x_api_key, x_auth_token)
        h = history(indicator)
        record = next((x for x in h['instances'] if x['result']['calculation_id'] == calculation_id), None)
        if record is None:
            fail(404, 'Calculation instance not found.')
        d = next(d for d in h['definitions'] if d['definition_hash'] == record['result']['definition_hash'])
        if find_scoped_dataset(data, actor.organization_id, d['source_dataset_id']) is None:
            fail(404, 'Calculation source is unavailable.')
        return {**deepcopy(record), 'definition': deepcopy(d), 'historical': True}
