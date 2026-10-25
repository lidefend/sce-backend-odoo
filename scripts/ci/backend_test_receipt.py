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
import tarfile
import time
import functools
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = 'backend-test-execution/v1'
ENV_MARKER = 'SC_BACKEND_TEST_ENVIRONMENT='
MAX_AGE = timedelta(hours=24)
ISOLATED_MODULE = 'smart_construction_scene'
ISOLATED_MARKER = 'SC_BACKEND_ISOLATED_PYTHON='



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
        markers = [json.loads(line[len(ENV_MARKER):]) for line in text.splitlines() if line.startswith(ENV_MARKER)]
        if len(markers) > 1:
            raise ValueError('ambiguous Python environment')
        environment = markers[0] if markers else python_environment()
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
            'integration_base':base,'selection_mode':plan['mode'],
            'dependency_closure_complete':bool(target.get('dependency_closure_complete'))}


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


def workflow_definition_observation(environment: dict | None = None) -> dict:
    """Capture the workflow identity separately from the checked-out code.

    On PR runs the workflow may come from the merge ref while tests explicitly
    check out the head. Never fill missing workflow facts with the test SHA.
    These environment values are producer assertions, not platform attestation.
    """
    environment = os.environ if environment is None else environment
    sha = environment.get('GITHUB_WORKFLOW_SHA')
    ref = environment.get('GITHUB_WORKFLOW_REF')
    if not sha and not ref:
        return {'status': 'not_captured', 'attested': False}
    pattern = re.escape(REPOSITORY) + r'/\.github/workflows/([A-Za-z0-9_-]+\.ya?ml)@(refs/(?:heads|tags|pull)/[^\s@]+)'
    match = re.fullmatch(pattern, ref or '')
    if not re.fullmatch(r'[0-9a-f]{40}', sha or '') or not match:
        raise ValueError('invalid or incomplete workflow definition identity')
    return {'status': 'producer_observed', 'attested': False, 'sha': sha,
            'path': '.github/workflows/' + match.group(1), 'ref': match.group(2)}


def record(root: Path, *, module: str, kind: str, head: str, base: str,
           database: str, status: int, log: Path, context_file: Path, output: Path,
           now: datetime | None = None, selection: str = '', duration_seconds: float | None = None, secrets_file: Path | None = None, scope_plan: Path | None = None,
           readback: dict | Path | None = None) -> dict:
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
    isolated_log = kind == 'python' and any(x.startswith(ISOLATED_MARKER) for x in log.read_text().splitlines())
    if isolated_log:
        if set(runtime) != {'services', 'isolated_image_id'} or runtime['services'] != {} or not re.fullmatch(r'sha256:[0-9a-f]{64}', str(runtime['isolated_image_id'])):
            raise ValueError('isolated runtime identity missing')
    elif set(runtime.get('services', {})) != {'db', 'redis'}:
        raise ValueError('runtime service identity missing')
    image_ids = [runtime['isolated_image_id']] if isolated_log else [runtime.get('odoo_image_id')] + [runtime['services'][s].get('image_id') for s in ('db', 'redis')]
    if any(not re.fullmatch(r'sha256:[0-9a-f]{64}', str(value)) for value in image_ids):
        raise ValueError('content-bound runtime image identity missing')
    workflow_definition = workflow_definition_observation()
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
    readback_blockers, readback_closure = readback_closure_blockers(readback, head=head)
    blockers = ['platform_source_not_authenticated'] + readback_blockers
    if not (scope and scope.get('dependency_closure_complete')):
        blockers.append('target_dependency_closure_not_certified')
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
        'workflow_definition': workflow_definition,
        'files': {name: digest((target / name).read_bytes()) for name in ('execution.log', 'runtime.json', 'python.json')},
        'reuse_ready': False,
        'blockers': blockers,
    }
    if readback_closure is not None:
        receipt['readback_closure'] = readback_closure
    isolated = [json.loads(line[len(ISOLATED_MARKER):]) for line in text.splitlines() if line.startswith(ISOLATED_MARKER)]
    if isolated:
        if len(isolated) != 1 or kind != 'python' or module != ISOLATED_MODULE:
            raise ValueError('invalid isolated execution marker')
        validate_isolated_result(isolated[0], count)
        receipt['isolated_python'] = isolated[0]
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
    if 'workflow_definition' in receipt:
        definition = receipt['workflow_definition']
        if not isinstance(definition, dict):
            raise ValueError('invalid workflow definition observation')
        if definition == {'status': 'not_captured', 'attested': False}:
            pass
        else:
            expected = workflow_definition_observation({
                'GITHUB_WORKFLOW_SHA': definition.get('sha'),
                'GITHUB_WORKFLOW_REF': REPOSITORY + '/' + str(definition.get('path')) + '@' + str(definition.get('ref')),
            })
            if definition != expected:
                raise ValueError('workflow definition observation cannot self-attest')
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


