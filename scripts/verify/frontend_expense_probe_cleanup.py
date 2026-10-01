"""Exact transient browser document cleanup; never fixture provisioning."""
import base64
import hashlib
import json
import os
import re
from datetime import datetime, timezone


def validate_payment_review_probe_target(database, scope, row):
    """Authorize only this run's pre-cash execution for eventual recovery."""
    assert database == 'sc_frontend_acceptance' and scope['model'] == 'sc.payment.execution'
    assert scope['source'] == {'id': 1710, 'company_id': 8}
    marker = scope['marker']
    assert re.fullmatch(r'TPL53-PAYMENT-REVIEW-\d{13}', marker)
    assert 186 in scope['baseline']['execution_ids']
    assert isinstance(row['id'], int) and row['id'] > 0 and row['id'] not in scope['baseline']['execution_ids']
    assert row['note'] == marker and row['payment_request_id'] == 1710
    assert row['company_id'] == 8 and row['create_uid'] == 44 and row['paid_amount'] == 1
    assert row['source_origin'] != 'legacy' and row['state'] in ('draft', 'confirmed')
    if scope.get('id'):
        assert row['id'] == scope['id']
    assert scope['phase'] in ('create_in_flight', 'created', 'submit', 'submit_in_flight',
                              'submitted', 'approve', 'approve_in_flight', 'done')
    if row['state'] == 'confirmed':
        assert scope['phase'] in ('approve_in_flight', 'done')
        assert row['validation_status'] == 'validated'
        assert scope['origin']['source'] == 'tier.review' and scope['origin']['id'] in row['review_ids']
        assert row['reviewer_ids'] == [30]
    started = int(marker.rsplit('-', 1)[1]) / 1000
    created = datetime.fromisoformat(row['create_date']).replace(tzinfo=timezone.utc).timestamp()
    assert -5 <= created - started <= 300


def payment_review_baseline(env, exclude_ids=()):
    source = env['payment.request'].sudo().browse(1710).exists()
    assert source and source.company_id.id == 8 and source.type == 'pay' and source.state == 'approved'
    executions = env['sc.payment.execution'].sudo().with_context(active_test=False).search([
        ('payment_request_id', '=', 1710), ('id', 'not in', list(exclude_ids))], order='id')
    assert 186 in executions.ids
    facts = {
        'source': source.read(['state', 'company_id', 'project_id', 'partner_id', 'amount',
                               'paid_amount_total', 'unpaid_amount', 'terminal_cash_source_model', 'terminal_cash_source_res_id']),
        'execution_ids': executions.ids,
        'executions': executions.read(['write_date', 'state', 'paid_amount', 'active']),
        'reviews': env['tier.review'].sudo().search([('model', '=', 'sc.payment.execution'),
                    ('res_id', 'in', executions.ids)], order='id').read(['write_date', 'status', 'done_by']),
        'ledger': env['payment.ledger'].sudo().search([('payment_request_id', '=', 1710)], order='id').read(['write_date']),
    }
    Policy = env['sc.approval.policy'].sudo().with_context(active_test=False)
    policies = Policy.search([('target_model', '=', 'sc.payment.execution'), ('company_id', 'in', [False, 8])], order='id')
    assert 18 in policies.ids
    facts['policies'] = policies.read(['write_date', 'approval_required', 'active'])
    facts['steps'] = policies.step_ids.sorted('id').read(['write_date', 'active'])
    facts['definitions'] = env['tier.definition'].sudo().with_context(active_test=False).search([
        ('model', '=', 'sc.payment.execution')], order='id').read(['write_date'])
    actions = [env.ref(ref).sudo() for ref in Policy._tier_server_action_xmlids('sc.payment.execution')]
    facts['callbacks'] = [{'id': action.id, 'groups': sorted(action.groups_id.ids)} for action in actions]
    return json.loads(json.dumps(facts, default=str))


