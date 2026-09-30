"""Run, seal and publish frontend evidence through the existing owner SSH trust.

There is deliberately no import-receipt option. --apply runs the verifier itself.
The remote command loads only the active root-owned installed controller.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import shlex
import subprocess

from scripts.ci.gitee_frontend_reuse import expected, git, sha, validate, archive_files
from scripts.ops.gitee_frontend_cache import verify

HOST = 'root@1.95.2.123'
REPO = Path(__file__).resolve().parents[2]


def assert_clean(repo, identity):
    if (git(repo, 'rev-parse', 'HEAD') != identity['head_sha']
            or git(repo, 'branch', '--show-current') != identity['source_branch']
            or git(repo, 'status', '--porcelain')):
        raise ValueError('reuse_clean_exact_candidate_required')
    subprocess.run(['git', '-C', str(repo), 'merge-base', '--is-ancestor',
                    identity['base_sha'], identity['head_sha']], check=True)


def remote_command(digest):
    if not re.fullmatch('[0-9a-f]{64}', digest): raise ValueError('reuse_bundle_digest')
    # Read only the non-secret formal-root setting; no environment file is
    # sourced and no candidate path or executable is accepted.
    program = """import pathlib,sys,re
p=pathlib.Path('/etc/gitee-ci/sce-product-odoo-worker.env')
values=[line.split('=',1)[1] for line in p.read_text().splitlines() if line.startswith('GITEE_FORMAL_ROOT=')]
assert len(values)==1 and re.fullmatch('/opt/gitee-ci/formal/[0-9a-f]{40}',values[0])
root=pathlib.Path(values[0])
for directory in [root,*root.parents]:
 s=directory.lstat();assert not directory.is_symlink() and s.st_uid==0 and not s.st_mode&0o022
for relative in ['scripts','scripts/ci','scripts/ops','scripts/ci/gitee_frontend_reuse.py']:
 q=root/relative;s=q.lstat();assert not q.is_symlink() and s.st_uid==0 and not s.st_mode&0o022
sys.path.insert(0,str(root))
from scripts.ci.gitee_frontend_reuse import install,LIMIT
import json
print(json.dumps(install(sys.stdin.buffer.read(LIMIT+1),sys.argv[1]),sort_keys=True))
"""
    return 'python3 -c ' + shlex.quote(program) + ' ' + shlex.quote(digest)


def publish(repo, prepared, node_archive, identity, *, apply=False):
    assert_clean(repo, identity)
    context = expected(repo, identity)
    if not apply:
        return {'status': 'planned', 'identity': context['identity'],
                'dependency_key': context['dependency_key'], 'writes': 0,
                'trust': 'owner SSH authenticated local runner; no arbitrary receipt import'}
    result = verify(repo, prepared, node_archive, reuse_context=context)
    assert_clean(repo, identity)
    if expected(repo, identity) != context:
        raise ValueError('reuse_input_drift_after_execution')
    if result['status'] != 'passed': raise ValueError('reuse_verification_failed')
    bundle = Path(prepared) / result['attempt'] / 'reuse-bundle.tar.gz'
    data = bundle.read_bytes(); validate(archive_files(data), context)
    # Authenticated owner publication is the trust boundary; hashes alone do
    # not establish provenance. Candidate processes have no SSH credentials.
    completed = subprocess.run(['ssh', '-o', 'BatchMode=yes', HOST, remote_command(sha(data))],
                               input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
    if completed.returncode:
        raise RuntimeError('reuse_install_failed_inspect_exact_key_before_retry')
    remote = json.loads(completed.stdout)
    if remote.get('status') not in ('installed', 'already_installed'):
        raise ValueError('reuse_install_receipt')
    return {'status': 'published', 'identity': context['identity'], 'verification': result,
            'bundle_sha256': sha(data), 'remote': remote}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--head', required=True); p.add_argument('--base', required=True)
    p.add_argument('--pr-number', type=int, required=True); p.add_argument('--prepared', required=True)
    p.add_argument('--node-archive', required=True); p.add_argument('--apply', action='store_true')
    p.add_argument('--confirm', default=''); a = p.parse_args()
    if a.apply and a.confirm != 'RUN_AND_PUBLISH_EXACT_FRONTEND_EVIDENCE':
        raise ValueError('reuse_publication_confirmation')
    identity = dict(repository='leegege/sce-product-odoo', source_branch=git(REPO, 'branch', '--show-current'),
                    target_branch='main', head_sha=a.head, base_sha=a.base, pr_number=a.pr_number)
    print(json.dumps(publish(REPO, Path(a.prepared), Path(a.node_archive), identity, apply=a.apply), sort_keys=True))


if __name__ == '__main__': main()
