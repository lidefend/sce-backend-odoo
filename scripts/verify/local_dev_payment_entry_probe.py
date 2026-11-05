"""P4 read-only payment entry diagnosis on the registered local.dev database."""
import json

DATABASE = 'sc_dev_demo'
MENU = 'smart_construction_core.menu_sc_payment_execution'


def schema_readback(env):
    """Read existing facts even when model prefetch would hit an unupgraded column."""
    cr = env.cr
    cr.execute("SELECT column_name FROM information_schema.columns WHERE table_name='ir_ui_menu'")
    columns = {r[0] for r in cr.fetchall()}
    if 'sc_scenario_exempt' in columns:
        return None
    cr.execute("SELECT m.id, m.action FROM ir_ui_menu m JOIN ir_model_data x ON x.res_id=m.id "
               "WHERE x.module='smart_construction_core' AND x.name='menu_sc_payment_execution' AND x.model='ir.ui.menu'")
    menu = cr.dictfetchone()
    cr.execute("SELECT id, name, latest_version, state FROM ir_module_module "
               "WHERE name IN ('smart_core','smart_construction_core','smart_construction_scene') ORDER BY name")
    modules = cr.dictfetchall()
    tables = {}
    for table in ('sc_product_scenario', 'sc_product_scenario_entry'):
        cr.execute('SELECT to_regclass(%s)', (table,))
        tables[table] = bool(cr.fetchone()[0])
    bindings = []
    if menu and all(tables.values()):
        cr.execute('SELECT s.id, s.code, s.active FROM sc_product_scenario_entry e '
                   'JOIN sc_product_scenario s ON s.id=e.scenario_id WHERE e.menu_id=%s', (menu['id'],))
        bindings = cr.dictfetchall()
    cr.execute("SELECT key, value FROM ir_config_parameter WHERE key LIKE 'sc.scene.tenant.enablement.%%.business.v1:payment.%%' "
               "OR key IN ('smart_core.platform_release_db','smart_core.release_operator.catalog_source_db') ORDER BY key")
    enablement = cr.dictfetchall()
    cr.execute("SELECT company_id, scene_key, enabled FROM sc_scene_company_enablement "
               "WHERE scene_key IN ('business.v1:payment.capital','payment.capital') ORDER BY company_id")
    legacy_enablement = cr.dictfetchall()
    cr.execute("SELECT id, product_key, active, state, menu_groups FROM sc_product_policy ORDER BY id")
    policies = []
    for row in cr.dictfetchall():
        groups = row.pop('menu_groups') or []
        row['payment_menus'] = [m for g in groups for m in g.get('menus', []) if m.get('menu_xmlid') == MENU]
        if row['payment_menus']:
            policies.append(row)
    cr.execute("SELECT id, product_key, version, state, is_active, snapshot_json, meta_json "
               "FROM sc_edition_release_snapshot WHERE active AND is_active ORDER BY id")
    snapshots = []
    for row in cr.dictfetchall():
        meta = row.pop('meta_json') or {}
        frozen = row.pop('snapshot_json') or {}
        row['payment_pages'] = [p for p in (meta.get('release_draft') or {}).get('pages', [])
                                if p.get('menu_xmlid') == MENU]
        row['schema'] = frozen.get('policy_snapshot_schema')
        snapshots.append(row)
    # Use registered relation metadata, never fetch menu records on the missing schema.
    menu_groups = env['ir.ui.menu']._fields['groups_id']
    from psycopg2 import sql
    cr.execute(sql.SQL('SELECT {} FROM {} WHERE {}=%s').format(
        sql.Identifier(menu_groups.column2), sql.Identifier(menu_groups.relation),
        sql.Identifier(menu_groups.column1)), (menu['id'],))
    gids = [r[0] for r in cr.fetchall()]
    cr.execute("SELECT module || '.' || name AS xmlid, res_id FROM ir_model_data "
               "WHERE model='res.groups' AND res_id=ANY(%s)", (gids,))
    menu_group_xmlids = cr.dictfetchall()
    action_id = int(menu['action'].split(',')[1])
    cr.execute("SELECT module || '.' || name AS xmlid FROM ir_model_data "
               "WHERE model='ir.actions.act_window' AND res_id=%s", (action_id,))
    action_xmlids = [r[0] for r in cr.fetchall()]
    action_groups = env['ir.actions.act_window']._fields['groups_id']
    cr.execute(sql.SQL('SELECT {} FROM {} WHERE {}=%s').format(
        sql.Identifier(action_groups.column2), sql.Identifier(action_groups.relation),
        sql.Identifier(action_groups.column1)), (action_id,))
    action_gids = [r[0] for r in cr.fetchall()]
    cr.execute("SELECT a.group_id, a.perm_read, a.perm_write, a.perm_create, a.perm_unlink "
               "FROM ir_model_access a JOIN ir_model m ON a.model_id=m.id "
               "WHERE a.active AND m.model='sc.payment.execution' ORDER BY a.id")
    acl = cr.dictfetchall()
    cr.execute('SELECT u.id, u.login, u.company_id, ARRAY_AGG(r.gid ORDER BY r.gid) AS matched_menu_groups '
               'FROM res_users u LEFT JOIN res_groups_users_rel r ON r.uid=u.id AND r.gid=ANY(%s) '
               'WHERE u.active AND NOT u.share GROUP BY u.id ORDER BY u.id', (gids,))
    principals = cr.dictfetchall()
    for row in principals:
        row['matched_menu_groups'] = [gid for gid in row['matched_menu_groups'] if gid is not None]
        cr.execute('SELECT gid FROM res_groups_users_rel WHERE uid=%s', (row['id'],))
        memberships = {r[0] for r in cr.fetchall()}
        row['action_group_allowed'] = not action_gids or bool(memberships.intersection(action_gids))
        row['acl'] = {permission: any(a[permission] for a in acl if not a['group_id'] or a['group_id'] in memberships)
                      for permission in ('perm_read', 'perm_write', 'perm_create', 'perm_unlink')}
    from odoo.addons.smart_core.handlers.system_init import _load_platform_release_gate
    gate = _load_platform_release_gate(env, product_key='construction.standard')
    return {'database': cr.dbname, 'readonly': True, 'blocking_layer': 'module_schema_upgrade',
            'missing_columns': ['ir_ui_menu.sc_scenario_exempt'], 'modules': modules,
            'menu': menu, 'scenario_tables': tables, 'bindings': bindings,
            'enablement_parameters': enablement, 'legacy_enablement': legacy_enablement,
            'policies': policies, 'local_active_snapshots': snapshots,
            'publication_gate': {key: gate.get(key) for key in ('applied', 'fail_closed', 'reason', 'platform_db', 'snapshot_id')},
            'menu_group_ids': gids, 'menu_group_xmlids': menu_group_xmlids,
            'action_id': action_id, 'action_xmlids': action_xmlids,
            'action_group_ids': action_gids, 'model_acl': acl, 'principals': principals,
            'limits': 'Raw existing facts only. Runtime route/ACL evaluation blocked by schema mismatch; no upgrade or configuration write performed.'}


