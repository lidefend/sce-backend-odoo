#!/usr/bin/env python3
"""Lock the field-ownership detector against substring false positives.

The audited surfaces use generic field names (`name`, `state`, `note`, ...).
A bare substring test treats an Odoo manifest's own ``name`` key as a leak, so
every clean custom module would fail. These cases prove that the detector only
fires on a real field declaration or view field reference, and that a clean
baseline stays clean before an injection is judged.
"""

from pathlib import Path
import sys
import tempfile
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parent))

from user_formal_field_module_boundary_audit import (  # noqa: E402
    BOUNDARY_CASES,
    CUSTOM_ADDON,
    _scan_static,
)


ROOT = Path(__file__).resolve().parents[2]
CORE_ADDON_ROOT = ROOT / "addons"

MANIFEST = """# -*- coding: utf-8 -*-
{
    "name": "Smart Construction Custom Compatibility",
    "summary": "Compatibility carrier for databases migrated to the P2 customer modules",
    "version": "17.0.2.0.0",
    "depends": ["smart_construction_bundle"],
    "data": [],
    "installable": True,
}
"""

CASE = {
    "name": "报价单",
    "model": "sc.material.rfq",
    "owner": "core",
    "fields": ["state", "name"],
}


class BoundaryDetectorTest(unittest.TestCase):
    def _addons(self, *, manifest=True, python=None, xml=None):
        temporary = tempfile.TemporaryDirectory()
        addon_root = Path(temporary.name) / "addons"
        custom = addon_root / CUSTOM_ADDON
        custom.mkdir(parents=True, exist_ok=True)
        if manifest:
            (custom / "__manifest__.py").write_text(MANIFEST, encoding="utf-8")
        if python is not None:
            (custom / "models").mkdir(exist_ok=True)
            (custom / "models" / "custom.py").write_text(python, encoding="utf-8")
        if xml is not None:
            (custom / "views").mkdir(exist_ok=True)
            (custom / "views" / "custom_views.xml").write_text(xml, encoding="utf-8")
        self.addCleanup(temporary.cleanup)
        return addon_root

    def test_manifest_key_is_not_a_field_leak(self):
        core_root = self._addons(manifest=False)
        core = core_root / "smart_construction_core"
        (core / "models").mkdir(parents=True, exist_ok=True)
        (core / "models" / "rfq.py").write_text(
            "class Rfq(models.Model):\n"
            "    name = fields.Char(string=\"单据编号\")\n"
            "    state = fields.Selection([(\"draft\", \"草稿\")])\n",
            encoding="utf-8",
        )
        custom_root = self._addons()
        self.assertEqual(_scan_static(core_root, custom_root, cases=[CASE]), [])

    def test_real_baseline_with_live_custom_manifest_passes(self):
        """The production configuration that produced the false positive."""
        custom_root = self._addons()
        failures = _scan_static(
            CORE_ADDON_ROOT,
            custom_root,
            cases=BOUNDARY_CASES,
        )
        self.assertEqual(failures, [])

    def test_python_field_declaration_leak_is_detected(self):
        core_root = self._addons(manifest=False)
        core = core_root / "smart_construction_core"
        core.mkdir(parents=True, exist_ok=True)
        (core / "models").mkdir(parents=True, exist_ok=True)
        (core / "models" / "rfq.py").write_text(
            "class Rfq(models.Model):\n    name = fields.Char()\n    state = fields.Selection([])\n",
            encoding="utf-8",
        )
        custom_root = self._addons(python="class Rfq(models.Model):\n    name = fields.Char()\n")
        failures = _scan_static(core_root, custom_root, cases=[CASE])
        leaks = [row for row in failures if row["type"] == "custom_business_field_leak"]
        self.assertEqual([row["field"] for row in leaks], ["name"])

    def test_view_field_reference_leak_is_detected(self):
        core_root = self._addons(manifest=False)
        core = core_root / "smart_construction_core"
        core.mkdir(parents=True, exist_ok=True)
        (core / "models").mkdir(parents=True, exist_ok=True)
        (core / "models" / "rfq.py").write_text(
            "class Rfq(models.Model):\n    name = fields.Char()\n    state = fields.Selection([])\n",
            encoding="utf-8",
        )
        custom_root = self._addons(
            xml='<odoo><record id="v" model="ir.ui.view"><field name="arch" type="xml">'
            '<tree><field name="name" string="单据编号"/></tree></field></record></odoo>\n'
        )
        failures = _scan_static(core_root, custom_root, cases=[CASE])
        self.assertIn("custom_business_field_leak", {row["type"] for row in failures})

    def test_missing_core_owner_is_reported_when_field_absent(self):
        core_root = self._addons(manifest=False)
        core = core_root / "smart_construction_core"
        core.mkdir(parents=True, exist_ok=True)
        (core / "models").mkdir(parents=True, exist_ok=True)
        (core / "models" / "rfq.py").write_text(
            "class Rfq(models.Model):\n    name = fields.Char()\n", encoding="utf-8"
        )
        custom_root = self._addons()
        failures = _scan_static(core_root, custom_root, cases=[CASE])
        self.assertIn("missing_core_owner", {row["type"] for row in failures})
        self.assertEqual(
            {row["field"] for row in failures if row["type"] == "missing_core_owner"},
            {"state"},
        )


if __name__ == "__main__":
    unittest.main()
