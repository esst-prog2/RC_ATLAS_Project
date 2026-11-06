"""Versioned OC-A01/A02/A03 calculation contracts. Pure: no clock, I/O or eval.

Fractions preserve exact decimal-input arithmetic. Numeric display is deliberately
separate from the exact rational result. This is not a statistical/risk engine.
"""
from collections import Counter
from copy import deepcopy
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation, localcontext, ROUND_HALF_UP
from fractions import Fraction
import hashlib
import json
import re


ENGINE_VERSION = '1.0.0'
PROFILES = {
    'CHANGE_FROM_BASELINE': ('final_target_achievement', '(A-B)/(T-B) * 100 [up]; (B-A)/(B-T) * 100 [down]'),
    'TARGET_RATIO': ('final_target_achievement', 'A/T * 100 [up only]'),
    'TIME_PHASED': ('schedule_attainment', 'A/planned_target(as_of) * 100'),
    'MAINTENANCE_BAND': ('maintenance_state', 'lower <= A <= upper (inclusive)'),
    'MILESTONE': ('milestone_achievement', 'completed approved weight / applicable approved weight'),
    'NO_AUTOMATIC_PROGRESS': ('qualitative_review', 'No automatic numeric progress'),
}
STATES = {'VALID', 'MISSING', 'INVALID', 'NOT_APPLICABLE'}
FLAGS = {'PROVISIONAL', 'IMPUTED'}
ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z')
SEMVER = re.compile(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\Z')
FIELDS = {'value', 'period', 'state', 'flags', 'unit', 'currency', 'original_state'}
DEFINITION_FIELDS = {
    'methodology_id', 'version', 'status', 'profile', 'owner_decision',
    'effective_from', 'effective_to', 'intended_use', 'limitations', 'unit',
    'currency', 'direction', 'scale', 'domain', 'baseline', 'target',
    'reference_period', 'source_dataset_id', 'source_fields', 'aggregation',
    'aggregation_rationale', 'quality_rules', 'planned_targets', 'band',
}


class MethodologyError(ValueError):
    """Controlled messages only; never interpolate source values or internals."""


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def source_digest(value):
    # Invalid nonfinite input remains distinguishable in source identity, but is
    # never emitted as a JSON number or admitted to arithmetic. PostgreSQL also
    # rejects nonfinite canonical JSON at its persistence boundary.
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    ensure_ascii=False, allow_nan=True).encode()).hexdigest()


def iso_date(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise MethodologyError('A date must use YYYY-MM-DD.')
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise MethodologyError('A calendar date is invalid.') from None


def number(value):
    # No boolean, blank, null, NaN, infinity or implicit locale conversion.
    if isinstance(value, bool) or not isinstance(value, (int, float, str, Decimal)):
        return None
    if isinstance(value, str) and not re.fullmatch(r'-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?', value):
        return None
    try:
        decimal = Decimal(str(value))
        if not decimal.is_finite() or abs(decimal.adjusted()) > 100 or len(decimal.as_tuple().digits) > 120:
            return None
        return Fraction(decimal)
    except (InvalidOperation, ValueError, OverflowError):
        return None


def exact(value):
    if value is None:
        return None
    return {'numerator': str(value.numerator), 'denominator': str(value.denominator)}


def displayed(value):
    if value is None:
        return None
    with localcontext() as ctx:
        ctx.prec = 260
        return str((Decimal(value.numerator) / Decimal(value.denominator)).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP))


