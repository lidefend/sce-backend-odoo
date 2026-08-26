from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "scripts/audit/generate_frontend_component_driver_takeover_inventory.py"
SPEC = importlib.util.spec_from_file_location("component_takeover", PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ComponentDriverTakeoverInventoryTest(unittest.TestCase):
    def test_catalog_is_bound_to_installed_official_version(self) -> None:
        report = MODULE.build_inventory()
        self.assertEqual(report["authority"]["lockedVersion"], "1.20.5")
        self.assertEqual(report["summary"]["officialComponents"], len(MODULE.official_components()))

    def test_all_required_drivers_are_explicitly_assessed(self) -> None:
        report = MODULE.build_inventory()
        required = {row["officialComponent"] for row in report["components"] if row["requiredForCurrentProduct"]}
        self.assertEqual(required, MODULE.REQUIRED_DRIVERS)
        self.assertTrue(all(row["status"] in {"adapter_present", "adapter_unconsumed", "bridge_only", "missing"} for row in report["components"] if row["requiredForCurrentProduct"]))

    def test_business_sources_cannot_import_tdesign_directly(self) -> None:
        report = MODULE.build_inventory()
        self.assertEqual(report["directLibraryImportBypasses"], [])

    def test_completion_rule_cannot_hide_unassessed_raw_behavior(self) -> None:
        report = MODULE.build_inventory()
        self.assertEqual(report["rawBehaviorSurfaces"], [])
        self.assertIn("unassessedRawBehaviorSurfaces=0", report["completionRule"])
        self.assertIn("adapter_unconsumed=0", report["completionRule"])

    def test_semantically_rejected_drivers_have_explicit_architecture_decisions(self) -> None:
        report = MODULE.build_inventory()
        rows = {row["officialComponent"]: row for row in report["components"]}
        for component in ("popconfirm", "switch", "time-picker"):
            self.assertFalse(rows[component]["requiredForCurrentProduct"])
            self.assertNotEqual(rows[component]["requirementDecision"], "not required by current formal product semantics")


if __name__ == "__main__":
    unittest.main()
