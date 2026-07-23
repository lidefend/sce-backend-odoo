#!/usr/bin/env python3
"""Read-only, live-remote production Git authority diagnostic."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
import subprocess
import sys
from typing import Callable


ROOT = Path(__file__).resolve().parents[2]
APPROVED_REMOTE_URL = "https://github.com/lidefend/sce-backend-odoo.git"
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
Runner = Callable[[list[str], int], tuple[int, str, str]]


def _run(args: list[str], timeout: int = 15) -> tuple[int, str, str]:
    proc = subprocess.run(
        args,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def evaluate_authority(
    *,
    expected_sha: str,
    expected_branch: str = "main",
    expected_remote: str = "origin",
    runner: Runner = _run,
    timeout: int = 20,
) -> dict:
    errors: list[str] = []
    evidence: dict[str, object] = {
        "guard": "production_git_authority_guard",
        "schema_version": "2.0",
        "expected_branch": expected_branch,
        "expected_remote": expected_remote,
        "expected_release_sha": expected_sha,
        "approved_remote_url": APPROVED_REMOTE_URL,
    }
    if expected_branch != "main":
        errors.append("production authority branch must be main")
    if not FULL_SHA.fullmatch(expected_sha):
        errors.append("EXPECTED_RELEASE_SHA must be a full lowercase SHA")

    rc, inside, err = runner(["git", "rev-parse", "--is-inside-work-tree"], timeout)
    evidence["inside_work_tree"] = inside
    if rc != 0 or inside != "true":
        errors.append(f"not a git work tree: {err or inside}")
        evidence.update(errors=errors, warnings=[], status="BLOCKED")
        return evidence

    rc, symbolic, err = runner(["git", "symbolic-ref", "--quiet", "--short", "HEAD"], timeout)
    detached = rc != 0
    evidence["detached_head"] = detached
    evidence["branch"] = symbolic
    if detached:
        errors.append(f"detached HEAD is forbidden: {err or '<no symbolic branch>'}")
    elif symbolic != expected_branch:
        errors.append(f"branch mismatch: expected {expected_branch}, got {symbolic}")

    rc, head, err = runner(["git", "rev-parse", "HEAD"], timeout)
    evidence["head"] = head
    if rc != 0 or not FULL_SHA.fullmatch(head):
        errors.append(f"cannot read a full local HEAD: {err or head}")

    rc, status, err = runner(["git", "status", "--porcelain", "--untracked-files=all"], timeout)
    evidence["status_porcelain"] = status
    if rc != 0:
        errors.append(f"cannot read git status: {err}")
    elif status:
        errors.append("git work tree is not clean")

    rc, remote_url, err = runner(["git", "remote", "get-url", expected_remote], timeout)
    evidence["remote_url"] = remote_url
    if rc != 0:
        errors.append(f"cannot read remote URL: {err}")
    elif remote_url != APPROVED_REMOTE_URL:
        errors.append(f"remote URL is not approved: {remote_url}")

    remote_ref = f"refs/remotes/{expected_remote}/{expected_branch}"
    rc, tracking_sha, _ = runner(["git", "rev-parse", remote_ref], timeout)
    evidence["remote_tracking_ref"] = remote_ref
    evidence["remote_tracking_sha"] = tracking_sha if rc == 0 else ""

    rc, live, err = runner(
        ["git", "ls-remote", "--heads", expected_remote, expected_branch], timeout
    )
    evidence["live_remote_query_ok"] = rc == 0
    if rc != 0:
        live_sha = ""
        errors.append(f"live remote main query failed: {err or live}")
    else:
        live_sha = live.split()[0] if live else ""
        if not FULL_SHA.fullmatch(live_sha):
            errors.append("live remote main response is missing or invalid")
    evidence["live_remote_main_sha"] = live_sha
    evidence["stale_remote_ref_detected"] = bool(
        tracking_sha and live_sha and tracking_sha != live_sha
    )

    if FULL_SHA.fullmatch(expected_sha) and FULL_SHA.fullmatch(head) and FULL_SHA.fullmatch(live_sha):
        if len({expected_sha, head, live_sha}) != 1:
            errors.append(
                "authority mismatch: "
                f"EXPECTED_RELEASE_SHA={expected_sha} local_HEAD={head} live_remote_main={live_sha}"
            )

    evidence["errors"] = errors
    evidence["warnings"] = []
    evidence["status"] = "PASS" if not errors else "BLOCKED"
    return evidence


def main() -> int:
    expected_sha = os.getenv("EXPECTED_RELEASE_SHA", "").strip()
    expected_branch = os.getenv("PRODUCTION_GIT_AUTHORITY_BRANCH", "main").strip() or "main"
    expected_remote = os.getenv("PRODUCTION_GIT_AUTHORITY_REMOTE", "origin").strip() or "origin"
    timeout = int(os.getenv("PRODUCTION_GIT_AUTHORITY_REMOTE_TIMEOUT", "20"))
    evidence = evaluate_authority(
        expected_sha=expected_sha,
        expected_branch=expected_branch,
        expected_remote=expected_remote,
        timeout=timeout,
    )
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    if evidence["status"] != "PASS":
        print("[production_git_authority_guard] BLOCKED")
        return 2
    print("[production_git_authority_guard] PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
