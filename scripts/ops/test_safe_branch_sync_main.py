#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import safe_branch_sync_main as syncer


def git(root: Path, *args: str, check: bool = True, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=root, check=check, text=True, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


class SafeBranchSyncMainTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        base = Path(self.temp.name)
        self.remote = base / "origin.git"
        self.root = base / "repo"
        git(base, "init", "--bare", str(self.remote))
        git(base, "clone", str(self.remote), str(self.root))
        git(self.root, "config", "user.email", "test@example.invalid")
        git(self.root, "config", "user.name", "Test")
        (self.root / "base.txt").write_text("base\n", encoding="utf-8")
        git(self.root, "add", "base.txt")
        git(self.root, "commit", "-m", "base")
        git(self.root, "push", "origin", "HEAD:main")
        git(self.root, "branch", "-M", "main")
        git(self.root, "fetch", "origin", "main")
        self.old_base = git(self.root, "rev-parse", "HEAD").stdout.strip()
        git(self.root, "switch", "-c", "feature/local-sync")
        (self.root / "feature.txt").write_text("feature\n", encoding="utf-8")
        git(self.root, "add", "feature.txt")
        git(self.root, "commit", "-m", "feature")
        self.head = git(self.root, "rev-parse", "HEAD").stdout.strip()
        git(self.root, "switch", "main")
        (self.root / "main.txt").write_text("main\n", encoding="utf-8")
        git(self.root, "add", "main.txt")
        git(self.root, "commit", "-m", "main")
        git(self.root, "push", "origin", "HEAD:main")
        git(self.root, "fetch", "origin", "main")
        self.new_main = git(self.root, "rev-parse", "origin/main").stdout.strip()
        git(self.root, "switch", "feature/local-sync")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def plan(self, **overrides: object) -> syncer.SyncPlan:
        values: dict[str, object] = dict(root=self.root, expected_root=self.root, expected_branch="feature/local-sync", expected_head=self.head, expected_old_base=self.old_base, expected_main=self.new_main, pr_checker=lambda _: False, origin_checker=lambda _: True)
        values.update(overrides)
        return syncer.validate(**values)  # type: ignore[arg-type]

    def test_clean_unpublished_branch_syncs_and_preserves_patch(self) -> None:
        plan = self.plan()
        new_head = syncer.sync(plan)
        self.assertNotEqual(new_head, self.head)
        self.assertEqual(git(self.root, "merge-base", "HEAD", "origin/main").stdout.strip(), self.new_main)
        self.assertTrue(plan.recovery_bundle.is_file())
        self.assertEqual(git(self.root, "bundle", "verify", str(plan.recovery_bundle)).returncode, 0)
        self.assertEqual(git(self.root, "diff", "--name-only", f"{self.new_main}..{new_head}").stdout.splitlines(), ["feature.txt"])
        self.assertEqual(len(git(self.root, "rev-list", f"{self.new_main}..{new_head}").stdout.splitlines()), 1)

    def test_main_and_dirty_worktrees_are_denied(self) -> None:
        git(self.root, "switch", "main")
        with self.assertRaisesRegex(syncer.SyncError, "write-eligible"):
            self.plan(expected_branch="main", expected_head=self.new_main)
        git(self.root, "switch", "feature/local-sync")
        (self.root / "dirty").write_text("x", encoding="utf-8")
        with self.assertRaisesRegex(syncer.SyncError, "clean"):
            self.plan()
        (self.root / "dirty").unlink()

    def test_head_old_base_and_main_identity_are_denied(self) -> None:
        with self.assertRaisesRegex(syncer.SyncError, "EXPECTED_HEAD"):
            self.plan(expected_head="f" * 40)
        with self.assertRaisesRegex(syncer.SyncError, "EXPECTED_OLD_BASE"):
            self.plan(expected_old_base="f" * 40)
        with self.assertRaisesRegex(syncer.SyncError, "EXPECTED_MAIN"):
            self.plan(expected_main="f" * 40)
        with self.assertRaisesRegex(syncer.SyncError, "origin/main does not match"):
            self.plan(expected_main=self.old_base)

    def test_remote_publication_is_denied(self) -> None:
        git(self.root, "push", "origin", "HEAD:feature/local-sync")
        with self.assertRaisesRegex(syncer.SyncError, "published"):
            self.plan()

    def test_open_pr_merge_commit_path_and_writer_are_denied(self) -> None:
        with self.assertRaisesRegex(syncer.SyncError, "open PR"):
            self.plan(pr_checker=lambda _: True)
        common = Path(git(self.root, "rev-parse", "--path-format=absolute", "--git-common-dir").stdout.strip())
        (common / "index.lock").write_text("writer", encoding="utf-8")
        with self.assertRaisesRegex(syncer.SyncError, "writer"):
            self.plan()
        (common / "index.lock").unlink()
        git(self.root, "switch", "-c", "feature/other", self.old_base)
        (self.root / "other.txt").write_text("other\n", encoding="utf-8")
        git(self.root, "add", "other.txt")
        git(self.root, "commit", "-m", "other")
        git(self.root, "switch", "feature/local-sync")
        git(self.root, "commit", "--allow-empty", "-m", "second")
        git(self.root, "merge", "--no-ff", "feature/other", "-m", "merge")
        merge_head = git(self.root, "rev-parse", "HEAD").stdout.strip()
        with self.assertRaisesRegex(syncer.SyncError, "merge commits"):
            self.plan(expected_head=merge_head)

    def temp_path(self, name: str) -> Path:
        return Path(self.temp.name) / name

    def test_conflict_aborts_restores_head_and_environment_is_sanitized(self) -> None:
        git(self.root, "reset", "--hard", self.head)
        (self.root / "base.txt").write_text("feature-change\n", encoding="utf-8")
        git(self.root, "add", "base.txt")
        git(self.root, "commit", "-m", "conflict feature")
        conflict_head = git(self.root, "rev-parse", "HEAD").stdout.strip()
        git(self.root, "switch", "main")
        (self.root / "base.txt").write_text("main-change\n", encoding="utf-8")
        git(self.root, "add", "base.txt")
        git(self.root, "commit", "-m", "conflict main")
        git(self.root, "push", "origin", "HEAD:main")
        git(self.root, "fetch", "origin", "main")
        conflict_main = git(self.root, "rev-parse", "origin/main").stdout.strip()
        git(self.root, "switch", "feature/local-sync")
        plan = self.plan(expected_head=conflict_head, expected_main=conflict_main)
        with self.assertRaisesRegex(syncer.SyncError, "aborted"):
            syncer.sync(plan)
        self.assertEqual(git(self.root, "rev-parse", "HEAD").stdout.strip(), conflict_head)
        self.assertEqual(git(self.root, "status", "--porcelain").stdout.strip(), "")
        original = os.environ.get("GIT_DIR")
        try:
            os.environ["GIT_DIR"] = "/tmp/injected"
            self.assertNotIn("GIT_DIR", syncer.sanitized_environment())
        finally:
            if original is None:
                os.environ.pop("GIT_DIR", None)
            else:
                os.environ["GIT_DIR"] = original

    def test_root_mismatch_and_no_push_or_force_push_in_implementation(self) -> None:
        with self.assertRaisesRegex(syncer.SyncError, "repository root"):
            self.plan(expected_root=self.temp_path("other-root"))
        source = Path(syncer.__file__).read_text(encoding="utf-8")
        self.assertNotIn('["git", "push"', source)
        self.assertNotIn('["git", "push", "--force"', source)

    def test_repository_origin_identity_is_denied(self) -> None:
        with self.assertRaisesRegex(syncer.SyncError, "repository identity"):
            self.plan(origin_checker=lambda _: False)

    def test_cli_uses_an_explicit_target_worktree_for_bootstrap(self) -> None:
        plan = self.plan()
        arguments = [
            "safe_branch_sync_main.py",
            "--worktree", str(self.root),
            "--expected-root", str(self.root),
            "--expected-branch", "feature/local-sync",
            "--expected-head", self.head,
            "--expected-old-base", self.old_base,
            "--expected-main", self.new_main,
            "--confirm", syncer.CONFIRMATION,
        ]
        with mock.patch.object(syncer, "validate", return_value=plan) as validate, \
             mock.patch.object(syncer, "sync", return_value="a" * 40), \
             mock.patch.object(sys, "argv", arguments):
            self.assertEqual(syncer.main(), 0)
        self.assertEqual(validate.call_args.kwargs["root"], self.root)
        self.assertEqual(validate.call_args.kwargs["expected_root"], self.root)

    def test_make_target_keeps_target_worktree_as_the_expected_root(self) -> None:
        makefile = Path(__file__).resolve().parents[2] / "make" / "codex.mk"
        source = makefile.read_text(encoding="utf-8")
        recipe = source.split("workspace.branch.sync-main: guard.prod.forbid", 1)[1].split("\n\n", 1)[0]
        self.assertIn('--worktree "$(WORKSPACE_BRANCH_SYNC_WORKTREE)"', recipe)
        self.assertIn('--expected-root "$(WORKSPACE_BRANCH_SYNC_WORKTREE)"', recipe)


if __name__ == "__main__":
    unittest.main()
