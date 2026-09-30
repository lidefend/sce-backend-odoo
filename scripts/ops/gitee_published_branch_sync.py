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


def discard_local(root, branch, head, main, target, target_head, bundle,
                  apply=False, confirm=""):
    """Owner-approved abandonment, local only; never infer merge or touch remotes."""
    root = Path(root).resolve()
    archive = Path(bundle)
    def check():
        for value in (branch, target):
            if not re.fullmatch(r"(feature|fix|refactor|audit|codex)/[A-Za-z0-9_./-]+", value):
                raise RuntimeError("unprotected topic branch required")
            git(root, "check-ref-format", "refs/heads/" + value)
        if any(not re.fullmatch(r"[0-9a-f]{40}", v) for v in (head, main, target_head)):
            raise RuntimeError("full exact SHA required")
        if Path(out(root, "rev-parse", "--show-toplevel")).resolve() != root:
            raise RuntimeError("repository root mismatch")
        if out(root, "status", "--porcelain"):
            raise RuntimeError("clean candidate required")
        if out(root, "branch", "--show-current") != branch or out(root, "rev-parse", "HEAD") != head:
            raise RuntimeError("candidate identity changed")
        if out(root, "rev-parse", "refs/heads/main") != main:
            raise RuntimeError("local main drift")
        if "branch refs/heads/" + target in out(root, "worktree", "list", "--porcelain").splitlines():
            raise RuntimeError("target occupied by worktree")
        if git(root, "symbolic-ref", "-q", "refs/heads/" + target, check=False).returncode == 0:
            raise RuntimeError("symbolic target refused")
        if out(root, "rev-parse", "refs/heads/" + target) != target_head:
            raise RuntimeError("target identity drift")
        if not archive.is_absolute() or archive.is_symlink() or archive.resolve().is_relative_to(root):
            raise RuntimeError("external regular recovery bundle required")
    check()
    receipt = dict(target=target, target_head=target_head, head=head, main=main,
                   mode="explicit_local_abandonment", remote_writes=0)
    if not apply:
        return dict(receipt, writes=0, bundle=str(archive))
    if confirm != "DISCARD_EXACT_LOCAL_BRANCH_KEEP_RECOVERY":
        raise RuntimeError("exact local abandonment confirmation required")
    archive.parent.mkdir(parents=True, exist_ok=True)
    if not archive.exists():
        git(root, "bundle", "create", str(archive), "refs/heads/" + target)
    if not archive.is_file() or archive.is_symlink():
        raise RuntimeError("regular recovery bundle required")
    git(root, "bundle", "verify", str(archive))
    expected = target_head + " refs/heads/" + target
    if expected not in out(root, "bundle", "list-heads", str(archive)).splitlines():
        raise RuntimeError("recovery bundle target mismatch")
    # Existing bundles must also restore independently after local objects are GC'd.
    with archive.open("rb") as stream:
        header_bytes = 0
        while True:
            line = stream.readline(65537)
            header_bytes += len(line)
            if not line or header_bytes > 1048576:
                raise RuntimeError("invalid recovery bundle header")
            if line == b"\n": break
            if line.startswith(b"-"):
                raise RuntimeError("incremental recovery bundle refused")
    bundle_hash = hashlib.sha256(archive.read_bytes()).hexdigest()
    check()
    git(root, "update-ref", "--no-deref", "-d", "refs/heads/" + target, target_head)
    if git(root, "show-ref", "--verify", "refs/heads/" + target, check=False).returncode == 0:
        raise RuntimeError("local deletion readback failed")
    if out(root,"rev-parse","HEAD") != head or out(root,"status","--porcelain"):
        raise RuntimeError("worktree changed during cleanup")
    return dict(receipt, writes=1, bundle=str(archive), bundle_sha256=bundle_hash,
                local_ref="absent", worktree_changed=False)


