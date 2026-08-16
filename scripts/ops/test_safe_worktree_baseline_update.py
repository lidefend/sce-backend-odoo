#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import safe_worktree_baseline_update as updater


def git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=root, check=check, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )


class SafeWorktreeBaselineUpdateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        base = Path(self.temp.name)
        self.remote = base / "remote.git"
        self.root = base / "repo"
        self.target = base / "repo-task"
        git(base, "init", "--bare", str(self.remote))
        self.root.mkdir()
        git(self.root, "init", "-b", "main")
        git(self.root, "config", "user.email", "test@example.invalid")
        git(self.root, "config", "user.name", "Test")
        (self.root / "base.txt").write_text("base\n", encoding="utf-8")
        git(self.root, "add", "base.txt")
        git(self.root, "commit", "-m", "base")
        git(self.root, "remote", "add", "origin", str(self.remote))
        git(self.root, "push", "-u", "origin", "main")
        git(self.root, "worktree", "add", "-b", "feature/task", str(self.target), "HEAD")
        git(self.target, "config", "user.email", "test@example.invalid")
        git(self.target, "config", "user.name", "Test")
        (self.target / "task.txt").write_text("task\n", encoding="utf-8")
        git(self.target, "add", "task.txt")
        git(self.target, "commit", "-m", "task")
        self.expected_head = git(self.target, "rev-parse", "HEAD").stdout.strip()
        (self.root / "main.txt").write_text("main\n", encoding="utf-8")
        git(self.root, "add", "main.txt")
        git(self.root, "commit", "-m", "advance main")
        git(self.root, "push", "origin", "main")
        self.baseline = git(self.root, "rev-parse", "HEAD").stdout.strip()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def invoke(self, **overrides: object) -> tuple[updater.Worktree, str]:
        values: dict[str, object] = {
            "root": self.root,
            "candidate": self.target,
            "expected_head": self.expected_head,
            "baseline": self.baseline,
            "mode": "merge",
            "apply": False,
            "confirmation": "",
        }
        values.update(overrides)
        return updater.update(**values)  # type: ignore[arg-type]

    def test_dry_run_preserves_exact_candidate(self) -> None:
        selected, new_head = self.invoke()
        self.assertEqual(selected.head, self.expected_head)
        self.assertEqual(new_head, self.expected_head)
        self.assertEqual(git(self.target, "status", "--porcelain").stdout.strip(), "")

    def test_merge_updates_same_worktree_and_contains_baseline(self) -> None:
        _, new_head = self.invoke(apply=True, confirmation=updater.CONFIRMATION)
        self.assertNotEqual(new_head, self.expected_head)
        self.assertEqual(git(self.target, "branch", "--show-current").stdout.strip(), "feature/task")
        self.assertEqual(git(self.target, "merge-base", "--is-ancestor", self.baseline, new_head).returncode, 0)
        self.assertEqual(git(self.target, "status", "--porcelain").stdout.strip(), "")

    def test_rebase_is_allowed_only_before_publication(self) -> None:
        _, new_head = self.invoke(mode="rebase", apply=True, confirmation=updater.CONFIRMATION)
        self.assertNotEqual(new_head, self.expected_head)
        self.assertEqual(git(self.target, "merge-base", "--is-ancestor", self.baseline, new_head).returncode, 0)

    def test_published_branch_rebase_is_denied(self) -> None:
        git(self.target, "push", "-u", "origin", "feature/task")
        with self.assertRaisesRegex(updater.UpdateError, "already published"):
            self.invoke(mode="rebase")

    def test_dirty_stale_and_non_main_inputs_are_denied(self) -> None:
        (self.target / "dirty.txt").write_text("dirty\n", encoding="utf-8")
        with self.assertRaisesRegex(updater.UpdateError, "must be clean"):
            self.invoke()
        (self.target / "dirty.txt").unlink()
        with self.assertRaisesRegex(updater.UpdateError, "HEAD changed"):
            self.invoke(expected_head="f" * 40)
        with self.assertRaisesRegex(updater.UpdateError, "current origin/main"):
            self.invoke(baseline=self.expected_head)

    def test_conflict_aborts_and_restores_frozen_head(self) -> None:
        # Build a second independent fixture where both sides modify the same line.
        (self.target / "base.txt").write_text("task side\n", encoding="utf-8")
        git(self.target, "add", "base.txt")
        git(self.target, "commit", "-m", "task conflict")
        expected = git(self.target, "rev-parse", "HEAD").stdout.strip()
        (self.root / "base.txt").write_text("main side\n", encoding="utf-8")
        git(self.root, "add", "base.txt")
        git(self.root, "commit", "-m", "main conflict")
        git(self.root, "push", "origin", "main")
        baseline = git(self.root, "rev-parse", "HEAD").stdout.strip()
        with self.assertRaisesRegex(updater.UpdateError, "conflicts"):
            self.invoke(expected_head=expected, baseline=baseline, apply=True, confirmation=updater.CONFIRMATION)
        self.assertEqual(git(self.target, "rev-parse", "HEAD").stdout.strip(), expected)
        self.assertEqual(git(self.target, "status", "--porcelain").stdout.strip(), "")


if __name__ == "__main__":
    unittest.main()