def reuse_closure(*, platform_source_authenticated: bool = False,
                  artifact_attempt_attested: bool = False,
                  execution_definition_attested: bool = False,
                  runtime_contract_readback: bool = False,
                  fact_scope_readback: bool = False,
                  target_dependency_closure: bool = False) -> dict:
    """Single source of truth for the ORM reuse closure dimensions.

    Reuse is authorized only when every dimension is independently certified.
    No dimension may be inferred from another: an identical source tree does
    not close the runtime contract readback, and a green full run does not
    close the fact readback. The returned blockers keep the existing receipt
    vocabulary so consumers stay stable.
    """
    dimensions = {
        'platform_source_authenticated': (platform_source_authenticated,
                                          'platform_source_not_authenticated'),
        'artifact_attempt_attested': (artifact_attempt_attested,
                                      'artifact_attempt_not_attested'),
        'execution_definition_attested': (execution_definition_attested,
                                          'execution_definition_not_attested'),
        'runtime_contract_readback': (runtime_contract_readback,
                                      'runtime_contract_readback_missing'),
        'fact_scope_readback': (fact_scope_readback,
                                'fact_scope_readback_missing'),
        'target_dependency_closure': (target_dependency_closure,
                                      'target_dependency_closure_not_certified'),
    }
    blockers = [label for closed, label in dimensions.values() if not closed]
    return {'reuse_ready': not blockers,
            'dimensions': {name: bool(closed) for name, (closed, _) in dimensions.items()},
            'blockers': blockers}


def readback_witness_closure(witness: dict) -> dict:
    """Map a runtime readback report to the contract and fact closure.

    The runtime-sealed contract and the business facts are the only product
    authority. A report closes `runtime_contract_readback` only when it carries
    a verified source->contract binding, and closes `fact_scope_readback` only
    under full three-way scalar parity (no mismatches and no uncovered fields).
    Uncovered relation/derived/context-dependent fields always keep the fact
    scope open; a static JSON snapshot never stands in for either dimension.
    """
    if not isinstance(witness, dict) or witness.get('schema') != 'backend-contract-fact-readback/v1':
        raise ValueError('runtime readback witness required')
    observation = witness.get('observation')
    if (not isinstance(observation, dict) or not observation.get('source_sha256')
            or not observation.get('contract_sha256')):
        raise ValueError('readback source/contract binding missing')
    parity = observation.get('value_parity')
    if (not isinstance(parity, dict) or not isinstance(parity.get('checked_fields'), list)
            or not parity['checked_fields']):
        raise ValueError('readback value parity missing')
    mismatches = list(parity.get('mismatch_fields') or [])
    uncovered = dict(parity.get('uncovered_fields') or {})
    full = bool(parity.get('full_projection_parity', not mismatches and not uncovered))
    return {'runtime_contract_readback': not mismatches,
            'fact_scope_readback': full and not mismatches,
            'projection_value_coverage_incomplete': not full,
            'checked_fields': list(parity['checked_fields']),
            'uncovered_fields': uncovered,
            'mismatch_fields': mismatches}


def readback_closure_blockers(readback, *, head: str) -> tuple[list[str], dict | None]:
    """Bind a runtime readback witness to an exact head and return its blockers.

    Only a witness whose source head equals the receipt head and whose value
    parity is full closes the contract/fact dimensions. An absent witness keeps
    both blockers open; a mismatched head is refused; uncovered fields keep the
    fact scope open. Closure is never fabricated.
    """
    if readback is None:
        return ['runtime_contract_readback_missing', 'fact_scope_readback_missing'], None
    if not isinstance(readback, dict):
        readback = json.loads(readback.read_text() if hasattr(readback, 'read_text') else readback)
    if readback.get('source_head') != head:
        raise ValueError('readback witness source head does not match receipt head')
    closure = readback_witness_closure(readback)
    blockers = []
    if not closure['runtime_contract_readback']:
        blockers.append('runtime_contract_readback_missing')
    if not closure['fact_scope_readback']:
        blockers.append('fact_scope_readback_missing')
        if closure['projection_value_coverage_incomplete']:
            blockers.append('projection_value_coverage_incomplete')
    return blockers, closure


def receipt_reuse_authorized(receipt: dict) -> tuple[bool, list[str]]:
    """Whether an authenticated receipt authorizes reuse for its target.

    Authorization is never inferred, and a producer's ``reuse_ready`` flag is
    never trusted on its own. Two independently attested authorities authorize
    reuse: the isolated pure-Python profile's verified workflow-execution
    authority, and a verify_github_origin result whose six closure dimensions
    all closed. Every other target stays blocked.
    """
    if not isinstance(receipt, dict):
        return False, ['receipt_missing']
    if receipt.get('isolated_execution_authority') == 'verified_workflow_execution':
        return True, []
    if receipt.get('reuse_authority') == 'verified_six_dimension_closure':
        return True, []
    return False, list(receipt.get('blockers') or ['reuse_closure_not_independently_attested'])


REPOSITORY = 'lidefend/sce-backend-odoo'
REPOSITORY_ID = 1307419149
ARCHIVE_LIMIT = 64 * 1024 * 1024
MAX_LOCATORS = 256


def github_bytes(endpoint: str) -> bytes:
    # Fixed host, read-only GET, managed credential configuration. No URL from
    # an artifact or receipt is ever followed by this code.
    env = dict(os.environ)
    if not env.get('GH_TOKEN') and not env.get('GITHUB_TOKEN'):
        env['GH_CONFIG_DIR'] = '/home/lidefend/.config/gh-new-account'
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


WORKFLOW_PATHS = frozenset({
    '.github/workflows/backend_test_suite.yml',
    '.github/workflows/professional_quality_gate.yml',
})


