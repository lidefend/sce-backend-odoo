#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import base64
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
        (self.root / ".gitignore").write_text("artifacts/\n", encoding="utf-8")
        git(self.root, "add", "README", ".gitignore")
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

    def evidence_receipt(self, path: Path, head: str) -> Path:
        archive = Path(self.temp.name) / "archive" / head
        archive.mkdir(parents=True, exist_ok=True)
        sources = {
            "summary": ("summary.md", f"summary {head}\n".encode()),
            "identity": ("identity.json", json.dumps({"candidateHead": head}).encode()),
            "screenshot": ("screenshot.png", base64.b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
            )),
            "review": ("review.md", f"review {head}\n".encode()),
        }
        rows = []
        manifest_rows = []
        source_root = path / "artifacts" / "delivery"
        source_root.mkdir(parents=True, exist_ok=True)
        for role, (name, content) in sources.items():
            source = source_root / name
            source.write_bytes(content)
            archived = archive / name
            archived.write_bytes(content)
            rows.append({
                "role": role,
                "sourcePath": str(source.relative_to(path)),
                "archivePath": str(archived.resolve()),
                "sha256": hashlib.sha256(archived.read_bytes()).hexdigest(),
            })
            manifest_rows.append({"role": role, "path": str(source.relative_to(path))})
        manifest = source_root / "archive-manifest.json"
        manifest.write_text(json.dumps({
            "schemaVersion": 1,
            "topic": "test-delivery",
            "candidateHead": head,
            "files": manifest_rows,
        }), encoding="utf-8")
        receipt = archive / "archive-receipt.json"
        receipt.write_text(json.dumps({
            "schemaVersion": 1,
            "status": "verified",
            "topic": "test-delivery",
            "candidateWorktree": str(path.resolve()),
            "candidateHead": head,
            "manifestPath": str(manifest.resolve()),
            "manifestSha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
            "files": rows,
        }), encoding="utf-8")
        return receipt

    def test_clean_merged_worktree_is_removed_locally(self) -> None:
        path = self.add_worktree()
        head = git(path, "rev-parse", "HEAD")
        selected = cleanup.cleanup(
            self.root, path, apply=True, evidence_receipt=self.evidence_receipt(path, head)
        )
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

    def test_detach_unmerged_worktree_keeps_exact_branch(self) -> None:
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
            evidence_receipt=self.evidence_receipt(path, expected_head),
        )

        self.assertEqual(selected.head, expected_head)
        self.assertFalse(path.exists())
        self.assertEqual(git(self.root, "rev-parse", selected.branch), expected_head)

    def test_detach_release_worktree_is_allowed_but_primary_is_denied(self) -> None:
        path = self.add_worktree("release/retained-record")
        expected_head = git(path, "rev-parse", "HEAD")
        cleanup.detach_worktree(
            self.root,
            path,
            expected_head=expected_head,
            apply=True,
            confirmation=cleanup.DETACH_CONFIRMATION,
            evidence_receipt=self.evidence_receipt(path, expected_head),
        )
        self.assertEqual(git(self.root, "rev-parse", "release/retained-record"), expected_head)
        with self.assertRaisesRegex(cleanup.CleanupError, "primary"):
            cleanup.plan_detach(
                self.root, self.root, expected_head=git(self.root, "rev-parse", "HEAD")
            )

    def test_detach_rejects_dirty_sha_drift_and_bad_confirmation(self) -> None:
        path = self.add_worktree("fix/retained-dirty")
        expected_head = git(path, "rev-parse", "HEAD")
        (path / "dirty.txt").write_text("not committed\n", encoding="utf-8")
        with self.assertRaisesRegex(cleanup.CleanupError, "not clean"):
            cleanup.plan_detach(self.root, path, expected_head=expected_head)
        with self.assertRaisesRegex(cleanup.CleanupError, "HEAD changed"):
            cleanup.plan_detach(self.root, path, expected_head="0" * 40)
        (path / "dirty.txt").unlink()
        with self.assertRaisesRegex(cleanup.CleanupError, "requires confirmation"):
            cleanup.detach_worktree(
                self.root,
                path,
                expected_head=expected_head,
                apply=True,
                confirmation="wrong",
                evidence_receipt=self.evidence_receipt(path, expected_head),
            )
        self.assertTrue(path.is_dir())

    def test_apply_without_external_evidence_receipt_is_denied(self) -> None:
        path = self.add_worktree("fix/missing-receipt")
        with self.assertRaisesRegex(cleanup.CleanupError, "evidence receipt"):
            cleanup.cleanup(self.root, path, apply=True)
        self.assertTrue(path.is_dir())

    def test_receipt_head_mismatch_is_denied_without_removal(self) -> None:
        path = self.add_worktree("fix/receipt-head-mismatch")
        receipt = self.evidence_receipt(path, "0" * 40)
        with self.assertRaisesRegex(cleanup.CleanupError, "HEAD mismatch"):
            cleanup.cleanup(self.root, path, apply=True, evidence_receipt=receipt)
        self.assertTrue(path.is_dir())

    def test_missing_archived_file_is_denied_without_removal(self) -> None:
        path = self.add_worktree("fix/missing-archived-file")
        head = git(path, "rev-parse", "HEAD")
        receipt = self.evidence_receipt(path, head)
        payload = json.loads(receipt.read_text(encoding="utf-8"))
        Path(payload["files"][0]["archivePath"]).unlink()
        with self.assertRaisesRegex(cleanup.CleanupError, "missing or inside"):
            cleanup.cleanup(self.root, path, apply=True, evidence_receipt=receipt)
        self.assertTrue(path.is_dir())

    def test_archived_file_hash_mismatch_is_denied_without_removal(self) -> None:
        path = self.add_worktree("fix/archived-hash-mismatch")
        head = git(path, "rev-parse", "HEAD")
        receipt = self.evidence_receipt(path, head)
        payload = json.loads(receipt.read_text(encoding="utf-8"))
        Path(payload["files"][0]["archivePath"]).write_text("tampered\n", encoding="utf-8")
        with self.assertRaisesRegex(cleanup.CleanupError, "verification failed"):
            cleanup.cleanup(self.root, path, apply=True, evidence_receipt=receipt)
        self.assertTrue(path.is_dir())

    def test_governed_branch_cleanup_has_no_force_switch_and_binds_shas(self) -> None:
        source = (
            Path(__file__).resolve().parent / "branch_cleanup_safe.sh"
        ).read_text(encoding="utf-8")
        # The historical CLEANUP_FORCE bypass is gone: nothing may skip proof.
        self.assertNotIn("CLEANUP_FORCE", source)
        self.assertIn('EXPECTED_BRANCH_SHA must be the full reviewed branch SHA', source)
        self.assertIn("EXPECTED_MAIN_SHA must be the full SHA of", source)
        self.assertIn("DELETE_EXACT_REVIEWED_BRANCH", source)
        self.assertIn('--force-with-lease=refs/heads/${branch}:${expected_branch_sha}', source)
        self.assertIn('git update-ref -d "refs/heads/${branch}" "$expected_branch_sha"', source)
        self.assertIn("refusing to delete protected branch", source)
        self.assertIn("cannot read", source)
        self.assertIn("squash_merge_verified=1", source)
        self.assertIn('--head "$branch" --json headRefOid,number)', source)
        self.assertIn('select(.headRefOid == $sha)', source)


    def squash_integrate(self, path: Path, branch: str) -> tuple[str, str, str]:
        """Land the worktree HEAD on main as a single-parent, tree-identical commit."""
        head = git(path, "rev-parse", "HEAD")
        tree = git(path, "rev-parse", f"{head}^{{tree}}")
        base = git(self.root, "rev-parse", "HEAD")
        merge = git(self.root, "commit-tree", tree, "-p", base, "-m", f"squash {branch}")
        git(self.root, "update-ref", "refs/heads/main", merge)
        git(self.root, "push", "origin", "main")
        return head, tree, merge

    def track_record(self, payload: dict, name: str = "docs/legacy-retirement.json") -> Path:
        record = self.root / name
        record.parent.mkdir(parents=True, exist_ok=True)
        record.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        git(self.root, "add", name)
        git(self.root, "commit", "-m", "record legacy retirement")
        git(self.root, "push", "origin", "main")
        return record

    def record_payload(self, record: Path) -> dict:
        return json.loads(record.read_text(encoding="utf-8"))

    def recommit_record(self, record: Path, payload: dict) -> None:
        """Commit a revised record: only committed content is admissible."""
        record.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        git(self.root, "add", str(record.relative_to(self.root)))
        git(self.root, "commit", "-m", "revise legacy retirement record")

    def retire(self, path: Path, record: Path, bundle: Path) -> cleanup.Worktree:
        return cleanup.cleanup(
            self.root,
            path,
            apply=True,
            retirement_record=record,
            recovery_bundle=bundle,
            confirmation=cleanup.SQUASH_RETIREMENT_CONFIRMATION,
        )

    def recovery_bundle(self, branch: str, name: str = "recovery.bundle") -> Path:
        bundle = Path(self.temp.name) / name
        git(self.root, "bundle", "create", str(bundle), branch)
        return bundle

    def patch_proof(self, merge: str, number: int = 501) -> None:
        """Pin the merged-PR lookup so integration proofs are deterministic."""
        original = cleanup.merged_pull_request

        def fake(root: Path, branch: str, head: str) -> dict | None:
            return {"number": number, "mergeCommit": merge}

        cleanup.merged_pull_request = fake
        self.addCleanup(setattr, cleanup, "merged_pull_request", original)

    def legacy_record(
        self,
        path: Path,
        branch: str,
        head: str,
        tree: str,
        merge: str,
        pr: int,
        bundle: Path,
        integration: str = "squash",
        name: str = "docs/legacy-retirement.json",
    ) -> Path:
        """Commit the reviewed retirement record for one integrated worktree."""
        return self.track_record({
            "schemaVersion": 1,
            "worktrees": [{
                "path": str(path.resolve()),
                "branch": branch,
                "head": head,
                "integrationKind": integration,
                "evidenceStatus": "absent",
                "reason": "delivered before delivery-evidence archiving existed",
                "mergedPr": pr,
                "mergeCommit": merge,
                "tree": tree,
                "recoveryBundle": {
                    "path": str(bundle),
                    "sha256": hashlib.sha256(bundle.read_bytes()).hexdigest(),
                },
            }],
        }, name)


