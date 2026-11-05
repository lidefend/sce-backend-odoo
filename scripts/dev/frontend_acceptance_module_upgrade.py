#!/usr/bin/env python3
"""Quiesce registered local acceptance writers for a non-reset module upgrade.

After -u begins, writers deliberately stay stopped, even on failure: restarting
an old registry is not database recovery. The caller next uses backend.up on
this exact source revision. This entry never resets/restores a database.
"""
from __future__ import annotations

import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import uuid

from frontend_acceptance_runtime_profile import resolve

ROOT = Path(__file__).resolve().parents[2]


def command(args, *, capture=True, env=None, stdin=None):
    if not capture:
        child = subprocess.Popen(args, cwd=ROOT, env=env, stdin=stdin, start_new_session=True)
        try:
            code = child.wait()
        except BaseException:
            # Do not release the lease while an interrupted -u child still writes.
            for sig in (signal.SIGTERM, signal.SIGKILL):
                try:
                    os.killpg(child.pid, sig)
                except ProcessLookupError:
                    pass
                if sig == signal.SIGTERM:
                    try:
                        child.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        pass
            child.wait()
            raise
        if code:
            raise subprocess.CalledProcessError(code, args)
        return ""
    return subprocess.run(args, cwd=ROOT, check=True, text=True,
                          stdout=subprocess.PIPE if capture else None,
                          stderr=subprocess.PIPE if capture else None).stdout


def inspect(name):
    rows = json.loads(command(['docker', 'inspect', name]))
    if len(rows) != 1:
        raise ValueError('ambiguous writer identity')
    return rows[0]


def checkout_identity(env, *, require_expected=True):
    head = command(['git', 'rev-parse', 'HEAD']).strip()
    if require_expected and (not re.fullmatch(r'[0-9a-f]{40}', env.get('EXPECTED_HEAD', '')) or env['EXPECTED_HEAD'] != head):
        raise ValueError('EXPECTED_HEAD must equal current full HEAD')
    if env.get('SC_ACCEPTANCE_SOURCE_SHA', head) != head:
        raise ValueError('artifact source SHA differs from upgrade HEAD')
    if command(['git', 'status', '--porcelain', '--untracked-files=all']).strip():
        raise ValueError('module upgrade requires a clean checkout')
    return head


def source_identity(env):
    head = checkout_identity(env)
    modules = env.get('MODULE', '').split(',')
    if not modules or len(set(modules)) != len(modules):
        raise ValueError('explicit distinct module list required')
    for module in modules:
        if not re.fullmatch(r'[a-z][a-z0-9_]*', module) or module == 'all':
            raise ValueError('invalid explicit module name')
        if not any((ROOT / directory / module / '__manifest__.py').is_file()
                   for directory in ('addons', 'demo_addons')):
            raise ValueError(f'module is outside registered local source: {module}')
    if env.get('ODOO_ARGS', '').strip() or env.get('SC_CUSTOMER_ADDONS_ROOT', ''):
        raise ValueError('upgrade argument/customer source overrides are not allowed')
    return head


def profile_identity(env):
    if env.get('SC_FRONTEND_ACCEPTANCE_RUNTIME_ENTRY') != 'operation_entry_v1':
        raise ValueError('use governed acceptance.module.upgrade entry')
    if env.get('SC_ACCEPTANCE_RUNTIME_PROFILE') != 'local':
        raise ValueError('module upgrade lifecycle requires registered local profile')
    profile = resolve('local')
    for key in ('COMPOSE_PROJECT_NAME', 'DB_NAME', 'ODOO_DB', 'ODOO_DBFILTER', 'DB_DATA',
                'REDIS_DATA', 'ODOO_DATA', 'BACKEND_ACCEPTANCE_NAME', 'BACKEND_ACCEPTANCE_DB',
                'BACKEND_ACCEPTANCE_PORT', 'FRONTEND_ACCEPTANCE_PORT', 'SC_ENVIRONMENT'):
        if env.get(key) != profile[key]:
            raise ValueError(f'profile identity mismatch: {key}')
    if env.get('SC_ACCEPTANCE_STANDARD_PREVIEW_PORT', '5180') != '5180':
        raise ValueError('local standard preview port override is not allowed')
    return profile


