#!/usr/bin/env python3
"""Persist an already-active immutable P2 add-on root in production config."""

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
CONFIRMATION = "PROMOTE_VERIFIED_PRODUCTION_CUSTOMER_RUNTIME_CONFIG"
SHA = re.compile(r"^[0-9a-f]{40}$")
RUNTIME_ROOT = re.compile(r"^/opt/sce/customer-addons/[A-Za-z0-9._+-]+$")
RELEASE_SET = re.compile(
    r"^/data/backups/production_acceptance/tenant-deliveries/[a-z0-9.-]+/production-release-set.json$"
)
EVIDENCE = re.compile(r"^/data/backups/deployments/[A-Za-z0-9._+-]+/[A-Za-z0-9._+-]+\.json$")


class PromoteError(RuntimeError):
    pass


REMOTE_PROMOTE = r'''
import json, os, re, shutil, stat, subprocess, sys, tempfile
from datetime import datetime, timezone
from pathlib import Path

tool_sha, release_set_value, customer_sha, current_value, next_value, evidence_value = sys.argv[1:]
tool = Path("/opt/sce/deployment-tools") / tool_sha
release_set = Path(release_set_value)
current_root = Path(current_value)
next_root = Path(next_value)
evidence = Path(evidence_value)
runtime = Path("/opt/sce/config/sc_production/runtime.env")
if tool.is_symlink() or not tool.is_dir() or (tool / "DEPLOYMENT_TOOL_SHA").read_text().strip() != tool_sha:
    raise SystemExit("CUSTOMER_RUNTIME_TOOL_IDENTITY_INVALID")
sys.path.insert(0, str(tool / "scripts/release"))
import production_release_set
lock = production_release_set.load_lock(release_set)
production_release_set.verify_bound_files(lock)
modules = set(lock.get("customer_modules") or [])
if (lock.get("customer_sha") != customer_sha or not modules
        or any(not re.fullmatch(r"[a-z][a-z0-9_]{2,63}", module) for module in modules)):
    raise SystemExit("CUSTOMER_RUNTIME_RELEASE_SET_IDENTITY_MISMATCH")

runtime_meta = runtime.stat()
if runtime.is_symlink() or not runtime.is_file() or runtime_meta.st_uid != 0 or runtime_meta.st_gid != 0 or stat.S_IMODE(runtime_meta.st_mode) != 0o600:
    raise SystemExit("CUSTOMER_RUNTIME_CONFIG_UNSAFE")
if next_root.is_symlink() or not next_root.is_dir() or next_root.stat().st_uid != 0:
    raise SystemExit("CUSTOMER_RUNTIME_ROOT_UNSAFE")
if {path.name for path in next_root.iterdir() if path.is_dir()} != modules:
    raise SystemExit("CUSTOMER_RUNTIME_MODULE_SET_MISMATCH")
if any(not (next_root / module / "__manifest__.py").is_file() for module in modules):
    raise SystemExit("CUSTOMER_RUNTIME_MODULE_MANIFEST_MISSING")

container = json.loads(subprocess.run(
    ["docker", "inspect", "sc_production-odoo-1"], check=True,
    stdout=subprocess.PIPE, text=True,
).stdout)[0]
mounts = [row for row in container.get("Mounts", []) if row.get("Destination") == "/mnt/customer-addons"]
if len(mounts) != 1 or mounts[0].get("Source") != str(next_root):
    raise SystemExit("CUSTOMER_RUNTIME_ACTIVE_MOUNT_MISMATCH")

rows = runtime.read_text().splitlines()
indexes = [index for index, line in enumerate(rows) if line.startswith("SC_CUSTOMER_ADDONS_ROOT=")]
if len(indexes) != 1:
    raise SystemExit("CUSTOMER_RUNTIME_CONFIG_KEY_INVALID")
observed = rows[indexes[0]].split("=", 1)[1]
if observed not in {str(current_root), str(next_root)}:
    raise SystemExit("CUSTOMER_RUNTIME_CURRENT_ROOT_MISMATCH")
changed = observed != str(next_root)
backup = None
if changed:
    rows[indexes[0]] = "SC_CUSTOMER_ADDONS_ROOT=" + str(next_root)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = runtime.with_name(runtime.name + ".pre-p2-" + customer_sha[:8] + "-" + stamp)
    shutil.copy2(runtime, backup)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".runtime.env.", dir=runtime.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w") as stream:
            stream.write("\n".join(rows) + "\n")
            stream.flush(); os.fsync(stream.fileno())
        os.chown(temporary, 0, 0); temporary.chmod(0o600)
        os.replace(temporary, runtime)
    except Exception:
        temporary.unlink(missing_ok=True)
        shutil.copy2(backup, runtime)
        raise
if runtime.read_text().splitlines()[indexes[0]] != "SC_CUSTOMER_ADDONS_ROOT=" + str(next_root):
    raise SystemExit("CUSTOMER_RUNTIME_CONFIG_POSTCHECK_FAILED")

if evidence.exists() or evidence.is_symlink():
    raise SystemExit("CUSTOMER_RUNTIME_EVIDENCE_MUST_BE_NEW")
evidence.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
report = {"status":"PASS", "changed":changed, "customer_sha":customer_sha,
          "release_set":str(release_set), "current_root":str(current_root),
          "next_root":str(next_root), "active_mount_verified":True,
          "runtime_backup":str(backup) if backup else None}
descriptor, temporary_name = tempfile.mkstemp(prefix=".customer-runtime-config.", dir=evidence.parent)
with os.fdopen(descriptor, "w") as stream:
    json.dump(report, stream, sort_keys=True); stream.write("\n"); stream.flush(); os.fsync(stream.fileno())
temporary = Path(temporary_name); os.chown(temporary, 0, 0); temporary.chmod(0o600); os.replace(temporary, evidence)
print(json.dumps(report, sort_keys=True))
'''


