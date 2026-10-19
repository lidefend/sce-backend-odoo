"""Governed isolated-database probe. Never run against the persistent demo."""
import hashlib
import json
import os
from pathlib import Path
import threading

CONFIRMATION = 'RUN_ISOLATED_PERMISSION_CONCURRENCY'
FILES = (
    'addons/smart_core/models/res_users.py',
    'addons/smart_core/models/res_users_group_authority.py',
    'addons/smart_core/models/group_authority_reconciliation.py',
    'addons/smart_core/security/group_assignment.py',
)


def source_hashes(root):
    return {name: hashlib.sha256((Path(root) / name).read_bytes()).hexdigest() for name in FILES}


def validate_identity(database, dbfilter, confirmation, test_mode, expected, actual):
    if database != 'sc_contract_lifecycle' or dbfilter != '^sc_contract_lifecycle$':
        raise ValueError('PERMISSION_PROBE_WRONG_DATABASE_IDENTITY')
    if confirmation != CONFIRMATION:
        raise ValueError('PERMISSION_PROBE_CONFIRMATION_REQUIRED')
    if test_mode:
        raise ValueError('PERMISSION_PROBE_SHARED_TEST_CURSOR_FORBIDDEN')
    if (not isinstance(expected, dict) or set(expected) != set(FILES) or expected != actual
            or any(not isinstance(value, str) or len(value) != 64
                   or any(char not in '0123456789abcdef' for char in value) for value in expected.values())):
        raise ValueError('PERMISSION_PROBE_SOURCE_MISMATCH')


def validate_mode(mode):
    if mode not in ('baseline', 'editor_only'):
        raise ValueError('PERMISSION_PROBE_UNKNOWN_MODE')
    return mode


