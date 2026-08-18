# -*- coding: utf-8 -*-
"""
smart_owner_core minimal tests (PRODUCTIZATION-P0-SPRINT-001, R1).

Pins the extension-point contract: handler registration into the smart_core
registry and the industry-gated system_init overlay (must be a no-op unless
context carries sc.industry=owner).

PENDING-ENV: to be executed in an Odoo test run (make mod.tests or CI).
"""

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.smart_owner_core.core_extension import (
    get_intent_handler_contributions,
    smart_core_extend_system_init,
    smart_core_register,
)


class _ContextEnv:
    def __init__(self, context):
        self.context = context


@tagged("post_install", "-at_install", "smart_owner_core", "extension_contract")
class TestOwnerCoreExtensionContract(TransactionCase):
    def test_intent_contributions_are_unique_and_active(self):
        contributions = get_intent_handler_contributions()
        intents = [item["intent"] for item in contributions]
        self.assertEqual(len(intents), len(set(intents)), msg="duplicate intent registrations")
        for item in contributions:
            self.assertEqual(item["source_module"], "smart_owner_core")
            self.assertEqual(item["domain"], "owner")
            self.assertEqual(item["status"], "active")
            self.assertIsNotNone(item["handler"])
        # productization storefront intents must stay registered
        for required in (
            "owner.payment.request.submit",
            "owner.payment.request.approve",
            "owner.approval.center",
        ):
            self.assertIn(required, intents)

    def test_smart_core_register_fills_registry(self):
        registry = {}
        smart_core_register(registry)
        self.assertTrue(registry)
        for intent, handler in registry.items():
            self.assertTrue(intent)
            self.assertTrue(callable(handler) or hasattr(handler, "__name__"))

    def test_smart_core_register_ignores_non_dict(self):
        smart_core_register(None)  # must not raise

    def test_system_init_overlay_is_gated_by_industry(self):
        data = {"scenes": ["keep-me"], "capabilities": ["keep-me"]}
        smart_core_extend_system_init(data, _ContextEnv({"sc.industry": "construction"}), None)
        self.assertEqual(data["scenes"], ["keep-me"], msg="overlay must be a no-op for non-owner industry")

        smart_core_extend_system_init(data, _ContextEnv({}), None)
        self.assertEqual(data["scenes"], ["keep-me"], msg="overlay must be a no-op without industry context")

    def test_system_init_overlay_replaces_payload_for_owner(self):
        data = {"scenes": ["old"], "capabilities": ["old"]}
        smart_core_extend_system_init(data, _ContextEnv({"sc.industry": "OWNER"}), None)
        self.assertNotEqual(data["scenes"], ["old"])
        self.assertEqual(data["scene_count"], len(data["scenes"]))
        self.assertEqual(data["capability_count"], len(data["capabilities"]))
        scene_codes = {scene["code"] for scene in data["scenes"]}
        self.assertIn("owner.dashboard", scene_codes)
