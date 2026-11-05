"""Exact owner-authorized local.dev publication and payment company enablement."""
import json
import os

MENU = 'smart_construction_core.menu_sc_payment_execution'
ACK = 'PUBLISH_EXISTING_LOCAL_CATALOG_ENABLE_PAYMENT_COMPANY_1'


def unchanged_boundaries(before, after):
    return all(before[key] == after[key] for key in ('groups', 'menu_groups', 'action_groups', 'exempt', 'bindings', 'acl'))


def publish_frozen_snapshot(snapshot):
    # The existing freeze action may already have approved the candidate.
    if snapshot.state == 'candidate':
        snapshot.action_approve()
    if snapshot.state != 'approved':
        raise RuntimeError('Expected approved frozen snapshot before release')
    snapshot.action_release()


def assert_entry_ready(gate, route, snapshot_ids, menu_id, action_id):
    """Existence of any snapshot is not proof that this entry is published."""
    if (gate.get('applied') is not True or gate.get('reason') != 'OK'
            or gate.get('platform_db') != 'sc_dev_demo'
            or gate.get('snapshot_id') not in snapshot_ids
            or (gate.get('menu_release_states') or {}).get(MENU) != 'released'):
        raise RuntimeError('Effective snapshot does not publish the payment entry')
    data = route.get('data') or {}
    if (route.get('ok') is not True or data.get('allowed') is not True
            or data.get('menu_id') != menu_id or data.get('action_id') != action_id
            or data.get('model') != 'sc.payment.execution'):
        raise RuntimeError('Finance non-sudo route validation rejected the payment entry')


