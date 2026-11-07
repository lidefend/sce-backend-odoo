import subprocess
import tempfile
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class PrPublishPreflightTest(unittest.TestCase):
    def test_serial_publish_shares_preflight_and_stops_before_create_on_failure(self):
        source = (ROOT / 'make/codex.mk').read_text()
        block = re.search(r'(?m)^pr\.publish:[^\n]*\n(?:\t[^\n]*\n)+', source)
        self.assertIsNotNone(block)
        # Run the real orchestration recipe against non-mutating fake stages;
        # this exercises recursive make and shared phony prerequisites under -j.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'Makefile').write_text(block.group() + '''
.PHONY: guard.prod.forbid pr.publish.preflight pr.push pr.create
guard.prod.forbid:
\t@:
pr.publish.preflight:
\t@echo preflight >> trace
\t@test "$(FAIL_PREFLIGHT)" != 1
pr.push: pr.publish.preflight
\t@echo push >> trace
\t@test "$(FAIL_PUSH)" != 1
pr.create: pr.publish.preflight
\t@echo create >> trace
''')
            for flags, expected, success in [([], ['preflight', 'push', 'create'], True),
                    (['FAIL_PREFLIGHT=1'], ['preflight'], False),
                    (['FAIL_PUSH=1'], ['preflight', 'push'], False)]:
                (root / 'trace').unlink(missing_ok=True)
                result = subprocess.run(['make', '--no-print-directory', '-j4', '-k', 'pr.publish', *flags],
                                        cwd=root, text=True, capture_output=True)
                self.assertEqual(success, result.returncode == 0, result.stderr)
                self.assertEqual(expected, (root / 'trace').read_text().splitlines())

    def test_head_mismatch_blocks_push_preflight(self):
        proc = subprocess.run(
            ["make", "--no-print-directory", "pr.publish.preflight", "EXPECTED_HEAD=" + "a" * 40],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("does not match EXPECTED_HEAD", proc.stdout + proc.stderr)

    def test_missing_quick_evidence_is_not_reusable(self):
        proc = subprocess.run(
            [
                "python3",
                "scripts/ops/local_quick_evidence.py",
                "verify",
                "--expected-head",
                "0" * 40,
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        self.assertNotEqual(proc.returncode, 0)

    def test_pr_create_blocks_on_local_head_mismatch(self):
        proc = subprocess.run(
            [
                "make",
                "--no-print-directory",
                "pr.create",
                "EXPECTED_HEAD=" + "a" * 40,
                "PR_TITLE=x",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("does not match EXPECTED_HEAD", proc.stdout + proc.stderr)

    def test_pr_create_cannot_bypass_publish_preflight(self):
        makefile = (ROOT / "make" / "codex.mk").read_text(encoding="utf-8")
        import re
        m = re.search(r"^pr\.create:\s*(.*)$", makefile, re.MULTILINE)
        self.assertIsNotNone(m)
        self.assertIn("pr.publish.preflight", m.group(1))

    def test_review_publication_is_explicit_and_merge_keeps_runtime_gate(self):
        makefile = (ROOT / "make" / "codex.mk").read_text(encoding="utf-8")
        self.assertIn("PR_PUBLISH_MODE ?= merge", makefile)
        block = re.search(r"(?m)^pr\.publish\.preflight:[^\n]*\n(?:\t[^\n]*\n)+", makefile)
        self.assertIsNotNone(block)
        self.assertIn("REVIEW_ONLY merge-time runtime evidence may remain pending", block.group())
        self.assertIn("--stage merge --require-ready", block.group())
        self.assertIn("PR_PUBLISH_MODE must be merge or review", block.group())


if __name__ == "__main__":
    unittest.main()
