#!/usr/bin/env python3
"""Install one immutable main revision as production deployment tooling."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SSH_TARGET = "sc-prod"
CONFIRMATION = "YES_SYNC_IMMUTABLE_DEPLOYMENT_TOOLING"
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")


class SyncError(RuntimeError):
    pass


REMOTE_INSTALL = r'''
import fcntl, json, os, shutil, stat, sys, tarfile, tempfile
from pathlib import Path, PurePosixPath

source_sha = sys.argv[1]
root = Path("/opt/sce/deployment-tools")
target = root / source_sha
lock_path = Path("/run/lock/sc_production-deployment-tool-sync.lock")
root.mkdir(parents=True, exist_ok=True, mode=0o755)
lock_path.parent.mkdir(parents=True, exist_ok=True)
with lock_path.open("a+b") as lock:
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit("[production.deployment.tool.sync] BLOCKED concurrent sync")
    marker = target / "DEPLOYMENT_TOOL_SHA"
    if target.exists() or target.is_symlink():
        if target.is_symlink() or not target.is_dir() or not marker.is_file() or marker.read_text() != source_sha + "\n":
            raise SystemExit("[production.deployment.tool.sync] BLOCKED immutable target differs")
        print(json.dumps({"status":"PASS","changed":False,"target":str(target),"source_sha":source_sha}))
        raise SystemExit(0)
    staging = Path(tempfile.mkdtemp(prefix=".incomplete-" + source_sha[:12] + "-", dir=root))
    try:
        with tarfile.open(fileobj=sys.stdin.buffer, mode="r|") as archive:
            for member in archive:
                path = PurePosixPath(member.name)
                if path.is_absolute() or ".." in path.parts or member.issym() or member.islnk() or not (member.isdir() or member.isfile()):
                    raise SystemExit("[production.deployment.tool.sync] BLOCKED archive member is unsafe")
                destination = staging.joinpath(*path.parts)
                if member.isdir():
                    destination.mkdir(parents=True, exist_ok=True)
                    destination.chmod(member.mode & 0o755)
                    continue
                destination.parent.mkdir(parents=True, exist_ok=True)
                stream = archive.extractfile(member)
                if stream is None:
                    raise SystemExit("[production.deployment.tool.sync] BLOCKED archive member unavailable")
                with destination.open("wb") as output:
                    shutil.copyfileobj(stream, output)
                destination.chmod(member.mode & 0o755)
        marker = staging / "DEPLOYMENT_TOOL_SHA"
        marker.write_text(source_sha + "\n")
        marker.chmod(0o444)
        os.replace(staging, target)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    print(json.dumps({"status":"PASS","changed":True,"target":str(target),"source_sha":source_sha}))
'''


def run(command: list[str]) -> str:
    completed = subprocess.run(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, text=True)
    if completed.returncode:
        raise SyncError(f"command failed ({command[0]}): {completed.stderr.strip()[:600]}")
    return completed.stdout.strip()


def git(*arguments: str) -> str:
    return run(["git", *arguments])


def preflight(expected_sha: str) -> None:
    if not FULL_SHA.fullmatch(expected_sha):
        raise SyncError("expected live main SHA must be a full lowercase SHA")
    if git("rev-parse", "HEAD") != expected_sha or git("branch", "--show-current") != "main":
        raise SyncError("sync must run from the approved main SHA")
    if git("status", "--porcelain"):
        raise SyncError("sync worktree must be clean")
    for remote in ("origin", "gitee-mirror"):
        lines = git("ls-remote", remote, "refs/heads/main").splitlines()
        if len(lines) != 1 or lines[0].split()[0] != expected_sha:
            raise SyncError(f"{remote} main identity differs")


def synchronize(expected_sha: str) -> dict:
    if os.environ.get("ENV") != "prod" or os.environ.get("PROD_DANGER") != "1":
        raise SyncError("ENV=prod and PROD_DANGER=1 are required")
    if os.environ.get("CONFIRM_PRODUCTION_DEPLOYMENT_TOOL_SYNC") != CONFIRMATION:
        raise SyncError("exact deployment tooling synchronization confirmation is required")
    preflight(expected_sha)
    remote = " ".join(shlex.quote(item) for item in ("python3", "-c", REMOTE_INSTALL, expected_sha))
    archive = subprocess.Popen(["git", "archive", "--format=tar", expected_sha], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert archive.stdout is not None
    ssh = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", SSH_TARGET, remote], cwd=ROOT,
        stdin=archive.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    archive.stdout.close()
    archive_error = archive.stderr.read().decode(errors="replace") if archive.stderr else ""
    archive_code = archive.wait()
    if archive_code:
        raise SyncError(f"git archive failed: {archive_error.strip()[:600]}")
    if ssh.returncode:
        raise SyncError(f"remote tool sync failed: {ssh.stderr.decode(errors='replace').strip()[:600]}")
    try:
        result = json.loads(ssh.stdout.decode().splitlines()[-1])
    except (IndexError, json.JSONDecodeError) as exc:
        raise SyncError("remote tool synchronization evidence is invalid") from exc
    if result.get("status") != "PASS" or result.get("source_sha") != expected_sha:
        raise SyncError("remote tool synchronization evidence differs")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-live-main-sha", required=True)
    args = parser.parse_args()
    try:
        result = synchronize(args.expected_live_main_sha)
    except SyncError as exc:
        raise SystemExit(f"[production.deployment.tool.sync] BLOCKED: {exc}") from exc
    print("[production.deployment.tool.sync] PASS " + json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
