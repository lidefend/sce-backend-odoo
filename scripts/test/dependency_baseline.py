#!/usr/bin/env python3
"""Prepare pristine dependency clones only inside one ephemeral CI shard.

No successful test state is ever used as a template. Target installation and
its at_install/post_install tests still run through the normal test entrypoint.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

CORE = 'smart_construction_core'
ROOTS = (Path('/mnt/source-addons'), Path('/mnt/demo-addons'))
DATA = Path('/var/lib/odoo')


def eligible(module: str, roots=ROOTS) -> bool:
    if module in (CORE, 'smart_construction_demo'):
        return False
    pending, seen = [module], set()
    while pending:
        name = pending.pop()
        if name in seen:
            continue
        if not re.fullmatch(r'[a-zA-Z_][a-zA-Z_0-9]*', name):
            raise ValueError('invalid manifest dependency')
        seen.add(name)
        if name == CORE:
            return True
        manifests = [root / name / '__manifest__.py' for root in roots]
        existing = [path for path in manifests if path.is_file()]
        if len(existing) > 1:
            raise ValueError('ambiguous addon')
        if not existing:  # external Odoo addons cannot depend on this industry addon
            continue
        manifest = ast.literal_eval(existing[0].read_text())
        dependencies = manifest.get('depends', [])
        if not isinstance(dependencies, list) or not all(isinstance(x, str) for x in dependencies):
            raise ValueError('invalid manifest dependencies')
        pending.extend(dependencies)
    return False


def identity(env: dict) -> dict:
    run, attempt, shard = (env.get(k, '') for k in ('GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT', 'SHARD_INDEX'))
    head = env.get('SOURCE_SHA', '')
    if not all(re.fullmatch(r'[0-9]+', v) for v in (run, attempt, shard)):
        raise ValueError('preparation requires exact CI run/attempt/shard')
    if not re.fullmatch('[0-9a-f]{40}', head):
        raise ValueError('preparation requires exact source SHA')
    if env.get('COMPOSE_PROJECT_NAME') != f'sc-suite-{run}-{shard}':
        raise ValueError('not an isolated backend suite project')
    if env.get('SC_ENVIRONMENT') != 'test' or env.get('SC_ALLOW_DEMO_DATA', '') not in ('', '0'):
        raise ValueError('dependency preparation requires non-demo test environment')
    module, database = env.get('SC_TEST_TARGET_MODULE', ''), env.get('SC_TEST_TARGET_DB', '')
    if not re.fullmatch('[a-zA-Z_][a-zA-Z_0-9]*', module):
        raise ValueError('invalid target module')
    if database not in (f'sc_suite_ci_{module}', f'sc_suite_ci_{module}_retry1') or len(database) > 63:
        raise ValueError('invalid isolated target database')
    return dict(run=run, attempt=attempt, shard=shard, head=head, dependency=CORE,
                demo=False, schema=1)


def prepare(env: dict) -> None:
    module = env.get('SC_TEST_TARGET_MODULE', '')
    # Demo has a separate authority and must always use a fresh installation.
    if module == 'smart_construction_demo':
        print('DEPENDENCY_PREPARATION=clean reason=demo', flush=True)
        return
    key = identity(env)
    if not eligible(module):
        print('DEPENDENCY_PREPARATION=clean reason=no_shared_dependency', flush=True)
        return
    import psycopg2
    from psycopg2 import sql

    started = time.monotonic()
    digest = hashlib.sha256(json.dumps(key, sort_keys=True).encode()).hexdigest()[:24]
    baseline = 'sc_suite_prep_' + digest
    target = env['SC_TEST_TARGET_DB']
    directory = DATA / 'ci-dependency-preparation'
    directory.mkdir(exist_ok=True)
    marker = directory / (baseline + '.json')
    connection = psycopg2.connect(host='db', port=5432, user=env['DB_USER'],
                                  password=env['DB_PASSWORD'], dbname='postgres')
    connection.autocommit = True
    with connection.cursor() as cursor:
        cursor.execute('SELECT datname FROM pg_database WHERE datname IN (%s, %s)', (baseline, target))
        existing = {row[0] for row in cursor.fetchall()}
        if target in existing or (DATA / 'filestore' / target).exists():
            raise ValueError('target must be new; refusing to overwrite database or filestore')
        if baseline in existing:
            if not marker.is_file() or json.loads(marker.read_text()) != key:
                raise ValueError('unproven or incomplete dependency baseline')
            prepared = False
        else:
            if marker.exists() or (DATA / 'filestore' / baseline).exists():
                raise ValueError('orphaned baseline state')
            command = ['/usr/bin/odoo', '--db_host=db', '--db_port=5432',
                       '--db_user=' + env['DB_USER'], '--db_password=' + env['DB_PASSWORD'],
                       '-d', baseline, '--db-filter=^' + baseline + '$',
                       '--data-dir=' + str(DATA),
                       '--addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/source-addons,/mnt/demo-addons,'
                       + env.get('ADDONS_EXTERNAL_MOUNT', '/mnt/addons_external/oca_server_ux'),
                       '-i', CORE, '--without-demo=all', '--no-http', '--workers=0',
                       '--max-cron-threads=0', '--stop-after-init', '--log-level=info']
            # Deliberately no --test-enable or --test-tags. Never seed from a test DB.
            outcome = subprocess.run(command, check=False)
            if outcome.returncode:
                # Do not include argv: it contains the existing database credential.
                raise RuntimeError('dependency installation failed: exit ' + str(outcome.returncode))
            marker.write_text(json.dumps(key, sort_keys=True) + '\n')
            prepared = True
        # Read the pristine database before cloning. An auto-install that already
        # installed the target would suppress its hooks/tests, so reject it.
        with psycopg2.connect(host='db', port=5432, user=env['DB_USER'],
                              password=env['DB_PASSWORD'], dbname=baseline) as check:
            with check.cursor() as probe:
                probe.execute('SELECT name, state FROM ir_module_module WHERE name IN (%s, %s)', (CORE, module))
                states = dict(probe.fetchall())
                if states.get(CORE) != 'installed' or states.get(module) != 'uninstalled':
                    raise ValueError('baseline must contain installed dependency and uninstalled target')
        check.close()
        cursor.execute(sql.SQL('CREATE DATABASE {} WITH TEMPLATE {} OWNER {}').format(
            sql.Identifier(target), sql.Identifier(baseline), sql.Identifier(env['DB_USER'])))
        source = DATA / 'filestore' / baseline
        if source.exists():
            shutil.copytree(source, DATA / 'filestore' / target)
    connection.close()
    print('DEPENDENCY_PREPARATION=' + json.dumps(dict(key, baseline=baseline,
          target=target, installed=prepared, elapsed_seconds=round(time.monotonic()-started, 3)),
          sort_keys=True), flush=True)


if __name__ == '__main__':
    prepare(dict(os.environ))
