#!/usr/bin/env python3
from __future__ import annotations

import copy
import unittest

from scripts.verify import test_payment_execution_business_task_profile as execution_fixture
from scripts.verify import test_payment_request_business_task_profile as request_fixture


def facts(task: dict) -> dict:
    return {row["key"]: row.get("value") for row in task["facts"]}


def relations(task: dict) -> dict:
    return {row["key"]: row for row in task["relations"]}


def capabilities(task: dict) -> dict:
    return {row["key"]: row for row in task["capabilities"]}


class PaymentBusinessTaskJourneySimulationTest(unittest.TestCase):
    def test_request_to_execution_preserves_business_anchors(self):
        request_scene = request_fixture.attach_payment_request_business_task_scene(
            request_fixture.normalized_payment_contract(authorization_allowed=True)
        )
        execution_scene = execution_fixture.attach(
            execution_fixture.normalized_contract(), render_profile="edit"
        )
        request_task = request_scene["runtimeContract"]["businessTaskContract"]
        execution_task = execution_scene["runtimeContract"]["businessTaskContract"]
        self.assertEqual(request_task["completion"]["next_capability_key"], "payment_execution.create")
        self.assertEqual(execution_task["completion"]["next_capability_key"], "payment_execution.submit")
        self.assertEqual(relations(request_task)["project_anchor"]["summary"], relations(execution_task)["project_anchor"]["summary"])
        self.assertEqual(relations(request_task)["payee_anchor"]["summary"], relations(execution_task)["payee_anchor"]["summary"])
        self.assertEqual(relations(request_task)["contract_anchor"]["summary"], relations(execution_task)["contract_anchor"]["summary"])
        self.assertEqual(relations(execution_task)["request_anchor"]["summary"], "FE-PAY-001")

    def test_role_handoff_changes_only_capability_verdicts(self):
        denied_contract = execution_fixture.normalized_contract(
            validation_status="pending", active_method="validate_tier", authorized=False
        )
        allowed_contract = execution_fixture.normalized_contract(
            validation_status="pending", active_method="validate_tier", authorized=True
        )
        denied = execution_fixture.business_task(denied_contract)
        allowed = execution_fixture.business_task(allowed_contract)
        self.assertEqual(facts(denied), facts(allowed))
        self.assertEqual(relations(denied), relations(allowed))
        self.assertFalse(capabilities(denied)["payment_execution.approve"]["enabled"])
        self.assertEqual(capabilities(denied)["payment_execution.approve"]["reason_code"], "ROLE_HANDOFF_REQUIRED")
        self.assertTrue(capabilities(allowed)["payment_execution.approve"]["enabled"])
        self.assertEqual(denied["completion"]["next_capability_key"], "payment_execution.approve")
        self.assertEqual(allowed["completion"]["next_capability_key"], "payment_execution.approve")

    def test_submit_approval_payment_and_terminal_snapshots_are_deterministic(self):
        snapshots = (
            execution_fixture.normalized_contract(),
            execution_fixture.normalized_contract(validation_status="pending", active_method="validate_tier"),
            execution_fixture.normalized_contract(state="confirmed", validation_status="validated", active_method="action_paid"),
            execution_fixture.normalized_contract(state="paid", validation_status="validated", active_method="action_reverse_payment"),
        )
        expected = (
            "payment_execution.submit",
            "payment_execution.approve",
            "payment_execution.mark_paid",
            "",
        )
        for contract, next_key in zip(snapshots, expected):
            first = execution_fixture.project(copy.deepcopy(contract))
            second = execution_fixture.project(copy.deepcopy(contract))
            self.assertEqual(first, second)
            task = first["business_task"]
            self.assertEqual(task["completion"]["next_capability_key"], next_key)
            self.assertEqual(len(task["trace"]["sealed_contract_sha256"]), 64)
        self.assertTrue(execution_fixture.project(snapshots[-1])["business_task"]["completion"]["complete"])


if __name__ == "__main__":
    unittest.main()
