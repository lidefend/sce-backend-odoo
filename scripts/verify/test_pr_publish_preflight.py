import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class PrPublishPreflightTest(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
