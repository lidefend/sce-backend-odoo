# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase

from odoo.addons.smart_core.core.unified_page_contract_v2_assembler import (
    _has_submission_readiness_body_field,
    _suppress_notice_owned_body_fields,
)


def _field_node(container_id: str, name: str) -> dict:
    return {
        "containerId": container_id,
        "containerType": "field",
        "type": "field",
        "name": name,
        "children": [],
        "widgetList": [],
    }


class SubmissionReadinessNoticeSuppressionTests(TransactionCase):

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
        _suppress_notice_owned_body_fields(contract)
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
        _suppress_notice_owned_body_fields(contract)
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
        _suppress_notice_owned_body_fields(contract)
        group = contract["layoutContract"]["containerTree"][0]
        self.assertNotIn("visible", group)
        self.assertNotIn("visible", group["children"][0])

    def test_notice_scope_requires_a_declared_readiness_body_field(self):
        with_field = {
            "layoutContract": {
                "containerTree": [{
                    "containerId": "group.readiness",
                    "containerType": "group",
                    "type": "group",
                    "title": "办理前检查",
                    "children": [_field_node("field.submission_readiness_display.occ.1", "submission_readiness_display")],
                    "widgetList": [],
                }],
            },
        }
        self.assertTrue(_has_submission_readiness_body_field(with_field))
        # The quick-create project form never declares 办理前检查, so it must
        # not receive the page-header notice.
        without_field = {
            "layoutContract": {
                "containerTree": [{
                    "containerId": "group.quick_create",
                    "containerType": "group",
                    "type": "group",
                    "title": "项目创建",
                    "children": [_field_node("field.name.occ.1", "name")],
                    "widgetList": [],
                }],
            },
        }
        self.assertFalse(_has_submission_readiness_body_field(without_field))