def recover_payment_review(env, scope, *, commit=True):
    assert env.cr.dbname == 'sc_frontend_acceptance' and scope['model'] == 'sc.payment.execution'
    assert scope['source'] == {'id': 1710, 'company_id': 8}
    assert re.fullmatch(r'TPL53-PAYMENT-REVIEW-\d{13}', scope['marker'])
    for uid, login in ((30, 'fixture_role_finance'), (44, 'fixture_role_pfl035_finance_user')):
        user = env['res.users'].sudo().browse(uid)
        assert user.active and user.login == login and user.company_id.id == 8
    records = env['sc.payment.execution'].sudo().with_context(active_test=False).search([('note', '=', scope['marker'])])
    assert len(records) <= 1
    if scope.get('baseline') is None:
        assert scope['phase'] == 'prepare' and not records and not scope.get('id')
        baseline = payment_review_baseline(env)
        assert not any(row['state'] in ('draft', 'confirmed') for row in baseline['executions'])
        print('EXPENSE_BROWSER_CLEANUP=' + json.dumps({'status': 'preflight', 'baseline': baseline}))
        return baseline
    baseline = scope['baseline']
    assert payment_review_baseline(env, records.ids) == baseline, 'source/configuration/original financial facts changed'
    ids = records.ids
    for record in records:
        row = {key: record[key] for key in ('id', 'note', 'state', 'paid_amount', 'source_origin', 'validation_status')}
        row.update({key: record[key].id for key in ('payment_request_id', 'company_id', 'create_uid')})
        row.update(create_date=str(record.create_date), review_ids=record.review_ids.ids,
                   reviewer_ids=sorted(set(record.review_ids.filtered(lambda r: r.status == 'approved').mapped('done_by').ids)))
        validate_payment_review_probe_target(env.cr.dbname, scope, row)
        assert not env['ir.attachment'].sudo().search_count([('res_model', '=', record._name), ('res_id', '=', record.id)])
        definitions = {row['id'] for row in baseline['definitions']}
        for review in record.review_ids:
            assert review.model == record._name and review.res_id == record.id and review.requested_by.id == 44
            assert review.definition_id.id in definitions and review.status in ('waiting', 'pending', 'approved')
            assert not review.done_by or (review.status == 'approved' and review.done_by.id == 30)
    # All ownership and unchanged-baseline checks precede deletion. Native unlink removes own tier reviews.
    review_ids = records.mapped('review_ids').ids
    records.unlink()
    assert not records.exists() and not env['tier.review'].sudo().browse(review_ids).exists()
    assert payment_review_baseline(env) == baseline
    if commit:
        env.cr.commit()
        env.invalidate_all()
        assert payment_review_baseline(env) == baseline
        assert not env['sc.payment.execution'].sudo().browse(ids).exists()
    print('EXPENSE_BROWSER_CLEANUP=' + json.dumps({'status': 'restored', 'record_ids': ids, 'review_ids': review_ids}))


def validate_expense_probe_target(database, scope, row):
    assert database == 'sc_frontend_acceptance'
    marker = scope['request']['vals']['summary']
    assert re.fullmatch(r'TPL53-EXPENSE-SUCCESS-\d{13}', marker)
    vals, source = scope['request']['vals'], scope['source']
    assert row['summary'] == marker and row['create_uid'] == 30 and row['company_id'] == 8
    assert row['source_origin'] != 'legacy' and row['state'] in ('draft', 'submit', 'approved')
    assert row['project_id'] == vals['project_id'] == source['project_id'][0]
    assert row['partner_id'] == vals['partner_id'] == source['partner_id'][0]
    assert row['payment_request_id'] == vals['payment_request_id'] == source['id']
    assert row['amount'] == vals['amount'] == source['amount']
    assert row['payee_account'] == vals['payee_account'] == 'EXPENSE-SAVE-PAYEE'
    assert row['payer_account'] == vals['payer_account'] == 'EXPENSE-SAVE-PAYER'
    if scope.get('id'):
        assert row['id'] == scope['id']
    started = int(marker.rsplit('-', 1)[1]) / 1000
    created = datetime.fromisoformat(row['create_date']).replace(tzinfo=timezone.utc).timestamp()
    assert -5 <= created - started <= 300, 'record predates or exceeds this bounded browser run'


def expense_probe_attachment_checksums(scope):
    files = scope.get('files')
    if files is None:
        files = [{'name': scope['filename'], 'data': scope['data']}]
    else:
        assert isinstance(files, list) and len(files) == 2
        assert files[0] == {'name': scope['filename'], 'data': scope['data']}
        assert files[1] == {'name': 'tpl53-partial-second.txt',
                            'data': base64.b64encode(b'Rollback-only second attachment').decode()}
    assert len({f['name'] for f in files}) == len(files)
    return {f['name']: hashlib.sha1(base64.b64decode(f['data'], validate=True)).hexdigest() for f in files}


