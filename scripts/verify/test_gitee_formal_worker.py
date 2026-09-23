import tempfile
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
from scripts.ci.gitee_formal_worker import Inbox, Worker

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
        w=Worker.__new__(Worker);w.inbox=Mock();w.queue=Mock();w.executor=Mock();w.reporter=Mock();return w
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
    @patch('scripts.ci.gitee_formal_worker.execute_once',return_value=True)
    def test_authenticated_event_becomes_plan_then_execution(self,execute):
        w=self.worker();w.inbox.claim.return_value=('123',{'pr_number':5});w.prepare=Mock(return_value={'plan':'fixture'})
        self.assertTrue(w.tick());w.queue.enqueue.assert_called_once_with({'plan':'fixture'},'123')
        w.inbox.finish.assert_called_once_with('123','prepared');execute.assert_called_once_with(w.queue,w.executor,w.refresh)

if __name__=='__main__':unittest.main()
