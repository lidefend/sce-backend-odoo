#!/usr/bin/env python3
"""Record and verify worktree-local evidence for an exact-head quick gate."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path


SCHEMA_VERSION = 1
SUITE = "ci.local.quick"
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")


class EvidenceError(RuntimeError):
    pass


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


def record(root: Path, expected_head: str) -> Path:
    root, tree = require_exact_clean_head(root, expected_head)
    path = evidence_path(root, expected_head)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "suite": SUITE,
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
        "head": expected_head,
        "tree": tree,
    }
    if payload != expected:
        raise EvidenceError("exact-head quick evidence does not match the current candidate")
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("record", "verify"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--expected-head", required=True)
    args = parser.parse_args()
    try:
        path = (
            record(args.root, args.expected_head)
            if args.mode == "record"
            else verify(args.root, args.expected_head)
        )
    except EvidenceError as exc:
        print(f"[local_quick_evidence] MISS {exc}")
        return 2
    print(f"[local_quick_evidence] {'RECORDED' if args.mode == 'record' else 'VERIFIED'} {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
