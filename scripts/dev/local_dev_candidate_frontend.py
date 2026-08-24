#!/usr/bin/env python3
"""Serve a frozen linked-worktree frontend against the governed local.dev API."""
from __future__ import annotations

import os
import json
import re
import signal
import stat
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# Direct execution and import-based unit tests have different sys.path roots.
# Keep the authority helper as the single source of truth without requiring a
# package-level scripts/ module.
if str(ROOT / "scripts/dev") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts/dev"))
from local_dev_frontend_quick import LocalDevAuthorityError, _isolated_environment, _git_output, resolve_authority_env

PORT = 5176
API_PROXY = "http://127.0.0.1:18081"
CONFIRMATION = "SERVE_FROZEN_LOCAL_DEV_CANDIDATE"
ALLOWED_BRANCH = re.compile(r"^(feature|fix|refactor|audit|release|codex)/.+$")
SHA = re.compile(r"^[0-9a-f]{40}$")
PIDFILE = Path("/tmp/sc-local-dev-candidate-frontend.pid")


class CandidateFrontendError(RuntimeError):
    pass


def _candidate_identity(root: Path = ROOT) -> tuple[str, str]:
    root = root.resolve()
    if Path(_git_output(root, "rev-parse", "--show-toplevel")).resolve() != root:
        raise CandidateFrontendError("candidate root is not the active git worktree")
    branch = _git_output(root, "branch", "--show-current")
    head = _git_output(root, "rev-parse", "HEAD")
    status = _git_output(root, "status", "--porcelain=v2", "--untracked-files=all")
    requested = os.environ.get("CANDIDATE_GIT_HEAD", "")
    if not ALLOWED_BRANCH.fullmatch(branch) or branch == "main":
        raise CandidateFrontendError("candidate branch is not an allowed topic branch")
    if not SHA.fullmatch(requested) or requested != head:
        raise CandidateFrontendError("CANDIDATE_GIT_HEAD must equal the current full candidate SHA")
    if status:
        raise CandidateFrontendError("candidate worktree must be clean")
    if os.environ.get("CONFIRM_LOCAL_DEV_CANDIDATE_FRONTEND") != CONFIRMATION:
        raise CandidateFrontendError("candidate static service confirmation is missing")
    return branch, head


def _read_process_identity(pidfile: Path = PIDFILE) -> dict[str, object]:
    try:
        metadata = pidfile.lstat()
    except FileNotFoundError as exc:
        raise CandidateFrontendError("candidate pidfile is missing") from exc
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise CandidateFrontendError("candidate pidfile must be a regular non-symlink file")
    if metadata.st_uid != os.getuid():
        raise CandidateFrontendError("candidate pidfile owner mismatch")
    try:
        payload = json.loads(pidfile.read_text(encoding="utf-8"))
        pid = int(payload["pid"])
        head = str(payload["head"])
        root = str(payload["root"])
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise CandidateFrontendError("candidate pidfile contains an invalid identity") from exc
    if pid <= 1:
        raise CandidateFrontendError("candidate pid is unsafe")
    if not SHA.fullmatch(head) or not Path(root).is_absolute():
        raise CandidateFrontendError("candidate pidfile identity is unsafe")
    return {"pid": pid, "head": head, "root": root}


def _validate_process(root: Path, head: str, pidfile: Path = PIDFILE) -> int:
    identity = _read_process_identity(pidfile)
    pid = int(identity["pid"])
    if Path(str(identity["root"])).resolve() != root.resolve() or identity["head"] != head:
        raise CandidateFrontendError("candidate pidfile root or head mismatch")
    process_root = Path(f"/proc/{pid}")
    if not process_root.is_dir():
        raise ProcessLookupError(pid)
    if process_root.stat().st_uid != os.getuid():
        raise CandidateFrontendError("candidate process owner mismatch")
    if Path(os.readlink(process_root / "cwd")).resolve() != root.resolve():
        raise CandidateFrontendError("candidate process cwd mismatch")
    command = (process_root / "cmdline").read_bytes().replace(b"\0", b" ").decode("utf-8", errors="replace")
    expected_script = str(root / "scripts/release/release_static_server.mjs")
    if expected_script not in command or "node" not in command:
        raise CandidateFrontendError("candidate process command mismatch")
    environment = (process_root / "environ").read_bytes().split(b"\0")
    expected_environment = {
        f"STATIC_ROOT={root / 'frontend/apps/web/dist-dev'}".encode(),
        f"STATIC_PORT={PORT}".encode(),
        f"API_PROXY_TARGET={API_PROXY}".encode(),
        f"CANDIDATE_GIT_HEAD={head}".encode(),
    }
    if not expected_environment.issubset(set(environment)):
        raise CandidateFrontendError("candidate process environment mismatch")
    return pid


