"""Boundary tests for the parameterized Gitee PR merge entry.

The platform is a fake: these tests prove refusal semantics (pending, failed,
stale-SHA and drifted identities must never merge) and the readback receipt,
not a live integration eligibility.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
import urllib.parse
from pathlib import Path
from unittest.mock import patch

from scripts.ops import gitee_pr_bot

HEAD = "a" * 40
MAIN = "b" * 40
MERGED = "c" * 40
SOURCE = "fix/example-topic"
NUMBER = 42
REQUIRED = gitee_pr_bot.REQUIRED_CHECKS


def check(name, *, head_sha=HEAD, status="completed", conclusion="success"):
    return {"name": name, "head_sha": head_sha, "status": status, "conclusion": conclusion}


def passing_checks():
    return [check(name) for name in REQUIRED]


class FakeAPI:
    """Minimal Gitee surface used by merge_pull."""

    def __init__(self, *, checks=None, pr=None, main_sha=MAIN, source_sha=HEAD,
                 merge_state="merged", merged_sha=MERGED, free_main=True, merge_raises=None):
        self.checks = passing_checks() if checks is None else checks
        self.pr = pr if pr is not None else {
            "number": NUMBER, "state": "open", "title": "example",
            "mergeable": True, "head": {"ref": SOURCE, "sha": HEAD,
                                        "repo": {"full_name": f"{gitee_pr_bot.OWNER}/{gitee_pr_bot.REPO}"}},
            "base": {"ref": "main", "sha": MAIN},
        }
        self.main_sha = main_sha
        self.source_sha = source_sha
        self.merge_state = merge_state
        self.merged_sha = merged_sha
        self.free_main = free_main
        self.merge_raises = merge_raises
        self.calls = []

    def __call__(self, token, method, path, payload=None):
        self.calls.append((method, path))
        if method == "PUT" and path.endswith("/merge"):
            if self.merge_raises:
                raise self.merge_raises
            return {"sha": self.merged_sha, "merged": True}
        if method == "GET" and "/check-runs" in path:
            return {"check_runs": list(self.checks)}
        if method == "GET" and "/branches/" in path:
            branch = urllib.parse.unquote(path.rsplit("/", 1)[-1])
            return {"name": branch, "commit": {"sha": self.source_sha if branch == SOURCE else self.main_sha}}
        if method == "GET" and "/pulls/" in path:
            if path.endswith("/merge"):
                raise AssertionError("unexpected read of the merge endpoint")
            if self.calls.count(("GET", path)) > 1 and self.free_main:
                # Post-merge readback: the PR is closed and main advanced.
                return {**self.pr, "state": self.merge_state}
            return self.pr
        raise AssertionError(f"unexpected call {method} {path}")

    @property
    def merge_calls(self):
        return [c for c in self.calls if c[0] == "PUT"]


def merged_api(**kwargs):
    api = FakeAPI(**kwargs)
    original = api.__call__

    def wrapper(token, method, path, payload=None):
        if method == "GET" and "/branches/main" in path and api.merge_calls:
            return {"name": "main", "commit": {"sha": api.merged_sha}}
        return original(token, method, path, payload)

    return api, wrapper


class MergeEntryTests(unittest.TestCase):
    def run_merge(self, api, wrapper=None, **kwargs):
        target = wrapper or api
        with patch.object(gitee_pr_bot, "request", target):
            return gitee_pr_bot.merge_pull("token", number=NUMBER, expected_head=HEAD,
                                           expected_main=MAIN, expected_source=SOURCE, **kwargs)

    def refuse(self, api, code, wrapper=None, **kwargs):
        with self.assertRaises(gitee_pr_bot.Denied) as ctx:
            self.run_merge(api, wrapper=wrapper, **kwargs)
        self.assertIn(code, str(ctx.exception))
        self.assertEqual(api.merge_calls, [], "a refusal must never call the merge endpoint")

    def test_success_merges_and_reads_back(self):
        api, wrapper = merged_api()
        receipt = self.run_merge(api, wrapper=wrapper)
        self.assertEqual(api.merge_calls, [("PUT", f"/repos/{gitee_pr_bot.OWNER}/{gitee_pr_bot.REPO}/pulls/{NUMBER}/merge")])
        self.assertEqual(receipt["merge_commit"], MERGED)
        self.assertEqual(receipt["main_after"], MERGED)
        self.assertEqual(receipt["head_sha"], HEAD)
        self.assertEqual(set(receipt["checks"]), set(REQUIRED))
        self.assertTrue(all(v["head_sha"] == HEAD for v in receipt["checks"].values()))
        self.assertFalse(receipt["pushed_main"])
        self.assertTrue(receipt["branch_protection_preserved"])

    def test_pending_check_refuses(self):
        api = FakeAPI(checks=[check(name, status="in_progress", conclusion=None) for name in REQUIRED])
        self.refuse(api, "required_checks_pending")

    def test_partially_pending_check_refuses(self):
        checks = [check(name) for name in REQUIRED[:-1]] + [check(REQUIRED[-1], status="queued", conclusion=None)]
        self.refuse(FakeAPI(checks=checks), "required_checks_pending")

    def test_failed_check_refuses(self):
        checks = [check(name) for name in REQUIRED[:-1]] + [check(REQUIRED[-1], conclusion="failure")]
        self.refuse(FakeAPI(checks=checks), "required_checks_not_success")

    def test_check_bound_to_another_commit_refuses(self):
        api = FakeAPI(checks=[check(name, head_sha="d" * 40) for name in REQUIRED])
        self.refuse(api, "required_checks_stale_sha")

    def test_missing_required_check_refuses(self):
        api = FakeAPI(checks=[check(name) for name in REQUIRED[:-1]])
        self.refuse(api, "required_checks_missing")

    def test_source_branch_drift_refuses(self):
        self.refuse(FakeAPI(source_sha="e" * 40), "source_branch_drift")

    def test_target_branch_drift_refuses(self):
        self.refuse(FakeAPI(main_sha="f" * 40), "target_branch_drift")

    def test_pr_head_sha_mismatch_refuses(self):
        pr = dict(FakeAPI().pr)
        pr["head"] = {**pr["head"], "sha": "1" * 40}
        self.refuse(FakeAPI(pr=pr), "pr_head_sha_mismatch")

    def test_pr_target_sha_mismatch_refuses(self):
        pr = dict(FakeAPI().pr)
        pr["base"] = {"ref": "main", "sha": "2" * 40}
        self.refuse(FakeAPI(pr=pr), "pr_target_sha_mismatch")

    def test_closed_pr_refuses(self):
        pr = dict(FakeAPI().pr)
        pr["state"] = "closed"
        self.refuse(FakeAPI(pr=pr), "pr_not_open")

    def test_unmergeable_pr_refuses(self):
        pr = dict(FakeAPI().pr)
        pr["mergeable"] = False
        self.refuse(FakeAPI(pr=pr), "pr_not_mergeable")

    def test_fork_pr_refuses(self):
        pr = dict(FakeAPI().pr)
        pr["head"] = {**pr["head"], "repo": {"full_name": "someone/fork"}}
        self.refuse(FakeAPI(pr=pr), "fork_pr_denied")

    def test_denied_merge_reports_refusal_not_success(self):
        api = FakeAPI(merge_raises=gitee_pr_bot.Denied("api_denied method=PUT status=403"))
        with self.assertRaises(gitee_pr_bot.Denied) as ctx:
            self.run_merge(api)
        self.assertIn("api_denied", str(ctx.exception))

    def test_readback_mismatch_is_not_a_pass(self):
        api = FakeAPI(merged_sha=MERGED, main_sha=MAIN)

        def wrapper(token, method, path, payload=None):
            value = api(token, method, path, payload)
            return value

        with self.assertRaises(gitee_pr_bot.Denied) as ctx:
            self.run_merge(api, wrapper=wrapper)
        self.assertIn("merge_readback_mismatch", str(ctx.exception))

    def test_unsupported_merge_method_refused(self):
        api = FakeAPI()
        with self.assertRaises(gitee_pr_bot.Denied) as ctx:
            self.run_merge(api, merge_method="fast-forward")
        self.assertIn("unsupported_merge_method", str(ctx.exception))

    def test_required_check_set_is_the_four_named_checks(self):
        self.assertEqual(gitee_pr_bot.REQUIRED_CHECKS,
                         ("public_guard", "merge_policy_gate", "professional_quality_gate", "frontend_release_gate"))


class TokenFileTests(unittest.TestCase):
    def test_group_readable_token_file_is_rejected_before_any_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            token = Path(tmp) / "token"
            token.write_text("x")
            os.chmod(token, 0o644)
            result = subprocess.run([sys.executable, "-m", "scripts.ops.gitee_pr_bot", "status",
                                     "--token-file", str(token)], text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("owner-only regular file", result.stderr + result.stdout)

    def test_merge_requires_expected_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            token = Path(tmp) / "token"
            token.write_text("x")
            os.chmod(token, 0o600)
            result = subprocess.run([sys.executable, "-m", "scripts.ops.gitee_pr_bot", "merge",
                                     "--token-file", str(token), "--number", str(NUMBER)],
                                    text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("expected-head and expected-main", result.stderr + result.stdout)


if __name__ == "__main__":
    unittest.main()
