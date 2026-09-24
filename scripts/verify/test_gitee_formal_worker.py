import json
import tempfile
from pathlib import Path
import subprocess
import unittest
from unittest.mock import Mock, patch
from scripts.ci.gitee_formal_queue import FormalQueue
from scripts.ci.gitee_formal_worker import Inbox, PreparationFailed, Worker

class InboxTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'queue.sqlite3'; self.q=Inbox(self.path)
        self.event={'hook_name':'merge_request_hooks','repository':'leegege/sce-product-odoo','pr_number':5,'sha':'a'*40}
    def test_replay_and_conflicting_delivery(self):
        self.assertTrue(self.q.enqueue(self.event,'123'))
        self.assertFalse(self.q.enqueue(self.event,'123'))
        with self.assertRaises(ValueError): self.q.enqueue(dict(self.event,sha='b'*40),'123')
        delivery,event=self.q.claim(); self.assertEqual(event,self.event)
        self.q.finish(delivery,'prepared'); self.assertIsNone(self.q.claim())
    def test_reject_push_foreign_repo_and_bool_pr(self):
        for update in [{'hook_name':'push_hooks'},{'repository':'foreign/repo'},{'pr_number':True},{'sha':'HEAD'}]:
            with self.assertRaises(ValueError):self.q.enqueue(dict(self.event,**update),'123')
    def test_recovery_does_not_reexecute_preparing(self):
        self.q.enqueue(self.event,'123');self.q.claim()
        recovered=Inbox(self.path,recover_running=True)
        self.assertIsNone(recovered.claim())
        with recovered.connect() as db:self.assertEqual(db.execute('SELECT status FROM formal_inbox').fetchone()[0],'environment_error')
    def test_extra_secret_fields_not_persisted(self):
        self.q.enqueue(dict(self.event,password='fixture-secret'),'123')
        with self.q.connect() as db:self.assertNotIn('fixture-secret',db.execute('SELECT event FROM formal_inbox').fetchone()[0])

