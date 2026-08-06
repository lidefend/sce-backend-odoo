#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import safe_worktree_create as creator


def git(
    root: Path,
    *args: str,
    check: bool = True,
    input: str | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=check,
        text=True,
        input=input,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


class SafeWorktreeCreateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "repo"
        self.root.mkdir()
        git(self.root, "init", "-b", "main")
        git(self.root, "config", "user.email", "test@example.invalid")
        git(self.root, "config", "user.name", "Test")
        (self.root / "README").write_text("base\n", encoding="utf-8")
        git(self.root, "add", "README")
        git(self.root, "commit", "-m", "base")
        self.base = git(self.root, "rev-parse", "HEAD").stdout.strip()
        git(self.root, "switch", "-c", "fix/controller")
        self.target = Path(self.temp.name) / "repo-task"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def create(self, **overrides: object) -> creator.WorktreePlan:
        values: dict[str, object] = {
            "root": self.root,
            "candidate": self.target,
            "branch": "feature/task",
            "base": self.base,
            "apply": False,
            "confirmation": "",
        }
        values.update(overrides)
        return creator.create(**values)  # type: ignore[arg-type]

    def test_dry_run_is_non_mutating(self) -> None:
        plan = self.create()
        self.assertEqual(plan.base, self.base)
        self.assertFalse(self.target.exists())

    def test_apply_creates_exact_clean_worktree(self) -> None:
        plan = self.create(apply=True, confirmation=creator.CONFIRMATION)
        self.assertEqual(git(plan.path, "branch", "--show-current").stdout.strip(), "feature/task")
        self.assertEqual(git(plan.path, "rev-parse", "HEAD").stdout.strip(), self.base)
        self.assertEqual(git(plan.path, "status", "--porcelain").stdout.strip(), "")

    def test_apply_requires_exact_confirmation(self) -> None:
        with self.assertRaisesRegex(creator.CreateError, "requires --confirm"):
            self.create(apply=True, confirmation="YES")
        self.assertFalse(self.target.exists())

    def test_relative_and_outside_paths_are_denied(self) -> None:
        with self.assertRaisesRegex(creator.CreateError, "absolute"):
            self.create(candidate=Path("repo-task"))
        with self.assertRaisesRegex(creator.CreateError, "direct sibling"):
            self.create(candidate=Path(self.temp.name) / "nested" / "repo-task")

    def test_unrelated_sibling_name_is_denied(self) -> None:
        with self.assertRaisesRegex(creator.CreateError, "must start"):
            self.create(candidate=Path(self.temp.name) / "other-task")

    def test_invalid_or_existing_branch_is_denied(self) -> None:
        with self.assertRaisesRegex(creator.CreateError, "write-eligible"):
            self.create(branch="main")
        git(self.root, "branch", "feature/task", self.base)
        with self.assertRaisesRegex(creator.CreateError, "already exists"):
            self.create()

    def test_short_missing_and_unreachable_bases_are_denied(self) -> None:
        with self.assertRaisesRegex(creator.CreateError, "full 40-character"):
            self.create(base=self.base[:12])
        with self.assertRaisesRegex(creator.CreateError, "does not exist"):
            self.create(base="f" * 40)
        orphan = git(self.root, "commit-tree", f"{self.base}^{{tree}}", input="orphan\n")
        orphan_sha = orphan.stdout.strip()
        with self.assertRaisesRegex(creator.CreateError, "not reachable"):
            self.create(base=orphan_sha)

    def test_existing_path_is_denied(self) -> None:
        self.target.mkdir()
        with self.assertRaisesRegex(creator.CreateError, "already exists"):
            self.create()


if __name__ == "__main__":
    unittest.main()
