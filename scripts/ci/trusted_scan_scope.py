#!/usr/bin/env python3
"""Reuse proved ancestor scan coverage, never infer historical proof from a tree.

Legacy Quick receipts remain exact-head evidence but cannot skip scanning.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

AUTHORITY = {
    'secrets': ('scripts/ci/secret_scan.py', 'config/security/legacy_credential_fingerprints.json'),
    'personal': ('scripts/ci/personal_data_scan.py', 'scripts/ci/personal_data_false_positives.json'),
    'history': ('scripts/verify/repository_clean_history_guard.py',
                'config/security/repository_clean_history_policy.v1.json',
                'config/security/repository_oversized_blob_exceptions.v1.json',
                'scripts/ci/personal_data_false_positives.json', '.github/workflows/public_guard.yml'),
}
COMMON_AUTHORITY = ('scripts/ops/local_quick_evidence.py', 'scripts/ci/trusted_scan_scope.py',
                    'scripts/dev/local_dev_frontend_quick.py', 'Makefile')
SHA = re.compile(r'^[0-9a-f]{40}$')
COVERAGE_PROTOCOL = 'quick-scan-occurrences-v1'
COVERAGE_ENV = 'SC_QUICK_SCAN_COVERAGE_DIR'
PRODUCER = 'atomic-ci-local-quick-runner-v2'


def revision_args(kind: str) -> tuple[str, ...]:
    return ('HEAD', '--branches', '--tags', '--remotes') if kind == 'history' else ('HEAD', '--all')


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


def authority_digest(root: Path, kind: str, revision: str | None = None) -> str:
    """Bind the entire execution chain, including added/deleted Make includes."""
    names = (git(root, 'ls-tree', '-r', '--name-only', '-z', revision).split('\0') if revision else
             (git(root, 'ls-files', '--cached', '--others', '--exclude-standard', '-z')).split('\0'))
    paths = set(COMMON_AUTHORITY + AUTHORITY[kind])
    paths.update(name for name in names if name.startswith('make/') and name.endswith('.mk'))
    rows = []
    for relative in sorted(paths):
        data = source_at(root, revision, relative) if revision else (root / relative).read_bytes()
        rows.append((relative, hashlib.sha256(data).hexdigest()))
    return hashlib.sha256(json.dumps(rows, separators=(',', ':')).encode()).hexdigest()


def ref_snapshot(root: Path, kind: str) -> list[list[str]]:
    rows = [['HEAD', git(root, 'rev-parse', 'HEAD').strip(), 'commit']]
    for line in git(root, 'for-each-ref', '--format=%(refname)%00%(objectname)%00%(objecttype)').splitlines():
        name, oid, object_type = line.split('\0')
        if kind != 'history' or name.startswith(('refs/heads/', 'refs/tags/', 'refs/remotes/')):
            rows.append([name, oid, object_type])
    # --all includes registered worktree HEADs; publication revisions do not.
    if kind != 'history':
        worktree = ''
        for line in git(root, 'worktree', 'list', '--porcelain', '-z').split('\0'):
            if line.startswith('worktree '): worktree = line[9:]
            elif line.startswith('HEAD '): rows.append(['worktree:' + worktree, line[5:], 'commit'])
    return sorted(rows)


def coverage_snapshot(root: Path) -> dict:
    return {'protocol': COVERAGE_PROTOCOL, 'scanners': {
        kind: {'authority': authority_digest(root, kind), 'refs': ref_snapshot(root, kind),
               'revisions': list(revision_args(kind))} for kind in AUTHORITY}}


def valid_coverage(root: Path, coverage: object, head: str) -> bool:
    if not isinstance(coverage, dict) or set(coverage) != {'protocol', 'scanners'} or coverage['protocol'] != COVERAGE_PROTOCOL:
        return False
    scanners = coverage['scanners']
    if not isinstance(scanners, dict) or set(scanners) != set(AUTHORITY): return False
    for kind, row in scanners.items():
        if not isinstance(row, dict) or set(row) != {'authority', 'refs', 'revisions'}: return False
        if row['revisions'] != list(revision_args(kind)) or row['authority'] != authority_digest(root, kind, head): return False
        refs = row['refs']
        if not isinstance(refs, list) or not refs or ['HEAD', head, 'commit'] not in refs: return False
        if any(not isinstance(ref, list) or len(ref) != 3 or not all(isinstance(v, str) for v in ref)
               or not SHA.fullmatch(ref[1]) for ref in refs): return False
        if len({ref[0] for ref in refs}) != len(refs) or sorted(refs) != refs: return False
        for name, oid, typ in refs:
            if name != 'HEAD' and not name.startswith(('refs/', 'worktree:')): return False
            if kind == 'history' and name != 'HEAD' and not name.startswith(('refs/heads/', 'refs/tags/', 'refs/remotes/')): return False
            if git(root, 'cat-file', '-t', oid).strip() != typ: return False
    return True


def equivalent_coverage(root: Path, saved: dict, current: dict) -> bool:
    """Ref aliases may change without changing any scanned reachable object.

    Deleting unique reachability is deliberately not equivalent: exception
    registry staleness is also part of the successful scan result.
    """
    if saved['protocol'] != current['protocol']: return False
    for kind in AUTHORITY:
        old, new = saved['scanners'][kind], current['scanners'][kind]
        if old['authority'] != new['authority'] or old['revisions'] != new['revisions']: return False
        def objects(row):
            tips = sorted({ref[1] for ref in row['refs']})
            return set(git(root, 'rev-list', '--objects', '--no-object-names', *tips, '--').splitlines())
        if objects(old) != objects(new): return False
    return True


def record_scan_success(root: Path, kind: str, base: str | None = None) -> None:
    """Optional per-run handshake; standalone scans create no persistent evidence."""
    directory = os.environ.get(COVERAGE_ENV)
    if not directory: return
    folder = Path(directory)
    launch = json.loads((folder / 'launch.json').read_text())
    if str(root.resolve()) != launch['root']: return  # isolated scanner unit fixtures
    expected = launch['coverage']['scanners'][kind]
    actual = coverage_snapshot(root)['scanners'][kind]
    if actual != expected or git(root, 'rev-parse', 'HEAD').strip() != launch['head']:
        raise ValueError('scan coverage identity changed')
    proof = {'protocol': COVERAGE_PROTOCOL, 'kind': kind, 'head': launch['head'], 'tree': launch['tree'], 'coverage': actual, 'mode': 'incremental' if base else 'full', 'base': base}
    temporary = folder / (kind + '.tmp')
    temporary.write_text(json.dumps(proof, sort_keys=True))
    temporary.replace(folder / (kind + '.json'))


def source_at(root: Path, base: str, relative: str) -> bytes:
    return subprocess.check_output(['git', '-C', str(root), 'show', f'{base}:{relative}'], stderr=subprocess.DEVNULL)


def select_scope(root: Path, kind: str) -> Scope:
    if kind not in AUTHORITY: raise ValueError('unknown scan kind')
    if os.environ.get('GITHUB_EVENT_NAME') == 'schedule': return Scope(None, 'scheduled_full_audit')
    try:
        if git(root, 'remote', 'get-url', 'origin').strip() not in (
            'https://github.com/lidefend/sce-backend-odoo.git', 'git@github.com:lidefend/sce-backend-odoo.git'):
            return Scope(None, 'untrusted_origin')
        main = git(root, 'rev-parse', '--verify', 'refs/remotes/origin/main^{commit}').strip()
        git(root, 'merge-base', '--is-ancestor', main, 'HEAD')
        if git(root, 'rev-parse', '--is-shallow-repository').strip() != 'false':
            return Scope(None, 'shallow_history')
        for _, oid, _ in ref_snapshot(root, kind):
            try: git(root, 'cat-file', '-e', oid + '^{commit}')
            except subprocess.CalledProcessError: return Scope(None, 'noncommit_ref_requires_full')
        order = {head: index for index, head in enumerate(git(root, 'rev-list', '--topo-order', 'HEAD').splitlines())}
        common = Path(git(root, 'rev-parse', '--path-format=absolute', '--git-common-dir').strip())
        candidates = []
        for folder in receipt_directories(root, common):
            for path in folder.glob('*.json'):
                try:
                    if path.is_symlink() or path.parent.resolve() != path.parent: continue
                    payload = json.loads(path.read_text())
                    if not isinstance(payload, dict) or set(payload) != {'schema_version', 'suite', 'producer', 'head', 'tree', 'coverage'}: continue
                    head = payload['head']
                    if not isinstance(head, str) or not SHA.fullmatch(head) or path.stem != head or head not in order: continue
                    if payload['schema_version'] != 3 or payload['suite'] != 'ci.local.quick' or payload['producer'] != PRODUCER: continue
                    if payload['tree'] != git(root, 'rev-parse', head + '^{tree}').strip(): continue
                    if not valid_coverage(root, payload['coverage'], head): continue
                    candidates.append((order[head], str(path), head, payload))
                except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError): continue
        if not candidates: return Scope(None, 'verified_coverage_receipt_missing')
        current = authority_digest(root, kind)
        for _, path, base, payload in sorted(candidates):
            if payload['coverage']['scanners'][kind]['authority'] != current: continue
            # Endpoint equality cannot hide an intervening authority modification.
            commits = git(root, 'rev-list', '--full-history', base + '..HEAD', '--', *COMMON_AUTHORITY, *AUTHORITY[kind], 'make/').splitlines()
            if any(authority_digest(root, kind, commit) != current for commit in commits): continue
            return Scope(base, 'verified_ancestor_coverage_unchanged_authority', path)
        return Scope(None, 'scan_authority_changed')
    except (OSError, ValueError, subprocess.CalledProcessError):
        return Scope(None, 'coverage_identity_unprovable')


def candidate_blobs(root: Path, base: str | None, revisions: tuple[str, ...] = ('HEAD',)) -> list[tuple[str, str, int]]:
    """Every committed path/blob occurrence; merges inspect each parent.

    Raw NUL-delimited diffs avoid one Git process per commit and preserve paths,
    including old blobs reused at new paths and files deleted in later commits.
    """
    if '--all' in revisions or '--tags' in revisions:
        kind = 'secrets' if '--all' in revisions else 'history'
        for name, oid, _ in ref_snapshot(root, kind):
            result = subprocess.run(['git', '-C', str(root), 'cat-file', '-e', oid + '^{commit}'],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if result.returncode:
                raise ValueError('unsupported noncommit scan reference: ' + name)
    arguments = [*revisions, *(['^' + base] if base else [])]
    raw = git(root, 'log', '--raw', '-z', '--format=', '--no-abbrev', '--no-renames', '--root', '-m',
              '--diff-filter=ACMRT', *arguments, '--')
    tokens = raw.split('\0')
    occurrences = set()
    index = 0
    while index < len(tokens):
        header = tokens[index].lstrip('\n')
        index += 1
        if not header: continue
        match = re.fullmatch(r':([0-7]{6}) ([0-7]{6}) ([0-9a-f]{40}) ([0-9a-f]{40}) ([ACMRT])', header)
        if not match or index >= len(tokens) or not tokens[index]: raise ValueError('malformed occurrence diff')
        path = tokens[index]; index += 1
        if match[2] == '160000': continue  # submodule commit, not a blob
        occurrences.add((match[4], path))
    if not occurrences: return []
    oid_set = {oid for oid, _ in occurrences}
    oids = sorted(oid_set)
    result = subprocess.run(['git', '-C', str(root), 'cat-file', '--batch-check=%(objectname) %(objecttype) %(objectsize)'],
                            input='\n'.join(oids) + '\n', text=True, capture_output=True, check=True)
    sizes = {}
    for row in result.stdout.splitlines():
        parts = row.split()
        if len(parts) != 3 or parts[0] not in oid_set or parts[1] != 'blob' or not parts[2].isdigit():
            raise ValueError('unreadable occurrence blob')
        sizes[parts[0]] = int(parts[2])
    if set(sizes) != set(oids): raise ValueError('incomplete blob metadata')
    return sorted((oid, path, sizes[oid]) for oid, path in occurrences)


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
