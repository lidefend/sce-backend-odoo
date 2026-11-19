#!/usr/bin/env python3
"""Run the full local release in a fresh, profile-bound acceptance carrier."""
from __future__ import annotations

import fcntl
import hashlib
import re
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys

from frontend_acceptance_runtime_profile import resolve

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / '.runtime/frontend-release-disposable'


def command(args, env, *, capture=False, check=True):
    return subprocess.run(args, cwd=ROOT, env=env, text=True,
                          stdout=subprocess.PIPE if capture else None,
                          stderr=subprocess.PIPE if capture else None, check=check)


def require_absent(profile, env):
    project = profile['COMPOSE_PROJECT_NAME']
    rows = command(['docker', 'ps', '-aq', '--filter',
                    f'label=com.docker.compose.project={project}'], env, capture=True)
    if rows.stdout.strip():
        raise ValueError('disposable project already exists; refusing reuse or deletion')
    for key in ('DB_DATA', 'REDIS_DATA', 'ODOO_DATA'):
        if command(['docker', 'volume', 'inspect', profile[key]], env,
                   capture=True, check=False).returncode == 0:
            raise ValueError('disposable volume already exists; refusing reuse or deletion')
    if command(['docker', 'inspect', profile['BACKEND_ACCEPTANCE_NAME']], env,
               capture=True, check=False).returncode == 0:
        raise ValueError('disposable backend already exists')
    if Path(profile['FRONTEND_ACCEPTANCE_PIDFILE']).exists():
        raise ValueError('disposable frontend pidfile already exists')
    for key in ('ODOO_PORT', 'BACKEND_ACCEPTANCE_PORT', 'FRONTEND_ACCEPTANCE_PORT'):
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', int(profile[key])))


def write_credentials(path, head):
    values = dict(ENV='dev', DB_USER='odoo', DB_PASSWORD=secrets.token_hex(32),
                  ADMIN_PASSWD=secrets.token_hex(32), JWT_SECRET=secrets.token_hex(32),
                  SC_BOOTSTRAP_SECRET=secrets.token_hex(32),
                  SC_BOOTSTRAP_LOGIN='frontend_release_local', SCENE_CHANNEL='stable',
                  SCENE_USE_PINNED='0', SCENE_ROLLBACK='0', SC_SOURCE_REVISION=head,
                  SC_ACCEPTANCE_FIXTURE_PASSWORD=secrets.token_hex(24),
                  SC_ACCEPTANCE_FIXTURE_SCOPE='acceptance')
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as stream:
        stream.write(''.join(f'{key}={value}\n' for key, value in values.items()))
    return values



def offline_stage(stage, args):
    """Reuse only exact-head offline results; runtime assertions always execute."""
    if stage not in ('unit', 'static') or not args:
        raise ValueError('unsupported offline checkpoint')
    env = os.environ.copy()
    if env.get('SC_ACCEPTANCE_RUNTIME_PROFILE') != 'disposable':
        raise ValueError('checkpoint requires the disposable runtime')
    head = command(['git', 'rev-parse', 'HEAD'], env, capture=True).stdout.strip()
    if command(['git', 'status', '--porcelain'], env, capture=True).stdout.strip():
        raise ValueError('checkpoint requires a clean source')
    identity = dict(head=head, command=args, profile=resolve('disposable'))
    def outputs():
        if stage == 'unit':
            return {}
        paths = [ROOT / 'artifacts/frontend-release-audit/static.json']
        paths.extend(sorted((ROOT / 'frontend/apps/web/dist').rglob('*')))
        return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in paths if path.is_file()}
    checkpoint = STATE / (stage + '.json')
    previous = json.loads(checkpoint.read_text()) if checkpoint.exists() else {}
    if previous.get('identity') == identity and previous.get('outputs') == outputs() and previous.get('passed'):
        print('[release.disposable] REUSED exact-head ' + stage, flush=True)
        return 0
    status = command(args, env, check=False).returncode
    checkpoint.write_text(json.dumps(dict(identity=identity, passed=status == 0,
                                          outputs=outputs()), indent=2) + '\n')
    return status


