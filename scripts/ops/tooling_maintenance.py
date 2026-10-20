#!/usr/bin/env python3
"""Fast, bounded maintenance lane for P4 tooling-only changes.

This lane is intentionally narrower than the product delivery lane. It exists
so a small guard or ops-tool fix does not pay the product/ORM/browser matrix
when no product, runtime, data or deployment surface changed.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BRANCH = "main"

ALLOWED_PREFIXES = (
    "docs/ops/",
    "scripts/verify/",
    "scripts/ops/",
)
ALLOWED_EXACT = {
    "make/guards.mk",
}
FORBIDDEN_PREFIXES = (
    "addons/",
    "demo_addons/",
    "config/",
    "frontend/",
    ".agent/",
)


def git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def changed_paths(root: Path, base: str = "origin/main") -> list[str]:
    paths: set[str] = set()
    for args in (
        ("diff", "--name-only", "--no-renames", base, "HEAD"),
        ("diff", "--name-only", "--no-renames"),
        ("diff", "--cached", "--name-only", "--no-renames"),
        ("ls-files", "--others", "--exclude-standard"),
    ):
        result = git(root, *args)
        if result.returncode == 0:
            paths.update(line for line in result.stdout.splitlines() if line)
    return sorted(paths)


def classify(paths: list[str], allow_make_guards: bool = False) -> dict:
    allowed: list[str] = []
    blocked: list[tuple[str, str]] = []
    for path in paths:
        if path.startswith(FORBIDDEN_PREFIXES):
            blocked.append((path, "forbidden_product_runtime_or_ledger_path"))
        elif path in ALLOWED_EXACT:
            if path == "make/guards.mk" and not allow_make_guards:
                blocked.append((path, "make_guards_requires_explicit_flag"))
            else:
                allowed.append(path)
        elif path.startswith(ALLOWED_PREFIXES):
            allowed.append(path)
        else:
            blocked.append((path, "outside_tooling_maintenance_allowlist"))
    return {"allowed": allowed, "blocked": blocked, "ok": not blocked}


def module_name(path: str) -> str:
    return path.removesuffix(".py").replace("/", ".")


def run_command(command: list[str], root: Path, log: Path, timeout: int = 300) -> dict:
    started = time.monotonic()
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("w", encoding="utf-8") as handle:
        handle.write("$ " + " ".join(command) + "\n")
        handle.flush()
        try:
            result = subprocess.run(
                command,
                cwd=str(root),
                stdin=subprocess.DEVNULL,
                stdout=handle,
                stderr=subprocess.STDOUT,
                timeout=timeout,
                check=False,
            )
            code = result.returncode
            timed_out = False
        except subprocess.TimeoutExpired:
            code = 124
            timed_out = True
        except FileNotFoundError:
            code = 127
            timed_out = False
    return {
        "command": command,
        "status": "passed" if code == 0 else "failed",
        "exit_code": code,
        "timed_out": timed_out,
        "duration_seconds": round(time.monotonic() - started, 2),
        "log": str(log),
    }


def check(root: Path, allow_make_guards: bool = False) -> dict:
    paths = changed_paths(root)
    classification = classify(paths, allow_make_guards=allow_make_guards)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_dir = root / ".runtime" / "tooling-maintenance" / stamp
    results: list[dict] = []
    if not classification["ok"]:
        return {
            "schema": "tooling_maintenance.check.v1",
            "status": "blocked",
            "paths": paths,
            "classification": classification,
            "results": results,
        }

    python_files = [path for path in paths if path.endswith(".py")]
    if python_files:
        results.append(run_command([sys.executable, "-m", "py_compile", *python_files], root, log_dir / "py_compile.log"))

    test_files = [
        path for path in paths
        if path.startswith(("scripts/verify/test_", "scripts/ops/test_")) and path.endswith(".py")
    ]
    for path in test_files:
        results.append(
            run_command(
                [sys.executable, "-m", "unittest", module_name(path)],
                root,
                log_dir / f"test-{Path(path).stem}.log",
                300,
            )
        )

    if any(path.startswith("docs/") for path in paths):
        results.append(run_command(["make", "verify.docs.all"], root, log_dir / "docs.log", 600))

    if "make/guards.mk" in paths or any(path.startswith("scripts/verify/") for path in paths):
        results.append(
            run_command(
                ["make", "verify.environment.topology.guard"],
                root,
                log_dir / "environment-topology.log",
                600,
            )
        )

    results.append(run_command(["git", "diff", "--check"], root, log_dir / "diff-check.log", 60))
    failed = [row for row in results if row["status"] != "passed"]
    return {
        "schema": "tooling_maintenance.check.v1",
        "status": "passed" if not failed else "failed",
        "head": git(root, "rev-parse", "HEAD").stdout.strip(),
        "paths": paths,
        "classification": classification,
        "results": results,
        "failed": [row["command"] for row in failed],
    }


def publish(root: Path, expected_head: str, allow_make_guards: bool = False) -> dict:
    report = check(root, allow_make_guards=allow_make_guards)
    if report["status"] != "passed":
        return {"status": "blocked", "reason": "fast_check_failed", "check": report}
    branch = git(root, "branch", "--show-current").stdout.strip()
    head = git(root, "rev-parse", "HEAD").stdout.strip()
    status = git(root, "status", "--porcelain").stdout.strip()
    if branch != DEFAULT_BRANCH:
        return {"status": "blocked", "reason": f"branch_must_be_{DEFAULT_BRANCH}", "branch": branch}
    if head != expected_head:
        return {"status": "blocked", "reason": "expected_head_mismatch", "head": head}
    if status:
        return {"status": "blocked", "reason": "worktree_not_clean", "status": status}

    fetch = git(root, "fetch", "origin", DEFAULT_BRANCH)
    if fetch.returncode != 0:
        return {"status": "blocked", "reason": "origin_fetch_failed", "detail": fetch.stderr.strip()}
    origin_main = git(root, "rev-parse", f"origin/{DEFAULT_BRANCH}").stdout.strip()
    parent = git(root, "rev-parse", "HEAD^").stdout.strip()
    if parent != origin_main:
        return {
            "status": "blocked",
            "reason": "maintenance_commit_must_be_exactly_one_commit_ahead_of_origin_main",
            "parent": parent,
            "origin_main": origin_main,
        }

    push = git(root, "push", "origin", f"HEAD:{DEFAULT_BRANCH}")
    if push.returncode != 0:
        return {
            "status": "blocked",
            "reason": "direct_main_push_rejected",
            "detail": push.stderr.strip()[-2000:],
            "fallback": "create a governed fix/* branch and PR; do not force push main",
        }
    remote = git(root, "ls-remote", "--heads", "origin", DEFAULT_BRANCH).stdout.strip().split()
    remote_head = remote[0] if remote else ""
    return {
        "status": "passed" if remote_head == head else "failed_remote_readback",
        "head": head,
        "origin_main": remote_head,
        "check": report,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT))
    sub = parser.add_subparsers(dest="command", required=True)
    classify_parser = sub.add_parser("classify")
    classify_parser.add_argument("--allow-make-guards", action="store_true")
    check_parser = sub.add_parser("check")
    check_parser.add_argument("--allow-make-guards", action="store_true")
    publish_parser = sub.add_parser("publish")
    publish_parser.add_argument("--expected-head", required=True)
    publish_parser.add_argument("--allow-make-guards", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()

    if args.command == "classify":
        payload = classify(changed_paths(root), allow_make_guards=args.allow_make_guards)
    elif args.command == "check":
        payload = check(root, allow_make_guards=args.allow_make_guards)
    else:
        payload = publish(root, args.expected_head, allow_make_guards=args.allow_make_guards)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("status") in {"passed", "ok"} or payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