def lease_paths(profile, env):
    directory = Path(env.get('XDG_RUNTIME_DIR') or env.get('TMPDIR') or tempfile.gettempdir()) / 'sce-frontend-acceptance/leases'
    result = []
    for port in (profile['FRONTEND_ACCEPTANCE_PORT'], '5180'):
        target = f"http://127.0.0.1:{port}|http://127.0.0.1:{profile['BACKEND_ACCEPTANCE_PORT']}|{profile['DB_NAME']}"
        key = hashlib.sha256(target.encode()).hexdigest()
        result.append(directory / key)
    return result


def pending_paths(profile, env):
    return [path.with_suffix('.module-upgrade-pending.json') for path in lease_paths(profile, env)]


def check_pending(profile, env):
    if any(path.exists() or path.is_symlink() for path in pending_paths(profile, env)):
        raise ValueError('module upgrade recovery pending; runtime/acceptance blocked')


@contextlib.contextmanager
def leases(profile, env):
    # Same keys and directory as frontend_acceptance_environment.mjs and backend.up.
    with contextlib.ExitStack() as stack:
        for path in lease_paths(profile, env):
            path.parent.mkdir(parents=True, exist_ok=True)
            stream = stack.enter_context(path.with_suffix('.lock').open('a'))
            try:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise ValueError('active acceptance lease; no writer changed') from exc
        yield


def pending_record(profile, env, head, name, token, operation="module-upgrade"):
    return {'schema': 'acceptance-module-upgrade-pending.v1', 'profile': 'local',
            'database': profile['DB_NAME'], 'database_filter': profile['ODOO_DBFILTER'],
            'filestore': profile['ODOO_DATA'], 'source_sha': head,
            'modules': env['MODULE'].split(',') if operation == 'module-upgrade' else [],
            'operation': operation, 'container_name': name, 'attempt_id': token}


