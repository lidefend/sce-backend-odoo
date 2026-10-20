#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SERVICE_PATH = (
    ROOT
    / "addons/smart_construction_core/services/product_configuration_capability.py"
)
MANIFEST_PATH = ROOT / "config/product_configuration_capability_v1.json"
MODULE_MANIFEST_PATH = (
    ROOT
    / "addons/smart_construction_core/data/product_configuration_capability_v1.json"
)


def _load_service():
    spec = importlib.util.spec_from_file_location(
        "product_configuration_capability_service", SERVICE_PATH
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


service = _load_service()


class FakeUser:
    def __init__(self, groups):
        self.groups = set(groups)

    def has_group(self, xmlid):
        return xmlid in self.groups


class ProductConfigurationCapabilityServiceTest(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    def test_business_full_sees_workspace_and_business_not_platform(self):
        user = FakeUser({"smart_construction_core.group_sc_business_full"})
        audiences = service.resolve_audiences(user)
        catalog = service.build_catalog(self.manifest, audiences)
        keys = {row["key"] for row in catalog["capabilities"]}
        self.assertIn("workspace.today_actions", keys)
        self.assertIn("business.centers", keys)
        self.assertNotIn("platform.tenant_company", keys)
        self.assertEqual(catalog["configuration_cards"], [])
        self.assertEqual(len(catalog["login_home"]["blocks"]), 6)

    def test_business_config_admin_gets_cards_and_business_capabilities(self):
        user = FakeUser(
            {"smart_construction_core.group_sc_cap_business_config_admin"}
        )
        audiences = service.resolve_audiences(user)
        catalog = service.build_catalog(self.manifest, audiences)
        keys = {row["key"] for row in catalog["capabilities"]}
        self.assertIn("workspace.today_actions", keys)
        self.assertIn("config.system_parameters", keys)
        self.assertNotIn("platform.tenant_company", keys)
        self.assertEqual(len(catalog["configuration_cards"]), 8)
        self.assertEqual(len(catalog["system_parameter_categories"]), 6)

    def test_platform_admin_sees_platform_and_support_not_workspace(self):
        user = FakeUser({"smart_core.group_smart_core_admin"})
        audiences = service.resolve_audiences(user)
        catalog = service.build_catalog(self.manifest, audiences)
        keys = {row["key"] for row in catalog["capabilities"]}
        self.assertIn("platform.tenant_company", keys)
        self.assertIn("support.diagnostics", keys)
        self.assertNotIn("workspace.today_actions", keys)

    def test_support_audience_is_read_only_surface(self):
        catalog = service.build_catalog(self.manifest, ["support"])
        keys = {row["key"] for row in catalog["capabilities"]}
        self.assertEqual(keys, {"support.diagnostics"})

    def test_planned_capability_is_not_available(self):
        catalog = service.build_catalog(self.manifest, ["business_full"])
        row = next(
            item
            for item in catalog["capabilities"]
            if item["key"] == "workspace.capability_map"
        )
        self.assertFalse(row["available"])
        self.assertEqual(row["reason"], "planned")

    def test_no_platform_capability_leaks_into_business_full(self):
        catalog = service.build_catalog(self.manifest, ["business_full"])
        keys = {row["key"] for row in catalog["capabilities"]}
        self.assertFalse(any(key.startswith(("platform.", "support.")) for key in keys))

    def test_runtime_manifest_copy_matches_product_manifest(self):
        self.assertEqual(
            MODULE_MANIFEST_PATH.read_bytes(),
            MANIFEST_PATH.read_bytes(),
        )


if __name__ == "__main__":
    unittest.main()
