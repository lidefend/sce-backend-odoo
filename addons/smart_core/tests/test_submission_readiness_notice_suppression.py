# -*- coding: utf-8 -*-
import sys
from unittest import mock

from odoo.tests import TransactionCase

from odoo.addons.smart_core.core.unified_page_contract_v2_assembler import (
    _inject_submission_readiness_notice,
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


def _readiness_patch():
    """Provide a governed readiness projection without installing P1 modules."""
    baseline = mock.MagicMock()
    baseline.build_readiness = mock.MagicMock(return_value={
        "status": "ready",
        "reason_code": "OK",
        "message": "当前可提交；提示项及提交时的重新校验仍然适用。",
        "next_step": {"action": "submit_record", "label": "提交业务记录"},
    })
    services = mock.MagicMock()
    services.baseline_readiness = baseline
    core = mock.MagicMock()
    core.services = services
    patch = mock.patch.dict(sys.modules, {
        "odoo.addons.smart_construction_core": core,
        "odoo.addons.smart_construction_core.services": services,
        "odoo.addons.smart_construction_core.services.baseline_readiness": baseline,
    })
    return baseline, patch


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
        source = {"model": "project.project"}
        baseline, patch = _readiness_patch()
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
        with patch:
            # The quick-create project form never declares 办理前检查, so it
            # must not receive the page-header notice, and the readiness
            # service must never be invoked.
            _inject_submission_readiness_notice(without_field, source, self.env)
            self.assertNotIn("noticeContract", without_field)
            baseline.build_readiness.assert_not_called()

            # A view that declares the field must produce exactly one notice.
            _inject_submission_readiness_notice(with_field, source, self.env)
        self.assertIn("noticeContract", with_field)
        readiness = with_field["noticeContract"]["submissionReadiness"]
        self.assertTrue(readiness["visible"])
        self.assertEqual(readiness["status"], "ready")
        self.assertFalse(with_field["layoutContract"]["containerTree"][0]["children"][0]["visible"])
        baseline.build_readiness.assert_called_once()

    def test_notice_respects_native_hidden_visibility(self):
        source = {"model": "project.project"}
        baseline, patch = _readiness_patch()
        readiness = _field_node("field.submission_readiness_display.occ.1", "submission_readiness_display")

        # Field itself hidden.
        field_hidden = {
            "layoutContract": {
                "containerTree": [{
                    "containerId": "group.readiness",
                    "containerType": "group",
                    "type": "group",
                    "title": "办理前检查",
                    "children": [{**readiness, "invisible": True}],
                    "widgetList": [],
                }],
            },
        }
        # Parent group hidden.
        group_hidden = {
            "layoutContract": {
                "containerTree": [{
                    "containerId": "group.readiness",
                    "containerType": "group",
                    "type": "group",
                    "title": "办理前检查",
                    "invisible": True,
                    "children": [dict(readiness)],
                    "widgetList": [],
                }],
            },
        }
        with patch:
            _inject_submission_readiness_notice(field_hidden, source, self.env)
            _inject_submission_readiness_notice(group_hidden, source, self.env)
        self.assertNotIn("noticeContract", field_hidden)
        self.assertNotIn("noticeContract", group_hidden)
        baseline.build_readiness.assert_not_called()
