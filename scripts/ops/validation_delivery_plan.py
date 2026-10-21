#!/usr/bin/env python3
"""Read-only readiness diagnostics; existing validators remain the authorities.

No tests, deployment, credential reads, evidence recording or merge are executed.
The merge mode obtains the actual PR base/head instead of trusting BASE_SHA.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.ops import agent_run_context as runs
from scripts.verify import acceptance_evolution_binding_guard as binding


def pr_identity(pr: str, expected: str) -> dict:
    if not pr.isdigit() or not binding.SHA_RE.fullmatch(expected):
        raise binding.BindingError('PR must be numeric; EXPECTED_HEAD must be a full 40-character SHA')
    command = ['gh', 'pr', 'view', pr, '--json',
               'number,state,isCrossRepository,headRefOid,baseRefOid,baseRefName,url']
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=True)
    data = json.loads(result.stdout)
    if (data.get('state') != 'OPEN' or data.get('isCrossRepository') is not False
            or data.get('baseRefName') != 'main' or data.get('headRefOid') != expected
            or str(data.get('number')) != pr
            or not binding.SHA_RE.fullmatch(str(data.get('baseRefOid', '')))):
        raise binding.BindingError('PR identity is not the expected open same-repository main candidate: '
                                   f'expected_head={expected} actual_head={data.get("headRefOid")}')
    # GitHub can still report the PR's previous base while main has advanced.
    # Resolve the target ref independently before accepting its evidence scope.
    live = subprocess.run(['gh', 'api', 'repos/{owner}/{repo}/git/ref/heads/main',
                           '--jq', '.object.sha'], cwd=ROOT, text=True,
                          capture_output=True, check=True).stdout.strip()
    if not binding.SHA_RE.fullmatch(live) or live != data['baseRefOid']:
        raise binding.BindingError('live main differs from PR base; synchronize and revalidate: '
                                   f'pr_base={data["baseRefOid"]} live_main={live}')
    if runs.git(ROOT, 'rev-parse', 'HEAD') != expected:
        raise binding.BindingError('local head does not match PR head')
    return data


def evidence_states(registry: dict, plan: dict, manifest: dict, dirty: list[str]) -> dict:
    states = {}
    for suite_id in plan['required_evidence_suites']:
        suite = registry['suites'][suite_id]
        state = {'status': 'missing', 'entrypoints': suite['entrypoints']}
        changed = [path for path in dirty if binding.suite_owns_path(registry, suite_id, path)]
        record = manifest.get('suites', {}).get(suite_id)
        if changed:
            state.update(status='affected', reason='uncommitted suite inputs changed', changed_inputs=changed)
        elif record is None:
            state['reason'] = 'no recorded runtime evidence; resolve environment and credential authority before execution'
        else:
            try:
                candidate = dict(record)
                candidate['bound_head'] = record.get('bound_head') or manifest.get('head_sha')
                binding.validate_suite_record(registry, suite_id, candidate, plan['head_sha'],
                                              str(manifest.get('recorded_at') or ''))
                state.update(status='reusable', source_head=candidate['bound_head'])
            except (binding.BindingError, TypeError, ValueError, OSError, AttributeError) as exc:
                state.update(status='invalid', reason=str(exc))
        states[suite_id] = state
    return states


def build_report(base: str, head: str, manifest_path: Path, *, frozen: bool = False, stage: str = "all") -> dict:
    registry = binding.load_registry(binding.DEFAULT_REGISTRY)
    dirty = runs.delta_paths(ROOT, head)
    plan = binding.build_plan(registry, runs.delta_paths(ROOT, base), base, head)
    blockers = []
    try:
        manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
        if manifest and (manifest.get('schema') != binding.EVIDENCE_SCHEMA
                         or not isinstance(manifest.get('suites'), dict)):
            raise ValueError('invalid evidence manifest schema/suites')
    except (OSError, ValueError, AttributeError) as exc:
        manifest = {}
        blockers.append('evidence manifest: ' + str(exc))
    stage_plan = binding.plan_for_stage(registry, plan, stage)
    deferred = stage_plan['deferred_evidence_suites']
    states = evidence_states(registry, stage_plan, manifest, dirty)
    if plan['unclassified']:
        blockers.append('unclassified paths: ' + ', '.join(plan['unclassified']))
    if frozen and dirty:
        blockers.append('merge requires a clean frozen candidate')
    for key, state in states.items():
        if state['status'] != 'reusable':
            blockers.append(key + ': ' + state['reason'])
    try:
        local = runs.summary(ROOT)
    except (runs.RunError, OSError, ValueError) as exc:
        local = {'status': 'reconcile', 'reason': str(exc)}
    return {'schema': 'validation_delivery_plan.v1', 'head': head, 'base': base,
            'dirty_paths': dirty, 'impact': plan, 'local_checks': local,
            'runtime_evidence': states, 'blockers': blockers,
            'stage': stage, 'deferred_evidence': {key: {'status': 'not_run', 'required_stages': registry['suites'][key]['stages']} for key in deferred},
            'status': 'blocked' if blockers else 'ready_for_existing_gates',
            'candidate_evidence': False, 'writes_authorized': False,
            'limits': ['No runtime readback or credential verification performed',
                       'Quick, independent review and current remote CI remain mandatory']}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pr')
    parser.add_argument('--expected-head')
    parser.add_argument('--base')
    parser.add_argument('--stage', choices=['all', 'merge', 'deployment'], default='all')
    parser.add_argument('--manifest', type=Path, default=ROOT / '.runtime/acceptance-evolution/evidence.v1.json')
    parser.add_argument('--output', type=Path, default=ROOT / '.runtime/validation-delivery/plan.json')
    parser.add_argument('--require-ready', action='store_true')
    parser.add_argument('--verify-pr-identity', action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.pr and args.stage not in {'all', 'merge'}:
            raise binding.BindingError('PR preflight always evaluates the merge stage')
        identity = pr_identity(args.pr, args.expected_head or '') if args.pr else None
        if args.verify_pr_identity:
            previous = json.loads(args.output.read_text())
            if not identity or previous.get('pr_identity') != identity:
                raise binding.BindingError('PR source/target identity drifted since preflight')
            report = build_report(identity['baseRefOid'], identity['headRefOid'], args.manifest, frozen=True, stage="merge")
            if report['blockers']:
                raise binding.BindingError('evidence changed since preflight: ' + '; '.join(report['blockers']))
            return 0
        head = runs.git(ROOT, 'rev-parse', 'HEAD')
        # PR mode never consumes caller-selected BASE_SHA/HEAD_SHA or --base.
        base = identity['baseRefOid'] if identity else (args.base or binding.resolve_base(None, head))
        binding.resolve_head(base)  # require locally available exact target commit
        report = build_report(base, head, args.manifest, frozen=bool(identity), stage="merge" if identity else args.stage)
        report['pr_identity'] = identity
        binding.write_json(args.output, report)
        print(json.dumps({key: report[key] for key in ('status', 'head', 'base', 'blockers', 'candidate_evidence', 'limits')}, ensure_ascii=False, indent=2))
        print(f'[validation.delivery.plan] report={args.output}')
        return 1 if args.require_ready and report['blockers'] else 0
    except (binding.BindingError, runs.RunError, OSError, ValueError, TypeError,
            subprocess.CalledProcessError) as exc:
        print(json.dumps({'status': 'blocked', 'reason': str(exc)}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
