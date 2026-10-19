"""Bounded metadata transaction, invoked only by the daily-duty wrapper.

The industry XML remains authoritative. This tool never imports module data.
"""
import hashlib
import importlib.util
from pathlib import Path
from xml.etree import ElementTree as ET

VIEW_TYPES = {
    'smart_construction_core.view_sc_runtime_user_form': 'form',
    'smart_construction_core.view_sc_runtime_user_tree': 'tree',
    'smart_construction_core.view_sc_runtime_user_search': 'search',
}
FACT_MODELS = ('res.users', 'res.company', 'res.partner', 'hr.employee',
               'res.groups', 'sc.project.member.assignment', 'mail.followers',
               'sc.tenant.company.registration')


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def source_views(source, expected):
    require(hashlib.sha256(source.read_bytes()).hexdigest() == expected, 'XML digest mismatch')
    root = ET.parse(source).getroot()
    result = {}
    for xmlid, kind in VIEW_TYPES.items():
        rows = root.findall("record[@id='%s']" % xmlid.split('.', 1)[1])
        require(len(rows) == 1 and rows[0].get('model') == 'ir.ui.view', 'missing/duplicate view declaration')
        arch = rows[0].find("field[@name='arch']")
        require(arch is not None and len(arch) == 1 and arch[0].tag == kind, 'invalid view type')
        result[xmlid] = ET.tostring(arch[0], encoding='unicode')
    return result


def validate_plan(current, plan):
    require(set(plan['views']) == set(VIEW_TYPES), 'plan write set mismatch')
    require(current == {'views': plan['views'], 'facts': plan['facts']}, 'plan drift; replan required')


def execute_change(env, action, before, saved, replacements, snapshot, validate, restore):
    """One transaction; commit is reached only after contract and fact checks."""
    commit = env.cr.commit
    def reject_commit():
        raise RuntimeError('premature commit forbidden')
    env.cr.commit = reject_commit
    try:
        if action == 'apply':
            validate_plan(before, saved)
            for xmlid in VIEW_TYPES:
                env.ref(xmlid).with_context(lang=None).write({'arch_db': replacements[xmlid]})
            env.flush_all()
            validate()
        else:
            require(action == 'restore', 'unsupported write action')
            require(before == saved['after'], 'restore refuses changed views or facts')
            restore(saved['before']['views'])
        env.flush_all()
        after = snapshot()
        require(before['facts'] == after['facts'], 'business/authorization facts changed')
        commit()
        return after
    except BaseException:
        env.cr.rollback()
        raise
    finally:
        env.cr.commit = commit


def reconcile_state(current, before, replacements):
    if current == before:
        return {'outcome': 'not_committed', 'before': before, 'after': current}
    require(current['facts'] == before['facts'], 'reconcile fact conflict')
    require(set(current['views']) == set(VIEW_TYPES), 'reconcile view set conflict')
    for xmlid, translated in current['views'].items():
        arch = translated.get('en_US') if isinstance(translated, dict) else translated
        require(arch and ET.canonicalize(arch, strip_text=True) ==
                ET.canonicalize(replacements[xmlid], strip_text=True), 'reconcile view conflict')
    return {'outcome': 'committed_observed', 'before': before, 'after': current}


def validate_connection(env, config, request):
    require(env.cr.dbname == request['database'], 'database identity mismatch')
    require(config['dbfilter'] == request['dbfilter'], 'effective dbfilter mismatch')
    env.cr.execute('SELECT system_identifier::text FROM pg_control_system()')
    require(env.cr.fetchone()[0] == request['system_identifier'], 'connected cluster identity mismatch')
    env.cr.execute('SELECT current_user')
    require(env.cr.fetchone()[0] == request['database_role'], 'connected database role mismatch')


def run(env, request):
    from psycopg2 import sql
    from psycopg2.extras import Json
    from odoo.addons import smart_construction_core

    from odoo.tools import config
    validate_connection(env, config, request)
    source = Path(smart_construction_core.__file__).parent / 'views/support/runtime_user_management_views.xml'
    require(str(source).startswith('/mnt/source-addons/'), 'unregistered addon source')
    replacements = source_views(source, request['xml_sha256'])
    tables = sorted(set([env[m]._table for m in FACT_MODELS] + [
        env['res.users']._fields[n].relation for n in ('groups_id', 'company_ids')]))
    # Block concurrent fact writes for this short metadata transaction; timeout fails closed.
    env.cr.execute("SET LOCAL lock_timeout = '5s'")
    for table in tables:
        env.cr.execute(sql.SQL('LOCK TABLE {} IN SHARE MODE').format(sql.Identifier(table)))
    ids = {}
    for xmlid, kind in VIEW_TYPES.items():
        view = env.ref(xmlid)
        require(view._name == 'ir.ui.view' and view.model == 'res.users' and view.type == kind,
                'installed view identity/type mismatch')
        ids[xmlid] = view.id
    env.cr.execute('SELECT id FROM ir_ui_view WHERE id IN %s ORDER BY id FOR UPDATE', (tuple(ids.values()),))

    def snapshot():
        facts = {}
        for table in tables:
            env.cr.execute(sql.SQL("SELECT count(*), md5(COALESCE(string_agg(row_to_json(t)::text, '' ORDER BY row_to_json(t)::text), '')) FROM {} t").format(sql.Identifier(table)))
            facts[table] = list(env.cr.fetchone())
        views = {}
        for xmlid, view_id in ids.items():
            env.cr.execute('SELECT arch_db FROM ir_ui_view WHERE id = %s', (view_id,))
            views[xmlid] = env.cr.fetchone()[0]
        return {'facts': facts, 'views': views}

    def validate():
        spec = importlib.util.spec_from_file_location('personnel_boundary', '/mnt/scripts/verify/user_permission_view_contract_boundary_guard.py')
        guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guard)
        guard.env = env
        guard.main()

    def restore(views):
        require(set(views) == set(VIEW_TYPES), 'restore write set mismatch')
        for xmlid, arch in views.items():
            env.cr.execute('UPDATE ir_ui_view SET arch_db = %s WHERE id = %s', (Json(arch), ids[xmlid]))
        env.invalidate_all(flush=False)
        env.registry.clear_cache()

    before = snapshot()
    action = request['action']
    if action == 'plan':
        env.cr.rollback()
        return before
    if action == 'reconcile':
        if request.get('verify_target') == 'restore':
            saved = request['saved']
            require(before in (saved['before'], saved['after']), 'restore reconciliation conflict')
            state = {'outcome': 'restored_observed' if before == saved['before'] else 'not_restored',
                     'before': saved['after'], 'after': before}
        else:
            state = reconcile_state(before, request['saved'], replacements)
        if state['outcome'] == 'committed_observed':
            validate()
            env.flush_all()
            require(snapshot() == before, 'reconcile changed facts/views')
        env.cr.rollback()
        return state
    if action == 'verify':
        require(before == request['saved']['after'], 'persistent readback mismatch')
        if request.get('verify_target') == 'apply':
            validate()
        env.flush_all()
        require(snapshot() == before, 'readback modified facts/views')
        env.cr.rollback()
        return before
    after = execute_change(env, action, before, request['saved'], replacements, snapshot, validate, restore)
    # Commit succeeded; a lost receipt requires readback, never blind replay.
    return {'before': before, 'after': after, 'committed': True}