def main_only_plan(root, branch, head, main, allowed_urls=URLS):
    """Inventory exact local refs/worktrees for an explicit retain-main-only request."""
    root = Path(root).resolve()
    if any(not re.fullmatch(r"[0-9a-f]{40}", v) for v in (head, main)):
        raise RuntimeError("full exact SHA required")
    if Path(out(root,"rev-parse","--show-toplevel")).resolve() != root:
        raise RuntimeError("repository root mismatch")
    if out(root,"branch","--show-current") != branch or out(root,"rev-parse","HEAD") != head:
        raise RuntimeError("candidate identity changed")
    if out(root,"remote","get-url","gitee-mirror") not in allowed_urls:
        raise RuntimeError("unexpected Gitee remote")
    if remote_refs(root,branch).get("refs/heads/main") != main:
        raise RuntimeError("remote main drift")
    if out(root,"rev-parse","refs/heads/main") != main:
        raise RuntimeError("local main drift")
    refs = {}
    for line in out(root,"for-each-ref","--format=%(objectname) %(refname)","refs/heads").splitlines():
        sha, ref = line.split(" ",1)
        if ref != "refs/heads/main" and not re.fullmatch(r"refs/heads/(feature|fix|refactor|audit|release|codex)/[A-Za-z0-9_./-]+",ref):
            raise RuntimeError("unexpected local branch")
        if git(root,"symbolic-ref","-q",ref,check=False).returncode == 0:
            raise RuntimeError("symbolic local branch refused")
        refs[ref] = sha
    worktrees=[]
    for block in out(root,"worktree","list","--porcelain").split("\n\n"):
        lines=block.splitlines();path=Path(lines[0].removeprefix("worktree "))
        if path != root and (path.parent != root.parent or not path.name.startswith(root.name+"-")):
            raise RuntimeError("worktree outside registered sibling scope")
        if path.is_symlink() or not path.is_dir():
            raise RuntimeError("unsafe worktree path")
        if out(path,"status","--porcelain","--untracked-files=all"):
            raise RuntimeError("dirty worktree refused")
        sha=out(path,"rev-parse","HEAD")
        if path != root and not any(line.startswith("branch ") for line in lines):
            if git(root,"merge-base","--is-ancestor",sha,main,check=False).returncode:
                raise RuntimeError("unretained detached worktree history")
        worktrees.append(dict(path=str(path),head=sha))
    if not worktrees or worktrees[0]['path'] != str(root):
        raise RuntimeError("run from primary worktree")
    return dict(root=str(root),branch=branch,head=head,main=main,refs=refs,worktrees=worktrees,
                remote_writes=0,operation="retain_latest_main_only")


