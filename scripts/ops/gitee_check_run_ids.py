#!/usr/bin/env python3
"""Resolve the four required Gitee check-run ids for one commit.

The platform's commit check-run *list* endpoint answers ``total_count=0`` for
every commit in this repository, so ``gitee_pr_bot.py merge`` cannot read the
required checks back from the platform alone and refuses with
``required_checks_missing``.  The trusted CI worker that created those runs keeps
the authoritative record in its own ledger, so this entry reads that record over
the operator's existing read-only access, keeps the newest run id per required
check, and then re-verifies every id against the platform *by id*.

It is a discovery helper, never a merge authority: it does not write, does not
merge and cannot relax the merge entry's own gates.  Output is one receipt plus a
ready ``GITEE_PR_CHECK_RUNS`` value.

Boundaries:

* the ledger is read by a fixed remote program over ssh: the target commit is
  passed as an argument instead of being interpolated into a shell command, the
  database is opened read-only, and nothing is written on the CI host;
* a run is usable only when the ledger's own delivered payload binds it to both
  the exact expected commit *and* the expected target baseline; a run created
  against another base is refused as stale rather than silently reused;
* the newest id per name wins, mirroring the merge entry's strictly-increasing
  order proof, and every id is confirmed against the platform by id afterwards;
* a missing check, a queued re-run or a non-success conclusion is reported as not
  yet mergeable instead of being presented as passing.
"""
from __future__ import annotations
import argparse, json, os, re, stat, subprocess, urllib.error, urllib.request
from pathlib import Path

API = "https://gitee.com/api/v5"
OWNER = "leegege"
REPO = "sce-product-odoo"
REQUIRED_CHECKS = ("public_guard", "merge_policy_gate", "professional_quality_gate", "frontend_release_gate")
DEFAULT_HOST = "1.95.2.123"
DEFAULT_USER = "root"
DEFAULT_DB = "/var/lib/gitee-ci/jobs.sqlite3"
SHA = re.compile(r"[0-9a-f]{40}")
SAFE_PATH = re.compile(r"/[A-Za-z0-9._/-]+")
BASE_IN_SUMMARY = re.compile(r"base=([0-9a-f]{40})")
PR_IN_SUMMARY = re.compile(r"pr=([0-9]+)")
SSH_TIMEOUT = 60


class Denied(RuntimeError):
    """Refusals; never carries ledger contents or credentials."""


REMOTE_SCRIPT = r'''
import json, re, sqlite3, sys
sha, db = sys.argv[1], sys.argv[2]
if not re.fullmatch(r"[0-9a-f]{40}", sha) or not re.fullmatch(r"/[A-Za-z0-9._/-]+", db):
    print(json.dumps({"error": "invalid_argument"})); raise SystemExit(0)
con = sqlite3.connect("file:" + db + "?mode=ro", uri=True)
rows = [{"name": name, "remote_id": remote_id, "delivered": delivered}
        for name, remote_id, delivered in con.execute(
            "select name, remote_id, delivered from formal_reports where instr(delivered, ?) > 0", (sha,))]
print(json.dumps({"rows": rows}))
'''


def validate_sha(value, label):
    if not SHA.fullmatch(str(value or "")):
        raise Denied(f"full exact {label} required")
    return str(value)


def read_ledger(*, head, host=DEFAULT_HOST, user=DEFAULT_USER, db=DEFAULT_DB):
    """Read the trusted worker's own record for one commit, read-only.

    The command is fixed and the commit travels as an argument, so no caller value
    reaches a shell.  A transport or parse failure is a stop, never an empty set:
    "could not read" must not look like "no queued re-run".
    """
    if not SAFE_PATH.fullmatch(db):
        raise Denied("unsafe ledger path")
    argv = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", f"{user}@{host}", "python3", "-", head, db]
    try:
        result = subprocess.run(argv, input=REMOTE_SCRIPT, text=True, capture_output=True, timeout=SSH_TIMEOUT)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Denied("ci_ledger_unreachable") from exc
    if result.returncode:
        raise Denied("ci_ledger_unreadable")
    try:
        payload = json.loads(result.stdout)
    except ValueError as exc:
        raise Denied("ci_ledger_unreadable") from exc
    if not isinstance(payload, dict) or payload.get("error") or not isinstance(payload.get("rows"), list):
        raise Denied("ci_ledger_unreadable")
    return payload["rows"]


