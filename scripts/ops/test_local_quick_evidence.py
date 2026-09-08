#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("local_quick_evidence.py")
SPEC = importlib.util.spec_from_file_location("local_quick_evidence", MODULE_PATH)
assert SPEC and SPEC.loader
evidence = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(evidence)


class LocalQuickEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        (self.root / "tracked.txt").write_text("baseline\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.root), "add", "tracked.txt"], check=True)
        subprocess.run(
            [
                "git",
                "-C",
                str(self.root),
                "-c",
                "user.name=Codex Test",
                "-c",
                "user.email=codex-test@example.invalid",
                "commit",
                "-q",
                "-m",
                "fixture",
            ],
            check=True,
        )
        self.head = subprocess.run(
            ["git", "-C", str(self.root), "rev-parse", "HEAD"],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
        ).stdout.strip()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_recorded_exact_clean_head_verifies(self) -> None:
        path = evidence.record(self.root, self.head)
        self.assertEqual(evidence.verify(self.root, self.head), path)
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["head"], self.head)
        self.assertEqual(payload["suite"], "ci.local.quick")

    def test_missing_or_tampered_receipt_is_rejected(self) -> None:
        with self.assertRaisesRegex(evidence.EvidenceError, "missing"):
            evidence.verify(self.root, self.head)
        path = evidence.record(self.root, self.head)
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["tree"] = "b" * 40
        path.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaisesRegex(evidence.EvidenceError, "does not match"):
            evidence.verify(self.root, self.head)

    def test_dirty_worktree_cannot_record_or_reuse(self) -> None:
        path = evidence.record(self.root, self.head)
        (self.root / "untracked.txt").write_text("dirty\n", encoding="utf-8")
        with self.assertRaisesRegex(evidence.EvidenceError, "must be clean"):
            evidence.record(self.root, self.head)
        with self.assertRaisesRegex(evidence.EvidenceError, "must be clean"):
            evidence.verify(self.root, self.head)
        self.assertTrue(path.exists())

    def test_different_head_cannot_reuse_receipt(self) -> None:
        evidence.record(self.root, self.head)
        with self.assertRaisesRegex(evidence.EvidenceError, "HEAD changed"):
            evidence.verify(self.root, "b" * 40)


if __name__ == "__main__":
    unittest.main()
