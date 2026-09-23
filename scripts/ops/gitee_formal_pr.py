"""Create or inspect the one reviewed integration PR; never merge or deploy."""
from __future__ import annotations
import argparse
import json
import os
import tempfile
from pathlib import Path
import re
import subprocess
import urllib.parse
import urllib.request
from scripts.ci.gitee_ci_checks import API, BASE, ReportError
from scripts.ci.gitee_pr_identity import ReadAPI, observe

BRANCH='fix/gitee-temporary-integration-v1'
TITLE='ci: restore Gitee integration with isolated self-hosted checks'
BODY="""The GitHub outage left Gitee without verified integration gates. This change connects the existing signed receiver and isolated worker to exact-commit PR checks, durable reporting, and bounded service updates.

Architecture Impact: P4 ops delivery tool.
Layer Target: existing Gitee receiver, worker, and governed publication tooling.
Validation: local targeted tests and exact-head Quick; real PR gate acceptance is recorded separately.

This PR does not authorize automatic merging or product deployment. Unsupported candidate and frontend runtime lanes fail closed.
"""

class PRAPI(API):
    def call(self,method,suffix,fields=None):
        if (method,suffix) not in {('GET','/pulls?state=open&per_page=100'),('POST','/pulls')}:
            raise ReportError('endpoint_rejected')
        data=urllib.parse.urlencode(fields).encode() if fields else None
        request=urllib.request.Request(BASE+suffix,data=data,method=method,headers={'Authorization':'token '+self.token,'Content-Type':'application/x-www-form-urlencoded'})
        try:
            with self.opener.open(request,timeout=15) as response:raw=response.read(1048577)
            if len(raw)>1048576:raise ValueError()
            return json.loads(raw)
        except Exception:raise ReportError('pr_request_uncertain') from None

def select(rows):
    if not isinstance(rows,list) or len(rows)>=100:raise ValueError('pr_list_incomplete')
    matches=[x for x in rows if x.get('head',{}).get('ref')==BRANCH and x.get('base',{}).get('ref')=='main']
    if len(matches)>1:raise ValueError('ambiguous_pr')
    return matches[0] if matches else None

def ensure(api,reader,head,base,ledger,apply=False):
    source=reader.get('/branches/'+urllib.parse.quote(BRANCH,safe=''))
    target=reader.get('/branches/main')
    if source.get('commit',{}).get('sha')!=head or target.get('commit',{}).get('sha')!=base or target.get('protected') is not True:
        raise ValueError('remote_identity_drift')
    existing=select(api.call('GET','/pulls?state=open&per_page=100'))
    if existing:
        snapshot=observe(reader,number=existing['number'],source=BRANCH,head=head,base=base)
        return {'status':'existing','url':'https://gitee.com/leegege/sce-product-odoo/pulls/'+str(existing['number']),'snapshot':snapshot}
    if not apply:return {'status':'planned','head':head,'base':base,'title':TITLE,'body':BODY,'writes':0}
    if ledger.exists():raise ValueError('previous_create_unresolved_inspect_before_retry')
    ledger.parent.mkdir(parents=True,exist_ok=True)
    with ledger.open('x') as f:
        json.dump({'head':head,'base':base,'phase':'creating'},f);f.flush();os.fsync(f.fileno())
    directory=os.open(ledger.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(directory)
    finally:os.close(directory)
    value=api.call('POST','/pulls',{'title':TITLE,'head':BRANCH,'base':'main','body':BODY,'prune_source_branch':'false','draft':'false'})
    if type(value.get('number')) is not int:raise ValueError('create_response_unresolved')
    snapshot=observe(reader,number=value['number'],source=BRANCH,head=head,base=base)
    result={'status':'created','url':'https://gitee.com/leegege/sce-product-odoo/pulls/'+str(value['number']),'snapshot':snapshot}
    with tempfile.NamedTemporaryFile(mode='w',dir=ledger.parent,delete=False) as f:
        json.dump(result,f,sort_keys=True);f.flush();os.fsync(f.fileno());temporary=Path(f.name)
    try:
        os.replace(temporary,ledger)
        directory=os.open(ledger.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(directory)
        finally:os.close(directory)
    finally:temporary.unlink(missing_ok=True)
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--expected-head',required=True);p.add_argument('--expected-main',required=True);p.add_argument('--token-file',required=True);p.add_argument('--apply',action='store_true');a=p.parse_args()
    root=Path(__file__).resolve().parents[2]
    def git(*args):return subprocess.check_output(['git',*args],cwd=root,text=True).strip()
    if any(not re.fullmatch('[0-9a-f]{40}',x) for x in (a.expected_head,a.expected_main)):raise ValueError('full_sha_required')
    if git('branch','--show-current')!=BRANCH or git('rev-parse','HEAD')!=a.expected_head or git('status','--porcelain'):raise ValueError('clean_exact_candidate_required')
    if a.apply:subprocess.run(['python3','scripts/ops/local_quick_evidence.py','verify','--expected-head',a.expected_head],cwd=root,check=True,stdout=subprocess.DEVNULL)
    ledger=Path(git('rev-parse','--absolute-git-dir'))/'codex/gitee-formal-pr-create.json'
    print(json.dumps(ensure(PRAPI(a.token_file),ReadAPI(a.token_file),a.expected_head,a.expected_main,ledger,a.apply),sort_keys=True))

if __name__=='__main__':
    try:main()
    except Exception:raise SystemExit('formal PR operation failed; inspect remote identity/create ledger before retry') from None
