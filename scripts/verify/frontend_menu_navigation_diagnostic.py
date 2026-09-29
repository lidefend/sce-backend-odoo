"""Read-only diagnosis in the registered acceptance backend; never commit data."""
import logging
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
    user = env['res.users'].search([('login', '=', 'fixture_role_config_admin')], limit=1)
    assert user and user.id == 34
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
