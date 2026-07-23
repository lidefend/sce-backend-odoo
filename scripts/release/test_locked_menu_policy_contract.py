#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "addons/smart_construction_core/services/locked_menu_policy_contract.py"
SPEC = importlib.util.spec_from_file_location("locked_menu_policy_contract", MODULE_PATH)
assert SPEC and SPEC.loader
CONTRACT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTRACT)


class LockedMenuPolicyContractTests(unittest.TestCase):
    def setUp(self):
        self.baseline = ROOT / "scripts/verify/baselines/formal_business_product_menu_policy_v1.json"
        self.checksum = ROOT / "scripts/verify/baselines/formal_business_product_menu_policy_v1.json.sha256"
        self.archive_views = (
            ROOT
            / "addons/smart_construction_core/views/core/fund_legacy_readonly_archive_views.xml"
        )

    def test_action_only_targets_use_stable_external_ids(self):
        self.assertEqual(
            CONTRACT.FORMAL_ACTION_ONLY_MENU_TARGETS[
                "smart_construction_core.menu_sc_material_rental_in_acceptance"
            ],
            "smart_construction_core.action_sc_material_rental_in_acceptance",
        )
        for menu_xmlid, action_xmlid in CONTRACT.FORMAL_ACTION_ONLY_MENU_TARGETS.items():
            self.assertTrue(menu_xmlid.startswith("smart_construction_core.menu_"))
            self.assertTrue(action_xmlid.startswith("smart_construction_core.action_"))

    def test_formal_initialization_action_specs_are_stable_and_complete(self):
        for action_xmlid, spec in CONTRACT.FORMAL_INITIALIZATION_ACTION_SPECS.items():
            self.assertIn(action_xmlid, CONTRACT.FORMAL_ACTION_ONLY_MENU_TARGETS.values())
            self.assertTrue(spec["name"])
            self.assertTrue(spec["res_model"])
            self.assertIn("domain", spec)
            self.assertIn("context", spec)

    def test_fund_archives_are_installed_xml_contracts_not_dynamic_fallbacks(self):
        xml = self.archive_views.read_text(encoding="utf-8")
        for action_xmlid in (
            "action_sc_fuel_card_registration_formal",
            "action_sc_fuel_card_recharge_formal",
        ):
            self.assertIn(f'id="{action_xmlid}"', xml)
            self.assertNotIn(
                f"smart_construction_core.{action_xmlid}",
                CONTRACT.FORMAL_INITIALIZATION_ACTION_SPECS,
            )
        self.assertIn("online_old_legacy_direct:direct_acceptance", xml)
        self.assertIn("direct_acceptance:油卡登记", xml)
        self.assertIn("direct_acceptance:充值登记", xml)
        self.assertIn('create="false" edit="false" delete="false" duplicate="false"', xml)

    def test_unresolved_tax_certificate_target_requires_business_decision(self):
        menu_xmlid = "smart_construction_core.menu_sc_tax_certificate_registration_user"
        action_xmlid = "smart_construction_core.action_sc_tax_certificate_registration_user"
        self.assertEqual(CONTRACT.FORMAL_ACTION_ONLY_MENU_TARGETS[menu_xmlid], action_xmlid)
        self.assertEqual(CONTRACT.FORMAL_BUSINESS_DECISION_REQUIRED_TARGETS[menu_xmlid], action_xmlid)
        self.assertNotIn(action_xmlid, CONTRACT.FORMAL_INITIALIZATION_ACTION_SPECS)
        self.assertNotEqual(action_xmlid, "smart_construction_core.action_sc_invoice_registration")

    def _write_contract(self, root: Path, payload) -> tuple[Path, Path]:
        baseline = root / CONTRACT.BASELINE_FILE
        checksum = root / CONTRACT.BASELINE_CHECKSUM_FILE
        raw = payload if isinstance(payload, bytes) else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        baseline.write_bytes(raw)
        checksum.write_text(f"{hashlib.sha256(raw).hexdigest()}  {CONTRACT.BASELINE_FILE}\n", encoding="utf-8")
        return baseline, checksum

    def test_versioned_locked_baseline_loads_and_contains_expected_contract(self):
        contract = CONTRACT.load_locked_menu_policy_contract(self.baseline, self.checksum)
        self.assertEqual(
            contract["sha256"],
            "5bc14fa2496e244ab14efa722f38f199659f5a4f506f7958e8d595a7b24dcee2",
        )
        for product_key in CONTRACT.REQUIRED_PRODUCT_KEYS:
            self.assertEqual(len(CONTRACT.baseline_rows(contract, product_key)), 97)

    def test_missing_baseline_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaisesRegex(CONTRACT.LockedMenuPolicyContractError, "LOCKED_MENU_BASELINE_MISSING"):
                CONTRACT.load_locked_menu_policy_contract(root / "missing.json", root / "missing.sha256")

    def test_invalid_json_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            baseline, checksum = self._write_contract(Path(temp), b"{not-json")
            with self.assertRaisesRegex(CONTRACT.LockedMenuPolicyContractError, "LOCKED_MENU_BASELINE_INVALID"):
                CONTRACT.load_locked_menu_policy_contract(baseline, checksum)

    def test_checksum_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            baseline = root / CONTRACT.BASELINE_FILE
            checksum = root / CONTRACT.BASELINE_CHECKSUM_FILE
            baseline.write_text("{}", encoding="utf-8")
            checksum.write_text("0" * 64, encoding="utf-8")
            with self.assertRaisesRegex(CONTRACT.LockedMenuPolicyContractError, "sha256 mismatch"):
                CONTRACT.load_locked_menu_policy_contract(baseline, checksum)

    def test_product_key_mismatch_fails_closed(self):
        payload = json.loads(self.baseline.read_text(encoding="utf-8"))
        payload["products"] = [row for row in payload["products"] if row["product_key"] != "construction.preview"]
        with tempfile.TemporaryDirectory() as temp:
            baseline, checksum = self._write_contract(Path(temp), payload)
            with self.assertRaisesRegex(CONTRACT.LockedMenuPolicyContractError, "LOCKED_MENU_BASELINE_PRODUCT_MISMATCH"):
                CONTRACT.load_locked_menu_policy_contract(baseline, checksum)

    def test_duplicate_stable_identity_fails_normalization(self):
        payload = json.loads(self.baseline.read_text(encoding="utf-8"))
        product = payload["products"][0]
        product["menu_groups"][0]["menus"].append(copy.deepcopy(product["menu_groups"][0]["menus"][0]))
        with tempfile.TemporaryDirectory() as temp:
            baseline, checksum = self._write_contract(Path(temp), payload)
            with self.assertRaisesRegex(
                CONTRACT.LockedMenuPolicyContractError,
                "LOCKED_MENU_BASELINE_NORMALIZATION_MISMATCH",
            ):
                CONTRACT.load_locked_menu_policy_contract(baseline, checksum)

    def test_policy_comparison_uses_stable_identity_not_database_ids(self):
        contract = CONTRACT.load_locked_menu_policy_contract(self.baseline, self.checksum)
        groups = copy.deepcopy(contract["products"]["construction.standard"]["menu_groups"])
        for index, menu in enumerate((menu for group in groups for menu in group["menus"]), start=10000):
            menu["menu_id"] = index
            menu["action_id"] = index + 10000
        result = CONTRACT.assert_policy_matches_locked_contract(contract, "construction.standard", groups)
        self.assertEqual(result["menu_count"], 97)

    def test_snapshot_must_match_locked_baseline_in_order(self):
        contract = CONTRACT.load_locked_menu_policy_contract(self.baseline, self.checksum)
        rows = CONTRACT.baseline_rows(contract, "construction.standard")
        pages = [
            {"label": label, "menu_xmlid": menu_xmlid, "enabled": True, "release_state": "released"}
            for _group, label, menu_xmlid in rows
        ]
        self.assertEqual(
            CONTRACT.assert_snapshot_matches_locked_contract(contract, "construction.standard", pages)["menu_count"],
            97,
        )
        pages.reverse()
        with self.assertRaisesRegex(CONTRACT.LockedMenuPolicyContractError, "LOCKED_MENU_SNAPSHOT_MISMATCH"):
            CONTRACT.assert_snapshot_matches_locked_contract(contract, "construction.standard", pages)

    def test_standard_and_preview_contracts_are_independent_objects(self):
        contract = CONTRACT.load_locked_menu_policy_contract(self.baseline, self.checksum)
        standard = contract["products"]["construction.standard"]
        preview = contract["products"]["construction.preview"]
        self.assertIsNot(standard, preview)
        self.assertEqual(len(CONTRACT.baseline_rows(contract, "construction.standard")), 97)
        self.assertEqual(len(CONTRACT.baseline_rows(contract, "construction.preview")), 97)
        self.assertNotEqual(standard["product_key"], preview["product_key"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
