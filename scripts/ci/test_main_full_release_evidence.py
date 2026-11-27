#!/usr/bin/env python3
"""Real operator CLI against a bounded GitHub transport fixture, no DB/writes."""
from __future__ import annotations
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from datetime import datetime, timedelta, timezone

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.ci import backend_suite_plan as plans
from scripts.ci import backend_test_receipt as receipts
from scripts.ci import main_full_release_dispatch as dispatch
from scripts.ci.main_full_release_evidence import REQUIRED_JOBS, required_runner_kinds
from scripts.ci.release_condition import build_condition


def encoded(value):
    return json.dumps(value, sort_keys=True).encode()


class Fixture:
    def __init__(self):
        self.head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        self.tree = subprocess.check_output(['git', 'rev-parse', 'HEAD^{tree}'], cwd=ROOT, text=True).strip()
        self.data, self.runs, self.jobs, self.artifacts, self.views = {}, {}, {}, {}, {}
        self.extra_runs = {}
        self.now = datetime.now(timezone.utc)
        self.start = (self.now - timedelta(minutes=2)).isoformat()
        self.end = (self.now + timedelta(minutes=2)).isoformat()
        self.manifest = dict(schema_version=dispatch.SCHEMA, repository=dispatch.REPOSITORY,
            expected_main=self.head, expected_tree=self.tree, event='workflow_dispatch', head_branch='main',
            release_condition_kind='operator_full_audit', dispatched_at=self.start, workflows=[])
        for i, name in enumerate(dispatch.WORKFLOWS, 101):
            r = dict(id=i, run_attempt=1, head_sha=self.head, head_branch='main', event='workflow_dispatch',
                     path='.github/workflows/'+name, status='completed', conclusion='success',
                     repository={'full_name':dispatch.REPOSITORY}, head_repository={'full_name':dispatch.REPOSITORY},
                     created_at=self.start)
            self.runs[name] = r
            view = dict(databaseId=i, attempt=1, headSha=self.head, headBranch='main', event='workflow_dispatch',
                        status='completed', conclusion='success', url=f'https://github.com/{dispatch.REPOSITORY}/actions/runs/{i}',
                        workflowName=name[:-4])
            self.views[str(i)] = view
            self.manifest['workflows'].append(dispatch.normalize_run(view, name, self.head))
            self.jobs[name] = []; self.artifacts[name] = []
            for job in sorted(REQUIRED_JOBS[name]):self.job(name, job)
        for workflow, suite, prefix in [('professional_quality_gate.yml','product','backend_impact_suite'),
                                        ('auxiliary_backend_suite.yml','demo','demo'),
                                        ('auxiliary_backend_suite.yml','acceptance','acceptance')]:
            self.suite(workflow,suite,prefix)
        workflow = 'frontend_release_gate.yml';run=self.runs[workflow]
        sections={'accessibility','delivery_hardening','error_recovery','navigation','performance','responsive','role_release_projection','static'}
        members={f'sections/{s}.json':encoded({'git_sha':self.head,'result':'PASS'}) for s in sections}
        report=dict(git_sha=self.head,git_tree=self.tree,result='PASS',summary_exit_code=0,
                    workflow={'run_id':str(run['id']),'run_attempt':'1','event':'workflow_dispatch','checkout_sha':self.head},
                    required_sections=sorted(sections),blocking_failures=[],missing_evidence=[],evidence={})
        for section in sections:
            path=f'sections/{section}.json';report['evidence'][section]=dict(path='artifacts/'+path,git_sha=self.head,sha256=hashlib.sha256(members[path]).hexdigest())
        members['frontend-release-audit/report.json']=encoded(report)
        members['frontend-release-audit/gate-result.json']=encoded(dict(schema_version='frontend-release-gate-result/v1',
            git_sha=self.head,git_tree=self.tree,result='PASS',event='workflow_dispatch',run_id=str(run['id']),run_attempt='1'))
        self.artifact(workflow,f"frontend-release-evidence-{run['id']}-1-{self.head}",members)
        condition=build_condition([r for n,r in self.runs.items() if n!='release_candidate_gate.yml'],repository=dispatch.REPOSITORY,
            head_sha=self.head,tree=self.tree,event='workflow_dispatch',head_branch='main',workflow_dispatch_producer='workflow_dispatch',schedule_slot=None,current_main=self.head)
        self.artifact('release_candidate_gate.yml',f'release-condition-106-1-{self.head}',{'release-condition.json':encoded(condition)})

    def job(self, workflow, name):
        run=self.runs[workflow];job=dict(id=1000+sum(len(x) for x in self.jobs.values()),name=name,run_id=run['id'],run_attempt=1,
            head_sha=self.head,status='completed',conclusion='success',started_at=self.start,completed_at=self.end)
        self.jobs[workflow].append(job)

    def artifact(self, workflow, name, members):
        run=self.runs[workflow];aid=2000+sum(len(x) for x in self.artifacts.values());stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as z:
            for path,raw in members.items():z.writestr(path,raw)
        raw=stream.getvalue();self.data[f'actions/artifacts/{aid}/zip']=raw
        self.artifacts[workflow].append(dict(id=aid,name=name,expired=False,created_at=self.now.isoformat(),
            workflow_run={'id':run['id'],'head_sha':self.head},digest='sha256:'+hashlib.sha256(raw).hexdigest()))

    def change_artifact(self, workflow, starts, member, mutate):
        artifact=next(a for a in self.artifacts[workflow] if a['name'].startswith(starts))
        key=f"actions/artifacts/{artifact['id']}/zip"
        members=receipts.archive_members(self.data[key]);value=json.loads(members[member]);mutate(value)
        members[member]=encoded(value);stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as archive:
            for name,data in members.items():archive.writestr(name,data)
        self.data[key]=stream.getvalue();artifact['digest']='sha256:'+hashlib.sha256(stream.getvalue()).hexdigest()

    def change_execution_fact(self, fact):
        artifact=next(a for a in self.artifacts['professional_quality_gate.yml'] if a['name'].startswith('backend-execution'))
        key=f"actions/artifacts/{artifact['id']}/zip"
        members=receipts.archive_members(self.data[key])
        name=next(name for name in members if name.endswith('/orm/receipt.json'))
        row=json.loads(members[name]);directory=name.rsplit('/',1)[0]
        if fact=='selection':row['selection']='sc_smoke/'+row['module']
        elif fact=='source':row['test_source_blobs']=[]
        else:
            filename='runtime.json' if fact=='runtime' else 'python.json'
            members[directory+'/'+filename]=b'{}';row['files'][filename]=hashlib.sha256(b'{}').hexdigest()
        members[name]=encoded(row);stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as archive:
            for name,data in members.items():archive.writestr(name,data)
        self.data[key]=stream.getvalue();artifact['digest']='sha256:'+hashlib.sha256(stream.getvalue()).hexdigest()

    def suite(self, workflow, suite, prefix):
        run=self.runs[workflow];plan=plans.build_plan('',self.head,suite=suite,include_inputs=True);plan_raw=encoded(plan)
        self.job(workflow,prefix+' / plan');self.job(workflow,prefix+' / verify_coverage')
        self.artifact(workflow,f"backend-plan-{run['id']}-{suite}",{'backend-plan.json':plan_raw})
        kinds=required_runner_kinds(self.head,plan['modules'])
        for shard in plan['shards']:
            self.job(workflow,f"{prefix} / backend_suite ({shard['index']})")
            members={'scope-plan.json':plan_raw}
            for module in shard['modules']:
                classes=[row for row in plan['changed_test_coverage'] if row['module']==module]
                kind=kinds[module];count=max(1,len(classes))
                # Native host unittest records its actual environment in python.json,
                # without an inline marker; it must not be confused with the operator host.
                log=b'Ran 1 test in 0.001s\nOK\n'
                if kind=='orm':
                    if not classes:classes=[{'logger':f'odoo.addons.{module}.tests.test_fixture','class':'TestFixture','method':'test_one'}]
                    log=(''.join(f"2026-11-27 00:00:00 INFO fixture_db {row['logger']}: Starting {row['class']}.{row['method']} ...\n" for row in classes)+f"0 failed, 0 error(s) of {count} tests when loading database 'fixture_db'\n").encode()+receipts.ENV_MARKER.encode()+encoded({'python':'3.fixture','packages':[{'name':'fixture'}]})+b'\n'
                runtime={'services':{name:{'image_id':'sha256:'+'1'*64} for name in ('db','redis')},'odoo_image_id':'sha256:'+'2'*64}
                files={'execution.log':log,'runtime.json':encoded(runtime),'python.json':encoded({'python':'3.fixture','packages':[{'name':'fixture'}]})}
                row=dict(schema=receipts.SCHEMA,module=module,kind=kind,execution='',source_head=self.head,source_tree=self.tree,
                    input_binding={'policy':'whole-tracked-tree/v1','tree':self.tree},
                    test_source_blobs=plans.impact.git('ls-tree','-r',self.head,'--',*[root+'/'+module+'/tests' for root in plans.impact.ROOTS]).strip().splitlines(),
                    selection='/'+module if kind=='orm' else 'test*.py',
                    integration_base='',exit_code=0,test_count=count,database='fixture_db' if classes else '',scope_plan=receipts.scope_reference(plan_raw,head=self.head,base='',module=module),
                    issued_at=self.now.isoformat(),expires_at=(self.now+timedelta(hours=24)).isoformat(),reuse_ready=False,
                    provenance={'GITHUB_REPOSITORY':dispatch.REPOSITORY,'GITHUB_RUN_ID':str(run['id']),'GITHUB_RUN_ATTEMPT':'1'},
                    files={k:hashlib.sha256(v).hexdigest() for k,v in files.items()})
                files['receipt.json']=encoded(row)
                for name,raw in files.items():members[f'{module}/{kind}/{name}']=raw
            self.artifact(workflow,f"backend-execution-{run['id']}-{suite}-{shard['index']}",members)
        self.artifact(workflow,f"changed-test-coverage-{run['id']}-{suite}",{'changed-test-coverage.json':encoded({'head':self.head,'base':'','tests':[dict(row,status='executed') for row in plan['changed_test_coverage']],'pending':[]})})

    def responses(self):
        data=dict(self.data)
        for name,run in self.runs.items():
            rid=run['id'];data[f'actions/runs/{rid}']=encoded(run)
            data[f"actions/workflows/{name}/runs?head_sha={self.head}&per_page=100&page=1"]=encoded({'total_count':1+len(self.extra_runs.get(name,[])),'workflow_runs':[run,*self.extra_runs.get(name,[])]})
            data[f'actions/runs/{rid}/attempts/1/jobs?per_page=100&page=1']=encoded({'total_count':len(self.jobs[name]),'jobs':self.jobs[name]})
            data[f'actions/runs/{rid}/artifacts?per_page=100&page=1']=encoded({'total_count':len(self.artifacts[name]),'artifacts':self.artifacts[name]})
        return data


