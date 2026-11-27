"""Read-only operator qualification: authenticate existing workflow evidence.

No status-only success and no caller-supplied artifact URLs. The current
attempt, its jobs, safe archive bytes and exact-source plans must agree.
"""
from __future__ import annotations

import hashlib
import json
import tempfile
import zipfile
import sys
import subprocess
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from scripts.ci import backend_suite_plan as plans
    from scripts.ci import backend_test_receipt as receipts
    from scripts.ci.release_condition import build_condition
    from scripts.ci.select_authoritative_workflow_run import select_latest_run
except ModuleNotFoundError:
    import backend_suite_plan as plans
    import backend_test_receipt as receipts
    from release_condition import build_condition
    from select_authoritative_workflow_run import select_latest_run

REPOSITORY = receipts.REPOSITORY
REQUIRED_JOBS = {
    'public_guard.yml': {'public_guard_classify', 'public_guard'},
    'professional_quality_gate.yml': {'professional_authorization', 'python310_runtime_compatibility',
                                     'professional_quality_checks', 'professional_quality_gate'},
    'frontend_release_gate.yml': {'frontend_release_gate'},
    'merge_policy_gate.yml': {'classify', 'wait_for_fact_checks', 'merge_policy_gate'},
    'auxiliary_backend_suite.yml': set(),
    'release_candidate_gate.yml': {'classify', 'wait_for_candidate_checks', 'release_candidate_gate'},
}


def timestamp(value):
    result = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('evidence timestamp has no timezone')
    return result


class EvidenceReader:
    def __init__(self, fetch=None):
        self.fetch = fetch or receipts.github_bytes
        self.evidence = []

    def json(self, endpoint):
        return json.loads(self.fetch(endpoint))

    def pages(self, endpoint, field):
        rows = []
        for page in range(1, 101):
            value = self.json(endpoint + ('&' if '?' in endpoint else '?') + f'per_page=100&page={page}')
            part = value.get(field)
            if not isinstance(part, list):
                raise ValueError('invalid paginated evidence: ' + field)
            rows.extend(part)
            if len(rows) == value.get('total_count'):
                return rows
            if len(part) < 100:
                raise ValueError('incomplete paginated evidence: ' + field)
        raise ValueError('evidence pagination exceeded limit')

    def run(self, expected):
        run_id, attempt = expected['run_id'], expected['attempt']
        actual = self.json(f'actions/runs/{run_id}')
        for key, value in {'id': run_id, 'run_attempt': attempt, 'head_sha': expected['head_sha'],
                           'head_branch': 'main', 'event': 'workflow_dispatch',
                           'path': '.github/workflows/' + expected['workflow'],
                           'status': 'completed', 'conclusion': 'success'}.items():
            if actual.get(key) != value:
                raise ValueError(f'workflow evidence identity/outcome mismatch: {key}')
        for key in ('repository', 'head_repository'):
            if actual.get(key, {}).get('full_name') != REPOSITORY:
                raise ValueError('workflow evidence repository mismatch')
        candidates = self.pages(f"actions/workflows/{expected['workflow']}/runs?head_sha={expected['head_sha']}", 'workflow_runs')
        latest = select_latest_run({'workflow_runs': candidates}, repository=REPOSITORY,
            workflow_path=actual['path'], head_sha=actual['head_sha'], event='workflow_dispatch',
            head_branch='main', head_repository=REPOSITORY)
        if latest is None or latest.get('id') != run_id or latest.get('run_attempt') != attempt:
            raise ValueError('manifest is not the latest authoritative workflow attempt')
        return actual

    def jobs(self, run):
        jobs = self.pages(f"actions/runs/{run['id']}/attempts/{run['run_attempt']}/jobs", 'jobs')
        names = [job.get('name') for job in jobs]
        if not jobs or len(names) != len(set(names)):
            raise ValueError('missing or ambiguous attempt jobs')
        for job in jobs:
            if (job.get('run_id') != run['id'] or job.get('run_attempt') != run['run_attempt']
                    or job.get('head_sha') != run['head_sha'] or job.get('status') != 'completed'
                    or job.get('conclusion') not in ('success', 'skipped')):
                raise ValueError('invalid attempt job identity/outcome')
        return {job['name']: job for job in jobs}

    @staticmethod
    def require_jobs(jobs, names):
        for name in names:
            if jobs.get(name, {}).get('conclusion') != 'success':
                raise ValueError('required job missing or not successful: ' + name)

    def artifact(self, run, artifacts, name, job):
        found = [a for a in artifacts if a.get('name') == name]
        if len(found) != 1:
            raise ValueError('missing or ambiguous artifact: ' + name)
        artifact = found[0]
        bound = artifact.get('workflow_run', {})
        if (artifact.get('expired') is not False or bound.get('id') != run['id']
                or bound.get('head_sha') != run['head_sha']
                or not timestamp(job['started_at']) <= timestamp(artifact['created_at']) <= timestamp(job['completed_at'])):
            raise ValueError('artifact not attributable to exact attempt job: ' + name)
        raw = self.fetch(f"actions/artifacts/{artifact['id']}/zip")
        digest = hashlib.sha256(raw).hexdigest()
        if artifact.get('digest') != 'sha256:' + digest:
            raise ValueError('artifact digest missing or mismatched: ' + name)
        try:
            members = receipts.archive_members(raw)
        except zipfile.BadZipFile as exc:
            raise ValueError('invalid evidence archive: ' + name) from exc
        self.evidence.append({'artifact_id': artifact['id'], 'name': name, 'sha256': digest,
                              'run_id': run['id'], 'attempt': run['run_attempt'], 'job_id': job['id']})
        return members


