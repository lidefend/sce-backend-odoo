#!/usr/bin/env python3
"""Local acceptance source custody; export Git objects, never a mutable worktree.

This is a local content-verified artifact, not a production signing authority.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[2]
MOUNTS = {'addons':'/mnt/source-addons', 'demo_addons':'/mnt/demo-addons',
          'addons_external':'/mnt/addons_external', 'scripts':'/mnt/scripts', 'docs':'/mnt/docs',
          'VERSION':'/opt/sce-product/VERSION', 'config/odoo.conf.template':'/etc/odoo/odoo.conf.template',
          'scripts/render_odoo_conf.py':'/usr/local/bin/render_odoo_conf.py',
          'scripts/odoo-entrypoint.sh':'/usr/local/bin/odoo-entrypoint.sh'}
INPUTS = ('addons', 'demo_addons', 'addons_external', 'scripts', 'docs', 'VERSION', 'config')


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args])


def inventory(root, sha):
    if not re.fullmatch(r'[0-9a-f]{40}', sha):
        raise ValueError('full immutable source SHA required')
    if git(root, 'rev-parse', sha + '^{commit}').decode().strip() != sha:
        raise ValueError('source must be an exact commit')
    result = {}
    for row in git(root, 'ls-tree', '-r', '-z', sha, '--', *INPUTS).split(b'\0'):
        if not row:
            continue
        meta, name = row.split(b'\t', 1)
        mode, kind, oid = meta.decode().split()
        name = name.decode()
        if mode not in ('100644', '100755') or kind != 'blob':
            raise ValueError('artifact forbids symlinks and gitlinks: ' + name)
        if PurePosixPath(name).is_absolute() or '..' in PurePosixPath(name).parts:
            raise ValueError('unsafe artifact path')
        result[name] = {'blob': oid, 'mode': mode}
    if not result or 'VERSION' not in result:
        raise ValueError('incomplete artifact source')
    return result


def store(root):
    common = Path(git(root, 'rev-parse', '--path-format=absolute', '--git-common-dir').decode().strip())
    return common / 'codex' / 'acceptance-artifacts'


def verify(root, sha):
    target = store(root) / sha
    if target.is_symlink():
        raise ValueError('artifact root must not be a symlink')
    expected = inventory(root, sha)
    manifest = json.loads((target / 'manifest.json').read_text())
    if manifest.get('source_sha') != sha or manifest.get('files') != expected:
        raise ValueError('artifact manifest differs from immutable Git authority')
    actual = set()
    for p in target.rglob('*'):
        if p.is_symlink():
            raise ValueError('artifact contains symlink')
        if p.is_file() and p != target / 'manifest.json':
            actual.add(p.relative_to(target).as_posix())
    if actual != set(expected):
        raise ValueError('artifact inventory differs')
    for name, entry in expected.items():
        p = target / name
        data = p.read_bytes()
        oid = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        if oid != entry['blob']:
            raise ValueError('artifact content changed: ' + name)
        mode = p.stat().st_mode
        if mode & 0o222 or bool(mode & 0o111) != (entry['mode'] == '100755'):
            raise ValueError('artifact permissions changed: ' + name)
    digest = hashlib.sha256(json.dumps(expected, sort_keys=True).encode()).hexdigest()
    if manifest.get('artifact_digest') != digest:
        raise ValueError('artifact digest mismatch')
    return target, manifest


def build(root, sha):
    expected = inventory(root, sha)
    parent = store(root)
    parent.mkdir(parents=True, exist_ok=True)
    target = parent / sha
    if target.exists():
        return verify(root, sha)
    stage = Path(tempfile.mkdtemp(prefix='.build-', dir=parent))
    try:
        archive = git(root, 'archive', '--format=tar', sha, '--', *sorted({name.split('/')[0] for name in expected}))
        with tarfile.open(fileobj=io.BytesIO(archive)) as tf:
            for member in tf:
                if member.isdir():
                    continue
                if not member.isfile() or member.name not in expected:
                    raise ValueError('unexpected archive member')
                p = stage / member.name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(tf.extractfile(member).read())
                p.chmod(0o555 if expected[member.name]['mode'] == '100755' else 0o444)
        manifest = {'schema': 'acceptance.source_artifact.v1', 'artifact_kind': 'backend-source',
                    'source_sha': sha, 'files': expected,
                    'artifact_digest': hashlib.sha256(json.dumps(expected, sort_keys=True).encode()).hexdigest(),
                    'authority': 'local immutable Git objects; not production signature'}
        (stage / 'manifest.json').write_text(json.dumps(manifest, sort_keys=True, indent=2)+'\n')
        (stage / 'manifest.json').chmod(0o444)
        os.rename(stage, target)
        return verify(root, sha)
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def compose_override(root, sha):
    target, _ = verify(root, sha)
    volumes = []
    for source, destination in MOUNTS.items():
        if not (target / source).exists():
            raise ValueError('artifact mount source missing: ' + source)
        volumes.append({'type': 'bind', 'source': str(target / source),
                        'target': destination, 'read_only': True,
                        'bind': {'create_host_path': False}})
    output = store(root) / (sha + '.compose.json')
    data = json.dumps({'services': {'odoo': {'volumes': volumes}}}, sort_keys=True, indent=2)+'\n'
    if output.is_symlink():
        raise ValueError('compose receipt must not be a symlink')
    output.write_text(data)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['build', 'verify', 'path', 'compose'])
    parser.add_argument('--source-sha', required=True)
    args = parser.parse_args()
    if args.operation == 'compose':
        print(compose_override(ROOT, args.source_sha))
        return
    target, manifest = (build if args.operation == 'build' else verify)(ROOT, args.source_sha)
    print(str(target) if args.operation == 'path' else json.dumps({k:v for k,v in manifest.items() if k != 'files'}, sort_keys=True))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        raise SystemExit('[acceptance.artifact] DENY ' + str(exc)) from exc