def validate_diary_probe_target(database, scope, row, actor_id):
    assert database == 'sc_frontend_acceptance' and scope['model'] == 'sc.construction.diary'
    vals = scope['request']['vals']
    assert re.fullmatch(r'TPL53-DIARY-SAVE-\d{13}', vals['title'])
    assert set(vals) == {'project_id', 'title', 'description'} and vals['project_id'] == 10
    assert scope['request']['context']['company_id'] == 8
    assert row['title'] == vals['title'] and row['description'] == vals['description']
    assert row['project_id'] == 10 and row['company_id'] == 8 and row['create_uid'] == actor_id
    assert row['source_origin'] == 'manual' and row['state'] in ('draft', 'confirmed')
    if scope.get('id'):
        assert row['id'] == scope['id']
    started = int(vals['title'].rsplit('-', 1)[1]) / 1000
    created = datetime.fromisoformat(row['create_date']).replace(tzinfo=timezone.utc).timestamp()
    assert -5 <= created - started <= 300


def recover_diary(env, scope):
    assert env.cr.dbname == 'sc_frontend_acceptance' and scope['model'] == 'sc.construction.diary'
    actor = env['res.users'].sudo().search([('login', '=', 'fixture_role_pm')])
    assert len(actor) == 1 and actor.company_id.id == 8
    vals = scope['request']['vals']
    assert set(vals) == {'project_id', 'title', 'description'} and vals['project_id'] == 10
    marker = vals['title']
    assert re.fullmatch(r'TPL53-DIARY-SAVE-\d{13}', marker)
    project = env['project.project'].sudo().browse(10).exists()
    assert project and project.company_id.id == 8
    # Do not change or bypass existing approval configuration for this probe.
    assert not env['sc.approval.policy'].sudo().search_count([
        ('target_model', '=', 'sc.construction.diary'), ('company_id', 'in', [False, 8]),
        ('approval_required', '=', True)])
    records = env['sc.construction.diary'].sudo().with_context(active_test=False).search([('title', '=', marker)])
    assert len(records) <= 1
    ids = records.ids
    for record in records:
        row = {key: record[key] for key in ('id', 'title', 'description', 'source_origin', 'state')}
        row.update({key: record[key].id for key in ('create_uid', 'company_id', 'project_id')})
        row['create_date'] = str(record.create_date)
        validate_diary_probe_target(env.cr.dbname, scope, row, actor.id)
        assert not record.review_ids and not record.attachment_ids
        assert not env['ir.attachment'].sudo().search_count([('res_model', '=', record._name), ('res_id', '=', record.id)])
        record.unlink()
    env.cr.commit()
    env.invalidate_all()
    assert not env['sc.construction.diary'].sudo().with_context(active_test=False).search_count([('title', '=', marker)])
    print('EXPENSE_BROWSER_CLEANUP=' + json.dumps({'status': 'restored', 'model': scope['model'], 'record_ids': ids, 'actor_id': actor.id}))


def validate_event_probe_target(database, scope, row, actor_id):
    assert database == 'sc_frontend_acceptance' and scope['model'] == 'sc.contract.event'
    vals = scope['request']['vals']
    assert re.fullmatch(r'TPL53-EVENT-SAVE-\d{13}', vals['name'])
    assert set(vals) == {'project_id', 'name', 'description', 'event_type'} and vals['project_id'] == scope['projectId'] and isinstance(scope['projectId'], int) and scope['projectId'] > 0
    assert scope['request']['context']['company_id'] == 8
    assert row['name'] == vals['name'] and row['description'] == vals['description']
    assert row['project_id'] == scope['projectId'] and row['company_id'] == 8 and row['create_uid'] == actor_id
    assert row['event_type'] == vals['event_type'] == 'design_change' and row['state'] in ('draft', 'approved')
    if scope.get('id'):
        assert row['id'] == scope['id']
    started = int(vals['name'].rsplit('-', 1)[1]) / 1000
    created = datetime.fromisoformat(row['create_date']).replace(tzinfo=timezone.utc).timestamp()
    assert -5 <= created - started <= 300


