#!/usr/bin/env python3
"""Reuse a verified main tree; scan candidate occurrences, never just final diff.

Local Quick receipts are existing governed evidence. A squash merge can reuse a
receipt only when its complete tree equals origin/main. Missing evidence or
changed scanner authority selects full scanning, never a successful skip.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

AUTHORITY = {
    'secrets': ('scripts/ci/secret_scan.py',),
    'personal': ('scripts/ci/personal_data_scan.py', 'scripts/ci/personal_data_false_positives.json'),
    'history': ('scripts/verify/repository_clean_history_guard.py',
                'config/security/repository_clean_history_policy.v1.json',
                'config/security/repository_oversized_blob_exceptions.v1.json',
                'scripts/ci/personal_data_false_positives.json', '.github/workflows/public_guard.yml'),
}
COMMON_AUTHORITY = ('scripts/ci/trusted_scan_scope.py', 'scripts/ops/local_quick_evidence.py', 'make/ci.mk')
SHA = re.compile(r'^[0-9a-f]{40}$')


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(['git', '-C', str(root), *args], text=True)


@dataclass(frozen=True)
class Scope:
    base: str | None
    reason: str
    receipt: str | None = None

    def report(self, kind: str) -> None:
        print(f'[trusted_scan_scope] kind={kind} mode={"incremental" if self.base else "full"} '
              f'base={self.base or "none"} reason={self.reason} evidence={self.receipt or "none"}')


def changed_paths(root: Path, base: str) -> list[str]:
    # --no-renames includes a reused blob at its NEW path; -z preserves filenames.
    changed = git(root, 'diff', '--no-renames', '--name-only', '-z', '--diff-filter=ACMRT', base, '--')
    untracked = git(root, 'ls-files', '--others', '--exclude-standard', '-z')
    return sorted(set(filter(None, (changed + untracked).split('\0'))))


def select_scope(root: Path, kind: str) -> Scope:
    if kind not in AUTHORITY:
        raise ValueError('unknown scan kind')
    if os.environ.get('GITHUB_EVENT_NAME') == 'schedule':
        return Scope(None, 'scheduled_full_audit')
    try:
        remote = git(root, 'remote', 'get-url', 'origin').strip()
        if remote not in ('https://github.com/lidefend/sce-backend-odoo.git',
                           'git@github.com:lidefend/sce-backend-odoo.git'):
            return Scope(None, 'untrusted_origin')
        base = git(root, 'rev-parse', '--verify', 'refs/remotes/origin/main^{commit}').strip()
        git(root, 'merge-base', '--is-ancestor', base, 'HEAD')
        tree = git(root, 'rev-parse', f'{base}^{{tree}}').strip()
        directory = Path(git(root, 'rev-parse', '--path-format=absolute', '--git-common-dir').strip())
        evidence = None
        for path in sorted((directory / 'codex/evidence/ci.local.quick').glob('*.json')):
            try:
                payload = json.loads(path.read_text())
                head = payload['head']
                if not isinstance(head, str) or not SHA.fullmatch(head) or path.stem != head:
                    continue
                expected = dict(schema_version=2, suite='ci.local.quick',
                                producer='atomic-ci-local-quick-runner-v1', head=head, tree=tree)
                if payload != expected or git(root, 'rev-parse', f'{head}^{{tree}}').strip() != tree:
                    continue
                evidence = str(path)
                break
            except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError):
                continue
        if not evidence:
            return Scope(None, 'main_tree_evidence_missing')
        for relative in COMMON_AUTHORITY + AUTHORITY[kind]:
            old = subprocess.run(['git', '-C', str(root), 'show', f'{base}:{relative}'],
                                 stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
            path = root / relative
            if old.returncode or not path.is_file() or path.read_bytes() != old.stdout:
                return Scope(None, f'authority_changed:{relative}')
        return Scope(base, 'verified_main_tree_unchanged_authority', evidence)
    except (OSError, subprocess.CalledProcessError):
        return Scope(None, 'main_identity_unavailable_or_not_ancestor')


def candidate_blobs(root: Path, base: str) -> list[tuple[str, str, int]]:
    """All added/modified occurrences in every candidate commit, including deletes later.

    Enumerating commit diffs rather than only newly allocated objects also catches
    an existing blob moved into a path with stricter rules or different exemptions.
    """
    rows: set[tuple[str, str, int]] = set()
    for commit in git(root, 'rev-list', '--reverse', f'{base}..HEAD').splitlines():
        paths = git(root, 'diff-tree', '--root', '-m', '--no-commit-id', '--no-renames',
                    '--name-only', '-r', '-z', '--diff-filter=ACMRT', commit).split('\0')
        paths = sorted(set(filter(None, paths)))
        for start in range(0, len(paths), 100):
            for row in git(root, 'ls-tree', '-r', '-l', '-z', commit, '--', *paths[start:start+100]).split('\0'):
                if not row:
                    continue
                metadata, path = row.split('\t', 1)
                _mode, kind, oid, size = metadata.split()
                if kind == 'blob':
                    rows.add((oid, path, int(size)))
    return sorted(rows)


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    for kind in AUTHORITY:
        selected = select_scope(root, kind)
        selected.report(kind)
        if selected.base:
            print(f"[trusted_scan_scope] kind={kind} changed_worktree_paths={len(changed_paths(root, selected.base))} history_scope=candidate_commits")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
