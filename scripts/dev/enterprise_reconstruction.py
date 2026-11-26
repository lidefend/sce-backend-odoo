"""Demo reference extraction and minimal platform bootstrap for a fresh rehearsal.

No organization, job, employee, ordinary user, business role assignment or company
scenario choice is inserted here. Those facts must be produced by the browser.
"""
import ast
import hashlib
import json
import os
from pathlib import Path
import xml.etree.ElementTree as ET


def reference(root):
    demo = root / 'demo_addons/smart_construction_demo'
    manifest = ast.literal_eval((demo / '__manifest__.py').read_text())
    records = {}
    sources = {}
    for filename in manifest['data']:
        if not filename.endswith('.xml'):
            continue
        source = demo / filename
        for node in ET.parse(source).iter('record'):
            if node.get('model') not in ('hr.department', 'hr.job', 'hr.employee', 'res.users'):
                continue
            sources[str(source.relative_to(root))] = hashlib.sha256(source.read_bytes()).hexdigest()
            xmlid = node.get('id')
            if '.' not in xmlid:
                xmlid = 'smart_construction_demo.' + xmlid
            row = records.setdefault(xmlid, {'xmlid': xmlid, 'model': node.get('model'), 'fields': {}})
            for field in node.findall('field'):
                # Preserve references and declarations; never execute XML eval.
                row['fields'][field.get('name')] = dict(field.attrib, text=field.text or '')
    return {'schema': 'enterprise_reconstruction.reference.v1', 'sources': sources,
            'records': list(records.values()), 'transactions': 'representative_journeys_only'}


def compare_configuration(reference_data, facts, progress):
    """Compare saved business facts; record creation counts are not parity."""
    failures = []
    checked = 0
    bindings = {row['xmlid']: row['id'] for stage in progress['stages'].values()
                for row in stage.get('records', []) if 'id' in row and 'xmlid' in row}
    groups = {row['id']: row for row in facts['res.groups']['rows']}
    xmlids = {xmlid: int(key) for item in facts.values() for key, xmlid in item.get('external_ids', {}).items()}
    xmlids.update(bindings)
    def closure(ids):
        result, pending = set(), list(ids)
        while pending:
            item = pending.pop()
            if item not in result:
                result.add(item)
                pending.extend(groups.get(item, {}).get('implied_ids', []))
        return result
    def relation_id(value):
        return value[0] if isinstance(value, list) and value else value or False
    def check(identity, field, actual, expected):
        nonlocal checked
        checked += 1
        if actual != expected:
            failures.append({'record': identity, 'field': field, 'expected': expected, 'actual': actual})
    def group_refs(expression):
        # Parse declarations, never eval their code.
        tree = ast.parse(expression, mode='eval')
        return [node.args[0].value for node in ast.walk(tree)
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'ref'
                and len(node.args) == 1 and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str)]
    expected_rows = [row for row in reference_data['records'] if row['model'] != 'res.users'
                     or 'group_sc_role_' in row['fields'].get('groups_id', {}).get('eval', '')]
    # Employee identities are established by the actual linked user, not copied demo XML ids.
    for row in expected_rows:
        if row['model'] != 'hr.employee':
            continue
        user_id = bindings.get(row['fields']['user_id']['ref'])
        matches = [item for item in facts['hr.employee']['rows'] if user_id and relation_id(item['user_id']) == user_id]
        if len(matches) == 1:
            xmlids[row['xmlid']] = matches[0]['id']
    for row in expected_rows:
        identity, model = row['xmlid'], row['model']
        actual = next((item for item in facts[model]['rows'] if item['id'] == xmlids.get(identity)), None)
        check(identity, 'exists', bool(actual), True)
        if not actual:
            continue
        for field, declaration in row['fields'].items():
            if field in ('company_ids', 'groups_id'):
                continue
            if 'ref' in declaration:
                expected = xmlids.get(declaration['ref'])
                check(identity, field, relation_id(actual.get(field)), expected)
            elif 'eval' in declaration:
                check(identity, field, actual.get(field), ast.literal_eval(declaration['eval']))
            elif field in ('active', 'share'):
                check(identity, field, actual.get(field), ast.literal_eval(declaration['text']))
            else:
                check(identity, field, actual.get(field), declaration['text'])
        if model in ('res.users', 'hr.employee'):
            check(identity, 'active', actual['active'], True)
        if model == 'res.users':
            check(identity, 'company_ids', sorted(actual['company_ids']), [xmlids['base.main_company']])
            expected = closure([xmlids[ref] for ref in group_refs(row['fields']['groups_id']['eval'])])
            observed = closure(actual['groups_id'])
            check(identity, 'permission_closure', sorted(observed), sorted(expected))
    return {'status': 'passed' if not failures else 'failed', 'assertions': checked,
            'business_users': sum(row['model'] == 'res.users' for row in expected_rows),
            'employees': sum(row['model'] == 'hr.employee' for row in expected_rows), 'differences': failures}