def workflow_authority_blobs(source_tree: str, fetch) -> dict[str, str]:
    """Workflow files at the candidate source tree are the verified definition."""
    tree = json.loads(fetch(f'git/trees/{source_tree}?recursive=1'))
    if tree.get('sha') != source_tree or tree.get('truncated') is not False:
        raise ValueError('source tree incomplete for workflow authority')
    blobs = {}
    for item in tree.get('tree', []):
        if item.get('path') in WORKFLOW_PATHS:
            if item.get('type') != 'blob' or item.get('mode') not in ('100644', '100755'):
                raise ValueError('workflow authority entry is not a regular blob')
            blobs[item['path']] = item['sha']
    if set(blobs) != WORKFLOW_PATHS:
        raise ValueError('workflow authority blobs incomplete')
    return blobs


def verify_github_origin(*, run_id: int, attempt: int, artifact_id: int,
                         shard: int, expected_head: str, module: str,
                         now: datetime | None = None, fetch=None) -> dict:
    # This authenticates platform origin, not the correctness of candidate-
    # supplied test code. Trusted execution-definition approval remains separate.
    if (any(type(v) is not int or v <= 0 for v in (run_id, attempt, artifact_id))
            or type(shard) is not int or shard < 0
            or not re.fullmatch('[0-9a-f]{40}', expected_head)
            or not re.fullmatch('[a-zA-Z_][a-zA-Z0-9_]*', module)):
        raise ValueError('invalid exact platform identity')
    fetch = github_bytes if fetch is None else fetch
    run_path = f'actions/runs/{run_id}/attempts/{attempt}'
    run = json.loads(fetch(run_path))
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
    artifact = json.loads(fetch(f'actions/artifacts/{artifact_id}'))
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
    raw = fetch(f'actions/artifacts/{artifact_id}/zip')
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
    commit = json.loads(fetch(f'git/commits/{expected_head}'))
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
    execution_definition_attested = False
    if isinstance(receipt.get('workflow_definition'), dict):
        try:
            attest_execution_definition(
                run, receipt['workflow_definition'],
                workflow_authority_blobs(receipt['source_tree'], fetch), fetch)
            execution_definition_attested = True
        except (ValueError, KeyError, TypeError, AttributeError, OSError, subprocess.SubprocessError):
            execution_definition_attested = False
    readback_closure = receipt.get('readback_closure')
    runtime_contract_readback = bool(readback_closure and readback_closure.get('runtime_contract_readback'))
    fact_scope_readback = bool(readback_closure and readback_closure.get('fact_scope_readback'))
    scope_plan = receipt.get('scope_plan')
    target_dependency_closure = bool(scope_plan and scope_plan.get('dependency_closure_complete'))
    blockers = []
    if not execution_definition_attested:
        blockers.append('execution_definition_not_attested')
    if not runtime_contract_readback:
        blockers.append('runtime_contract_readback_missing')
    if not fact_scope_readback:
        blockers.append('fact_scope_readback_missing')
    if not target_dependency_closure:
        blockers.append('target_dependency_closure_not_certified')
    # The GitHub artifact API does not expose the upload attempt, so this
    # dimension stays closed-shut until an alternative authority is available.
    blockers.append('artifact_attempt_not_attested')
    reuse_authority = 'verified_six_dimension_closure' if not blockers else None
    return {**verified, 'platform_origin': 'verified', 'repository': REPOSITORY,
            'run_id': run_id, 'requested_attempt': attempt, 'artifact_id': artifact_id,
            'run_attempt_metadata': 'verified', 'artifact_attempt': 'not_attested',
            'execution_definition_attested': execution_definition_attested,
            'reuse_authority': reuse_authority,
            'archive_sha256': archive_digest.removeprefix('sha256:'),
            'receipt_sha256': digest(files[module+'/receipt.json']),
            'workflow_path': run['path'],
            'scope_plan': receipt.get('scope_plan'), 'test_count': receipt['test_count'],
            'issued_at': receipt['issued_at'], 'expires_at': receipt['expires_at'],
            'actual_duration_seconds': receipt.get('actual_duration_seconds'),
            'isolated_python': receipt.get('isolated_python'), 'source_tree': receipt['source_tree'],
            'workflow_definition': receipt.get('workflow_definition'),
            'blockers': blockers}


