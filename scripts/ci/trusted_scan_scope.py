#!/usr/bin/env python3
"""Reuse a verified main tree; scan candidate occurrences, never just final diff.

Local Quick receipts are existing governed evidence. A squash merge can reuse a
receipt only when its complete tree equals origin/main. Missing evidence or
changed scanner authority selects full scanning, never a successful skip.
"""
from __future__ import annotations

import ast
import hashlib
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
COMMON_AUTHORITY = ('scripts/ops/local_quick_evidence.py',)
SHA = re.compile(r'^[0-9a-f]{40}$')
# Only this reviewed lookup migration may preserve old scan results.
EVIDENCE_SELECTION_MIGRATIONS = frozenset([('8c8938e55d5b97306b51429453ffa0f13aff04f6334d2fde1770cff64701b277', 'b3ed3da94595dcd4b078a681c38685b74860468fa993542d89a328e82c187e05')])


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


def receipt_directories(root: Path, common: Path) -> list[Path]:
    """Only Git-registered worktrees sharing this repository's common directory."""
    directories = {common / 'codex/evidence/ci.local.quick'}
    rows = git(root, 'worktree', 'list', '--porcelain', '-z').split('\0')
    for row in rows:
        if not row.startswith('worktree '):
            continue
        worktree = Path(row[len('worktree '):])
        if not worktree.is_dir():
            continue  # A prunable checkout does not establish a receipt authority.
        try:
            owner = Path(git(worktree, 'rev-parse', '--path-format=absolute', '--git-common-dir').strip()).resolve()
            directory = Path(git(worktree, 'rev-parse', '--path-format=absolute', '--git-dir').strip()).resolve()
            if owner != common.resolve() or not directory.is_relative_to(common.resolve()):
                continue
            directories.add(directory / 'codex/evidence/ci.local.quick')
        except (OSError, subprocess.CalledProcessError):
            continue
    return sorted(directories)


def scan_semantics(source: bytes) -> str:
    """Compare the whole helper except explicitly reviewed evidence-selection code.

    All coverage functions, imports, scanner authority and unclassified globals
    remain in the comparison, including future dependencies. This is not a
    general exemption for helper changes. A changed producer is compared in full.
    """
    tree = ast.parse(source)
    selection = {'select_scope', 'receipt_directories', 'scan_semantics',
                 'make_scan_authority', 'source_at', 'main',
                 'selection_digest', 'helper_authority_equal'}
    kept = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in selection:
            continue
        if isinstance(node, ast.Assign) and all(isinstance(t, ast.Name) and t.id in ('COMMON_AUTHORITY', 'EVIDENCE_SELECTION_MIGRATIONS') for t in node.targets):
            continue
        if isinstance(node, ast.Import) and len(node.names) == 1 and node.names[0].name in ('ast', 'hashlib') and node.names[0].asname is None:
            continue
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            continue
        kept.append(node)
    return ast.dump(ast.Module(body=kept, type_ignores=[]), include_attributes=False)


def selection_digest(source: bytes) -> str:
    # Bind all source structure (including excluded selection functions), except
    # the migration registry itself to avoid a self-referential digest.
    tree = ast.parse(source)
    tree.body = [node for node in tree.body if not (
        isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and
        t.id == 'EVIDENCE_SELECTION_MIGRATIONS' for t in node.targets))]
    return hashlib.sha256(ast.dump(tree, include_attributes=False).encode()).hexdigest()


def helper_authority_equal(old: bytes, current: bytes) -> bool:
    if old == current:
        return True
    # The registry is executable authority too: allow only identical registry
    # declarations or the exact legacy(no registry)->reviewed current transition.
    def registry(source):
        return [ast.dump(n, include_attributes=False) for n in ast.parse(source).body
                if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and
                t.id == 'EVIDENCE_SELECTION_MIGRATIONS' for t in n.targets)]
    previous, present = registry(old), registry(current)
    expected_registry = registry(('EVIDENCE_SELECTION_MIGRATIONS = frozenset('
                                  + repr(sorted(EVIDENCE_SELECTION_MIGRATIONS)) + ')').encode())
    if present != expected_registry:
        return False
    digests = (selection_digest(old), selection_digest(current))
    if previous == present and digests[0] == digests[1]:
        return True
    return (not previous and len(present) == 1
            and digests in EVIDENCE_SELECTION_MIGRATIONS
            and scan_semantics(old) == scan_semantics(current))


def make_scan_authority(source: bytes) -> bytes:
    """Ignore only the known daily L1 rule, which Quick does not execute.

    Keep every other recipe, dependency, variable, include and condition exactly.
    Unknown/duplicate/dynamic L1 definitions fail closed; no candidate Make runs.
    """
    lines = source.decode().splitlines(keepends=True)
    starts = [i for i, line in enumerate(lines) if line.startswith('ci.local.iteration:')]
    if len(starts) != 1:
        raise ValueError('one static daily iteration rule required')
    start = starts[0]
    if not re.fullmatch(r'ci\.local\.iteration: [A-Za-z0-9_. -]+\n?', lines[start]):
        raise ValueError('dynamic daily iteration prerequisites')
    end = start + 1
    while end < len(lines) and (lines[end].startswith('\t') or not lines[end].strip()):
        end += 1
    # Do not exempt a newly introduced Quick -> daily-iteration dependency:
    # every other line, including the Quick dependency list, stays compared.
    return ''.join(lines[:start] + ['ci.local.iteration: <daily-only>\n'] + lines[end:]).encode()


def source_at(root: Path, base: str, relative: str) -> bytes:
    return subprocess.check_output(['git', '-C', str(root), 'show', f'{base}:{relative}'], stderr=subprocess.DEVNULL)


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
        for path in sorted(path for folder in receipt_directories(root, directory) for path in folder.glob('*.json')):
            try:
                if path.is_symlink() or path.parent.resolve() != path.parent:
                    continue
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
        try:
            if not helper_authority_equal(source_at(root, base, 'scripts/ci/trusted_scan_scope.py'),
                                          (root / 'scripts/ci/trusted_scan_scope.py').read_bytes()):
                return Scope(None, 'authority_changed:scripts/ci/trusted_scan_scope.py')
        except (OSError, ValueError, SyntaxError, subprocess.CalledProcessError):
            return Scope(None, 'authority_unprovable:scripts/ci/trusted_scan_scope.py')
        for relative, projection in (('make/ci.mk', make_scan_authority),):
            try:
                if projection(source_at(root, base, relative)) != projection((root / relative).read_bytes()):
                    return Scope(None, f'authority_changed:{relative}')
            except (OSError, ValueError, SyntaxError, subprocess.CalledProcessError):
                return Scope(None, f'authority_unprovable:{relative}')
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