def authority_manifest(reference_data, progress, import_report=None):
    """Use recorded submissions, never infer explicit roots from effective groups."""
    records = progress['stages']['res.users']['records']
    assert len(records) == 21 and len({row['id'] for row in records}) == 21
    role_writes = [write for write in progress['writes'] if write.get('ok')
                   and write.get('model') == 'res.users'
                   and set(write.get('fields', [])) & {'sc_user_permission_group_ids', 'sc_user_role_group_ids'}]
    assert len(role_writes) == 1 and role_writes[0]['ids'] == [7], 'unexpected assignment history'
    sources = {row['xmlid']: row for row in reference_data['records']}
    imported_ids = set()
    if import_report is not None:
        assert import_report.get('scope') == 'configuration'
        for case in import_report.get('cases', []):
            if case.get('status') == 'passed' and case.get('name') == 'formal_business_role_configuration_import':
                ids = set(case['ids'])
                assert any(event.get('phase') == 'execute' and event.get('dry_run') is False
                           and event.get('ok') and event.get('error_count') == 0 and set(event.get('ids', [])) == ids
                           for event in import_report.get('imports', [])), 'missing native commit evidence'
                imported_ids.update(ids)
        assert imported_ids == {7, 8, 9, 10}, 'unexpected import recovery scope'
    result = []
    for row in records:
        source = sources[row['xmlid']]
        roots = ['smart_construction_core.group_sc_internal_user']
        if row['id'] == 7:
            assert row['xmlid'] == 'smart_construction_demo.user_sc_operation_demo'
            roots.append('smart_construction_core.group_sc_role_operation_user')
        if row['id'] in imported_ids:
            tree = ast.parse(source['fields']['groups_id']['eval'], mode='eval')
            roles = [node.args[0].value for node in ast.walk(tree) if isinstance(node, ast.Call)
                     and isinstance(node.func, ast.Name) and node.func.id == 'ref'
                     and '.group_sc_role_' in node.args[0].value]
            roots = ['smart_construction_core.group_sc_internal_user'] + roles
        result.append({'id': row['id'], 'login': source['fields']['login']['text'], 'roots': roots})
    return {'database': 'sc_init_6b0769da09e2', 'accounts': result,
            'basis': 'Recorded UI creation roots, operation-role write for uid 7, and committed native import evidence: '
                     + (hashlib.sha256(json.dumps(import_report, sort_keys=True).encode()).hexdigest() if import_report else 'none'),
            'journal_sha256': hashlib.sha256(json.dumps(progress, sort_keys=True).encode()).hexdigest()}


def reconcile_reconstruction_authority(env, manifest, apply=False):
    assert env.cr.dbname == manifest['database'] == 'sc_init_6b0769da09e2'
    assert len(manifest['accounts']) == 21
    assert not env['ir.module.module'].search_count([('name', '=', 'smart_construction_demo'), ('state', '=', 'installed')])
    actor = env.ref('base.user_admin')
    assert actor.has_group('base.group_system')
    Users = env['res.users'].with_user(actor)
    assert not Users.env.su
    before_count = Users.with_context(active_test=False).search_count([])
    results = []
    for account in manifest['accounts']:
        user = Users.browse(account['id']).exists()
        assert user.login == account['login']
        before = set(user.groups_id.ids)
        roots = env['res.groups']
        for xmlid in account['roots']:
            roots |= env.ref(xmlid)
        assert set((roots | roots.trans_implied_ids).ids) == before, 'submitted roots must preserve every permission'
        if (user.sudo().sc_group_authority_state or {}).get('status') != 'tracked':
            action = user.action_sc_review_group_authority()
            review = env[action['res_model']].with_user(actor).browse(action['res_id'])
            review.write({'root_group_ids': [(6, 0, roots.ids)],
                          'note': manifest['basis'] + ' Journal SHA256=' + manifest['journal_sha256']})
            review.action_confirm()
        assert set(user.groups_id.ids) == before
        assert user._sc_explicit_group_roots() == set(roots.ids)
        results.append({'user_id': user.id, 'permissions_unchanged': True, 'origin': 'tracked'})
    assert Users.with_context(active_test=False).search_count([]) == before_count
    report = {'status': 'passed', 'apply': apply, 'actor_id': actor.id, 'accounts': results,
              'journal_sha256': manifest['journal_sha256'], 'business_writes': 0}
    if apply:
        env.cr.commit()
    else:
        env.cr.rollback()
    print('RECONSTRUCTION_AUTHORITY_RECOVERY=' + json.dumps(report))



