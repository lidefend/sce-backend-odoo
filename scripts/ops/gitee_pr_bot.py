#!/usr/bin/env python3
"""Fail-closed PR automation for the Gitee integration lane.

``create``/``status`` still serve the one approved governance commit.  ``merge``
is parameterized: it takes the PR number plus the exact expected source and
target SHAs, reads the four required checks back from the platform, refuses on
any pending/failed/stale or drifted identity, calls the platform merge endpoint
(branch protection untouched, main is never pushed) and prints a readback
receipt.

Only fixed codes cross this boundary; response bodies are never echoed.

Platform limitation -- do not overstate this entry.  The Gitee merge endpoint has
no compare-and-swap on ``(head_sha, base_sha)``: the identity checks below are a
pre-flight snapshot, not an atomic binding, so a concurrent push between the
check and the ``PUT`` is not prevented by this tool.  Drift safety still comes
from branch protection plus the post-merge readback, and every receipt therefore
reports ``atomic_sha_binding=false``.  Three further boundaries are enforced:

* each required check must be the *latest* run for this commit -- a re-run that
  is still queued is never masked by an older success.  Order is proven only by
  strictly increasing platform ids: a set that is missing ids, or that repeats
  one, is refused rather than judged by array position.  Pagination that did not
  complete is refused the same way;
* the platform readback is the single success authority.  The ordinary path and
  the timeout-recovery path share it, so both verify the *observed* PR identity,
  merge commit and post-merge ``main``.  A PR that was merely closed, or a merge
  that landed another commit, is refused rather than reported as the expected
  one (the receipt's ``target_sha`` stays the pre-flight target snapshot);
* a merge request that times out is classified (merged / not merged yet /
  uncertain) and never retried blindly, because a second ``PUT`` could merge
  twice.  Reading ``open`` afterwards only shows it had not landed *yet*;
* ``--require-check`` may only *add* checks to the fixed four, never shrink them.

Platform limitation -- check-run *listing*.  ``GET /commits/{sha}/check-runs``
answers ``total_count=0`` for every commit in this repository, ``main`` included,
while ``GET /check-runs/{id}`` reads the same runs back correctly.  The latest-run
proof therefore cannot be taken from the list endpoint here, so a caller that has
already observed the run ids may pass ``--check-run NAME=ID``.  Each id is then
read back individually and must carry the expected name, this exact commit and a
completed ``success``.  That path is reported honestly as
``check_verification={"source": "explicit_ids", "latest_run_proof": false}``: an id
cannot prove that no *newer* run was queued after it was observed, so it is never
presented as the list-endpoint guarantee.  The list endpoint stays the default and
its stricter proof is used whenever it returns anything.
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
CHECK_RUN_PAGES = 10
CHECK_RUN_PER_PAGE = 100


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


def _numeric(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def latest_check_run(runs):
    """Pick the newest run for a single check name, or refuse.

    A re-run always carries a larger ``id``, so a strictly increasing platform id
    is the only proof of order.  When any run omits its id -- or two runs share
    one -- the order cannot be established, and guessing from the response's
    array position is exactly what let an older success mask a queued re-run.
    Such a set is refused instead of judged.
    """
    if not runs:
        return None
    ids = [_numeric(run.get("id")) for run in runs]
    if any(ident is None for ident in ids) or len(set(ids)) != len(ids):
        raise Denied("check_run_order_undetermined")
    return max(zip(ids, runs), key=lambda pair: pair[0])[1]


def check_runs(token, sha, owner=OWNER, repo=REPO):
    """All check runs seen for one commit, grouped by name.

    Pagination must be exhausted: a truncated list could hide a newer run, so an
    incomplete read is refused rather than judged.
    """
    grouped: dict[str, list[dict]] = {}
    seen = 0
    total_count = None
    complete = False
    for page in range(1, CHECK_RUN_PAGES + 1):
        value = request(token, "GET",
                        f"/repos/{owner}/{repo}/commits/{sha}/check-runs?page={page}&per_page={CHECK_RUN_PER_PAGE}")
        rows = value.get("check_runs") if isinstance(value, dict) else value
        if not isinstance(rows, list):
            raise Denied("invalid_check_list_response")
        if isinstance(value, dict):
            raw_total = value.get("total_count")
            if isinstance(raw_total, int) and not isinstance(raw_total, bool):
                total_count = raw_total
        for item in rows:
            if isinstance(item, dict):
                grouped.setdefault(str(item.get("name") or ""), []).append(item)
        seen += len(rows)
        if len(rows) < CHECK_RUN_PER_PAGE:
            complete = True
            break
    if not complete:
        raise Denied("check_run_pagination_incomplete")
    if total_count is not None and seen < total_count:
        raise Denied("check_run_pagination_incomplete")
    return grouped


def required_check_snapshot(token, *, head_sha, required, owner=OWNER, repo=REPO):
    """The latest run of each required check must be a success on this commit."""
    grouped = check_runs(token, head_sha, owner, repo)
    missing = [name for name in required if name not in grouped]
    if missing:
        raise Denied("required_checks_missing:" + ",".join(sorted(missing)))
    stale = [name for name in required if not any(str(run.get("head_sha") or "") == head_sha for run in grouped[name])]
    if stale:
        raise Denied("required_checks_stale_sha:" + ",".join(sorted(stale)))
    snapshot = {}
    for name in required:
        runs_for_commit = [run for run in grouped[name] if str(run.get("head_sha") or "") == head_sha]
        run = latest_check_run(runs_for_commit)
        snapshot[name] = {"head_sha": head_sha, "check_run_id": run.get("id"),
                          "status": run.get("status"), "conclusion": run.get("conclusion")}
    pending = [name for name in required if str(snapshot[name]["status"] or "") != "completed"]
    if pending:
        raise Denied("required_checks_pending:" + ",".join(sorted(pending)))
    failed = [name for name in required if str(snapshot[name]["conclusion"] or "") != "success"]
    if failed:
        raise Denied("required_checks_not_success:" + ",".join(sorted(failed)))
    return snapshot


def enforce_required_checks(required):
    """The four required checks are fixed; nothing may shrink the set."""
    names = tuple(dict.fromkeys(str(name).strip() for name in (required or ()) if str(name).strip()))
    shrunk = [name for name in REQUIRED_CHECKS if name not in names]
    if shrunk:
        raise Denied("required_checks_shrunk:" + ",".join(shrunk))
    return names


def check_snapshot_by_id(token, *, head_sha, required, evidence, owner=OWNER, repo=REPO):
    """Bind every required check to this commit through an explicit check-run id.

    Fallback for the platform limitation documented in the module docstring: the
    commit check-run list is empty here, so the ids are supplied by the caller and
    each is read back on its own.  A run must carry the expected name, this exact
    commit, ``completed`` and ``success``; the set must cover every required check,
    add nothing unknown, and repeat neither a name nor an id.  This cannot prove
    the run is the *latest* one, so callers report ``latest_run_proof=false``.
    """
    names = [str(name) for name, _ in evidence]
    missing = [name for name in required if name not in names]
    if missing:
        raise Denied("required_checks_missing:" + ",".join(sorted(missing)))
    unknown = [name for name in names if name not in required]
    if unknown:
        raise Denied("check_evidence_unknown:" + ",".join(sorted(set(unknown))))
    if len(set(names)) != len(names):
        raise Denied("check_evidence_duplicate_name")
    if len({ident for _, ident in evidence}) != len(evidence):
        raise Denied("check_evidence_duplicate_id")
    snapshot = {}
    for name, ident in evidence:
        if not isinstance(ident, int) or isinstance(ident, bool) or ident <= 0:
            raise Denied("check_evidence_invalid_id:" + name)
        run = request(token, "GET", f"/repos/{owner}/{repo}/check-runs/{ident}")
        if str(run.get("name") or "") != name:
            raise Denied("check_evidence_name_mismatch:" + name)
        if str(run.get("head_sha") or "") != head_sha:
            raise Denied("required_checks_stale_sha:" + name)
        if str(run.get("status") or "") != "completed":
            raise Denied("required_checks_pending:" + name)
        if str(run.get("conclusion") or "") != "success":
            raise Denied("required_checks_not_success:" + name)
        snapshot[name] = {"head_sha": head_sha, "check_run_id": ident,
                          "status": "completed", "conclusion": "success"}
    return snapshot


def with_required_checks(extra):
    """``--require-check`` may only add to the fixed four required checks."""
    return enforce_required_checks((*REQUIRED_CHECKS, *(extra or ())))


def verify_merge_readback(token, *, path, expected_head, expected_main, expected_source="",
                          reported_sha="", uncertain=False, owner=OWNER, repo=REPO):
    """Prove from the platform what actually landed after a merge request.

    Shared by the ordinary path and the timeout-recovery path so neither can
    report success for a merge that did not happen, that merged another commit,
    or that merely closed the PR.  Every identity in the receipt is the *observed*
    value: a mismatch is an anomaly, never the expected value echoed back.
    """
    try:
        readback = request(token, "GET", path)
    except (Denied, OSError, ValueError) as exc:
        raise Denied(f"merge_outcome_uncertain readback_failed:{exc}") from exc
    if not isinstance(readback, dict):
        raise Denied("merge_outcome_uncertain readback_unreadable")
    state = str(readback.get("state") or "")
    merged_flag = readback.get("merged") is True or bool(readback.get("merged_at"))
    if not (state == "merged" or (state == "closed" and merged_flag)):
        # ``closed`` alone is a refusal: a closed PR is not a merged one.
        if uncertain and state == "open":
            # An open PR at readback time only proves it had not landed *yet*; it
            # does not prove the timed-out request never executed.  Never retry.
            raise Denied("merge_outcome_open_at_readback")
        raise Denied(f"merge_state_unexpected:{state or 'unknown'}")
    sha, ref, _head = head_data(readback)
    if sha != expected_head:
        raise Denied(f"merge_readback_head_mismatch observed={sha or 'none'} expected={expected_head}")
    if expected_source and ref != expected_source:
        raise Denied(f"merge_readback_source_mismatch observed={ref or 'none'} expected={expected_source}")
    if (readback.get("base") or {}).get("ref") != TARGET:
        raise Denied("merge_readback_target_ref_mismatch")
    merged_sha = str(readback.get("merge_commit_sha") or reported_sha or "")
    if len(merged_sha) != 40:
        raise Denied("merge_outcome_uncertain missing_merge_sha")
    main_after = branch_sha(token, TARGET, owner, repo)
    if main_after != merged_sha:
        # The merge may still have landed; report observations instead of a pass.
        raise Denied(f"merge_readback_mismatch main={main_after} reported={merged_sha}")
    return {"state": state, "head_sha": sha, "source_branch": ref,
            "merge_commit": merged_sha, "main_after": main_after}


def merge_pull(token, *, number, expected_head, expected_main, expected_source="", merge_method="squash",
               required=REQUIRED_CHECKS, check_evidence=(), owner=OWNER, repo=REPO):
    """Merge one protected-lane PR only when every identity and check matches."""
    if merge_method not in MERGE_METHODS:
        raise Denied("unsupported_merge_method")
    required = enforce_required_checks(required)
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
    if check_evidence:
        checks = check_snapshot_by_id(token, head_sha=expected_head, required=tuple(required),
                                      evidence=tuple(check_evidence), owner=owner, repo=repo)
        verification = {"source": "explicit_ids", "latest_run_proof": False}
    else:
        checks = required_check_snapshot(token, head_sha=expected_head, required=tuple(required),
                                         owner=owner, repo=repo)
        verification = {"source": "commit_list", "latest_run_proof": True}
    try:
        result = request(token, "PUT", f"{path}/merge",
                         {"merge_method": merge_method, "prune_source_branch": False, "title": pr.get("title")})
    except (OSError, ValueError):
        # The write may have landed before the connection or body died.  Read the
        # platform back and classify; a retry here could merge a second time.
        observed = verify_merge_readback(token, path=path, expected_head=expected_head,
                                         expected_main=expected_main, expected_source=ref or "",
                                         uncertain=True, owner=owner, repo=repo)
        merge_outcome = "merged_after_uncertain_request"
    else:
        observed = verify_merge_readback(
            token, path=path, expected_head=expected_head, expected_main=expected_main,
            expected_source=ref or "", reported_sha=str(result.get("sha") or "") if isinstance(result, dict) else "",
            owner=owner, repo=repo)
        merge_outcome = "confirmed"
    return {"action": "merge", "number": number, "target_branch": TARGET,
            "target_sha": expected_main, "merge_method": merge_method,
            "checks": checks, "check_verification": verification,
            "branch_protection_preserved": True, "pushed_main": False,
            "atomic_sha_binding": False, "merge_outcome": merge_outcome, **observed}


def parse_check_evidence(pairs):
    """``NAME=ID`` pairs from ``--check-run`` into verified-by-id evidence."""
    evidence = []
    for raw in pairs or ():
        name, _, value = str(raw).partition("=")
        name, value = name.strip(), value.strip()
        if not name or not value.isdigit():
            raise SystemExit(f"--check-run must be NAME=<numeric id>, got {raw!r}")
        evidence.append((name, int(value)))
    return evidence


def main():
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=("create", "status", "merge"))
    p.add_argument("--token-file", type=Path, required=True)
    p.add_argument("--number", type=int)
    p.add_argument("--expected-head")
    p.add_argument("--expected-main")
    p.add_argument("--expected-source")
    p.add_argument("--merge-method", default="squash", choices=MERGE_METHODS)
    # Add-only: the four platform-required checks are always enforced, so this
    # flag can never shrink the set that gates a merge.
    p.add_argument("--require-check", action="append", dest="required",
                   help="extra required checks; the fixed four are always enforced")
    p.add_argument("--check-run", action="append", default=[], dest="check_run", metavar="NAME=ID",
                   help="read a required check back by explicit run id instead of the commit list")
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
                             required=with_required_checks(a.required),
                             check_evidence=parse_check_evidence(a.check_run))
        print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
