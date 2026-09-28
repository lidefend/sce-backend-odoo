"""Validate owner-published local execution evidence in the trusted controller.

Trust comes from the existing owner SSH publication boundary and root-owned
storage, not from candidate JSON or hashes alone. Never import candidate tools.
"""
from __future__ import annotations
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import subprocess
import tarfile
import tempfile

ROOT = Path('/opt/gitee-ci/frontend-reuse')
SCHEMA = 'gitee-local-frontend-execution/v1'
STEPS = ('lint:src', 'typecheck:strict', 'test', 'build')
LOGS = tuple(s.replace(':', '-') + '.log' for s in STEPS)
FILES = ('attestation.json', 'build.tar.gz', *LOGS)
LIMIT = 64 * 1024 * 1024
IDENTITY = ('repository', 'source_branch', 'target_branch', 'head_sha', 'base_sha', 'pr_number')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True).strip()


def identity_key(identity):
    from scripts.ci.gitee_pr_identity import valid_branch
    if (identity.get('repository') != 'leegege/sce-product-odoo'
            or identity.get('target_branch') != 'main'
            or not valid_branch(identity.get('source_branch'))
            or type(identity.get('pr_number')) is not int or identity['pr_number'] <= 0
            or any(not re.fullmatch('[0-9a-f]{40}', str(identity.get(k, ''))) for k in ('head_sha', 'base_sha'))
            or identity['head_sha'] == identity['base_sha']):
        raise ValueError('reuse_identity')
    return sha(canonical({k: identity[k] for k in IDENTITY}))


def environment():
    from scripts.ci.gitee_formal_executor import RESOURCE_ENV
    return {'PATH': '/tools:/usr/bin:/bin', 'HOME': '/tmp', 'ENV': 'test', 'CI': '1',
            'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null',
            'PYTHONDONTWRITEBYTECODE': '1', 'XDG_CACHE_HOME': '/tmp/cache', **RESOURCE_ENV}


def policy_hashes():
    from scripts.ci.gitee_gate_plan import INPUTS
    root = Path(__file__).resolve().parents[2]
    return {p: sha((root / p).read_bytes()) for p in INPUTS}


def expected(repo, identity):
    from scripts.ops.gitee_frontend_cache import inputs, key
    from scripts.ci.gitee_formal_executor import recipes
    identity_key(identity)
    if git(repo, 'rev-parse', 'HEAD') != identity['head_sha']:
        raise ValueError('reuse_checkout_identity')
    return {'schema': SCHEMA, 'identity': {k: identity[k] for k in IDENTITY},
            'source_tree': git(repo, 'rev-parse', 'HEAD^{tree}'),
            'dependency_key': key(inputs(repo)), 'policy_hashes': policy_hashes(),
            'commands': [cmd for cmd, _ in recipes('frontend_release_gate', 'standard', identity['base_sha'])[1:]],
            'environment': environment(),
            'platform': [platform.system(), platform.machine(), platform.python_version()],
            'issuer': 'owner-ssh-governed-local-execution'}


def archive_files(data):
    """Read bounded regular files without extraction; reject links/escape/duplicates."""
    if len(data) > LIMIT:
        raise ValueError('reuse_archive_size')
    result = {}; total = 0
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as tf:
        for m in tf:
            name = PurePosixPath(m.name)
            if (not m.isfile() or name.is_absolute() or '..' in name.parts
                    or str(name) != m.name or not name.parts or '\\' in m.name
                    or m.name in result or len(result) >= 10000):
                raise ValueError('reuse_archive_member')
            total += m.size
            if m.size < 0 or total > LIMIT:
                raise ValueError('reuse_archive_expansion')
            result[m.name] = tf.extractfile(m).read()
    return result


def pack(files):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode='w:gz') as tf:
        for name, data in sorted(files.items()):
            m = tarfile.TarInfo(name); m.size = len(data); m.mode = 0o644
            tf.addfile(m, io.BytesIO(data))
    return stream.getvalue()


def build_archive(dist, work):
    files = {}
    relative = dist.relative_to(work)
    for p in (work, *(work.joinpath(*relative.parts[:i]) for i in range(1, len(relative.parts)+1))):
        if p.is_symlink() or not p.is_dir():
            raise ValueError('reuse_build_parent')
    if dist.is_symlink() or not dist.is_dir():
        raise ValueError('reuse_build_missing')
    total = 0
    for index, p in enumerate(dist.rglob('*')):
        if index >= 10000:
            raise ValueError('reuse_build_file_count')
        if p.is_symlink() or (not p.is_file() and not p.is_dir()):
            raise ValueError('reuse_build_special_file')
        if p.is_file():
            total += p.stat().st_size
            if total > LIMIT or len(files) >= 10000:
                raise ValueError('reuse_build_size')
            with p.open('rb') as f:
                data = f.read(LIMIT+1)
            if len(data) != p.stat().st_size or len(data) > LIMIT:
                raise ValueError('reuse_build_size_changed')
            files[p.relative_to(dist).as_posix()] = data
    if not files.get('index.html'):
        raise ValueError('reuse_build_empty')
    data = pack(files)
    archive_files(data)
    return data