def recover_event(env, scope):
    assert env.cr.dbname == 'sc_frontend_acceptance' and scope['model'] == 'sc.contract.event'
    actor = env['res.users'].sudo().search([('login', '=', 'fixture_role_contract_operator')])
    assert len(actor) == 1 and actor.company_id.id == 8
    vals = scope['request']['vals']
    assert set(vals) == {'project_id', 'name', 'description', 'event_type'} and vals['project_id'] == scope['projectId'] and isinstance(scope['projectId'], int) and scope['projectId'] > 0
    marker = vals['name']
    assert re.fullmatch(r'TPL53-EVENT-SAVE-\d{13}', marker)
    project = env['project.project'].sudo().browse(scope['projectId']).exists()
    assert project and project.company_id.id == 8
    # Do not change or bypass existing approval configuration for this probe.
    assert not env['sc.approval.policy'].sudo().search_count([
        ('target_model', '=', 'sc.contract.event'), ('company_id', 'in', [False, 8]),
        ('approval_required', '=', True)])
    records = env['sc.contract.event'].sudo().with_context(active_test=False).search([('name', '=', marker)])
    assert len(records) <= 1
    ids = records.ids
    for record in records:
        row = {key: record[key] for key in ('id', 'name', 'description', 'event_type', 'state')}
        row.update({key: record[key].id for key in ('create_uid', 'company_id', 'project_id')})
        row['create_date'] = str(record.create_date)
        validate_event_probe_target(env.cr.dbname, scope, row, actor.id)
        assert not record.contract_id and not record.settlement_included and not record.legacy_fact_id
        assert not record.review_ids and not record.attachment_ids
        assert not env['ir.attachment'].sudo().search_count([('res_model', '=', record._name), ('res_id', '=', record.id)])
        record.unlink()
    env.cr.commit()
    env.invalidate_all()
    assert not env['sc.contract.event'].sudo().with_context(active_test=False).search_count([('name', '=', marker)])
    print('EXPENSE_BROWSER_CLEANUP=' + json.dumps({'status': 'restored', 'model': scope['model'], 'record_ids': ids, 'actor_id': actor.id}))


def validate_report_probe_target(database, scope, row, actor_id, parent=False):
    assert database == 'sc_frontend_acceptance' and scope['model'] == 'sc.plan.report'
    marker = scope['marker']
    assert re.fullmatch(r'TPL53-REPORT-SAVE-\d{13}', marker)
    assert row['company_id'] == 8 and row['create_uid'] == actor_id
    assert row['name'] == (marker.replace('REPORT-SAVE', 'REPORT-PARENT') if parent else marker)
    if parent:
        assert row['project_id'] == 10
        assert row['state'] in (('draft', 'confirmed', 'in_progress', 'done') if scope.get('planExecutionProbe') else ('draft',))
        if scope.get('parentId'): assert row['id'] == scope['parentId']
    else:
        assert set(scope['request']['vals']) == {'name', 'plan_id', 'summary'}
        assert scope['request']['context']['company_id'] == 8
        assert scope['request']['vals']['name'] == marker and scope['request']['vals']['plan_id'] == scope['parentId']
        assert row['plan_id'] == scope['parentId'] and row['state'] in ('draft', 'accepted')
        assert row['summary'] == scope['request']['vals']['summary']
        if scope.get('id'): assert row['id'] == scope['id']
    started = int(marker.rsplit('-', 1)[1]) / 1000
    created = datetime.fromisoformat(row['create_date']).replace(tzinfo=timezone.utc).timestamp()
    assert -5 <= created - started <= 300


def validate_version_probe_target(database, scope, row, actor_id):
    assert database == 'sc_frontend_acceptance' and scope.get('versionProbe') is True
    marker = scope['marker']
    assert scope['model'] == 'sc.plan.report' and re.fullmatch(r'TPL53-REPORT-SAVE-\d{13}', marker)
    assert row['version_no'] == marker.replace('REPORT-SAVE', 'VERSION-SAVE')
    assert row['plan_id'] == scope['parentId'] and row['company_id'] == 8 and row['create_uid'] == actor_id
    assert row['revision_type'] == 'adjustment'
    if row['state'] != 'draft':
        assert row['state'] == 'approved' and scope.get('versionSubmitProbe') is True
        phases = ('version-submit_in_flight', 'done', 'version-approve_in_flight') if scope.get('versionReviewProbe') else ('version-submit_in_flight', 'done')
        assert scope.get('phase') in phases and scope.get('versionId') == row['id']
        if scope.get('versionReviewProbe'):
            assert row.get('approved_by') == scope['approvalBaseline']['reviewer_id']
        else:
            assert not row.get('approved_by')
        assert row.get('approved_date') == scope['versionDefaults']['version_date']
    assert row['version_date'] == scope['versionDefaults']['version_date']
    if scope.get('versionId'): assert row['id'] == scope['versionId']
    started = int(marker.rsplit('-', 1)[1]) / 1000
    created = datetime.fromisoformat(row['create_date']).replace(tzinfo=timezone.utc).timestamp()
    assert -5 <= created - started <= 300


