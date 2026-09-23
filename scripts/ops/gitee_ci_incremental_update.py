"""Bounded incremental update of the existing Gitee CI installation; plan by default."""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import tempfile

HOST = 'root@1.95.2.123'
INSTALL = '/opt/gitee-ci/sce-product-odoo/'
MODULES = ('gitee_webhook_ci.py', 'gitee_ci_acceptance.py', 'gitee_ci_acceptance_check.py')
ENVS = ('/etc/gitee-ci/sce-product-odoo-receiver.env', '/etc/gitee-ci/sce-product-odoo-worker.env')
UNIT = '/etc/systemd/system/gitee-ci-worker.service'
UNITS = ('gitee-webhook-ci.service','gitee-ci-worker.service')
CREDENTIALS = ('/etc/gitee-ci/id_ed25519','/etc/gitee-ci/id_ed25519.pub','/etc/gitee-ci/known_hosts')
PACKAGE = 'bubblewrap=0.9.0-1ubuntu0.3'
DB = '/var/lib/gitee-ci/jobs.sqlite3'


def digest(data): return hashlib.sha256(data).hexdigest()
def canonical(value): return json.dumps(value,sort_keys=True,separators=(',',':')).encode()


def env_update(data, worker=False):
    lines=data.splitlines(keepends=True)
    if sum(line.startswith(b'GITEE_CI_MODE=') for line in lines)>1: raise ValueError('duplicate mode setting')
    drop=(b'GITEE_CI_MODE=',b'GITEE_MIRROR_SOURCE_REPO=') if worker else (b'GITEE_CI_MODE=',)
    kept=b''.join(line for line in lines if not line.startswith(drop))
    if kept and not kept.endswith(b'\n'): kept+=b'\n'
    return kept+b'GITEE_CI_MODE=ci-only\n'


def unit_update(data):
    old=b'ReadWritePaths=/var/lib/gitee-ci /var/log/gitee-ci /var/lib/gitee-mirror/source.git'
    new=b'ReadWritePaths=/var/lib/gitee-ci /var/log/gitee-ci'
    if data.count(old)!=1 and data.count(new)!=1: raise ValueError('unexpected worker unit write paths')
    return data.replace(old,new)