class SquashIntegrationProofTest(SafeWorktreeCleanupTest):
    def test_squash_integrated_head_passes_merge_check(self) -> None:
        path = self.add_worktree("fix/squash-integrated")
        (path / "feature.txt").write_text("integrated\n", encoding="utf-8")
        git(path, "add", "feature.txt")
        git(path, "commit", "-m", "feature")
        head, _tree, merge = self.squash_integrate(path, "fix/squash-integrated")
        self.patch_proof(merge, 501)
        proof = cleanup.prove_integration(
            self.root,
            cleanup.Worktree(
                path=path.resolve(), branch="fix/squash-integrated", head=head
            ),
        )
        self.assertEqual(proof.kind, "squash")
        self.assertEqual(proof.merge_commit, merge)
        self.assertEqual(proof.pull_request, 501)
        self.assertEqual(proof.tree, git(self.root, "rev-parse", f"{head}^{{tree}}"))

    def test_tree_mismatch_is_denied(self) -> None:
        path = self.add_worktree("fix/tree-mismatch")
        (path / "feature.txt").write_text("integrated\n", encoding="utf-8")
        git(path, "add", "feature.txt")
        git(path, "commit", "-m", "feature")
        _head, tree, merge = self.squash_integrate(path, "fix/tree-mismatch")
        base_tree = git(self.root, "rev-parse", f"{merge}~1^{{tree}}")
        other = git(self.root, "commit-tree", base_tree, "-p", merge, "-m", "other tree")
        git(self.root, "update-ref", "refs/heads/main", other)
        git(self.root, "push", "origin", "main")
        self.patch_proof(other)
        self.assertNotEqual(base_tree, tree)
        with self.assertRaisesRegex(cleanup.CleanupError, "tree does not match"):
            cleanup.cleanup(self.root, path, apply=False)

    def test_merge_commit_outside_main_is_denied(self) -> None:
        path = self.add_worktree("fix/merge-off-main")
        (path / "feature.txt").write_text("integrated\n", encoding="utf-8")
        git(path, "add", "feature.txt")
        git(path, "commit", "-m", "feature")
        head = git(path, "rev-parse", "HEAD")
        off_main = git(self.root, "commit-tree", git(path, "rev-parse", "HEAD^{tree}"),
                       "-p", head, "-m", "off main")
        self.patch_proof(off_main)
        with self.assertRaisesRegex(cleanup.CleanupError, "not on origin/main"):
            cleanup.cleanup(self.root, path, apply=False)

    def test_merge_commit_with_two_parents_is_denied(self) -> None:
        path = self.add_worktree("fix/multi-parent")
        (path / "feature.txt").write_text("integrated\n", encoding="utf-8")
        git(path, "add", "feature.txt")
        git(path, "commit", "-m", "feature")
        main_tip = git(self.root, "rev-parse", "HEAD")
        orphan = git(self.root, "commit-tree", git(self.root, "rev-parse", f"{main_tip}^{{tree}}"),
                     "-m", "unrelated side history")
        merged = git(self.root, "commit-tree", git(path, "rev-parse", "HEAD^{tree}"),
                     "-p", main_tip, "-p", orphan, "-m", "real merge")
        git(self.root, "update-ref", "refs/heads/main", merged)
        git(self.root, "push", "origin", "main")
        self.patch_proof(merged)
        with self.assertRaisesRegex(cleanup.CleanupError, "single-parent"):
            cleanup.cleanup(self.root, path, apply=False)