def _run_make(root: Path, authority: Path, target: str, extra: list[str] | None = None) -> None:
    command = ["make", "--no-print-directory", "ENV=dev", f"ENV_FILE={authority}", f"LOCAL_DEV_ENV_FILE={authority}"]
    command.extend(extra or [])
    command.append(target)
    result = subprocess.run(command, cwd=root, env=_isolated_environment(), text=True, check=False)
    if result.returncode:
        raise CandidateFrontendError(f"governed target failed: {target}")


def _health() -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/login", timeout=2) as response:
            return response.status == 200
    except OSError:
        return False


def _wait_until_stopped(pid: int) -> None:
    for _ in range(30):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.1)
    raise CandidateFrontendError("candidate process did not stop after SIGTERM")


def up(root: Path = ROOT) -> None:
    _branch, head = _candidate_identity(root)
    authority = resolve_authority_env(root)
    _run_make(root, authority, "local.dev.ready")
    _run_make(root, authority, "verify.frontend.build", ["FRONTEND_DIST_DIR=frontend/apps/web/dist-dev"])
    dist = root / "frontend/apps/web/dist-dev"
    if not (dist / "index.html").is_file():
        raise CandidateFrontendError("candidate static build is missing index.html")
    pidfile = PIDFILE
    if pidfile.exists():
        try:
            _validate_process(root, head, pidfile)
        except ProcessLookupError:
            pidfile.unlink(missing_ok=True)
        else:
            if _health():
                print(f"[local.dev.candidate.frontend] PASS reused url=http://127.0.0.1:{PORT} sha={head}")
                return
            raise CandidateFrontendError("candidate pid exists but service is unhealthy; use governed down first")
    process_env = _isolated_environment()
    process_env.update(STATIC_ROOT=str(dist), STATIC_PORT=str(PORT), API_PROXY_TARGET=API_PROXY, CANDIDATE_GIT_HEAD=head)
    process = subprocess.Popen(
        ["node", str(root / "scripts/release/release_static_server.mjs")], cwd=root,
        env=process_env, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    pidfile.write_text(json.dumps({"pid": process.pid, "root": str(root.resolve()), "head": head}) + "\n", encoding="utf-8")
    pidfile.chmod(0o600)
    for _ in range(30):
        if process.poll() is not None:
            pidfile.unlink(missing_ok=True)
            raise CandidateFrontendError("candidate static service exited during startup")
        if _health():
            print(f"[local.dev.candidate.frontend] PASS url=http://127.0.0.1:{PORT} sha={head} api={API_PROXY}")
            return
        time.sleep(0.2)
    os.killpg(process.pid, signal.SIGTERM)
    pidfile.unlink(missing_ok=True)
    raise CandidateFrontendError("candidate static service did not become healthy")


def down(root: Path = ROOT) -> None:
    _branch, head = _candidate_identity(root)
    pidfile = PIDFILE
    if not pidfile.exists():
        print("[local.dev.candidate.frontend] PASS already absent")
        return
    try:
        running_identity = _read_process_identity(pidfile)
        running_head = str(running_identity["head"])
        pid = _validate_process(root, running_head, pidfile)
    except ProcessLookupError:
        pidfile.unlink(missing_ok=True)
        print(f"[local.dev.candidate.frontend] PASS removed stale pidfile sha={head}")
        return
    os.killpg(pid, signal.SIGTERM)
    _wait_until_stopped(pid)
    pidfile.unlink(missing_ok=True)
    print(f"[local.dev.candidate.frontend] PASS stopped sha={running_head} current_sha={head}")


def health(root: Path = ROOT) -> None:
    _branch, head = _candidate_identity(root)
    _validate_process(root, head, PIDFILE)
    if not _health():
        raise CandidateFrontendError("candidate static service is not healthy")
    print(f"[local.dev.candidate.frontend] PASS healthy url=http://127.0.0.1:{PORT} sha={head}")


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in {"up", "down", "health"}:
        print("usage: local_dev_candidate_frontend.py {up|down|health}", file=sys.stderr)
        return 2
    try:
        {"up": up, "down": down, "health": health}[sys.argv[1]]()
        return 0
    except (CandidateFrontendError, LocalDevAuthorityError, subprocess.CalledProcessError) as exc:
        print(f"[local.dev.candidate.frontend] DENY {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
