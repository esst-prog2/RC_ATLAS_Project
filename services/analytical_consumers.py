"""Read adapters for the Package 1 engine; no formulas or canonical storage here.

Legacy location/history records have no approved population binding. They remain
source records and cannot be substituted for a definition's bound TidyDataset.
"""
from copy import deepcopy

from services import methodology as core
from services.errors import ServiceError
from services.tenant_security import find_scoped_project, find_scoped_dataset


CONTRACT = 'analytical-consumers/1.0.0'
AGGREGATION_LIMIT = 'APPROVED_COMPARABLE_GROUP_AND_ESTIMAND_REQUIRED'
LEGACY_LIMIT = 'LEGACY_OBSERVATIONS_REQUIRE_APPROVED_SOURCE_BINDING'


def selection(start=None, end=None, as_of=None, methodology_id='', version='', locale='EN'):
    """Absence is explicit, partial context is an error, never use the wall clock."""
    supplied = any(value not in (None, '') for value in (start, end, as_of, methodology_id, version))
    if not supplied:
        return None
    try:
        ctx = core.context(start, end, as_of, locale)
    except (core.MethodologyError, TypeError) as exc:
        raise ServiceError(400, 'An explicit valid reporting period, as_of and locale are required.') from exc
    if bool(methodology_id) != bool(version):
        raise ServiceError(400, 'Select both methodology_id and version.')
    return {'context': ctx, 'methodology_id': methodology_id, 'version': version}


def unavailable(reason, *, state='NOT_ASSESSED', ctx=None, scope=None):
    return {'definition': None, 'historical': False, 'result': {
        'state': state, 'display_value': None, 'exact_value': None,
        'methodology_version': None, 'formula': None, 'context': deepcopy(ctx),
        'scope': deepcopy(scope), 'warnings': [reason],
        'limitations': ['No method, population, target, weight or status threshold is inferred from legacy values.'],
    }}


def calculate_indicator(data, organization_id, project_id, indicator_id, selected):
    """Shared by the canonical endpoint and each migrated consumer."""
    project = find_scoped_project(data, organization_id, project_id)
    indicator = next((i for i in project.indicators if i.id == indicator_id), None) if project else None
    if (indicator is None or not organization_id or indicator.organization_id != organization_id
            or indicator.project_id != project_id):
        raise ServiceError(404, 'Indicator methodology resource not found.')
    identity = {'organization_id': organization_id, 'project_id': project_id, 'indicator_id': indicator_id}
    try:
        core.validate_history(indicator.methodology, identity)
    except core.MethodologyError as exc:
        raise ServiceError(409, 'Methodology history is unavailable or invalid.') from exc
    if selected is None:
        return unavailable('EXPLICIT_CALCULATION_CONTEXT_REQUIRED', state='UNCONFIGURED', scope=identity)
    ctx = selected['context']
    method_id, version = selected['methodology_id'], selected['version']
    definitions = (indicator.methodology or {}).get('definitions', [])
    d = next((d for d in definitions if d['methodology_id'] == method_id and d['version'] == version), None)
    if d is None:
        if method_id or version:
            raise ServiceError(404, 'Methodology version not found.')
        return unavailable('APPROVED_INDICATOR_DEFINITION_REQUIRED', state='UNCONFIGURED', ctx=ctx, scope=identity)
    dataset = find_scoped_dataset(data, organization_id, d['source_dataset_id'])
    if dataset is None:
        raise ServiceError(404, 'Calculation source is unavailable.')
    try:
        result = core.calculate(d, dataset.rows, ctx)
    except core.MethodologyError as exc:
        raise ServiceError(409, 'Methodology calculation is unavailable or invalid.') from exc
    return {'definition': deepcopy(d), 'result': result, 'historical': False}


