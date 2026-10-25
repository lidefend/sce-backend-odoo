#!/usr/bin/env python3
"""Single governed owner of the registered disposable sc_test database.

Credentials come only from the existing private profile. No shell sourcing,
recursive Make overrides, persistent application server, or retry-to-green.
"""
from __future__ import annotations
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
ORDER_DRIVER = ROOT / 'scripts/test/odoo_ordered_tests.py'
PROFILE = Path('/home/lidefend/workspace/sce-backend-odoo/.env.local.test')
IDENTITY = dict(ENV='dev', COMPOSE_PROJECT_NAME='sc-local-test', DB_NAME='sc_test',
    DB_USER='sc_test_odoo', ODOO_DBFILTER='^sc_test$', DB_DATA='sc_local_test_db_data',
    REDIS_DATA='sc_local_test_redis_data', ODOO_DATA='sc_local_test_odoo_data',
    NGINX_PORT='18084', ODOO_PORT='8073', SC_ALLOW_DEMO_DATA='0', ISOLATED_REHEARSAL_DATABASE='1')
START = re.compile(r' INFO sc_test odoo\.addons\.([\w.]+): Starting ([\w.]+) \.\.\.')


def profile(path: Path) -> dict:
    if path != PROFILE or path.is_symlink() or not path.is_file():
        raise ValueError('registered local.test credential file required')
    if path.stat().st_mode & 0o077:
        raise ValueError('private credential file must have mode600')
    values = {}
    for line in path.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        key, sep, raw = line.partition('=')
        if not sep or not re.fullmatch('[A-Z][A-Z0-9_]*', key) or key in values:
            raise ValueError('invalid or duplicate profile entry')
        parts = shlex.split(raw, comments=False)
        if len(parts) != 1 or any(c in parts[0] for c in ('`', '\n', '\r')) or '$(' in raw:
            raise ValueError('profile must contain literal values')
        values[key] = parts[0]
    for key, expected in IDENTITY.items():
        if values.get(key) != expected:
            raise ValueError('foreign local.test identity: ' + key)
    # Older registered credentials use dev. Every test carrier is forced to test
    # explicitly; never rewrite credentials or source the profile as shell code.
    if values.get('SC_ENVIRONMENT') not in ('dev', 'test'):
        raise ValueError('invalid test purpose')
    for key in ('DB_PASSWORD', 'ADMIN_PASSWD', 'JWT_SECRET'):
        if not values.get(key):
            raise ValueError('missing registered secret')
    return values


def selection(module: str, tags: str) -> tuple[str, str]:
    if not re.fullmatch('[a-z][a-z0-9_]*', module):
        raise ValueError('one explicit MODULE is required before any runtime write')
    if not any((ROOT / folder / module / '__manifest__.py').is_file() for folder in ('addons', 'demo_addons')):
        raise ValueError('unknown repository module')
    tags = tags or '/' + module
    if not re.fullmatch(r'[a-zA-Z0-9_.,/+:@-]+', tags):
        raise ValueError('invalid TEST_TAGS')
    return module, tags


def command(argv, env, *, capture=True):
    return subprocess.run(argv, cwd=ROOT, env=env, text=True, capture_output=capture, check=True)


def compose_config(config: dict) -> None:
    if config.get('name') != 'sc-local-test':
        raise ValueError('foreign compose project')
    for key, name in [('db_data', 'sc_local_test_db_data'), ('redis_data', 'sc_local_test_redis_data'),
                      ('odoo_data', 'sc_local_test_odoo_data')]:
        item = config['volumes'][key]
        if item.get('name') != name or item.get('external'):
            raise ValueError('foreign or external volume')
    db = config['services']['db']
    if db['environment'].get('POSTGRES_DB') != 'sc_test' or db['environment'].get('POSTGRES_USER') != 'sc_test_odoo':
        raise ValueError('foreign database config')
    data_mounts = [x for x in db['volumes'] if x['target'] == '/var/lib/postgresql/data']
    if len(data_mounts) != 1 or data_mounts[0].get('type') != 'volume' or data_mounts[0].get('source') != 'db_data':
        raise ValueError('foreign database mount')
    mounts = {x['target']: x for x in config['services']['odoo']['volumes']}
    for target, source in [('/mnt/source-addons', ROOT / 'addons'), ('/mnt/scripts', ROOT / 'scripts'),
                           ('/mnt/demo-addons', ROOT / 'demo_addons'),
                           ('/mnt/addons_external', ROOT / 'addons_external')]:
        if Path(mounts[target]['source']).resolve() != source.resolve():
            raise ValueError('stale candidate bind mount')


def outcome(log: str, module: str) -> list[str]:
    starts = [f'{m}:{case}' for m, case in START.findall(log)]
    if not starts or len(starts) != len(set(starts)):
        raise ValueError('missing or duplicate executed test identities')
    if not any(x.startswith(module + '.tests.') for x in starts):
        raise ValueError('requested module executed no tests')
    return sorted(starts)