def configure(env):
    from odoo import api
    from odoo.addons.smart_core.delivery.edition_release_snapshot_service import EditionReleaseSnapshotService
    from odoo.addons.smart_construction_scene.handlers.scenario_activation import ScenarioActivationSetHandler
    from odoo.addons.smart_construction_scene.services.tenant_scene_activation import read_tenant_enablement
    phase = os.environ.get('BUSINESS_CONFIG_PAYMENT_PHASE', 'plan')
    if env.cr.dbname != 'sc_dev_demo' or phase not in ('plan', 'apply'):
        raise RuntimeError('Exact local.dev configuration scope required')
    if phase == 'apply' and os.environ.get('SC_CONFIRM_PAYMENT_CONFIG') != ACK:
        raise RuntimeError('Exact approved configuration acknowledgement required')
    if phase == 'plan':
        env.cr.rollback()
        env.cr.execute('SET TRANSACTION READ ONLY')
    menu = env.ref(MENU)
    if menu.id != 339 or menu.action.id != 908 or menu.action.res_model != 'sc.payment.execution':
        raise RuntimeError('Payment entry checkpoint changed')
    user = env['res.users'].search([('login', '=', 'demo_role_finance'), ('active', '=', True)])
    maintainer = env['res.users'].search([('login', '=', 'sc_demo_business_config'), ('active', '=', True)])
    if len(user) != 1 or user.id != 47 or user.company_id.id != 1 or len(maintainer) != 1:
        raise RuntimeError('Existing company/principal checkpoint changed')
    actor = api.Environment(env.cr, maintainer.id, {**env.context, 'allowed_company_ids': [1]}, su=False)
    if not actor.user.has_group('smart_construction_core.group_sc_cap_business_config_admin'):
        raise RuntimeError('Existing activation maintainer lacks required group')
    policy = env['sc.product.policy'].search([('product_key', '=', 'construction.standard'), ('active', '=', True)])
    if len(policy) != 1:
        raise RuntimeError('Exactly one existing standard policy required')
    snapshots = env['sc.edition.release.snapshot']
    params = env['ir.config_parameter'].sudo()
    publication_params = ('smart_core.platform_release_db', 'smart_core.release_operator.catalog_source_db')
    def state():
        bindings = env['sc.product.scenario.entry'].search([('menu_id', '=', menu.id)])
        return {'groups': sorted(user.groups_id.ids), 'menu_groups': sorted(menu.groups_id.ids),
                'action_groups': sorted(menu.action.groups_id.ids), 'exempt': bool(menu.sc_scenario_exempt),
                'bindings': [(r.id, r.scenario_id.code) for r in bindings],
                'acl': env['ir.model.access'].search([('model_id.model', '=', 'sc.payment.execution')]).read(
                    ['group_id', 'perm_read', 'perm_write', 'perm_create', 'perm_unlink', 'active']),
                'publication_parameters': {key: params.get_param(key) for key in publication_params},
                'enabled': read_tenant_enablement(env, 1, 'business.v1:payment.capital'),
                'active_snapshot_ids': snapshots.search([('product_key', '=', policy.product_key), ('state', '=', 'released'), ('is_active', '=', True)]).ids}
    before = state()
    if before['exempt'] or len(before['bindings']) != 1 or before['bindings'][0][1] != 'payment.capital':
        raise RuntimeError('Existing nonexempt scenario binding must remain intact')
    service = EditionReleaseSnapshotService(env)
    if phase == 'apply':
        for key in publication_params:
            params.set_param(key, env.cr.dbname)
    draft = service.build_policy_draft_contract(product_key=policy.product_key)
    report = {'phase': phase, 'database': env.cr.dbname, 'before': before,
              'preflight': draft['preflight_checks'], 'blocking_issue_count': draft['blocking_issue_count'],
              'policy_id': policy.id, 'publication_actor_uid': env.uid, 'activation_actor_uid': maintainer.id}
    print('PAYMENT_CONFIG_BEFORE=' + json.dumps(report, ensure_ascii=False, default=str), flush=True)
    if phase == 'plan':
        env.cr.rollback()
        return report
    if draft['blocking_issue_count']:
        raise RuntimeError('Publication preflight blocked; no configuration written')
    if not before['active_snapshot_ids']:
        policy.action_freeze_candidate()
        snapshot = snapshots.search([('source_policy_id', '=', policy.id), ('version', '=', policy.version or 'v1')], order='id desc', limit=1)
        service.assert_candidate_matches_current_draft(snapshot)
        service.assert_frozen_release_integrity(snapshot)
        publish_frozen_snapshot(snapshot)
    if not before['enabled']:
        result = ScenarioActivationSetHandler(actor).handle({'scene_key': 'payment.capital',
            'enablement_scope': 'business.v1', 'company_id': 1, 'enabled': True})
        if result.get('ok') is not True:
            raise RuntimeError('Formal activation rejected: %s' % result)
    after = state()
    if (not unchanged_boundaries(before, after) or not after['enabled'] or not after['active_snapshot_ids']
            or any(value != env.cr.dbname for value in after['publication_parameters'].values())):
        raise RuntimeError('Configuration readback or preserved boundaries failed')
    # Use the same non-sudo product route as the consumer, before commit. A
    # stale/missing target snapshot must roll back, even if enablement is true.
    from odoo.addons.smart_core.handlers.system_init import _load_platform_release_gate
    from odoo.addons.smart_core.handlers.route_authority_validate import RouteAuthorityValidateHandler
    principal = api.Environment(env.cr, user.id, {**env.context, 'allowed_company_ids': [1]}, su=False)
    gate = _load_platform_release_gate(principal, product_key=policy.product_key)
    route = RouteAuthorityValidateHandler(principal).handle({'action_id': menu.action.id, 'menu_id': menu.id}).to_legacy_dict()
    assert_entry_ready(gate, route, after['active_snapshot_ids'], menu.id, menu.action.id)
    report['entry_readback'] = {'snapshot_id': gate['snapshot_id'], 'uid': principal.uid,
                               'su': principal.su, 'company_id': 1, 'route': route}
    env.cr.commit()
    return {**report, 'after': after, 'status': 'passed', 'unchanged_boundaries': True}


if 'env' in globals():
    try:
        print('PAYMENT_CONFIG_RESULT=' + json.dumps(configure(env), ensure_ascii=False, default=str))
    except Exception:
        env.cr.rollback()
        raise
