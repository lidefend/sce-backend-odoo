#!/usr/bin/env python3
"""Execution-layer helpers for one converged product/demo integration cycle.

The tool is intentionally read-mostly: it never edits product code, never
rewrites generated evidence, and never merges a pull request. It reduces three
measured sources of wasted cycles:

* files already committed being reported as "in flight";
* independent local gate failures being discovered one push at a time;
* an exact-head Quick being terminated by a short-lived runner session.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / ".runtime/integration-cycle"


@dataclass(frozen=True)
class Gate:
    key: str
    command: tuple[str, ...]
    timeout: int = 900


FAST_GATES: tuple[Gate, ...] = (
    Gate("complexity", ("make", "architecture.complexity_baseline_lock"), 300),
    Gate("decision_authority", ("make", "verify.frontend.decision_authority.unit"), 300),
    Gate("contract_architecture", ("make", "verify.contract.architecture.suite"), 600),
    Gate("data_scope", ("make", "verify.sc_data_scope.rule_coverage"), 300),
    Gate("component_takeover", ("make", "verify.frontend.component_driver_takeover.unit"), 300),
    Gate("test_coverage_registry", ("make", "verify.test.coverage.registry"), 300),
    Gate("test_inventory", ("python3", "scripts/ci/generate_test_inventory.py"), 300),
    Gate("frontend_lint", ("make", "verify.frontend.lint.src"), 300),
    Gate("typecheck", ("bash", "scripts/dev/pnpm_exec.sh", "-C", "frontend/apps/web", "typecheck"), 600),
    Gate("lane_coverage", ("python3", "scripts/audit/verification_lane_coverage.py", "--check"), 300),
)

SUCCESS_STATES = {"SUCCESS", "PASS", "SKIPPED", "NEUTRAL"}
FAILURE_STATES = {"FAILURE", "ERROR", "CANCELLED", "TIMED_OUT", "ACTION_REQUIRED"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.rstrip("\n") if result.returncode == 0 else ""


def clean_status(root: Path) -> str:
    return git(root, "status", "--porcelain=v2", "--untracked-files=all")


def path_ownership(root: Path, path: str) -> dict:
    status = git(root, "status", "--porcelain=v2", "--untracked-files=all", "--", path)
    log = git(root, "log", "-1", "--format=%H%x09%ci%x09%s", "--", path)
    if status:
        state = "dirty_or_untracked"
    elif log:
        state = "committed"
    else:
        state = "absent"
    return {"path": path, "state": state, "status": status.splitlines(), "head": log.split("\t", 2)[0] if log else ""}


def worktrees(root: Path) -> list[dict]:
    rows: list[dict] = []
    current: dict = {}
    for line in git(root, "worktree", "list", "--porcelain").splitlines():
        if not line:
            if current:
                rows.append(current)
                current = {}
            continue
        key, _, value = line.partition(" ")
        if key == "worktree":
            if current:
                rows.append(current)
            current = {"worktree": value}
        elif key in {"HEAD", "branch"}:
            current[key] = value
    if current:
        rows.append(current)
    return rows


def snapshot(root: Path, paths: Iterable[str]) -> dict:
    return {
        "schema": "integration_cycle.snapshot.v1",
        "generated_at": utc_now(),
        "branch": git(root, "branch", "--show-current"),
        "head": git(root, "rev-parse", "HEAD"),
        "clean": not clean_status(root),
        "worktrees": worktrees(root),
        "paths": [path_ownership(root, path) for path in paths],
    }


def _write_json(path: Path | None, payload: dict) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_gate(
    gate: Gate,
    root: Path,
    log_path: Path,
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> dict:
    started = time.monotonic()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    timed_out = False
    with log_path.open("w", encoding="utf-8") as log:
        log.write(f"$ {' '.join(gate.command)}\n")
        log.flush()
        try:
            completed = runner(
                list(gate.command),
                cwd=str(root),
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=gate.timeout,
                check=False,
            )
            code = int(completed.returncode)
        except subprocess.TimeoutExpired:
            code = 124
            timed_out = True
        except FileNotFoundError:
            code = 127
    duration = round(time.monotonic() - started, 2)
    return {
        "key": gate.key,
        "command": list(gate.command),
        "status": "passed" if code == 0 else "failed",
        "exit_code": code,
        "timed_out": timed_out,
        "duration_seconds": duration,
        "log": str(log_path),
    }


def summarize_gates(results: Iterable[dict]) -> dict:
    rows = list(results)
    failed = [row["key"] for row in rows if row["status"] != "passed"]
    return {
        "passed": [row["key"] for row in rows if row["status"] == "passed"],
        "failed": failed,
        "ok": not failed,
    }


def fast_gates(
    root: Path,
    log_dir: Path,
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
    fail_fast: bool = False,
) -> dict:
    log_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []
    for gate in FAST_GATES:
        result = run_gate(gate, root, log_dir / f"{gate.key}.log", runner=runner)
        results.append(result)
        print(
            f"[{result['status']}] {gate.key} {result['duration_seconds']}s "
            f"log={result['log']}",
            flush=True,
        )
        if fail_fast and result["status"] != "passed":
            break
    summary = summarize_gates(results)
    payload = {
        "schema": "integration_cycle.fast_gates.v1",
        "generated_at": utc_now(),
        "head": git(root, "rev-parse", "HEAD"),
        "results": results,
        "summary": summary,
    }
    return payload


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _receipt_verified(root: Path, head: str) -> bool:
    result = subprocess.run(
        [sys.executable, "scripts/ops/local_quick_evidence.py", "verify", "--expected-head", head],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def quick_paths(root: Path, head: str) -> tuple[Path, Path]:
    base = root / ".runtime/integration-cycle" / f"quick-{head[:12]}"
    return base.with_suffix(".json"), base.with_suffix(".log")


def quick_env(source: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(source if source is not None else os.environ)
    for key in ("MAKEFLAGS", "MFLAGS", "MAKELEVEL", "MAKEOVERRIDES"):
        env.pop(key, None)
    return env


def quick_start(root: Path) -> tuple[int, dict]:
    status = clean_status(root)
    head = git(root, "rev-parse", "HEAD")
    meta_path, log_path = quick_paths(root, head)
    if status:
        return 2, {"status": "blocked", "reason": "worktree_not_clean", "head": head}
    if meta_path.is_file():
        existing = json.loads(meta_path.read_text(encoding="utf-8"))
        if _pid_alive(int(existing.get("pid") or 0)):
            return 0, {"status": "already_running", **existing}
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    log_handle = log_path.open("w", encoding="utf-8")
    process = subprocess.Popen(
        ["make", "ci.local.quick"],
        cwd=str(root),
        stdin=subprocess.DEVNULL,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        start_new_session=True,
        env=quick_env(),
    )
    log_handle.close()
    payload = {
        "schema": "integration_cycle.quick.v1",
        "head": head,
        "pid": process.pid,
        "log": str(log_path),
        "started_at": utc_now(),
    }
    meta_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0, {"status": "started", **payload}


def quick_status(root: Path) -> tuple[int, dict]:
    head = git(root, "rev-parse", "HEAD")
    meta_path, log_path = quick_paths(root, head)
    if not meta_path.is_file():
        return 2, {"status": "missing", "head": head, "reason": "no quick metadata for this head"}
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    running = _pid_alive(int(meta.get("pid") or 0))
    verified = _receipt_verified(root, head)
    tail = ""
    if log_path.is_file():
        tail = "\n".join(log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-20:])
    payload = {
        "schema": "integration_cycle.quick_status.v1",
        "head": head,
        "running": running,
        "receipt_verified": verified,
        "log": str(log_path),
        "log_tail": tail,
    }
    if verified:
        return 0, {"status": "passed", **payload}
    if running:
        return 1, {"status": "running", **payload}
    return 2, {"status": "stopped_without_receipt", **payload}


def checks_ready(rows: Iterable[dict]) -> tuple[bool, list[str], list[str]]:
    failed: list[str] = []
    pending: list[str] = []
    for row in rows:
        name = str(row.get("name") or row.get("context") or "unknown")
        state = str(row.get("conclusion") or row.get("state") or "").upper()
        if state in FAILURE_STATES:
            failed.append(name)
        elif state not in SUCCESS_STATES:
            pending.append(name)
    return not failed and not pending, failed, pending


def merge_readiness(root: Path, pr: int, allow_no_quick: bool = False) -> tuple[int, dict]:
    result = subprocess.run(
        [
            "gh",
            "pr",
            "view",
            str(pr),
            "--json",
            "headRefOid,mergeStateStatus,mergeable,state,statusCheckRollup",
        ],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return 2, {"status": "error", "reason": result.stderr.strip() or "gh pr view failed"}
    payload = json.loads(result.stdout)
    head = git(root, "rev-parse", "HEAD")
    ready_checks, failed, pending = checks_ready(payload.get("statusCheckRollup") or [])
    quick_verified = _receipt_verified(root, head)
    ready = (
        payload.get("state") == "OPEN"
        and payload.get("headRefOid") == head
        and payload.get("mergeable") == "MERGEABLE"
        and payload.get("mergeStateStatus") in {"CLEAN", "HAS_HOOKS"}
        and ready_checks
        and (quick_verified or allow_no_quick)
    )
    return (0 if ready else 1), {
        "schema": "integration_cycle.merge_readiness.v1",
        "status": "ready" if ready else "blocked",
        "pr": pr,
        "local_head": head,
        "pr_head": payload.get("headRefOid"),
        "merge_state": payload.get("mergeStateStatus"),
        "mergeable": payload.get("mergeable"),
        "quick_verified": quick_verified,
        "allow_no_quick": allow_no_quick,
        "failed_checks": failed,
        "pending_checks": pending,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT))
    sub = parser.add_subparsers(dest="command", required=True)

    snap = sub.add_parser("snapshot")
    snap.add_argument("--path", action="append", default=[])
    snap.add_argument("--json")

    fast = sub.add_parser("fast-gates")
    fast.add_argument("--json")
    fast.add_argument("--fail-fast", action="store_true")

    sub.add_parser("quick-start")
    sub.add_parser("quick-status")

    merge = sub.add_parser("merge-readiness")
    merge.add_argument("--pr", type=int, required=True)
    merge.add_argument("--allow-no-quick", action="store_true")

    args = parser.parse_args(argv)
    root = Path(args.root).resolve()

    if args.command == "snapshot":
        payload = snapshot(root, args.path)
        _write_json(Path(args.json) if args.json else None, payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if args.command == "fast-gates":
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        payload = fast_gates(
            root,
            root / ".runtime/integration-cycle" / f"fast-{stamp}",
            fail_fast=args.fail_fast,
        )
        _write_json(Path(args.json) if args.json else None, payload)
        summary = payload["summary"]
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0 if summary["ok"] else 1

    if args.command == "quick-start":
        code, payload = quick_start(root)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return code

    if args.command == "quick-status":
        code, payload = quick_status(root)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return code

    if args.command == "merge-readiness":
        code, payload = merge_readiness(root, args.pr, allow_no_quick=args.allow_no_quick)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return code

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
