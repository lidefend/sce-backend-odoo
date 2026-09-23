"""Prepare a lock-bound frontend dependency bundle without network or scripts.

Preparation is local, inside the existing external evidence root. This command
never installs a server cache or grants frontend check success.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import tarfile
import tempfile
import time
import uuid
from contextlib import contextmanager

PNPM_SHA = "24235772cc4ac82a62627cd47f834c72667a2ce87799a846ec4e8e555e2d4b8b"
NODE_SHA = "8071ae0fca095a272ad698a90c7061801a86fb6392ddb81e922b68a91a4374b9"
NODE_ARCHIVE_SHA = "325c0f1261e0c61bcae369a1274028e9cfb7ab7949c05512c5b1e630f7e80e12"


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''): h.update(block)
    return h.hexdigest()


def inputs(repo):
    root=Path(repo)/'frontend'
    names=['package.json','pnpm-lock.yaml','pnpm-workspace.yaml']
    workspace=(root/'pnpm-workspace.yaml').read_text()
    normalized=''.join(workspace.split()).replace('"','').replace("'",'')
    if normalized!='packages:-apps/*-packages/*':raise ValueError('unsupported_workspace_patterns')
    names += sorted(str(p.relative_to(root)) for group in ('apps','packages')
                    for p in (root/group).glob('*/package.json'))
    # Hook/patch/custom registry handling is deliberately unsupported, not ignored.
    for directory in [root.parent,root]+[ (root/n).parent for n in names if n.endswith('package.json') ]:
        for name in ('.npmrc','.pnpmfile.cjs','pnpmfile.cjs'):
            if (directory/name).exists(): raise ValueError('unsupported_install_configuration')
    if (root/'patches').exists(): raise ValueError('unsupported_patches')
    for name in names:
        f=root/name
        if not f.is_file() or f.is_symlink() or not f.resolve().is_relative_to(root.resolve()):
            raise ValueError('unsafe_dependency_input')
        if name.endswith('package.json'):
            obj=json.loads(f.read_text())
            if name=='package.json' and obj.get('packageManager')!='pnpm@9.12.3':
                raise ValueError('pnpm_version_mismatch')
            for field in ('dependencies','devDependencies','optionalDependencies','peerDependencies'):
                for value in obj.get(field,{}).values():
                    if not isinstance(value,str) or any(x in value for x in ('file:','link:','git:','git+','http:','https:')):
                        raise ValueError('unsupported_dependency_source')
            if any(k in obj.get('pnpm',{}) for k in ('patchedDependencies','neverBuiltDependencies','onlyBuiltDependencies')):
                raise ValueError('unsupported_pnpm_policy')
    lock=(root/'pnpm-lock.yaml').read_text()
    if re.search(r'(?:^|[\s{,])(?:tarball:|file:|git\+|patch_hash:|patchedDependencies:)',lock,re.MULTILINE):
        raise ValueError('unsupported_lock_source')
    return {'platform':'linux-x86_64','node_sha256':NODE_SHA,'pnpm_sha256':PNPM_SHA,
            'files':{'frontend/'+n:sha(root/n) for n in names}}


def key(manifest):
    return hashlib.sha256(json.dumps(manifest,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def extract_pnpm(archive,dest):
    if sha(archive)!=PNPM_SHA: raise ValueError('pnpm_archive_mismatch')
    with tarfile.open(archive,'r:gz') as tf:
        for m in tf.getmembers():
            rel=Path(m.name)
            if rel.is_absolute() or '..' in rel.parts or rel.parts[0]!='package' or not (m.isfile() or m.isdir()):
                raise ValueError('pnpm_archive_member_rejected')
        tf.extractall(dest,filter='data')


def prepare(repo,output,node_archive,pnpm_archive,store):
    repo=Path(repo).resolve();output=Path(output).resolve();store=Path(store).resolve()
    allowed=(repo/'artifacts/gitee-temporary-integration').resolve()
    if not output.is_relative_to(allowed) or output==allowed: raise ValueError('output_scope')
    if platform.system()!='Linux' or platform.machine()!='x86_64': raise ValueError('unsupported_platform')
    before=inputs(repo)
    if sha(node_archive)!=NODE_ARCHIVE_SHA: raise ValueError('node_archive_mismatch')
    if not store.is_dir(): raise ValueError('offline_store_missing')
    if output.exists(): raise ValueError('output_exists')
    output.mkdir(parents=True)
    receipt={'status':'failed','dependency_inputs':before,'dependency_key':key(before),
             'network':False,'install_scripts':False,'server_install':'not_run'}
    try:
        with tempfile.TemporaryDirectory(prefix='frontend-prepare-',dir=allowed) as tmp:
            tmp=Path(tmp);work=tmp/'work';work.mkdir();runtime=tmp/'runtime';runtime.mkdir()
            for name in before['files']:
                target=work/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(repo/name,target)
            extract_pnpm(pnpm_archive,runtime)
            with tarfile.open(node_archive,'r:xz') as tf:
                m=tf.getmember('node-v22.17.0-linux-x64/bin/node')
                if not m.isfile(): raise ValueError('node_member_rejected')
                (runtime/'node').write_bytes(tf.extractfile(m).read())
            if sha(runtime/'node')!=NODE_SHA: raise ValueError('node_binary_mismatch')
            (runtime/'node').chmod(0o755)
            # Store is read-only; cache writes go to the disposable work directory.
            cmd=['/usr/bin/bwrap','--unshare-all','--die-with-parent','--new-session',
                 '--ro-bind','/usr','/usr','--symlink','usr/bin','/bin','--symlink','usr/lib','/lib',
                 '--symlink','usr/lib64','/lib64','--proc','/proc','--dev','/dev','--tmpfs','/tmp',
                 '--bind',str(work),'/work','--ro-bind',str(runtime/'package'),'/pnpm',
                 '--ro-bind',str(runtime/'node'),'/usr/bin/node','--ro-bind',str(store),'/store/v3',
                 '--chdir','/work/frontend','node','/pnpm/bin/pnpm.cjs','install','--offline',
                 '--frozen-lockfile','--ignore-scripts','--store-dir','/store','--package-import-method','copy']
            env={'PATH':'/usr/bin:/bin','HOME':'/tmp','CI':'1','PNPM_HOME':'/tmp/pnpm',
                 'XDG_CONFIG_HOME':'/tmp/config','XDG_CACHE_HOME':'/tmp/cache'}
            with (output/'install.log').open('wb') as log:
                from scripts.ci.gitee_ci_acceptance import Executor
                r=Executor(output).command(cmd,work,log,lambda:False,time.monotonic()+600,env)
            if r: raise ValueError('offline_install_failed')
            if inputs(repo)!=before: raise ValueError('dependency_inputs_changed')
            # Only package-manager runtime and dependency directories enter bundle.
            roots=[work/'frontend/node_modules']
            roots += sorted(q for group in ('apps','packages') for q in (work/'frontend'/group).glob('*/node_modules'))
            if not roots[0].is_dir(): raise ValueError('missing_node_modules')
            entries={}
            for root in roots:
                for q in [root,*root.rglob('*')]:
                    name=str(q.relative_to(work));info=q.lstat()
                    if q.is_symlink():
                        target=os.readlink(q)
                        if Path(target).is_absolute() or not q.resolve().is_relative_to(work):
                            raise ValueError('dependency_link_escape')
                        entries[name]={'link':target}
                    elif q.is_file():entries[name]={'sha256':sha(q),'executable':bool(info.st_mode&0o111)}
                    elif not q.is_dir():raise ValueError('special_dependency_file')
            receipt.update(status='prepared',mounts=[str(q.relative_to(work)) for q in roots],entries=entries)
            with tarfile.open(output/'dependencies.tar.gz','w:gz',dereference=False) as tf:
                for root in roots:tf.add(root,arcname=str(root.relative_to(work)))
                tf.add(runtime/'package',arcname='pnpm')
            receipt['archive_sha256']=sha(output/'dependencies.tar.gz')
    finally:
        (output/'manifest.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    return {k:v for k,v in receipt.items() if k!='entries'}


@contextmanager
def attempt_receipt(prepared,result):
    folder=prepared/('attempt-'+uuid.uuid4().hex)
    folder.mkdir()
    result.update(attempt=folder.name,status='running',tool_sha256=sha(__file__))
    path=folder/'verification.json'
    path.write_text(json.dumps(result,indent=2)+'\n')
    try:
        yield folder
    except BaseException as exc:
        result['status']='timed_out' if isinstance(exc,subprocess.TimeoutExpired) or getattr(exc,'status',None)=='timed_out' else 'failed'
        result['failure_type']=type(exc).__name__
        raise
    finally:
        if result['status']=='running':result['status']='failed'
        result['log_hashes']={f.name:sha(f) for f in folder.glob('*.log')}
        path.write_text(json.dumps(result,indent=2)+'\n')


def verify(repo,prepared,node_archive):
    repo=Path(repo).resolve();prepared=Path(prepared).resolve()
    allowed=(repo/'artifacts/gitee-temporary-integration').resolve()
    if not prepared.is_relative_to(allowed):raise ValueError('evidence_scope')
    manifest=json.loads((prepared/'manifest.json').read_text())
    if manifest.get('status')!='prepared' or manifest['dependency_inputs']!=inputs(repo):
        raise ValueError('dependency_identity_mismatch')
    if sha(prepared/'dependencies.tar.gz')!=manifest['archive_sha256']:
        raise ValueError('dependency_archive_mismatch')
    if sha(node_archive)!=NODE_ARCHIVE_SHA:raise ValueError('node_archive_mismatch')
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
    result={'head':head,'dependency_key':manifest['dependency_key'],'archive_sha256':manifest['archive_sha256'],'steps':[],
            'status':'failed','server_install':'not_run','network':False}
    with attempt_receipt(prepared,result) as attempt:
        with tempfile.TemporaryDirectory(prefix='frontend-verify-',dir=allowed) as tmp:
            tmp=Path(tmp);work=tmp/'work';work.mkdir()
            source=tmp/'source.tar'
            with source.open('wb') as stream:subprocess.run(['git','archive',head],cwd=repo,stdout=stream,check=True)
            with tarfile.open(source) as tf:tf.extractall(work,filter='data')
            if inputs(work)!=manifest['dependency_inputs']:raise ValueError('committed_input_mismatch')
            unpack_dependencies(prepared/'dependencies.tar.gz',work,manifest['mounts'])
            with tarfile.open(node_archive,'r:xz') as tf:(tmp/'node').write_bytes(tf.extractfile('node-v22.17.0-linux-x64/bin/node').read())
            if sha(tmp/'node')!=NODE_SHA:raise ValueError('node_binary_mismatch')
            (tmp/'node').chmod(0o755)
            (tmp/'tools').mkdir()
            launcher=tmp/'tools/pnpm';launcher.write_text('#!/bin/sh\nexec node /pnpm/bin/pnpm.cjs "$@"\n');launcher.chmod(0o755)
            prefix=['/usr/bin/bwrap','--unshare-all','--die-with-parent','--new-session',
                    '--ro-bind','/usr','/usr','--symlink','usr/bin','/bin','--symlink','usr/lib','/lib',
                    '--symlink','usr/lib64','/lib64','--proc','/proc','--dev','/dev','--tmpfs','/tmp',
                    '--bind',str(work),'/work','--ro-bind',str(work/'pnpm'),'/pnpm',
                    '--ro-bind',str(tmp/'node'),'/usr/bin/node','--ro-bind',str(tmp/'tools'),'/tools','--chdir','/work']
            env={'PATH':'/tools:/usr/bin:/bin','HOME':'/tmp','CI':'1','ENV':'test','PYTHONDONTWRITEBYTECODE':'1',
                 'GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':'/dev/null','XDG_CACHE_HOME':'/tmp/cache'}
            for step in ['lint:src','typecheck:strict','test','build']:
                path=attempt/(step.replace(':','-')+'.log')
                with path.open('wb') as stream:
                    from scripts.ci.gitee_ci_acceptance import Executor
                    r=Executor(attempt).command(prefix+['pnpm','-C','frontend/apps/web',step],work,stream,lambda:False,time.monotonic()+900,env)
                row={'step':step,'exit_code':r,'log':path.name}
                if step=='test' and r==0:
                    from scripts.ci.gitee_formal_executor import nonzero_tests
                    row['python_tests']=nonzero_tests(path.read_text(errors='replace'))
                    row['scope']='make verify.frontend.pr.unit; Node assertion entries recorded in raw log, not added to Python count'
                result['steps'].append(row)
            result['status']='passed' if all(s['exit_code']==0 for s in result['steps']) else 'failed'
    return result


def unpack_dependencies(archive,work,mounts):
    work=Path(work).resolve()
    allowed={'frontend/node_modules','frontend/apps/mobile/node_modules',
             'frontend/apps/web/node_modules','frontend/packages/ui/node_modules'}
    if not isinstance(mounts,list) or not set(mounts)<=allowed or 'frontend/node_modules' not in mounts:
        raise ValueError('dependency_mount_scope')
    with tarfile.open(archive,'r:gz') as tf:
        members=tf.getmembers()
        if len(members)>100000 or sum(m.size for m in members)>1500000000:
            raise ValueError('dependency_archive_size')
        seen=set()
        for m in members:
            rel=Path(m.name)
            if (m.name in seen or rel.is_absolute() or '..' in rel.parts or
                not any(m.name==r or m.name.startswith(r+'/') for r in [*mounts,'pnpm']) or
                not (m.isfile() or m.isdir() or m.issym())):
                raise ValueError('dependency_archive_scope')
            seen.add(m.name)
            if m.issym() and (Path(m.linkname).is_absolute() or
                not (work/rel.parent/m.linkname).resolve().is_relative_to(work)):
                raise ValueError('dependency_archive_link')
        for r in [*mounts,'pnpm']:
            if (work/r).exists() or (work/r).is_symlink():raise ValueError('existing_dependency_target')
        tf.extractall(work,filter='data')


def runtime_cache(work,cache_parent=Path('/opt/gitee-ci/frontend')):
    wanted=inputs(work);folder=cache_parent/key(wanted)
    for target in [folder/'manifest.json',folder/'dependencies.tar.gz',folder,*folder.parents]:
        info=target.lstat()
        if target.is_symlink() or info.st_uid!=0 or info.st_mode&0o022:
            raise ValueError('untrusted_frontend_cache')
    manifest=json.loads((folder/'manifest.json').read_text())
    if manifest.get('dependency_inputs')!=wanted or manifest.get('status')!='prepared':
        raise ValueError('frontend_cache_identity')
    if sha(folder/'dependencies.tar.gz')!=manifest['archive_sha256']:
        raise ValueError('frontend_cache_corrupt')
    unpack_dependencies(folder/'dependencies.tar.gz',work,manifest['mounts'])
    return {'dependency_key':key(wanted),'archive_sha256':manifest['archive_sha256']}


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--node-archive',required=True)
    p.add_argument('--pnpm-archive');p.add_argument('--store');p.add_argument('--verify',action='store_true');a=p.parse_args()
    if a.verify:
        result=verify(Path(__file__).resolve().parents[2],a.output,a.node_archive);print(json.dumps(result));raise SystemExit(0 if result['status']=='passed' else 1)
    print(json.dumps(prepare(Path(__file__).resolve().parents[2],a.output,a.node_archive,a.pnpm_archive,a.store),sort_keys=True))

if __name__=='__main__':main()
