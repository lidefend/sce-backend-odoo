#!/usr/bin/env python3
"""Bounded, read-only run resolution; local receipts are NOT delivery gates.

JSON records are intentionally stdlib-only for the installed controller. No
commands from a run are executed. Only explicitly declared offline dependencies
can be reused; runtime evidence needs authoritative environment reconciliation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path

try:
    from scripts.ops.generated_evidence_paths import GENERATED_EVIDENCE_PATH_SET
except ModuleNotFoundError:
    from generated_evidence_paths import GENERATED_EVIDENCE_PATH_SET


class RunError(ValueError):
    pass


MAKE_TARGET_RE = re.compile(r'^([A-Za-z0-9][A-Za-z0-9_.-]*)\s*:(?!=)')
PHONY_RE = re.compile(r'^\s*\.PHONY\s*:(.*)$')
MAKE_NAME = r'[A-Za-z0-9_][A-Za-z0-9_.-]*'
MAKE_RULE_RE = re.compile(
    rf'^\s*(?P<targets>{MAKE_NAME}(?:\s+{MAKE_NAME})*)\s*:(?!=)\s*(?P<rhs>.*)$'
)
MAKE_ASSIGN_RE = re.compile(
    r'^\s*(?:export\s+|override\s+|private\s+)*'
    r'(?P<name>[A-Za-z_][A-Za-z0-9_.-]*)\s*(?::=|\?=|\+=|=)'
)
MAKE_TARGET_ASSIGN_RE = re.compile(
    r'^[A-Za-z_][A-Za-z0-9_.-]*\s*(?::=|\?=|\+=|=)'
)
MAKE_INCLUDE_RE = re.compile(r'^\s*(?:include|-include|sinclude)\s+(.*)$')
MAKE_VAR_REF_RE = re.compile(
    r'\$(?:\((?P<paren>[A-Za-z_][A-Za-z0-9_.-]*)\)|'
    r'\{(?P<brace>[A-Za-z_][A-Za-z0-9_.-]*)\})'
)
MAKE_RECURSIVE_CALL_RE = re.compile(
    rf'\$\(MAKE\)(?:\s+-[A-Za-z-]+(?:\s+\S+)?)*\s+'
    rf'(?P<targets>{MAKE_NAME}(?:\s+{MAKE_NAME})*)'
)
MAKE_FUNCTIONS = frozenset({
    'abspath', 'addprefix', 'addsuffix', 'and', 'basename', 'call', 'dir',
    'error', 'eval', 'file', 'filter', 'filter-out', 'findstring', 'firstword',
    'flavor', 'foreach', 'if', 'info', 'join', 'lastword', 'let', 'notdir',
    'or', 'origin', 'patsubst', 'realpath', 'shell', 'sort', 'strip', 'subst',
    'suffix', 'value', 'warning', 'wildcard', 'word', 'wordlist', 'words',
    'MAKE', 'CURDIR',
})
DELIVERY_STAGES = (
    'stage_0_scope_frozen',
    'stage_1_baseline_gates',
    'stage_2_candidate_manifest',
    'stage_3_candidate_commit',
    'stage_4_pr_validation',
    'stage_5_formal_build',
    'stage_6_rollback_rehearsal',
    'stage_7_merge_approval',
    'stage_8_post_merge_validation',
    'stage_9_deploy_r7',
)
DELIVERY_STAGE_STATES = frozenset({'not_started', 'in_progress', 'blocked', 'passed'})
RUN_STATUSES = frozenset({
    'planned',
    'active',
    'blocked',
    'verification_pending',
    'pending_merge_decision',
    'completed',
    'superseded',
})
DELIVERY_GATE_FIELDS = frozenset({
    'commit_approved',
    'candidate_commit',
    'pr_head_sha',
    'build_source_sha',
    'candidate_frontend_sha256',
    'rollback_source_sha',
    'rollback_artifact_sha256',
    'owner_merge_approved',
    'merged_main_sha',
    'deployment_approved',
    'deployed_source_sha',
    'deployment_target',
})


def defined_make_targets(root: Path) -> set[str]:
    """Every target the Makefile fragments declare, so a check cannot cite a
    non-existent entry point: an unexecutable check can never be recorded or
    reused, which silently degrades the ledger into repeated re-runs."""
    targets: set[str] = set()
    files = [root / 'Makefile', *sorted((root / 'make').glob('*.mk'))]
    for path in files:
        if not path.is_file():
            continue
        for line in path.read_text(encoding='utf-8', errors='replace').splitlines():
            match = MAKE_TARGET_RE.match(line)
            if match:
                targets.add(match.group(1))
            phony = PHONY_RE.match(line)
            if phony:
                targets.update(phony.group(1).split())
    return targets


def join_make_continuations(lines: list[str]) -> list[str]:
    """Join physical Makefile continuations without interpreting recipes."""
    joined: list[str] = []
    pending = ''
    for line in lines:
        current = pending + line
        if current.rstrip().endswith('\\'):
            pending = current.rstrip()[:-1].rstrip() + ' '
            continue
        joined.append(current)
        pending = ''
    if pending:
        joined.append(pending.rstrip())
    return joined


def git_bytes(root: Path, *args: str) -> bytes:
    result = subprocess.run(['git', '-C', str(root), *args], capture_output=True)
    if result.returncode:
        raise RunError(
            f'git {args[0]} failed: '
            f'{result.stderr.decode("utf-8", errors="replace").strip()}'
        )
    return result.stdout


def is_make_source(path: Path) -> bool:
    return path.name == 'Makefile' or path.suffix == '.mk'


def make_source_texts(root: Path, revision: str | None = None) -> dict[str, str]:
    """Read the literal, repository-local Makefile include closure.

    Dynamic includes (for example an optional ``.env`` file) carry invocation
    environment, not target recipe authority, and are intentionally not walked.
    """
    sources: dict[str, str] = {}

    def read(relative: str) -> str | None:
        path = Path(relative)
        if path.is_absolute() or '..' in path.parts:
            raise RunError(f'make include escapes worktree: {relative}')
        if not is_make_source(path):
            return None
        if revision is not None:
            try:
                return git_bytes(root, 'show', f'{revision}:{relative}').decode(
                    'utf-8', errors='replace'
                )
            except RunError:
                raise RunError(f'make include missing at {revision}: {relative}')
        candidate = local_path(root, relative)
        if not candidate.is_file():
            raise RunError(f'make include missing: {relative}')
        return candidate.read_text(encoding='utf-8', errors='replace')

    def visit(relative: str) -> None:
        if relative in sources:
            return
        text = read(relative)
        if text is None:
            return
        sources[relative] = text
        for logical in join_make_continuations(text.splitlines()):
            include = MAKE_INCLUDE_RE.match(logical)
            if not include:
                continue
            for token in include.group(1).split():
                if '$' in token or token.startswith('-'):
                    continue
                candidate = Path(token)
                if not is_make_source(candidate):
                    continue
                normalized = candidate.as_posix()
                visit(normalized)

    visit('Makefile')
    if 'Makefile' not in sources:
        raise RunError('Makefile is required for target-scoped dependency state')
    return sources


def parse_make_material(sources: dict[str, str]) -> tuple[
    dict[str, list[dict]], dict[str, list[str]], set[str]
]:
    """Index rule blocks, variable definitions and phony target identities."""
    rules: dict[str, list[dict]] = {}
    variables: dict[str, list[str]] = {}
    phony: set[str] = set()
    for relative, text in sources.items():
        lines = text.splitlines()
        index = 0
        while index < len(lines):
            raw = lines[index]
            stripped = raw.strip()
            phony_match = PHONY_RE.match(raw)
            if phony_match:
                phony.update(phony_match.group(1).split('#', 1)[0].split())
                index += 1
                continue
            if not stripped or stripped.startswith('#') or raw.startswith('\t'):
                index += 1
                continue
            assignment = MAKE_ASSIGN_RE.match(raw)
            if assignment:
                name = assignment.group('name')
                block = [f'{relative}:{index + 1}\n', raw]
                while (block[-1].rstrip().endswith('\\')
                       and index + 1 < len(lines)):
                    index += 1
                    block.append(lines[index])
                variables.setdefault(name, []).append('\n'.join(block) + '\n')
                index += 1
                continue
            rule = MAKE_RULE_RE.match(raw)
            if not rule:
                index += 1
                continue
            rhs = rule.group('rhs').split('#', 1)[0].split(';', 1)[0].strip()
            prerequisites = []
            if rhs and not MAKE_TARGET_ASSIGN_RE.match(rhs):
                prerequisites = [
                    token for token in rhs.split()
                    if token != '|' and not token.startswith('-')
                ]
            block = [f'{relative}:{index + 1}\n', raw]
            while index + 1 < len(lines):
                following = lines[index + 1]
                if not (following.startswith('\t')
                        or block[-1].rstrip().endswith('\\')):
                    break
                index += 1
                block.append(following)
            block_text = '\n'.join(block) + '\n'
            for target in rule.group('targets').split():
                rules.setdefault(target, []).append({
                    'text': block_text,
                    'prerequisites': prerequisites,
                })
            index += 1
    return rules, variables, phony


def make_target_material(
    root: Path,
    sources: dict[str, str],
    target: str,
    *,
    revision: str | None = None,
) -> str:
    """Fingerprint a target's recipe and literal dependency closure.

    Rule blocks from every active include, recursive ``$(MAKE)`` calls, the
    target's phony identity and every Make variable referenced by that material
    are included. Unrelated targets and unrelated variables are not.
    """
    rules, variables, phony = parse_make_material(sources)
    if target not in rules:
        location = f' at {revision}' if revision else ''
        raise RunError(f'make target {target!r} is not defined in the active include closure{location}')

    closure: list[str] = []
    pending = [target]
    while pending:
        current = pending.pop(0)
        if current in closure:
            continue
        closure.append(current)
        for block in rules.get(current, []):
            for dependency in block['prerequisites']:
                if '$' not in dependency and dependency in rules:
                    pending.append(dependency)
            for line in block['text'].splitlines():
                for call in MAKE_RECURSIVE_CALL_RE.finditer(line):
                    pending.extend(call.group('targets').split())

    material: list[str] = [f'make-target-closure-v1\t{target}\n']
    referenced: set[str] = set()
    for current in closure:
        blocks = rules.get(current, [])
        material.append(f'phony\t{current}\t{int(current in phony)}\n')
        for block in blocks:
            material.append(block['text'])
            for dependency in block['prerequisites']:
                if '$' in dependency:
                    referenced.update(
                        match.group('paren') or match.group('brace')
                        for match in MAKE_VAR_REF_RE.finditer(dependency)
                    )
                elif dependency not in rules:
                    path = Path(dependency)
                    if path.is_absolute() or '..' in path.parts:
                        material.append(f'external-prerequisite\t{dependency}\n')
                        continue
                    if revision is not None:
                        try:
                            content = git_bytes(root, 'show', f'{revision}:{dependency}')
                        except RunError:
                            material.append(f'missing-file-prerequisite\t{dependency}\n')
                            continue
                    else:
                        candidate = local_path(root, dependency)
                        if not candidate.is_file():
                            material.append(f'missing-file-prerequisite\t{dependency}\n')
                            continue
                        content = candidate.read_bytes()
                    digest = hashlib.sha256(content).hexdigest()
                    material.append(f'file-prerequisite\t{dependency}\t{digest}\n')
        for match in MAKE_VAR_REF_RE.finditer('\n'.join(block['text'] for block in blocks)):
            referenced.add(match.group('paren') or match.group('brace'))

    expanded: set[str] = set()
    while referenced - expanded:
        name = sorted(referenced - expanded)[0]
        expanded.add(name)
        if name in MAKE_FUNCTIONS:
            continue
        definitions = variables.get(name, [])
        if definitions:
            material.extend(definitions)
            for definition in definitions:
                referenced.update(
                    match.group('paren') or match.group('brace')
                    for match in MAKE_VAR_REF_RE.finditer(definition)
                )
        else:
            material.append(f'external-variable\t{name}\n')
        referenced.discard(name)
    return ''.join(material)


def git(root: Path, *args: str) -> str:
    result = subprocess.run(['git', '-C', str(root), *args], capture_output=True, text=True)
    if result.returncode:
        raise RunError(f'git {args[0]} failed: {result.stderr.strip()}')
    return result.stdout.rstrip("\n")


def local_path(root: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or '..' in path.parts or not value:
        raise RunError(f'expected repository-relative path: {value}')
    candidate = root / path
    if candidate.is_symlink():
        raise RunError(f"symlink path is unsupported: {value}")
    resolved = candidate.resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise RunError(f'path escapes worktree: {value}')
    return resolved


def read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise RunError(f'unreadable record {path}: {exc}') from exc
    if not isinstance(data, dict):
        raise RunError(f'expected object: {path}')
    return data


def resolve_run(root: Path) -> tuple[str, dict] | None:
    index_path = root / '.agent/active-runs.json'
    if not index_path.exists():
        return None
    index = read_json(index_path)
    if index.get('schema_version') != 1 or not isinstance(index.get('branches'), dict):
        raise RunError('invalid active-runs index')
    branch = git(root, 'branch', '--show-current')
    relative = index['branches'].get(branch)
    if relative is None:
        return None
    if not isinstance(relative, str) or not relative.startswith('.agent/runs/'):
        raise RunError('run must be under .agent/runs')
    run = read_json(local_path(root, relative))
    if run.get('schema_version') != 1 or run.get('branch') != branch:
        raise RunError('run schema or branch mismatch')
    if not re.fullmatch(r'[A-Za-z0-9_-]+', run.get('id', '')):
        raise RunError('invalid run id')
    baseline = run.get('baseline_sha', '')
    if not re.fullmatch(r'[0-9a-f]{40}', baseline):
        raise RunError('run baseline must be a full SHA')
    git(root, 'merge-base', '--is-ancestor', baseline, 'HEAD')
    for field in ('scope', 'checks', 'environment', 'next_exact_step', 'goal', 'record'):
        if not run.get(field) and field != 'checks':
            raise RunError(f'missing run field: {field}')
    if not isinstance(run.get('environment'), dict) or run['environment'].get('kind') not in ('offline', 'runtime'):
        raise RunError('environment must declare offline or runtime kind')
    if not isinstance(run.get('next_exact_step'), str) or not isinstance(run.get('blockers', []), list):
        raise RunError('invalid next step or blockers')
    if not isinstance(run.get('checks'), dict):
        raise RunError('checks must be an object')
    if not isinstance(run['scope'], list) or not all(isinstance(p, str) for p in run['scope']):
        raise RunError('scope must be a path list')
    for path in [*run['scope'], run['goal'], run['record']]:
        local_path(root, path)
    for field in ('goal', 'record'):
        if not local_path(root, run[field]).is_file():
            raise RunError(f'missing {field} file')
    make_targets = defined_make_targets(root)
    for check_id, check in run['checks'].items():
        if not isinstance(check, dict) or not re.fullmatch(r'verify\.[a-zA-Z0-9_.-]+', check.get('target', '')):
            raise RunError(f'check {check_id} must name a registered verify target')
        if check.get('kind') not in ('offline', 'runtime'):
            raise RunError(f"check {check_id} must declare kind offline|runtime; "
                           'an undeclared kind is never reusable and silently forces a rerun')
        for verdict in ('status', 'detail'):
            if verdict in check:
                raise RunError(f'check {check_id} must not declare {verdict}; the receipt written by '
                               'make agent.run.record is the only verdict; keep narrative in the run record')
        if check['target'] not in make_targets:
            raise RunError(f"check {check_id} names target {check['target']!r}, which no Makefile fragment defines")
        if (not isinstance(check.get('inputs'), list) or not check['inputs']
                or not all(isinstance(value, str) for value in check['inputs'])):
            raise RunError('check requires explicit dependency path strings')
        for value in check['inputs']:
            dependency_path(root, value)
        if 'readback' in check:
            readback_path(root, check['readback'])
    check_order(run['checks'])
    if run.get('status') not in RUN_STATUSES:
        raise RunError('invalid run status')
    validate_delivery_lifecycle(root, run)
    return relative, run


def validate_delivery_lifecycle(root: Path, run: dict) -> None:
    """Reject candidate-delivery runs that skip a stage or supporting identity.

    The lifecycle is optional for ordinary development runs. Once a run freezes
    candidate evidence, however, it must declare the complete stage ladder. This
    validates recorded identities and Owner approvals; it does not pretend that
    a local assertion proves an external CI, merge or deployment outcome.
    """
    lifecycle = run.get('delivery_lifecycle')
    if lifecycle is None:
        if run.get('candidate_evidence') is True:
            raise RunError('candidate evidence requires delivery_lifecycle')
        return
    if not isinstance(lifecycle, dict) or lifecycle.get('schema_version') != 1:
        raise RunError('delivery_lifecycle must be an object with schema_version=1')
    stages = lifecycle.get('stages')
    gates = lifecycle.get('gates')
    current = lifecycle.get('current_stage')
    if not isinstance(stages, dict) or tuple(stages) != DELIVERY_STAGES:
        raise RunError('delivery_lifecycle.stages must declare the complete ordered stage ladder')
    if not isinstance(gates, dict) or set(gates) != DELIVERY_GATE_FIELDS:
        raise RunError('delivery_lifecycle.gates must declare the exact supporting identity set')
    bad_states = {
        stage: value for stage, value in stages.items()
        if value not in DELIVERY_STAGE_STATES
    }
    if bad_states:
        raise RunError(f'invalid delivery stage states: {bad_states}')
    non_passed = [stage for stage in DELIVERY_STAGES if stages[stage] != 'passed']
    active = [stage for stage in DELIVERY_STAGES if stages[stage] in ('in_progress', 'blocked')]
    if len(active) > 1:
        raise RunError('delivery_lifecycle may have at most one in-progress or blocked stage')
    expected_current = non_passed[0] if non_passed else 'complete'
    if current != expected_current:
        raise RunError(
            f'delivery_lifecycle.current_stage must be {expected_current!r}, got {current!r}'
        )
    first_incomplete = non_passed[0] if non_passed else None
    later_stages = (
        DELIVERY_STAGES[DELIVERY_STAGES.index(first_incomplete) + 1:]
        if first_incomplete else ()
    )
    if any(stages[stage] == 'passed' for stage in later_stages):
        raise RunError('delivery stages cannot be passed after an earlier incomplete stage')

    def require_sha(field: str) -> str:
        value = gates.get(field)
        if not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{40}', value):
            raise RunError(f'delivery_lifecycle.gates.{field} must be a full commit SHA')
        return value

    def require_fingerprint(field: str) -> str:
        value = gates.get(field)
        if not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{64}', value):
            raise RunError(f'delivery_lifecycle.gates.{field} must be a SHA-256 fingerprint')
        return value

    if stages['stage_3_candidate_commit'] == 'passed':
        if gates['commit_approved'] is not True:
            raise RunError('candidate commit stage requires explicit commit approval')
        candidate = require_sha('candidate_commit')
        git(root, 'merge-base', '--is-ancestor', candidate, 'HEAD')
    if stages['stage_4_pr_validation'] == 'passed' or gates['pr_head_sha'] is not None:
        require_sha('candidate_commit')
        if gates['pr_head_sha'] != gates['candidate_commit']:
            raise RunError('PR validation must bind the exact approved candidate commit')
    if (stages['stage_5_formal_build'] == 'passed'
            or gates['build_source_sha'] is not None
            or gates['candidate_frontend_sha256'] is not None):
        require_sha('candidate_commit')
        if gates['build_source_sha'] != gates['candidate_commit']:
            raise RunError('formal build source must equal the approved candidate commit')
        require_fingerprint('candidate_frontend_sha256')
    if (stages['stage_6_rollback_rehearsal'] == 'passed'
            or gates['rollback_source_sha'] is not None
            or gates['rollback_artifact_sha256'] is not None):
        require_sha('rollback_source_sha')
        require_fingerprint('rollback_artifact_sha256')
    if stages['stage_7_merge_approval'] == 'passed' and gates['owner_merge_approved'] is not True:
        raise RunError('merge approval stage requires explicit Owner approval')
    if stages['stage_8_post_merge_validation'] == 'passed':
        require_sha('merged_main_sha')
    if stages['stage_9_deploy_r7'] == 'passed':
        if gates['deployment_approved'] is not True:
            raise RunError('deployment stage requires explicit Owner approval')
        require_sha('deployed_source_sha')
        if not isinstance(gates['deployment_target'], str) or not gates['deployment_target'].strip():
            raise RunError('deployment stage requires a declared target')


def check_order(checks: dict) -> list[str]:
    """Validate the declared DAG before any check can start."""
    ordered, visiting = [], set()
    def visit(key):
        if key in visiting:
            raise RunError('check dependency cycle')
        if key in ordered:
            return
        visiting.add(key)
        dependencies = checks[key].get('depends_on', [])
        if (not isinstance(dependencies, list)
                or any(not isinstance(dep, str) or dep not in checks for dep in dependencies)):
            raise RunError(f'check {key} has unknown or invalid dependencies')
        for dep in dependencies:
            visit(dep)
        visiting.remove(key)
        ordered.append(key)
    for key in checks:
        visit(key)
    return ordered


def declared_check_targets(run: dict) -> set[str]:
    """Return the executable targets declared by one resolved run.

    Impact planning supplies the required target set for the current delta.
    This helper owns the other half of the comparison so callers do not
    reimplement run-ledger parsing or accidentally treat path scope as check
    coverage.
    """
    return {check["target"] for check in run["checks"].values()}


def registration_missing_targets(run: dict, required_targets: set[str] | list[str]) -> list[str]:
    """Targets required by the current delta but absent from run registration."""
    return sorted(set(required_targets) - declared_check_targets(run))


def check_states(root: Path, run: dict) -> dict:
    states = {}
    for key in check_order(run['checks']):
        blocked = [dep for dep in run['checks'][key].get('depends_on', [])
                   if states[dep]['status'] != 'reusable']
        states[key] = (dict(target=run['checks'][key]['target'], status='blocked',
                            reason='prerequisite checks are not reusable', dependencies=blocked)
                       if blocked else evaluate(root, run, key))
    return states


def upstream_inputs(root: Path, run: dict, key: str) -> dict:
    state = {}
    def collect(current):
        for dep in run['checks'][current].get('depends_on', []):
            if dep not in state:
                state[dep] = {'check': run['checks'][dep],
                              'inputs': dependency_state(root, run['checks'][dep])}
                collect(dep)
    collect(key)
    return state


def delta_paths(root: Path, baseline: str) -> list[str]:
    paths: set[str] = set()
    for args in (('diff', '--no-renames', '--name-only', '-z', baseline, 'HEAD'),
                 ('diff', '--no-renames', '--name-only', '-z'),
                 ('diff', '--no-renames', '--cached', '--name-only', '-z'),
                 ('ls-files', '--others', '--exclude-standard', '-z')):
        paths.update(p for p in git(root, *args).split('\0') if p)
    return sorted(paths)


def dependency_path(root: Path, value: str) -> Path:
    path = local_path(root, value)
    relative = path.relative_to(root.resolve())
    if not relative.parts or relative.parts[0] in ('.git', '.runtime'):
        raise RunError('dependency must be bounded source/tool paths, not repository root or internal state')
    return path


READBACK_ROOTS = ('.runtime', 'artifacts')


def readback_path(root: Path, readback) -> str:
    """Validate a declared authoritative-environment readback artifact.

    A runtime receipt may only be reused through the exact artifact that proves
    the environment identity it recorded; the artifact is hashed into the
    check's dependency state below. It must live in the ignored runtime-evidence
    area, never in a source/tool path, so it can never masquerade as code.
    """
    if (not isinstance(readback, dict) or set(readback) != {'artifact'}
            or not isinstance(readback['artifact'], str) or not readback['artifact']):
        raise RunError('readback must declare exactly an artifact path string')
    value = readback['artifact']
    path = Path(value)
    if path.is_absolute() or '..' in path.parts:
        raise RunError(f'expected repository-relative path: {value}')
    if not path.parts or path.parts[0] not in READBACK_ROOTS:
        raise RunError('readback artifact must live under .runtime or artifacts')
    candidate = root / path
    if candidate.is_symlink():
        raise RunError(f'symlink path is unsupported: {value}')
    if not candidate.resolve().is_relative_to(root.resolve()):
        raise RunError(f'path escapes worktree: {value}')
    return value


# Derived bytecode is not an input. A declared input directory is walked
# recursively, so ``__pycache__`` used to enter a check's dependency state --
# and a ``.pyc`` embeds its source's mtime, so a governed generator that
# rewrites a generated ``.py`` with byte-identical content still changed the
# ``.pyc`` and invalidated an unchanged result. The ``.py`` source itself is
# hashed in full, so dropping the cache removes a false invalidation instead
# of weakening any check: no assertion, scope or covered target changes.
DERIVED_BYTECODE_SUFFIXES = frozenset({'.pyc', '.pyo'})


def is_derived_bytecode(path: Path) -> bool:
    return path.suffix in DERIVED_BYTECODE_SUFFIXES or '__pycache__' in path.parts


def comparable_inputs(state) -> dict:
    """Normalise a recorded or freshly walked state by dropping derived bytecode.

    The current walker never emits those keys, but a receipt written before
    that fix still carries them. Dropping them on both sides compares the same
    fact -- every declared ``.py`` source is still hashed in full -- instead of
    invalidating an unchanged result, and it can never hide a source change,
    because a source edit still moves the hash of the file that owns it.
    """
    if not isinstance(state, dict):
        return {}
    return {name: value for name, value in state.items() if not is_derived_bytecode(Path(name))}


def make_target_dependency_state(
    root: Path, check: dict, *, revision: str | None = None
) -> dict:
    target = check['target']
    material = make_target_material(
        root,
        make_source_texts(root, revision),
        target,
        revision=revision,
    )
    digest = hashlib.sha256(material.encode('utf-8')).hexdigest()
    return {f'make-target:{target}#closure': [digest, 0o644]}


def make_input_paths(check: dict) -> list[str]:
    return [value for value in check['inputs'] if is_make_source(Path(value))]


def historical_make_file_state(root: Path, revision: str, relative: str) -> list:
    tree = git(root, 'ls-tree', revision, '--', relative)
    if not tree:
        raise RunError(f'make input missing at receipt head: {relative}')
    metadata = tree.split('\t', 1)[0].split()
    if len(metadata) != 3 or metadata[1] != 'blob':
        raise RunError(f'make input is not a regular blob at receipt head: {relative}')
    content = git_bytes(root, 'show', f'{revision}:{relative}')
    return [
        hashlib.sha256(content).hexdigest(),
        int(metadata[0][-3:], 8),
    ]


def legacy_make_projection(
    root: Path,
    receipt: dict,
    check: dict,
    current: dict,
) -> dict | None:
    """Project a pre-target-scoped receipt onto the current Make fingerprint.

    Legacy receipts hashed the whole Make fragment. They may be carried forward
    only when Git proves each such file at the receipt head matched the recorded
    bytes, the receipt had no dirty Make source, and the selected target's
    material was byte-for-byte identical then and now. Anything less remains
    stale; this never treats the old whole-file hash as target-specific proof.
    """
    make_inputs = make_input_paths(check)
    if not make_inputs:
        return None
    recorded = comparable_inputs(receipt.get('inputs'))
    head = receipt.get('head')
    dirty = receipt.get('dirty')
    if not isinstance(head, str) or not re.fullmatch(r'[0-9a-f]{40}', head):
        return None
    if not isinstance(dirty, str):
        return None
    historical_sources = make_source_texts(root, head)
    dirty_paths = {
        line[3:].strip().split(' -> ')[-1].strip('"')
        for line in dirty.splitlines()
        if len(line) > 3
    }
    if any(is_make_source(Path(path)) or path in historical_sources for path in dirty_paths):
        return None
    for relative in make_inputs:
        try:
            recorded_state = recorded[relative]
            historical_state = historical_make_file_state(root, head, relative)
        except (KeyError, RunError):
            return None
        if recorded_state != historical_state or recorded.get(relative + '/') != 'file':
            return None
    historical = make_target_dependency_state(root, check, revision=head)
    if any(current.get(name) != value for name, value in historical.items()):
        return None
    projected = dict(recorded)
    for relative in make_inputs:
        projected.pop(relative, None)
        projected.pop(relative + '/', None)
    projected.update({name: current[name] for name in historical})
    return projected


def dependency_state(root: Path, check: dict) -> dict:
    state = {}
    if 'readback' in check:
        value = readback_path(root, check['readback'])
        path = root / value
        if not path.exists():
            state[value] = None
        elif path.is_dir():
            raise RunError('readback artifact must be a file, not a directory')
        else:
            state[value] = [hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mode & 0o777]
    make_inputs = []
    for value in check['inputs']:
        path = dependency_path(root, value)
        if is_make_source(path):
            make_inputs.append(value)
            continue
        if not path.exists():
            state[value] = None
            continue
        files = (sorted(file for file in path.rglob('*') if not is_derived_bytecode(file))
                 if path.is_dir() else [path])
        state[value + '/'] = 'directory' if path.is_dir() else 'file'
        for file in files:
            if file.is_symlink():
                raise RunError(f'symlink dependency is unsupported: {file}')
            if file.is_file():
                name = file.relative_to(root.resolve()).as_posix()
                state[name] = [hashlib.sha256(file.read_bytes()).hexdigest(), file.stat().st_mode & 0o777]
    if make_inputs:
        state.update(make_target_dependency_state(root, check))
    return state


def execution_input_state(root: Path, check: dict) -> dict:
    """Inputs that must remain fixed while a check executes.

    A runtime readback is the authoritative output of the run-time environment:
    a governed check may create or refresh that artifact while it executes. The
    final receipt still records its new hash, so any later readback change
    invalidates reuse. Source, tool and upstream dependencies remain frozen
    between ``begin`` and ``record``.
    """
    state = dependency_state(root, check)
    if 'readback' in check:
        state.pop(readback_path(root, check['readback']), None)
    return state


def receipt_path(root: Path, run: dict, check_id: str) -> Path:
    if check_id not in run['checks'] or not re.fullmatch(r'[A-Za-z0-9_-]+', check_id):
        raise RunError('unknown check id')
    return local_path(root, f'.runtime/agent-runs/{run["id"]}/{check_id}.json')


def evaluate(root: Path, run: dict, check_id: str) -> dict:
    check = run['checks'][check_id]
    path = receipt_path(root, run, check_id)
    result = {'target': check['target'], 'status': 'not_run', 'reason': 'no local receipt'}
    if not path.exists():
        return result
    try:
        receipt = read_json(path)
        result['source_head'] = receipt.get('head')
        if receipt.get('branch') != run['branch'] or receipt.get('run_id') != run['id']:
            raise RunError('receipt identity mismatch')
        git(root, 'merge-base', '--is-ancestor', receipt['head'], 'HEAD')
        current_inputs = dependency_state(root, check)
        recorded_inputs = comparable_inputs(receipt.get('inputs'))
        if (receipt.get('check') != check
                or recorded_inputs != comparable_inputs(current_inputs)):
            projected = legacy_make_projection(root, receipt, check, current_inputs)
            if projected is None or comparable_inputs(projected) != comparable_inputs(current_inputs):
                raise RunError('code, tool or dependency inputs changed')
        if receipt.get('upstream_inputs', {}) != upstream_inputs(root, run, check_id):
            raise RunError('upstream check inputs changed')
        if receipt.get('environment') != run['environment']:
            raise RunError('declared environment changed')
        if receipt.get('status') == 'failed':
            return dict(result, status='failed', reason='previous failure unchanged; diagnose before retry')
        log = local_path(root, receipt['log'])
        if hashlib.sha256(log.read_bytes()).hexdigest() != receipt.get('log_sha256'):
            raise RunError('evidence log changed')
        if receipt.get('status') != 'passed':
            return dict(result, status='failed', reason='previous failure unchanged; diagnose before retry')
        if type(receipt.get('test_count')) is not int or receipt['test_count'] <= 0:
            raise RunError('non-zero test count missing')
        if 'readback' not in check and check.get('kind') != 'offline':
            raise RunError('runtime evidence requires authoritative environment readback')
        if run['environment'].get('kind') != 'offline':
            raise RunError('runtime evidence requires authoritative environment readback')
        return dict(result, status='reusable', reason='declared inputs and original log unchanged', test_count=receipt['test_count'])
    except (RunError, OSError, KeyError, TypeError) as exc:
        return dict(result, status='stale', reason=str(exc))


def summary(root: Path) -> dict:
    selected = resolve_run(root)
    if selected is None:
        return {'status': 'unregistered', 'next_exact_step': 'Select/register one goal; do not infer completion or scan all historical goals.'}
    relative, run = selected
    paths = delta_paths(root, run['baseline_sha'])
    derived_scope = [p for p in paths if p in GENERATED_EVIDENCE_PATH_SET and p not in run['scope']]
    outside = [
        p for p in paths
        if p not in GENERATED_EVIDENCE_PATH_SET
        and not any(p == s or (s.endswith('/') and p.startswith(s)) for s in run['scope'])
    ]
    checks = check_states(root, run)
    reuse: dict[str, int] = {}
    for value in checks.values():
        reuse[value['status']] = reuse.get(value['status'], 0) + 1
    state = 'closed' if run['status'] in ('completed', 'superseded') else ('reconcile' if outside else 'resolved')
    return {'status': state, 'run': relative, 'check_reuse_summary': reuse,
            'branch': run['branch'], 'head': git(root, 'rev-parse', 'HEAD'),
            'dirty': git(root, 'status', '--porcelain=v1', '--untracked-files=all'),
            'baseline_sha': run['baseline_sha'], 'run_status': run['status'], 'record': run['record'],
            'changed_paths': paths, 'derived_scope': derived_scope,
            'outside_scope': outside, 'checks': checks,
            'registered_check_targets': sorted(declared_check_targets(run)),
            'blockers': run.get('blockers', []), 'next_exact_step': run['next_exact_step'],
            'write_replay_authorized': False,
            'candidate_evidence': run.get('candidate_evidence', False)}


def resume_prompt(root: Path) -> str:
    try:
        payload = summary(root)
    except (RunError, TypeError, KeyError) as exc:
        payload = {'status': 'reconcile', 'reason': str(exc), 'write_replay_authorized': False}
    return ('Repository run checkpoint (advisory, not authority):\n' + json.dumps(payload, ensure_ascii=False) +
            '\nUse the selected run and changed dependencies; do not repeat full inventory. '
            'Reconcile missing/stale/out-of-scope evidence before dependent work. '
            'A next step or reusable receipt never authorizes replaying a write or passing a delivery gate.')


def begin(root: Path, check_id: str, reverify_reason: str = '') -> None:
    selected = resolve_run(root)
    if selected is None:
        raise RunError('no registered run')
    _, run = selected
    if summary(root)['status'] != 'resolved':
        raise RunError('run is closed or out of scope; reconcile before testing')
    path = receipt_path(root, run, check_id).with_suffix('.pending.json')
    state = check_states(root, run)[check_id]
    if state['status'] in ('failed', 'blocked'):
        raise RunError(state['reason'])
    if state['status'] == 'reusable' and not reverify_reason.strip():
        raise RunError('check is reusable; an explicit reverify reason is required')
    check = run['checks'][check_id]
    declared_inputs = dependency_state(root, check)
    if any(value is None for value in declared_inputs.values()):
        raise RunError('declared dependency is missing; reconcile inputs before testing')
    payload = {'head': git(root, 'rev-parse', 'HEAD'), 'branch': run['branch'],
               'check': check, 'inputs': execution_input_state(root, check),
               'environment': run['environment'], 'started_at': time.time(),
               'reverify_reason': reverify_reason.strip(),
               'upstream_inputs': upstream_inputs(root, run, check_id)}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + '\n')


def record(root: Path, check_id: str, status: str, count: int, log_path: str) -> None:
    selected = resolve_run(root)
    if selected is None:
        raise RunError('no registered run')
    _, run = selected
    if summary(root)['status'] != 'resolved':
        raise RunError('run is closed or out of scope; reconcile before recording')
    path = receipt_path(root, run, check_id)
    if check_states(root, run)[check_id]['status'] == 'blocked':
        raise RunError('prerequisite evidence changed during execution')
    if status not in ('passed', 'failed') or (status == 'passed' and count <= 0):
        raise RunError('passed checks require non-zero tests')
    log = local_path(root, log_path)
    if not log.is_file() or not log.stat().st_size:
        raise RunError('readable nonempty original log required')
    pending_path = path.with_suffix('.pending.json')
    pending = read_json(pending_path)
    current_inputs = dependency_state(root, run['checks'][check_id])
    current_execution_inputs = execution_input_state(root, run['checks'][check_id])
    if 'readback' in run['checks'][check_id]:
        readback = readback_path(root, run['checks'][check_id]['readback'])
        if current_inputs.get(readback) is None:
            raise RunError('authoritative environment readback was not produced')
    if any(pending.get(key) != value for key, value in {
        'head': git(root, 'rev-parse', 'HEAD'), 'branch': run['branch'],
        'check': run['checks'][check_id], 'inputs': current_execution_inputs,
        'environment': run['environment'],
        'upstream_inputs': upstream_inputs(root, run, check_id)}.items()):
        raise RunError('test inputs or identity changed since begin; result cannot be recorded')
    receipt = {'schema_version': 1, 'duration_seconds': time.time() - pending['started_at'], 'run_id': run['id'], 'branch': run['branch'],
               'head': git(root, 'rev-parse', 'HEAD'), 'dirty': git(root, 'status', '--porcelain=v1'),
               'check': run['checks'][check_id], 'inputs': current_inputs,
               'environment': run['environment'], 'status': status, 'test_count': count,
               'log': log_path, 'log_sha256': hashlib.sha256(log.read_bytes()).hexdigest(),
               'reverify_reason': pending.get('reverify_reason', ''),
               'upstream_inputs': pending['upstream_inputs'],
               'attestation': 'executor-recorded; not a CI receipt', 'candidate_evidence': False}
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(receipt, indent=2) + '\n')
    os.replace(temporary, path)
    pending_path.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    operation = parser.add_mutually_exclusive_group()
    operation.add_argument('--record', metavar='CHECK_ID')
    operation.add_argument('--begin', metavar='CHECK_ID')
    parser.add_argument('--status', choices=['passed', 'failed'], default='failed')
    parser.add_argument('--test-count', type=int, default=0)
    parser.add_argument('--log', default='')
    parser.add_argument('--reverify-reason', default=os.environ.get('AGENT_REVERIFY_REASON', ''))
    args = parser.parse_args()
    try:
        if args.begin:
            begin(args.root.resolve(), args.begin, args.reverify_reason)
        if args.record:
            record(args.root.resolve(), args.record, args.status, args.test_count, args.log)
        payload = summary(args.root.resolve())
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if payload['status'] == 'resolved' else 2
    except (RunError, KeyError, TypeError) as exc:
        print(json.dumps({'status': 'reconcile', 'reason': str(exc)}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
