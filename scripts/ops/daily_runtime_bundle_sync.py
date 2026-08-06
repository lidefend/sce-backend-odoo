#!/usr/bin/env python3
"""Fast-forward the daily runtime repository from an exact verified Git bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
SSH_HOST = re.compile(r"^[A-Za-z0-9._-]+$")
ALLOWED_LOCAL_BRANCH = re.compile(r"^(main|(feature|fix|refactor|audit|release|codex)/.+)$")
REMOTE_ROOT = "/opt/projects/repos/sce-product-odoo"
BUNDLE_MAIN_REF = "refs/remotes/origin/main"
CONFIRMATION = "SYNC_EXACT_DAILY_MAIN_SHA_WITH_BUNDLE"
MAX_BUNDLE_BYTES = 128 * 1024 * 1024


class SyncError(RuntimeError):
    pass


REMOTE_SYNC = r'''
import fcntl, hashlib, json, os, subprocess, sys, tempfile
from pathlib import Path

expected_sha, expected_old_sha, expected_bundle_sha, remote_root = sys.argv[1:5]
fixed_root = Path("/opt/projects/repos/sce-product-odoo")
root = Path(remote_root)
if root != fixed_root or not root.is_dir():
    raise SystemExit("[daily.runtime.main.bundle_sync] BLOCKED invalid remote repository")

lock_path = Path("/run/lock/sc_daily-runtime-bundle-sync.lock")
lock_path.parent.mkdir(parents=True, exist_ok=True)

def git(*args, check=True):
    result = subprocess.run(
        ["git", *args], cwd=root, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
    )
    if check and result.returncode:
        raise SystemExit("[daily.runtime.main.bundle_sync] BLOCKED git " + args[0] + ": " + result.stderr.strip()[:600])
    return result

with lock_path.open("a+b") as lock:
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit("[daily.runtime.main.bundle_sync] BLOCKED concurrent sync")

    branch = git("branch", "--show-current").stdout.strip()
    current_sha = git("rev-parse", "HEAD").stdout.strip()
    upstream_name = git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}").stdout.strip()
    upstream_sha = git("rev-parse", "@{upstream}").stdout.strip()
    if branch != "main" or current_sha != expected_old_sha:
        raise SystemExit("[daily.runtime.main.bundle_sync] BLOCKED remote branch or old SHA differs")
    if upstream_name != "origin/main" or upstream_sha != expected_old_sha:
        raise SystemExit("[daily.runtime.main.bundle_sync] BLOCKED remote upstream identity differs")
    if git("status", "--porcelain").stdout.strip():
        raise SystemExit("[daily.runtime.main.bundle_sync] BLOCKED remote worktree is not clean")

    bundle_path = None
    try:
        with tempfile.NamedTemporaryFile(prefix="sc-daily-main-", suffix=".bundle", dir="/tmp", delete=False) as bundle:
            bundle_path = Path(bundle.name)
            digest = hashlib.sha256()
            size = 0
            while True:
                chunk = sys.stdin.buffer.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > 128 * 1024 * 1024:
                    raise SystemExit("[daily.runtime.main.bundle_sync] BLOCKED bundle exceeds size limit")
                digest.update(chunk)
                bundle.write(chunk)
        bundle_path.chmod(0o600)
        if not size or digest.hexdigest() != expected_bundle_sha:
            raise SystemExit("[daily.runtime.main.bundle_sync] BLOCKED bundle digest differs")

        git("bundle", "verify", str(bundle_path))
        heads = git("bundle", "list-heads", str(bundle_path), "refs/remotes/origin/main").stdout.split()
        if len(heads) != 2 or heads[0] != expected_sha or heads[1] != "refs/remotes/origin/main":
            raise SystemExit("[daily.runtime.main.bundle_sync] BLOCKED bundle main identity differs")

        git("fetch", str(bundle_path), "refs/remotes/origin/main")
        if git("rev-parse", "FETCH_HEAD").stdout.strip() != expected_sha:
            raise SystemExit("[daily.runtime.main.bundle_sync] BLOCKED fetched bundle SHA differs")
        if git("merge-base", "--is-ancestor", expected_old_sha, expected_sha, check=False).returncode:
            raise SystemExit("[daily.runtime.main.bundle_sync] BLOCKED candidate is not a fast-forward descendant")

        git("pull", "--ff-only", str(bundle_path), "refs/remotes/origin/main")
        if git("rev-parse", "HEAD").stdout.strip() != expected_sha:
            raise SystemExit("[daily.runtime.main.bundle_sync] BLOCKED post-sync HEAD differs")
        git("update-ref", "refs/remotes/origin/main", expected_sha, expected_old_sha)
        if git("rev-parse", "@{upstream}").stdout.strip() != expected_sha:
            raise SystemExit("[daily.runtime.main.bundle_sync] BLOCKED post-sync upstream differs")
        if git("status", "--porcelain").stdout.strip():
            raise SystemExit("[daily.runtime.main.bundle_sync] BLOCKED post-sync worktree is not clean")

        print(json.dumps({
            "status": "PASS",
            "changed": expected_sha != expected_old_sha,
            "old_sha": expected_old_sha,
            "source_sha": expected_sha,
            "bundle_sha256": expected_bundle_sha,
            "remote_root": str(root),
            "upstream": "origin/main",
        }, sort_keys=True))
    finally:
        if bundle_path is not None:
            bundle_path.unlink(missing_ok=True)
'''


def run(command: list[str], *, cwd: Path = ROOT, input_bytes: bytes | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        command,
        cwd=cwd,
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def git(*arguments: str) -> str:
    result = run(["git", *arguments])
    if result.returncode:
        raise SyncError(f"git {arguments[0]} failed: {result.stderr.decode(errors='replace').strip()[:600]}")
    return result.stdout.decode().strip()


def preflight(expected_sha: str, expected_old_sha: str, ssh_host: str) -> None:
    if not FULL_SHA.fullmatch(expected_sha) or not FULL_SHA.fullmatch(expected_old_sha):
        raise SyncError("expected SHAs must be full lowercase commit identities")
    if expected_sha == expected_old_sha:
        raise SyncError("expected SHA must differ from the remote old SHA")
    if not SSH_HOST.fullmatch(ssh_host):
        raise SyncError("SSH host must be a configured host alias")
    if os.environ.get("CONFIRM_DAILY_RUNTIME_BUNDLE_SYNC") != CONFIRMATION:
        raise SyncError("exact daily runtime bundle synchronization confirmation is required")
    branch = git("branch", "--show-current")
    if not ALLOWED_LOCAL_BRANCH.fullmatch(branch) or git("rev-parse", "HEAD") != expected_sha:
        raise SyncError("bundle sync must run from the exact approved SHA on a governed branch")
    if git("status", "--porcelain"):
        raise SyncError("local main worktree must be clean")
    if git("rev-parse", "refs/remotes/origin/main") != expected_sha:
        raise SyncError("local origin/main does not match the approved SHA")
    if run(["git", "merge-base", "--is-ancestor", expected_old_sha, expected_sha]).returncode:
        raise SyncError("remote old SHA is not an ancestor of the approved SHA")


def create_bundle(expected_old_sha: str) -> bytes:
    with tempfile.TemporaryDirectory(prefix="sc-daily-bundle-") as directory:
        bundle_path = Path(directory) / "main.bundle"
        result = run(
            ["git", "bundle", "create", str(bundle_path), BUNDLE_MAIN_REF, f"^{expected_old_sha}"],
        )
        if result.returncode:
            raise SyncError(f"git bundle create failed: {result.stderr.decode(errors='replace').strip()[:600]}")
        payload = bundle_path.read_bytes()
    if not payload or len(payload) > MAX_BUNDLE_BYTES:
        raise SyncError("bundle is empty or exceeds the size limit")
    return payload


def synchronize(expected_sha: str, expected_old_sha: str, ssh_host: str) -> dict[str, object]:
    preflight(expected_sha, expected_old_sha, ssh_host)
    bundle = create_bundle(expected_old_sha)
    bundle_sha = hashlib.sha256(bundle).hexdigest()
    command = [
        "ssh",
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=10",
        "-o", "ServerAliveInterval=15",
        "-o", "ServerAliveCountMax=4",
        ssh_host,
        "python3", "-c", REMOTE_SYNC,
        expected_sha, expected_old_sha, bundle_sha, REMOTE_ROOT,
    ]
    result = run(command, input_bytes=bundle)
    if result.returncode:
        message = result.stderr.decode(errors="replace").strip() or result.stdout.decode(errors="replace").strip()
        raise SyncError(f"remote bundle sync failed: {message[:1000]}")
    try:
        evidence = json.loads(result.stdout.decode().splitlines()[-1])
    except (IndexError, json.JSONDecodeError) as exc:
        raise SyncError("remote bundle sync evidence is invalid") from exc
    if (
        evidence.get("status") != "PASS"
        or evidence.get("source_sha") != expected_sha
        or evidence.get("old_sha") != expected_old_sha
        or evidence.get("bundle_sha256") != bundle_sha
        or evidence.get("remote_root") != REMOTE_ROOT
    ):
        raise SyncError("remote bundle sync evidence differs")
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--expected-old-sha", required=True)
    parser.add_argument("--ssh-host", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    try:
        evidence = synchronize(args.expected_sha, args.expected_old_sha, args.ssh_host)
    except SyncError as exc:
        raise SystemExit(f"[daily.runtime.main.bundle_sync] BLOCKED: {exc}") from exc
    report = Path(args.report)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("[daily.runtime.main.bundle_sync] PASS " + json.dumps(evidence, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
