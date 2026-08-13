#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock
import json

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

    def test_cleanup_uses_verified_origin_main_when_controller_head_is_behind(self) -> None:
        path = self.add_worktree("fix/remote-merged")
        (path / "README").write_text("merged remotely\n", encoding="utf-8")
        git(path, "add", "README")
        git(path, "commit", "-m", "remote merged")
        branch_head = git(path, "rev-parse", "HEAD")
        git(path, "push", "origin", "HEAD:main")

        self.assertNotEqual(git(self.root, "rev-parse", "HEAD"), branch_head)
        selected = cleanup.cleanup(self.root, path, apply=True)

        self.assertEqual(selected.head, branch_head)
        self.assertFalse(path.exists())
        self.assertNotIn("fix/remote-merged", git(self.root, "branch", "--format=%(refname:short)").splitlines())

    def test_squash_equivalent_worktree_is_cleanup_eligible(self) -> None:
        path = self.add_worktree("fix/squash-equivalent")
        (path / "squash.txt").write_text("same patch\n", encoding="utf-8")
        git(path, "add", "squash.txt")
        git(path, "commit", "-m", "feature patch")

        (self.root / "squash.txt").write_text("same patch\n", encoding="utf-8")
        git(self.root, "add", "squash.txt")
        git(self.root, "commit", "-m", "squashed upstream patch")
        git(self.root, "push", "origin", "main")

        self.assertTrue(git(self.root, "cherry", "origin/main", "fix/squash-equivalent").startswith("-"))
        cleanup.cleanup(self.root, path, apply=True)

        self.assertFalse(path.exists())
        self.assertNotIn("fix/squash-equivalent", git(self.root, "branch", "--format=%(refname:short)").splitlines())

    def test_historical_main_tree_allows_multi_commit_squash_cleanup(self) -> None:
        path = self.add_worktree("fix/squashed-tree")
        (path / "first.txt").write_text("first\n", encoding="utf-8")
        git(path, "add", "first.txt")
        git(path, "commit", "-m", "first feature commit")
        (path / "second.txt").write_text("second\n", encoding="utf-8")
        git(path, "add", "second.txt")
        git(path, "commit", "-m", "second feature commit")
        branch_tree = git(path, "rev-parse", "HEAD^{tree}")

        (self.root / "first.txt").write_text("first\n", encoding="utf-8")
        (self.root / "second.txt").write_text("second\n", encoding="utf-8")
        git(self.root, "add", "first.txt", "second.txt")
        git(self.root, "commit", "-m", "squashed feature")
        self.assertEqual(git(self.root, "rev-parse", "HEAD^{tree}"), branch_tree)
        (self.root / "later.txt").write_text("main evolved\n", encoding="utf-8")
        git(self.root, "add", "later.txt")
        git(self.root, "commit", "-m", "later main change")
        git(self.root, "push", "origin", "main")

        self.assertTrue(all(line.startswith("+") for line in git(self.root, "cherry", "origin/main", "fix/squashed-tree").splitlines()))
        cleanup.cleanup(self.root, path, apply=True)

        self.assertFalse(path.exists())
        self.assertNotIn("fix/squashed-tree", git(self.root, "branch", "--format=%(refname:short)").splitlines())

    def test_dry_run_preserves_worktree(self) -> None:
        path = self.add_worktree()
        cleanup.cleanup(self.root, path, apply=False)
        self.assertTrue(path.is_dir())

    def test_detach_clean_unmerged_worktree_keeps_exact_branch(self) -> None:
        path = self.add_worktree("feature/retained-unmerged")
        (path / "retained.txt").write_text("unique work\n", encoding="utf-8")
        git(path, "add", "retained.txt")
        git(path, "commit", "-m", "retain unique work")
        expected_head = git(path, "rev-parse", "HEAD")

        selected = cleanup.detach_worktree(
            self.root,
            path,
            expected_head=expected_head,
            apply=True,
            confirmation=cleanup.DETACH_CONFIRMATION,
        )

        self.assertEqual(selected.head, expected_head)
        self.assertFalse(path.exists())
        self.assertEqual(
            git(self.root, "rev-parse", "feature/retained-unmerged"), expected_head
        )

    def test_detach_rejects_dirty_or_changed_worktree(self) -> None:
        path = self.add_worktree("release/retained-record")
        expected_head = git(path, "rev-parse", "HEAD")
        (path / "dirty.txt").write_text("not committed\n", encoding="utf-8")

        with self.assertRaisesRegex(cleanup.CleanupError, "not clean"):
            cleanup.detach_worktree(
                self.root,
                path,
                expected_head=expected_head,
                apply=True,
                confirmation=cleanup.DETACH_CONFIRMATION,
            )
        self.assertTrue(path.is_dir())

        with self.assertRaisesRegex(cleanup.CleanupError, "HEAD changed"):
            cleanup.plan_detach(self.root, path, expected_head="0" * 40)

    def test_dirty_worktree_is_denied(self) -> None:
        path = self.add_worktree()
        (path / "untracked").write_text("keep me\n", encoding="utf-8")
        with self.assertRaisesRegex(cleanup.CleanupError, "not clean"):
            cleanup.cleanup(self.root, path, apply=True)
        self.assertTrue(path.is_dir())

    def test_non_removable_directory_is_denied_before_worktree_removal(self) -> None:
        path = self.add_worktree("fix/non-removable")
        locked = path / "locked"
        locked.mkdir()
        (locked / "tracked.txt").write_text("keep\n", encoding="utf-8")
        git(path, "add", "locked/tracked.txt")
        git(path, "commit", "-m", "merged with locked artifact")
        git(path, "push", "origin", "HEAD:main")

        real_access = cleanup.os.access
        with mock.patch.object(
            cleanup.os,
            "access",
            side_effect=lambda target, mode: False if Path(target) == locked else real_access(target, mode),
        ):
            with self.assertRaisesRegex(cleanup.CleanupError, "non-removable"):
                cleanup.cleanup(self.root, path, apply=True)

        self.assertTrue(path.is_dir())
        self.assertIn("fix/non-removable", git(self.root, "branch", "--format=%(refname:short)").splitlines())

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

    def test_primary_worktree_is_denied_when_called_from_linked_worktree(self) -> None:
        caller = self.add_worktree("fix/linked-caller")

        with self.assertRaisesRegex(cleanup.CleanupError, "primary"):
            cleanup.cleanup(caller, self.root, apply=True)

        self.assertTrue(self.root.is_dir())

    def test_verified_orphan_branch_recovery_deletes_only_exact_local_ref(self) -> None:
        path = self.add_worktree("fix/orphaned")
        expected_head = git(path, "rev-parse", "HEAD")
        git(self.root, "worktree", "remove", str(path))

        selected = cleanup.cleanup_orphan_branch(
            self.root,
            path,
            branch="fix/orphaned",
            expected_head=expected_head,
            apply=False,
            confirmation="",
        )
        self.assertEqual(selected.head, expected_head)
        self.assertIn("fix/orphaned", git(self.root, "branch", "--format=%(refname:short)").splitlines())

        cleanup.cleanup_orphan_branch(
            self.root,
            path,
            branch="fix/orphaned",
            expected_head=expected_head,
            apply=True,
            confirmation=cleanup.ORPHAN_CONFIRMATION,
        )
        self.assertNotIn("fix/orphaned", git(self.root, "branch", "--format=%(refname:short)").splitlines())

    def test_orphan_branch_recovery_rejects_changed_head(self) -> None:
        path = self.add_worktree("fix/orphan-head-changed")
        git(self.root, "worktree", "remove", str(path))

        with self.assertRaisesRegex(cleanup.CleanupError, "branch HEAD changed"):
            cleanup.cleanup_orphan_branch(
                self.root,
                path,
                branch="fix/orphan-head-changed",
                expected_head="0" * 40,
                apply=True,
                confirmation=cleanup.ORPHAN_CONFIRMATION,
            )

    def test_verified_local_branch_cleanup_requires_exact_confirmation(self) -> None:
        path = self.add_worktree("fix/local-only")
        expected_head = git(path, "rev-parse", "HEAD")
        git(self.root, "worktree", "remove", str(path))

        with self.assertRaisesRegex(cleanup.CleanupError, "requires confirmation"):
            cleanup.cleanup_local_branch(
                self.root,
                branch="fix/local-only",
                expected_head=expected_head,
                apply=True,
                confirmation="wrong",
            )
        self.assertIn("fix/local-only", git(self.root, "branch", "--format=%(refname:short)").splitlines())

        cleanup.cleanup_local_branch(
            self.root,
            branch="fix/local-only",
            expected_head=expected_head,
            apply=True,
            confirmation=cleanup.LOCAL_BRANCH_CONFIRMATION,
        )
        self.assertNotIn("fix/local-only", git(self.root, "branch", "--format=%(refname:short)").splitlines())

    def test_local_branch_cleanup_rejects_checked_out_branch(self) -> None:
        path = self.add_worktree("fix/still-checked-out")
        expected_head = git(path, "rev-parse", "HEAD")

        with self.assertRaisesRegex(cleanup.CleanupError, "still checked out"):
            cleanup.cleanup_local_branch(
                self.root,
                branch="fix/still-checked-out",
                expected_head=expected_head,
                apply=False,
                confirmation="",
            )

    def test_local_branch_batch_validates_all_before_deleting(self) -> None:
        first = self.add_worktree("fix/batch-first")
        first_head = git(first, "rev-parse", "HEAD")
        git(self.root, "worktree", "remove", str(first))
        checked_out = self.add_worktree("fix/batch-checked-out")
        checked_out_head = git(checked_out, "rev-parse", "HEAD")

        with self.assertRaisesRegex(cleanup.CleanupError, "still checked out"):
            cleanup.cleanup_local_branches(
                self.root,
                [
                    ("fix/batch-first", first_head),
                    ("fix/batch-checked-out", checked_out_head),
                ],
                apply=True,
                confirmation=cleanup.LOCAL_BRANCH_CONFIRMATION,
            )

        branches = git(self.root, "branch", "--format=%(refname:short)").splitlines()
        self.assertIn("fix/batch-first", branches)
        self.assertIn("fix/batch-checked-out", branches)

    def test_local_branch_batch_deletes_verified_refs(self) -> None:
        specs = []
        for branch in ("fix/batch-one", "fix/batch-two"):
            path = self.add_worktree(branch)
            specs.append((branch, git(path, "rev-parse", "HEAD")))
            git(self.root, "worktree", "remove", str(path))

        selected = cleanup.cleanup_local_branches(
            self.root,
            specs,
            apply=True,
            confirmation=cleanup.LOCAL_BRANCH_CONFIRMATION,
        )

        self.assertEqual([item.branch for item in selected], ["fix/batch-one", "fix/batch-two"])
        branches = git(self.root, "branch", "--format=%(refname:short)").splitlines()
        self.assertNotIn("fix/batch-one", branches)
        self.assertNotIn("fix/batch-two", branches)

    def _superseded_fixture(self):
        path = self.add_worktree("fix/superseding-pr-head")
        (path / "feature.txt").write_text("first\n", encoding="utf-8")
        git(path, "add", "feature.txt")
        git(path, "commit", "-m", "first PR commit")
        candidate_head = git(path, "rev-parse", "HEAD")
        git(self.root, "branch", "codex/superseded", candidate_head)
        (path / "feature.txt").write_text("first\nsecond\n", encoding="utf-8")
        git(path, "add", "feature.txt")
        git(path, "commit", "-m", "complete PR")
        pr_head = git(path, "rev-parse", "HEAD")
        git(self.root, "worktree", "remove", str(path))

        (self.root / "feature.txt").write_text("first\nsecond\n", encoding="utf-8")
        git(self.root, "add", "feature.txt")
        git(self.root, "commit", "-m", "squash merged PR")
        merge_sha = git(self.root, "rev-parse", "HEAD")
        git(self.root, "push", "origin", "main")
        payload = {
            "state": "MERGED",
            "mergedAt": "2026-08-06T00:22:49Z",
            "baseRefName": "main",
            "headRefOid": pr_head,
            "mergeCommit": {"oid": merge_sha},
        }
        return candidate_head, pr_head, payload

    def test_superseded_local_branch_requires_merged_pr_ancestry(self) -> None:
        candidate_head, pr_head, payload = self._superseded_fixture()
        gh_result = subprocess.CompletedProcess([], 0, json.dumps(payload), "")
        with mock.patch.object(cleanup, "run_gh", return_value=gh_result), mock.patch.object(
            cleanup, "fetch_pr_head", return_value=pr_head
        ):
            selected = cleanup.cleanup_superseded_local_branch(
                self.root,
                branch="codex/superseded",
                expected_head=candidate_head,
                pr_number=128,
                expected_pr_head=pr_head,
                apply=True,
                confirmation=cleanup.SUPERSEDED_BRANCH_CONFIRMATION,
            )
        self.assertEqual(selected.head, candidate_head)
        self.assertNotIn("codex/superseded", git(self.root, "branch", "--format=%(refname:short)").splitlines())

    def test_superseded_local_branch_rejects_pr_identity_drift(self) -> None:
        candidate_head, pr_head, payload = self._superseded_fixture()
        for key, value in (("state", "OPEN"), ("baseRefName", "release"), ("headRefOid", "0" * 40)):
            drifted = {**payload, key: value}
            gh_result = subprocess.CompletedProcess([], 0, json.dumps(drifted), "")
            with self.subTest(key=key), mock.patch.object(
                cleanup, "run_gh", return_value=gh_result
            ):
                with self.assertRaisesRegex(cleanup.CleanupError, "identity"):
                    cleanup.cleanup_superseded_local_branch(
                        self.root,
                        branch="codex/superseded",
                        expected_head=candidate_head,
                        pr_number=128,
                        expected_pr_head=pr_head,
                        apply=False,
                        confirmation="",
                    )

    def test_superseded_local_branch_rejects_unrelated_candidate(self) -> None:
        _candidate_head, pr_head, payload = self._superseded_fixture()
        git(self.root, "branch", "fix/unrelated", "main")
        unrelated = git(self.root, "rev-parse", "fix/unrelated")
        gh_result = subprocess.CompletedProcess([], 0, json.dumps(payload), "")
        with mock.patch.object(cleanup, "run_gh", return_value=gh_result), mock.patch.object(
            cleanup, "fetch_pr_head", return_value=pr_head
        ):
            with self.assertRaisesRegex(cleanup.CleanupError, "not an ancestor"):
                cleanup.cleanup_superseded_local_branch(
                    self.root,
                    branch="fix/unrelated",
                    expected_head=unrelated,
                    pr_number=128,
                    expected_pr_head=pr_head,
                    apply=False,
                    confirmation="",
                )

    def test_governed_branch_cleanup_force_uses_explicit_force_delete(self) -> None:
        source = (
            Path(__file__).resolve().parent / "branch_cleanup_safe.sh"
        ).read_text(encoding="utf-8")
        self.assertIn('if [[ "${CLEANUP_FORCE:-0}" == "1" ]]', source)
        self.assertIn('delete_flag="-D"', source)
        self.assertIn('git branch "${delete_flag}" -- "${branch}"', source)


if __name__ == "__main__":
    unittest.main()
