"""Explicit ordinary-PR worker using the existing signed receiver and SQLite DB."""
from __future__ import annotations
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import tempfile
import time

from scripts.ci.gitee_ci_checks import API
from scripts.ci.gitee_pr_identity import ReadAPI, observe, observe_merged, valid_branch
from scripts.ci.gitee_gate_plan import PREPARATION_FAILURE_REASONS, SHA, changed_paths, digest, plan
from scripts.ci.gitee_formal_executor import IDENTITY_KEYS, FormalExecutor
from scripts.ci.gitee_formal_queue import FormalQueue, FormalReporter, execute_once


class PreparationFailed(Exception):
    """A bounded, trusted reason why no runnable gate plan could be produced."""

    def __init__(self,reason):
        if reason not in PREPARATION_FAILURE_REASONS: raise ValueError('unknown_preparation_reason')
        super().__init__(reason); self.reason=reason


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

    def identity(self,event):
        """Resolve the authoritative PR/base identity before any checkout."""
        try:
            pr=self.reader.get('/pulls/'+str(event['pr_number']))
            source=(pr.get('head') or {}).get('ref');base=(pr.get('base') or {}).get('sha')
        except Exception as exc:
            raise PreparationFailed('pull_request_unavailable') from exc
        if not valid_branch(source) or not isinstance(base,str) or not SHA.fullmatch(base):
            raise PreparationFailed('invalid_source_branch')
        candidate=self.candidate_requested(pr)
        try:
            snapshot=observe(self.reader,number=event['pr_number'],source=source,head=event['sha'],base=base)
        except Exception as exc:
            raise PreparationFailed('platform_identity_unavailable') from exc
        return source,base,candidate,snapshot

    @staticmethod
    def seal(p,snapshot):
        p['platform_snapshot']=snapshot;p['pr_identity_verified']=True;p['remote_refs_verified']=True
        p.pop('plan_sha256');p['plan_sha256']=digest(p)
        return p

    def prepare(self,event):
        source,base,candidate,snapshot=self.identity(event)
        self.executor.artifacts.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='formal-plan-') as temp:
            workspace=Path(temp)
            with tempfile.NamedTemporaryFile(prefix='prepare-',suffix='.log',dir=self.executor.artifacts,delete=False) as log:
                try:
                    head=self.executor.checkout(workspace,event['sha'],log,lambda:False,time.monotonic()+300)
                except Exception as exc:
                    raise PreparationFailed('checkout_failed') from exc
                if head!=event['sha']:raise PreparationFailed('checkout_mismatch')
            try:
                paths=changed_paths(workspace/'repo',base,event['sha'])
            except subprocess.CalledProcessError as exc:
                # The accepted baseline must be an ancestor of the candidate. This
                # gate is reported, never bypassed.
                raise PreparationFailed('baseline_not_ancestor') from exc
            except Exception as exc:
                raise PreparationFailed('change_set_unavailable') from exc
            try:
                p=plan(head=event['sha'],base=base,source_branch=source,pr_number=event['pr_number'],paths=paths,candidate=candidate)
            except Exception as exc:
                raise PreparationFailed('plan_rejected') from exc
        return self.seal(p,snapshot)

    def failure_plan(self,event,reason):
        """Build a reportable plan for an unusable candidate; identity is re-read."""
        source,base,candidate,snapshot=self.identity(event)
        p=plan(head=event['sha'],base=base,source_branch=source,pr_number=event['pr_number'],
               paths=(),candidate=candidate,preparation_failure=reason)
        return self.seal(p,snapshot)

    @staticmethod
    def failure_receipt(p):
        return {**{k:p[k] for k in IDENTITY_KEYS},'plan_sha256':p['plan_sha256'],
                'status':'environment_error','checks':[],'integration_eligible':False}

    def report_preparation_failure(self,delivery,event,reason):
        """Publish four attributed red checks, or record why none could be bound."""
        reported=False;detail=''
        try:
            p=self.failure_plan(event,reason)
            key,_=self.queue.enqueue(p,delivery)
            self.queue.fail(key,self.failure_receipt(p))
            reported=True
        except Exception as exc:
            # Only the exception class is logged: it is code-controlled and a
            # candidate must never be able to write text into the check report.
            detail=' error='+type(exc).__name__
        self.inbox.finish(delivery,'prepared' if reported else 'environment_error')
        print('[gitee_formal] preparation_failed reason='+reason+
              ' reported='+('true' if reported else 'false')+detail,flush=True)

    def prepare_delivery(self,delivery,event):
        try:
            p=self.prepare(event)
        except Exception as exc:
            reason=exc.reason if isinstance(exc,PreparationFailed) else 'preparation_incomplete'
        else:
            try:
                self.queue.enqueue(p,delivery);self.inbox.finish(delivery,'prepared');return
            except Exception:
                reason='preparation_incomplete'
        self.report_preparation_failure(delivery,event,reason)

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
            self.prepare_delivery(delivery,event)
        if incoming:self.report()
        worked=execute_once(self.queue,self.executor,self.refresh)
        self.report()
        return bool(incoming) or worked
