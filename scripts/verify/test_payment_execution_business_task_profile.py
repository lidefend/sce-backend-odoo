#!/usr/bin/env python3
from __future__ import annotations

import copy
import importlib.util
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
SERVICES_PACKAGE = "addons.smart_construction_scene.services"
services_package = types.ModuleType(SERVICES_PACKAGE)
services_package.__path__ = [str(ROOT / "addons" / "smart_construction_scene" / "services")]
sys.modules[SERVICES_PACKAGE] = services_package
MODULE_NAME = f"{SERVICES_PACKAGE}.payment_execution_business_task_projection"
SPEC = importlib.util.spec_from_file_location(
    MODULE_NAME,
    services_package.__path__[0] + "/payment_execution_business_task_projection.py",
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[MODULE_NAME] = MODULE
SPEC.loader.exec_module(MODULE)

project = MODULE.project_payment_execution_business_task_scene
attach = MODULE.attach_payment_execution_business_task_scene


METHODS = {
    "action_confirm": "submit",
    "validate_tier": "approve",
    "reject_tier": "reject",
    "action_paid": "paid",
    "action_cancel": "cancel",
    "action_reverse_payment": "reverse",
}


def action_rule(method: str, *, visible: bool, available: bool, authorized: bool | None, enabled: bool, reason: str = "") -> tuple[dict, dict]:
    key = METHODS[method]
    trace = {"businessAvailable": available, "entitlementEvaluated": authorized is not None}
    if authorized is not None:
        trace["authorizationAllowed"] = authorized
    rule = {
        "actionKey": key,
        "backendIdentity": f"button:object:{method}",
        "button": {"name": method, "type": "object"},
        "visible": visible,
        "enabled": enabled,
        "disabled": not enabled,
        "sourceTrace": [trace],
    }
    status = {
        "btnId": f"btn.{key}",
        "visible": visible,
        "disabled": not enabled,
        "reasonCode": reason,
        "reason": reason,
    }
    return rule, status


def normalized_contract(*, state: str = "draft", validation_status: str = "no", active_method: str = "action_confirm", authorized: bool | None = True) -> dict:
    fields = {
        "name": "FE-EXE-001",
        "execution_flow_label": "付款执行",
        "state": state,
        "validation_status": validation_status,
        "payment_request_id": [11, "FE-PAY-001"],
        "project_id": [12, "FE Project A"],
        "partner_id": [13, "FE 往来单位"],
        "contract_id": [14, "FE 合同"],
        "planned_amount": 80,
        "paid_amount": 80,
        "payment_method": "银行转账",
        "receipt_account_name": "FE 往来单位",
        "receipt_bank_name": "招商银行",
        "receipt_account_no": "****1234",
        "payment_account_name": "FE Company A",
        "payment_bank_name": "建设银行",
        "payment_account_no": "****5678",
        "company_contractor_responsibility_state": "ready",
        "cancellation_kind": False,
        "date_payment": "2026-08-16",
        "note": "合同付款",
        "reversal_reason": "",
        "attachment_ids": [21],
        "review_ids": [22],
    }
    rules = []
    buttons = []
    for method in METHODS:
        active = method == active_method
        rule, status = action_rule(
            method,
            visible=active,
            available=active,
            authorized=authorized if active else True,
            enabled=bool(active and authorized is True),
            reason="" if active and authorized is True else "ROLE_HANDOFF_REQUIRED" if active else "STATE_NOT_APPLICABLE",
        )
        rules.append(rule)
        buttons.append(status)
    widget_status = [
        {"widgetId": f"field.{field}", "visible": True, "readonly": field == "reversal_reason", "required": field in {"paid_amount", "payment_method"}, "disabled": False}
        for field in ("date_payment", "paid_amount", "payment_method", "payment_account_name", "payment_bank_name", "payment_account_no", "note", "reversal_reason")
    ]
    return {
        "pageInfo": {"model": "sc.payment.execution", "viewType": "form", "renderProfile": "edit"},
        "dataContract": {"mainData": fields},
        "actionContract": {"actionRuleList": rules},
        "statusContract": {"buttonStatus": buttons, "widgetStatus": widget_status},
        "runtimeContract": {"existing": {"kept": True}},
    }


def business_task(contract: dict, **kwargs) -> dict:
    scene = project(contract, **kwargs)
    assert scene is not None
    return scene["business_task"]


class PaymentExecutionBusinessTaskProfileTest(unittest.TestCase):
    def test_draft_projects_submit_and_canonical_input_flags(self):
        task = business_task(normalized_contract())
        self.assertEqual(task["task"]["stage"], "preparation")
        self.assertEqual(task["completion"]["next_capability_key"], "payment_execution.submit")
        submit = next(row for row in task["capabilities"] if row["key"] == "payment_execution.submit")
        self.assertTrue(submit["enabled"])
        paid_amount = next(row for row in task["inputs"] if row["key"] == "actual_amount")
        self.assertTrue(paid_amount["visible"])
        self.assertTrue(paid_amount["required"])
        self.assertFalse(paid_amount["readonly"])

    def test_pending_approval_projects_handoff_actions(self):
        task = business_task(normalized_contract(validation_status="pending", active_method="validate_tier"))
        self.assertEqual(task["task"]["stage"], "approval")
        self.assertEqual(task["completion"]["next_capability_key"], "payment_execution.approve")

    def test_confirmed_projects_paid_posting(self):
        task = business_task(normalized_contract(state="confirmed", validation_status="validated", active_method="action_paid"))
        self.assertEqual(task["task"]["stage"], "payment")
        self.assertEqual(task["completion"]["next_capability_key"], "payment_execution.mark_paid")

    def test_paid_is_complete_but_preserves_reversal_capability(self):
        task = business_task(normalized_contract(state="paid", validation_status="validated", active_method="action_reverse_payment"))
        self.assertTrue(task["completion"]["complete"])
        self.assertEqual(task["completion"]["next_capability_key"], "")
        reverse = next(row for row in task["capabilities"] if row["key"] == "payment_execution.reverse")
        self.assertTrue(reverse["enabled"])

    def test_missing_authorization_stays_disabled_without_fallback(self):
        task = business_task(normalized_contract(authorized=None))
        self.assertEqual(task["completion"]["next_capability_key"], "payment_execution.submit")
        submit = next(row for row in task["capabilities"] if row["key"] == "payment_execution.submit")
        self.assertFalse(submit["authorization_allowed"])
        self.assertFalse(submit["enabled"])
        self.assertEqual(submit["reason_code"], "ACTION_PERMISSION_UNRESOLVED")

    def test_missing_widget_authority_is_hidden_and_readonly(self):
        contract = normalized_contract()
        contract["statusContract"]["widgetStatus"] = []
        task = business_task(contract)
        self.assertTrue(all(not row["visible"] and row["readonly"] for row in task["inputs"]))

    def test_wrong_model_and_missing_current_action_fail_closed(self):
        wrong = normalized_contract()
        wrong["pageInfo"]["model"] = "payment.request"
        self.assertIsNone(project(wrong))
        missing = normalized_contract()
        missing["actionContract"]["actionRuleList"] = []
        missing["statusContract"]["buttonStatus"] = []
        self.assertIsNone(project(missing))

    def test_attach_preserves_source_and_sealed_mirrors(self):
        source = normalized_contract(state="confirmed", validation_status="validated", active_method="action_paid")
        frozen = copy.deepcopy(source)
        out = attach(source, render_profile="readonly")
        self.assertIsNotNone(out)
        self.assertEqual(source, frozen)
        runtime = out["runtimeContract"]
        self.assertEqual(runtime["existing"], {"kept": True})
        self.assertEqual(runtime["businessTaskContract"], runtime["businessTaskSceneContract"]["business_task"])
        runtime["businessTaskContract"]["task"]["state"] = "mutated"
        self.assertEqual(runtime["businessTaskSceneContract"]["business_task"]["task"]["state"], "confirmed")


if __name__ == "__main__":
    unittest.main()