def retain_main_only(root, branch, head, main, bundle, plan_sha256="", apply=False,
                     confirm="", allowed_urls=URLS):
    plan=main_only_plan(root,branch,head,main,allowed_urls)
    digest=hashlib.sha256(json.dumps(plan,sort_keys=True).encode()).hexdigest()
    if not apply: return dict(plan,plan_sha256=digest,writes=0)
    if confirm != "RETAIN_EXACT_MAIN_ONLY_WITH_RECOVERY" or digest != plan_sha256:
        raise RuntimeError("exact reviewed main-only plan required")
    archive=Path(bundle);root=Path(root).resolve()
    if not archive.is_absolute() or archive.is_symlink() or archive.resolve().is_relative_to(root):
        raise RuntimeError("external recovery bundle required")
    archive.parent.mkdir(parents=True,exist_ok=True)
    if not archive.exists():git(root,"bundle","create",str(archive),"--branches")
    if not archive.is_file() or archive.is_symlink():raise RuntimeError("regular bundle required")
    git(root,"bundle","verify",str(archive))
    with archive.open("rb") as stream:
        size=0
        while True:
            line=stream.readline(65537);size+=len(line)
            if not line or size>1048576:raise RuntimeError("invalid bundle header")
            if line == b"\n":break
            if line.startswith(b"-"):raise RuntimeError("incremental bundle refused")
    heads=set(out(root,"bundle","list-heads",str(archive)).splitlines())
    if any(sha+" "+ref not in heads for ref,sha in plan['refs'].items()):
        raise RuntimeError("bundle does not cover all local refs")
    bundle_sha=hashlib.sha256(archive.read_bytes()).hexdigest()
    if main_only_plan(root,branch,head,main,allowed_urls) != plan:
        raise RuntimeError("local cleanup plan drift")
    # Ignored evidence must be moved/deleted by the reviewed file inventory first.
    for entry in plan['worktrees']:
        if out(Path(entry['path']),"ls-files","--others","--ignored","--exclude-standard"):
            raise RuntimeError("worktree ignored files require preservation first")
    removed=[]
    for entry in plan['worktrees'][1:]:
        git(root,"worktree","remove","--",entry['path']);removed.append(entry['path'])
    git(root,"switch","--no-overwrite-ignore","main")
    commands=["start","option no-deref"]
    commands += ["delete "+ref+" "+sha for ref,sha in plan['refs'].items() if ref != "refs/heads/main"]
    commands += ["prepare","commit",""]
    result=subprocess.run(["git","update-ref","--stdin"],cwd=root,input="\n".join(commands),text=True,capture_output=True)
    if result.returncode:raise RuntimeError("ref transaction refused; recovery bundle preserved")
    if out(root,"for-each-ref","--format=%(refname)","refs/heads") != "refs/heads/main" or out(root,"rev-parse","HEAD") != main or out(root,"status","--porcelain"):
        raise RuntimeError("main-only readback mismatch")
    return dict(status="cleaned",main=main,local_branches=["main"],removed_worktrees=removed,
                deleted_refs=[r for r in plan['refs'] if r != "refs/heads/main"],
                bundle=str(archive),bundle_sha256=bundle_sha,remote_writes=0,plan_sha256=digest)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    for name in ("root", "branch", "head", "main"):
        p.add_argument("--" + name, required=True)
    p.add_argument("--retain-main-only", action="store_true")
    p.add_argument("--plan-sha256", default="")
    p.add_argument("--discard-local", action="store_true")
    p.add_argument("--target")
    p.add_argument("--target-head")
    p.add_argument("--bundle")
    p.add_argument("--local-main", action="store_true")
    p.add_argument("--old-main")
    p.add_argument("--remote-head")
    p.add_argument("--allow-absent", action="store_true")
    p.add_argument("--apply", action="store_true")
    p.add_argument("--confirm", default="")
    args = vars(p.parse_args())
    local_main = args.pop("local_main")
    old_main = args.pop("old_main")
    discard = args.pop("discard_local")
    target, target_head, bundle = (args.pop(k) for k in ("target", "target_head", "bundle"))
    main_only = args.pop("retain_main_only")
    plan_sha = args.pop("plan_sha256")
    if main_only:
        if discard or local_main or old_main or target or target_head or args.pop("remote_head") or args.pop("allow_absent") or not bundle:
            p.error("main-only rejects other modes and requires recovery bundle")
        result=retain_main_only(**args,bundle=bundle,plan_sha256=plan_sha)
    elif plan_sha:
        p.error("plan-sha256 requires retain-main-only")
    elif discard:
        if local_main or old_main or args.pop("remote_head") or args.pop("allow_absent") or not all((target, target_head, bundle)):
            p.error("local abandonment requires target/head/bundle, rejects synchronization flags")
        result = discard_local(**args, target=target, target_head=target_head, bundle=bundle)
    elif target or target_head or bundle:
        p.error("target/head/bundle require discard-local")
    elif local_main:
        if not old_main or args.pop("remote_head") or args.pop("allow_absent"):
            p.error("local-main requires old-main and rejects candidate sync flags")
        result = sync_local_main(**args, old_main=old_main)
    else:
        if old_main: p.error("old-main requires local-main")
        result = sync(**args)
    print(json.dumps(result, sort_keys=True))
