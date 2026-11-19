# -*- coding: utf-8 -*-
import json
import unittest

from lxml import etree
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
                    {"type": "field", "name": "initiation_date"},
                    {"type": "field", "name": "manager_id"},
                    {"type": "field", "name": "operation_strategy"},
                    {"type": "field", "name": "owner_id"},
                    {"type": "field", "name": "project_type_id"},
                    {"type": "field", "name": "location"},
                    {"type": "field", "name": "start_date"},
                    {"type": "field", "name": "end_date"},
                ]
            }
        },
        "fields": {
            "name": {"string": "名称", "type": "char", "required": True, "readonly": False},
            "initiation_date": {
                "string": "立项日期",
                "type": "date",
                "required": True,
                "readonly": False,
            },
            "manager_id": {
                "string": "项目管理员",
                "type": "many2one",
                "relation": "res.users",
                "required": False,
                "readonly": False,
            },
            "operation_strategy": {
                "string": "经营方式",
                "type": "selection",
                "selection": [("direct", "公司直营"), ("joint", "联合经营")],
                "required": False,
                "readonly": False,
            },
            "owner_id": {
                "string": "业主单位",
                "type": "many2one",
                "relation": "res.partner",
                "required": False,
                "readonly": False,
            },
            "project_type_id": {
                "string": "项目类型",
                "type": "many2one",
                "relation": "project.type",
                "required": False,
                "readonly": False,
            },
            "location": {
                "string": "项目地点",
                "type": "char",
                "size": 128,
                "required": False,
                "readonly": False,
            },
            "start_date": {
                "string": "计划开始",
                "type": "date",
                "required": False,
                "readonly": False,
            },
            "end_date": {
                "string": "计划结束",
                "type": "date",
                "required": False,
                "readonly": False,
            },
            "project_category_id": {
                "string": "项目分类",
                "type": "many2one",
                "relation": "project.category",
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
        autosave = governed["views"]["form"]["autosave"]
        self.assertTrue(autosave["enabled"])
        self.assertEqual(autosave["scope"], "project_intake_standard")
        self.assertEqual(autosave["appliesTo"], ["create"])
        self.assertEqual(autosave["policyVersion"], 1)
        self.assertEqual(autosave["storage"]["kind"], "browser_local_storage")
        self.assertEqual(autosave["retention"]["seconds"], 86400)
        self.assertEqual(autosave["retention"]["basis"], "last_valid_input")
        self.assertEqual(autosave["recovery"]["strategy"], "prompt_restore_or_discard")
        self.assertEqual(
            set(autosave["identity"]["requiredScopes"]),
            {
                "tenant", "user", "company", "menu", "action",
                "form_view", "entry_scope", "form_instance",
            },
        )
        fields = {row["name"]: row for row in autosave["fields"]}
        self.assertEqual(
            set(fields),
            {
                "name", "initiation_date", "manager_id", "operation_strategy",
                "owner_id", "project_type_id", "location", "start_date", "end_date",
            },
        )
        self.assertEqual(fields["name"]["inputKind"], "text")
        self.assertEqual(fields["manager_id"]["inputKind"], "relation")
        self.assertEqual(fields["manager_id"]["relation"], "res.users")
        self.assertTrue(fields["manager_id"]["constraints"]["mustExist"])
        self.assertEqual(fields["operation_strategy"]["inputKind"], "selection")
        self.assertEqual(
            fields["operation_strategy"]["constraints"]["allowedValues"],
            ["direct", "joint"],
        )
        self.assertEqual(fields["initiation_date"]["constraints"]["format"], "YYYY-MM-DD")
        self.assertNotIn("project_category_id", fields)
        self.assertFalse(autosave["coverage"]["attachments"])
        self.assertFalse(autosave["coverage"]["unsavedChildRecords"])

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
        autosave = governed["views"]["form"]["autosave"]
        self.assertTrue(autosave["enabled"])
        self.assertEqual(autosave["scope"], "project_intake_quick")
        self.assertEqual(
            {row["name"] for row in autosave["fields"]},
            {"name", "initiation_date", "manager_id", "operation_strategy", "owner_id"},
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
        self.assertTrue(payload["views"]["form"]["autosave"]["enabled"])

    def test_native_authority_intake_quick_create_still_receives_its_declaration(self):
        payload = _payload(
            scene_key="",
            menu_xmlid="smart_construction_core.menu_sc_project_quick_create",
        )
        apply_native_authority_domain_overrides(payload, "user")

        governance = payload.get("form_governance") or {}
        self.assertEqual(governance.get("create_flow_mode"), "quick")
        self.assertTrue(governance.get("primary_action_label"))
        self.assertTrue(payload["views"]["form"]["autosave"]["enabled"])

    def test_native_authority_skip_does_not_leak_into_non_intake_forms(self):
        """Only semantic declarations survive the skip; the predicate still guards it."""
        payload = _payload(scene_key="projects.list")
        apply_native_authority_domain_overrides(payload, "user")

        governance = payload.get("form_governance") or {}
        self.assertIsNone(governance.get("create_flow_mode"))
        self.assertIsNone(governance.get("primary_action_label"))
        self.assertNotIn("autosave", payload["views"]["form"])

    def test_non_intake_project_contract_is_not_overridden(self):
        governed = apply_contract_governance(_payload(scene_key="projects.list"), "user")

        governance = governed.get("form_governance") or {}
        self.assertNotEqual(governance.get("surface"), "project_intake")
        self.assertIsNone(governance.get("create_flow_mode"))
        self.assertIsNone(governance.get("post_create_target"))
        self.assertNotIn("autosave", governed["views"]["form"])

    def test_non_create_project_contract_is_not_overridden(self):
        governed = apply_contract_governance(_payload(render_profile="edit"), "user")

        governance = governed.get("form_governance") or {}
        self.assertNotEqual(governance.get("surface"), "project_intake")
        self.assertIsNone(governance.get("create_flow_mode"))
        self.assertIsNone(governance.get("post_create_target"))
        self.assertNotIn("autosave", governed["views"]["form"])

    def test_readonly_effective_field_is_excluded_from_standard_draft(self):
        payload = _payload()
        payload["fields"]["manager_id"]["readonly"] = True

        governed = apply_contract_governance(payload, "user")

        fields = governed["views"]["form"]["autosave"]["fields"]
        self.assertNotIn("manager_id", {row["name"] for row in fields})

    def test_native_xml_readonly_truth_values_exclude_draft_field(self):
        root = etree.fromstring(
            b'<form><field name="owner_id" readonly="1"/></form>'
        )
        raw_readonly = root.xpath('.//field[@name="owner_id"]')[0].get("readonly")

        for value in (True, 1, "1", raw_readonly):
            with self.subTest(value=value):
                payload = _payload()
                payload["views"]["form"]["field_modifiers"] = {
                    "owner_id": {"readonly": value},
                }

                governed = apply_contract_governance(payload, "user")

                fields = governed["views"]["form"]["autosave"]["fields"]
                self.assertNotIn("owner_id", {row["name"] for row in fields})

        sample = _payload()
        sample["views"]["form"]["field_modifiers"] = {
            "owner_id": {"readonly": raw_readonly},
        }
        sample_contract = apply_contract_governance(sample, "user")
        autosave = sample_contract["views"]["form"]["autosave"]
        print(
            "CLOSE03_R1_READONLY_SAMPLE="
            + json.dumps(
                {
                    "source_xml": '<field name="owner_id" readonly="1"/>',
                    "source_modifiers": sample["views"]["form"]["field_modifiers"],
                    "allowed_fields": [row["name"] for row in autosave["fields"]],
                    "owner_id_declared": any(
                        row["name"] == "owner_id" for row in autosave["fields"]
                    ),
                    "autosave_policy": autosave,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )

    def test_native_xml_readonly_false_values_keep_draft_field(self):
        for value in (False, 0, "0"):
            with self.subTest(value=value):
                payload = _payload()
                payload["views"]["form"]["field_modifiers"] = {
                    "owner_id": {"readonly": value},
                }

                governed = apply_contract_governance(payload, "user")

                fields = governed["views"]["form"]["autosave"]["fields"]
                self.assertIn("owner_id", {row["name"] for row in fields})

    def test_dynamic_readonly_expression_uses_current_create_values(self):
        payload = _payload()
        payload["values"] = {"state": "draft"}
        payload["views"]["form"]["field_modifiers"] = {
            "owner_id": {"readonly": "state == 'draft'"},
        }

        governed = apply_contract_governance(payload, "user")

        fields = governed["views"]["form"]["autosave"]["fields"]
        self.assertNotIn("owner_id", {row["name"] for row in fields})

    def test_payment_create_does_not_inherit_project_intake_draft_policy(self):
        payload = _payload(scene_key="payments.payment", menu_xmlid="")
        payload["head"]["model"] = "payment.request"
        payload["model"] = "payment.request"

        governed = apply_contract_governance(payload, "user")

        self.assertNotIn("autosave", governed["views"]["form"])


if __name__ == "__main__":
    unittest.main()
