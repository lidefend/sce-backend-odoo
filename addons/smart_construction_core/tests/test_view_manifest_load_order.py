# -*- coding: utf-8 -*-
from __future__ import annotations

import ast
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


class TestViewManifestLoadOrder(unittest.TestCase):
    def test_settlement_base_view_precedes_variation_inheritance(self):
        module_root = Path(__file__).resolve().parents[1]
        manifest = ast.literal_eval((module_root / "__manifest__.py").read_text(encoding="utf-8"))
        data_files = list(manifest.get("data") or [])

        self.assertLess(
            data_files.index("views/core/settlement_views.xml"),
            data_files.index("views/support/variation_change_views.xml"),
            "the settlement form external ID must exist before its variation inheritance is loaded",
        )

    def test_accounting_center_identity_precedes_accounting_children(self):
        module_root = Path(__file__).resolve().parents[1]
        manifest = ast.literal_eval((module_root / "__manifest__.py").read_text(encoding="utf-8"))
        data_files = list(manifest.get("data") or [])
        navigation_path = "views/menu_product_navigation_v2.xml"
        accounting_path = "views/menu_product_accounting_foundation.xml"
        navigation = ET.parse(module_root / navigation_path).getroot()

        self.assertIsNotNone(
            navigation.find(".//record[@id='menu_sc_accounting_center']"),
            "the navigation baseline must create the accounting center identity",
        )
        self.assertLess(
            data_files.index(navigation_path),
            data_files.index(accounting_path),
            "the accounting center identity must exist before its child menus are loaded",
        )


if __name__ == "__main__":
    unittest.main()