def validate_plan_node_probe_target(database, scope, row, actor_id):
    assert database == 'sc_frontend_acceptance' and scope.get('planExecutionProbe') is True and not scope.get('versionProbe')
    marker = scope['marker']
    assert scope['model'] == 'sc.plan.report' and re.fullmatch(r'TPL53-REPORT-SAVE-\d{13}', marker)
    assert row['name'] == marker.replace('REPORT-SAVE', 'PLAN-NODE')
    assert row['plan_id'] == scope['parentId'] and row['create_uid'] == actor_id
    if scope.get('nodeId'): assert row['id'] == scope['nodeId']
    assert (row['state'], row['progress_rate']) in (('draft', 0), ('in_progress', 50), ('done', 100))
    started = int(marker.rsplit('-', 1)[1]) / 1000
    created = datetime.fromisoformat(row['create_date']).replace(tzinfo=timezone.utc).timestamp()
    assert -5 <= created - started <= 300


def validate_version_review_policy(database, scope, row):
    assert database == 'sc_frontend_acceptance' and scope.get('versionReviewProbe') is True
    assert scope.get('model') == 'sc.plan.report' and type(row['id']) is int and row['id'] > 0
    assert scope.get('versionProbe') is True and scope.get('versionSubmitProbe') is True
    assert not scope.get('planExecutionProbe')
    assert re.fullmatch(r'TPL53-REPORT-SAVE-\d{13}', scope['marker'])
    assert row['code'] == 'low_code_sc_plan_version_company_8'
    assert row['target_model'] == 'sc.plan.version' and row['company_id'] == 8 and row['create_uid'] == 34
    assert row['approval_required'] is True and row['mode'] == 'single' and row['trigger'] == 'submit'
    assert row['manager_scope_key'] == 'executive' and row['active'] is True
    if scope.get('approvalPolicyId'):
        assert row['id'] == scope['approvalPolicyId']
    started = int(scope['marker'].rsplit('-', 1)[1]) / 1000
    created = datetime.fromisoformat(row['create_date']).replace(tzinfo=timezone.utc).timestamp()
    assert -5 <= created - started <= 300


def version_review_recovery_bundle(env, scope):
    Policy = env['sc.approval.policy'].sudo().with_context(active_test=False)
    Definition = env['tier.definition'].sudo().with_context(active_test=False)
    policies = Policy.search([('target_model', '=', 'sc.plan.version')])
    definitions = Definition.search([('model', '=', 'sc.plan.version')])
    reviewer = env['res.users'].sudo().search([('login', '=', 'fixture_role_executive')])
    assert len(reviewer) == 1 and reviewer.active and reviewer.company_id.id == 8
    admin = env['res.users'].sudo().search([('login', '=', 'fixture_role_config_admin')])
    assert len(admin) == 1 and admin.id == 34 and admin.company_id.id == 8
    group = Policy._group_for_approval_scope('executive')
    assert group and group in reviewer.groups_id
    actions = [env.ref(xmlid).sudo() for xmlid in Policy._tier_server_action_xmlids('sc.plan.version')]
    baseline = scope.get('approvalBaseline')
    if baseline is None:
        assert not policies and not definitions
        assert not env['sc.plan'].sudo().search_count([('name', '=', scope['parentRequest']['vals']['name'])])
        return {'baseline': {'reviewer_id': reviewer.id, 'definition_ids': definitions.ids,
                            'actions': [{'id': action.id, 'groups': sorted(action.groups_id.ids)} for action in actions]}}
    assert baseline['reviewer_id'] == reviewer.id
    assert [row['id'] for row in baseline['actions']] == [action.id for action in actions]
    assert len(policies) <= 1
    for policy in policies:
        row = policy.read(['code', 'target_model', 'approval_required', 'mode', 'trigger', 'manager_scope_key', 'active', 'create_date'])[0]
        row.update(company_id=policy.company_id.id, create_uid=policy.create_uid.id, create_date=str(policy.create_date))
        validate_version_review_policy(env.cr.dbname, scope, row)
    steps = policies.with_context(active_test=False).step_ids
    assert all(step.approve_group_id == group and not step.amount_min and not step.amount_max
               and not step.condition_note and not step.note for step in steps)
    assert len(steps) <= 2 and len(steps.filtered('active')) <= 1
    owned_definitions = steps.tier_definition_id
    assert set(definitions.ids) == set(baseline['definition_ids']) | set(owned_definitions.ids)
    assert set(baseline['definition_ids']).isdisjoint(owned_definitions.ids)
    assert not env['sc.approval.step'].sudo().with_context(active_test=False).search_count([
        ('tier_definition_id', 'in', owned_definitions.ids), ('policy_id', 'not in', policies.ids)])
    for action, saved in zip(actions, baseline['actions']):
        assert sorted(action.groups_id.ids) in (saved['groups'], [group.id]), 'callback permissions changed outside this probe'
    reviews = env['tier.review'].sudo().search([('definition_id', 'in', owned_definitions.ids)])
    return {'policies': policies, 'steps': steps, 'definitions': owned_definitions,
            'reviews': reviews, 'actions': actions, 'baseline': baseline}


