#!/usr/bin/env python3
"""Real Make subprocess interruption/resume; temporary Git repo, no ORM/database.
Production planner/executor unchanged. Fixture recipes are not product acceptance.
"""
import hashlib,json,os,signal,subprocess,sys,tempfile,time
from pathlib import Path
ROOT=Path.cwd();sys.path.insert(0,str(ROOT))
from scripts.verify import frontend_dev_incremental as e
OUT=ROOT/'.runtime/verify-system-closeout-01/resume';OUT.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory(prefix='sce-r1-resume-') as tmp:
 r=Path(tmp)
 def git(*a):return subprocess.check_output(['git','-C',str(r),*a],text=True).strip()
 subprocess.run(['git','init','-q','-b','main',str(r)],check=True)
 git('config','user.name','R1 Audit');git('config','user.email','r1@example.invalid')
 paths=['frontend/apps/web/src/NewSurface.vue','scripts/ops/safe_branch_sync_main.py']
 for p in paths:(r/p).parent.mkdir(parents=True,exist_ok=True);(r/p).write_text('VERSION = 1\n')
 (r/'.gitignore').write_text('.runtime/\nfrontend/apps/web/node_modules/\n')
 for tool in ['eslint','vue-tsc','esbuild']:
  p=r/'frontend/apps/web/node_modules/.bin'/tool;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('#!/bin/sh\nexit 0\n');p.chmod(0o755)
 targets=e.select_iteration_targets(paths)
 (r/'producer.py').write_text("import os,time,pathlib\nif os.environ.get('R1_BLOCK')=='1':\n pathlib.Path('.runtime/entered').touch()\n time.sleep(30)\nprint('Ran 1 test in 0.001s\\nOK')\n")
 (r/'Makefile').write_text(''.join(t+':\n\t@R1_BLOCK='+('$$R1_BLOCK' if 'workspace' in t else '0')+' python3 producer.py\n' for t in targets))
 git('add','.');git('commit','-qm','isolated fixture')
 (r/'.runtime').mkdir()
 harness=r/'.runtime/execute.py'
 harness.write_text('import sys\nfrom pathlib import Path\nsys.path.insert(0,'+repr(str(ROOT))+')\nfrom scripts.verify import frontend_dev_incremental as e\nr=Path('+repr(str(r))+')\ne.STATE_PATH=r/".runtime/state.json"\nidentity=e.current_execution_identity(r)\nidentity["environmentIdentitySha256"]=sys.argv[3]*64\nraise SystemExit(e.execute_targets('+repr(paths)+',root=r,run_id=sys.argv[2],registered_targets=set('+repr(targets)+'),receipt_dir=r/".runtime/frontend-dev-validation/executions"/sys.argv[1],worktree_identity=identity))\n')
 def run(name,runid='R1',environment='a',block=False):
  log=OUT/(name+'.log');f=log.open('w');p=subprocess.Popen([sys.executable,str(harness),name,runid,environment],cwd=r,env=dict(os.environ,R1_BLOCK='1' if block else '0'),stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
  if block:
   deadline=time.monotonic()+15
   while not (r/'.runtime/entered').exists() and p.poll() is None and time.monotonic()<deadline:time.sleep(.05)
   if not (r/'.runtime/entered').exists():raise RuntimeError('interruption marker not reached')
   os.killpg(p.pid,signal.SIGINT)
  code=p.wait(timeout=20);f.close();receipt=json.loads((r/'.runtime/frontend-dev-validation/executions'/name/'receipt.json').read_text());(OUT/(name+'.json')).write_text(json.dumps(receipt,indent=2)+'\n')
  return dict(name=name,returncode=code,status=receipt['status'],executed=receipt.get('executedTargetCount'),reused=receipt.get('reusedTargetCount'),log=str(log.relative_to(ROOT)),source_head=receipt['identity']['head'])
 results=[run('interrupted',block=True)]
 (r/paths[1]).write_text('VERSION = 2\n');git('add',paths[1]);git('commit','-qm','changed one dependency')
 results.append(run('resumed'))
 # Environmental identity change is deliberately explicit, not inferred.
 results.append(run('environment_changed',environment='b'))
 results.append(run('different_run',runid='OTHER',environment='b'))
 # Corrupt all existing copies of one target log; unrelated targets remain reusable.
 for p in (r/'.runtime/frontend-dev-validation/executions').glob('*/receipt.json'):
  receipt=json.loads(p.read_text())
  for row in receipt['targetResults']:
   if row['target']==targets[0]:(r/row['log']).write_text('tampered\n')
 results.append(run('tampered_log',environment='b'))
 # Full reexecution: remove only temporary fixture receipts/index, never real repository evidence.
 import shutil
 shutil.rmtree(r/'.runtime/frontend-dev-validation')
 results.append(run('fresh_full',environment='b'))
 (OUT/'results.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results,indent=2))
