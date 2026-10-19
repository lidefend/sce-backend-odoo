#!/usr/bin/env python3
"""Host-side P4 entry: plan/apply/readback/restore exactly three personnel views."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import daily_runtime_duty_identity as identity
import daily_runtime_duty_payload as runtime
import daily_runtime_duty_odoo_shell as shell

MARKER = 'PERSONNEL_VIEW_RESULT='


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_new(path, value):
    # Complete a private sibling first, then atomically publish without replacement.
    descriptor, temporary = tempfile.mkstemp(prefix='.personnel-receipt-', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'w') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        os.unlink(temporary)


def bound_identity(document, duty_key, head, expected):
    require(duty_key == 'demo', 'this closeout authorizes only the demo duty')
    require(re.fullmatch('[0-9a-f]{40}', expected) and head == expected, 'candidate SHA mismatch')
    raw = shell.resolve_duty(document, duty_key)
    require(raw['stack']['product_root'] == str(ROOT), 'wrong deployed source root')
    return raw


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--action', required=True, choices=('plan', 'apply', 'verify', 'restore', 'reconcile'))
    parser.add_argument('--verify-target', choices=('apply', 'restore'), default='apply')
    parser.add_argument('--duty', required=True)
    parser.add_argument('--expected-sha', required=True)
    parser.add_argument('--declaration-sha256', required=True)
    parser.add_argument('--plan-sha256', default='')
    args = parser.parse_args()
    declaration = ROOT / 'config/ops/daily_runtime_database_duties.v1.json'
    require(digest(declaration) == args.declaration_sha256, 'declaration digest mismatch')
    head = runtime.run(['git', '-C', str(ROOT), 'rev-parse', 'HEAD']).strip()
    require(not runtime.run(['git', '-C', str(ROOT), 'status', '--porcelain']).strip(), 'deployed source is dirty')
    document = json.loads(declaration.read_text())
    raw = bound_identity(document, args.duty, head, args.expected_sha)
    duty = identity.resolve(args.duty, declaration)
    ops = Path(document['ops_root'])
    values = runtime.read_duty_env(identity.duty_env_path(duty, ops, reading=True), duty)
    container = runtime.inspect_odoo_container(duty, values)
    require(container['mounts'].get('/mnt/source-addons', {}).get('source') == str(ROOT / 'addons'), 'source mount mismatch')
    require(container['mounts'].get('/mnt/scripts', {}).get('source') == str(ROOT / 'scripts'), 'scripts mount mismatch')
    require(container['mounts'].get('/var/lib/odoo', {}).get('name') == duty['odoo_data_volume'], 'filestore volume mismatch')
    db = json.loads(runtime.run(['docker', 'inspect', duty['database_container']]))[0]
    require(any(m.get('Name') == duty['database_volume'] and m.get('Destination') == '/var/lib/postgresql/data' for m in db['Mounts']), 'database volume mismatch')
    observed = runtime.run(['docker', 'exec', duty['database_container'], 'psql', '-U', raw['cluster']['maintenance_role'], '-d', duty['database'], '-Atc', 'SELECT system_identifier FROM pg_control_system()']).strip()
    require(observed == raw['cluster']['system_identifier'], 'database cluster identity mismatch')
    require(values.get('ODOO_DBFILTER') == duty['dbfilter'], 'dbfilter mismatch')
    evidence = ops / 'personnel-view-closeout' / head
    evidence.mkdir(parents=True, exist_ok=True, mode=0o700)
    plan_path, receipt_path = evidence / 'plan.json', evidence / 'apply.json'
    attempt_path = evidence / 'apply-attempt.json'
    with (ops / 'personnel-view-closeout.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        saved = None
        if args.action != 'plan':
            require(digest(plan_path) == args.plan_sha256, 'plan digest mismatch')
            plan = json.loads(plan_path.read_text())
            require(plan['candidate'] == head and plan['declaration_sha256'] == args.declaration_sha256, 'plan identity mismatch')
            if args.action in ('apply', 'reconcile'):
                saved = plan['state']
            else:
                receipt = evidence / 'restore.json' if args.action == 'verify' and args.verify_target == 'restore' else receipt_path
                if not receipt.exists() and receipt == receipt_path:
                    receipt = evidence / 'reconcile-apply.json'
                if not receipt.exists() and args.verify_target == 'restore':
                    receipt = evidence / 'reconcile-restore.json'
                saved = json.loads(receipt.read_text())['state']
                if 'outcome' in saved:
                    require(saved['outcome'] in ('committed_observed', 'restored_observed'), 'no committed application to verify or restore')
            if args.action == 'reconcile':
                attempt = json.loads((attempt_path if args.verify_target == 'apply' else evidence / 'restore-attempt.json').read_text())
                if args.verify_target == 'restore':
                    saved = attempt['request']['saved']
                require(attempt['plan_sha256'] == args.plan_sha256, 'attempt identity mismatch')
        if args.action in ('apply', 'restore'):
            require(os.environ.get('CONFIRM_DAILY_PERSONNEL_VIEWS') == 'UPDATE_ONLY_THREE_PERSONNEL_VIEWS', 'write confirmation missing')
            require(not (receipt_path if args.action == 'apply' else evidence / 'restore.json').exists(), 'existing receipt: read back, do not replay')
        request = dict(action=args.action, database=duty['database'], saved=saved,
                       verify_target=args.verify_target, dbfilter=duty['dbfilter'],
                       database_role=duty['database_role'], system_identifier=raw['cluster']['system_identifier'],
                       xml_sha256=digest(ROOT / 'addons/smart_construction_core/views/support/runtime_user_management_views.xml'))
        if args.action in ('apply', 'restore'):
            attempt = attempt_path if args.action == 'apply' else evidence / 'restore-attempt.json'
            save_new(attempt, dict(candidate=head, plan_sha256=args.plan_sha256, request=request))
        program = "import importlib.util, json\ns = importlib.util.spec_from_file_location('transaction', '/mnt/scripts/ops/daily_personnel_views_transaction.py')\nm = importlib.util.module_from_spec(s)\ns.loader.exec_module(m)\nprint(%r + json.dumps(m.run(env, %r), ensure_ascii=False))\n" % (MARKER, request)
        output = runtime.run(shell.build_command(raw, container['container'], odoo_config=shell.DEFAULT_ODOO_CONFIG, environment={}), input=program)
        rows = [row[len(MARKER):] for row in output.splitlines() if row.startswith(MARKER)]
        require(len(rows) == 1, 'missing receipt; inspect before any retry')
        state = json.loads(rows[0])
        record = dict(candidate=head, declaration_sha256=args.declaration_sha256, duty=args.duty, container_id=container['container_id'], state=state)
        target = {'plan': plan_path, 'apply': receipt_path, 'verify': evidence / ('verify-' + args.verify_target + '.json'), 'restore': evidence / 'restore.json', 'reconcile': evidence / ('reconcile-' + args.verify_target + '.json')}[args.action]
        save_new(target, record)
        print(json.dumps(dict(status='passed', action=args.action, evidence=str(target), sha256=digest(target), candidate=head, duty=args.duty), ensure_ascii=False))


if __name__ == '__main__':
    main()
