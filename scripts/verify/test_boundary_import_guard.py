#!/usr/bin/env python3
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import boundary_import_guard


class BoundaryImportGuardTest(unittest.TestCase):
    def test_finds_manifest_in_registered_demo_module_root(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = root / "demo_addons" / "smart_demo" / "__manifest__.py"
            manifest.parent.mkdir(parents=True)
            manifest.write_text("{'depends': ['smart_core']}\n", encoding="utf-8")

            paths = boundary_import_guard._find_manifest_paths(
                "smart_demo",
                ["addons", "demo_addons"],
                root=root,
            )

            self.assertEqual(paths, [manifest])
            self.assertEqual(boundary_import_guard._parse_manifest_depends(manifest), ["smart_core"])

    def test_reports_all_duplicate_manifests_for_fail_closed_caller(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            expected = []
            for module_root in ("addons", "demo_addons"):
                manifest = root / module_root / "duplicate_module" / "__manifest__.py"
                manifest.parent.mkdir(parents=True)
                manifest.write_text("{'depends': ['base']}\n", encoding="utf-8")
                expected.append(manifest)

            paths = boundary_import_guard._find_manifest_paths(
                "duplicate_module",
                ["addons", "demo_addons"],
                root=root,
            )

            self.assertEqual(paths, expected)


if __name__ == "__main__":
    unittest.main()
