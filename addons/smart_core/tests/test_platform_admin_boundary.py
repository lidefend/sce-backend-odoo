# -*- coding: utf-8 -*-
import importlib.util
import csv
import unittest
from pathlib import Path
import xml.etree.ElementTree as ET


def _load_module():
    root = Path(__file__).resolve().parents[1]
    module_name = "platform_admin_boundary_under_test"
    spec = importlib.util.spec_from_file_location(module_name, root / "security" / "platform_admin.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_construction_policy():
    addons_dir = Path(__file__).resolve().parents[2]
    module_name = "construction_policy_map_under_test"
    spec = importlib.util.spec_from_file_location(
        module_name,
        addons_dir / "smart_construction_core" / "core_extension_policy_maps.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _FakeUser:
    def __init__(self, groups):
        self._groups = set(groups)

    def has_group(self, xmlid):
        return xmlid in self._groups


class TestPlatformAdminBoundary(unittest.TestCase):
    def setUp(self):
        self.module = _load_module()

    def test_platform_admin_default_excludes_legacy_industry_config_group(self):
        user = _FakeUser({self.module.LEGACY_PLATFORM_ADMIN_GROUP})

        self.assertFalse(self.module.user_is_platform_admin(user))
        self.assertTrue(self.module.user_is_platform_admin(user, include_legacy=True))

    def test_platform_admin_default_excludes_system_admin_group(self):
        user = _FakeUser({self.module.SYSTEM_ADMIN_GROUP})

        self.assertFalse(self.module.user_is_platform_admin(user))
        self.assertTrue(self.module.user_is_platform_admin(user, include_system=True))
        self.assertFalse(self.module.can_discover_platform_capabilities(user))
        self.assertFalse(self.module.can_manage_system_configuration(user))
        self.assertTrue(self.module.user_is_break_glass_technical_admin(user))
        self.assertFalse(self.module.has_customer_business_data_scope(user))

    def test_smart_core_admin_discovers_capabilities_without_business_data_scope(self):
        user = _FakeUser({self.module.PLATFORM_ADMIN_GROUP})

        self.assertTrue(self.module.user_is_platform_admin(user))
        self.assertTrue(self.module.can_discover_platform_capabilities(user))
        self.assertTrue(self.module.can_manage_system_configuration(user))
        self.assertFalse(self.module.has_customer_business_data_scope(user))

    def test_legacy_config_admin_is_not_promoted_to_capability_discovery_admin(self):
        user = _FakeUser({self.module.LEGACY_PLATFORM_ADMIN_GROUP})

        self.assertFalse(self.module.can_discover_platform_capabilities(user))
        self.assertFalse(self.module.can_manage_system_configuration(user))
        self.assertFalse(self.module.has_customer_business_data_scope(user))

    def test_security_admin_identity_is_independent(self):
        user = _FakeUser({self.module.SECURITY_ADMIN_GROUP})

        self.assertTrue(self.module.user_is_security_admin(user))
        self.assertFalse(self.module.user_is_platform_admin(user))
        self.assertFalse(self.module.user_is_break_glass_technical_admin(user))
        self.assertFalse(self.module.can_discover_platform_capabilities(user))

    def test_platform_admin_group_xmlids_are_strict_by_default(self):
        self.assertEqual(self.module.platform_admin_group_xmlids(), [self.module.PLATFORM_ADMIN_GROUP])

    def test_customer_business_models_do_not_grant_admin_identity_groups_acl(self):
        addons_dir = Path(__file__).resolve().parents[2]
        acl_path = addons_dir / "smart_construction_core" / "security" / "ir.model.access.csv"
        customer_models = {
            "model_project_project",
            "model_sc_general_contract",
            "model_payment_request",
        }
        admin_identity_groups = {
            self.module.PLATFORM_ADMIN_GROUP,
            self.module.SYSTEM_ADMIN_GROUP,
        }

        with acl_path.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))

        forbidden = [
            row
            for row in rows
            if row.get("model_id:id") in customer_models
            and row.get("group_id:id") in admin_identity_groups
        ]
        self.assertEqual(forbidden, [])

    def test_daily_product_admin_policy_excludes_break_glass_group(self):
        policy = _load_construction_policy()
        groups = policy.ROLE_GROUPS_EXPLICIT["system_admin"]
        surface = policy.ROLE_SURFACE_OVERRIDES["system_admin"]

        self.assertIn(self.module.PLATFORM_ADMIN_GROUP, groups)
        self.assertNotIn(self.module.SYSTEM_ADMIN_GROUP, groups)
        self.assertTrue(surface["discover_installed_capabilities"])
        self.assertTrue(surface["system_configuration_visible"])
        self.assertFalse(surface.get("deny_all_navigation", False))

    def test_construction_group_graph_removes_legacy_system_bridge(self):
        addons_dir = Path(__file__).resolve().parents[2]
        path = (
            addons_dir
            / "smart_construction_core"
            / "security"
            / "sc_capability_groups.xml"
        )
        root = ET.parse(path).getroot()
        system_record = next(
            record
            for record in root.iter("record")
            if record.attrib.get("id") == "base.group_system"
        )
        system_eval = next(
            field.attrib.get("eval", "")
            for field in system_record
            if field.attrib.get("name") == "implied_ids"
        )
        task_record = next(
            record
            for record in root.iter("record")
            if record.attrib.get("id") == "group_sc_task_entry_access"
        )
        task_eval = next(
            field.attrib.get("eval", "")
            for field in task_record
            if field.attrib.get("name") == "implied_ids"
        )

        self.assertIn(
            "(3, ref('smart_construction_core.group_sc_task_entry_access'))",
            system_eval,
        )
        self.assertIn(
            "(3, ref('smart_construction_core.group_sc_cap_settlement_read'))",
            system_eval,
        )
        self.assertNotIn("base.group_system", task_eval)
        self.assertNotIn("project.group_project_manager", task_eval)


if __name__ == "__main__":
    unittest.main()
