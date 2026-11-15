import unittest
from pathlib import Path

from scripts.verify.odoo_native_capability_explorer_probe import (
    classify_business_domain,
    entry_selection_assessment,
)


class NativeCapabilitySelectionTest(unittest.TestCase):
    def assess(self, **overrides):
        values = {
            "menu_xmlid": "smart_construction_core.menu_example",
            "action_xmlid": "smart_construction_core.action_example",
            "action_type": "ir.actions.act_window",
            "res_model": "project.project",
            "module_state": "installed",
            "action_exists": True,
            "menu_action_matches": True,
            "model_exists": True,
        }
        values.update(overrides)
        return entry_selection_assessment(**values)

    def test_complete_native_window_entry_is_selectable(self):
        result = self.assess()
        self.assertTrue(result["draft_selectable"])
        self.assertEqual(result["selection_blockers"], [])
        self.assertTrue(result["requires_scene_qualification"])

    def test_missing_stable_identity_is_blocked(self):
        result = self.assess(menu_xmlid="", action_xmlid="")
        self.assertFalse(result["draft_selectable"])
        self.assertEqual(result["selection_blockers"], [
            "MENU_XMLID_MISSING",
            "ACTION_XMLID_MISSING",
        ])

    def test_uninstalled_or_broken_provider_is_blocked(self):
        result = self.assess(
            module_state="uninstalled",
            action_exists=False,
            menu_action_matches=False,
        )
        self.assertFalse(result["draft_selectable"])
        self.assertEqual(result["selection_blockers"], [
            "MODULE_NOT_INSTALLED",
            "ACTION_NOT_FOUND",
            "MENU_ACTION_MISMATCH",
        ])

    def test_window_action_requires_installed_model(self):
        result = self.assess(res_model="missing.model", model_exists=False)
        self.assertFalse(result["draft_selectable"])
        self.assertEqual(result["selection_blockers"], ["MODEL_NOT_FOUND"])

    def test_non_window_action_does_not_require_model(self):
        result = self.assess(
            action_type="ir.actions.client",
            res_model="",
            model_exists=False,
        )
        self.assertTrue(result["draft_selectable"])

    def test_probe_has_no_parallel_capability_registry_reference(self):
        source = Path(__file__).with_name("odoo_native_capability_explorer_probe.py").read_text()
        self.assertNotIn("sc.capability", source)

    def test_single_scene_binding_is_authoritative_domain(self):
        result = classify_business_domain(
            scene_bindings=[{
                "scenario_key": "material.management",
                "scenario_name": "项目材料管理",
            }],
            center_key="construction.项目中心",
            center_name="项目中心",
        )
        self.assertEqual(result["business_domain_key"], "material.management")
        self.assertEqual(result["classification_confidence"], "authoritative_scene_binding")

    def test_multiple_scene_bindings_are_unclassified(self):
        result = classify_business_domain(
            scene_bindings=[
                {"scenario_key": "material.management", "scenario_name": "项目材料管理"},
                {"scenario_key": "cost.budget", "scenario_name": "成本与预算管理"},
            ],
            center_key="construction.项目中心",
            center_name="项目中心",
        )
        self.assertEqual(result["business_domain_key"], "")
        self.assertEqual(result["classification_reason"], "AMBIGUOUS_SCENE_BINDING")

    def test_center_does_not_guess_business_domain(self):
        result = classify_business_domain(
            scene_bindings=[],
            center_key="construction.项目中心",
            center_name="项目中心",
        )
        self.assertEqual(result["business_domain_key"], "")
        self.assertEqual(result["classification_confidence"], "center_only")
        self.assertEqual(result["classification_reason"], "NO_SCENE_BINDING")

    def test_missing_binding_and_center_is_unclassified(self):
        result = classify_business_domain(scene_bindings=[])
        self.assertEqual(result["business_domain_key"], "")
        self.assertEqual(result["classification_confidence"], "unclassified")
        self.assertEqual(result["classification_reason"], "NO_CLASSIFICATION_EVIDENCE")


if __name__ == "__main__":
    unittest.main()
