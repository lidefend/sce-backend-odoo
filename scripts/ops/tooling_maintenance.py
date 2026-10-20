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
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BRANCH = "main"
GITHUB_REPOSITORY = "lidefend/sce-backend-odoo"
RULESET_NAME = "main-github-authoritative-pr"

ALLOWED_PREFIXES = (
    "docs/",
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


def ruleset_payload_with_bypass(ruleset: dict, actor_id: int = 0) -> dict:
    payload = {
        "name": ruleset["name"],
        "target": ruleset["target"],
        "enforcement": ruleset["enforcement"],
        "conditions": ruleset["conditions"],
        "rules": ruleset["rules"],
        "bypass_actors": [],
    }
    if actor_id:
        payload["bypass_actors"] = [
            {
                "actor_id": actor_id,
                "actor_type": "User",
                "bypass_mode": "always",
            }
        ]
    return payload


def _gh_api(*args: str) -> object:
    result = subprocess.run(
        ["gh", "api", *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or f"gh api failed: {' '.join(args)}")
    return json.loads(result.stdout) if result.stdout.strip() else None


def set_owner_bypass(enabled: bool) -> dict:
    rulesets = _gh_api(f"repos/{GITHUB_REPOSITORY}/rulesets")
    matches = [row for row in rulesets if row.get("name") == RULESET_NAME]
    if len(matches) != 1:
        raise RuntimeError("main ruleset is not unique")
    ruleset_id = int(matches[0]["id"])
    ruleset = _gh_api(f"repos/{GITHUB_REPOSITORY}/rulesets/{ruleset_id}")
    owner_id = int(_gh_api("user")["id"]) if enabled else 0
    payload = ruleset_payload_with_bypass(ruleset, owner_id)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json") as handle:
        json.dump(payload, handle)
        handle.flush()
        result = subprocess.run(
            ["gh", "api", "--method", "PUT", f"repos/{GITHUB_REPOSITORY}/rulesets/{ruleset_id}", "--input", handle.name],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "ruleset update failed")
    readback = _gh_api(f"repos/{GITHUB_REPOSITORY}/rulesets/{ruleset_id}")
    if readback.get("bypass_actors") != payload["bypass_actors"]:
        raise RuntimeError("ruleset bypass readback mismatch")
    return {"ruleset_id": ruleset_id, "bypass_actors": payload["bypass_actors"]}


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


def publish(
    root: Path,
    expected_head: str,
    allow_make_guards: bool = False,
    owner_bypass_window: bool = False,
) -> dict:
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

    bypass = {"enabled": False, "removed": False}
    push = None
    try:
        if owner_bypass_window:
            set_owner_bypass(True)
            bypass["enabled"] = True
        push = git(root, "push", "origin", f"HEAD:{DEFAULT_BRANCH}")
    finally:
        if bypass["enabled"]:
            try:
                set_owner_bypass(False)
                bypass["removed"] = True
            except Exception as exc:
                bypass["error"] = str(exc)
    if push is None:
        return {"status": "blocked", "reason": "push_not_attempted", "bypass": bypass}
    if push.returncode != 0:
        return {
            "status": "blocked",
            "reason": "direct_main_push_rejected",
            "detail": push.stderr.strip()[-2000:],
            "bypass": bypass,
            "fallback": "create a governed fix/* branch and PR; do not force push main",
        }
    if bypass["enabled"] and not bypass["removed"]:
        return {
            "status": "failed_bypass_cleanup",
            "head": head,
            "bypass": bypass,
            "detail": "main push succeeded but temporary owner bypass cleanup failed",
        }
    remote = git(root, "ls-remote", "--heads", "origin", DEFAULT_BRANCH).stdout.strip().split()
    remote_head = remote[0] if remote else ""
    return {
        "status": "passed" if remote_head == head else "failed_remote_readback",
        "head": head,
        "origin_main": remote_head,
        "bypass": bypass,
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
    publish_parser.add_argument("--owner-bypass-window", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()

    if args.command == "classify":
        payload = classify(changed_paths(root), allow_make_guards=args.allow_make_guards)
    elif args.command == "check":
        payload = check(root, allow_make_guards=args.allow_make_guards)
    else:
        payload = publish(
            root,
            args.expected_head,
            allow_make_guards=args.allow_make_guards,
            owner_bypass_window=args.owner_bypass_window,
        )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("status") in {"passed", "ok"} or payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
