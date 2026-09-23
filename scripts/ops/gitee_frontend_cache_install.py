"""Append-only installation of reviewed public frontend dependencies, never services."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile

HOST='root@1.95.2.123'
ROOT=Path('/opt/gitee-ci/frontend')
LIMIT=200000000


def digest(data):return hashlib.sha256(data).hexdigest()
def key(inputs):return digest(json.dumps(inputs,sort_keys=True,separators=(',',':')).encode())


def trusted_parent(p):
    if p.is_symlink() or (p.exists() and (p.stat().st_uid!=0 or p.stat().st_mode&0o022)):
        raise ValueError('untrusted_install_parent')


def install(manifest,data,expected,root=ROOT):
    if os.geteuid()!=0:raise ValueError('root_required')
    if digest(data)!=expected or manifest.get('archive_sha256')!=expected:raise ValueError('archive_digest')
    if manifest.get('status')!='prepared' or len(data)>LIMIT:raise ValueError('invalid_bundle')
    k=key(manifest['dependency_inputs'])
    if manifest.get('dependency_key')!=k:raise ValueError('input_digest')
    target=root/k
    for p in [root,*root.parents]:
        trusted_parent(p)
    root.mkdir(mode=0o755,parents=True,exist_ok=True)
    metadata=json.dumps(manifest,sort_keys=True,separators=(',',':')).encode()
    if target.exists() or target.is_symlink():
        if target.is_symlink():raise ValueError('existing_symlink')
        for f in [target,target/'manifest.json',target/'dependencies.tar.gz']:trusted_parent(f)
        if (target/'manifest.json').read_bytes()!=metadata or digest((target/'dependencies.tar.gz').read_bytes())!=expected:
            raise ValueError('existing_cache_conflict')
        return {'status':'already_installed','dependency_key':k,'archive_sha256':expected}
    with tempfile.TemporaryDirectory(prefix='.prepare-',dir=root) as tmp:
        tmp=Path(tmp);staged=tmp/'cache';staged.mkdir(mode=0o755)
        for name,content in [('manifest.json',metadata),('dependencies.tar.gz',data)]:
            with (staged/name).open('xb') as f:f.write(content);f.flush();os.fsync(f.fileno())
            (staged/name).chmod(0o644)
        # No archive member is ever extracted or executed by this root installer.
        os.rename(staged,target)
    assert digest((target/'dependencies.tar.gz').read_bytes())==expected
    return {'status':'installed','dependency_key':k,'archive_sha256':expected,
            'services_changed':False,'recovery':'append-only cache; previous caches and service config unchanged'}


def receive(expected):
    line=sys.stdin.buffer.readline(100000)
    if not line.endswith(b'\n'):raise ValueError('metadata_frame')
    manifest=json.loads(line);data=sys.stdin.buffer.read(LIMIT+1)
    print(json.dumps(install(manifest,data,expected),sort_keys=True))


def main():
    p=argparse.ArgumentParser();p.add_argument('--prepared',required=True);p.add_argument('--archive-sha256',required=True)
    p.add_argument('--expected-head',required=True);p.add_argument('--apply',action='store_true');p.add_argument('--confirm',default='');a=p.parse_args()
    if not re.fullmatch('[0-9a-f]{64}',a.archive_sha256):raise ValueError('full_archive_digest_required')
    repo=Path(__file__).resolve().parents[2];prepared=Path(a.prepared).resolve()
    if not prepared.is_relative_to((repo/'artifacts/gitee-temporary-integration').resolve()):raise ValueError('scope')
    m=json.loads((prepared/'manifest.json').read_text());m.pop('entries',None)
    data=(prepared/'dependencies.tar.gz').read_bytes()
    if digest(data)!=a.archive_sha256 or m.get('archive_sha256')!=a.archive_sha256:raise ValueError('archive_mismatch')
    from scripts.ops.gitee_frontend_cache import inputs
    if inputs(repo)!=m['dependency_inputs']:raise ValueError('candidate_dependency_drift')
    result={'status':'preview','writes':0,'host':HOST,'dependency_key':m['dependency_key'],'archive_sha256':a.archive_sha256,'bytes':len(data)}
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
    if head!=a.expected_head:raise ValueError('source_head_drift')
    result['source_sha']=head
    if not a.apply:print(json.dumps(result));return
    if subprocess.check_output(['git','status','--porcelain'],cwd=repo,text=True).strip():raise ValueError('clean_source_required')
    if a.confirm!='INSTALL_REVIEWED_FRONTEND_CACHE':raise ValueError('confirmation')
    source=Path(__file__).read_text().rsplit("\nif __name__=='__main__':",1)[0]
    command='python3 -c '+shlex.quote(source+'\nreceive('+repr(a.archive_sha256)+')')
    payload=json.dumps(m,separators=(',',':')).encode()+b'\n'+data
    try:r=subprocess.run(['ssh','-o','BatchMode=yes',HOST,command],input=payload,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=300)
    except subprocess.TimeoutExpired:raise RuntimeError('uncertain transfer; inspect exact cache before retry') from None
    if r.returncode:raise RuntimeError('cache transfer failed; inspect exact target; services unchanged')
    print(r.stdout.decode())

if __name__=='__main__':main()
