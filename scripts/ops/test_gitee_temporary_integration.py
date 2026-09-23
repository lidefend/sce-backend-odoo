"""Negative publication tests: every refused prerequisite must cause zero pushes."""
import os
import subprocess
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.ops.gitee_temporary_integration import Denied, PushUncertain, GITEE, GITHUB, HISTORICAL_MAIN, Integration

HEAD = "a" * 40
OLD = "b" * 40
BRANCH = "fix/example"


class FakeLane(Integration):
    def __init__(self, root):
        super().__init__(root)
        self.calls = []
        self.head = HEAD
        self.branch = BRANCH
        self.dirty = False
        self.url = GITEE
        self.origin = GITHUB
        self.remote_main = HISTORICAL_MAIN
        self.remote_branch = ""
        self.anchor = HISTORICAL_MAIN
        self.nonancestor = set()
        self.fail = ""
        self.after_gate = None
        self.publish_visible = True
        self.after_bundle = None
        self.after_push = None
        self.bundle_head = HISTORICAL_MAIN

    def run(self, *args):
        self.calls.append(args)
        if args[0] == "python3":
            if self.fail == "quick": raise Denied("missing quick")
            return "VERIFIED"
        if args[0] == "make":
            if self.after_gate: self.after_gate()
            if self.fail == "generated": raise Denied("stale generated evidence")
            return "PASS"
        self.assert_git(args)
        cmd = args[1:]
        if cmd == ("rev-parse", "--show-toplevel"): return str(self.root)
        if cmd == ("branch", "--show-current"): return self.branch
        if cmd[:1] == ("check-ref-format",): return ""
        if cmd == ("rev-parse", "HEAD"): return self.head
        if cmd[:1] == ("status",): return "?? untracked" if self.dirty else ""
        if cmd[:2] == ("remote", "get-url"):
            return self.origin if cmd[-1] == "origin" else self.url
        if cmd[:1] == ("ls-remote",):
            if self.fail == "transport": raise Denied("unreachable")
            ref = cmd[-1]
            value = self.remote_main if ref == "refs/heads/main" else self.remote_branch
            return f"{value}\t{ref}" if value else ""
        if cmd[:2] == ("merge-base", "--is-ancestor"):
            if cmd[2:] in self.nonancestor: raise Denied("non fast forward")
            return ""
        if cmd[:2] == ("rev-list", "--count"): return "133"
        if cmd[:2] == ("rev-list", "--reverse"): return HEAD
        if cmd[:2] == ("diff", "--name-only"): return "scripts/ops/example.py"
        if cmd[:2] == ("rev-parse", "--path-format=absolute"): return str(self.root)
        if cmd[:1] == ("rev-parse",): return self.anchor
        if cmd[:2] == ("bundle", "list-heads"):
            return f"{self.bundle_head} refs/heads/main"
        if cmd[:1] == ("bundle",):
            if self.fail == "bundle": raise Denied("bundle invalid")
            if cmd[1] == "verify" and self.after_bundle: self.after_bundle()
            return ""
        if cmd[:1] == ("push",):
            if self.fail == "push": raise Denied("protected branch")
            sha, ref = cmd[-1].split(":", 1)
            if self.publish_visible:
                if ref == "refs/heads/main": self.remote_main = sha
                else: self.remote_branch = sha
            if self.after_push: self.after_push()
            return ""
        raise AssertionError(args)

    @staticmethod
    def assert_git(args):
        if args[0] != "git": raise AssertionError(args)

    def pushes(self):
        return [c for c in self.calls if c[:2] == ("git", "push")]


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.env = patch.dict(os.environ, {"ENV": "dev", "PROD_DANGER": "0"})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.lane = FakeLane(Path(self.directory.name))

    def publish(self):
        return self.lane.publish(HEAD, HISTORICAL_MAIN, True, "PUBLISH_EXACT_GITEE_CANDIDATE")

    def denied(self):
        with self.assertRaises(Denied): self.publish()
        self.assertEqual(self.lane.pushes(), [])

    def test_inspect_dirty_is_diagnostic_only(self):
        self.lane.dirty = True
        self.assertTrue(self.lane.inspect(HEAD, HISTORICAL_MAIN)["dirty"])
        self.assertFalse(self.lane.inspect(HEAD, HISTORICAL_MAIN)["delivery_gate"])
        self.assertEqual(self.lane.pushes(), [])

    def test_publish_dry_run_writes_nothing(self):
        self.assertFalse(self.lane.publish(HEAD, HISTORICAL_MAIN, False, "")["applied"])
        self.assertEqual(self.lane.pushes(), [])

    def test_publish_exact_sha_only(self):
        self.assertTrue(self.publish()["applied"])
        self.assertEqual(self.lane.pushes(), [("git", "push", GITEE, f"{HEAD}:refs/heads/{BRANCH}")])

    def test_wrong_repository(self):
        self.lane.url = "git@gitee.com:other/repo.git"
        self.denied()

    def test_multiple_push_urls(self):
        self.lane.url += "\ngit@gitee.com:other/repo.git"
        self.denied()

    def test_origin_not_rewritten(self):
        self.lane.origin = GITEE
        self.denied()

    def test_main_branch_denied(self):
        self.lane.branch = "main"
        self.denied()

    def test_prod_denied(self):
        os.environ["ENV"] = "prod"
        self.denied()

    def test_dirty_denied(self):
        self.lane.dirty = True
        self.denied()

    def test_head_drift_denied(self):
        self.lane.head = OLD
        self.denied()

    def test_remote_main_drift_denied(self):
        self.lane.remote_main = OLD
        self.denied()

    def test_non_fast_forward_main_denied(self):
        self.lane.nonancestor.add((HISTORICAL_MAIN, HEAD))
        self.denied()

    def test_lagging_baseline_denied(self):
        self.lane.remote_main = OLD
        self.lane.nonancestor.add((HISTORICAL_MAIN, OLD))
        with self.assertRaises(Denied): self.lane.publish(HEAD, OLD, True, "PUBLISH_EXACT_GITEE_CANDIDATE")
        self.assertEqual(self.lane.pushes(), [])

    def test_non_fast_forward_candidate_denied(self):
        self.lane.remote_branch = OLD
        self.lane.nonancestor.add((OLD, HEAD))
        self.denied()

    def test_quick_missing_denied(self):
        self.lane.fail = "quick"
        self.denied()

    def test_generated_stale_denied(self):
        self.lane.fail = "generated"
        self.denied()

    def test_transport_failure_denied(self):
        self.lane.fail = "transport"
        self.denied()

    def test_mutation_by_preflight_denied(self):
        self.lane.after_gate = lambda: setattr(self.lane, "dirty", True)
        self.denied()

    def test_branch_drift_during_preflight_denied(self):
        self.lane.after_gate = lambda: setattr(self.lane, "branch", "fix/other")
        self.denied()

    def test_remote_drift_during_preflight_denied(self):
        self.lane.after_gate = lambda: setattr(self.lane, "remote_branch", OLD)
        self.denied()

    def test_main_drift_during_preflight_denied(self):
        self.lane.after_gate = lambda: setattr(self.lane, "remote_main", OLD)
        self.denied()

    def test_existing_candidate_fast_forward(self):
        self.lane.remote_branch = OLD
        self.assertTrue(self.publish()["applied"])
        self.assertEqual(len(self.lane.pushes()), 1)

    def test_push_error_is_uncertain_without_retry(self):
        self.lane.fail = "push"
        with self.assertRaises(PushUncertain): self.publish()
        self.assertEqual(len(self.lane.pushes()), 1)

    def test_accepted_push_then_timeout_is_uncertain(self):
        def timeout(): raise subprocess.TimeoutExpired("git", 120)
        self.lane.after_push = timeout
        with self.assertRaises(PushUncertain): self.publish()
        self.assertEqual(self.lane.remote_branch, HEAD)
        self.assertEqual(len(self.lane.pushes()), 1)

    def test_readback_transport_failure_then_readonly_recovery(self):
        self.lane.after_push = lambda: setattr(self.lane, "fail", "transport")
        with self.assertRaises(PushUncertain): self.publish()
        self.lane.fail = ""
        self.assertEqual(self.lane.remote_head(f"refs/heads/{BRANCH}"), HEAD)
        self.assertEqual(len(self.lane.pushes()), 1)

    def test_ci_only_preview_lagging_main_and_scope(self):
        self.lane.branch = "fix/gitee-temporary-integration-v1"
        self.lane.remote_main = OLD
        self.lane.nonancestor.add((HISTORICAL_MAIN, OLD))
        result = self.lane.publish(HEAD, OLD, False, "", "ci-only")
        self.assertEqual(result["commits_relative_to_main"], [HEAD])
        self.assertFalse(result["integration_eligible"])
        self.assertFalse(result["pr_required"])
        self.assertEqual(self.lane.pushes(), [])

    def test_ci_only_apply_blocked_without_platform_evidence(self):
        self.lane.branch = "fix/gitee-temporary-integration-v1"
        with self.assertRaisesRegex(Denied, "platform automation"):
            self.lane.publish(HEAD, HISTORICAL_MAIN, True, "PUBLISH_EXACT_GITEE_CANDIDATE", "ci-only")
        self.assertEqual(self.lane.pushes(), [])

    def test_ci_only_with_reviewed_evidence_keeps_quick_and_readback(self):
        self.lane.branch = "fix/gitee-temporary-integration-v1"
        with patch.dict(os.environ, {'GITEE_CI_EVIDENCE': 'receipt.json', 'GITEE_CI_EVIDENCE_SHA256': 'f'*64}):
            result = self.lane.publish(HEAD, HISTORICAL_MAIN, True, "PUBLISH_EXACT_GITEE_CANDIDATE", "ci-only")
        self.assertTrue(result['applied'])
        self.assertEqual(result['writes'], 1)
        self.assertFalse(result['merge_authorized'])
        self.assertEqual(self.lane.remote_branch, HEAD)
        self.assertTrue(any('scripts/ops/local_quick_evidence.py' in c for c in self.lane.calls))
        self.assertTrue(any('scripts.ops.gitee_ci_publication_gate' in c for c in self.lane.calls))

    def test_ci_only_evidence_does_not_bypass_quick(self):
        self.lane.branch = "fix/gitee-temporary-integration-v1"
        self.lane.fail = 'quick'
        with patch.dict(os.environ, {'GITEE_CI_EVIDENCE': 'receipt.json', 'GITEE_CI_EVIDENCE_SHA256': 'f'*64}):
            with self.assertRaises(Denied):
                self.lane.publish(HEAD, HISTORICAL_MAIN, True, "PUBLISH_EXACT_GITEE_CANDIDATE", "ci-only")
        self.assertEqual(self.lane.pushes(), [])

    def test_ci_only_invalid_receipt_digest_zero_writes(self):
        self.lane.branch = "fix/gitee-temporary-integration-v1"
        with patch.dict(os.environ, {'GITEE_CI_EVIDENCE': 'receipt.json', 'GITEE_CI_EVIDENCE_SHA256': 'invalid'}):
            with self.assertRaises(Denied):
                self.lane.publish(HEAD, HISTORICAL_MAIN, True, "PUBLISH_EXACT_GITEE_CANDIDATE", "ci-only")
        self.assertEqual(self.lane.pushes(), [])

    def test_ci_only_wrong_scope_zero_writes(self):
        for branch in ["main", "refs/tags/v1", "fix/other"]:
            self.lane.branch = branch
            with self.assertRaises(Denied): self.lane.publish(HEAD, HISTORICAL_MAIN, False, "", "ci-only")
        self.lane.branch = "fix/gitee-temporary-integration-v1"
        self.lane.url = "git@gitee.com:wrong/repo.git"
        with self.assertRaises(Denied): self.lane.publish(HEAD, HISTORICAL_MAIN, False, "", "ci-only")
        self.assertEqual(self.lane.pushes(), [])

    def test_confirmation_required(self):
        with self.assertRaises(Denied): self.lane.publish(HEAD, HISTORICAL_MAIN, True, "")
        self.assertEqual(self.lane.pushes(), [])

    def test_readback_failure_is_not_success(self):
        self.lane.publish_visible = False
        with self.assertRaisesRegex(Denied, "readback"): self.publish()
        self.assertEqual(len(self.lane.pushes()), 1)

    def test_catchup_is_fixed_historical_main(self):
        self.lane.remote_main = OLD
        result = self.lane.catchup(HEAD, OLD, True, "FAST_FORWARD_HISTORICAL_GITEE_MAIN")
        self.assertTrue(result["applied"])
        self.assertEqual(self.lane.pushes(), [("git", "push", GITEE, f"{HISTORICAL_MAIN}:refs/heads/main")])
        self.assertTrue(any(c[1:3] == ("bundle", "verify") for c in self.lane.calls))

    def test_catchup_changed_anchor_denied(self):
        self.lane.anchor = HEAD
        with self.assertRaises(Denied): self.lane.catchup(HEAD, HISTORICAL_MAIN, True, "FAST_FORWARD_HISTORICAL_GITEE_MAIN")
        self.assertEqual(self.lane.pushes(), [])

    def test_catchup_non_fast_forward_denied(self):
        self.lane.remote_main = OLD
        self.lane.nonancestor.add((OLD, HISTORICAL_MAIN))
        with self.assertRaises(Denied): self.lane.catchup(HEAD, OLD, True, "FAST_FORWARD_HISTORICAL_GITEE_MAIN")
        self.assertEqual(self.lane.pushes(), [])

    def test_catchup_confirmation_required(self):
        self.lane.remote_main = OLD
        with self.assertRaises(Denied): self.lane.catchup(HEAD, OLD, True, "")
        self.assertEqual(self.lane.pushes(), [])

    def test_catchup_dry_run_does_not_create_bundle(self):
        self.lane.remote_main = OLD
        self.lane.catchup(HEAD, OLD, False, "")
        self.assertFalse(any(c[1] in {"bundle", "push"} for c in self.lane.calls))

    def test_catchup_branch_drift_denied(self):
        self.lane.after_bundle = lambda: setattr(self.lane, "branch", "fix/other")
        self.assert_catchup_denied()

    def test_catchup_bundle_wrong_head_denied(self):
        self.lane.bundle_head = OLD
        self.assert_catchup_denied()

    def test_catchup_bundle_verification_failure_denied(self):
        self.lane.fail = "bundle"
        self.assert_catchup_denied()

    def assert_catchup_denied(self):
        self.lane.remote_main = OLD
        with self.assertRaises(Denied):
            self.lane.catchup(HEAD, OLD, True, "FAST_FORWARD_HISTORICAL_GITEE_MAIN")
        self.assertEqual(self.lane.pushes(), [])


