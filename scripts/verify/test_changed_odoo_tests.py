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
                "from odoo.tests import TransactionCase\n"
                "class TestOne(TransactionCase):\n"
                "    pass\n"
                "class Helper:\n"
                "    pass\n"
                "class TestTwo(TransactionCase):\n"
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
            one.write_text(
                "from odoo.tests import TransactionCase\n"
                "class TestOne(TransactionCase):\n"
                "    pass\n"
            )
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

    def test_odoo_classes_are_selected_by_inheritance_not_name_prefix(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test_example.py"
            path.write_text(
                "from odoo.tests.common import BaseCase, HttpCase\n"
                "class SubmissionReadinessNoticeP1Tests(BaseCase):\n"
                "    pass\n"
                "class SubmissionReadinessNoticeSuppressionTests(HttpCase):\n"
                "    pass\n"
            )
            with mock.patch.object(selection, "ROOT", path.parent):
                self.assertEqual(
                    selection.classes(path, "smart_core"),
                    [
                        "/smart_core:SubmissionReadinessNoticeP1Tests",
                        "/smart_core:SubmissionReadinessNoticeSuppressionTests",
                    ],
                )

    def test_unknown_test_base_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test_unknown.py"
            path.write_text(
                "class TestUnknown(ProjectSpecificCase):\n"
                "    pass\n"
            )
            with self.assertRaisesRegex(ValueError, "cannot identify Odoo or unittest test base"):
                selection.odoo_test_classes(path)

    def test_existing_non_test_prefix_orm_classes_are_discovered(self):
        cases = {
            "addons/smart_construction_core/tests/test_submission_readiness_notice_p1.py":
                "SubmissionReadinessNoticeP1Tests",
            "addons/smart_core/tests/test_submission_readiness_notice_suppression.py":
                "SubmissionReadinessNoticeSuppressionTests",
        }
        for path, class_name in cases.items():
            with self.subTest(path=path):
                classes = selection.odoo_test_classes(selection.ROOT / path)
                self.assertEqual([node.name for node in classes], [class_name])

    def test_mixed_changed_files_keep_every_orm_test_class(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tests = root / "addons/example/tests"
            tests.mkdir(parents=True)
            first = tests / "test_localized_display.py"
            second = tests / "test_submission_readiness_notice_suppression.py"
            first.write_text(
                "from odoo.tests import TransactionCase\n"
                "class TestLocalizedDisplay(TransactionCase):\n"
                "    pass\n"
            )
            second.write_text(
                "from odoo.tests.common import TransactionCase\n"
                "class SubmissionReadinessNoticeSuppressionTests(TransactionCase):\n"
                "    pass\n"
            )
            with mock.patch.object(
                selection,
                "resolve_run",
                return_value=("run", {"baseline_sha": "a" * 40}),
            ), mock.patch.object(
                selection,
                "delta_paths",
                return_value=[
                    "addons/example/tests/test_localized_display.py",
                    "addons/example/tests/test_submission_readiness_notice_suppression.py",
                ],
            ):
                self.assertEqual(
                    selection.selection(root, "example"),
                    [
                        "/example:SubmissionReadinessNoticeSuppressionTests",
                        "/example:TestLocalizedDisplay",
                    ],
                )

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
