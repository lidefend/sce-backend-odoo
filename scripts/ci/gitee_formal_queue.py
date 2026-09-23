"""Durable formal jobs and four-check projection; trusted-controller input only.

Not enabled by the legacy/ci-only receiver. No module here grants merge authority.
"""
from __future__ import annotations
import fcntl
import json
from pathlib import Path
import sqlite3
import time
import uuid

from scripts.ci.gitee_gate_plan import CHECKS, digest
from scripts.ci.gitee_formal_executor import IDENTITY_KEYS, verify_snapshot
from scripts.ci.gitee_ci_checks import ReportError

TERMINAL = {'success','failed','timed_out','cancelled','environment_error'}


def job_key(plan):
    original = dict(plan); expected = original.pop('plan_sha256', None)
    if digest(original) != expected: raise ValueError('plan_digest_mismatch')
    snapshot = plan.get('platform_snapshot', {})
    verify_snapshot(plan, snapshot)
    if type(snapshot.get('pr_id')) is not int or snapshot['pr_id'] < 1:
        raise ValueError('verified_pr_id_required')
    if tuple(x['name'] for x in plan['checks']) != CHECKS:
        raise ValueError('required_checks_mismatch')
    return digest({**{k:plan[k] for k in IDENTITY_KEYS},
                   'source_hashes':plan['source_hashes'], 'checks':plan['checks'],
                   'candidate_requested':plan['candidate_requested'], 'pr_id':snapshot['pr_id']})