class Update:
    def __init__(self, root=Path('/')):
        self.root=Path(root)

    def path(self, path):
        p=self.root/path.lstrip('/')
        if p.is_symlink(): raise ValueError('symlink target rejected')
        return p

    def run(self,*args):
        r=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=180,text=True)
        if r.returncode: raise RuntimeError('command failed: '+args[0]+' '+args[1])
        return r.stdout.strip()

    def snapshot(self,path):
        p=self.path(path)
        if not p.exists(): return None
        s=p.stat()
        return {'sha256':digest(p.read_bytes()),'mode':s.st_mode&0o777,'uid':s.st_uid,'gid':s.st_gid}

    def desired(self,payload):
        if not re.fullmatch('[0-9a-f]{40}',payload.get('source_sha','')): raise ValueError('full source SHA required')
        if set(payload.get('modules',{}))!=set(MODULES): raise ValueError('module allowlist mismatch')
        changes={}
        for name,item in payload['modules'].items():
            data=base64.b64decode(item['content'],validate=True)
            if digest(data)!=item['sha256']: raise ValueError('module digest mismatch')
            changes[INSTALL+name]=data
        for index,name in enumerate(ENVS): changes[name]=env_update(self.path(name).read_bytes(),worker=index==1)
        changes[UNIT]=unit_update(self.path(UNIT).read_bytes())
        return changes

    def active_jobs(self):
        with sqlite3.connect('file:'+str(self.path(DB))+'?mode=ro',uri=True) as db:
            tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            total=0
            for name in ('jobs','ci_acceptance_jobs'):
                if name in tables: total+=db.execute(f"SELECT count(*) FROM {name} WHERE status IN ('pending','running')").fetchone()[0]
            return total

    def plan(self,payload):
        desired=self.desired(payload)
        for f in CREDENTIALS:
            if self.snapshot(f) is None: raise ValueError('registered credential missing')
        plan={'source_sha':payload['source_sha'],'host':HOST,'package':PACKAGE,
              'files':{f:{'before':self.snapshot(f),'after_sha256':digest(v)} for f,v in desired.items()},
              'credentials':'preserve bytes/mode/owner; values excluded',
              'credential_state_digest':digest(canonical({f:self.snapshot(f) for f in CREDENTIALS})),
              'updater_sha256':payload.get('updater_sha256','unit-test'),
              'active_jobs':self.active_jobs(),
              'bwrap_present':self.path('/usr/bin/bwrap').exists(),
              'services':{u:self.run('systemctl','show',u,'--property=ActiveState','--value') for u in UNITS},
              'isolation_required':'mirror timer and service inactive; platform isolation separately approved',
              'writes':0}
        plan['plan_sha256']=digest(canonical(plan))
        return plan

    def verify_isolation(self):
        for unit in ('gitee-to-github-mirror.timer','gitee-to-github-mirror.service'):
            if self.run('systemctl','show',unit,'--property=ActiveState','--value') not in ('inactive','failed'):
                raise ValueError('reverse mirror is not isolated')
        if self.run('systemctl','show','gitee-to-github-mirror.timer','--property=UnitFileState','--value') not in ('disabled','masked'):
            raise ValueError('mirror timer can restart')
        if self.active_jobs(): raise ValueError('active or queued CI jobs')

    def install_package(self):
        if not self.path('/usr/bin/bwrap').exists():
            # No source rewrite, dist-upgrade, key generation or unsandboxed fallback.
            self.run('apt-get','install','--yes','--no-install-recommends',PACKAGE)
        self.run('/usr/bin/bwrap','--version')

    def probe(self):
        # Same service hardening/user as worker via a bounded transient probe, not a runner.
        self.run('systemd-run','--quiet','--wait','--pipe','--collect',
                 '--unit=gitee-ci-isolation-probe','--uid=gitee-ci','--gid=gitee-ci',
                 '-p','RuntimeMaxSec=30','-p','TimeoutStopSec=5','-p','KillMode=control-group',
                 '-p','NoNewPrivileges=yes','-p','PrivateTmp=yes','-p','ProtectSystem=strict',
                 '-p','ProtectHome=yes','/usr/bin/bwrap','--unshare-all','--die-with-parent',
                 '--ro-bind','/usr','/usr','--symlink','usr/bin','/bin','--symlink','usr/lib','/lib',
                 '--symlink','usr/lib64','/lib64','--proc','/proc','--dev','/dev','--tmpfs','/tmp',
                 '/usr/bin/python3','-c',
                 "import os,socket; assert not os.path.exists('/etc/gitee-ci'); s=socket.socket(); s.settimeout(2); assert s.connect_ex(('1.1.1.1',443)) != 0")

    def atomic_write(self,path,data,metadata=None):
        target=self.path(path)
        with tempfile.NamedTemporaryFile(dir=target.parent,delete=False) as f:
            tmp=Path(f.name);f.write(data);f.flush();os.fsync(f.fileno())
        try:
            os.chmod(tmp,metadata['mode'] if metadata else 0o644)
            if metadata: os.chown(tmp,metadata['uid'],metadata['gid'])
            os.replace(tmp,target)
        finally:
            tmp.unlink(missing_ok=True)

    def backup(self,desired):
        parent=self.path('/var/lib/gitee-ci/update-backups');parent.mkdir(mode=0o700,exist_ok=True)
        folder=Path(tempfile.mkdtemp(prefix='incremental-',dir=parent));os.chmod(folder,0o700)
        manifest={}
        for i,path in enumerate(desired):
            meta=self.snapshot(path);manifest[path]={'metadata':meta,'file':str(i)}
            if meta:
                data=self.path(path).read_bytes();dest=folder/str(i);dest.write_bytes(data);dest.chmod(0o600)
                if digest(dest.read_bytes())!=meta['sha256']: raise ValueError('backup verification failed')
        with sqlite3.connect('file:'+str(self.path(DB))+'?mode=ro',uri=True) as src, sqlite3.connect(folder/'queue.sqlite3') as dst:
            src.backup(dst)
            if dst.execute('PRAGMA integrity_check').fetchone()[0]!='ok': raise ValueError('database backup integrity')
        (folder/'queue.sqlite3').chmod(0o600)
        (folder/'manifest.json').write_bytes(canonical(manifest));(folder/'manifest.json').chmod(0o600)
        return folder,manifest

    def verify_plan_inputs(self,plan):
        for path,item in plan["files"].items():
            if self.snapshot(path)!=item["before"]: raise ValueError("file changed after plan")

    def restore(self,folder,manifest,desired):
        # Do not start legacy services or re-enable automation during recovery.
        for unit in UNITS: self.run('systemctl','stop',unit)
        for path,entry in manifest.items():
            now=self.snapshot(path)
            if now!=entry['metadata'] and (now is None or now['sha256']!=digest(desired[path])):
                raise ValueError('unowned change during recovery; do not overwrite')
        for path,entry in manifest.items():
            if entry['metadata']:
                data=(folder/entry['file']).read_bytes()
                if digest(data)!=entry['metadata']['sha256']: raise ValueError('corrupt backup; recovery stopped')
                self.atomic_write(path,data,entry['metadata'])
            else: self.path(path).unlink(missing_ok=True)
        self.run('systemctl','daemon-reload')
        for path,entry in manifest.items():
            if self.snapshot(path)!=entry['metadata']: raise ValueError('restore readback mismatch')

    def apply(self,payload,expected_plan,confirm):
        plan=self.plan(payload)
        if confirm!='APPLY_REVIEWED_CI_INCREMENTAL_UPDATE' or plan['plan_sha256']!=expected_plan:
            raise ValueError('exact reviewed plan and confirmation required')
        self.verify_isolation()
        original_credentials={f:self.snapshot(f) for f in CREDENTIALS}
        desired=self.desired(payload);folder=None;manifest=None
        try:
            # Receiver first closes admission; do not stop the unrelated GitHub runner.
            for unit in UNITS: self.run('systemctl','stop',unit)
            if self.active_jobs(): raise ValueError('job arrived during admission shutdown')
            self.verify_plan_inputs(plan)
            folder,manifest=self.backup(desired)
            self.install_package();self.probe()
            self.verify_plan_inputs(plan)
            for path,data in desired.items(): self.atomic_write(path,data,plan['files'][path]['before'])
            if any(self.snapshot(f)!=v for f,v in original_credentials.items()): raise ValueError('credential drift')
            for path,data in desired.items():
                if self.path(path).read_bytes()!=data: raise ValueError('installed content mismatch')
            self.run('systemctl','daemon-reload')
            for unit in reversed(UNITS): self.run('systemctl','start',unit)
            for unit in UNITS:
                if self.run('systemctl','show',unit,'--property=ActiveState','--value')!='active': raise ValueError('service not active')
            if any(self.snapshot(f)!=v for f,v in original_credentials.items()): raise ValueError('credential drift after start')
            return {'status':'installed','source_sha':payload['source_sha'],'backup':str(folder),'credentials_unchanged':True,'online_ci_acceptance':'not_run'}
        except Exception:
            if manifest is not None:
                self.restore(folder,manifest,desired)
            else:
                for unit in UNITS: self.run('systemctl','stop',unit)
            # Package installation is intentionally not auto-purged; report/review dependencies.
            raise RuntimeError('update failed; services remain stopped; backup='+str(folder)+'; inspect package state before recovery') from None


