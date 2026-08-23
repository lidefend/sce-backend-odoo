#!/usr/bin/env python3
"""Run the frontend Quick gate with the governed local.dev authority."""
from __future__ import annotations

import os
import stat
import subprocess
import sys
from pathlib import Path
from typing import Callable


ROOT = Path(__file__).resolve().parents[2]
EXPECTED_ENV_NAME = ".env.dev"


class LocalDevAuthorityError(RuntimeError):
    """The governed local.dev credential authority cannot be trusted."""


def _git_output(repo: Path, *args: str) -> str:
    git_environment = {
        key: value for key, value in os.environ.items() if not key.startswith("GIT_")
    }
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        env=git_environment,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def resolve_authority_env(repo_root: Path = ROOT) -> Path:
    """Resolve the primary worktree's fixed local.dev carrier via git metadata."""
    repo_root = repo_root.resolve()
    current_top = Path(_git_output(repo_root, "rev-parse", "--show-toplevel")).resolve()
    if current_top != repo_root:
        raise LocalDevAuthorityError("current source root is not the active git worktree")

    common_dir = Path(
        _git_output(
            repo_root,
            "rev-parse",
            "--path-format=absolute",
            "--git-common-dir",
        )
    ).resolve()
    if common_dir.name != ".git" or not common_dir.is_dir():
        raise LocalDevAuthorityError("git common directory is not a primary-worktree authority")

    primary_root = common_dir.parent.resolve()
    primary_top = Path(
        _git_output(primary_root, "rev-parse", "--show-toplevel")
    ).resolve()
    primary_common = Path(
        _git_output(
            primary_root,
            "rev-parse",
            "--path-format=absolute",
            "--git-common-dir",
        )
    ).resolve()
    if primary_top != primary_root or primary_common != common_dir:
        raise LocalDevAuthorityError("primary worktree identity does not match git common-dir")

    authority = primary_root / EXPECTED_ENV_NAME
    try:
        metadata = authority.lstat()
    except FileNotFoundError as exc:
        raise LocalDevAuthorityError("governed local.dev authority is missing") from exc
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise LocalDevAuthorityError("governed local.dev authority must be a regular file")
    if stat.S_IMODE(metadata.st_mode) != 0o600:
        raise LocalDevAuthorityError("governed local.dev authority must use mode 0600")
    if metadata.st_uid != os.getuid():
        raise LocalDevAuthorityError("governed local.dev authority owner mismatch")
    return authority


def _isolated_environment() -> dict[str, str]:
    environment = os.environ.copy()
    for key in (
        "ENV",
        "ENV_FILE",
        "LOCAL_DEV_ENV_FILE",
        "ROOT_DIR",
        "DB_NAME",
        "DB",
        "BD",
        "DB_USER",
        "DB_PASSWORD",
        "DB_DATA",
        "REDIS_DATA",
        "ODOO_DATA",
        "ODOO_DB",
        "ODOO_DBFILTER",
        "ODOO_PORT",
        "LIST_DB",
        "COMPOSE_PROJECT_NAME",
        "PROJECT",
        "SC_ENVIRONMENT",
        "SC_ALLOW_DEMO_DATA",
        "ISOLATED_DEMO_TENANT",
        "MAKEFLAGS",
        "MAKEOVERRIDES",
        "MFLAGS",
        "PROD_DANGER",
    ):
        environment.pop(key, None)
    for key in tuple(environment):
        if key.startswith("GIT_"):
            environment.pop(key)
    return environment


Runner = Callable[..., subprocess.CompletedProcess[str]]


def run_gate(
    repo_root: Path = ROOT,
    runner: Runner = subprocess.run,
) -> int:
    repo_root = repo_root.resolve()
    authority = resolve_authority_env(repo_root)
    environment = _isolated_environment()
    print("[local.dev.frontend.quick] governed authority validated")

    ready = runner(
        [
            "make",
            "--no-print-directory",
            f"LOCAL_DEV_ENV_FILE={authority}",
            "local.dev.ready",
        ],
        cwd=repo_root,
        env=environment,
        check=False,
        text=True,
    )
    if ready.returncode != 0:
        return ready.returncode

    quick = runner(
        [
            "make",
            "--no-print-directory",
            "ENV=dev",
            f"ENV_FILE={authority}",
            f"LOCAL_DEV_ENV_FILE={authority}",
            "verify.frontend.quick.gate",
        ],
        cwd=repo_root,
        env=environment,
        check=False,
        text=True,
    )
    return quick.returncode


def main() -> int:
    try:
        return run_gate()
    except (LocalDevAuthorityError, subprocess.CalledProcessError) as exc:
        print(f"[local.dev.frontend.quick] DENY {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
