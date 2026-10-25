import json
import copy
import io
import zipfile
import stat
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import backend_test_receipt as receipt


class WorkflowDefinitionAttestationTest(unittest.TestCase):
    def fixture(self):
        head, merge, tree = 'a'*40, 'b'*40, 'c'*40
        workflow = '.github/workflows/backend_test_suite.yml'
        caller = '.github/workflows/professional_quality_gate.yml'
        blobs = {workflow:'d'*40, caller:'e'*40}
        run = {'event':'pull_request','path':caller,'head_sha':head,
               'referenced_workflows':[{'path':receipt.REPOSITORY+'/'+workflow+'@'+merge,'sha':merge}]}
        definition = {'sha':merge,'path':caller}
        responses = {'git/commits/'+merge:{'sha':merge,'tree':{'sha':tree},'parents':[{'sha':head}]},
                     'git/trees/'+tree+'?recursive=1':{'sha':tree,'truncated':False,
                         'tree':[{'path':p,'sha':oid,'mode':'100644','type':'blob'} for p,oid in blobs.items()]}}
        return run, definition, blobs, responses

    def test_pr_reusable_definition_is_eligible_when_platform_and_bytes_agree(self):
        run, definition, blobs, responses = self.fixture()
        receipt.attest_execution_definition(run,definition,blobs,lambda p:json.dumps(responses[p]).encode())

    def test_producer_sha_without_platform_binding_is_rejected(self):
        run, definition, blobs, responses = self.fixture()
        run['referenced_workflows'] = []
        with self.assertRaisesRegex(ValueError,'missing or ambiguous'):
            receipt.attest_execution_definition(run,definition,blobs,lambda p:json.dumps(responses[p]).encode())

    def test_changed_workflow_merge_parent_or_incomplete_tree_is_rejected(self):
        for mutation in ('bytes','parent','truncated','observed_sha'):
            with self.subTest(mutation=mutation):
                run, definition, blobs, responses = self.fixture()
                if mutation == 'bytes': blobs[run['path']] = 'f'*40
                if mutation == 'parent': responses['git/commits/'+'b'*40]['parents'] = []
                if mutation == 'truncated': responses['git/trees/'+'c'*40+'?recursive=1']['truncated'] = True
                if mutation == 'observed_sha': definition['sha'] = 'a'*40
                with self.assertRaises(ValueError):
                    receipt.attest_execution_definition(run,definition,blobs,lambda p:json.dumps(responses[p]).encode())

    def test_workflow_authority_blobs_resolve_exact_blobs_and_reject_incomplete(self):
        tree = 'c'*40
        workflow = '.github/workflows/backend_test_suite.yml'
        caller = '.github/workflows/professional_quality_gate.yml'
        responses = {'git/trees/'+tree+'?recursive=1': {'sha':tree,'truncated':False,'tree':[
            {'path':workflow,'sha':'d'*40,'mode':'100644','type':'blob'},
            {'path':caller,'sha':'e'*40,'mode':'100644','type':'blob'}]}}
        blobs = receipt.workflow_authority_blobs(tree, lambda p: json.dumps(responses[p]).encode())
        self.assertEqual({'d'*40,'e'*40}, set(blobs.values()))
        for mutation in ('missing','truncated','non_blob'):
            with self.subTest(mutation=mutation):
                broken = copy.deepcopy(responses)
                if mutation == 'missing':
                    broken['git/trees/'+tree+'?recursive=1']['tree'].pop()
                elif mutation == 'truncated':
                    broken['git/trees/'+tree+'?recursive=1']['truncated'] = True
                else:
                    broken['git/trees/'+tree+'?recursive=1']['tree'][0]['type'] = 'tree'
                with self.assertRaises(ValueError):
                    receipt.workflow_authority_blobs(tree, lambda p: json.dumps(broken[p]).encode())


