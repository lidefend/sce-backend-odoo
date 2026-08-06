#!/usr/bin/env python3
"""Create one governed, local-only linked worktree.

The target must be a new sibling of the primary repository, the branch must be
Codex-write eligible, and the exact base commit must already be reachable from
a local or origin remote-tracking branch.  Creation is dry-run unless both
``--apply`` and the exact confirmation phrase are supplied.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ALLOWED_BRANCH = re.compile(r"^(feature|fix|refactor|audit|release|codex)/.+$")
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
CONFIRMATION = "CREATE_GOVERNED_WORKTREE"


class CreateError(RuntimeError):
    pass


@dataclass(frozen=True)
class WorktreePlan:
    path: Path
    branch: str
    base: str


def run(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    process = subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if check and process.returncode:
        raise CreateError(f"git {' '.join(args)} failed: {process.stdout.strip()}")
    return process


def validate_plan(root: Path, candidate: Path, branch: str, base: str) -> WorktreePlan:
    root = root.resolve()
    if not candidate.is_absolute():
        raise CreateError("target path must be absolute")
    candidate = candidate.resolve(strict=False)
    if candidate.parent != root.parent:
        raise CreateError("target must be a direct sibling of the primary repository")
    if candidate == root or not candidate.name.startswith(f"{root.name}-"):
        raise CreateError(f"target name must start with {root.name}-")
    if candidate.exists():
        raise CreateError(f"target path already exists: {candidate}")

    if not ALLOWED_BRANCH.fullmatch(branch):
        raise CreateError(f"branch is not write-eligible: {branch}")
    if run(root, "check-ref-format", "--branch", branch, check=False).returncode:
        raise CreateError(f"invalid branch name: {branch}")
    if run(root, "show-ref", "--verify", "--quiet", f"refs/heads/{branch}", check=False).returncode == 0:
        raise CreateError(f"local branch already exists: {branch}")

    if not FULL_SHA.fullmatch(base):
        raise CreateError("base must be a full 40-character lowercase commit SHA")
    if run(root, "cat-file", "-e", f"{base}^{{commit}}", check=False).returncode:
        raise CreateError(f"base commit does not exist: {base}")
    containing_refs = run(
        root,
        "for-each-ref",
        "--format=%(refname)",
        "--contains",
        base,
        "refs/heads",
        "refs/remotes/origin",
    ).stdout.splitlines()
    if not containing_refs:
        raise CreateError("base commit is not reachable from a local or origin branch")

    registered = run(root, "worktree", "list", "--porcelain").stdout
    if f"worktree {candidate}\n" in registered:
        raise CreateError(f"target is already a registered worktree: {candidate}")
    return WorktreePlan(path=candidate, branch=branch, base=base)


def create(
    root: Path,
    candidate: Path,
    branch: str,
    base: str,
    *,
    apply: bool,
    confirmation: str,
) -> WorktreePlan:
    plan = validate_plan(root, candidate, branch, base)
    if not apply:
        return plan
    if confirmation != CONFIRMATION:
        raise CreateError(f"apply requires --confirm {CONFIRMATION}")
    run(root, "worktree", "add", "-b", plan.branch, "--", str(plan.path), plan.base)
    try:
        actual_branch = run(root, "-C", str(plan.path), "branch", "--show-current").stdout.strip()
        actual_head = run(root, "-C", str(plan.path), "rev-parse", "HEAD").stdout.strip()
        status = run(
            root,
            "-C",
            str(plan.path),
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
        ).stdout.strip()
        if actual_branch != plan.branch or actual_head != plan.base or status:
            raise CreateError("created worktree failed branch, HEAD, or cleanliness verification")
    except Exception:
        run(root, "worktree", "remove", "--force", "--", str(plan.path), check=False)
        run(root, "branch", "-D", "--", plan.branch, check=False)
        raise
    return plan


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", required=True)
    parser.add_argument("--branch", required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm", default="")
    args = parser.parse_args()
    try:
        root = Path(
            subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                check=True,
                text=True,
                stdout=subprocess.PIPE,
            ).stdout.strip()
        )
        current_branch = run(root, "branch", "--show-current").stdout.strip()
        if not ALLOWED_BRANCH.fullmatch(current_branch):
            raise CreateError(f"controller branch is not write-eligible: {current_branch}")
        plan = create(
            root,
            Path(args.path),
            args.branch,
            args.base,
            apply=args.apply,
            confirmation=args.confirm,
        )
    except (CreateError, subprocess.CalledProcessError) as exc:
        print(f"[workspace.worktree.create] DENY {exc}", file=sys.stderr)
        return 2
    mode = "APPLIED" if args.apply else "DRY_RUN"
    print(
        f"[workspace.worktree.create] {mode} "
        f"path={plan.path} branch={plan.branch} base={plan.base}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
