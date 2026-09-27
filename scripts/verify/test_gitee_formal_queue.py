import copy
import json
from pathlib import Path
import tempfile
import unittest
import urllib.parse
from unittest.mock import Mock
from scripts.ci.gitee_formal_queue import FormalQueue, FormalReporter, execute_once, job_key, IDENTITY_KEYS, CHECKS
from scripts.ci.gitee_gate_plan import plan, digest
from scripts.verify.test_gitee_ci_checks import FakeAPI


class FormalFakeAPI(FakeAPI):
    omit_pr=False
    def request(self,method,path,payload=None):
        value=super().request(method,path,payload)
        if method=='GET' and path.startswith('/commits/') and 'pull_request_id=' in path:
            pr=int(urllib.parse.parse_qs(urllib.parse.urlsplit(path).query)['pull_request_id'][0])
            value['check_runs']=[x for x in value['check_runs'] if x.get('pull_request_id')==pr]
        if self.omit_pr:
            if isinstance(value,dict) and 'check_runs' in value:
                for row in value['check_runs']:row.pop('pull_request_id',None)
            elif isinstance(value,dict):value.pop('pull_request_id',None)
        return value


def candidate(base='b'*40,pr=1,observed=100):
    p=plan(head='a'*40,base=base,source_branch='fix/unit',pr_number=pr,paths=['docs/unit.md'])
    p['platform_snapshot']={**{k:p[k] for k in IDENTITY_KEYS},'pr_id':123+pr,
        'pr_identity_verified':True,'remote_refs_verified':True,'observed_finished_at':observed}
    p.pop('plan_sha256');p['plan_sha256']=digest(p)
    return p


def receipt(p):
    return {**{k:p[k] for k in IDENTITY_KEYS},'plan_sha256':p['plan_sha256'],
        'status':'success','integration_eligible':False,
        'checks':[{'name':x['name'],'mode':x['mode'],'status':'success','tests':2} for x in p['checks']]}


def failure_candidate(reason='baseline_not_ancestor',base='b'*40,pr=1,observed=100,head='a'*40):
    p=plan(head=head,base=base,source_branch='fix/unit',pr_number=pr,paths=(),preparation_failure=reason)
    p['platform_snapshot']={**{k:p[k] for k in IDENTITY_KEYS},'pr_id':123+pr,
        'pr_identity_verified':True,'remote_refs_verified':True,'observed_finished_at':observed}
    p.pop('plan_sha256');p['plan_sha256']=digest(p)
    return p


def failure_receipt(p):
    return {**{k:p[k] for k in IDENTITY_KEYS},'plan_sha256':p['plan_sha256'],
        'status':'environment_error','checks':[],'integration_eligible':False}


class FormalQueueTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.q=FormalQueue(Path(self.tmp.name)/'q.sqlite');self.p=candidate()
        self.key,_=self.q.enqueue(self.p,'1');self.api=FormalFakeAPI();self.now=100
        self.refresh=lambda p:p['platform_snapshot']
        self.reporter=FormalReporter(self.q,self.api,lambda p:self.refresh(p),clock=lambda:self.now)

    def publish_all(self):
        for _ in range(4):self.reporter.sync_once()

    def terminal(self):
        self.q.claim();self.q.finish(self.key,receipt(self.p))

    def test_dedupe_ignores_observation_timestamp(self):
        key,inserted=self.q.enqueue(candidate(observed=200),'2')
        self.assertEqual(key,self.key);self.assertFalse(inserted)

    def test_base_and_pr_are_distinct_jobs(self):
        for p in [candidate(base='c'*40),candidate(pr=2)]:self.assertNotEqual(job_key(p),self.key)

    def test_delivery_replay_rejected(self):
        with self.assertRaises(ValueError):self.q.enqueue(candidate(base='c'*40),'1')

    def test_claim_serializes(self):
        self.q.enqueue(candidate(base='c'*40),'2')
        self.assertIsNotNone(self.q.claim());self.assertIsNone(self.q.claim())

    def test_restart_does_not_requeue_running(self):
        self.q.claim();FormalQueue(self.q.path,recover_running=True)
        with self.q.connect() as db:self.assertEqual(db.execute('SELECT status FROM formal_jobs').fetchone()[0],'environment_error')

    def test_cancel_race_cannot_succeed(self):
        self.q.claim();self.q.cancel(self.key);self.q.finish(self.key,receipt(self.p));self.publish_all()
        self.assertTrue(all(x['conclusion']=='cancelled' for x in self.api.rows.values()))

    def test_invalid_success_receipts_rejected(self):
        self.q.claim()
        variants=[]
        for key,value in [('base_sha','c'*40),('plan_sha256','bad'),('integration_eligible',True),('checks',[])]:
            r=receipt(self.p);r[key]=value;variants.append(r)
        r=receipt(self.p);r['checks'][2]['tests']=0;variants.append(r)
        r=receipt(self.p);r['checks'][2]['tests']=True;variants.append(r)
        for r in variants:
            with self.subTest(r=r),self.assertRaises(ValueError):self.q.finish(self.key,r)

    def test_four_independent_checks_bound_to_pr_and_base(self):
        self.terminal();self.publish_all()
        self.assertEqual({x['name'] for x in self.api.rows.values()},set(CHECKS))
        for x in self.api.rows.values():
            self.assertEqual(x['conclusion'],'success');self.assertEqual(x['pull_request_id'],124)
            self.assertIn(self.p['base_sha'],x['output']['summary'])

    def test_merged_success_restores_previously_invalidated_checks(self):
        self.terminal();self.refresh=lambda p:{};self.publish_all();self.now+=31
        self.refresh=lambda p:{**{k:p[k] for k in IDENTITY_KEYS},'pr_id':124,
                              'historical_merged':True,'merged_at':'2026-09-23'}
        self.publish_all()
        self.assertTrue(all(x['conclusion']=='success' for x in self.api.rows.values()))
        self.now+=31;self.publish_all()
        self.assertEqual(sum(x[0]=='POST' for x in self.api.calls),4)

    def test_merged_flag_cannot_promote_missing_failed_or_mismatched_receipt(self):
        from scripts.ci.gitee_formal_queue import payload
        current={**{k:self.p[k] for k in IDENTITY_KEYS},'pr_id':124,
                 'historical_merged':True,'merged_at':'2026-09-23'}
        for state in ['running','pending','failed','cancelled','environment_error']:
            self.assertEqual(payload(self.p,state,receipt(self.p),CHECKS[0],'m',current)['conclusion'],'action_required')
        for key,value in [('head_sha','c'*40),('base_sha','c'*40),('plan_sha256','bad'),('checks',[]),('integration_eligible',True)]:
            r=receipt(self.p);r[key]=value
            self.assertEqual(payload(self.p,'success',r,CHECKS[0],'m',current)['conclusion'],'action_required')
        for key,value in [('pr_id',999),('head_sha','c'*40),('base_sha','c'*40),('merged_at',None)]:
            c={**current,key:value}
            self.assertEqual(payload(self.p,'success',receipt(self.p),CHECKS[0],'m',c)['conclusion'],'action_required')

    def test_main_drift_revokes_previous_success(self):
        self.terminal();self.publish_all();self.now+=31
        self.refresh=lambda p:{**p['platform_snapshot'],'base_sha':'c'*40}
        self.publish_all()
        self.assertTrue(all(x['conclusion']=='action_required' for x in self.api.rows.values()))

    def test_unknown_snapshot_never_success(self):
        self.terminal();self.refresh=lambda p:{};self.publish_all()
        self.assertTrue(all(x['conclusion']=='action_required' for x in self.api.rows.values()))

    def test_lost_create_no_duplicate_post(self):
        self.api.lose_create=True;self.reporter.sync_once();self.now+=31
        self.publish_all()
        first_posts=[x for x in self.api.calls if x[0]=='POST' and x[2]['name']==CHECKS[0]]
        self.assertEqual(len(first_posts),1)

    def test_unknown_create_not_reposted(self):
        self.api.fail_create=True;self.reporter.sync_once();self.now+=31;self.api.fail_create=False
        self.reporter.sync_once()
        self.assertEqual(sum(x[0]=='POST' for x in self.api.calls),1)

    def test_wrong_pr_readback_is_not_delivered(self):
        self.reporter.sync_once();self.api.rows[1]['pull_request_id']=999
        self.terminal();self.now+=31;self.api.reject_patch=True;self.reporter.sync_once()
        with self.q.connect() as db:
            row=db.execute('SELECT error FROM formal_reports WHERE name=?',(CHECKS[0],)).fetchone()
        self.assertEqual(row[0],'readback_mismatch')

    def test_real_gitee_shape_uses_filtered_pr_association(self):
        self.api.omit_pr=True;self.terminal();self.publish_all()
        with self.q.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM formal_reports WHERE delivered IS NOT NULL AND error IS NULL').fetchone()[0],4)
        self.assertTrue(any('&pull_request_id=124' in x[1] for x in self.api.calls))

    def test_missing_filtered_association_never_delivered(self):
        original=self.api.request
        def detached(method,path,payload=None):
            if '&pull_request_id=' in path:return {'check_runs':[]}
            return original(method,path,payload)
        self.api.request=detached;self.terminal();self.reporter.sync_once()
        with self.q.connect() as db:
            row=db.execute('SELECT delivered,error FROM formal_reports WHERE name=?',(CHECKS[0],)).fetchone()
        self.assertIsNone(row[0]);self.assertEqual(row[1],'pr_association_readback_mismatch')

    def test_worker_exception_is_terminal(self):
        worker=Mock();worker.execute_plan.side_effect=RuntimeError('private detail')
        self.assertTrue(execute_once(self.q,worker,self.refresh));self.publish_all()
        self.assertTrue(all(x['conclusion']=='action_required' for x in self.api.rows.values()))
        self.assertNotIn('private detail',json.dumps(self.api.calls))

    def test_malformed_result_does_not_strand_running_job(self):
        worker=Mock();worker.execute_plan.return_value={'status':'success'}
        execute_once(self.q,worker,self.refresh)
        with self.q.connect() as db:
            self.assertEqual(db.execute('SELECT status FROM formal_jobs').fetchone()[0],'environment_error')

    def isolated(self):
        self.counter=getattr(self,'counter',0)+1
        queue=FormalQueue(Path(self.tmp.name)/('isolated-'+str(self.counter)+'.sqlite'))
        api=FormalFakeAPI()
        return queue,api,FormalReporter(queue,api,lambda p:p['platform_snapshot'],clock=lambda:self.now)

    def test_preparation_failure_is_reported_red_and_never_executed(self):
        queue,api,reporter=self.isolated();p=failure_candidate()
        key,inserted=queue.enqueue(p,'9');self.assertTrue(inserted);queue.fail(key,failure_receipt(p))
        worker=Mock();self.assertFalse(execute_once(queue,worker,self.refresh));worker.execute_plan.assert_not_called()
        for _ in range(4):reporter.sync_once()
        self.assertEqual({x['name'] for x in api.rows.values()},set(CHECKS))
        for x in api.rows.values():
            self.assertEqual((x['status'],x['conclusion']),('completed','action_required'))
            self.assertEqual(x['head_sha'],'a'*40);self.assertEqual(x['pull_request_id'],124)
            self.assertIn('preparation_failure=baseline_not_ancestor',x['output']['summary'])
        with queue.connect() as db:
            self.assertEqual(db.execute('SELECT status FROM formal_jobs').fetchone()[0],'environment_error')

    def test_preparation_failure_cannot_be_success_skip_or_foreign(self):
        queue,api,reporter=self.isolated();p=failure_candidate();key,_=queue.enqueue(p,'9')
        for name,value in [('status','success'),('status','cancelled'),('integration_eligible',True),
                           ('base_sha','c'*40),('head_sha','c'*40),('plan_sha256','bad'),('plan_sha256',None)]:
            with self.subTest(field=(name,value)),self.assertRaises(ValueError):
                receipt=failure_receipt(p);receipt[name]=value;queue.fail(key,receipt)
        queue.fail(key,failure_receipt(p))
        for _ in range(4):reporter.sync_once()
        self.assertTrue(all(x['conclusion']=='action_required' for x in api.rows.values()))

    def test_old_head_failure_cannot_overwrite_new_head_success(self):
        queue,api,reporter=self.isolated()
        new=candidate()                                    # head a*40, the current PR head
        old=failure_candidate(head='c'*40)                 # same PR and base, superseded head
        self.assertEqual(new['platform_snapshot']['pr_id'],old['platform_snapshot']['pr_id'])
        key,_=queue.enqueue(new,'1');queue.claim();queue.finish(key,receipt(new))
        for _ in range(4):reporter.sync_once()
        settled={x['id']:(x['head_sha'],x['conclusion']) for x in api.rows.values()}
        failure_key,_=queue.enqueue(old,'2');queue.fail(failure_key,failure_receipt(old))
        for _ in range(4):reporter.sync_once()
        # The superseded head gets its own red checks; the current head keeps green ones.
        for identifier,(head,conclusion) in settled.items():
            self.assertEqual((api.rows[identifier]['head_sha'],api.rows[identifier]['conclusion']),(head,conclusion))
        self.assertEqual(len(api.rows),8)
        by_head={}
        for row in api.rows.values():by_head.setdefault(row['head_sha'],set()).add(row['conclusion'])
        self.assertEqual(by_head,{'a'*40:{'success'},'c'*40:{'action_required'}})
        # No check was ever created or patched against the wrong commit.
        for method,path,payload in api.calls:
            sha=(payload or {}).get('head_sha') or (path.split('/')[2] if path.startswith('/commits/') else None)
            if sha:self.assertIn(sha,('a'*40,'c'*40))

    def test_fail_refuses_runnable_and_already_claimed_jobs(self):
        queue,api,reporter=self.isolated()
        with self.assertRaises(ValueError):queue.fail(self.key,failure_receipt(self.p))
        p=failure_candidate();key,_=queue.enqueue(p,'9')
        with self.assertRaises(ValueError):queue.fail(key,failure_receipt(self.p))
        queue.claim()
        with self.assertRaises(ValueError):queue.fail(key,failure_receipt(p))

    def test_final_readback_rejects_malformed_and_wrong_identity(self):
        self.terminal();self.reporter.sync_once()
        desired=self.api.rows[1]
        for value in [None, [], {**desired,'id':99}, {**desired,'name':'wrong'},
                      {**desired,'head_sha':'c'*40}]:
            with self.subTest(value=value):
                self.assertFalse(FormalReporter.matches(value,desired,1))

    def test_cursor_visits_jobs_beyond_first_page(self):
        for number in range(2,131): self.q.enqueue(candidate(pr=number),str(number))
        # Mark page one temporarily throttled. A durable cursor must reach page
        # two without discarding the old page; restart keeps the position.
        with self.q.connect() as db:
            for key, in db.execute('SELECT id FROM formal_jobs ORDER BY rowid LIMIT 128').fetchall():
                for name in CHECKS:
                    db.execute("INSERT INTO formal_reports(job,name,marker,phase,retry_at) VALUES (?,?,?,'new',999)",
                               (key,name,'fixture-'+key+name))
        self.assertFalse(self.reporter.sync_once())
        other=FormalReporter(self.q,self.api,self.refresh,clock=lambda:self.now)
        self.assertTrue(other.sync_once())
        self.assertEqual(self.api.rows[1]['pull_request_id'],252)
        with self.q.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM formal_jobs').fetchone()[0],130)

    def test_targeted_report_ignores_historical_cursor(self):
        newer=candidate(pr=2);key,_=self.q.enqueue(newer,'2')
        self.refresh=Mock(side_effect=lambda p:p['platform_snapshot'])
        self.reporter.sync_once(job=key)
        self.assertEqual(self.api.rows[1]['pull_request_id'],125)
        self.assertEqual(self.refresh.call_count,1)
        with self.q.connect() as db:
            self.assertEqual(db.execute('SELECT position FROM formal_report_cursor').fetchone()[0],0)

    def test_history_refresh_has_constant_budget_and_progress(self):
        self.terminal();self.publish_all()
        other=candidate(pr=2);self.q.enqueue(other,'2')
        self.now+=31
        self.refresh=Mock(side_effect=lambda p:p['platform_snapshot'])
        self.reporter.sync_once()
        self.assertEqual(self.refresh.call_count,1)
        self.reporter.sync_once()
        self.assertEqual(self.api.rows[5]['pull_request_id'],125)

    def test_completed_job_wakes_reports_without_throttle_delay(self):
        self.publish_all()
        self.terminal()
        self.publish_all()
        self.assertTrue(all(x['conclusion']=='success' for x in self.api.rows.values()))

    def test_only_verified_merged_success_gets_longer_poll(self):
        self.terminal()
        self.refresh=lambda p:{**{k:p[k] for k in IDENTITY_KEYS},'pr_id':124,
                              'historical_merged':True,'merged_at':'2026-09-23'}
        self.publish_all()
        with self.q.connect() as db:
            self.assertEqual(db.execute('SELECT DISTINCT retry_at FROM formal_reports').fetchall(),[(400.0,)])

    def test_worker_to_reporter_lifecycle(self):
        worker=Mock();worker.execute_plan.return_value=receipt(self.p)
        self.assertTrue(execute_once(self.q,worker,self.refresh));self.assertFalse(execute_once(self.q,worker,self.refresh))
        self.publish_all();self.assertEqual(len(self.api.rows),4)
        self.assertTrue(all(x['conclusion']=='success' for x in self.api.rows.values()))


if __name__=='__main__':unittest.main()
