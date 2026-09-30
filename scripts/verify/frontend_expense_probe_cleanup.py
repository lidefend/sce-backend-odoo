"""Exact transient browser document cleanup; never fixture provisioning."""
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


def recover(env, scope):
    assert env.cr.dbname == 'sc_frontend_acceptance'
    finance = env['res.users'].sudo().browse(30)
    assert finance.login == 'fixture_role_finance' and finance.company_id.id == 8
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
        assert all(a.create_uid == finance and a.name == scope['filename'] for a in attachments)
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
