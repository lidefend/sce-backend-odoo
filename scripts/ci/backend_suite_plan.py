#!/usr/bin/env python3
"""Partition the existing backend scope; never cache or reduce test outcomes."""
from __future__ import annotations

import argparse
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


def build_plan(base: str, head: str, override: str = '') -> dict:
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
    return {**selected, 'base': base, 'head': head, 'shards': partition(selected['modules'])}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', default='')
    parser.add_argument('--head', required=True)
    parser.add_argument('--modules', default='')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--github-output', type=Path)
    parser.add_argument('--shard', type=int)
    args = parser.parse_args()
    plan = build_plan(args.base, args.head, args.modules)
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
