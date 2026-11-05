#!/usr/bin/env python3
"""Bind changed ORM methods to selectors and actual execution log identities."""
from __future__ import annotations

import argparse
import ast
import json
import hashlib
import io
import zipfile
import re
import time
import os
from scheduled_validation import scheduled_slot
from datetime import datetime
from pathlib import Path

import backend_impact_plan as impact
import backend_test_receipt as receipts
from ci_risk_classifier import classify

MANAGED_MODULE = 'smart_construction_acceptance_fixture'
MANAGED_TARGET = 'acceptance.frontend.fixture_orm'


def inventory(source: str, path: str) -> list[dict]:
    parts = path.split('/')
    if (len(parts) < 4 or parts[0] not in impact.ROOTS or parts[2] != 'tests'
            or not parts[-1].startswith('test') or not path.endswith('.py')):
        return []
    tree = ast.parse(source, filename=path)
    # Relative common-case imports are conservatively treated as ORM. Pure
    # unittest files declare their standard-library runner explicitly.
    imports = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
    pure = any((isinstance(n, ast.ImportFrom) and n.module == 'unittest') or
               (isinstance(n, ast.Import) and any(a.name == 'unittest' for a in n.names)) for n in imports)
    orm = any(isinstance(n, ast.ImportFrom) and (n.module or '').startswith('odoo') for n in imports)
    kind = 'python' if pure and not orm else 'orm'
    module = parts[1]
    logger = 'odoo.addons.' + module + '.' + '.'.join(parts[2:])[:-3]
    rows = []
    for cls in tree.body:
        if not isinstance(cls, ast.ClassDef):
            continue
        for method in cls.body:
            if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)) and method.name.startswith('test_'):
                rows.append({'path': path, 'module': module, 'class': cls.name,
                             'method': method.name, 'logger': logger, 'kind': kind,
                             'selector': f'/{module}:{cls.name}.{method.name}',
                             'owner': MANAGED_TARGET if module == MANAGED_MODULE else 'backend_suite',
                             'status': 'pending'})
    return rows


def managed_tests(head: str) -> list[dict]:
    paths = impact.git('ls-tree', '-r', '--name-only', head, '--',
                       'addons/' + MANAGED_MODULE + '/tests').splitlines()
    return [row for path in paths if path.endswith('.py')
            for row in inventory(impact.git('show', head + ':' + path), path)]


def changed_tests(base: str, head: str) -> list[dict]:
    if not base:
        return []
    paths = impact.git('diff', '--no-renames', '--diff-filter=AM', '--name-only', base, head, '--').splitlines()
    if 'navigation_maintenance' in classify(paths, event_name='pull_request').orm_scopes:
        # The dedicated navigation regression belongs to the governed fixture,
        # even when this PR only changes its production inputs.
        for name in ('test_business_scene_lifecycle.py', 'test_scenario_navigation_maintenance.py'):
            path = f'addons/{MANAGED_MODULE}/tests/{name}'
            if path not in paths:
                paths.append(path)
    rows = []
    for path in paths:
        if '/tests/' in path and path.endswith('.py'):
            rows.extend(inventory(impact.git('show', head + ':' + path), path))
    return rows


def verify_logs(rows: list[dict], logs: list[str]) -> list[dict]:
    text = '\n'.join(logs)
    result = []
    for row in rows:
        identity = re.escape(row['logger']) + r': Starting ' + re.escape(row['class'] + '.' + row['method']) + r'(?:\s|\(|$)'
        # An overall non-zero suite cannot stand in for the changed method.
        if row.get('kind') == 'python':
            identity = re.escape(row['method']) + r' \((?:[\w.]+\.)?' + re.escape(
                Path(row['path']).stem + '.' + row['class'] + '.' + row['method']) + r'\).*?\.\.\. ok(?:\n|$)'
        matched = bool(re.search(identity, text))
        skipped = any('skipp' in line.lower() and row['class'] + '.' + row['method'] in line
                      for line in text.splitlines())
        result.append({**row, 'status': 'executed' if matched and not skipped and row['owner'] != MANAGED_TARGET else 'pending'})
    return result