def run(command: list[str]) -> str:
    completed = subprocess.run(
        command, cwd=ROOT, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=False,
    )
    if completed.returncode:
        raise PromoteError(completed.stderr.strip()[:800] or "command failed")
    return completed.stdout.strip()


def git(*args: str) -> str:
    return run(["git", *args])


def promote(args: argparse.Namespace) -> dict:
    if os.environ.get("ENV") != "prod" or os.environ.get("PROD_DANGER") != "1":
        raise PromoteError("ENV=prod and PROD_DANGER=1 are required")
    if os.environ.get("CONFIRM_PRODUCTION_CUSTOMER_RUNTIME_CONFIG_PROMOTE") != CONFIRMATION:
        raise PromoteError("exact customer runtime config confirmation is required")
    if not SHA.fullmatch(args.tool_sha) or not SHA.fullmatch(args.customer_sha):
        raise PromoteError("immutable SHA identity is invalid")
    if git("rev-parse", "HEAD") != args.tool_sha or git("branch", "--show-current") != "main":
        raise PromoteError("promotion must run from approved main")
    if git("status", "--porcelain"):
        raise PromoteError("promotion worktree must be clean")
    for remote in ("origin", "gitee-mirror"):
        rows = git("ls-remote", remote, "refs/heads/main").splitlines()
        if len(rows) != 1 or rows[0].split()[0] != args.tool_sha:
            raise PromoteError(f"{remote} main identity differs")
    if not RUNTIME_ROOT.fullmatch(args.current_root) or not RUNTIME_ROOT.fullmatch(args.next_root):
        raise PromoteError("customer runtime root is invalid")
    if not RELEASE_SET.fullmatch(args.release_set) or not EVIDENCE.fullmatch(args.evidence):
        raise PromoteError("release-set or evidence path is invalid")
    command = " ".join(shlex.quote(value) for value in (
        "python3", "-c", REMOTE_PROMOTE, args.tool_sha, args.release_set,
        args.customer_sha, args.current_root, args.next_root, args.evidence,
    ))
    output = run(["ssh", "-o", "BatchMode=yes", SSH_TARGET, command])
    try:
        result = json.loads(output.splitlines()[-1])
    except (IndexError, json.JSONDecodeError) as exc:
        raise PromoteError("remote evidence is invalid") from exc
    if result.get("status") != "PASS" or result.get("customer_sha") != args.customer_sha:
        raise PromoteError("remote result identity differs")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tool-sha", required=True)
    parser.add_argument("--release-set", required=True)
    parser.add_argument("--customer-sha", required=True)
    parser.add_argument("--current-root", required=True)
    parser.add_argument("--next-root", required=True)
    parser.add_argument("--evidence", required=True)
    try:
        result = promote(parser.parse_args())
    except (OSError, PromoteError) as exc:
        raise SystemExit(f"[production.customer.runtime.config.promote] BLOCKED: {exc}") from exc
    print("[production.customer.runtime.config.promote] PASS " + json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
