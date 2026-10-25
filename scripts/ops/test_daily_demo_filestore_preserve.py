import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.ops.daily_demo_filestore_preserve import checked_path, digest, move_preserved, restore_preserved


class PreservationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / "live"
        self.saved = Path(self.temp.name) / "saved"
        self.source.mkdir()
        self.rows = []
        for body in (b"synthetic-one", b"synthetic-two"):
            sha = hashlib.sha1(body).hexdigest()
            row = {"path": sha[:2] + "/" + sha, "size": len(body), "sha1": sha}
            file = self.source / row["path"]
            file.parent.mkdir(exist_ok=True)
            file.write_bytes(body)
            self.rows.append(row)

    def test_move_and_exact_restore(self):
        move_preserved(self.source, self.saved, self.rows)
        for row in self.rows:
            self.assertFalse((self.source / row["path"]).exists())
            checked_path(self.saved, row)
        restore_preserved(self.source, self.saved, self.rows)
        for row in self.rows:
            checked_path(self.source, row)

    def test_changed_body_prevents_all_moves(self):
        (self.source / self.rows[1]["path"]).write_bytes(b"changed")
        with self.assertRaisesRegex(RuntimeError, "drift"):
            move_preserved(self.source, self.saved, self.rows)
        checked_path(self.source, self.rows[0])
        self.assertFalse(self.saved.exists())

    def test_partial_move_failure_restores_earlier_files(self):
        import os
        rename = os.rename
        count = 0
        def fail_second(src, dst):
            nonlocal count
            count += 1
            if count == 2:
                raise OSError("simulated storage failure")
            return rename(src, dst)
        with patch("scripts.ops.daily_demo_filestore_preserve.os.rename", side_effect=fail_second):
            with self.assertRaisesRegex(OSError, "simulated"):
                move_preserved(self.source, self.saved, self.rows)
        for row in self.rows:
            checked_path(self.source, row)

    def test_restore_collision_preserves_saved_bodies(self):
        move_preserved(self.source, self.saved, self.rows)
        (self.source / self.rows[0]["path"]).write_bytes(b"new live data")
        with self.assertRaisesRegex(RuntimeError, "overwrite"):
            restore_preserved(self.source, self.saved, self.rows)
        for row in self.rows:
            checked_path(self.saved, row)

    def test_symlink_refused(self):
        target = self.source / self.rows[0]["path"]
        body = target.read_bytes()
        target.unlink()
        outside = Path(self.temp.name) / "outside"
        outside.write_bytes(body)
        target.symlink_to(outside)
        with self.assertRaisesRegex(RuntimeError, "Symlink"):
            move_preserved(self.source, self.saved, self.rows)

    def test_traversal_refused(self):
        with self.assertRaisesRegex(RuntimeError, "exact store"):
            checked_path(self.source, {"path": "../outside"})

    def test_existing_destination_refused(self):
        self.saved.mkdir()
        with self.assertRaisesRegex(RuntimeError, "already exists"):
            move_preserved(self.source, self.saved, self.rows)

    def test_inventory_digest_detects_changed_content(self):
        changed = [dict(r) for r in self.rows]
        changed[0]["size"] += 1
        self.assertNotEqual(digest(self.rows), digest(changed))
