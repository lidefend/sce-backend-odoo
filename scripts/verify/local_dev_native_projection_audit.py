"""Governed read-only ORM proof for native projection retirement.

No record creation or configuration writes. Uses the existing project actor;
metadata retirement reads use sudo, actor view/access reads do not.
"""
import ast
import json
from pathlib import Path
from xml.etree import ElementTree as ET

from odoo import api
from odoo.addons import smart_construction_core
from odoo.addons.smart_core.core.form_structure_authority import authenticated_form_role_key
from odoo.addons.smart_core.handlers.ui_contract_v2 import UiContractV2Handler
from odoo.addons.smart_core.handlers.system_init import SystemInitHandler
from odoo.addons.smart_core.delivery.menu_service import MenuService
from odoo.addons.smart_core.delivery.menu_fact_service import MenuFactService
from odoo.addons.smart_construction_core.services.locked_menu_policy_contract import load_locked_menu_policy_contract

assert env.cr.dbname == "sc_dev_demo", "requires exact local.dev database"
env.cr.rollback()
original_commit = env.cr.commit
def reject_commit(*args, **kwargs):
    raise RuntimeError("readback forbids transaction commit")
env.cr.commit = reject_commit
results, errors = [], []
root = Path(smart_construction_core.__file__).parent

try:
    declaration = ET.parse(root / 'data/native_guidance_form_retirement.xml').getroot()
    expression = ast.parse(declaration.find('function/value').get('eval'), mode='eval').body
    identities = [call.args[0].value for call in expression.elts]
    identities += ['smart_construction_core.business_config_contract_tender_doc_purchase_form_structure_v1',
                   'smart_construction_core.business_config_contract_tender_doc_purchase_productized_form_v1']
    for identity in identities:
        record = env.ref(identity)
        assert not record.active and record.status == 'draft', identity + ' remains effective'
    results.append({'check': 'exact_retired_projections', 'status': 'passed', 'count': len(identities)})
    contract = load_locked_menu_policy_contract()
    for key, declared in contract['products'].items():
        policy = env['sc.product.policy'].sudo().search([('product_key', '=', key), ('active', '=', True)])
        assert len(policy) == 1, 'ambiguous installed edition ' + key
        expected = {row['menu_xmlid']: row['release_state'] for group in declared['menu_groups'] for row in group['menus']}
        actual = {row['menu_xmlid']: row['release_state'] for group in policy.menu_groups for row in group['menus']}
        assert actual == expected, 'installed edition drift ' + key
        results.append({'check': 'edition_definition', 'product_key': key, 'status': 'passed',
                        'released': sum(value == 'released' for value in actual.values()),
                        'preview': sum(value == 'preview' for value in actual.values())})
    actor = env['res.users'].sudo().search([('login', '=', 'sc_test_admin'), ('active', '=', True)])
    assert len(actor) == 1, 'existing managed project actor unavailable'
    actor_env = api.Environment(env.cr, actor.id, {'allowed_company_ids': [actor.company_id.id], 'lang': 'zh_CN'})
    group_xmlids = actor.groups_id.get_external_id()
    visible_ids = {row['menu_id'] for row in MenuFactService(actor_env).export_visible_menu_facts().flat}
    permission_rows = []
    for group in contract['products']['construction.standard']['menu_groups']:
        for row in group['menus']:
            native_menu = actor_env.ref(row['menu_xmlid'])
            action = actor_env.ref(row['action_xmlid']) if row.get('action_xmlid') else None
            model_name = row.get('res_model')
            permission_rows.append({'menu_xmlid': row['menu_xmlid'], 'menu_id': native_menu.id,
                'native_visible': native_menu.id in visible_ids,
                'menu_active': native_menu.active,
                'menu_group_allowed': not native_menu.groups_id or bool(native_menu.groups_id & actor.groups_id),
                'model': model_name, 'model_read_acl': actor_env[model_name].check_access_rights('read', raise_exception=False) if model_name else None,
                'action_read_allowed': MenuService(actor_env)._action_is_runtime_allowed(action, 'read') if action else None})
    results.append({'check': 'admin_permission_facts', 'status': 'observed', 'user_id': actor.id,
                    'company_id': actor.company_id.id, 'group_xmlids': sorted(group_xmlids.values()),
                    'entries': permission_rows, 'limitation': 'model ACL and action/menu facts; record rules require record-specific observations'})
    model = actor_env['tender.doc.purchase']
    model.check_access_rights('read')
    action = actor_env.ref('smart_construction_core.action_sc_tender_registration_fee')
    menu = actor_env.ref('smart_construction_core.menu_sc_tender_registration_fee')
    view = model.get_view(view_type='form')
    form = ET.fromstring(view['arch'])
    for name in ('legacy_visible_applicant_name', 'legacy_visible_document_state', 'legacy_record_id', 'legacy_source_table', 'legacy_attachment_ref'):
        assert form.find(f".//field[@name='{name}']").get('readonly') in {'1', 'True'}, name
    assert form.find(".//field[@name='active']") is not None
    assert form.find(".//field[@name='attachment_ids']").get('widget') == 'many2many_binary'
    role = authenticated_form_role_key(actor_env)
    configs = actor_env['ui.business.config.contract']._effective_view_orchestration_contracts(
        'tender.doc.purchase', view_type='form', action_id=action.id, view_id=view['id'], role_key=role)
    retired_ids = {env.ref(identity).id for identity in identities}
    config_ids = [config.id for config in configs]
    assert not set(config_ids) & retired_ids, 'retired projection still selected'
    response = UiContractV2Handler(actor_env, su_env=actor_env['ir.model'].sudo().env).handle({'params': {
        'op': 'action_open', 'model': 'tender.doc.purchase', 'action_id': action.id, 'menu_id': menu.id,
        'view_id': view['id'], 'view_type': 'form', 'render_profile': 'create', 'client_type': 'web_pc',
        'delivery_profile': 'full', 'context': {'allowed_company_ids': [actor.company_id.id]},
    }})
    assert response.ok, str(response.error)
    delivered = response.data
    structure = delivered.get('formStructureContract') or {}
    assert structure.get('structureAuthority') == 'container_tree' and structure.get('structureSource') == 'native_view', 'delivered layout still has a second owner'
    names = set()
    def collect(value):
        if isinstance(value, dict):
            if value.get('type') == 'field' or value.get('fieldCode'):
                names.add(value.get('fieldCode') or value.get('name'))
            for child in value.values():
                collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)
    collect((delivered.get('layoutContract') or {}).get('containerTree'))
    required = {'legacy_visible_applicant_name', 'legacy_visible_document_state', 'legacy_record_id',
                'legacy_source_table', 'legacy_attachment_ref', 'active', 'attachment_ids'}
    assert required <= names, 'native fields missing from delivered layout: ' + str(sorted(required - names))
    results.append({'check': 'native_tender_actor_contract', 'status': 'passed', 'user_id': actor.id,
                    'company_id': actor.company_id.id, 'role': role, 'view_id': view['id'],
                    'effective_config_ids': config_ids, 'structure_authority': structure['structureAuthority'],
                    'required_native_fields': sorted(required)})
    edition_entries = {key: {row['menu_xmlid'] for group in product['menu_groups'] for row in group['menus']}
                       for key, product in contract['products'].items()}
    preview_only = edition_entries['construction.preview'] - edition_entries['construction.standard']
    preview_ids = {env.ref(xmlid).id for xmlid in preview_only}
    for key in ('construction.standard', 'construction.preview'):
        reply = SystemInitHandler(env=actor_env).handle(payload={'params': {'delivery_product_key': key,
            'delivery_edition_key': key.split('.')[-1]}})
        assert reply.ok, str(reply.error)
        effective = reply.data['edition_runtime']['effective']['product_key']
        assert effective == key, 'unexpected edition fallback: ' + effective
        observed = set()
        def visit(nodes):
            for node in nodes:
                metadata = node.get('meta') or {}
                identity = node.get('menu_id') or metadata.get('menu_id')
                if identity:
                    observed.add(int(identity))
                visit(node.get('children') or [])
        visit(reply.data['navigation']['nav'])
        declared_ids = {env.ref(xmlid).id for xmlid in edition_entries[key]}
        assert observed & declared_ids, 'empty edition observation'
        assert key != 'construction.standard' or not observed & preview_ids, 'preview entries leaked into standard'
        assert key != 'construction.preview' or observed & preview_ids, 'preview edition has no discriminating preview entry'
        results.append({'check': 'actor_edition_navigation', 'status': 'passed', 'product_key': key,
                        'observed_declared_count': len(observed & declared_ids),
                        'observed_preview_count': len(observed & preview_ids),
                        'user_id': actor.id, 'company_id': actor.company_id.id})
except Exception as exc:
    errors.append(str(exc))
finally:
    env.cr.rollback()
    env.cr.commit = original_commit

print('NATIVE_PROJECTION_AUDIT=' + json.dumps({'database': 'sc_dev_demo', 'status': 'failed' if errors else 'passed',
      'checks': results, 'errors': errors}, ensure_ascii=False), flush=True)
if errors:
    raise RuntimeError('native projection audit failed')
