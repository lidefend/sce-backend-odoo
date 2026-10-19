"""P4 observation on the registered demo duty. Never assigns roles or commits."""
import hashlib
import inspect
import json
import os
from pathlib import Path


def observation_plan(groups, users):
    """Select existing non-superuser witnesses; membership is not assignment."""
    rows = []
    for group in sorted(groups, key=lambda row: row['id']):
        witnesses = sorted(user['id'] for user in users
                           if user['id'] != 1 and group['id'] in user['group_ids'])
        rows.append({'group_id': group['id'], 'xmlids': group['xmlids'],
                     'witness_uids': witnesses,
                     'selected_uid': witnesses[0] if witnesses else None,
                     'status': 'observed_membership' if witnesses else 'uncovered'})
    return rows


def observe(env):
    from odoo import api
    assert env.cr.dbname == 'sc_demo', 'demo duty database required'
    env.cr.rollback()
    env.cr.execute('SET TRANSACTION READ ONLY')
    original_commit = env.cr.commit
    def refuse_commit(*args, **kwargs):
        raise RuntimeError('AUTH-01 read-only observation forbids commit')
    env.cr.commit = refuse_commit
    try:
        Group = env['res.groups'].sudo()
        groups = Group.search([('sc_assignable_user_permission', '=', True)])
        users = env['res.users'].sudo().search([('active', '=', True), ('share', '=', False)])
        xmlid_rows = env['ir.model.data'].sudo().search([('model', '=', 'res.groups')])
        xmlids = {}
        for item in xmlid_rows:
            xmlids.setdefault(item.res_id, []).append(item.module + '.' + item.name)
        group_rows = [{'id': group.id, 'xmlids': sorted(xmlids.get(group.id, [])),
                       'closure_ids': sorted((group | group.trans_implied_ids).ids),
                       'closure_without_xmlid': sorted(g.id for g in group | group.trans_implied_ids if g.id not in xmlids)}
                      for group in groups]
        user_rows = [{'id': user.id, 'group_ids': user.groups_id.ids} for user in users]
        plan = observation_plan(group_rows, user_rows)
        selected = sorted({row['selected_uid'] for row in plan if row['selected_uid']})
        acl_rows = []
        for uid in selected:
            user = users.browse(uid)
            actor = api.Environment(env.cr, uid, dict(env.context, allowed_company_ids=[user.company_id.id]), su=False)
            models = {}
            for model in ('res.users', 'res.groups', 'sc.approval.scope', 'sc.approval.scope.user.wizard', 'project.project'):
                models[model] = {operation: bool(actor[model].check_access_rights(operation, raise_exception=False))
                                 for operation in ('read', 'write', 'create', 'unlink')}
            acl_rows.append({'uid': uid, 'company_id': user.company_id.id, 'su': actor.su, 'acl_only': models})
        # Installed implementation provenance, including native Odoo and overlays.
        methods = []
        for model in ('res.users', 'res.groups'):
            for cls in type(env[model]).__mro__:
                for method in ('create', 'write', 'unlink'):
                    function = cls.__dict__.get(method)
                    if function is None:
                        continue
                    try:
                        path = Path(inspect.getsourcefile(inspect.unwrap(function)))
                        methods.append({'model': model, 'method': method, 'module': cls.__module__,
                                        'source': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
                    except (TypeError, OSError) as error:
                        methods.append({'model': model, 'method': method, 'module': cls.__module__, 'unresolved': type(error).__name__})
        return {'schema': 'system_permission_runtime_observation.v1',
                'database': env.cr.dbname, 'source_revision': os.getenv('SC_SOURCE_REVISION'),
                'mode': 'transaction_read_only', 'authorization_verdict': 'not_evaluated',
                'groups': group_rows, 'role_observations': plan, 'acl_observations': acl_rows,
                'installed_user_group_write_implementations': methods,
                'limitations': ['Effective membership does not prove explicit assignment.',
                                'Witness may hold several roles; ACL cannot be attributed to a single role.',
                                'ACL only: record rules, intent gates, system.init and actual operations not exercised.',
                                'Missing witness remains uncovered; no temporary user or grant is created.']}
    finally:
        env.cr.rollback()
        env.cr.commit = original_commit



def validate_witness_uids(uids):
    if not isinstance(uids, list) or not uids or any(type(uid) is not int or uid <= 1 for uid in uids):
        raise ValueError('explicit non-superuser witnesses required')
    return sorted(set(uids))


def observe_navigation(env, uids):
    uids = validate_witness_uids(uids)
    from odoo import api
    from odoo.addons.smart_core.handlers.system_init import SystemInitHandler
    assert env.cr.dbname == 'sc_demo', 'demo duty database required'
    results = []
    original_commit = env.cr.commit
    def refuse_commit(*args, **kwargs):
        raise RuntimeError('AUTH-01 navigation observation forbids commit')
    env.cr.commit = refuse_commit
    try:
        for uid in sorted(set(uids)):
            env.cr.rollback()
            env.cr.execute('SET TRANSACTION READ ONLY')
            print('AUTH01_NAVIGATION_START uid=' + str(uid), flush=True)
            try:
                user = env['res.users'].sudo().browse(uid).exists()
                if not user or not user.active or user.share:
                    raise ValueError('witness no longer active internal user')
                actor = api.Environment(env.cr, uid, dict(env.context, allowed_company_ids=[user.company_id.id]), su=False)
                result = SystemInitHandler(actor).run({'intent': 'system.init', 'params': {}})
                data = result.data if hasattr(result, 'data') else result.get('data', {})
                nav = data.get('navigation') or {}
                if nav.get('source') != 'system_init.navigation' or not isinstance(nav.get('nav'), list):
                    raise ValueError('final navigation contract missing')
                integrity = nav.get('integrity') or {}
                if integrity.get('missing_authority_count') != 0:
                    raise ValueError('final navigation authority incomplete')
                results.append({'uid': uid, 'status': 'observed', 'su': actor.su,
                                'integrity': integrity,
                                'role_surface': data.get('role_surface'),
                                'navigation_meta': nav.get('meta'),
                                'default_route': data.get('default_route'),
                                'navigation_sha256': hashlib.sha256(json.dumps(nav, sort_keys=True, default=str).encode()).hexdigest()})
            except Exception as error:
                results.append({'uid': uid, 'status': 'failed', 'error_type': type(error).__name__,
                                'error': str(error)[:300]})
            finally:
                env.cr.rollback()
                print('AUTH01_NAVIGATION_END uid=' + str(uid), flush=True)
        return {'schema': 'system_permission_navigation_observation.v1',
                'source_revision': os.getenv('SC_SOURCE_REVISION'), 'database': env.cr.dbname,
                'mode': 'transaction_read_only', 'results': results,
                'limitations': ['Actual handler execution under each user; HTTP authentication and router gate are not exercised.',
                                'No business operation performed; navigation observation is not full role acceptance.']}
    finally:
        env.cr.rollback()
        env.cr.commit = original_commit


if __name__ == '__main__' and 'env' in globals():
    uids = os.getenv('ROLE_PERMISSION_OBSERVATION_UIDS')
    result = observe_navigation(env, json.loads(uids)) if uids else observe(env)
    print('AUTH01_OBSERVATION=' + json.dumps(result, ensure_ascii=False, sort_keys=True))

