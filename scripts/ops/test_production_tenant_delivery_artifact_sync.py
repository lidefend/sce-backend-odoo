#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("production_tenant_delivery_artifact_sync.py")
SPEC = importlib.util.spec_from_file_location("artifact_sync", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class ArtifactTreeTest(unittest.TestCase):
    def build(self, root: Path) -> None:
        (root / "records").mkdir()
        value = root / "records" / "one.jsonl"
        value.write_text("{}\n", encoding="utf-8")
        digest = hashlib.sha256(value.read_bytes()).hexdigest()
        (root / "checksums.sha256").write_text(f"{digest}  records/one.jsonl\n", encoding="utf-8")
        (root / "manifest.json").write_text("{}\n", encoding="utf-8")
        (root / "signature").write_bytes(b"signature")

    def test_checksum_inventory_passes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); self.build(root)
            values = MODULE.validate_checksum_tree(root, extra_files={"manifest.json", "signature"})
            self.assertEqual(list(values), ["records/one.jsonl"])

    def test_unlisted_file_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); self.build(root)
            (root / "unexpected").write_text("x", encoding="utf-8")
            with self.assertRaises(MODULE.SyncError):
                MODULE.validate_checksum_tree(root, extra_files={"manifest.json", "signature"})

    def test_checksum_difference_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); self.build(root)
            (root / "records" / "one.jsonl").write_text("changed", encoding="utf-8")
            with self.assertRaises(MODULE.SyncError):
                MODULE.validate_checksum_tree(root, extra_files={"manifest.json", "signature"})

    def test_remote_reader_modes_are_private_group_readable(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("normalize_reader_modes", source)
        self.assertIn("0o750 if path.is_dir() else 0o640", source)
        self.assertIn("tenant-payload-public-key.pem", source)


if __name__ == "__main__":
    unittest.main()
