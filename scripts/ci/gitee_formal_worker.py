"""Explicit ordinary-PR worker using the existing signed receiver and SQLite DB."""
from __future__ import annotations
import json
from pathlib import Path
import re
import sqlite3
import tempfile
import time

from scripts.ci.gitee_ci_checks import API
from scripts.ci.gitee_pr_identity import ReadAPI, observe, observe_merged, valid_branch
from scripts.ci.gitee_gate_plan import plan, changed_paths, digest
from scripts.ci.gitee_formal_executor import FormalExecutor
from scripts.ci.gitee_formal_queue import FormalQueue, FormalReporter, execute_once


class Inbox:
    def __init__(self,path,*,recover_running=False):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS formal_inbox (delivery TEXT PRIMARY KEY, event TEXT NOT NULL, status TEXT NOT NULL)')
            if recover_running:db.execute("UPDATE formal_inbox SET status='environment_error' WHERE status='preparing'")

    def connect(self):return sqlite3.connect(self.path,timeout=30)

    def enqueue(self,event,timestamp):
        if (event.get('hook_name')!='merge_request_hooks' or
                event.get('repository')!='leegege/sce-product-odoo' or
                type(event.get('pr_number')) is not int or event['pr_number']<1 or
                not isinstance(event.get('sha'),str) or not re.fullmatch('[0-9a-f]{40}',event['sha']) or
                not isinstance(timestamp,str) or not timestamp.isdigit() or len(timestamp)>32):
            raise ValueError('formal_event_rejected')
        # The receiver authenticates sender/signature. Only these non-secret event
        # fields survive into the inbox; source/base authority is read via API.
        normalized={k:event[k] for k in ('hook_name','repository','pr_number','sha')}
        raw=json.dumps(normalized,sort_keys=True)
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            old=db.execute('SELECT event FROM formal_inbox WHERE delivery=?',(timestamp,)).fetchone()
            if old:
                if old[0]!=raw:raise ValueError('delivery_replay')
                return False
            db.execute("INSERT INTO formal_inbox VALUES (?,?,'pending')",(timestamp,raw))
        return True

    def claim(self):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute("SELECT delivery,event FROM formal_inbox WHERE status='pending' ORDER BY rowid LIMIT 1").fetchone()
            if row:
                db.execute("UPDATE formal_inbox SET status='preparing' WHERE delivery=?",(row[0],))
                return row[0],json.loads(row[1])
        return None

    def finish(self,delivery,status):
        if status not in {'prepared','environment_error'}:raise ValueError('invalid_inbox_state')
        with self.connect() as db:
            db.execute("UPDATE formal_inbox SET status=? WHERE delivery=? AND status='preparing'",(status,delivery))


class Worker:
    def __init__(self,path,log_dir,token_file):
        self.inbox=Inbox(path,recover_running=True)
        self.queue=FormalQueue(path,recover_running=True)
        self.reader=ReadAPI(token_file)
        self.executor=FormalExecutor(Path(log_dir)/'formal')
        self.reporter=FormalReporter(self.queue,API(token_file),self.refresh_report)

    def refresh_report(self,p):
        pr=self.reader.get('/pulls/'+str(p['pr_number']))
        if pr.get('state') == 'merged':
            return observe_merged(self.reader,p)
        return self.refresh(p)

    def refresh(self,p):
        pr=self.reader.get('/pulls/'+str(p['pr_number']))
        if self.candidate_requested(pr)!=p['candidate_requested']:
            raise ValueError('requested_lane_changed')
        return observe(self.reader,number=p['pr_number'],source=p['source_branch'],
                       head=p['head_sha'],base=p['base_sha'])

    @staticmethod
    def candidate_requested(pr):
        labels=pr.get('labels') or []
        return any((x.get('name') if isinstance(x,dict) else x)=='ci:candidate' for x in labels)

    def prepare(self,event):
        pr=self.reader.get('/pulls/'+str(event['pr_number']))
        source=(pr.get('head') or {}).get('ref');base=(pr.get('base') or {}).get('sha')
        if not valid_branch(source):raise ValueError('invalid_source')
        candidate=self.candidate_requested(pr)
        snapshot=observe(self.reader,number=event['pr_number'],source=source,head=event['sha'],base=base)
        self.executor.artifacts.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='formal-plan-') as temp:
            workspace=Path(temp)
            with tempfile.NamedTemporaryFile(prefix='prepare-',suffix='.log',dir=self.executor.artifacts,delete=False) as log:
                if self.executor.checkout(workspace,event['sha'],log,lambda:False,time.monotonic()+300)!=event['sha']:
                    raise ValueError('checkout_mismatch')
            paths=changed_paths(workspace/'repo',base,event['sha'])
            p=plan(head=event['sha'],base=base,source_branch=source,pr_number=event['pr_number'],paths=paths,candidate=candidate)
        p['platform_snapshot']=snapshot;p['pr_identity_verified']=True;p['remote_refs_verified']=True
        p.pop('plan_sha256');p['plan_sha256']=digest(p)
        return p

    def report(self):
        for _ in range(4):
            try:self.reporter.sync_once()
            except Exception:
                print('[gitee_formal] report_pending_retry',flush=True)
                break

    def tick(self):
        self.report()
        incoming=self.inbox.claim()
        if incoming:
            delivery,event=incoming
            try:
                p=self.prepare(event);self.queue.enqueue(p,delivery)
                self.inbox.finish(delivery,'prepared')
            except Exception:
                self.inbox.finish(delivery,'environment_error')
                print('[gitee_formal] preparation_failed',flush=True)
        if incoming:self.report()
        worked=execute_once(self.queue,self.executor,self.refresh)
        self.report()
        return bool(incoming) or worked
