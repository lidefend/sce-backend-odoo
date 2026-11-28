#!/usr/bin/env python3
"""Archive an exact superseded PR before closing it; never deletes branches."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

try:
    from . import retire_historical_branch_refs as retirement
except ImportError:
    import retire_historical_branch_refs as retirement


def gh(root, *args):
    return subprocess.check_output(['gh', *args], cwd=root, text=True)


def validate_prs(old, replacement, entry, expected_main, root):
    if old['number'] == replacement['number']:
        raise retirement.RetirementError('replacement must be a different PR')
    if old['state'] not in ('OPEN', 'CLOSED') or not old['isDraft']:
        raise retirement.RetirementError('only an unmerged Draft candidate can be retired')
    if old['headRefName'] != entry.branch or old['headRefOid'] != entry.remote_sha:
        raise retirement.RetirementError('original PR identity drift')
    if old['isCrossRepository'] or replacement['isCrossRepository']:
        raise retirement.RetirementError('cross-repository PR is outside scope')
    if replacement['state'] != 'MERGED' or replacement['baseRefName'] != 'main':
        raise retirement.RetirementError('replacement must be merged into main')
    merge = (replacement.get('mergeCommit') or {}).get('oid')
    if not merge or retirement.is_ancestor(root, merge, expected_main) is not True:
        raise retirement.RetirementError('replacement is not in exact main')


def execute(args, root):
    payload, entries = retirement.load_manifest(args.manifest)
    digest = retirement.manifest_digest(args.manifest)
    if digest != args.manifest_sha256 or len(entries) != 1:
        raise retirement.RetirementError('require exact approved single-branch manifest')
    if retirement.run_git(root, 'remote', 'get-url', 'origin').stdout.strip() != payload['repository']['origin_url']:
        raise retirement.RetirementError('origin mismatch')
    if retirement.remote_main_sha(root) != args.expected_main:
        raise retirement.RetirementError('main drift')
    fields = 'number,state,isDraft,headRefName,headRefOid,isCrossRepository,baseRefName,mergeCommit,url'
    def read(number):
        return json.loads(gh(root, 'pr', 'view', str(number), '--json', fields))
    old, replacement = read(args.pr), read(args.replacement)
    validate_prs(old, replacement, entries[0], args.expected_main, root)
    # Open PR is expected here; all OTHER retirement guards must already pass.
    assessments = retirement.assess_entries(root, entries, open_branches=retirement.github_open_branches(root), expected_main=args.expected_main)
    for assessment in assessments:
        reasons = [r for r in assessment.reasons if r != 'branch has an open pull request']
        if reasons:
            raise retirement.RetirementError('; '.join(reasons))
    report = {'mode': 'apply' if args.apply else 'dry-run', 'manifest_sha256': digest,
              'expected_main': args.expected_main, 'original': old, 'replacement': replacement}
    if args.apply:
        if args.confirm != 'ARCHIVE_AND_CLOSE_SUPERSEDED_PR':
            raise retirement.RetirementError('missing explicit close confirmation')
        report['bundle'] = retirement.create_recovery_bundle(root, args.bundle, digest, entries)
        report['bundle']['sha256'] = hashlib.sha256(args.bundle.read_bytes()).hexdigest()
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2)+'\n')
        # Recheck identities after potentially expensive bundle creation.
        current, replacement = read(args.pr), read(args.replacement)
        validate_prs(current, replacement, entries[0], args.expected_main, root)
        if retirement.remote_main_sha(root) != args.expected_main:
            raise retirement.RetirementError('main advanced during archival')
        if current['state'] == 'OPEN':
            gh(root, 'pr', 'close', str(args.pr))
        report['readback'] = read(args.pr)
        if report['readback']['state'] != 'CLOSED' or report['readback']['headRefOid'] != entries[0].remote_sha:
            raise retirement.RetirementError('closed PR readback mismatch')
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2)+'\n')
    print('[pr.close.superseded] '+report['mode']+' verified; '+str(args.report))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('manifest', 'bundle', 'report'):
        parser.add_argument('--'+name, type=Path, required=True)
    for name in ('manifest-sha256', 'expected-main'):
        parser.add_argument('--'+name, required=True)
    for name in ('pr', 'replacement'):
        parser.add_argument('--'+name, type=int, required=True)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--confirm', default='')
    args = parser.parse_args()
    root = Path(subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], text=True).strip())
    try:
        execute(args, root)
    except (retirement.RetirementError, subprocess.CalledProcessError, KeyError, ValueError) as exc:
        parser.exit(2, '[pr.close.superseded] DENY '+str(exc)+'\n')


if __name__ == '__main__':
    main()
