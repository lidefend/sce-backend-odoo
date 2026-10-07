# -*- coding: utf-8 -*-
import unittest

from odoo.tests.common import BaseCase, tagged

from odoo.addons.smart_core.utils.contract_governance import (
    apply_contract_governance,
    apply_native_authority_domain_overrides,
)
from odoo.addons.smart_construction_core.services import contract_governance_overrides  # noqa: F401


def _payload(scene_key="projects.intake", render_profile="create", menu_xmlid=None):
    return {
        "head": {
            "model": "project.project",
            "view_type": "form",
            "scene_key": scene_key,
            "render_profile": render_profile,
            "menu_xmlid": menu_xmlid,
        },
        "model": "project.project",
        "scene_key": scene_key,
        "render_profile": render_profile,
        "menu_xmlid": menu_xmlid,
        "views": {
            "form": {
                "layout": [
                    {"type": "sheet"},
                    {"type": "field", "name": "name"},
                    {"type": "field", "name": "manager_id"},
                ]
            }
        },
        "fields": {
            "name": {"string": "名称", "type": "char", "required": True, "readonly": False},
            "manager_id": {
                "string": "项目管理员",
                "type": "many2one",
                "required": False,
                "readonly": False,
            },
        },
    }


@tagged("post_install", "-at_install", "uc4_native_lowcode")
class ProjectIntakeContractGovernanceCase(BaseCase):
    def test_project_intake_create_contract_receives_scene_governance(self):
        governed = apply_contract_governance(_payload(), "user")

        governance = governed.get("form_governance") or {}
        self.assertEqual(governance.get("surface"), "project_intake")
        self.assertEqual(governance.get("create_flow_mode"), "standard")
        self.assertEqual(governance.get("autosave_scope"), "project_intake_standard")
        self.assertEqual(governance.get("primary_action_label"), "创建项目")
        self.assertEqual(
            governance.get("post_create_target"),
            {
                "intent": "project.dashboard.enter",
                "route": "/s/project.management",
            },
        )
        self.assertNotEqual(governance.get("primary_action_label"), "保存草稿")

    def test_project_quick_create_contract_receives_quick_governance(self):
        governed = apply_contract_governance(
            _payload(
                scene_key="",
                menu_xmlid="smart_construction_core.menu_sc_project_quick_create",
            ),
            "user",
        )

        governance = governed.get("form_governance") or {}
        self.assertEqual(governance.get("surface"), "project_intake")
        self.assertEqual(governance.get("create_flow_mode"), "quick")
        self.assertEqual(governance.get("autosave_scope"), "project_intake_quick")
        self.assertEqual(governance.get("primary_action_label"), "创建并进入项目驾驶舱")
        self.assertEqual(
            governance.get("post_create_target"),
            {
                "intent": "project.dashboard.enter",
                "route": "/s/project.management",
            },
        )

    def test_native_authority_intake_create_still_receives_its_declaration(self):
        """The intake form resolves to a native view, which skips generic governance.

        The declaration only describes what saving means on the entry (it never
        rewrites the native structure), so it must still reach the contract on
        that path. The registration defect this locks was silent: the generic
        `apply_contract_governance` path delivered the label, while the real
        handler took the native-authority branch and delivered nothing, so the
        entry fell back to the generic draft wording on the live page.
        """
        payload = _payload()
        apply_native_authority_domain_overrides(payload, "user")

        governance = payload.get("form_governance") or {}
        self.assertEqual(governance.get("surface"), "project_intake")
        self.assertEqual(governance.get("create_flow_mode"), "standard")
        self.assertTrue(governance.get("primary_action_label"))
        self.assertNotEqual(governance.get("primary_action_label"), "保存草稿")

    def test_native_authority_intake_quick_create_still_receives_its_declaration(self):
        payload = _payload(
            scene_key="",
            menu_xmlid="smart_construction_core.menu_sc_project_quick_create",
        )
        apply_native_authority_domain_overrides(payload, "user")

        governance = payload.get("form_governance") or {}
        self.assertEqual(governance.get("create_flow_mode"), "quick")
        self.assertTrue(governance.get("primary_action_label"))

    def test_native_authority_skip_does_not_leak_into_non_intake_forms(self):
        """Only semantic declarations survive the skip; the predicate still guards it."""
        payload = _payload(scene_key="projects.list")
        apply_native_authority_domain_overrides(payload, "user")

        governance = payload.get("form_governance") or {}
        self.assertIsNone(governance.get("create_flow_mode"))
        self.assertIsNone(governance.get("primary_action_label"))

    def test_non_intake_project_contract_is_not_overridden(self):
        governed = apply_contract_governance(_payload(scene_key="projects.list"), "user")

        governance = governed.get("form_governance") or {}
        self.assertNotEqual(governance.get("surface"), "project_intake")
        self.assertIsNone(governance.get("create_flow_mode"))
        self.assertIsNone(governance.get("post_create_target"))

    def test_non_create_project_contract_is_not_overridden(self):
        governed = apply_contract_governance(_payload(render_profile="edit"), "user")

        governance = governed.get("form_governance") or {}
        self.assertNotEqual(governance.get("surface"), "project_intake")
        self.assertIsNone(governance.get("create_flow_mode"))
        self.assertIsNone(governance.get("post_create_target"))


if __name__ == "__main__":
    unittest.main()