def audit_configuration_permissions(env):
    """Read native configuration surfaces as the real actor, without sudo probes.

    Inventory includes every business-config ACL, every menu/action explicitly
    assigned to that capability, and descendants of those menus. Method bodies
    and writes still require targeted ORM/UI verification; inventory is not PASS.
    """
    from lxml import etree
    actor = env['res.users'].search([('login', '=', 'init_business_admin')], limit=1)
    assert actor and not actor.has_group('base.group_system')
    groups = env.ref('smart_construction_core.group_sc_cap_business_config_admin') | env.ref(
        'smart_core.group_smart_core_business_config_admin')
    acl = env['ir.model.access'].search([('group_id', 'in', groups.ids), ('active', '=', True)])
    models = set(acl.mapped('model_id.model'))
    menu_ids = env['ir.model.data'].search([('model', '=', 'ir.ui.menu')]).mapped('res_id')
    all_menus = env['ir.ui.menu'].browse(menu_ids).exists()
    menus = all_menus.filtered(lambda row: bool(row.groups_id & groups))
    roots = env.ref('smart_construction_core.menu_sc_business_config_center') | menus
    actions = env['ir.actions.act_window'].search([('groups_id', 'in', groups.ids)])
    def under_configuration(menu):
        current = menu
        while current:
            if current in roots:
                return True
            current = current.parent_id
        return False
    menus |= all_menus.filtered(lambda row: under_configuration(row) or (
        row.action and row.action._name == 'ir.actions.act_window' and row.action.id in actions.ids))
    actions |= env['ir.actions.act_window'].browse([
        menu.action.id for menu in menus if menu.action and menu.action._name == 'ir.actions.act_window'])
    assert menus and actions, 'configuration inventory must not be empty'
    models.update(actions.mapped('res_model'))
    models.update(('res.company', 'hr.employee', 'hr.employee.public', 'res.users', 'res.groups',
                   'hr.department', 'hr.job', 'sc.scene.company.enablement'))
    report = {'status': 'inventory_only', 'database': env.cr.dbname, 'actor_id': actor.id,
              'platform_admin': False, 'models': [], 'actions': [], 'menus': [],
              'limitations': ['method writes require ORM/UI tests', 'empty recordsets do not prove record access',
                              'ACL denial alone may be an intentional or delegated boundary']}
    for menu in menus.sorted('id'):
        chain = menu
        current = menu.parent_id
        while current:
            chain |= current
            current = current.parent_id
        report['menus'].append({'xmlid': menu.get_external_id().get(menu.id), 'id': menu.id,
            'name': menu.name, 'active': menu.active, 'action': str(menu.action),
            'group_visible': all(not row.groups_id or bool(row.groups_id & actor.groups_id) for row in chain)})
    for name in sorted(models):
        if name not in env:
            report['models'].append({'model': name, 'error': 'not_installed'})
            continue
        model = env[name].with_user(actor).with_context(allowed_company_ids=actor.company_ids.ids)
        assert not model.env.su
        item = {'model': name, 'acl': {op: model.check_access_rights(op, raise_exception=False)
                for op in ('read', 'create', 'write', 'unlink')}, 'transient': model._transient}
        try:
            with env.cr.savepoint():
                rows = model.search([], limit=5)
                rows.read(['display_name'])
                item['sample_read_count'] = len(rows)
        except Exception as exc:
            item['read_error'] = type(exc).__name__ + ': ' + str(exc)
        report['models'].append(item)
    for action in actions.sorted('id'):
        row = {'xmlid': action.get_external_id().get(action.id), 'name': action.name,
               'model': action.res_model, 'group_visible': not action.groups_id or bool(action.groups_id & actor.groups_id),
               'views': []}
        model = env[action.res_model].with_user(actor).with_context(allowed_company_ids=actor.company_ids.ids)
        for view_id, kind in action.views:
            if kind not in ('tree', 'form', 'search'):
                continue
            view = {'type': kind, 'id': view_id, 'relations': [], 'buttons': []}
            try:
                with env.cr.savepoint():
                    arch = etree.fromstring(model.get_view(view_id or None, kind)['arch'])
                    view['flags'] = {key: arch.get(key) for key in ('create', 'edit', 'delete', 'import', 'export_xlsx')}
                    def inspect_fields(container, current_model, path=''):
                        for field in container.xpath('.//field[not(ancestor::field)]'):
                            descriptor = current_model._fields.get(field.get('name'))
                            related = getattr(descriptor, 'comodel_name', None)
                            if not related:
                                continue
                            target = env[related].with_user(actor)
                            relation = {'field': path + field.get('name'), 'model': related,
                                        'read_acl': target.check_access_rights('read', raise_exception=False)}
                            try:
                                with env.cr.savepoint():
                                    matches = target.search([], limit=1)
                                    matches.read(['display_name'])
                                    relation['sample_read_count'] = len(matches)
                            except Exception as exc:
                                relation['error'] = type(exc).__name__ + ': ' + str(exc)
                            view['relations'].append(relation)
                            for child in field:
                                if child.tag in ('tree', 'form'):
                                    # Detach to make ancestor predicates local to this subview.
                                    inspect_fields(etree.fromstring(etree.tostring(child)), target,
                                                   path + field.get('name') + '.')
                    inspect_fields(arch, model)
                    view['buttons'] = [{'name': node.get('name'), 'type': node.get('type'),
                                        'invisible': node.get('invisible')} for node in arch.xpath('.//button[not(ancestor::field)]')]
            except Exception as exc:
                view['error'] = type(exc).__name__ + ': ' + str(exc)
            row['views'].append(view)
        report['actions'].append(row)
    env.cr.rollback()
    print('RECONSTRUCTION_PERMISSION_AUDIT=' + json.dumps(report, ensure_ascii=False, default=str))


