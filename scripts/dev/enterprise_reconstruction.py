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
            if field in ('tz', 'lang', 'company_ids', 'groups_id'):
                continue
            if 'ref' in declaration:
                expected = xmlids.get(declaration['ref'])
                check(identity, field, relation_id(actual.get(field)), expected)
            elif field in actual and field != 'active' and 'eval' not in declaration:
                check(identity, field, actual[field] or '', declaration['text'])
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


def bootstrap(env):
    assert env.cr.dbname == 'sc_init_6b0769da09e2', 'only the registered fresh reconstruction database'
    assert not env['ir.module.module'].search_count([('name', '=', 'smart_construction_demo'), ('state', '=', 'installed')])
    if os.environ.get('FRESH_DB_BASELINE_ONLY') == '1':
        facts = {}
        for model in ('res.company', 'hr.department', 'hr.job', 'hr.employee', 'res.users', 'sc.scene.company.enablement'):
            rows = env[model].with_context(active_test=False).search([])
            fields = ['id'] + {
                'res.company': ['name', 'currency_id'],
                'hr.department': ['name', 'parent_id', 'company_id', 'manager_id'],
                'hr.job': ['name', 'department_id', 'company_id'],
                'hr.employee': ['name', 'user_id', 'department_id', 'job_id', 'company_id', 'work_email', 'active'],
                'res.users': ['name', 'login', 'email', 'company_id', 'company_ids', 'groups_id', 'employee_id', 'sc_personnel_department_id', 'sc_personnel_job_id', 'active'],
                'sc.scene.company.enablement': ['scene_key', 'enabled'],
            }[model]
            facts[model] = {'rows': rows.read(fields), 'external_ids': rows.get_external_id()}
        groups = env['res.groups'].search([])
        facts['res.groups'] = {'rows': groups.read(['id', 'name', 'implied_ids']), 'external_ids': groups.get_external_id()}
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
    parser.add_argument('--facts-log')
    parser.add_argument('--progress')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    result = reference(root)
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
