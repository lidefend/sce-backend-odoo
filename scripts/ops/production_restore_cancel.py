#!/usr/bin/env python3
"""Cancel one stuck isolated restore rehearsal through its retained report."""

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
CONFIRMATION = "YES_CANCEL_SCOPED_RESTORE_REHEARSAL"
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
RESTORE_ID = re.compile(r"^sc_restore_[0-9]{8}t[0-9]{6}z_[0-9a-f]{8}$")
REPORT_ROOT = "/data/backups/sc_production/restore-rehearsals"


class CancelError(RuntimeError):
    pass


REMOTE_CANCEL = r'''
import json, os, re, signal, sys, time
from pathlib import Path

report_path = Path(sys.argv[1])
root = Path("/data/backups/sc_production/restore-rehearsals")
pattern = re.compile(r"^sc_restore_[0-9]{8}t[0-9]{6}z_[0-9a-f]{8}$")
if report_path.parent != root or report_path.is_symlink() or not report_path.is_file():
    raise SystemExit("[production.restore.cancel] BLOCKED unsafe report path")
report = json.loads(report_path.read_text())
restore_id = str(report.get("restore_id") or "")
if not pattern.fullmatch(restore_id) or report_path.name != restore_id + ".json":
    raise SystemExit("[production.restore.cancel] BLOCKED invalid restore identity")
expected = {
    "network": restore_id + "_internal",
    "db_volume": restore_id + "_db",
    "filestore_volume": restore_id + "_filestore",
    "db_container": restore_id + "_db",
    "odoo_container": restore_id + "_odoo",
}
if report.get("resources") != expected or report.get("status") != "PLANNED":
    raise SystemExit("[production.restore.cancel] BLOCKED report is not cancellable")

def argv(pid):
    try:
        return [item.decode(errors="replace") for item in Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0") if item]
    except (FileNotFoundError, PermissionError, ProcessLookupError):
        return []

def parent(pid):
    try:
        for line in Path(f"/proc/{pid}/status").read_text().splitlines():
            if line.startswith("PPid:"):
                return int(line.split()[1])
    except (FileNotFoundError, PermissionError, ProcessLookupError):
        pass
    return -1

pids = [int(item.name) for item in Path("/proc").iterdir() if item.name.isdigit()]
matches = []
for pid in pids:
    command = argv(pid)
    if (
        "/opt/ops/production_backup_restore.py" in command
        and "restore-rehearsal" in command
        and "--restore-id" in command
        and command[command.index("--restore-id") + 1] == restore_id
        and "--report" in command
        and command[command.index("--report") + 1] == str(report_path)
    ):
        matches.append(pid)
if len(matches) != 1:
    raise SystemExit("[production.restore.cancel] BLOCKED expected exactly one restore process")
restore_pid = matches[0]
descendants = set()
frontier = {restore_pid}
while frontier:
    children = {pid for pid in pids if parent(pid) in frontier}
    descendants.update(children)
    frontier = children
for pid in sorted(descendants, reverse=True):
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
deadline = time.monotonic() + 15
while time.monotonic() < deadline and Path(f"/proc/{restore_pid}").exists():
    time.sleep(0.25)
if Path(f"/proc/{restore_pid}").exists():
    os.kill(restore_pid, signal.SIGTERM)
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline and Path(f"/proc/{restore_pid}").exists():
        time.sleep(0.25)
if Path(f"/proc/{restore_pid}").exists():
    raise SystemExit("[production.restore.cancel] BLOCKED restore process did not terminate")
final = json.loads(report_path.read_text())
if final.get("status") not in {"FAIL", "PLANNED"}:
    raise SystemExit("[production.restore.cancel] BLOCKED unexpected final report status")
print(json.dumps({"status":"PASS","restore_id":restore_id,"process_terminated":True,
                  "report_status":final.get("status"),"production_resources_touched":False}))
'''


def run(command: list[str]) -> str:
    completed = subprocess.run(
        command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        check=False, text=True,
    )
    if completed.returncode:
        raise CancelError(f"command failed ({command[0]}): {completed.stderr.strip()[:600]}")
    return completed.stdout.strip()


def git(*arguments: str) -> str:
    return run(["git", *arguments])


def preflight(expected_sha: str, report: str) -> None:
    if not FULL_SHA.fullmatch(expected_sha):
        raise CancelError("expected live main SHA must be a full lowercase SHA")
    report_path = Path(report)
    if str(report_path.parent) != REPORT_ROOT or not RESTORE_ID.fullmatch(report_path.stem):
        raise CancelError("restore report path is outside the governed root")
    if git("rev-parse", "HEAD") != expected_sha or git("branch", "--show-current") != "main":
        raise CancelError("cancel must run from the approved main SHA")
    if git("status", "--porcelain"):
        raise CancelError("cancel worktree must be clean")
    for remote in ("origin", "gitee-mirror"):
        lines = git("ls-remote", remote, "refs/heads/main").splitlines()
        if len(lines) != 1 or lines[0].split()[0] != expected_sha:
            raise CancelError(f"{remote} main identity differs")


def cancel(expected_sha: str, report: str) -> dict:
    if os.environ.get("ENV") != "prod" or os.environ.get("PROD_DANGER") != "1":
        raise CancelError("ENV=prod and PROD_DANGER=1 are required")
    if os.environ.get("CONFIRM_PRODUCTION_RESTORE_CANCEL") != CONFIRMATION:
        raise CancelError("exact restore cancellation confirmation is required")
    preflight(expected_sha, report)
    remote = " ".join(shlex.quote(item) for item in ("python3", "-c", REMOTE_CANCEL, report))
    output = run(["ssh", "-o", "BatchMode=yes", SSH_TARGET, remote])
    try:
        result = json.loads(output.splitlines()[-1])
    except (IndexError, json.JSONDecodeError) as exc:
        raise CancelError("remote cancellation evidence is invalid") from exc
    if result.get("status") != "PASS" or not result.get("process_terminated"):
        raise CancelError("remote cancellation evidence differs")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-live-main-sha", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    try:
        result = cancel(args.expected_live_main_sha, args.report)
    except CancelError as exc:
        raise SystemExit(f"[production.restore.cancel] BLOCKED: {exc}") from exc
    print("[production.restore.cancel] PASS " + json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