def context(start, end, as_of, locale='EN'):
    first, last = iso_date(start), iso_date(end)
    if first > last:
        raise MethodologyError('Reporting start must not follow reporting end.')
    try:
        stamp = datetime.fromisoformat(as_of.replace('Z', '+00:00'))
        if stamp.tzinfo is None or not isinstance(as_of, str) or 'T' not in as_of:
            raise ValueError()
        stamp = stamp.astimezone(timezone.utc)
    except (ValueError, AttributeError, TypeError):
        raise MethodologyError('as_of must be an explicit timezone-aware ISO timestamp.') from None
    if locale not in ('EN', 'PT', 'FR'):
        raise MethodologyError('Locale must be EN, PT or FR.')
    return {'reporting_period': {'start': start, 'end': end, 'boundaries': 'inclusive'},
            'as_of': stamp.isoformat().replace('+00:00', 'Z'), 'timezone': 'UTC', 'locale': locale}


def identifier(value):
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise MethodologyError('Identifiers and field references must be bounded simple identifiers.')
    return value


def _text(value, *, required=False):
    if not isinstance(value, str) or len(value) > 2000 or (required and not value.strip()):
        raise MethodologyError('A required methodology description is missing or too long.')
    return value


def _fields(value):
    if not isinstance(value, list) or len(value) > 50 or len(set(map(str, value))) != len(value):
        raise MethodologyError('Rule fields must be a bounded list of distinct identifiers.')
    return [identifier(x) for x in value]


def validate_quality(rules):
    if not isinstance(rules, dict) or set(rules) - {'required_fields', 'conformance', 'identity_fields', 'timeliness', 'traceability_fields'}:
        raise MethodologyError('Unsupported quality rule configuration.')
    for name in ('required_fields', 'identity_fields', 'traceability_fields'):
        if name in rules:
            _fields(rules[name])
    conformance = rules.get('conformance', {})
    if not isinstance(conformance, dict) or len(conformance) > 50:
        raise MethodologyError('Conformance rules must be a bounded object.')
    for field, rule in conformance.items():
        identifier(field)
        if not isinstance(rule, dict) or set(rule) - {'type', 'min', 'max'} or rule.get('type') not in ('number', 'text', 'date'):
            raise MethodologyError('Unsupported conformance rule.')
        for bound in ('min', 'max'):
            if bound in rule and (rule['type'] != 'number' or number(rule[bound]) is None):
                raise MethodologyError('Conformance bounds require finite numbers.')
        if 'min' in rule and 'max' in rule and number(rule['min']) > number(rule['max']):
            raise MethodologyError('Conformance minimum must not exceed maximum.')
    if 'timeliness' in rules:
        rule = rules['timeliness']
        if not isinstance(rule, dict) or set(rule) != {'field', 'max_age_days'}:
            raise MethodologyError('Timeliness requires a field and approved maximum age.')
        identifier(rule['field'])
        if type(rule['max_age_days']) is not int or rule['max_age_days'] < 0:
            raise MethodologyError('Maximum age must be a nonnegative integer.')


