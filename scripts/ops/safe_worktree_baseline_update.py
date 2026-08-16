#!/usr/bin/env python3
"""Update a clean linked worktree to the exact current main baseline.

The operation is dry-run by default.  Merge preserves published history;
rebase is restricted to branches that do not exist on origin.
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
CONFIRMATION = "UPDATE_GOVERNED_WORKTREE_BASELINE"


class UpdateError(RuntimeError):
    pass


@dataclass(frozen=True)
class Worktree:
    path: Path
    branch: str | None
    head: str


def run(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    process = subprocess.run(
        ["git", *args], cwd=root, check=False, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    if check and process.returncode:
        raise UpdateError(f"git {' '.join(args)} failed: {process.stdout.strip()}")
    return process


def parse_worktrees(output: str) -> list[Worktree]:
    result: list[Worktree] = []
    for block in output.strip().split("\n\n"):
        fields: dict[str, str] = {}
        for line in block.splitlines():
            key, _, value = line.partition(" ")
            fields[key] = value
        if fields.get("worktree") and fields.get("HEAD"):
            branch_ref = fields.get("branch")
            result.append(Worktree(
                Path(fields["worktree"]).resolve(),
                branch_ref.removeprefix("refs/heads/") if branch_ref else None,
                fields["HEAD"],
            ))
    return result


def validate(root: Path, candidate: Path, expected_head: str, baseline: str, mode: str) -> Worktree:
    root = root.resolve()
    candidate = candidate.resolve()
    if mode not in {"merge", "rebase"}:
        raise UpdateError("mode must be merge or rebase")
    if not FULL_SHA.fullmatch(expected_head) or not FULL_SHA.fullmatch(baseline):
        raise UpdateError("expected HEAD and baseline must be full lowercase commit SHAs")

    worktrees = parse_worktrees(run(root, "worktree", "list", "--porcelain").stdout)
    primary = worktrees[0] if worktrees else None
    selected = next((item for item in worktrees if item.path == candidate), None)
    if primary is None or selected is None:
        raise UpdateError("target must be a registered linked worktree")
    if selected.path == primary.path:
        raise UpdateError("refusing to update the primary worktree")
    if not selected.branch or not ALLOWED_BRANCH.fullmatch(selected.branch):
        raise UpdateError("target branch is not write-eligible")
    if selected.head != expected_head:
        raise UpdateError(f"worktree HEAD changed: expected={expected_head} actual={selected.head}")
    branch_head = run(root, "rev-parse", "--verify", f"refs/heads/{selected.branch}").stdout.strip()
    if branch_head != expected_head:
        raise UpdateError("branch HEAD does not match the frozen worktree HEAD")
    status = run(root, "-C", str(selected.path), "status", "--porcelain=v1", "--untracked-files=all").stdout.strip()
    if status:
        raise UpdateError("target worktree must be clean")

    for operation in ("rebase-merge", "rebase-apply", "MERGE_HEAD", "CHERRY_PICK_HEAD"):
        git_path = run(root, "-C", str(selected.path), "rev-parse", "--git-path", operation).stdout.strip()
        if Path(git_path).exists():
            raise UpdateError(f"unfinished Git operation detected: {operation}")

    run(root, "fetch", "--prune", "origin", "main")
    origin_main = run(root, "rev-parse", "origin/main").stdout.strip()
    if baseline != origin_main:
        raise UpdateError(f"baseline must equal current origin/main: expected={origin_main} actual={baseline}")
    if mode == "rebase":
        remote = run(root, "ls-remote", "--exit-code", "--heads", "origin", selected.branch, check=False)
        if remote.returncode == 0 and remote.stdout.strip():
            raise UpdateError("rebase is forbidden for a branch already published on origin; use merge")
    return selected


def update(root: Path, candidate: Path, expected_head: str, baseline: str, mode: str, *, apply: bool, confirmation: str) -> tuple[Worktree, str]:
    selected = validate(root, candidate, expected_head, baseline, mode)
    if not apply:
        return selected, selected.head
    if confirmation != CONFIRMATION:
        raise UpdateError(f"apply requires --confirm {CONFIRMATION}")

    command = ["rebase", "--rebase-merges", baseline] if mode == "rebase" else ["merge", "--no-edit", "--no-ff", baseline]
    process = run(root, "-C", str(selected.path), *command, check=False)
    if process.returncode:
        abort = ["rebase", "--abort"] if mode == "rebase" else ["merge", "--abort"]
        run(root, "-C", str(selected.path), *abort, check=False)
        restored = run(root, "-C", str(selected.path), "rev-parse", "HEAD").stdout.strip()
        clean = not run(root, "-C", str(selected.path), "status", "--porcelain=v1", "--untracked-files=all").stdout.strip()
        if restored != expected_head or not clean:
            raise UpdateError("baseline update failed and automatic rollback could not restore the frozen worktree")
        raise UpdateError(f"baseline update conflicts; operation aborted with zero candidate drift: {process.stdout.strip()}")

    new_head = run(root, "-C", str(selected.path), "rev-parse", "HEAD").stdout.strip()
    if run(root, "merge-base", "--is-ancestor", baseline, new_head, check=False).returncode:
        raise UpdateError("updated branch does not contain the requested baseline")
    if run(root, "-C", str(selected.path), "status", "--porcelain=v1", "--untracked-files=all").stdout.strip():
        raise UpdateError("updated worktree is not clean")
    return selected, new_head


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", required=True)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--mode", choices=("merge", "rebase"), required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm", default="")
    args = parser.parse_args()
    try:
        root = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], check=True, text=True, stdout=subprocess.PIPE).stdout.strip())
        selected, new_head = update(root, Path(args.path), args.expected_head, args.baseline, args.mode, apply=args.apply, confirmation=args.confirm)
    except (UpdateError, subprocess.CalledProcessError) as exc:
        print(f"[workspace.worktree.baseline.update] DENY {exc}", file=sys.stderr)
        return 2
    mode = "APPLIED" if args.apply else "DRY_RUN"
    print(f"[workspace.worktree.baseline.update] {mode} path={selected.path} branch={selected.branch} old_head={selected.head} new_head={new_head} baseline={args.baseline} strategy={args.mode}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
