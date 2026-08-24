#!/usr/bin/env python3
"""Fail-closed main-baseline sync for an unpublished local delivery branch.

This is the only governed path that may invoke ``git rebase``.  It never pushes
or alters a public branch, and it leaves a locally verifiable recovery bundle
before replaying the branch's responsibility commits on an exact origin/main.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


ALLOWED_BRANCH = re.compile(r"^(feature|fix|refactor|audit|release|codex)/.+$")
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
CONFIRMATION = "REBASE_UNPUBLISHED_BRANCH_ON_EXACT_MAIN"
MAX_RESPONSIBILITY_COMMITS = 12
APPEND_ONLY_CONFLICT_PATH = "docs/ops/iterations/delivery_context_switch_log_v1.md"
CANONICAL_ORIGIN_URLS = {
    "https://github.com/lidefend/sce-backend-odoo.git",
    "git@github.com:lidefend/sce-backend-odoo.git",
}


class SyncError(RuntimeError):
    pass


@dataclass(frozen=True)
class SyncPlan:
    root: Path
    branch: str
    head: str
    old_base: str
    new_main: str
    commit_count: int
    paths: tuple[str, ...]
    recovery_bundle: Path


def sanitized_environment() -> dict[str, str]:
    """Do not inherit caller-controlled Git execution identity."""
    return {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}


def run(root: Path, *args: str, check: bool = True, input: str | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *args], cwd=root, env=sanitized_environment(), text=True,
        input=input, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
    )
    if check and result.returncode:
        raise SyncError(f"git {' '.join(args)} failed: {result.stdout.strip()}")
    return result


def git_output(root: Path, *args: str) -> str:
    return run(root, *args).stdout.strip()


def ensure_sha(label: str, value: str) -> None:
    if not FULL_SHA.fullmatch(value):
        raise SyncError(f"{label} must be a full 40-character lowercase SHA")


def has_open_pr(branch: str) -> bool:
    """Published or review-visible work must never have its history rewritten."""
    result = subprocess.run(
        ["gh", "pr", "list", "--state", "open", "--head", branch, "--json", "number", "--jq", "length"],
        env=sanitized_environment(), text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
    )
    if result.returncode:
        raise SyncError("unable to verify open PR state; refuse branch sync")
    return result.stdout.strip() != "0"


def has_canonical_origin(root: Path) -> bool:
    return git_output(root, "remote", "get-url", "origin") in CANONICAL_ORIGIN_URLS


def require_clean(root: Path) -> None:
    if git_output(root, "status", "--porcelain=v1", "--untracked-files=all"):
        raise SyncError("worktree must be clean, including untracked files")


def common_git_dir(root: Path) -> Path:
    return Path(git_output(root, "rev-parse", "--path-format=absolute", "--git-common-dir")).resolve()


def require_no_writer(root: Path) -> None:
    common = common_git_dir(root)
    locks = (common / "index.lock", common / "packed-refs.lock", common / "rebase-merge", common / "rebase-apply")
    if any(path.exists() for path in locks):
        raise SyncError("Git writer or unfinished history operation is active")
    if run(root, "rev-parse", "-q", "--verify", "MERGE_HEAD", check=False).returncode == 0:
        raise SyncError("unfinished merge is active")


def ref_exists(root: Path, ref: str) -> bool:
    return run(root, "show-ref", "--verify", "--quiet", ref, check=False).returncode == 0


def commit_exists(root: Path, sha: str) -> bool:
    return run(root, "cat-file", "-e", f"{sha}^{{commit}}", check=False).returncode == 0


def commit_paths(root: Path, left: str, right: str) -> tuple[str, ...]:
    return tuple(sorted(filter(None, git_output(root, "diff", "--name-only", left, right).splitlines())))


def patch_id(root: Path, left: str, right: str) -> str:
    diff = run(root, "diff", "--binary", left, right).stdout
    result = subprocess.run(
        ["git", "patch-id", "--stable"], cwd=root, env=sanitized_environment(), input=diff,
        text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
    )
    if result.returncode or not result.stdout.strip():
        raise SyncError("unable to calculate responsibility patch identity")
    return result.stdout.split()[0]


def recovery_path(root: Path, branch: str, head: str) -> Path:
    safe_branch = branch.replace("/", "-")
    return common_git_dir(root) / "codex-recovery" / "branch-sync" / f"{safe_branch}-{head}.bundle"


def validate(
    *, root: Path, expected_root: Path, governance_root: Path, expected_branch: str, expected_head: str,
    expected_old_base: str, expected_main: str, pr_checker: Callable[[str], bool] = has_open_pr,
    origin_checker: Callable[[Path], bool] = has_canonical_origin,
) -> SyncPlan:
    root = root.resolve()
    expected_root = expected_root.resolve()
    governance_root = governance_root.resolve()
    for label, value in (("EXPECTED_HEAD", expected_head), ("EXPECTED_OLD_BASE", expected_old_base), ("EXPECTED_MAIN", expected_main)):
        ensure_sha(label, value)
    actual_root = Path(git_output(root, "rev-parse", "--show-toplevel")).resolve()
    if root != actual_root or expected_root != actual_root:
        raise SyncError("worktree path and expected repository root must match")
    actual_governance_root = Path(
        git_output(governance_root, "rev-parse", "--show-toplevel")
    ).resolve()
    if governance_root != actual_governance_root:
        raise SyncError("governance root must be a repository root")
    if common_git_dir(root) != common_git_dir(governance_root):
        raise SyncError("worktree must share the governance repository identity")
    actual_branch = git_output(root, "branch", "--show-current")
    if actual_branch != expected_branch or not ALLOWED_BRANCH.fullmatch(actual_branch):
        raise SyncError("current branch does not match a write-eligible expected branch")
    actual_head = git_output(root, "rev-parse", "HEAD")
    if actual_head != expected_head:
        raise SyncError("current HEAD does not match EXPECTED_HEAD")
    require_clean(root)
    require_no_writer(root)
    if not origin_checker(root):
        raise SyncError("origin remote does not match the governed repository identity")
    run(root, "fetch", "--no-tags", "origin", "main")
    if not ref_exists(root, "refs/remotes/origin/main"):
        raise SyncError("origin/main is unavailable")
    actual_main = git_output(root, "rev-parse", "origin/main")
    if actual_main != expected_main:
        raise SyncError("origin/main does not match EXPECTED_MAIN")
    if not commit_exists(root, expected_old_base):
        raise SyncError("EXPECTED_OLD_BASE does not name an available commit")
    if not commit_exists(root, expected_main):
        raise SyncError("EXPECTED_MAIN does not name an available commit")
    if git_output(root, "merge-base", "HEAD", "origin/main") != expected_old_base:
        raise SyncError("merge base does not match EXPECTED_OLD_BASE")
    if run(root, "merge-base", "--is-ancestor", expected_old_base, expected_main, check=False).returncode:
        raise SyncError("EXPECTED_OLD_BASE must be an ancestor of EXPECTED_MAIN")
    if ref_exists(root, f"refs/remotes/origin/{actual_branch}"):
        raise SyncError("remote branch already exists; published history cannot be rewritten")
    remote = run(root, "ls-remote", "--heads", "origin", f"refs/heads/{actual_branch}").stdout.strip()
    if remote:
        raise SyncError("remote branch already exists; published history cannot be rewritten")
    if pr_checker(actual_branch):
        raise SyncError("open PR exists; published history cannot be rewritten")
    merges = git_output(root, "rev-list", "--merges", f"{expected_old_base}..{expected_head}")
    if merges:
        raise SyncError("responsibility branch contains merge commits")
    commits = tuple(filter(None, git_output(root, "rev-list", "--reverse", f"{expected_old_base}..{expected_head}").splitlines()))
    if not 1 <= len(commits) <= MAX_RESPONSIBILITY_COMMITS:
        raise SyncError(f"responsibility commit count must be within 1..{MAX_RESPONSIBILITY_COMMITS}")
    paths = commit_paths(root, expected_old_base, expected_head)
    if not paths:
        raise SyncError("responsibility branch has no changed paths")
    return SyncPlan(root, actual_branch, actual_head, expected_old_base, expected_main, len(commits), paths, recovery_path(root, actual_branch, actual_head))


def create_bundle(plan: SyncPlan) -> None:
    plan.recovery_bundle.parent.mkdir(parents=True, exist_ok=True)
    run(
        plan.root,
        "bundle",
        "create",
        str(plan.recovery_bundle),
        f"refs/heads/{plan.branch}",
        f"^{plan.old_base}",
    )
    run(plan.root, "bundle", "verify", str(plan.recovery_bundle))


def text_at_revision(root: Path, revision: str, path: str) -> str:
    result = run(root, "show", f"{revision}:{path}", check=False)
    if result.returncode:
        raise SyncError(f"append-only conflict source is unavailable: {path}")
    return result.stdout


def resolve_append_only_log_conflict(plan: SyncPlan) -> bool:
    """Resolve only a pure append conflict in the formal delivery log.

    Both branch versions must retain the old-base text verbatim and only append
    new entries. The result keeps main's entries first, then appends the local
    branch's suffix. Any other conflict remains a fail-closed abort.
    """
    conflicts = tuple(
        sorted(
            filter(
                None,
                git_output(plan.root, "diff", "--name-only", "--diff-filter=U").splitlines(),
            )
        )
    )
    if conflicts != (APPEND_ONLY_CONFLICT_PATH,):
        return False
    base = text_at_revision(plan.root, plan.old_base, APPEND_ONLY_CONFLICT_PATH)
    main = text_at_revision(plan.root, plan.new_main, APPEND_ONLY_CONFLICT_PATH)
    topic = text_at_revision(plan.root, plan.head, APPEND_ONLY_CONFLICT_PATH)
    if not main.startswith(base) or not topic.startswith(base):
        return False
    target = plan.root / APPEND_ONLY_CONFLICT_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(main + topic[len(base):], encoding="utf-8")
    run(plan.root, "add", "--", APPEND_ONLY_CONFLICT_PATH)
    return True


def run_rebase(plan: SyncPlan) -> bool | None:
    append_only_log_resolved = False
    result = run(plan.root, "rebase", "--onto", plan.new_main, plan.old_base, check=False)
    while result.returncode:
        if not resolve_append_only_log_conflict(plan):
            return None
        append_only_log_resolved = True
        result = run(plan.root, "-c", "core.editor=true", "rebase", "--continue", check=False)
    return append_only_log_resolved


def verify_append_only_log_resolution(plan: SyncPlan) -> None:
    base = text_at_revision(plan.root, plan.old_base, APPEND_ONLY_CONFLICT_PATH)
    main = text_at_revision(plan.root, plan.new_main, APPEND_ONLY_CONFLICT_PATH)
    topic = text_at_revision(plan.root, plan.head, APPEND_ONLY_CONFLICT_PATH)
    current = (plan.root / APPEND_ONLY_CONFLICT_PATH).read_text(encoding="utf-8")
    if not main.startswith(base) or not topic.startswith(base):
        raise SyncError("append-only conflict inputs changed during sync")
    if current != main + topic[len(base):]:
        raise SyncError("append-only delivery log suffix was not preserved")


def sync(plan: SyncPlan) -> str:
    create_bundle(plan)
    append_only_log_resolved = run_rebase(plan)
    if append_only_log_resolved is None:
        aborted = run(plan.root, "rebase", "--abort", check=False)
        restored_head = git_output(plan.root, "rev-parse", "HEAD")
        require_clean(plan.root)
        if aborted.returncode or restored_head != plan.head:
            raise SyncError("rebase conflict and automatic recovery failed; use recovery bundle")
        raise SyncError("rebase conflict; aborted and restored original HEAD")
    new_head = git_output(plan.root, "rev-parse", "HEAD")
    require_clean(plan.root)
    new_commits = tuple(filter(None, git_output(plan.root, "rev-list", "--reverse", f"{plan.new_main}..{new_head}").splitlines()))
    if len(new_commits) != plan.commit_count:
        raise SyncError("responsibility commit count changed after sync")
    if commit_paths(plan.root, plan.new_main, new_head) != plan.paths:
        raise SyncError("responsibility path set changed after sync")
    if append_only_log_resolved:
        verify_append_only_log_resolution(plan)
    elif patch_id(plan.root, plan.old_base, plan.head) != patch_id(plan.root, plan.new_main, new_head):
        raise SyncError("responsibility patch identity changed after sync")
    return new_head


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-root", required=True)
    parser.add_argument("--governance-root", required=True)
    parser.add_argument("--expected-branch", required=True)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--expected-old-base", required=True)
    parser.add_argument("--expected-main", required=True)
    parser.add_argument("--confirm", required=True)
    args = parser.parse_args()
    if args.confirm != CONFIRMATION:
        print(f"[workspace.branch.sync-main] DENY confirmation must equal {CONFIRMATION}", file=sys.stderr)
        return 2
    try:
        plan = validate(
            root=Path.cwd(), expected_root=Path(args.expected_root), governance_root=Path(args.governance_root),
            expected_branch=args.expected_branch,
            expected_head=args.expected_head, expected_old_base=args.expected_old_base,
            expected_main=args.expected_main,
        )
        new_head = sync(plan)
    except SyncError as exc:
        print(f"[workspace.branch.sync-main] DENY {exc}", file=sys.stderr)
        return 2
    print(f"[workspace.branch.sync-main] PASS branch={plan.branch} old_head={plan.head} new_head={new_head} recovery_bundle={plan.recovery_bundle}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
