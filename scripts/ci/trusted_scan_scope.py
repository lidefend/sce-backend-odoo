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
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

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
# Which make target owns each scan kind's command. The digest binds that target's
# merged declaration rather than every ``make/*.mk`` byte: a fragment that cannot
# declare, extend or parameterise these commands cannot change what a scan covers,
# and binding all of them charged a full rescan of all three kinds for an
# unrelated fragment -- or an unrelated region of the same fragment.
GOVERNED_SCAN_TARGETS = {
    'secrets': 'security.secrets.scan',
    'personal': 'security.personal_data_scan',
    'history': 'repository.clean_history.scan',
}
MAKE_ENTRY_FILE = 'Makefile'
MAKE_FRAGMENT_PREFIX = 'make/'
MAKE_FRAGMENT_SUFFIX = '.mk'
MAKE_RULE = re.compile(r'^([A-Za-z0-9_][A-Za-z0-9_.\-]*(?:[ \t]+[A-Za-z0-9_][A-Za-z0-9_.\-]*)*)[ \t]*:(?!=)[ \t]*(.*)$')
MAKE_ASSIGN = re.compile(r'^[ \t]*(?:export[ \t]+|override[ \t]+|private[ \t]+)*([A-Za-z_][A-Za-z0-9_.\-]*)[ \t]*(?::=|\+=|\?=|=)')
MAKE_REF = re.compile(r'\$[\(\{]([A-Za-z_][A-Za-z0-9_.\-]*)[\)\}]')
MAKE_DEFINE = re.compile(r'^define\b')
MAKE_INCLUDE = re.compile(r'^(?:-?include|sinclude)\b')
MAKE_MACRO = re.compile(r'\$\((?:eval|call)\b|\bdefine\b|(?:^|\n)[ \t]*(?:-?include|sinclude)\b')
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


def revision_blobs(root: Path, revision: str, relative_paths: list[str]) -> dict[str, bytes]:
    """Historical authority bytes in two Git processes.

    Reading each authority file with its own ``git show`` spawned one process per
    file per revision, and a candidate sweep re-derived the same revisions once
    per candidate, so scope selection measured process startup instead of the
    repository. ``ls-tree`` plus a single ``--batch`` returns the identical bytes
    for the identical blob, and a path absent at that revision stays a hard
    failure exactly as ``git show`` was.
    """
    if not relative_paths:
        return {}
    listing = subprocess.run(
        ['git', '-C', str(root), 'ls-tree', '-r', '-z', revision, '--', *relative_paths],
        capture_output=True, check=True).stdout
    blob_by_path: dict[str, str] = {}
    for row in listing.split(b'\0'):
        if not row:
            continue
        meta, separator, name = row.partition(b'\t')
        fields = meta.split()
        if not separator or len(fields) != 3 or fields[1] != b'blob':
            raise ValueError('unreadable authority revision')
        blob_by_path[name.decode('utf-8')] = fields[2].decode('ascii')
    if set(blob_by_path) != set(relative_paths):
        raise ValueError('unreadable authority revision')
    ordered = sorted(set(blob_by_path.values()))
    payload = subprocess.run(
        ['git', '-C', str(root), 'cat-file', '--batch'],
        input=''.join(oid + '\n' for oid in ordered).encode('ascii'), capture_output=True, check=True).stdout
    content_by_oid: dict[str, bytes] = {}
    cursor = 0
    for oid in ordered:
        newline = payload.find(b'\n', cursor)
        header = payload[cursor:newline].split() if newline >= 0 else []
        if len(header) != 3 or header[0].decode('ascii') != oid or header[1] != b'blob' or not header[2].isdigit():
            raise ValueError('unreadable authority revision')
        size = int(header[2])
        start = newline + 1
        content = payload[start:start + size]
        if len(content) != size or payload[start + size:start + size + 1] != b'\n':
            raise ValueError('unreadable authority revision')
        content_by_oid[oid] = content
        cursor = start + size + 1
    if set(content_by_oid) != set(ordered):
        raise ValueError('unreadable authority revision')
    return {relative: content_by_oid[oid] for relative, oid in blob_by_path.items()}


