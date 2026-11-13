# -*- coding: utf-8 -*-
"""Read-only golden business chain readback (contract -> settlement -> payment
-> ledger -> receipt -> treasury -> reconciliation).

This test never writes. It pins the one main demo story so a rebuild cannot
silently lose cross-record amount/state coherence or the role relay. The XMLIDs
and field names below are the persisted, already-validated demo fixtures.
"""
from __future__ import annotations

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.smart_construction_core.services.project_dashboard_builders.project_finance_builder import (
    ProjectFinanceBuilder,
)
from odoo.addons.smart_construction_demo.seed.steps.step_40_contracts_demo import (
    _ensure_actionable_payment_draft,
)
from odoo.addons.smart_construction_demo.tools.scenario_loader import (
    _demo_drive_approval,
)


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

    def test_demo01_exec_project_chain_and_project_summary(self):
        project = self.env.ref("smart_construction_demo.sc_demo_project")
        expense_contract = self.env.ref(
            "smart_construction_demo.sc_demo_exec_expense_contract"
        )
        settlement = self.env.ref("smart_construction_demo.sc_demo_exec_settlement")
        request = self.env.ref("smart_construction_demo.sc_demo_exec_payment_request")
        execution = self.env.ref(
            "smart_construction_demo.sc_demo_exec_payment_execution"
        )
        ledger = self.env.ref("smart_construction_demo.sc_demo_exec_payment_ledger")
        draft = self.env.ref(
            "smart_construction_demo.sc_demo_exec_actionable_payment_draft"
        )

        self.assertEqual(project.project_code, "DEMO-PJ-EXEC")
        self.assertEqual(project.start_date.isoformat(), "2026-10-19")
        self.assertEqual(project.end_date.isoformat(), "2027-10-18")
        self.assertTrue(project.description)

        self.assertEqual(expense_contract.type, "in")
        self.assertEqual(expense_contract.project_id, project)
        self.assertAlmostEqual(expense_contract.amount_total, 452000.0)
        self.assertAlmostEqual(
            sum(expense_contract.line_ids.mapped("price_contract")), 400000.0
        )
        self.assertEqual(settlement.project_id, project)
        self.assertEqual(settlement.contract_id, expense_contract)
        self.assertEqual(settlement.state, "approve")
        self.assertAlmostEqual(settlement.amount_total, 400000.0)
        self.assertTrue(settlement.purchase_order_ids)

        self.assertEqual(request.project_id, project)
        self.assertEqual(request.contract_id, expense_contract)
        self.assertEqual(request.settlement_id, settlement)
        self.assertEqual(request.state, "done")
        self.assertAlmostEqual(request.amount, 160000.0)
        self.assertEqual(request.payee_account_completeness, "complete")
        self.assertEqual(
            request.payment_account_name, request.partner_id.name
        )
        self.assertTrue(request.payment_bank_name)
        self.assertTrue(request.payment_account_no)

        self.assertEqual(execution.payment_request_id, request)
        self.assertEqual(execution.project_id, project)
        self.assertEqual(execution.state, "paid")
        self.assertAlmostEqual(execution.paid_amount, 160000.0)
        self.assertEqual(ledger.payment_request_id, request)
        self.assertEqual(ledger.payment_execution_id, execution)
        self.assertEqual(ledger.project_id, project)
        self.assertEqual(ledger.state, "posted")
        self.assertAlmostEqual(ledger.amount, 160000.0)

        self.assertEqual(draft.project_id, project)
        self.assertEqual(draft.contract_id, expense_contract)
        self.assertEqual(draft.settlement_id, settlement)
        self.assertEqual(draft.type, "pay")
        self.assertEqual(draft.state, "draft")
        self.assertAlmostEqual(draft.amount, 120000.0)

        finance_user = self.env.ref(
            "smart_construction_demo.user_sc_fin_mgr_01"
        )
        finance_env = self.env(
            user=finance_user,
            context={
                **self.env.context,
                "allowed_company_ids": [project.company_id.id],
            },
        )
        finance_block = ProjectFinanceBuilder(finance_env).build(
            project=project.with_user(finance_user).sudo(False)
        )
        self.assertEqual(finance_block["state"], "ready")
        self.assertAlmostEqual(
            finance_block["data"]["summary"]["paid"], 160000.0
        )

    def test_demo01_actionable_draft_replay_preserves_user_progress(self):
        project = self.env.ref("smart_construction_demo.sc_demo_project")
        contract = self.env.ref(
            "smart_construction_demo.sc_demo_exec_expense_contract"
        )
        settlement = self.env.ref("smart_construction_demo.sc_demo_exec_settlement")
        draft = self.env.ref(
            "smart_construction_demo.sc_demo_exec_actionable_payment_draft"
        )
        draft_id = draft.id

        _demo_drive_approval(self.env, draft)
        draft.invalidate_recordset()
        self.assertEqual(draft.state, "approved")

        replayed = _ensure_actionable_payment_draft(
            self.env, project, contract, settlement
        )
        self.assertEqual(replayed.id, draft_id)
        replayed.invalidate_recordset()
        self.assertEqual(replayed.state, "approved")
