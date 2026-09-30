"""Explicit CI-only worker mode. No platform status credentials enter the sandbox."""
from __future__ import annotations
import json
import os
from pathlib import Path
import re
import signal
import stat
import sqlite3
import subprocess
import tempfile
import time

REPOSITORY = 'leegege/sce-product-odoo'
BRANCH = 'fix/gitee-temporary-integration-v1'
REMOTE = 'git@gitee.com:leegege/sce-product-odoo.git'
SHA = re.compile(r'[0-9a-f]{40}')
TERMINAL = {'success', 'failed', 'timed_out', 'cancelled', 'environment_error'}


def validate(job):
    if (job.get('repository') != REPOSITORY or job.get('ref') != 'refs/heads/' + BRANCH
            or job.get('hook_name') != 'push_hooks' or not SHA.fullmatch(job.get('sha', ''))):
        raise ValueError('CI-only scope rejected')


class AcceptanceQueue:
    def __init__(self, path, *, recover_running=False):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS ci_acceptance_jobs (sha TEXT PRIMARY KEY, job TEXT NOT NULL, status TEXT NOT NULL, cancel INTEGER NOT NULL DEFAULT 0, receipt TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS ci_acceptance_deliveries (timestamp TEXT PRIMARY KEY, sha TEXT NOT NULL)')
            # Never relabel an interrupted attempt as a fresh success.
            if recover_running:
                db.execute("UPDATE ci_acceptance_jobs SET status='environment_error', receipt=? WHERE status='running'", (json.dumps({'reason': 'worker_restarted'}),))

    def connect(self):
        return sqlite3.connect(self.path, timeout=30)

    def enqueue(self, job, signature_timestamp):
        validate(job)
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            previous = db.execute('SELECT sha FROM ci_acceptance_deliveries WHERE timestamp=?', (signature_timestamp,)).fetchone()
            if previous and previous[0] != job['sha']:
                raise ValueError('replayed signature for different SHA')
            db.execute('INSERT OR IGNORE INTO ci_acceptance_deliveries(timestamp,sha) VALUES (?,?)', (signature_timestamp, job['sha']))
            return db.execute("INSERT OR IGNORE INTO ci_acceptance_jobs(sha,job,status) VALUES (?,?,'pending')", (job['sha'], json.dumps(job))).rowcount == 1

    def claim(self):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute("SELECT sha,job FROM ci_acceptance_jobs WHERE status='pending' ORDER BY rowid LIMIT 1").fetchone()
            if not row: return None
            db.execute("UPDATE ci_acceptance_jobs SET status='running' WHERE sha=?", (row[0],))
            return json.loads(row[1])

    def cancel(self, sha):
        if not SHA.fullmatch(sha): raise ValueError('full SHA required')
        with self.connect() as db:
            db.execute("UPDATE ci_acceptance_jobs SET cancel=1 WHERE sha=? AND status IN ('pending','running')", (sha,))

    def cancelled(self, sha):
        with self.connect() as db:
            row = db.execute('SELECT cancel FROM ci_acceptance_jobs WHERE sha=?', (sha,)).fetchone()
            return bool(row and row[0])

    def finish(self, sha, receipt):
        if receipt['sha'] != sha or receipt['status'] not in TERMINAL: raise ValueError('receipt identity')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT status,cancel FROM ci_acceptance_jobs WHERE sha=?', (sha,)).fetchone()
            if not row or row[0] != 'running': return
            if row[1] and receipt['status'] == 'success':
                receipt['status'] = 'cancelled'
                if receipt.get('log'):
                    (Path(receipt['log']).parent/'receipt.json').write_text(json.dumps(receipt)+'\n')
            db.execute("UPDATE ci_acceptance_jobs SET status=?,receipt=? WHERE sha=? AND status='running'", (receipt['status'], json.dumps(receipt), sha))

    def result(self, sha):
        with self.connect() as db:
            row = db.execute('SELECT status,receipt FROM ci_acceptance_jobs WHERE sha=?', (sha,)).fetchone()
            return {'sha': sha, 'status': row[0], 'receipt': json.loads(row[1]) if row[1] else None} if row else None


class Interrupted(Exception):
    def __init__(self, status): self.status = status


class Executor:
    def __init__(self, artifacts, *, timeout=120):
        self.artifacts = Path(artifacts)
        self.timeout = timeout
        self.last_exit_code = None

    def command(self, args, cwd, log, cancelled, deadline, env):
        if cancelled(): raise Interrupted('cancelled')
        proc = subprocess.Popen(args, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            while proc.poll() is None:
                if cancelled(): raise Interrupted('cancelled')
                if time.monotonic() >= deadline: raise Interrupted('timed_out')
                time.sleep(.02)
            if cancelled(): raise Interrupted('cancelled')
            return proc.returncode
        finally:
            # Includes background descendants on normal completion. PID namespace teardown
            # additionally kills descendants that escape the process group with setsid().
            try: os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            self.last_exit_code = proc.wait()

    def checkout(self, workspace, sha, log, cancelled, deadline):
        env = {'PATH': '/usr/bin:/bin', 'HOME': str(workspace), 'GIT_CONFIG_NOSYSTEM': '1',
               'GIT_TERMINAL_PROMPT': '0'}
        # Transport belongs to the trusted parent, never the build environment.
        if os.environ.get('GIT_SSH_COMMAND'): env['GIT_SSH_COMMAND'] = os.environ['GIT_SSH_COMMAND']
        for args in [['git','clone','--no-checkout','--no-tags',REMOTE,str(workspace/'repo')],
                     ['git','-C',str(workspace/'repo'),'fetch','--no-tags','origin',sha],
                     ['git','-C',str(workspace/'repo'),'checkout','--detach',sha]]:
            if self.command(args, workspace, log, cancelled, deadline, env): raise RuntimeError('checkout failed')
        # Read exact HEAD without executing candidate hooks or code.
        head = (workspace/'repo'/'.git'/'HEAD').read_text().strip()
        return head

    def sandbox(self, workspace):
        harness = Path(__file__).with_name('gitee_ci_acceptance_check.py').resolve()
        return ['/usr/bin/bwrap','--unshare-all','--die-with-parent','--new-session',
                '--ro-bind','/usr','/usr','--symlink','usr/bin','/bin',
                '--symlink','usr/lib','/lib','--symlink','usr/lib64','/lib64',
                '--proc','/proc','--dev','/dev','--tmpfs','/tmp',
                '--bind',str(workspace/'repo'),'/work',
                '--ro-bind',str(harness),'/check.py',
                '--chdir','/work','/usr/bin/python3','/check.py']

    def execute(self, job, cancelled=lambda: False):
        validate(job)
        self.artifacts.mkdir(parents=True, exist_ok=True)
        attempt = Path(tempfile.mkdtemp(prefix=job['sha']+'-', dir=self.artifacts))
        receipt = {'sha': job['sha'], 'repository': REPOSITORY, 'branch': BRANCH,
                   'checkout_sha': None, 'exit_code': None, 'tests': None,
                   'status': 'environment_error', 'log': str(attempt/'build.log'),
                   'attempt': attempt.name, 'integration_eligible': False}
        deadline = time.monotonic() + self.timeout
        with (attempt/'build.log').open('wb') as log, tempfile.TemporaryDirectory(prefix='ci-only-') as temp:
            workspace = Path(temp)
            try:
                receipt['checkout_sha'] = self.checkout(workspace, job['sha'], log, cancelled, deadline)
                if receipt['checkout_sha'] != job['sha']: raise RuntimeError('checkout SHA mismatch')
                report_path = workspace/'repo'/'.ci-count.json'
                if report_path.exists() or report_path.is_symlink(): report_path.unlink()
                env = {'PATH':'/usr/bin:/bin','HOME':'/tmp','ENV':'test','CI':'1',
                       'GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':'/dev/null'}
                receipt['exit_code'] = self.command(self.sandbox(workspace), workspace, log, cancelled, deadline, env)
                report_path = workspace/'repo'/'.ci-count.json'
                info = report_path.lstat()
                if not stat.S_ISREG(info.st_mode) or info.st_size > 65536:
                    raise ValueError('report must be a bounded regular file')
                report = json.loads(report_path.read_text())
                count = report['tests']
                if type(count) is not int or count < 0: raise ValueError('invalid count')
                receipt['tests'] = count
                receipt['status'] = 'success' if receipt['exit_code'] == 0 and count > 0 and report['ok'] is True else 'failed'
            except Interrupted as exc:
                receipt['status'] = exc.status
                receipt['exit_code'] = self.last_exit_code
            except (OSError, ValueError, KeyError, RuntimeError) as exc:
                receipt['status'] = 'environment_error'
                receipt['reason'] = type(exc).__name__
                receipt['exit_code'] = self.last_exit_code
        if cancelled() and receipt['status'] == 'success': receipt['status'] = 'cancelled'
        # Parent-owned receipt is outside the sandbox and published only after cleanup.
        (attempt/'receipt.json').write_text(json.dumps(receipt, sort_keys=True)+'\n')
        return receipt