def indicator_kpi(data, project, indicator, selected=None):
    if not project.organization_id or indicator.organization_id != project.organization_id or indicator.project_id != project.id:
        calculation = unavailable('UNRESOLVED_OWNERSHIP', state='BLOCKED')
    else:
        calculation = calculate_indicator(data, project.organization_id, project.id, indicator.id, selected)
    result = calculation['result']
    return {
        'project_id': project.id, 'indicator_id': indicator.id, 'indicator_name': indicator.name,
        'level': indicator.level, 'direction': indicator.direction,
        # These old keys described district means/weights, not the selected metric.
        'progress_mean_pct': None, 'progress_weighted_pct': None,
        'status_mean_canon': 'NOT_ASSESSED', 'status_weighted_canon': 'NOT_ASSESSED',
        'district_valid_count': 0, 'district_missing_count': sum(loc.actual_local is None for loc in indicator.locations),
        'district_unassessed_count': len(indicator.locations), 'budget_total': None,
        'analytical_contract': CONTRACT, 'calculation_state': result['state'],
        'calculated_value': result['display_value'], 'calculation': calculation,
        'aggregation_state': 'NOT_ASSESSED', 'aggregation_limitation': AGGREGATION_LIMIT,
    }


def quality_report(data, dataset, selected=None, *, project_id='', indicator_id=''):
    """Quality of the exact indicator population, or an honest unassessed profile."""
    envelope = None
    if selected is not None:
        if not project_id or not indicator_id:
            raise ServiceError(400, 'Select the project and indicator whose approved quality rules apply.')
        envelope = calculate_indicator(data, dataset.organization_id, project_id, indicator_id, selected)
        d = envelope['definition']
        if d is not None and d['source_dataset_id'] != dataset.id:
            raise ServiceError(404, 'Calculation source is unavailable.')
    if envelope is not None and envelope['result'].get('quality') is not None:
        profile = deepcopy(envelope['result']['quality'])
        state = 'ASSESSED' if any(d['state'] == 'ASSESSED' for d in profile['dimensions'].values()) else 'NOT_ASSESSED'
        limitations = envelope['result']['limitations']
        warnings = envelope['result']['warnings']
    else:
        profile = core.quality_profile(dataset.rows, {}, None, 'NOT_CONFIGURED')
        profile['scope'] = 'Unfiltered dataset inventory only; no approved assessment scope selected.'
        state = 'NOT_ASSESSED'
        limitations = ['Select an approved indicator definition and explicit period/as_of; no dataset-wide rules are inferred.']
        warnings = ['QUALITY_RULES_AND_SCOPE_REQUIRED']
    return {
        'dataset_id': dataset.id, 'row_count': len(dataset.rows),
        'column_count': len({key for row in dataset.rows if isinstance(row, dict) for key in row}),
        'analytical_contract': CONTRACT, 'state': state, 'profile': profile,
        'overall_score': None, 'overall_state': 'UNSUPPORTED',
        'scores': {key: None for key in ('completeness', 'duplicates', 'freshness', 'validity')},
        'data_freshness_days': None, 'duplicate_rows': None, 'invalid_time_rows': None,
        'empty_columns': [], 'measure_outliers': [], 'column_completeness': [],
        'mapping': {'status': 'NOT_ASSESSED', 'confidence': None, 'fields': {}},
        'issues': [], 'warnings': deepcopy(warnings), 'limitations': deepcopy(limitations),
        'calculation': envelope,
        'coverage': deepcopy(envelope['result'].get('coverage')) if envelope else None,
        'exclusions': deepcopy(envelope['result'].get('exclusions')) if envelope else None,
        'period_exclusions': deepcopy(envelope['result'].get('period_exclusions')) if envelope else None,
    }


def guard_aggregate(row, reason=AGGREGATION_LIMIT):
    """Keep response keys while refusing an unsupported cross-indicator estimand."""
    row.update(progress_mean_pct=None, progress_weighted_pct=None,
               status_mean_canon='NOT_ASSESSED', status_weighted_canon='NOT_ASSESSED',
               analytical_contract=CONTRACT, calculation_state='NOT_ASSESSED',
               limitations=[reason])
    return row
