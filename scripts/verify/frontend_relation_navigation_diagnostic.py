"""Read-only diagnosis of exact readonly relation navigation authority.

Runs inside the registered acceptance backend against the fixed acceptance
database. It never writes: the transaction is read-only and rolled back.
It reports the exact denial stage for one declared relation navigation.
"""
import json

from odoo import api

assert env.cr.dbname == 'sc_frontend_acceptance', env.cr.dbname
env.cr.rollback()
env.cr.execute('SET TRANSACTION READ ONLY')

from odoo.addons.smart_core.handlers.route_authority_validate import RouteAuthorityValidateHandler
from odoo.addons.smart_core.core.relation_action_authority import (
    positive_relation_id, validate_relation_action_origin,
)

MODEL = 'res.partner'
RECORD_ID = 56
ACTION_ID = 324
MENU_ID = 164
ORIGIN = {'model': 'payment.request', 'record_id': 1813, 'field': 'partner_id',
          'action_id': 775, 'menu_id': 545}
LOGIN = 'fixture_role_finance'


def _attempt(function, *arguments):
    try:
        function(*arguments)
        return True
    except Exception as error:  # noqa: BLE001 - diagnostic reports, never masks
        return f'{type(error).__name__}: {error}'


def _find_field(value, field_name):
    if isinstance(value, dict):
        if str(value.get('type') or '').strip().lower() == 'field' and value.get('name') == field_name:
            return value
        for nested in value.values():
            found = _find_field(nested, field_name)
            if found:
                return found
    elif isinstance(value, list):
        for nested in value:
            found = _find_field(nested, field_name)
            if found:
                return found
    return None


user = env['res.users'].search([('login', '=', LOGIN)], limit=1)
assert user, LOGIN
actor = api.Environment(env.cr, user.id, dict(env.context, allowed_company_ids=[user.company_id.id]))

params = {
    'model': MODEL, 'record_id': RECORD_ID, 'action_id': ACTION_ID, 'menu_id': MENU_ID,
    'route_path': f'/r/{MODEL}/{RECORD_ID}', 'access_mode': 'read', 'render_profile': 'readonly',
    'relation_origin': ORIGIN, 'company_id': user.company_id.id,
}

handler = RouteAuthorityValidateHandler(actor, payload={'params': params})
result = handler.handle()
envelope = result.to_legacy_dict() if hasattr(result, 'to_legacy_dict') else result
print('RELATION_NAV_RESPONSE', json.dumps(envelope, ensure_ascii=False, default=str))

stages = {'parent_entry_denied': handler._validate_relation_parent_entry(775, 545, 'payment.request')}

parent = actor['payment.request'].browse(1813).exists()
stages['parent_exists'] = bool(parent)
if parent:
    stages['parent_read_rights'] = _attempt(parent.check_access_rights, 'read')
    stages['parent_read_rule'] = _attempt(parent.check_access_rule, 'read')
    field = parent._fields.get('partner_id')
    stages['parent_field_model'] = getattr(field, 'comodel_name', None)
    stages['parent_membership'] = RECORD_ID in parent['partner_id'].ids

try:
    contract = handler._load_relation_contract(model='payment.request', record_id=1813, action_id=775, menu_id=545)
    stages['parent_contract_loaded'] = True
    stages['parent_effective_read'] = bool(
        contract.get('statusContract', {}).get('globalStatus', {})
        .get('effectiveRecordCapabilities', {}).get('read'))
    node = _find_field(contract.get('layoutContract'), 'partner_id')
    stages['parent_field_node_found'] = bool(node)
    if node:
        entry = (node.get('fieldInfo') or {}).get('relation_entry') or node.get('relation_entry') or {}
        stages['parent_relation_entry'] = {key: entry.get(key) for key in
            ('model', 'can_read', 'can_open', 'action_id', 'menu_id', 'reason_code', 'create_mode')}
        stages['parent_relation_entry_exact_target'] = (
            entry.get('model') == MODEL and entry.get('can_read') is True and entry.get('can_open') is True
            and positive_relation_id(entry.get('action_id')) == ACTION_ID
            and positive_relation_id(entry.get('menu_id')) == MENU_ID)
        stages['parent_relation_entry_visible'] = node.get('invisible') is not True
except Exception as error:  # noqa: BLE001 - diagnostic must report, never mask
    stages['parent_contract_error'] = f'{type(error).__name__}: {error}'

child_record = actor[MODEL].browse(RECORD_ID).exists()
stages['child_exists'] = bool(child_record)
if child_record:
    stages['child_read_rights'] = _attempt(child_record.check_access_rights, 'read')
    stages['child_read_rule'] = _attempt(child_record.check_access_rule, 'read')
    stages['child_field_access'] = _attempt(child_record.check_field_access_rights, 'read', None)

try:
    child_contract = handler._load_relation_contract(model=MODEL, record_id=RECORD_ID, action_id=ACTION_ID, menu_id=MENU_ID)
    stages['child_contract_loaded'] = True
    stages['child_effective_read'] = bool(
        child_contract.get('statusContract', {}).get('globalStatus', {})
        .get('effectiveRecordCapabilities', {}).get('read'))
except Exception as error:  # noqa: BLE001
    stages['child_contract_error'] = f'{type(error).__name__}: {error}'

try:
    validate_relation_action_origin(
        actor, ORIGIN, model=MODEL, record_id=RECORD_ID,
        target_action_id=ACTION_ID, target_menu_id=MENU_ID,
        load_contract=handler._load_relation_contract,
        validate_entry=handler._validate_relation_parent_entry,
    )
    stages['validate_relation_action_origin'] = True
except Exception as error:  # noqa: BLE001 - exact denial stage is the diagnostic outcome
    stages['validate_relation_action_origin'] = f'{type(error).__name__}: {error}'

print('RELATION_NAV_STAGES', json.dumps(stages, ensure_ascii=False, default=str))
env.cr.rollback()
