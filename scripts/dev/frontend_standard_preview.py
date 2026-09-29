#!/usr/bin/env python3
"""Bounded continuation of the owner's existing 5180 static preview."""
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT.parent / 'sce-offrepo/artifacts/auth03-20260929'
DIST = OUTPUT / 'dist'
PREVIOUS = ROOT.parent / 'sce-offrepo/artifacts/auth02-20260929/dist'
INPUTS = ['frontend', ':!frontend/apps/web/scripts']


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


def inputs(base):
    if git('ls-files', '--others', '--exclude-standard', '--', *INPUTS).strip():
        raise RuntimeError('untracked frontend build inputs must be reviewed and staged')
    return hashlib.sha256(git('diff', '--binary', base, '--', *INPUTS)).hexdigest()


def identity(*, observed_only=False):
    saved = json.loads((OUTPUT / 'build-identity.json').read_text())
    if not observed_only and inputs(saved['base_sha']) != saved['diff_sha256']:
        raise RuntimeError('preview build inputs changed')
    html = (DIST / 'index.html').read_bytes()
    if hashlib.sha256(html).hexdigest() != saved['index_sha256']:
        raise RuntimeError('preview index changed')
    if hashlib.sha256((DIST / saved['entry'].lstrip('/')).read_bytes()).hexdigest() != saved['entry_sha256']:
        raise RuntimeError('preview entry changed')
    return saved


def validate_listener(environment, command, owner, current_only=False):
    if owner != os.getuid() or 'scripts/release/release_static_server.mjs' not in command:
        raise RuntimeError('preview process owner/command mismatch')
    if environment.get('STATIC_ROOT') not in {str(PREVIOUS), str(DIST)}:
        raise RuntimeError('preview belongs to a different candidate')
    if current_only and environment.get('STATIC_ROOT') != str(DIST):
        raise RuntimeError('browser requires the current candidate')
    if environment.get('STATIC_PORT') != '5180' or environment.get('API_PROXY_TARGET') != 'http://127.0.0.1:18082':
        raise RuntimeError('preview port/proxy mismatch')
    return environment['STATIC_ROOT']


def main():
    if os.environ.get('SC_FRONTEND_ACCEPTANCE_RUNTIME_ENTRY') != 'operation_entry_v1':
        raise RuntimeError('use the governed Make entry')
    if os.environ.get('DB_NAME') != 'sc_frontend_acceptance' or os.environ.get('COMPOSE_PROJECT_NAME') != 'sc-fe-r2-p1-01':
        raise RuntimeError('managed profile mismatch')
    operation = sys.argv[1]
    if operation == 'build':
        if (OUTPUT / 'build-identity.json').exists():
            identity()
            print('[standard.preview] REUSED unchanged build')
            return
        OUTPUT.mkdir(parents=True, exist_ok=True)
        base = git('rev-parse', 'HEAD').decode().strip()
        before = inputs(base)
        build_env = dict(os.environ, FRONTEND_DIST_DIR=str(DIST), VITE_ODOO_DB='sc_frontend_acceptance', VITE_ODOO_DB_LOCKED='1', VITE_APP_ENV='acceptance')
        subprocess.run(['bash', str(ROOT / 'scripts/dev/frontend_static_build.sh')], env=build_env, check=True)
        if inputs(base) != before:
            raise RuntimeError('source changed during build')
        html = (DIST / 'index.html').read_bytes()
        entry = re.search(rb'src="(/assets/index-[^"]+\.js)"', html).group(1).decode()
        receipt = {'base_sha': base, 'dirty_scope': git('status', '--short').decode(), 'diff_sha256': before,
                   'index_sha256': hashlib.sha256(html).hexdigest(), 'entry': entry,
                   'entry_sha256': hashlib.sha256((DIST / entry.lstrip('/')).read_bytes()).hexdigest()}
        (OUTPUT / 'build-identity.json').write_text(json.dumps(receipt, indent=2))
    elif operation == 'up':
        identity()
        result = subprocess.check_output(['ss', '-ltnp', 'sport = :5180']).decode()
        pids = re.findall(r'pid=(\d+)', result)
        previous = None
        if pids:
            if len(pids) != 1:
                raise RuntimeError('ambiguous preview listener')
            proc = Path('/proc') / pids[0]
            environment = dict(item.split('=', 1) for item in (proc / 'environ').read_text().split('\0') if '=' in item)
            previous = validate_listener(environment, (proc / 'cmdline').read_text(), proc.stat().st_uid)
            if previous == str(DIST):
                print('[standard.preview] REUSED current 5180 listener')
                return
            os.kill(int(pids[0]), signal.SIGTERM)
            for _ in range(50):
                if not re.search(r'pid=\d+', subprocess.check_output(['ss', '-ltnp', 'sport = :5180']).decode()):
                    break
                time.sleep(0.1)
            else:
                raise RuntimeError('previous preview did not release 5180')
        runtime_env = dict(os.environ, FRONTEND_ACCEPTANCE_PORT='5180', FRONTEND_ACCEPTANCE_MODE='production',
                           FRONTEND_ACCEPTANCE_STATIC_DIST=str(DIST), FRONTEND_ACCEPTANCE_PIDFILE=str(OUTPUT / 'preview.pid'),
                           FRONTEND_ACCEPTANCE_LOGFILE=str(OUTPUT / 'preview.log'))
        command = ['bash', str(ROOT / 'scripts/dev/frontend_acceptance_up.sh')]
        try:
            subprocess.run(command, env=runtime_env, check=True)
        except subprocess.CalledProcessError:
            if previous:
                runtime_env['FRONTEND_ACCEPTANCE_STATIC_DIST'] = previous
                subprocess.run(command, env=runtime_env, check=True)
            raise
    elif operation in {'identity', 'observed-identity'}:
        pids = re.findall(r'pid=(\d+)', subprocess.check_output(['ss', '-ltnp', 'sport = :5180']).decode())
        if len(pids) != 1:
            raise RuntimeError('browser requires one live preview listener')
        proc = Path('/proc') / pids[0]
        environment = dict(item.split('=', 1) for item in (proc / 'environ').read_text().split('\0') if '=' in item)
        validate_listener(environment, (proc / 'cmdline').read_text(), proc.stat().st_uid, current_only=True)
        print(json.dumps(identity(observed_only=operation == 'observed-identity')))
    else:
        raise RuntimeError('unknown bounded preview operation')


if __name__ == '__main__':
    main()
