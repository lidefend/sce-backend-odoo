"""Read-only diagnosis in the registered acceptance backend; never commit data."""
import logging
import json
from odoo import api
from odoo.addons.smart_core.handlers.menu_configuration import MenuConfigurationLoadHandler
from odoo.addons.smart_core.identity.identity_resolver import IdentityResolver


def _xmlid(record):
    if not record:
        return ""
    return str(record.get_external_id().get(record.id) or "")


def _flatten_navigation_pairs(nodes):
    pairs = set()
    stack = list(nodes or [])
    while stack:
        node = stack.pop()
        if not isinstance(node, dict):
            continue
        meta = node.get("meta") if isinstance(node.get("meta"), dict) else {}
        action_id = int(node.get("action_id") or meta.get("action_id") or 0)
        menu_id = int(node.get("menu_id") or meta.get("menu_id") or 0)
        if action_id > 0 and menu_id > 0:
            pairs.add((menu_id, action_id))
        stack.extend(node.get("children") or [])
    return pairs


def _target_menu_diagnostic(env, actor, menu_xmlid):
    from odoo.addons.smart_core.delivery.runtime_route_authority import (
        menu_publication_decision,
        published_route_authority,
    )
    from odoo.addons.smart_construction_core.services.scenario_surface_projection import (
        load_runtime_surface,
        runtime_menu_scope,
    )
    from odoo.addons.smart_construction_scene.services.business_scene_enablement import (
        business_catalog,
        business_key,
    )
    from odoo.addons.smart_construction_scene.services.tenant_scene_activation import (
        read_tenant_enablement,
    )

    menu = env.ref(menu_xmlid)
    action = menu.action
    action_id = int(action.id or 0)
    menu_id = int(menu.id or 0)
    context = dict(actor.context or {})
    context["allowed_company_ids"] = [int(actor.user.company_id.id)]
    actor = api.Environment(env.cr, actor.user.id, context)
    authority = published_route_authority(actor)
    surface = load_runtime_surface(actor)
    index, _by_id, _by_action = runtime_menu_scope(actor, surface)
    company_id = int(actor.user.company_id.id)
    tenant_enabled = read_tenant_enablement(
        actor,
        company_id,
        business_key("project.management"),
    )
    release_states = _load_published_menu_release_states(actor)
    release_state = {
        row["scene_key"]: row
        for row in business_catalog(surface, release_states, {
            business_key("project.management"): tenant_enabled,
        })
        if row.get("scene_key") == "project.management"
    }
    nav, nav_meta = MenuConfigurationLoadHandler(actor)._runtime_release_navigation_tree()
    nav_pairs = _flatten_navigation_pairs(nav)
    denied = [
        row for row in authority.get("denied_actions", [])
        if int(row.get("menu_id") or 0) in {0, menu_id}
        or int(row.get("action_id") or 0) in {0, action_id}
    ]
    group_xmlids = [
        _xmlid(group) for group in menu.groups_id
    ]
    return {
        "menu_xmlid": menu_xmlid,
        "menu_id": menu_id,
        "action_id": action_id,
        "action_xmlid": _xmlid(action),
        "model": str(action.res_model or ""),
        "native_visible": menu_id in set(
            actor["ir.ui.menu"].with_user(actor.user)._visible_menu_ids()
        ),
        "menu_group_xmlids": [value for value in group_xmlids if value],
        "menu_groups_match": all(actor.user.has_group(value) for value in group_xmlids if value),
        "model_read_acl": bool(
            actor[action.res_model].check_access_rights("read", raise_exception=False)
        ),
        "surface_location": index.get(menu_xmlid),
        "menu_release_state": release_states.get(menu_xmlid),
        "tenant_project_management_enabled": tenant_enabled,
        "business_catalog": release_state.get("project.management"),
        "published": menu_publication_decision(authority, menu_id, action_id),
        "published_in_runtime_nav": (menu_id, action_id) in nav_pairs,
        "runtime_nav_target_count": len(nav_pairs),
        "runtime_nav_meta": nav_meta,
        "denied_route_rows": denied,
    }


def _load_published_menu_release_states(env):
    from odoo.addons.smart_construction_core.services.product_menu_source import (
        load_published_menu_release_states,
    )
    return load_published_menu_release_states(env)
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
        'my_work': _target_menu_diagnostic(
            env,
            finance_actor,
            'smart_construction_core.menu_sc_my_work',
        ),
        'denials': [row for row in authority.get('denied_actions', [])
                    if row.get('menu_id') == menu.id or row.get('action_id') == menu.action.id],
        'company_states': states,
    }, ensure_ascii=False))
    from odoo.addons.smart_core.handlers.system_init import _load_platform_release_gate
    my_work = env.ref('smart_construction_core.menu_sc_my_work')
    policy = env['sc.product.policy'].sudo().with_context(active_test=False).search([
        ('product_key', '=', 'construction.standard'),
    ], limit=1)
    policy_rows = [
        row for group in (policy.menu_groups or []) for row in (group.get('menus') or [])
    ]
    policy_my_work = next(
        (row for row in policy_rows
         if row.get('menu_xmlid') == 'smart_construction_core.menu_sc_my_work'),
        None,
    )
    release_gate = _load_platform_release_gate(env, product_key='construction.standard')
    print('MY_WORK_POLICY_DIAGNOSTIC', json.dumps({
        'policy_id': int(policy.id or 0),
        'policy_active': bool(policy.active),
        'policy_state': policy.state,
        'policy_menu_count': len(policy_rows),
        'policy_my_work': policy_my_work,
        'snapshot': {
            key: release_gate.get(key)
            for key in ('applied', 'reason', 'snapshot_id', 'version', 'page_count', 'total_page_count')
        },
        'snapshot_my_work_release_state': (
            release_gate.get('menu_release_states') or {}
        ).get('smart_construction_core.menu_sc_my_work'),
        'menu': {'menu_id': my_work.id, 'action_id': my_work.action.id},
    }, ensure_ascii=False, default=str))
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
    role_diagnostics = {}
    for label, user_xmlid in (
        ("config_admin", "smart_construction_acceptance_fixture.fe_user_config_admin"),
        ("pm", "smart_construction_acceptance_fixture.fe_user_pm"),
        ("project_member", "smart_construction_acceptance_fixture.fe_user_project_a_member"),
    ):
        role_user = env.ref(user_xmlid)
        role_actor = api.Environment(
            env.cr,
            role_user.id,
            dict(env.context, allowed_company_ids=[role_user.company_id.id]),
        )
        role_resolver = IdentityResolver(role_actor)
        role_groups = role_resolver.user_group_xmlids(role_user)
        role_codes, role_evidence = role_resolver.resolve_role_codes_with_evidence(role_groups)
        role_diagnostics[label] = {
            "uid": role_user.id,
            "login": role_user.login,
            "company_id": role_user.company_id.id,
            "role_codes": role_codes,
            "role_evidence": role_evidence,
            "project_kanban": _target_menu_diagnostic(
                env,
                role_actor,
                "smart_construction_core.menu_sc_project_kanban",
            ),
            "project_dashboard": _target_menu_diagnostic(
                env,
                role_actor,
                "smart_construction_core.menu_sc_project_dashboard",
            ),
        }
    print("MENU_KANBAN_ROLE_DIAGNOSTIC", json.dumps(
        role_diagnostics,
        ensure_ascii=False,
        default=str,
    ))
finally:
    logger.removeHandler(handler)
    logger.setLevel(previous)
    env.cr.rollback()