def bootstrap(env):
    if os.environ.get('FRESH_DB_AUTHORITY_MANIFEST'):
        return reconcile_reconstruction_authority(env, json.loads(os.environ['FRESH_DB_AUTHORITY_MANIFEST']),
                                                  os.environ.get('FRESH_DB_AUTHORITY_APPLY') == '1')
    assert env.cr.dbname == 'sc_init_6b0769da09e2', 'only the registered fresh reconstruction database'
    assert not env['ir.module.module'].search_count([('name', '=', 'smart_construction_demo'), ('state', '=', 'installed')])
    if os.environ.get('FRESH_DB_PERMISSION_AUDIT') == '1':
        return audit_configuration_permissions(env)
    if os.environ.get('FRESH_DB_BASELINE_ONLY') == '1':
        facts = {}
        for model in ('res.company', 'hr.department', 'hr.job', 'hr.employee', 'res.users', 'sc.scene.company.enablement'):
            rows = env[model].with_context(active_test=False).search([])
            fields = ['id'] + {
                'res.company': ['name', 'currency_id'],
                'hr.department': ['name', 'parent_id', 'company_id', 'manager_id'],
                'hr.job': ['name', 'department_id', 'company_id'],
                'hr.employee': ['name', 'user_id', 'department_id', 'job_id', 'company_id', 'work_email', 'active'],
                'res.users': ['name', 'login', 'email', 'company_id', 'company_ids', 'groups_id', 'employee_id', 'sc_personnel_department_id', 'sc_personnel_job_id', 'active', 'lang', 'tz', 'share'],
                'sc.scene.company.enablement': ['scene_key', 'enabled'],
            }[model]
            facts[model] = {'rows': rows.read(fields), 'external_ids': rows.get_external_id()}
        groups = env['res.groups'].search([])
        facts['res.groups'] = {'rows': groups.read(['id', 'name', 'implied_ids']), 'external_ids': groups.get_external_id()}
        actor = env['res.users'].search([('login', '=', 'init_business_admin')], limit=1)
        public = env['hr.employee.public'].with_user(actor)
        print('RECONSTRUCTION_RELATION_AUTHORITY=' + json.dumps({
            'public_employee_read': public.check_access_rights('read', raise_exception=False),
            'private_employee_read': env['hr.employee'].with_user(actor).check_access_rights('read', raise_exception=False),
            'public_employee_ids': public.search([]).ids,
        }))
        print('RECONSTRUCTION_BASELINE=' + json.dumps(facts, ensure_ascii=False, default=str))
        env.cr.rollback()
        return
    assert not env['res.users'].search_count([('login', '=', 'init_business_admin')]), 'bootstrap is single-use'
    assert env['hr.department'].search([]) == env.ref('hr.dep_administration'), 'only the Odoo installation department may preexist'
    assert not env['hr.job'].search_count([]), 'jobs must begin empty'
    assert env['hr.employee'].search([]) == env.ref('hr.employee_admin'), 'only the Odoo installation employee may preexist'
    password = os.environ['FRESH_DB_PASSWORD']
    assert len(password) >= 24
    company = env.ref('base.main_company')
    company.write({'name': '企业初始化重建验收', 'currency_id': env.ref('base.CNY').id})
    env['res.lang']._activate_lang('zh_CN')
    admin = env['res.users'].with_context(no_reset_password=True).create({
        'name': '业务配置管理员', 'login': 'init_business_admin', 'password': password,
        'company_id': company.id, 'company_ids': [(6, 0, company.ids)], 'lang': 'zh_CN',
        'groups_id': [(6, 0, (env.ref('base.group_user') | env.ref('smart_construction_core.group_sc_role_business_admin')).ids)],
    })
    assert not admin.has_group('base.group_system'), 'business operator must not be platform administrator'
    namespace = env['sc.platform.namespace'].sudo().create({
        'namespace_id': 'ns_6b0769da09e2', 'display_name': '一次性企业初始化验收',
        'database_name': env.cr.dbname, 'lifecycle_state': 'active', 'audience': 'tenant',
        'duty_key': 'enterprise_reconstruction',
    })
    alias = env['sc.platform.namespace.alias'].sudo().search([('alias', '=', 'clean'), ('alias_kind', '=', 'path')])
    if alias:
        alias.write({'namespace_id': namespace.id, 'retired_at': False})
    else:
        env['sc.platform.namespace.alias'].sudo().create({'alias': 'clean', 'alias_kind': 'path', 'namespace_id': namespace.id, 'is_primary': True})
    config = env['ir.config_parameter'].sudo()
    config.set_param('smart_core.platform_release_db', env.cr.dbname)
    config.set_param('smart_core.release_operator.catalog_source_db', env.cr.dbname)
    from odoo.addons.smart_core.delivery.edition_release_snapshot_service import EditionReleaseSnapshotService
    EditionReleaseSnapshotService(env).freeze_release_surface(product_key='construction.standard',
        version='synthetic-enterprise-reconstruction', note='Unmodified standard product, fresh disposable tenant', replace_active=True)
    facts = {model: env[model].search_count([]) for model in ('hr.department', 'hr.job', 'hr.employee', 'sc.scene.company.enablement')}
    assert facts['hr.department'] == 1 and facts['hr.job'] == 0 and facts['hr.employee'] == 1
    env.cr.commit()
    print('RECONSTRUCTION_BOOTSTRAP=' + json.dumps({'database': env.cr.dbname, 'company_id': company.id,
        'login': admin.login, 'user_id': admin.id, 'platform_admin': False, 'business_baseline': facts}, ensure_ascii=False))