def managed_report(head: str, log: str) -> dict:
    if impact.git('rev-parse', 'HEAD').strip() != head:
        raise ValueError('managed evidence must bind the checked out candidate')
    summaries = re.findall(r'(\d+) failed, (\d+) error\(s\) of (\d+) tests', log)
    if not summaries or any(int(f) or int(e) for f, e, _ in summaries) or int(summaries[-1][2]) <= 0:
        raise ValueError('managed ORM evidence lacks a passing nonzero summary')
    rows = managed_tests(head)
    observed = verify_logs([dict(r, owner='backend_suite') for r in rows], [log])
    return {'schema': 'managed-changed-tests/v1', 'head': head, 'owner': MANAGED_TARGET,
            'log_sha256': hashlib.sha256(log.encode()).hexdigest(),
            'executed': [r['selector'] for r in observed if r['status'] == 'executed']}


def authenticate_managed_report(head: str, run: dict, artifact: dict, raw: bytes, *, schedule_slot: str | None = None) -> dict:
    for field in ('repository', 'head_repository'):
        if run.get(field, {}).get('full_name') != receipts.REPOSITORY or run[field].get('id') != receipts.REPOSITORY_ID:
            raise ValueError('foreign managed evidence repository')
    if (run.get('head_sha') != head or run.get('conclusion') != 'success'
            or run.get('status') != 'completed' or run.get('run_attempt') != 1
            or run.get('path') != '.github/workflows/frontend_release_gate.yml'):
        raise ValueError('managed run identity, attempt or outcome mismatch')
    if schedule_slot and (run.get('event') != 'schedule' or scheduled_slot(run.get('created_at', '')) != schedule_slot):
        raise ValueError('managed evidence is not from this scheduled validation slot')
    origin = artifact.get('workflow_run', {})
    if (artifact.get('name') != f"managed-orm-{run['id']}-1-{head}"
            or artifact.get('expired') is not False or origin.get('id') != run['id']
            or origin.get('head_sha') != head
            or origin.get('repository_id') != receipts.REPOSITORY_ID
            or origin.get('head_repository_id') != receipts.REPOSITORY_ID
            or artifact.get('digest') != 'sha256:' + hashlib.sha256(raw).hexdigest()):
        raise ValueError('managed artifact origin or digest mismatch')
    if len(raw) > receipts.ARCHIVE_LIMIT:
        raise ValueError('managed artifact too large')
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        if any(info.file_size > 1024 * 1024 for info in archive.infolist()):
            raise ValueError('managed report too large')
        if archive.namelist() != ['managed-test-evidence.json']:
            raise ValueError('unexpected managed artifact contents')
        report = json.loads(archive.read('managed-test-evidence.json'))
    if (report.get('schema') != 'managed-changed-tests/v1' or report.get('head') != head
            or report.get('owner') != MANAGED_TARGET
            or not isinstance(report.get('executed'), list)
            or not all(isinstance(x, str) for x in report['executed'])
            or not re.fullmatch('[0-9a-f]{64}', str(report.get('log_sha256', '')))):
        raise ValueError('invalid managed test evidence')
    return {**report, 'run_id': run['id'], 'artifact_id': artifact['id'], 'artifact_digest': artifact['digest']}


