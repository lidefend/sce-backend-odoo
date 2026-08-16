#!/usr/bin/env python3
from __future__ import annotations

import unittest

from addons.smart_construction_core.services.settlement_business_actions import (
    build_settlement_form_actions,
    build_settlement_task_semantics,
)


class FakeUser:
    def __init__(self, groups=()):
        self.groups = set(groups)

    def has_group(self, xmlid):
        return xmlid in self.groups


class FakeEnv:
    def __init__(self, groups=()):
        self.user = FakeUser(groups)


class FakeSettlement:
    _name = "sc.settlement.order"

    def __init__(self, *, state="draft", validation_status="no", groups=(), can_review=False, precheck_error="", cancel_error="", amount_total=100):
        self.state = state
        self.validation_status = validation_status
        self.env = FakeEnv(groups)
        self.can_review = can_review
        self.precheck_error = precheck_error
        self.cancel_error = cancel_error
        self.amount_total = amount_total
        self.project_id = 11
        self.partner_id = 12
        self.legacy_fact_model = ""
        self.line_ids = [13]

    def _check_business_anchor_or_raise(self):
        if self.precheck_error:
            raise ValueError(self.precheck_error)

    def _check_line_contracts_or_raise(self):
        return None

    def _check_contract_consistency_or_raise(self, *, strict):
        return strict

    def _check_purchase_orders_or_raise(self, *, strict):
        return strict

    def _check_payments_before_cancel(self):
        if self.cancel_error:
            raise ValueError(self.cancel_error)


SETTLEMENT_USER = "smart_construction_core.group_sc_cap_settlement_user"
SETTLEMENT_MANAGER = "smart_construction_core.group_sc_cap_settlement_manager"


class SettlementBusinessActionsTest(unittest.TestCase):
    def test_draft_submit_uses_explicit_capability_verdict(self):
        rows = build_settlement_form_actions(FakeSettlement(groups={SETTLEMENT_USER}))
        submit = next(row for row in rows if row["action_key"] == "submit")
        self.assertTrue(submit["business_available"])
        self.assertTrue(submit["authorization_allowed"])
        self.assertTrue(submit["enabled"])
        self.assertTrue(submit["primary"])

    def test_readonly_role_sees_handoff_but_cannot_submit(self):
        rows = build_settlement_form_actions(FakeSettlement())
        submit = next(row for row in rows if row["action_key"] == "submit")
        self.assertTrue(submit["business_available"])
        self.assertFalse(submit["authorization_allowed"])
        self.assertFalse(submit["enabled"])
        self.assertEqual(submit["reason_code"], "ROLE_HANDOFF_REQUIRED")

    def test_pending_review_requires_manager_and_oca_review_verdict(self):
        denied = build_settlement_form_actions(FakeSettlement(
            state="submit", validation_status="pending", groups={SETTLEMENT_MANAGER}, can_review=False,
        ))
        self.assertTrue(all(not row["enabled"] for row in denied if row["action_key"] in {"approve", "reject"}))
        allowed = build_settlement_form_actions(FakeSettlement(
            state="submit", validation_status="pending", groups={SETTLEMENT_MANAGER}, can_review=True,
        ))
        self.assertTrue(next(row for row in allowed if row["action_key"] == "approve")["enabled"])
        self.assertTrue(next(row for row in allowed if row["action_key"] == "reject")["enabled"])

    def test_validated_and_approved_states_follow_real_model_transitions(self):
        validated = build_settlement_form_actions(FakeSettlement(
            state="submit", validation_status="validated", groups={SETTLEMENT_MANAGER},
        ))
        self.assertEqual(next(row for row in validated if row["primary"])["method"], "action_approve")
        approved = build_settlement_form_actions(FakeSettlement(
            state="approve", validation_status="validated", groups={SETTLEMENT_MANAGER},
        ))
        self.assertEqual(next(row for row in approved if row["primary"])["method"], "action_done")

    def test_business_precheck_and_payment_cancel_fail_closed(self):
        rows = build_settlement_form_actions(FakeSettlement(
            groups={SETTLEMENT_USER, SETTLEMENT_MANAGER},
            precheck_error="missing lines",
            cancel_error="payment exists",
        ))
        submit = next(row for row in rows if row["action_key"] == "submit")
        cancel = next(row for row in rows if row["action_key"] == "cancel")
        self.assertFalse(submit["business_available"])
        self.assertFalse(submit["enabled"])
        self.assertEqual(submit["reason_code"], "SETTLEMENT_FACTS_INCOMPLETE")
        self.assertFalse(cancel["business_available"])
        self.assertFalse(cancel["enabled"])
        self.assertEqual(cancel["reason_code"], "SETTLEMENT_PAYMENT_EXISTS")

    def test_task_semantics_materialize_model_owned_blockers(self):
        semantics = build_settlement_task_semantics(FakeSettlement(amount_total=0))
        self.assertEqual(semantics["version"], "v1")
        self.assertFalse(semantics["blockers"]["contract_scope_consistency"]["active"])
        self.assertTrue(semantics["blockers"]["amount_readiness"]["active"])
        self.assertEqual(
            semantics["blockers"]["amount_readiness"]["source_authority"],
            "settlement_order_model_prechecks.amount",
        )
        self.assertEqual(
            semantics["blockers"]["amount_readiness"]["repair_field_names"],
            ["line_ids"],
        )

    def test_scope_semantics_name_only_the_exact_editable_gap(self):
        record = FakeSettlement()
        record.partner_id = False
        semantics = build_settlement_task_semantics(record)
        scope = semantics["blockers"]["contract_scope_consistency"]
        self.assertTrue(scope["active"])
        self.assertEqual(scope["missing_items"], ["往来单位"])
        self.assertEqual(scope["repair_field_names"], ["partner_id"])


if __name__ == "__main__":
    unittest.main()
