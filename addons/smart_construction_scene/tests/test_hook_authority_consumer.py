from odoo.tests.common import TransactionCase, tagged
from odoo.addons.smart_core.utils.extension_hooks import call_extension_hook_first


@tagged("post_install", "-at_install", "sc_gate", "extension_hook_authority")
class TestHookAuthorityConsumer(TransactionCase):
    def test_scene_navigation_provider_reaches_real_consumer(self):
        payload = call_extension_hook_first(
            self.env,
            "smart_core_nav_scene_maps",
            self.env,
        )
        self.assertIsInstance(payload, dict)
        menu_map = payload.get("menu_scene_map") or {}
        self.assertEqual(
            menu_map.get("smart_construction_core.menu_sc_project_manage"),
            "project.management",
        )

    def test_scene_target_overrides_are_merged_with_core(self):
        payload = call_extension_hook_first(
            self.env,
            "smart_core_critical_scene_target_overrides",
            self.env,
        )
        self.assertIn("projects.list", payload)
        self.assertIn("material.outbound", payload)

    def test_scene_route_override_provider_reaches_real_consumer(self):
        payload = call_extension_hook_first(
            self.env,
            "smart_core_critical_scene_target_route_overrides",
            self.env,
        )
        self.assertIsInstance(payload, dict)

    def test_identity_profile_has_core_single_owner(self):
        payload = call_extension_hook_first(
            self.env,
            "smart_core_identity_profile",
            self.env,
        )
        self.assertIsInstance(payload, dict)
        self.assertIn("system_admin", payload.get("role_precedence") or ())
