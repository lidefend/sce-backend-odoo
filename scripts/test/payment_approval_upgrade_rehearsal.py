"""Bounded persistent phases inside one fresh, locked local.test attempt.

The host runner owns installation and two actual -u processes. This script uses
formal ORM/Form operations only; it never upgrades, pays or cancels anything.
"""
import base64
import json
import os

from odoo import api
from odoo.tests.common import Form
from odoo.addons.smart_construction_core.tests.business_case import BusinessTransactionCase

KEY = 'sc_test.approval_step_upgrade_rehearsal'
POLICY = 'smart_construction_core.approval_policy_payment_request'


def snapshot(policy):
    rows = policy.with_context(active_test=False).step_ids.sorted(lambda s: (s.sequence, s.id)).read(
        ['sequence', 'approval_scope_key', 'approve_group_id', 'amount_min', 'amount_max', 'active', 'tier_definition_id'])
    # ORM many2one reads are tuples; persisted JSON is arrays. Compare stable
    # identities, not Python transport shape or translated display names.
    return [{**row, **{key: row[key][0] if row[key] else False
                      for key in ('approve_group_id', 'tier_definition_id')}} for row in rows]


def instance(request):
    rows = request.review_ids.sorted('sequence').read(['sequence', 'definition_id', 'status', 'reviewer_group_id'])
    return {'id': request.id, 'state': request.state,
            'reviews': [{**row, **{key: row[key][0] if row[key] else False
                                  for key in ('definition_id', 'reviewer_group_id')}} for row in rows]}


def new_request(env, state, suffix):
    request = env['payment.request'].create({
        'name': 'UPGRADE-ORDER-' + suffix, 'type': 'pay', 'contract_id': state['contract_id'], 'amount': 100.0,
    })
    env['ir.attachment'].create({'name': 'upgrade-order-test.txt', 'type': 'binary',
        'datas': base64.b64encode(b'synthetic approval upgrade test'),
        'res_model': request._name, 'res_id': request.id, 'mimetype': 'text/plain'})
    actor_request = request.with_user(state['users']['finance_user'])
    assert not actor_request.env.su
    actor_request.action_submit()
    assert request.state == 'submit' and len(request.review_ids) == 4
    return request


def approve_in_order(request, policy, state, expected_groups):
    assert request.review_ids.sorted('sequence').mapped('reviewer_group_id').ids == expected_groups
    users_by_group = {group: state['users'][scope] for scope, group in state['groups'].items()}
    transitions = []
    for index, group in enumerate(expected_groups):
        before = {row.id for row in request.review_ids if row.status == 'approved'}
        actor = request.with_user(users_by_group[group])
        assert not actor.env.su and actor.can_review
        actor.action_approval_decision()
        request.invalidate_recordset()
        after = {row.id for row in request.review_ids if row.status == 'approved'}
        completed = request.review_ids.filtered(lambda row: row.id in after - before)
        assert len(completed) == 1 and completed.reviewer_group_id.id == group, request.review_ids.read(['sequence', 'status', 'reviewer_group_id'])
        assert completed.sequence == index + 1
        transitions.append({'sequence': completed.sequence, 'group_id': group,
                            'uid': actor.env.uid, 'su': actor.env.su, 'state': request.state})
    assert request.state == 'approved' and request.validation_status == 'validated'
    assert not request.payment_execution_ids
    return transitions


