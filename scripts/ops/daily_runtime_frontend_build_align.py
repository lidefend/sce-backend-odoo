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
   `scripts/verify/frontend_build_fingerprint.sh`, sweep the artifact for the
   physical database names this lane knows about (their presence would be a
   second routing input beside the entry namespace), and declare the
   fingerprint in the build input file so the next governed duty refresh
   publishes it;
4. read back `/index.html` and the built entry asset through the public entry,
   proving the bind-mounted static face is the generation just built;
5. leave the runtime identity refresh to the governed duty refresh: the Odoo
   process publishes `FRONTEND_BUILD_SHA256`, but restarting the legacy
   `.env.dev` stack is not the duty that serves the entry.

The remote script runs over SSH and touches only the frontend output directory,
that single declared env line, and the build input file; it never rewrites the
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
#: No bare default: the served database is a governance fact the lane derives
#: from the duty declaration. A database name does not identify a carrier on
#: its own, and a shipped literal would silently bake a stale name.
DEFAULT_DATABASE = ""
DEFAULT_BASE_URL = "http://127.0.0.1:18081"
#: Batch C: the entry namespace, not a physical database name, selects the
#: platform-admin authority. The duty database is still an input here because a
#: bundle that carries it would reintroduce the retired second selector.
PLATFORM_ADMIN_KEY = "VITE_PLATFORM_ADMIN_DB"
DATABASE_NAME = re.compile(r"^[a-z][a-z0-9_]*$")
DEFAULT_RECEIPT = ".runtime/final-acceptance/daily-deployed/frontend-build.json"
CONFIRMATION = "BUILD_AND_DECLARE_DAILY_RUNTIME_FRONTEND_AT_DEPLOYED_HEAD"
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
FULL_FP = re.compile(r"^[0-9a-f]{64}$")
ENTRY_PREFIX = re.compile(r"^/(t/[a-z0-9-]+|platform-admin)$")
ENTRY_ASSET = re.compile(r"^index-[A-Za-z0-9_-]+\.js$")
SSH_HOST = re.compile(r"^[A-Za-z0-9._-]+$")


class BuildError(RuntimeError):
    pass


