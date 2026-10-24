#!/usr/bin/env python3
"""Partition the existing backend scope; never cache or reduce test outcomes."""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import re
from pathlib import Path

import backend_impact_plan as impact


def partition(modules: list[str], limit: int = 4) -> list[dict]:
    if not modules or len(set(modules)) != len(modules):
        raise ValueError('scope must be nonempty and unique')
    if not 1 <= limit <= 4:
        raise ValueError('parallelism must be between one and four')
    if any(not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', name) for name in modules):
        raise ValueError('invalid module name')
    ordered = sorted(modules)
    count = min(limit, len(ordered))
    shards = [{'index': index, 'modules': ordered[index::count]} for index in range(count)]
    flattened = [name for shard in shards for name in shard['modules']]
    if sorted(flattened) != ordered or len(set(flattened)) != len(ordered):
        raise ValueError('shard union differs from selected scope')
    return shards


# Known execution dependencies supplement the existing selector; this inventory
# does not certify imports, external packages, dynamic contracts or SQL reads.
EXECUTION_INPUTS = impact.GLOBAL + ('scripts/ci/backend_suite_plan.py',
    'scripts/ci/backend_test_receipt.py', 'scripts/common/**', 'scripts/_lib/**',
    'scripts/render_odoo_conf.py', 'config/requirements-test.txt')


def inventory_from_tree(graph: dict, modules: list[str], entries: dict) -> dict:
    targets = {}; used = set()
    shared = {path for path in entries if any(fnmatch.fnmatchcase(path,p) for p in EXECUTION_INPUTS)}
    for name in sorted(modules):
        if name not in graph:
            raise ValueError('inventory target absent: ' + name)
        closure = set(); external = set(); pending = [name]
        while pending:
            current = pending.pop()
            if current in closure or current in external:
                continue
            if current not in graph:
                external.add(current)
                continue
            closure.add(current)
            pending.extend(graph[current]['depends'])
        prefixes = tuple(graph[m]['prefix'] for m in sorted(closure))
        reads = {path for m in closure for path in graph[m].get('file_inputs', [])}
        paths = sorted(shared | {path for path in entries if path.startswith(prefixes)} | (reads & entries.keys()))
        unresolved = sorted({site for m in closure for site in graph[m].get('unresolved_file_reads', [])})
        missing = sorted(reads - entries.keys())
        special = [path for path in paths if entries[path]['mode'] not in ('100644','100755') or entries[path]['kind'] != 'blob']
        identity = {'files':{path:entries[path] for path in paths}, 'declared_modules':sorted(closure),
                    'external_modules':sorted(external), 'unresolved_file_reads':unresolved,
                    'missing_file_inputs':missing, 'special_git_entries':special}
        targets[name] = {'target':name,'declared_module_closure':sorted(closure),
            'input_paths':paths,'direct_test_file_inputs':sorted(graph[name].get('file_inputs', [])),
            'known_inputs_sha256':hashlib.sha256(json.dumps(identity,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
            'external_modules':sorted(external),'unresolved_file_reads':unresolved,
            'missing_file_inputs':missing,'special_git_entries':special,
            'dependency_closure_complete':False,'reuse_ready':False,
            'blockers':['dynamic_import_and_read_closure_unproven','runtime_environment_identity_required',
                        'runtime_contract_and_fact_scope_not_bound','verified_execution_receipt_required']}
        used.update(paths)
    return {'schema':'backend-known-input-inventory/v1','targets':targets,
            'files':{path:entries[path] for path in sorted(used)},'reuse_authority':False}


def target_input_inventory(head: str, graph: dict, modules: list[str]) -> dict:
    entries = {}
    for item in impact.git('ls-tree','-r','-z',head).split('\0'):
        if not item:
            continue
        metadata,path = item.split('\t',1)
        mode,kind,oid = metadata.split(' ')
        if path in entries or not re.fullmatch('[0-9a-f]{40}',oid):
            raise ValueError('invalid exact tree inventory')
        entries[path] = {'mode':mode,'kind':kind,'oid':oid}
    return inventory_from_tree(graph,modules,entries)


def build_plan(base: str, head: str, override: str = '', *, include_inputs: bool = False) -> dict:
    head = impact.git('rev-parse', '--verify', head + '^{commit}').strip()
    after = impact.snapshot(head)
    if base:
        if override:
            raise ValueError('premerge scope cannot be overridden')
        base = impact.git('rev-parse', '--verify', base + '^{commit}').strip()
        paths = impact.git('diff', '--no-renames', '--name-only', base, head, '--').splitlines()
        selected = impact.select(paths, impact.snapshot(base), after)
    else:
        # Preserve the original nightly/dispatch discovery: a manifest and
        # tests directory, including non-installable pure-Python test modules.
        directories = set(impact.git('ls-tree', '-r', '-d', '--name-only', head,
                                     '--', 'addons', 'demo_addons').splitlines())
        modules = sorted(name for name, data in after.items()
                         if data['prefix'] + 'tests' in directories)
        selected = {'modules': modules, 'mode': 'full', 'reasons': ['explicit_full']}
        if override:
            modules = override.replace(',', ' ').split()
            if not modules or any(name not in selected['modules'] for name in modules):
                raise ValueError('override contains a module without runnable tests')
            selected.update(modules=modules, mode='explicit_override', reasons=['owner_dispatch_override'])
    plan = {**selected, 'base': base, 'head': head, 'shards': partition(selected['modules'])}
    if include_inputs:
        plan['input_inventory'] = target_input_inventory(head,after,plan['modules'])
    return plan


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', default='')
    parser.add_argument('--head', required=True)
    parser.add_argument('--modules', default='')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--github-output', type=Path)
    parser.add_argument('--shard', type=int)
    parser.add_argument('--input-inventory', action='store_true')
    args = parser.parse_args()
    plan = build_plan(args.base, args.head, args.modules, include_inputs=args.input_inventory)
    args.output.write_text(json.dumps(plan, indent=2) + '\n')
    if args.shard is not None:
        if not 0 <= args.shard < len(plan['shards']):
            raise ValueError('shard outside selected scope')
        print(' '.join(plan['shards'][args.shard]['modules']))
    else:
        print(json.dumps(plan, indent=2))
    if args.github_output:
        matrix = {'include': [{'index': shard['index']} for shard in plan['shards']]}
        with args.github_output.open('a') as output:
            output.write('matrix=' + json.dumps(matrix, separators=(',', ':')) + '\n')
            output.write('head=' + plan['head'] + '\n')


if __name__ == '__main__':
    main()
