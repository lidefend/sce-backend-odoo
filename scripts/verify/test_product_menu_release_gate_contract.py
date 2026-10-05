#!/usr/bin/env python3
"""Unit tests for the same-caliber release-gate contract projection.

These lock the declaration consumption (the locked baseline owns the released
caliber, the product policy owns any declared ``preview`` widening) and the
fail-closed product-scope declaration. Passing assertions here is necessary but
not sufficient: runtime page behavior is proved only by the governed runtime
guard, never by selector strings or pixel values.
"""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "locked_menu_policy_contract",
    ROOT / "addons" / "smart_construction_core" / "services" / "locked_menu_policy_contract.py",
)
assert SPEC and SPEC.loader
contract = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(contract)

PRODUCT = "construction.standard"


def _groups(menus):
    return [{"group_label": "项目中心", "group_key": "construction.项目中心", "menus": list(menus)}]


def _menu(label, xmlid, state="released", enabled=True):
    return {"page_label": label, "menu_xmlid": xmlid, "release_state": state, "enabled": enabled}


def _page(label, xmlid, state="released", enabled=True):
    return {"label": label, "menu_xmlid": xmlid, "release_state": state, "enabled": enabled}


def _baseline(menus):
    return {"products": {PRODUCT: {"product_key": PRODUCT, "menu_groups": _groups(menus)}}}


class DeclaredProductScopeTests(unittest.TestCase):
    def test_empty_declaration_uses_full_published_scope(self):
        self.assertEqual(contract.resolve_declared_product_keys(None), contract.REQUIRED_PRODUCT_KEYS)
        self.assertEqual(contract.resolve_declared_product_keys("   "), contract.REQUIRED_PRODUCT_KEYS)

    def test_explicit_declaration_is_honored(self):
        self.assertEqual(contract.resolve_declared_product_keys("construction.standard"), ("construction.standard",))
        self.assertEqual(
            contract.resolve_declared_product_keys(" construction.preview , construction.standard "),
            ("construction.preview", "construction.standard"),
        )

    def test_unknown_product_fails_closed(self):
        with self.assertRaises(contract.LockedMenuPolicyContractError) as ctx:
            contract.resolve_declared_product_keys("construction.standard,construction.bogus")
        self.assertEqual(ctx.exception.code, "PRODUCT_MENU_CATALOG_PRODUCT_KEYS_INVALID")


class SameCaliberSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.baseline = _baseline([_menu("项目台账", "smart_construction_core.menu_sc_project_project")])

    def test_declared_preview_widening_is_accepted(self):
        policy_groups = _groups(
            [
                _menu("项目台账", "smart_construction_core.menu_sc_project_project"),
                _menu("预览入口", "smart_construction_core.menu_sc_preview_only", state="preview"),
            ]
        )
        pages = [
            _page("项目台账", "smart_construction_core.menu_sc_project_project"),
            _page("预览入口", "smart_construction_core.menu_sc_preview_only", state="preview"),
        ]
        result = contract.assert_snapshot_matches_policy_release_states(self.baseline, PRODUCT, pages, policy_groups)
        self.assertEqual(result["released_count"], 1)
        self.assertEqual(result["preview_count"], 1)
        self.assertEqual(result["effective_count"], 2)
        self.assertEqual(result["locked_released_count"], 1)
        self.assertEqual(result["declared_preview_count"], 1)
        self.assertTrue(result["exact_match"])

    def test_released_drift_is_rejected(self):
        policy_groups = _groups([_menu("项目台账", "smart_construction_core.menu_sc_project_project")])
        pages = [
            _page("项目台账", "smart_construction_core.menu_sc_project_project"),
            _page("旧全量入口", "smart_construction_core.menu_sc_legacy_full"),
        ]
        with self.assertRaises(contract.LockedMenuPolicyContractError) as ctx:
            contract.assert_snapshot_matches_policy_release_states(self.baseline, PRODUCT, pages, policy_groups)
        self.assertEqual(ctx.exception.code, "LOCKED_MENU_SNAPSHOT_MISMATCH")

    def test_undeclared_preview_is_rejected(self):
        policy_groups = _groups([_menu("项目台账", "smart_construction_core.menu_sc_project_project")])
        pages = [
            _page("项目台账", "smart_construction_core.menu_sc_project_project"),
            _page("未声明预览", "smart_construction_core.menu_sc_undeclared", state="preview"),
        ]
        with self.assertRaises(contract.LockedMenuPolicyContractError) as ctx:
            contract.assert_snapshot_matches_policy_release_states(self.baseline, PRODUCT, pages, policy_groups)
        self.assertEqual(ctx.exception.code, "LOCKED_MENU_SNAPSHOT_PREVIEW_MISMATCH")

    def test_disabled_page_is_rejected(self):
        policy_groups = _groups([_menu("项目台账", "smart_construction_core.menu_sc_project_project")])
        pages = [
            _page("项目台账", "smart_construction_core.menu_sc_project_project"),
            _page("隐藏入口", "smart_construction_core.menu_sc_hidden", enabled=False),
        ]
        with self.assertRaises(contract.LockedMenuPolicyContractError) as ctx:
            contract.assert_snapshot_matches_policy_release_states(self.baseline, PRODUCT, pages, policy_groups)
        self.assertEqual(ctx.exception.code, "LOCKED_MENU_SNAPSHOT_MISMATCH")

    def test_page_state_normalization(self):
        self.assertEqual(contract.normalized_page_release_state({}), "hidden")
        self.assertEqual(contract.normalized_page_release_state({"enabled": True}), "released")
        self.assertEqual(
            contract.normalized_page_release_state({"enabled": True, "release_state": "preview"}), "preview"
        )
        self.assertEqual(
            contract.normalized_page_release_state({"enabled": False, "release_state": "released"}), "hidden"
        )


if __name__ == "__main__":
    unittest.main()
