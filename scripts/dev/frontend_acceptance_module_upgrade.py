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

from frontend_acceptance_runtime_profile import resolve

ROOT = Path(__file__).resolve().parents[2]


def command(args, *, capture=True):
    if not capture:
        child = subprocess.Popen(args, cwd=ROOT)
        try:
            code = child.wait()
        except BaseException:
            # Do not release the lease while an interrupted -u child still writes.
            child.terminate()
            try:
                child.wait(timeout=30)
            except subprocess.TimeoutExpired:
                child.kill()
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


def source_identity(env):
    head = command(['git', 'rev-parse', 'HEAD']).strip()
    if not re.fullmatch(r'[0-9a-f]{40}', env.get('EXPECTED_HEAD', '')) or env['EXPECTED_HEAD'] != head:
        raise ValueError('EXPECTED_HEAD must equal current full HEAD')
    if env.get('SC_ACCEPTANCE_SOURCE_SHA', head) != head:
        raise ValueError('artifact source SHA differs from upgrade HEAD')
    if command(['git', 'status', '--porcelain', '--untracked-files=all']).strip():
        raise ValueError('module upgrade requires a clean checkout')
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


@contextlib.contextmanager
def leases(profile, env):
    # Same keys and directory as frontend_acceptance_environment.mjs and backend.up.
    directory = Path(env.get('XDG_RUNTIME_DIR') or env.get('TMPDIR') or tempfile.gettempdir()) / 'sce-frontend-acceptance/leases'
    directory.mkdir(parents=True, exist_ok=True)
    with contextlib.ExitStack() as stack:
        for port in (profile['FRONTEND_ACCEPTANCE_PORT'], '5180'):
            target = f"http://127.0.0.1:{port}|http://127.0.0.1:{profile['BACKEND_ACCEPTANCE_PORT']}|{profile['DB_NAME']}"
            key = hashlib.sha256(target.encode()).hexdigest()
            stream = stack.enter_context((directory / f'{key}.lock').open('a'))
            try:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise ValueError('active acceptance lease; no writer changed') from exc
        yield


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


def upgrade(env):
    profile = profile_identity(env)
    head = source_identity(env)
    with leases(profile, env):
        # Recheck after lock acquisition; never execute against a drifted checkout.
        if source_identity(env) != head:
            raise ValueError('source changed while acquiring lease')
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
            command(['bash', str(ROOT / 'scripts/mod/upgrade.sh')], capture=False)
        except BaseException:
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


def main():
    def interrupted(signum, frame):
        raise InterruptedError('module upgrade interrupted')
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        upgrade(os.environ)
    except (ValueError, subprocess.CalledProcessError, OSError) as exc:
        # Do not expose Docker inspect environments or credentials in diagnostics.
        detail = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
        print(f'[acceptance.module.upgrade] DENY {detail}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