class FormalQueue:
    def __init__(self, path, *, recover_running=False):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS formal_jobs (id TEXT PRIMARY KEY, plan TEXT NOT NULL, status TEXT NOT NULL, cancel INTEGER NOT NULL DEFAULT 0, receipt TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS formal_deliveries (delivery TEXT PRIMARY KEY, job TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS formal_reports (job TEXT NOT NULL, name TEXT NOT NULL, marker TEXT NOT NULL, phase TEXT NOT NULL, remote_id INTEGER, delivered TEXT, retry_at REAL NOT NULL DEFAULT 0, error TEXT, PRIMARY KEY(job,name))')
            db.execute('CREATE TABLE IF NOT EXISTS formal_report_cursor (id INTEGER PRIMARY KEY, position INTEGER NOT NULL)')
            db.execute('INSERT OR IGNORE INTO formal_report_cursor VALUES (1,0)')
            if recover_running:
                db.execute("UPDATE formal_jobs SET status='environment_error',receipt=NULL WHERE status='running'")

    def connect(self): return sqlite3.connect(self.path,timeout=30)

    def enqueue(self, plan, delivery):
        key=job_key(plan)
        if not isinstance(delivery,str) or not delivery.isdigit() or len(delivery)>32:
            raise ValueError('invalid_delivery')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            old=db.execute('SELECT job FROM formal_deliveries WHERE delivery=?',(delivery,)).fetchone()
            if old and old[0]!=key: raise ValueError('delivery_replay')
            db.execute('INSERT OR IGNORE INTO formal_deliveries VALUES (?,?)',(delivery,key))
            inserted=db.execute("INSERT OR IGNORE INTO formal_jobs(id,plan,status) VALUES (?,?,'pending')",
                                (key,json.dumps(plan,sort_keys=True))).rowcount==1
        return key,inserted

    def claim(self):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute("SELECT 1 FROM formal_jobs WHERE status='running'").fetchone(): return None
            row=db.execute("SELECT id,plan FROM formal_jobs WHERE status='pending' ORDER BY rowid LIMIT 1").fetchone()
            if row is None: return None
            db.execute("UPDATE formal_jobs SET status='running' WHERE id=?",(row[0],))
            return row[0],json.loads(row[1])

    def cancel(self,key):
        with self.connect() as db:
            db.execute("UPDATE formal_jobs SET cancel=1 WHERE id=? AND status IN ('pending','running')",(key,))

    def cancelled(self,key):
        with self.connect() as db:
            row=db.execute('SELECT cancel FROM formal_jobs WHERE id=?',(key,)).fetchone()
            return bool(row and row[0])

    def finish(self,key,receipt):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT plan,status,cancel FROM formal_jobs WHERE id=?',(key,)).fetchone()
            if not row or row[1]!='running': raise ValueError('job_not_running')
            p=json.loads(row[0])
            if (not isinstance(receipt,dict) or receipt.get('status') not in TERMINAL or
                    any(receipt.get(k)!=p[k] for k in IDENTITY_KEYS) or
                    receipt.get('plan_sha256')!=p['plan_sha256'] or
                    receipt.get('integration_eligible') is not False): raise ValueError('receipt_identity')
            receipt=dict(receipt)
            if row[2]: receipt['status']='cancelled'
            if receipt['status']=='success': validate_success(p,receipt)
            db.execute('UPDATE formal_jobs SET status=?,receipt=? WHERE id=?',
                       (receipt['status'],json.dumps(receipt,sort_keys=True),key))


def validate_success(plan,receipt):
    rows=receipt.get('checks')
    if not isinstance(rows,list) or len(rows)!=len(CHECKS): raise ValueError('incomplete_checks')
    for required,row in zip(plan['checks'],rows):
        if (not isinstance(row,dict) or row.get('name')!=required['name'] or
                row.get('mode')!=required['mode'] or row.get('status')!='success' or
                type(row.get('tests')) is not int or row['tests']<0): raise ValueError('invalid_check_result')
        needs_tests = (row['name']=='professional_quality_gate' or
                       row['name']=='public_guard' and row['mode']=='required' or
                       row['name']=='merge_policy_gate' and row['mode']=='fast' or
                       row['name']=='frontend_release_gate' and row['mode']!='skip')
        if needs_tests and row['tests']==0: raise ValueError('zero_tests')


def payload(plan,status,receipt,name,marker,current):
    summary=marker+'; base='+plan['base_sha']+'; pr='+str(plan['pr_number'])+'; integration_eligible=false'
    value={'name':name,'head_sha':plan['head_sha'],
           'pull_request_id':plan['platform_snapshot']['pr_id'],
           'output':{'title':'Formal gate: '+name,'summary':summary}}
    fresh=True
    try: verify_snapshot(plan,current)
    except ValueError: fresh=False
    if not fresh:
        value.update(status='completed',conclusion='action_required');return value
    if status in {'pending','running'}:
        value['status']='queued' if status=='pending' else 'in_progress';return value
    conclusion={'failed':'failure','timed_out':'timed_out','cancelled':'cancelled',
                'environment_error':'action_required'}.get(status,'action_required')
    if status=='success':
        try: validate_success(plan,receipt);conclusion='success'
        except (ValueError,TypeError,AttributeError): conclusion='action_required'
    value.update(status='completed',conclusion=conclusion)
    return value


class FormalReporter:
    def __init__(self,queue,api,refresh_identity,*,clock=time.time):
        self.queue,self.api,self.refresh,self.clock=queue,api,refresh_identity,clock

    def sync_once(self):
        with Path(str(self.queue.path)+'.formal-report.lock').open('a') as lock:
            try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError: return False
            with self.queue.connect() as db:
                position=db.execute('SELECT position FROM formal_report_cursor WHERE id=1').fetchone()[0]
                jobs=db.execute('SELECT rowid,id,plan,status,receipt FROM formal_jobs WHERE rowid>? ORDER BY rowid LIMIT 128',(position,)).fetchall()
                if not jobs:
                    db.execute('UPDATE formal_report_cursor SET position=0 WHERE id=1')
                    jobs=db.execute('SELECT rowid,id,plan,status,receipt FROM formal_jobs ORDER BY rowid LIMIT 128').fetchall()
            for rowid,key,raw,state,result in jobs:
                plan=json.loads(raw)
                current=None
                for name in CHECKS:
                    with self.queue.connect() as db:
                        db.execute("INSERT OR IGNORE INTO formal_reports(job,name,marker,phase) VALUES (?,?,?,'new')",
                                   (key,name,'sce-formal-'+uuid.uuid4().hex))
                        marker,phase,remote_id,delivered,retry_at=db.execute('SELECT marker,phase,remote_id,delivered,retry_at FROM formal_reports WHERE job=? AND name=?',(key,name)).fetchone()
                    if retry_at>self.clock():continue
                    if current is None:
                        try: current=self.refresh(plan)
                        except Exception: current={}
                    desired=payload(plan,state,json.loads(result) if result else None,name,marker,current)
                    encoded=json.dumps(desired,sort_keys=True)
                    if encoded==delivered:
                        with self.queue.connect() as db:
                            db.execute('UPDATE formal_reports SET retry_at=? WHERE job=? AND name=?',(self.clock()+30,key,name))
                        continue
                    try:
                        if phase=='new':
                            with self.queue.connect() as db:
                                db.execute("UPDATE formal_reports SET phase='creating' WHERE job=? AND name=?",(key,name))
                            remote=self.api.request('POST','/check-runs',desired)
                            remote_id=remote.get('id') if isinstance(remote,dict) else None
                            if type(remote_id) is not int or remote_id<1: raise ReportError('invalid_create_response')
                        elif remote_id is None:
                            found=[]
                            for page in range(1,11):
                                values=self.api.request('GET',f"/commits/{plan['head_sha']}/check-runs?page={page}&per_page=100")
                                items=values.get('check_runs') if isinstance(values,dict) else values
                                if not isinstance(items,list): raise ReportError('invalid_list_response')
                                found.extend(x['id'] for x in items if self.bound(x,desired,marker))
                                if len(items)<100:break
                            else:raise ReportError('list_limit_reached')
                            if len(found)!=1:raise ReportError('create_outcome_unresolved')
                            remote_id=found[0]
                        remote=self.api.request('GET',f'/check-runs/{remote_id}')
                        if not self.bound(remote,desired,marker):raise ReportError('remote_identity_mismatch')
                        with self.queue.connect() as db:
                            db.execute("UPDATE formal_reports SET phase='bound',remote_id=? WHERE job=? AND name=?",(remote_id,key,name))
                        if not self.matches(remote,desired,remote_id):
                            self.api.request('PATCH',f'/check-runs/{remote_id}',{k:v for k,v in desired.items() if k!='head_sha'})
                            remote=self.api.request('GET',f'/check-runs/{remote_id}')
                        if not self.matches(remote,desired,remote_id):raise ReportError('readback_mismatch')
                        with self.queue.connect() as db:
                            db.execute('UPDATE formal_reports SET delivered=?,error=NULL,retry_at=? WHERE job=? AND name=?',(encoded,self.clock()+30,key,name))
                    except ReportError as exc:
                        with self.queue.connect() as db:
                            db.execute('UPDATE formal_reports SET error=?,retry_at=? WHERE job=? AND name=?',(str(exc),self.clock()+30,key,name))
                    return True
                with self.queue.connect() as db:
                    db.execute('UPDATE formal_report_cursor SET position=? WHERE id=1',(rowid,))
            return False

    @staticmethod
    def bound(remote,desired,marker):
        return (isinstance(remote,dict) and type(remote.get('id')) is int and remote['id']>0 and
                remote.get('name')==desired['name'] and remote.get('head_sha')==desired['head_sha'] and
                isinstance(remote.get('output'),dict) and
                remote['output'].get('summary')==desired['output']['summary'])

    @staticmethod
    def matches(remote,desired,expected_id):
        return (FormalReporter.bound(remote,desired,'') and remote['id']==expected_id and remote.get('status')==desired['status'] and
                remote.get('conclusion')==desired.get('conclusion') and
                isinstance(remote.get('output'),dict) and
                all(remote['output'].get(k)==v for k,v in desired['output'].items()) and
                type(remote.get('pull_request_id')) is int and
                remote['pull_request_id']==desired['pull_request_id'])


def execute_once(queue, executor, refresh_identity):
    claimed=queue.claim()
    if claimed is None:return False
    key,plan=claimed
    try:
        result=executor.execute_plan(plan,lambda:refresh_identity(plan),lambda:queue.cancelled(key))
    except Exception:
        # Trusted executor failures are terminal, never an implicit retry/pass.
        result={**{k:plan[k] for k in IDENTITY_KEYS},'plan_sha256':plan['plan_sha256'],
                'status':'environment_error','checks':[],'integration_eligible':False}
    try:
        queue.finish(key,result)
    except ValueError:
        failure={**{k:plan[k] for k in IDENTITY_KEYS},'plan_sha256':plan['plan_sha256'],
                 'status':'environment_error','checks':[],'integration_eligible':False}
        try: queue.finish(key,failure)
        except ValueError: pass  # Another recovery already made the job terminal.
    return True
