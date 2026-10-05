#!/usr/bin/env python3
"""Declare the daily runtime's exact deployed revision and prove it end to end.

The daily runtime serves `/api/runtime-version` from the `SC_SOURCE_REVISION`
environment variable, but the governed code-sync entry only checks out an exact
SHA and never declares it. The served revision can therefore lag the deployed
tree, and the acceptance identity check (`identity_deployed_sha`) would then bind
a stale value. This entry rewrites only that single declared identity to the
exact running HEAD, recreates the governed runtime through `make restart`,
readbacks the served endpoint, and restores the previous env file when the
readback does not confirm the new revision.

The remote script runs over SSH and touches only the declared revision line; it
never rewrites the code tree, database, volumes or credentials.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REMOTE_ROOT = "/opt/projects/repos/sce-product-odoo"
DEFAULT_ENV_NAME = "dev"
DEFAULT_ENV_FILE = ".env.dev"
CONFIRMATION = "ALIGN_DAILY_RUNTIME_SOURCE_REVISION_WITH_DEPLOYED_HEAD"
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
SSH_HOST = re.compile(r"^[A-Za-z0-9._-]+$")


class AlignError(RuntimeError):
    pass


REMOTE_ALIGN = r'''
import fcntl, json, os, re, shutil, subprocess, sys, time, urllib.request
from pathlib import Path

expected_sha, env_name, env_file, service, base_url, remote_root = sys.argv[1:7]
fixed_root = Path("/opt/projects/repos/sce-product-odoo")
root = Path(remote_root)
full_sha = re.compile(r"^[0-9a-f]{40}$")
tag = "[daily.runtime.source_revision.align]"
if root != fixed_root or not root.is_dir():
    raise SystemExit(tag + " BLOCKED invalid remote repository")
if not full_sha.fullmatch(expected_sha):
    raise SystemExit(tag + " BLOCKED invalid deployed revision")

lock_path = Path("/run/lock/sc_daily-runtime-source-revision-align.lock")
lock_path.parent.mkdir(parents=True, exist_ok=True)

KEY = "SC_SOURCE_REVISION"

def git(*args):
    return subprocess.run(
        ["git", *args], cwd=root, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
    )

def restart():
    result = subprocess.run(
        ["make", "restart", "ENV=" + env_name, "ENV_FILE=" + env_file],
        cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        check=False,
    )
    return result.returncode, result.stdout

def readback():
    try:
        with urllib.request.urlopen(base_url + "/api/runtime-version", timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None

with lock_path.open("a+b") as lock:
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit(tag + " BLOCKED concurrent alignment")

    head = git("rev-parse", "HEAD")
    head_sha = head.stdout.strip() if head.returncode == 0 else ""
    if head_sha != expected_sha:
        raise SystemExit(tag + " BLOCKED remote HEAD %s != deployed revision %s" % (head_sha or "<unknown>", expected_sha))

    env_path = root / env_file
    if not env_path.is_file():
        raise SystemExit(tag + " BLOCKED missing env file %s" % env_path)
    rows = env_path.read_text(encoding="utf-8").splitlines()
    key_rows = [i for i, row in enumerate(rows) if row.startswith(KEY + "=")]
    if len(key_rows) != 1:
        raise SystemExit(tag + " BLOCKED env file must declare exactly one " + KEY)
    current = rows[key_rows[0]].split("=", 1)[1].strip()

    changed = current != expected_sha
    backup_path = ""
    restarted = False
    rolled_back = False
    restart_tail = ""

    if changed:
        backup_path = str(env_path) + ".bak"
        shutil.copy2(env_path, backup_path)
        rows[key_rows[0]] = KEY + "=" + expected_sha
        env_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
        os.chmod(env_path, 0o600)
        verified = any(
            row == KEY + "=" + expected_sha
            for row in env_path.read_text(encoding="utf-8").splitlines()
        )
        if not verified:
            shutil.copy2(backup_path, env_path)
            raise SystemExit(tag + " BLOCKED env write not verified; restored")
        code, restart_tail = restart()
        restarted = True
        if code:
            shutil.copy2(backup_path, env_path)
            restart()
            raise SystemExit(tag + " BLOCKED governed restart failed; env restored")

    deadline = time.time() + 180
    served = None
    while time.time() < deadline:
        served = readback()
        if served and served.get("git_sha") == expected_sha:
            break
        time.sleep(6)

    ok = bool(served and served.get("git_sha") == expected_sha)
    if not ok and changed:
        shutil.copy2(backup_path, env_path)
        restart()
        rolled_back = True

    print(json.dumps({
        "status": "PASS" if ok else "BLOCKED",
        "expected_sha": expected_sha,
        "head": head_sha,
        "previous_revision": current,
        "env_file": str(env_path),
        "env_written": changed,
        "backup_path": backup_path,
        "restarted": restarted,
        "rolled_back": rolled_back,
        "served": served,
        "remote_root": str(root),
        "restart_tail": restart_tail[-600:],
    }, sort_keys=True))
    sys.exit(0 if ok else 1)
'''


def remote_command(
    expected_sha: str, env_name: str, env_file: str, service: str, base_url: str
) -> str:
    return " ".join(
        shlex.quote(item)
        for item in (
            "python3",
            "-c",
            REMOTE_ALIGN,
            expected_sha,
            env_name,
            env_file,
            service,
            base_url,
            REMOTE_ROOT,
        )
    )


def preflight(expected_sha: str, ssh_host: str) -> None:
    if os.environ.get("CONFIRM_DAILY_RUNTIME_SOURCE_REVISION_ALIGN") != CONFIRMATION:
        raise AlignError("exact daily runtime source-revision alignment confirmation is required")
    if not FULL_SHA.fullmatch(expected_sha or ""):
        raise AlignError("expected revision must be a full lowercase commit SHA")
    if not SSH_HOST.fullmatch(ssh_host or ""):
        raise AlignError("ssh host must be a configured host alias")


def run(command: list[str]) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False
    )


def align(
    expected_sha: str,
    ssh_host: str,
    env_name: str,
    env_file: str,
    service: str,
    base_url: str,
) -> dict[str, object]:
    preflight(expected_sha, ssh_host)
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
        remote_command(expected_sha, env_name, env_file, service, base_url),
    ]
    result = run(command)
    if result.returncode:
        message = (
            result.stderr.decode(errors="replace").strip()
            or result.stdout.decode(errors="replace").strip()
        )
        raise AlignError(f"remote source-revision alignment failed: {message[:1000]}")
    try:
        evidence = json.loads(result.stdout.decode().splitlines()[-1])
    except (IndexError, json.JSONDecodeError) as exc:
        raise AlignError("remote source-revision alignment evidence is invalid") from exc
    served = evidence.get("served")
    if (
        evidence.get("status") != "PASS"
        or evidence.get("expected_sha") != expected_sha
        or evidence.get("head") != expected_sha
        or evidence.get("remote_root") != REMOTE_ROOT
        or evidence.get("rolled_back") is not False
        or not isinstance(served, dict)
        or served.get("git_sha") != expected_sha
    ):
        raise AlignError("remote source-revision alignment evidence differs")
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--ssh-host", required=True)
    parser.add_argument("--env-name", default=DEFAULT_ENV_NAME)
    parser.add_argument("--env-file", default=DEFAULT_ENV_FILE)
    parser.add_argument("--service", default="odoo")
    parser.add_argument("--base-url", default="http://127.0.0.1:18081")
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    try:
        evidence = align(
            args.expected_sha,
            args.ssh_host,
            args.env_name,
            args.env_file,
            args.service,
            args.base_url,
        )
    except AlignError as exc:
        raise SystemExit(f"[daily.runtime.source_revision.align] BLOCKED: {exc}") from exc
    report = Path(args.report)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        "[daily.runtime.source_revision.align] PASS "
        + json.dumps(evidence, sort_keys=True)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
