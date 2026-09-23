#!/usr/bin/env python3
"""Bounded GitHub-outage lane; never merges new product changes into main."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

GITEE = "git@gitee.com:leegege/sce-product-odoo.git"
GITHUB = "https://github.com/lidefend/sce-backend-odoo.git"
HISTORICAL_MAIN = "de9a230d3faab18dd60a219f445f932a8af9d7f5"
SHA = re.compile(r"[0-9a-f]{40}")
CI_BRANCH = "fix/gitee-temporary-integration-v1"
BRANCH = re.compile(r"(?:feature|fix|refactor|audit|release|codex)/.+")


class Denied(RuntimeError):
    pass


class PushUncertain(Denied):
    """A push was attempted; inspecting the remote is required before recovery."""


class Integration:
    def __init__(self, root: Path):
        self.root = root.resolve()

    def run(self, *args: str) -> str:
        result = subprocess.run(args, cwd=self.root, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=120)
        if result.returncode:
            # Do not echo subprocess stderr: transport helpers may contain credentials.
            raise Denied(f"command failed: {args[0]} {args[1]} (exit {result.returncode})")
        return result.stdout.strip()

    def git(self, *args: str) -> str:
        return self.run("git", *args)

    def identity(self, expected_head: str, *, clean: bool) -> str:
        if os.environ.get("ENV", "dev") not in {"dev", "test"} or os.environ.get("PROD_DANGER") == "1":
            raise Denied("dev/test only")
        if not SHA.fullmatch(expected_head):
            raise Denied("full expected HEAD required")
        if Path(self.git("rev-parse", "--show-toplevel")).resolve() != self.root:
            raise Denied("repository root mismatch")
        branch = self.git("branch", "--show-current")
        if not BRANCH.fullmatch(branch):
            raise Denied("allowed controller branch required")
        self.git("check-ref-format", "--branch", branch)
        if self.git("rev-parse", "HEAD") != expected_head:
            raise Denied("HEAD drift")
        if clean and self.git("status", "--porcelain=v1", "--untracked-files=all"):
            raise Denied("clean worktree required")
        if self.git("remote", "get-url", "--all", "origin") != GITHUB:
            raise Denied("canonical origin must remain unchanged")
        for args in [("--all",), ("--push", "--all")]:
            if self.git("remote", "get-url", *args, "gitee-mirror") != GITEE:
                raise Denied("Gitee URL must be the single registered repository")
        return branch

    def remote_head(self, ref: str, *, absent: bool = False) -> str:
        rows = self.git("ls-remote", GITEE, ref).splitlines()
        if absent and not rows:
            return ""
        if len(rows) != 1:
            raise Denied(f"remote ref missing or ambiguous: {ref}")
        fields = rows[0].split()
        if len(fields) != 2 or fields[1] != ref or not SHA.fullmatch(fields[0]):
            raise Denied("invalid remote identity")
        return fields[0]

    def baseline(self, expected_main: str, target: str) -> None:
        if not SHA.fullmatch(expected_main):
            raise Denied("full expected Gitee main required")
        if self.remote_head("refs/heads/main") != expected_main:
            raise Denied("Gitee main drift")
        # Missing local objects are a stop, never an invitation to force push.
        self.git("merge-base", "--is-ancestor", expected_main, target)

    def readback(self, ref: str, expected: str) -> None:
        try:
            actual = self.remote_head(ref)
        except (Denied, subprocess.TimeoutExpired, OSError) as exc:
            raise PushUncertain("readback failed after push; remote may have changed, inspect before recovery") from exc
        if actual != expected:
            raise PushUncertain("readback mismatch after push; remote may have changed, inspect before recovery")

    def push_and_readback(self, ref: str, head: str) -> None:
        # Ordinary FF push is not compare-and-swap against the preflight SHA.
        # Even a transport error can occur after the remote accepted the write.
        try:
            self.git("push", GITEE, f"{head}:{ref}")
        except (Denied, subprocess.TimeoutExpired, OSError) as exc:
            raise PushUncertain("push outcome uncertain; inspect remote before recovery; do not retry blindly") from exc
        self.readback(ref, head)

    def inspect(self, head: str, main: str) -> dict:
        branch = self.identity(head, clean=False)
        self.baseline(main, head)
        return {"action": "inspect", "branch": branch, "head": head, "gitee_main": main,
                "commits_ahead": int(self.git("rev-list", "--count", f"{main}..{head}")),
                "dirty": bool(self.git("status", "--porcelain=v1", "--untracked-files=all")),
                "status": "passed", "writes": 0, "delivery_gate": False}

    def catchup(self, head: str, main: str, apply: bool, confirm: str) -> dict:
        branch = self.identity(head, clean=apply)
        # Only restore the already integrated GitHub main observed at takeover.
        # This target cannot integrate either of the two unmerged product topics.
        for ref in ("refs/heads/main", "refs/remotes/origin/main"):
            if self.git("rev-parse", ref) != HISTORICAL_MAIN:
                raise Denied("historical baseline anchor changed")
        self.baseline(main, HISTORICAL_MAIN)
        result = {"action": "catchup", "head": head, "old_main": main,
                  "target_main": HISTORICAL_MAIN, "applied": False}
        if not apply:
            return result
        if confirm != "FAST_FORWARD_HISTORICAL_GITEE_MAIN":
            raise Denied("catchup confirmation required")
        if main == HISTORICAL_MAIN:
            return {**result, "already_aligned": True}
        common = Path(self.git("rev-parse", "--path-format=absolute", "--git-common-dir"))
        recovery = common / "codex-recovery" / "gitee-temporary-integration"
        recovery.mkdir(parents=True, exist_ok=True)
        folder = Path(tempfile.mkdtemp(prefix="catchup-", dir=recovery))
        bundle = folder / "historical-main.bundle"
        self.git("bundle", "create", str(bundle), "refs/heads/main")
        self.git("bundle", "verify", str(bundle))
        if self.git("bundle", "list-heads", str(bundle)) != f"{HISTORICAL_MAIN} refs/heads/main":
            raise Denied("recovery bundle historical head mismatch")
        if self.identity(head, clean=True) != branch:
            raise Denied("controller branch drift before catchup")
        self.baseline(main, HISTORICAL_MAIN)
        for ref in ("refs/heads/main", "refs/remotes/origin/main"):
            if self.git("rev-parse", ref) != HISTORICAL_MAIN:
                raise Denied("historical baseline anchor changed before push")
        # Ordinary push keeps server-side fast-forward protection. Never force/lease.
        self.push_and_readback("refs/heads/main", HISTORICAL_MAIN)
        return {**result, "applied": True, "recovery_bundle": str(bundle)}

    def publish(self, head: str, main: str, apply: bool, confirm: str, purpose: str = "integration") -> dict:
        if purpose not in {"integration", "ci-only"}:
            raise Denied("unknown publication purpose")
        branch = self.identity(head, clean=apply or purpose != "ci-only")
        if purpose == "ci-only" and branch != CI_BRANCH:
            raise Denied("CI-only requires the registered candidate branch")
        self.baseline(main, head)
        # Candidates cannot accidentally smuggle the 133-commit catchup into their PR.
        if purpose == "integration":
            self.git("merge-base", "--is-ancestor", HISTORICAL_MAIN, main)
        ref = f"refs/heads/{branch}"
        old = self.remote_head(ref, absent=True)
        if old:
            self.git("merge-base", "--is-ancestor", old, head)
        result = {"action": "publish", "branch": branch, "head": head,
                  "gitee_main": main, "old_branch": old, "applied": False,
                  "pr_required": True, "merge_authorized": False}
        if purpose == "ci-only":
            commits = self.git("rev-list", "--reverse", f"{main}..{head}").splitlines()
            result.update(purpose="ci-only", integration_eligible=False, pr_required=False,
                          notice="CI acceptance only; no formal integration eligibility",
                          commits_relative_to_main=commits, commit_count=len(commits),
                          changed_paths=self.git("diff", "--name-only", main, head).splitlines(),
                          scope_basis="relative_to_observed_main_not_all_remote_refs",
                          additional_visible_code_possible=bool(commits),
                          dirty=bool(self.git("status", "--porcelain=v1", "--untracked-files=all")),
                          excludes_uncommitted_changes=True, writes=0)
            if apply:
                receipt = os.environ.get("GITEE_CI_EVIDENCE", "")
                digest = os.environ.get("GITEE_CI_EVIDENCE_SHA256", "")
                if not receipt or not re.fullmatch(r"[0-9a-f]{64}", digest):
                    raise Denied("CI-only requires reviewed platform automation evidence")
        if not apply:
            return result
        if confirm != "PUBLISH_EXACT_GITEE_CANDIDATE":
            raise Denied("publish confirmation required")
        if purpose == "ci-only":
            # Legacy bootstrap has no accepted PR lane; preserve its separate gate.
            self.run("python3", "scripts/ops/local_quick_evidence.py", "verify", "--expected-head", head)
            self.run("make", "--no-print-directory", "ci.generated_evidence.preflight")
        else:
            # Owner-directed local iteration / remote integration split. This only
            # publishes a topic branch; required remote PR checks still own merge.
            self.run("make", "--no-print-directory", "ci.local.iteration")
            self.git("diff", "--check", main, head, "--")
        if self.identity(head, clean=True) != branch:
            raise Denied("branch drift after preflight")
        self.baseline(main, head)
        if self.remote_head(ref, absent=True) != old:
            raise Denied("remote candidate drift after preflight")
        if purpose == "ci-only":
            self.run("python3", "-m", "scripts.ops.gitee_ci_publication_gate", "--head", head,
                     "--main", main, "--receipt", receipt, "--receipt-sha256", digest)
            if self.identity(head, clean=True) != branch:
                raise Denied("candidate changed during online evidence verification")
            self.baseline(main, head)
            if self.remote_head(ref, absent=True) != old:
                raise Denied("remote candidate drift during online evidence verification")
        self.push_and_readback(ref, head)
        return {**result, "applied": True, "writes": 1}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("inspect", "catchup", "publish"))
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--expected-main", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--purpose", choices=("integration", "ci-only"), default="integration")
    parser.add_argument("--confirm", default="")
    args = parser.parse_args()
    try:
        lane = Integration(Path.cwd())
        if args.action == "inspect":
            if args.apply:
                raise Denied("inspect is read-only")
            result = lane.inspect(args.expected_head, args.expected_main)
        elif args.action == "publish":
            result = lane.publish(args.expected_head, args.expected_main, args.apply, args.confirm, args.purpose)
        else:
            if args.purpose != "integration":
                raise Denied("purpose applies only to publish")
            result = getattr(lane, args.action)(args.expected_head, args.expected_main, args.apply, args.confirm)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except PushUncertain as exc:
        print(json.dumps({"status": "uncertain", "reason": str(exc), "retry_allowed": False}, ensure_ascii=False))
        return 3
    except (Denied, subprocess.TimeoutExpired, OSError, ValueError) as exc:
        print(json.dumps({"status": "denied", "reason": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