REMOTE_BUILD = r'''
import fcntl, json, os, re, shutil, subprocess, sys, time, urllib.request
from pathlib import Path

(expected_sha, env_name, env_file, database, base_url, remote_root,
 fingerprint_hint, entry_hint, platform_admin_database,
 entry_prefix) = sys.argv[1:11]

tag = "[daily.runtime.frontend.build]"
fixed_root = Path("/opt/projects/repos/sce-product-odoo")
root = Path(remote_root)
full_sha = re.compile(r"^[0-9a-f]{40}$")
full_fp = re.compile(r"^[0-9a-f]{64}$")
entry_re = re.compile(r'src="/assets/(index-[^"?]+\.js)"')
entry_prefix_re = re.compile(r"^/(t/[a-z0-9-]+|platform-admin)$")

if root != fixed_root or not root.is_dir():
    raise SystemExit(tag + " BLOCKED invalid remote repository")
if not full_sha.fullmatch(expected_sha):
    raise SystemExit(tag + " BLOCKED invalid deployed revision")
if not entry_prefix_re.fullmatch(entry_prefix or ""):
    raise SystemExit(tag + " BLOCKED invalid entry namespace prefix")

env_path = root / env_file
dist_dir = root / "frontend/apps/web/dist-dev"
head_sha = ""
state = {
    "expected_sha": expected_sha, "head": "", "reused": False, "rebuilt": False,
    "fingerprint": "", "entry_asset": "", "env_file": str(env_path),
    "env_written": False, "backup_path": "", "restarted": False,
    "platform_admin_database": platform_admin_database,
    "entry_prefix": entry_prefix,
    "physical_db_sweep": "NOT_RUN", "physical_db_bakes": [],
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

def env_write_line(key, value):
    """Declare one env line, keeping a single backup for rollback.

    Two authorities must not drift, so this is the only writer: a value that a
    build *consumes* has to be declared before the build runs, and a value that
    only records the build's outcome is declared after it. The backup is taken
    once, so a rollback restores the file as it was before either write.
    """
    rows = env_rows()
    key_rows = [i for i, row in enumerate(rows) if row.startswith(key + "=")]
    if len(key_rows) > 1:
        blocked("env file must declare at most one " + key)
    target = key + "=" + value
    if len(key_rows) == 1 and rows[key_rows[0]] == target:
        return False
    if not state["backup_path"]:
        state["backup_path"] = str(env_path) + ".bak"
        shutil.copy2(env_path, state["backup_path"])
    if key_rows:
        rows[key_rows[0]] = target
    else:
        rows.append(target)
    env_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    os.chmod(env_path, 0o600)
    if env_single(key) != value:
        shutil.copy2(state["backup_path"], env_path)
        blocked("env write not verified; restored")
    state["env_written"] = True
    return True

def restore_env():
    if state["env_written"] and state["backup_path"]:
        shutil.copy2(state["backup_path"], env_path)

def physical_db_bakes():
    """Physical database names present in the served bundle.

    Batch C removed every build-time database selector: the entry namespace is
    the only routing input. A bundle that still carries one of these names has
    silently reinstated the selector the entry refuses to honour, so the build
    fails instead of publishing two competing authorities.
    """
    names = [name for name in dict.fromkeys([database, platform_admin_database]) if name]
    found = []
    for path in sorted(dist_dir.rglob("*")):
        if path.suffix not in (".js", ".mjs", ".css") or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for name in names:
            if name in text:
                found.append(name)
    return sorted(set(found))

def readback():
    # Batch C: the namespace prefix carries the database authority. The bare
    # /api path is refused with NS_NAMESPACE_REQUIRED, so the served identity is
    # read from the same namespace the browser uses.
    try:
        with urllib.request.urlopen(
            base_url + entry_prefix + "/api/runtime-version", timeout=20
        ) as resp:
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
        and declared == fingerprint_hint
        and disk_fp == fingerprint_hint
        and entry_before == entry_hint
        and not physical_db_bakes()
    )
    if reused:
        state["reused"] = True
        state["fingerprint"] = fingerprint_hint
        state["entry_asset"] = entry_hint
        # The reuse precondition already scanned the served bundle for physical
        # database names.  Report that fact instead of NOT_RUN, otherwise a
        # byte-identical reuse is rejected by the caller as missing evidence.
        state["physical_db_bakes"] = []
        state["physical_db_sweep"] = "NO_PHYSICAL_DB_NAME"
        state["runtime_refresh_required"] = not (
            isinstance(served_before, dict)
            and served_before.get("git_sha") == expected_sha
            and served_before.get("frontend_build_sha256") == fingerprint_hint
        )
        emit("PASS")
        sys.exit(0)

    # Batch C: no physical database is a build input. The static build removes
    # the legacy selectors from its environment, so writing one here would only
    # make the declaration look like an authority the bundle no longer reads.
    code, build_tail = build()
    state["rebuilt"] = True
    state["build_tail"] = build_tail[-1200:]
    if code:
        restore_env()
        blocked("governed frontend build failed")

    code, fingerprint, fingerprint_tail = fingerprint(dist_dir)
    state["fingerprint"] = fingerprint
    state["fingerprint_tail"] = fingerprint_tail[-600:]
    if code or not full_fp.fullmatch(fingerprint):
        restore_env()
        blocked("frontend build fingerprint is invalid")

    index_path = dist_dir / "index.html"
    entry = entry_of(index_path.read_text(encoding="utf-8") if index_path.is_file() else "")
    state["entry_asset"] = entry
    if not entry:
        restore_env()
        blocked("built index.html does not declare an entry asset")

    state["physical_db_bakes"] = physical_db_bakes()
    state["physical_db_sweep"] = (
        "NO_PHYSICAL_DB_NAME" if not state["physical_db_bakes"] else "FOUND"
    )
    if state["physical_db_bakes"]:
        restore_env()
        blocked(
            "the built bundle carries a physical database name: "
            + ", ".join(state["physical_db_bakes"])
        )

    env_write_line("FRONTEND_BUILD_SHA256", fingerprint)
    # The static bundle is served from a bind mount, so the public entry sees
    # this build as soon as the files are written.  The Odoo process publishes
    # its declared build identity through `/api/runtime-version`; that fact is
    # refreshed by the governed duty refresh, not by restarting the legacy
    # `.env.dev` stack that this entry used to address by mistake.
    state["runtime_refresh_required"] = True
    served = readback()
    state["served"] = served

    served_code, served_html = http_text(entry_prefix + "/index.html")
    served_entry = entry_of(served_html)
    state["served_entry_asset"] = served_entry
    asset_code = http_status(entry_prefix + "/assets/" + entry)

    ok = bool(
        served_entry == entry
        and asset_code == 200
        and state["physical_db_sweep"] == "NO_PHYSICAL_DB_NAME"
    )
    if not ok and state["env_written"]:
        restore_env()
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
    platform_admin_database: str,
    entry_prefix: str,
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
            platform_admin_database,
            entry_prefix,
        )
    )


def preflight(
    expected_sha: str, ssh_host: str, platform_admin_database: str, entry_prefix: str
) -> None:
    if os.environ.get("CONFIRM_DAILY_RUNTIME_FRONTEND_BUILD") != CONFIRMATION:
        raise BuildError("exact daily runtime frontend build confirmation is required")
    if not FULL_SHA.fullmatch(expected_sha or ""):
        raise BuildError("expected revision must be a full lowercase commit SHA")
    if not SSH_HOST.fullmatch(ssh_host or ""):
        raise BuildError("ssh host must be a configured host alias")
    if not DATABASE_NAME.fullmatch(platform_admin_database or ""):
        raise BuildError(
            "the platform-admin database must be the declared duty database name"
        )
    if not ENTRY_PREFIX.fullmatch(entry_prefix or ""):
        raise BuildError("the entry namespace prefix must be a declared path prefix")


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
    platform_admin_database: str,
    entry_prefix: str,
) -> dict[str, object]:
    preflight(expected_sha, ssh_host, platform_admin_database, entry_prefix)
    if not DATABASE_NAME.fullmatch(database or ""):
        raise BuildError(
            "the served database must be a declared duty database name; this "
            "entry no longer ships a bare default"
        )
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
            platform_admin_database,
            entry_prefix,
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
        or not isinstance(evidence.get("runtime_refresh_required"), bool)
        or evidence.get("platform_admin_database") != platform_admin_database
        or evidence.get("physical_db_sweep") != "NO_PHYSICAL_DB_NAME"
        or evidence.get("physical_db_bakes") != []
        or evidence.get("entry_prefix") != entry_prefix
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
    parser.add_argument("--platform-admin-database", required=True)
    parser.add_argument("--entry-prefix", required=True)
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
            args.platform_admin_database,
            args.entry_prefix,
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
