#!/usr/bin/env python3
"""R1 offline audit. Uses unchanged production entrypoints, never GitHub writes/DBs.
External GitHub/git transport is fixture-controlled for main-full CLI tests;
executor tests run actual Make and Node processes. Run from repository root.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
sys.path.insert(0, str(Path.cwd()))
from scripts.verify import frontend_dev_incremental as executor
from scripts.ci import main_full_release_dispatch as dispatch
from scripts.ci import release_condition

ROOT = Path.cwd()
OUT = ROOT / '.runtime/verify-system-closeout-01/replay'
OUT.mkdir(parents=True, exist_ok=True)
HEAD = subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
TREE = subprocess.check_output(['git','rev-parse','HEAD^{tree}'],text=True).strip()
rows=[]
def record(name, expected, observed, evidence, level):
    rows.append(dict(case=name,expected=expected,observed=observed,status='VERIFIED' if observed==expected else 'FAILED',evidence=evidence,evidence_level=level,source_head=HEAD))

with tempfile.TemporaryDirectory(prefix='sce-r1-executor-') as tmp:
    root=Path(tmp)
    (root/'ok.mjs').write_text("import test from 'node:test'; test('real pass',()=>{});\n")
    (root/'skip.mjs').write_text("import test from 'node:test'; test('skipped',{skip:true},()=>{throw Error('must not run')});\n")
    (root/'fail.mjs').write_text("import test from 'node:test'; test('real failure',()=>{throw Error('injected')});\n")
    cases={
        'node_pass':('node --test --test-reporter=tap ok.mjs','passed'),
        'node_skip':('node --test --test-reporter=tap skip.mjs','failed'),
        'node_failure':('node --test --test-reporter=tap fail.mjs','failed'),
        'zero':("printf 'Ran 0 tests in 0.001s\\nOK\\n'",'failed'),
        'incomplete_tap':("printf '# tests 5\\n'",'failed'),
        'mixed_incomplete':("printf 'Ran 1 test in 0.001s\\nOK\\n# tests 5\\n'",'failed'),
        'bare_pass':("printf 'PASS\\n'",'failed'),
        'masked_child_failure':('node --test --test-reporter=tap fail.mjs; node --test --test-reporter=tap ok.mjs','failed'),
        'nonzero_with_pass':("printf 'PASS tests=1\\n'; exit 3",'failed'),
    }
    for name,(recipe,expected) in cases.items():
        (root/'Makefile').write_text('verify.audit.unit:\n\t@'+recipe+'\n')
        log=OUT/(name+'.log')
        actual=executor._run_make_target('verify.audit.unit',root,log)
        (OUT/(name+'.json')).write_text(json.dumps(actual,indent=2)+'\n')
        record(name,expected,actual['status'],str(log.relative_to(ROOT)),'real Make/Node subprocess; controlled producer fixture')

# Exercise the actual main-full CLI. Only external git/gh transport is replaced.
with tempfile.TemporaryDirectory(prefix='sce-r1-remote-') as tmp:
    root=Path(tmp);bindir=root/'bin';bindir.mkdir();fixture=root/'fixture.json';trace=root/'trace.jsonl';state=root/'state.json'
    transport='''#!/usr/bin/env python3
import json,os,sys
from pathlib import Path
f=json.loads(Path(os.environ['R1_FIXTURE']).read_text());s=Path(os.environ['R1_STATE']);v=json.loads(s.read_text()) if s.exists() else {'views':0,'refs':0}
a=sys.argv[1:];name=Path(sys.argv[0]).name
with open(os.environ['R1_TRACE'],'a') as out: out.write(json.dumps({'command':name,'args':a})+'\\n')
if name=='git' and a==['ls-remote','origin','refs/heads/main']:
 v['refs']+=1;print((f['other_head'] if f['case']=='main_advanced_during_wait' and v['views'] else f['head'])+'\\trefs/heads/main')
elif name=='gh' and a[:2]==['repo','view']: print('lidefend/sce-backend-odoo')
elif name=='gh' and a[:2]==['run','view']:
 v['views']+=1;r=f['runs'][a[2]].copy()
 if f['case']=='main_advanced_during_wait' and v['views']==1:r.update(status='in_progress',conclusion='')
 print(json.dumps(r))
else: print('unexpected transport call '+str(a),file=sys.stderr);sys.exit(9)
s.write_text(json.dumps(v))
'''
    for name in ('git','gh'):
        p=bindir/name;p.write_text(transport);p.chmod(0o755)
    base=[];views={}
    for i,workflow in enumerate(dispatch.WORKFLOWS,101):
        raw=dict(databaseId=i,headSha=HEAD,headBranch='main',event='workflow_dispatch',status='completed',conclusion='success',url=f'https://github.com/{dispatch.REPOSITORY}/actions/runs/{i}',workflowName=workflow[:-4],attempt=1)
        base.append(dispatch.normalize_run(raw,workflow,HEAD));views[str(i)]=raw
    manifest_base=dict(schema_version=dispatch.SCHEMA,repository=dispatch.REPOSITORY,expected_main=HEAD,expected_tree=TREE,event='workflow_dispatch',head_branch='main',release_condition_kind='operator_full_audit',dispatched_at='2026-11-27T00:00:00+00:00',workflows=base)
    scenarios={'missing_condition':'DENY','failed_and_pending':'FAILURE_REPORTED','main_advanced_during_wait':'DENY','wrong_tree':'DENY','missing_workflow':'DENY','cross_head':'DENY','all_pending':'PENDING'}
    for name,expected in scenarios.items():
        doc=copy.deepcopy(manifest_base);runs=copy.deepcopy(views)
        if name=='failed_and_pending':runs['101']['conclusion']='failure';runs['102'].update(status='in_progress',conclusion='')
        if name=='all_pending':runs['101'].update(status='in_progress',conclusion='')
        if name=='wrong_tree':doc['expected_tree']='f'*40
        if name=='missing_workflow':doc['workflows'].pop()
        if name=='cross_head':runs['101']['headSha']='c'*40
        fixture.write_text(json.dumps(dict(case=name,head=HEAD,other_head='c'*40,runs=runs)));trace.write_text('');state.unlink(missing_ok=True)
        manifest=root/'manifest.json';manifest.write_text(json.dumps(doc))
        env=dict(os.environ,PATH=str(bindir)+os.pathsep+os.environ['PATH'],R1_FIXTURE=str(fixture),R1_TRACE=str(trace),R1_STATE=str(state))
        args=[sys.executable,str(ROOT/'scripts/ci/main_full_release_dispatch.py'),'verify','--expected-main',HEAD,'--manifest',str(manifest),'--wait-seconds','1' if name=='main_advanced_during_wait' else '0','--poll-seconds','0.01']
        p=subprocess.run(args,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        log=OUT/(name+'.log');log.write_text(p.stdout+'\nTRANSPORT CALLS\n'+trace.read_text())
        observed='PASS' if p.returncode==0 else 'PENDING' if 'still pending' in p.stdout else 'FAILURE_REPORTED' if 'did not succeed' in p.stdout else 'DENY'
        record(name,expected,observed,str(log.relative_to(ROOT)),'production CLI; fixture git/GitHub transport, not live workflow injection')
    # Independent release-condition CLI fails closed for malformed dependency input.
    condition_rows=[]
    for i,path in enumerate(sorted(release_condition.MAINLINE_REQUIRED_WORKFLOWS),201):
        condition_rows.append(dict(id=i,run_attempt=1,path=path,event='workflow_dispatch',head_branch='main',status='completed',conclusion='success',head_sha=HEAD,repository={'full_name':dispatch.REPOSITORY},head_repository={'full_name':dispatch.REPOSITORY}))
    for name in ['success','missing_auxiliary','latest_failure','cross_head','stale_main','pending']:
        rs=copy.deepcopy(condition_rows);current=HEAD
        if name=='missing_auxiliary':rs=[r for r in rs if 'auxiliary' not in r['path']]
        if name=='latest_failure':rs[0]['conclusion']='failure'
        if name=='cross_head':rs[0]['head_sha']='c'*40
        if name=='stale_main':current='c'*40
        if name=='pending':rs[0]['status']='in_progress'
        source=root/'runs.ndjson';source.write_text(''.join(json.dumps(r)+'\n' for r in rs));output=root/'condition.json';output.unlink(missing_ok=True)
        args=[sys.executable,str(ROOT/'scripts/ci/release_condition.py'),'--runs',str(source),'--output',str(output),'--repository',dispatch.REPOSITORY,'--head-sha',HEAD,'--tree',TREE,'--event','workflow_dispatch','--head-branch','main','--workflow-dispatch-producer','workflow_dispatch','--current-main',current]
        p=subprocess.run(args,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);log=OUT/('condition_'+name+'.log');log.write_text(p.stdout)
        record('condition_'+name,'PASS' if name=='success' else 'DENY','PASS' if p.returncode==0 else 'DENY',str(log.relative_to(ROOT)),'production CLI with controlled NDJSON input')
for row in rows:row['log_sha256']=hashlib.sha256((ROOT/row['evidence']).read_bytes()).hexdigest()
(OUT/'results.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps(rows,indent=2))
