import unittest
from pathlib import Path

from scripts.verify.odoo_native_capability_explorer_probe import entry_selection_assessment


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


if __name__ == "__main__":
    unittest.main()
