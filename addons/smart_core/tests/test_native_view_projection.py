# -*- coding: utf-8 -*-
from __future__ import annotations

import unittest

from lxml import etree

from odoo.addons.smart_core.core.native_view_projection import (
    NativeView,
    build_native_form_structure_contract,
    derive_native_field_ownership,
    project_native_view,
)


class _FakeModel:
    def __init__(self, arch, fields):
        self._arch = arch
        self._fields = fields

    def get_view(self, view_id=False, view_type="form"):
        return {"arch": self._arch, "id": 1776, "model": "project.project"}

    def fields_get(self):
        return self._fields


class _FakeEnv(dict):
    @property
    def context(self):
        return {"lang": "zh_CN", "tz": "Asia/Shanghai", "contract_action_id": 590}


ARCH = """<form string="Project">
  <sheet>
    <group name="sc_project_information_identity" string="项目身份">
      <field name="name" string="项目名称"/>
      <field name="project_code" readonly="1"/>
    </group>
    <group string="未命名">
      <field name="name"/>
    </group>
    <field name="reject_reason" invisible="not reject_reason"/>
  </sheet>
</form>"""


class TestNativeViewProjection(unittest.TestCase):
    def setUp(self):
        self.env = _FakeEnv()
        self.env["project.project"] = _FakeModel(
            ARCH,
            {
                "name": {"type": "char", "string": "名称", "required": True},
                "project_code": {"type": "char", "string": "项目编号"},
                "reject_reason": {"type": "text", "string": "驳回原因", "readonly": True},
            },
        )

    def test_projects_containers_and_fields_once(self):
        view = project_native_view(self.env, "project.project", action_id=590, view_id=1776)
        self.assertIsInstance(view, NativeView)
        self.assertEqual(len(view.containers), 1)
        form = view.containers[0]
        self.assertEqual(form.native_type, "form")
        self.assertEqual(form.container_ref, "form")
        self.assertEqual(len(form.children), 1)
        sheet = form.children[0]
        self.assertEqual(sheet.native_type, "sheet")
        self.assertEqual(len(sheet.children), 2)

    def test_native_group_name_is_stable_identity(self):
        view = project_native_view(self.env, "project.project", action_id=590, view_id=1776)
        names = {
            item.container_ref
            for item in view.containers[0].children[0].children
        }
        self.assertIn("sc_project_information_identity", names)
        unnamed = [
            item.container_ref
            for item in view.containers[0].children[0].children
            if not item.native_name
        ]
        self.assertTrue(unnamed)
        self.assertIn("group[2]", unnamed[0])

    def test_duplicate_field_keeps_occurrences(self):
        view = project_native_view(self.env, "project.project", action_id=590, view_id=1776)
        name_occurrences = [f for f in view.fields if f.field_code == "name"]
        self.assertEqual(len(name_occurrences), 2)
        self.assertEqual([f.occurrence_index for f in name_occurrences], [1, 2])

    def test_modifiers_projected_raw(self):
        view = project_native_view(self.env, "project.project", action_id=590, view_id=1776)
        reject = next(f for f in view.fields if f.field_code == "reject_reason")
        self.assertEqual(reject.modifiers_raw.get("invisible"), "not reject_reason")
        code = next(f for f in view.fields if f.field_code == "project_code")
        self.assertEqual(code.modifiers_raw.get("readonly"), "1")

    def test_field_metadata_projected(self):
        view = project_native_view(self.env, "project.project", action_id=590, view_id=1776)
        name = next(f for f in view.fields if f.field_code == "name")
        self.assertEqual(name.field_metadata.get("type"), "char")
        self.assertEqual(name.field_metadata.get("string"), "名称")

    def test_to_dict_serializable(self):
        view = project_native_view(self.env, "project.project", action_id=590, view_id=1776)
        payload = view.to_dict()
        self.assertEqual(payload["identity"]["model"], "project.project")
        self.assertGreaterEqual(len(payload["fields"]), 3)

    def test_derive_ownership_from_native_position(self):
        view = project_native_view(self.env, "project.project", action_id=590, view_id=1776)
        ownership = derive_native_field_ownership(view, identity_fields=["name"])
        # name first occurrence is in the identity group and wins primary ownership
        self.assertEqual(
            ownership["field:name"]["ownerGroupRef"],
            "group:sc_project_information_identity",
        )
        self.assertNotIn("role", ownership["field:name"])
        # project_code is in the same identity group
        self.assertEqual(
            ownership["field:project_code"]["ownerGroupRef"],
            "group:sc_project_information_identity",
        )
        # reject_reason is sheet-level (not in a named group), so it is a
        # summary projection rather than a primary business owner
        self.assertNotIn("field:reject_reason", ownership)

    def test_build_form_structure_contract_from_native(self):
        view = project_native_view(self.env, "project.project", action_id=590, view_id=1776)
        contract = build_native_form_structure_contract(
            view,
            model="project.project",
            identity_fields=["name"],
            navigation_title="项目台账",
        )
        self.assertEqual(contract["structureAuthority"], "native_form_slots")
        self.assertEqual(len(contract["slots"]), 1)
        slot = contract["slots"][0]
        group_names = {group["name"] for group in slot["groups"]}
        self.assertIn("sc_project_information_identity", group_names)
        identity_group = next(
            group for group in slot["groups"] if group["name"] == "sc_project_information_identity"
        )
        self.assertIn("name", identity_group["fieldRefs"])
        self.assertEqual(contract["fieldRoles"]["name"]["role"], "context")
        self.assertEqual(
            contract["fieldOwnership"]["field:name"]["ownerGroupRef"],
            "group:sc_project_information_identity",
        )

    def test_many2one_field_inherits_group_role_not_type_role(self):
        model = _FakeModel(
            """<form string="Project">
              <sheet>
                <group name="sc_project_information_responsible" string="责任信息">
                  <field name="manager_id" string="项目经理"/>
                </group>
              </sheet>
            </form>""",
            {
                "manager_id": {"type": "many2one", "string": "项目经理", "relation": "res.users"},
            },
        )
        env = _FakeEnv()
        env["project.project"] = model
        view = project_native_view(env, "project.project", action_id=590, view_id=1776)
        contract = build_native_form_structure_contract(
            view,
            model="project.project",
            identity_fields=[],
            navigation_title="项目台账",
        )
        self.assertEqual(
            contract["fieldRoles"]["manager_id"]["role"],
            "context",
        )
        self.assertEqual(
            contract["fieldRoles"]["manager_id"]["group"],
            "sc_project_information_responsible",
        )

    def test_duplicate_field_in_multiple_named_groups_is_not_auto_owned(self):
        model = _FakeModel(
            """<form string="Project">
              <sheet>
                <group name="first_group" string="第一组">
                  <field name="partner_id" string="客户"/>
                </group>
                <group name="second_group" string="第二组">
                  <field name="partner_id" string="客户摘要"/>
                </group>
              </sheet>
            </form>""",
            {
                "partner_id": {"type": "many2one", "string": "客户", "relation": "res.partner"},
            },
        )
        env = _FakeEnv()
        env["project.project"] = model
        view = project_native_view(env, "project.project", action_id=590, view_id=1776)
        ownership = derive_native_field_ownership(view, identity_fields=[])
        self.assertNotIn("field:partner_id", ownership)

    def test_layout_tags_are_containers_and_nested_groups_are_projected(self):
        model = _FakeModel(
            """<form string="Project">
              <sheet>
                <div class="oe_title">
                  <h1>项目标题</h1>
                </div>
                <notebook>
                  <page name="main_page" string="主要信息">
                    <group name="nested_group" string="嵌套分组">
                      <field name="name" string="项目名称"/>
                    </group>
                  </page>
                </notebook>
              </sheet>
            </form>""",
            {
                "name": {"type": "char", "string": "项目名称"},
            },
        )
        env = _FakeEnv()
        env["project.project"] = model
        view = project_native_view(env, "project.project", action_id=590, view_id=1776)
        container_types = set()

        def collect(node):
            container_types.add(node.native_type)
            for child in node.children:
                collect(child)

        for root in view.containers:
            collect(root)
        self.assertIn("div", container_types)
        self.assertIn("notebook", container_types)
        contract = build_native_form_structure_contract(
            view,
            model="project.project",
            identity_fields=[],
            navigation_title="项目台账",
        )
        nested_group_names = {
            group["name"]
            for slot in contract["slots"]
            for group in slot["groups"]
        }
        self.assertIn("nested_group", nested_group_names)
        self.assertEqual(contract["fieldRoles"]["name"]["group"], "nested_group")

    def test_native_attributes_are_kept_and_serializable(self):
        model = _FakeModel(
            """<form string="Project">
              <sheet>
                <div class="oe_title" colspan="2">
                  <group name="facts" string="事实" col="2">
                    <field name="name" string="项目名称" widget="char" placeholder="输入名称"/>
                  </group>
                </div>
              </sheet>
            </form>""",
            {"name": {"type": "char", "string": "项目名称"}},
        )
        env = _FakeEnv()
        env["project.project"] = model
        view = project_native_view(env, "project.project", action_id=590, view_id=1776)
        payload = view.to_dict()

        def find_container(native_type):
            stack = list(payload["containers"])
            while stack:
                row = stack.pop()
                if row["native_type"] == native_type:
                    return row
                stack.extend(row.get("children", []))
            return None

        self.assertEqual(find_container("div")["native_attributes"]["class"], "oe_title")
        self.assertEqual(find_container("div")["native_attributes"]["colspan"], "2")
        name_field = next(f for f in payload["fields"] if f["field_code"] == "name")
        self.assertEqual(name_field["native_attributes"]["widget"], "char")
        self.assertEqual(name_field["native_attributes"]["placeholder"], "输入名称")
        import json
        json.dumps(payload)

    def test_relation_descriptor_from_field_metadata_not_type_guess(self):
        model = _FakeModel(
            """<form string="Project">
              <sheet>
                <group name="relations" string="关系">
                  <field name="partner_id"/>
                  <field name="responsibility_ids"/>
                  <field name="tag_ids"/>
                  <field name="name"/>
                </group>
              </sheet>
            </form>""",
            {
                "partner_id": {"type": "many2one", "string": "客户", "relation": "res.partner"},
                "responsibility_ids": {"type": "one2many", "string": "责任矩阵", "relation": "sc.project.responsibility"},
                "tag_ids": {"type": "many2many", "string": "标签", "relation": "sc.project.tag"},
                "name": {"type": "char", "string": "项目名称"},
            },
        )
        env = _FakeEnv()
        env["project.project"] = model
        view = project_native_view(env, "project.project", action_id=590, view_id=1776)
        by_code = {f.field_code: f for f in view.fields}
        self.assertEqual(
            by_code["partner_id"].relation_descriptor,
            {"field_type": "many2one", "relation_type": "many2one", "relation_model": "res.partner"},
        )
        self.assertEqual(
            by_code["responsibility_ids"].relation_descriptor["relation_model"],
            "sc.project.responsibility",
        )
        self.assertEqual(
            by_code["tag_ids"].relation_descriptor["relation_type"],
            "many2many",
        )
        self.assertIsNone(by_code["name"].relation_descriptor)

    def test_internal_attributes_do_not_leak_into_form_structure(self):
        model = _FakeModel(
            """<form string="Project">
              <sheet>
                <group name="facts" string="事实">
                  <field name="manager_id" widget="many2one"/>
                </group>
              </sheet>
            </form>""",
            {"manager_id": {"type": "many2one", "string": "项目经理", "relation": "res.users"}},
        )
        env = _FakeEnv()
        env["project.project"] = model
        view = project_native_view(env, "project.project", action_id=590, view_id=1776)
        contract = build_native_form_structure_contract(
            view,
            model="project.project",
            identity_fields=[],
            navigation_title="项目台账",
        )
        for slot in contract["slots"]:
            self.assertNotIn("native_attributes", slot)
            for group in slot.get("groups", []):
                self.assertNotIn("native_attributes", group)
        role = contract["fieldRoles"]["manager_id"]
        self.assertNotIn("relation_descriptor", role)
        self.assertNotIn("native_attributes", role)


if __name__ == "__main__":
    unittest.main()
