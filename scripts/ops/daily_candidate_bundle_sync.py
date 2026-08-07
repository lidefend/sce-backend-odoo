#!/usr/bin/env python3
"""Deploy an exact governed branch commit to daily dev through a verified bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
SSH_HOST = re.compile(r"^[A-Za-z0-9._-]+$")
ALLOWED_BRANCH = re.compile(r"^(feature|fix|refactor|audit|release|codex)/.+$")
REMOTE_ROOT = "/opt/projects/repos/sce-product-odoo"
CONFIRMATION = "SYNC_EXACT_DAILY_CANDIDATE_SHA_WITH_BUNDLE"
MAX_BUNDLE_BYTES = 128 * 1024 * 1024


class SyncError(RuntimeError):
    pass


REMOTE_SYNC = r'''
import fcntl, hashlib, json, os, re, subprocess, sys, tempfile
from pathlib import Path

expected_sha, expected_old_sha, expected_bundle_sha, source_branch, bundle_base_sha, remote_root = sys.argv[1:7]
fixed_root = Path("/opt/projects/repos/sce-product-odoo")
root = Path(remote_root)
full_sha = re.compile(r"^[0-9a-f]{40}$")
allowed_branch = re.compile(r"^(feature|fix|refactor|audit|release|codex)/.+$")
if root != fixed_root or not root.is_dir():
    raise SystemExit("[daily.runtime.candidate.bundle_sync] BLOCKED invalid remote repository")
if not full_sha.fullmatch(expected_sha) or not full_sha.fullmatch(expected_old_sha) or not full_sha.fullmatch(bundle_base_sha):
    raise SystemExit("[daily.runtime.candidate.bundle_sync] BLOCKED invalid commit identity")
if not allowed_branch.fullmatch(source_branch):
    raise SystemExit("[daily.runtime.candidate.bundle_sync] BLOCKED invalid source branch")

lock_path = Path("/run/lock/sc_daily-runtime-bundle-sync.lock")
lock_path.parent.mkdir(parents=True, exist_ok=True)

def git(*args, check=True):
    result = subprocess.run(
        ["git", *args], cwd=root, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
    )
    if check and result.returncode:
        raise SystemExit("[daily.runtime.candidate.bundle_sync] BLOCKED git " + args[0] + ": " + result.stderr.strip()[:600])
    return result

with lock_path.open("a+b") as lock:
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit("[daily.runtime.candidate.bundle_sync] BLOCKED concurrent sync")

    previous_branch = git("branch", "--show-current").stdout.strip()
    current_sha = git("rev-parse", "HEAD").stdout.strip()
    if current_sha != expected_old_sha:
        raise SystemExit("[daily.runtime.candidate.bundle_sync] BLOCKED remote old SHA differs")
    if git("status", "--porcelain").stdout.strip():
        raise SystemExit("[daily.runtime.candidate.bundle_sync] BLOCKED remote worktree is not clean")
    if git("cat-file", "-e", bundle_base_sha + "^{commit}", check=False).returncode:
        raise SystemExit("[daily.runtime.candidate.bundle_sync] BLOCKED remote lacks bundle base commit")

    bundle_path = None
    try:
        with tempfile.NamedTemporaryFile(prefix="sc-daily-candidate-", suffix=".bundle", dir="/tmp", delete=False) as bundle:
            bundle_path = Path(bundle.name)
            digest = hashlib.sha256()
            size = 0
            while True:
                chunk = sys.stdin.buffer.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > 128 * 1024 * 1024:
                    raise SystemExit("[daily.runtime.candidate.bundle_sync] BLOCKED bundle exceeds size limit")
                digest.update(chunk)
                bundle.write(chunk)
        bundle_path.chmod(0o600)
        if not size or digest.hexdigest() != expected_bundle_sha:
            raise SystemExit("[daily.runtime.candidate.bundle_sync] BLOCKED bundle digest differs")

        git("bundle", "verify", str(bundle_path))
        source_ref = "refs/heads/" + source_branch
        heads = git("bundle", "list-heads", str(bundle_path), source_ref).stdout.split()
        if len(heads) != 2 or heads[0] != expected_sha or heads[1] != source_ref:
            raise SystemExit("[daily.runtime.candidate.bundle_sync] BLOCKED bundle candidate identity differs")

        evidence_ref = "refs/daily-candidates/" + source_branch
        git("fetch", str(bundle_path), "+" + source_ref + ":" + evidence_ref)
        if git("rev-parse", evidence_ref).stdout.strip() != expected_sha:
            raise SystemExit("[daily.runtime.candidate.bundle_sync] BLOCKED fetched candidate SHA differs")
        git("checkout", "--detach", expected_sha)
        if git("rev-parse", "HEAD").stdout.strip() != expected_sha:
            raise SystemExit("[daily.runtime.candidate.bundle_sync] BLOCKED post-sync HEAD differs")
        if git("branch", "--show-current").stdout.strip():
            raise SystemExit("[daily.runtime.candidate.bundle_sync] BLOCKED candidate runtime is not detached")
        if git("status", "--porcelain").stdout.strip():
            raise SystemExit("[daily.runtime.candidate.bundle_sync] BLOCKED post-sync worktree is not clean")

        print(json.dumps({
            "status": "PASS",
            "deployment_mode": "candidate",
            "old_sha": expected_old_sha,
            "source_branch": source_branch,
            "source_sha": expected_sha,
            "bundle_base_sha": bundle_base_sha,
            "bundle_sha256": expected_bundle_sha,
            "remote_root": str(root),
            "previous_branch": previous_branch or "detached",
            "runtime_branch": "detached",
            "evidence_ref": evidence_ref,
            "origin_main_mutated": False,
        }, sort_keys=True))
    finally:
        if bundle_path is not None:
            bundle_path.unlink(missing_ok=True)
'''


def run(
    command: list[str], *, cwd: Path = ROOT, input_bytes: bytes | None = None
) -> subprocess.CompletedProcess[bytes]:
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
        raise SyncError(
            f"git {arguments[0]} failed: "
            f"{result.stderr.decode(errors='replace').strip()[:600]}"
        )
    return result.stdout.decode().strip()


def preflight(source_branch: str, expected_sha: str, expected_old_sha: str, ssh_host: str) -> None:
    if not ALLOWED_BRANCH.fullmatch(source_branch):
        raise SyncError("source branch must be a governed development branch")
    if not FULL_SHA.fullmatch(expected_sha) or not FULL_SHA.fullmatch(expected_old_sha):
        raise SyncError("expected SHAs must be full lowercase commit identities")
    if expected_sha == expected_old_sha:
        raise SyncError("candidate SHA must differ from the daily runtime SHA")
    if not SSH_HOST.fullmatch(ssh_host):
        raise SyncError("SSH host must be a configured host alias")
    if os.environ.get("CONFIRM_DAILY_CANDIDATE_BUNDLE_SYNC") != CONFIRMATION:
        raise SyncError("exact daily candidate bundle synchronization confirmation is required")
    if git("branch", "--show-current") != source_branch:
        raise SyncError("source branch differs from the current governed branch")
    if git("rev-parse", "HEAD") != expected_sha:
        raise SyncError("local HEAD differs from the approved candidate SHA")
    if git("status", "--porcelain"):
        raise SyncError("local candidate worktree must be clean")
    check_ref = run(["git", "check-ref-format", f"refs/heads/{source_branch}"])
    if check_ref.returncode:
        raise SyncError("source branch is not a valid Git ref")


def create_bundle(source_branch: str, expected_old_sha: str) -> tuple[bytes, str]:
    bundle_base_sha = git("merge-base", expected_old_sha, "HEAD")
    if not FULL_SHA.fullmatch(bundle_base_sha):
        raise SyncError("candidate and daily runtime have no valid merge base")
    with tempfile.TemporaryDirectory(prefix="sc-daily-candidate-bundle-") as directory:
        bundle_path = Path(directory) / "candidate.bundle"
        result = run(
            [
                "git",
                "bundle",
                "create",
                str(bundle_path),
                f"refs/heads/{source_branch}",
                f"^{bundle_base_sha}",
            ]
        )
        if result.returncode:
            raise SyncError(
                "git bundle create failed: "
                + result.stderr.decode(errors="replace").strip()[:600]
            )
        payload = bundle_path.read_bytes()
    if not payload or len(payload) > MAX_BUNDLE_BYTES:
        raise SyncError("bundle is empty or exceeds the size limit")
    return payload, bundle_base_sha


def remote_command(
    expected_sha: str,
    expected_old_sha: str,
    bundle_sha: str,
    source_branch: str,
    bundle_base_sha: str,
) -> str:
    return " ".join(
        shlex.quote(item)
        for item in (
            "python3",
            "-c",
            REMOTE_SYNC,
            expected_sha,
            expected_old_sha,
            bundle_sha,
            source_branch,
            bundle_base_sha,
            REMOTE_ROOT,
        )
    )


def synchronize(
    source_branch: str, expected_sha: str, expected_old_sha: str, ssh_host: str
) -> dict[str, object]:
    preflight(source_branch, expected_sha, expected_old_sha, ssh_host)
    bundle, bundle_base_sha = create_bundle(source_branch, expected_old_sha)
    bundle_sha = hashlib.sha256(bundle).hexdigest()
    command = [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=10",
        "-o",
        "ServerAliveInterval=15",
        "-o",
        "ServerAliveCountMax=4",
        ssh_host,
        remote_command(
            expected_sha,
            expected_old_sha,
            bundle_sha,
            source_branch,
            bundle_base_sha,
        ),
    ]
    result = run(command, input_bytes=bundle)
    if result.returncode:
        message = (
            result.stderr.decode(errors="replace").strip()
            or result.stdout.decode(errors="replace").strip()
        )
        raise SyncError(f"remote candidate bundle sync failed: {message[:1000]}")
    try:
        evidence = json.loads(result.stdout.decode().splitlines()[-1])
    except (IndexError, json.JSONDecodeError) as exc:
        raise SyncError("remote candidate bundle sync evidence is invalid") from exc
    if (
        evidence.get("status") != "PASS"
        or evidence.get("deployment_mode") != "candidate"
        or evidence.get("source_branch") != source_branch
        or evidence.get("source_sha") != expected_sha
        or evidence.get("old_sha") != expected_old_sha
        or evidence.get("bundle_base_sha") != bundle_base_sha
        or evidence.get("bundle_sha256") != bundle_sha
        or evidence.get("remote_root") != REMOTE_ROOT
        or evidence.get("runtime_branch") != "detached"
        or evidence.get("origin_main_mutated") is not False
    ):
        raise SyncError("remote candidate bundle sync evidence differs")
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-branch", required=True)
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--expected-old-sha", required=True)
    parser.add_argument("--ssh-host", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    try:
        evidence = synchronize(
            args.source_branch,
            args.expected_sha,
            args.expected_old_sha,
            args.ssh_host,
        )
    except SyncError as exc:
        raise SystemExit(f"[daily.runtime.candidate.bundle_sync] BLOCKED: {exc}") from exc
    report = Path(args.report)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print("[daily.runtime.candidate.bundle_sync] PASS " + json.dumps(evidence, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
