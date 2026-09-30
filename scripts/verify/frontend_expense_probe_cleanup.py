"""Exact transient browser document cleanup; never fixture provisioning."""
import base64
import hashlib
import json
import os
import re
from datetime import datetime, timezone


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


def recover(env, scope):
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
