"""P4 exact owned journal cleanup; no general-purpose deletion authority."""
import json
import os
import re


def validate_run_ref(ref, head):
    assert re.fullmatch(r"[a-f0-9]{40}", head or "")
    assert re.fullmatch(r"P4-JOURNAL-" + head + r"-[a-f0-9]{32}", ref or "")


def validate_identity(visible_ids, audited_ids, known_existing_ids=None):
    assert len(audited_ids) <= 1 and visible_ids == audited_ids, 'owned record hidden from creator'
    if known_existing_ids is not None:
        assert known_existing_ids == audited_ids, 'browser identity differs from marker identity'


def validate_snapshot(snapshot, ref):
    assert snapshot['ref'] == ref
    assert snapshot['creator'] == 40 and snapshot['company'] == 1 and snapshot['journal'] == 3
    assert snapshot['currency'] == 6 and snapshot['state'] == 'draft'
    assert snapshot['posted_before'] is False and snapshot['name'] == '/'
    assert type(snapshot['id']) is int and snapshot['id'] > 0
    lines = snapshot['lines']
    assert len(lines) == 2 and {line['account'] for line in lines} == {48, 49}
    assert len({line['id'] for line in lines}) == 2
    for line in lines:
        assert type(line['id']) is int and line['id'] > 0
        assert line['move'] == snapshot['id'] and line['currency'] == 6 and line['company'] == 1
        assert not line['matched_debit'] and not line['matched_credit']
        assert all(type(line[key]) in (int, float) for key in ('debit', 'credit', 'balance', 'amount_currency'))
        debit = line['account'] == 49
        assert line['debit'] in (0, 100 if debit else 0) and line['credit'] in (0, 0 if debit else 100)
        assert line['balance'] in (0, 100 if debit else -100)
        assert line['amount_currency'] in (0, 100 if debit else -100)


def run_owned(env):
    assert env.cr.dbname == 'sc_dev_demo'
    assert os.environ.get('SC_CONFIRM_JOURNAL_RECOVERY') == 'PREFLIGHT_CLEANUP_ONE_OWNED_DRAFT'
    ref, head = os.environ.get('SC_RUNTIME_JOURNAL_REF'), os.environ.get('CANDIDATE_GIT_HEAD')
    validate_run_ref(ref, head)
    mode = os.environ.get('SC_RUNTIME_JOURNAL_RECOVERY')
    assert mode in ('preflight', 'cleanup', 'verify_absent')
    actor = env['res.users'].browse(40)
    assert actor.exists() and actor.login == 'demo_full'
    model = env['account.move'].with_user(actor).with_context(allowed_company_ids=[1], company_id=1)
    assert not model.env.su
    model.check_access_rights('read')
    model.check_access_rights('create')
    model.check_access_rights('unlink')
    records = model.search([('ref', '=', ref)], limit=2)
    # Exact run-owned identity audit only. Elevation may detect hidden IDs but
    # never supplies business values or authorizes unlink; actor ACL/rules do.
    audited = env['account.move'].sudo().search([('ref', '=', ref)], limit=2)
    validate_identity(records.ids, audited.ids)
    browser_receipt = json.loads(os.environ.get('SC_RUNTIME_JOURNAL_BROWSER_RECEIPT', 'null'))
    if browser_receipt is not None:
        assert browser_receipt['head'] == head and browser_receipt['ref'] == ref
        known_id = browser_receipt['record_id']
        assert type(known_id) is int and known_id > 0
        known_lines = browser_receipt['line_ids']
        assert isinstance(known_lines, list) and len(known_lines) in (0, 2)
        assert all(type(i) is int and i > 0 for i in known_lines)
        existing = env['account.move'].sudo().browse(known_id).exists()
        validate_identity(records.ids, audited.ids, existing.ids)
        if records and known_lines:
            records.check_access_rule('read')
            assert set(records.line_ids.ids) == set(known_lines)
        if not records:
            assert not env['account.move.line'].sudo().browse(known_lines).exists()

    result = {'mode': mode, 'ref': ref, 'head': head}
    if mode == 'preflight':
        assert not records
        # Demonstrate record-rule and unlink support on the exact draft shape,
        # in a savepoint that is unconditionally rolled back before the browser.
        class RollbackProbe(Exception): pass
        try:
            with env.cr.savepoint():
                probe = model.create({'ref': ref, 'journal_id': 3, 'move_type': 'entry',
                                      'line_ids': [(0, 0, {'account_id': 49, 'debit': 100, 'credit': 0}),
                                                   (0, 0, {'account_id': 48, 'debit': 0, 'credit': 100})]})
                probe.check_access_rule('read')
                probe.check_access_rule('unlink')
                probe.unlink()
                env.flush_all()
                raise RollbackProbe()
        except RollbackProbe:
            pass
        assert not model.search_count([('ref', '=', ref)])
        result.update(passed=True, rolled_back=True)
    elif mode == 'cleanup':
        result.update(record_id=None, line_ids=[])
        if records:
            records.check_access_rule('read')
            snapshot = {'id': records.id, 'ref': records.ref, 'creator': records.create_uid.id,
                        'company': records.company_id.id, 'journal': records.journal_id.id,
                        'currency': records.currency_id.id, 'state': records.state,
                        'posted_before': records.posted_before, 'name': records.name,
                        'lines': [{'id': line.id, 'move': line.move_id.id, 'account': line.account_id.id,
                                   'company': line.company_id.id, 'currency': line.currency_id.id,
                                   'debit': line.debit, 'credit': line.credit, 'balance': line.balance,
                                   'amount_currency': line.amount_currency,
                                   'matched_debit': line.matched_debit_ids.ids,
                                   'matched_credit': line.matched_credit_ids.ids} for line in records.line_ids]}
            validate_snapshot(snapshot, ref)
            print('JOURNAL_RECOVERY_BEFORE ' + json.dumps(snapshot))
            result.update(record_id=records.id, line_ids=records.line_ids.ids)
            records.check_access_rule('unlink')
            records.unlink()
            env.flush_all()
        assert not model.search_count([('ref', '=', ref)])
        assert not env['account.move.line'].sudo().browse(result['line_ids']).exists()
        env.cr.commit()
        result.update(passed=True, committed=True, absent=True)
    else:
        receipt = json.loads(os.environ['SC_RUNTIME_JOURNAL_CLEANUP_RECEIPT'])
        assert receipt['ref'] == ref and receipt['head'] == head and receipt['mode'] == 'cleanup'
        assert receipt['passed'] is True and receipt['committed'] is True and receipt['absent'] is True
        record_id, line_ids = receipt['record_id'], receipt['line_ids']
        assert (record_id is None and line_ids == []) or (type(record_id) is int and record_id > 0
            and len(line_ids) == 2 and all(type(i) is int and i > 0 for i in line_ids))
        assert not records
        if record_id:
            assert not env['account.move'].sudo().browse(record_id).exists()
        assert not env['account.move.line'].sudo().browse(line_ids).exists()
        result.update(passed=True, absent=True, record_id=record_id, line_ids=line_ids)
    print('JOURNAL_RECOVERY ' + json.dumps(result))


