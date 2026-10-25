#!/usr/bin/env python3
"""Partition the existing backend scope; never cache or reduce test outcomes."""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import re
import sys
import functools
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import backend_impact_plan as impact
import backend_test_receipt as execution_receipt
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'ops'))
import evidence_scope


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
    'scripts/ops/evidence_scope.py',
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
        unresolved_imports = sorted({site for m in closure for site in graph[m].get('unresolved_imports', [])})
        unresolved_sql = sorted({site for m in closure for site in graph[m].get('unresolved_sql', [])})
        missing = sorted(reads - entries.keys())
        special = [path for path in paths if entries[path]['mode'] not in ('100644','100755') or entries[path]['kind'] != 'blob']
        external_imports = sorted({pkg for m in closure for pkg in graph[m].get('external_imports', [])})
        sql_reads = sorted({digest for m in closure for digest in graph[m].get('sql_reads', [])})
        dependency_blockers = []
        if unresolved:
            dependency_blockers.append('unresolved_file_reads')
        if unresolved_imports:
            dependency_blockers.append('unresolved_python_imports')
        if unresolved_sql:
            dependency_blockers.append('unresolved_sql_execute_sites')
        if missing:
            dependency_blockers.append('missing_file_inputs')
        if special:
            dependency_blockers.append('special_git_entries')
        closure_complete = not dependency_blockers
        identity = {'files':{path:entries[path] for path in paths}, 'declared_modules':sorted(closure),
                    'external_modules':sorted(external), 'external_imports':external_imports,
                    'sql_reads':sql_reads, 'unresolved_file_reads':unresolved,
                    'unresolved_imports':unresolved_imports, 'unresolved_sql':unresolved_sql,
                    'missing_file_inputs':missing, 'special_git_entries':special}
        targets[name] = {'target':name,'declared_module_closure':sorted(closure),
            'input_paths':paths,'direct_test_file_inputs':sorted(graph[name].get('file_inputs', [])),
            'known_inputs_sha256':hashlib.sha256(json.dumps(identity,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
            'external_modules':sorted(external),'external_imports':external_imports,
            'sql_reads':sql_reads,'unresolved_file_reads':unresolved,
            'unresolved_imports':unresolved_imports,'unresolved_sql':unresolved_sql,
            'missing_file_inputs':missing,'special_git_entries':special,
            'dependency_closure_complete':closure_complete,'reuse_ready':False,
            'blockers':dependency_blockers}
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
    plan = {**selected, 'base': base, 'head': head, 'shards': partition(selected['modules']) if selected['modules'] else []}
    if include_inputs:
        plan['input_inventory'] = target_input_inventory(head,after,plan['modules'])
    return plan


def compare_candidate_history(plan: dict, previous_heads: list[str]) -> dict:
    """Search source-input history per target, without authorizing execution reuse.

    Candidates may come from PR/branch iterations or the same-SHA retry. Only
    exact current/ancestor commits are supported here; a rebase or unrelated
    branch needs additional provenance and is refused, never silently ignored.
    History inventories are observations, not successful test receipts.
    """
    head = plan['head']
    if not previous_heads or not all(isinstance(value, str) and re.fullmatch('[0-9a-f]{40}', value)
                                    for value in [head, *previous_heads]):
        raise ValueError('history comparison requires exact candidate commits')
    distances = {}
    for previous in sorted(set(previous_heads)):
        impact.git('merge-base', '--is-ancestor', previous, head)
        distances[previous] = int(impact.git('rev-list', '--count', previous + '..' + head).strip())
    ordered = sorted(distances, key=lambda sha: (distances[sha], sha))
    modules = plan['modules']
    after = target_input_inventory(head, impact.snapshot(head), modules)
    histories = {}
    for previous in ordered:
        graph = impact.snapshot(previous)
        histories[previous] = target_input_inventory(previous, graph,
                                 [name for name in modules if name in graph])
    check = 'backend.module.known_inputs'
    decisions = []
    for name in modules:
        new = after['targets'][name]
        available = [sha for sha in ordered if name in histories[sha]['targets']]
        matching = [sha for sha in available if histories[sha]['targets'][name]['known_inputs_sha256']
                    == new['known_inputs_sha256']]
        selected = next(iter(matching or available), None)
        before = histories[selected] if selected else {'targets': {}, 'files': {}}
        old = before['targets'].get(name)
        document = {'schema': evidence_scope.UNITS_SCHEMA, 'check': check,
                    'identity': {'scope': 'known_source_inputs_only'},
                    'units': [{'id': name, 'fingerprint': new['known_inputs_sha256'], 'required': True}]}
        ledger = {'schema': evidence_scope.LEDGER_SCHEMA, 'check': check,
                  'identity': document['identity'], 'units': {
                      name: {'fingerprint': old['known_inputs_sha256'], 'status': 'observed'}
                  } if old else {}}
        verdict = evidence_scope.plan_units(document, ledger)
        paths = set(new['input_paths']) | set(old['input_paths'] if old else [])
        changed = sorted(path for path in paths
                         if before['files'].get(path) != after['files'].get(path))
        must_run = name in verdict['affected']
        decisions.append({
            'target': name, 'decision': 'RUN' if must_run else 'BLOCK',
            'reason': ('no_previous_target' if old is None else 'known_inputs_changed') if must_run
                      else 'known_inputs_equal_but_authenticated_reuse_evidence_missing',
            'input_comparison_candidate': selected,
            'input_matching_candidates': matching,
            'same_candidate_retry': selected == head,
            'previous_input_fingerprint': old['known_inputs_sha256'] if old else None,
            'input_fingerprint': new['known_inputs_sha256'], 'changed_known_inputs': changed,
            'previous_receipt': None, 'required_evidence': new['blockers'],
            'estimated_saved_time': 0, 'actual_duration': None,
        })
    return {'schema': 'backend-candidate-comparison/v1', 'mode': 'shadow_only',
            'integration_base': plan['base'], 'head': head,
            'candidate_history': ordered, 'candidate_distance': distances,
            'history_order': 'matching_inputs_first_then_git_distance_then_sha',
            'previous_candidate_execution_verified': False,
            'integration_modules': list(modules), 'decisions': decisions,
            'counts': {key: sum(row['decision'] == key for row in decisions)
                       for key in ('RUN', 'REUSE', 'BLOCK')},
            'execution_selection_changed': False, 'reuse_authority': False,
            'evidence_engine': verdict['schema'],
            'limitations': ['source_comparison_not_receipt_selection',
                           'run_attempt_success_environment_and_scope_not_verified',
                           'non_ancestor_history_not_supported']}


def compare_previous_candidate(plan: dict, previous_head: str) -> dict:
    result = compare_candidate_history(plan, [previous_head])
    result['incremental_base'] = previous_head
    return result


def select_historical_receipts(plan: dict, locators: list[dict]) -> dict:
    """Authenticate remote target results before choosing a history reference.

    Locators are untrusted addresses, not verdicts. Source authentication does
    not certify full dependencies/environment; this stage never authorizes skip.
    """
    if not isinstance(locators, list) or len(locators) > 256:
        raise ValueError('receipt history must be a bounded list')
    fields = {'head', 'module', 'run_id', 'attempt', 'artifact_id', 'shard'}
    modules, head = plan['modules'], plan['head']
    if not isinstance(head, str) or not re.fullmatch('[0-9a-f]{40}', head):
        raise ValueError('exact current candidate required')
    for item in locators:
        if (not isinstance(item, dict) or set(item) != fields
                or not isinstance(item['head'], str) or not re.fullmatch('[0-9a-f]{40}', item['head'])
                or item['module'] not in modules
                or any(type(item[k]) is not int or item[k] <= 0 for k in ('run_id', 'attempt', 'artifact_id'))
                or type(item['shard']) is not int or item['shard'] < 0):
            raise ValueError('invalid history locator; no producer verdict fields accepted')
    unique = {json.dumps(item, sort_keys=True): item for item in locators}
    current = target_input_inventory(head, impact.snapshot(head), modules)
    accepted, rejected = {name: [] for name in modules}, []
    now = datetime.now(timezone.utc)
    # Request-local byte cache only: repeated module lookups share archive GETs.
    # Nothing is persisted or treated as a reusable test result by this cache.
    fetch = functools.lru_cache(maxsize=8)(execution_receipt.github_bytes)
    for key in sorted(unique):
        item = unique[key]
        try:
            # Reuse is decided by verifiable input equivalence, not Git ancestry.
            # A sibling branch with identical content-addressed inputs is a valid
            # reuse source; verify_github_origin binds the platform run/source
            # tree and receipt_reuse_authorized then requires independent closure
            # attestation, so ancestry adds no safety and only blocks reuse.
            verified = execution_receipt.verify_github_origin(
                run_id=item['run_id'], attempt=item['attempt'], artifact_id=item['artifact_id'],
                shard=item['shard'], expected_head=item['head'], module=item['module'], now=now, fetch=fetch)
            scope = verified.get('scope_plan') or {}
            fingerprint = scope.get('known_inputs_sha256')
            if (verified.get('integrity') != 'verified' or verified.get('platform_origin') != 'verified'
                    or verified.get('module') != item['module'] or verified.get('source_head') != item['head']
                    or scope.get('target') != item['module']
                    or not isinstance(fingerprint, str) or not re.fullmatch('[0-9a-f]{64}', fingerprint)):
                raise ValueError('authenticated target input binding missing')
            issued = datetime.fromisoformat(verified['issued_at'])
            if issued.tzinfo is None:
                raise ValueError('receipt issue time lacks timezone')
            accepted[item['module']].append((item, verified, issued))
        except (ValueError, KeyError, TypeError, AttributeError, OSError, subprocess.SubprocessError) as exc:
            # A hash-authenticated archive may still contain malformed producer
            # JSON. Reject that candidate without hiding older valid results.
            rejected.append({'locator': item, 'reason': type(exc).__name__ + ': ' + str(exc)})
    decisions = []
    for name in modules:
        target = current['targets'][name]
        fingerprint = target['known_inputs_sha256']
        candidates = sorted(accepted[name], key=lambda row: (
            row[1]['scope_plan']['known_inputs_sha256'] == fingerprint, row[2],
            row[0]['run_id'], row[0]['attempt'], row[0]['artifact_id']), reverse=True)
        selected = candidates[0] if candidates else None
        document = {'schema': evidence_scope.UNITS_SCHEMA, 'check': 'backend.module.known_inputs',
                    'identity': {'scope': 'known_source_inputs_only'},
                    'units': [{'id': name, 'fingerprint': fingerprint, 'required': True}]}
        ledger = {'check': document['check'], 'identity': document['identity'], 'units': {}}
        reuse_authorized, reuse_authorized_blockers = False, []
        if selected:
            reuse_authorized, reuse_authorized_blockers = execution_receipt.receipt_reuse_authorized(selected[1])
            ledger['units'][name] = {'fingerprint': selected[1]['scope_plan']['known_inputs_sha256'],
                                    'status': 'passed' if reuse_authorized else 'observed'}
        verdict = evidence_scope.plan_units(document, ledger)
        must_run = name in verdict['affected']
        reusable = name in verdict['reusable']
        failures = [row for row in rejected if row['locator']['module'] == name]
        if reusable:
            decision = 'REUSE'
        elif not selected and failures:
            decision = 'BLOCK'
        elif must_run:
            decision = 'RUN'
        else:
            decision = 'BLOCK'
        decisions.append({'target': name, 'decision': decision,
            'reason': ('history_authentication_failed' if failures else 'no_successful_history') if not selected
                      else ('authenticated_reuse_ready_inputs_match' if reusable
                            else ('known_inputs_changed' if must_run
                                  else 'authenticated_result_missing_reuse_proofs')),
            'reuse_authorized': reuse_authorized,
            'reuse_authorized_blockers': reuse_authorized_blockers,
            'input_fingerprint': fingerprint,
            'previous_receipt': {'locator': selected[0], 'sha256': selected[1]['receipt_sha256']} if selected else None,
            'verified_successful_candidates': len(candidates), 'rejected_candidates': failures,
            'required_evidence': sorted(set(target['blockers'] + (selected[1]['blockers'] if selected else []))),
            'previous_actual_duration': selected[1]['actual_duration_seconds'] if selected else None,
            'actual_duration': None,
            'estimated_saved_time': selected[1]['actual_duration_seconds'] if reusable else 0})
    return {'schema': 'backend-remote-receipt-selection/v1', 'mode': 'shadow_only',
            'head': head, 'integration_base': plan['base'], 'decisions': decisions,
            'counts': {key: sum(row['decision'] == key for row in decisions) for key in ('RUN', 'REUSE', 'BLOCK')},
            'locators_checked': len(unique), 'rejected': rejected,
            'execution_selection_changed': False,
            'reuse_authority': any(row['decision'] == 'REUSE' for row in decisions)}


def apply_reuse_decision(plan: dict, decisions: list[dict]) -> dict:
    """Partition only RUN targets; REUSE/BLOCK are carried, never executed.

    A scope that is entirely REUSE or BLOCK yields zero shards, so no test
    shard, Docker build or database is created. Coverage must account for every
    selected module exactly once; a partial or ambiguous decision is refused.
    """
    if not isinstance(plan, dict) or not isinstance(plan.get('modules'), list):
        raise ValueError('plan with selected modules required')
    if not isinstance(decisions, list) or not decisions:
        raise ValueError('non-empty reuse decision list required')
    by_target: dict[str, str] = {}
    for row in decisions:
        target, decision = row.get('target'), row.get('decision')
        if (not isinstance(target, str) or target not in plan['modules']
                or decision not in ('RUN', 'REUSE', 'BLOCK') or target in by_target):
            raise ValueError('decision outside selected scope, invalid or duplicated')
        by_target[target] = decision
    if set(by_target) != set(plan['modules']):
        raise ValueError('reuse decision does not cover the selected scope')
    block = sorted(target for target, decision in by_target.items() if decision == 'BLOCK')
    if block:
        raise ValueError('blocked targets must not be passed to execution: ' + ', '.join(block))
    run = sorted(target for target, decision in by_target.items() if decision == 'RUN')
    reuse = sorted(target for target, decision in by_target.items() if decision == 'REUSE')
    result = dict(plan)
    result['shards'] = partition(run) if run else []
    result['reuse_decision'] = {'schema': 'backend-reuse-decision/v1',
                                'run': run, 'reuse': reuse, 'block': block,
                                'execution_required': bool(run),
                                'decisions': decisions}
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', default='')
    parser.add_argument('--head', required=True)
    parser.add_argument('--modules', default='')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--github-output', type=Path)
    parser.add_argument('--shard', type=int)
    parser.add_argument('--input-inventory', action='store_true')
    parser.add_argument('--previous-candidate', action='append', help='Repeat for exact historical candidates, including same-SHA retry; source comparison only')
    parser.add_argument('--receipt-history', type=Path, help='JSON list of exact remote artifact locators; authenticate and select per target without skipping CI')
    parser.add_argument('--discover-receipts', action='store_true', help='Discover recent successful remote receipts and apply authenticated reuse before partition')
    args = parser.parse_args()
    plan = build_plan(args.base, args.head, args.modules, include_inputs=args.input_inventory)
    if args.previous_candidate:
        plan['candidate_comparison'] = compare_candidate_history(plan, args.previous_candidate)
    if args.discover_receipts or args.receipt_history:
        locators = (json.loads(args.receipt_history.read_text()) if args.receipt_history
                    else execution_receipt.discover_receipt_locators(head=plan['head'], modules=plan['modules']))
        result = select_historical_receipts(plan, locators)
        if args.discover_receipts:
            # Auto-discovery is an optimization, not a correctness gate: a
            # discovered but non-reusable receipt falls back to RUN (fresh
            # execution). Only an explicit caller-supplied locator that fails
            # authentication stays BLOCK as a fail-closed signal.
            decisions = [dict(row, decision='RUN') if row['decision'] == 'BLOCK' else row
                         for row in result['decisions']]
            result = {**result, 'decisions': decisions,
                      'counts': {key: sum(row['decision'] == key for row in decisions)
                                 for key in ('RUN', 'REUSE', 'BLOCK')},
                      'reuse_authority': any(row['decision'] == 'REUSE' for row in decisions)}
        plan = apply_reuse_decision(plan, result['decisions'])
        plan['receipt_history'] = result
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
            output.write('required=' + str(bool(plan['shards'])).lower() + '\n')
            output.write('reuse_authority=' + str(bool(plan.get('reuse_decision', {}).get('reuse'))).lower() + '\n')


if __name__ == '__main__':
    main()