def one_json(members, name):
    matches = [value for path, value in members.items() if Path(path).name == name]
    if len(matches) != 1:
        raise ValueError('missing or ambiguous archive document: ' + name)
    return json.loads(matches[0])


def required_runner_kinds(head, modules):
    """Mirror the full-suite dispatch classifier against the exact source tree."""
    paths = [root + '/' + module + '/tests'
             for root in plans.impact.ROOTS for module in modules]
    result = subprocess.run(
        ['git', 'grep', '-l', '-E', r'(^|[[:space:]])(from|import)[[:space:]]+odoo\.tests',
         head, '--', *paths], cwd=plans.impact.ROOT, text=True, capture_output=True)
    if result.returncode not in (0, 1):
        raise ValueError('cannot determine exact-source backend runner responsibility')
    files = [line.removeprefix(head + ':') for line in result.stdout.splitlines()]
    return {module: ('orm' if any(path.startswith(root + '/' + module + '/tests/')
                                  for root in plans.impact.ROOTS for path in files) else 'python')
            for module in modules}


def verify_suite(reader, run, jobs, artifacts, suite, prefix, head, tree):
    reader.require_jobs(jobs, {prefix + ' / plan', prefix + ' / verify_coverage'})
    plan_files = reader.artifact(run, artifacts, f"backend-plan-{run['id']}-{suite}", jobs[prefix + ' / plan'])
    plan = one_json(plan_files, 'backend-plan.json')
    authority = plans.impact.git('show', head + ':' + plans.MODULE_SETS_PATH)
    if (plans.impact.ROOT / plans.MODULE_SETS_PATH).read_text() != authority:
        raise ValueError('local module-set authority differs from qualified source')
    required = plans.build_plan('', head, suite=suite)
    plans.validate_execution_plan(plan, required)
    if plan.get('mode') != 'full' or plan.get('scope_mode') != 'full':
        raise ValueError('main qualification requires full backend scope')
    expected_jobs = {f"{prefix} / backend_suite ({s['index']})" for s in plan['shards']}
    reader.require_jobs(jobs, expected_jobs)
    actual_jobs = {name for name in jobs if name.startswith(prefix + ' / backend_suite (')}
    if actual_jobs != expected_jobs:
        raise ValueError('backend shard jobs differ from frozen plan')
    kinds = required_runner_kinds(head, plan['modules'])
    observed = []
    log_sources = []
    with tempfile.TemporaryDirectory(prefix='main-qualification-') as tmp:
        root = Path(tmp)
        for shard in plan['shards']:
            index = shard['index']
            members = reader.artifact(run, artifacts, f"backend-execution-{run['id']}-{suite}-{index}",
                                      jobs[f'{prefix} / backend_suite ({index})'])
            directory = root / str(index)
            for name, data in members.items():
                path = directory / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            found = []
            for path in directory.rglob('receipt.json'):
                receipt = json.loads(path.read_bytes())
                scope_path = plans.locate_scope_plan(path)
                plans.validate_execution_plan(json.loads(scope_path.read_bytes()), required)
                receipts.verify(path.parent, expected_head=head,
                    expected_digest=hashlib.sha256(path.read_bytes()).hexdigest(), scope_plan=scope_path)
                if receipt.get('source_tree') != tree or receipt.get('module') not in shard['modules']:
                    raise ValueError('receipt tree or shard membership mismatch')
                provenance = receipt.get('provenance', {})
                if any(str(provenance.get(key)) != str(value) for key, value in {
                        'GITHUB_REPOSITORY': REPOSITORY, 'GITHUB_RUN_ID': run['id'],
                        'GITHUB_RUN_ATTEMPT': run['run_attempt']}.items()):
                    raise ValueError('receipt attempt provenance mismatch')
                count, _ = receipts.parse_result(receipt['kind'], receipt['module'], receipt.get('database', ''),
                                                 receipt['exit_code'], path.parent / 'execution.log')
                if count != receipt['test_count']:
                    raise ValueError('receipt count differs from actual runner log')
                log_sources.append({'module': receipt['module'], 'kind': receipt['kind'],
                    'execution': receipt.get('execution', ''), 'text': (path.parent / 'execution.log').read_text()})
                found.append(receipt)
            if {r['module'] for r in found} != set(shard['modules']):
                raise ValueError('shard execution evidence incomplete')
            observed.extend(found)
    plans.verify_execution_coverage(plan, observed)
    for module in {name for shard in plan['shards'] for name in shard['modules']}:
        if not any(row['module'] == module and row['kind'] == kinds[module]
                   and not row.get('execution') for row in observed):
            raise ValueError('required full-suite runner missing for ' + module)
    coverage = one_json(reader.artifact(run, artifacts, f"changed-test-coverage-{run['id']}-{suite}",
        jobs[prefix + ' / verify_coverage']), 'changed-test-coverage.json')
    if coverage.get('head') != head or coverage.get('base') != '' or coverage.get('pending') or not isinstance(coverage.get('tests'), list):
        raise ValueError('changed-test coverage identity or result mismatch')
    actual_coverage = plans.changed_coverage.verify_logs(plan.get('changed_test_coverage', []),
        log_sources, accept_direct_managed_executions=suite == 'acceptance')
    if any(row['status'] != 'executed' for row in actual_coverage):
        raise ValueError('required test identities absent from authenticated runner logs')
    if coverage['tests'] != actual_coverage:
        raise ValueError('coverage report differs from authenticated test identities')
    return {'suite': suite, 'modules': plan['modules'], 'shards': len(plan['shards']),
            'executions': [{'module': r['module'], 'kind': r['kind'], 'tests': r['test_count']} for r in observed]}