def source_fingerprint(env):
    paths = command(['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'], env).stdout.split('\0')
    digest = hashlib.sha256()
    for name in sorted(set(paths) - {''}):
        path = ROOT / name
        digest.update(name.encode() + b'\0')
        if path.is_symlink():
            digest.update(b'link:' + os.readlink(path).encode())
        elif path.is_file():
            digest.update(str(path.stat().st_mode & 0o777).encode() + path.read_bytes())
        else:
            digest.update(b'missing')
    return digest.hexdigest()


def cleanup_carrier(name, env):
    found = command(['docker', 'ps', '-aq', '--filter', 'name=^/' + name + '$'], env).stdout.strip()
    if not found:
        return 'absent'
    rows = json.loads(command(['docker', 'inspect', found], env).stdout)
    if len(rows) != 1 or rows[0].get('Name') != '/' + name:
        raise ValueError('carrier cleanup identity mismatch')
    labels = rows[0]['Config'].get('Labels') or {}
    if labels.get('com.docker.compose.project') != 'sc-local-test' or labels.get('com.docker.compose.service') != 'odoo':
        raise ValueError('carrier cleanup owner mismatch')
    command(['docker', 'rm', '-f', rows[0]['Id']], env)
    if command(['docker', 'ps', '-aq', '--filter', 'name=^/' + name + '$'], env).stdout.strip():
        raise ValueError('carrier remains after cleanup')
    return 'removed_exact_carrier'


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('action', choices=['prepare', 'up', 'down', 'test'])
    ap.add_argument('--env-file', type=Path, default=PROFILE)
    ap.add_argument('--module', default='')
    ap.add_argument('--tags', default='')
    ap.add_argument('--order', choices=['forward','reverse','random'], default='forward')
    args = ap.parse_args(argv)
    try:
        if not ORDER_DRIVER.is_file() or ORDER_DRIVER.is_symlink():
            raise ValueError('ordered test driver missing or unsafe')
        module, tags = selection(args.module, args.tags) if args.action == 'test' else ('', '')
        values = profile(args.env_file)
        profile_sha = hashlib.sha256(PROFILE.read_bytes()).hexdigest()
        env = {k: os.environ[k] for k in ('PATH', 'HOME', 'DOCKER_HOST', 'DOCKER_CONFIG') if k in os.environ}
        env.update(values, ENV_FILE=str(PROFILE), SC_ENVIRONMENT='test', SC_ALLOW_DEMO_DATA='0')
        dc = ['docker', 'compose', '--env-file', str(PROFILE), '-p', 'sc-local-test', '-f', str(ROOT / 'docker-compose.yml')]
        config = json.loads(command(dc + ['config', '--format', 'json'], env).stdout)
        compose_config(config)
        # A fixed lock in the shared Git directory serializes all linked worktrees.
        common = Path(command(['git', 'rev-parse', '--git-common-dir'], env).stdout.strip()).resolve()
        with (common / 'local-test.lock').open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            # Existing named resources must be owned by this exact project.
            for name in (IDENTITY['DB_DATA'], IDENTITY['REDIS_DATA'], IDENTITY['ODOO_DATA']):
                found = command(['docker', 'volume', 'ls', '--filter', 'name=^' + name + '$', '--format', '{{.Name}}'], env).stdout.strip()
                if found:
                    rows = json.loads(command(['docker', 'volume', 'inspect', name], env).stdout)
                    if len(rows) != 1 or (rows[0].get('Labels') or {}).get('com.docker.compose.project') != 'sc-local-test':
                        raise ValueError('unowned test volume')
            running = command(['docker', 'ps', '--filter', 'label=com.docker.compose.project=sc-local-test', '--format', '{{.Label "com.docker.compose.service"}}'], env).stdout.splitlines()
            if set(running) - {'db', 'redis'}:
                raise ValueError('concurrent application/test carrier; no database mutation allowed')
            if args.action == 'prepare':
                print('[local.test] validated registered identity; no runtime writes')
                return 0
            if args.action == 'down':
                command(dc + ['stop', 'db', 'redis'], env)
                return 0
            command(dc + ['up', '-d', '--wait', 'db', 'redis'], env)
            if args.action == 'up':
                return 0
            # Exact disposable target only. DB and volume names cannot be overridden.
            actual = command(dc + ['exec', '-T', 'db', 'psql', '-U', 'sc_test_odoo', '-d', 'postgres', '-Atc', 'SELECT current_user'], env).stdout.strip()
            if actual != 'sc_test_odoo':
                raise ValueError('database role readback mismatch')
            command(dc + ['exec', '-T', 'db', 'dropdb', '-U', 'sc_test_odoo', '--if-exists', 'sc_test'], env)
            output = ROOT / '.runtime/test-baseline' / str(time.time_ns())
            output.mkdir(parents=True)
            log = output / 'odoo.log'
            image_id = command(['docker','image','inspect',config['services']['odoo']['image'],'--format','{{.Id}}'],env).stdout.strip()
            source_before = source_fingerprint(env)
            head_before = command(['git','rev-parse','HEAD'],env).stdout.strip()
            carrier = 'sc-local-test-attempt-' + output.name
            # Transient data-dir prevents prior filestore/sessions/config leakage.
            script = '''set -euo pipefail
python3 -m pip install -q -r /mnt/config/requirements-test.txt
python3 -c 'import importlib.metadata as m,hashlib; print("LOCAL_TEST_PACKAGES="+hashlib.sha256("\\n".join(sorted(d.metadata["Name"]+"=="+d.version for d in m.distributions())).encode()).hexdigest())'
python3 -c 'import os; assert os.environ["DB_NAME"]=="sc_test" and os.environ["SC_ENVIRONMENT"]=="test" and os.environ["SC_ALLOW_DEMO_DATA"]=="0"; print("LOCAL_TEST_IDENTITY=sc-local-test/sc_test/test")'
exec python3 /tmp/odoo_ordered_tests.py --db_host=db --db_port=5432 --db_user="$DB_USER" --db_password="$DB_PASSWORD" -d sc_test --db-filter='^sc_test$' --data-dir=/tmp/sc-test-data --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/source-addons,/mnt/demo-addons,/mnt/addons_external/oca_server_ux -i "$SC_TEST_MODULE" --without-demo=all --no-http --workers=0 --max-cron-threads=0 --test-enable --test-tags="$SC_TEST_TAGS" --stop-after-init --log-level=test
'''
            run = dc + ['run', '--name', carrier, '--rm', '--no-deps', '-T', '-v', str(ORDER_DRIVER) + ':/tmp/odoo_ordered_tests.py:ro', '-v', str(ROOT / 'config') + ':/mnt/config:ro', '-e', 'SC_ENVIRONMENT=test', '-e', 'SC_ALLOW_DEMO_DATA=0', '-e', 'SC_TEST_ORDER=' + args.order, '-e', 'SC_TEST_ORDER_SEED=20261026', '-e', 'SC_TEST_MODULE=' + module, '-e', 'SC_TEST_TAGS=' + tags, '--entrypoint', 'bash', 'odoo', '-ec', script]
            process_status = 1
            cleanup = 'not_run'
            try:
                with log.open('w') as stream:
                    result = subprocess.run(run, cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=7200)
                    process_status = result.returncode
            except subprocess.TimeoutExpired:
                process_status = 124
            except OSError:
                process_status = 127
            finally:
                try:
                    cleanup = cleanup_carrier(carrier, env)
                except (ValueError, OSError, subprocess.SubprocessError):
                    cleanup = 'failed'
                    process_status = 1
            text = log.read_text()
            for key in ('DB_PASSWORD', 'ADMIN_PASSWD', 'JWT_SECRET', 'SC_BOOTSTRAP_SECRET'):
                if values.get(key): text = text.replace(values[key], '[REDACTED]')
            log.write_text(text)
            guard_env = dict(env, orm_expect_database='sc_test', orm_expect_identity=module + '.tests.')
            guard = subprocess.run(['bash', '-c', 'source scripts/ci/orm_result_guard.sh; evaluate_orm_outcome "$1" "$2"', 'guard', str(process_status), str(log)], cwd=ROOT, env=guard_env, capture_output=True, text=True)
            source_after = source_fingerprint(env)
            profile_unchanged = profile_sha == hashlib.sha256(PROFILE.read_bytes()).hexdigest()
            image_after = command(['docker','image','inspect',config['services']['odoo']['image'],'--format','{{.Id}}'],env).stdout.strip()
            try:
                cases = outcome(text, module) if guard.returncode == 0 and source_before == source_after and image_id == image_after and profile_unchanged else []
            except ValueError:
                cases = []
            receipt = dict(schema='local-test-execution/v1', head=head_before, source_fingerprint=source_before, source_unchanged=source_before == source_after, cleanup=cleanup,
                dirty=command(['git','status','--porcelain'],env).stdout, profile=IDENTITY, purpose='test',
                profile_sha256=profile_sha, profile_unchanged=profile_unchanged, image_id=image_id, image_unchanged=image_id == image_after, module=module, tags=tags, order=args.order, seed=20261026, execution_order=[f'{m}:{case}' for m,case in START.findall(text)], packages_sha256=(re.findall(r'^LOCAL_TEST_PACKAGES=([a-f0-9]{64})$',text,re.M) or ['missing'])[0], fresh_database=True, transient_application_state=True,
                cases=cases, count=len(cases), status='passed' if cases else 'failed', log=str(log.relative_to(ROOT)),
                log_sha256=hashlib.sha256(log.read_bytes()).hexdigest(), process_status=process_status, guard_status=guard.returncode)
            (output / 'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
            print(guard.stdout, guard.stderr, '[local.test] receipt=' + str(output / 'receipt.json'), sep='\n')
            return 0 if cases else 1
    except (ValueError, KeyError, OSError, subprocess.SubprocessError) as exc:
        # Never echo subprocess argv, env or stderr: they can contain credentials.
        print('[local.test] BLOCKED ' + (str(exc) if isinstance(exc, ValueError) else type(exc).__name__))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
