"""Versioned permission representation; v0 keeps the legacy interpretation.

The existing relational permissions_json column stores v0 lists unchanged and
a tagged v1 envelope for new semantics. No database schema migration is needed.
"""
import json


def policy_version(value=0):
    if type(value) is not int or value not in (0, 1):
        raise ValueError('Unsupported permission policy version.')
    return value


def validate_grant_shape(grants):
    if grants is not None and (not isinstance(grants, list) or any(
            not isinstance(item, str) or not item.strip() for item in grants)):
        raise ValueError('Permissions must be null for inheritance or a list of known permission IDs.')
    return grants


def encode_permission_policy(user):
    version = policy_version(user.get('permission_policy_version', 0))
    if version == 0:
        return json.dumps(user.get('permissions', []) or [], ensure_ascii=False)
    if 'permissions' not in user:
        raise ValueError('Versioned permission records require an explicit permissions field.')
    return json.dumps({'permission_policy_version': 1,
                       'permissions': validate_grant_shape(user['permissions'])}, ensure_ascii=False)


def decode_permission_policy(raw):
    # Corrupt JSON cannot safely be interpreted as legacy inheritance.
    try:
        value = json.loads(str(raw or '[]'))
    except (TypeError, ValueError) as exc:
        raise ValueError('Stored permission policy is invalid.') from exc
    if isinstance(value, dict) and 'permission_policy_version' in value:
        if set(value) != {'permission_policy_version', 'permissions'} or policy_version(value['permission_policy_version']) != 1:
            raise ValueError('Stored permission policy is invalid.')
        return {'permission_policy_version': 1, 'permissions': validate_grant_shape(value['permissions'])}
    return {'permission_policy_version': 0, 'permissions': value if isinstance(value, list) else []}
