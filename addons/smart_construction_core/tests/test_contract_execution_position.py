# -*- coding: utf-8 -*-
import ast

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged

from ..models.support import operating_metrics as opm


@tagged("post_install", "-at_install", "p1_contract_execution_position")
class TestContractExecutionPosition(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.currency = cls.company.currency_id
        cls.partner = cls.env["res.partner"].create({"name": "Position Counterparty"})
        cls.project = cls.env["project.project"].create(
            {"name": "Position Project", "company_id": cls.company.id}
        )
        cls.tax = cls.env["account.tax"].search(
            [("company_id", "=", cls.company.id), ("type_tax_use", "=", "sale")], limit=1
        )
        if not cls.tax:
            cls.tax = cls.env["account.tax"].create(
                {
                    "name": "Position Zero Tax",
                    "amount": 0.0,
                    "amount_type": "percent",
                    "type_tax_use": "sale",
                    "company_id": cls.company.id,
                }
            )

    def _contract(self, name, amount=0.0, contract_type="out", currency=None):
        currency = currency or self.currency
        contract = self.env["construction.contract"].create(
            {
                "subject": name,
                "type": contract_type,
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "company_id": self.company.id,
                "currency_id": currency.id,
                "tax_id": self.tax.id,
            }
        )
        if amount:
            self.env["construction.contract.line"].create(
                {"contract_id": contract.id, "qty_contract": 1.0, "price_contract": amount}
            )
        contract.invalidate_recordset()
        return contract

    def _approved_payment_request(self, name, contract, amount):
        request = self.env["payment.request"].create(
            {
                "name": name,
                "type": "pay",
                "project_id": contract.project_id.id,
                "partner_id": contract.partner_id.id,
                "currency_id": contract.currency_id.id,
                "contract_id": contract.id,
                "amount": amount,
            }
        )
        self.env.cr.execute(
            "UPDATE payment_request SET state='approved', validation_status='validated' WHERE id=%s",
            (request.id,),
        )
        request.invalidate_recordset()
        return request

    def _posted_receipt_evidence(self, name, contract, amount):
        request = self.env["payment.request"].create(
            {
                "name": name,
                "type": "receive",
                "project_id": contract.project_id.id,
                "partner_id": contract.partner_id.id,
                "currency_id": contract.currency_id.id,
                "contract_id": contract.id,
                "amount": amount,
            }
        )
        receipt = self.env["sc.receipt.income"].create(
            {
                "name": name + " receipt",
                "project_id": contract.project_id.id,
                "partner_id": contract.partner_id.id,
                "contract_id": contract.id,
                "payment_request_id": request.id,
                "currency_id": contract.currency_id.id,
                "amount": amount,
            }
        )
        request._claim_terminal_cash_source(receipt)
        ledger = request._ensure_treasury_ledger(amount=amount)
        receipt._write_finance_authority(
            {"state": "received", "treasury_ledger_id": ledger.id}
        )
        return ledger

    def test_income_position_uses_authoritative_states_and_signed_balances(self):
        contract = self._contract("Income Position", 100.0)
        contract_amount = contract.amount_final
        settlement = self.env["sc.settlement.order"].create(
            {
                "name": "Position Settlement",
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "contract_id": contract.id,
                "currency_id": self.currency.id,
                "settlement_type": "in",
                "line_ids": [(0, 0, {"name": "line", "contract_id": contract.id, "qty": 1.0, "price_unit": contract_amount + 20.0})],
            }
        )
        settlement._write_lifecycle("approve")
        self.assertEqual(settlement.line_ids.contract_id, contract)
        self.env["sc.invoice.registration"].create(
            {
                "name": "Position Invoice",
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "contract_id": contract.id,
                "currency_id": self.currency.id,
                "direction": "output",
                "state": "registered",
                "amount_total": contract_amount + 10.0,
            }
        )
        self._posted_receipt_evidence("Position Receipt Evidence", contract, contract_amount + 30.0)
        self.env.flush_all()
        position = self.env["sc.contract.execution.position"].search([("contract_id", "=", contract.id)])
        self.assertEqual(position.contract_amount, contract_amount)
        self.assertEqual(position.settled_amount, contract_amount + 20.0)
        self.assertEqual(position.invoiced_amount, contract_amount + 10.0)
        self.assertEqual(position.cash_executed_amount, contract_amount + 30.0)
        self.assertEqual((position.settlement_balance, position.invoice_balance, position.cash_balance), (-20.0, -10.0, -30.0))
        self.assertTrue(position.ratio_defined)
        self.assertAlmostEqual(position.settlement_rate, (contract_amount + 20.0) / contract_amount * 100.0)
        self.assertAlmostEqual(position.invoice_rate, (contract_amount + 10.0) / contract_amount * 100.0)
        self.assertAlmostEqual(position.cash_execution_rate, (contract_amount + 30.0) / contract_amount * 100.0)
        contract.invalidate_recordset()
        self.assertAlmostEqual(contract.settlement_rate, position.settlement_rate)
        self.assertAlmostEqual(contract.invoice_rate, position.invoice_rate)
        self.assertAlmostEqual(contract.cash_execution_rate, position.cash_execution_rate)
        summary = self.env["sc.contract.recon.summary"].create({"contract_id": contract.id})
        self.assertEqual(summary.contract_amount_total, contract_amount)
        self.assertEqual(summary.settlement_total, contract_amount + 20.0)
        self.assertEqual(summary.payment_total, contract_amount + 30.0)
        self.assertEqual(summary.payment_ids_count, 1)
        evidence_action = position.action_open_cash_evidence()
        self.assertEqual(evidence_action["res_model"], "sc.treasury.ledger")
        self.assertIn(("company_id", "=", self.company.id), evidence_action["domain"])
        self.assertIn(("currency_id", "=", self.currency.id), evidence_action["domain"])
        self.assertIn(("payment_request_id.contract_id", "=", contract.id), evidence_action["domain"])

    def test_zero_contract_amount_has_undefined_ratios(self):
        contract = self._contract("Zero Position")
        position = self.env["sc.contract.execution.position"].search([("contract_id", "=", contract.id)])
        self.assertFalse(position.ratio_defined)
        self.assertFalse(position.settlement_rate)
        self.assertFalse(position.invoice_rate)
        self.assertFalse(position.cash_execution_rate)

    def test_received_header_without_posted_treasury_evidence_is_not_cash(self):
        contract = self._contract("Income Without Cash Evidence", 100.0)
        receipt = self.env["sc.receipt.income"].create(
            {
                "name": "Receipt Header Only",
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "contract_id": contract.id,
                "currency_id": self.currency.id,
                "amount": 40.0,
            }
        )
        receipt._write_finance_authority({"state": "received"})
        self.env.flush_all()

        position = self.env["sc.contract.execution.position"].search([("contract_id", "=", contract.id)])
        self.assertEqual(position.cash_executed_amount, 0.0)
        summary = self.env["sc.contract.recon.summary"].create({"contract_id": contract.id})
        self.assertEqual(summary.payment_total, 0.0)
        self.assertEqual(summary.payment_ids_count, 0)

    def test_ratio_scale_preserves_half_full_overrun_and_negative_facts(self):
        expected_rates = (50.0, 100.0, 120.0)
        contracts = [self._contract(f"Ratio Position {rate}", 100.0) for rate in expected_rates]
        for contract, rate in zip(contracts, expected_rates):
            settlement = self.env["sc.settlement.order"].create(
                {
                    "name": f"Ratio Settlement {rate}",
                    "project_id": self.project.id,
                    "partner_id": self.partner.id,
                    "contract_id": contract.id,
                    "currency_id": self.currency.id,
                    "settlement_type": "in",
                    "line_ids": [
                        (
                            0,
                            0,
                            {
                                "name": "ratio line",
                                "contract_id": contract.id,
                                "qty": 1.0,
                                "price_unit": contract.amount_final * rate / 100.0,
                            },
                        )
                    ],
                }
            )
            settlement._write_lifecycle("approve")

        negative_contract = self._contract("Negative Ratio Position", 100.0)
        self.env["sc.settlement.adjustment"].create(
            {
                "project_id": self.project.id,
                "contract_id": negative_contract.id,
                "partner_id": self.partner.id,
                "item_name": "negative ratio deduction",
                "adjustment_type": "deduction",
                "state": "confirmed",
                "amount": negative_contract.amount_final / 4.0,
                "currency_id": self.currency.id,
            }
        )
        self.env.flush_all()
        contract_ids = [contract.id for contract in contracts] + [negative_contract.id]
        positions = self.env["sc.contract.execution.position"].search(
            [("contract_id", "in", contract_ids)]
        )
        rates = {position.contract_id.id: position.settlement_rate for position in positions}
        for contract, rate in zip(contracts, expected_rates):
            self.assertAlmostEqual(rates[contract.id], rate)
            contract.invalidate_recordset()
            self.assertAlmostEqual(contract.settlement_rate, rate)
        self.assertAlmostEqual(rates[negative_contract.id], -25.0)
        negative_contract.invalidate_recordset()
        self.assertAlmostEqual(negative_contract.settlement_rate, -25.0)

    def test_multi_contract_settlement_lines_are_attributed_to_each_contract(self):
        contract_a = self._contract("Line Position A", 100.0)
        contract_b = self._contract("Line Position B", 100.0)
        settlement = self.env["sc.settlement.order"].create(
            {
                "name": "Multi Contract Position Settlement",
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "currency_id": self.currency.id,
                "settlement_type": "in",
                "line_ids": [
                    (0, 0, {"name": "A", "contract_id": contract_a.id, "qty": 1.0, "price_unit": 30.0}),
                    (0, 0, {"name": "B", "contract_id": contract_b.id, "qty": 1.0, "price_unit": 40.0}),
                ],
            }
        )
        settlement._write_lifecycle("approve")
        self.env.flush_all()
        positions = self.env["sc.contract.execution.position"].search(
            [("contract_id", "in", [contract_a.id, contract_b.id])]
        )
        amounts = {row.contract_id.id: row.settled_amount for row in positions}
        self.assertEqual(amounts, {contract_a.id: 30.0, contract_b.id: 40.0})

    def test_only_authoritative_workflow_states_and_invoice_direction_are_counted(self):
        contract = self._contract("State Position", 100.0)
        self.env["sc.settlement.order"].create(
            {
                "name": "Draft Position Settlement",
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "contract_id": contract.id,
                "currency_id": self.currency.id,
                "settlement_type": "in",
                "line_ids": [(0, 0, {"name": "draft", "contract_id": contract.id, "qty": 1.0, "price_unit": 11.0})],
            }
        )
        self.env["sc.settlement.adjustment"].create(
            {
                "project_id": self.project.id,
                "contract_id": contract.id,
                "partner_id": self.partner.id,
                "item_name": "draft adjustment",
                "adjustment_type": "addition",
                "amount": 12.0,
                "currency_id": self.currency.id,
            }
        )
        self.env["sc.invoice.registration"].create(
            {
                "name": "Draft Position Invoice",
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "contract_id": contract.id,
                "currency_id": self.currency.id,
                "direction": "output",
                "state": "draft",
                "amount_total": 13.0,
            }
        )
        self.env["sc.receipt.income"].create(
            {
                "name": "Draft Position Receipt",
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "contract_id": contract.id,
                "currency_id": self.currency.id,
                "state": "draft",
                "amount": 14.0,
            }
        )
        self.env.flush_all()
        position = self.env["sc.contract.execution.position"].search([("contract_id", "=", contract.id)])
        self.assertEqual(position.settled_amount, 0.0)
        self.assertEqual(position.invoiced_amount, 0.0)
        self.assertEqual(position.cash_executed_amount, 0.0)

    def test_confirmed_signed_adjustments_are_part_of_settlement_position(self):
        contract = self._contract("Adjustment Position", 100.0)
        for adjustment_type, amount in (("addition", 20.0), ("deduction", 5.0)):
            self.env["sc.settlement.adjustment"].create(
                {
                    "project_id": self.project.id,
                    "contract_id": contract.id,
                    "partner_id": self.partner.id,
                    "item_name": f"{adjustment_type} position",
                    "adjustment_type": adjustment_type,
                    "state": "confirmed",
                    "amount": amount,
                    "currency_id": self.currency.id,
                }
            )
        self.env.flush_all()
        position = self.env["sc.contract.execution.position"].search([("contract_id", "=", contract.id)])
        self.assertEqual(position.settled_amount, 15.0)
        self.assertEqual(position.settlement_balance, position.contract_amount - 15.0)

    def test_expense_cash_uses_posted_allocation_and_reversal_is_excluded(self):
        contract = self._contract("Expense Position", 100.0, contract_type="in")
        request = self._approved_payment_request("Expense Position Payment", contract, 35.0)
        ledger = request.sudo()._ensure_payment_ledger(amount=35.0)
        self.env.flush_all()
        position = self.env["sc.contract.execution.position"].search([("contract_id", "=", contract.id)])
        self.assertEqual(position.cash_executed_amount, 35.0)
        self.assertEqual(position.cash_balance, position.contract_amount - 35.0)
        summary = self.env["sc.contract.recon.summary"].create({"contract_id": contract.id})
        self.assertEqual(summary.payment_total, 35.0)
        self.assertEqual(summary.payment_ids_count, 1)
        evidence_action = position.action_open_cash_evidence()
        self.assertEqual(evidence_action["res_model"], "payment.ledger.allocation")
        self.assertIn(("company_id", "=", self.company.id), evidence_action["domain"])
        self.assertIn(("currency_id", "=", self.currency.id), evidence_action["domain"])
        self.assertIn(("contract_id", "=", contract.id), evidence_action["domain"])
        evidence = self.env["payment.ledger.allocation"].search(evidence_action["domain"])
        self.assertEqual(sum(evidence.mapped("allocated_amount")), position.cash_executed_amount)
        ledger.sudo().with_context(_sc_payment_ledger_internal_reversal=True).write(
            {"state": "reversed"}
        )
        self.env.flush_all()
        position.invalidate_recordset()
        self.assertEqual(position.cash_executed_amount, 0.0)
        self.assertEqual(position.cash_balance, position.contract_amount)
        summary.invalidate_recordset()
        self.assertEqual(summary.payment_total, 0.0)
        self.assertEqual(summary.payment_ids_count, 0)

    def test_batch_position_helper_has_fixed_query_budget(self):
        one_contract = self._contract("Query Position One", 1.0)
        ten_contracts = self.env["construction.contract"]
        fifty_contracts = self.env["construction.contract"]
        for index in range(50):
            contract = self._contract(f"Query Position Many {index}")
            fifty_contracts |= contract
            if index < 10:
                ten_contracts |= contract
        opm.contract_execution_position_map(self.env, [one_contract.id])
        start = self.env.cr.sql_log_count
        opm.contract_execution_position_map(self.env, [one_contract.id])
        one_count = self.env.cr.sql_log_count - start
        start = self.env.cr.sql_log_count
        opm.contract_execution_position_map(self.env, ten_contracts.ids)
        ten_count = self.env.cr.sql_log_count - start
        start = self.env.cr.sql_log_count
        opm.contract_execution_position_map(self.env, fifty_contracts.ids)
        fifty_count = self.env.cr.sql_log_count - start
        self.assertEqual((ten_count, fifty_count), (one_count, one_count))
        self.assertLessEqual(fifty_count, 5)
        one_summary = self.env["sc.contract.recon.summary"].create({"contract_id": one_contract.id})
        ten_summaries = self.env["sc.contract.recon.summary"].create(
            [{"contract_id": contract.id} for contract in ten_contracts]
        )
        fifty_summaries = self.env["sc.contract.recon.summary"].create(
            [{"contract_id": contract.id} for contract in fifty_contracts]
        )
        one_summary._compute_totals()
        start = self.env.cr.sql_log_count
        one_summary._compute_totals()
        one_summary_count = self.env.cr.sql_log_count - start
        start = self.env.cr.sql_log_count
        ten_summaries._compute_totals()
        ten_summary_count = self.env.cr.sql_log_count - start
        start = self.env.cr.sql_log_count
        fifty_summaries._compute_totals()
        fifty_summary_count = self.env.cr.sql_log_count - start
        self.assertEqual(ten_summary_count, fifty_summary_count)
        self.assertLessEqual(one_summary_count, 9)
        self.assertLessEqual(fifty_summary_count, 9)

    def test_position_read_is_capability_and_allowed_company_scoped(self):
        visible_contract = self._contract("Visible Company Position", 10.0)
        other_company = self.env["res.company"].create(
            {"name": "Position Other Company", "currency_id": self.currency.id}
        )
        other_project = self.env["project.project"].with_company(other_company).create(
            {"name": "Position Other Project", "company_id": other_company.id}
        )
        country = (
            other_company.account_fiscal_country_id
            or other_company.partner_id.country_id
            or self.env.ref("base.cn")
        )
        tax_group = self.env["account.tax.group"].with_company(other_company).create(
            {
                "name": "Position Other Tax Group",
                "company_id": other_company.id,
                "country_id": country.id,
            }
        )
        other_tax = self.env["account.tax"].with_company(other_company).create(
            {
                "name": "Position Other Tax",
                "amount": 9.0,
                "amount_type": "percent",
                "type_tax_use": "sale",
                "company_id": other_company.id,
                "tax_group_id": tax_group.id,
                "country_id": country.id,
            }
        )
        other_purchase_tax = self.env["account.tax"].with_company(other_company).create(
            {
                "name": "Position Other Purchase Tax",
                "amount": 13.0,
                "amount_type": "percent",
                "type_tax_use": "purchase",
                "company_id": other_company.id,
                "tax_group_id": tax_group.id,
                "country_id": country.id,
            }
        )
        other_contract = self.env["construction.contract"].with_company(other_company).create(
            {
                "subject": "Hidden Company Position",
                "type": "out",
                "project_id": other_project.id,
                "partner_id": self.partner.id,
                "company_id": other_company.id,
                "currency_id": self.currency.id,
                "tax_id": other_tax.id,
            }
        )
        contract_reader = self.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "position_contract_reader",
                "login": "position_contract_reader",
                "email": "position_contract_reader@example.com",
                "company_id": self.company.id,
                "company_ids": [(6, 0, [self.company.id])],
                "groups_id": [(6, 0, [self.env.ref("smart_construction_core.group_sc_cap_contract_read").id])],
            }
        )
        no_capability = self.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "position_no_capability",
                "login": "position_no_capability",
                "email": "position_no_capability@example.com",
                "company_id": self.company.id,
                "company_ids": [(6, 0, [self.company.id])],
                "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        finance_reader = self.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "position_finance_reader",
                "login": "position_finance_reader",
                "email": "position_finance_reader@example.com",
                "company_id": self.company.id,
                "company_ids": [(6, 0, [self.company.id])],
                "groups_id": [
                    (6, 0, [self.env.ref("smart_construction_core.group_sc_cap_finance_read").id])
                ],
            }
        )
        self.env.flush_all()
        Position = self.env["sc.contract.execution.position"]
        visible = Position.with_user(contract_reader).search(
            [("contract_id", "in", [visible_contract.id, other_contract.id])]
        )
        self.assertEqual(visible.contract_id, visible_contract)
        with self.assertRaises(AccessError):
            Position.with_user(contract_reader).browse(other_contract.id).read(["subject"])
        with self.assertRaises(AccessError):
            Position.with_user(no_capability).search([], limit=1).read(["subject"])
        with self.assertRaises(AccessError):
            Position.with_user(finance_reader).search([], limit=1).read(["subject"])

        visible_expense = self._contract("Visible Expense Position", 10.0, "in")
        other_expense = self.env["construction.contract"].with_company(other_company).create(
            {
                "subject": "Hidden Expense Position",
                "type": "in",
                "project_id": other_project.id,
                "partner_id": self.partner.id,
                "company_id": other_company.id,
                "currency_id": self.currency.id,
                "tax_id": other_purchase_tax.id,
            }
        )
        wrapper_cases = (
            ("construction.contract.income", visible_contract, other_contract),
            ("construction.contract.expense", visible_expense, other_expense),
        )
        canonical_visible = self.env["construction.contract"].with_user(contract_reader).search(
            [("id", "in", [visible_contract.id, other_contract.id])]
        )
        self.assertEqual(canonical_visible, visible_contract)
        with self.assertRaises(AccessError):
            self.env["construction.contract"].with_user(contract_reader).browse(other_contract.id).read(
                ["subject"]
            )
        for model_name, visible_source, hidden_source in wrapper_cases:
            Wrapper = self.env[model_name]
            visible_wrapper = Wrapper.sudo().search([("contract_id", "=", visible_source.id)], limit=1)
            hidden_wrapper = Wrapper.sudo().search([("contract_id", "=", hidden_source.id)], limit=1)
            self.assertTrue(visible_wrapper)
            self.assertTrue(hidden_wrapper)
            allowed = Wrapper.with_user(contract_reader).search(
                [("id", "in", [visible_wrapper.id, hidden_wrapper.id])]
            )
            self.assertEqual(allowed, visible_wrapper)
            with self.assertRaises(AccessError):
                Wrapper.with_user(contract_reader).browse(hidden_wrapper.id).read(["subject"])

    def test_position_is_readonly_and_traces_to_canonical_contract(self):
        contract = self._contract("Trace Position", 10.0)
        position = self.env["sc.contract.execution.position"].search([("contract_id", "=", contract.id)])
        action = position.action_open_execution_source_contract()
        self.assertEqual(action["res_model"], "construction.contract.income")
        self.assertTrue(action["res_id"])
        with self.assertRaises(AccessError):
            position.sudo().write({"subject": "forbidden"})
        with self.assertRaises(AccessError):
            position.sudo().unlink()
        with self.assertRaises(AccessError):
            self.env["sc.contract.execution.position"].sudo().create({"subject": "forbidden"})

    def test_native_action_has_tree_pivot_form_and_readonly_context(self):
        action = self.env.ref("smart_construction_core.action_sc_contract_execution_position")
        self.assertEqual(action.res_model, "sc.contract.execution.position")
        self.assertEqual(action.view_mode, "tree,pivot,form")
        context = ast.literal_eval(action.context)
        self.assertFalse(context.get("create"))
        self.assertFalse(context.get("edit"))
        self.assertFalse(context.get("delete"))
        self.assertTrue(context.get("search_default_group_company"))
        self.assertTrue(context.get("search_default_group_currency"))
        self.assertTrue(context.get("search_default_group_project"))
        self.assertEqual(ast.literal_eval(action.domain), [])
        for view_xmlid in (
            "smart_construction_core.view_sc_contract_execution_position_tree",
            "smart_construction_core.view_sc_contract_execution_position_pivot",
            "smart_construction_core.view_sc_contract_execution_position_form",
        ):
            self.assertIn('name="currency_id"', self.env.ref(view_xmlid).arch_db)

    def test_native_grouping_separates_contract_currencies(self):
        other_currency = self.env["res.currency"].search(
            [("id", "!=", self.currency.id)], limit=1
        )
        if not other_currency.active:
            other_currency.active = True
        contracts = (
            self._contract("Currency Position Domestic", 31.0)
            | self._contract("Currency Position Foreign", 47.0, currency=other_currency)
        )
        self.env.flush_all()
        rows = self.env["sc.contract.execution.position"].read_group(
            [("contract_id", "in", contracts.ids)],
            ["contract_amount:sum"],
            ["currency_id"],
            lazy=False,
        )
        self.assertEqual({row["currency_id"][0] for row in rows}, set(contracts.mapped("currency_id").ids))