class JobObservationTest(unittest.TestCase):
    def setUp(self):
        self.head = 'a' * 40
        self.workflow = '.github/workflows/professional_quality_gate.yml'
        repository = {'id': receipt.REPOSITORY_ID, 'full_name': receipt.REPOSITORY}
        self.run_path = 'actions/runs/10/attempts/2'
        self.job_path = 'actions/jobs/30'
        self.responses = {
            self.run_path: {'id': 10, 'run_attempt': 2, 'head_sha': self.head,
                'repository': dict(repository), 'head_repository': dict(repository),
                'event': 'pull_request', 'path': self.workflow,
                'status': 'completed', 'conclusion': 'success'},
            self.job_path: {'id': 30, 'run_id': 10, 'run_attempt': 2,
                'head_sha': self.head, 'status': 'completed', 'conclusion': 'success',
                'steps': [dict(number=1, name='standard', status='completed', conclusion='success'),
                          dict(number=2, name='full', status='completed', conclusion='skipped')]},
            'git/commits/' + self.head: {'sha': self.head, 'tree': {'sha': 'b' * 40}},
        }

    def observe(self, **overrides):
        arguments = dict(run_id=10, attempt=2, job_id=30,
                         expected_head=self.head, workflow_path=self.workflow)
        arguments.update(overrides)
        with patch.object(receipt, 'github_bytes',
                          side_effect=lambda path: json.dumps(self.responses[path]).encode()):
            return receipt.observe_github_job(**arguments)

    def test_success_and_skip_remain_distinct_not_reusable(self):
        result = self.observe()
        self.assertEqual(['success', 'skipped'], [s['conclusion'] for s in result['steps']])
        self.assertFalse(result['reuse_ready'])
        self.assertFalse(result['quick_receipt'])
        self.assertIn('environment_identity_not_attested', result['blockers'])
        self.assertEqual(3, len(result['metadata_sha256']))
        self.assertEqual('verified', result['platform_origin'])

    def test_failed_execution_preserved_not_promoted(self):
        self.responses[self.run_path]['conclusion'] = 'failure'
        self.responses[self.job_path]['conclusion'] = 'failure'
        self.responses[self.job_path]['steps'][0]['conclusion'] = 'failure'
        result = self.observe()
        self.assertEqual('failure', result['job_conclusion'])
        self.assertEqual('failure', result['steps'][0]['conclusion'])
        self.assertFalse(result['reuse_ready'])

    def test_invalid_requested_identity_never_fetches(self):
        for change in ({'run_id': True}, {'attempt': 0}, {'job_id': -1},
                       {'expected_head': None}, {'expected_head': 'main'},
                       {'workflow_path': 'https://foreign.invalid/workflow'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.observe(**change)

    def test_foreign_repository_refused(self):
        for field in ('repository', 'head_repository'):
            original = copy.deepcopy(self.responses[self.run_path][field])
            self.responses[self.run_path][field]['id'] = 1
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'foreign'):
                self.observe()
            self.responses[self.run_path][field] = original

    def test_run_and_job_attempt_head_workflow_mismatch_refused(self):
        for endpoint, fields in (
            (self.run_path, {'id': 11, 'run_attempt': 1, 'head_sha': 'c' * 40,
                             'path': 'other.yml', 'event': 'pull_request_target', 'status': 'queued'}),
            (self.job_path, {'id': 31, 'run_id': 11, 'run_attempt': 1,
                             'head_sha': 'c' * 40, 'status': 'in_progress'})):
            for field, value in fields.items():
                original = self.responses[endpoint][field]
                self.responses[endpoint][field] = value
                with self.subTest(endpoint=endpoint, field=field), self.assertRaises(ValueError):
                    self.observe()
                self.responses[endpoint][field] = original

    def test_missing_or_ambiguous_steps_refused(self):
        original = self.responses[self.job_path]['steps']
        for steps in (None, [], [original[0], original[0]],
                      [dict(original[0], number=True)], [dict(original[0], conclusion='unknown')],
                      [dict(original[0], status='in_progress')]):
            self.responses[self.job_path]['steps'] = steps
            with self.subTest(steps=steps), self.assertRaises(ValueError):
                self.observe()
        self.responses[self.job_path]['steps'] = original

    def test_tree_identity_required(self):
        path = 'git/commits/' + self.head
        self.responses[path]['tree']['sha'] = 'branch'
        with self.assertRaisesRegex(ValueError, 'tree identity'):
            self.observe()

    def test_unknown_run_conclusion_refused(self):
        self.responses[self.run_path]['conclusion'] = None
        with self.assertRaisesRegex(ValueError, 'conclusion'):
            self.observe()


class WorkflowDefinitionObservationTest(unittest.TestCase):
    def observe(self, values):
        with patch.dict(os.environ, values, clear=True):
            return receipt.workflow_definition_observation()

    def test_absent_is_not_filled_from_checkout_sha(self):
        self.assertEqual({'status': 'not_captured', 'attested': False},
                         self.observe({'GITHUB_SHA': 'a' * 40, 'HEAD_SHA': 'b' * 40}))

    def test_merge_workflow_identity_is_distinct_and_not_attested(self):
        value = self.observe({'GITHUB_SHA': 'a' * 40, 'GITHUB_WORKFLOW_SHA': 'b' * 40,
            'GITHUB_WORKFLOW_REF': receipt.REPOSITORY + '/.github/workflows/backend_test_suite.yml@refs/pull/723/merge',
            'UNRELATED_SECRET': 'not-collected'})
        self.assertEqual('b' * 40, value['sha'])
        self.assertEqual('refs/pull/723/merge', value['ref'])
        self.assertEqual('producer_observed', value['status'])
        self.assertFalse(value['attested'])
        self.assertNotIn('not-collected', json.dumps(value))

    def test_incomplete_or_foreign_definition_refused(self):
        good = receipt.REPOSITORY + '/.github/workflows/backend_test_suite.yml@refs/heads/main'
        for values in ({'GITHUB_WORKFLOW_SHA': 'b' * 40}, {'GITHUB_WORKFLOW_REF': good},
                       {'GITHUB_WORKFLOW_SHA': 'main', 'GITHUB_WORKFLOW_REF': good},
                       {'GITHUB_WORKFLOW_SHA': 'b' * 40, 'GITHUB_WORKFLOW_REF': good.replace(receipt.REPOSITORY, 'foreign/repo')},
                       {'GITHUB_WORKFLOW_SHA': 'b' * 40, 'GITHUB_WORKFLOW_REF': good + '\ncredential'}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                self.observe(values)


class IsolatedPythonDecisionTest(unittest.TestCase):
    def proof(self, fingerprint='a'*64):
        return {'schema':'backend-isolated-python/v1','module':receipt.ISOLATED_MODULE,
                'fingerprint':fingerprint,'test_ids':['test_case.C.test_one'],'skipped':0}

    def previous(self, fingerprint='a'*64):
        return {'isolated_python':self.proof(fingerprint),'test_count':1,
                'platform_origin':'verified','integrity':'verified',
                'isolated_execution_authority':'verified_workflow_execution',
                'locator':{'run_id':10,'artifact_id':20},'receipt_sha256':'b'*64,
                'actual_duration_seconds':5.0}

    def test_first_run_and_daily_full_never_skip(self):
        self.assertEqual('RUN',receipt.isolated_decision('a'*64,None,force_full=False)['decision'])
        self.assertEqual('RUN',receipt.isolated_decision('a'*64,self.previous(),force_full=True)['decision'])

    def test_equal_authenticated_inputs_reuse_and_bind_old_receipt(self):
        result=receipt.isolated_decision('a'*64,self.previous(),force_full=False)
        self.assertEqual('REUSE',result['decision'])
        self.assertEqual(10,result['previous_receipt']['run_id'])
        self.assertEqual(5.0,result['estimated_saved_time'])
        self.assertIsNone(result['actual_saved_time'])

    def test_changed_input_runs(self):
        self.assertEqual('RUN',receipt.isolated_decision('c'*64,self.previous(),force_full=False)['decision'])

    def test_unverified_history_cannot_become_passed_ledger(self):
        for field in ('platform_origin','integrity','isolated_execution_authority'):
            value=self.previous();value[field]='observed'
            with self.subTest(field=field),self.assertRaises(ValueError):
                receipt.isolated_decision('a'*64,value,force_full=False)

    def test_skips_zero_duplicate_and_foreign_scope_are_rejected(self):
        for field,value in [('skipped',1),('test_ids',[]),('test_ids',['x','x']),
                            ('test_ids',[42]),('module','smart_core'),('fingerprint','')]:
            proof=self.proof();proof[field]=value
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):
                receipt.validate_isolated_result(proof,1)

    def test_reuse_consumes_receipt_without_executing_or_issuing_new_success(self):
        head='a'*40
        def command(*args,**kwargs):
            if args[:3]==('git','rev-parse','HEAD'):return head
            if args[:2]==('git','status'):return ''
            if args[:2]==('git','show'):return 'ARG ODOO_BASE_IMAGE=odoo:17.0@sha256:'+'b'*64
            if args[:3]==('docker','image','inspect'):return 'sha256:'+'c'*64
            if args[:2]==('git','rev-parse'):return 'd'*40
            raise AssertionError(args)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);output=root/'out'
            with patch.object(receipt,'command',side_effect=command), \
                    patch.object(receipt,'isolated_snapshot',return_value={'fingerprint':'a'*64,'recipe':{}}), \
                    patch.object(receipt,'isolated_history',return_value=(self.previous(),[])), \
                    patch.object(receipt,'execute_isolated_container') as execute, \
                    patch.object(receipt,'record') as record:
                result=receipt.run_isolated_python(root=root,head=head,base='',output=output,
                    context_file=root/'unused',scope_plan=root/'unused',force_full=False)
            self.assertEqual('REUSE',result['decision']);execute.assert_not_called();record.assert_not_called()
            saved=json.loads((output/('isolated-decision-'+receipt.ISOLATED_MODULE+'.json')).read_text())
            self.assertEqual(head,saved['source_head']);self.assertEqual(10,saved['previous_receipt']['run_id'])
            self.assertFalse((output/receipt.ISOLATED_MODULE/'receipt.json').exists())

    def test_container_timeout_preserves_output_and_cleans_only_owned_container(self):
        with tempfile.TemporaryDirectory() as tmp:
            log=Path(tmp)/'run.log'
            def run(args,**kwargs):
                if args[1]=='run':raise subprocess.TimeoutExpired(args,1,output=b'partial output')
                return subprocess.CompletedProcess(args,0,'')
            with patch.object(receipt.subprocess,'run',side_effect=run) as calls:
                result=receipt.execute_isolated_container(['docker','run','--rm','image'],log,timeout=1)
            self.assertEqual(124,result.returncode)
            self.assertIn('partial output',log.read_text())
            command=calls.call_args_list[0].args[0];name=command[command.index('--name')+1]
            self.assertTrue(name.startswith('sc-isolated-python-'))
            self.assertEqual(['docker','rm','-f',name],calls.call_args_list[-1].args[0])

    def test_legacy_receipt_does_not_create_isolated_baseline(self):
        with self.assertRaises(ValueError):receipt.validate_isolated_result(None,71)

    def test_history_requires_root_full_workflow_and_exact_visible_inputs(self):
        head='a'*40; tree_sha='b'*40; fingerprint='a'*64
        workflow='.github/workflows/backend_test_suite.yml'
        recipe={'source_files':{'addons/example/test.py':{'git_blob':'c'*40,'mode':0o644}},
                'authority_blobs':{workflow:'d'*40,'scripts/ci/backend_test_receipt.py':'e'*40}}
        proof=self.proof()
        value={**self.previous(),'source_tree':tree_sha,'workflow_definition':{'sha':head,'path':workflow}}
        run={'id':10,'run_attempt':1,'event':'schedule','path':workflow,'head_sha':head,
             'repository':{'id':receipt.REPOSITORY_ID},'head_repository':{'id':receipt.REPOSITORY_ID},
             'run_started_at':datetime.now(timezone.utc).isoformat()}
        rows=[{'path':path,'type':'blob','mode':'100644','sha':oid} for path,oid in
              [('addons/example/test.py','c'*40),*recipe['authority_blobs'].items()]]
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w') as archive:
            archive.writestr(receipt.ISOLATED_MODULE+'/execution.log',receipt.ISOLATED_MARKER+json.dumps(proof)+'\n')
        data={'actions/runs?status=success&per_page=30':{'workflow_runs':[run]},
              'actions/runs/10/artifacts?per_page=100':{'artifacts':[{'id':20,'name':'backend-execution-10-1-0'}]},
              'git/trees/'+tree_sha+'?recursive=1':{'sha':tree_sha,'truncated':False,'tree':rows},
              'actions/artifacts/20/zip':stream.getvalue()}
        def fetch(path):
            item=data[path];return item if isinstance(item,bytes) else json.dumps(item).encode()
        def select():
            with patch.object(receipt,'verify_github_origin',return_value=value),patch.dict(os.environ,{'GITHUB_RUN_ID':'99'}):
                return receipt.isolated_history(fingerprint,recipe=recipe,fetch=fetch)
        selected,rejected=select()
        self.assertEqual('verified_workflow_execution',selected['isolated_execution_authority'])
        self.assertEqual([],rejected)
        run['event']='pull_request'
        self.assertIsNone(select()[0])  # merge-ref workflow identity is not inferred from head
        run['event']='schedule';run['run_attempt']=2
        self.assertIsNone(select()[0])
        run['run_attempt']=1
        data['git/trees/'+tree_sha+'?recursive=1']['truncated']=True
        self.assertIsNone(select()[0]);self.assertTrue(select()[1])
        data['git/trees/'+tree_sha+'?recursive=1']['truncated']=False
        rows[0]['sha']='f'*40
        self.assertIsNone(select()[0])
        rows[0]['sha']='c'*40;value['workflow_definition']['sha']='f'*40
        self.assertIsNone(select()[0])

    def test_snapshot_hashes_actual_git_bytes_not_dirty_files(self):
        import backend_impact_plan as impact
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'repo';root.mkdir()
            def git(*args):return subprocess.check_output(['git',*args],cwd=root,text=True).strip()
            git('init','-q');git('config','user.name','Fixture');git('config','user.email','fixture@example.invalid')
            paths={'addons/example/test.py':'one','demo_addons/example/data.xml':'<data/>',
                   'docs/input.json':'{}','docs/unrelated.md':'notes',
                   'scripts/ci/backend_test_receipt.py':'executor',
                   'scripts/ci/backend_impact_plan.py':'mapper','scripts/ops/evidence_scope.py':'authority',
                   '.github/workflows/backend_test_suite.yml':'suite',
                   '.github/workflows/professional_quality_gate.yml':'caller'}
            for path,value in paths.items():
                file=root/path;file.parent.mkdir(parents=True,exist_ok=True);file.write_text(value)
            git('add','.');git('commit','-qm','fixture');head=git('rev-parse','HEAD')
            graph={receipt.ISOLATED_MODULE:{'file_inputs':['docs/input.json'],'unresolved_file_reads':[]}}
            def snapshot(sha,name):
                dest=Path(tmp)/name;dest.mkdir()
                with patch.object(impact,'snapshot',return_value=graph):
                    return receipt.isolated_snapshot(root,sha,dest,'sha256:'+'f'*64)
            first=snapshot(head,'first')
            (root/'addons/example/test.py').write_text('dirty')
            self.assertEqual(first['fingerprint'],snapshot(head,'dirty')['fingerprint'])
            git('checkout','--','addons/example/test.py')
            (root/'docs/unrelated.md').write_text('new bookkeeping')
            git('add','.');git('commit','-qm','bookkeeping')
            self.assertEqual(first['fingerprint'],snapshot(git('rev-parse','HEAD'),'notes')['fingerprint'])
            (root/'docs/input.json').write_text('{"changed":true}')
            git('add','.');git('commit','-qm','input')
            self.assertNotEqual(first['fingerprint'],snapshot(git('rev-parse','HEAD'),'input')['fingerprint'])
            (root/'addons/example/link').symlink_to('/etc/passwd')
            git('add','.');git('commit','-qm','link')
            with self.assertRaisesRegex(ValueError,'links/special'):
                snapshot(git('rev-parse','HEAD'),'links')


class ExecutionReceiptTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.root = self.home / 'repo'
        self.root.mkdir()
        def git(*args):
            return subprocess.check_output(['git', *args], cwd=self.root, text=True).strip()
        self.git = git
        git('init', '-q'); git('config', 'user.name', 'Fixture'); git('config', 'user.email', 'fixture@example.invalid')
        module = self.root / 'addons/example'
        (module / 'tests').mkdir(parents=True)
        (module / '__manifest__.py').write_text("{'depends': []}")
        (module / 'tests/test_example.py').write_text('import unittest\nclass Example(unittest.TestCase):\n def test_case(self): self.assertEqual(2, 1+1)\n')
        (self.root / '.gitignore').write_text('__pycache__/\n')
        git('add', '.'); git('commit', '-qm', 'fixture')
        self.head = git('rev-parse', 'HEAD')
        self.log = self.home / 'execution.log'
        result = subprocess.run(['python3', '-m', 'unittest', 'discover', '-s', str(module / 'tests')],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.log.write_text(result.stdout + result.stderr)
        self.context = self.home / 'context.json'
        self.context.write_text(json.dumps({'services': {s: {'image_id': 'sha256:' + 'a'*64} for s in ('db','redis')},
                                           'odoo_image_id': 'sha256:' + 'b'*64}))
        self.output = self.home / 'receipts'
        self.now = datetime(2026, 10, 24, tzinfo=timezone.utc)
        self.environment = {'python':'3.10.22','packages':[{'name':'fixture','version':'1'}]}

    def test_record_preserves_workflow_sha_separate_from_test_source(self):
        with patch.dict(os.environ, {'GITHUB_WORKFLOW_SHA': 'f' * 40,
                'GITHUB_WORKFLOW_REF': receipt.REPOSITORY + '/.github/workflows/backend_test_suite.yml@refs/pull/723/merge'}):
            result = self.record()
        self.assertEqual(self.head, result['source_head'])
        self.assertEqual('f' * 40, result['workflow_definition']['sha'])
        self.assertFalse(result['workflow_definition']['attested'])
        self.assertFalse(result['reuse_ready'])

    def test_invalid_definition_leaves_no_success_receipt(self):
        with patch.dict(os.environ, {'GITHUB_WORKFLOW_SHA': 'invalid', 'GITHUB_WORKFLOW_REF': ''}):
            with self.assertRaisesRegex(ValueError, 'workflow definition'):
                self.record()
        self.assertFalse((self.output / 'example/receipt.json').exists())

    def test_workflow_definition_cannot_self_attest_and_old_receipts_remain_valid(self):
        self.record()
        path = self.output / 'example/receipt.json'
        original = json.loads(path.read_text())
        for definition in ({'status': 'not_captured', 'attested': True},
                           {'status': 'producer_observed', 'attested': True, 'sha': 'a' * 40,
                            'path': '.github/workflows/backend_test_suite.yml', 'ref': 'refs/heads/main'}):
            changed = dict(original, workflow_definition=definition)
            path.write_bytes(receipt.canonical(changed))
            with self.subTest(definition=definition), self.assertRaises(ValueError):
                receipt.verify(path.parent, expected_head=self.head,
                    expected_digest=receipt.digest(path.read_bytes()), now=self.now)
        original.pop('workflow_definition')
        path.write_bytes(receipt.canonical(original))
        result = receipt.verify(path.parent, expected_head=self.head,
            expected_digest=receipt.digest(path.read_bytes()), now=self.now)
        self.assertEqual('verified', result['integrity'])
        self.assertFalse(result['reuse_ready'])

    def record(self, **overrides):
        args = dict(module='example', kind='python', head=self.head, base=self.head,
                    database='', status=0, log=self.log, context_file=self.context,
                    output=self.output, now=self.now)
        args.update(overrides)
        with patch.object(receipt, 'python_environment', return_value=self.environment):
            return receipt.record(self.root, **args)

    def verify(self, result, **kwargs):
        return receipt.verify(self.output/'example', expected_head=self.head,
                              expected_digest=result['receipt_sha256'], now=kwargs.get('now', self.now))

    def test_real_execution_roundtrip_never_self_authorizes_reuse(self):
        result = self.record()
        self.assertEqual(1, result['test_count'])
        verified = self.verify(result)
        self.assertEqual('verified', verified['integrity'])
        self.assertFalse(verified['reuse_ready'])
        self.assertIn('runtime_contract_readback_missing', verified['blockers'])
        self.assertIn('platform_source_not_authenticated', verified['blockers'])

    def test_changed_log_or_environment_is_rejected(self):
        result = self.record()
        for name in ('execution.log','runtime.json','python.json'):
            path = self.output/'example'/name
            original = path.read_bytes()
            with self.subTest(name=name):
                path.write_bytes(original+b' ')
                with self.assertRaisesRegex(ValueError, 'bytes changed'):
                    self.verify(result)
                path.write_bytes(original)

    def test_changed_receipt_target_count_and_lifetime_are_rejected(self):
        result = self.record()
        path = self.output/'example/receipt.json'; original = path.read_bytes()
        for key, value in [('module','other'),('test_count',99),('expires_at','2030-01-01T00:00:00+00:00')]:
            with self.subTest(key=key):
                changed=json.loads(original);changed[key]=value;path.write_bytes(receipt.canonical(changed))
                with self.assertRaisesRegex(ValueError, 'receipt bytes changed'):
                    self.verify(result)
                path.write_bytes(original)

    def test_expired_and_future_results_are_rejected(self):
        result = self.record()
        for now in (self.now+timedelta(days=1), self.now-timedelta(seconds=1)):
            with self.assertRaisesRegex(ValueError, 'lifetime'):
                self.verify(result, now=now)

    def test_source_identity_and_dirty_inputs_rejected(self):
        with self.assertRaisesRegex(ValueError, 'identity mismatch'):
            self.record(head='0'*40)
        (self.root/'unknown.py').write_text('pass')
        with self.assertRaisesRegex(ValueError, 'not clean'):
            self.record()

    def test_failed_and_zero_test_execution_cannot_issue_receipt(self):
        with self.assertRaisesRegex(ValueError, 'execution failed'):
            self.record(status=1)
        self.log.write_text('Ran 0 tests in 0.001s\n\nOK\n')
        with self.assertRaisesRegex(ValueError, 'nonzero'):
            self.record()
        self.assertFalse(self.output.exists())

    def test_missing_database_identity_rejected(self):
        self.context.write_text('{}')
        with self.assertRaisesRegex(ValueError, 'runtime service'):
            self.record()

    def test_existing_evidence_is_never_overwritten(self):
        self.record()
        with self.assertRaisesRegex(ValueError, 'overwrite'):
            self.record()

    def test_symlink_evidence_rejected(self):
        result = self.record()
        path=self.output/'example/execution.log';path.unlink();path.symlink_to(self.log)
        with self.assertRaisesRegex(ValueError, 'linked'):
            self.verify(result)

    def test_no_credential_values_in_archived_log(self):
        secret='fixture-redaction-value'
        self.log.write_text(self.log.read_text()+secret+'\n')
        with patch.dict(os.environ, {'DB_PASSWORD':secret}):
            result=self.record()
        self.assertNotIn(secret, (self.output/'example/execution.log').read_text())
        self.verify(result)

    def test_orm_actual_selection_environment_and_identity(self):
        text = ('2026-10-24 00:00:00 INFO fixture_db odoo.addons.example.tests.test_example: Starting Example.test_case ...\n'
                "0 failed, 0 error(s) of 1 tests when loading database 'fixture_db'\n")
        marker = receipt.ENV_MARKER + json.dumps(self.environment) + '\n'
        self.log.write_text(marker + text)
        result = self.record(kind='orm', database='fixture_db', selection='custom/example', duration_seconds=12)
        self.assertEqual('custom/example', result['selection'])
        self.assertEqual(12, result['actual_duration_seconds'])
        self.assertEqual(1, result['test_count'])
        self.verify(result)
        for invalid in (text, marker + marker + text, marker + text.replace('fixture_db', 'foreign_db'),
                        marker + text.replace('odoo.addons.example.', 'odoo.addons.other.'),
                        marker + text.replace('0 failed', '1 failed')):
            self.log.write_text(invalid)
            with self.assertRaises((ValueError, subprocess.CalledProcessError)):
                receipt.parse_result('orm', 'example', 'fixture_db', 0, self.log)

    def test_orm_missing_selection_cannot_be_reported_as_default(self):
        with self.assertRaisesRegex(ValueError, 'actual ORM selection'):
            self.record(kind='orm', database='fixture_db')

    def test_self_authorized_reuse_rejected_even_with_matching_digest(self):
        self.record()
        path = self.output/'example/receipt.json'
        value = json.loads(path.read_text()); value['reuse_ready'] = True
        path.write_bytes(receipt.canonical(value))
        with self.assertRaisesRegex(ValueError, 'self-authorize'):
            receipt.verify(path.parent, expected_head=self.head,
                           expected_digest=receipt.digest(path.read_bytes()), now=self.now)

    def test_invalid_measured_duration_rejected(self):
        for duration in (-1, float('nan'), float('inf')):
            with self.assertRaisesRegex(ValueError, 'duration'):
                self.record(duration_seconds=duration)

    def test_all_skipped_is_not_executed_success(self):
        self.log.write_text('Ran 1 test in 0.001s\n\nOK (skipped=1)\n')
        with self.assertRaisesRegex(ValueError, 'all tests skipped'):
            self.record()

    def test_partial_skip_counts_are_explicit(self):
        self.log.write_text('Ran 2 tests in 0.001s\n\nOK (skipped=1)\n')
        result = self.record()
        self.assertEqual({'collected':2, 'skipped':1, 'executed':1}, result['python_counts'])

    def test_managed_env_secrets_are_redacted_without_export(self):
        env_file = self.home/'managed.env'
        env_file.write_text('SC_DEMO_USER_PASSWORD=fixture-not-exported\n')
        self.log.write_text(self.log.read_text()+'fixture-not-exported\n')
        result = self.record(secrets_file=env_file)
        self.assertNotIn('fixture-not-exported', (self.output/'example/execution.log').read_text())
        self.verify(result)

    def scope_fixture(self, base=None):
        plan={'head':self.head,'base':self.head if base is None else base,'mode':'full',
              'modules':['example'],'shards':[{'index':0,'modules':['example']}],
              'input_inventory':{'schema':'backend-known-input-inventory/v1','targets':{
                  'example':{'target':'example','known_inputs_sha256':'a'*64}}}}
        path=self.home/'scope-plan.json';path.write_bytes(receipt.canonical(plan));return path

    def test_receipt_requires_its_exact_archived_scope_plan(self):
        plan=self.scope_fixture();result=self.record(scope_plan=plan)
        with self.assertRaisesRegex(ValueError,'scope plan missing'):
            self.verify(result)
        verified=receipt.verify(self.output/'example',expected_head=self.head,
            expected_digest=result['receipt_sha256'],now=self.now,scope_plan=plan)
        self.assertFalse(verified['reuse_ready'])
        plan.write_bytes(plan.read_bytes()+b' ')
        with self.assertRaisesRegex(ValueError,'scope plan missing or changed'):
            receipt.verify(self.output/'example',expected_head=self.head,
                expected_digest=result['receipt_sha256'],now=self.now,scope_plan=plan)

    def test_wrong_head_base_target_or_shard_membership_is_rejected(self):
        plan=self.scope_fixture();original=json.loads(plan.read_text())
        for key,value in [('head','0'*40),('base','0'*40),('modules',[]),
                          ('shards',[{'modules':['example','example']}])]:
            changed=copy.deepcopy(original);changed[key]=value;plan.write_bytes(receipt.canonical(changed))
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'scope plan identity'):
                self.record(scope_plan=plan)

    def test_explicit_full_run_does_not_invent_integration_base(self):
        plan=self.scope_fixture(base='');result=self.record(base='',scope_plan=plan)
        self.assertEqual('',result['integration_base'])
        self.assertEqual('',result['scope_plan']['integration_base'])
        with self.assertRaisesRegex(ValueError,'missing integration base'):
            self.record(base='')

    def test_complete_dependency_closure_drops_its_blocker(self):
        plan = self.scope_fixture()
        payload = json.loads(plan.read_text())
        payload['input_inventory']['targets']['example']['dependency_closure_complete'] = True
        plan.write_bytes(receipt.canonical(payload))
        result = self.record(scope_plan=plan)
        self.assertTrue(result['scope_plan']['dependency_closure_complete'])
        self.assertNotIn('target_dependency_closure_not_certified', result['blockers'])
        self.assertIn('platform_source_not_authenticated', result['blockers'])

    def test_failed_retry_logs_are_distinct_and_redacted(self):
        env=self.home/'managed.env';env.write_text('SC_DEMO_USER_PASSWORD=fixture-attempt-secret\n')
        self.log.write_text('fixture-attempt-secret failed before completion\n')
        for number,status in ((1,137),(2,0)):
            result=receipt.archive_attempt(output=self.output,module='example',attempt=number,
                head=self.head,status=status,log_status=0,log=self.log,secrets_file=env)
            self.assertEqual('diagnostic_only_not_test_success',result['interpretation'])
            self.assertFalse(result['reuse_ready'])
            folder=self.output/'attempts/example'/str(number)
            self.assertNotIn('fixture-attempt-secret',(folder/'execution.log').read_text())
            self.assertFalse((folder/'receipt.json').exists())
        with self.assertRaises(FileExistsError):
            receipt.archive_attempt(output=self.output,module='example',attempt=1,head=self.head,
                status=137,log_status=0,log=self.log)

    def test_attempt_path_and_status_cannot_escape_archive(self):
        for overrides in ({'module':'../escape'},{'attempt':0},{'status':-1},{'log_status':256}):
            args=dict(output=self.output,module='example',attempt=1,head=self.head,status=1,log_status=0,log=self.log)
            args.update(overrides)
            with self.assertRaisesRegex(ValueError,'invalid attempt'):receipt.archive_attempt(**args)

    def platform_fixture(self, scoped=False):
        plan = self.scope_fixture() if scoped else None
        with patch.dict(os.environ, {'GITHUB_REPOSITORY':receipt.REPOSITORY, 'GITHUB_RUN_ID':'10',
                'GITHUB_RUN_ATTEMPT':'2', 'GITHUB_JOB':'backend_suite'}):
            observed = self.record(scope_plan=plan)
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w') as archive:
            for path in (self.output/'example').iterdir():
                archive.writestr('example/'+path.name, path.read_bytes())
            if plan is not None:
                archive.writestr('scope-plan.json',plan.read_bytes())
        raw = stream.getvalue()
        repo = {'id':receipt.REPOSITORY_ID,'full_name':receipt.REPOSITORY}
        run = {'id':10,'run_attempt':2,'head_sha':self.head,'status':'completed','conclusion':'success',
               'event':'pull_request','path':'.github/workflows/professional_quality_gate.yml',
               'repository':repo,'head_repository':dict(repo)}
        artifact = {'id':20,'name':'backend-execution-10-2-0','expired':False,
                    'digest':'sha256:'+receipt.digest(raw), 'workflow_run':{'id':10,'head_sha':self.head,
                        'repository_id':receipt.REPOSITORY_ID,'head_repository_id':receipt.REPOSITORY_ID}}
        return {'actions/runs/10/attempts/2':run, 'actions/artifacts/20':artifact,
                'actions/artifacts/20/zip':raw,
                'git/commits/'+self.head:{'sha':self.head,'tree':{'sha':observed['source_tree']}}}

    def origin(self, responses):
        def api(endpoint):
            result = responses[endpoint]
            return result if isinstance(result, bytes) else json.dumps(result).encode()
        with patch.object(receipt, 'github_bytes', side_effect=api):
            return receipt.verify_github_origin(run_id=10,attempt=2,artifact_id=20,shard=0,
                                                expected_head=self.head,module='example',now=self.now)

    def test_platform_origin_does_not_authorize_reuse(self):
        result = self.origin(self.platform_fixture())
        self.assertEqual('verified',result['platform_origin'])
        self.assertFalse(result['reuse_ready'])
        self.assertIn('execution_definition_not_attested',result['blockers'])
        self.assertIn('artifact_attempt_not_attested',result['blockers'])
        self.assertEqual('not_attested', result['artifact_attempt'])
        self.assertEqual(2, result['requested_attempt'])
        self.assertNotIn('attempt', result)
        self.assertIn('fact_scope_readback_missing',result['blockers'])

    def test_execution_definition_attested_drops_only_that_blocker(self):
        responses = self.platform_fixture()
        with patch.object(receipt, 'workflow_authority_blobs', return_value={'w':'e'*40}), \
             patch.object(receipt, 'attest_execution_definition'):
            result = self.origin(responses)
        self.assertTrue(result['execution_definition_attested'])
        self.assertNotIn('execution_definition_not_attested', result['blockers'])
        self.assertIn('artifact_attempt_not_attested', result['blockers'])
        self.assertIn('runtime_contract_readback_missing', result['blockers'])
        self.assertIn('fact_scope_readback_missing', result['blockers'])
        self.assertIn('target_dependency_closure_not_certified', result['blockers'])

    def test_malformed_authenticated_newer_receipt_falls_back_to_valid_history(self):
        import backend_suite_plan as planner
        original = self.platform_fixture(scoped=True)
        files = receipt.archive_members(original['actions/artifacts/20/zip'])
        valid = json.loads(files['example/receipt.json'])
        target = {'known_inputs_sha256':valid['scope_plan']['known_inputs_sha256'],
                  'blockers':['dependency_closure_not_certified']}
        plan = {'head':self.head,'base':self.head,'modules':['example']}
        for invalid in ('missing',123):
            changed = copy.deepcopy(original)
            changed['actions/runs/11/attempts/2'] = dict(original['actions/runs/10/attempts/2'],id=11)
            broken = copy.deepcopy(valid); broken['provenance']['GITHUB_RUN_ID']='11'
            if invalid == 'missing': del broken['issued_at']
            else: broken['issued_at']=invalid
            stream=io.BytesIO()
            with zipfile.ZipFile(stream,'w') as archive:
                for path,data in files.items():
                    archive.writestr(path,receipt.canonical(broken) if path=='example/receipt.json' else data)
            changed['actions/artifacts/21/zip']=stream.getvalue()
            metadata=copy.deepcopy(original['actions/artifacts/20'])
            metadata.update(id=21,name='backend-execution-11-2-0',digest='sha256:'+receipt.digest(stream.getvalue()))
            metadata['workflow_run']['id']=11;changed['actions/artifacts/21']=metadata
            def api(path):
                value=changed[path]
                return value if isinstance(value,bytes) else json.dumps(value).encode()
            locators=[dict(head=self.head,module='example',run_id=run,attempt=2,artifact_id=artifact,shard=0)
                      for run,artifact in ((11,21),(10,20))]
            with self.subTest(invalid=invalid), patch.object(receipt,'github_bytes',side_effect=api), \
                 patch.object(planner.impact,'git',return_value=''), \
                 patch.object(planner.impact,'snapshot',return_value={}), \
                 patch.object(planner,'target_input_inventory',return_value={'targets':{'example':target}}), \
                 patch.object(planner,'datetime',wraps=datetime) as clock:
                clock.now.return_value=self.now
                result=planner.select_historical_receipts(plan,locators)
                row=result['decisions'][0]
                self.assertEqual(20,row['previous_receipt']['locator']['artifact_id'])
                self.assertEqual(1,len(row['rejected_candidates']))
                self.assertEqual('BLOCK',row['decision'])
                self.assertFalse(result['reuse_authority'])

    def test_platform_archive_must_include_receipt_bound_plan(self):
        responses=self.platform_fixture(scoped=True)
        self.assertEqual('verified',self.origin(responses)['platform_origin'])
        files=receipt.archive_members(responses['actions/artifacts/20/zip'])
        for missing in (True,False):
            modified=dict(files)
            if missing:del modified['scope-plan.json']
            else:modified['scope-plan.json']+=b' '
            stream=io.BytesIO()
            with zipfile.ZipFile(stream,'w') as archive:
                for name,data in modified.items():archive.writestr(name,data)
            changed=copy.deepcopy(responses);changed['actions/artifacts/20/zip']=stream.getvalue()
            changed['actions/artifacts/20']['digest']='sha256:'+receipt.digest(stream.getvalue())
            with self.subTest(missing=missing),self.assertRaisesRegex(ValueError,'scope plan'):
                self.origin(changed)

    def test_platform_run_identity_failure_and_attempt_mismatch(self):
        responses=self.platform_fixture()
        for key,value in [('run_attempt',1),('head_sha','0'*40),('conclusion','failure'),
                          ('status','in_progress'),('event','pull_request_target'),('path','other.yml')]:
            changed=copy.deepcopy(responses);changed['actions/runs/10/attempts/2'][key]=value
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'run identity'):
                self.origin(changed)
        changed=copy.deepcopy(responses)
        changed['actions/runs/10/attempts/2']['head_repository']['id']=1
        with self.assertRaisesRegex(ValueError,'foreign repository'):self.origin(changed)

    def test_platform_artifact_binding_and_digest_required(self):
        responses=self.platform_fixture()
        for key,value in [('name','backend-execution-10-1-0'),('expired',True),('digest',''),
                          ('digest','sha256:'+'0'*64),('workflow_run',{'id':11})]:
            changed=copy.deepcopy(responses);changed['actions/artifacts/20'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):self.origin(changed)
        changed=copy.deepcopy(responses);changed['git/commits/'+self.head]['tree']['sha']='0'*40
        with self.assertRaisesRegex(ValueError,'tree mismatch'):self.origin(changed)

    def test_archive_paths_links_duplicates_and_size_refused(self):
        for name in ('../escape', '/absolute', 'a/../escape', 'a\\escape', './a'):
            stream=io.BytesIO()
            with zipfile.ZipFile(stream,'w') as z:z.writestr(name,b'x')
            with self.subTest(name=name),self.assertRaisesRegex(ValueError,'unsafe'):
                receipt.archive_members(stream.getvalue())
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w') as z:
            info=zipfile.ZipInfo('linked'); info.external_attr=(stat.S_IFLNK|0o777)<<16
            z.writestr(info,'target')
        with self.assertRaisesRegex(ValueError,'unsafe'):receipt.archive_members(stream.getvalue())
        with patch.object(receipt,'ARCHIVE_LIMIT',1),self.assertRaisesRegex(ValueError,'too large'):
            receipt.archive_members(b'xx')

    def contract_fixture(self):
        path=receipt.ROOT/'addons/smart_core/core/contract_lifecycle.py'
        spec=receipt.importlib.util.spec_from_file_location('fixture_lifecycle',path)
        lifecycle=receipt.importlib.util.module_from_spec(spec);spec.loader.exec_module(lifecycle)
        source={'model':'example','fields':{'amount':{'type':'monetary'}},
                'domain':[['project_id','=',7]],'records':[{'id':1,'amount':100}]}
        contract=lifecycle.seal_unified_page_contract({'model':'example','data':{'amount':100}},
                  source_payload=source,source_type='ui.contract',request_id='fixture')
        return contract,source

    def test_contract_source_binding_uses_existing_lifecycle(self):
        contract,source=self.contract_fixture()
        result=receipt.contract_source_binding(contract,source)
        self.assertEqual('verified',result['consistency'])
        self.assertFalse(result['reuse_ready'])
        self.assertIn('fact_scope_readback_missing',result['blockers'])

    def test_unchanged_contract_cannot_hide_changed_facts(self):
        contract,source=self.contract_fixture()
        for key,value in [('model','other'),('fields',{'amount':{'type':'char'}}),
                          ('domain',[]),('records',[{'id':1,'amount':101}])]:
            changed=copy.deepcopy(source);changed[key]=value
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'facts binding'):
                receipt.contract_source_binding(contract,changed)

    def test_unchanged_facts_cannot_hide_changed_contract(self):
        contract,source=self.contract_fixture();contract['data']['amount']=101
        with self.assertRaisesRegex(ValueError,'integrity mismatch'):
            receipt.contract_source_binding(contract,source)

    def test_absent_fact_payload_cannot_be_filled_by_default(self):
        contract,source=self.contract_fixture()
        with self.assertRaisesRegex(ValueError,'actual source'):
            receipt.contract_source_binding(contract,{})

    def test_runtime_snapshot_retains_only_image_identity(self):
        def fake(*args, **kwargs):
            if args[:3]==('docker','compose','ps'):return 'container'
            if args[:3]==('docker','compose','config'):
                return json.dumps({'services':{'odoo':{'image':'test-image','environment':{'SECRET':'do-not-retain'}}}})
            if '{{json .RepoDigests}}' in args:return '["image@sha256:abc"]'
            if '{{.Image}}' in args or '{{.Id}}' in args:return 'sha256:'+'a'*64
            return 'version'
        with patch.object(receipt,'command',side_effect=fake):value=receipt.context()
        self.assertNotIn('do-not-retain',json.dumps(value))
        self.assertIn('odoo_image_id',value)


