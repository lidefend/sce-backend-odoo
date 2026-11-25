from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.dev import changed_odoo_tests as selection


class ChangedOdooTestSelectionTest(unittest.TestCase):
    def test_classes_are_explicit_module_qualified_test_tags(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test_example.py"
            path.write_text(
                "class TestOne:\n"
                "    pass\n"
                "class Helper:\n"
                "    pass\n"
                "class TestTwo:\n"
                "    pass\n"
            )
            with mock.patch.object(selection, "ROOT", path.parent):
                self.assertEqual(
                    selection.classes(path, "smart_core"),
                    ["/smart_core:TestOne", "/smart_core:TestTwo"],
                )

    def test_changed_test_files_produce_one_nonzero_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            one = root / "addons/example/tests/test_one.py"
            one.parent.mkdir(parents=True)
            one.write_text("class TestOne:\n    pass\n")
            with mock.patch.object(
                selection,
                "resolve_run",
                return_value=("run", {"baseline_sha": "a" * 40}),
            ), mock.patch.object(
                selection,
                "delta_paths",
                return_value=["addons/example/tests/test_one.py"],
            ):
                self.assertEqual(
                    selection.selection(root, "example"),
                    ["/example:TestOne"],
                )

    def test_offline_unittest_file_is_not_an_odoo_test_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test_example.py"
            path.write_text(
                "import unittest\n"
                "class TestOffline(unittest.TestCase):\n"
                "    pass\n"
            )
            self.assertEqual(selection.odoo_test_classes(path), [])
            self.assertEqual(selection.classes(path, "example"), [])

    def test_missing_or_non_test_changes_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with mock.patch.object(
                selection,
                "resolve_run",
                return_value=("run", {"baseline_sha": "a" * 40}),
            ), mock.patch.object(
                selection,
                "delta_paths",
                return_value=["addons/example/models/example.py"],
            ):
                with self.assertRaisesRegex(ValueError, "no changed test files"):
                    selection.selection(root, "example")


if __name__ == "__main__":
    unittest.main()