class LegacyRetirementRecordTest(SafeWorktreeCleanupTest):
    def prepare(self, branch: str = "codex/legacy-retired"):
        path = self.add_worktree(branch)
        (path / "feature.txt").write_text("integrated\n", encoding="utf-8")
        git(path, "add", "feature.txt")
        git(path, "commit", "-m", "legacy feature")
        head, tree, merge = self.squash_integrate(path, branch)
        bundle = self.recovery_bundle(branch)
        record = self.legacy_record(path, branch, head, tree, merge, 501, bundle)
        self.patch_proof(merge)
        return path, head, merge, record, bundle

    def test_record_and_bundle_allow_squash_retirement(self) -> None:
        path, head, _merge, record, bundle = self.prepare()
        selected = cleanup.cleanup(
            self.root,
            path,
            apply=True,
            retirement_record=record,
            recovery_bundle=bundle,
            confirmation=cleanup.SQUASH_RETIREMENT_CONFIRMATION,
        )
        self.assertEqual(selected.head, head)
        self.assertFalse(path.exists())
        self.assertNotIn("codex/legacy-retired", git(self.root, "branch", "--format=%(refname:short)").splitlines())

    def test_receipt_path_also_allows_squash_retirement(self) -> None:
        path = self.add_worktree("fix/squash-with-receipt")
        (path / "feature.txt").write_text("integrated\n", encoding="utf-8")
        git(path, "add", "feature.txt")
        git(path, "commit", "-m", "feature")
        head, _tree, merge = self.squash_integrate(path, "fix/squash-with-receipt")
        self.patch_proof(merge)
        cleanup.cleanup(
            self.root, path, apply=True, evidence_receipt=self.evidence_receipt(path, head)
        )
        self.assertFalse(path.exists())

    def test_wrong_confirmation_is_denied(self) -> None:
        path, _head, _merge, record, bundle = self.prepare("codex/wrong-confirmation")
        with self.assertRaisesRegex(cleanup.CleanupError, "requires confirmation"):
            cleanup.cleanup(
                self.root, path, apply=True, retirement_record=record, recovery_bundle=bundle,
                confirmation="WRONG",
            )
        self.assertTrue(path.is_dir())

    def test_untracked_record_is_denied(self) -> None:
        path, _head, _merge, record, bundle = self.prepare("codex/untracked-record")
        untracked = self.root / "docs" / "untracked-retirement.json"
        untracked.write_text(record.read_text(encoding="utf-8"), encoding="utf-8")
        record = untracked
        with self.assertRaisesRegex(cleanup.CleanupError, "tracked repository file"):
            cleanup.cleanup(
                self.root, path, apply=True, retirement_record=record, recovery_bundle=bundle,
                confirmation=cleanup.SQUASH_RETIREMENT_CONFIRMATION,
            )
        self.assertTrue(path.is_dir())

    def test_bundle_hash_mismatch_is_denied(self) -> None:
        path, _head, _merge, record, bundle = self.prepare("codex/bundle-mismatch")
        bundle.write_bytes(b"tampered")
        with self.assertRaisesRegex(cleanup.CleanupError, "recovery bundle hash"):
            cleanup.cleanup(
                self.root, path, apply=True, retirement_record=record, recovery_bundle=bundle,
                confirmation=cleanup.SQUASH_RETIREMENT_CONFIRMATION,
            )
        self.assertTrue(path.is_dir())

    def test_record_claiming_wrong_merge_is_denied(self) -> None:
        path, _head, merge, record, bundle = self.prepare("codex/wrong-merge-claim")
        payload = self.record_payload(record)
        payload["worktrees"][0]["mergeCommit"] = "0" * 40
        self.recommit_record(record, payload)
        with self.assertRaisesRegex(cleanup.CleanupError, "merge commit does not match"):
            self.retire(path, record, bundle)
        self.assertTrue(path.is_dir())

    def test_uncommitted_record_edit_cannot_widen_retirement(self) -> None:
        path, _head, _merge, record, bundle = self.prepare("codex/dirty-record")
        payload = self.record_payload(record)
        payload["worktrees"][0]["mergedPr"] = 999999
        record.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        selected = self.retire(path, record, bundle)
        self.assertEqual(selected.branch, "codex/dirty-record")
        self.assertFalse(path.exists())

    def test_record_must_be_committed_at_head(self) -> None:
        path, _head, _merge, record, bundle = self.prepare("codex/staged-only-record")
        payload = self.record_payload(record)
        staged = self.root / "docs" / "staged-only-retirement.json"
        staged.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        git(self.root, "add", "docs/staged-only-retirement.json")
        with self.assertRaisesRegex(cleanup.CleanupError, "committed at HEAD"):
            self.retire(path, staged, bundle)
        self.assertTrue(path.is_dir())

    def test_non_integer_merged_pr_is_denied(self) -> None:
        path, _head, _merge, record, bundle = self.prepare("codex/bad-pr-field")
        payload = self.record_payload(record)
        payload["worktrees"][0]["mergedPr"] = "not-a-number"
        self.recommit_record(record, payload)
        with self.assertRaisesRegex(cleanup.CleanupError, "mergedPr must be an integer"):
            self.retire(path, record, bundle)
        self.assertTrue(path.is_dir())

    def test_coercible_merged_pr_values_are_denied(self) -> None:
        for value in (501.5, 501.0, "501", True, None):
            with self.subTest(value=value):
                path, _head, _merge, record, bundle = self.prepare(
                    f"codex/pr-field-{str(value).replace('.', '-').lower()}"
                )
                payload = self.record_payload(record)
                payload["worktrees"][0]["mergedPr"] = value
                self.recommit_record(record, payload)
                with self.assertRaisesRegex(
                    cleanup.CleanupError, "mergedPr must be an integer"
                ):
                    self.retire(path, record, bundle)
                self.assertTrue(path.is_dir())

    def test_bundle_not_covering_head_is_denied(self) -> None:
        path, _head, _merge, record, bundle = self.prepare("codex/bundle-other-ref")
        other = Path(self.temp.name) / "other-ref.bundle"
        git(self.root, "bundle", "create", str(other), "main")
        payload = self.record_payload(record)
        payload["worktrees"][0]["recoveryBundle"] = {
            "path": str(other),
            "sha256": hashlib.sha256(other.read_bytes()).hexdigest(),
        }
        self.recommit_record(record, payload)
        with self.assertRaisesRegex(cleanup.CleanupError, "does not cover the worktree HEAD"):
            self.retire(path, record, other)
        self.assertTrue(path.is_dir())

    def test_unreadable_remote_state_is_denied(self) -> None:
        path, _head, _merge, record, bundle = self.prepare("codex/unreadable-remote")
        git(self.root, "remote", "set-url", "origin", str(Path(self.temp.name) / "missing.git"))
        with self.assertRaisesRegex(cleanup.CleanupError, "cannot read origin/"):
            cleanup.remote_branch_sha(self.root, "codex/unreadable-remote")
        self.assertTrue(path.is_dir())

    def test_remote_branch_at_integrated_head_is_deleted_under_lease(self) -> None:
        path, head, _merge, record, bundle = self.prepare("codex/remote-integrated")
        git(self.root, "push", "origin", "codex/remote-integrated")
        selected = self.retire(path, record, bundle)
        self.assertEqual(selected.head, head)
        self.assertFalse(path.exists())
        self.assertEqual(
            git(self.root, "ls-remote", "--heads", "origin", "codex/remote-integrated"), ""
        )

    def test_remote_branch_moved_away_is_denied(self) -> None:
        path, _head, _merge, record, bundle = self.prepare("codex/remote-moved")
        git(self.root, "push", "origin", "codex/remote-moved")
        moved = git(self.root, "rev-parse", "origin/main")
        git(self.root, "push", "-f", "origin", f"{moved}:refs/heads/codex/remote-moved")
        with self.assertRaisesRegex(cleanup.CleanupError, "moved: expected="):
            self.retire(path, record, bundle)
        self.assertTrue(path.is_dir())

    def test_branch_ref_moved_before_deletion_is_denied(self) -> None:
        path, head, _merge, record, bundle = self.prepare("codex/ref-moves-mid-flight")
        stray = git(self.root, "commit-tree", f"{head}^{{tree}}", "-m", "stray")
        original = cleanup.remote_branch_sha

        def move_then_report(root: Path, branch: str) -> str | None:
            git(root, "update-ref", f"refs/heads/{branch}", stray)
            return None

        cleanup.remote_branch_sha = move_then_report
        self.addCleanup(setattr, cleanup, "remote_branch_sha", original)
        with self.assertRaisesRegex(cleanup.CleanupError, "branch ref moved before deletion"):
            self.retire(path, record, bundle)
        self.assertEqual(
            git(self.root, "rev-parse", "refs/heads/codex/ref-moves-mid-flight"), stray
        )

    def test_denial_reports_completed_destructive_steps(self) -> None:
        path, _head, _merge, record, bundle = self.prepare("codex/locked-retirement")
        git(self.root, "push", "origin", "codex/locked-retirement")
        git(self.root, "worktree", "lock", str(path))
        with self.assertRaisesRegex(
            cleanup.CleanupError, "destructive steps already completed: remote ref origin/"
        ):
            self.retire(path, record, bundle)
        self.assertEqual(
            git(self.root, "ls-remote", "--heads", "origin", "codex/locked-retirement"), ""
        )
        self.assertTrue(path.is_dir())