def missing_layers(row):
    missing = []
    if row.get('published') is not True:
        missing.append('native_publication')
    scope = row.get('scope') or {}
    if scope.get('location') == 'missing' or not scope:
        missing.append('scenario_binding')
    elif scope.get('scenario_key'):
        if scope.get('scenario_active') is False:
            missing.append('scenario_inactive')
        if row.get('enabled') is not True:
            missing.append('company_enablement')
    if not row.get('menu_group_allowed') or not row.get('action_group_allowed') or not row.get('read_acl'):
        missing.append('role_authorization')
    if row.get('route_allowed') is not True and not missing:
        missing.append('runtime_route_authority')
    return missing


def probe(env):
    if env.cr.dbname != DATABASE:
        raise RuntimeError('registered local.dev database required')
    env.cr.rollback()
    env.cr.execute('SET TRANSACTION READ ONLY')
    original_commit = env.cr.commit
    def refuse_commit(*args, **kwargs):
        raise RuntimeError('payment entry probe forbids commit')
    env.cr.commit = refuse_commit
    try:
        schema = schema_readback(env)
        if schema is not None:
            return schema
        from odoo import api
        from odoo.addons.smart_core.handlers.system_init import _load_platform_release_gate, _resolve_startup_delivery_identity
        from odoo.addons.smart_core.delivery.runtime_route_authority import build_runtime_route_authority, menu_publication_decision
        from odoo.addons.smart_construction_core.services.scenario_surface_projection import runtime_menu_scope
        from odoo.addons.smart_construction_scene.services.tenant_scene_activation import read_tenant_enablement, _enablement_param_key
        from odoo.addons.smart_construction_scene.services.business_scene_enablement import business_key
        menu = env.ref(MENU).sudo()
        action = menu.action
        if not action or action._name != 'ir.actions.act_window' or action.res_model != 'sc.payment.execution':
            raise RuntimeError('payment native identity mismatch')
        scope = runtime_menu_scope(env)[0].get(MENU, {})
        scenario = env['sc.product.scenario'].sudo().with_context(active_test=False).search([('code', '=', scope.get('scenario_key'))], limit=1)
        scope['scenario_active'] = bool(scenario.active) if scenario else None
        users = env['res.users'].sudo().search([('active', '=', True), ('login', '=', 'demo_role_finance')], order='id')
        if len(users) != 1:
            raise RuntimeError('exact existing finance principal required')
        results = []
        for user in users:
            for company in user.company_ids:
                principal = api.Environment(env.cr, user.id, {**env.context, 'allowed_company_ids': [company.id]}, su=False)
                identity = _resolve_startup_delivery_identity(principal, {})
                gate = _load_platform_release_gate(principal, product_key=identity['product_key'])
                scene = scope.get('scenario_key')
                key = business_key(scene) if scene else ''
                groups = set(user.groups_id.ids)
                row = {'uid': user.id, 'login': user.login, 'company_id': company.id,
                       'product_key': identity['product_key'], 'scope': scope,
                       'exempt': bool(menu.sc_scenario_exempt),
                       'publication_gate': {k: gate.get(k) for k in ('applied', 'fail_closed', 'reason', 'platform_db', 'snapshot_id', 'version')},
                       'published': MENU in (gate.get('menu_release_states') or {}),
                       'release_state': (gate.get('menu_release_states') or {}).get(MENU),
                       'enablement_key': key,
                       'enablement_value': env['ir.config_parameter'].sudo().get_param(_enablement_param_key(company.id, key)) if key else None,
                       'enabled': read_tenant_enablement(principal, company.id, key) if key else None,
                       'menu_group_allowed': not menu.groups_id or bool(groups.intersection(menu.groups_id.ids)),
                       'action_group_allowed': not action.groups_id or bool(groups.intersection(action.groups_id.ids)),
                       'matched_group_xmlids': [v for k, v in user.groups_id.get_external_id().items() if k in set(menu.groups_id.ids + action.groups_id.ids)],
                       'read_acl': principal[action.res_model].check_access_rights('read', raise_exception=False)}
                authority = build_runtime_route_authority(principal)
                row['route_allowed'] = menu_publication_decision(authority, menu.id, action.id)
                row['denials'] = [r for r in authority.get('denied_actions', []) if r.get('menu_id') == menu.id or r.get('action_id') == action.id]
                from odoo.tools.safe_eval import safe_eval
                from odoo.addons.smart_core.handlers.route_authority_validate import RouteAuthorityValidateHandler
                validation = RouteAuthorityValidateHandler(principal).handle({'action_id': action.id, 'menu_id': menu.id})
                row['route_validation'] = validation.to_legacy_dict()
                action_domain = safe_eval(action.domain or '[]', {'uid': user.id, 'context': principal.context})
                records = principal[action.res_model].search(action_domain, limit=10)
                records.check_access_rule('read')
                records.read(['id'])
                row['record_access'] = {'visible_count': principal[action.res_model].search_count([]),
                                        'action_visible_count': principal[action.res_model].search_count(action_domain),
                                        'action_domain': action_domain,
                                        'sample_ids': records.ids, 'read_rule_passed': True,
                                        'su': principal.su, 'allowed_company_ids': principal.context['allowed_company_ids']}
                row['missing_layers'] = missing_layers(row)
                results.append(row)
        return {'database': env.cr.dbname, 'menu_id': menu.id, 'menu_xmlid': MENU,
                'menu_active': menu.active if 'active' in menu._fields else None,
                'scenario_source': __import__('inspect').getfile(runtime_menu_scope),
                'action_id': action.id, 'action_xmlid': action.get_external_id().get(action.id), 'model': action.res_model,
                'principals': results, 'readonly': True,
                'limits': 'Entry authority and ID-only read-rule sample; no payment writes or execution; no permission or exemption changes.'}
    finally:
        env.cr.rollback()
        env.cr.commit = original_commit


if 'env' in globals():
    print('PAYMENT_ENTRY_PROBE=' + json.dumps(probe(env), ensure_ascii=False, default=str))
