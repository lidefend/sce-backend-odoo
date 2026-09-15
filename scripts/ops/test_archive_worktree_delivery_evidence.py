#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import archive_worktree_delivery_evidence as evidence


class ArchiveWorktreeDeliveryEvidenceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "repo"
        self.archive_root = Path(self.temp.name) / "archives"
        self.root.mkdir()
        subprocess.run(["git", "init", "-b", "main"], cwd=self.root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.root, check=True)
        for role in evidence.REQUIRED_ROLES:
            path = self.root / f"{role}.txt"
            path.write_text(f"{role} evidence\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-m", "evidence"], cwd=self.root, check=True, capture_output=True)
        self.head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=self.root, check=True, text=True, capture_output=True
        ).stdout.strip()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def manifest(self, *, head: str | None = None, roles=None) -> Path:
        roles = roles or sorted(evidence.REQUIRED_ROLES)
        path = self.root / "manifest.json"
        path.write_text(json.dumps({
            "schemaVersion": 1,
            "topic": "sample-delivery",
            "candidateHead": head or self.head,
            "files": [{"role": role, "path": f"{role}.txt"} for role in roles],
        }), encoding="utf-8")
        return path

    def test_archive_copies_and_rereads_every_required_role(self) -> None:
        plan = evidence.load_plan(self.root, self.manifest(), self.archive_root)
        receipt_path = evidence.archive(
            plan, apply=True, confirmation=evidence.CONFIRMATION
        )
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(receipt["status"], "verified")
        self.assertEqual(receipt["candidateHead"], self.head)
        self.assertEqual({row["role"] for row in receipt["files"]}, evidence.REQUIRED_ROLES)
        for row in receipt["files"]:
            archived = Path(row["archivePath"])
            self.assertTrue(archived.is_file())
            self.assertEqual(evidence.sha256(archived), row["sha256"])

    def test_plan_rejects_missing_role_and_head_drift(self) -> None:
        with self.assertRaisesRegex(evidence.ArchiveError, "missing required roles"):
            evidence.load_plan(
                self.root,
                self.manifest(roles=["summary", "identity", "review"]),
                self.archive_root,
            )
        with self.assertRaisesRegex(evidence.ArchiveError, "candidateHead"):
            evidence.load_plan(self.root, self.manifest(head="0" * 40), self.archive_root)


if __name__ == "__main__":
    unittest.main()
