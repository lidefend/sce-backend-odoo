"""Read-only formal gate selection. This module never executes or approves a merge.

Run from the trusted controller installation, not a candidate checkout's module.
The resulting plan is draft until a trusted isolated runner consumes it.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

from scripts.ci.ci_risk_classifier import classify, load_policy

ROOT = Path(__file__).resolve().parents[2]
REPOSITORY = "leegege/sce-product-odoo"
CHECKS = ("public_guard", "merge_policy_gate", "professional_quality_gate", "frontend_release_gate")
SOURCES = tuple(".github/workflows/" + name + ".yml" for name in CHECKS)
INPUTS = SOURCES + ("config/ci/risk_tiering_v1.json", "scripts/ci/ci_risk_classifier.py",
                    "scripts/ci/gitee_gate_plan.py", "scripts/ci/gitee_pr_identity.py",
                    "scripts/ci/gitee_ci_checks.py", "scripts/ci/gitee_formal_executor.py", "scripts/ci/gitee_formal_queue.py", "scripts/ci/gitee_formal_worker.py", "scripts/ops/gitee_frontend_cache.py",
                    "scripts/ci/gitee_ci_acceptance.py", "scripts/ci/gitee_frontend_reuse.py", "scripts/ops/gitee_frontend_reuse.py")
SHA = re.compile(r"[0-9a-f]{40}")
# A candidate whose preparation failed must still produce four attributed, red
# checks instead of four silent waits. Only these bounded, trusted codes may be
# echoed into a check summary, so no candidate-controlled text reaches the report.
PREPARATION_FAILURE_REASONS = (
    "pull_request_unavailable",
    "invalid_source_branch",
    "platform_identity_unavailable",
    "checkout_failed",
    "checkout_mismatch",
    "baseline_not_ancestor",
    "change_set_unavailable",
    "plan_rejected",
    "preparation_incomplete",
)
BLOCKERS = ("isolated_product_runner_not_accepted", "protected_pr_behavior_not_accepted")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def select_modes(result, candidate):
    professional = result.professional_mode
    frontend = result.frontend_mode
    if not candidate:
        if frontend == "full":
            frontend = "standard"
        if professional == "full":
            professional = ("standard_backend" if result.backend_changed else
                            "standard_frontend" if result.frontend_changed else "governance")
    return {
        "public_guard": "skip_fast" if result.lane == "FAST" else "required",
        "merge_policy_gate": "fast" if result.lane == "FAST" else "required",
        "professional_quality_gate": professional,
        "frontend_release_gate": frontend,
    }


def plan(*, head, base, source_branch, pr_number, paths, candidate=False, root=ROOT, preparation_failure=None):
    if not isinstance(head, str) or not SHA.fullmatch(head) or not isinstance(base, str) or not SHA.fullmatch(base):
        raise ValueError("full head and base SHA required")
    if head == base or head == "0" * 40 or base == "0" * 40:
        raise ValueError("distinct nonzero commits required")
    if type(pr_number) is not int or pr_number < 1:
        raise ValueError("positive PR number required")
    if type(candidate) is not bool:
        raise ValueError("candidate must be a boolean")
    if (not isinstance(source_branch, str) or
            not re.fullmatch(r"(?:feature|fix|refactor|audit|release|codex)/[A-Za-z0-9_./-]+", source_branch) or
            any(x in source_branch for x in ("..", "//", "@{")) or
            source_branch.endswith(("/", ".", ".lock"))):
        raise ValueError("invalid source branch")
    if preparation_failure is not None and preparation_failure not in PREPARATION_FAILURE_REASONS:
        raise ValueError("unknown preparation failure reason")
    paths = tuple(paths)
    if any(not isinstance(p, str) or not p or p.startswith("/") or
           ".." in Path(p).parts or any(c in p for c in ("\\", "\n", "\r", "\0")) for p in paths):
        raise ValueError("invalid change set")
    if not paths and preparation_failure is None:
        raise ValueError("invalid or empty change set")
    if paths and preparation_failure is not None:
        # A failed preparation has no trustworthy change set. Accepting paths here
        # would let an unattributable failure pass itself off as a classified plan.
        raise ValueError("preparation failure cannot claim a change set")
    result = classify(paths, event_name="pull_request", policy=load_policy(root / "config/ci/risk_tiering_v1.json"))
    modes = select_modes(result, candidate)
    blockers = list(BLOCKERS)
    if preparation_failure is not None:
        blockers.insert(0, "preparation_failed:" + preparation_failure)
    record = {
        "schema_version": "gitee-formal-gate-plan/v1",
        "repository": REPOSITORY, "target_branch": "main", "source_branch": source_branch,
        "head_sha": head, "base_sha": base, "pr_number": pr_number,
        "candidate_requested": candidate, "lane": result.lane,
        "frontend_changed": result.frontend_changed, "backend_changed": result.backend_changed,
        "paths": sorted(set(paths)),
        "source_hashes": {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in INPUTS},
        "checks": [{"name": name, "mode": modes[name], "workflow": SOURCES[i],
                    "state": "not_run"} for i, name in enumerate(CHECKS)],
        "toolchain": {"node": "22.17.0", "pnpm": "9.12.3",
                      "python310_compatibility_required": candidate and result.professional_mode == "full"},
        "pr_identity_verified": False, "remote_refs_verified": False,
        "execution_ready": False, "integration_eligible": False,
        "blockers": blockers,
    }
    if preparation_failure is not None:
        record["preparation_failure"] = preparation_failure
    record["plan_sha256"] = digest(record)
    return record


def git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def changed_paths(root, base, head):
    for value in (base, head):
        if not SHA.fullmatch(value):
            raise ValueError("full SHA required")
        if git(root, "rev-parse", value + "^{commit}") != value:
            raise ValueError("commit identity mismatch")
    subprocess.run(["git", "merge-base", "--is-ancestor", base, head], cwd=root, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # Include deletions and both sides of moves; no rename heuristics can hide a
    # deleted security/CI-owned path behind its new documentation-only name.
    raw = subprocess.check_output(["git", "diff", "--no-renames", "--name-only", "-z", base, head, "--"], cwd=root)
    return tuple(p.decode("utf-8", errors="strict") for p in raw.split(b"\0") if p)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--head", required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--source-branch", required=True)
    parser.add_argument("--pr-number", required=True, type=int)
    parser.add_argument("--candidate", action="store_true")
    parser.add_argument("--token-file", help="Optional owner-only file for live read-only PR verification")
    args = parser.parse_args()
    if git(ROOT, "rev-parse", "HEAD") != args.head:
        raise ValueError("controller HEAD mismatch")
    if git(ROOT, "branch", "--show-current") != args.source_branch:
        raise ValueError("controller branch mismatch")
    dirty = bool(git(ROOT, "status", "--porcelain=v1", "--untracked-files=all"))
    if dirty:
        raise ValueError("clean committed controller required")
    record = plan(head=args.head, base=args.base, source_branch=args.source_branch,
                  pr_number=args.pr_number, paths=changed_paths(ROOT, args.base, args.head),
                  candidate=args.candidate)
    if args.token_file:
        from scripts.ci.gitee_pr_identity import ReadAPI, observe
        snapshot = observe(ReadAPI(args.token_file), number=args.pr_number,
                           source=args.source_branch, head=args.head, base=args.base)
        record["platform_snapshot"] = snapshot
        record["pr_identity_verified"] = True
        record["remote_refs_verified"] = True
        record.pop("plan_sha256")
        record["plan_sha256"] = digest(record)
    print(json.dumps(record, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
