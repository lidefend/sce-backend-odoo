import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from scripts.ops import agent_dispatch_inbox as m

class InboxTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.repo = self.base / 'repo'; self.repo.mkdir()
        def git(*a):
            subprocess.run(['git','-C',str(self.repo),*a],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        git('init','-b','fix/test');git('config','user.name','Test');git('config','user.email','test@example.invalid')
        (self.repo/'run.json').write_text(json.dumps({'id':'TEST','branch':'fix/test'}))
        (self.repo/'evidence.txt').write_text('actual evidence')
        git('add','.');git('commit','-m','test')
        self.root = self.base/'inbox'
        m.initialize(self.root, {'pilot':str(self.repo)}, '/bin/codex')
        m.takeover(self.root, 'test-dispatcher', '2026-10-17T00:00:00Z')
        self.authorization=m.authorize(self.root,self.authorization_spec())
        self.report = dict(task_id='TEST',run='run.json',status='paused',summary='test',next_step='review',evidence=['evidence.txt'],blockers=[],resources=['worktree:test'])
    def authorization_spec(self,status='active'):
        spec={'id':'test-auth','source':'owner test instruction','granted_at':'2026-10-17T00:00:00Z',
              'status':status,'scope':['test task scope'],'allowed_actions':['modify test files','run tests','local commit'],
              'exclusions':['production'],'revocation':{'conditions':['owner revokes in writing'],'by':'owner','recorded_at':'2026-10-17T00:00:00Z'}}
        if status=='revoked':
            spec.update(revoked_at='2026-10-17T01:00:00Z',revoked_reason='test revocation')
        return spec
    def submit(self): return m.submit(self.root,'pilot',self.report)
    def review_success(self,args,**kwargs):
        Path(args[args.index('--output-last-message')+1]).write_text('待调度确认：草案')
        return subprocess.CompletedProcess(args,0,json.dumps({'item':{'type':'agent_message','text':'draft'}}),'')
    def make_repo(self,name):
        repo=self.base/name;repo.mkdir()
        def git(*a):subprocess.run(['git','-C',str(repo),*a],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        git('init','-b','fix/test');git('config','user.name','Test');git('config','user.email','test@example.invalid')
        (repo/'run.json').write_text(json.dumps({'id':'TEST','branch':'fix/test'}))
        (repo/'evidence.txt').write_text('actual evidence')
        git('add','.');git('commit','-m','test')
        return repo
    def legacy_event(self):
        identity={'repository':str(self.repo),'head':m.git(self.repo,'rev-parse','HEAD'),
                  'branch':m.git(self.repo,'branch','--show-current'),
                  'worktree_digest':m.worktree_digest(self.repo),
                  'dirty':m.git(self.repo,'status','--porcelain=v1','--untracked-files=all')}
        payload={'schema':1,'lane':'pilot','identity':identity,'report':dict(self.report),
                 'run':m.evidence(self.repo,'run.json'),'evidence':[m.evidence(self.repo,'evidence.txt')]}
        event_id=m.digest(m.encode(payload))
        m.write(self.root/'events'/f'{event_id}.json',{'id':event_id,'received_at':m.now(),'payload':payload})
        m.write(self.root/'reviews'/f'{event_id}.json',{'status':'pending','attempts':0})
        return event_id
    def test_deduplicate(self):
        self.assertEqual(self.submit(),self.submit());self.assertEqual(len(m.status(self.root)['receipts']),1)
    def test_unknown_lane(self):
        with self.assertRaises(KeyError):m.submit(self.root,'demo',self.report)
    def test_task_mismatch(self):
        self.report['task_id']='OTHER'
        with self.assertRaises(ValueError):self.submit()
    def test_no_missing_evidence(self):
        self.report['evidence']=['missing']
        with self.assertRaises(ValueError):self.submit()
    def test_no_path_escape(self):
        self.report['evidence']=['../secret']
        with self.assertRaises(ValueError):self.submit()
    def test_no_symlink(self):
        (self.repo/'link').symlink_to(self.repo/'evidence.txt');self.report['evidence']=['link']
        with self.assertRaises(ValueError):self.submit()
    def test_no_world_readable_root(self):
        self.root.chmod(0o755)
        with self.assertRaises(ValueError):self.submit()
    def test_corrupted_event(self):
        eid=self.submit();p=self.root/'events'/f'{eid}.json';e=m.read(p);e['payload']['report']['summary']='tampered';m.write(p,e)
        with self.assertRaises(ValueError):m.check_event(e)
    def test_dirty_content_drift(self):
        (self.repo/'evidence.txt').write_text('dirty1');eid=self.submit()
        (self.repo/'evidence.txt').write_text('dirty2')
        self.assertEqual(m.review_one(self.root)['status'],'blocked')
    def test_failure_not_success_and_no_retry(self):
        self.submit()
        def fail(*a,**kw):return subprocess.CompletedProcess(a[0],2,'','failed')
        self.assertEqual(m.review_one(self.root,fail)['status'],'blocked')
        self.assertEqual(m.review_one(self.root,fail)['status'],'idle')
    def test_review_is_draft_not_execution(self):
        self.submit()
        def success(args,**kw):
            self.assertIn('read-only',args);self.assertIn('shell_tool',args);self.assertIn('hooks',args)
            Path(args[args.index('--output-last-message')+1]).write_text('待调度确认：下一任务草案')
            return subprocess.CompletedProcess(args,0,json.dumps({'item':{'type':'agent_message','text':'draft'}}),'')
        result=m.review_one(self.root,success)
        self.assertEqual(result['status'],'proposal_ready');self.assertFalse(result['background_auto_execution'])
        self.assertEqual(m.review_one(self.root)['status'],'idle')
    def test_review_time_mutation_blocks(self):
        self.submit()
        def changed(args,**kw):
            Path(args[args.index('--output-last-message')+1]).write_text('draft')
            (self.repo/'evidence.txt').write_text('changed')
            return subprocess.CompletedProcess(args,0,json.dumps({'item':{'type':'agent_message','text':'draft'}}),'')
        self.assertEqual(m.review_one(self.root,changed)['status'],'blocked')
    def test_no_empty_model_result(self):
        self.submit()
        self.assertEqual(m.review_one(self.root,lambda *a,**k:subprocess.CompletedProcess(a[0],0,'',''))['status'],'blocked')
    def test_live_reviewer_serializes_queue(self):
        eid=self.submit()
        m.write(self.root/'reviews'/f'{eid}.json',dict(status='reviewing',pid=os.getpid(),process_identity=m.process_identity(os.getpid()),attempts=1))
        self.assertEqual(m.review_one(self.root)['status'],'busy')
    def test_dead_reviewer_blocks(self):
        from unittest.mock import patch
        eid=self.submit()
        m.write(self.root/'reviews'/f'{eid}.json',dict(status='reviewing',pid=99999999,attempts=1))
        with patch.object(m.os,'kill',side_effect=ProcessLookupError):
            self.assertEqual(m.review_one(self.root)['status'],'idle')
        self.assertEqual(m.status(self.root)['receipts'][0]['status'],'blocked')
    def test_retry_requires_recovery_fact(self):
        eid=self.submit()
        with self.assertRaises(ValueError):m.retry(self.root,eid,'')
        with self.assertRaises(ValueError):m.retry(self.root,eid,'restored')
        m.review_one(self.root,lambda *a,**k:subprocess.CompletedProcess(a[0],1,'','failed'))
        m.retry(self.root,eid,'model authentication restored')
        self.assertEqual(m.status(self.root)['receipts'][0]['status'],'pending')
    def test_changed_lane_registration_blocks(self):
        self.submit();cfg=m.read(self.root/'config.json');cfg['repositories']['pilot']='/tmp/other';m.write(self.root/'config.json',cfg)
        self.assertEqual(m.review_one(self.root)['status'],'blocked')
    def test_retry_does_not_accept_old_output(self):
        eid=self.submit()
        def fail_with_output(args,**kw):
            Path(args[args.index('--output-last-message')+1]).write_text('old')
            return subprocess.CompletedProcess(args,1,'','failure')
        self.assertEqual(m.review_one(self.root,fail_with_output)['status'],'blocked')
        m.retry(self.root,eid,'provider recovered')
        self.assertEqual(m.review_one(self.root,lambda *a,**k:subprocess.CompletedProcess(a[0],0,'',''))['status'],'blocked')
    def test_missing_state_is_blocked_not_queue_crash(self):
        eid=self.submit();(self.root/'reviews'/f'{eid}.json').unlink()
        self.assertEqual(m.status(self.root)['receipts'][0]['status'],'blocked')
        self.assertEqual(m.review_one(self.root)['status'],'idle')
    def test_reused_pid_is_not_active_review(self):
        eid=self.submit()
        m.write(self.root/'reviews'/f'{eid}.json',dict(status='reviewing',pid=os.getpid(),process_identity='old',attempts=1))
        self.assertEqual(m.review_one(self.root)['status'],'idle')
        self.assertEqual(m.status(self.root)['receipts'][0]['status'],'blocked')
    def test_disabled_code_mode_notice_is_not_tool_use(self):
        self.submit()
        def success(args,**kw):
            Path(args[args.index('--output-last-message')+1]).write_text('draft')
            notice='Code Mode is unavailable because code-mode host is disabled. Code mode will fail closed; enable `features.code_mode_host` and install `codex-code-mode-host`.'
            events=[{'item':{'type':'error','message':notice}},{'item':{'type':'agent_message'}}]
            return subprocess.CompletedProcess(args,0,'\n'.join(json.dumps(e) for e in events),'')
        result=m.review_one(self.root,success)
        self.assertEqual(result['status'],'proposal_ready');self.assertTrue(result['disabled_tool_notice'])
    def test_tool_item_blocks_even_with_text_output(self):
        self.submit()
        def bad(args,**kw):
            Path(args[args.index('--output-last-message')+1]).write_text('draft')
            return subprocess.CompletedProcess(args,0,json.dumps({'item':{'type':'command_execution'}}),'')
        self.assertEqual(m.review_one(self.root,bad)['status'],'blocked')
    def test_generic_error_not_whitelisted(self):
        self.submit()
        def bad(args,**kw):
            Path(args[args.index('--output-last-message')+1]).write_text('draft')
            return subprocess.CompletedProcess(args,0,json.dumps({'item':{'type':'error','message':'provider failed'}}),'')
        self.assertEqual(m.review_one(self.root,bad)['status'],'blocked')
    def test_top_level_failure_and_malformed_stream_block(self):
        for bad_event in ('{broken', json.dumps({'type':'error'}), json.dumps({'type':'turn.failed'})):
            with self.subTest(event=bad_event):
                self.report['summary']=bad_event
                self.submit()
                def bad(args,**kw):
                    Path(args[args.index('--output-last-message')+1]).write_text('draft')
                    return subprocess.CompletedProcess(args,0,json.dumps({'item':{'type':'agent_message'}})+'\n'+bad_event,'')
                self.assertEqual(m.review_one(self.root,bad)['status'],'blocked')
    def test_empty_required_field(self):
        self.report['summary']=''
        with self.assertRaises(ValueError):self.submit()

    def test_takeover_records_one_current_dispatcher_and_history(self):
        first=m.takeover(self.root,'dispatcher-a','2026-10-17T01:00:00+08:00')
        self.assertEqual(first['takeover_at'],'2026-10-16T17:00:00+00:00')
        m.takeover(self.root,'dispatcher-a','2026-10-17T01:00:00+08:00')
        self.assertEqual([x['id'] for x in m.status(self.root)['dispatcher_history']],['test-dispatcher'])
        m.takeover(self.root,'dispatcher-b','2026-10-17T02:00:00+08:00')
        result=m.status(self.root)
        self.assertEqual(result['dispatcher']['id'],'dispatcher-b')
        self.assertEqual([x['id'] for x in result['dispatcher_history']],['test-dispatcher','dispatcher-a'])

    def test_takeover_rejects_invalid_identity_and_time(self):
        with self.assertRaises(ValueError):m.takeover(self.root,'bad id')
        with self.assertRaises(ValueError):m.takeover(self.root,'dispatcher-c','2026-10-17T00:00:00')

    def test_bind_lane_requires_verified_git_root(self):
        m.bind_lane(self.root,'frontend',self.repo)
        other=self.make_repo('other-repo')
        with self.assertRaises(ValueError):m.bind_lane(self.root,'frontend',other)
        m.bind_lane(self.root,'frontend',other,replace=True)
        self.assertEqual(m.status(self.root)['lanes']['frontend'],str(other))
        not_git=self.base/'not-git';not_git.mkdir()
        with self.assertRaises(ValueError):m.bind_lane(self.root,'environment',not_git)
        link=self.base/'repo-link';link.symlink_to(self.repo,target_is_directory=True)
        with self.assertRaises(ValueError):m.bind_lane(self.root,'environment',link)

    def test_bind_lane_requires_registered_dispatcher(self):
        root=self.base/'unbound-inbox'
        m.initialize(root,{'pilot':str(self.repo)},'/bin/codex')
        with self.assertRaises(ValueError):m.bind_lane(root,'frontend',self.repo)

    def test_task_assignment_and_acknowledgement_are_recorded(self):
        spec={'task_id':'TASK-1','lane':'pilot','objective':'verify','scope':['one'],'acceptance':['two']}
        first=m.assign(self.root,spec)
        self.assertEqual(first,m.assign(self.root,spec))
        with self.assertRaises(ValueError):m.assign(self.root,{**spec,'objective':'changed'})
        with self.assertRaises(ValueError):m.ack(self.root,'TASK-1','executor-a','declined','')
        accepted=m.ack(self.root,'TASK-1','executor-a','accepted')
        self.assertEqual(accepted['status'],'acknowledged')
        task_row=[t for t in m.status(self.root)['tasks'] if t['task_id']=='TASK-1'][0]
        self.assertEqual(task_row['execution_authority']['authorization_id'],'test-auth')
        self.assertIn('local commit',task_row['execution_authority']['allowed_actions'])
        self.assertIn('不是二次授权',task_row['execution_authority']['note'])
        self.assertEqual(len(accepted['acknowledgements']),1)
        self.assertEqual(len(m.ack(self.root,'TASK-1','executor-a','accepted')['acknowledgements']),1)
        declined=m.ack(self.root,'TASK-1','executor-a','declined','not ready')
        self.assertEqual(declined['status'],'declined')

    def test_task_update_refreshes_stale_authorization_reference(self):
        spec={'task_id':'TASK-REFRESH','lane':'pilot','objective':'verify','scope':['one'],'acceptance':['two']}
        task=m.assign(self.root,spec)
        stale=dict(task['authorization'])
        stale.pop('status'); stale.pop('scope')
        task['authorization']=stale
        m.write(m.task_path(self.root,'TASK-REFRESH'),task)
        refreshed=m.assign(self.root,{**spec,'authorization_ref':'test-auth'},update=True)
        self.assertEqual(refreshed['authorization'],m.authorization_reference(m.active_authorization(m.read(self.root/'config.json'))))
        self.assertIn('status',refreshed['authorization'])
        self.assertIn('scope',refreshed['authorization'])

    def test_task_ref_requires_lane_and_latest_acceptance(self):
        spec={'task_id':'TEST','lane':'pilot','objective':'verify','scope':['one'],'acceptance':['two']}
        m.assign(self.root,spec)
        m.ack(self.root,'TEST','executor-a','accepted')
        report={**self.report,'task_ref':'TEST','executor':'executor-a'}
        self.submit()
        self.assertTrue(m.submit(self.root,'pilot',report))
        with self.assertRaises(ValueError):m.validate_task_ref(self.root,'demo',report)
        with self.assertRaises(ValueError):m.validate_task_ref(self.root,'pilot',{**report,'executor':'executor-b'})
        with self.assertRaises(ValueError):m.validate_task_ref(self.root,'pilot',{k:v for k,v in report.items() if k!='executor'})
        m.ack(self.root,'TEST','executor-a','declined','changed')
        with self.assertRaises(ValueError):m.validate_task_ref(self.root,'pilot',report)

    def test_supersedes_closes_prior_blocker_and_prevents_retry(self):
        first_report={**self.report,'summary':'first','blockers':['BLOCKER-1']}
        first_id=m.submit(self.root,'pilot',first_report)
        time.sleep(0.002)
        second_report={**self.report,'summary':'second','supersedes':first_id,'blockers':[],
                       'closed_blockers':[{'blocker':'BLOCKER-1','reason':'fixed','evidence':['evidence.txt']}]}
        second_id=m.submit(self.root,'pilot',second_report)
        rows={row['id']:row for row in m.status(self.root)['receipts']}
        self.assertEqual(rows[first_id]['superseded_by'],[second_id])
        self.assertEqual(m.review_one(self.root,self.review_success)['status'],'proposal_ready')
        rows={row['id']:row for row in m.status(self.root)['receipts']}
        self.assertEqual(rows[first_id]['status'],'superseded')
        self.assertEqual(rows[second_id]['status'],'proposal_ready')
        with self.assertRaises(ValueError):m.retry(self.root,first_id,'recovered')

    def test_supersedes_invalidates_existing_proposal_and_blocks_retry(self):
        first_id=self.submit()
        self.assertEqual(m.review_one(self.root,self.review_success)['status'],'proposal_ready')
        rows={row['id']:row for row in m.status(self.root)['receipts']}
        self.assertEqual(rows[first_id]['status'],'proposal_ready')
        time.sleep(0.002)
        second_id=m.submit(self.root,'pilot',{**self.report,'summary':'second','supersedes':first_id,'blockers':[]})
        rows={row['id']:row for row in m.status(self.root)['receipts']}
        self.assertEqual(rows[first_id]['status'],'superseded')
        self.assertEqual(rows[first_id]['superseded_by'],[second_id])
        self.assertFalse(rows[first_id]['background_auto_execution'])
        with self.assertRaises(ValueError):m.retry(self.root,first_id,'recovered')
        self.assertEqual(m.review_one(self.root,self.review_success)['status'],'proposal_ready')
        rows={row['id']:row for row in m.status(self.root)['receipts']}
        self.assertEqual(rows[second_id]['status'],'proposal_ready')

    def test_supersedes_requires_explicit_blocker_closure(self):
        first_report={**self.report,'summary':'first','blockers':['BLOCKER-1']}
        first_id=m.submit(self.root,'pilot',first_report)
        time.sleep(0.002)
        with self.assertRaises(ValueError):
            m.submit(self.root,'pilot',{**self.report,'summary':'missing','supersedes':first_id,'blockers':[]})
        with self.assertRaises(ValueError):
            m.submit(self.root,'pilot',{**self.report,'summary':'wrong-evidence','supersedes':first_id,'blockers':[],
                'closed_blockers':[{'blocker':'BLOCKER-1','reason':'fixed','evidence':['other.txt']}]})
        with self.assertRaises(ValueError):
            m.submit(self.root,'pilot',{**self.report,'summary':'both','supersedes':first_id,'blockers':['BLOCKER-1'],
                'closed_blockers':[{'blocker':'BLOCKER-1','reason':'fixed','evidence':['evidence.txt']}]})
        with self.assertRaises(ValueError):
            m.submit(self.root,'pilot',{**self.report,'summary':'unknown','supersedes':first_id,'blockers':[],
                'closed_blockers':[{'blocker':'BLOCKER-2','reason':'fixed','evidence':['evidence.txt']}]})
        repeated=m.submit(self.root,'pilot',{**self.report,'summary':'repeat','supersedes':first_id,'blockers':['BLOCKER-1']})
        self.assertTrue(repeated)
        with self.assertRaises(ValueError):
            m.submit(self.root,'pilot',{**self.report,'summary':'second-successor','supersedes':first_id,'blockers':['BLOCKER-1']})

    def test_supersedes_multiple_duplicate_receipts_invalidates_both(self):
        first_id=m.submit(self.root,'pilot',{**self.report,'summary':'first'})
        time.sleep(0.002)
        second_id=m.submit(self.root,'pilot',{**self.report,'summary':'second'})
        self.assertEqual(m.review_one(self.root,self.review_success)['status'],'proposal_ready')
        self.assertEqual(m.review_one(self.root,self.review_success)['status'],'proposal_ready')
        time.sleep(0.002)
        third_id=m.submit(self.root,'pilot',{**self.report,'summary':'third','supersedes':[first_id,second_id],'blockers':[]})
        rows={row['id']:row for row in m.status(self.root)['receipts']}
        self.assertEqual(rows[first_id]['status'],'superseded')
        self.assertEqual(rows[second_id]['status'],'superseded')
        self.assertEqual(rows[first_id]['superseded_by'],[third_id])
        self.assertEqual(rows[second_id]['superseded_by'],[third_id])
        self.assertFalse(rows[first_id]['background_auto_execution'])
        self.assertFalse(rows[second_id]['background_auto_execution'])
        with self.assertRaises(ValueError):m.retry(self.root,first_id,'recovered')
        with self.assertRaises(ValueError):m.retry(self.root,second_id,'recovered')
        self.assertEqual(rows[third_id]['status'],'pending')

    def test_supersedes_multiple_covers_every_prior_blocker(self):
        first_id=m.submit(self.root,'pilot',{**self.report,'summary':'first','blockers':['BLOCKER-1']})
        time.sleep(0.002)
        second_id=m.submit(self.root,'pilot',{**self.report,'summary':'second','blockers':['BLOCKER-2']})
        time.sleep(0.002)
        with self.assertRaises(ValueError):
            m.submit(self.root,'pilot',{**self.report,'summary':'partial','supersedes':[first_id,second_id],
                'blockers':['BLOCKER-1']})
        with self.assertRaises(ValueError):
            m.submit(self.root,'pilot',{**self.report,'summary':'partial-close','supersedes':[first_id,second_id],
                'blockers':[],'closed_blockers':[{'blocker':'BLOCKER-1','reason':'fixed','evidence':['evidence.txt']}]})
        third_id=m.submit(self.root,'pilot',{**self.report,'summary':'complete','supersedes':[first_id,second_id],
            'blockers':['BLOCKER-1','BLOCKER-2']})
        rows={row['id']:row for row in m.status(self.root)['receipts']}
        self.assertEqual(rows[first_id]['status'],'superseded')
        self.assertEqual(rows[second_id]['status'],'superseded')
        self.assertEqual(rows[third_id]['status'],'pending')

    def test_supersedes_rejects_empty_or_duplicate_ids(self):
        first_id=m.submit(self.root,'pilot',{**self.report,'summary':'first'})
        time.sleep(0.002)
        with self.assertRaises(ValueError):
            m.submit(self.root,'pilot',{**self.report,'summary':'empty','supersedes':[],'blockers':[]})
        with self.assertRaises(ValueError):
            m.submit(self.root,'pilot',{**self.report,'summary':'duplicate','supersedes':[first_id,first_id],'blockers':[]})

    def test_closed_blockers_require_supersedes(self):
        self.report['closed_blockers']=[{'blocker':'BLOCKER-1','reason':'fixed','evidence':['evidence.txt']}]
        with self.assertRaises(ValueError):self.submit()

    def test_evidence_nonempty_format_and_assertions(self):
        self.report['evidence']=[]
        with self.assertRaises(ValueError):self.submit()
        (self.repo/'empty.log').write_text('')
        self.report['evidence']=['empty.log']
        with self.assertRaises(ValueError):self.submit()
        (self.repo/'bad.json').write_text('{')
        self.report['evidence']=[{'path':'bad.json','format':'json'}]
        with self.assertRaises(ValueError):self.submit()
        (self.repo/'result.json').write_text(json.dumps({'status':'PASS'}))
        self.report['evidence']=[{'path':'result.json','format':'json','assert':['json:/status=FAIL']}]
        with self.assertRaises(ValueError):self.submit()
        self.report['evidence']=[{'path':'result.json','format':'json','assert':['json:/status=PASS']}]
        self.assertTrue(self.submit())

    def test_schema_one_receipt_remains_readable_and_reviewable(self):
        event_id=self.legacy_event()
        m.check_event(m.read(self.root/'events'/f'{event_id}.json'))
        self.assertEqual(m.status(self.root)['receipts'][0]['id'],event_id)
        self.assertEqual(m.review_one(self.root,self.review_success)['status'],'proposal_ready')

    def test_review_blocks_when_task_acceptance_is_revoked(self):
        spec={'task_id':'TEST','lane':'pilot','objective':'verify','scope':['one'],'acceptance':['two']}
        m.assign(self.root,spec)
        m.ack(self.root,'TEST','executor-a','accepted')
        m.submit(self.root,'pilot',{**self.report,'task_ref':'TEST','executor':'executor-a'})
        m.ack(self.root,'TEST','executor-a','declined','revoked')
        self.assertEqual(m.review_one(self.root,self.review_success)['status'],'blocked')

    def test_review_blocks_without_registered_dispatcher(self):
        root=self.base/'no-dispatcher'
        m.initialize(root,{'pilot':str(self.repo)},'/bin/codex')
        m.submit(root,'pilot',dict(self.report))
        result=m.review_one(root)
        self.assertEqual(result['status'],'blocked')
        self.assertFalse(result['background_auto_execution'])

    def test_assign_requires_registered_owner_authorization(self):
        root=self.base/'no-auth'
        m.initialize(root,{'pilot':str(self.repo)},'/bin/codex')
        m.takeover(root,'dispatcher-no-auth','2026-10-17T00:00:00Z')
        spec={'task_id':'TASK-NOAUTH','lane':'pilot','objective':'verify','scope':['one'],'acceptance':['two']}
        with self.assertRaisesRegex(ValueError,'authorization is not registered'):
            m.assign(root,spec)

    def test_takeover_inherits_active_authorization(self):
        result=m.takeover(self.root,'dispatcher-c','2026-10-17T02:00:00+00:00')
        self.assertEqual(result['authorization_id'],'test-auth')
        self.assertEqual(result['authorization_sha256'],m.digest(m.encode(self.authorization['authorization'])))
        self.assertTrue(result['authorization_inherited'])
        self.assertEqual(m.status(self.root)['dispatcher']['authorization_id'],'test-auth')

    def test_authorization_reference_validates_itself(self):
        reference=m.authorization_reference(self.authorization['authorization'])
        m.validate_authorization_reference(reference)
        self.assertEqual(reference['scope'],['test task scope'])
        self.assertEqual(reference['status'],'active')
        bad=dict(reference);bad['sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'digest mismatch'):
            m.validate_authorization_reference(bad)

    def test_revoked_authorization_blocks_task_assignment(self):
        m.authorize(self.root,self.authorization_spec('revoked'))
        spec={'task_id':'TASK-REVOKED','lane':'pilot','objective':'verify','scope':['one'],'acceptance':['two']}
        with self.assertRaisesRegex(ValueError,'not active'):
            m.assign(self.root,spec)

    def test_precondition_is_not_authorization_wait(self):
        base={'lane':'pilot','objective':'verify','scope':['one'],'acceptance':['two']}
        m.assign(self.root,{**base,'task_id':'TASK-PREREQ'})
        task=m.assign(self.root,{**base,'task_id':'TASK-DEPENDENT','preconditions':['TASK-PREREQ']})
        readiness=m.task_readiness(self.root,task)
        self.assertEqual(readiness['state'],'waiting_preconditions')
        self.assertEqual(readiness['unmet_preconditions'],['TASK-PREREQ'])
        self.assertIn('不是等待所有者授权',readiness['note'])

    def test_status_normalizes_legacy_execution_authorized_field(self):
        event_id=self.submit()
        m.write(self.root/'reviews'/f'{event_id}.json',
                {'status':'proposal_ready','attempts':1,'execution_authorized':False,
                 'dispatcher_decision':{'decision':'accepted','execution_authorized':False}})
        row=[x for x in m.status(self.root)['receipts'] if x['id']==event_id][0]
        self.assertNotIn('execution_authorized',row)
        self.assertNotIn('execution_authorized',row['dispatcher_decision'])
        self.assertFalse(row['background_auto_execution'])
        self.assertFalse(row['dispatcher_decision']['background_auto_execution'])

if __name__ == '__main__':unittest.main()
