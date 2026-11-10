from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _load_product_menu_source():
    path = ROOT / "addons/smart_construction_core/services/product_menu_source.py"
    spec = importlib.util.spec_from_file_location("be_u03_product_menu_source", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _tokens(relative_path: str, *expected: str) -> None:
    text = (ROOT / relative_path).read_text(encoding="utf-8")
    for token in expected:
        if token not in text:
            raise AssertionError(f"{relative_path}: missing token: {token}")


class CapabilityIdentityBoundaryTest(unittest.TestCase):
    def test_menu_row_remains_entry_alias_identity(self):
        source = _load_product_menu_source()
        row = source._menu_row(
            "合同中心",
            "日常合同",
            "smart_construction_core.menu_sc_p1_daily_contract",
            "smart_construction_core.action_sc_general_contract",
            "sc.general.contract",
            ("合同", "日常合同"),
            maturity="released",
        )
        self.assertEqual(row["identity_kind"], "entry_compatibility_alias")
        self.assertFalse(row["business_capability"])
        self.assertEqual(row["qualification_authority"], "published_product_release")
        self.assertEqual(row["provider_authority"], "native_menu_action_entry")

    def test_scene_entry_remains_entry_alias_identity(self):
        source = _load_product_menu_source()
        row = source._scene_entry_row(
            "项目中心",
            "项目驾驶舱",
            "smart_construction_core.menu_project_dashboard",
            "project.execution",
            ("项目", "驾驶舱"),
            maturity="released",
        )
        self.assertEqual(row["identity_kind"], "entry_compatibility_alias")
        self.assertFalse(row["business_capability"])
        self.assertEqual(row["provider_authority"], "scene_entry_target")

    def test_menu_capability_projection_preserves_alias_contract(self):
        source = _load_product_menu_source()
        row = source._menu_row(
            "合同中心",
            "日常合同",
            "smart_construction_core.menu_sc_p1_daily_contract",
            "smart_construction_core.action_sc_general_contract",
            "sc.general.contract",
            ("合同", "日常合同"),
            maturity="released",
        )
        capability = source._capability_from_menu(row)
        self.assertEqual(
            capability["capability_key"],
            "construction.menu.smart_construction_core_menu_sc_p1_daily_contract",
        )
        self.assertEqual(capability["identity_kind"], "entry_compatibility_alias")
        self.assertFalse(capability["business_capability"])
        self.assertNotIn("default_payload", capability)

    def test_business_registry_and_delivery_projection_declare_identity(self):
        _tokens(
            "addons/smart_construction_core/services/capability_registry.py",
            '"identity_kind": "business_capability"',
            '"business_capability": True',
            '"definition_authority": "smart_construction_core.services.capability_registry"',
            '"qualification_authority": "product_catalog_and_effective_release"',
            "ENTRY_ALIAS_NOT_BUSINESS_CAPABILITY",
        )
        _tokens(
            "addons/smart_core/delivery/capability_service.py",
            '"capability_identity"',
            '"identity_kind": identity_kind',
            '"business_capability": bool(',
        )
        _tokens(
            "addons/smart_core/delivery/product_policy_catalog_sync_service.py",
            '"identity_kind": "entry_compatibility_alias"',
            '"business_capability": False',
        )
        _tokens(
            "addons/smart_construction_core/models/support/product_policy_sync.py",
            '"identity_kind": "entry_compatibility_alias"',
            '"business_capability": False',
        )


if __name__ == "__main__":
    unittest.main()
