# -*- coding: utf-8 -*-
"""
smart_owner_bundle minimal tests (PRODUCTIZATION-P0-SPRINT-001, R1).

Cross-consistency: every tile capability required by a bundle scene must be
declared in the bundle capability registry — a broken workbench tile is a
customer-visible defect.

PENDING-ENV: to be executed in an Odoo test run (make mod.tests or CI).
"""

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.smart_owner_bundle.services.bundle_registry import (
    default_dashboard,
    list_bundle_capabilities,
    list_bundle_scenes,
    recommended_roles,
)


@tagged("post_install", "-at_install", "smart_owner_bundle", "registry_consistency")
class TestOwnerBundleRegistryConsistency(TransactionCase):
    def test_scene_tile_capabilities_are_declared(self):
        capability_keys = {cap["key"] for cap in list_bundle_capabilities()}
        for scene in list_bundle_scenes():
            for tile in scene["tiles"]:
                for required in tile["required_capabilities"]:
                    self.assertIn(
                        required,
                        capability_keys,
                        msg=f"scene {scene['code']} tile {tile['key']} requires undeclared capability {required}",
                    )

    def test_scenes_carry_route_targets(self):
        for scene in list_bundle_scenes():
            self.assertEqual(scene["target"]["scene_key"], scene["code"])
            self.assertTrue(scene["target"]["route"].startswith("/workbench?scene="))

    def test_capability_records_are_wellformed(self):
        required_fields = {
            "key", "name", "ui_label", "intent", "group_key",
            "version", "state", "capability_state", "default_payload",
            "required_roles",
        }
        for cap in list_bundle_capabilities():
            missing = required_fields - set(cap.keys())
            self.assertFalse(missing, msg=f"capability {cap.get('key')} missing fields {missing}")
            self.assertIn(cap["capability_state"], {"allow", "readonly", "pending"})

    def test_registry_defaults(self):
        scenes = {scene["code"] for scene in list_bundle_scenes()}
        self.assertIn(default_dashboard(), scenes)
        self.assertIn("owner", recommended_roles())
