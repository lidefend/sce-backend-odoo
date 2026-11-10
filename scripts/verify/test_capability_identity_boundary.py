from __future__ import annotations

import importlib.util
import sys
import types
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
    def test_unclassified_and_legacy_alias_rows_fail_closed(self):
        rows = _load_capability_rows()
        alias = rows.normalize_capability_row({"key": "construction.menu.example"})
        catalog_alias = rows.normalize_capability_row({"key": "catalog.menu.example"})
        unknown = rows.normalize_capability_row({"key": "legacy.unknown.key"})
        self.assertEqual(alias["identity_kind"], "entry_compatibility_alias")
        self.assertFalse(alias["business_capability"])
        self.assertEqual(catalog_alias["identity_kind"], "entry_compatibility_alias")
        self.assertFalse(catalog_alias["business_capability"])
        self.assertEqual(unknown["identity_kind"], "unclassified_capability")
        self.assertFalse(unknown["business_capability"])

    def test_delivery_projection_does_not_promote_runtime_presence_to_capability(self):
        service_module = _load_capability_service()
        service = service_module.CapabilityService()
        entries = service.build_entries(
            policy={"capabilities": [
                {"capability_key": "construction.menu.example"},
                {"capability_key": "legacy.unknown.key"},
            ]},
            capabilities=[
                {"key": "construction.menu.example"},
                {"key": "legacy.unknown.key"},
            ],
        )
        by_key = {row["key"]: row for row in entries}
        self.assertEqual(
            by_key["construction.menu.example"]["capability_identity"]["identity_kind"],
            "entry_compatibility_alias",
        )
        self.assertFalse(
            by_key["construction.menu.example"]["capability_identity"]["business_capability"]
        )
        self.assertEqual(
            by_key["legacy.unknown.key"]["capability_identity"]["identity_kind"],
            "unclassified_capability",
        )
        self.assertFalse(
            by_key["legacy.unknown.key"]["capability_identity"]["business_capability"]
        )

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
            '"business_capability": business_capability',
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

def _load_capability_rows():
    return _load_real_module(
        "smart_construction_core_capability_rows_test",
        "addons/smart_construction_core/core_extension_capability_rows.py",
    )


def _load_capability_service():
    _ensure_capability_service_packages()
    _load_real_module(
        "odoo.addons.smart_core.core.source_authority",
        "addons/smart_core/core/source_authority.py",
    )
    _load_real_module(
        "odoo.addons.smart_core.core.delivery_capability_entry_defaults",
        "addons/smart_core/core/delivery_capability_entry_defaults.py",
    )
    return _load_real_module(
        "odoo.addons.smart_core.delivery.capability_service",
        "addons/smart_core/delivery/capability_service.py",
    )


def _load_real_module(name: str, relative_path: str):
    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _ensure_capability_service_packages():
    for name, path in (
        ("odoo", ROOT / "addons/smart_core"),
        ("odoo.addons", ROOT / "addons"),
        ("odoo.addons.smart_core", ROOT / "addons/smart_core"),
        ("odoo.addons.smart_core.core", ROOT / "addons/smart_core/core"),
        ("odoo.addons.smart_core.delivery", ROOT / "addons/smart_core/delivery"),
    ):
        module = sys.modules.get(name) or types.ModuleType(name)
        module.__path__ = [str(path)]
        sys.modules[name] = module


if __name__ == "__main__":
    unittest.main()
