# -*- coding: utf-8 -*-
"""Read-only golden business chain readback (contract -> settlement -> payment
-> ledger -> receipt -> treasury -> reconciliation).

The readback pins the one main demo story so a rebuild cannot silently lose
cross-record amount/state coherence or the role relay. Replay and user-progress
regressions use TransactionCase writes that are rolled back; they never alter
the persistent demo records. The XMLIDs and field names below are the persisted,
already-validated demo fixtures.
"""
from __future__ import annotations

from odoo import fields
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.smart_construction_core.services.project_dashboard_builders.project_finance_builder import (
    ProjectFinanceBuilder,
)
from odoo.addons.smart_construction_core.services.project_dashboard_service import (
    ProjectDashboardService,
)
from odoo.addons.smart_construction_demo.seed.steps.step_20_projects_demo import (
    run as run_projects_demo,
)
from odoo.addons.smart_construction_demo.seed.steps.step_40_contracts_demo import (
    DEMO01_FIXED_PAYMENT_NOTE,
    _ensure_actionable_payment_draft,
    _ensure_complete_payment_request,
    _ensure_payments,
    _fixed_demo01_payment_request,
    run as run_contracts_demo,
)
from odoo.addons.smart_construction_demo.seed.steps.step_demo_business_chain import (
    run as run_demo_business_chain,
)
from odoo.addons.smart_construction_demo.tools.scenario_loader import (
    _bind_generated_demo_xmlid,
    _demo_drive_approval,
    _generated_demo_model_data,
)