def definition(payload, scope):
    """Validate external configuration; generate invariant explanatory metadata."""
    if not isinstance(payload, dict) or set(payload) - DEFINITION_FIELDS:
        raise MethodologyError('Unsupported methodology fields.')
    d = deepcopy(payload)
    for name in ('methodology_id', 'source_dataset_id'):
        identifier(d.get(name))
    if not isinstance(d.get('version'), str) or not SEMVER.fullmatch(d['version']):
        raise MethodologyError('A semantic methodology version is required.')
    if d.get('status') not in ('APPROVED', 'UNCONFIGURED') or not isinstance(d.get('profile'), str) or d['profile'] not in PROFILES:
        raise MethodologyError('A recognized profile and explicit approval state are required.')
    if d['status'] == 'APPROVED':
        identifier(d.get('owner_decision'))
    else:
        d['owner_decision'] = ''
    start = iso_date(d.get('effective_from'))
    if d.get('effective_to') is not None and iso_date(d['effective_to']) <= start:
        raise MethodologyError('Effective end must follow effective start.')
    d.setdefault('effective_to', None)
    _text(d.get('intended_use'), required=True)
    _text(d.get('limitations'), required=True)
    for field in ('unit', 'currency'):
        _text(d.get(field, ''), required=field == 'unit')
    d.setdefault('currency', '')
    if d.get('direction') not in ('up', 'down', 'maintain', 'none') or d.get('scale') not in ('ratio', 'interval', 'ordinal'):
        raise MethodologyError('Explicit measurement scale and direction are required.')
    if d.get('aggregation') not in ('single', 'mean'):
        raise MethodologyError('Select single observation or an explicitly approved valid-value mean.')
    _text(d.get('aggregation_rationale', ''), required=d['aggregation'] == 'mean')
    d.setdefault('aggregation_rationale', '')
    domain = d.get('domain')
    if not isinstance(domain, dict) or set(domain) != {'min', 'max'}:
        raise MethodologyError('Explicit domain bounds are required; null means unbounded.')
    for bound in domain.values():
        if bound is not None and number(bound) is None:
            raise MethodologyError('Domain bounds must be finite numbers or null.')
    if domain['min'] is not None and domain['max'] is not None and number(domain['min']) > number(domain['max']):
        raise MethodologyError('Domain minimum must not exceed maximum.')
    for field in ('baseline', 'target'):
        d.setdefault(field, None)
        if d[field] is not None and number(d[field]) is None:
            raise MethodologyError('Baseline and target must be finite numbers or null.')
    reference = d.get('reference_period')
    if not isinstance(reference, dict) or set(reference) != {'start', 'end'} or iso_date(reference['start']) > iso_date(reference['end']):
        raise MethodologyError('An ordered reference period is required.')
    fields = d.get('source_fields')
    if not isinstance(fields, dict) or not {'value', 'period'} <= set(fields) or set(fields) - FIELDS:
        raise MethodologyError('An explicit value/period source mapping is required.')
    for value in fields.values():
        identifier(value)
    rules = d.setdefault('quality_rules', {})
    validate_quality(rules)
    schedule = d.setdefault('planned_targets', {})
    if not isinstance(schedule, dict) or len(schedule) > 366:
        raise MethodologyError('Planned targets must be a bounded exact-date schedule.')
    for point, value in schedule.items():
        iso_date(point)
        if number(value) is None:
            raise MethodologyError('Planned targets must be finite numbers.')
    band = d.setdefault('band', None)
    if band is not None:
        if not isinstance(band, dict) or set(band) != {'lower', 'upper'} or any(number(x) is None for x in band.values()):
            raise MethodologyError('A maintenance band requires finite lower and upper limits.')
        if number(band['lower']) > number(band['upper']):
            raise MethodologyError('Maintenance lower limit must not exceed upper limit.')
    kind, formula = PROFILES[d['profile']]
    numerator_meaning, denominator_meaning, target_meaning = {
        'CHANGE_FROM_BASELINE': ('A-B (up) or B-A (down)', 'T-B (up) or B-T (down)', 'approved final target'),
        'TARGET_RATIO': ('A', 'T', 'approved final ratio-scale target'),
        'TIME_PHASED': ('A', 'planned_target(as_of)', 'approved planned target at the explicit reference date'),
        'MAINTENANCE_BAND': (None, None, 'approved inclusive lower and upper bounds'),
        'MILESTONE': ('completed approved milestone weight', 'applicable approved milestone weight', 'approved milestone set; evidence and weights not implemented in Package 1'),
        'NO_AUTOMATIC_PROGRESS': (None, None, 'no automatic numeric target semantics'),
    }[d['profile']]
    d.update(scope=deepcopy(scope), engine_version=ENGINE_VERSION, metric_kind=kind,
             formula=formula, methodology_decisions=['OC-A01', 'OC-A02', 'OC-A03', 'OC-A04', 'OC-A05', 'QA-003'],
             aggregation_eligibility='within this definition only; portfolio NOT_ASSESSED',
             actual_semantics='eligible observations in explicit reporting period',
             target_semantics=target_meaning,
             numerator_definition=numerator_meaning,
             denominator_definition=denominator_meaning,
             data_state_policy='N/A excluded from applicability; missing/invalid never zero; flagged values excluded',
             rounding='exact rational arithmetic; display 2 decimals ROUND_HALF_UP; no classification bands',
             revision_policy='immutable approved definition; explicit saved calculation snapshots',
             fixture_version='OC-A01-A03-V1', uncertainty='NOT_ASSESSED',
             reference_principle='Approved RC Atlas methodology register; no external certification claim')
    d['definition_hash'] = digest(d)
    return d


