#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import backend_model_field_declaration_guard as guard


ROOT = Path(__file__).resolve().parents[2]


def write(root: Path, relative: str, source: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


class BackendModelFieldDeclarationGuardTest(unittest.TestCase):
    def test_repository_has_no_duplicate_field_declarations(self) -> None:
        report = guard.check(ROOT)
        self.assertEqual([], report["failures"])
        self.assertEqual(0, report["duplicate_count"])
        self.assertEqual(0, report["same_class_duplicate_count"])
        self.assertGreater(report["declaration_count"], 0)

    def test_duplicate_across_extension_classes_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            write(
                root,
                "addons/demo_module/models/partner_a.py",
                'from odoo import fields, models\n\n'
                'class PartnerA(models.Model):\n'
                '    _inherit = "res.partner"\n'
                '    x_code = fields.Char(help="a")\n',
            )
            write(
                root,
                "addons/demo_module/models/partner_b.py",
                'from odoo import fields, models\n\n'
                'class PartnerB(models.Model):\n'
                '    _inherit = "res.partner"\n'
                '    x_code = fields.Char(index=True)\n',
            )
            report = guard.check(root)
            self.assertEqual("failed", report["status"])
            self.assertIn("res.partner.x_code", report["duplicates"])
            self.assertTrue(any("res.partner.x_code" in failure for failure in report["failures"]))

    def test_duplicate_between_owning_and_extension_class_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            write(
                root,
                "addons/demo_module/models/record.py",
                'from odoo import fields, models\n\n'
                'class DemoRecord(models.Model):\n'
                '    _name = "demo.record"\n'
                '    amount = fields.Monetary(compute="_compute_amount", store=True)\n',
            )
            write(
                root,
                "addons/demo_module/models/record_extension.py",
                'from odoo import fields, models\n\n'
                'class DemoRecordExtension(models.Model):\n'
                '    _inherit = "demo.record"\n'
                '    amount = fields.Monetary(string="Platform amount")\n',
            )
            report = guard.check(root)
            self.assertEqual("failed", report["status"])
            self.assertIn("demo.record.amount", report["duplicates"])
            sites = report["duplicates"]["demo.record.amount"]
            self.assertEqual({"owning class", "extension class"}, {site["role"] for site in sites})

    def test_same_class_duplicate_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            write(
                root,
                "addons/demo_module/models/record.py",
                'from odoo import fields, models\n\n'
                'class DemoRecord(models.Model):\n'
                '    _name = "demo.record"\n'
                '    amount = fields.Monetary()\n'
                '    amount = fields.Float()\n',
            )
            report = guard.check(root)
            self.assertEqual("failed", report["status"])
            self.assertEqual(1, report["same_class_duplicate_count"])
            self.assertEqual("demo.record", report["same_class_duplicates"][0]["model"])
            self.assertEqual("amount", report["same_class_duplicates"][0]["field"])

    def test_model_name_constant_is_resolved(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            write(
                root,
                "addons/demo_module/models/record.py",
                'from odoo import fields, models\n\n'
                'DEMO_RECORD = "demo.record"\n\n'
                'class DemoRecord(models.Model):\n'
                '    _name = DEMO_RECORD\n'
                '    amount = fields.Monetary()\n\n'
                'class DemoRecordExtension(models.Model):\n'
                '    _inherit = DEMO_RECORD\n'
                '    amount = fields.Monetary()\n',
            )
            report = guard.check(root)
            self.assertEqual("failed", report["status"])
            self.assertIn("demo.record.amount", report["duplicates"])

    def test_clean_fixture_passes(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            write(
                root,
                "addons/demo_module/models/record.py",
                'from odoo import fields, models\n\n'
                'class DemoRecord(models.Model):\n'
                '    _name = "demo.record"\n'
                '    amount = fields.Monetary(help="owning declaration")\n\n'
                'class DemoRecordExtension(models.Model):\n'
                '    _inherit = "demo.record"\n'
                '    note = fields.Char()\n',
            )
            report = guard.check(root)
            self.assertEqual([], report["failures"])
            self.assertEqual("passed", report["status"])
            self.assertEqual(0, report["duplicate_count"])


if __name__ == "__main__":
    unittest.main()
