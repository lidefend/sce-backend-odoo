from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "scripts/audit/generate_frontend_official_design_alignment_inventory.py"
SPEC = importlib.util.spec_from_file_location("official_design_alignment", PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class OfficialDesignAlignmentInventoryTest(unittest.TestCase):
    def test_inventory_is_bound_to_installed_locked_tdesign(self) -> None:
        report = MODULE.build_inventory()
        self.assertEqual(report["authority"]["lockedVersion"], "1.20.5")
        self.assertGreater(report["summary"]["officialPublicTokenCount"], 200)

    def test_project_overrides_are_real_official_public_tokens(self) -> None:
        report = MODULE.build_inventory()
        self.assertEqual(report["themeTokens"]["unknownProjectTokenOverrides"], [])

    def test_internal_selector_detection_distinguishes_root_and_descendant(self) -> None:
        self.assertFalse(MODULE.selector_has_descendant_vendor_target(".sc-btn.t-button"))
        self.assertTrue(MODULE.selector_has_descendant_vendor_target(".sc-input .t-input"))
        self.assertTrue(MODULE.selector_has_descendant_vendor_target(".t-input"))

    def test_every_product_appearance_has_a_real_consumer(self) -> None:
        report = MODULE.build_inventory()
        orphaned = [row["appearance"] for row in report["productAppearanceVariants"] if row["status"] == "orphaned_product_variance"]
        self.assertEqual(orphaned, [])

    def test_inventory_scans_all_formal_style_carriers(self) -> None:
        report = MODULE.build_inventory()
        self.assertGreater(report["summary"]["formalStyleSourceCount"], 100)
        for gap in report["internalVendorSelectorGaps"]:
            self.assertIn("file", gap)


if __name__ == "__main__":
    unittest.main()