def validate(files, want=None):
    from scripts.ci.gitee_formal_executor import nonzero_tests
    if set(files) != set(FILES) or any(len(v) > LIMIT for v in files.values()):
        raise ValueError('reuse_file_set')
    if len(files['attestation.json']) > 1024 * 1024:
        raise ValueError('reuse_attestation_size')
    receipt = json.loads(files['attestation.json'])
    identity_key(receipt['identity'])
    if want is not None and any(receipt.get(k) != v for k, v in want.items()):
        raise ValueError('reuse_context_mismatch')
    if (receipt.get('schema') != SCHEMA or receipt.get('status') != 'passed'
            or receipt.get('issuer') != 'owner-ssh-governed-local-execution'
            or receipt.get('policy_hashes') != policy_hashes()):
        raise ValueError('reuse_untrusted_policy_or_status')
    if receipt.get('steps') != [{'step': s, 'exit_code': 0} for s in STEPS]:
        raise ValueError('reuse_incomplete_steps')
    if receipt.get('log_hashes') != {name: sha(files[name]) for name in LOGS}:
        raise ValueError('reuse_log_digest')
    count = nonzero_tests(files['test.log'].decode('utf-8'))
    if type(receipt.get('tests')) is not int or receipt['tests'] != count:
        raise ValueError('reuse_test_count')
    artifact = archive_files(files['build.tar.gz'])
    if not artifact.get('index.html') or receipt.get('artifact') != {
            'sha256': sha(files['build.tar.gz']), 'files': {n: sha(b) for n, b in artifact.items()}}:
        raise ValueError('reuse_artifact_digest')
    if not re.fullmatch('[0-9a-f]{64}', str(receipt.get('dependency_archive_sha256', ''))):
        raise ValueError('reuse_dependency_archive')
    return receipt


def seal(work, attempt, result, identity):
    """Called only by the controller after all actual subprocesses completed."""
    if result.get('status') != 'passed' or [s['step'] for s in result['steps']] != list(STEPS):
        raise ValueError('reuse_execution_incomplete')
    if any(s['exit_code'] != 0 for s in result['steps']):
        raise ValueError('reuse_execution_failed')
    # git archive has no .git; the producer binds the independently checked tree.
    receipt = dict(identity)
    receipt.update(status='passed', steps=[{'step': s, 'exit_code': 0} for s in STEPS],
                   dependency_archive_sha256=result['archive_sha256'],
                   tests=result['steps'][2]['python_tests'])
    files = {name: (attempt / name).read_bytes() for name in LOGS}
    files['build.tar.gz'] = build_archive(work / 'frontend/apps/web/dist', work)
    artifact = archive_files(files['build.tar.gz'])
    receipt.update(log_hashes={n: sha(files[n]) for n in LOGS},
                   artifact={'sha256': sha(files['build.tar.gz']), 'files': {n: sha(b) for n, b in artifact.items()}})
    files['attestation.json'] = canonical(receipt)
    validate(files, identity)
    (attempt / 'reuse-bundle.tar.gz').write_bytes(pack(files))


def trusted(path):
    info = path.lstat()
    if path.is_symlink() or info.st_uid != 0 or info.st_mode & 0o022:
        raise ValueError('reuse_storage_untrusted')


def read_files(folder):
    for p in (folder, *folder.parents):
        trusted(p)
    if {p.name for p in folder.iterdir()} != set(FILES):
        raise ValueError('reuse_storage_files')
    result = {}
    for name in FILES:
        p = folder / name; trusted(p)
        if not p.is_file() or p.stat().st_size > LIMIT:
            raise ValueError('reuse_storage_size')
        result[name] = p.read_bytes()
    return result


def install(data, expected_digest, root=ROOT):
    if os.geteuid() != 0 or sha(data) != expected_digest:
        raise ValueError('reuse_publisher_or_digest')
    files = archive_files(data); receipt = validate(files)
    # Validate against the active installed controller before publication, too.
    for parent in (root, *root.parents):
        if parent.exists() or parent.is_symlink(): trusted(parent)
    if not root.exists():
        root.mkdir(mode=0o755, parents=True); root.chmod(0o755)
    target = root / identity_key(receipt['identity'])
    if target.exists() or target.is_symlink():
        if read_files(target) != files:
            raise ValueError('reuse_existing_conflict')
        return {'status': 'already_installed', 'key': target.name}
    with tempfile.TemporaryDirectory(prefix='.publish-', dir=root) as tmp:
        folder = Path(tmp) / 'sealed'; folder.mkdir(mode=0o755); folder.chmod(0o755)
        for name, body in files.items():
            with (folder / name).open('xb') as f:
                f.write(body); f.flush(); os.fsync(f.fileno())
            (folder / name).chmod(0o644)
        os.rename(folder, target)
        fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(fd)
        finally: os.close(fd)
    if read_files(target) != files:
        raise ValueError('reuse_install_readback')
    return {'status': 'installed', 'key': target.name, 'bundle_sha256': expected_digest,
            'identity': receipt['identity'], 'tests': receipt['tests'], 'services_changed': False}


def consume(repo, identity, root=ROOT):
    """No candidate can turn a cache miss or invalid receipt into success."""
    try:
        want = expected(repo, identity)
        files = read_files(root / identity_key(identity))
        receipt = validate(files, want)
        return {'status': 'verified_local_execution', 'tests': receipt['tests'],
                'attestation_sha256': sha(files['attestation.json']),
                'artifact_sha256': receipt['artifact']['sha256'], 'key': identity_key(identity)}
    except FileNotFoundError:
        return {'status': 'fallback', 'reason': 'receipt_missing'}
    except (OSError, ValueError, KeyError, TypeError, tarfile.TarError, UnicodeError, subprocess.SubprocessError):
        return {'status': 'fallback', 'reason': 'receipt_invalid_or_stale'}
