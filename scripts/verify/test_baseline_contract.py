#!/usr/bin/env python3
"""Explicit reproducibility surface: stable case identities across fresh processes.

This is a finite declared surface, not a claim that arbitrary repository tests
or external systems are deterministic. No flaky retry or quarantine-as-pass.
"""
from __future__ import annotations
import argparse
import ast
import re
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import unittest
from scripts.dev.local_test_runner import source_fingerprint, IDENTITY

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / 'scripts/verify/test_baseline_manifest.json'


def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item


def ordered(cases, order, seed):
    cases = sorted(cases, key=lambda case: case.id())
    if order == 'reverse': cases.reverse()
    elif order == 'random': random.Random(seed).shuffle(cases)
    elif order != 'forward': raise ValueError('unknown ordering')
    ids = [case.id() for case in cases]
    if not ids or len(ids) != len(set(ids)):
        raise ValueError('empty or duplicate collected identities')
    return cases


class Results(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.outcomes = {}
    def startTest(self, test):
        super().startTest(test)
        self.outcomes[test.id()] = 'started'
    def addSuccess(self, test):
        super().addSuccess(test)
        if self.outcomes[test.id()] == 'started': self.outcomes[test.id()] = 'passed'
    def addFailure(self, test, err):
        super().addFailure(test, err); self.outcomes[test.id()] = 'failed'
    def addError(self, test, err):
        super().addError(test, err); self.outcomes[test.id()] = 'error'
    def addSkip(self, test, reason):
        super().addSkip(test, reason); self.outcomes[test.id()] = 'skipped'
    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test, err); self.outcomes[test.id()] = 'expected_failure'
    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test); self.outcomes[test.id()] = 'unexpected_success'
    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err is not None: self.outcomes[test.id()] = 'failed_subtest'


def validate_manifest(data):
    if data.get('schema') != 'test-baseline-surface/v1': raise ValueError('invalid baseline schema')
    modules=data.get('modules', [])
    if not modules or len(modules)!=len(set(modules)): raise ValueError('empty or duplicate surface')
    for module in modules:
        if not module.startswith(('scripts.ci.test_', 'scripts.verify.test_', 'scripts.ops.test_')):
            raise ValueError('undeclared test module namespace')
        if not (ROOT / (module.replace('.','/')+'.py')).is_file(): raise ValueError('missing declared module')
    # Empty quarantine is intentional. A newly flaky case blocks the baseline;
    # this runner offers no exclusion flag and never auto-retries failures.
    if data.get('quarantine') != []: raise ValueError('quarantined tests cannot establish this baseline')
    if data.get('orders') != ['forward','reverse','random'] or type(data.get('seed')) is not int:
        raise ValueError('three explicit orders and fixed seed required')
    orm=data.get('orm',{})
    if orm.get('module')!='smart_core' or orm.get('files')!=[
            'addons/smart_core/tests/test_contract_assembly_determinism.py',
            'addons/smart_core/tests/test_lowcode_config_contract_write_authority.py']:
        raise ValueError('unregistered ORM baseline surface')
    if orm.get('tags')!='contract_assembly_determinism/smart_core,lowcode_contract_write_authority/smart_core':
        raise ValueError('ORM baseline selection changed')
    return data


def compare(reports):
    if len(reports)!=3: raise ValueError('three independent runs required')
    reference=None
    for expected, report in zip(('forward','reverse','random'),reports):
        cases=report.get('collected',[]); results=report.get('outcomes',{})
        if (report.get('order')!=expected or report.get('status')!='passed' or not cases
                or len(cases)!=len(set(cases)) or set(cases)!=set(results)
                or any(value!='passed' for value in results.values())):
            raise ValueError('missing, duplicate, skipped or failed case')
        canonical=sorted(results.items())
        if reference is not None and canonical!=reference: raise ValueError('case identities or outcomes diverge')
        reference=canonical
    return len(reference)


def child(modules, order, seed, output):
    sys.path[:0]=[str(ROOT),str(ROOT/'scripts/ci'),str(ROOT/'scripts/verify')]
    source_before=source_fingerprint(os.environ)
    cases=ordered(list(flatten(unittest.defaultTestLoader.loadTestsFromNames(modules))),order,seed)
    ids=[test.id() for test in cases]
    result=unittest.TextTestRunner(resultclass=Results,verbosity=1).run(unittest.TestSuite(cases))
    passed=source_before==source_fingerprint(os.environ) and result.wasSuccessful() and len(result.outcomes)==len(ids) and all(x=='passed' for x in result.outcomes.values())
    output.write_text(json.dumps(dict(source_fingerprint=source_before,order=order,seed=seed,collected=ids,outcomes=result.outcomes,status='passed' if passed else 'failed'),indent=2)+'\n')
    return 0 if passed else 1


