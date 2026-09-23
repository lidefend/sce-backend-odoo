"""Trusted-parent CI-only Check Runs projection; never grants integration eligibility.

A create intent is persisted before POST. Unknown create outcomes are reconciled by
an unguessable marker and never blindly POSTed again. Remote readback is mandatory.
"""
from __future__ import annotations
import fcntl
import json
import os
from pathlib import Path
import re
import stat
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

NAME = "sce/ci-only-acceptance"
BASE = "https://gitee.com/api/v5/repos/leegege/sce-product-odoo"
CONCLUSIONS = {"success": "success", "failed": "failure", "timed_out": "timed_out",
               "cancelled": "cancelled", "environment_error": "action_required"}


class ReportError(RuntimeError):
    """Only fixed codes may cross the reporting boundary; never response bodies."""


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ReportError("redirect_rejected")


class API:
    def __init__(self, token_file):
        fd = os.open(token_file, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            info = os.fstat(fd)
            if (not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077
                    or info.st_uid != os.geteuid() or info.st_size > 4096):
                raise ReportError("unsafe_token_file")
            self.token = os.read(fd, 4096).decode().strip()
        finally:
            os.close(fd)
        if not self.token or any(c.isspace() for c in self.token):
            raise ReportError("invalid_token")
        self.opener = urllib.request.build_opener(NoRedirect())

    def request(self, method, suffix, payload=None):
        if not re.fullmatch(r"/(check-runs(?:/[0-9]+)?|commits/[0-9a-f]{40}/check-runs\?page=[0-9]+&per_page=100)", suffix):
            raise ReportError("endpoint_rejected")
        body = None
        if payload is not None:
            flat = {k: v for k, v in payload.items() if k != "output"}
            flat.update({"output["+k+"]": v for k, v in payload["output"].items()})
            body = urllib.parse.urlencode(flat).encode()
        req = urllib.request.Request(BASE+suffix, data=body, method=method,
            headers={"Authorization": "token "+self.token,
                     "Content-Type": "application/x-www-form-urlencoded"})
        try:
            with self.opener.open(req, timeout=10) as response:
                data = response.read(1048577)
            if len(data) > 1048576: raise ReportError("response_too_large")
            return json.loads(data)
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            raise ReportError("api_request_failed") from None


def payload_for(sha, status, receipt, marker):
    if not re.fullmatch(r"[0-9a-f]{40}", sha): raise ReportError("invalid_sha")
    output = {"title": "CI-only acceptance (not a product integration gate)",
              "summary": marker+"; exact_sha="+sha+"; integration_eligible=false"}
    payload = {"name": NAME, "head_sha": sha, "output": output}
    if status in {"pending", "running"}:
        payload["status"] = "queued" if status == "pending" else "in_progress"
        return payload
    if status not in CONCLUSIONS: raise ReportError("invalid_state")
    conclusion = CONCLUSIONS[status]
    if status == "success":
        if (not isinstance(receipt, dict) or receipt.get("sha") != sha
                or receipt.get("checkout_sha") != sha or receipt.get("status") != "success"
                or type(receipt.get("exit_code")) is not int or receipt.get("exit_code") != 0
                or type(receipt.get("tests")) is not int or receipt["tests"] < 1
                or receipt.get("integration_eligible") is not False):
            conclusion = "action_required"
    payload.update(status="completed", conclusion=conclusion)
    # No build logs, paths, exception text, or candidate-generated output is uploaded.
    return payload


def matches(remote, payload):
    return (isinstance(remote, dict) and type(remote.get("id")) is int
            and remote["id"] > 0 and remote.get("head_sha") == payload["head_sha"]
            and remote.get("name") == NAME and remote.get("status") == payload["status"]
            and remote.get("conclusion") == payload.get("conclusion")
            and isinstance(remote.get("output"), dict)
            and remote["output"].get("summary") == payload["output"]["summary"])


class Reporter:
    def __init__(self, queue, api, *, clock=time.time):
        self.queue, self.api, self.clock = queue, api, clock
        self.lock = Path(str(queue.path)+".checks.lock")
        with queue.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS ci_check_reports (sha TEXT PRIMARY KEY, marker TEXT NOT NULL, phase TEXT NOT NULL, remote_id INTEGER, delivered TEXT, retry_at REAL NOT NULL DEFAULT 0, error TEXT)")

    def recover_id(self, sha, marker):
        found = []
        for page in range(1, 11):
            value = self.api.request("GET", f"/commits/{sha}/check-runs?page={page}&per_page=100")
            rows = value.get("check_runs") if isinstance(value, dict) else value
            if not isinstance(rows, list): raise ReportError("invalid_list_response")
            for item in rows:
                if (isinstance(item, dict) and item.get("name") == NAME
                        and item.get("head_sha") == sha
                        and isinstance(item.get("output"), dict)
                        and isinstance(item["output"].get("summary"), str)
                        and item["output"]["summary"].startswith(marker+";")):
                    found.append(item.get("id"))
            if len(rows) < 100: break
        else: raise ReportError("list_limit_reached")
        if len(found) != 1 or type(found[0]) is not int or found[0] < 1:
            raise ReportError("create_outcome_unresolved")
        return found[0]

    def sync_once(self):
        # Receiver and executor remain independent; only reporter processes serialize.
        with self.lock.open("a") as lock:
            try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError: return False
            with self.queue.connect() as db:
                jobs = db.execute("SELECT sha,status,receipt FROM ci_acceptance_jobs ORDER BY rowid").fetchall()
            for sha, status, raw in jobs:
                with self.queue.connect() as db:
                    db.execute("INSERT OR IGNORE INTO ci_check_reports(sha,marker,phase) VALUES (?,?,'new')",
                               (sha, "sce-ci-"+uuid.uuid4().hex))
                    row = db.execute("SELECT marker,phase,remote_id,delivered,retry_at FROM ci_check_reports WHERE sha=?", (sha,)).fetchone()
                marker, phase, remote_id, delivered, retry_at = row
                payload = payload_for(sha, status, json.loads(raw) if raw else None, marker)
                desired = json.dumps(payload, sort_keys=True)
                if desired == delivered or retry_at > self.clock(): continue
                try:
                    if phase == "new":
                        # Crash or network loss after this commit must NOT create another run.
                        with self.queue.connect() as db:
                            db.execute("UPDATE ci_check_reports SET phase='creating' WHERE sha=?", (sha,))
                        created = self.api.request("POST", "/check-runs", payload)
                        if (not isinstance(created, dict) or type(created.get("id")) is not int
                                or created["id"] < 1):
                            raise ReportError("invalid_create_response")
                        remote_id = created["id"]
                    elif remote_id is None:
                        remote_id = self.recover_id(sha, marker)
                    remote = self.api.request("GET", f"/check-runs/{remote_id}")
                    if (not isinstance(remote, dict) or remote.get("head_sha") != sha
                            or remote.get("name") != NAME or not isinstance(remote.get("output"), dict)
                            or not isinstance(remote["output"].get("summary"), str)
                            or not remote["output"]["summary"].startswith(marker+";")):
                        raise ReportError("remote_identity_mismatch")
                    with self.queue.connect() as db:
                        db.execute("UPDATE ci_check_reports SET phase='bound',remote_id=? WHERE sha=?", (remote_id, sha))
                    if not matches(remote, payload):
                        update = {k: v for k, v in payload.items() if k != "head_sha"}
                        self.api.request("PATCH", f"/check-runs/{remote_id}", update)
                        remote = self.api.request("GET", f"/check-runs/{remote_id}")
                    if not matches(remote, payload): raise ReportError("readback_mismatch")
                    with self.queue.connect() as db:
                        db.execute("UPDATE ci_check_reports SET delivered=?,retry_at=0,error=NULL WHERE sha=?", (desired, sha))
                except ReportError as exc:
                    with self.queue.connect() as db:
                        db.execute("UPDATE ci_check_reports SET retry_at=?,error=? WHERE sha=?", (self.clock()+30, str(exc), sha))
                return True
            return False