def verify_evidence(document, *, fetch=None):
    reader = EvidenceReader(fetch)
    head, tree = document['expected_main'], document['expected_tree']
    runs, jobs, artifacts = {}, {}, {}
    for expected in document['workflows']:
        name = expected['workflow']
        runs[name] = run = reader.run(expected)
        jobs[name] = reader.jobs(run)
        reader.require_jobs(jobs[name], REQUIRED_JOBS[name])
        artifacts[name] = reader.pages(f"actions/runs/{run['id']}/artifacts", 'artifacts')
    front = runs['frontend_release_gate.yml']
    members = reader.artifact(front, artifacts['frontend_release_gate.yml'],
        f"frontend-release-evidence-{front['id']}-{front['run_attempt']}-{head}",
        jobs['frontend_release_gate.yml']['frontend_release_gate'])
    gate = one_json(members, 'gate-result.json')
    if any(gate.get(key) != value for key, value in {
            'schema_version': 'frontend-release-gate-result/v1', 'result': 'PASS',
            'git_sha': head, 'git_tree': tree, 'event': 'workflow_dispatch',
            'run_id': str(front['id']), 'run_attempt': str(front['run_attempt'])}.items()):
        raise ValueError('frontend release gate evidence mismatch')
    reports = [json.loads(data) for path, data in members.items()
               if path.endswith('frontend-release-audit/report.json')]
    if len(reports) != 1:
        raise ValueError('frontend complete release report missing')
    report = reports[0]
    workflow = report.get('workflow', {})
    if any(str(workflow.get(key)) != str(value) for key, value in {
            'run_id': front['id'], 'run_attempt': front['run_attempt'],
            'event': 'workflow_dispatch', 'checkout_sha': head}.items()):
        raise ValueError('frontend report workflow identity mismatch')
    sections = {'accessibility', 'delivery_hardening', 'error_recovery', 'navigation',
                'performance', 'responsive', 'role_release_projection', 'static'}
    if (report.get('git_sha') != head or report.get('git_tree') != tree
            or report.get('result') != 'PASS' or report.get('summary_exit_code') != 0
            or report.get('blocking_failures') or report.get('missing_evidence')
            or set(report.get('required_sections', [])) != sections
            or set(report.get('evidence', {})) != sections):
        raise ValueError('frontend full release sections incomplete')
    for item in report['evidence'].values():
        path = str(item.get('path', '')).removeprefix('artifacts/')
        raw = members.get(path)
        if raw is None or item.get('git_sha') != head or hashlib.sha256(raw).hexdigest() != item.get('sha256'):
            raise ValueError('frontend section evidence missing or changed')
    run = runs['release_candidate_gate.yml']
    condition = one_json(reader.artifact(run, artifacts['release_candidate_gate.yml'],
        f"release-condition-{run['id']}-{run['run_attempt']}-{head}",
        jobs['release_candidate_gate.yml']['wait_for_candidate_checks']), 'release-condition.json')
    expected = build_condition([r for name, r in runs.items() if name != 'release_candidate_gate.yml'],
        repository=REPOSITORY, head_sha=head, tree=tree, event='workflow_dispatch', head_branch='main',
        workflow_dispatch_producer='workflow_dispatch', schedule_slot=None, current_main=head)
    if condition != expected:
        raise ValueError('release condition does not match manifest identities and qualification facts')
    suites = []
    for workflow, suite, prefix in [('professional_quality_gate.yml', 'product', 'backend_impact_suite'),
                                    ('auxiliary_backend_suite.yml', 'demo', 'demo'),
                                    ('auxiliary_backend_suite.yml', 'acceptance', 'acceptance')]:
        suites.append(verify_suite(reader, runs[workflow], jobs[workflow], artifacts[workflow], suite, prefix, head, tree))
    # Reject reruns started while downloading evidence; do not mix attempts.
    for expected_run in document['workflows']:
        reader.run(expected_run)
    return {'status': 'VERIFIED', 'artifacts': reader.evidence, 'backend_suites': suites,
            'release_condition': condition}
