"""P4 recovery of exactly the one draft left by the recorded browser attempt."""
import json
import os

REF = 'P4-JOURNAL-c0624c553232883baa8552fa49ca667f14326ef8-1793004275831'
assert env.cr.dbname == 'sc_dev_demo'
assert os.environ.get('SC_CONFIRM_JOURNAL_RECOVERY') == 'READBACK_CLEANUP_OWNED_DRAFT_13'
mode = os.environ.get('SC_RUNTIME_JOURNAL_RECOVERY', 'inspect')
assert mode in ('inspect', 'cleanup')
actor = env['res.users'].browse(40)
assert actor.exists() and actor.login == 'demo_full'
model = env['account.move'].with_user(actor).with_context(allowed_company_ids=[1], company_id=1)
by_ref = model.search([('ref', '=', REF)])
record = model.browse(13).exists()
assert by_ref.ids == record.ids
if not record:
    assert not env['account.move.line'].browse([21, 22]).exists()
    print('JOURNAL_RECOVERY ' + json.dumps({'mode': mode, 'record_id': 13, 'ref': REF, 'absent': True}))
else:
    assert record.ref == REF and record.state == 'draft'
    assert record.company_id.id == 1 and record.journal_id.id == 3 and record.create_uid.id == 40
    assert not record.posted_before and record.name == '/'
    lines = record.line_ids
    assert len(lines) == 2 and set(lines.account_id.ids) == {48, 49}
    line_ids = lines.ids
    assert set(line_ids) == {21, 22}
    before = {'mode': mode, 'record_id': record.id, 'ref': REF, 'company_id': record.company_id.id,
              'journal_id': record.journal_id.id, 'state': record.state,
              'lines': lines.read(['id', 'move_id', 'account_id', 'currency_id', 'debit', 'credit', 'balance', 'amount_currency', 'reconciled', 'matched_debit_ids', 'matched_credit_ids'])}
    print('JOURNAL_RECOVERY_BEFORE ' + json.dumps(before, ensure_ascii=False))
    assert all(line.currency_id.id == 6 and not line.matched_debit_ids and not line.matched_credit_ids for line in lines)
    if mode == 'cleanup':
        record.check_access_rights('unlink')
        record.check_access_rule('unlink')
        record.unlink()
        env.flush_all()
        assert not model.browse(13).exists() and not model.search_count([('ref', '=', REF)])
        assert not env['account.move.line'].browse(line_ids).exists()
        env.cr.commit()
        env.invalidate_all()
        assert not model.browse(13).exists() and not env['account.move.line'].browse(line_ids).exists()
        print('JOURNAL_RECOVERY ' + json.dumps({'mode': mode, 'record_id': 13, 'line_ids': line_ids, 'absent': True, 'committed': True}))
