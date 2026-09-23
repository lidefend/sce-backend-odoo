"""Behavior tests use real sandboxed processes, no network or business data."""
import json
import os
import subprocess
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from scripts.ci.gitee_ci_acceptance import AcceptanceQueue, Executor, BRANCH, REPOSITORY, validate

H = 'a'*40
H2 = 'b'*40

def job(sha=H):
    return {'sha':sha, 'repository':REPOSITORY, 'ref':'refs/heads/'+BRANCH, 'hook_name':'push_hooks', 'sender':'leegege', 'pr_number':None}


class LocalExecutor(Executor):
    def __init__(self, root, source, **kwargs):
        super().__init__(root, **kwargs)
        self.source = source
        self.checked = H
        self.workspace = None

    def checkout(self, workspace, sha, log, cancelled, deadline):
        self.workspace = workspace
        repo = workspace/'repo'
        (repo/'scripts'/'ops').mkdir(parents=True)
        (repo/'scripts'/'__init__.py').touch()
        (repo/'scripts'/'ops'/'__init__.py').touch()
        (repo/'scripts'/'ops'/'test_gitee_temporary_integration.py').write_text(self.source)
        return self.checked


class AcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def run_case(self, source, **kwargs):
        executor = LocalExecutor(self.root/'logs', source, **kwargs)
        result = executor.execute(job())
        self.assertFalse(executor.workspace.exists())
        self.assertEqual(result['sha'], H)
        self.assertEqual(json.loads((Path(result['log']).parent/'receipt.json').read_text()), result)
        return result

    def test_success_actual_count_and_credentials_hidden(self):
        source = '''import os, pathlib, socket, unittest
class T(unittest.TestCase):
 def test_isolation(self):
  self.assertNotIn('GITEE_WEBHOOK_SECRET', os.environ)
  self.assertNotIn('DEPLOY_TOKEN', os.environ)
  self.assertFalse(pathlib.Path('/etc/gitee-ci').exists())
  self.assertFalse(pathlib.Path('/var/lib/gitee-mirror').exists())
  with self.assertRaises(OSError): socket.create_connection(('1.1.1.1', 443), timeout=.1)
 def test_two(self): self.assertEqual(2+2,4)
'''
        with patch.dict(os.environ, {'GITEE_WEBHOOK_SECRET':'test-secret', 'DEPLOY_TOKEN':'test-deploy'}):
            r = self.run_case(source)
        self.assertEqual((r['status'],r['tests'],r['exit_code']), ('success',2,0))
        self.assertEqual(r['checkout_sha'],H)

    def test_current_fixed_suite_runs_in_real_sandbox(self):
        root=Path(__file__).resolve().parents[2]
        source=(root/'scripts/ops/test_gitee_temporary_integration.py').read_text()
        executor=LocalExecutor(self.root/'logs',source)
        original=executor.checkout
        def checkout(*args):
            sha=original(*args)
            (executor.workspace/'repo/scripts/ops/gitee_temporary_integration.py').write_text(
                (root/'scripts/ops/gitee_temporary_integration.py').read_text())
            return sha
        with patch.object(executor,'checkout',side_effect=checkout): r=executor.execute(job())
        self.assertEqual(r['status'],'success',Path(r['log']).read_text())
        self.assertGreater(r['tests'],0)
        self.assertFalse(executor.workspace.exists())

    def test_stale_report_cannot_turn_early_exit_into_success(self):
        executor=LocalExecutor(self.root/'logs','import os; os._exit(0)')
        original=executor.checkout
        def checkout(*args):
            sha=original(*args)
            (executor.workspace/'repo/.ci-count.json').write_text('{"tests":99,"ok":true}')
            return sha
        with patch.object(executor,'checkout',side_effect=checkout): r=executor.execute(job())
        self.assertEqual(r['status'],'environment_error')
        self.assertIsNone(r['tests'])
        self.assertFalse(executor.workspace.exists())

    def test_symlink_report_is_rejected(self):
        source="import pathlib\npathlib.Path('/work/.ci-count.json').symlink_to('/tmp/fake-count')\n"
        r=self.run_case(source)
        self.assertEqual(r['status'],'environment_error')

    def test_failure(self):
        r = self.run_case('import unittest\nclass T(unittest.TestCase):\n def test_bad(self): self.fail("intentional")\n')
        self.assertEqual((r['status'],r['tests']),('failed',1))
        self.assertNotEqual(r['exit_code'],0)
        self.assertIn('intentional',Path(r['log']).read_text())

    def test_zero(self):
        r = self.run_case('import unittest\n')
        self.assertEqual((r['status'],r['tests']),('failed',0))

    def test_all_skipped_is_zero(self):
        r = self.run_case('import unittest\nclass T(unittest.TestCase):\n @unittest.skip("skip")\n def test_x(self): pass\n')
        self.assertEqual((r['status'],r['tests']),('failed',0))

    def blocked_source(self, marker):
        return f'''import subprocess, sys, time, pathlib, unittest
class T(unittest.TestCase):
 def test_wait(self):
  subprocess.Popen([sys.executable, '-c', 'import os,time;os.setsid();time.sleep(100)', {marker!r}])
  pathlib.Path('/work/started').touch()
  time.sleep(100)
'''

    def assert_no_process(self, marker):
        for p in Path('/proc').glob('[0-9]*/cmdline'):
            try: data=p.read_bytes()
            except OSError: continue
            self.assertNotIn(marker.encode(), data, str(p))

    def test_timeout_kills_escaped_descendant(self):
        marker='ci-child-'+self.root.name
        r=self.run_case(self.blocked_source(marker), timeout=.7)
        self.assertEqual(r['status'],'timed_out')
        self.assertIsNotNone(r['exit_code'])
        self.assert_no_process(marker)

    def test_running_cancel_cleans_processes_and_workspace(self):
        marker='ci-child-'+self.root.name
        executor=LocalExecutor(self.root/'logs',self.blocked_source(marker))
        cancelled=threading.Event()
        results=[]
        t=threading.Thread(target=lambda: results.append(executor.execute(job(),cancelled.is_set)))
        t.start()
        try:
            deadline=time.monotonic()+5
            while not (executor.workspace and (executor.workspace/'repo'/'started').exists()):
                if time.monotonic()>deadline: self.fail('task did not start')
                time.sleep(.01)
            cancelled.set()
        finally:
            cancelled.set();t.join(5)
        self.assertFalse(t.is_alive())
        self.assertEqual(results[0]['status'],'cancelled')
        self.assertFalse(executor.workspace.exists())
        self.assert_no_process(marker)

    def test_checkout_mismatch_never_runs_check(self):
        executor=LocalExecutor(self.root/'logs','raise Exception("must not execute")')
        executor.checked=H2
        r=executor.execute(job())
        self.assertEqual(r['status'],'environment_error')
        self.assertEqual(r['checkout_sha'],H2)
        self.assertIsNone(r['exit_code'])
        self.assertFalse(executor.workspace.exists())

    def test_missing_sandbox_is_environment_error(self):
        executor=LocalExecutor(self.root/'logs','')
        with patch.object(executor,'sandbox',return_value=['/missing-ci-executable']): r=executor.execute(job())
        self.assertEqual(r['status'],'environment_error')
        self.assertFalse(executor.workspace.exists())

    def test_scope_rejection(self):
        for change in [{'repository':'wrong/repo'},{'ref':'refs/heads/main'}, {'ref':'refs/tags/v1'}, {'sha':'abc'}, {'hook_name':'merge_request_hooks'}]:
            with self.subTest(change=change),self.assertRaises(ValueError): validate({**job(),**change})
        self.assertEqual(list(self.root.iterdir()),[])

    def test_signature_replay_cannot_enqueue_other_sha(self):
        q=AcceptanceQueue(self.root/'q.sqlite')
        self.assertTrue(q.enqueue(job(),'timestamp1'))
        self.assertFalse(q.enqueue(job(),'timestamp1'))
        with self.assertRaises(ValueError): q.enqueue(job(H2),'timestamp1')
        self.assertIsNone(q.result(H2))

    def test_duplicate_and_late_old_sha(self):
        queue=AcceptanceQueue(self.root/'q.sqlite')
        self.assertTrue(queue.enqueue(job(), 'event1'))
        self.assertFalse(queue.enqueue(job(), 'event2'))
        self.assertEqual(queue.claim()['sha'],H)
        self.assertTrue(queue.enqueue(job(H2),'event3'))
        queue.finish(H,{'sha':H,'status':'success','tests':2})
        self.assertEqual(queue.result(H2)['status'],'pending')
        self.assertEqual(queue.result(H)['receipt']['sha'],H)
        self.assertEqual(queue.claim()['sha'],H2)
        queue.finish(H2,{'sha':H2,'status':'failed','tests':1})
        queue.finish(H,{'sha':H,'status':'success','tests':2})
        self.assertEqual(queue.result(H2)['status'],'failed')

    def test_real_checkout_and_run(self):
        source=self.root/'source';source.mkdir()
        env={**os.environ, 'GIT_CONFIG_GLOBAL':'/dev/null','GIT_CONFIG_NOSYSTEM':'1'}
        def git(*args):
            return subprocess.check_output(['git','-C',str(source),*args],env=env,stderr=subprocess.DEVNULL,text=True).strip()
        git('init')
        target=source/'scripts'/'ops';target.mkdir(parents=True)
        (source/'scripts'/'__init__.py').touch();(target/'__init__.py').touch()
        (target/'test_gitee_temporary_integration.py').write_text('import unittest\nclass T(unittest.TestCase):\n def test_ok(self): self.assertTrue(True)\n')
        git('add','.')
        git('-c','user.name=Test','-c','user.email=test@example.invalid','commit','-m','fixture')
        sha=git('rev-parse','HEAD')
        with patch('scripts.ci.gitee_ci_acceptance.REMOTE',str(source)):
            r=Executor(self.root/'logs').execute(job(sha))
        self.assertEqual((r['status'],r['checkout_sha'],r['tests']),('success',sha,1))

    def test_cancel_finish_race_remains_cancelled(self):
        q=AcceptanceQueue(self.root/'q.sqlite');q.enqueue(job(),'1');q.claim();q.cancel(H)
        q.finish(H,{'sha':H,'status':'success','tests':1})
        self.assertEqual(q.result(H)['status'],'cancelled')

    def test_application_accepts_only_explicit_ci_branch(self):
        from scripts.ci.gitee_webhook_ci import Application, expected_signature, Rejected
        env={'GITEE_CI_MODE':'ci-only','GITEE_WEBHOOK_SECRET':'test-secret',
             'GITEE_ALLOWED_REPOSITORY':REPOSITORY,'GITEE_ALLOWED_SENDER':'leegege',
             'GITEE_CI_DB':str(self.root/'app.sqlite')}
        with patch.dict(os.environ,env): app=Application(worker_enabled=False)
        timestamp=str(int(time.time()*1000))
        headers={'X-Gitee-Timestamp':timestamp, 'X-Gitee-Token':expected_signature(timestamp,'test-secret')}
        payload={'hook_name':'push_hooks','after':H,'repository':{'full_name':REPOSITORY},
                 'sender':{'login':'leegege'},'ref':'refs/heads/'+BRANCH,'command':'touch /must-not-run'}
        self.assertTrue(app.accept(json.dumps(payload).encode(),headers)[0])
        self.assertFalse(app.accept(json.dumps(payload).encode(),headers)[0])
        queued=app.queue.claim()
        self.assertNotIn('command',queued)
        payload['ref']='refs/tags/v1'
        with self.assertRaises(Rejected): app.accept(json.dumps(payload).encode(),headers)

    def test_queue_cancel_and_restart_not_success(self):
        q=AcceptanceQueue(self.root/'q.sqlite');q.enqueue(job(),'1');q.claim();q.cancel(H)
        self.assertTrue(q.cancelled(H))
        recovered=AcceptanceQueue(q.path,recover_running=True)
        self.assertEqual(recovered.result(H)['status'],'environment_error')


if __name__=='__main__': unittest.main()