def expected_orm_cases(data):
    cases=[]
    for filename in data['orm']['files']:
        module=filename.removesuffix('.py').replace('addons/','',1).replace('/','.')
        tree=ast.parse((ROOT/filename).read_text())
        for cls in tree.body:
            if isinstance(cls,ast.ClassDef):
                cases += [module+':'+cls.name+'.'+method.name for method in cls.body
                          if isinstance(method,ast.FunctionDef) and method.name.startswith('test_')]
    if not cases or len(set(cases))!=len(cases):raise ValueError('invalid ORM case declaration')
    return sorted(cases)


def verify_orm_reports(reports, expected, source):
    if len(reports)!=3:raise ValueError('three fresh ORM executions required')
    environments=set()
    for order,r in zip(('forward','reverse','random'),reports):
        if (r.get('seed')!=20261026 or r.get('profile')!=IDENTITY or r.get('purpose')!='test' or r.get('order')!=order or r.get('status')!='passed' or r.get('cases')!=expected
                or r.get('count')!=len(expected) or r.get('source_fingerprint')!=source
                or r.get('source_unchanged') is not True or r.get('fresh_database') is not True
                or r.get('profile_unchanged') is not True
                or r.get('transient_application_state') is not True or r.get('image_unchanged') is not True
                or r.get('cleanup') not in ('absent','removed_exact_carrier')
                or r.get('process_status')!=0 or r.get('guard_status')!=0):
            raise ValueError('ORM case, input, cleanup or outcome mismatch')
        package=r.get('packages_sha256','');image=r.get('image_id','')
        if not re.fullmatch('[a-f0-9]{64}',package) or not re.fullmatch('sha256:[a-f0-9]{64}',image):
            raise ValueError('missing runtime dependencies')
        profile_sha=r.get('profile_sha256','')
        if not re.fullmatch('[a-f0-9]{64}',profile_sha):raise ValueError('missing profile identity')
        environments.add((package,image,profile_sha))
        actual=r.get('execution_order',[])
        if sorted(actual)!=expected:raise ValueError('execution order loses cases')
        groups={case.rsplit('.',1)[0] for case in expected}
        for cls in groups:
            methods=sorted(case.rsplit('.',1)[1] for case in expected if case.rsplit('.',1)[0]==cls)
            if order=='reverse':methods.reverse()
            elif order=='random':random.Random(str(r['seed'])+':odoo.addons.'+cls.replace(':','.')).shuffle(methods)
            if [case.rsplit('.',1)[1] for case in actual if case.rsplit('.',1)[0]==cls]!=methods:
                raise ValueError('actual ORM method order does not match requested order')
    if len(environments)!=1:raise ValueError('runtime dependency drift between attempts')
    return len(expected)


def orm_surface(data, output):
    output.mkdir(parents=True,exist_ok=True)
    receipt=output/'orm-receipt.json'
    receipt.write_text(json.dumps({'status':'running'})+'\n')
    source=source_fingerprint(os.environ)
    reports=[];paths=[];hashes={}
    try:
        for order in data['orders']:
            path=output/('orm-'+order+'.log')
            with path.open('w') as log:
                result=subprocess.run(['make','--no-print-directory','local.test.test',
                    'MODULE='+data['orm']['module'],'TEST_TAGS='+data['orm']['tags'],'LOCAL_TEST_ORDER='+order],
                    cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=7500)
            matches=re.findall(r'^\[local.test\] receipt=(.+)$',path.read_text(),re.M)
            if result.returncode or len(matches)!=1:raise ValueError('failed ORM order '+order)
            report_path=Path(matches[0]).resolve()
            if ROOT/'.runtime/test-baseline' not in report_path.parents:raise ValueError('foreign ORM receipt')
            r=json.loads(report_path.read_text());log_path=(ROOT/r['log']).resolve()
            if ROOT/'.runtime/test-baseline' not in log_path.parents or hashlib.sha256(log_path.read_bytes()).hexdigest()!=r['log_sha256']:
                raise ValueError('ORM log evidence mismatch')
            reports.append(r);paths.append(str(report_path.relative_to(ROOT)))
            hashes[paths[-1]]=hashlib.sha256(report_path.read_bytes()).hexdigest()
        if source_fingerprint(os.environ)!=source:raise ValueError('source changed during ORM comparison')
        count=verify_orm_reports(reports,expected_orm_cases(data),source)
        receipt.write_text(json.dumps(dict(schema='test-baseline-orm/v1',status='passed',source_fingerprint=source,count=count,orders=data['orders'],proof='class-local method ordering on fresh databases',reports=paths,receipt_sha256=hashes),indent=2)+'\n')
        print(f'[test.baseline.orm] PASS cases={count} fresh_attempts=3 receipt={receipt}')
        return 0
    except (ValueError,KeyError,TypeError,AttributeError,OSError,subprocess.SubprocessError) as exc:
        receipt.write_text(json.dumps({'schema':'test-baseline-orm/v1','status':'failed','reason':str(exc),'reports':paths})+'\n')
        print('[test.baseline.orm] FAIL '+str(exc));return 1


def verified_json(path, digest):
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=digest:raise ValueError('evidence digest mismatch')
    value=json.loads(raw)
    if not isinstance(value,dict):raise ValueError('evidence must be an object')
    return value


