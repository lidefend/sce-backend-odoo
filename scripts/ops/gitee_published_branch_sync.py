#!/usr/bin/env python3
"""Append exact main to a candidate; never rewrite or push history.

Two modes share one merge, recovery and identity path:

* published (default): the candidate already has a same-name remote branch, whose
  head must stay an ancestor of the local head.
* unpublished (``--allow-absent``): the candidate has no same-name remote branch
  yet. Absence must be proven by a *successful* ``ls-remote``; a failed check is
  never accepted as absence. If the branch appears at any point, the run stops
  instead of overwriting it.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

URLS = {"git@gitee.com:leegege/sce-product-odoo.git", "https://gitee.com/leegege/sce-product-odoo.git"}
CONFIRM = "APPEND_EXACT_MAIN_TO_PUBLISHED_CANDIDATE"
CONFIRM_UNPUBLISHED = "APPEND_EXACT_MAIN_TO_UNPUBLISHED_CANDIDATE"


def git(root, *args, check=True):
    p = subprocess.run(["git", *args], cwd=root, text=True, capture_output=True)
    if check and p.returncode:
        raise RuntimeError(p.stderr.strip() or p.stdout.strip())
    return p


def out(root, *args):
    return git(root, *args).stdout.strip()


def remote_refs(root, branch):
    """Return the observed head refs, or raise. A failed check is never absence."""
    rows = out(root, "ls-remote", "gitee-mirror", "refs/heads/main", "refs/heads/" + branch)
    return dict(line.split()[::-1] for line in rows.splitlines())


def inspect(root, branch, head, main, allowed_urls=URLS, remote_head=None, allow_absent=False):
    if allow_absent and remote_head:
        raise RuntimeError("unpublished mode cannot pin a remote head")
    remote_head = None if allow_absent else (remote_head or head)
    root = Path(root).resolve()
    if not re.fullmatch(r"(feature|fix|refactor|audit|release|codex)/.+", branch):
        raise RuntimeError("candidate branch required")
    if any(not re.fullmatch(r"[0-9a-f]{40}", s) for s in (head, main)):
        raise RuntimeError("full exact SHA required")
    if remote_head is not None and not re.fullmatch(r"[0-9a-f]{40}", remote_head):
        raise RuntimeError("full exact SHA required")
    if Path(out(root, "rev-parse", "--show-toplevel")).resolve() != root:
        raise RuntimeError("repository root mismatch")
    if out(root, "status", "--porcelain"):
        raise RuntimeError("clean candidate required")
    if out(root, "branch", "--show-current") != branch or out(root, "rev-parse", "HEAD") != head:
        raise RuntimeError("candidate identity changed")
    if out(root, "remote", "get-url", "gitee-mirror") not in allowed_urls:
        raise RuntimeError("unexpected Gitee remote")
    refs = remote_refs(root, branch)
    if refs.get("refs/heads/main") != main:
        raise RuntimeError("remote identity drift")
    if allow_absent:
        if "refs/heads/" + branch in refs:
            raise RuntimeError("remote branch already exists; use the published entry")
    else:
        if refs.get("refs/heads/" + branch) != remote_head:
            raise RuntimeError("remote identity drift")
        if git(root, "merge-base", "--is-ancestor", remote_head, head, check=False).returncode:
            raise RuntimeError("local candidate rewrites published history")
    return root


def sync(root, branch, head, main, apply=False, confirm="", allowed_urls=URLS, remote_head=None,
         allow_absent=False):
    mode = "unpublished" if allow_absent else "published"
    root = inspect(root, branch, head, main, allowed_urls, remote_head, allow_absent)
    git(root, "fetch", "gitee-mirror", "main")
    if out(root, "rev-parse", "FETCH_HEAD") != main:
        raise RuntimeError("main changed during fetch")
    if not apply:
        return {"writes": 0, "head": head, "main": main, "mode": mode}
    if confirm != (CONFIRM_UNPUBLISHED if allow_absent else CONFIRM):
        raise RuntimeError("exact confirmation required")
    inspect(root, branch, head, main, allowed_urls, remote_head, allow_absent)
    if git(root, "merge-base", "--is-ancestor", main, head, check=False).returncode == 0:
        return {"changed": False, "head": head, "main": main}
    recovery = Path(out(root, "rev-parse", "--path-format=absolute", "--git-common-dir")) / "codex/recovery"
    recovery.mkdir(parents=True, exist_ok=True)
    bundle = recovery / ("published-sync-" + head + "-" + main + ".bundle")
    if not bundle.exists():
        git(root, "bundle", "create", str(bundle), "HEAD")
    git(root, "bundle", "verify", str(bundle))
    if head not in out(root, "bundle", "list-heads", str(bundle)).split():
        raise RuntimeError("recovery identity mismatch")
    result = git(root, "merge", "--no-ff", "--no-commit", main, check=False)
    if result.returncode:
        if git(root, "rev-parse", "--verify", "MERGE_HEAD", check=False).returncode == 0:
            git(root, "merge", "--abort")
        raise RuntimeError("merge conflict; original candidate restored: " + result.stdout)
    try:
        git(root, "diff", "--check", "--cached")
        git(root, "commit", "-m", "merge: synchronize candidate with reviewed main " + main[:8])
    except Exception:
        if git(root, "rev-parse", "--verify", "MERGE_HEAD", check=False).returncode == 0:
            git(root, "merge", "--abort")
        raise
    new_head = out(root, "rev-parse", "HEAD")
    parents = out(root, "show", "-s", "--format=%P", new_head).split()
    if parents != [head, main] or out(root, "status", "--porcelain"):
        raise RuntimeError("post-sync identity mismatch; preserve recovery bundle")
    return {"changed": True, "old_head": head, "head": new_head, "main": main,
            "recovery_bundle": str(bundle), "bundle_sha256": hashlib.sha256(bundle.read_bytes()).hexdigest(),
            "published": False, "mode": mode, "ci_required": True}


def sync_local_main(root, branch, head, main, old_main, apply=False, confirm="", allowed_urls=URLS):
    """Fast-forward only the unoccupied local main ref; retain topic worktree."""
    root = Path(root).resolve()
    def check():
        if not re.fullmatch(r"(feature|fix|refactor|audit|release|codex)/.+", branch):
            raise RuntimeError("candidate branch required")
        if any(not re.fullmatch(r"[0-9a-f]{40}", v) for v in (head, main, old_main)):
            raise RuntimeError("full exact SHA required")
        if Path(out(root, "rev-parse", "--show-toplevel")).resolve() != root:
            raise RuntimeError("repository root mismatch")
        if out(root, "status", "--porcelain"):
            raise RuntimeError("clean candidate required")
        if out(root, "branch", "--show-current") != branch or out(root, "rev-parse", "HEAD") != head:
            raise RuntimeError("candidate identity changed")
        if out(root, "remote", "get-url", "gitee-mirror") not in allowed_urls:
            raise RuntimeError("unexpected Gitee remote")
        if git(root, "symbolic-ref", "-q", "refs/heads/main", check=False).returncode == 0:
            raise RuntimeError("symbolic local main refused")
        if out(root, "rev-parse", "refs/heads/main") != old_main:
            raise RuntimeError("local main drift")
        if "branch refs/heads/main" in out(root, "worktree", "list", "--porcelain").splitlines():
            raise RuntimeError("local main occupied by worktree")
        if remote_refs(root, branch).get("refs/heads/main") != main:
            raise RuntimeError("remote identity drift")
    check()
    git(root, "fetch", "gitee-mirror", "main")
    if out(root, "rev-parse", "FETCH_HEAD") != main:
        raise RuntimeError("main changed during fetch")
    if git(root, "merge-base", "--is-ancestor", old_main, main, check=False).returncode:
        raise RuntimeError("local main is not a fast-forward")
    if not apply:
        return {"writes": 0, "old_main": old_main, "main": main, "head": head}
    if confirm != "FAST_FORWARD_EXACT_LOCAL_GITEE_MAIN":
        raise RuntimeError("exact confirmation required")
    check()
    git(root, "update-ref", "--no-deref", "-m", "governed Gitee local main fast-forward", "refs/heads/main", main, old_main)
    if out(root, "rev-parse", "refs/heads/main") != main or out(root, "rev-parse", "HEAD") != head or out(root, "status", "--porcelain"):
        raise RuntimeError("post-sync identity mismatch")
    return {"changed": old_main != main, "old_main": old_main, "main": main,
            "head": head, "worktree_changed": False, "remote_writes": 0}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    for name in ("root", "branch", "head", "main"):
        p.add_argument("--" + name, required=True)
    p.add_argument("--local-main", action="store_true")
    p.add_argument("--old-main")
    p.add_argument("--remote-head")
    p.add_argument("--allow-absent", action="store_true")
    p.add_argument("--apply", action="store_true")
    p.add_argument("--confirm", default="")
    args = vars(p.parse_args())
    local_main = args.pop("local_main")
    old_main = args.pop("old_main")
    if local_main:
        if not old_main or args.pop("remote_head") or args.pop("allow_absent"):
            p.error("local-main requires old-main and rejects candidate sync flags")
        result = sync_local_main(**args, old_main=old_main)
    else:
        if old_main: p.error("old-main requires local-main")
        result = sync(**args)
    print(json.dumps(result, sort_keys=True))