def observe_github_job(*, run_id: int, attempt: int, job_id: int,
                       expected_head: str, workflow_path: str) -> dict:
    """Authenticate completed step observations, never a Quick/test reuse receipt.

    A green job is not proof of its shell branches, checkout, target coverage or
    test environment. Preserve failed/skipped steps rather than converting the
    job conclusion into target-level success.
    """
    workflows = {'.github/workflows/' + name + '.yml' for name in (
        'professional_quality_gate', 'frontend_release_gate', 'public_guard',
        'merge_policy_gate', 'backend_test_suite')}
    if (any(type(v) is not int or v <= 0 for v in (run_id, attempt, job_id))
            or not isinstance(expected_head, str)
            or not re.fullmatch('[0-9a-f]{40}', expected_head)
            or workflow_path not in workflows):
        raise ValueError('invalid exact job observation identity')
    paths = [f'actions/runs/{run_id}/attempts/{attempt}',
             f'actions/jobs/{job_id}', f'git/commits/{expected_head}']
    raw = {path: github_bytes(path) for path in paths}
    run, job, commit = (json.loads(raw[path]) for path in paths)
    if not all(isinstance(value, dict) for value in (run, job, commit)):
        raise ValueError('invalid platform metadata shape')
    for field in ('repository', 'head_repository'):
        repository = run.get(field)
        if (not isinstance(repository, dict)
                or repository.get('id') != REPOSITORY_ID
                or repository.get('full_name') != REPOSITORY):
            raise ValueError('foreign repository')
    if (run.get('id') != run_id or run.get('run_attempt') != attempt
            or run.get('head_sha') != expected_head or run.get('path') != workflow_path
            or run.get('event') not in ('pull_request', 'workflow_dispatch', 'schedule')
            or run.get('status') != 'completed'):
        raise ValueError('run observation identity mismatch or unfinished')
    if (job.get('id') != job_id or job.get('run_id') != run_id
            or job.get('run_attempt') != attempt or job.get('head_sha') != expected_head
            or job.get('status') != 'completed'):
        raise ValueError('job observation identity mismatch or unfinished')
    tree = (commit.get('tree') or {}).get('sha')
    if commit.get('sha') != expected_head or not isinstance(tree, str) or not re.fullmatch('[0-9a-f]{40}', tree):
        raise ValueError('source tree identity missing')
    conclusions = {'success', 'failure', 'skipped', 'cancelled', 'timed_out',
                   'neutral', 'action_required', 'stale', 'startup_failure'}
    if run.get('conclusion') not in conclusions or job.get('conclusion') not in conclusions:
        raise ValueError('unknown execution conclusion')
    steps = job.get('steps')
    if not isinstance(steps, list) or not steps:
        raise ValueError('step observations missing')
    numbers, observations = set(), []
    for step in steps:
        if (not isinstance(step, dict) or type(step.get('number')) is not int
                or step['number'] <= 0 or step['number'] in numbers
                or not isinstance(step.get('name'), str) or not step['name']
                or step.get('status') != 'completed' or step.get('conclusion') not in conclusions):
            raise ValueError('invalid or ambiguous step observation')
        numbers.add(step['number'])
        observations.append({key: step.get(key) for key in (
            'number', 'name', 'status', 'conclusion', 'started_at', 'completed_at')})
    return {
        'schema': 'github-job-observation/v1', 'platform_origin': 'verified',
        'repository': REPOSITORY, 'head': expected_head, 'tree': tree,
        'run_id': run_id, 'attempt': attempt, 'job_id': job_id,
        'workflow_path': workflow_path, 'run_conclusion': run['conclusion'],
        'job_conclusion': job['conclusion'], 'steps': observations,
        'metadata_sha256': {path: digest(value) for path, value in raw.items()},
        'reuse_ready': False, 'quick_receipt': False,
        'blockers': ['checkout_identity_not_attested', 'execution_definition_not_attested',
                     'target_coverage_not_attested', 'environment_identity_not_attested',
                     'target_dependency_closure_not_certified'],
    }



# The first closed execution profile uses immutable container bytes and an
# explicit read-only source view. ORM observations remain non-reusable: this
# profile proves no database, role or live-contract behavior.
ISOLATED_RUNNER = r"""
import importlib.util,json,sys,unittest
spec=importlib.util.spec_from_file_location('capture','/tools/scripts/ci/backend_test_receipt.py')
capture=importlib.util.module_from_spec(spec);spec.loader.exec_module(capture)
print(capture.ENV_MARKER+json.dumps(capture.python_environment()),flush=True)
suite=unittest.defaultTestLoader.discover('addons/smart_construction_scene/tests',pattern='test*.py')
def ids(item):
    if isinstance(item,unittest.TestSuite):
        return [name for child in item for name in ids(child)]
    return [item.id()]
names=sorted(ids(suite))
result=unittest.TextTestRunner(verbosity=2).run(suite)
print('SC_BACKEND_TEST_IDS='+json.dumps({'ids':names,'run':result.testsRun,'skipped':len(result.skipped)}),flush=True)
sys.exit(0 if names and result.wasSuccessful() and not result.skipped and result.testsRun==len(names) else 1)
"""


def validate_isolated_result(value: dict, count: int) -> None:
    if (not isinstance(value, dict) or value.get('schema') != 'backend-isolated-python/v1'
            or not re.fullmatch('[0-9a-f]{64}', str(value.get('fingerprint', '')))
            or value.get('module') != ISOLATED_MODULE or value.get('skipped') != 0
            or not isinstance(value.get('test_ids'), list) or not value['test_ids']
            or any(not isinstance(x, str) or not x for x in value['test_ids'])
            or value['test_ids'] != sorted(set(value['test_ids']))
            or len(value['test_ids']) != count):
        raise ValueError('isolated execution scope is incomplete')