def verified_definition(d, scope):
    try:
        return definition({k: v for k, v in d.items() if k in DEFINITION_FIELDS}, scope) == d
    except (MethodologyError, ValueError, TypeError, AttributeError, KeyError):
        return False


def register(existing, candidate):
    """No in-place version edits, silent replacement or overlapping effective versions."""
    for old in existing:
        if (old['methodology_id'], old['version']) == (candidate['methodology_id'], candidate['version']):
            if old == candidate:
                return False
            raise MethodologyError('A methodology version is immutable; register a new version.')
        if old['status'] == candidate['status'] == 'APPROVED' and old['metric_kind'] == candidate['metric_kind']:
            if max(old['effective_from'], candidate['effective_from']) < min(old.get('effective_to') or '9999-12-31', candidate.get('effective_to') or '9999-12-31'):
                raise MethodologyError('Approved effective periods for this metric kind must not overlap.')
    existing.append(deepcopy(candidate))
    return True


def cell(value):
    if isinstance(value, dict):
        state = value.get('state')
        if not isinstance(state, str) or state not in STATES or set(value) - {'value', 'state'}:
            return None, 'INVALID'
        raw = value.get('value')
        if state == 'VALID' and (raw is None or raw == ''):
            return None, 'MISSING'
        return raw, state
    return value, 'MISSING' if value is None or value == '' else 'VALID'


def observation(row, d):
    fields = d['source_fields']
    value, state = cell(row.get(fields['value']))
    if 'state' in fields:
        state = row.get(fields['state'])
    if not isinstance(state, str) or state not in STATES:
        state = 'INVALID'
    numeric = number(value)
    if state == 'VALID':
        if value is None or value == '':
            state = 'MISSING'
        elif numeric is None:
            state = 'INVALID'
    flags = row.get(fields['flags'], []) if 'flags' in fields else []
    if not isinstance(flags, list) or any(not isinstance(x, str) or x not in FLAGS for x in flags) or len(flags) != len(set(flags)):
        return {'state': 'INVALID', 'value': None, 'flags': [], 'reason': 'INVALID_FLAGS'}
    flags = sorted(flags)
    original = row.get(fields.get('original_state'))
    if 'IMPUTED' in flags and (not isinstance(original, str) or original not in STATES):
        return {'state': 'INVALID', 'value': None, 'flags': flags, 'reason': 'IMPUTATION_ORIGINAL_STATE_REQUIRED'}
    reason = state if state != 'VALID' else None
    if state == 'VALID':
        if 'unit' in fields and row.get(fields['unit']) != d['unit']:
            reason = 'INCOMPATIBLE_UNIT'
        elif 'currency' in fields and row.get(fields['currency']) != d['currency']:
            reason = 'INCOMPATIBLE_CURRENCY'
        elif not in_domain(numeric, d):
            reason = 'OUTSIDE_DOMAIN'
            state = 'INVALID'
        elif flags:
            reason = 'FLAG_POLICY_NOT_APPROVED'
    return {'state': state, 'value': numeric, 'flags': flags, 'original_state': original if 'IMPUTED' in flags else None, 'reason': reason}


def in_domain(value, d):
    domain = d['domain']
    return value is not None and (domain['min'] is None or value >= number(domain['min'])) and (
        domain['max'] is None or value <= number(domain['max']))