def restore_version_review_bundle(env, bundle):
    bundle['reviews'].unlink()
    bundle['steps'].with_context(skip_tier_sync=True).write({'active': False})
    bundle['steps'].with_context(skip_tier_sync=True).unlink()
    bundle['policies'].with_context(skip_tier_sync=True).write({'active': False})
    bundle['policies'].unlink()
    bundle['definitions'].unlink()
    for action, saved in zip(bundle['actions'], bundle['baseline']['actions']):
        action.write({'groups_id': [(6, 0, saved['groups'])]})


def assert_version_review_restored(env, baseline):
    assert not env['sc.approval.policy'].sudo().with_context(active_test=False).search_count([('target_model', '=', 'sc.plan.version')])
    assert set(env['tier.definition'].sudo().with_context(active_test=False).search([('model', '=', 'sc.plan.version')]).ids) == set(baseline['definition_ids'])
    for saved in baseline['actions']:
        assert sorted(env['ir.actions.server'].sudo().browse(saved['id']).groups_id.ids) == saved['groups']


def recover_report(env, scope):
    assert env.cr.dbname == 'sc_frontend_acceptance' and scope['model'] == 'sc.plan.report'
    marker = scope['marker']
    assert re.fullmatch(r'TPL53-REPORT-SAVE-\d{13}', marker)
    vals = scope['parentRequest']['vals']
    assert vals == {'name': marker.replace('REPORT-SAVE', 'REPORT-PARENT'), 'project_id': 10}
    assert scope['parentRequest']['context']['company_id'] == 8
    actor = env['res.users'].sudo().search([('login', '=', 'fixture_role_pm')])
    assert len(actor) == 1 and actor.company_id.id == 8
    assert env['project.project'].sudo().browse(10).company_id.id == 8
    review_bundle = None
    if scope.get('versionReviewProbe'):
        assert scope.get('versionProbe') and scope.get('versionSubmitProbe') and not scope.get('planExecutionProbe')
        review_bundle = version_review_recovery_bundle(env, scope)
        if 'policies' not in review_bundle:
            print('EXPENSE_BROWSER_CLEANUP=' + json.dumps({'status': 'restored', 'approval_baseline': review_bundle['baseline']}))
            return
    assert not env['sc.approval.policy'].sudo().search_count([
        ('target_model', '=', 'sc.plan.report'), ('company_id', 'in', [False, 8]), ('approval_required', '=', True)])
    if scope.get('planExecutionProbe'):
        assert not scope.get('versionProbe')
        assert not env['sc.approval.policy'].sudo().search_count([
            ('target_model', '=', 'sc.plan'), ('company_id', 'in', [False, 8]), ('approval_required', '=', True)])
    Node = env['sc.plan.line'].sudo()
    nodes = Node.search([('name', '=', marker.replace('REPORT-SAVE', 'PLAN-NODE'))])
    assert len(nodes) <= 1 and (not nodes or scope.get('planExecutionProbe') is True)
    node_ids = nodes.ids
    Plan = env['sc.plan'].sudo().with_context(active_test=False)
    Report = env['sc.plan.report'].sudo().with_context(active_test=False)
    Version = env['sc.plan.version'].sudo().with_context(active_test=False)
    if scope.get('versionSubmitProbe'):
        assert scope.get('versionProbe') is True
        assert review_bundle or not env['sc.approval.policy'].sudo().search_count([
            ('target_model', '=', 'sc.plan.version'), ('company_id', 'in', [False, 8]), ('approval_required', '=', True)])
    versions = Version.search([('version_no', '=', marker.replace('REPORT-SAVE', 'VERSION-SAVE'))])
    assert not versions or scope.get('versionProbe') is True
    assert len(versions) <= 1
    version_ids = versions.ids
    plans = Plan.search([('name', '=', vals['name'])])
    reports = Report.search([('name', '=', marker)])
    assert len(plans) <= 1 and len(reports) <= 1
    plan_ids, report_ids = plans.ids, reports.ids
    # Validate both records and every dependent before making either deletion.
    for record in plans:
        row = {key: record[key] for key in ('id', 'name', 'state')}
        row.update({key: record[key].id for key in ('company_id', 'create_uid', 'project_id')})
        row['create_date'] = str(record.create_date)
        validate_report_probe_target(env.cr.dbname, scope, row, actor.id, parent=True)
        assert set(record.line_ids.ids) == set(node_ids) and not record.review_ids and not record.attachment_ids
        assert set(record.version_ids.ids) == set(version_ids)
        assert set(record.report_ids.ids) == set(report_ids)
        assert not env['sc.plan.warning.log'].sudo().search_count([('plan_id', '=', record.id)])
    for record in reports:
        assert plans and record.plan_id == plans
        row = {key: record[key] for key in ('id', 'name', 'state', 'summary')}
        row.update({key: record[key].id for key in ('company_id', 'create_uid', 'plan_id')})
        row['create_date'] = str(record.create_date)
        validate_report_probe_target(env.cr.dbname, scope, row, actor.id)
        assert not record.line_id and not record.review_ids and not record.attachment_ids and not record.legacy_fact_id
    for record in versions:
        assert plans and record.plan_id == plans
        row = {key: record[key] for key in ('id', 'version_no', 'state', 'revision_type')}
        row.update({key: record[key].id for key in ('company_id', 'create_uid', 'plan_id')})
        row.update(create_date=str(record.create_date), version_date=str(record.version_date),
                   approved_date=str(record.approved_date) if record.approved_date else False, approved_by=record.approved_by.id)
        validate_version_probe_target(env.cr.dbname, scope, row, actor.id)
        assert not record.base_version_id
        if review_bundle:
            assert set(record.review_ids.ids) == set(review_bundle['reviews'].ids)
            for review in record.review_ids:
                assert review.model == record._name and review.res_id == record.id
                assert review.create_uid == actor and review.status in ('waiting', 'pending', 'approved')
                assert not review.done_by or review.done_by.id == review_bundle['baseline']['reviewer_id']
        else:
            assert not record.review_ids and not record.approved_by
        if record.state == "draft": assert not record.approved_date and not record.approved_by
        assert not record.legacy_fact_id and not Version.search_count([('base_version_id', '=', record.id)])
    for record in nodes:
        assert plans and record.plan_id == plans
        row = {key: record[key] for key in ('id', 'name', 'state', 'progress_rate')}
        row.update(plan_id=record.plan_id.id, create_uid=record.create_uid.id, create_date=str(record.create_date))
        validate_plan_node_probe_target(env.cr.dbname, scope, row, actor.id)
        assert not record.parent_id and not record.child_ids and not record.predecessor_ids and not record.linked_plan_line_id
        assert not record.contract_id and not record.deliverable_attachment_ids and not record.legacy_fact_id
        for field in ('parent_id', 'linked_plan_line_id', 'predecessor_ids'):
            assert not Node.search_count([(field, '=', record.id)])
        assert not Report.search_count([('line_id', '=', record.id)])
    for records in (nodes, versions, reports, plans):
        for record in records:
            assert not env['ir.attachment'].sudo().search_count([('res_model', '=', record._name), ('res_id', '=', record.id)])
    # All identities/dependencies above are checked before restoring this exact temporary fact.
    if review_bundle:
        assert set(review_bundle['reviews'].ids) == set(versions.review_ids.ids)
        restore_version_review_bundle(env, review_bundle)
    for record in versions.filtered(lambda row: row.state == 'approved'):
        record._write_document_state({'state': 'draft', 'approved_date': False, 'approved_by': False})
    if scope.get('planExecutionProbe'):
        plans._write_document_state({'state': 'draft', 'actual_start': False, 'actual_finish': False})
    nodes.unlink()
    versions.unlink()
    reports.unlink()
    plans.unlink()
    env.cr.commit()
    env.invalidate_all()
    assert not Plan.search_count([('name', '=', vals['name'])]) and not Report.search_count([('name', '=', marker)])
    assert not Version.search_count([('version_no', '=', marker.replace('REPORT-SAVE', 'VERSION-SAVE'))])
    assert not Node.search_count([('name', '=', marker.replace('REPORT-SAVE', 'PLAN-NODE'))])
    if review_bundle:
        assert_version_review_restored(env, review_bundle['baseline'])
    print('EXPENSE_BROWSER_CLEANUP=' + json.dumps({'status': 'restored', 'model': scope['model'], 'record_ids': report_ids, 'version_ids': version_ids, 'node_ids': node_ids, 'parent_ids': plan_ids, 'actor_id': actor.id}))