def run_editor_races(registry, report):
    from odoo import api, SUPERUSER_ID
    from odoo.exceptions import AccessError
    from odoo.sql_db import TestCursor
    from psycopg2.errors import SerializationFailure

    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        if env['res.users'].with_context(active_test=False).search_count([
                ('login', '=', 'auth01_concurrency_editor_admin')]):
            raise AssertionError('prior editor fixture exists; no replay')
        internal = env.ref('base.group_user')
        group = env['res.groups'].create({'name': 'Synthetic AUTH01 editor root'})
        company = env.company
        context = {'allowed_company_ids': company.ids}
        def user(suffix, groups):
            return env['res.users'].with_context(no_reset_password=True).create({
                'name': 'Synthetic editor ' + suffix, 'login': 'auth01_concurrency_editor_' + suffix,
                'company_id': company.id, 'company_ids': [(6, 0, company.ids)],
                'groups_id': [(6, 0, groups.ids)],
            })
        admin = user('admin', internal | env.ref('base.group_system'))
        cases = []
        for key in ('confirm_first', 'edit_first'):
            target = user(key, internal | group)
            target._sc_store_group_authority(None, 'synthetic editor legacy source')
            review = env['sc.group.authority.reconcile'].with_user(admin).create({'user_id': target.id})
            review.write({'root_group_ids': [(6, 0, (internal | group).ids)], 'note': 'Synthetic original basis'})
            cases.append((key, target.id, review.id))
        actor = admin.id
        report.update(actor_id=actor, editor_cases=cases)
        cr.commit()

    for key, target_id, review_id in cases:
        barrier = threading.Barrier(2, timeout=10)
        outcomes, transactions = [None, None], [None, None]
        def worker(index):
            try:
                with registry.cursor() as cr:
                    if isinstance(cr, TestCursor):
                        raise AssertionError('independent transaction required')
                    cr.execute("SET LOCAL lock_timeout = '5s'")
                    cr.execute("SET LOCAL statement_timeout = '15s'")
                    cr.execute('SELECT pg_backend_pid(), txid_current()')
                    pid, txid = cr.fetchone()
                    transactions[index] = {'backend_pid': pid, 'transaction_id': txid}
                    env = api.Environment(cr, actor, context)
                    review = env['sc.group.authority.reconcile'].browse(review_id)
                    review.read(['confirmed', 'note'])
                    confirm = (key == 'confirm_first') == (index == 0)
                    if index == 1:
                        barrier.wait()
                    if confirm:
                        review.action_confirm()
                    else:
                        review.write({'note': 'Synthetic edited basis'})
                    if index == 0:
                        barrier.wait()
                    cr.commit()
                    outcomes[index] = 'committed'
            except SerializationFailure:
                outcomes[index] = 'serialization_conflict'
            except Exception as error:
                outcomes[index] = 'unexpected:' + type(error).__name__
        threads = [threading.Thread(target=worker, args=(i,), daemon=True) for i in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(25)
        if any(thread.is_alive() for thread in threads):
            raise AssertionError('editor worker timeout')
        if outcomes != ['committed', 'serialization_conflict']:
            raise AssertionError((key, outcomes))
        if len({row['backend_pid'] for row in transactions}) != 2 or len({row['transaction_id'] for row in transactions}) != 2:
            raise AssertionError('independent concurrent transactions required')
        with registry.cursor() as cr:
            env = api.Environment(cr, actor, context)
            review = env['sc.group.authority.reconcile'].browse(review_id)
            if key == 'confirm_first':
                try:
                    review.write({'note': 'Synthetic edited basis'})
                except AccessError as error:
                    if 'GROUP_AUTHORITY_REVIEW_IMMUTABLE' not in str(error):
                        raise
                    cr.rollback()
                else:
                    cr.rollback()
                    raise AssertionError('confirmed edit retry accepted')
            else:
                review.action_confirm()
                cr.commit()
        with registry.cursor() as cr:
            env = api.Environment(cr, actor, context)
            review = env['sc.group.authority.reconcile'].browse(review_id)
            audit = env['sc.group.authority.confirmation'].search([('user_id', '=', target_id)])
            expected_note = 'Synthetic original basis' if key == 'confirm_first' else 'Synthetic edited basis'
            if len(audit) != 1 or not review.confirmed or review.note != expected_note or audit.note != expected_note:
                raise AssertionError('editor/audit authoritative readback differs')
            report['checks'].append({'key': key, 'status': 'passed', 'outcomes': outcomes,
                                     'transactions': transactions, 'audit_ids': audit.ids, 'note': expected_note})


def run(shell_env):
    from odoo import api, SUPERUSER_ID, tools
    from odoo.exceptions import UserError
    from odoo.modules.registry import Registry
    from odoo.sql_db import TestCursor
    from psycopg2.errors import SerializationFailure
    from odoo.addons.smart_core.models import res_users, res_users_group_authority, group_authority_reconciliation
    from odoo.addons.smart_core.security import group_assignment

    modules = (res_users, res_users_group_authority, group_authority_reconciliation, group_assignment)
    actual = {name: hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
              for name, module in zip(FILES, modules)}
    registry = Registry(shell_env.cr.dbname)
    validate_identity(shell_env.cr.dbname, tools.config['dbfilter'],
                      os.environ.get('SC_CONFIRM_PERMISSION_CONCURRENCY'),
                      isinstance(shell_env.cr, TestCursor) or registry.test_cr is not None,
                      json.loads(os.environ.get('SC_ACCEPTANCE_PERMISSION_HASHES', '{}')), actual)
    mode = validate_mode(os.environ.get('SC_ACCEPTANCE_PERMISSION_MODE', 'baseline'))
    shell_env.cr.rollback()
    report = {'database': shell_env.cr.dbname, 'source_hashes': actual,
              'status': 'failed', 'checks': [], 'cleanup': 'governed profile discard required'}
    context = {}

    def execute_pair(actor, review_ids=None, target_id=None):
        barrier = threading.Barrier(2, timeout=10)
        outcomes = [None, None]
        transactions = [None, None]

        def worker(index):
            try:
                with registry.cursor() as cr:
                    if isinstance(cr, TestCursor):
                        raise AssertionError('independent transaction required')
                    cr.execute("SET LOCAL lock_timeout = '5s'")
                    cr.execute("SET LOCAL statement_timeout = '15s'")
                    env = api.Environment(cr, actor, context)
                    cr.execute('SELECT pg_backend_pid(), txid_current()')
                    pid, txid = cr.fetchone()
                    transactions[index] = {'backend_pid': pid, 'transaction_id': txid}
                    if review_ids is not None:
                        env['sc.group.authority.reconcile'].browse(review_ids[index]).read(['confirmed', 'snapshot'])
                    else:
                        env['res.users'].browse(target_id).read(['token_version'])
                    barrier.wait()
                    if review_ids is not None:
                        env['sc.group.authority.reconcile'].browse(review_ids[index]).action_confirm()
                    else:
                        env['res.users'].browse(target_id)._sc_bump_token_epoch()
                    cr.commit()
                    outcomes[index] = 'committed'
            except SerializationFailure:
                outcomes[index] = 'serialization_conflict'
            except UserError:
                outcomes[index] = 'rejected'
            except Exception as error:
                outcomes[index] = 'unexpected:' + type(error).__name__

        threads = [threading.Thread(target=worker, args=(i,), daemon=True) for i in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(25)
        if any(thread.is_alive() for thread in threads):
            raise AssertionError('concurrency worker timeout')
        if any(row is None for row in transactions) or len({row['backend_pid'] for row in transactions}) != 2 or len({row['transaction_id'] for row in transactions}) != 2:
            raise AssertionError('two independent simultaneous transactions required')
        return {'outcomes': outcomes, 'transactions': transactions}

    try:
        if mode == 'editor_only':
            run_editor_races(registry, report)
            report['status'] = 'passed'
            return
        with registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            # A previous probe must be inspected/discarded, never silently adopted.
            if env['res.users'].with_context(active_test=False).search_count([
                    ('login', 'in', ['auth01_concurrency_admin', 'auth01_concurrency_same', 'auth01_concurrency_distinct'])]):
                raise AssertionError('prior concurrency fixture exists; no replay')
            internal = env.ref('base.group_user')
            group = env['res.groups'].create({'name': 'Synthetic AUTH01 concurrency root'})
            company = env.company
            context = {'allowed_company_ids': company.ids}
            def user(login, groups):
                return env['res.users'].with_context(no_reset_password=True).create({
                    'name': 'Synthetic ' + login, 'login': login,
                    'company_id': company.id, 'company_ids': [(6, 0, company.ids)],
                    'groups_id': [(6, 0, groups.ids)],
                })
            admin = user('auth01_concurrency_admin', internal | env.ref('base.group_system'))
            targets = [user('auth01_concurrency_' + suffix, internal | group) for suffix in ('same', 'distinct')]
            reviews = []
            for index, target in enumerate(targets):
                target._sc_store_group_authority(None, 'synthetic concurrent legacy source')
                rows = []
                for _ in range(index + 1):
                    review = env['sc.group.authority.reconcile'].with_user(admin).create({'user_id': target.id})
                    review.write({'root_group_ids': [(6, 0, (internal | group).ids)],
                                  'note': 'Synthetic concurrent source confirmation'})
                    rows.append(review.id)
                reviews.append(rows * 2 if index == 0 else rows)
            actor, target_ids = admin.id, [target.id for target in targets]
            report.update(actor_id=actor, target_ids=target_ids, review_ids=reviews)
            cr.commit()

        for label, target_id, review_ids in zip(('same_review', 'distinct_reviews'), target_ids, reviews):
            pair = execute_pair(actor, review_ids=review_ids)
            outcomes = pair['outcomes']
            if outcomes.count('committed') != 1 or any(x not in ('committed', 'serialization_conflict', 'rejected') for x in outcomes):
                raise AssertionError((label, outcomes))
            loser = outcomes.index(next(x for x in outcomes if x != 'committed'))
            with registry.cursor() as cr:
                env = api.Environment(cr, actor, context)
                # A fresh retry must reject stale/replayed confirmation, not create a second audit.
                try:
                    env['sc.group.authority.reconcile'].browse(review_ids[loser]).action_confirm()
                except UserError:
                    cr.rollback()
                else:
                    cr.rollback()
                    raise AssertionError('loser replay unexpectedly accepted')
            with registry.cursor() as cr:
                env = api.Environment(cr, actor, context)
                target = env['res.users'].browse(target_id)
                audit = env['sc.group.authority.confirmation'].search([('user_id', '=', target_id)])
                if len(audit) != 1 or target.sc_group_authority_state['status'] != 'tracked':
                    raise AssertionError('authoritative confirmation readback failed')
                report['checks'].append({'key': label, 'status': 'passed', **pair, 'audit_ids': audit.ids})

        with registry.cursor() as cr:
            env = api.Environment(cr, actor, context)
            before = env['res.users'].browse(target_ids[0]).token_version
        pair = execute_pair(actor, target_id=target_ids[0])
        outcomes = pair['outcomes']
        if any(x not in ('committed', 'serialization_conflict') for x in outcomes):
            raise AssertionError(('epoch', outcomes))
        for outcome in outcomes:
            if outcome == 'serialization_conflict':
                with registry.cursor() as cr:
                    api.Environment(cr, actor, context)['res.users'].browse(target_ids[0])._sc_bump_token_epoch()
                    cr.commit()
        with registry.cursor() as cr:
            env = api.Environment(cr, actor, context)
            after = env['res.users'].browse(target_ids[0]).token_version
            if after != before + 2:
                raise AssertionError('lost concurrent epoch increment')
        report['checks'].append({'key': 'epoch_increment', 'status': 'passed', **pair,
                                 'before': before, 'after': after})
        report['status'] = 'passed'
    finally:
        shell_env.cr.rollback()
        print('AUTH01_CONCURRENCY=' + json.dumps(report, sort_keys=True))


if 'env' in globals():
    run(env)
elif __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-hashes', action='store_true', required=True)
    parser.parse_args()
    print(json.dumps(source_hashes(Path(__file__).resolve().parents[2]), sort_keys=True))