def entry(payload,apply=False,expected_plan='',confirm=''):
    updater=Update()
    if apply and os.geteuid()!=0: raise ValueError('root required for reviewed update')
    return updater.apply(payload,expected_plan,confirm) if apply else updater.plan(payload)


def main():
    p=argparse.ArgumentParser();p.add_argument('--expected-head',required=True);p.add_argument('--apply',action='store_true');p.add_argument('--plan-sha256',default='');p.add_argument('--confirm',default='');a=p.parse_args()
    root=Path(__file__).resolve().parents[2]
    def git(*args): return subprocess.check_output(['git',*args],cwd=root,text=True).strip()
    if not re.fullmatch('(feature|fix|refactor|audit|release|codex)/.+',git('branch','--show-current')): raise ValueError('controller branch')
    if git('rev-parse','HEAD')!=a.expected_head: raise ValueError('source HEAD drift')
    if a.apply and git('status','--porcelain'): raise ValueError('clean source required')
    payload={'source_sha':a.expected_head,'updater_sha256':digest(Path(__file__).read_bytes()),'modules':{}}
    for name in MODULES:
        data=subprocess.check_output(['git','show',a.expected_head+':scripts/ci/'+name],cwd=root)
        if a.apply and (root/'scripts/ci'/name).read_bytes()!=data: raise ValueError('module dirty')
        payload['modules'][name]={'content':base64.b64encode(data).decode(),'sha256':digest(data)}
    source=Path(__file__).read_text().rsplit("\nif __name__ == '__main__':",1)[0]
    invocation='\nprint(json.dumps(entry('+repr(payload)+','+repr(a.apply)+','+repr(a.plan_sha256)+','+repr(a.confirm)+'),sort_keys=True))\n'
    try:
        r=subprocess.run(['ssh','-o','BatchMode=yes',HOST,'python3','-'],input=source+invocation,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=900)
    except subprocess.TimeoutExpired:
        print(json.dumps({'status':'uncertain' if a.apply else 'failed','retry_allowed':False,'reason':'transport timeout; inspect remote before recovery'}))
        raise SystemExit(3) from None
    if r.returncode:
        print(json.dumps({'status':'uncertain' if a.apply else 'failed','retry_allowed':False,'reason':'remote invocation failed; inspect backup and services before recovery'}))
        raise SystemExit(3)
    print(r.stdout.strip())

if __name__ == '__main__':
    main()
