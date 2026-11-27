"""Actual Make subprocess recovery and environment identity regression."""
from __future__ import annotations
import contextlib
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from scripts.verify import frontend_dev_incremental as executor


class EnvironmentExecutionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.paths=['frontend/apps/web/src/NewSurface.vue','scripts/ops/safe_branch_sync_main.py']
        for path in self.paths:
            file=self.root/path;file.parent.mkdir(parents=True,exist_ok=True);file.write_text('VERSION = 1\n')
        for name in ['eslint','vue-tsc','esbuild']:
            file=self.root/'frontend/apps/web/node_modules/.bin'/name;file.parent.mkdir(parents=True,exist_ok=True)
            file.write_text('#!/bin/sh\nexit 0\n');file.chmod(0o755)
        self.targets=executor.select_iteration_targets(self.paths)
        (self.root/'.gitignore').write_text('.runtime/\nfrontend/apps/web/node_modules/\n')
        (self.root/'producer.py').write_text("import os,time,pathlib\nif os.getenv('ENV_TEST_BLOCK')=='1':\n pathlib.Path('.runtime/entered').touch()\n time.sleep(30)\nprint('Ran 1 test in 0.001s\\nOK')\n")
        (self.root/'Makefile').write_text(''.join(target+':\n\t@ENV_TEST_BLOCK='+('$$ENV_TEST_BLOCK' if 'workspace' in target else '0')+' python3 producer.py\n' for target in self.targets))
        for cmd in [['init','-q','-b','main'],['config','user.name','Test'],['config','user.email','test@example.invalid'],['add','.'],['commit','-qm','fixture']]:self.git(*cmd)
        (self.root/'.runtime').mkdir()

    def git(self,*args):
        subprocess.run(['git','-C',str(self.root),*args],check=True,stdout=subprocess.DEVNULL)

    def execute(self,name,env='a',run='R1',channel='all',explicit_environment=True,readback='a'):
        identity=executor.current_execution_identity(self.root)
        if explicit_environment:
            identity['environmentIdentitySha256']=env*64
            identity['environmentReadbackSha256']=readback*64
        directory=self.root/'.runtime/frontend-dev-validation/executions'/name
        with patch.object(executor,'STATE_PATH',self.root/'.runtime/state.json'),contextlib.redirect_stdout(io.StringIO()):
            code=executor.execute_targets(self.paths,root=self.root,registered_targets=set(self.targets),run_id=run,channel=channel,
                                          worktree_identity=identity,receipt_dir=directory)
        return code,json.loads((directory/'receipt.json').read_text())

    def test_environment_change_reexecutes_both_cache_paths_but_same_environment_reuses(self):
        code,first=self.execute('first');self.assertEqual(code,0);self.assertEqual(first['executedTargetCount'],4)
        code,same=self.execute('same');self.assertEqual(code,0);self.assertEqual(same['executedTargetCount'],0)
        code,changed=self.execute('changed',env='b');self.assertEqual(code,0);self.assertEqual(changed['executedTargetCount'],4)
        self.assertEqual(changed['reusedTargetCount'],0)
        code,readback=self.execute('readback',env='b',readback='b');self.assertEqual(code,0);self.assertEqual(readback['executedTargetCount'],4)
        # Remove the aggregate index only, exercising the independent per-target path.
        for path in (self.root/'.runtime/frontend-dev-validation/reuse').glob('*.json'):path.unlink()
        code,again=self.execute('per-target',env='c');self.assertEqual(code,0);self.assertEqual(again['executedTargetCount'],4)

    def test_observed_host_tool_change_invalidates_without_caller_invented_fingerprint(self):
        _,first=self.execute('first',explicit_environment=False)
        file=self.root/'frontend/apps/web/node_modules/.bin/vue-tsc';file.write_text('#!/bin/sh\nexit 2\n')
        _,changed=self.execute('changed',explicit_environment=False)
        self.assertNotEqual(first['identity']['environmentIdentitySha256'],changed['identity']['environmentIdentitySha256'])
        self.assertEqual(changed['executedTargetCount'],4)

    def test_cross_run_content_reuse_is_distinct_from_same_run_channel(self):
        self.execute('all-first')
        _,same=self.execute('all-second',run='R2');self.assertEqual(same['executedTargetCount'],0)
        _,channel=self.execute('front-first',run='R3',channel='frontend');self.assertGreater(channel['executedTargetCount'],0)
        _,other=self.execute('front-second',run='R4',channel='frontend');self.assertGreater(other['executedTargetCount'],0)

    def test_registered_runtime_readback_changes_fingerprint(self):
        file=self.root/'.runtime/readback.json';file.write_text('{"database":"isolated-a"}')
        run={'environment':{'kind':'runtime','authority':'governed test fixture'},'checks':{'orm':{'target':'verify.audit.orm','kind':'runtime','readback':{'artifact':'.runtime/readback.json'}}}}
        before=executor.governed_environment_identity(self.root,run,{'verify.audit.orm'})
        file.write_text('{"database":"isolated-b"}')
        after=executor.governed_environment_identity(self.root,run,{'verify.audit.orm'})
        self.assertNotEqual(before['environmentReadbackSha256'],after['environmentReadbackSha256'])
        file.unlink();missing=executor.governed_environment_identity(self.root,run,{'verify.audit.orm'})
        self.assertEqual(missing['environmentReadbackSha256'],'')

    def test_real_sigint_then_changed_dependency_resumes_only_unaffected_targets(self):
        script=self.root/'.runtime/execute.py'
        script.write_text('import sys\nfrom pathlib import Path\nsys.path.insert(0,'+repr(str(ROOT))+')\nfrom scripts.verify import frontend_dev_incremental as e\nr=Path('+repr(str(self.root))+')\ne.STATE_PATH=r/".runtime/state.json"\ni=e.current_execution_identity(r)\ni["environmentIdentitySha256"]="a"*64\ni["environmentReadbackSha256"]="a"*64\nraise SystemExit(e.execute_targets('+repr(self.paths)+',root=r,run_id="R1",registered_targets=set('+repr(self.targets)+'),worktree_identity=i,receipt_dir=r/".runtime/frontend-dev-validation/executions/interrupted"))\n')
        with (self.root/'.runtime/interrupt.log').open('w') as log:
            proc=subprocess.Popen([sys.executable,str(script)],cwd=self.root,env=dict(os.environ,ENV_TEST_BLOCK='1'),stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            try:
                deadline=time.monotonic()+15
                while not (self.root/'.runtime/entered').exists() and proc.poll() is None and time.monotonic()<deadline:time.sleep(.02)
                self.assertTrue((self.root/'.runtime/entered').exists())
                os.killpg(proc.pid,signal.SIGINT);self.assertEqual(proc.wait(timeout=10),130)
            finally:
                if proc.poll() is None:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
        (self.root/self.paths[1]).write_text('VERSION = 2\n');self.git('add',self.paths[1]);self.git('commit','-qm','changed one dependency')
        code,resumed=self.execute('resumed');self.assertEqual(code,0)
        self.assertEqual((resumed['executedTargetCount'],resumed['reusedTargetCount']),(1,3))
        for row in resumed['targetResults']:
            if row['target']==self.targets[0]:(self.root/row['log']).unlink()
        code,missing=self.execute('missing-log');self.assertEqual(code,0);self.assertGreater(missing['executedTargetCount'],0)


if __name__=='__main__':unittest.main()