def revision_blob_sha256(root: Path, revision: str, relative_paths: list[str]) -> dict[str, str]:
    return {relative: hashlib.sha256(content).hexdigest()
            for relative, content in revision_blobs(root, revision, relative_paths).items()}


def make_fragments(root: Path, revision: str | None = None) -> list[str]:
    """Every make fragment that participates in the build, at that revision."""
    listed = (git(root, 'ls-files', '--cached', '--others', '--exclude-standard', '-z').split('\0') if revision is None
              else git(root, 'ls-tree', '-r', '--name-only', '-z', revision).split('\0'))
    return sorted(name for name in listed if name and (
        name == MAKE_ENTRY_FILE
        or (name.startswith(MAKE_FRAGMENT_PREFIX) and name.endswith(MAKE_FRAGMENT_SUFFIX))))


def fragment_texts(root: Path, revision: str | None, fragments: list[str]) -> dict[str, str]:
    if revision is None:
        return {name: (root / name).read_text(encoding='utf-8', errors='replace') for name in fragments}
    return {name: content.decode('utf-8', errors='replace')
            for name, content in revision_blobs(root, revision, fragments).items()}


def logical_make_lines(text: str) -> list[tuple[bool, str]]:
    """(is_recipe, joined line); a trailing backslash joins the next physical line."""
    lines: list[tuple[bool, str]] = []
    pending: str | None = None
    for raw in text.splitlines():
        pending = raw if pending is None else pending + '\n' + raw
        if pending.endswith('\\'):
            continue
        lines.append((pending.startswith('\t'), pending))
        pending = None
    if pending is not None:
        lines.append((pending.startswith('\t'), pending))
    return lines


def parse_fragment(text: str) -> tuple[dict[str, dict], dict[str, list[str]], bool]:
    """Rules, variable assignments and macro use of one make fragment.

    Conditionals are deliberately not evaluated: a rule that is live under only
    one branch is still recorded, which over-includes rather than under-includes.
    A recipe line attaches to the most recent rule, so a redefined or extended
    target is merged exactly the way make merges it.
    """
    rules: dict[str, dict] = {}
    assignments: dict[str, list[str]] = {}
    current: str | None = None
    defining = False
    for is_recipe, line in logical_make_lines(text):
        if defining:
            defining = line.strip() != 'endef'
            continue
        if is_recipe:
            if current is not None:
                rules[current]['recipe'].append(line[1:])
            continue
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        if MAKE_DEFINE.match(stripped):
            defining, current = True, None
            continue
        if MAKE_INCLUDE.match(stripped):
            current = None
            continue
        assignment = MAKE_ASSIGN.match(line)
        if assignment:
            assignments.setdefault(assignment.group(1), []).append(stripped)
            current = None
            continue
        rule = MAKE_RULE.match(line)
        if rule:
            names = rule.group(1).split()
            prerequisites = rule.group(2).split()
            for name in names:
                entry = rules.setdefault(name, {'prereqs': [], 'recipe': []})
                entry['prereqs'].extend(p for p in prerequisites if p not in entry['prereqs'])
            current = names[-1] if names else None
            continue
        current = None
    return rules, assignments, bool(MAKE_MACRO.search(text))


