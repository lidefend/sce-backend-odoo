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


if __name__ == '__main__':
    unittest.main()
