#!/usr/bin/env python3
"""Select backend test modules from exact Git trees; never treat unknown as skip.

No result cache: excluded modules are outside impact, not claimed as executed.
The nightly runner still discovers and executes its entire module set.
"""
from __future__ import annotations

import argparse
import ast
import fnmatch
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ROOTS = ('addons', 'demo_addons')
GLOBAL = ('Dockerfile*', 'docker-compose*', 'requirements*', 'odoo.conf',
          'config/odoo*', 'scripts/test/**', 'scripts/ci/orm_result_guard.sh',
          'scripts/ci/backend_impact_plan.py', '.github/workflows/backend_test_suite.yml',
          '.github/workflows/professional_quality_gate.yml', 'make/ci.mk',
          'make/dev_test.mk', 'Makefile')
NON_RUNTIME = ('docs/**', '.agent/**', 'frontend/**', '*.md',
               'scripts/verify/**', 'scripts/ci/test_*.py',
               'scripts/ci/personal_data_false_positives.json')


def git(*args: str) -> str:
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True)


def snapshot(revision: str) -> dict:
    files = git('ls-tree', '-r', '--name-only', revision).splitlines()
    modules = {}
    for path in files:
        parts = path.split('/')
        if len(parts) != 3 or parts[0] not in ROOTS or parts[2] != '__manifest__.py':
            continue
        name = parts[1]
        if not re.fullmatch(r'[a-zA-Z_][a-zA-Z0-9_]*', name) or name in modules:
            raise ValueError(f'invalid or ambiguous module: {name}')
        data = ast.literal_eval(git('show', f'{revision}:{path}'))
        deps = data.get('depends', [])
        if not isinstance(deps, list) or not all(isinstance(v, str) for v in deps):
            raise ValueError(f'invalid dependencies: {path}')
        prefix = '/'.join(parts[:2]) + '/'
        modules[name] = {'depends': set(deps), 'prefix': prefix,
                         'tests': any(f.startswith(prefix + 'tests/') and f.endswith('.py') for f in files),
                         'installable': data.get('installable', True)}
    # Cross-module Python imports also express consumers, including test helpers.
    imports = subprocess.run(
        ['git', 'grep', '-I', '-n', '-E', r'odoo\.addons\.[A-Za-z_]', revision,
         '--', 'addons/**/*.py', 'demo_addons/**/*.py'],
        cwd=ROOT, text=True, capture_output=True)
    if imports.returncode not in (0, 1):
        raise ValueError('cannot resolve cross-module imports')
    for line in imports.stdout.splitlines():
        _, path, _, source = line.split(':', 3)
        parts = path.split('/')
        if len(parts) >= 3 and parts[1] in modules:
            modules[parts[1]]['depends'].update(re.findall(r'odoo\.addons\.([A-Za-z_][A-Za-z_0-9]*)', source))
    return modules


def select(paths: list[str], before: dict, after: dict, *, full: bool = False) -> dict:
    runnable = {k for k, v in after.items() if v['tests'] and v.get('installable', True)}
    graph = {}
    for tree in (before, after):
        for name, data in tree.items():
            graph.setdefault(name, set()).update(data['depends'])
    seeds, reasons = set(), []
    for path in paths:
        parts = path.split('/')
        if path.startswith('/') or '..' in parts:
            raise ValueError('invalid changed path')
        if len(parts) >= 3 and parts[0] in ROOTS:
            if parts[1] in graph:
                seeds.add(parts[1])
            else:
                reasons.append('unknown_module:' + path)
        elif any(fnmatch.fnmatchcase(path, pattern) for pattern in GLOBAL):
            reasons.append('shared_runtime:' + path)
        elif not any(fnmatch.fnmatchcase(path, pattern) for pattern in NON_RUNTIME):
            reasons.append('unknown_impact:' + path)
    if not paths and not full:
        reasons.append('empty_diff_requires_full')
    affected = set(seeds)
    while True:
        consumers = {name for name, deps in graph.items() if deps & affected}
        if consumers <= affected:
            break
        affected |= consumers
    if full:
        reasons.append('explicit_full')
    selected = runnable if reasons else runnable & affected
    # A module change without any executable owner/consumer must not turn green.
    for seed in sorted(seeds):
        closure = {seed}
        while True:
            consumers = {name for name, deps in graph.items() if deps & closure}
            if consumers <= closure:
                break
            closure |= consumers
        if not closure & selected:
            raise ValueError(f'changed backend module has no runnable test coverage: {seed}')
    if not runnable:
        raise ValueError('no runnable backend tests')
    return {'mode': 'full' if reasons else 'incremental', 'reasons': sorted(reasons),
            'seeds': sorted(seeds), 'affected': sorted(affected),
            'modules': sorted(selected), 'excluded': sorted(runnable - selected),
            'changed_paths': sorted(paths)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', required=True)
    parser.add_argument('--head', required=True)
    parser.add_argument('--full', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--github-output', type=Path)
    args = parser.parse_args()
    base = git('rev-parse', '--verify', args.base + '^{commit}').strip()
    head = git('rev-parse', '--verify', args.head + '^{commit}').strip()
    # No rename collapsing: both old and new owners remain in the impact set.
    paths = git('diff', '--no-renames', '--name-only', base, head, '--').splitlines()
    before, after = snapshot(base), snapshot(head)
    plan = select(paths, before, after, full=args.full)
    plan.update(schema='backend-impact/v1', base=base, head=head)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(plan, indent=2) + '\n')
    print(json.dumps(plan, indent=2))
    if args.github_output:
        with args.github_output.open('a') as stream:
            stream.write('modules=' + ' '.join(plan['modules']) + '\n')
            stream.write('required=' + str(bool(plan['modules'])).lower() + '\n')


if __name__ == '__main__':
    main()