def isolated_snapshot(root: Path, head: str, destination: Path, image_id: str) -> dict:
    import backend_impact_plan as impact
    graph = impact.snapshot(head)
    target = graph[ISOLATED_MODULE]
    if target.get('unresolved_file_reads'):
        raise ValueError('isolated test file inputs unresolved')
    paths = sorted(set(['addons', 'demo_addons'] + target['file_inputs']))
    raw = subprocess.check_output(['git', 'archive', '--format=tar', head, '--', *paths], cwd=root)
    files = {}
    with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
        for member in archive:
            path = PurePosixPath(member.name)
            if path.is_absolute() or '..' in path.parts or str(path) != member.name.rstrip('/'):
                raise ValueError('invalid snapshot path')
            if member.isdir():
                continue
            if not member.isfile():
                raise ValueError('isolated source links/special files are not supported')
            data = archive.extractfile(member).read()
            file = destination / str(path)
            file.parent.mkdir(parents=True, exist_ok=True)
            mode = 0o755 if member.mode & 0o111 else 0o644
            file.write_bytes(data); file.chmod(mode)
            files[str(path)] = {'sha256': digest(data), 'mode': mode,
                                'git_blob': hashlib.sha1(('blob '+str(len(data))+'\0').encode()+data).hexdigest()}
    executor = subprocess.check_output(['git', 'show', head + ':scripts/ci/backend_test_receipt.py'], cwd=root)
    recipe = {'schema': 'backend-isolated-python/v1', 'module': ISOLATED_MODULE,
              'source_files': files, 'executor_sha256': digest(executor),
              'image_id': image_id, 'runner_sha256': digest(ISOLATED_RUNNER.encode()),
              'definitions': {path: digest(subprocess.check_output(['git','show',head+':'+path],cwd=root))
                  for path in ('scripts/ci/backend_impact_plan.py','scripts/ops/evidence_scope.py',
                               '.github/workflows/backend_test_suite.yml',
                               '.github/workflows/professional_quality_gate.yml')},
              'network': 'none', 'rootfs': 'readonly', 'user': '65534:65534',
              'cwd': '/workspace', 'environment': ['PATH=/usr/bin:/bin', 'HOME=/tmp',
              'LANG=C.UTF-8', 'LC_ALL=C.UTF-8', 'TZ=UTC', 'ENV=',
              'PYTHONHASHSEED=0', 'PYTHONDONTWRITEBYTECODE=1']}
    if not files or not re.fullmatch('sha256:[0-9a-f]{64}', image_id):
        raise ValueError('incomplete isolated inputs')
    definitions = list(recipe['definitions']) + ['scripts/ci/backend_test_receipt.py']
    authority_blobs = {path: command('git','rev-parse',head+':'+path,cwd=root) for path in definitions}
    recipe['authority_blobs'] = authority_blobs
    return {'fingerprint': digest(canonical(recipe)), 'recipe': recipe, 'executor': executor}


def attest_execution_definition(run: dict, definition: dict, authority_blobs: dict, fetch) -> None:
    """Bind workflow bytes to platform provenance, separately from test checkout.

    Reusable PR workflows are executed from a platform-reported merge revision.
    Never equate that revision with the tested source SHA or trust a producer's
    workflow SHA without the platform's referenced_workflows observation.
    """
    workflow = '.github/workflows/backend_test_suite.yml'
    if run.get('event') in ('schedule', 'workflow_dispatch') and run.get('path') == workflow:
        if definition.get('sha') != run.get('head_sha') or definition.get('path') != workflow:
            raise ValueError('root execution definition does not match platform revision')
        return
    if run.get('event') != 'pull_request' or run.get('path') != '.github/workflows/professional_quality_gate.yml':
        raise ValueError('unsupported execution definition provenance')
    references = run.get('referenced_workflows') or []
    matches = [ref for ref in references
               if ref.get('path') == REPOSITORY + '/' + workflow + '@' + str(ref.get('sha'))]
    if len(matches) != 1:
        raise ValueError('reusable workflow platform revision missing or ambiguous')
    revision = matches[0].get('sha', '')
    if (not re.fullmatch('[0-9a-f]{40}', revision)
            or definition.get('sha') != revision
            or definition.get('path') not in (run['path'], workflow)):
        raise ValueError('observed workflow does not match platform reusable revision')
    commit = json.loads(fetch('git/commits/' + revision))
    if commit.get('sha') != revision or run['head_sha'] not in [x.get('sha') for x in commit.get('parents', [])]:
        raise ValueError('workflow merge revision does not contain tested head as parent')
    tree_sha = (commit.get('tree') or {}).get('sha')
    tree = json.loads(fetch('git/trees/' + str(tree_sha) + '?recursive=1'))
    if tree.get('sha') != tree_sha or tree.get('truncated') is not False:
        raise ValueError('workflow revision tree incomplete')
    files = {x['path']: x for x in tree['tree']}
    for path in (workflow, run['path']):
        item = files.get(path, {})
        if (path not in authority_blobs or item.get('type') != 'blob'
                or item.get('mode') not in ('100644', '100755') or item.get('sha') != authority_blobs[path]):
            raise ValueError('executed workflow bytes differ from verified source definition')


