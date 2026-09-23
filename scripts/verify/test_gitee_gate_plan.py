"""Focused formal selection and real Git deletion/rename boundary tests."""
import copy
from pathlib import Path
import subprocess
import tempfile
import unittest
from scripts.ci.gitee_gate_plan import CHECKS, changed_paths, digest, plan


class GatePlanTests(unittest.TestCase):
    def build(self, paths=("docs/example.md",), **kw):
        args = dict(head="a" * 40, base="b" * 40, source_branch="fix/example", pr_number=1, paths=paths)
        args.update(kw)
        return plan(**args)

    def modes(self, record):
        return {x["name"]: x["mode"] for x in record["checks"]}

    def test_all_four_are_pending_never_eligible(self):
        r = self.build()
        self.assertEqual(tuple(x["name"] for x in r["checks"]), CHECKS)
        self.assertTrue(all(x["state"] == "not_run" for x in r["checks"]))
        self.assertFalse(r["execution_ready"])
        self.assertFalse(r["integration_eligible"])

    def test_fast(self):
        self.assertEqual(self.modes(self.build()), dict(public_guard="skip_fast", merge_policy_gate="fast",
            professional_quality_gate="fast", frontend_release_gate="skip"))

    def test_standard_frontend(self):
        m = self.modes(self.build(("frontend/apps/web/src/components/Example.vue",)))
        self.assertEqual(m["frontend_release_gate"], "standard")
        self.assertEqual(m["professional_quality_gate"], "standard_frontend")

    def test_backend(self):
        m = self.modes(self.build(("addons/example/models/item.py",)))
        self.assertEqual(m["professional_quality_gate"], "standard_backend")
        self.assertEqual(m["frontend_release_gate"], "skip")

    def test_high_risk_governance(self):
        r = self.build(("scripts/ci/example.py",))
        self.assertEqual(r["lane"], "HIGH_RISK")
        self.assertEqual(self.modes(r)["professional_quality_gate"], "governance")

    def test_high_risk_backend(self):
        r = self.build(("scripts/ci/example.py", "scripts/verify/test_example.py"))
        self.assertEqual(self.modes(r)["professional_quality_gate"], "standard_backend")

    def test_candidate_full(self):
        r = self.build(("frontend/pnpm-lock.yaml",), candidate=True)
        self.assertEqual(self.modes(r)["frontend_release_gate"], "full")
        self.assertEqual(self.modes(r)["professional_quality_gate"], "full")
        self.assertTrue(r["toolchain"]["python310_compatibility_required"])

    def test_ordinary_lockfile_standard(self):
        r = self.build(("frontend/pnpm-lock.yaml",))
        self.assertEqual(self.modes(r)["frontend_release_gate"], "standard")
        self.assertEqual(self.modes(r)["professional_quality_gate"], "standard_frontend")

    def test_digest_binds_source_target_pr_and_request(self):
        original = self.build()
        for kw in [dict(head="c"*40), dict(base="c"*40), dict(pr_number=2), dict(candidate=True)]:
            self.assertNotEqual(original["plan_sha256"], self.build(**kw)["plan_sha256"])
        content = copy.deepcopy(original)
        expected = content.pop("plan_sha256")
        self.assertEqual(digest(content), expected)

    def test_invalid_inputs_rejected(self):
        for kw in [dict(head="main"), dict(base="0"*40), dict(base="a"*40), dict(pr_number=True),
                   dict(pr_number=0), dict(candidate="false"), dict(source_branch="main"),
                   dict(source_branch="fix/a..b"), dict(paths=[]), dict(paths=["../escape"]),
                   dict(paths=["x\ny"]), dict(paths=["/absolute"])]:
            with self.subTest(kw=kw), self.assertRaises(ValueError):
                self.build(**kw)

    def test_unknown_path_fails_closed(self):
        self.assertEqual(self.build(("unknown/source.dat",))["lane"], "HIGH_RISK")

    def test_real_git_move_and_delete_preserve_risk(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            def git(*args):
                return subprocess.check_output(["git", "-c", "user.name=Gate Test", "-c",
                    "user.email=gate@example.invalid", *args], cwd=root, stderr=subprocess.DEVNULL, text=True).strip()
            git("init")
            (root/"scripts/ci").mkdir(parents=True)
            (root/"scripts/ci/old.py").write_text("print('test')\n")
            (root/"scripts/ci/deleted.py").write_text("print('delete')\n")
            git("add", "."); git("commit", "-m", "base")
            base = git("rev-parse", "HEAD")
            (root/"docs").mkdir()
            (root/"scripts/ci/old.py").rename(root/"docs/moved.md")
            (root/"scripts/ci/deleted.py").unlink()
            git("add", "-A"); git("commit", "-m", "move and delete")
            head = git("rev-parse", "HEAD")
            paths = changed_paths(root, base, head)
            self.assertEqual(set(paths), {"scripts/ci/old.py", "scripts/ci/deleted.py", "docs/moved.md"})
            self.assertEqual(self.build(paths)["lane"], "HIGH_RISK")
            with self.assertRaises(subprocess.CalledProcessError):
                changed_paths(root, head, base)


if __name__ == "__main__":
    unittest.main()
