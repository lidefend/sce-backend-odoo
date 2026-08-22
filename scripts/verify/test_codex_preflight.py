from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
PREFLIGHT = ROOT / "scripts" / "ops" / "codex_preflight.sh"


class CodexPreflightTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo = Path(self.tempdir.name)
        self._git("init", "-b", "codex/preflight-test")
        self._git("config", "user.email", "codex-test@example.invalid")
        self._git("config", "user.name", "Codex Test")

        (self.repo / "scripts" / "ops").mkdir(parents=True)
        (self.repo / "scripts" / "verify").mkdir(parents=True)
        shutil.copy2(PREFLIGHT, self.repo / "scripts" / "ops" / "codex_preflight.sh")
        for name, marker in (
            ("agent_context_lint.py", "AGENT_CONTEXT_PASS"),
            ("agent_context_verify.py", "ENGINEERING_CONTEXT_READY"),
        ):
            (self.repo / "scripts" / "verify" / name).write_text(
                f'print("{marker}")\n', encoding="utf-8"
            )
        (self.repo / "tracked.txt").write_text("baseline\n", encoding="utf-8")
        self._git("add", "-A")
        self._git("commit", "-m", "test baseline")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _git(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=self.repo,
            check=True,
            text=True,
            capture_output=True,
        )

    def _run(self, **environment: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env.update(environment)
        return subprocess.run(
            ["bash", "scripts/ops/codex_preflight.sh"],
            cwd=self.repo,
            check=False,
            text=True,
            capture_output=True,
            env=env,
        )

    def test_clean_allowed_branch_passes(self) -> None:
        result = self._run()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("WORKTREE_STATE: CLEAN", result.stdout)
        self.assertIn("AGENT_CONTEXT_PASS", result.stdout)
        self.assertIn("CANDIDATE_FINGERPRINT_SHA256:", result.stdout)

    def test_dirty_iteration_passes_with_complete_fingerprint(self) -> None:
        (self.repo / "tracked.txt").write_text("changed\n", encoding="utf-8")
        (self.repo / "empty-untracked.txt").touch()
        result = self._run()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("WORKTREE_STATE: DIRTY", result.stdout)
        self.assertIn("UNTRACKED_MANIFEST_SHA256:", result.stdout)
        self.assertIn("OK: dirty worktree inventoried", result.stdout)

    def test_clean_mode_rejects_dirty_worktree(self) -> None:
        (self.repo / "tracked.txt").write_text("changed\n", encoding="utf-8")
        result = self._run(CODEX_PREFLIGHT_REQUIRE_CLEAN="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("clean worktree required", result.stdout)

    def test_main_branch_is_rejected(self) -> None:
        self._git("switch", "-c", "main")
        result = self._run()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("branch is not an allowed write branch", result.stdout)

    def test_non_allowlisted_branch_is_rejected(self) -> None:
        self._git("switch", "-c", "topic/not-allowed")
        result = self._run()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("branch is not an allowed write branch", result.stdout)

    def test_audit_csv_change_is_rejected(self) -> None:
        audit_path = self.repo / "docs" / "audit" / "generated.csv"
        audit_path.parent.mkdir(parents=True)
        audit_path.write_text("generated\n", encoding="utf-8")
        result = self._run()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("docs/audit CSV changes detected", result.stdout)


if __name__ == "__main__":
    unittest.main()