class AncestorRetirementRecordTest(SafeWorktreeCleanupTest):
    """A topic merged as a real merge commit is retired through containment.

    Its HEAD is contained in ``origin/main``, so the squash tree-identity proof
    does not apply, but the reviewed record is still bound to the verified
    merged pull request of the exact HEAD.
    """

    def prepare(self, branch: str = "codex/ancestor-retired"):
        path = self.add_worktree(branch)
        head = git(path, "rev-parse", "HEAD")
        merge = git(self.root, "rev-parse", "HEAD")
        bundle = self.recovery_bundle(branch)
        record = self.legacy_record(
            path,
            branch,
            head,
            git(path, "rev-parse", f"{head}^{{tree}}"),
            merge,
            524,
            bundle,
            integration="ancestor",
            name="docs/ancestor-retirement.json",
        )
        self.patch_proof(merge, 524)
        return path, head, merge, record, bundle

    def test_contained_head_is_proven_as_ancestor_integration(self) -> None:
        path = self.add_worktree("fix/ancestor-contained")
        head = git(path, "rev-parse", "HEAD")
        original = cleanup.merged_pull_request
        cleanup.merged_pull_request = lambda root, branch, head: None
        self.addCleanup(setattr, cleanup, "merged_pull_request", original)
        proof = cleanup.prove_integration(
            self.root,
            cleanup.Worktree(
                path=path.resolve(), branch="fix/ancestor-contained", head=head
            ),
        )
        self.assertEqual(proof.kind, "ancestor")
        self.assertEqual(proof.pull_request, 0)
        self.assertEqual(proof.tree, git(self.root, "rev-parse", f"{head}^{{tree}}"))

    def test_record_and_bundle_allow_ancestor_retirement(self) -> None:
        path, head, _merge, record, bundle = self.prepare()
        selected = cleanup.cleanup(
            self.root,
            path,
            apply=True,
            retirement_record=record,
            recovery_bundle=bundle,
            confirmation=cleanup.SQUASH_RETIREMENT_CONFIRMATION,
        )
        self.assertEqual(selected.head, head)
        self.assertFalse(path.exists())
        self.assertNotIn(
            "codex/ancestor-retired",
            git(self.root, "branch", "--format=%(refname:short)").splitlines(),
        )

    def test_ancestor_retirement_without_a_verified_merged_pr_is_denied(self) -> None:
        path, _head, _merge, record, bundle = self.prepare("codex/ancestor-no-pr")
        original = cleanup.merged_pull_request
        cleanup.merged_pull_request = lambda root, branch, head: None
        self.addCleanup(setattr, cleanup, "merged_pull_request", original)
        with self.assertRaisesRegex(cleanup.CleanupError, "verified merged pull request"):
            cleanup.cleanup(
                self.root,
                path,
                apply=True,
                retirement_record=record,
                recovery_bundle=bundle,
                confirmation=cleanup.SQUASH_RETIREMENT_CONFIRMATION,
            )
        self.assertTrue(path.is_dir())


