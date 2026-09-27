#!/usr/bin/env python3
"""Fail-closed PR automation for the Gitee integration lane.

``create``/``status`` still serve the one approved governance commit.  ``merge``
is parameterized: it takes the PR number plus the exact expected source and
target SHAs, reads the four required checks back from the platform, refuses on
any pending/failed/stale or drifted identity, calls the platform merge endpoint
(branch protection untouched, main is never pushed) and prints a readback
receipt.

Only fixed codes cross this boundary; response bodies are never echoed.
"""
from __future__ import annotations
import argparse, json, os, stat, urllib.error, urllib.parse, urllib.request
from pathlib import Path

API = "https://gitee.com/api/v5"
OWNER = "leegege"
REPO = "sce-product-odoo"
SOURCE = "fix/gitee-github-mirror-governance"
TARGET = "main"
HEAD = "e2c6aebca5a702ab273081e9fe2c154391155da7"
BOT = "sce-ci-bot"
REQUIRED_CHECKS = ("public_guard", "merge_policy_gate", "professional_quality_gate", "frontend_release_gate")
MERGE_METHODS = ("merge", "squash", "rebase")


class Denied(RuntimeError):
    """Refusals and API failures; never carries a response body."""


def request(token, method, path, payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(f"{API}{path}", data=data, method=method,
        headers={"Authorization": f"token {token}", "Content-Type": "application/json",
                 "Accept": "application/json", "User-Agent": "sce-pr-bot/1"})
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            raw = res.read(); status = res.status
    except urllib.error.HTTPError as exc:
        raw = exc.read(); status = exc.code
    body = json.loads(raw) if raw else {}
    if status in {200, 201, 204}:
        return body
    # 401/403 are authorization refusals (no merge rights or no branch-protection
    # bypass); every other non-2xx is a plain API failure.  Both stay fixed codes.
    if status in {401, 403}:
        raise Denied(f"api_denied method={method} status={status}")
    raise Denied(f"api_failed method={method} status={status}")


def branch_sha(token, branch, owner=OWNER, repo=REPO):
    row = request(token, "GET", f"/repos/{owner}/{repo}/branches/{urllib.parse.quote(branch, safe='')}")
    return (row.get("commit") or {}).get("sha")


def head_data(pr):
    head = pr.get("head") or {}
    return head.get("sha") or (head.get("commit") or {}).get("sha"), head.get("ref") or head.get("label"), head


def matching(pr):
    sha, ref, _ = head_data(pr); base = pr.get("base") or {}
    return (ref == SOURCE or str(ref).endswith(":" + SOURCE)) and base.get("ref") == TARGET and sha == HEAD


def matching_pulls(token, state="all"):
    pulls = request(token, "GET", f"/repos/{OWNER}/{REPO}/pulls?state={state}&per_page=100")
    return [p for p in pulls if matching(p)]


def find_or_create(token):
    if request(token, "GET", "/user").get("login") != BOT:
        raise Denied("bot_identity_mismatch")
    if branch_sha(token, SOURCE) != HEAD:
        raise Denied("source_head_changed")
    candidates = matching_pulls(token)
    if len(candidates) > 1:
        raise Denied("duplicate_pr_for_fixed_head")
    if candidates:
        return candidates[0], "existing"
    pr = request(token, "POST", f"/repos/{OWNER}/{REPO}/pulls", {
        "title": "ci: enforce Gitee-authoritative GitHub mirroring", "head": SOURCE, "base": TARGET,
        "body": "Machine-governance-only PR. Fixed HEAD: `" + HEAD + "`.\n\nArchitecture Impact: P4 operations governance\nLayer Target: Gitee authoritative mirroring\nAffected Modules: scripts/ci, scripts/ops, deploy/gitee-mirror, Make governance"})
    if not matching(pr):
        raise Denied("created_pr_identity_mismatch")
    return pr, "created"


def status(token):
    if request(token, "GET", "/user").get("login") != BOT:
        raise Denied("bot_identity_mismatch")
    candidates = matching_pulls(token)
    if len(candidates) != 1:
        raise Denied("fixed_head_pr_not_unique")
    return candidates[0]


def check_runs(token, sha, owner=OWNER, repo=REPO):
    """All check runs seen for one commit, grouped by name."""
    grouped: dict[str, list[dict]] = {}
    for page in range(1, 11):
        value = request(token, "GET", f"/repos/{owner}/{repo}/commits/{sha}/check-runs?page={page}&per_page=100")
        rows = value.get("check_runs") if isinstance(value, dict) else value
        if not isinstance(rows, list):
            raise Denied("invalid_check_list_response")
        for item in rows:
            if isinstance(item, dict):
                grouped.setdefault(str(item.get("name") or ""), []).append(item)
        if len(rows) < 100:
            break
    return grouped


def required_check_snapshot(token, *, head_sha, required, owner=OWNER, repo=REPO):
    """Success must belong to this exact commit; otherwise refuse."""
    grouped = check_runs(token, head_sha, owner, repo)
    missing = [name for name in required if name not in grouped]
    if missing:
        raise Denied("required_checks_missing:" + ",".join(sorted(missing)))
    stale = [name for name in required if not any(str(run.get("head_sha") or "") == head_sha for run in grouped[name])]
    if stale:
        raise Denied("required_checks_stale_sha:" + ",".join(sorted(stale)))
    snapshot = {}
    for name in required:
        run = next(run for run in reversed(grouped[name]) if str(run.get("head_sha") or "") == head_sha)
        snapshot[name] = {"head_sha": head_sha, "status": run.get("status"), "conclusion": run.get("conclusion")}
    pending = [name for name in required if str(snapshot[name]["status"] or "") != "completed"]
    if pending:
        raise Denied("required_checks_pending:" + ",".join(sorted(pending)))
    failed = [name for name in required if str(snapshot[name]["conclusion"] or "") != "success"]
    if failed:
        raise Denied("required_checks_not_success:" + ",".join(sorted(failed)))
    return snapshot


def merge_pull(token, *, number, expected_head, expected_main, expected_source="", merge_method="squash",
               required=REQUIRED_CHECKS, owner=OWNER, repo=REPO):
    """Merge one protected-lane PR only when every identity and check matches."""
    if merge_method not in MERGE_METHODS:
        raise Denied("unsupported_merge_method")
    path = f"/repos/{owner}/{repo}/pulls/{number}"
    pr = request(token, "GET", path)
    if pr.get("state") != "open":
        raise Denied("pr_not_open")
    sha, ref, head = head_data(pr)
    base = pr.get("base") or {}
    if sha != expected_head:
        raise Denied("pr_head_sha_mismatch")
    if (base.get("ref") or "") != TARGET:
        raise Denied("pr_target_ref_mismatch")
    if (base.get("sha") or "") != expected_main:
        raise Denied("pr_target_sha_mismatch")
    if expected_source and ref != expected_source:
        raise Denied("pr_source_ref_mismatch")
    head_repo = head.get("repo") or {}
    if head_repo and head_repo.get("full_name") not in {f"{owner}/{repo}", None}:
        raise Denied("fork_pr_denied")
    if pr.get("mergeable") is False:
        raise Denied("pr_not_mergeable")
    # Remote truth comes from the branch refs, never from the PR snapshot alone.
    if branch_sha(token, TARGET, owner, repo) != expected_main:
        raise Denied("target_branch_drift")
    if branch_sha(token, ref or "", owner, repo) != expected_head:
        raise Denied("source_branch_drift")
    checks = required_check_snapshot(token, head_sha=expected_head, required=tuple(required), owner=owner, repo=repo)
    result = request(token, "PUT", f"{path}/merge",
                     {"merge_method": merge_method, "prune_source_branch": False, "title": pr.get("title")})
    merged_sha = str((result or {}).get("sha") or "")
    readback = request(token, "GET", path)
    state = readback.get("state")
    if state not in {"merged", "closed"}:
        raise Denied(f"merge_state_unexpected:{state}")
    if len(merged_sha) != 40:
        raise Denied("merge_sha_missing")
    main_after = branch_sha(token, TARGET, owner, repo)
    if main_after != merged_sha:
        # The merge may still have landed; report observations instead of a pass.
        raise Denied(f"merge_readback_mismatch main={main_after} reported={merged_sha}")
    return {"action": "merge", "number": number, "source_branch": ref, "target_branch": TARGET,
            "head_sha": expected_head, "target_sha": expected_main, "state": state,
            "merge_method": merge_method, "merge_commit": merged_sha, "main_after": main_after,
            "checks": checks, "branch_protection_preserved": True, "pushed_main": False}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=("create", "status", "merge"))
    p.add_argument("--token-file", type=Path, required=True)
    p.add_argument("--number", type=int)
    p.add_argument("--expected-head")
    p.add_argument("--expected-main")
    p.add_argument("--expected-source")
    p.add_argument("--merge-method", default="squash", choices=MERGE_METHODS)
    p.add_argument("--require-check", action="append", dest="required")
    p.add_argument("--evidence", type=Path)
    a = p.parse_args()
    token_stat = a.token_file.stat()
    if not stat.S_ISREG(token_stat.st_mode) or token_stat.st_uid != os.getuid() or token_stat.st_mode & 0o077:
        raise SystemExit("token file must be an owner-only regular file")
    token = a.token_file.read_text().strip()
    if not token:
        raise SystemExit("token file is empty")
    if a.action == "create":
        pr, mode = find_or_create(token)
        print(f"[gitee_pr_bot] PASS action=create mode={mode} number={pr.get('number')} state={pr.get('state')} head={HEAD}")
    elif a.action == "status":
        pr = status(token)
        print(f"[gitee_pr_bot] PASS action=status number={pr.get('number')} state={pr.get('state')} head={HEAD}")
    else:
        if not a.number or not a.expected_head or not a.expected_main:
            raise SystemExit("merge requires number, expected-head and expected-main")
        if a.evidence is not None:
            evidence = json.loads(a.evidence.read_text())
            if str(evidence.get("HEAD") or "") not in {"", a.expected_head}:
                raise SystemExit("evidence head does not match expected head")
        receipt = merge_pull(token, number=a.number, expected_head=a.expected_head,
                             expected_main=a.expected_main, expected_source=a.expected_source or "",
                             merge_method=a.merge_method,
                             required=tuple(a.required) if a.required else REQUIRED_CHECKS)
        print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
