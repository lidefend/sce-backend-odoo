# -*- coding: utf-8 -*-
from __future__ import annotations

import unittest

from lxml import etree

from odoo.addons.smart_core.core.native_view_projection import (
    NativeView,
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
        self.assertEqual(ownership["field:name"]["role"], "identity")
        # project_code is in the same identity group
        self.assertEqual(
            ownership["field:project_code"]["ownerGroupRef"],
            "group:sc_project_information_identity",
        )
        # reject_reason is sheet-level, not in any group
        self.assertEqual(
            ownership["field:reject_reason"]["ownerGroupRef"],
            "group:form/sheet[1]",
        )


if __name__ == "__main__":
    unittest.main()
