#!/usr/bin/env python3
"""Collect execution evidence; integrity verification never authorizes reuse.

The GitHub artifact/source verifier and authoritative dynamic-contract readback
are still required before a future evidence_scope adapter may consume a result.
No cache lookup or test skipping is implemented here.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.metadata
import importlib.util
import json
import io
import math
import os
from pathlib import Path, PurePosixPath
import platform
import re
import subprocess
import sys
import stat
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = 'backend-test-execution/v1'
ENV_MARKER = 'SC_BACKEND_TEST_ENVIRONMENT='
MAX_AGE = timedelta(hours=24)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def command(*args, cwd=ROOT) -> str:
    return subprocess.check_output(list(args), cwd=cwd, text=True).strip()


def python_environment() -> dict:
    # Do not capture environment variables, pip credentials or index URLs.
    packages = []
    for dist in importlib.metadata.distributions():
        record = dist.read_text('RECORD')
        packages.append({'name': dist.metadata.get('Name', ''), 'version': dist.version,
                         'installed_record_sha256': digest(record.encode()) if record else None})
    return {'python': platform.python_version(), 'implementation': platform.python_implementation(),
            'executable_sha256': digest(Path(sys.executable).read_bytes()),
            'platform': platform.system(), 'architecture': platform.machine(),
            'os_release_sha256': digest(Path('/etc/os-release').read_bytes()) if Path('/etc/os-release').exists() else None,
            'packages': sorted(packages, key=lambda x: (x['name'], x['version']))}


def context() -> dict:
    services = {}
    for service in ('db', 'redis'):
        container = command('docker', 'compose', 'ps', '-q', service)
        if not container or '\n' in container:
            raise ValueError('expected one running ' + service)
        image_id = command('docker', 'inspect', '--format', '{{.Image}}', container)
        if not re.fullmatch(r'sha256:[0-9a-f]{64}', image_id):
            raise ValueError('missing content-bound image identity')
        services[service] = {
            'image_id': image_id,
            'repo_digests': json.loads(command('docker', 'image', 'inspect', '--format', '{{json .RepoDigests}}', image_id)),
        }
    # Compose config can contain credentials: consume it in memory and retain
    # only the selected image name, never the expanded configuration.
    image_name = json.loads(command('docker', 'compose', 'config', '--format', 'json'))['services']['odoo']['image']
    image_id = command('docker', 'image', 'inspect', '--format', '{{.Id}}', image_name)
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', image_id):
        raise ValueError('Odoo image identity missing')
    return {'services': services, 'odoo_image_id': image_id, 'docker': command('docker', '--version'),
            'compose': command('docker', 'compose', 'version'),
            'runner_os': os.environ.get('RUNNER_OS'), 'runner_arch': os.environ.get('RUNNER_ARCH')}


def parse_result(kind: str, module: str, database: str, status: int, log: Path) -> tuple[int, dict]:
    text = log.read_text(encoding='utf-8')
    if status != 0:
        raise ValueError('execution failed: ' + str(status))
    if kind == 'orm':
        result = command('bash', '-c',
                         'source "$1"; orm_expect_identity="$2"; orm_expect_database="$3"; evaluate_orm_outcome "$4" "$5"',
                         'receipt', str(ROOT / 'scripts/ci/orm_result_guard.sh'),
                         f'odoo.addons.{module}.tests.', database, str(status), str(log))
        count = int(re.search(r'ORM_RESULT_GUARD=PASS tests=(\d+)', result).group(1))
        environments = [json.loads(line[len(ENV_MARKER):]) for line in text.splitlines() if line.startswith(ENV_MARKER)]
        if len(environments) != 1:
            raise ValueError('exactly one actual container environment observation required')
        environment = environments[0]
    else:
        counts = re.findall(r'^Ran ([1-9][0-9]*) tests? in [0-9.]+s$', text, re.M)
        if len(counts) != 1 or not re.search(r'^OK(?: \([^\n]*\))?$', text, re.M):
            raise ValueError('missing unambiguous nonzero unittest result')
        count = int(counts[0])
        skipped = re.findall(r'^OK \(.*?skipped=(\d+).*?\)$', text, re.M)
        if skipped and int(skipped[0]) >= count:
            raise ValueError('all tests skipped')
        environment = python_environment()
    if not count or not isinstance(environment, dict) or not environment.get('python') or not environment.get('packages'):
        raise ValueError('incomplete Python environment or zero tests')
    return count, environment


def redacted_log(log: Path, secrets_file: Path | None = None) -> str:
    text = log.read_text(encoding='utf-8')
    secret_keys = {'DB_PASSWORD', 'ADMIN_PASSWD', 'JWT_SECRET', 'SC_BOOTSTRAP_SECRET', 'SC_DEMO_USER_PASSWORD'}
    secrets = [os.environ.get(key) for key in secret_keys]
    # CI writes plain KEY=value entries to its managed temporary env file.
    # Read only allowlisted secrets; never execute or archive that file.
    if secrets_file is not None:
        for line in secrets_file.read_text().splitlines():
            key, sep, value = line.partition('=')
            if sep and key in secret_keys:
                secrets.append(value.strip().strip("\"'"))
    for secret in sorted((s for s in secrets if s), key=len, reverse=True):
        text = text.replace(secret, '[REDACTED]')
    return text


def scope_reference(raw: bytes, *, head: str, base: str, module: str) -> dict:
    plan = json.loads(raw)
    inventory = plan.get('input_inventory') or {}
    target = (inventory.get('targets') or {}).get(module) or {}
    membership = [name for shard in plan.get('shards',[]) for name in shard.get('modules',[])]
    if (plan.get('head') != head or plan.get('base') != base
            or module not in plan.get('modules',[]) or membership.count(module) != 1
            or inventory.get('schema') != 'backend-known-input-inventory/v1'
            or target.get('target') != module
            or not re.fullmatch('[0-9a-f]{64}',str(target.get('known_inputs_sha256','')))):
        raise ValueError('scope plan identity or target mismatch')
    if not base and plan.get('mode') not in ('full','explicit_override'):
        raise ValueError('missing integration base without explicit full scope')
    return {'sha256':digest(raw),'target':module,'known_inputs_sha256':target['known_inputs_sha256'],
            'integration_base':base,'selection_mode':plan['mode'],'dependency_closure_complete':False}


def archive_attempt(*, output: Path, module: str, attempt: int, head: str,
                    status: int, log_status: int, log: Path, database: str = '',
                    secrets_file: Path | None = None) -> dict:
    if (not re.fullmatch('[A-Za-z_][A-Za-z0-9_]*',module)
            or not re.fullmatch('[0-9a-f]{40}',head) or type(attempt) is not int or attempt <= 0
            or any(type(v) is not int or not 0 <= v <= 255 for v in (status,log_status))):
        raise ValueError('invalid attempt identity or exit status')
    text = redacted_log(log,secrets_file)
    target = output/'attempts'/module/str(attempt)
    target.mkdir(parents=True,exist_ok=False)
    (target/'execution.log').write_text(text,encoding='utf-8')
    result = {'schema':'backend-test-attempt/v1','module':module,'attempt':attempt,
              'source_head':head,'database':database,'process_exit_code':status,'log_exit_code':log_status,
              'log_sha256':digest((target/'execution.log').read_bytes()),
              'interpretation':'diagnostic_only_not_test_success','reuse_ready':False}
    (target/'attempt.json').write_bytes(canonical(result))
    return result


def record(root: Path, *, module: str, kind: str, head: str, base: str,
           database: str, status: int, log: Path, context_file: Path, output: Path,
           now: datetime | None = None, selection: str = '', duration_seconds: float | None = None, secrets_file: Path | None = None, scope_plan: Path | None = None) -> dict:
    if kind not in ('orm', 'python'):
        raise ValueError('unknown executor kind')
    if kind == 'orm' and (not selection or not database):
        raise ValueError('actual ORM selection and database required')
    if duration_seconds is not None and (not math.isfinite(duration_seconds) or duration_seconds < 0):
        raise ValueError('invalid measured duration')
    if not re.fullmatch(r'[a-zA-Z_][a-zA-Z0-9_]*', module):
        raise ValueError('invalid module')
    if not re.fullmatch(r'[0-9a-f]{40}',head) or (base and not re.fullmatch(r'[0-9a-f]{40}',base)):
        raise ValueError('exact source/base commits required')
    if command('git', 'rev-parse', 'HEAD', cwd=root) != head:
        raise ValueError('checkout identity mismatch')
    if command('git', 'status', '--porcelain', '--untracked-files=all', cwd=root):
        raise ValueError('source worktree is not clean')
    if base:
        command('git', 'cat-file', '-e', base + '^{commit}', cwd=root)
    elif scope_plan is None:
        raise ValueError('missing integration base without full scope plan')
    scope = scope_reference(scope_plan.read_bytes(),head=head,base=base,module=module) if scope_plan else None
    tree = command('git', 'rev-parse', head + '^{tree}', cwd=root)
    candidates = [prefix for prefix in ('addons/' + module, 'demo_addons/' + module)
                  if command('git', 'ls-tree', '-r', '--name-only', head, '--', prefix + '/__manifest__.py', cwd=root)]
    if len(candidates) != 1:
        raise ValueError('module identity missing or ambiguous')
    files = command('git', 'ls-tree', '-r', head, '--', candidates[0] + '/tests', cwd=root).splitlines()
    if not files:
        raise ValueError('test scope absent')
    count, python = parse_result(kind, module, database, status, log)
    skipped_matches = re.findall(r'^OK \(.*?skipped=(\d+).*?\)$', log.read_text(), re.M) if kind == 'python' else []
    skipped_count = int(skipped_matches[0]) if skipped_matches else 0
    runtime = json.loads(context_file.read_text())
    if set(runtime.get('services', {})) != {'db', 'redis'}:
        raise ValueError('runtime service identity missing')
    image_ids = [runtime.get('odoo_image_id')] + [runtime['services'][s].get('image_id') for s in ('db', 'redis')]
    if any(not re.fullmatch(r'sha256:[0-9a-f]{64}', str(value)) for value in image_ids):
        raise ValueError('content-bound runtime image identity missing')
    now = now or datetime.now(timezone.utc)
    output.mkdir(parents=True, exist_ok=True)
    target = output / module
    if target.exists():
        raise ValueError('refuse to overwrite existing target evidence')
    target.mkdir()
    text = log.read_text(encoding='utf-8')
    text = redacted_log(log, secrets_file)
    (target / 'execution.log').write_text(text, encoding='utf-8')
    (target / 'runtime.json').write_bytes(canonical(runtime))
    (target / 'python.json').write_bytes(canonical(python))
    receipt = {
        'schema': SCHEMA, 'module': module, 'kind': kind, 'source_head': head,
        'source_tree': tree, 'integration_base': base, 'database': database, 'scope_plan':scope,
        'target': f'make test MODULE={module}' if kind == 'orm' else f'unittest discover {candidates[0]}/tests',
        'selection': selection if kind == 'orm' else 'test*.py',
        'actual_duration_seconds': duration_seconds,
        'test_source_blobs': files, 'exit_code': status, 'test_count': count,
        'python_counts': {'collected': count, 'skipped': skipped_count, 'executed': count - skipped_count} if kind == 'python' else None,
        # Whole-tree binding is conservative; do not pretend the incomplete
        # static read map is already a certified target dependency closure.
        'input_binding': {'policy': 'whole-tracked-tree/v1', 'tree': tree},
        'issued_at': now.isoformat(), 'expires_at': (now + MAX_AGE).isoformat(),
        'provenance': {key: os.environ.get(key) for key in
                       ('GITHUB_REPOSITORY', 'GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT', 'GITHUB_JOB')},
        'files': {name: digest((target / name).read_bytes()) for name in ('execution.log', 'runtime.json', 'python.json')},
        'reuse_ready': False,
        'blockers': ['platform_source_not_authenticated', 'runtime_contract_readback_missing', 'fact_scope_readback_missing',
                     'target_dependency_closure_not_certified'],
    }
    (target / 'receipt.json').write_bytes(canonical(receipt))
    return {**receipt, 'receipt_sha256': digest(canonical(receipt))}


def verify(directory: Path, *, expected_head: str, expected_digest: str,
           now: datetime | None = None, scope_plan: Path | None = None) -> dict:
    for name in ('receipt.json', 'execution.log', 'runtime.json', 'python.json'):
        path = directory / name
        if path.is_symlink() or not path.is_file():
            raise ValueError('missing or linked evidence file: ' + name)
    raw = (directory / 'receipt.json').read_bytes()
    if not re.fullmatch(r'[0-9a-f]{64}', expected_digest) or digest(raw) != expected_digest:
        raise ValueError('receipt bytes changed')
    receipt = json.loads(raw)
    if receipt.get('schema') != SCHEMA or receipt.get('source_head') != expected_head:
        raise ValueError('receipt source/schema mismatch')
    if receipt.get('exit_code') != 0 or type(receipt.get('test_count')) is not int or receipt['test_count'] <= 0:
        raise ValueError('invalid execution result')
    issued, expires = (datetime.fromisoformat(receipt[k]) for k in ('issued_at', 'expires_at'))
    now = now or datetime.now(timezone.utc)
    if issued.tzinfo is None or expires.tzinfo is None or not issued <= now < expires or expires - issued != MAX_AGE:
        raise ValueError('expired or invalid evidence lifetime')
    expected_files = {'execution.log', 'runtime.json', 'python.json'}
    if set(receipt.get('files', {})) != expected_files:
        raise ValueError('evidence file scope mismatch')
    for name, sha in receipt['files'].items():
        if digest((directory / name).read_bytes()) != sha:
            raise ValueError('evidence bytes changed: ' + name)
    if receipt.get('scope_plan') is not None:
        if scope_plan is None or scope_reference(scope_plan.read_bytes(),head=expected_head,
                base=receipt['integration_base'],module=receipt['module']) != receipt['scope_plan']:
            raise ValueError('scope plan missing or changed')
    # Integrity is not provenance authentication. Never promote this local
    # check to a successful reusable test verdict, even if JSON requests it.
    if receipt.get('reuse_ready') is not False:
        raise ValueError('observation cannot self-authorize reuse')
    return {'integrity': 'verified', 'source_head': expected_head, 'module': receipt['module'],
            'reuse_ready': False, 'blockers': ['platform_source_not_authenticated',
                'runtime_contract_readback_missing', 'fact_scope_readback_missing', 'target_dependency_closure_not_certified']}


def contract_source_binding(contract: dict, source_payload: dict) -> dict:
    """Check the existing lifecycle binding, not a parallel contract format.

    Both inputs must ultimately come from the same governed runtime delivery.
    This offline consistency check cannot authenticate a caller-supplied source
    or prove that its database query/read scope was complete.
    """
    path = ROOT / 'addons/smart_core/core/contract_lifecycle.py'
    spec = importlib.util.spec_from_file_location('backend_receipt_lifecycle', path)
    lifecycle = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lifecycle)
    if not isinstance(contract, dict) or not isinstance(source_payload, dict) or not source_payload:
        raise ValueError('contract and actual source payload required')
    ok, reason = lifecycle.verify_unified_page_contract_integrity(contract)
    if not ok:
        raise ValueError('contract integrity mismatch: ' + str(reason))
    evidence = contract.get('meta', {}).get('lifecycle', {})
    source_digest = lifecycle.payload_sha256(lifecycle.strip_request_transport_identity(source_payload))
    if evidence.get('generation', {}).get('sourceSha256') != source_digest:
        raise ValueError('contract/source facts binding mismatch')
    return {'consistency': 'verified', 'source_sha256': source_digest,
            'contract_sha256': evidence['integrity']['contractSha256'],
            'lifecycle_tool_sha256': digest(path.read_bytes()),
            'reuse_ready': False,
            'blockers': ['runtime_contract_readback_missing', 'fact_scope_readback_missing',
                         'target_dependency_closure_not_certified']}


REPOSITORY = 'lidefend/sce-backend-odoo'
REPOSITORY_ID = 1307419149
ARCHIVE_LIMIT = 64 * 1024 * 1024


def github_bytes(endpoint: str) -> bytes:
    # Fixed host, read-only GET, managed credential configuration. No URL from
    # an artifact or receipt is ever followed by this code.
    env = dict(os.environ, GH_CONFIG_DIR='/home/lidefend/.config/gh-new-account')
    with tempfile.TemporaryFile() as out:
        subprocess.run(['gh', 'api', '--hostname', 'github.com', '--method', 'GET',
                        'repos/' + REPOSITORY + '/' + endpoint], stdout=out,
                       check=True, timeout=45, env=env)
        if out.tell() > ARCHIVE_LIMIT:
            raise ValueError('platform response too large')
        out.seek(0)
        return out.read()


def archive_members(data: bytes) -> dict[str, bytes]:
    if len(data) > ARCHIVE_LIMIT:
        raise ValueError('archive too large')
    files = {}; total = 0; seen = set()
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        if len(archive.infolist()) > 1000:
            raise ValueError('archive member count')
        for item in archive.infolist():
            path = PurePosixPath(item.filename)
            name = item.filename.rstrip('/')
            mode = item.external_attr >> 16
            if (not name or path.is_absolute() or '..' in path.parts or '\\' in name
                    or str(PurePosixPath(name)) != name or name in seen
                    or stat.S_ISLNK(mode) or (stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR))):
                raise ValueError('unsafe archive member')
            seen.add(name)
            total += item.file_size
            if total > ARCHIVE_LIMIT:
                raise ValueError('archive expansion too large')
            if not item.is_dir():
                files[name] = archive.read(item)
    return files


def verify_github_origin(*, run_id: int, attempt: int, artifact_id: int,
                         shard: int, expected_head: str, module: str,
                         now: datetime | None = None) -> dict:
    # This authenticates platform origin, not the correctness of candidate-
    # supplied test code. Trusted execution-definition approval remains separate.
    if (any(type(v) is not int or v <= 0 for v in (run_id, attempt, artifact_id))
            or type(shard) is not int or shard < 0
            or not re.fullmatch('[0-9a-f]{40}', expected_head)
            or not re.fullmatch('[a-zA-Z_][a-zA-Z0-9_]*', module)):
        raise ValueError('invalid exact platform identity')
    run_path = f'actions/runs/{run_id}/attempts/{attempt}'
    run = json.loads(github_bytes(run_path))
    expected_repository = {'id': REPOSITORY_ID, 'full_name': REPOSITORY}
    for field in ('repository', 'head_repository'):
        if any(run.get(field, {}).get(k) != v for k, v in expected_repository.items()):
            raise ValueError('foreign repository')
    if (run.get('id') != run_id or run.get('run_attempt') != attempt
            or run.get('head_sha') != expected_head or run.get('status') != 'completed'
            or run.get('conclusion') != 'success'
            or run.get('event') not in ('pull_request', 'workflow_dispatch', 'schedule')
            or run.get('path') not in ('.github/workflows/professional_quality_gate.yml',
                                      '.github/workflows/backend_test_suite.yml')):
        raise ValueError('run identity or successful execution mismatch')
    artifact = json.loads(github_bytes(f'actions/artifacts/{artifact_id}'))
    origin = artifact.get('workflow_run') or {}
    # Artifact names/receipt attempt fields are producer assertions. The API
    # binds only run ID/head; never promote the name to attempt authentication.
    expected_name = f'backend-execution-{run_id}-{attempt}-{shard}'
    if (artifact.get('id') != artifact_id or artifact.get('name') != expected_name
            or artifact.get('expired') is not False or origin.get('id') != run_id
            or origin.get('head_sha') != expected_head
            or origin.get('repository_id') != REPOSITORY_ID
            or origin.get('head_repository_id') != REPOSITORY_ID):
        raise ValueError('artifact origin mismatch or expired')
    archive_digest = artifact.get('digest', '')
    if not re.fullmatch('sha256:[0-9a-f]{64}', archive_digest):
        raise ValueError('platform archive digest missing')
    raw = github_bytes(f'actions/artifacts/{artifact_id}/zip')
    if 'sha256:' + digest(raw) != archive_digest:
        raise ValueError('platform archive digest mismatch')
    files = archive_members(raw)
    names = ('receipt.json', 'execution.log', 'runtime.json', 'python.json')
    if any(module + '/' + name not in files for name in names):
        raise ValueError('target execution evidence missing')
    receipt = json.loads(files[module + '/receipt.json'])
    provenance = receipt.get('provenance') or {}
    if (receipt.get('module') != module
            or provenance.get('GITHUB_REPOSITORY') != REPOSITORY
            or provenance.get('GITHUB_RUN_ID') != str(run_id)
            or provenance.get('GITHUB_RUN_ATTEMPT') != str(attempt)
            or provenance.get('GITHUB_JOB') != 'backend_suite'):
        raise ValueError('receipt origin mismatch')
    commit = json.loads(github_bytes(f'git/commits/{expected_head}'))
    if commit.get('sha') != expected_head or receipt.get('source_tree') != (commit.get('tree') or {}).get('sha'):
        raise ValueError('source tree mismatch')
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        for name in names:
            (folder/name).write_bytes(files[module + '/' + name])
        scope_path = None
        if receipt.get('scope_plan') is not None:
            if 'scope-plan.json' not in files:
                raise ValueError('archived scope plan missing')
            scope_path = folder/'scope-plan.json'
            scope_path.write_bytes(files['scope-plan.json'])
        verified = verify(folder, expected_head=expected_head,
                          expected_digest=digest(files[module+'/receipt.json']), now=now,scope_plan=scope_path)
    return {**verified, 'platform_origin': 'verified', 'repository': REPOSITORY,
            'run_id': run_id, 'requested_attempt': attempt, 'artifact_id': artifact_id,
            'run_attempt_metadata': 'verified', 'artifact_attempt': 'not_attested',
            'archive_sha256': archive_digest.removeprefix('sha256:'),
            'receipt_sha256': digest(files[module+'/receipt.json']),
            'workflow_path': run['path'],
            'blockers': ['artifact_attempt_not_attested', 'execution_definition_not_attested', 'runtime_contract_readback_missing', 'fact_scope_readback_missing',
                         'target_dependency_closure_not_certified']}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('environment', 'context', 'record', 'verify', 'verify-origin', 'verify-contract-source', 'archive-attempt'))
    parser.add_argument('--output', type=Path)
    parser.add_argument('--head')
    parser.add_argument('--base', default='')
    parser.add_argument('--module')
    parser.add_argument('--kind', choices=('orm', 'python'))
    parser.add_argument('--database', default='')
    parser.add_argument('--selection', default='')
    parser.add_argument('--duration-seconds', type=float)
    parser.add_argument('--status', type=int)
    parser.add_argument('--log', type=Path)
    parser.add_argument('--context', type=Path)
    parser.add_argument('--receipt-sha256')
    parser.add_argument('--secrets-file', type=Path)
    parser.add_argument('--scope-plan', type=Path)
    parser.add_argument('--log-status', type=int, default=0)
    parser.add_argument('--contract', type=Path)
    parser.add_argument('--source-payload', type=Path)
    parser.add_argument('--run-id', type=int)
    parser.add_argument('--attempt', type=int)
    parser.add_argument('--artifact-id', type=int)
    parser.add_argument('--shard', type=int)
    args = parser.parse_args()
    if args.mode == 'environment':
        print(ENV_MARKER + canonical(python_environment()).decode())
    elif args.mode == 'context':
        args.output.write_bytes(canonical(context()))
    elif args.mode == 'record':
        result = record(ROOT, module=args.module, kind=args.kind, head=args.head, base=args.base,
                        database=args.database, status=args.status, log=args.log,
                        context_file=args.context, output=args.output, selection=args.selection,
                        duration_seconds=args.duration_seconds, secrets_file=args.secrets_file, scope_plan=args.scope_plan)
        print(json.dumps({'module': result['module'], 'test_count': result['test_count'],
                          'receipt_sha256': result['receipt_sha256'], 'reuse_ready': False}))
    elif args.mode == 'archive-attempt':
        print(json.dumps(archive_attempt(output=args.output,module=args.module,attempt=args.attempt,
             head=args.head,status=args.status,log_status=args.log_status,log=args.log,
             database=args.database,secrets_file=args.secrets_file)))
    elif args.mode == 'verify-contract-source':
        print(json.dumps(contract_source_binding(json.loads(args.contract.read_text()),
                                                json.loads(args.source_payload.read_text()))))
    elif args.mode == 'verify-origin':
        print(json.dumps(verify_github_origin(run_id=args.run_id, attempt=args.attempt,
            artifact_id=args.artifact_id, shard=args.shard, expected_head=args.head, module=args.module)))
    else:
        print(json.dumps(verify(args.output, expected_head=args.head, expected_digest=args.receipt_sha256,scope_plan=args.scope_plan)))


if __name__ == '__main__':
    main()