@tagged("post_install", "-at_install", "-standard", "demo_golden_chain")
class TestDemoGoldenChain(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if not cls.env.ref(
            "smart_construction_demo.sc_demo_exec_expense_contract",
            raise_if_not_found=False,
        ):
            run_projects_demo(cls.env)
            run_contracts_demo(cls.env)
            run_demo_business_chain(cls.env)

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
        self.assertGreaterEqual(float(finance_block["data"]["summary"]["paid"]), 160000.0)
        dashboard = ProjectDashboardService(finance_env).build(project_id=project.id)
        self.assertGreaterEqual(
            float(dashboard["project"]["payment_executed_total"]), 160000.0
        )
        self.assertGreaterEqual(int(dashboard["project"]["payment_executed_record_count"]), 1)
        self.assertIn(
            "payment.ledger#%s" % ledger.id,
            dashboard["project"]["evidence_refs"],
        )

    def test_demo01_user_approval_does_not_rewrite_fixed_showcase_evidence(self):
        project = self.env.ref("smart_construction_demo.sc_demo_project")
        contract = self.env.ref("smart_construction_demo.sc_demo_exec_expense_contract")
        settlement = self.env.ref("smart_construction_demo.sc_demo_exec_settlement")
        fixed_ledger = self.env.ref("smart_construction_demo.sc_demo_exec_payment_ledger")
        finance_user = self.env.ref("smart_construction_demo.user_sc_fin_mgr_01")
        submitter = self.env.ref("smart_construction_demo.user_demo_role_project_a_member")
        finance_env = self.env(
            user=finance_user,
            context={
                **self.env.context,
                "allowed_company_ids": [project.company_id.id],
            },
        )
        project_for_finance = project.with_user(finance_user).sudo(False)

        def finance_snapshot():
            block = ProjectFinanceBuilder(finance_env).build(project=project_for_finance)
            dashboard = ProjectDashboardService(finance_env).build(project_id=project.id)
            return (
                float(block["data"]["summary"]["paid"]),
                float(dashboard["project"]["payment_executed_total"]),
                int(dashboard["project"]["payment_executed_record_count"]),
                dashboard["project"]["evidence_refs"],
            )

        paid_before, executed_before, count_before, refs_before = finance_snapshot()
        self.assertGreaterEqual(paid_before, fixed_ledger.amount)
        self.assertGreaterEqual(executed_before, fixed_ledger.amount)
        self.assertGreaterEqual(count_before, 1)
        self.assertIn("payment.ledger#%s" % fixed_ledger.id, refs_before)

        Payment = self.env["payment.request"].with_user(submitter).sudo(False)
        extra = Payment.create(
            {
                "type": "pay",
                "project_id": project.id,
                "partner_id": contract.partner_id.id,
                "contract_id": contract.id,
                "settlement_id": settlement.id,
                "amount": 120000.0,
                "date_request": fields.Date.context_today(submitter),
                "note": "DEMO-01 Golden approved-progress regression",
            }
        )
        _demo_drive_approval(self.env, extra)
        extra.invalidate_recordset()
        self.assertIn(extra.state, ("approved", "done"))

        paid_after, executed_after, count_after, refs_after = finance_snapshot()
        self.assertAlmostEqual(paid_after, paid_before + extra.amount)
        self.assertGreaterEqual(executed_after, fixed_ledger.amount)
        self.assertGreaterEqual(count_after, 1)
        self.assertIn("payment.ledger#%s" % fixed_ledger.id, refs_after)

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
        state_before = draft.state
        amount_before = draft.amount

        replayed = _ensure_actionable_payment_draft(
            self.env, project, contract, settlement
        )
        self.assertEqual(replayed.id, draft_id)
        replayed.invalidate_recordset()
        self.assertEqual(replayed.state, state_before)
        self.assertAlmostEqual(replayed.amount, amount_before)

    def test_demo01_full_replay_isolated_from_user_modified_draft(self):
        project = self.env.ref("smart_construction_demo.sc_demo_project")
        expense_contract = self.env.ref(
            "smart_construction_demo.sc_demo_exec_expense_contract"
        )
        income_contract = self.env.ref(
            "smart_construction_demo.sc_demo_exec_income_contract"
        )
        settlement = self.env.ref("smart_construction_demo.sc_demo_exec_settlement")
        fixed_request = self.env.ref(
            "smart_construction_demo.sc_demo_exec_payment_request"
        )
        draft = self.env.ref(
            "smart_construction_demo.sc_demo_exec_actionable_payment_draft"
        )
        draft_id = draft.id
        draft_state_before = draft.state
        draft_amount_before = draft.amount
        request_ids_before = set(
            self.env["payment.request"]
            .sudo()
            .search([("project_id", "=", project.id)])
            .ids
        )
        submitter = self.env.ref(
            "smart_construction_demo.user_demo_role_project_a_member"
        )
        collision = (
            self.env["payment.request"]
            .with_user(submitter)
            .sudo(False)
            .create(
                {
                    "type": "pay",
                    "project_id": project.id,
                    "partner_id": expense_contract.partner_id.id,
                    "contract_id": expense_contract.id,
                    "settlement_id": settlement.id,
                    "amount": 160000.0,
                    "note": "DEMO-01 replay collision test",
                }
            )
        )
        request_ids_before.add(collision.id)

        pay, _receive = _ensure_payments(
            self.env,
            project,
            expense_contract,
            income_contract,
            settlement,
        )
        self.assertEqual(pay, fixed_request)
        self.assertNotEqual(pay, draft)

        run_demo_business_chain(self.env)
        request_ids_after = set(
            self.env["payment.request"]
            .sudo()
            .search([("project_id", "=", project.id)])
            .ids
        )
        self.assertEqual(request_ids_after, request_ids_before)
        draft.invalidate_recordset()
        self.assertEqual(draft.id, draft_id)
        self.assertEqual(draft.state, draft_state_before)
        self.assertAlmostEqual(draft.amount, draft_amount_before)


@tagged("post_install", "-at_install", "-standard", "demo_golden_chain")
class TestDemoGoldenChainLegacyUpgrade(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Emulate a pre-DEMO-01 database before the contract seed resolves
        # candidates: no generated payment identity is bound yet.
        for name in (
            "sc_demo_exec_payment_request",
            "sc_demo_exec_payment_execution",
            "sc_demo_exec_payment_ledger",
        ):
            xmlid = cls.env["ir.model.data"].sudo().search(
                [
                    ("module", "=", "smart_construction_demo"),
                    ("name", "=", name),
                ],
                limit=1,
            )
            if xmlid:
                xmlid.unlink()
        cls.env["ir.model.data"].flush_model()
        cls.env["ir.model.data"].invalidate_model()
        cls.env.registry.clear_all_caches()
        cls.env.clear()
        cls.env.cr.execute(
            "SELECT res_id FROM ir_model_data "
            "WHERE module = %s AND name = %s",
            ("smart_construction_demo", "sc_demo_exec_payment_request"),
        )
        if cls.env.cr.fetchone():
            raise AssertionError("legacy fixture XMLID deletion did not persist")

        project = cls.env["project.project"].sudo().search(
            [("project_code", "=", "DEMO-PJ-EXEC")],
            limit=2,
        )
        if not project:
            run_projects_demo(cls.env)
        run_contracts_demo(cls.env)
        cls.env.cr.execute(
            "SELECT res_id FROM ir_model_data "
            "WHERE module = %s AND name = %s",
            ("smart_construction_demo", "sc_demo_exec_payment_request"),
        )
        if cls.env.cr.fetchone():
            raise AssertionError("contracts seed rebound the legacy payment XMLID")
        project = cls.env["project.project"].sudo().search(
            [("project_code", "=", "DEMO-PJ-EXEC")],
            limit=2,
        )
        if len(project) != 1:
            raise AssertionError("DEMO-01 project must be unique")
        contract_data = _generated_demo_model_data(
            cls.env, "sc_demo_exec_expense_contract"
        )
        contract = (
            cls.env[contract_data.model].browse(contract_data.res_id)
            if contract_data
            else cls.env["construction.contract"].sudo().search(
                [
                    ("project_id", "=", project.id),
                    ("type", "=", "in"),
                ],
                limit=2,
            )
        )
        if len(contract) != 1:
            raise AssertionError("DEMO-01 expense contract must be unique")
        settlement_data = _generated_demo_model_data(
            cls.env, "sc_demo_exec_settlement"
        )
        settlement = (
            cls.env[settlement_data.model].browse(settlement_data.res_id)
            if settlement_data
            else cls.env["sc.settlement.order"].sudo().search(
                [
                    ("project_id", "=", project.id),
                    ("contract_id", "=", contract.id),
                    ("state", "!=", "cancel"),
                ],
                limit=2,
            )
        )
        if len(settlement) != 1:
            raise AssertionError("DEMO-01 settlement must be unique")

        prior = cls.env["payment.request"].sudo().search(
            [("note", "=", DEMO01_FIXED_PAYMENT_NOTE)]
        )
        if prior:
            # Terminal business facts intentionally reject note rewrites. This
            # transaction-only fixture adjustment recreates the pre-upgrade
            # database shape; all new approval/repair steps still use public
            # model actions below.
            cls.env.cr.execute(
                "UPDATE payment_request SET note = %s WHERE id IN %s",
                ("DEMO-01 legacy full-chain payment (unbound)", tuple(prior.ids)),
            )
            prior.invalidate_recordset(["note"])

        submitter = cls.env.ref(
            "smart_construction_demo.user_demo_role_project_a_member"
        )
        Payment = cls.env["payment.request"].with_user(submitter).sudo(False)
        legacy = Payment.create(
            {
                "type": "pay",
                "project_id": project.id,
                "partner_id": contract.partner_id.id,
                "contract_id": contract.id,
                "settlement_id": settlement.id,
                "amount": 160000.0,
                "date_request": fields.Date.context_today(submitter),
                "note": DEMO01_FIXED_PAYMENT_NOTE,
            }
        )
        legacy.write(
            {
                "actual_payee_unit": False,
                "payment_account_name": False,
                "payment_bank_name": False,
                "payment_account_no": False,
            }
        )
        legacy.invalidate_recordset()
        if legacy.payee_account_completeness != "incomplete":
            raise AssertionError("legacy DEMO-01 payment must have an incomplete account")
        _demo_drive_approval(cls.env, legacy)
        legacy.invalidate_recordset()
        if legacy.state != "approved":
            raise AssertionError("legacy DEMO-01 payment must reach approved")
        cls.legacy_payment = legacy
        cls.project = project
        cls.contract = contract
        cls.settlement = settlement

    def test_contracts_then_business_chain_repairs_unbound_legacy_payment(self):
        self.assertEqual(self.legacy_payment.state, "approved")
        self.assertEqual(self.legacy_payment.payee_account_completeness, "incomplete")
        legacy_request = _fixed_demo01_payment_request(
            self.env,
            self.project,
            self.contract,
            self.settlement,
        )
        self.assertEqual(legacy_request, self.legacy_payment)

        repaired = _ensure_complete_payment_request(
            self.env, legacy_request
        )
        self.legacy_payment.invalidate_recordset()
        repaired.invalidate_recordset()
        self.assertNotEqual(repaired, self.legacy_payment)
        self.assertEqual(self.legacy_payment.state, "cancel")
        self.assertEqual(repaired.note, DEMO01_FIXED_PAYMENT_NOTE)
        self.assertIn(repaired.state, ("approved", "done"))
        self.assertEqual(repaired.payee_account_completeness, "complete")
        self.assertTrue(repaired.payment_account_name)
        self.assertTrue(repaired.payment_bank_name)
        self.assertTrue(repaired.payment_account_no)
        self.assertEqual(repaired.project_id, self.project)
        self.assertEqual(repaired.contract_id, self.contract)
        self.assertEqual(repaired.settlement_id, self.settlement)
        self.assertEqual(repaired.type, "pay")

        _bind_generated_demo_xmlid(
            self.env, "sc_demo_exec_payment_request", repaired
        )
        run_demo_business_chain(self.env)

        fixed_data = _generated_demo_model_data(
            self.env, "sc_demo_exec_payment_request"
        )
        fixed = self.env[fixed_data.model].browse(fixed_data.res_id)
        self.assertEqual(fixed, repaired)
        self.assertTrue(
            self.env.ref(
                "smart_construction_demo.sc_demo_exec_payment_execution"
            )
        )
        self.assertTrue(
            self.env.ref(
                "smart_construction_demo.sc_demo_exec_payment_ledger"
            )
        )
