#!/usr/bin/env python3
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ci_artifact_host_write_guard import verify_host_write


class CiArtifactHostWriteGuardTests(unittest.TestCase):
    def test_atomic_host_write_succeeds_and_leaves_no_probe(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            verify_host_write(root)
            self.assertTrue((root / "backend").is_dir())
            self.assertEqual(list((root / "backend").iterdir()), [])

    def test_non_directory_backend_path_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "backend").write_text("blocked", encoding="utf-8")
            with self.assertRaises(OSError):
                verify_host_write(root)


if __name__ == "__main__":
    unittest.main()