class WorkerTests(unittest.TestCase):
    def worker(self):
        w=Worker.__new__(Worker);w.inbox=Mock();w.queue=Mock();w.executor=Mock();w.reporter=Mock();w.reader=Mock();return w
    def test_candidate_label_invalidates_previous_ordinary_success(self):
        w=self.worker();w.reader=Mock();w.reader.get.return_value={'labels':[{'name':'ci:candidate'}]}
        with self.assertRaisesRegex(ValueError,'requested_lane_changed'):
            w.refresh({'pr_number':5,'candidate_requested':False})

    def test_report_failure_does_not_kill_worker(self):
        w=self.worker();w.reporter.sync_once.side_effect=RuntimeError('private diagnostic')
        w.report();self.assertEqual(w.reporter.sync_once.call_count,1)
    @patch('scripts.ci.gitee_formal_worker.execute_once',return_value=False)
    def test_prepare_failure_terminalized_without_execute(self,execute):
        w=self.worker();w.inbox.claim.return_value=('123',{});w.prepare=Mock(side_effect=ValueError('stale'))
        self.assertTrue(w.tick());w.inbox.finish.assert_called_once_with('123','environment_error');w.queue.enqueue.assert_not_called()

    @patch('scripts.ci.gitee_formal_worker.execute_once',return_value=False)
    def test_bindable_prepare_failure_reports_visible_failure(self,execute):
        w=self.worker();w.inbox.claim.return_value=('123',{'pr_number':5})
        w.prepare=Mock(side_effect=PreparationFailed('baseline_not_ancestor'))
        failure={'repository':'leegege/sce-product-odoo','source_branch':'fix/unit','target_branch':'main',
                 'head_sha':'a'*40,'base_sha':'b'*40,'pr_number':5,'plan_sha256':'d'}
        w.failure_plan=Mock(return_value=dict(failure));w.queue.enqueue.return_value=('k',True)
        self.assertTrue(w.tick())
        w.queue.enqueue.assert_called_once_with(dict(failure),'123')
        w.queue.fail.assert_called_once_with('k',Worker.failure_receipt(dict(failure)))
        w.inbox.finish.assert_called_once_with('123','prepared')

    @patch('scripts.ci.gitee_formal_worker.execute_once',return_value=False)
    def test_unbindable_prepare_failure_never_claims_a_report(self,execute):
        w=self.worker();w.inbox.claim.return_value=('123',{'pr_number':5})
        w.prepare=Mock(side_effect=PreparationFailed('baseline_not_ancestor'))
        w.failure_plan=Mock(side_effect=PreparationFailed('pull_request_unavailable'))
        self.assertTrue(w.tick())
        w.queue.enqueue.assert_not_called();w.queue.fail.assert_not_called()
        w.inbox.finish.assert_called_once_with('123','environment_error')

    def test_unknown_prepare_error_maps_to_bounded_reason(self):
        w=self.worker();w.failure_plan=Mock(side_effect=PreparationFailed('pull_request_unavailable'))
        w.prepare=Mock(side_effect=RuntimeError('private diagnostic'))
        w.prepare_delivery('123',{'pr_number':5})
        self.assertEqual(w.failure_plan.call_args[0][1],'preparation_incomplete')

    def duplicate_worker(self):
        w=self.worker()
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        path=Path(temp.name)/'inbox.sqlite3'
        w.inbox=Inbox(path);w.queue=FormalQueue(path)
        w.prepare=Mock(side_effect=PreparationFailed('baseline_not_ancestor'))
        w.identity=Mock(return_value=('fix/unit','b'*40,False,{
            'repository':'leegege/sce-product-odoo','source_branch':'fix/unit','target_branch':'main',
            'head_sha':'a'*40,'base_sha':'b'*40,'pr_number':5,'pr_id':124,
            'pr_identity_verified':True,'remote_refs_verified':True}))
        return w

    @patch('scripts.ci.gitee_formal_worker.execute_once',return_value=False)
    def test_repeated_event_never_creates_a_conflicting_terminal_state(self,execute):
        w=self.duplicate_worker()
        event={'hook_name':'merge_request_hooks','repository':'leegege/sce-product-odoo','pr_number':5,'sha':'a'*40}
        w.inbox.enqueue(event,'111');self.assertTrue(w.tick())
        w.inbox.enqueue(event,'222');self.assertTrue(w.tick())
        with w.queue.connect() as db:
            rows=db.execute('SELECT status,receipt FROM formal_jobs').fetchall()
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0][0],'environment_error')
        self.assertEqual(json.loads(rows[0][1])['status'],'environment_error')
        with w.inbox.connect() as db:
            self.assertEqual([x[0] for x in db.execute('SELECT status FROM formal_inbox ORDER BY rowid')],
                             ['prepared','environment_error'])

    def test_preparation_failure_reason_must_be_trusted(self):
        with self.assertRaises(ValueError): PreparationFailed('candidate supplied text')

    def test_baseline_gate_is_reported_not_bypassed(self):
        w=self.worker()
        w.identity=Mock(return_value=('fix/unit','b'*40,False,{'pr_id':7}))
        with tempfile.TemporaryDirectory() as temp:
            w.executor.artifacts=Path(temp);w.executor.checkout=Mock(return_value='a'*40)
            with patch('scripts.ci.gitee_formal_worker.changed_paths',
                       side_effect=subprocess.CalledProcessError(1,['git','merge-base'])):
                with self.assertRaisesRegex(PreparationFailed,'baseline_not_ancestor'):
                    w.prepare({'pr_number':5,'sha':'a'*40})
    @patch('scripts.ci.gitee_formal_worker.execute_once',return_value=True)
    def test_authenticated_event_becomes_plan_then_execution(self,execute):
        w=self.worker();w.inbox.claim.return_value=('123',{'pr_number':5});w.prepare=Mock(return_value={'plan':'fixture'})
        self.assertTrue(w.tick());w.queue.enqueue.assert_called_once_with({'plan':'fixture'},'123')
        w.inbox.finish.assert_called_once_with('123','prepared');execute.assert_called_once_with(w.queue,w.executor,w.refresh)

if __name__=='__main__':unittest.main()
