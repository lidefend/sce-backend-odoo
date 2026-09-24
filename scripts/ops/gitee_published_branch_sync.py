#!/usr/bin/env python3
"""Append exact main to a published candidate; never rewrite or push history."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

URLS = {"git@gitee.com:leegege/sce-product-odoo.git", "https://gitee.com/leegege/sce-product-odoo.git"}
CONFIRM = "APPEND_EXACT_MAIN_TO_PUBLISHED_CANDIDATE"


def git(root, *args, check=True):
    p = subprocess.run(["git", *args], cwd=root, text=True, capture_output=True)
    if check and p.returncode:
        raise RuntimeError(p.stderr.strip() or p.stdout.strip())
    return p


def out(root, *args):
    return git(root, *args).stdout.strip()


def inspect(root, branch, head, main, allowed_urls=URLS):
    root = Path(root).resolve()
    if not re.fullmatch(r"(feature|fix|refactor|audit|release|codex)/.+", branch):
        raise RuntimeError("candidate branch required")
    if any(not re.fullmatch(r"[0-9a-f]{40}", s) for s in (head, main)):
        raise RuntimeError("full exact SHA required")
    if Path(out(root, "rev-parse", "--show-toplevel")).resolve() != root:
        raise RuntimeError("repository root mismatch")
    if out(root, "status", "--porcelain"):
        raise RuntimeError("clean candidate required")
    if out(root, "branch", "--show-current") != branch or out(root, "rev-parse", "HEAD") != head:
        raise RuntimeError("candidate identity changed")
    if out(root, "remote", "get-url", "gitee-mirror") not in allowed_urls:
        raise RuntimeError("unexpected Gitee remote")
    refs = dict(line.split()[::-1] for line in out(root, "ls-remote", "gitee-mirror", "refs/heads/main", "refs/heads/" + branch).splitlines())
    if refs.get("refs/heads/main") != main or refs.get("refs/heads/" + branch) != head:
        raise RuntimeError("remote identity drift")
    return root


def sync(root, branch, head, main, apply=False, confirm="", allowed_urls=URLS):
    root = inspect(root, branch, head, main, allowed_urls)
    git(root, "fetch", "gitee-mirror", "main")
    if out(root, "rev-parse", "FETCH_HEAD") != main:
        raise RuntimeError("main changed during fetch")
    if not apply:
        return {"writes": 0, "head": head, "main": main}
    if confirm != CONFIRM:
        raise RuntimeError("exact confirmation required")
    inspect(root, branch, head, main, allowed_urls)
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
            "published": False, "ci_required": True}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    for name in ("root", "branch", "head", "main"):
        p.add_argument("--" + name, required=True)
    p.add_argument("--apply", action="store_true")
    p.add_argument("--confirm", default="")
    print(json.dumps(sync(**vars(p.parse_args())), sort_keys=True))
