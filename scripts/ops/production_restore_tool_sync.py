#!/usr/bin/env python3
"""Atomically synchronize the governed restore tool to sc-prod."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "scripts/release/production_backup_restore.py"
TARGET = "/opt/ops/production_backup_restore.py"
SSH_TARGET = "sc-prod"
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
CHECKSUM = re.compile(r"^[0-9a-f]{64}$")
CONFIRMATION = "YES_SYNC_GOVERNED_RESTORE_TOOL"


class SyncError(RuntimeError):
    pass


REMOTE_INSTALL = r'''
import fcntl, hashlib, json, os, secrets, shutil, stat, sys, tempfile
from datetime import datetime, timezone
from pathlib import Path

expected, source_sha = sys.argv[1:]
target = Path("/opt/ops/production_backup_restore.py")
history_root = Path("/opt/ops/backup-install-history")
lock_path = Path("/run/lock/sc_production-restore-tool-sync.lock")
payload = sys.stdin.buffer.read()
actual = hashlib.sha256(payload).hexdigest()
if actual != expected or len(payload) < 1024:
    raise SystemExit("[production.restore-tool.sync] BLOCKED payload identity mismatch")
if b'"--user"' not in payload or b'"0:0"' not in payload:
    raise SystemExit("[production.restore-tool.sync] BLOCKED permission fix missing")
lock_path.parent.mkdir(parents=True, exist_ok=True)
with lock_path.open("a+b") as lock:
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit("[production.restore-tool.sync] BLOCKED concurrent sync")
    if target.is_symlink() or not target.is_file():
        raise SystemExit("[production.restore-tool.sync] BLOCKED target is unsafe")
    meta = target.stat()
    if meta.st_uid != 0 or meta.st_gid != 0 or stat.S_IMODE(meta.st_mode) != 0o755:
        raise SystemExit("[production.restore-tool.sync] BLOCKED target ownership or mode")
    before = hashlib.sha256(target.read_bytes()).hexdigest()
    if before == expected:
        print(json.dumps({"status":"PASS","changed":False,"sha256":expected,"target":str(target)}))
        raise SystemExit(0)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    history = history_root / f"{stamp}-{source_sha[:12]}-{secrets.token_hex(4)}-restore-tool-sync"
    history.mkdir(parents=True, mode=0o700)
    previous = history / "production_backup_restore.py.previous"
    shutil.copy2(target, previous)
    os.chown(previous, 0, 0)
    previous.chmod(0o600)
    manifest = history / "rollback-manifest.json"
    manifest.write_text(json.dumps({
        "schema_version": 1,
        "status": "prepared",
        "source_sha": source_sha,
        "target": str(target),
        "before_sha256": before,
        "after_sha256": expected,
        "backup_path": str(previous),
    }, indent=2, sort_keys=True) + "\n")
    os.chown(manifest, 0, 0)
    manifest.chmod(0o600)
    descriptor, temporary = tempfile.mkstemp(prefix=".production_backup_restore.py.", dir=target.parent)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.chown(temporary_path, 0, 0)
        temporary_path.chmod(0o755)
        os.replace(temporary_path, target)
    finally:
        temporary_path.unlink(missing_ok=True)
    installed = hashlib.sha256(target.read_bytes()).hexdigest()
    if installed != expected:
        shutil.copy2(previous, target)
        os.chown(target, 0, 0)
        target.chmod(0o755)
        raise SystemExit("[production.restore-tool.sync] BLOCKED post-install digest mismatch")
    data = json.loads(manifest.read_text())
    data["status"] = "installed"
    manifest.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    os.chown(manifest, 0, 0)
    manifest.chmod(0o600)
    print(json.dumps({"status":"PASS","changed":True,"sha256":installed,
                      "target":str(target),"rollback_manifest":str(manifest)}))
'''


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_source(path: Path = SOURCE) -> str:
    if path.is_symlink() or not path.is_file():
        raise SyncError("restore tool source is missing or unsafe")
    payload = path.read_bytes()
    if b'"--user"' not in payload or b'"0:0"' not in payload:
        raise SyncError("restore tool source lacks the isolated root extraction fix")
    return hashlib.sha256(payload).hexdigest()


def run(command: list[str], *, input_bytes: bytes | None = None) -> str:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode:
        detail = completed.stderr.decode(errors="replace").strip()[:600]
        raise SyncError(f"command failed ({command[0]}): {detail}")
    return completed.stdout.decode().strip()


def git(*arguments: str) -> str:
    return run(["git", *arguments])


def preflight(expected_sha: str) -> dict[str, str]:
    if not FULL_SHA.fullmatch(expected_sha):
        raise SyncError("EXPECTED_LIVE_MAIN_SHA must be a full SHA")
    head = git("rev-parse", "HEAD")
    if head != expected_sha or git("branch", "--show-current") != "main":
        raise SyncError("sync must run from the approved main SHA")
    if git("status", "--porcelain"):
        raise SyncError("sync worktree must be clean")
    remotes = {}
    for name in ("origin", "gitee-mirror"):
        lines = git("ls-remote", name, "refs/heads/main").splitlines()
        if len(lines) != 1 or lines[0].split()[0] != expected_sha:
            raise SyncError(f"{name} main identity differs")
        remotes[name] = expected_sha
    return remotes


def remote_command(digest: str, expected_sha: str) -> str:
    if not CHECKSUM.fullmatch(digest) or not FULL_SHA.fullmatch(expected_sha):
        raise SyncError("remote synchronization identity is invalid")
    return " ".join(
        shlex.quote(value)
        for value in ("python3", "-c", REMOTE_INSTALL, digest, expected_sha)
    )


def synchronize(expected_sha: str) -> dict:
    if os.environ.get("ENV") != "prod" or os.environ.get("PROD_DANGER") != "1":
        raise SyncError("ENV=prod and PROD_DANGER=1 are required")
    if os.environ.get("CONFIRM_PRODUCTION_RESTORE_TOOL_SYNC") != CONFIRMATION:
        raise SyncError("exact restore tool synchronization confirmation is required")
    preflight(expected_sha)
    digest = validate_source()
    output = run(
        [
            "ssh", "-o", "BatchMode=yes", SSH_TARGET,
            remote_command(digest, expected_sha),
        ],
        input_bytes=SOURCE.read_bytes(),
    )
    try:
        result = json.loads(output.splitlines()[-1])
    except (IndexError, json.JSONDecodeError) as exc:
        raise SyncError("remote synchronization evidence is invalid") from exc
    if result.get("status") != "PASS" or result.get("sha256") != digest:
        raise SyncError("remote synchronization evidence differs")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-live-main-sha", required=True)
    args = parser.parse_args()
    try:
        result = synchronize(args.expected_live_main_sha)
    except SyncError as exc:
        raise SystemExit(f"[production.restore-tool.sync] BLOCKED: {exc}") from exc
    print("[production.restore-tool.sync] PASS " + json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
