#!/usr/bin/env python3
"""Read-only developer readiness; optional absence is not a passed runtime test."""
from __future__ import annotations

import argparse
import json
import subprocess
import shlex
import re
from pathlib import Path

PROFILES = {
    'dev': ('sc-local-dev', 'sc_dev_demo', 'sc_local_dev', True),
    'sample': ('sc-local-sample', 'sc_dev_sample', 'sc_local_sample', False),
    'clean': ('sc-local-clean', 'sc_clean', 'sc_local_clean', False),
}


def command(args):
    return subprocess.run(args, text=True, capture_output=True, check=False)


def inspect_profile(name, env_file, root, runner=command):
    project, database, volume_prefix, required = PROFILES[name]
    row = dict(profile=name, project=project, database=database, required=required,
               status='failed', health='not_run')
    # Query stopped containers too: missing credentials must never imply empty data.
    queries = [['docker', 'ps', '-a', '--filter', f'label=com.docker.compose.project={project}', '--format', '{{.ID}}']]
    queries += [['docker', 'volume', 'ls', '--filter', f'name=^{volume_prefix}_{part}_data$', '--format', '{{.Name}}'] for part in ('db', 'redis', 'odoo')]
    outputs = []
    for query in queries:
        result = runner(query)
        if result.returncode:
            return {**row, 'reason': 'resource_inventory_failed'}
        outputs.append(result.stdout.strip())
    if not env_file.is_file():
        if any(outputs):
            return {**row, 'reason': 'credential_authority_missing_with_existing_resources'}
        return {**row, 'status': 'failed' if required else 'not_prepared',
                'reason': 'required_profile_missing' if required else 'on_demand_profile_not_provisioned'}
    # clean.health also supports other isolated profiles, so bind canonical identity here first.
    expected = {'ENV': 'dev', 'COMPOSE_PROJECT_NAME': project, 'DB_NAME': database,
                'ODOO_DBFILTER': f'^{database}$',
                **{key: f'{volume_prefix}_{part}_data' for key, part in
                   (('DB_DATA', 'db'), ('REDIS_DATA', 'redis'), ('ODOO_DATA', 'odoo'))}}
    if name == 'clean':
        expected['ISOLATED_REHEARSAL_DATABASE'] = '1'
    if name == 'sample':
        expected['TECHNICAL_SAMPLE_DATABASE'] = '1'
    values = {}
    try:
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            assignment = re.fullmatch(r'(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)=(.*)', line)
            if not assignment:
                return {**row, 'reason': 'unsupported_environment_syntax'}
            key, value = assignment.groups()
            # Managed env files are literal assignments, not executable shell programs.
            if re.search(r'\$[A-Za-z_0-9{(?!*#@-]', value) or any(token in value for token in ('`', ';', '|', '&', '<', '>')):
                return {**row, 'reason': 'unsupported_environment_syntax'}
            tokens = shlex.split(value, comments=True)
            if len(tokens) > 1:
                return {**row, 'reason': 'unsupported_environment_syntax'}
            if key in expected:
                if key in values or len(tokens) != 1:
                    return {**row, 'reason': 'ambiguous_profile_identity'}
                values[key] = tokens[0]
    except (OSError, ValueError):
        return {**row, 'reason': 'profile_identity_unreadable'}
    if any(values.get(key) != value for key, value in expected.items()):
        return {**row, 'reason': 'profile_identity_mismatch'}
    # Never source or print credentials here. Existing health entry owns runtime assertions.
    result = runner(['make', '--no-print-directory', '-C', str(root),
                     f'local.{name}.health', f'LOCAL_{name.upper()}_ENV_FILE={env_file}'])
    return {**row, 'status': 'passed' if result.returncode == 0 else 'failed',
            'health': 'passed' if result.returncode == 0 else 'failed',
            'reason': 'governed_health_check', 'exit_code': result.returncode}


def evaluate(rows):
    return not any(row['status'] == 'failed' for row in rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    for profile in PROFILES:
        parser.add_argument(f'--{profile}-env', type=Path, required=True)
    args = parser.parse_args()
    rows = [inspect_profile(p, getattr(args, f'{p}_env'), args.root) for p in PROFILES]
    ok = evaluate(rows)
    print(json.dumps({'status': 'passed' if ok else 'failed', 'scope': 'local_developer_readiness',
                      'product_acceptance': 'not_claimed', 'profiles': rows}, indent=2))
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
