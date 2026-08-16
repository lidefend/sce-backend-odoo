#!/usr/bin/env python3
from __future__ import annotations

import unittest

from addons.smart_construction_scene.profiles.approval_work_item_business_task_profile import (
    approval_work_item_task_profile_v1,
)
from addons.smart_construction_scene.profiles.settlement_order_business_task_profile import (
    settlement_order_task_profile_v1,
)
from addons.smart_scene.core.business_task_scene_compiler import (
    compile_business_task_scene_contract,
    verify_business_task_scene_contract_seal,
)


def semantic_supply(profile: dict, *, enabled_capability: str, complete: bool = False) -> dict:
    return {
        "task": {"mode": "readonly", "stage": "decision", "state": "pending"},
        "facts": {
            row["key"]: {
                "value": f"value:{row['key']}",
                "value_state": "ready",
                "source_authority": "domain.fact",
                "applicability": "applicable",
            }
            for row in profile["facts"]
        },
        "inputs": {
            row["key"]: {
                "value": "",
                "visible": True,
                "readonly": False,
                "required": row["key"] == "decision_comment",
                "source_authority": "canonical.widget_status",
                "applicability": "applicable",
            }
            for row in profile["inputs"]
        },
        "blockers": {
            row["key"]: {
                "active": False,
                "reason_code": "NOT_BLOCKED",
                "message": "",
                "missing_items": [],
                "source_authority": "domain.precheck",
            }
            for row in profile["blockers"]
        },
        "capabilities": {
            row["key"]: {
                "visible": row["key"] == enabled_capability,
                "business_available": row["key"] == enabled_capability,
                "authorization_allowed": True,
                "enabled": row["key"] == enabled_capability,
                "reason_code": "" if row["key"] == enabled_capability else "STATE_NOT_APPLICABLE",
                "reason": "" if row["key"] == enabled_capability else "当前阶段不适用",
                "source_authority": "canonical.action_contract",
            }
            for row in profile["capabilities"]
        },
        "evidence": {
            row["key"]: {
                "state": "ready",
                "count": 1,
                "required": False,
                "source_authority": "domain.evidence",
            }
            for row in profile["evidence"]
        },
        "relations": {
            row["key"]: {
                "state": "linked",
                "count": 1,
                "summary": f"anchor:{row['key']}",
                "source_authority": "domain.relation",
            }
            for row in profile["relations"]
        },
        "completion": {
            "complete": complete,
            "next_capability_key": "" if complete else enabled_capability,
            "outcome_code": "COMPLETE" if complete else "ACTION_REQUIRED",
        },
    }


class CrossModelBusinessTaskProfileTest(unittest.TestCase):
    def _compile(self, profile: dict, enabled_capability: str) -> dict:
        terminal = compile_business_task_scene_contract(
            profile=profile,
            semantic_supply=semantic_supply(profile, enabled_capability=enabled_capability),
        )
        self.assertTrue(verify_business_task_scene_contract_seal(terminal))
        self.assertEqual(terminal["completion"]["next_capability_key"], enabled_capability)
        self.assertEqual(
            [row["key"] for row in terminal["capabilities"] if row["enabled"]],
            [enabled_capability],
        )
        self.assertNotIn("model", repr(terminal))
        self.assertNotIn("view_type", repr(terminal))
        return terminal

    def test_approval_work_item_uses_same_terminal_language(self):
        terminal = self._compile(
            approval_work_item_task_profile_v1(),
            "approval_work_item.approve",
        )
        self.assertEqual(terminal["task"]["key"], "governance.approval_work_item.process")
        self.assertEqual(
            {row["key"] for row in terminal["relations"]},
            {"source_record", "workflow_instance"},
        )

    def test_settlement_order_uses_same_terminal_language(self):
        terminal = self._compile(
            settlement_order_task_profile_v1(),
            "settlement_order.submit",
        )
        self.assertEqual(terminal["task"]["key"], "contract.settlement_order.process")
        self.assertEqual(
            {row["key"] for row in terminal["blockers"]},
            {"contract_scope_consistency", "amount_readiness"},
        )
        self.assertIn("settlement_order.complete", {row["key"] for row in terminal["capabilities"]})
        self.assertNotIn("settlement_order.confirm", {row["key"] for row in terminal["capabilities"]})

    def test_profiles_do_not_smuggle_payment_specific_renderer_keys(self):
        approval = approval_work_item_task_profile_v1()
        settlement = settlement_order_task_profile_v1()
        self.assertNotEqual(approval["task"]["key"], settlement["task"]["key"])
        self.assertFalse(any("payment_request" in row["key"] for row in approval["capabilities"]))
        self.assertFalse(any("payment_execution" in row["key"] for row in settlement["capabilities"]))


if __name__ == "__main__":
    unittest.main()
