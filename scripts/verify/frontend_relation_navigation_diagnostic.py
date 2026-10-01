"""Read-only diagnosis of exact readonly relation navigation authority.

Runs inside the registered acceptance backend against the fixed acceptance
database. It never writes: the transaction is read-only and rolled back.
It reports the exact denial stage for one declared relation navigation.

The origin record identity is resolved from the governed fixture declaration
(stable fixture name bound to model, owning company and expected business
state, requiring a unique match); no record id is hardcoded.
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

FIXTURE_MODEL = 'payment.request'
FIXTURE_NAME = 'FE-DELIVERY-HARDENING-001'
FIXTURE_COMPANY_NAME = 'FE Company A'
FIXTURE_EXPECTED_STATE = 'draft'
FIXTURE_RELATION_FIELD = 'partner_id'
PARENT_ACTION_ID = 775
PARENT_MENU_ID = 545
# Declared child target contract: the partner record form.
MODEL = 'res.partner'
ACTION_ID = 324
MENU_ID = 164
LOGIN = 'fixture_role_finance'


def _resolve_unique(records, label):
    """Return the single record matching a governed fixture declaration."""
    count = len(records)
    if count != 1:
        raise RuntimeError(f'{label} requires a unique match, found {count}')
    return records


company = _resolve_unique(
    env['res.company'].sudo().search([('name', '=', FIXTURE_COMPANY_NAME)], limit=2),
    f'fixture company {FIXTURE_COMPANY_NAME}',
)
parent = _resolve_unique(
    env[FIXTURE_MODEL].sudo().search([
        ('name', '=', FIXTURE_NAME),
        ('company_id', '=', company.id),
        ('state', '=', FIXTURE_EXPECTED_STATE),
    ], limit=2),
    f'fixture {FIXTURE_MODEL} {FIXTURE_NAME} company={company.id} state={FIXTURE_EXPECTED_STATE}',
)
parent_partner = _resolve_unique(parent[FIXTURE_RELATION_FIELD], f'{FIXTURE_MODEL}.{FIXTURE_RELATION_FIELD}')
child_model = parent._fields[FIXTURE_RELATION_FIELD].comodel_name
assert child_model == MODEL, f'fixture relation comodel {child_model} != declared target {MODEL}'
PARENT_RECORD_ID = parent.id
RECORD_ID = parent_partner.id
ORIGIN = {'model': FIXTURE_MODEL, 'record_id': PARENT_RECORD_ID, 'field': FIXTURE_RELATION_FIELD,
          'action_id': PARENT_ACTION_ID, 'menu_id': PARENT_MENU_ID}
print('RELATION_NAV_RESOLVED_IDENTITY', json.dumps({
    'parent_model': FIXTURE_MODEL,
    'parent_record_id': PARENT_RECORD_ID,
    'parent_company_id': company.id,
    'parent_state': FIXTURE_EXPECTED_STATE,
    'relation_field': FIXTURE_RELATION_FIELD,
    'child_model': child_model,
    'child_record_id': RECORD_ID,
}, ensure_ascii=False))


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

stages = {'parent_entry_denied': handler._validate_relation_parent_entry(
    PARENT_ACTION_ID, PARENT_MENU_ID, FIXTURE_MODEL)}

parent_actor_record = actor[FIXTURE_MODEL].browse(PARENT_RECORD_ID).exists()
stages['parent_exists'] = bool(parent_actor_record)
if parent_actor_record:
    stages['parent_read_rights'] = _attempt(parent_actor_record.check_access_rights, 'read')
    stages['parent_read_rule'] = _attempt(parent_actor_record.check_access_rule, 'read')
    field = parent_actor_record._fields.get(FIXTURE_RELATION_FIELD)
    stages['parent_field_model'] = getattr(field, 'comodel_name', None)
    stages['parent_membership'] = RECORD_ID in parent_actor_record[FIXTURE_RELATION_FIELD].ids

try:
    contract = handler._load_relation_contract(
        model=FIXTURE_MODEL, record_id=PARENT_RECORD_ID,
        action_id=PARENT_ACTION_ID, menu_id=PARENT_MENU_ID)
    stages['parent_contract_loaded'] = True
    stages['parent_effective_read'] = bool(
        contract.get('statusContract', {}).get('globalStatus', {})
        .get('effectiveRecordCapabilities', {}).get('read'))
    node = _find_field(contract.get('layoutContract'), FIXTURE_RELATION_FIELD)
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
