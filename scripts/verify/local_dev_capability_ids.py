"""Read-only authority capture for the personal capability page."""
import hashlib
import json
from odoo.addons.smart_construction_core.services import capability_registry
from odoo.addons.smart_construction_core.handlers.product_configuration_capability import ProductConfigurationCapabilityCatalogHandler
from odoo.addons.smart_core.handlers.system_init import _resolve_startup_delivery_identity, _load_platform_release_gate
from odoo.addons.smart_core.delivery.product_policy_service import ProductPolicyService
assert env.cr.dbname == 'sc_dev_demo'
cases = []
for key, xmlid in (
    ('admin', 'smart_construction_demo.sc_demo_user_test_admin'),
    ('project-reader', 'smart_construction_demo.user_demo_project_read'),
):
    user = env.ref(xmlid)
    assert user.active
    principal = user.with_user(user).with_company(user.company_id).with_context(allowed_company_ids=user.company_ids.ids)
    result = ProductConfigurationCapabilityCatalogHandler(principal.env).handle()
    assert result['ok']
    navigation = []
    for row in capability_registry.list_capabilities_for_user(principal.env, user):
        if row['key'] == 'project.list.open' or (key == 'admin' and row['key'] in (
                'contract.income.track', 'contract.expense.track', 'cost.ledger.open', 'cost.profit.compare')):
            navigation.append({'key': row['key'], **row['default_payload']})
    if key == 'admin':
        assert len(navigation) == 5, 'project, two contract and two cost native query targets required'
    else:
        assert len(navigation) == 1, 'project reader must resolve project query target'
    startup_identity = _resolve_startup_delivery_identity(principal.env, {})
    editions = {}
    for edition in ('standard', 'preview'):
        product_key = 'construction.' + edition
        policy = ProductPolicyService(principal.env).get_policy(
            product_key=product_key, base_product_key='construction', edition_key=edition,
            enforce_release=True, enforce_access=True)
        editions[edition] = {
            'product_key': policy.get('product_key'),
            'diagnostics': policy.get('edition_diagnostics'),
            'declared_menu_xmlids': sorted(row['menu_xmlid'] for group in policy.get('menu_groups', [])
                                          for row in group.get('menus', []) if row.get('menu_xmlid')),
            'release_gate': _load_platform_release_gate(principal.env, product_key=product_key),
        }
    cases.append({'startup_identity': startup_identity, 'editions': editions,
                  'navigation': navigation, 'key': key, 'actor': {'id': user.id, 'login': user.login},
                  'groups': sorted(user.groups_id.ids), 'expected': result['data']['user_capabilities']})
facts = {}
for model in ('project.project', 'payment.request', 'tier.review', 'sc.approval.policy', 'construction.contract', 'construction.contract.income', 'construction.contract.expense'):
    facts[model] = env[model].sudo().with_context(active_test=False).search_read([], ['id', 'write_date'], order='id')
print('LOCAL_DEV_CAPABILITY_JSON=' + json.dumps({'database': env.cr.dbname, 'cases': cases,
      'business_fingerprint': hashlib.sha256(json.dumps(facts, sort_keys=True, default=str).encode()).hexdigest()}, ensure_ascii=True))
