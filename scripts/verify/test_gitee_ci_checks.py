"""Offline Check Runs failure/restart/readback tests: no platform writes."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts.ci.gitee_ci_checks import API, NAME, NoRedirect, Reporter, ReportError, payload_for
from scripts.ci.gitee_ci_acceptance import AcceptanceQueue, BRANCH, REPOSITORY

H = "a"*40
H2 = "b"*40

def job(sha=H):
    return dict(sha=sha,repository=REPOSITORY,ref="refs/heads/"+BRANCH,hook_name="push_hooks")

def receipt(sha=H):
    return dict(sha=sha,checkout_sha=sha,status="success",exit_code=0,tests=42,integration_eligible=False)

class FakeAPI:
    def __init__(self):
        self.rows = {}
        self.calls = []
        self.lose_create = False
        self.fail_create = False
        self.lose_patch = False
        self.reject_patch = False
    def request(self, method, path, payload=None):
        self.calls.append((method,path,copy.deepcopy(payload)))
        if method == "POST":
            if self.fail_create: raise ReportError("api_request_failed")
            i=len(self.rows)+1
            self.rows[i]={**copy.deepcopy(payload),"id":i}
            if self.lose_create:
                self.lose_create=False
                raise ReportError("api_request_failed")
            return copy.deepcopy(self.rows[i])
        if path.startswith("/commits/"):
            sha=path.split("/")[2]
            return {"check_runs":[copy.deepcopy(v) for v in self.rows.values() if v["head_sha"]==sha]}
        i=int(path.split("/")[-1])
        if method == "PATCH":
            if not self.reject_patch: self.rows[i].update(copy.deepcopy(payload))
            if self.lose_patch:
                self.lose_patch=False
                raise ReportError("api_request_failed")
        return copy.deepcopy(self.rows[i])

class ChecksTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.q=AcceptanceQueue(self.root/"q.sqlite")
        self.api=FakeAPI();self.now=100
        self.reporter=Reporter(self.q,self.api,clock=lambda:self.now)
        self.q.enqueue(job(),"1")
    def state(self,sha=H):
        with self.q.connect() as db:
            return db.execute("SELECT phase,remote_id,delivered,error FROM ci_check_reports WHERE sha=?",(sha,)).fetchone()
    def terminal(self,status="success"):
        self.q.claim();self.q.finish(H,{**receipt(),"status":status})
    def test_lifecycle_and_exact_sha(self):
        self.reporter.sync_once();self.assertEqual(self.api.rows[1]["status"],"queued")
        self.q.claim();self.reporter.sync_once();self.assertEqual(self.api.rows[1]["status"],"in_progress")
        self.q.finish(H,receipt());self.reporter.sync_once()
        self.assertEqual(self.api.rows[1]["conclusion"],"success")
        self.assertIn("integration_eligible=false",self.api.rows[1]["output"]["summary"])
        before=len(self.api.calls);self.reporter.sync_once();self.assertEqual(before,len(self.api.calls))
    def test_lost_create_response_reconciles_without_duplicate(self):
        self.api.lose_create=True;self.reporter.sync_once()
        self.now+=31;Reporter(self.q,self.api,clock=lambda:self.now).sync_once()
        self.assertIsNotNone(self.state()[2]);self.assertEqual(len(self.api.rows),1)
        self.assertEqual(sum(x[0]=="POST" for x in self.api.calls),1)
    def test_unknown_create_never_blindly_reposts(self):
        self.api.fail_create=True;self.reporter.sync_once();self.api.fail_create=False
        self.now+=31;self.reporter.sync_once()
        self.assertEqual(self.state()[3],"create_outcome_unresolved")
        self.assertEqual(sum(x[0]=="POST" for x in self.api.calls),1)
    def test_lost_patch_readback_recovers(self):
        self.reporter.sync_once();self.terminal();self.api.lose_patch=True
        self.reporter.sync_once();self.now+=31;self.reporter.sync_once()
        self.assertIsNone(self.state()[3]);self.assertEqual(self.api.rows[1]["conclusion"],"success")
    def test_readback_mismatch_never_delivered(self):
        self.reporter.sync_once();old=self.state()[2];self.terminal();self.api.reject_patch=True
        self.reporter.sync_once();self.assertEqual(self.state()[2],old)
        self.assertEqual(self.state()[3],"readback_mismatch")
    def test_remote_identity_mismatch_zero_patch(self):
        self.reporter.sync_once();self.api.rows[1]["head_sha"]=H2;self.terminal()
        self.reporter.sync_once();self.assertEqual(self.state()[3],"remote_identity_mismatch")
        self.assertFalse(any(x[0]=="PATCH" for x in self.api.calls))
    def test_old_sha_cannot_set_new_sha_success(self):
        self.terminal();self.q.enqueue(job(H2),"2")
        self.reporter.sync_once();self.reporter.sync_once()
        self.assertEqual(self.api.rows[1]["head_sha"],H)
        self.assertEqual(self.api.rows[2]["head_sha"],H2)
        self.assertNotIn("conclusion",self.api.rows[2])
    def test_restart_reports_action_required(self):
        self.q.claim();AcceptanceQueue(self.q.path,recover_running=True)
        self.reporter.sync_once();self.assertEqual(self.api.rows[1]["conclusion"],"action_required")
    def test_cancel_race_reports_cancelled(self):
        self.q.claim();self.q.cancel(H);self.q.finish(H,receipt());self.reporter.sync_once()
        self.assertEqual(self.api.rows[1]["conclusion"],"cancelled")
    def test_terminal_mapping(self):
        for state,value in [("failed","failure"),("timed_out","timed_out"),("cancelled","cancelled"),("environment_error","action_required")]:
            self.assertEqual(payload_for(H,state,None,"marker")["conclusion"],value)
    def test_invalid_success_receipt_fails_closed(self):
        for change in [{"tests":0},{"tests":True},{"checkout_sha":H2},{"sha":H2},{"exit_code":False},{"integration_eligible":True},{"status":"failed"}]:
            with self.subTest(change=change):
                self.assertEqual(payload_for(H,"success",{**receipt(),**change},"marker")["conclusion"],"action_required")
    def test_logs_and_secrets_not_uploaded(self):
        value=payload_for(H,"success",{**receipt(),"reason":"PRIVATE","log":"/SECRET","output":"TOKEN"},"marker")
        for secret in ["PRIVATE","SECRET","TOKEN"]: self.assertNotIn(secret,json.dumps(value))
    def test_redirect_denied(self):
        with self.assertRaises(ReportError): NoRedirect().redirect_request(None,None,302,"",{},"https://other.invalid")
    def test_token_permissions_and_symlink(self):
        path=self.root/"token";path.write_text("fixture-only");path.chmod(0o644)
        with self.assertRaises(ReportError): API(path)
        path.chmod(0o600);self.assertEqual(API(path).token,"fixture-only")
        link=self.root/"link";link.symlink_to(path)
        with self.assertRaises(OSError): API(link)
    def test_api_endpoint_scope(self):
        path=self.root/"token";path.write_text("fixture-only");path.chmod(0o600)
        api=API(path)
        for endpoint in ["/pulls/1/merge","https://other.invalid/","/check-runs/../../keys"]:
            with self.assertRaises(ReportError): api.request("POST",endpoint,{})
    def test_malformed_output_fails_closed(self):
        self.reporter.sync_once();self.terminal()
        for value in [None, [], {"summary": None}, {"summary": 2}, {"summary": []}]:
            with self.subTest(value=value):
                self.api.rows[1]["output"]=value;self.now+=31
                self.reporter.sync_once()
                self.assertEqual(self.state()[3],"remote_identity_mismatch")
    def test_reporter_failure_does_not_interrupt_execution(self):
        import contextlib
        import io
        from scripts.ci.gitee_webhook_ci import Application
        from unittest.mock import Mock
        env={"GITEE_CI_MODE":"ci-only","GITEE_CI_RUNNER":"/bin/true",
             "GITEE_CI_DB":str(self.root/"app.sqlite"),"GITEE_CI_LOG_DIR":str(self.root/"logs")}
        with patch.dict(os.environ,env,clear=True): app=Application(receiver_enabled=False)
        app.queue.enqueue(job(),"1")
        app.reporter=Mock();app.reporter.sync_once.side_effect=RuntimeError("PRIVATE")
        out=io.StringIO()
        with patch("gitee_ci_acceptance.Executor.execute",return_value=receipt()), contextlib.redirect_stdout(out):
            self.assertTrue(app.execute_once())
        self.assertEqual(app.queue.result(H)["status"],"success")
        self.assertNotIn("PRIVATE",out.getvalue())

    def test_ambiguous_marker_fails_closed(self):
        self.api.lose_create=True;self.reporter.sync_once();self.api.rows[2]={**self.api.rows[1],"id":2}
        self.now+=31;self.reporter.sync_once()
        self.assertEqual(self.state()[3],"create_outcome_unresolved")

if __name__ == "__main__": unittest.main()
