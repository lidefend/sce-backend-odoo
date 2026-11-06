# -*- coding: utf-8 -*-
import sys
from unittest import mock

from odoo.tests import TransactionCase

from odoo.addons.smart_construction_core import core_extension


def _field_node(container_id, name):
    return {
        "containerId": container_id,
        "containerType": "field",
        "type": "field",
        "name": name,
        "children": [],
        "widgetList": [],
    }


def _readiness_contract():
    return {
        "layoutContract": {
            "containerTree": [{
                "containerId": "group.readiness",
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


def _readiness_patch(status="ready", message="当前可提交；提示项及提交时的重新校验仍然适用。"):
    baseline = mock.MagicMock()
    baseline.build_readiness = mock.MagicMock(return_value={
        "status": status,
        "reason_code": "OK" if status == "ready" else "BLOCK",
        "message": message,
        "next_step": {"action": "submit_record", "label": "提交业务记录"},
    })
    patch = mock.patch.dict(sys.modules, {
        "odoo.addons.smart_construction_core.services.baseline_readiness": baseline,
    })
    return baseline, patch


class SubmissionReadinessNoticeP1Tests(TransactionCase):

    def test_notice_injected_for_declared_field(self):
        contract = _readiness_contract()
        core_extension._sc_inject_submission_readiness_notice(
            self.env, contract, {"model": "project.project"},
        )
        readiness = contract["noticeContract"]["submissionReadiness"]
        self.assertEqual(readiness["status"], "no_data")
        self.assertEqual(readiness["statusLabel"], "暂无记录")
        self.assertEqual(readiness["state"], "empty")
        self.assertFalse(contract["layoutContract"]["containerTree"][0]["children"][0]["visible"])
        self.assertEqual(
            contract["layoutContract"]["containerTree"][0]["widgetList"][0]["ownerContainerId"],
            "field.submission_readiness_display.occ.1",
        )

    def test_notice_skipped_without_declared_field(self):
        contract = {
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
        core_extension._sc_inject_submission_readiness_notice(
            self.env, contract, {"model": "project.project"},
        )
        self.assertNotIn("noticeContract", contract)

    def test_notice_skipped_for_unrelated_model(self):
        contract = _readiness_contract()
        core_extension._sc_inject_submission_readiness_notice(
            self.env, contract, {"model": "res.partner"},
        )
        self.assertNotIn("noticeContract", contract)

    def test_notice_maps_ready_status(self):
        baseline, patch = _readiness_patch()
        contract = _readiness_contract()
        with patch:
            core_extension._sc_inject_submission_readiness_notice(
                self.env, contract, {"model": "payment.request"},
            )
        readiness = contract["noticeContract"]["submissionReadiness"]
        self.assertEqual(readiness["status"], "ready")
        self.assertEqual(readiness["statusLabel"], "可提交")
        self.assertEqual(readiness["state"], "success")
        baseline.build_readiness.assert_called_once()

    def test_finalize_hook_injects_notice(self):
        contract = {
            "layoutContract": {
                "containerTree": [{
                    "type": "form",
                    "containerId": "root",
                    "children": [{
                        "type": "group",
                        "containerId": "group.readiness",
                        "title": "办理前检查",
                        "children": [_field_node("field.submission_readiness_display.occ.1", "submission_readiness_display")],
                    }],
                }],
                "componentRegistry": {},
            },
            "statusContract": {"globalStatus": {"pageAuth": "edit"}, "widgetStatus": []},
            "runtimeContract": {},
        }
        projected = core_extension.smart_core_finalize_unified_page_contract_v2(
            self.env,
            contract,
            {"source_contract": {"model": "project.project", "view_type": "form"}},
        )
        self.assertIsInstance(projected, dict)
        self.assertEqual(projected["noticeContract"]["submissionReadiness"]["status"], "no_data")