def main(probe=False):
    env = {key: os.environ[key] for key in ('PATH', 'HOME', 'DOCKER_CONFIG', 'XDG_RUNTIME_DIR')
           if key in os.environ}
    if command(['git', 'status', '--porcelain'], env, capture=True).stdout.strip():
        raise ValueError('freeze a clean candidate before the disposable full release')
    head = command(['git', 'rev-parse', 'HEAD'], env, capture=True).stdout.strip()
    profile = resolve('disposable')
    common = Path(command(['git', 'rev-parse', '--path-format=absolute', '--git-common-dir'],
                          env, capture=True).stdout.strip())
    with (common / 'frontend-release-disposable.lock').open('w') as lease:
        fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
        owner_path = STATE / 'owner.json'
        owner = json.loads(owner_path.read_text()) if owner_path.exists() else None
        if owner is not None and (owner.get('root') != str(ROOT) or owner.get('profile') != profile):
            raise ValueError('retained environment belongs to another checkout or profile')
        if owner is None:
            require_absent(profile, env)
        # Docker creates a missing bind source as root. Prepare host evidence
        # before provisioning so the local audit can write its reports.
        artifacts = ROOT / 'artifacts'
        if artifacts.is_symlink():
            raise ValueError('artifact output must not be a symlink')
        artifacts.mkdir(exist_ok=True)
        if not os.access(artifacts, os.W_OK):
            raise ValueError('artifact output is not writable by the local runner')
        STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
        credential_path = Path(profile['SC_ACCEPTANCE_BASE_ENV_FILE'])
        if owner is None:
            credentials = write_credentials(credential_path, head)
            owner = dict(root=str(ROOT), profile=profile, provisioned=False)
        else:
            if credential_path.is_symlink() or credential_path.stat().st_uid != os.getuid() or credential_path.stat().st_mode & 0o777 != 0o600:
                raise ValueError('retained credentials have unsafe owner or mode')
            content = credential_path.read_text()
            if hashlib.sha256(content.encode()).hexdigest() != owner.get('credential_sha256'):
                raise ValueError('retained credential authority changed')
            credentials = {}
            for line in content.splitlines():
                if not re.fullmatch(r'[A-Z_]+=[a-zA-Z0-9_]+', line):
                    raise ValueError('retained credentials contain unexpected syntax')
                key, value = line.split('=', 1)
                credentials[key] = value
            credentials['SC_SOURCE_REVISION'] = head
            credential_path.write_text(''.join(f'{key}={value}\n' for key, value in credentials.items()))
        owner['credential_sha256'] = hashlib.sha256(credential_path.read_bytes()).hexdigest()
        owner['head'] = head
        owner_path.write_text(json.dumps(owner, indent=2) + '\n')
        env.update(profile)
        env.update(credentials)
        env.update(CONFIRM_FRONTEND_RELEASE_AUDIT='RUN_FROZEN_FRONTEND_RELEASE_AUDIT',
                   CONFIRM_ACCEPTANCE_CARRIER_PROVISION='PROVISION_MANAGED_ACCEPTANCE_CARRIER',
                   CONFIRM_ACCEPTANCE_CARRIER_DISCARD='DISCARD_MANAGED_ACCEPTANCE_CARRIER',
                   SC_ACCEPTANCE_PROFILE='local',
                   SC_RELEASE_STAGE_RUNNER='python3 scripts/dev/frontend_release_disposable.py --stage',
                   FRONTEND_URL=f"http://127.0.0.1:{profile['FRONTEND_ACCEPTANCE_PORT']}",
                   ODOO_URL=f"http://127.0.0.1:{profile['BACKEND_ACCEPTANCE_PORT']}",
                   SC_ACCEPTANCE_INTENT_URL=f"http://127.0.0.1:{profile['BACKEND_ACCEPTANCE_PORT']}/api/v1/intent",
                   ENV_FILE=str(credential_path))
        result = 1
        cleanup = []
        try:
            if not owner.get('provisioned'):
                command(['make', '--no-print-directory', 'acceptance.runtime.carrier.provision'], env)
                owner['provisioned'] = True
                owner_path.write_text(json.dumps(owner, indent=2) + '\n')
            command(['make', '--no-print-directory', 'acceptance.runtime.preflight'], env)
            target = 'verify.frontend.delivery_hardening.release.browser' if probe else 'verify.frontend.release.local'
            result = command(['make', '--no-print-directory', target],
                             env, check=False).returncode
            if result == 0 and not probe:
                result = command(['make', '--no-print-directory', 'acceptance.frontend.fixture_orm'],
                                 env, check=False).returncode
        finally:
            unchanged = command(['git', 'rev-parse', 'HEAD'], env, capture=True).stdout.strip() == head
            unchanged &= not command(['git', 'status', '--porcelain'], env, capture=True).stdout.strip()
            if not unchanged:
                result = 1
            targets = ('frontend.acceptance.down', 'backend.acceptance.down',
                       'acceptance.runtime.carrier.discard') if result == 0 and not probe else ()
            for target in targets:
                status = command(['make', '--no-print-directory', target], env, check=False).returncode
                cleanup.append(dict(target=target, status=status))
            absent = False
            if result == 0 and not probe:
                try:
                    require_absent(profile, env)
                    absent = True
                except (ValueError, OSError):
                    pass
            receipt = dict(head=head, project=profile['COMPOSE_PROJECT_NAME'],
                           database=profile['DB_NAME'], release_status=result, probe_only=probe,
                           cleanup=cleanup, resources_absent=absent, source_unchanged=unchanged)
            (STATE / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
            if absent:
                credential_path.unlink()
                owner_path.unlink()
            elif result != 0 or probe:
                print('[release.disposable] RETAINED environment and credentials for retry', flush=True)
            if not unchanged or (result == 0 and not probe and (not absent or any(item['status'] for item in cleanup))):
                result = 1
            print('[release.disposable] receipt=' + str(STATE / 'receipt.json'), flush=True)
        return result


if __name__ == '__main__':
    try:
        if len(sys.argv) > 2 and sys.argv[1] == '--stage':
            raise SystemExit(offline_stage(sys.argv[2], sys.argv[3:]))
        raise SystemExit(main(probe=sys.argv[1:] == ["--probe"]))
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        # Never print subprocess argv/environment: it can contain credentials.
        print('[release.disposable] FAIL ' + (str(exc) if isinstance(exc, ValueError) else type(exc).__name__))
        raise SystemExit(2)
