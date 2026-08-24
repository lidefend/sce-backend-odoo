# -*- coding: utf-8 -*-
import importlib.util
import sys
import types
import unittest
from pathlib import Path


SMART_CORE_DIR = Path(__file__).resolve().parents[1]


def _load_module(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


sys.modules.setdefault("odoo", types.ModuleType("odoo"))
sys.modules.setdefault("odoo.addons", types.ModuleType("odoo.addons"))
smart_core_pkg = sys.modules.setdefault("odoo.addons.smart_core", types.ModuleType("odoo.addons.smart_core"))
smart_core_pkg.__path__ = [str(SMART_CORE_DIR)]
core_pkg = sys.modules.setdefault("odoo.addons.smart_core.core", types.ModuleType("odoo.addons.smart_core.core"))
core_pkg.__path__ = [str(SMART_CORE_DIR / "core")]

navigation_entry_target = _load_module(
    "odoo.addons.smart_core.core.navigation_entry_target",
    SMART_CORE_DIR / "core" / "navigation_entry_target.py",
)


class TestNavigationEntryTarget(unittest.TestCase):
    def test_scene_entry_target_carries_native_refs(self):
        entry = navigation_entry_target.normalize_entry_target(
            scene_key="projects.list",
            menu_id=379,
            action_id=506,
            model="project.project",
            view_modes=["tree", "form"],
        )

        self.assertEqual(entry["type"], "scene")
        self.assertEqual(entry["scene_key"], "projects.list")
        self.assertEqual(entry["route"], "/s/projects.list")
        self.assertEqual(
            entry["compatibility_refs"],
            {
                "menu_id": 379,
                "action_id": 506,
                "model": "project.project",
                "view_modes": ["tree", "form"],
            },
        )

    def test_action_result_is_wrapped_as_compatibility_entry_target(self):
        action = navigation_entry_target.normalize_odoo_action_result(
            None,
            {
                "type": "ir.actions.act_window",
                "id": 601,
                "res_model": "res.partner",
                "view_mode": "tree,form",
            },
        )

        self.assertEqual(action["entry_target"]["type"], "compatibility")
        self.assertEqual(action["entry_target"]["route"], "/a/601")
        self.assertEqual(
            action["entry_target"]["compatibility_refs"],
            {
                "action_id": 601,
                "model": "res.partner",
                "view_modes": ["tree", "form"],
                "target_type": "action",
                "delivery_mode": "odoo_action_result",
            },
        )

    def test_plain_business_result_does_not_invent_navigation(self):
        result = navigation_entry_target.normalize_odoo_action_result(
            None,
            {"warnings": {42: [{"reason_code": "ADVISORY"}]}},
            source_model="payment.request",
            source_record_id=42,
        )

        self.assertEqual(result, {"warnings": {42: [{"reason_code": "ADVISORY"}]}})
        self.assertNotIn("entry_target", result)
        self.assertNotIn("action_id", result)

    def test_record_entry_carries_formal_intent_and_current_user_write_authority(self):
        class _Model:
            def check_access_rights(self, mode, raise_exception=False):
                assert mode == "write"
                assert raise_exception is False
                return True

        class _Env(dict):
            def __getitem__(self, key):
                if key == "project.project":
                    return _Model()
                return super().__getitem__(key)

        action = navigation_entry_target.normalize_odoo_action_result(
            _Env(),
            {
                "type": "ir.actions.act_window",
                "res_model": "project.project",
                "res_id": 42,
                "view_mode": "form",
                "context": {"entry_intent": "handling"},
            },
        )

        self.assertEqual(
            action["entry_target"]["record_entry"],
            {
                "model": "project.project",
                "record_id": 42,
                "entry_intent": "handling",
                "model_write_authority": True,
            },
        )

    def test_record_entry_omits_unavailable_write_authority(self):
        entry = navigation_entry_target.normalize_entry_target(
            model="project.project",
            record_id=42,
            entry_intent="handling",
        )

        self.assertEqual(entry["record_entry"]["entry_intent"], "handling")
        self.assertNotIn("model_write_authority", entry["record_entry"])

    def test_explicit_entry_target_is_completed_without_using_legacy_route_as_authority(self):
        class _Model:
            def check_access_rights(self, mode, raise_exception=False):
                assert mode == "write"
                assert raise_exception is False
                return True

        action = navigation_entry_target.normalize_odoo_action_result(
            {"payment.request": _Model()},
            {
                "type": "ir.actions.act_window",
                "context": {"entry_intent": "handling"},
                "entry_target": {
                    "type": "compatibility",
                    "route": "/r/payment.request/100",
                    "record_entry": {"model": "payment.request", "record_id": 100},
                },
            },
        )

        self.assertEqual(
            action["entry_target"]["record_entry"],
            {
                "model": "payment.request",
                "record_id": 100,
                "entry_intent": "handling",
                "model_write_authority": True,
            },
        )

    def test_client_action_next_is_wrapped_and_promoted_to_entry_target(self):
        action = navigation_entry_target.normalize_odoo_action_result(
            None,
            {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "message": "ok",
                    "next": {
                        "type": "ir.actions.act_window",
                        "id": 77,
                        "res_model": "project.project",
                        "view_mode": "form",
                    },
                },
            },
        )

        self.assertEqual(action["entry_target"]["type"], "compatibility")
        self.assertEqual(action["entry_target"]["compatibility_refs"]["action_id"], 77)
        self.assertEqual(action["params"]["next"]["entry_target"], action["entry_target"])

    def test_modal_form_action_opens_create_form_without_source_record_leakage(self):
        action = navigation_entry_target.normalize_odoo_action_result(
            None,
            {
                "type": "ir.actions.act_window",
                "name": "Create target document",
                "res_model": "x.relation.wizard",
                "view_mode": "form",
                "target": "new",
                "context": {"default_source_id": 42},
            },
            source_model="x.source",
            source_record_id=42,
        )

        entry_target = action["entry_target"]
        self.assertEqual(entry_target["route"], "/f/x.relation.wizard/new")
        self.assertEqual(entry_target["compatibility_refs"]["model"], "x.relation.wizard")
        self.assertEqual(
            entry_target["presentation"],
            {
                "title": "Create target document",
                "title_authority": "odoo_action_result",
            },
        )
        self.assertNotIn("record_entry", entry_target)

    def test_existing_entry_target_receives_action_result_title_authority(self):
        action = navigation_entry_target.normalize_odoo_action_result(
            None,
            {
                "type": "ir.actions.act_window",
                "name": "Create reviewed item",
                "entry_target": {
                    "type": "compatibility",
                    "route": "/f/x.review/new",
                    "presentation": {"subtitle": "Review"},
                },
            },
        )

        self.assertEqual(
            action["entry_target"]["presentation"],
            {
                "subtitle": "Review",
                "title": "Create reviewed item",
                "title_authority": "odoo_action_result",
            },
        )

    def test_modal_form_action_preserves_explicit_view_without_guessing_menu_action(self):
        class _ActionModel:
            def sudo(self):
                return self

            def search(self, *_args, **_kwargs):
                raise AssertionError("explicit modal view must not guess a menu action")

        action = navigation_entry_target.normalize_odoo_action_result(
            {"ir.actions.act_window": _ActionModel()},
            {
                "type": "ir.actions.act_window",
                "res_model": "x.relation.wizard",
                "view_mode": "form",
                "view_id": 812,
                "target": "new",
            },
        )

        entry_target = action["entry_target"]
        self.assertEqual(entry_target["route"], "/f/x.relation.wizard/new")
        self.assertEqual(entry_target["compatibility_refs"]["view_id"], 812)
        self.assertNotIn("action_id", entry_target["compatibility_refs"])


if __name__ == "__main__":
    unittest.main()