def isolated_history(fingerprint: str, *, recipe: dict, fetch=None) -> tuple[dict | None, list]:
    """Only completed real executions seed reuse; reused decisions never renew TTL."""
    fetch = fetch or functools.lru_cache(maxsize=64)(github_bytes)
    rejected = []
    payload = json.loads(fetch('actions/runs?status=success&per_page=30'))
    for run in payload.get('workflow_runs', []):
        if (run.get('id') == int(os.environ.get('GITHUB_RUN_ID', '0'))
                or run.get('path') not in ('.github/workflows/backend_test_suite.yml',
                                           '.github/workflows/professional_quality_gate.yml')
                or run.get('event') not in ('schedule', 'workflow_dispatch', 'pull_request')
                or run.get('repository', {}).get('id') != REPOSITORY_ID
                or run.get('head_repository', {}).get('id') != REPOSITORY_ID):
            continue
        try:
            # An attempt-1 run has no ambiguous artifact attribution to a retry.
            # Later attempts remain RUN until the platform can attest their upload.
            if run.get('run_attempt') != 1:
                continue
            started = datetime.fromisoformat(run['run_started_at'].replace('Z', '+00:00'))
            if datetime.now(timezone.utc) - started >= MAX_AGE:
                continue
            artifacts = json.loads(fetch(f"actions/runs/{run['id']}/artifacts?per_page=100"))
            for artifact in artifacts.get('artifacts', []):
                match = re.fullmatch(r'backend-execution-(\d+)-1-(\d+)', artifact.get('name', ''))
                if not match or int(match[1]) != run['id']:
                    continue
                locator = {'run_id':run['id'], 'attempt':1, 'artifact_id':artifact['id'],
                           'shard':int(match[2]), 'expected_head':run['head_sha'], 'module':ISOLATED_MODULE}
                try:
                    verified = verify_github_origin(**locator, fetch=fetch)
                    proof = verified.get('isolated_python')
                    validate_isolated_result(proof, verified['test_count'])
                    if proof['fingerprint'] != fingerprint:
                        continue
                    tree = json.loads(fetch(f"git/trees/{verified['source_tree']}?recursive=1"))
                    if tree.get('truncated') is not False or tree.get('sha') != verified['source_tree']:
                        raise ValueError('historical tree is incomplete')
                    blobs = {x['path']:x for x in tree['tree'] if x['type'] != 'tree'}
                    expected_files = recipe['source_files']
                    visible = {path for path in blobs if path.startswith(('addons/','demo_addons/')) or path in expected_files}
                    if visible != set(expected_files):
                        raise ValueError('historical source scope differs')
                    for path, entry in expected_files.items():
                        old = blobs[path]
                        if (old['type'] != 'blob' or old['sha'] != entry['git_blob']
                                or old['mode'] != format(0o100000 | entry['mode'], 'o')):
                            raise ValueError('historical source bytes differ')
                    for path, oid in recipe['authority_blobs'].items():
                        if blobs.get(path, {}).get('sha') != oid or blobs[path]['type'] != 'blob':
                            raise ValueError('historical executor/decision definition differs')
                    definition = verified.get('workflow_definition') or {}
                    attest_execution_definition(run, definition, recipe['authority_blobs'], fetch)
                    # Do not trust producer field names alone: match the execution
                    # marker against the authenticated log. Only an original
                    # attempt is eligible; attempt-number names alone are insufficient.
                    raw = fetch(f"actions/artifacts/{artifact['id']}/zip")
                    members = archive_members(raw)
                    log = members[ISOLATED_MODULE+'/execution.log'].decode()
                    markers = [json.loads(x[len(ISOLATED_MARKER):]) for x in log.splitlines()
                               if x.startswith(ISOLATED_MARKER)]
                    if markers != [proof]:
                        raise ValueError('isolated execution log binding mismatch')
                    return {**verified, 'locator': locator,
                            'isolated_execution_authority':'verified_workflow_execution'}, rejected
                except (ValueError, KeyError, TypeError, AttributeError, zipfile.BadZipFile, OSError, subprocess.SubprocessError) as exc:
                    rejected.append({'run_id':run['id'], 'artifact_id':artifact['id'], 'reason':str(exc)})
        except (ValueError, KeyError, TypeError, AttributeError, zipfile.BadZipFile, OSError, subprocess.SubprocessError) as exc:
            rejected.append({'run_id':run.get('id'), 'reason':str(exc)})
    return None, rejected


def discover_receipt_locators(*, head: str, modules: list[str],
                              fetch=None, max_runs: int = 30) -> list[dict]:
    """Discover exact remote artifact locators for the current modules.

    Bounded by a TTL and a run limit and never returns producer verdicts: the
    returned locators are untrusted addresses consumed by verify_github_origin.
    A failed or empty API response yields an empty list, which forces RUN and
    never fabricates REUSE. Non-ancestor or mismatched locators are rejected
    later by select_historical_receipts, not trusted here.
    """
    if (not re.fullmatch('[0-9a-f]{40}', head) or not isinstance(modules, list)
            or not modules or any(not re.fullmatch('[A-Za-z_][A-Za-z0-9_]*', name) for name in modules)):
        return []
    fetch = fetch or functools.lru_cache(maxsize=64)(github_bytes)
    locators = []
    try:
        payload = json.loads(fetch(f'actions/runs?status=success&per_page={max_runs}'))
    except (ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError):
        return []
    for run in payload.get('workflow_runs', []):
        if (run.get('run_attempt') != 1
                or run.get('repository', {}).get('id') != REPOSITORY_ID
                or run.get('head_repository', {}).get('id') != REPOSITORY_ID
                or run.get('event') not in ('pull_request', 'workflow_dispatch', 'schedule')
                or run.get('path') not in ('.github/workflows/backend_test_suite.yml',
                                           '.github/workflows/professional_quality_gate.yml')):
            continue
        try:
            started = datetime.fromisoformat(run['run_started_at'].replace('Z', '+00:00'))
        except (KeyError, AttributeError, ValueError):
            continue
        if datetime.now(timezone.utc) - started >= MAX_AGE:
            continue
        try:
            artifacts = json.loads(fetch(f"actions/runs/{run['id']}/artifacts?per_page=100"))
        except (ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError):
            continue
        for artifact in artifacts.get('artifacts', []):
            match = re.fullmatch(r'backend-execution-(\d+)-1-(\d+)', artifact.get('name', ''))
            if (not match or int(match[1]) != run['id'] or artifact.get('expired') is not False):
                continue
            for module in modules:
                locators.append({'head': run['head_sha'], 'module': module,
                                 'run_id': run['id'], 'attempt': 1,
                                 'artifact_id': artifact['id'], 'shard': int(match[2])})
                if len(locators) >= MAX_LOCATORS:
                    return locators
    return locators