if 'env' in globals():
    if os.environ.get('FRESH_DB_REFERENCE_ONLY') == '1':
        assert env.cr.dbname == 'sc_dev_demo'
        rows = env['sc.scene.company.enablement'].sudo().search([('company_id', '=', 1), ('enabled', '=', True)])
        print('RECONSTRUCTION_SCENARIO_REFERENCE=' + json.dumps({'database': env.cr.dbname, 'company_id': 1,
            'scene_keys': sorted(rows.mapped('scene_key'))}, ensure_ascii=False))
        env.cr.rollback()
    else:
        bootstrap(env)
elif __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    parser.add_argument('--import-report')
    parser.add_argument('--authority-manifest', action='store_true')
    parser.add_argument('--facts-log')
    parser.add_argument('--progress')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    result = reference(root)
    if args.authority_manifest:
        result = authority_manifest(result, json.loads(Path(args.progress).read_text()),
                                    json.loads(Path(args.import_report).read_text()) if args.import_report else None)
        Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
        raise SystemExit(0)
    if args.facts_log:
        payloads = [line.split('RECONSTRUCTION_BASELINE=', 1)[1] for line in Path(args.facts_log).read_text().splitlines() if 'RECONSTRUCTION_BASELINE=' in line]
        assert len(payloads) == 1
        facts = json.loads(payloads[0])
        Path(args.output).with_name('configuration-facts.json').write_text(json.dumps(facts, ensure_ascii=False, indent=2) + '\n')
        result = compare_configuration(result, facts, json.loads(Path(args.progress).read_text()))
        Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps({key: value for key, value in result.items() if key != 'differences'}, ensure_ascii=False))
        raise SystemExit(0 if result['status'] == 'passed' else 1)
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    from collections import Counter
    print(dict(Counter(row['model'] for row in result['records'])))
