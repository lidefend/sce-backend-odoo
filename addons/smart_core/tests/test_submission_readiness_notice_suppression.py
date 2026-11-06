# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path


CORE_DIR = Path(__file__).resolve().parents[1] / "core"


def _load_assembler():
    sys.modules.setdefault("odoo", types.ModuleType("odoo"))
    sys.modules.setdefault("odoo.addons", types.ModuleType("odoo.addons"))
    smart_core_pkg = sys.modules.setdefault("odoo.addons.smart_core", types.ModuleType("odoo.addons.smart_core"))
    smart_core_pkg.__path__ = [str(CORE_DIR.parent)]
    core_pkg = sys.modules.setdefault("odoo.addons.smart_core.core", types.ModuleType("odoo.addons.smart_core.core"))
    core_pkg.__path__ = [str(CORE_DIR)]
    for module_name in (
        "odoo.addons.smart_core.core.source_authority",
        "odoo.addons.smart_core.core.unified_page_contract_v2_assembler",
    ):
        sys.modules.pop(module_name, None)
    source_spec = importlib.util.spec_from_file_location(
        "odoo.addons.smart_core.core.source_authority",
        CORE_DIR / "source_authority.py",
    )
    source_module = importlib.util.module_from_spec(source_spec)
    assert source_spec and source_spec.loader
    sys.modules["odoo.addons.smart_core.core.source_authority"] = source_module
    source_spec.loader.exec_module(source_module)
    spec = importlib.util.spec_from_file_location(
        "odoo.addons.smart_core.core.unified_page_contract_v2_assembler",
        CORE_DIR / "unified_page_contract_v2_assembler.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules["odoo.addons.smart_core.core.unified_page_contract_v2_assembler"] = module
    spec.loader.exec_module(module)
    return module


def _field_node(container_id: str, name: str) -> dict:
    return {
        "containerId": container_id,
        "containerType": "field",
        "type": "field",
        "name": name,
        "children": [],
        "widgetList": [],
    }


class SubmissionReadinessNoticeSuppressionTests(unittest.TestCase):
    def setUp(self):
        self.assembler = _load_assembler()

    def test_single_field_group_is_suppressed_without_orphaning_widgets(self):
        contract = {
            "layoutContract": {
                "containerTree": [{
                    "containerId": "group.sc_project_submission_readiness",
                    "containerType": "group",
                    "type": "group",
                    "title": "办理前检查",
                    "children": [_field_node("field.submission_readiness_display.occ.1", "submission_readiness_display")],
                    "widgetList": [{
                        "widgetId": "field.submission_readiness_display.occ.1",
                        "fieldCode": "submission_readiness_display",
                        "ownerContainerId": "field.submission_readiness_display.occ.1",
                    }],
                }],
            },
        }
        self.assembler._suppress_notice_owned_body_fields(contract)
        group = contract["layoutContract"]["containerTree"][0]
        field = group["children"][0]
        self.assertFalse(group["visible"])
        self.assertFalse(field["visible"])
        self.assertEqual(len(group["children"]), 1, "field node must not be deleted")
        self.assertEqual(len(group["widgetList"]), 1, "parent widgetList must keep its binding")
        self.assertEqual(group["widgetList"][0]["ownerContainerId"], field["containerId"])

    def test_mixed_group_keeps_other_fields_visible(self):
        contract = {
            "layoutContract": {
                "containerTree": [{
                    "containerId": "group.project_create_required",
                    "containerType": "group",
                    "type": "group",
                    "title": "项目创建（必填）",
                    "children": [
                        _field_node("field.submission_readiness_display.occ.1", "submission_readiness_display"),
                        _field_node("field.name.occ.1", "name"),
                    ],
                    "widgetList": [],
                }],
            },
        }
        self.assembler._suppress_notice_owned_body_fields(contract)
        group = contract["layoutContract"]["containerTree"][0]
        self.assertNotIn("visible", group, "a group with other content must keep its own visibility")
        by_name = {child["name"]: child for child in group["children"]}
        self.assertFalse(by_name["submission_readiness_display"]["visible"])
        self.assertNotIn("visible", by_name["name"], "unrelated fields must stay visible")

    def test_other_field_names_are_untouched(self):
        contract = {
            "layoutContract": {
                "containerTree": [{
                    "containerId": "group.other",
                    "containerType": "group",
                    "type": "group",
                    "title": "其他",
                    "children": [_field_node("field.name.occ.1", "name")],
                    "widgetList": [],
                }],
            },
        }
        self.assembler._suppress_notice_owned_body_fields(contract)
        group = contract["layoutContract"]["containerTree"][0]
        self.assertNotIn("visible", group)
        self.assertNotIn("visible", group["children"][0])


if __name__ == "__main__":
    unittest.main()
