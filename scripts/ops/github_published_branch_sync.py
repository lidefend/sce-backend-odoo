#!/usr/bin/env python3
"""Governed append of exact GitHub main to an already published candidate."""
import argparse
import json
from pathlib import Path
import subprocess

from gitee_published_branch_sync import git, out, sync, CONFIRM

URLS = {'https://github.com/lidefend/sce-backend-odoo.git', 'git@github.com:lidefend/sce-backend-odoo.git'}
INDEX = '.agent/active-runs.json'
REPORTS = {'docs/engineering_convergence/complexity_budget_report.md',
           'docs/engineering_convergence/test_inventory.csv',
           'docs/engineering_convergence/test_inventory_summary.md'}


def merge_index(base, ours, theirs):
    """Three-way key merge; never choose between competing task assignments."""
    for doc in (base, ours, theirs):
        if set(doc) != {'schema_version', 'branches'} or doc['schema_version'] != 1:
            raise RuntimeError('unsupported active-run index schema')
        if not isinstance(doc['branches'], dict) or any(
                not isinstance(k, str) or not isinstance(v, str)
                for k, v in doc['branches'].items()):
            raise RuntimeError('invalid active-run mapping')
    missing = object()
    merged = {}
    for key in sorted(set(base['branches']) | set(ours['branches']) | set(theirs['branches'])):
        b, o, t = (d['branches'].get(key, missing) for d in (base, ours, theirs))
        if o == t or t == b:
            value = o
        elif o == b:
            value = t
        else:
            raise RuntimeError('competing active-run assignment: ' + key)
        if value is not missing:
            merged[key] = value
    return {'schema_version': 1, 'branches': merged}


def resolve_metadata(root):
    paths = set(out(root, 'diff', '--name-only', '--diff-filter=U').splitlines())
    if not paths or not paths <= REPORTS | {INDEX}:
        raise RuntimeError('unapproved merge conflict; original candidate restored')
    # Compute every resolution before changing the index; only regular files.
    results = {}
    for path in paths:
        stages = out(root, 'ls-files', '-u', '--', path).splitlines()
        if len(stages) != 3 or any(row.split()[0] != '100644' for row in stages):
            raise RuntimeError('unsupported conflict stages or file mode')
        if path == INDEX:
            docs = [json.loads(out(root, 'show', f':{stage}:{path}')) for stage in (1, 2, 3)]
            results[path] = json.dumps(merge_index(*docs), ensure_ascii=False, indent=2) + '\n'
        else:
            # Intermediate merge only: publication preflight requires regeneration.
            results[path] = git(root, 'show', ':2:' + path).stdout
    for path, content in results.items():
        (Path(root) / path).write_text(content)
        git(root, 'add', '--', path)
    return sorted(paths)


def verify_pr(root, pr, branch, remote_head):
    p = subprocess.run(['gh', 'pr', 'view', str(pr), '--repo', 'lidefend/sce-backend-odoo',
                        '--json', 'state,headRefName,headRefOid,baseRefName,isCrossRepository'],
                       cwd=root, text=True, capture_output=True, check=True)
    d = json.loads(p.stdout)
    if (d.get('state') != 'OPEN' or d.get('headRefName') != branch or
            d.get('headRefOid') != remote_head or d.get('baseRefName') != 'main' or
            d.get('isCrossRepository') is not False):
        raise RuntimeError('PR identity mismatch')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('root', 'branch', 'head', 'main', 'remote-head'):
        p.add_argument('--' + name, required=True)
    p.add_argument('--pr', type=int, required=True)
    p.add_argument('--apply', action='store_true')
    p.add_argument('--confirm', default='')
    args = vars(p.parse_args())
    pr = args.pop('pr')
    if pr <= 0:
        p.error('positive PR number required')
    verify_pr(args['root'], pr, args['branch'], args['remote_head'])
    result = sync(**args, allowed_urls=URLS, remote='origin', resolve_conflicts=resolve_metadata)
    result['pr'] = pr
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