def discover_managed_evidence(head: str, *, schedule_slot: str | None = None) -> dict | None:
    runs = json.loads(receipts.github_bytes(
        f'actions/workflows/frontend_release_gate.yml/runs?head_sha={head}&per_page=100'))
    for run in sorted(runs.get('workflow_runs', []), key=lambda r: r['id'], reverse=True):
        if schedule_slot and (run.get('event') != 'schedule' or scheduled_slot(run.get('created_at', '')) != schedule_slot):
            continue
        if (run.get('head_sha') != head or run.get('path') != '.github/workflows/frontend_release_gate.yml'
                or any(run.get(key, {}).get('full_name') != receipts.REPOSITORY
                       or run.get(key, {}).get('id') != receipts.REPOSITORY_ID
                       for key in ('repository', 'head_repository'))):
            continue
        event = os.environ.get('GITHUB_EVENT_NAME')
        if event in ('pull_request', 'push', 'workflow_dispatch') and run.get('event') != event:
            continue
        # The latest eligible producer is authoritative. Never wait out a known
        # failure or fall back to an older success while its replacement runs.
        if run.get('status') != 'completed':
            return None
        url = f"https://github.com/{receipts.REPOSITORY}/actions/runs/{run['id']}"
        jobs = json.loads(receipts.github_bytes(f"actions/runs/{run['id']}/jobs?per_page=100"))
        producers = [job for job in jobs.get('jobs', [])
                     if job.get('name') in ('frontend_release_gate', 'managed_orm')]
        if producers and all(job.get('conclusion') == 'skipped' for job in producers):
            # An unrelated label event selects neither producer and must not
            # shadow the current validation run for the same PR head.
            continue
        if not producers:
            raise ValueError(f"Managed ORM producer job identity missing: {url}")
        if run.get('conclusion') != 'success':
            raise ValueError(f"Managed ORM producer failed: {url} conclusion={run.get('conclusion')}")
        if run.get('run_attempt') != 1:
            raise ValueError(f"Managed ORM producer attempt lacks supported receipt authentication: {url}")
        artifacts = json.loads(receipts.github_bytes(f"actions/runs/{run['id']}/artifacts?per_page=100"))
        for artifact in artifacts.get('artifacts', []):
            if artifact.get('name') == f"managed-orm-{run['id']}-1-{head}":
                # Resolve authoritative artifact metadata before downloading bytes.
                artifact = json.loads(receipts.github_bytes(f"actions/artifacts/{artifact['id']}"))
                return authenticate_managed_report(head, run, artifact,
                    receipts.github_bytes(f"actions/artifacts/{artifact['id']}/zip"), schedule_slot=schedule_slot)
        raise ValueError(f"Successful managed ORM producer has no required artifact: {url}")
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan', type=Path)
    parser.add_argument('--record-managed', type=Path)
    parser.add_argument('--head')
    parser.add_argument('--discover-managed', action='store_true')
    parser.add_argument('--wait-managed-seconds', type=int, default=0)
    parser.add_argument('--module')
    parser.add_argument('--receipts', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.record_managed:
        args.output.write_text(json.dumps(managed_report(args.head, args.record_managed.read_text()), indent=2) + '\n')
        return
    plan = json.loads(args.plan.read_text())
    rows = plan.get('changed_test_coverage', [])
    if args.module:
        print(','.join(row['selector'] for row in rows
                       if row['module'] == args.module and row['owner'] == 'backend_suite' and row['kind'] == 'orm'))
        return
    if args.receipts is None or args.output is None:
        parser.error('receipt reconciliation requires --receipts and --output')
    rows = verify_logs(rows, [(p.parent / 'execution.log').read_text() for p in args.receipts.rglob('receipt.json')])
    managed = None
    if args.discover_managed and any(r['owner'] == MANAGED_TARGET for r in rows):
        if not 0 <= args.wait_managed_seconds <= 7200:
            parser.error('managed evidence wait must be between 0 and 7200 seconds')
        schedule_slot = None
        wait_seconds = args.wait_managed_seconds
        if os.environ.get('GITHUB_EVENT_NAME') == 'schedule':
            run_id = os.environ['GITHUB_RUN_ID']
            if not run_id.isdigit():
                raise ValueError('invalid current scheduled run id')
            current = json.loads(receipts.github_bytes(f'actions/runs/{run_id}'))
            if current.get('head_sha') != plan['head'] or current.get('event') != 'schedule':
                raise ValueError('current scheduled run identity mismatch')
            schedule_slot = scheduled_slot(current['created_at'])
            # Bound the complete producer window, rather than adding two hours
            # after a four-hour shard. Aggregators allow 340 minutes in total.
            created = datetime.fromisoformat(current['created_at'].replace('Z', '+00:00')).timestamp()
            wait_seconds = max(0, min(wait_seconds, created + 300 * 60 - time.time()))
        deadline = time.monotonic() + wait_seconds
        while True:
            managed = discover_managed_evidence(plan['head'], schedule_slot=schedule_slot)
            if managed or time.monotonic() >= deadline:
                break
            print('Managed ORM evidence pending for exact candidate; waiting for the selected acceptance lane', flush=True)
            time.sleep(min(20, max(0, deadline - time.monotonic())))
        if managed:
            rows = [dict(r, status='executed_managed') if r['owner'] == MANAGED_TARGET and r['selector'] in managed['executed'] else r for r in rows]
    report = {'managed_evidence': managed, 'head': plan['head'], 'base': plan['base'], 'tests': rows,
              'pending': [row for row in rows if row['status'] == 'pending']}
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    if report['pending']:
        raise SystemExit('Changed tests lack execution evidence; see coverage report and owner entrypoints')


if __name__ == '__main__':
    main()