def _key(row, fields):
    parts = []
    for field in fields:
        value, state = cell(row.get(field))
        if state != 'VALID' or isinstance(value, (list, dict, bool)) or not isinstance(value, (str, int, float)):
            return None
        if isinstance(value, (int, float)) and number(value) is None:
            return None
        parts.append(value)
    return digest(parts)


def _dimension(rule, numerator=None, denominator=None, exclusions=None, population=0):
    assessed = denominator is not None and denominator > 0
    ratio = Fraction(numerator, denominator) if assessed else None
    return {'state': 'ASSESSED' if assessed else 'NOT_ASSESSED', 'rule': rule,
            'population': population, 'numerator': numerator, 'denominator': denominator,
            'exact_ratio': exact(ratio), 'display_percent': displayed(ratio * 100) if assessed else None,
            'exclusions': dict(sorted((exclusions or {}).items())),
            'limitation': '' if assessed else ('NO_ASSESSABLE_POPULATION' if denominator == 0 else 'RULE_NOT_CONFIGURED')}


def quality_profile(rows, rules, as_of, intended_use):
    """Declared-use mechanical dimensions only; no composite or fitness inference."""
    validate_quality(rules)
    out = {}
    required = rules.get('required_fields', [])
    n = den = 0
    excludes = Counter()
    for row in rows:
        for field in required:
            value, state = cell(row.get(field))
            if state == 'NOT_APPLICABLE':
                excludes['NOT_APPLICABLE'] += 1
                continue
            den += 1
            n += state == 'VALID'
    out['completeness'] = _dimension({'required_fields': required}, n if required else None, den if required else None, excludes, len(rows))
    tests = rules.get('conformance', {})
    n = den = 0
    excludes = Counter()
    for row in rows:
        for field, rule in tests.items():
            value, state = cell(row.get(field))
            if state in {'MISSING', 'NOT_APPLICABLE'}:
                excludes[state] += 1
                continue
            den += 1
            valid = state == 'VALID'
            if rule['type'] == 'number':
                v = number(value)
                valid = valid and v is not None
                if valid:
                    valid = ('min' not in rule or v >= number(rule['min'])) and ('max' not in rule or v <= number(rule['max']))
            elif rule['type'] == 'text':
                valid = valid and isinstance(value, str)
            else:
                try:
                    iso_date(value)
                except MethodologyError:
                    valid = False
            n += valid
    out['conformance'] = _dimension(tests, n if tests else None, den if tests else None, excludes, len(rows))
    fields = rules.get('identity_fields', [])
    keys = [_key(row, fields) for row in rows] if fields else []
    assessable = [k for k in keys if k is not None]
    out['uniqueness'] = _dimension({'identity_fields': fields, 'meaning': 'distinct assessable keys / assessable records'},
                                  len(set(assessable)) if fields else None, len(assessable) if fields else None,
                                  {'UNASSESSABLE_KEY': len(keys) - len(assessable)}, len(rows))
    rule = rules.get('timeliness')
    n = den = 0
    excludes = Counter()
    if rule:
        for row in rows:
            value, state = cell(row.get(rule['field']))
            try:
                if state != 'VALID':
                    raise MethodologyError('Unassessable date.')
                day = iso_date(value)
            except MethodologyError:
                excludes['UNASSESSABLE_DATE'] += 1
                continue
            den += 1
            n += 0 <= (iso_date(as_of[:10]) - day).days <= rule['max_age_days']
    out['timeliness'] = _dimension(rule, n if rule else None, den if rule else None, excludes, len(rows))
    fields = rules.get('traceability_fields', [])
    n = sum(all(cell(row.get(f))[1] == 'VALID' for f in fields) for row in rows) if fields else None
    out['traceability'] = _dimension({'required_provenance_fields': fields}, n, len(rows) if fields else None, {}, len(rows))
    return {'methodology_version': ENGINE_VERSION, 'intended_use': intended_use,
            'population': len(rows), 'scope': 'records within reporting period and as_of; see calculation period exclusions',
            'dimensions': out, 'fitness': 'FITNESS_NOT_CONFIGURED',
            'methodological_validity': 'NOT_ASSESSED', 'statistical_precision': 'NOT_ASSESSED'}