def isolated_decision(fingerprint: str, previous: dict | None, *, force_full: bool) -> dict:
    sys.path.insert(0, str(ROOT/'scripts/ops'))
    import evidence_scope
    document = {'schema':evidence_scope.UNITS_SCHEMA, 'check':'backend.isolated.python',
                'identity':{'profile':'backend-isolated-python/v1'},
                'units':[{'id':ISOLATED_MODULE, 'fingerprint':fingerprint, 'required':True}]}
    ledger = {'check':document['check'], 'identity':document['identity'], 'units':{}}
    if previous and not force_full:
        validate_isolated_result(previous['isolated_python'], previous['test_count'])
        if (previous.get('platform_origin') != 'verified' or previous.get('integrity') != 'verified'
                or previous.get('isolated_execution_authority') != 'verified_workflow_execution'):
            raise ValueError('history was not authenticated')
        ledger['units'][ISOLATED_MODULE] = {'status':'passed',
            'fingerprint':previous['isolated_python']['fingerprint']}
    plan = evidence_scope.plan_units(document, ledger)
    reuse = ISOLATED_MODULE in plan['reusable']
    return {'target':ISOLATED_MODULE, 'decision':'REUSE' if reuse else 'RUN',
            'reason':'matching_authenticated_isolated_inputs' if reuse else ('scheduled_full' if force_full else 'no_matching_evidence'),
            'input_fingerprint':fingerprint, 'previous_receipt':previous['locator'] if reuse else None,
            'previous_receipt_sha256':previous['receipt_sha256'] if reuse else None,
            'estimated_saved_time':previous.get('actual_duration_seconds') if reuse else 0,
            'actual_duration':None, 'actual_saved_time':None}