class OrdinaryPushRaceTests(unittest.TestCase):
    """Real local Git refs demonstrate the boundary; no external repository writes."""

    def test_intermediate_fast_forward_is_accepted_but_divergence_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            env = {**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
                   "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@example.invalid",
                   "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@example.invalid"}
            def git(*args, input=None, check=True):
                return subprocess.run(("git", *args), cwd=root, env=env, input=input,
                                      text=True, capture_output=True, check=check)
            git("init", "--bare", "remote.git")
            git("init", "source")
            def local(*args, **kwargs): return git("-C", "source", *args, **kwargs)
            tree = local("mktree", input="").stdout.strip()
            def commit(message, parent=None):
                return local("commit-tree", tree, *(('-p', parent) if parent else ()),
                             input=message).stdout.strip()
            a = commit("a")
            b = commit("b", a)
            c = commit("c", b)
            d = commit("divergent", b)
            def push(sha, **kwargs): return local("push", "../remote.git", f"{sha}:refs/heads/main", **kwargs)
            push(a)
            self.assertTrue(local("ls-remote", "../remote.git", "refs/heads/main").stdout.startswith(a))
            push(b)  # Other writer advances after our observed A.
            self.assertEqual(push(c).returncode, 0)  # Ordinary push does not reject all drift.
            self.assertNotEqual(push(d, check=False).returncode, 0)
            self.assertTrue(local("ls-remote", "../remote.git", "refs/heads/main").stdout.startswith(c))


if __name__ == "__main__":
    unittest.main()
