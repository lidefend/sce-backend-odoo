#!/usr/bin/env python3
from __future__ import annotations

import copy
import importlib.util
import sys
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator


SCRIPT = Path(__file__).with_name("menu_governance_inventory.py")
SPEC = importlib.util.spec_from_file_location("menu_governance_inventory", SCRIPT)
assert SPEC and SPEC.loader
inventory = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = inventory
SPEC.loader.exec_module(inventory)


def minimal_report() -> dict:
    return {
        "schema_version": inventory.SCHEMA_VERSION,
        "scope": {"runtime_sampling": "not_run_fixture"},
        "coverage": {"static_manifest_menu_assets": {"covered": 1, "expected": 1}},
        "findings": {
            "duplicate_menuitem_xmlids": [],
            "missing_local_actions": [],
            "missing_local_parents": [],
            "depth_graph_errors": [],
            "technical_name_risks": [],
            "over_depth_risks": [],
        },
        "assets": [{
            "menu_xmlid": "smart_construction_core.menu_fixture",
            "decision": "investigate",
            "runtime_visible": None,
            "route_reachable": None,
        }],
    }


class MenuGovernanceInventoryTest(unittest.TestCase):
    def test_utf8_json_roundtrip(self) -> None:
        report = minimal_report()
        report["assets"][0]["current_name"] = "项目台账"
        decoded = inventory.json.loads(inventory._json_bytes(report).decode("utf-8"))
        self.assertEqual(decoded["assets"][0]["current_name"], "项目台账")

    def test_duplicate_effective_xmlid_fails_closed(self) -> None:
        report = minimal_report()
        report["assets"].append(copy.deepcopy(report["assets"][0]))
        report["coverage"]["static_manifest_menu_assets"] = {"covered": 2, "expected": 2}
        with self.assertRaisesRegex(inventory.InventoryError, "duplicate effective"):
            inventory.validate_inventory(report)

    def test_extra_or_missing_asset_fails_closed(self) -> None:
        report = minimal_report()
        report["coverage"]["static_manifest_menu_assets"]["expected"] = 2
        with self.assertRaisesRegex(inventory.InventoryError, "extra or missing"):
            inventory.validate_inventory(report)

    def test_broken_action_fails_release_candidate(self) -> None:
        report = minimal_report()
        report["findings"]["missing_local_actions"] = ["smart_construction_core.menu_fixture"]
        with self.assertRaisesRegex(inventory.InventoryError, "missing_local_actions"):
            inventory.assert_release_candidate(report)

    def test_duplicate_source_xmlid_fails_release_candidate(self) -> None:
        report = minimal_report()
        report["findings"]["duplicate_menuitem_xmlids"] = ["smart_construction_core.menu_fixture"]
        with self.assertRaisesRegex(inventory.InventoryError, "duplicate_menuitem_xmlids"):
            inventory.assert_release_candidate(report)

    def test_fourth_level_fails_release_candidate(self) -> None:
        report = minimal_report()
        report["findings"]["over_depth_risks"] = ["smart_construction_core.menu_fixture"]
        with self.assertRaisesRegex(inventory.InventoryError, "over_depth_risks"):
            inventory.assert_release_candidate(report)

    def test_technical_name_fails_release_candidate(self) -> None:
        report = minimal_report()
        report["findings"]["technical_name_risks"] = ["smart_construction_core.menu_fixture"]
        with self.assertRaisesRegex(inventory.InventoryError, "technical_name_risks"):
            inventory.assert_release_candidate(report)

    def test_runtime_claim_without_sampling_fails_closed(self) -> None:
        report = minimal_report()
        report["assets"][0]["runtime_visible"] = True
        with self.assertRaisesRegex(inventory.InventoryError, "runtime claim"):
            inventory.validate_inventory(report)

    def test_real_inventory_is_deterministic_and_complete(self) -> None:
        report = inventory.collect()
        inventory.validate_inventory(report)
        self.assertEqual(report["source"]["commit_sha"], inventory._scope()["audited_commit_sha"])
        self.assertEqual(report["statistics"]["menuitem_declaration_count"], 304)
        self.assertEqual(report["statistics"]["unique_menuitem_xmlid_count"], 304)
        self.assertEqual(report["statistics"]["missing_local_action_count"], 0)
        self.assertEqual(report["statistics"]["missing_local_parent_count"], 0)
        self.assertEqual(
            report["coverage"]["static_manifest_menu_assets"]["covered"],
            len(report["assets"]),
        )

    def test_real_inventory_matches_json_schema(self) -> None:
        schema = inventory.json.loads(
            (inventory.OUT_DIR / "menu_capability_inventory.schema.json").read_text(encoding="utf-8")
        )
        Draft202012Validator.check_schema(schema)
        errors = sorted(Draft202012Validator(schema).iter_errors(inventory.collect()), key=lambda item: list(item.path))
        self.assertEqual([], [error.message for error in errors])

    def test_m4_frozen_set_is_exact_and_fail_closed(self) -> None:
        report = inventory.collect()
        m4 = inventory.build_m4_governance(report)
        self.assertEqual(6, len(m4["decisions"]))
        self.assertEqual("BLOCKED_ON_RUNTIME_EVIDENCE", m4["status"])
        self.assertFalse(m4["scope"]["runtime_sampling_performed"])
        self.assertFalse(m4["scope"]["menu_xml_modified"])
        self.assertTrue(all(item["decision"] == "investigate" for item in m4["decisions"]))

    def test_m4_extra_or_missing_decision_fails_closed(self) -> None:
        report = inventory.collect()
        m4 = inventory.build_m4_governance(report)
        m4["decisions"].pop()
        with self.assertRaisesRegex(inventory.InventoryError, "extra or missing"):
            inventory.validate_m4_governance(m4, report)

    def test_m4_authority_drift_fails_closed(self) -> None:
        report = inventory.collect()
        m4 = inventory.build_m4_governance(report)
        m4["decisions"][0]["authority"]["effective_source"] = "wrong.xml"
        with self.assertRaisesRegex(inventory.InventoryError, "authority mismatch"):
            inventory.validate_m4_governance(m4, report)

    def test_m4_unproved_runtime_claim_fails_closed(self) -> None:
        report = inventory.collect()
        m4 = inventory.build_m4_governance(report)
        m4["decisions"][0]["capability_route_mapping"]["route_reachable"] = True
        with self.assertRaisesRegex(inventory.InventoryError, "unproved runtime claim"):
            inventory.validate_m4_governance(m4, report)

    def test_m4_compatibility_weakening_fails_closed(self) -> None:
        report = inventory.collect()
        m4 = inventory.build_m4_governance(report)
        m4["decisions"][0]["compatibility_invariants"]["preserve_action_xmlid"] = False
        with self.assertRaisesRegex(inventory.InventoryError, "invariant weakened"):
            inventory.validate_m4_governance(m4, report)

    def test_m4_matches_json_schema(self) -> None:
        report = inventory.collect()
        m4 = inventory.build_m4_governance(report)
        schema = inventory.json.loads(
            (inventory.OUT_DIR / "menu_m4_governance.schema.json").read_text(encoding="utf-8")
        )
        Draft202012Validator.check_schema(schema)
        errors = sorted(Draft202012Validator(schema).iter_errors(m4), key=lambda item: list(item.path))
        self.assertEqual([], [error.message for error in errors])


if __name__ == "__main__":
    unittest.main()
