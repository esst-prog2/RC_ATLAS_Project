"""Fictional, independently specified OC-A01/A02/A03 acceptance fixtures only."""
from copy import deepcopy

SCOPE = {'organization_id': 'org_method_a', 'project_id': 'project_method', 'indicator_id': 'indicator_method'}
AS_OF = '2026-09-30T23:59:59Z'
PASSWORD = 'Synthetic-Methodology-Only-2026!'


def definition_payload(**overrides):
    base = {
        'methodology_id': 'change-achievement', 'version': '1.0.0', 'status': 'APPROVED',
        'profile': 'CHANGE_FROM_BASELINE', 'owner_decision': 'SYNTHETIC-OC-A02',
        'effective_from': '2026-01-01', 'effective_to': '2027-01-01',
        'intended_use': 'Fictional fixture: final-target change achievement.',
        'limitations': 'Synthetic test only. No schedule or statistical inference.',
        'unit': 'people', 'currency': '', 'direction': 'up', 'scale': 'ratio',
        'domain': {'min': 0, 'max': None}, 'baseline': 20, 'target': 100,
        'reference_period': {'start': '2026-01-01', 'end': '2026-12-31'},
        'source_dataset_id': 'dataset_method', 'source_fields': {'value': 'actual', 'period': 'period'},
        'aggregation': 'single', 'quality_rules': {},
    }
    base.update(deepcopy(overrides))
    return base


def rows(actual=60):
    return [{'actual': actual, 'period': '2026-09-30'}]


def seed(module):
    """Use only with a caller-verified fresh disposable runtime."""
    data = module.LogiTrackData()
    for suffix in ('a', 'b'):
        org = 'org_method_' + suffix
        data.organizations.append(module.OrganizationAccount(id=org, organization_name='Synthetic ' + suffix))
        for role in ('organization_admin', 'executive_viewer'):
            username = 'method.' + suffix + '.' + role
            user = module.UserAccount(id='user_' + suffix + '_' + role, organization_id=org,
                                      username=username, full_name='Synthetic ' + role, role=role, status='active')
            user.password_salt, user.password_hash = module.build_password_hash(PASSWORD)
            data.users.append(user)
            module.register_session_for_token(data, user, 'token-' + username)
    indicator = module.Indicator(id=SCOPE['indicator_id'], name='Synthetic change achievement', unit='people',
                                 frequency='monthly', direction='up', level='outcome', target=100, baseline=20,
                                 organization_id=SCOPE['organization_id'], project_id=SCOPE['project_id'])
    data.projects.append(module.Project(id=SCOPE['project_id'], name='Synthetic Methodology Project',
                                       objective='OC-A02 independent fixture', organization_id=SCOPE['organization_id'],
                                       project_code='METHOD-001', indicators=[indicator]))
    data.tidy_datasets.append(module.TidyDataset(id='dataset_method', name='Synthetic methodology observations',
                                                organization_id=SCOPE['organization_id'], rows=rows()))
    data.tidy_datasets.append(module.TidyDataset(id='dataset_foreign', name='Foreign synthetic source',
                                                organization_id='org_method_b', rows=[{'secret': 'FOREIGN_SENTINEL'}]))
    module.save_data_to_path(data)
    return data
