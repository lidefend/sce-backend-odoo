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
MODULE_NAME = f"{SERVICES_PACKAGE}.settlement_order_business_task_projection"
SPEC = importlib.util.spec_from_file_location(
    MODULE_NAME,
    services_package.__path__[0] + "/settlement_order_business_task_projection.py",
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[MODULE_NAME] = MODULE
SPEC.loader.exec_module(MODULE)

project = MODULE.project_settlement_order_business_task_scene
attach = MODULE.attach_settlement_order_business_task_scene


METHODS = {
    "action_submit": "submit",
    "validate_tier": "tier_approve",
    "action_approve": "record_approve",
    "reject_tier": "reject",
    "action_done": "complete",
    "action_cancel": "cancel",
}


def action_rule(
    method: str,
    *,
    visible: bool,
    available: bool,
    authorized: bool | None,
    enabled: bool,
    reason: str = "",
) -> tuple[dict, dict]:
    key = METHODS[method]
    trace = {"businessAvailable": available, "entitlementEvaluated": authorized is not None}
    if authorized is not None:
        trace["authorizationAllowed"] = authorized
    return (
        {
            "actionKey": key,
            "backendIdentity": f"button:object:{method}",
            "button": {"name": method, "type": "object"},
            "visible": visible,
            "enabled": enabled,
            "disabled": not enabled,
            "sourceTrace": [trace],
        },
        {
            "btnId": f"btn.{key}",
            "visible": visible,
            "disabled": not enabled,
            "reasonCode": reason,
            "reason": reason,
        },
    )


def normalized_contract(
    *,
    state: str = "draft",
    validation_status: str = "no",
    active_method: str = "action_submit",
    authorized: bool | None = True,
) -> dict:
    rules = []
    statuses = []
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
        statuses.append(status)
    fields = {
        "name": "FE-SET-001",
        "state": state,
        "validation_status": validation_status,
        "project_id": [11, "FE Project A"],
        "contract_id": [12, "FE Contract A"],
        "partner_id": [13, "FE Counterparty A"],
        "line_ids": [21],
        "amount_total": 100.0,
        "submitted_amount": 100.0,
        "approved_amount": 0.0 if state in {"draft", "submit"} else 100.0,
        "amount_paid": 0.0,
        "amount_payable": 100.0,
        "date_settlement": "2026-08-16",
        "settlement_description": "合同结算",
        "attachment_ids": [],
        "review_ids": [31] if validation_status not in {"", "no"} else [],
        "payment_request_ids": [],
        "compliance_state": "ready",
    }
    widget_status = [
        {
            "widgetId": f"field.{field}",
            "visible": True,
            "readonly": False,
            "required": field in {"date_settlement", "submitted_amount"},
            "disabled": False,
        }
        for field in (
            "date_settlement", "submitted_amount", "approved_amount", "settlement_description",
            "project_id", "partner_id", "contract_id", "general_contract_id", "line_ids",
        )
    ]
    return {
        "pageInfo": {"model": "sc.settlement.order", "viewType": "form", "renderProfile": "edit"},
        "dataContract": {"mainData": fields},
        "actionContract": {"actionRuleList": rules},
        "statusContract": {
            "globalStatus": {"pageAuth": "edit"},
            "buttonStatus": statuses,
            "widgetStatus": widget_status,
        },
        "runtimeContract": {
            "existing": {"kept": True},
            "businessTaskSemantics": {
                "version": "v1",
                "source_authority": "settlement_order_model_prechecks",
                "blockers": {
                    "contract_scope_consistency": {
                        "active": False,
                        "reason_code": "",
                        "message": "",
                        "missing_items": [],
                        "repair_field_names": [],
                        "source_authority": "settlement_order_model_prechecks.scope",
                    },
                    "amount_readiness": {
                        "active": False,
                        "reason_code": "",
                        "message": "",
                        "missing_items": [],
                        "repair_field_names": [],
                        "source_authority": "settlement_order_model_prechecks.amount",
                    },
                },
            },
        },
    }


def business_task(contract: dict) -> dict:
    scene = project(contract)
    assert scene is not None
    return scene["business_task"]


class SettlementOrderBusinessTaskProfileTest(unittest.TestCase):
    def test_draft_uses_model_precheck_without_inventing_approved_amount_gate(self):
        task = business_task(normalized_contract())
        self.assertEqual(task["completion"]["next_capability_key"], "settlement_order.submit")
        self.assertFalse(next(row for row in task["blockers"] if row["key"] == "amount_readiness")["active"])
        self.assertTrue(next(row for row in task["capabilities"] if row["key"] == "settlement_order.submit")["enabled"])

    def test_pending_tier_action_wins_over_hidden_record_approval_alias(self):
        contract = normalized_contract(
            state="submit", validation_status="pending", active_method="validate_tier"
        )
        task = business_task(contract)
        approval = next(row for row in task["capabilities"] if row["key"] == "settlement_order.approve")
        self.assertTrue(approval["enabled"])
        self.assertEqual(task["completion"]["next_capability_key"], "settlement_order.approve")

    def test_record_approval_and_completion_follow_real_methods(self):
        approved = business_task(normalized_contract(
            state="submit", validation_status="validated", active_method="action_approve"
        ))
        self.assertEqual(approved["completion"]["next_capability_key"], "settlement_order.approve")
        complete = business_task(normalized_contract(
            state="approve", validation_status="validated", active_method="action_done"
        ))
        self.assertEqual(complete["completion"]["next_capability_key"], "settlement_order.complete")

    def test_handoff_stays_visible_disabled_and_does_not_fallback(self):
        task = business_task(normalized_contract(authorized=False))
        submit = next(row for row in task["capabilities"] if row["key"] == "settlement_order.submit")
        self.assertTrue(submit["visible"])
        self.assertFalse(submit["authorization_allowed"])
        self.assertFalse(submit["enabled"])
        self.assertEqual(submit["reason_code"], "ROLE_HANDOFF_REQUIRED")
        self.assertEqual(task["completion"]["next_capability_key"], "settlement_order.submit")

    def test_missing_scope_projects_repair_without_relaxing_page_authority(self):
        contract = normalized_contract()
        contract["dataContract"]["mainData"]["partner_id"] = False
        scope = contract["runtimeContract"]["businessTaskSemantics"]["blockers"]["contract_scope_consistency"]
        scope.update({
            "active": True,
            "reason_code": "SETTLEMENT_SCOPE_INCOMPLETE",
            "message": "缺少往来单位。",
            "missing_items": ["往来单位"],
            "repair_field_names": ["partner_id"],
        })
        contract["statusContract"]["globalStatus"]["pageAuth"] = "readonly"
        task = business_task(contract)
        blocker = next(row for row in task["blockers"] if row["key"] == "contract_scope_consistency")
        repair = next(row for row in task["capabilities"] if row["key"] == "settlement_order.repair_scope")
        self.assertTrue(blocker["active"])
        self.assertTrue(repair["visible"])
        self.assertFalse(repair["enabled"])
        self.assertEqual(task["completion"]["next_capability_key"], "settlement_order.repair_scope")

    def test_scope_repair_requires_the_exact_widget_authority(self):
        contract = normalized_contract()
        scope = contract["runtimeContract"]["businessTaskSemantics"]["blockers"]["contract_scope_consistency"]
        scope.update({
            "active": True,
            "reason_code": "SETTLEMENT_SCOPE_INCOMPLETE",
            "message": "缺少往来单位。",
            "missing_items": ["往来单位"],
            "repair_field_names": ["partner_id"],
        })
        task = business_task(contract)
        repair = next(row for row in task["capabilities"] if row["key"] == "settlement_order.repair_scope")
        self.assertTrue(repair["enabled"])
        partner_status = next(
            row for row in contract["statusContract"]["widgetStatus"]
            if row["widgetId"] == "field.partner_id"
        )
        partner_status["readonly"] = True
        task = business_task(contract)
        repair = next(row for row in task["capabilities"] if row["key"] == "settlement_order.repair_scope")
        self.assertFalse(repair["enabled"])

    def test_missing_domain_semantics_fails_closed(self):
        contract = normalized_contract()
        del contract["runtimeContract"]["businessTaskSemantics"]
        self.assertIsNone(project(contract))
        malformed = normalized_contract()
        del malformed["runtimeContract"]["businessTaskSemantics"]["blockers"]["amount_readiness"]["repair_field_names"]
        self.assertIsNone(project(malformed))

    def test_conflicting_visible_aliases_fail_closed(self):
        contract = normalized_contract(
            state="submit", validation_status="pending", active_method="validate_tier"
        )
        record_rule, record_status = action_rule(
            "action_approve", visible=True, available=True, authorized=False, enabled=False,
            reason="ROLE_HANDOFF_REQUIRED",
        )
        contract["actionContract"]["actionRuleList"] = [
            row for row in contract["actionContract"]["actionRuleList"]
            if row["button"]["name"] != "action_approve"
        ] + [record_rule]
        contract["statusContract"]["buttonStatus"] = [
            row for row in contract["statusContract"]["buttonStatus"]
            if row["btnId"] != "btn.record_approve"
        ] + [record_status]
        task = business_task(contract)
        approval = next(row for row in task["capabilities"] if row["key"] == "settlement_order.approve")
        self.assertFalse(approval["enabled"])
        self.assertEqual(approval["reason_code"], "ACTION_CAPABILITY_AMBIGUOUS")

    def test_attach_preserves_source_and_isolates_terminal_mirrors(self):
        source = normalized_contract()
        frozen = copy.deepcopy(source)
        out = attach(source, render_profile="readonly")
        self.assertIsNotNone(out)
        self.assertEqual(source, frozen)
        runtime = out["runtimeContract"]
        self.assertEqual(runtime["existing"], {"kept": True})
        self.assertEqual(runtime["businessTaskContract"], runtime["businessTaskSceneContract"]["business_task"])
        runtime["businessTaskContract"]["task"]["state"] = "mutated"
        self.assertEqual(runtime["businessTaskSceneContract"]["business_task"]["task"]["state"], "draft")


if __name__ == "__main__":
    unittest.main()
