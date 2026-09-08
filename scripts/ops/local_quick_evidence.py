#!/usr/bin/env python3
"""Atomically run the local Quick gate and verify its exact-head receipt."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path


SCHEMA_VERSION = 2
SUITE = "ci.local.quick"
PRODUCER = "atomic-ci-local-quick-runner-v1"
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")


class EvidenceError(RuntimeError):
    pass


class QuickRunFailed(EvidenceError):
    def __init__(self, returncode: int):
        super().__init__(f"{SUITE} failed with exit {returncode}; receipt not issued")
        self.returncode = returncode


def git(root: Path, *args: str) -> str:
    process = subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if process.returncode:
        raise EvidenceError(f"git {' '.join(args)} failed: {process.stdout.strip()}")
    return process.stdout.strip()


def repository_root(root: Path) -> Path:
    return Path(git(root, "rev-parse", "--show-toplevel")).resolve()


def require_exact_clean_head(root: Path, expected_head: str) -> tuple[Path, str]:
    if not FULL_SHA.fullmatch(expected_head):
        raise EvidenceError("expected head must be a full lowercase commit SHA")
    root = repository_root(root)
    actual_head = git(root, "rev-parse", "HEAD")
    if actual_head != expected_head:
        raise EvidenceError(
            f"worktree HEAD changed: expected={expected_head} actual={actual_head}"
        )
    status = git(root, "status", "--porcelain=v1", "--untracked-files=all")
    if status:
        raise EvidenceError("worktree must be clean for exact-head quick evidence")
    tree = git(root, "rev-parse", "HEAD^{tree}")
    if not FULL_SHA.fullmatch(tree):
        raise EvidenceError("HEAD tree identity is invalid")
    return root, tree


def evidence_path(root: Path, head: str) -> Path:
    raw = Path(git(root, "rev-parse", "--git-path", f"codex/evidence/{SUITE}/{head}.json"))
    return raw if raw.is_absolute() else root / raw


def _write_receipt_after_success(root: Path, expected_head: str) -> Path:
    root, tree = require_exact_clean_head(root, expected_head)
    path = evidence_path(root, expected_head)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "suite": SUITE,
        "producer": PRODUCER,
        "head": expected_head,
        "tree": tree,
    }
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{expected_head}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, sort_keys=True)
            stream.write("\n")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    return path


def is_linked_worktree(root: Path) -> bool:
    git_dir = Path(git(root, "rev-parse", "--path-format=absolute", "--git-dir")).resolve()
    common_dir = Path(
        git(root, "rev-parse", "--path-format=absolute", "--git-common-dir")
    ).resolve()
    return git_dir != common_dir


def run_quick(root: Path, runner=subprocess.run) -> Path | None:
    root = repository_root(root)
    start_status = git(root, "status", "--porcelain=v1", "--untracked-files=all")
    start_head = git(root, "rev-parse", "HEAD") if not start_status else None
    if start_head and not FULL_SHA.fullmatch(start_head):
        raise EvidenceError("Quick start HEAD identity is invalid")
    if start_head is None:
        print("[ci.local.quick] evidence disabled: worktree was not clean at suite start")

    command = (
        ["python3", "scripts/dev/local_dev_frontend_quick.py", "--full-ci-local-quick"]
        if is_linked_worktree(root)
        else ["make", "--no-print-directory", "ci.local.quick.run"]
    )
    completed = runner(command, cwd=root, check=False, text=True)
    if completed.returncode:
        raise QuickRunFailed(completed.returncode)
    if start_head is None:
        return None
    return _write_receipt_after_success(root, start_head)


def verify(root: Path, expected_head: str) -> Path:
    root, tree = require_exact_clean_head(root, expected_head)
    path = evidence_path(root, expected_head)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EvidenceError("exact-head quick evidence is missing") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise EvidenceError("exact-head quick evidence is unreadable") from exc
    expected = {
        "schema_version": SCHEMA_VERSION,
        "suite": SUITE,
        "producer": PRODUCER,
        "head": expected_head,
        "tree": tree,
    }
    if payload != expected:
        raise EvidenceError("exact-head quick evidence does not match the current candidate")
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("run", "verify"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--expected-head")
    args = parser.parse_args()
    try:
        if args.mode == "run":
            if args.expected_head is not None:
                raise EvidenceError("run mode does not accept --expected-head")
            path = run_quick(args.root)
        else:
            if args.expected_head is None:
                raise EvidenceError("verify mode requires --expected-head")
            path = verify(args.root, args.expected_head)
    except QuickRunFailed as exc:
        print(f"[local_quick_evidence] FAIL {exc}")
        return exc.returncode
    except EvidenceError as exc:
        print(f"[local_quick_evidence] MISS {exc}")
        return 2
    if path is not None:
        print(f"[local_quick_evidence] {'RECORDED' if args.mode == 'run' else 'VERIFIED'} {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