class ReuseClosureModelTest(unittest.TestCase):
    def test_reuse_requires_every_dimension_independently(self):
        closed = receipt.reuse_closure()
        self.assertFalse(closed['reuse_ready'])
        self.assertEqual({
            'platform_source_not_authenticated',
            'artifact_attempt_not_attested',
            'execution_definition_not_attested',
            'runtime_contract_readback_missing',
            'fact_scope_readback_missing',
            'target_dependency_closure_not_certified',
        }, set(closed['blockers']))
        # An identical source tree and authenticated platform never close the
        # dynamic contract or fact dimensions on their own.
        partial = receipt.reuse_closure(platform_source_authenticated=True,
                                        artifact_attempt_attested=True,
                                        execution_definition_attested=True,
                                        target_dependency_closure=True)
        self.assertFalse(partial['reuse_ready'])
        self.assertEqual({'runtime_contract_readback_missing', 'fact_scope_readback_missing'},
                         set(partial['blockers']))
        full = receipt.reuse_closure(platform_source_authenticated=True,
                                     artifact_attempt_attested=True,
                                     execution_definition_attested=True,
                                     runtime_contract_readback=True,
                                     fact_scope_readback=True,
                                     target_dependency_closure=True)
        self.assertTrue(full['reuse_ready'])
        self.assertEqual([], full['blockers'])

    def _witness(self, uncovered=None, full=None):
        parity = {'checked_fields': ['amount', 'state'], 'mismatch_fields': [],
                  'uncovered_fields': uncovered if uncovered is not None else {}}
        if full is not None:
            parity['full_projection_parity'] = full
        return {'schema': 'backend-contract-fact-readback/v1',
                'observation': {'source_sha256': 'a' * 64, 'contract_sha256': 'b' * 64,
                                'value_parity': parity}}

    def test_readback_witness_uncovered_fields_keep_fact_scope_open(self):
        witness = self._witness(uncovered={'partner': 'relation_or_non_scalar_projection'})
        closure = receipt.readback_witness_closure(witness)
        self.assertTrue(closure['runtime_contract_readback'])
        self.assertFalse(closure['fact_scope_readback'])
        self.assertTrue(closure['projection_value_coverage_incomplete'])

    def test_readback_witness_full_parity_closes_both_dimensions(self):
        closure = receipt.readback_witness_closure(self._witness(full=True))
        self.assertTrue(closure['runtime_contract_readback'])
        self.assertTrue(closure['fact_scope_readback'])
        self.assertFalse(closure['projection_value_coverage_incomplete'])

    def test_readback_witness_rejects_static_or_incomplete_authority(self):
        for bad in ({}, {'schema': 'not-readback'},
                    {'schema': 'backend-contract-fact-readback/v1', 'observation': {}},
                    {'schema': 'backend-contract-fact-readback/v1',
                     'observation': {'source_sha256': 'a' * 64, 'contract_sha256': 'b' * 64,
                                     'value_parity': {'checked_fields': [], 'mismatch_fields': [],
                                                      'uncovered_fields': {}}}}):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    receipt.readback_witness_closure(bad)

    def test_receipt_reuse_requires_independent_authority_not_claim(self):
        self.assertFalse(receipt.receipt_reuse_authorized(None)[0])
        isolated = {'isolated_execution_authority': 'verified_workflow_execution',
                    'platform_origin': 'verified', 'integrity': 'verified',
                    'reuse_ready': False, 'blockers': ['unused']}
        self.assertEqual((True, []), receipt.receipt_reuse_authorized(isolated))
        # A producer's reuse_ready=True is never trusted without independent attestation.
        claimed = {'platform_origin': 'verified', 'integrity': 'verified',
                   'reuse_ready': True, 'blockers': []}
        authorized, blockers = receipt.receipt_reuse_authorized(claimed)
        self.assertFalse(authorized)
        self.assertEqual(['reuse_closure_not_independently_attested'], blockers)
        open_closure = {'platform_origin': 'verified', 'integrity': 'verified',
                        'reuse_ready': False, 'blockers': ['runtime_contract_readback_missing']}
        authorized, blockers = receipt.receipt_reuse_authorized(open_closure)
        self.assertFalse(authorized)
        self.assertEqual(['runtime_contract_readback_missing'], blockers)

    def test_receipt_reuse_authorizes_verified_six_dimension_closure(self):
        verified = {'platform_origin': 'verified', 'integrity': 'verified',
                    'reuse_authority': 'verified_six_dimension_closure', 'blockers': []}
        self.assertEqual((True, []), receipt.receipt_reuse_authorized(verified))
        open_closure = {'platform_origin': 'verified', 'integrity': 'verified',
                        'reuse_authority': None,
                        'blockers': ['artifact_attempt_not_attested']}
        authorized, blockers = receipt.receipt_reuse_authorized(open_closure)
        self.assertFalse(authorized)
        self.assertEqual(['artifact_attempt_not_attested'], blockers)

    def test_readback_closure_blockers_bind_exact_head_and_parity(self):
        missing, closure = receipt.readback_closure_blockers(None, head='a' * 40)
        self.assertEqual(['runtime_contract_readback_missing', 'fact_scope_readback_missing'], missing)
        self.assertIsNone(closure)
        witness = {'schema': 'backend-contract-fact-readback/v1', 'source_head': 'a' * 40,
                   'observation': {'source_sha256': 'c' * 64, 'contract_sha256': 'd' * 64,
                                   'value_parity': {'checked_fields': ['amount'], 'mismatch_fields': [],
                                                    'uncovered_fields': {}, 'full_projection_parity': True}}}
        blockers, closure = receipt.readback_closure_blockers(witness, head='a' * 40)
        self.assertEqual([], blockers)
        self.assertTrue(closure['fact_scope_readback'])
        uncovered = {'schema': 'backend-contract-fact-readback/v1', 'source_head': 'a' * 40,
                     'observation': {'source_sha256': 'c' * 64, 'contract_sha256': 'd' * 64,
                                     'value_parity': {'checked_fields': ['amount'], 'mismatch_fields': [],
                                                      'uncovered_fields': {'partner': 'relation_or_non_scalar_projection'}}}}
        blockers, closure = receipt.readback_closure_blockers(uncovered, head='a' * 40)
        self.assertEqual(['fact_scope_readback_missing', 'projection_value_coverage_incomplete'], blockers)
        with self.assertRaisesRegex(ValueError, 'source head'):
            receipt.readback_closure_blockers(witness, head='b' * 40)

    def test_discover_receipt_locators_returns_only_valid_attempt_one_locators(self):
        runs={'workflow_runs':[
            {'id':10,'run_attempt':1,'head_sha':'a'*40,
             'repository':{'id':receipt.REPOSITORY_ID},'head_repository':{'id':receipt.REPOSITORY_ID},
             'event':'pull_request','path':'.github/workflows/backend_test_suite.yml',
             'run_started_at':datetime.now(timezone.utc).isoformat()},
            {'id':11,'run_attempt':2,'head_sha':'b'*40,
             'repository':{'id':receipt.REPOSITORY_ID},'head_repository':{'id':receipt.REPOSITORY_ID},
             'event':'pull_request','path':'.github/workflows/backend_test_suite.yml',
             'run_started_at':datetime.now(timezone.utc).isoformat()},
            {'id':12,'run_attempt':1,'head_sha':'c'*40,
             'repository':{'id':1},'head_repository':{'id':receipt.REPOSITORY_ID},
             'event':'pull_request','path':'.github/workflows/backend_test_suite.yml',
             'run_started_at':datetime.now(timezone.utc).isoformat()},
        ]}
        artifacts={'artifacts':[
            {'id':100,'name':'backend-execution-10-1-0','expired':False},
            {'id':101,'name':'backend-execution-10-1-1','expired':False},
            {'id':102,'name':'other','expired':False},
        ]}
        data={'actions/runs?status=success&per_page=30':runs,
              'actions/runs/10/artifacts?per_page=100':artifacts}
        def fetch(path):
            return json.dumps(data[path]).encode()
        locators=receipt.discover_receipt_locators(head='d'*40,modules=['core','scene'],fetch=fetch)
        self.assertEqual(4,len(locators))
        self.assertTrue(all(loc['run_id']==10 for loc in locators))
        self.assertEqual({100,101},{loc['artifact_id'] for loc in locators})
        self.assertEqual({'core','scene'},{loc['module'] for loc in locators})

    def test_discover_receipt_locators_degrades_to_empty_on_api_failure(self):
        def fetch(path):
            raise OSError('network down')
        self.assertEqual([],receipt.discover_receipt_locators(head='d'*40,modules=['core'],fetch=fetch))

    def test_discover_receipt_locators_is_bounded(self):
        runs={'workflow_runs':[{
            'id':100+index,'run_attempt':1,'head_sha':'a'*40,
            'repository':{'id':receipt.REPOSITORY_ID},'head_repository':{'id':receipt.REPOSITORY_ID},
            'event':'pull_request','path':'.github/workflows/backend_test_suite.yml',
            'run_started_at':datetime.now(timezone.utc).isoformat(),
        } for index in range(10)]}
        data={'actions/runs?status=success&per_page=30':runs}
        for index in range(10):
            data[f'actions/runs/{100+index}/artifacts?per_page=100']={'artifacts':[
                {'id':1000+index*10+shard,'name':f'backend-execution-{100+index}-1-{shard}','expired':False}
                for shard in range(4)
            ]}
        def fetch(path):
            return json.dumps(data[path]).encode()
        locators=receipt.discover_receipt_locators(head='d'*40,modules=['m%d' % i for i in range(10)],fetch=fetch)
        self.assertEqual(receipt.MAX_LOCATORS,len(locators))


if __name__ == '__main__':
    unittest.main()