TRANSPORT = '''#!/usr/bin/env python3
import json,os,sys
from pathlib import Path
root=Path(os.environ['QUAL_FIXTURE']);args=sys.argv[1:]
with (root/'calls').open('a') as f:f.write(json.dumps([Path(sys.argv[0]).name,*args])+'\\n')
if os.environ.get('QUAL_PROGRAM',Path(sys.argv[0]).name)=='git':
 if args==['ls-remote','origin','refs/heads/main']:
  seen=(root/'ref-seen').exists();(root/'ref-seen').touch();print((os.environ['QUAL_OTHER'] if seen and os.environ.get('QUAL_ADVANCE') else os.environ['QUAL_HEAD'])+'\\trefs/heads/main')
 else:os.execv(os.environ['QUAL_REAL_GIT'],[os.environ['QUAL_REAL_GIT'],*args])
elif args[:2]==['repo','view']:print('lidefend/sce-backend-odoo')
elif args[:2]==['run','view']:
 row=json.loads((root/('view-'+args[2])).read_text())
 if os.environ.get('QUAL_PENDING') and args[2]=='101' and not (root/'pending-seen').exists():
  (root/'pending-seen').touch();row.update(status='in_progress',conclusion='')
 print(json.dumps(row))
elif args[0]=='api':
 key=args[-1].removeprefix('repos/lidefend/sce-backend-odoo/');index=json.loads((root/'index').read_text());sys.stdout.buffer.write((root/index[key]).read_bytes())
else:raise SystemExit('unexpected transport request')
'''


class OperatorCliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Qualify a real clean checkout containing the current implementation.
        # Only GitHub transport is simulated; HEAD/tree/status use real Git.
        global ROOT
        original = ROOT
        temporary = tempfile.TemporaryDirectory(prefix='qualification-source-')
        cls.addClassCleanup(temporary.cleanup)
        checkout = Path(temporary.name) / 'repo'
        subprocess.run(['git', 'clone', '--quiet', '--shared', '--no-checkout', str(original), str(checkout)], check=True)
        subprocess.run(['git', '-C', str(checkout), 'checkout', '--quiet', '--detach', 'HEAD'], check=True)
        delta = subprocess.check_output(['git', 'diff', '--binary', 'HEAD'], cwd=original)
        if delta:
            subprocess.run(['git', 'apply', '--binary'], cwd=checkout, input=delta, check=True)
            subprocess.run(['git', 'add', '-A'], cwd=checkout, check=True)
            subprocess.run(['git', '-c', 'user.name=Qualification fixture', '-c', 'user.email=fixture@example.invalid',
                            'commit', '-qm', 'current qualification implementation'], cwd=checkout, check=True)
        old_impact_root = plans.impact.ROOT
        def restore():
            global ROOT
            ROOT = original
            plans.impact.ROOT = old_impact_root
        cls.addClassCleanup(restore)
        ROOT = checkout
        plans.impact.ROOT = checkout
        cls.fixture=Fixture()

    def execute(self, mutate=None, *, advance=False, pending=False, mode='verify'):
        fixture=copy.deepcopy(self.fixture)
        if mutate:mutate(fixture)
        with tempfile.TemporaryDirectory(prefix='qualification-cli-') as tmp:
            root=Path(tmp);bindir=root/'bin';bindir.mkdir();index={}
            for i,(key,value) in enumerate(fixture.responses().items()):
                name=f'response-{i}';(root/name).write_bytes(value);index[key]=name
            (root/'index').write_bytes(encoded(index))
            for rid,row in fixture.views.items():(root/('view-'+rid)).write_bytes(encoded(row))
            for name in ('git','gh'):
                p=bindir/name;p.write_text(TRANSPORT);p.chmod(0o755)
            (root/'transport.py').write_text(TRANSPORT)
            (bindir/'git').write_text('#!/bin/sh\nif [ \"$1\" = ls-remote ]; then\n  QUAL_PROGRAM=git exec python3 \"$QUAL_FIXTURE/transport.py\" \"$@\"\nfi\nexec \"$QUAL_REAL_GIT\" \"$@\"\n')
            manifest=root/'manifest.json';manifest.write_bytes(encoded(fixture.manifest))
            env=dict(os.environ,PATH=str(bindir)+os.pathsep+os.environ['PATH'],QUAL_FIXTURE=str(root),QUAL_HEAD=fixture.head,
                     QUAL_OTHER='f'*40,QUAL_REAL_GIT=shutil.which('git'),QUAL_ADVANCE='1' if advance else '',QUAL_PENDING='1' if pending else '')
            p=subprocess.run([sys.executable,str(ROOT/'scripts/ci/main_full_release_dispatch.py'),mode,'--expected-main',fixture.head,
                              '--manifest',str(manifest),*(['--wait-seconds','2' if pending else '0'] if mode=='verify' else []),'--poll-seconds','0.01'],cwd=ROOT,env=env,text=True,capture_output=True,timeout=120)
            print(p.stdout, end='')
            return p.returncode,p.stdout,json.loads(manifest.read_bytes()),(root/'calls').read_text()

    def test_local_checkout_identity_and_cleanliness_guard_both_entrypoints(self):
        original = self.fixture.head
        # A distinct real clean commit, retaining the same tree, must be refused.
        other = subprocess.check_output(['git', '-c', 'user.name=Qualification fixture',
            '-c', 'user.email=fixture@example.invalid', 'commit-tree', self.fixture.tree,
            '-p', original, '-m', 'different clean checkout'], cwd=ROOT, text=True).strip()
        try:
            subprocess.run(['git', 'checkout', '--quiet', '--detach', other], cwd=ROOT, check=True)
            self.assertEqual(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT), b'')
            for mode in ('verify', 'dispatch'):
                with self.subTest(mode=mode, mismatch='head'):
                    code,text,result,calls=self.execute(mode=mode)
                    self.assertNotEqual(code,0,text);self.assertIn('local HEAD does not match',text)
                    self.assertNotIn('verified_at',result);self.assertNotIn('"workflow", "run"',calls)
        finally:
            subprocess.run(['git', 'checkout', '--quiet', '--detach', original], cwd=ROOT, check=True)
        dirty = ROOT / 'qualification-untracked-negative.txt'
        try:
            dirty.write_text('uncommitted source must not qualify')
            for mode in ('verify', 'dispatch'):
                with self.subTest(mode=mode, mismatch='dirty'):
                    code,text,result,calls=self.execute(mode=mode)
                    self.assertNotEqual(code,0,text);self.assertIn('worktree must be clean',text)
                    self.assertNotIn('verified_at',result);self.assertNotIn('"workflow", "run"',calls)
        finally:
            dirty.unlink()

    def test_complete_actual_cli_evidence_passes(self):
        code,text,result,_=self.execute();self.assertEqual(code,0,text);self.assertEqual(result['qualification_evidence']['status'],'VERIFIED')
        self.assertEqual(len(result['qualification_evidence']['backend_suites']),3)

    def test_missing_artifact_wrong_tree_main_advance_and_job_deny(self):
        mutations={
            'latest_failed':lambda f:f.extra_runs.update({'public_guard.yml':[dict(f.runs['public_guard.yml'],id=999,created_at=f.end,conclusion='failure')]}),
            'cross_head':lambda f:f.runs['public_guard.yml'].update(head_sha='0'*40),
            'condition':lambda f:f.artifacts['release_candidate_gate.yml'].clear(),
            'tree':lambda f:f.manifest.update(expected_tree='f'*40),
            'job':lambda f:f.jobs['professional_quality_gate.yml'].pop(),
            'shard':lambda f:f.artifacts['professional_quality_gate.yml'].pop(1),
            'auxiliary':lambda f:f.artifacts['auxiliary_backend_suite.yml'].clear(),
            'attempt':lambda f:f.runs['public_guard.yml'].update(run_attempt=2),
            'pending_coverage':lambda f:f.jobs['auxiliary_backend_suite.yml'][1].update(conclusion='skipped'),
            'frontend':lambda f:f.artifacts['frontend_release_gate.yml'].clear(),
            'artifact_digest':lambda f:f.artifacts['release_candidate_gate.yml'][0].update(digest='sha256:'+'0'*64),
            'artifact_identity':lambda f:f.artifacts['release_candidate_gate.yml'][0]['workflow_run'].update(head_sha='0'*40),
            'condition_tree':lambda f:f.change_artifact('release_candidate_gate.yml','release-condition','release-condition.json',lambda r:r.update(exact_tree='0'*40)),
            'condition_run':lambda f:f.change_artifact('release_candidate_gate.yml','release-condition','release-condition.json',lambda r:r['required_workflows'][0].update(run_id=999)),
            'condition_missing_workflow':lambda f:f.change_artifact('release_candidate_gate.yml','release-condition','release-condition.json',lambda r:r['required_workflows'].pop()),
            'coverage_pending':lambda f:f.change_artifact('professional_quality_gate.yml','changed-test-coverage','changed-test-coverage.json',lambda r:r.update(pending=[{'status':'pending'}])),
        }
        reasons={
            'latest_failed':'latest authoritative', 'cross_head':'identity/outcome mismatch',
            'condition':'missing or ambiguous artifact: release-condition',
            'tree':'manifest tree differs', 'job':'required job missing',
            'shard':'missing or ambiguous artifact: backend-execution',
            'auxiliary':'missing or ambiguous artifact: backend-plan',
            'attempt':'identity/outcome mismatch', 'pending_coverage':'required job missing',
            'frontend':'missing or ambiguous artifact: frontend-release',
            'artifact_digest':'artifact digest missing or mismatched',
            'artifact_identity':'artifact not attributable',
            'condition_tree':'release condition does not match',
            'condition_run':'release condition does not match',
            'condition_missing_workflow':'release condition does not match',
            'coverage_pending':'changed-test coverage identity or result mismatch',
        }
        for case,mutate in mutations.items():
            with self.subTest(case=case):
                print("[qualification-negative] " + case, flush=True)
                code,text,result,_=self.execute(mutate);self.assertNotEqual(code,0,text);self.assertNotIn('verified_at',result);self.assertIn(reasons[case],text)
        code,text,_,calls=self.execute(advance=True,pending=True);self.assertNotEqual(code,0,text);self.assertEqual(calls.count('ls-remote'),2)

    def test_incomplete_execution_facts_cannot_qualify_full_suite(self):
        for fact,reason in {'selection':'full module selection', 'source':'test source inventory',
                            'runtime':'runtime service identity', 'python':'Python environment differs'}.items():
            with self.subTest(fact=fact):
                print('[qualification-execution-negative] '+fact,flush=True)
                code,text,result,_=self.execute(lambda fixture:fixture.change_execution_fact(fact))
                self.assertNotEqual(code,0,text);self.assertIn(reason,text);self.assertNotIn('verified_at',result)

    def test_wait_queries_only_nonterminal_runs_and_rechecks_final_main(self):
        code,text,result,calls=self.execute(pending=True)
        self.assertEqual(code,0,text)
        observed=[json.loads(line) for line in calls.splitlines()]
        self.assertEqual(sum(row[1:3]==['run','view'] for row in observed),7)
        self.assertEqual(sum('ls-remote' in row for row in observed),2)

    def test_terminal_failure_wins_over_pending_and_reports_matrix(self):
        def mutate(f):
            f.views['101'].update(conclusion='failure');f.views['102'].update(status='in_progress',conclusion='')
        code,text,_,calls=self.execute(mutate);self.assertNotEqual(code,0);self.assertIn('did not succeed',text)
        self.assertIn('in_progress',text);self.assertNotIn('still pending',text);self.assertNotIn('artifacts',calls)


if __name__=='__main__':unittest.main()
