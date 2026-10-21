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

    def test_capability_map_is_available(self):
        catalog = service.build_catalog(self.manifest, ["business_full"])
        row = next(
            item
            for item in catalog["capabilities"]
            if item["key"] == "workspace.capability_map"
        )
        self.assertTrue(row["available"])
        self.assertEqual(row["status"], "available")

    def test_planned_capability_projection_marks_not_available(self):
        manifest = {
            "capabilities": [
                {
                    "key": "workspace.example",
                    "label": "示例能力",
                    "audience": "business_full",
                    "status": "planned",
                    "entry": "workspace.example",
                    "authority": "system.init capabilities",
                    "description": "示例",
                }
            ]
        }
        catalog = service.build_catalog(manifest, ["business_full"])
        row = catalog["capabilities"][0]
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


class UserCapabilityProjectionTest(unittest.TestCase):
    def test_preserves_all_permission_verdicts_without_audience_inference(self):
        for state in ('allow', 'readonly', 'deny', 'pending', 'coming_soon'):
            row = {'key': 'finance', 'ui_label': '财务', 'capability_state': state,
                   'reason': 'authority reason', 'reason_code': 'AUTHORITY',
                   'group_label': '财务管理', 'ui_hint': '说明'}
            item = service.build_user_capabilities([row])['items'][0]
            self.assertEqual(item['status'], state)
            self.assertEqual(item['reason'], row['reason'])
            self.assertEqual(item['reason_code'], row['reason_code'])
            self.assertEqual(item['available'], state in {'allow', 'readonly'})
            self.assertTrue(item['status_label'])

    def test_empty_authority_stays_empty(self):
        surface = service.build_user_capabilities([])
        self.assertEqual(surface['items'], [])
        self.assertTrue(surface['empty_message'])

    def test_missing_or_unknown_verdict_fails(self):
        for row in ({'key': 'broken'}, {'key': 'broken', 'capability_state': 'invented'}):
            with self.assertRaises((KeyError, ValueError)):
                service.build_user_capabilities([row])


if __name__ == "__main__":
    unittest.main()
