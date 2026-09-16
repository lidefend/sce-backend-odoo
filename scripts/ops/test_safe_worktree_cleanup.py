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

    def test_governed_branch_cleanup_force_uses_explicit_force_delete(self) -> None:
        source = (
            Path(__file__).resolve().parent / "branch_cleanup_safe.sh"
        ).read_text(encoding="utf-8")
        self.assertIn('if [[ "${CLEANUP_FORCE:-0}" == "1" ]]', source)
        self.assertIn('delete_flag="-D"', source)
        self.assertIn('git branch "${delete_flag}" -- "${branch}"', source)
        self.assertIn('squash_merge_verified=1', source)
        self.assertIn('--head "$branch" --json headRefOid,number)', source)
        self.assertIn('jq --arg sha "$branch_sha"', source)
        self.assertIn('select(.headRefOid == $sha)', source)


if __name__ == "__main__":
    unittest.main()