def execute_isolated_container(args: list[str], log: Path, *, timeout: int = 300):
    # Unique ownership even in local fault tests; never remove another run's container.
    owner = '-'.join(str(os.environ.get(key, 'local')) for key in
                     ('GITHUB_RUN_ID','GITHUB_RUN_ATTEMPT','SHARD_INDEX'))
    owner = re.sub('[^a-zA-Z0-9_.-]', '-', owner)[:80]
    name = 'sc-isolated-python-' + owner + '-' + uuid.uuid4().hex[:12]
    args = args[:2] + ['--name',name] + args[2:]
    try:
        try:
            result = subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=timeout)
            log.write_text(result.stdout or '')
            return result
        except subprocess.TimeoutExpired as exc:
            partial = exc.stdout or b''
            if isinstance(partial,str):partial=partial.encode()
            log.write_bytes(partial+b'\n[isolated executor] timeout\n')
            return subprocess.CompletedProcess(args,124,log.read_text(errors='replace'))
    finally:
        subprocess.run(['docker','rm','-f',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=30,check=False)


def run_isolated_python(*, root: Path, head: str, base: str, output: Path,
                        context_file: Path, scope_plan: Path, force_full: bool) -> dict:
    if command('git','rev-parse','HEAD',cwd=root) != head or command('git','status','--porcelain',cwd=root):
        raise ValueError('isolated executor requires clean exact candidate')
    dockerfile = command('git','show',head+':Dockerfile',cwd=root)
    image = re.search(r'^ARG ODOO_BASE_IMAGE=(odoo:[^\s]+@sha256:[0-9a-f]{64})$',dockerfile,re.M)
    if not image:
        raise ValueError('immutable registered Python runtime image missing')
    image = image[1]
    try:
        image_id = command('docker','image','inspect','--format','{{.Id}}',image)
    except subprocess.CalledProcessError:
        subprocess.run(['docker','pull',image],check=True,timeout=300)
        image_id = command('docker','image','inspect','--format','{{.Id}}',image)
    output.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp); snapshot = home/'source';snapshot.mkdir()
        bound = isolated_snapshot(root,head,snapshot,image_id)
        previous, rejected = None, []
        if not force_full:
            try:
                previous, rejected = isolated_history(bound['fingerprint'], recipe=bound['recipe'])
            except (ValueError, KeyError, TypeError, AttributeError, zipfile.BadZipFile, OSError, subprocess.SubprocessError) as exc:
                rejected = [{'reason': 'history_unavailable: ' + str(exc)}]
        decision = isolated_decision(bound['fingerprint'],previous,force_full=force_full)
        decision.update(source_head=head, source_tree=command('git','rev-parse',head+'^{tree}',cwd=root),
                        rejected_candidates=rejected)
        path = output/('isolated-decision-'+ISOLATED_MODULE+'.json')
        if decision['decision'] == 'REUSE':
            path.write_bytes(canonical(decision));return decision
        tool = home/'backend_test_receipt.py';tool.write_bytes(bound['executor']);tool.chmod(0o644)
        home.chmod(0o755)
        args = ['docker','run','--rm','--network','none','--read-only','--cap-drop','ALL',
                '--security-opt','no-new-privileges','--user','65534:65534',
                '--tmpfs','/tmp:rw,nosuid,nodev,size=64m','--workdir','/workspace',
                '--mount',f'type=bind,src={snapshot},dst=/workspace,readonly',
                '--mount',f'type=bind,src={tool},dst=/tools/scripts/ci/backend_test_receipt.py,readonly',
                '--entrypoint','/usr/bin/env',image_id,'-i',*bound['recipe']['environment'],
                '/usr/bin/python3','-c',ISOLATED_RUNNER]
        started = time.monotonic()
        log = output/'isolated-python-execution.log'
        result = execute_isolated_container(args,log)
        duration = time.monotonic()-started
        decision['actual_duration'] = duration
        if result.returncode:
            decision.update(decision='BLOCK',reason='isolated_execution_failed',exit_code=result.returncode)
            path.write_bytes(canonical(decision));raise ValueError('isolated Python execution failed; original log retained')
        ids = [json.loads(x.split('=',1)[1]) for x in result.stdout.splitlines() if x.startswith('SC_BACKEND_TEST_IDS=')]
        if len(ids) != 1 or ids[0]['run'] != len(ids[0]['ids']):
            raise ValueError('isolated test IDs missing')
        proof = {'schema':'backend-isolated-python/v1','module':ISOLATED_MODULE,
                 'fingerprint':bound['fingerprint'],'test_ids':ids[0]['ids'],'skipped':ids[0]['skipped']}
        validate_isolated_result(proof,ids[0]['run'])
        with log.open('a') as stream:stream.write('\n'+ISOLATED_MARKER+canonical(proof).decode()+'\n')
        isolated_context = output/'isolated-runtime.json'
        isolated_context.write_bytes(canonical({'services':{},'isolated_image_id':image_id}))
        record(root,module=ISOLATED_MODULE,kind='python',head=head,base=base,database='',status=0,
               log=log,context_file=isolated_context,output=output,duration_seconds=duration,scope_plan=scope_plan)
        decision.update(test_count=ids[0]['run'],test_ids=ids[0]['ids'],exit_code=0)
        path.write_bytes(canonical(decision));return decision


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('environment', 'context', 'record', 'verify', 'verify-origin', 'verify-contract-source', 'archive-attempt', 'observe-job', 'isolated-python'))
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
    parser.add_argument('--readback', type=Path)
    parser.add_argument('--log-status', type=int, default=0)
    parser.add_argument('--contract', type=Path)
    parser.add_argument('--source-payload', type=Path)
    parser.add_argument('--run-id', type=int)
    parser.add_argument('--attempt', type=int)
    parser.add_argument('--artifact-id', type=int)
    parser.add_argument('--shard', type=int)
    parser.add_argument('--job-id', type=int)
    parser.add_argument('--workflow-path')
    parser.add_argument('--force-full', action='store_true')
    args = parser.parse_args()
    if args.mode == 'isolated-python':
        print(json.dumps(run_isolated_python(root=ROOT,head=args.head,base=args.base,output=args.output,
            context_file=args.context,scope_plan=args.scope_plan,force_full=args.force_full)))
    elif args.mode == 'environment':
        print(ENV_MARKER + canonical(python_environment()).decode())
    elif args.mode == 'context':
        args.output.write_bytes(canonical(context()))
    elif args.mode == 'record':
        result = record(ROOT, module=args.module, kind=args.kind, head=args.head, base=args.base,
                        database=args.database, status=args.status, log=args.log,
                        context_file=args.context, output=args.output, selection=args.selection,
                        duration_seconds=args.duration_seconds, secrets_file=args.secrets_file,
                        scope_plan=args.scope_plan, readback=args.readback)
        print(json.dumps({'module': result['module'], 'test_count': result['test_count'],
                          'receipt_sha256': result['receipt_sha256'], 'reuse_ready': False}))
    elif args.mode == 'archive-attempt':
        print(json.dumps(archive_attempt(output=args.output,module=args.module,attempt=args.attempt,
             head=args.head,status=args.status,log_status=args.log_status,log=args.log,
             database=args.database,secrets_file=args.secrets_file)))
    elif args.mode == 'verify-contract-source':
        print(json.dumps(contract_source_binding(json.loads(args.contract.read_text()),
                                                json.loads(args.source_payload.read_text()))))
    elif args.mode == 'observe-job':
        print(json.dumps(observe_github_job(run_id=args.run_id, attempt=args.attempt,
            job_id=args.job_id, expected_head=args.head, workflow_path=args.workflow_path)))
    elif args.mode == 'verify-origin':
        print(json.dumps(verify_github_origin(run_id=args.run_id, attempt=args.attempt,
            artifact_id=args.artifact_id, shard=args.shard, expected_head=args.head, module=args.module)))
    else:
        print(json.dumps(verify(args.output, expected_head=args.head, expected_digest=args.receipt_sha256,scope_plan=args.scope_plan)))


if __name__ == '__main__':
    main()