def select_latest(rows, *, head, main, required=REQUIRED_CHECKS):
    """Newest id per required check, bound to this commit and this target baseline."""
    seen: dict[str, dict] = {}
    for row in rows:
        name = str(row.get("name") or "")
        if name not in required:
            continue
        ident = row.get("remote_id")
        if not isinstance(ident, int) or isinstance(ident, bool) or ident <= 0:
            continue
        record = {"check_run_id": ident, "head_sha": "", "base_sha": "", "pull_request_id": None,
                  "status": "queued", "conclusion": None}
        raw = row.get("delivered")
        if raw:
            try:
                delivered = json.loads(raw)
            except ValueError:
                delivered = None
            if isinstance(delivered, dict):
                summary = str((delivered.get("output") or {}).get("summary") or "")
                base = BASE_IN_SUMMARY.search(summary)
                pull = PR_IN_SUMMARY.search(summary)
                record.update(head_sha=str(delivered.get("head_sha") or ""),
                              base_sha=base.group(1) if base else "",
                              pull_request_id=int(pull.group(1)) if pull else None,
                              status=str(delivered.get("status") or "queued"),
                              conclusion=delivered.get("conclusion"))
        if record["head_sha"] and record["head_sha"] != head:
            continue
        previous = seen.get(name)
        if previous is None or ident > previous["check_run_id"]:
            seen[name] = record
    if not seen:
        raise Denied("check_run_missing:" + ",".join(sorted(required)))
    missing = [name for name in required if name not in seen]
    if missing:
        raise Denied("check_run_missing:" + ",".join(sorted(missing)))
    for name in required:
        record = seen[name]
        if record["status"] != "completed" or not record["conclusion"]:
            raise Denied("check_run_pending:" + name)
        if not record["head_sha"]:
            raise Denied("check_run_unbound:" + name)
        if not record["base_sha"]:
            raise Denied("check_run_base_unknown:" + name)
        if record["base_sha"] != main:
            raise Denied("check_run_base_mismatch:" + name)
        if record["conclusion"] != "success":
            raise Denied("check_run_not_success:" + name)
    return seen


def request(token, path):
    req = urllib.request.Request(f"{API}{path}", method="GET",
        headers={"Authorization": f"token {token}", "Accept": "application/json",
                 "User-Agent": "sce-check-run-ids/1"})
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            return json.loads(res.read() or b"{}")
    except urllib.error.HTTPError as exc:
        code = exc.code
    except (OSError, ValueError) as exc:
        raise Denied("platform_unreachable") from exc
    raise Denied(f"platform_denied status={code}" if code in {401, 403} else f"platform_failed status={code}")


def confirm_by_id(token, *, head, checks, owner=OWNER, repo=REPO):
    """Re-read each chosen run from the platform by id (the list endpoint is empty)."""
    for name in sorted(checks):
        run = request(token, f"/repos/{owner}/{repo}/check-runs/{checks[name]['check_run_id']}")
        if not isinstance(run, dict):
            raise Denied("platform_invalid_check_run:" + name)
        if str(run.get("name") or "") != name:
            raise Denied("platform_name_mismatch:" + name)
        if str(run.get("head_sha") or "") != head:
            raise Denied("platform_stale_sha:" + name)
    return checks


def collect(token, *, head, main, host=DEFAULT_HOST, user=DEFAULT_USER, db=DEFAULT_DB, owner=OWNER, repo=REPO):
    head = validate_sha(head, "expected head")
    main = validate_sha(main, "expected Gitee main")
    rows = read_ledger(head=head, host=host, user=user, db=db)
    checks = select_latest(rows, head=head, main=main)
    confirm_by_id(token, head=head, checks=checks, owner=owner, repo=repo)
    return {"action": "check_run_ids", "head": head, "gitee_main": main,
            "checks": checks, "merge_ready": True, "merge_authorized": False,
            "writes": 0, "source": "ci_ledger+bydid_readback",
            "check_runs": " ".join(f"{name}={checks[name]['check_run_id']}" for name in REQUIRED_CHECKS)}


def read_token(path):
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise SystemExit("token file must be an owner-only regular file")
    token = path.read_text().strip()
    if not token:
        raise SystemExit("token file is empty")
    return token


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--head", required=True)
    parser.add_argument("--main", required=True)
    parser.add_argument("--token-file", type=Path, required=True)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--user", default=DEFAULT_USER)
    parser.add_argument("--db", default=DEFAULT_DB)
    args = parser.parse_args()
    token = read_token(args.token_file)
    try:
        receipt = collect(token, head=args.head, main=args.main, host=args.host, user=args.user, db=args.db)
    except Denied as exc:
        print(json.dumps({"action": "check_run_ids", "head": args.head, "gitee_main": args.main,
                          "alert": str(exc), "merge_ready": False, "merge_authorized": False,
                          "writes": 0}, sort_keys=True))
        raise SystemExit(1)
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
