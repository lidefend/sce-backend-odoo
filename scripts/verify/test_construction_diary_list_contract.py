#!/usr/bin/env python3
"""Offline checks for construction.diary.open List Contract loading mechanism."""
from __future__ import annotations

import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NEW_FILE = ROOT / "addons/smart_construction_core/data/construction_diary_list_contract.xml"
OLD_FILE = ROOT / "addons/smart_construction_core/data/construction_plan_form_productization_contract.xml"
MANIFEST = ROOT / "addons/smart_construction_core/__manifest__.py"


class DiaryListContractTests(unittest.TestCase):
    def test_new_file_is_upgrade_loadable_and_registered(self):
        root = ET.parse(NEW_FILE).getroot()
        self.assertNotIn("noupdate", root.attrib)
        rec = root.find("record[@id='business_config_contract_construction_diary_productized_list_v1']")
        self.assertIsNotNone(rec)
        fields = {f.get("name"): f for f in rec.findall("field")}
        self.assertEqual(fields["model"].text, "sc.construction.diary")
        self.assertEqual(fields["view_type"].text, "list")
        self.assertEqual(fields["action_id"].get("ref"),
                         "smart_construction_core.action_sc_construction_diary")
        self.assertEqual(fields["status"].text, "published")
        self.assertIn("construction_diary_list_contract.xml", MANIFEST.read_text(encoding="utf-8"))

    def test_record_removed_from_noupdate_file(self):
        self.assertNotIn("construction_diary_productized_list_v1",
                         OLD_FILE.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
