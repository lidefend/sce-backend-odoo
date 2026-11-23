#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = (
    ROOT / "addons" / "smart_core" / "core" / "page_block_action_contract.py"
)
SPEC = importlib.util.spec_from_file_location(
    "page_block_action_contract",
    MODULE_PATH,
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def action(**overrides):
    values = {
        "actionKey": "open_project",
        "label": "打开项目",
        "intent": "ui.contract",
        "target": {
            "type": "action",
            "action_xmlid": "smart_construction_core.action_sc_project_list",
        },
        "sourceWidgetId": "block.projects",
        "visible": True,
        "authorizationAllowed": True,
        "businessAvailable": True,
        "permissionEvaluated": True,
    }
    values.update(overrides)
    return values


class PageBlockActionContractTest(unittest.TestCase):
    def test_visible_allowed_action_projects_one_action_rule_and_carrier(self):
        result = MODULE.build_page_block_action_contract([action()])
        rule = result["action_contract"]["actionRuleList"][0]
        carrier = result["action_schema"]["actions"][rule["actionId"]]
        self.assertEqual(carrier["actionRuleRef"], rule["actionId"])
        self.assertEqual(carrier["target"]["value"], rule["target"])
        self.assertTrue(carrier["permission"]["allowed"])
        self.assertTrue(carrier["state"]["enabled"])
        self.assertFalse(carrier["state"]["disabled"])
        self.assertNotIn("authorizationSubject", str(result))

    def test_authorization_denial_is_visible_disabled_with_declared_reason(self):
        result = MODULE.build_page_block_action_contract([
            action(
                authorizationAllowed=False,
                reasonCode="ACTION_NOT_AUTHORIZED",
                reasonMessage="当前角色无权执行该动作",
            )
        ])
        carrier = next(iter(result["action_schema"]["actions"].values()))
        self.assertFalse(carrier["permission"]["allowed"])
        self.assertFalse(carrier["state"]["enabled"])
        self.assertEqual(carrier["state"]["reasonCode"], "ACTION_NOT_AUTHORIZED")

    def test_business_unavailability_is_visible_disabled_with_declared_reason(self):
        result = MODULE.build_page_block_action_contract([
            action(
                businessAvailable=False,
                reasonCode="ACTION_NOT_BUSINESS_AVAILABLE",
                reasonMessage="当前业务状态不允许该动作",
            )
        ])
        carrier = next(iter(result["action_schema"]["actions"].values()))
        self.assertTrue(carrier["permission"]["authorizationAllowed"])
        self.assertFalse(carrier["permission"]["businessAvailable"])
        self.assertFalse(carrier["permission"]["allowed"])
        self.assertFalse(carrier["state"]["enabled"])

    def test_missing_permission_evaluation_fails_closed(self):
        values = action()
        values.pop("permissionEvaluated")
        with self.assertRaisesRegex(
            MODULE.PageBlockActionContractError,
            "fully evaluated",
        ):
            MODULE.build_page_block_action_contract([values])

    def test_missing_target_fails_closed(self):
        with self.assertRaisesRegex(
            MODULE.PageBlockActionContractError,
            "target is required",
        ):
            MODULE.build_page_block_action_contract([action(target={})])

    def test_visible_unavailable_action_requires_reason(self):
        with self.assertRaisesRegex(
            MODULE.PageBlockActionContractError,
            "requires reasonCode",
        ):
            MODULE.build_page_block_action_contract([
                action(authorizationAllowed=False)
            ])

    def test_server_authorization_identity_is_never_public(self):
        with self.assertRaisesRegex(
            MODULE.PageBlockActionContractError,
            "authorization identity",
        ):
            MODULE.build_page_block_action_contract([
                action(authorizationSubject={"model": "project.project", "recordId": 1})
            ])

    def test_hidden_action_remains_non_executable(self):
        result = MODULE.build_page_block_action_contract([
            action(
                visible=False,
                authorizationAllowed=False,
                reasonCode="",
                reasonMessage="",
            )
        ])
        carrier = next(iter(result["action_schema"]["actions"].values()))
        self.assertFalse(carrier["visibility"]["visible"])
        self.assertFalse(carrier["state"]["enabled"])

    def test_feedback_preserves_action_reason_message_and_trace(self):
        feedback = MODULE.build_action_feedback(
            action_id="action.open_project",
            status="denied",
            reason_code="ACTION_NOT_AUTHORIZED",
            message="当前角色无权执行该动作",
            trace_id="trace-p0c",
        )
        self.assertEqual(feedback["actionId"], "action.open_project")
        self.assertEqual(feedback["status"], "denied")
        self.assertEqual(feedback["reasonCode"], "ACTION_NOT_AUTHORIZED")
        self.assertEqual(feedback["traceId"], "trace-p0c")

    def test_success_feedback_keeps_action_and_trace_identity(self):
        feedback = MODULE.build_action_feedback(
            action_id="action.open_project",
            status="success",
            reason_code="",
            message="",
            trace_id="trace-p0c-success",
        )
        self.assertEqual(feedback["status"], "success")
        self.assertEqual(feedback["actionId"], "action.open_project")
        self.assertEqual(feedback["traceId"], "trace-p0c-success")

    def test_failed_feedback_requires_reason_and_message(self):
        with self.assertRaisesRegex(
            MODULE.PageBlockActionContractError,
            "requires reasonCode and message",
        ):
            MODULE.build_action_feedback(
                action_id="action.open_project",
                status="failed",
                reason_code="",
                message="",
                trace_id="trace-p0c-failed",
            )

    def test_feedback_missing_trace_fails_closed(self):
        with self.assertRaisesRegex(
            MODULE.PageBlockActionContractError,
            "requires actionId and traceId",
        ):
            MODULE.build_action_feedback(
                action_id="action.open_project",
                status="success",
                reason_code="",
                message="",
                trace_id="",
            )

    def test_real_failure_envelope_classifies_denied_and_keeps_identity(self):
        feedback = MODULE.build_action_feedback_from_result(
            {
                "ok": False,
                "code": 403,
                "error": {
                    "code": "PERMISSION_DENIED",
                    "reason_code": "PERMISSION_DENIED",
                    "message": "当前角色无权执行该动作",
                },
                "data": {
                    "result": {
                        "status": "failure",
                        "reason_code": "PERMISSION_DENIED",
                        "message": "当前角色无权执行该动作",
                    }
                },
                "meta": {"trace_id": "trace-real-denied"},
            },
            action_id="action.open_project",
            trace_id="trace-real-denied",
        )
        self.assertEqual(feedback["status"], "denied")
        self.assertEqual(feedback["reasonCode"], "PERMISSION_DENIED")
        self.assertEqual(feedback["message"], "当前角色无权执行该动作")
        self.assertEqual(feedback["traceId"], "trace-real-denied")

    def test_real_success_envelope_keeps_action_identity(self):
        feedback = MODULE.build_action_feedback_from_result(
            {
                "ok": True,
                "data": {"result": {"status": "success"}},
                "meta": {"trace_id": "trace-real-success"},
            },
            action_id="action.open_project",
            trace_id="trace-real-success",
        )
        self.assertEqual(feedback["status"], "success")
        self.assertEqual(feedback["actionId"], "action.open_project")
        self.assertEqual(feedback["traceId"], "trace-real-success")


if __name__ == "__main__":
    unittest.main()