def _calculate_value(d, actual, ctx):
    p = d['profile']
    if p == 'NO_AUTOMATIC_PROGRESS':
        return 'NOT_ASSESSED', None, None, None, None, 'QUALITATIVE_REVIEW_REQUIRED'
    if p == 'MILESTONE':
        return 'NOT_ASSESSED', None, None, None, None, 'MILESTONE_EVIDENCE_CONTRACT_NOT_IMPLEMENTED'
    if p == 'MAINTENANCE_BAND':
        if d['direction'] != 'maintain' or not d['band']:
            return 'UNCONFIGURED', None, None, None, None, 'MAINTENANCE_BAND_REQUIRED'
        low, high = number(d['band']['lower']), number(d['band']['upper'])
        band_state = 'BELOW_BAND' if actual < low else 'ABOVE_BAND' if actual > high else 'IN_BAND'
        return 'VALID', None, None, None, band_state, None
    if d['direction'] not in {'up', 'down'} or d['scale'] == 'ordinal':
        return 'UNCONFIGURED', None, None, None, None, 'UNSUPPORTED_SCALE_OR_DIRECTION'
    baseline, target = number(d['baseline']), number(d['target'])
    if p in {'TARGET_RATIO', 'TIME_PHASED'}:
        if d['scale'] != 'ratio' or d['direction'] != 'up':
            return 'UNCONFIGURED', None, None, None, None, 'RATIO_SEMANTICS_NOT_APPROVED'
        if p == 'TIME_PHASED':
            target = number(d['planned_targets'].get(ctx['as_of'][:10]))
        if target is None:
            return 'UNCONFIGURED', None, None, None, None, 'EXPLICIT_TARGET_REQUIRED'
        if target == 0:
            return 'INVALID', None, actual, target, None, 'ZERO_DENOMINATOR'
        if target < 0 or actual < 0 or not in_domain(target, d):
            return 'INVALID', None, actual, target, None, 'UNAPPROVED_RATIO_DOMAIN'
        numerator, denominator = actual, target
    else:
        if baseline is None or target is None:
            return 'UNCONFIGURED', None, None, None, None, 'BASELINE_AND_TARGET_REQUIRED'
        numerator = actual - baseline if d['direction'] == 'up' else baseline - actual
        denominator = target - baseline if d['direction'] == 'up' else baseline - target
        if denominator == 0:
            return 'INVALID', None, numerator, denominator, None, 'ZERO_DENOMINATOR'
        if denominator < 0 or not in_domain(baseline, d) or not in_domain(target, d):
            return 'INVALID', None, numerator, denominator, None, 'TARGET_DIRECTION_OR_DOMAIN_CONFLICT'
    return 'VALID', numerator / denominator * 100, numerator, denominator, None, None