def write_pending(record, profile, env):
    for path in pending_paths(profile, env):
        # O_EXCL publishes an already fsynced complete JSON using a hard link.
        fd, temporary = tempfile.mkstemp(prefix='.upgrade-pending-', dir=path.parent)
        try:
            with os.fdopen(fd, 'w') as stream:
                json.dump(record, stream, sort_keys=True)
                stream.write('\n')
                stream.flush()
                os.fsync(stream.fileno())
            os.link(temporary, path)
            directory_fd = os.open(path.parent, os.O_DIRECTORY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            os.unlink(temporary)


def recover_pending(profile, env, head):
    paths = [path for path in pending_paths(profile, env) if path.exists() or path.is_symlink()]
    if not paths:
        raise ValueError('no pending module upgrade attempt to recover')
    records = []
    for path in paths:
        if path.is_symlink() or not path.is_file() or path.stat().st_uid != os.getuid():
            raise ValueError('pending marker identity invalid')
        try:
            records.append(json.loads(path.read_text()))
        except (ValueError, OSError) as exc:
            raise ValueError('pending marker unreadable/invalid') from exc
    record = records[0]
    token = record.get('attempt_id', '') if isinstance(record, dict) else ''
    if not re.fullmatch(r'[0-9a-f]{32}', token):
        raise ValueError('pending attempt identity invalid')
    name = f"{profile['COMPOSE_PROJECT_NAME']}-module-upgrade-{token}"
    operation = record.get('operation')
    if operation not in ('module-upgrade', 'release-snapshot'):
        raise ValueError('unknown pending operation')
    if operation == 'release-snapshot' and env.get('MODULE', ''):
        raise ValueError('snapshot recovery requires empty MODULE; never replays module upgrade')
    expected = pending_record(profile, env, head, name, token, operation)
    if any(item != expected for item in records):
        raise ValueError('pending marker scope/source mismatch')
    stop_upgrade_container(name, token, profile)
    for path in paths:
        path.unlink()
    print(f'[acceptance.module.upgrade] RECOVERED attempt={name} upgrade_replayed=false registry_pending=true', flush=True)


def writer_identity(row, name, profile):
    if row.get('Name') != '/' + name or not re.fullmatch(r'[0-9a-f]{64}', row.get('Id', '')):
        raise ValueError('writer container identity mismatch')
    labels = row.get('Config', {}).get('Labels') or {}
    if labels.get('com.docker.compose.project') != profile['COMPOSE_PROJECT_NAME'] or labels.get('com.docker.compose.service') != 'odoo':
        raise ValueError('writer project/service identity mismatch')
    values = dict(item.split('=', 1) for item in row['Config'].get('Env', []) if '=' in item)
    for key in ('DB_NAME', 'ODOO_DB', 'ODOO_DBFILTER'):
        if values.get(key) != profile[key]:
            raise ValueError(f'writer database identity mismatch: {key}')
    mounts = [m for m in row.get('Mounts', []) if m.get('Destination') == '/var/lib/odoo']
    if len(mounts) != 1 or mounts[0].get('Type') != 'volume' or mounts[0].get('Name') != profile['ODOO_DATA']:
        raise ValueError('writer filestore identity mismatch')
    if row.get('State', {}).get('Paused') or row.get('State', {}).get('Restarting'):
        raise ValueError('writer is paused/restarting; manual lifecycle reconciliation required')


def running_writers(profile):
    # Exited rollback containers are custody, not active writers. Never remove them.
    filters = [ ['--filter', f"volume={profile['ODOO_DATA']}"],
                ['--filter', f"label=com.docker.compose.project={profile['COMPOSE_PROJECT_NAME']}",
                 '--filter', 'label=com.docker.compose.service=odoo'] ]
    result = set()
    for subset in filters:
        result.update(command(['docker', 'ps', '--no-trunc', '-q', *subset]).split())
    return result


def stop_upgrade_container(name, token, profile):
    """Reap only this attempt's disposable Docker writer, while leases are held."""
    ids = command(['docker', 'ps', '-a', '--no-trunc', '-q', '--filter', f'name=^/{name}$']).split()
    if not ids:
        return
    if len(ids) != 1:
        raise ValueError('ambiguous upgrade container; manual recovery required')
    row = inspect(ids[0])
    labels = row.get('Config', {}).get('Labels') or {}
    if (row.get('Name') != '/' + name or row.get('Id') != ids[0]
            or labels.get('com.docker.compose.project') != profile['COMPOSE_PROJECT_NAME']
            or labels.get('com.docker.compose.service') != 'odoo'
            or labels.get('sce.acceptance.module-upgrade') != token):
        raise ValueError('upgrade container identity mismatch; not stopped')
    if row['State']['Running']:
        command(['docker', 'stop', row['Id']])
    # --rm may remove the stopped one-shot container. Both absence and an
    # inspected non-running exact attempt prove it no longer writes.
    remaining = command(['docker', 'ps', '-a', '--no-trunc', '-q', '--filter', f'name=^/{name}$']).split()
    if remaining and (remaining != ids or inspect(ids[0])['State']['Running']):
        raise ValueError('upgrade writer stop unconfirmed; manual recovery required')


def run_attempt(profile, env, head, operation, args, *, stdin=None):
    token = uuid.uuid4().hex
    name = f"{profile['COMPOSE_PROJECT_NAME']}-module-upgrade-{token}"
    if command(['docker', 'ps', '-a', '--no-trunc', '-q', '--filter', f'name=^/{name}$']).strip():
        raise ValueError('write attempt container already exists')
    write_pending(pending_record(profile, env, head, name, token, operation), profile, env)
    try:
        command(args, capture=False,
                env={**env, 'SC_ACCEPTANCE_UPGRADE_CONTAINER_NAME': name,
                     'SC_ACCEPTANCE_MODULE_UPGRADE_ID': token}, stdin=stdin)
        stop_upgrade_container(name, token, profile)
    except BaseException as error:
        try:
            stop_upgrade_container(name, token, profile)
            if not isinstance(error, (InterruptedError, KeyboardInterrupt)):
                for path in pending_paths(profile, env):
                    path.unlink()
            else:
                print('[acceptance.module.upgrade] RECOVERY_PENDING interrupted_attempt_requires_explicit_recovery=true', flush=True)
        except BaseException:
            print('[acceptance.module.upgrade] RECOVERY_PENDING writer_stop_unconfirmed=true acceptance_blocked=true', flush=True)
            raise
        raise
    for path in pending_paths(profile, env):
        path.unlink()


def upgrade(env):
    profile = profile_identity(env)
    if env.get('ACCEPTANCE_UPGRADE_RECOVER', '') not in ('', '0', '1'):
        raise ValueError('invalid recovery mode; upgrade not started')
    recovering = env.get('ACCEPTANCE_UPGRADE_RECOVER') == '1'
    head = checkout_identity(env) if recovering else source_identity(env)
    with leases(profile, env):
        # Recheck after lock acquisition; never execute against a drifted checkout.
        if (checkout_identity(env) if recovering else source_identity(env)) != head:
            raise ValueError('source changed while acquiring lease')
        if env.get('ACCEPTANCE_UPGRADE_RECOVER') == '1':
            recover_pending(profile, env, head)
            return
        check_pending(profile, env)
        names = [f"{profile['COMPOSE_PROJECT_NAME']}-odoo-1", profile['BACKEND_ACCEPTANCE_NAME']]
        rows = []
        for name in names:
            # Compose authority must exist; artifact may legitimately be absent.
            known = command(['docker', 'ps', '-a', '--format', '{{.Names}}']).splitlines()
            if name not in known:
                if name == names[0]:
                    raise ValueError('managed Compose writer is absent')
                continue
            row = inspect(name)
            writer_identity(row, name, profile)
            rows.append(row)
        allowed = {row['Id'] for row in rows}
        if running_writers(profile) - allowed:
            raise ValueError('unknown running writer shares managed resources')
        print(json.dumps({'stage': 'before', 'sha': head, 'database': profile['DB_NAME'],
                          'modules': env['MODULE'].split(','), 'writers': [
                              {'id': row['Id'], 'name': row['Name'], 'running': row['State']['Running']}
                              for row in rows]}, sort_keys=True), flush=True)
        stopped = []
        started = False
        try:
            for row in rows:
                if row['State']['Running']:
                    stopped.append(row)  # Includes a stop that failed after taking effect.
                    command(['docker', 'stop', row['Id']])
                if inspect(row['Id'])['State']['Running']:
                    raise ValueError('writer stop readback failed')
            if running_writers(profile):
                raise ValueError('writer appeared before upgrade')
            if source_identity(env) != head:
                raise ValueError('source changed before upgrade')
            started = True
            run_attempt(profile, env, head, 'module-upgrade',
                        ['bash', str(ROOT / 'scripts/mod/upgrade.sh')])
        except BaseException as error:
            if not started:
                for row in reversed(stopped):
                    current = inspect(row['Id'])
                    writer_identity(current, row['Name'].lstrip('/'), profile)
                    if not current['State']['Running']:
                        command(['docker', 'start', row['Id']])
                    if not inspect(row['Id'])['State']['Running']:
                        raise ValueError('pre-upgrade restoration failed; manual recovery required')
                print('[acceptance.module.upgrade] aborted_before_upgrade original_writer_states_restored=true', flush=True)
            else:
                print(f'[acceptance.module.upgrade] FAILED database_not_rolled_back=true writers_left_stopped=true sha={head}', flush=True)
            raise
        if running_writers(profile):
            raise ValueError('unexpected running writer after upgrade; do not accept runtime')
        print(f'[acceptance.module.upgrade] UPGRADED sha={head} writers_left_stopped=true registry_pending=true next=backend.acceptance.up-on-same-SHA', flush=True)


def release_snapshot(env):
    profile = profile_identity(env)
    head = checkout_identity(env, require_expected=False)
    with leases(profile, env):
        check_pending(profile, env)
        if checkout_identity(env, require_expected=False) != head:
            raise ValueError('snapshot source changed before write')
        with (ROOT / 'scripts/test/frontend_acceptance_release_snapshot.py').open() as source:
            run_attempt(profile, {**env, 'ODOO_SHELL_RUN_ISOLATED': '1'}, head,
                        'release-snapshot', ['bash', str(ROOT / 'scripts/ops/odoo_shell_exec.sh')], stdin=source)


def main():
    def interrupted(signum, frame):
        raise InterruptedError('module upgrade interrupted')
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        if sys.argv[1:] == ['--check-pending']:
            profile = profile_identity(os.environ)
            with leases(profile, os.environ):
                check_pending(profile, os.environ)
        elif sys.argv[1:] == ['--release-snapshot']:
            release_snapshot(os.environ)
        elif sys.argv[1:]:
            raise ValueError('unsupported module upgrade operation')
        else:
            upgrade(os.environ)
    except (ValueError, subprocess.CalledProcessError, OSError) as exc:
        # Do not expose Docker inspect environments or credentials in diagnostics.
        detail = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
        print(f'[acceptance.module.upgrade] DENY {detail}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
