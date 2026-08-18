# -*- coding: utf-8 -*-
"""
smart_scene minimal tests (PRODUCTIZATION-P0-SPRINT-001, R1).

scene_resolver is P0 kernel routing: pin the hint-priority contract
(scene hint wins over page hint wins over defaults) — every consumer of
resolve_scene_identity depends on this ordering.

PENDING-ENV: to be executed in an Odoo test run (make mod.tests or CI).
"""

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.smart_scene.core.scene_resolver import resolve_scene_identity


@tagged("post_install", "-at_install", "smart_scene", "scene_resolver")
class TestSceneResolverPriority(TransactionCase):
    def test_scene_hint_wins_over_defaults(self):
        result = resolve_scene_identity(
            scene_hint={"key": "owner.dashboard", "scene_type": "workbench"},
            page_hint=None,
            defaults={"scene_key": "fallback.scene"},
        )
        self.assertEqual(result["scene"]["scene_key"], "owner.dashboard")
        self.assertEqual(result["scene"]["scene_type"], "workbench")

    def test_page_hint_wins_over_defaults(self):
        result = resolve_scene_identity(
            scene_hint=None,
            page_hint={"key": "project.list", "route": "/workbench?scene=x", "model": "project.project"},
            defaults={"page_key": "fallback.page", "model": "fallback.model"},
        )
        self.assertEqual(result["page"]["key"], "project.list")
        self.assertEqual(result["page"]["route"], "/workbench?scene=x")
        self.assertEqual(result["page"]["model"], "project.project")

    def test_falls_back_to_defaults_when_hints_empty(self):
        result = resolve_scene_identity(
            scene_hint=None,
            page_hint=None,
            defaults={
                "scene_key": "default.scene",
                "page_key": "default.page",
                "page_route": "/default",
                "layout_mode": "dashboard",
            },
        )
        self.assertEqual(result["scene"]["scene_key"], "default.scene")
        self.assertEqual(result["page"]["key"], "default.page")
        self.assertEqual(result["page"]["route"], "/default")
        self.assertEqual(result["scene"]["layout_mode"], "dashboard")

    def test_scene_page_key_falls_back_to_scene_page(self):
        # page key may inherit the scene's declared page when page_hint is silent
        result = resolve_scene_identity(
            scene_hint={"key": "owner.payment.center", "page": "payment.center"},
            page_hint={},
            defaults=None,
        )
        self.assertEqual(result["page"]["key"], "payment.center")

    def test_blank_inputs_are_normalized_to_empty_strings(self):
        result = resolve_scene_identity(scene_hint=None, page_hint=None, defaults=None)
        self.assertEqual(result["scene"]["scene_key"], "")
        self.assertEqual(result["page"]["route"], "")
        self.assertIsNone(result["page"]["record_id"])
        # scene block must mirror key into scene_key for downstream lookups
        self.assertIn("scene_key", result["scene"])

    def test_whitespace_is_stripped(self):
        result = resolve_scene_identity(
            scene_hint={"key": "  owner.dashboard  "},
            page_hint={"route": "  /workbench  "},
            defaults=None,
        )
        self.assertEqual(result["scene"]["scene_key"], "owner.dashboard")
        self.assertEqual(result["page"]["route"], "/workbench")
