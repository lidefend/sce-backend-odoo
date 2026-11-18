#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROBE_PATH = ROOT / "scripts/verify/be_close_01_workflow_contract_http_probe.py"
SPEC = importlib.util.spec_from_file_location("be_close_01_workflow_contract_http_probe", PROBE_PATH)
assert SPEC and SPEC.loader
PROBE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROBE)


class BEClose01WorkflowContractProbeTest(unittest.TestCase):
    def test_action_summary_separates_enabled_and_denied_authority(self) -> None:
        contract = {
            "availableActions": [
                {
                    "key": "done",
                    "enabled": False,
                    "reason_code": "PAYMENT_EXECUTION_REQUIRED",
                    "blocked_message": "专业付款登记尚未完成。",
                },
                {
                    "key": "cancel",
                    "enabled": True,
                    "reason_code": "OK",
                    "blocked_message": "",
                },
            ]
        }
        summary = PROBE._action_summary(contract)
        self.assertEqual(summary["allowed_action_keys"], ["cancel"])
        self.assertEqual(summary["disabled_action_keys"], ["done"])
        self.assertEqual(
            summary["denial_reasons"]["done"]["reasonCode"],
            "PAYMENT_EXECUTION_REQUIRED",
        )
        self.assertTrue(summary["denial_reasons"]["done"]["message"])

    def test_action_rule_requires_one_identity(self) -> None:
        rule = {
            "actionId": "rule.submit",
            "backendIdentity": "payment.submit",
            "sourceWidgetId": "workflow.contract",
            "button": {"name": "action_submit", "type": "object"},
            "allowed": True,
            "enabled": True,
            "disabled": False,
            "entitlementEvaluated": True,
        }
        data = {"actionContract": {"actionRuleList": [rule]}}
        self.assertEqual(PROBE._action_rule(data, "action_submit"), rule)

    def test_create_request_never_sends_record_identity(self) -> None:
        entry = {
            "model": "payment.request",
            "action_id": 7,
            "menu_id": 9,
        }
        request = PROBE._create_request(entry)
        self.assertEqual(request["op"], "model")
        self.assertNotIn("record_id", request)


if __name__ == "__main__":
    unittest.main()
