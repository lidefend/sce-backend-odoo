#!/usr/bin/env python3
"""Remove one clean, merged, non-primary linked worktree.

This is deliberately local-only: it removes neither remote branches nor
standalone clones.  The caller must opt in with ``--apply``.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ALLOWED_BRANCH = re.compile(r"^(feature|fix|refactor|audit|codex)/.+$")
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
ORPHAN_CONFIRMATION = "DELETE_VERIFIED_ORPHAN_BRANCH"
LOCAL_BRANCH_CONFIRMATION = "DELETE_VERIFIED_LOCAL_BRANCH"
SUPERSEDED_BRANCH_CONFIRMATION = "DELETE_VERIFIED_SUPERSEDED_LOCAL_BRANCH"


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


def run_gh(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    process = subprocess.run(
        ["gh", *args],
        cwd=root,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if process.returncode:
        raise CleanupError(f"gh {' '.join(args)} failed: {process.stdout.strip()}")
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


def assert_removal_permissions(path: Path) -> None:
    blocked: list[Path] = []
    if not os.access(path.parent, os.W_OK | os.X_OK):
        blocked.append(path.parent)
    for current, dirnames, _filenames in os.walk(path, topdown=True, followlinks=False):
        directory = Path(current)
        if os.access(directory, os.W_OK | os.X_OK):
            continue
        blocked.append(directory)
        dirnames[:] = []
    if blocked:
        rendered = ", ".join(str(item) for item in blocked[:3])
        suffix = " ..." if len(blocked) > 3 else ""
        raise CleanupError(f"worktree contains non-removable directories: {rendered}{suffix}")


def is_integrated(root: Path, head: str, branch: str) -> bool:
    merged = run(
        root,
        "merge-base",
        "--is-ancestor",
        head,
        "origin/main",
        check=False,
    )
    if merged.returncode == 0:
        return True
    selected_tree = run(root, "rev-parse", f"{head}^{{tree}}").stdout.strip()
    main_trees = {
        line.strip()
        for line in run(root, "log", "--format=%T", "origin/main").stdout.splitlines()
        if line.strip()
    }
    if selected_tree in main_trees:
        return True
    patch_rows = [
        line.strip()
        for line in run(root, "cherry", "origin/main", branch).stdout.splitlines()
        if line.strip()
    ]
    return bool(patch_rows) and all(line.startswith("-") for line in patch_rows)


def plan_cleanup(root: Path, candidate: Path) -> Worktree:
    root = root.resolve()
    candidate = candidate.resolve()
    worktrees = parse_worktrees(run(root, "worktree", "list", "--porcelain").stdout)
    primary = worktrees[0] if worktrees else None
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

    assert_removal_permissions(selected.path)

    run(root, "fetch", "--prune", "origin")
    if not is_integrated(root, selected.head, selected.branch):
        raise CleanupError(f"worktree HEAD is not merged into origin/main: {selected.head}")
    return selected


def cleanup_orphan_branch(
    root: Path,
    candidate: Path,
    *,
    branch: str,
    expected_head: str,
    apply: bool,
    confirmation: str,
) -> Worktree:
    root = root.resolve()
    candidate = candidate.resolve()
    if candidate.exists():
        raise CleanupError(f"orphan recovery path still exists: {candidate}")
    worktrees = parse_worktrees(run(root, "worktree", "list", "--porcelain").stdout)
    if any(item.path == candidate for item in worktrees):
        raise CleanupError(f"target is still a registered linked worktree: {candidate}")
    selected = cleanup_local_branch(
        root,
        branch=branch,
        expected_head=expected_head,
        apply=False,
        confirmation="",
    )
    if apply:
        if confirmation != ORPHAN_CONFIRMATION:
            raise CleanupError(
                f"orphan recovery apply requires confirmation={ORPHAN_CONFIRMATION}"
            )
        run(root, "update-ref", "-d", f"refs/heads/{branch}", selected.head)
    return Worktree(path=candidate, branch=branch, head=selected.head)


def cleanup_local_branch(
    root: Path,
    *,
    branch: str,
    expected_head: str,
    apply: bool,
    confirmation: str,
    refresh_origin: bool = True,
) -> Worktree:
    root = root.resolve()
    if not ALLOWED_BRANCH.fullmatch(branch):
        raise CleanupError(f"branch is not cleanup-eligible: {branch}")
    if not FULL_SHA.fullmatch(expected_head):
        raise CleanupError("local cleanup requires a full 40-character lowercase expected HEAD")
    worktrees = parse_worktrees(run(root, "worktree", "list", "--porcelain").stdout)
    if any(item.branch == branch for item in worktrees):
        raise CleanupError(f"branch is still checked out in a worktree: {branch}")
    ref = f"refs/heads/{branch}"
    actual_head = run(root, "rev-parse", "--verify", ref).stdout.strip()
    if actual_head != expected_head:
        raise CleanupError(
            f"branch HEAD changed: expected={expected_head} actual={actual_head}"
        )
    if refresh_origin:
        run(root, "fetch", "--prune", "origin")
    if not is_integrated(root, actual_head, branch):
        raise CleanupError(f"local branch HEAD is not merged into origin/main: {actual_head}")
    if apply:
        if confirmation != LOCAL_BRANCH_CONFIRMATION:
            raise CleanupError(
                f"local cleanup apply requires confirmation={LOCAL_BRANCH_CONFIRMATION}"
            )
        run(root, "update-ref", "-d", ref, actual_head)
    return Worktree(path=root, branch=branch, head=actual_head)


def cleanup_local_branches(
    root: Path,
    specs: list[tuple[str, str]],
    *,
    apply: bool,
    confirmation: str,
) -> list[Worktree]:
    if not specs:
        raise CleanupError("local batch cleanup requires at least one branch=SHA spec")
    branches = [branch for branch, _head in specs]
    if len(branches) != len(set(branches)):
        raise CleanupError("local batch cleanup contains duplicate branches")
    run(root.resolve(), "fetch", "--prune", "origin")
    selected = [
        cleanup_local_branch(
            root,
            branch=branch,
            expected_head=expected_head,
            apply=False,
            confirmation="",
            refresh_origin=False,
        )
        for branch, expected_head in specs
    ]
    if apply:
        if confirmation != LOCAL_BRANCH_CONFIRMATION:
            raise CleanupError(
                f"local batch cleanup apply requires confirmation={LOCAL_BRANCH_CONFIRMATION}"
            )
        for item in selected:
            run(root.resolve(), "update-ref", "-d", f"refs/heads/{item.branch}", item.head)
    return selected


def fetch_pr_head(root: Path, pr_number: int) -> str:
    run(root, "fetch", "origin", f"pull/{pr_number}/head")
    return run(root, "rev-parse", "FETCH_HEAD").stdout.strip()


def cleanup_superseded_local_branch(
    root: Path,
    *,
    branch: str,
    expected_head: str,
    pr_number: int,
    expected_pr_head: str,
    apply: bool,
    confirmation: str,
) -> Worktree:
    root = root.resolve()
    if not ALLOWED_BRANCH.fullmatch(branch):
        raise CleanupError(f"branch is not cleanup-eligible: {branch}")
    if not FULL_SHA.fullmatch(expected_head) or not FULL_SHA.fullmatch(expected_pr_head):
        raise CleanupError("superseded cleanup requires full lowercase branch and PR head SHAs")
    if pr_number <= 0:
        raise CleanupError("superseded cleanup requires a positive merged PR number")
    worktrees = parse_worktrees(run(root, "worktree", "list", "--porcelain").stdout)
    if any(item.branch == branch for item in worktrees):
        raise CleanupError(f"branch is still checked out in a worktree: {branch}")
    ref = f"refs/heads/{branch}"
    actual_head = run(root, "rev-parse", "--verify", ref).stdout.strip()
    if actual_head != expected_head:
        raise CleanupError(
            f"branch HEAD changed: expected={expected_head} actual={actual_head}"
        )

    try:
        evidence = json.loads(
            run_gh(
                root,
                "pr",
                "view",
                str(pr_number),
                "--json",
                "state,mergedAt,baseRefName,headRefOid,mergeCommit",
            ).stdout
        )
    except json.JSONDecodeError as exc:
        raise CleanupError("merged PR evidence is not valid JSON") from exc
    merge_commit = evidence.get("mergeCommit")
    merge_sha = merge_commit.get("oid") if isinstance(merge_commit, dict) else ""
    if (
        evidence.get("state") != "MERGED"
        or not evidence.get("mergedAt")
        or evidence.get("baseRefName") != "main"
        or evidence.get("headRefOid") != expected_pr_head
        or not FULL_SHA.fullmatch(str(merge_sha or ""))
    ):
        raise CleanupError("merged PR identity does not match the requested supersession")

    run(root, "fetch", "--prune", "origin")
    fetched_pr_head = fetch_pr_head(root, pr_number)
    if fetched_pr_head != expected_pr_head:
        raise CleanupError(
            f"PR head changed: expected={expected_pr_head} actual={fetched_pr_head}"
        )
    if run(
        root, "merge-base", "--is-ancestor", str(merge_sha), "origin/main", check=False
    ).returncode:
        raise CleanupError(f"merged PR commit is not contained in origin/main: {merge_sha}")
    if run(
        root, "merge-base", "--is-ancestor", actual_head, expected_pr_head, check=False
    ).returncode:
        raise CleanupError(
            f"local branch is not an ancestor of merged PR head: {actual_head}"
        )
    if apply:
        if confirmation != SUPERSEDED_BRANCH_CONFIRMATION:
            raise CleanupError(
                "superseded cleanup apply requires "
                f"confirmation={SUPERSEDED_BRANCH_CONFIRMATION}"
            )
        run(root, "update-ref", "-d", ref, actual_head)
    return Worktree(path=root, branch=branch, head=actual_head)


def parse_local_branch_specs(value: str) -> list[tuple[str, str]]:
    specs: list[tuple[str, str]] = []
    for raw in value.split(","):
        item = raw.strip()
        if not item:
            continue
        branch, separator, expected_head = item.rpartition("=")
        if not separator or not branch or not expected_head:
            raise CleanupError(f"invalid local branch spec: {item}")
        specs.append((branch, expected_head))
    return specs


def cleanup(root: Path, candidate: Path, *, apply: bool) -> Worktree:
    selected = plan_cleanup(root, candidate)
    if apply:
        run(root, "worktree", "remove", "--", str(selected.path))
        # The ancestry check above is against the authoritative origin/main,
        # while `git branch -d` checks merge state against the controller
        # worktree's current HEAD.  Those refs can legitimately differ and
        # previously left a removed worktree's branch behind.  Delete only the
        # exact ref value that was already verified, so a concurrent branch
        # advance fails closed instead of being discarded.
        run(
            root,
            "update-ref",
            "-d",
            f"refs/heads/{selected.branch}",
            selected.head,
        )
    return selected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--orphan-branch")
    parser.add_argument("--local-branch")
    parser.add_argument("--local-branch-specs", default="")
    parser.add_argument("--superseded-local-branch")
    parser.add_argument("--merged-pr", type=int, default=0)
    parser.add_argument("--expected-pr-head", default="")
    parser.add_argument("--expected-head", default="")
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
        selected_modes = sum(
            bool(value)
            for value in (
                args.orphan_branch,
                args.local_branch,
                args.local_branch_specs,
                args.superseded_local_branch,
            )
        )
        if selected_modes > 1:
            raise CleanupError("choose one cleanup mode")
        if args.local_branch_specs:
            selected_batch = cleanup_local_branches(
                root,
                parse_local_branch_specs(args.local_branch_specs),
                apply=args.apply,
                confirmation=args.confirm,
            )
            mode = "APPLIED" if args.apply else "DRY_RUN"
            for selected in selected_batch:
                print(
                    f"[workspace.worktree.cleanup] {mode} "
                    f"branch={selected.branch} head={selected.head}"
                )
            return 0
        if args.superseded_local_branch:
            selected = cleanup_superseded_local_branch(
                root,
                branch=args.superseded_local_branch,
                expected_head=args.expected_head,
                pr_number=args.merged_pr,
                expected_pr_head=args.expected_pr_head,
                apply=args.apply,
                confirmation=args.confirm,
            )
        elif args.local_branch:
            selected = cleanup_local_branch(
                root,
                branch=args.local_branch,
                expected_head=args.expected_head,
                apply=args.apply,
                confirmation=args.confirm,
            )
        elif args.orphan_branch:
            selected = cleanup_orphan_branch(
                root,
                Path(args.path),
                branch=args.orphan_branch,
                expected_head=args.expected_head,
                apply=args.apply,
                confirmation=args.confirm,
            )
        else:
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