def make_execution_surface(root: Path, kind: str, revision: str | None = None) -> list[list]:
    """The make declaration that decides one scan kind's command.

    The rows are the merged prerequisite/recipe text of the governed target and
    its declared prerequisite closure, every variable assignment those recipes
    reference (transitively), and any macro fragment that could inject a rule for
    the governed target. Nothing else in the make surface can change the command
    make runs, so nothing else is bound.
    """
    fragments = make_fragments(root, revision)
    texts = fragment_texts(root, revision, fragments)
    merged: dict[str, dict] = {}
    assignments: dict[str, list[str]] = {}
    macro_fragments: list[str] = []
    for name in fragments:
        rules, fragment_assignments, macros = parse_fragment(texts[name])
        for target, rule in rules.items():
            entry = merged.setdefault(target, {'prereqs': [], 'recipe': []})
            entry['prereqs'].extend(p for p in rule['prereqs'] if p not in entry['prereqs'])
            entry['recipe'].extend(rule['recipe'])
        for variable, lines in fragment_assignments.items():
            assignments.setdefault(variable, []).extend(lines)
        if macros:
            macro_fragments.append(name)
    governed = GOVERNED_SCAN_TARGETS[kind]
    closure: set[str] = set()
    pending = [governed]
    while pending:
        target = pending.pop()
        if target in closure:
            continue
        closure.add(target)
        pending.extend(merged.get(target, {}).get('prereqs', []))
    referenced: set[str] = set()
    for target in closure:
        rule = merged.get(target, {'prereqs': [], 'recipe': []})
        referenced |= set(MAKE_REF.findall(' '.join(rule['prereqs'] + rule['recipe'])))
    expanded: set[str] = set()
    while referenced - expanded:
        variable = sorted(referenced - expanded)[0]
        expanded.add(variable)
        for line in assignments.get(variable, []):
            referenced |= set(MAKE_REF.findall(line))
    rows: list[list] = []
    for target in sorted(closure):
        rule = merged.get(target)
        rows.append([target, sorted(rule['prereqs']) if rule else None, rule['recipe'] if rule else None])
    for variable in sorted(referenced):
        rows.append(['variable:' + variable, sorted(assignments.get(variable, []))])
    for name in sorted(macro_fragments):
        if governed in texts[name]:
            rows.append(['fragment:' + name, hashlib.sha256(texts[name].encode()).hexdigest()])
    return rows


def authority_digest(root: Path, kind: str, revision: str | None = None) -> str:
    """Bind the scan's execution chain, not the whole make surface.

    Covered: the scanner and its rules (``AUTHORITY``), the shared consumers that
    decide scope and coverage (``COMMON_AUTHORITY``), and the make slice that
    decides this kind's command (``make_execution_surface``).
    """
    ordered = sorted(set(COMMON_AUTHORITY + AUTHORITY[kind]))
    digests = ({relative: hashlib.sha256((root / relative).read_bytes()).hexdigest() for relative in ordered}
               if revision is None else revision_blob_sha256(root, revision, ordered))
    rows: list[list] = [[relative, digests[relative]] for relative in ordered]
    rows.append(['make.execution.surface', make_execution_surface(root, kind, revision)])
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


def ref_object_types(root: Path, oids: Iterable[str]) -> dict[str, str]:
    """Resolve every referenced tip in one process.

    A per-ref ``cat-file -t`` spawns one Git process per reference, and scope
    selection validated the same candidate snapshots repeatedly, so the daily
    iteration entry spent its runtime in process startup rather than in the
    scan it was scoping. ``--batch-check`` returns the same object type for the
    same oid and keeps a missing or malformed tip a hard failure, exactly as the
    per-ref call did.
    """
    unique = sorted(set(oids))
    if not unique:
        return {}
    known = set(unique)
    result = subprocess.run(
        ['git', '-C', str(root), 'cat-file', '--batch-check=%(objectname) %(objecttype)'],
        input=''.join(oid + '\n' for oid in unique), text=True, capture_output=True, check=True)
    types: dict[str, str] = {}
    for row in result.stdout.splitlines():
        parts = row.split()
        if len(parts) != 2 or parts[0] not in known or parts[1] == 'missing':
            raise ValueError('unreadable scan reference')
        types[parts[0]] = parts[1]
    if set(types) != known:
        raise ValueError('unreadable scan reference')
    return types


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
        # Every declared (oid, type) pair stays independently asserted even when
        # two refs alias one oid, so a tampered snapshot cannot pass by aliasing.
        pairs = {(oid, typ) for _, oid, typ in refs}
        types = ref_object_types(root, (oid for oid, _ in pairs))
        if any(types.get(oid) != typ for oid, typ in pairs): return False
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
    # Concurrent shards share this evidence folder, so the temporary name must be
    # unique per writer; a fixed ``<kind>.tmp`` lets two writers delete each
    # other's temporary and makes ``os.replace`` fail with a spurious FileNotFoundError.
    descriptor, temporary_name = tempfile.mkstemp(prefix=f'.{kind}.', suffix='.tmp', dir=folder)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
            stream.write(json.dumps(proof, sort_keys=True))
        Path(temporary_name).replace(folder / (kind + '.json'))
    finally:
        Path(temporary_name).unlink(missing_ok=True)


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
