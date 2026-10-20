# -*- coding: utf-8 -*-
"""Read-only golden business chain readback (contract -> settlement -> payment
-> ledger -> receipt -> treasury -> reconciliation).

This test never writes. It pins the one main demo story so a rebuild cannot
silently lose cross-record amount/state coherence or the role relay. The XMLIDs
and field names below are the persisted, already-validated demo fixtures.
"""
from __future__ import annotations

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "-standard", "demo_golden_chain")
class TestDemoGoldenChain(TransactionCase):
    def test_golden_chain_amount_state_and_role_relay(self):
        settlement = self.env.ref("smart_construction_demo.sc_demo_settlement_069_payment")
        request = self.env.ref("smart_construction_demo.sc_demo_payment_request_069_pay")

        self.assertIn(settlement.state, ("approve", "done"))
        self.assertTrue(settlement.project_id)
        self.assertTrue(settlement.contract_id)
        self.assertTrue(settlement.purchase_order_ids)
        self.assertTrue(request.amount > 0)
        self.assertTrue(request.date_request)

        ledger = self.env["payment.ledger"].search(
            [("payment_request_id", "=", request.id), ("state", "=", "posted")]
        )
        self.assertEqual(len(ledger), 1)
        self.assertAlmostEqual(ledger.amount, 120000)
        self.assertEqual(ledger.payment_execution_id.state, "paid")
        self.assertEqual(ledger.payment_execution_id.payment_request_id, request)

        receipt = self.env.ref("smart_construction_demo.sc_demo_receipt_income_070_progress")
        self.assertEqual(receipt.state, "received")
        treasury = receipt.treasury_ledger_id
        self.assertEqual(treasury.state, "posted")
        self.assertEqual(treasury.direction, "in")
        self.assertAlmostEqual(treasury.amount, 1200000)
        self.assertEqual(treasury.payment_request_id, receipt.payment_request_id)

        reconciliation = self.env.ref(
            "smart_construction_demo.sc_demo_treasury_reconciliation_070_daily"
        )
        self.assertEqual(reconciliation.treasury_ledger_id, treasury)
        self.assertEqual(reconciliation.state, "confirmed")

        pending = self.env.ref("smart_construction_demo.sc_demo_pay_req_010_001")
        self.assertEqual(pending.state, "draft")
        self.assertAlmostEqual(pending.amount, 5000000)

        actor = self.env.ref("smart_construction_demo.user_sc_settlement_user_cap")
        self.assertTrue(
            settlement.with_user(actor).sudo(False).search_count([("id", "=", settlement.id)])
        )