def verify_local_baseline(data):
    source=source_fingerprint(os.environ)
    offline=ROOT/'.runtime/test-baseline/offline'
    receipt=json.loads((offline/'receipt.json').read_text())
    if receipt.get('status')!='passed' or receipt.get('source_fingerprint')!=source:
        raise ValueError('offline evidence stale or failed')
    if receipt.get('manifest_sha256')!=hashlib.sha256(MANIFEST.read_bytes()).hexdigest():
        raise ValueError('offline declaration changed')
    reports=[]
    for order in data['orders']:
        path=offline/(order+'.json')
        child=verified_json(path,receipt['reports'][order])
        if child.get('source_fingerprint')!=source:raise ValueError('child source changed')
        reports.append(child)
    count=compare(reports)
    orm=json.loads((ROOT/'.runtime/test-baseline/orm/orm-receipt.json').read_text())
    if orm.get('status')!='passed' or orm.get('source_fingerprint')!=source:raise ValueError('ORM evidence stale or failed')
    reports=[]
    for relative in orm['reports']:
        path=(ROOT/relative).resolve()
        if ROOT/'.runtime/test-baseline' not in path.parents:raise ValueError('foreign ORM receipt')
        report=verified_json(path,orm['receipt_sha256'][relative]);log=(ROOT/report['log']).resolve()
        if ROOT/'.runtime/test-baseline' not in log.parents or hashlib.sha256(log.read_bytes()).hexdigest()!=report['log_sha256']:
            raise ValueError('ORM log changed')
        reports.append(report)
    orm_count=verify_orm_reports(reports,expected_orm_cases(data),source)
    result=dict(schema='test-baseline-local-acceptance/v1',status='passed',source_fingerprint=source,
                head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                offline_cases=count,orm_cases=orm_count,independent_orders=3,quarantine=0,
                limits=['Explicit manifest surface only','ORM order proof is class-local','Mainline integration still requires independent review and current remote CI'])
    if source_fingerprint(os.environ)!=source:raise ValueError('source changed during final verification')
    (ROOT/'.runtime/test-baseline/baseline.json').write_text(json.dumps(result,indent=2)+'\n')
    print('[test.baseline.ready] PASS '+json.dumps(result))
    return 0


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('--verify',action='store_true')
    parser.add_argument('--orm',action='store_true')
    parser.add_argument('--child',action='store_true')
    parser.add_argument('--order',choices=['forward','reverse','random'])
    parser.add_argument('--output',type=Path,default=ROOT/'.runtime/test-baseline/offline')
    args=parser.parse_args(argv)
    result_name='orm-receipt.json' if args.orm else 'receipt.json'
    result_path=ROOT/'.runtime/test-baseline/baseline.json' if args.verify else args.output/result_name
    if not args.child:
        result_path.parent.mkdir(parents=True,exist_ok=True)
        result_path.write_text(json.dumps({'status':'running'})+'\n')
    try:
        data=validate_manifest(json.loads(MANIFEST.read_text()))
        if args.verify: return verify_local_baseline(data)
        if args.orm: return orm_surface(data,args.output)
        if args.child: return child(data['modules'],args.order,data['seed'],args.output)
        args.output.mkdir(parents=True,exist_ok=True)
        receipt_path=args.output/'receipt.json'
        receipt_path.write_text(json.dumps({'status':'running','schema':'test-baseline-offline/v1'})+'\n')
        source_before=source_fingerprint(os.environ)
        head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        reports=[]
        for order in data['orders']:
            path=args.output/(order+'.json')
            path.unlink(missing_ok=True)
            env=dict(os.environ,PYTHONHASHSEED=str(data['seed']))
            with (args.output/(order+'.log')).open('w') as log:
                result=subprocess.run([sys.executable,'-m','scripts.verify.test_baseline_contract','--child','--order',order,'--output',str(path)],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=1200)
            if result.returncode: raise ValueError('failed order '+order+'; no automatic retry')
            reports.append(json.loads(path.read_text()))
        if source_fingerprint(os.environ)!=source_before: raise ValueError('source changed during reproducibility run')
        if any(r.get('source_fingerprint')!=source_before for r in reports): raise ValueError('child source identity differs')
        count=compare(reports)
        receipt=dict(schema='test-baseline-offline/v1',head=head,source_fingerprint=source_before,source_unchanged=True,status='passed',count=count,orders=data['orders'],seed=data['seed'],modules=data['modules'],quarantine=[],manifest_sha256=hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),reports={order:hashlib.sha256((args.output/(order+'.json')).read_bytes()).hexdigest() for order in data['orders']})
        (args.output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
        print(f'[test.baseline] PASS cases={count} independent_orders=3 quarantine=0 receipt={args.output}/receipt.json')
        return 0
    except (ValueError,KeyError,TypeError,AttributeError,OSError,subprocess.SubprocessError) as exc:
        if not args.child:
            result_path.write_text(json.dumps({'schema':'test-baseline-failure/v1','status':'failed','reason':str(exc)})+'\n')
        print('[test.baseline] FAIL '+str(exc));return 1

if __name__=='__main__':raise SystemExit(main())