class GovernedBranchCleanupScriptTest(unittest.TestCase):
    """Behavioural tests for the governed branch deletion entry.

    The script is driven against an isolated repository through
    ``CLEAN_BRANCH_ROOT`` so the real rules run without touching this checkout.
    The remote is named ``gitee-mirror`` so no GitHub provider is ever reached.
    """

    SCRIPT = Path(__file__).resolve().parent / "branch_cleanup_safe.sh"
    REMOTE = "gitee-mirror"

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        base = Path(self.temp.name)
        self.remote = base / "mirror.git"
        self.root = base / "repo"
        self.root.mkdir()
        git(base, "init", "--bare", str(self.remote))
        git(self.root, "init", "-b", "main")
        git(self.root, "config", "user.email", "test@example.invalid")
        git(self.root, "config", "user.name", "Test")
        (self.root / "README").write_text("base\n", encoding="utf-8")
        git(self.root, "add", "README")
        git(self.root, "commit", "-m", "base")
        git(self.root, "remote", "add", self.REMOTE, str(self.remote))
        git(self.root, "push", "-u", self.REMOTE, "main")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def main_sha(self) -> str:
        return git(self.root, "rev-parse", "refs/heads/main")

    def landed_branch(self, branch: str = "fix/landed-topic") -> str:
        """A branch whose tip is contained in the remote's main."""
        git(self.root, "switch", "-c", branch, "main")
        (self.root / f"{branch.replace('/', '-')}.txt").write_text("x\n", encoding="utf-8")
        git(self.root, "add", ".")
        git(self.root, "commit", "-m", branch)
        git(self.root, "push", self.REMOTE, branch)
        sha = git(self.root, "rev-parse", "refs/heads/" + branch)
        git(self.root, "switch", "main")
        git(self.root, "merge", "--ff-only", branch)
        git(self.root, "push", self.REMOTE, "main")
        return sha

    def run_script(self, branch: str, *, sha: str, main: str, **overrides: str):
        import os

        env = {
            **os.environ,
            "CLEAN_BRANCH_ROOT": str(self.root),
            "CLEAN_BRANCH_REMOTE": self.REMOTE,
            "EXPECTED_BRANCH_SHA": sha,
            "EXPECTED_MAIN_SHA": main,
        }
        env.update(overrides)
        return subprocess.run(
            ["bash", str(self.SCRIPT), branch],
            text=True,
            capture_output=True,
            env=env,
        )

    def remote_ref(self, branch: str) -> str:
        return git(self.root, "ls-remote", "--heads", self.REMOTE, branch)

    def test_dry_run_reports_without_deleting(self) -> None:
        sha = self.landed_branch()
        result = self.run_script("fix/landed-topic", sha=sha, main=self.main_sha())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("DRY-RUN ok", result.stdout)
        self.assertIn(sha, self.remote_ref("fix/landed-topic"))
        self.assertEqual(git(self.root, "rev-parse", "refs/heads/fix/landed-topic"), sha)

    def test_apply_requires_confirmation_before_deleting(self) -> None:
        sha = self.landed_branch()
        result = self.run_script(
            "fix/landed-topic", sha=sha, main=self.main_sha(), APPLY="1"
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DELETE_EXACT_REVIEWED_BRANCH", result.stderr)
        self.assertIn(sha, self.remote_ref("fix/landed-topic"))

    def test_apply_deletes_remote_then_local(self) -> None:
        sha = self.landed_branch()
        result = self.run_script(
            "fix/landed-topic",
            sha=sha,
            main=self.main_sha(),
            APPLY="1",
            CLEAN_BRANCH_CONFIRM="DELETE_EXACT_REVIEWED_BRANCH",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.remote_ref("fix/landed-topic"), "")
        self.assertNotEqual(
            subprocess.run(
                ["git", "show-ref", "--verify", "--quiet", "refs/heads/fix/landed-topic"],
                cwd=self.root,
            ).returncode,
            0,
        )

    def test_local_sha_drift_is_refused(self) -> None:
        self.landed_branch()
        result = self.run_script("fix/landed-topic", sha="0" * 40, main=self.main_sha())
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("local SHA drift", result.stderr)

    def test_remote_sha_drift_is_refused(self) -> None:
        sha = self.landed_branch()
        main = self.main_sha()
        # Move only the remote ref: the local branch keeps the reviewed tip, so
        # this isolates the remote-drift refusal from the local one.
        (self.root / "moved.txt").write_text("moved\n", encoding="utf-8")
        git(self.root, "add", ".")
        git(self.root, "commit", "-m", "move the remote branch tip")
        git(self.root, "push", self.REMOTE, "main:refs/heads/fix/landed-topic")
        result = self.run_script("fix/landed-topic", sha=sha, main=main)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("branch drift", result.stderr)
        self.assertEqual(git(self.root, "rev-parse", "refs/heads/fix/landed-topic"), sha)
        self.assertNotEqual(self.remote_ref("fix/landed-topic"), "")

    def test_main_drift_is_refused(self) -> None:
        sha = self.landed_branch()
        before = git(self.root, "rev-parse", "refs/heads/main")
        (self.root / "later.txt").write_text("later\n", encoding="utf-8")
        git(self.root, "add", ".")
        git(self.root, "commit", "-m", "advance main")
        git(self.root, "push", self.REMOTE, "main")
        result = self.run_script("fix/landed-topic", sha=sha, main=before)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("main drift", result.stderr)
        self.assertIn(sha, self.remote_ref("fix/landed-topic"))

    def test_unmerged_branch_is_refused(self) -> None:
        git(self.root, "switch", "-c", "fix/never-landed", "main")
        (self.root / "unmerged.txt").write_text("n\n", encoding="utf-8")
        git(self.root, "add", ".")
        git(self.root, "commit", "-m", "unmerged")
        git(self.root, "push", self.REMOTE, "fix/never-landed")
        sha = git(self.root, "rev-parse", "refs/heads/fix/never-landed")
        git(self.root, "switch", "main")
        result = self.run_script("fix/never-landed", sha=sha, main=self.main_sha())
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not contained in", result.stderr)
        self.assertIn(sha, self.remote_ref("fix/never-landed"))

    def test_protected_and_occupied_branches_are_refused(self) -> None:
        sha = self.landed_branch("fix/occupied-topic")
        result = self.run_script("main", sha=sha, main=self.main_sha())
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("outside the canonical governed prefixes", result.stderr)

        release = self.run_script("release/topic", sha=sha, main=self.main_sha())
        self.assertNotEqual(release.returncode, 0)
        self.assertIn("refusing to delete protected branch", release.stderr)

        git(self.root, "worktree", "add", str(Path(self.temp.name) / "side"), "fix/occupied-topic")
        occupied = self.run_script("fix/occupied-topic", sha=sha, main=self.main_sha())
        self.assertNotEqual(occupied.returncode, 0)
        self.assertIn("checked out by a worktree", occupied.stderr)

    def test_expected_main_must_be_a_full_sha(self) -> None:
        sha = self.landed_branch()
        result = self.run_script("fix/landed-topic", sha=sha, main="HEAD")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("EXPECTED_MAIN_SHA must be the full SHA", result.stderr)


if __name__ == "__main__":
    unittest.main()
