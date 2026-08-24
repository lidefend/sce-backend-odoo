#!/usr/bin/env python3
"""Fail-closed owner-authorized fast-forward integration for narrow P4 fixes."""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
P4_BRANCH = re.compile(r"^fix/p4-[a-z0-9][a-z0-9-]*$")
AUTHORIZATION = "OWNER_AUTHORIZED_P4_DIRECT_MAIN_FAST_FORWARD"
CANONICAL_ORIGINS = {"https://github.com/lidefend/sce-backend-odoo.git", "git@github.com:lidefend/sce-backend-odoo.git"}
ALLOWED_PREFIXES = ("docs/ops/", "docs/engineering_convergence/", "make/", "scripts/ops/", "scripts/verify/")


class IntegrateError(RuntimeError):
    pass


def env() -> dict[str, str]:
    return {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}


def git(root: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(["git", *args], cwd=root, env=env(), text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    if check and result.returncode:
        raise IntegrateError(f"git {' '.join(args)} failed: {result.stdout.strip()}")
    return result.stdout.strip()


def open_pr(branch: str) -> bool:
    result = subprocess.run(["gh", "pr", "list", "--state", "open", "--head", branch, "--json", "number", "--jq", "length"], env=env(), text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    if result.returncode:
        raise IntegrateError("unable to verify open PR state")
    return result.stdout.strip() != "0"


def require_sha(label: str, value: str) -> None:
    if not FULL_SHA.fullmatch(value):
        raise IntegrateError(f"{label} must be a full 40-character lowercase SHA")


def validate(root: Path, expected_root: Path, expected_head: str, expected_main: str, authorization: str, reference: str) -> tuple[str, tuple[str, ...]]:
    require_sha("EXPECTED_HEAD", expected_head)
    require_sha("EXPECTED_MAIN", expected_main)
    if authorization != AUTHORIZATION or not reference.strip():
        raise IntegrateError("owner authorization phrase and reference are required")
    root, expected_root = root.resolve(), expected_root.resolve()
    if Path(git(root, "rev-parse", "--show-toplevel")).resolve() != root or root != expected_root:
        raise IntegrateError("worktree path and expected repository root must match")
    branch = git(root, "branch", "--show-current")
    if not P4_BRANCH.fullmatch(branch):
        raise IntegrateError("only an eligible fix/p4-* branch may use owner integration")
    if git(root, "rev-parse", "HEAD") != expected_head or git(root, "status", "--porcelain=v1", "--untracked-files=all"):
        raise IntegrateError("HEAD identity mismatch or dirty worktree")
    if git(root, "remote", "get-url", "origin") not in CANONICAL_ORIGINS:
        raise IntegrateError("origin remote does not match governed repository identity")
    git(root, "fetch", "--no-tags", "origin", "main")
    if git(root, "rev-parse", "origin/main") != expected_main:
        raise IntegrateError("origin/main does not match EXPECTED_MAIN")
    if subprocess.run(["git", "merge-base", "--is-ancestor", expected_main, expected_head], cwd=root, env=env()).returncode:
        raise IntegrateError("candidate must fast-forward exact main")
    if git(root, "rev-list", "--merges", f"{expected_main}..{expected_head}"):
        raise IntegrateError("candidate contains merge commits")
    remote_branch = git(root, "ls-remote", "--heads", "origin", f"refs/heads/{branch}")
    if not remote_branch.startswith(expected_head):
        raise IntegrateError("remote P4 branch must exist at EXPECTED_HEAD")
    if open_pr(branch):
        raise IntegrateError("open PR exists; owner direct integration requires no PR")
    paths = tuple(sorted(filter(None, git(root, "diff", "--name-only", expected_main, expected_head).splitlines())))
    if not paths or any(not path.startswith(ALLOWED_PREFIXES) for path in paths):
        raise IntegrateError("candidate changes exceed the owner P4 path allowlist")
    return branch, paths


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-root", required=True)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--expected-main", required=True)
    parser.add_argument("--owner-authorization", required=True)
    parser.add_argument("--owner-authorization-reference", required=True)
    args = parser.parse_args()
    try:
        root = Path.cwd()
        branch, paths = validate(root, Path(args.expected_root), args.expected_head, args.expected_main, args.owner_authorization, args.owner_authorization_reference)
        result = subprocess.run(["git", "push", "origin", f"{args.expected_head}:refs/heads/main"], cwd=root, env=env(), text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
        if result.returncode:
            raise IntegrateError(f"non-force main fast-forward failed: {result.stdout.strip()}")
        git(root, "fetch", "--no-tags", "origin", "main")
        if git(root, "rev-parse", "origin/main") != args.expected_head:
            raise IntegrateError("post-push origin/main identity mismatch")
    except IntegrateError as exc:
        print(f"[main.owner-authorized-integrate] DENY {exc}", file=sys.stderr)
        return 2
    print(f"[main.owner-authorized-integrate] PASS branch={branch} new_main={args.expected_head} paths={len(paths)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