def run_legacy(env):
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


def inspect_role_identity(env):
    """Read only: fixed demo principals; not a role assignment/fixture API."""
    assert env.cr.dbname == 'sc_dev_demo'
    assert os.environ.get('SC_CONFIRM_JOURNAL_RECOVERY') == 'READ_ONLY_ACCOUNTING_ROLE_IDENTITIES'
    from odoo.addons.smart_core.identity.identity_resolver import IdentityResolver
    from odoo.addons.smart_core.delivery.runtime_route_authority import build_runtime_route_authority
    original_commit = env.cr.commit
    def refuse_commit(*args, **kwargs):
        raise AssertionError('identity observation must not commit')
    env.cr.commit = refuse_commit
    rows = []
    try:
        for login in ('sc_demo_accounting_manager', 'sc_demo_accounting_read', 'sc_demo_accounting_user', 'demo_role_project_read', 'demo_role_finance'):
            user = env['res.users'].with_context(active_test=False).search([('login', '=', login)], limit=2)
            assert len(user) <= 1
            if not user:
                rows.append({'login': login, 'exists': False})
                continue
            actor_env = env['account.move'].with_user(user).with_context(allowed_company_ids=user.company_id.ids).env
            resolver = IdentityResolver(actor_env)
            groups = resolver.user_group_xmlids(user)
            roles, evidence = resolver.resolve_role_codes_with_evidence(groups)
            authority = build_runtime_route_authority(actor_env)
            rows.append({'login': login, 'exists': True, 'uid': user.id, 'active': user.active,
                         'company_id': user.company_id.id, 'company_ids': user.company_ids.ids,
                         'group_authority_state': user.sc_group_authority_state,
                         'assigned_role_xmlids': sorted(user.sc_user_role_group_ids.get_external_id().values()),
                         'effective_group_xmlids': sorted(groups), 'resolved_roles': roles,
                         'resolution_source': evidence.get('source'),
                         'primary_routes': authority.get('primary_actions', [])})
    finally:
        env.cr.rollback()
        env.cr.commit = original_commit
    print('JOURNAL_ROLE_IDENTITIES ' + json.dumps({'database': env.cr.dbname, 'read_only': True, 'actors': rows}, ensure_ascii=False))


if 'env' in globals():
    if os.environ.get('SC_CONFIRM_JOURNAL_RECOVERY') == 'READ_ONLY_ACCOUNTING_ROLE_IDENTITIES':
        inspect_role_identity(env)
    elif os.environ.get('SC_CONFIRM_JOURNAL_RECOVERY') == 'PREFLIGHT_CLEANUP_ONE_OWNED_DRAFT':
        run_owned(env)
    else:
        run_legacy(env)
