"""Rotate only the existing receiver secret over SSH stdin; never print its value."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess


def replacement(data, secret):
    if not re.fullmatch(r'[0-9a-f]{64}', secret):
        raise ValueError('expected generated 256-bit hex secret')
    lines = data.splitlines(keepends=True)
    if sum(line.startswith('GITEE_WEBHOOK_SECRET=') for line in lines) != 1:
        raise ValueError('unique existing receiver secret required')
    return ''.join('GITEE_WEBHOOK_SECRET=' + secret + '\n'
                   if line.startswith('GITEE_WEBHOOK_SECRET=') else line for line in lines)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--secret-file', required=True)
    p.add_argument('--expected-env-sha256', required=True)
    p.add_argument('--confirm', required=True)
    args = p.parse_args()
    if args.confirm != 'ROTATE_EXISTING_WEBHOOK_SIGNING_SECRET':
        raise ValueError('exact rotation confirmation required')
    path = Path(args.secret_file)
    if path.is_symlink() or path.stat().st_mode & 0o077:
        raise ValueError('private regular secret file required')
    secret = path.read_text().strip()
    replacement('GITEE_WEBHOOK_SECRET=old\n', secret)
    if not re.fullmatch('[0-9a-f]{64}', args.expected_env_sha256):
        raise ValueError('exact receiver env hash required')
    source = Path(__file__).read_text().split('\ndef main():', 1)[0]
    source += '\nsecret=' + repr(secret) + '\nexpected=' + repr(args.expected_env_sha256) + '\n'
    source += '''
import tempfile
p=Path('/etc/gitee-ci/sce-product-odoo-receiver.env')
assert not p.is_symlink()
old=p.read_bytes(); meta=p.stat()
assert hashlib.sha256(old).hexdigest()==expected, 'receiver env drift'
new=replacement(old.decode(),secret).encode()
assert b'GITEE_CI_MODE=ci-only' in new, 'CI-only required'
def run(*args):
    r=subprocess.run(args,capture_output=True,timeout=30)
    if r.returncode: raise RuntimeError('service operation failed; inspect receiver')
run('systemctl','stop','gitee-webhook-ci.service')
folder=Path(tempfile.mkdtemp(prefix='secret-rotation-',dir='/var/lib/gitee-ci/update-backups'))
folder.chmod(0o700)
backup=folder/'receiver.env'; backup.write_bytes(old); backup.chmod(0o600)
assert backup.read_bytes()==old
assert p.read_bytes()==old, 'receiver env drift after stop'
fd,name=tempfile.mkstemp(dir=p.parent)
with os.fdopen(fd,'wb') as f:
    f.write(new); f.flush(); os.fsync(f.fileno())
os.chmod(name,meta.st_mode&0o777); os.chown(name,meta.st_uid,meta.st_gid)
os.replace(name,p)
assert p.read_bytes()==new
run('systemctl','start','gitee-webhook-ci.service')
run('systemctl','is-active','--quiet','gitee-webhook-ci.service')
print(json.dumps({'rotation':'complete','backup':str(folder),'receiver':'active','secret_value':'omitted'}))
'''
    try:
        r = subprocess.run(['ssh', '-o', 'BatchMode=yes', 'root@1.95.2.123', 'python3', '-'],
                           input=source, text=True, capture_output=True, timeout=120)
    except subprocess.TimeoutExpired:
        print(json.dumps({'rotation': 'uncertain', 'retry_allowed': False,
                          'reason': 'transport timeout; inspect receiver and backup before recovery'}))
        raise SystemExit(3) from None
    if r.returncode:
        print(json.dumps({'rotation': 'uncertain', 'retry_allowed': False,
                          'reason': 'inspect receiver state and backup before recovery'}))
        raise SystemExit(2)
    print(r.stdout.strip())


if __name__ == '__main__':
    main()
