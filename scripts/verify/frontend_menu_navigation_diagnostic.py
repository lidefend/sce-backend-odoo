"""Read-only diagnosis in the registered acceptance backend; never commit data."""
import logging
import json
from odoo import api
from odoo.addons.smart_core.handlers.menu_configuration import MenuConfigurationLoadHandler
assert env.cr.dbname == 'sc_frontend_acceptance'
env.cr.rollback()
env.cr.execute('SET TRANSACTION READ ONLY')
class DiagnosticLog(logging.Handler):
    def emit(self, record):
        if record.getMessage().startswith('MENU_CONFIG_DELIVERY_NAVIGATION_STATE_FAILED'):
            print(record.getMessage())
logger = logging.getLogger('odoo.addons.smart_core.handlers.menu_configuration')
handler = DiagnosticLog()
previous = logger.level
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)
try:
    # Diagnose the declared finance acceptance route without granting anything.
    # XML identities survive module upgrades; integer fixture IDs do not.
    from odoo.addons.smart_core.delivery.runtime_route_authority import published_route_authority, menu_publication_decision
    finance = env.ref('smart_construction_acceptance_fixture.fe_user_finance')
    finance_actor = api.Environment(env.cr, finance.id, dict(env.context, allowed_company_ids=[finance.company_id.id]))
    menu = env.ref('smart_construction_core.menu_sc_user_payment_apply')
    authority = published_route_authority(finance_actor)
    states = finance_actor['sc.scene.company.enablement'].search_read(
        [('company_id', '=', finance.company_id.id)], ['scene_key', 'enabled'])
    print('BUSINESS_ROUTE_DIAGNOSTIC', json.dumps({
        'uid': finance.id, 'company_id': finance.company_id.id,
        'menu_id': menu.id, 'action_id': menu.action.id,
        'published': menu_publication_decision(authority, menu.id, menu.action.id),
        'denials': [row for row in authority.get('denied_actions', [])
                    if row.get('menu_id') == menu.id or row.get('action_id') == menu.action.id],
        'company_states': states,
    }, ensure_ascii=False))
    user = env.ref('smart_construction_acceptance_fixture.fe_user_config_admin')
    assert user.login == 'fixture_role_config_admin'
    actor = api.Environment(env.cr, user.id, dict(env.context, allowed_company_ids=[user.company_id.id]))
    nav, meta = MenuConfigurationLoadHandler(actor)._runtime_release_navigation_tree()
    print('MENU_NAV_DIAGNOSTIC', {'count': len(nav), 'meta': meta})
    from odoo.addons.smart_core.identity.identity_resolver import IdentityResolver
    resolver = IdentityResolver(actor)
    surface = resolver.build_role_surface(resolver.user_group_xmlids(actor.user), [], set())
    candidate = MenuConfigurationLoadHandler(actor)
    flags = candidate._runtime_role_surface()
    candidate._runtime_role_surface = lambda: dict(surface, is_platform_admin=flags['is_platform_admin'], is_business_config_admin=flags['is_business_config_admin'])
    nav, meta = candidate._runtime_release_navigation_tree()
    print('MENU_NAV_CANONICAL_IDENTITY_DIAGNOSTIC', {'count': len(nav), 'exposure': surface.get('exposure_policy_declared'), 'meta': meta})
finally:
    logger.removeHandler(handler)
    logger.setLevel(previous)
    env.cr.rollback()