def calculate(d, rows, ctx):
    """One instance, including deterministic quality and explanation intermediates."""
    if not verified_definition(d, d.get('scope')):
        raise MethodologyError('Methodology definition is unavailable or invalid.')
    # Reject malformed contexts even when called without an API boundary.
    if context(ctx['reporting_period']['start'], ctx['reporting_period']['end'], ctx['as_of'], ctx['locale']) != ctx:
        raise MethodologyError('Calculation context is invalid.')
    start, end = ctx['reporting_period']['start'], ctx['reporting_period']['end']
    cutoff = ctx['as_of'][:10]
    period_exclusions = Counter()
    selected = []
    for row in rows:
        try:
            if not isinstance(row, dict):
                raise MethodologyError('Invalid row.')
            day = iso_date(row.get(d['source_fields']['period'])).isoformat()
        except MethodologyError:
            period_exclusions['INVALID_OR_MISSING_PERIOD'] += 1
            continue
        if not start <= day <= end:
            period_exclusions['OUTSIDE_REPORTING_PERIOD'] += 1
        elif day > cutoff:
            period_exclusions['AFTER_AS_OF'] += 1
        else:
            selected.append(row)
    selected.sort(key=source_digest)
    identity_fields = d['quality_rules'].get('identity_fields', [])
    identities = Counter(_key(r, identity_fields) for r in selected) if identity_fields else Counter()
    state_counts, flag_counts, excluded = Counter(), Counter(), Counter()
    inputs, values, quality_rows = [], [], []
    for row in selected:
        obs = observation(row, d)
        typed_row = dict(row)
        typed_row[d['source_fields']['value']] = {
            'value': cell(row.get(d['source_fields']['value']))[0], 'state': obs['state'],
        }
        quality_rows.append(typed_row)
        state_counts[obs['state']] += 1
        flag_counts.update(obs['flags'])
        reason = obs['reason']
        if not reason and identity_fields:
            key = _key(row, identity_fields)
            if key is None:
                reason = 'UNASSESSABLE_IDENTITY'
            elif identities[key] > 1:
                reason = 'DUPLICATE_IDENTITY'
        if reason:
            excluded[reason] += 1
        else:
            values.append(obs['value'])
        inputs.append({'source_row_revision': source_digest(row), 'value': exact(obs['value']), 'state': obs['state'],
                       'flags': obs['flags'], 'original_state': obs.get('original_state'), 'exclusion': reason})
    actual = sum(values, Fraction()) / len(values) if values else None
    status, raw, numerator, denominator, band_state, warning = 'MISSING', None, None, None, None, 'NO_ELIGIBLE_OBSERVATIONS'
    if not selected and cutoff < start:
        status, warning = 'NOT_YET_DUE', 'REPORTING_PERIOD_NOT_YET_DUE'
    elif selected and state_counts['NOT_APPLICABLE'] == len(selected):
        status, warning = 'NOT_APPLICABLE', 'NO_APPLICABLE_OBSERVATIONS'
    elif not values and any(k not in {'MISSING', 'NOT_APPLICABLE'} for k in excluded):
        status, warning = 'INVALID', 'NO_VALID_ELIGIBLE_OBSERVATIONS'
    effective = d['status'] == 'APPROVED' and d['effective_from'] <= cutoff < (d['effective_to'] or '9999-12-31')
    if d['status'] != 'APPROVED':
        status, warning = 'UNCONFIGURED', 'OWNER_APPROVAL_REQUIRED'
    elif not d['effective_from'] <= cutoff < (d['effective_to'] or '9999-12-31'):
        status, warning = 'NOT_ASSESSED', 'METHOD_NOT_EFFECTIVE_AT_AS_OF'
    elif d['aggregation'] == 'single' and len(values) > 1:
        status, warning, actual = 'BLOCKED', 'MULTIPLE_OBSERVATIONS_REQUIRE_APPROVED_AGGREGATION', None
    elif actual is not None:
        status, raw, numerator, denominator, band_state, warning = _calculate_value(d, actual, ctx)
    result = {
        'schema_version': 1, 'methodology_id': d['methodology_id'], 'methodology_version': d['version'],
        'definition_hash': d['definition_hash'], 'engine_version': ENGINE_VERSION,
        'scope': deepcopy(d['scope']), 'metric_kind': d['metric_kind'], 'profile': d['profile'],
        'context': deepcopy(ctx), 'reference_period': d['reference_period'],
        'filters': {'period': ctx['reporting_period'], 'observation_date_lte': cutoff, 'aggregation': d['aggregation']},
        'source': {'dataset_id': d['source_dataset_id'], 'revision': source_digest(sorted(rows, key=source_digest)), 'rows': len(rows)},
        'state': status, 'exact_value': exact(raw), 'display_value': displayed(raw),
        'unit': '%' if d['profile'] in {'CHANGE_FROM_BASELINE', 'TARGET_RATIO', 'TIME_PHASED'} else d['unit'],
        'band_state': band_state, 'formula': d['formula'],
        'inputs': inputs, 'actual': exact(actual), 'baseline': exact(number(d['baseline'])),
        'target': exact(number(d['target'])), 'planned_target': exact(number(d['planned_targets'].get(cutoff))),
        'numerator': exact(numerator), 'denominator': exact(denominator),
        'coverage': {'source_total': len(rows), 'in_period': len(selected),
                     'applicable': len(selected) - state_counts['NOT_APPLICABLE'], 'included': len(values),
                     'excluded': len(selected) - len(values), 'period_excluded': sum(period_exclusions.values()),
                     'states': {s: state_counts[s] for s in sorted(STATES)},
                     'flags': {s: flag_counts[s] for s in sorted(FLAGS)}},
        'exclusions': dict(sorted(excluded.items())), 'period_exclusions': dict(sorted(period_exclusions.items())),
        'quality': quality_profile(quality_rows, d['quality_rules'] if effective else {}, ctx['as_of'], d['intended_use']),
        'warnings': ([warning] if warning else []) + (['PARTIAL_COVERAGE'] if excluded else []),
        'limitations': [d['limitations'], 'as_of is an observation cutoff; source revision is the data available at calculation.',
                        'No portfolio aggregation, statistical trend, causal inference or fitness classification.',
                        'Final-target achievement and schedule attainment have different meanings.'],
        'rounding': d['rounding'], 'statistical_trend': 'NOT_ASSESSED', 'portfolio_aggregation': 'NOT_ASSESSED',
    }
    result['calculation_id'] = digest(result)
    result['cache_identity'] = result['calculation_id']
    return result


