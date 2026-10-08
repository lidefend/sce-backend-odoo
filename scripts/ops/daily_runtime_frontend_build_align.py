#!/usr/bin/env python3
"""Build the daily runtime's served frontend at the exact deployed revision and declare it.

The daily runtime serves a prebuilt static frontend from `FRONTEND_DIST_DIR`
(`frontend/apps/web/dist-dev`) through the nginx bind mount. The governed code
sync (`daily.runtime.main.bundle_sync`) only fast-forwards the git tree, so a
mainline merge that changes frontend sources leaves the *served* bundle at the
previous generation while `/api/runtime-version` still reports the new commit.
User-level acceptance would then exercise a stale rendering surface, which no
assertion in the read-only probe can see.

This entry closes the gap with existing governed pieces only:

1. require the remote tree to be at the exact expected commit and clean;
2. reuse the already-declared bundle when the recorded receipt, the declared
   `FRONTEND_BUILD_SHA256`, the on-disk fingerprint and the served entry asset
   already agree;
3. otherwise run the existing governed `make verify.frontend.build`, compute the
   artifact fingerprint with the existing governed
   `scripts/verify/frontend_build_fingerprint.sh`, and declare that fingerprint
   in the runtime env file so `/api/runtime-version` exposes the served bundle;
4. recreate the governed runtime through `make restart`, then read back both
   `/api/runtime-version` and `/index.html` and prove the served entry asset is
   the one just built;
5. restore the previous env file and runtime when the readback does not confirm
   the new generation.

The remote script runs over SSH and touches only the frontend output directory,
that single declared env line, and the governed runtime; it never rewrites the
code tree, database, volumes, credentials or nginx configuration.
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
DEFAULT_DATABASE = "sc_demo"
DEFAULT_BASE_URL = "http://127.0.0.1:18081"
DEFAULT_RECEIPT = ".runtime/final-acceptance/daily-deployed/frontend-build.json"
CONFIRMATION = "BUILD_AND_DECLARE_DAILY_RUNTIME_FRONTEND_AT_DEPLOYED_HEAD"
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
FULL_FP = re.compile(r"^[0-9a-f]{64}$")
ENTRY_ASSET = re.compile(r"^index-[A-Za-z0-9_-]+\.js$")
SSH_HOST = re.compile(r"^[A-Za-z0-9._-]+$")


class BuildError(RuntimeError):
    pass


REMOTE_BUILD = r'''
import fcntl, json, os, re, shutil, subprocess, sys, time, urllib.request
from pathlib import Path

(expected_sha, env_name, env_file, database, base_url, remote_root,
 fingerprint_hint, entry_hint) = sys.argv[1:9]

tag = "[daily.runtime.frontend.build]"
fixed_root = Path("/opt/projects/repos/sce-product-odoo")
root = Path(remote_root)
full_sha = re.compile(r"^[0-9a-f]{40}$")
full_fp = re.compile(r"^[0-9a-f]{64}$")
entry_re = re.compile(r'src="/assets/(index-[^"?]+\.js)"')

if root != fixed_root or not root.is_dir():
    raise SystemExit(tag + " BLOCKED invalid remote repository")
if not full_sha.fullmatch(expected_sha):
    raise SystemExit(tag + " BLOCKED invalid deployed revision")

env_path = root / env_file
dist_dir = root / "frontend/apps/web/dist-dev"
head_sha = ""
state = {
    "expected_sha": expected_sha, "head": "", "reused": False, "rebuilt": False,
    "fingerprint": "", "entry_asset": "", "env_file": str(env_path),
    "env_written": False, "backup_path": "", "restarted": False,
    "rolled_back": False, "served": None, "served_entry_asset": "",
    "dist_dir": str(dist_dir), "remote_root": str(root),
    "build_tail": "", "fingerprint_tail": "", "restart_tail": "",
}

def emit(status):
    payload = {"status": status}
    payload.update(state)
    print(json.dumps(payload, sort_keys=True))
    sys.stdout.flush()

def blocked(reason):
    sys.stderr.write(tag + " BLOCKED " + reason + "\n")
    sys.stderr.flush()
    emit("BLOCKED")
    sys.exit(1)

def git(*args):
    return subprocess.run(
        ["git", *args], cwd=root, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
    )

def env_rows():
    return env_path.read_text(encoding="utf-8").splitlines()

def env_single(key):
    values = [row.split("=", 1)[1].strip() for row in env_rows() if row.startswith(key + "=")]
    if len(values) != 1:
        return None
    return values[0]

def readback():
    try:
        with urllib.request.urlopen(base_url + "/api/runtime-version", timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None

def http_text(path):
    try:
        with urllib.request.urlopen(base_url + path, timeout=20) as resp:
            return resp.getcode(), resp.read().decode("utf-8", "replace")
    except Exception:
        return None, ""

def http_status(path):
    try:
        with urllib.request.urlopen(base_url + path, timeout=20) as resp:
            return resp.getcode()
    except Exception:
        return None

def entry_of(html):
    match = entry_re.search(html or "")
    return match.group(1) if match else ""

def run_make(*args):
    result = subprocess.run(
        ["make", *args], cwd=root, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
    )
    return result.returncode, result.stdout

def restart():
    return run_make("restart", "ENV=" + env_name, "ENV_FILE=" + env_file)

def build():
    return run_make("verify.frontend.build", "ENV=" + env_name,
                    "ENV_FILE=" + env_file, "DB_NAME=" + database)

def fingerprint(dist):
    result = subprocess.run(
        ["bash", "scripts/verify/frontend_build_fingerprint.sh", str(dist)], cwd=root,
        text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
    )
    digest = ""
    for line in result.stdout.splitlines():
        match = re.search(r"sha256=([0-9a-f]{64})", line)
        if match:
            digest = match.group(1)
    return result.returncode, digest, result.stdout

lock_path = Path("/run/lock/sc_daily-runtime-frontend-build.lock")
lock_path.parent.mkdir(parents=True, exist_ok=True)

with lock_path.open("a+b") as lock:
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit(tag + " BLOCKED concurrent frontend build")

    head = git("rev-parse", "HEAD")
    head_sha = head.stdout.strip() if head.returncode == 0 else ""
    state["head"] = head_sha
    if head_sha != expected_sha:
        blocked("remote HEAD %s != deployed revision %s" % (head_sha or "<unknown>", expected_sha))
    if git("status", "--porcelain").stdout.strip():
        blocked("remote worktree is not clean")

    if not env_path.is_file():
        blocked("missing env file %s" % env_path)

    dist_raw = env_single("FRONTEND_DIST_DIR") or "frontend/apps/web/dist-dev"
    dist_rel = dist_raw[2:] if dist_raw.startswith("./") else dist_raw
    dist_dir = Path(dist_rel) if dist_raw.startswith("/") else root / dist_rel
    state["dist_dir"] = str(dist_dir)
    if not dist_dir.is_dir():
        blocked("missing frontend output directory %s" % dist_dir)

    code_before, html_before = http_text("/index.html")
    entry_before = entry_of(html_before)
    served_before = readback()
    state["served"] = served_before
    state["served_entry_asset"] = entry_before

    declared = env_single("FRONTEND_BUILD_SHA256")
    disk_fp = ""
    disk_fp_path = dist_dir / ".build-sha256"
    if disk_fp_path.is_file():
        disk_fp = disk_fp_path.read_text(encoding="utf-8").strip()

    reused = bool(
        fingerprint_hint and full_fp.fullmatch(fingerprint_hint)
        and entry_hint and entry_re.fullmatch('src="/assets/%s"' % entry_hint)
        and isinstance(served_before, dict)
        and served_before.get("git_sha") == expected_sha
        and served_before.get("frontend_build_sha256") == fingerprint_hint
        and declared == fingerprint_hint
        and disk_fp == fingerprint_hint
        and entry_before == entry_hint
    )
    if reused:
        state["reused"] = True
        state["fingerprint"] = fingerprint_hint
        state["entry_asset"] = entry_hint
        emit("PASS")
        sys.exit(0)

    code, build_tail = build()
    state["rebuilt"] = True
    state["build_tail"] = build_tail[-1200:]
    if code:
        blocked("governed frontend build failed")

    code, fingerprint, fingerprint_tail = fingerprint(dist_dir)
    state["fingerprint"] = fingerprint
    state["fingerprint_tail"] = fingerprint_tail[-600:]
    if code or not full_fp.fullmatch(fingerprint):
        blocked("frontend build fingerprint is invalid")

    index_path = dist_dir / "index.html"
    entry = entry_of(index_path.read_text(encoding="utf-8") if index_path.is_file() else "")
    state["entry_asset"] = entry
    if not entry:
        blocked("built index.html does not declare an entry asset")

    rows = env_rows()
    key_rows = [i for i, row in enumerate(rows) if row.startswith("FRONTEND_BUILD_SHA256=")]
    if len(key_rows) > 1:
        blocked("env file must declare at most one FRONTEND_BUILD_SHA256")
    target = "FRONTEND_BUILD_SHA256=" + fingerprint
    changed = not key_rows or rows[key_rows[0]] != target
    if changed:
        backup_path = str(env_path) + ".bak"
        state["backup_path"] = backup_path
        shutil.copy2(env_path, backup_path)
        if key_rows:
            rows[key_rows[0]] = target
        else:
            rows.append(target)
        env_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
        os.chmod(env_path, 0o600)
        if target not in env_rows():
            shutil.copy2(backup_path, env_path)
            blocked("env write not verified; restored")
        state["env_written"] = True

    code, restart_tail = restart()
    state["restarted"] = True
    state["restart_tail"] = restart_tail[-600:]
    if code:
        if changed:
            shutil.copy2(state["backup_path"], env_path)
            restart()
        blocked("governed restart failed")

    deadline = time.time() + 180
    served = None
    while time.time() < deadline:
        served = readback()
        if (served and served.get("git_sha") == expected_sha
                and served.get("frontend_build_sha256") == fingerprint):
            break
        time.sleep(6)
    state["served"] = served

    served_code, served_html = http_text("/index.html")
    served_entry = entry_of(served_html)
    state["served_entry_asset"] = served_entry
    asset_code = http_status("/assets/" + entry)

    ok = bool(
        served and served.get("git_sha") == expected_sha
        and served.get("frontend_build_sha256") == fingerprint
        and served_entry == entry
        and asset_code == 200
    )
    if not ok and changed:
        shutil.copy2(state["backup_path"], env_path)
        restart()
        state["rolled_back"] = True
    emit("PASS" if ok else "BLOCKED")
    sys.exit(0 if ok else 1)
'''


def remote_command(
    expected_sha: str,
    env_name: str,
    env_file: str,
    database: str,
    base_url: str,
    fingerprint_hint: str,
    entry_hint: str,
) -> str:
    return " ".join(
        shlex.quote(item)
        for item in (
            "python3",
            "-c",
            REMOTE_BUILD,
            expected_sha,
            env_name,
            env_file,
            database,
            base_url,
            REMOTE_ROOT,
            fingerprint_hint,
            entry_hint,
        )
    )


def preflight(expected_sha: str, ssh_host: str) -> None:
    if os.environ.get("CONFIRM_DAILY_RUNTIME_FRONTEND_BUILD") != CONFIRMATION:
        raise BuildError("exact daily runtime frontend build confirmation is required")
    if not FULL_SHA.fullmatch(expected_sha or ""):
        raise BuildError("expected revision must be a full lowercase commit SHA")
    if not SSH_HOST.fullmatch(ssh_host or ""):
        raise BuildError("ssh host must be a configured host alias")


def reuse_hint(receipt_path: str, expected_sha: str) -> tuple[str, str]:
    """Return the (fingerprint, entry asset) recorded by a previous governed build at this exact commit."""
    try:
        payload = json.loads(Path(receipt_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ("", "")
    if (
        isinstance(payload, dict)
        and payload.get("status") == "PASS"
        and payload.get("expected_sha") == expected_sha
        and payload.get("head") == expected_sha
        and payload.get("remote_root") == REMOTE_ROOT
        and FULL_FP.fullmatch(str(payload.get("fingerprint") or ""))
        and ENTRY_ASSET.fullmatch(str(payload.get("entry_asset") or ""))
    ):
        return (payload["fingerprint"], payload["entry_asset"])
    return ("", "")


def run(command: list[str]) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False
    )


def align(
    expected_sha: str,
    ssh_host: str,
    env_name: str,
    env_file: str,
    database: str,
    base_url: str,
    fingerprint_hint: str,
    entry_hint: str,
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
        remote_command(
            expected_sha,
            env_name,
            env_file,
            database,
            base_url,
            fingerprint_hint,
            entry_hint,
        ),
    ]
    result = run(command)
    if result.returncode:
        message = (
            result.stderr.decode(errors="replace").strip()
            or result.stdout.decode(errors="replace").strip()
        )
        raise BuildError(f"remote daily frontend build failed: {message[:1000]}")
    try:
        evidence = json.loads(result.stdout.decode().splitlines()[-1])
    except (IndexError, json.JSONDecodeError) as exc:
        raise BuildError("remote daily frontend build evidence is invalid") from exc
    served = evidence.get("served")
    if (
        evidence.get("status") != "PASS"
        or evidence.get("expected_sha") != expected_sha
        or evidence.get("head") != expected_sha
        or evidence.get("remote_root") != REMOTE_ROOT
        or evidence.get("rolled_back") is not False
        or not FULL_FP.fullmatch(str(evidence.get("fingerprint") or ""))
        or not ENTRY_ASSET.fullmatch(str(evidence.get("entry_asset") or ""))
        or evidence.get("served_entry_asset") != evidence.get("entry_asset")
        or not isinstance(served, dict)
        or served.get("git_sha") != expected_sha
        or served.get("frontend_build_sha256") != evidence.get("fingerprint")
    ):
        raise BuildError("remote daily frontend build evidence differs")
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--ssh-host", required=True)
    parser.add_argument("--env-name", default=DEFAULT_ENV_NAME)
    parser.add_argument("--env-file", default=DEFAULT_ENV_FILE)
    parser.add_argument("--database", default=DEFAULT_DATABASE)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--receipt", default=DEFAULT_RECEIPT)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    try:
        fingerprint_hint, entry_hint = reuse_hint(args.receipt, args.expected_sha)
        evidence = align(
            args.expected_sha,
            args.ssh_host,
            args.env_name,
            args.env_file,
            args.database,
            args.base_url,
            fingerprint_hint,
            entry_hint,
        )
    except BuildError as exc:
        raise SystemExit(f"[daily.runtime.frontend.build] BLOCKED: {exc}") from exc
    report = Path(args.report)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        "[daily.runtime.frontend.build] PASS " + json.dumps(evidence, sort_keys=True)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
