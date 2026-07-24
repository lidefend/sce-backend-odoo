#!/usr/bin/env python3
"""Remove one clean, merged, non-primary linked worktree.

This is deliberately local-only: it removes neither remote branches nor
standalone clones.  The caller must opt in with ``--apply``.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ALLOWED_BRANCH = re.compile(r"^(feature|fix|refactor|audit|codex)/.+$")


class CleanupError(RuntimeError):
    pass


@dataclass(frozen=True)
class Worktree:
    path: Path
    branch: str | None
    head: str


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
        raise CleanupError(f"git {' '.join(args)} failed: {process.stdout.strip()}")
    return process


def parse_worktrees(output: str) -> list[Worktree]:
    worktrees: list[Worktree] = []
    for block in output.strip().split("\n\n"):
        fields: dict[str, str] = {}
        for line in block.splitlines():
            key, _, value = line.partition(" ")
            fields[key] = value
        if not fields.get("worktree") or not fields.get("HEAD"):
            continue
        branch_ref = fields.get("branch")
        branch = branch_ref.removeprefix("refs/heads/") if branch_ref else None
        worktrees.append(
            Worktree(path=Path(fields["worktree"]).resolve(), branch=branch, head=fields["HEAD"])
        )
    return worktrees


def plan_cleanup(root: Path, candidate: Path) -> Worktree:
    root = root.resolve()
    candidate = candidate.resolve()
    worktrees = parse_worktrees(run(root, "worktree", "list", "--porcelain").stdout)
    primary = next((item for item in worktrees if item.path == root), None)
    selected = next((item for item in worktrees if item.path == candidate), None)
    if primary is None:
        raise CleanupError("primary worktree is not registered")
    if selected is None:
        raise CleanupError(f"target is not a registered linked worktree: {candidate}")
    if selected.path == primary.path:
        raise CleanupError("refusing to remove the primary worktree")
    if not selected.branch:
        raise CleanupError("detached worktree cleanup is not permitted")
    if not ALLOWED_BRANCH.fullmatch(selected.branch):
        raise CleanupError(f"branch is not cleanup-eligible: {selected.branch}")
    if not selected.path.is_dir():
        raise CleanupError(f"worktree path is missing: {selected.path}")

    status = run(
        root,
        "-C",
        str(selected.path),
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
    ).stdout.strip()
    if status:
        raise CleanupError(f"worktree is not clean: {selected.path}")

    run(root, "fetch", "--prune", "origin")
    merged = run(
        root,
        "merge-base",
        "--is-ancestor",
        selected.head,
        "origin/main",
        check=False,
    )
    if merged.returncode != 0:
        raise CleanupError(f"worktree HEAD is not merged into origin/main: {selected.head}")
    return selected


def cleanup(root: Path, candidate: Path, *, apply: bool) -> Worktree:
    selected = plan_cleanup(root, candidate)
    if apply:
        run(root, "worktree", "remove", "--", str(selected.path))
        run(root, "branch", "-d", "--", selected.branch or "")
    return selected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", required=True)
    parser.add_argument("--apply", action="store_true")
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
        selected = cleanup(root, Path(args.path), apply=args.apply)
    except (CleanupError, subprocess.CalledProcessError) as exc:
        print(f"[workspace.worktree.cleanup] DENY {exc}", file=sys.stderr)
        return 2
    mode = "APPLIED" if args.apply else "DRY_RUN"
    print(
        f"[workspace.worktree.cleanup] {mode} "
        f"path={selected.path} branch={selected.branch} head={selected.head}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