def validate_history(extension, scope):
    """Validate the nested persistence schema; no silently ignored extension data."""
    if extension == {}:
        return
    if not isinstance(extension, dict) or set(extension) != {'schema_version', 'definitions', 'instances'} or type(extension['schema_version']) is not int or extension['schema_version'] != 1:
        raise MethodologyError('Methodology persistence schema is invalid.')
    definitions, instances = extension['definitions'], extension['instances']
    if not isinstance(definitions, list) or not isinstance(instances, list):
        raise MethodologyError('Methodology history collections are invalid.')
    seen = []
    for d in definitions:
        if not verified_definition(d, scope) or not register(seen, d):
            raise MethodologyError('Methodology history contains an invalid or duplicate definition.')
    ids = set()
    for record in instances:
        if not isinstance(record, dict) or set(record) != {'result', 'saved_at'}:
            raise MethodologyError('Calculation history is invalid.')
        r = record['result']
        if not isinstance(r, dict):
            raise MethodologyError('Calculation history is invalid.')
        identity = r.get('calculation_id')
        content = {k: v for k, v in r.items() if k not in {'calculation_id', 'cache_identity'}}
        if identity != digest(content) or r.get('cache_identity') != identity or identity in ids or r.get('scope') != scope:
            raise MethodologyError('Calculation history integrity is invalid.')
        if not any(d['definition_hash'] == r.get('definition_hash') for d in definitions):
            raise MethodologyError('Calculation history methodology is missing.')
        ids.add(identity)


def validate_transition(before, after):
    """Prevent unrelated aggregate writers from dropping or changing approved history."""
    def histories(payload):
        return {(p.get('organization_id'), p['id'], i['id']): i.get('methodology', {})
                for p in payload.get('projects', []) for i in p.get('indicators', []) if i.get('methodology')}
    old, new = histories(before), histories(after)
    for key, history in old.items():
        candidate = new.get(key, {})
        for collection in ('definitions', 'instances'):
            if any(item not in candidate.get(collection, []) for item in history.get(collection, [])):
                raise MethodologyError('Approved methodology and calculation history are immutable.')
