"""Verify reviewed CI-only evidence and current server state before candidate Push."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]


def verify_receipt(data, head, main):
    if data.get('head') != head or data.get('main') != main:
        raise ValueError('evidence candidate identity mismatch')
    age = time.time() - data.get('observed_at', 0)
    if not 0 <= age <= 3600:
        raise ValueError('platform observation expired')
    required = {'repository': 'leegege/sce-product-odoo', 'hook_id': 2106026,
                'events': ['push', 'pull_request'], 'active': True,
                'platform_mirrors': [], 'gitee_go_enabled': False,
                'signing_secret_rotated': True}
    if data.get('platform') != required:
        raise ValueError('platform automation evidence incomplete')
    if data.get('public_scope_authorized') is not True or not data.get('evidence_files'):
        raise ValueError('public scope evidence required')
    for item in data['evidence_files']:
        path = (ROOT / item['path']).resolve()
        # Evidence lives in the registered artifacts symlink, never credential metadata.
        if not path.is_relative_to((ROOT / 'artifacts/gitee-temporary-integration').resolve()):
            raise ValueError('unregistered evidence path')
        if hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
            raise ValueError('evidence file drift')


def live_state(head):
    from scripts.ops.gitee_ci_incremental_update import Update, MODULES, INSTALL, ENVS, UNIT
    import scripts.ops.gitee_ci_incremental_update as module
    source = Path(module.__file__).read_text().rsplit("\nif __name__ == '__main__':", 1)[0]
    source += '''
u=Update()
u.verify_isolation()
assert u.run('systemctl','show','gitee-to-github-mirror.service','--property=MainPID','--value')=='0'
for unit in UNITS:
    assert u.run('systemctl','show',unit,'--property=ActiveState','--value')=='active'
for name in ENVS:
    assert env_update(u.path(name).read_bytes(),worker=name==ENVS[1])==u.path(name).read_bytes()
assert unit_update(u.path(UNIT).read_bytes())==u.path(UNIT).read_bytes()
worker=u.path(ENVS[1]).read_text()
assert any(line.startswith('GIT_SSH_COMMAND=') and '/etc/gitee-ci/' in line for line in worker.splitlines())
assert u.path('/usr/bin/bwrap').exists()
print(json.dumps({p:u.snapshot(p) for p in [*(INSTALL+n for n in MODULES),*ENVS,UNIT,'/etc/apparmor.d/bwrap-userns-restrict']}))
'''
    result = subprocess.run(['ssh', '-o', 'BatchMode=yes', module.HOST, 'python3', '-'],
                            input=source, text=True, capture_output=True, timeout=60)
    if result.returncode:
        raise ValueError('online isolation/configuration check failed; details withheld')
    state = json.loads(result.stdout)
    for name in MODULES:
        content = subprocess.check_output(['git', 'show', head + ':scripts/ci/' + name], cwd=ROOT)
        if state[INSTALL+name]['sha256'] != hashlib.sha256(content).hexdigest():
            raise ValueError('installed executor differs from candidate')
    return state


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--head', required=True); p.add_argument('--main', required=True)
    p.add_argument('--receipt', required=True); p.add_argument('--receipt-sha256', required=True)
    a = p.parse_args()
    raw = Path(a.receipt).read_bytes()
    if hashlib.sha256(raw).hexdigest() != a.receipt_sha256:
        raise ValueError('reviewed receipt digest mismatch')
    data = json.loads(raw)
    verify_receipt(data, a.head, a.main)
    if live_state(a.head) != data['online_state']:
        raise ValueError('online files changed after review')
    print('CI_ONLY_PLATFORM_EVIDENCE_VERIFIED')


if __name__ == '__main__':
    main()
