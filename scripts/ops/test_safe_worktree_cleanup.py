#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import safe_worktree_cleanup as cleanup


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    ).stdout.strip()


class SafeWorktreeCleanupTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "repo"
        self.remote = Path(self.temp.name) / "remote.git"
        self.root.mkdir()
        git(self.root, "init", "-b", "main")
        git(self.root, "config", "user.email", "test@example.invalid")
        git(self.root, "config", "user.name", "Test")
        (self.root / "README").write_text("base\n", encoding="utf-8")
        git(self.root, "add", "README")
        git(self.root, "commit", "-m", "base")
        git(self.root, "init", "--bare", str(self.remote))
        git(self.root, "remote", "add", "origin", str(self.remote))
        git(self.root, "push", "-u", "origin", "main")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def add_worktree(self, branch: str = "fix/merged") -> Path:
        path = Path(self.temp.name) / branch.replace("/", "-")
        git(self.root, "worktree", "add", "-b", branch, str(path), "main")
        return path

    def test_clean_merged_worktree_is_removed_locally(self) -> None:
        path = self.add_worktree()
        selected = cleanup.cleanup(self.root, path, apply=True)
        self.assertEqual(selected.branch, "fix/merged")
        self.assertFalse(path.exists())
        self.assertNotIn("fix/merged", git(self.root, "branch", "--format=%(refname:short)").splitlines())

    def test_dry_run_preserves_worktree(self) -> None:
        path = self.add_worktree()
        cleanup.cleanup(self.root, path, apply=False)
        self.assertTrue(path.is_dir())

    def test_dirty_worktree_is_denied(self) -> None:
        path = self.add_worktree()
        (path / "untracked").write_text("keep me\n", encoding="utf-8")
        with self.assertRaisesRegex(cleanup.CleanupError, "not clean"):
            cleanup.cleanup(self.root, path, apply=True)
        self.assertTrue(path.is_dir())

    def test_unmerged_worktree_is_denied(self) -> None:
        path = self.add_worktree("fix/unmerged")
        (path / "README").write_text("changed\n", encoding="utf-8")
        git(path, "add", "README")
        git(path, "commit", "-m", "unmerged")
        with self.assertRaisesRegex(cleanup.CleanupError, "not merged"):
            cleanup.cleanup(self.root, path, apply=True)
        self.assertTrue(path.is_dir())

    def test_primary_worktree_is_denied(self) -> None:
        with self.assertRaisesRegex(cleanup.CleanupError, "primary"):
            cleanup.cleanup(self.root, self.root, apply=True)

    def test_governed_branch_cleanup_force_uses_explicit_force_delete(self) -> None:
        source = (
            Path(__file__).resolve().parent / "branch_cleanup_safe.sh"
        ).read_text(encoding="utf-8")
        self.assertIn('if [[ "${CLEANUP_FORCE:-0}" == "1" ]]', source)
        self.assertIn('delete_flag="-D"', source)
        self.assertIn('git branch "${delete_flag}" -- "${branch}"', source)


if __name__ == "__main__":
    unittest.main()