def recover(env, scope):
    if scope.get("model") == "sc.payment.execution":
        return recover_payment_review(env, scope)
    if scope.get("model") == "sc.plan.report":
        return recover_report(env, scope)
    if scope.get("model") == "sc.contract.event":
        return recover_event(env, scope)
    if scope.get('model') == 'sc.construction.diary':
        return recover_diary(env, scope)
    assert env.cr.dbname == 'sc_frontend_acceptance'
    finance = env['res.users'].sudo().browse(30)
    assert finance.login == 'fixture_role_finance' and finance.company_id.id == 8
    expected_files = expense_probe_attachment_checksums(scope)
    vals = scope['request']['vals']
    marker = vals['summary']
    assert re.fullmatch(r'TPL53-EXPENSE-SUCCESS-\d{13}', marker)
    source = env['payment.request'].sudo().browse(scope['source']['id']).with_context(lang='zh_CN')
    assert json.loads(json.dumps(source.read(list(scope['source']))[0])) == scope['source']
    assert not source.terminal_cash_source_model
    assert not env['payment.ledger'].sudo().search_count([('payment_request_id', '=', source.id)])
    records = env['sc.expense.claim'].sudo().with_context(active_test=False).search([('summary', '=', marker)])
    assert len(records) <= 1
    attachment_ids, record_ids = [], records.ids
    for record in records:
        row = {key: record[key] for key in ['id', 'summary', 'source_origin', 'state', 'amount', 'payee_account', 'payer_account']}
        row.update({key: record[key].id for key in ['create_uid', 'company_id', 'project_id', 'partner_id', 'payment_request_id']})
        row['create_date'] = str(record.create_date)
        validate_expense_probe_target(env.cr.dbname, scope, row)
        assert not env['sc.treasury.ledger'].sudo().search_count([('source_model', '=', record._name), ('source_res_id', '=', record.id)])
        attachments = env['ir.attachment'].sudo().search([('res_model', '=', record._name), ('res_id', '=', record.id)])
        assert len(attachments) <= len(expected_files)
        assert len(set(attachments.mapped('name'))) == len(attachments)
        assert all(a.create_uid == finance and a.name in expected_files
                   and a.checksum == expected_files[a.name] for a in attachments)
        assert set(record.attachment_ids.ids) <= set(attachments.ids)
        attachment_ids = attachments.ids
        record.unlink()
        attachments.exists().unlink()
    assert not records.exists() and not env['ir.attachment'].sudo().browse(attachment_ids).exists()
    env.cr.commit()
    env.invalidate_all()
    assert not env['sc.expense.claim'].sudo().search_count([('summary', '=', marker)])
    assert not env['ir.attachment'].sudo().browse(attachment_ids).exists()
    assert json.loads(json.dumps(source.read(list(scope['source']))[0])) == scope['source']
    print('EXPENSE_BROWSER_CLEANUP=' + json.dumps({'status': 'restored', 'record_ids': record_ids, 'attachment_ids': attachment_ids, 'source_id': source.id}))


if 'env' in globals():
    recover(env, json.loads(os.environ['SC_EXPENSE_CREATE_PROBE_JSON']))