def run(env):
    if (env.cr.dbname != 'sc_test' or os.environ.get('SC_ENVIRONMENT') != 'test'
            or os.environ.get('SC_TEST_UPGRADE_REHEARSAL') != 'payment_approval_order'):
        raise RuntimeError('Only the governed fresh local.test upgrade attempt may run this fixture')
    phase = os.environ.get('SC_APPROVAL_UPGRADE_PHASE')
    assert phase in ('prepare', 'after_upgrade_1', 'after_upgrade_2')
    params = env['ir.config_parameter'].sudo()
    if phase == 'prepare':
        assert not params.get_param(KEY), 'fixture must start from a fresh database'
        policy = env.ref(POLICY)
        expected = [scope for _, scope in policy.USER_VISIBLE_APPROVAL_TEMPLATES[policy.code]['steps']]
        assert policy.step_ids.sorted('sequence').mapped('approval_scope_key') == expected
        company = env['res.company'].create({'name': 'Synthetic approval upgrade rehearsal'})
        BusinessTransactionCase.register_business_company(company)
        env = api.Environment(env.cr, env.uid, {**env.context, 'allowed_company_ids': company.ids}, su=True)
        policy = env.ref(POLICY)
        # Fixture ownership only: use the real default policy identity in the
        # registered synthetic company so the upgrade's code lookup is covered.
        policy.write({'company_id': company.id})
        state = {'company_id': company.id, 'users': {}, 'groups': {}, 'before': snapshot(policy)}
        for step in policy.step_ids:
            scope = step.approval_scope_key
            group_ids = {env.ref('base.group_user').id,
                         env.ref('smart_core.group_smart_core_finance_approver').id,
                         env.ref('smart_construction_core.group_sc_cap_finance_user').id,
                         step.approve_group_id.id}
            user = env['res.users'].with_context(no_reset_password=True).create({
                'name': 'Upgrade reviewer ' + scope, 'login': 'upgrade.reviewer.' + scope,
                'company_id': company.id, 'company_ids': [(6, 0, company.ids)],
                'groups_id': [(6, 0, sorted(group_ids))],
            })
            state['users'][scope] = user.id
            state['groups'][scope] = step.approve_group_id.id
        maintainer = env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Upgrade configuration maintainer', 'login': 'upgrade.config.maintainer',
            'company_id': company.id, 'company_ids': [(6, 0, company.ids)],
            'groups_id': [(6, 0, [env.ref('base.group_user').id,
                env.ref('smart_construction_core.group_sc_cap_business_config_admin').id])],
        })
        state['maintainer_uid'] = maintainer.id
        project = env['project.project'].create({'name': 'Upgrade order test project',
            'company_id': company.id, 'funding_enabled': True,
            'user_id': state['users']['finance_user'], 'manager_id': state['users']['project_manager']})
        project.message_subscribe(partner_ids=env['res.users'].browse(list(state['users'].values())).mapped('partner_id').ids)
        baseline = env['project.funding.baseline'].create({'project_id': project.id, 'total_amount': 10000,
            'period_start': '2020-01-01', 'period_end': '2099-12-31',
            'line_ids': [(0, 0, {'name': 'Synthetic funding plan', 'planned_amount': 10000})]})
        baseline.action_activate()
        partner = env['res.partner'].create({'name': 'Synthetic upgrade vendor', 'supplier_rank': 1,
            'sc_account_name': 'Synthetic upgrade vendor', 'sc_bank_name': 'Synthetic bank',
            'sc_bank_account': 'SYNTHETIC-UPGRADE-ACCOUNT'})
        contract = env['construction.contract'].create({'subject': 'Synthetic upgrade contract', 'type': 'in',
            'project_id': project.id, 'partner_id': partner.id})
        state['contract_id'] = contract.id
        inflight = new_request(env, state, 'INFLIGHT')
        state['inflight'] = instance(inflight)
        state['original_groups'] = inflight.review_ids.sorted('sequence').mapped('reviewer_group_id').ids
        editable = policy.with_user(maintainer)
        assert not editable.env.su
        # Same native view and one2many edit as 审批规则 → 步骤, not sudo SQL.
        with Form(editable, view='smart_construction_core.view_sc_approval_policy_form') as form:
            with form.step_ids.edit(0) as step:
                step.sequence = 25
        state['maintained'] = snapshot(policy)
        assert state['maintained'][0]['approval_scope_key'] == 'project_manager'
        assert sorted(row['id'] for row in state['before']) == sorted(row['id'] for row in state['maintained'])
        state['maintained_groups'] = policy.step_ids.sorted('sequence').mapped('approve_group_id').ids
    else:
        state = json.loads(params.get_param(KEY))
        env = api.Environment(env.cr, env.uid, {**env.context, 'allowed_company_ids': [state['company_id']]}, su=True)
        policy = env.ref(POLICY)
        assert snapshot(policy) == state['maintained'], {'reason': 'upgrade configuration mismatch', 'expected': state['maintained'], 'actual': snapshot(policy)}
        inflight = env['payment.request'].browse(state['inflight']['id'])
    assert instance(inflight) == state['inflight'], 'in-flight review instance was reordered or rewritten'
    request = new_request(env, state, phase)
    trace = approve_in_order(request, policy, state, state['maintained_groups'])
    assert instance(inflight) == state['inflight']
    report = {'phase': phase, 'status': 'passed', 'database': env.cr.dbname,
              'maintenance_uid': state['maintainer_uid'], 'maintenance_su': False,
              'before': state['before'], 'maintained': state['maintained'], 'after': snapshot(policy),
              'inflight_unchanged': True, 'inflight': state['inflight'],
              'new_request_id': request.id, 'approval_trace': trace, 'new_request_state': request.state}
    if phase == 'after_upgrade_2':
        report['original_instance_trace'] = approve_in_order(inflight, policy, state, state['original_groups'])
    params.set_param(KEY, json.dumps(state))
    env.cr.commit()
    print('APPROVAL_UPGRADE_EVIDENCE=' + json.dumps(report, ensure_ascii=False), flush=True)


try:
    run(env)
except Exception:
    env.cr.rollback()
    raise
