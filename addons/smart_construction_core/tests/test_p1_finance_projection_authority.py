# -*- coding: utf-8 -*-
import runpy
import threading
import uuid
from pathlib import Path
from unittest.mock import patch

from lxml import etree
from psycopg2.errors import SerializationFailure

from odoo import SUPERUSER_ID, api
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.modules.registry import Registry
from odoo.tests.common import TransactionCase, tagged

from ..models.support import operating_metrics as opm
from ..services.payment_slice_native_adapter import PaymentSliceNativeAdapter


@tagged("post_install", "-at_install", "sc_gate", "p1_finance_projection_authority")
class TestP1FinanceProjectionAuthority(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls.env["project.project"].create(
            {
                "name": "P1 财务投影权威项目",
                "code": "P1-FINANCE-AUTH",
                "company_id": cls.env.company.id,
                "operation_strategy": "direct",
            }
        )
        cls.partner = cls.env["res.partner"].create({"name": "P1 财务投影往来单位"})
        cls.receipt_contract = cls.env["construction.contract"].create(
            {
                "subject": "P1 财务投影收款合同",
                "type": "out",
                "project_id": cls.project.id,
                "partner_id": cls.partner.id,
                "company_id": cls.env.company.id,
                "currency_id": cls.env.company.currency_id.id,
            }
        )
        cls.reader = cls.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "P1 财务来源隔离读者",
                "login": "p1_finance_source_isolated_reader",
                "email": "p1-finance-source-isolated@example.invalid",
                "company_id": cls.env.company.id,
                "company_ids": [(6, 0, [cls.env.company.id])],
                "groups_id": [(6, 0, [cls.env.ref("smart_construction_core.group_sc_cap_finance_read").id])],
            }
        )
        cls.finance_user = cls.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "P1 财务来源经办用户",
                "login": "p1_finance_source_operator",
                "email": "p1-finance-source-operator@example.invalid",
                "company_id": cls.env.company.id,
                "company_ids": [(6, 0, [cls.env.company.id])],
                "groups_id": [(6, 0, [cls.env.ref("smart_construction_core.group_sc_cap_finance_user").id])],
            }
        )
        cls.finance_manager = cls.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "P1 财务来源授权经理",
                "login": "p1_finance_source_authorized_manager",
                "email": "p1-finance-source-authorized@example.invalid",
                "company_id": cls.env.company.id,
                "company_ids": [(6, 0, [cls.env.company.id])],
                "groups_id": [(6, 0, [cls.env.ref("smart_construction_core.group_sc_cap_finance_manager").id])],
            }
        )
        cls.other_currency = cls.env["res.currency"].search(
            [("id", "!=", cls.env.company.currency_id.id)], limit=1
        )
        if not cls.other_currency.active:
            cls.other_currency.active = True

    def _cleanup_committed_cash_source_race(self, request_id):
        registry = Registry(self.env.cr.dbname)
        with registry.cursor() as cursor:
            env = api.Environment(cursor, SUPERUSER_ID, {"tracking_disable": True})
            source_specs = (
                ("sc.receipt.income", "sc_receipt_income"),
                ("sc.expense.claim", "sc_expense_claim"),
            )
            for model_name, table_name in source_specs:
                records = env[model_name].sudo().search(
                    [("payment_request_id", "=", request_id)]
                )
                if records:
                    env["mail.activity"].sudo().search(
                        [("res_model", "=", model_name), ("res_id", "in", records.ids)]
                    ).unlink()
                    env["mail.followers"].sudo().search(
                        [("res_model", "=", model_name), ("res_id", "in", records.ids)]
                    ).unlink()
                    env["mail.message"].sudo().search(
                        [("model", "=", model_name), ("res_id", "in", records.ids)]
                    ).unlink()
                cursor.execute(
                    f"DELETE FROM {table_name} WHERE payment_request_id = %s",
                    [request_id],
                )
            env["sc.audit.log"].sudo().search(
                [("model", "=", "payment.request"), ("res_id", "=", request_id)]
            ).unlink()
            env["mail.activity"].sudo().search(
                [("res_model", "=", "payment.request"), ("res_id", "=", request_id)]
            ).unlink()
            env["mail.followers"].sudo().search(
                [("res_model", "=", "payment.request"), ("res_id", "=", request_id)]
            ).unlink()
            env["mail.message"].sudo().search(
                [("model", "=", "payment.request"), ("res_id", "=", request_id)]
            ).unlink()
            request = env["payment.request"].sudo().browse(request_id).exists()
            if request:
                cursor.execute(
                    "UPDATE payment_request SET state = 'cancel' WHERE id = %s",
                    [request_id],
                )
                request.invalidate_recordset()
                request.unlink()
            cursor.execute(
                "SELECT EXISTS(SELECT 1 FROM payment_request WHERE id = %s), "
                "EXISTS(SELECT 1 FROM sc_receipt_income WHERE payment_request_id = %s), "
                "EXISTS(SELECT 1 FROM sc_expense_claim WHERE payment_request_id = %s)",
                [request_id, request_id, request_id],
            )
            self.assertFalse(any(cursor.fetchone()))
            cursor.commit()

    def _receipt(self, amount, currency=None, *, with_ledger=True, state="received"):
        currency = currency or self.env.company.currency_id
        receipt = self.env["sc.receipt.income"].create(
            {
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "document_no": "P1-RECEIPT-%s" % amount,
                "date_receipt": "2026-09-02",
                "amount": amount,
                "currency_id": currency.id,
            }
        )
        values = {"state": state}
        ledger = self.env["sc.treasury.ledger"]
        if with_ledger:
            ledger = ledger._create_authoritative(
                {
                    "project_id": self.project.id,
                    "partner_id": self.partner.id,
                    "source_model": receipt._name,
                    "source_res_id": receipt.id,
                    "direction": "in",
                    "amount": amount,
                    "currency_id": currency.id,
                    "state": "posted",
                }
            )
            values["treasury_ledger_id"] = ledger.id
        receipt._write_finance_authority(values)
        receipt.invalidate_recordset()
        self.assertEqual(receipt.state, state)
        self.assertIn(receipt.finance_identity_state, {"normalized", "legacy_observed_identity"})
        self.assertEqual(receipt.company_id, self.env.company)
        if with_ledger:
            ledger.invalidate_recordset()
            self.assertEqual(ledger.state, "posted")
            self.assertEqual(ledger.company_id, self.env.company)
            self.assertEqual(ledger.normalization_state, "normalized")
        return receipt, ledger

    def test_only_terminal_sources_enter_and_posted_ledger_owns_cash(self):
        draft = self.env["sc.receipt.income"].create(
            {
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "amount": 11,
                "currency_id": self.env.company.currency_id.id,
            }
        )
        receipt, ledger = self._receipt(120)
        missing, _empty = self._receipt(80, with_ledger=False)
        Fact = self.env["sc.finance.business.fact"]

        self.assertFalse(Fact.search([("source_model", "=", draft._name), ("source_res_id", "=", draft.id)]))
        canonical = Fact.search([("source_model", "=", receipt._name), ("source_res_id", "=", receipt.id)])
        self.assertEqual(canonical.fact_type, "arrival_gross")
        self.assertEqual(canonical.balance_policy, "canonical")
        self.assertEqual(canonical.cash_evidence_state, "posted_ledger")
        self.assertEqual(canonical.cash_in_amount, ledger.amount)

        quarantined = Fact.search([("source_model", "=", missing._name), ("source_res_id", "=", missing.id)])
        self.assertEqual(quarantined.balance_policy, "policy_required")
        self.assertEqual(quarantined.cash_evidence_state, "missing_posted_ledger")
        self.assertEqual(quarantined.cash_in_amount, 0)
        summary = self.env["sc.finance.business.project.summary"].search(
            [("project_id", "=", self.project.id), ("currency_id", "=", self.env.company.currency_id.id),
             ("business_domain", "=", "arrival_settlement")]
        )
        self.assertEqual(summary.arrival_amount, 120)

    def test_terminal_sources_and_posted_ledgers_are_immutable(self):
        receipt, ledger = self._receipt(75)
        with self.assertRaises(UserError):
            self.env["sc.receipt.income"].create(
                {
                    "project_id": self.project.id,
                    "partner_id": self.partner.id,
                    "amount": 10,
                    "state": "legacy_confirmed",
                }
            )
        with self.assertRaises(UserError):
            receipt.write({"amount": 76})
        with self.assertRaises(UserError):
            receipt.with_context(sc_receipt_fact_authority_token=object()).write({"amount": 76})
        terminal_mutations = (
            {"source_kind": "residual_receipt"},
            {"business_category_id": False},
            {"document_no": "P1-FORGED-RECEIPT"},
            {"receipt_type": "forged"},
            {"income_category": "forged"},
            {"payment_method": "forged"},
            {"receiving_account": "forged"},
            {"receiving_account_name": "forged"},
            {"receiving_account_no": "forged"},
            {"receiving_bank_name": "forged"},
            {"bill_no": "forged"},
            {"invoice_ref": "forged"},
        )
        for values in terminal_mutations:
            with self.subTest(values=values), self.assertRaises(UserError):
                receipt.with_user(self.finance_manager).write(values)
        receipt.with_user(self.finance_manager).write({"note": "terminal evidence annotation"})
        self.assertEqual(receipt.note, "terminal evidence annotation")
        with self.assertRaises(UserError):
            ledger.write({"amount": 76})
        with self.assertRaises(UserError):
            self.env["sc.treasury.ledger"].with_context(allow_ledger_auto=True).create(
                {
                    "project_id": self.project.id,
                    "direction": "in",
                    "amount": 1,
                    "currency_id": self.env.company.currency_id.id,
                }
            )

        request = self.env["payment.request"].create(
            {
                "name": "P1 immutable receive request",
                "type": "receive",
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "amount": 25,
            }
        )
        receive_ledger = request._ensure_treasury_ledger(amount=25)
        self.assertEqual(request._ensure_treasury_ledger(amount=25), receive_ledger)
        with self.assertRaises(ValidationError):
            request._ensure_treasury_ledger(amount=26)
        receive_ledger.invalidate_recordset()
        self.assertEqual(receive_ledger.amount, 25)

    def test_receipt_native_terminal_controls_match_model_authority(self):
        root = etree.fromstring(
            self.env.ref("smart_construction_core.view_sc_receipt_income_form").arch_db.encode("utf-8")
        )
        received_button = root.xpath("//button[@name='action_received']")
        self.assertEqual(len(received_button), 1)
        self.assertEqual(
            received_button[0].get("groups"),
            "smart_construction_core.group_sc_cap_finance_manager",
        )
        cancel_button = root.xpath("//button[@name='action_cancel']")
        self.assertEqual(len(cancel_button), 1)
        self.assertIn("received", cancel_button[0].get("invisible", ""))
        for field_name in (
            "source_kind",
            "business_category_id",
            "date_receipt",
            "document_no",
            "project_id",
            "partner_id",
            "contract_id",
            "payment_request_id",
            "receipt_type",
            "income_category",
            "payment_method",
            "receiving_account",
            "receiving_account_name",
            "receiving_account_no",
            "receiving_bank_name",
            "bill_no",
            "invoice_ref",
            "amount",
            "deducted_invoice_amount",
            "deducted_tax_amount",
            "settlement_amount",
            "active",
        ):
            nodes = root.xpath("//field[@name='%s']" % field_name)
            self.assertTrue(nodes, field_name)
            self.assertIn("received", nodes[0].get("readonly", ""), field_name)

    def test_terminal_source_unlink_and_deduction_line_mutation_are_blocked(self):
        receipt, _ledger = self._receipt(76)
        with self.assertRaisesRegex(UserError, "不可删除"):
            receipt.with_user(self.finance_manager).unlink()

        category = self.env.ref("smart_construction_core.business_category_finance_deduction_bill")
        claim = self.env["sc.expense.claim"].create(
            {
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "business_category_id": category.id,
                "claim_type": "expense",
                "amount": 10,
                "currency_id": self.env.company.currency_id.id,
                "deduction_line_ids": [
                    (0, 0, {"item_name": "P1 终态扣款明细", "deduction_category": "other", "amount": 10})
                ],
            }
        )
        claim._write_finance_authority({"state": "done"})
        line = claim.deduction_line_ids
        with self.assertRaisesRegex(UserError, "不可删除"):
            claim.with_user(self.finance_manager).unlink()
        with self.assertRaisesRegex(UserError, "不可修改"):
            line.with_user(self.finance_manager).write({"amount": 9})
        with self.assertRaisesRegex(UserError, "不可删除"):
            line.with_user(self.finance_manager).unlink()
        with self.assertRaisesRegex(UserError, "不可新增"):
            self.env["sc.expense.claim.deduction.line"].with_user(self.finance_manager).create(
                {
                    "claim_id": claim.id,
                    "item_name": "非法追加",
                    "deduction_category": "other",
                    "amount": 1,
                }
            )
        with self.assertRaisesRegex(UserError, "不可新增"):
            self.env["sc.expense.claim.deduction.line"].with_user(
                self.finance_manager
            ).with_context(default_claim_id=claim.id).create(
                {
                    "item_name": "非法上下文追加",
                    "deduction_category": "other",
                    "amount": 1,
                }
            )

    def test_company_and_currency_are_frozen_aggregation_dimensions(self):
        domestic, _ledger = self._receipt(30)
        foreign, _foreign_ledger = self._receipt(40, self.other_currency)
        Fact = self.env["sc.finance.business.fact"]
        domestic_fact = Fact.search([("source_model", "=", domestic._name), ("source_res_id", "=", domestic.id)])
        foreign_fact = Fact.search([("source_model", "=", foreign._name), ("source_res_id", "=", foreign.id)])
        self.assertEqual(domestic_fact.company_id, self.env.company)
        self.assertEqual(foreign_fact.company_id, self.env.company)
        self.assertNotEqual(domestic_fact.currency_id, foreign_fact.currency_id)

        summaries = self.env["sc.finance.business.project.summary"].search(
            [("project_id", "=", self.project.id), ("business_domain", "=", "arrival_settlement")]
        )
        self.assertEqual(set(summaries.mapped("currency_id")), {domestic.currency_id, foreign.currency_id})
        for summary in summaries:
            facts = Fact.search(summary._project_domain() + [("business_domain", "=", summary.business_domain)])
            self.assertTrue(facts)
            self.assertEqual(set(facts.mapped("currency_id")), {summary.currency_id})

    def test_tax_lifecycle_and_guarantee_cash_authority(self):
        tax = self.env["sc.tax.deduction.registration"].create(
            {
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "invoice_no": "P1-TAX-001",
                "deduction_confirm_date": "2026-09-02",
                "deduction_amount": 100,
                "deduction_tax_amount": 9,
            }
        )
        Fact = self.env["sc.finance.business.fact"]
        domain = [("source_model", "=", tax._name), ("source_res_id", "=", tax.id)]
        self.assertFalse(Fact.search(domain))
        tax._write_finance_authority({"state": "deducted"})
        tax.invalidate_recordset()
        self.assertEqual(tax.state, "deducted")
        self.assertEqual(tax.finance_identity_state, "normalized")
        self.assertEqual(Fact.search(domain).balance_policy, "noncash_tax")

        bid = self.env["tender.bid"].create(
            {"tender_name": "P1 权威保证金投标", "project_id": self.project.id, "owner_id": self.partner.id}
        )
        guarantee = self.env["tender.guarantee"].create(
            {"bid_id": bid.id, "type": "out", "date": "2026-09-02", "amount": 55}
        )
        with self.assertRaises(UserError):
            self.env["tender.guarantee"].create(
                {"bid_id": bid.id, "type": "out", "amount": 1, "state": "confirmed"}
            )
        guarantee.action_confirm()
        guarantee.invalidate_recordset()
        self.assertEqual(guarantee.state, "confirmed")
        self.assertEqual(guarantee.finance_identity_state, "normalized")
        self.assertEqual(guarantee.company_id, self.env.company)
        self.assertTrue(guarantee.treasury_ledger_id)
        self.env.cr.execute(
            "SELECT source_model, source_res_id, balance_policy FROM sc_finance_business_fact "
            "WHERE source_model = 'tender.guarantee' AND source_res_id = %s",
            [guarantee.id],
        )
        raw_fact = self.env.cr.fetchone()
        self.assertTrue(raw_fact, "confirmed normalized guarantee must exist in raw finance projection")
        guarantee_fact = Fact.search(
            [("source_model", "=", guarantee._name), ("source_res_id", "=", guarantee.id)]
        )
        self.assertEqual(guarantee_fact.balance_policy, "canonical")
        self.assertEqual(guarantee_fact.cash_out_amount, 55)
        with self.assertRaises(UserError):
            guarantee.action_reset_draft()

    def test_projection_read_query_growth_is_bounded_for_1_10_50(self):
        for index in range(50):
            self._receipt(index + 1)
        domain = [("project_id", "=", self.project.id), ("fact_type", "=", "arrival_gross")]

        def query_count(limit):
            self.env["sc.finance.business.fact"].invalidate_model()
            start = self.env.cr.sql_log_count
            rows = self.env["sc.finance.business.fact"].search(domain, limit=limit)
            rows.read(["company_id", "currency_id", "amount", "cash_in_amount", "cash_evidence_state"])
            return self.env.cr.sql_log_count - start

        one = query_count(1)
        self.assertLessEqual(query_count(10), one + 2)
        self.assertLessEqual(query_count(50), one + 2)

    def test_payment_ledger_batch_create_query_growth_is_bounded_for_1_10_50(self):
        expense_contract = self.env["construction.contract"].create(
            {
                "subject": "P1 批量付款查询预算合同",
                "type": "in",
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "company_id": self.env.company.id,
                "currency_id": self.env.company.currency_id.id,
            }
        )
        requests = self.env["payment.request"]
        for index in range(61):
            requests |= self.env["payment.request"].create(
                {
                    "name": "P1 ledger batch %02d" % index,
                    "type": "pay",
                    "project_id": self.project.id,
                    "partner_id": self.partner.id,
                    "contract_id": expense_contract.id,
                    "amount": 1,
                    "currency_id": self.env.company.currency_id.id,
                }
            )
        self.env.cr.execute(
            "UPDATE payment_request SET state = 'approved' WHERE id = ANY(%s)",
            [requests.ids],
        )
        requests.invalidate_recordset(["state"])

        def create_count(batch):
            values = [
                {
                    "payment_request_id": request.id,
                    "amount": 1,
                    "paid_at": "2026-09-02 12:00:00",
                    "ref": "P1-BATCH-%s" % request.id,
                }
                for request in batch
            ]
            start = self.env.cr.sql_log_count
            self.env["payment.ledger"]._create_authoritative(values)
            return self.env.cr.sql_log_count - start

        one = create_count(requests[:1])
        ten = create_count(requests[1:11])
        fifty = create_count(requests[11:61])
        self.assertLessEqual(ten, one + 12)
        self.assertLessEqual(fifty, one + 20)

    def test_payment_execution_batch_create_has_one_ambiguity_guard_for_1_10_50(self):
        expense_contract = self.env["construction.contract"].create(
            {
                "subject": "P1 批量付款执行查询预算合同",
                "type": "in",
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "company_id": self.env.company.id,
                "currency_id": self.env.company.currency_id.id,
            }
        )
        requests = self.env["payment.request"]
        for index in range(61):
            requests |= self.env["payment.request"].create(
                {
                    "name": "P1 execution batch %02d" % index,
                    "type": "pay",
                    "project_id": self.project.id,
                    "partner_id": self.partner.id,
                    "contract_id": expense_contract.id,
                    "amount": 1,
                    "currency_id": self.env.company.currency_id.id,
                    "payment_account_name": "P1 batch payee",
                    "payment_bank_name": "P1 batch bank",
                    "payment_account_no": "P1-BATCH-ACCOUNT",
                }
            )
        self.env.cr.execute(
            "UPDATE payment_request SET state = 'approved' WHERE id = ANY(%s)",
            [requests.ids],
        )
        requests.invalidate_recordset(["state"])

        def create_count(batch):
            start = self.env.cr.sql_log_count
            self.env["sc.payment.execution"].create(
                [{"payment_request_id": request.id} for request in batch]
            )
            return self.env.cr.sql_log_count - start

        request_model = type(requests)
        original_ambiguity_probe = request_model._ambiguous_posted_payment_request_ids
        guarded_batch_sizes = []

        def counted_ambiguity_probe(records):
            guarded_batch_sizes.append(len(records))
            return original_ambiguity_probe(records)

        with patch.object(
            request_model,
            "_ambiguous_posted_payment_request_ids",
            counted_ambiguity_probe,
        ):
            one = create_count(requests[:1])
            ten = create_count(requests[1:11])
            fifty = create_count(requests[11:61])
        # Execution creation legitimately allocates one sequence and persists one
        # document per row. Heavy ambiguity and basis relation reads are batched;
        # the remaining budget covers only bounded per-document persistence.
        self.assertEqual(guarded_batch_sizes, [1, 10, 50])
        self.assertLessEqual(ten, one + 65)
        self.assertLessEqual(fifty, one + 325)

    def test_one_request_has_one_terminal_cash_source_and_one_projection_consumer(self):
        request = self.env["payment.request"].create(
            {
                "name": "P1 unique cash source request",
                "type": "receive",
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "contract_id": self.receipt_contract.id,
                "amount": 100,
                "currency_id": self.env.company.currency_id.id,
            }
        )
        first = self.env["sc.receipt.income"].create(
            {
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "payment_request_id": request.id,
                "amount": 100,
                "currency_id": request.currency_id.id,
            }
        )
        request._claim_terminal_cash_source(first)
        first._write_finance_authority({"state": "received"})
        second = self.env["sc.receipt.income"].create(
            {
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "payment_request_id": request.id,
                "amount": 100,
                "currency_id": request.currency_id.id,
            }
        )
        with self.assertRaisesRegex(UserError, "只能归属于一张"):
            request._claim_terminal_cash_source(second)

        ledger = request._ensure_treasury_ledger(amount=100)
        first._write_finance_authority({"treasury_ledger_id": ledger.id})
        facts = self.env["sc.finance.business.fact"].search(
            [("cash_evidence_state", "=", "posted_ledger"), ("source_model", "=", first._name)]
        )
        self.assertEqual(facts.filtered(lambda fact: fact.source_res_id == first.id).cash_in_amount, 100)

    def test_receive_request_cannot_bypass_terminal_receipt(self):
        request = self.env["payment.request"].create(
            {
                "name": "P1 receipt-only completion request",
                "type": "receive",
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "contract_id": self.receipt_contract.id,
                "amount": 15,
                "currency_id": self.env.company.currency_id.id,
            }
        )
        self.env.cr.execute(
            "UPDATE payment_request SET state='approved', validation_status='validated' WHERE id=%s",
            [request.id],
        )
        request.invalidate_recordset()
        with self.assertRaisesRegex(UserError, "专业收款登记"):
            request.with_user(self.finance_manager).action_done()
        self.assertFalse(self.env["sc.treasury.ledger"].search([("payment_request_id", "=", request.id)]))

    def test_receive_completion_counts_only_exact_canonical_cash_evidence(self):
        def receive_evidence(name):
            request = self.env["payment.request"].create(
                {
                    "name": name,
                    "type": "receive",
                    "project_id": self.project.id,
                    "partner_id": self.partner.id,
                    "contract_id": self.receipt_contract.id,
                    "amount": 10,
                    "currency_id": self.env.company.currency_id.id,
                }
            )
            receipt = self.env["sc.receipt.income"].create(
                {
                    "project_id": self.project.id,
                    "partner_id": self.partner.id,
                    "contract_id": self.receipt_contract.id,
                    "payment_request_id": request.id,
                    "amount": 10,
                    "currency_id": request.currency_id.id,
                }
            )
            request._claim_terminal_cash_source(receipt)
            receipt._write_finance_authority({"state": "received"})
            ledger = request._ensure_treasury_ledger(amount=10)
            receipt._write_finance_authority({"treasury_ledger_id": ledger.id})
            self.env.cr.execute(
                "UPDATE payment_request SET state = 'approved', validation_status = 'validated' "
                "WHERE id = %s",
                [request.id],
            )
            request.invalidate_recordset(["state", "validation_status"])
            return request, ledger

        canonical_request, _canonical_ledger = receive_evidence("P1 canonical received cash")
        void_request, void_ledger = receive_evidence("P1 void received cash")
        unresolved_request, unresolved_ledger = receive_evidence("P1 unresolved received cash")
        mismatch_request, mismatch_ledger = receive_evidence("P1 mismatched received cash")
        self.env.cr.execute(
            "UPDATE sc_treasury_ledger SET state = 'void' WHERE id = %s",
            [void_ledger.id],
        )
        self.env.cr.execute(
            "UPDATE sc_treasury_ledger SET normalization_state = 'legacy_unresolved_identity' "
            "WHERE id = %s",
            [unresolved_ledger.id],
        )
        self.env.cr.execute(
            "UPDATE sc_treasury_ledger SET currency_id = %s WHERE id = %s",
            [self.other_currency.id, mismatch_ledger.id],
        )
        requests = canonical_request | void_request | unresolved_request | mismatch_request
        authority = requests._receive_cash_authority_state_map()
        self.assertEqual(authority[canonical_request.id]["amount"], 10)
        self.assertFalse(authority[canonical_request.id]["has_ambiguous_posted_history"])
        self.assertEqual(authority[void_request.id]["amount"], 0)
        self.assertFalse(authority[void_request.id]["has_ambiguous_posted_history"])
        for request in unresolved_request | mismatch_request:
            self.assertEqual(authority[request.id]["amount"], 0)
            self.assertTrue(authority[request.id]["has_ambiguous_posted_history"])

        canonical_request._check_can_done()
        with self.assertRaisesRegex(ValidationError, "未结清"):
            void_request._check_can_done()
        for request in unresolved_request | mismatch_request:
            with self.assertRaisesRegex(UserError, "身份待确认或身份冲突"):
                request._check_can_done()

    def test_failed_receipt_completion_rolls_back_the_entire_cash_claim(self):
        request = self.env["payment.request"].create(
            {
                "name": "P1 atomic receipt rollback",
                "type": "receive",
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "contract_id": self.receipt_contract.id,
                "amount": 10,
                "currency_id": self.env.company.currency_id.id,
            }
        )
        self.env.cr.execute(
            "UPDATE payment_request SET state = 'approved', validation_status = 'validated' "
            "WHERE id = %s",
            [request.id],
        )
        request.invalidate_recordset(["state", "validation_status"])
        receipt = self.env["sc.receipt.income"].create(
            {
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "contract_id": self.receipt_contract.id,
                "payment_request_id": request.id,
                "amount": 5,
                "currency_id": request.currency_id.id,
            }
        )
        with self.assertRaisesRegex(UserError, "低于收款申请金额"):
            receipt.with_user(self.finance_manager).action_received()
        receipt.invalidate_recordset()
        request.invalidate_recordset()
        self.assertEqual(receipt.state, "draft")
        self.assertFalse(receipt.treasury_ledger_id)
        self.assertEqual(request.state, "approved")
        self.assertFalse(request.terminal_cash_source_model)
        self.assertFalse(request.terminal_cash_source_res_id)
        self.assertFalse(
            self.env["sc.treasury.ledger"].search_count(
                [("payment_request_id", "=", request.id)]
            )
        )

    def test_receipt_completion_enforces_real_finance_role_boundary(self):
        request = self.env["payment.request"].create(
            {
                "name": "P1 receipt role authority",
                "type": "receive",
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "contract_id": self.receipt_contract.id,
                "amount": 10,
                "currency_id": self.env.company.currency_id.id,
            }
        )
        self.env.cr.execute(
            "UPDATE payment_request SET state = 'approved', validation_status = 'validated' "
            "WHERE id = %s",
            [request.id],
        )
        request.invalidate_recordset(["state", "validation_status"])
        receipt = self.env["sc.receipt.income"].create(
            {
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "contract_id": self.receipt_contract.id,
                "payment_request_id": request.id,
                "amount": request.amount,
                "currency_id": request.currency_id.id,
            }
        )

        for user in self.reader | self.finance_user:
            with self.subTest(user=user.login), self.assertRaisesRegex(UserError, "财务确认权限"):
                receipt.with_user(user).action_received()
            receipt.invalidate_recordset()
            request.invalidate_recordset()
            self.assertEqual(receipt.state, "draft")
            self.assertFalse(receipt.treasury_ledger_id)
            self.assertEqual(request.state, "approved")
            self.assertFalse(request.terminal_cash_source_model)
            self.assertFalse(request.terminal_cash_source_res_id)
            self.assertFalse(
                self.env["sc.treasury.ledger"].search_count(
                    [("payment_request_id", "=", request.id)]
                )
            )

        receipt.with_user(self.finance_manager).action_received()
        receipt.invalidate_recordset()
        request.invalidate_recordset()
        self.assertEqual(receipt.state, "received")
        self.assertEqual(receipt.treasury_ledger_id.state, "posted")
        self.assertEqual(request.state, "done")
        self.assertEqual(request.terminal_cash_source_model, receipt._name)
        self.assertEqual(request.terminal_cash_source_res_id, receipt.id)
        self.assertEqual(receipt.treasury_ledger_id.payment_request_id, request)

    def test_terminal_cash_source_claim_is_private_and_immutable(self):
        with self.assertRaisesRegex(AccessError, "事实权威服务"):
            self.env["payment.request"].create(
                {
                    "name": "P1 forged cash source claim",
                    "type": "receive",
                    "project_id": self.project.id,
                    "partner_id": self.partner.id,
                    "contract_id": self.receipt_contract.id,
                    "amount": 1,
                    "terminal_cash_source_model": "sc.receipt.income",
                    "terminal_cash_source_res_id": 999999,
                }
            )
        request = self.env["payment.request"].create(
            {
                "name": "P1 protected cash source claim",
                "type": "receive",
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "contract_id": self.receipt_contract.id,
                "amount": 1,
            }
        )
        with self.assertRaisesRegex(AccessError, "事实权威服务"):
            request.write(
                {
                    "terminal_cash_source_model": "sc.receipt.income",
                    "terminal_cash_source_res_id": 999999,
                }
            )

    def test_legacy_observed_identity_cannot_duplicate_terminal_cash_owner(self):
        request = self.env["payment.request"].create(
            {
                "name": "P1 governed legacy cash owner",
                "type": "receive",
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "contract_id": self.receipt_contract.id,
                "amount": 21,
                "currency_id": self.env.company.currency_id.id,
            }
        )
        values = {
            "project_id": self.project.id,
            "company_id": self.env.company.id,
            "partner_id": self.partner.id,
            "contract_id": self.receipt_contract.id,
            "payment_request_id": request.id,
            "amount": 21,
            "currency_id": request.currency_id.id,
            "state": "legacy_confirmed",
        }
        first = self.env["sc.receipt.income"]._create_legacy_authoritative(values)
        self.assertEqual(first.finance_identity_state, "legacy_observed_identity")
        with self.assertRaisesRegex(UserError, "只能归属于一张"):
            self.env["sc.receipt.income"]._create_legacy_authoritative(values)
        deduction_category = self.env.ref(
            "smart_construction_core.business_category_finance_deduction_paid"
        )
        with self.assertRaisesRegex(UserError, "只能归属于一张"):
            self.env["sc.expense.claim"]._create_legacy_authoritative(
                {
                    "project_id": self.project.id,
                    "company_id": self.env.company.id,
                    "partner_id": self.partner.id,
                    "payment_request_id": request.id,
                    "business_category_id": deduction_category.id,
                    "claim_type": "expense",
                    "amount": 21,
                    "currency_id": request.currency_id.id,
                    "state": "legacy_confirmed",
                }
            )

        self.env.cr.execute(
            "SELECT indexname FROM pg_indexes WHERE indexname IN %s",
            [
                (
                    "sc_receipt_income_one_canonical_terminal_per_request_idx",
                    "sc_expense_claim_one_canonical_terminal_per_request_idx",
                )
            ],
        )
        self.assertEqual(len(self.env.cr.fetchall()), 2)

    def test_legacy_cash_owner_requires_full_semantic_identity(self):
        other_partner = self.env["res.partner"].create({"name": "P1 错误往来单位"})
        request = self.env["payment.request"].create(
            {
                "name": "P1 legacy identity quarantine",
                "type": "receive",
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "contract_id": self.receipt_contract.id,
                "amount": 21,
                "currency_id": self.env.company.currency_id.id,
            }
        )
        receipt = self.env["sc.receipt.income"]._create_legacy_authoritative(
            {
                "project_id": self.project.id,
                "company_id": self.env.company.id,
                "partner_id": other_partner.id,
                "contract_id": self.receipt_contract.id,
                "payment_request_id": request.id,
                "amount": 21,
                "currency_id": request.currency_id.id,
                "state": "legacy_confirmed",
            }
        )
        self.assertEqual(receipt.finance_identity_state, "legacy_unresolved_identity")
        request.invalidate_recordset(["terminal_cash_source_model", "terminal_cash_source_res_id"])
        self.assertFalse(request.terminal_cash_source_model)
        self.assertFalse(request.terminal_cash_source_res_id)

        wrong_kind_request = self.env["payment.request"].create(
            {
                "name": "P1 noncash claim quarantine",
                "type": "receive",
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "amount": 11,
                "currency_id": self.env.company.currency_id.id,
            }
        )
        claim = self.env["sc.expense.claim"]._create_legacy_authoritative(
            {
                "project_id": self.project.id,
                "company_id": self.env.company.id,
                "partner_id": self.partner.id,
                "payment_request_id": wrong_kind_request.id,
                "business_category_id": self.env.ref(
                    "smart_construction_core.business_category_finance_deduction_bill"
                ).id,
                "claim_type": "expense",
                "amount": 11,
                "currency_id": wrong_kind_request.currency_id.id,
                "state": "legacy_confirmed",
            }
        )
        self.assertEqual(claim.handling_kind, "deduction_bill")
        self.assertEqual(claim.finance_identity_state, "legacy_unresolved_identity")
        wrong_kind_request.invalidate_recordset(
            ["terminal_cash_source_model", "terminal_cash_source_res_id"]
        )
        self.assertFalse(wrong_kind_request.terminal_cash_source_model)

    def test_contract_economic_identity_freezes_when_business_evidence_exists(self):
        request = self.env["payment.request"].create(
            {
                "name": "P1 contract identity evidence",
                "type": "receive",
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "contract_id": self.receipt_contract.id,
                "amount": 8,
                "currency_id": self.env.company.currency_id.id,
            }
        )
        self.assertTrue(request)
        other_project = self.env["project.project"].create(
            {
                "name": "P1 身份漂移目标项目",
                "code": "P1-FINANCE-DRIFT",
                "company_id": self.env.company.id,
                "operation_strategy": "direct",
            }
        )
        with self.assertRaisesRegex(UserError, "不可变更"):
            self.receipt_contract.write({"project_id": other_project.id})
        self.assertEqual(self.receipt_contract.project_id, self.project)

    def test_supplement_original_contract_cannot_bypass_frozen_economic_identity(self):
        Contract = self.env["construction.contract"]
        base = Contract.create(
            {
                "subject": "P1 支出原合同",
                "type": "in",
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "company_id": self.env.company.id,
                "currency_id": self.env.company.currency_id.id,
            }
        )
        supplement = Contract.create(
            {
                "subject": "P1 支出补充合同",
                "business_category_id": self.env.ref(
                    "smart_construction_core.business_category_contract_expense_supplement"
                ).id,
                "original_contract_id": base.id,
            }
        )
        request = self.env["payment.request"].create(
            {
                "name": "P1 补充合同付款事实",
                "type": "pay",
                "project_id": supplement.project_id.id,
                "partner_id": supplement.partner_id.id,
                "contract_id": supplement.id,
                "amount": 17,
                "currency_id": supplement.currency_id.id,
                "state": "draft",
            }
        )
        request.flush_recordset(["state"])
        self.env.cr.execute(
            "UPDATE payment_request SET state = 'approved' WHERE id = %s",
            [request.id],
        )
        request.invalidate_recordset(["state"])
        ledger = request._ensure_payment_ledger(amount=17)
        self.assertEqual(
            opm.contract_actual_paid_amount_map(self.env, [supplement.id]),
            {supplement.id: 17},
        )

        other_project = self.env["project.project"].create(
            {
                "name": "P1 补充合同漂移目标",
                "code": "P1-SUPPLEMENT-DRIFT",
                "company_id": self.env.company.id,
                "operation_strategy": "direct",
            }
        )
        other_partner = self.env["res.partner"].create({"name": "P1 补充合同漂移往来单位"})
        other_base = Contract.create(
            {
                "subject": "P1 另一支出原合同",
                "type": "in",
                "project_id": other_project.id,
                "partner_id": other_partner.id,
                "company_id": self.env.company.id,
                "currency_id": self.env.company.currency_id.id,
            }
        )
        with self.assertRaisesRegex(UserError, "不可变更"):
            supplement.write({"original_contract_id": other_base.id})
        self.assertEqual(supplement.original_contract_id, base)
        self.assertEqual(supplement.project_id, self.project)
        self.assertEqual(
            opm.contract_actual_paid_amount_map(self.env, [supplement.id]),
            {supplement.id: 17},
        )
        position = self.env["sc.contract.execution.position"].search(
            [("contract_id", "=", supplement.id)]
        )
        self.assertEqual(position.cash_executed_amount, 17)
        evidence = self.env["payment.ledger.allocation"].search(
            position.action_open_cash_evidence()["domain"]
        )
        self.assertEqual(evidence.ledger_id, ledger)
        self.assertEqual(sum(evidence.mapped("allocated_amount")), position.cash_executed_amount)

    def test_received_position_flushes_same_transaction_fact_changes(self):
        request = self.env["payment.request"].create(
            {
                "name": "P1 same transaction receipt position",
                "type": "receive",
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "contract_id": self.receipt_contract.id,
                "amount": 23,
                "currency_id": self.env.company.currency_id.id,
            }
        )
        receipt = self.env["sc.receipt.income"].create(
            {
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "contract_id": self.receipt_contract.id,
                "payment_request_id": request.id,
                "amount": 23,
                "currency_id": request.currency_id.id,
            }
        )
        request._claim_terminal_cash_source(receipt)
        ledger = request._ensure_treasury_ledger(amount=23)
        receipt._write_finance_authority(
            {"state": "received", "treasury_ledger_id": ledger.id}
        )
        self.assertEqual(
            opm.contract_actual_received_position_map(
                self.env, [self.receipt_contract.id]
            ),
            {self.receipt_contract.id: {"amount": 23, "evidence_count": 1}},
        )

    def test_payment_ledger_migration_replay_preserves_snapshots_and_tuple_identity(self):
        contract = self.env["construction.contract"].create(
            {
                "subject": "P1 ledger migration contract",
                "type": "in",
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "company_id": self.env.company.id,
                "currency_id": self.env.company.currency_id.id,
            }
        )
        request = self.env["payment.request"].create(
            {
                "name": "P1 ledger migration request",
                "type": "pay",
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "contract_id": contract.id,
                "amount": 19,
                "currency_id": self.env.company.currency_id.id,
                "state": "draft",
            }
        )
        request.flush_recordset(["state"])
        self.env.cr.execute(
            "UPDATE payment_request SET state = 'approved' WHERE id = %s",
            [request.id],
        )
        request.invalidate_recordset(["state"])
        ledger = request._ensure_payment_ledger(amount=19)
        allocation = ledger.contract_allocation_ids
        migration_path = (
            Path(__file__).resolve().parents[1]
            / "migrations"
            / "17.0.0.153"
            / "pre-migration.py"
        )
        migrate = runpy.run_path(str(migration_path))["migrate"]

        self.env.cr.execute(
            "SELECT ctid::text FROM payment_ledger WHERE id = %s",
            [ledger.id],
        )
        ledger_ctid = self.env.cr.fetchone()[0]
        self.env.cr.execute(
            "SELECT ctid::text FROM payment_ledger_allocation WHERE id = %s",
            [allocation.id],
        )
        allocation_ctid = self.env.cr.fetchone()[0]
        migrate(self.env.cr, "17.0.0.152")
        migrate(self.env.cr, "17.0.0.153")
        self.env.cr.execute(
            "SELECT ctid::text FROM payment_ledger WHERE id = %s",
            [ledger.id],
        )
        self.assertEqual(self.env.cr.fetchone()[0], ledger_ctid)
        self.env.cr.execute(
            "SELECT ctid::text FROM payment_ledger_allocation WHERE id = %s",
            [allocation.id],
        )
        self.assertEqual(self.env.cr.fetchone()[0], allocation_ctid)

        original_strategy = self.project.operation_strategy
        self.project.write(
            {"operation_strategy": "joint" if original_strategy == "direct" else "direct"}
        )
        with self.assertRaisesRegex(RuntimeError, "conflicts with current authority"):
            with self.env.cr.savepoint():
                migrate(self.env.cr, "17.0.0.153")
        ledger.invalidate_recordset(["operation_strategy"])
        self.assertEqual(ledger.operation_strategy, original_strategy)
        self.project.write({"operation_strategy": original_strategy})

    def test_partial_legacy_payment_identity_is_quarantined_without_relation_guessing(self):
        self.project.write({"funding_enabled": True})
        baseline = self.env["project.funding.baseline"].create(
            {
                "project_id": self.project.id,
                "total_amount": 29,
                "period_start": "2026-01-01",
                "period_end": "2026-12-31",
                "line_ids": [(0, 0, {"name": "历史付款资金切片", "planned_amount": 29})],
            }
        )
        baseline.action_activate()
        plan_line = baseline.line_ids
        contract = self.env["construction.contract"].create(
            {
                "subject": "P1 partial legacy ledger contract",
                "type": "in",
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "company_id": self.env.company.id,
                "currency_id": self.env.company.currency_id.id,
            }
        )
        request = self.env["payment.request"].create(
            {
                "name": "P1 partial legacy ledger request",
                "type": "pay",
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "contract_id": contract.id,
                "funding_baseline_id": baseline.id,
                "amount": 29,
                "currency_id": self.env.company.currency_id.id,
                "state": "draft",
            }
        )
        request.flush_recordset(["state"])
        self.env.cr.execute(
            "UPDATE payment_request SET state = 'approved' WHERE id = %s",
            [request.id],
        )
        request.invalidate_recordset(["state"])
        ledger = request._ensure_payment_ledger(amount=29)
        allocation = ledger.contract_allocation_ids
        funding_allocation = ledger.action_allocate_funding(
            [{"plan_line_id": plan_line.id, "amount": 29}],
            "p1-partial-history-funding",
        )
        other_company = self.env["res.company"].create(
            {
                "name": "P1 历史事实隔离公司",
                "currency_id": self.env.company.currency_id.id,
            }
        )
        other_manager = self.env["res.users"].with_context(
            no_reset_password=True
        ).create(
            {
                "name": "P1 历史事实跨公司审计经理",
                "login": "p1_history_other_company_finance_manager",
                "email": "p1-history-other-company@example.invalid",
                "company_id": other_company.id,
                "company_ids": [(6, 0, [other_company.id])],
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            self.env.ref(
                                "smart_construction_core.group_sc_cap_finance_manager"
                            ).id
                        ],
                    )
                ],
            }
        )
        self.assertTrue(
            self.env["payment.ledger"].with_user(self.finance_manager).search(
                [("id", "=", ledger.id)]
            )
        )
        self.assertFalse(
            self.env["payment.ledger"].with_user(other_manager).search(
                [("id", "=", ledger.id)]
            )
        )
        original_strategy = ledger.operation_strategy
        drifted_strategy = "joint" if original_strategy == "direct" else "direct"

        self.env.cr.execute(
            "ALTER TABLE payment_ledger ALTER COLUMN normalization_state DROP NOT NULL"
        )
        self.env.cr.execute(
            "ALTER TABLE payment_ledger_allocation ALTER COLUMN normalization_state DROP NOT NULL"
        )
        self.env.cr.execute(
            """
            UPDATE payment_ledger
               SET company_id = NULL,
                   currency_id = NULL,
                   normalization_state = NULL
             WHERE id = %s
            """,
            [ledger.id],
        )
        self.env.cr.execute(
            """
            UPDATE payment_ledger_allocation
               SET company_id = NULL,
                   currency_id = NULL,
                   normalization_state = NULL,
                   allocation_state = 'allocated',
                   reason_code = 'direct_contract'
             WHERE id = %s
            """,
            [allocation.id],
        )
        self.env.cr.execute(
            "UPDATE project_project SET operation_strategy = %s WHERE id = %s",
            [drifted_strategy, self.project.id],
        )
        self.env.cr.execute(
            "UPDATE payment_request SET currency_id = %s WHERE id = %s",
            [self.other_currency.id, request.id],
        )

        migrations_root = Path(__file__).resolve().parents[1] / "migrations"
        migrations = [
            runpy.run_path(str(migrations_root / version / "pre-migration.py"))[
                "migrate"
            ]
            for version in (
                "17.0.0.152",
                "17.0.0.153",
                "17.0.0.154",
                "17.0.0.155",
                "17.0.0.156",
            )
        ]
        for migrate in migrations:
            migrate(self.env.cr, "17.0.0.151")

        self.env.cr.execute(
            """
            SELECT project_id, company_id, partner_id, currency_id,
                   operation_strategy, normalization_state, ctid::text
              FROM payment_ledger
             WHERE id = %s
            """,
            [ledger.id],
        )
        ledger_values = self.env.cr.fetchone()
        self.assertEqual(
            ledger_values[:6],
            (
                self.project.id,
                None,
                self.partner.id,
                None,
                original_strategy,
                "legacy_unresolved_identity",
            ),
        )
        self.env.cr.execute(
            """
            SELECT project_id, company_id, currency_id, allocation_state,
                   reason_code, normalization_state, ctid::text
              FROM payment_ledger_allocation
             WHERE id = %s
            """,
            [allocation.id],
        )
        allocation_values = self.env.cr.fetchone()
        self.assertEqual(
            allocation_values[:6],
            (
                self.project.id,
                None,
                None,
                "unresolved_global",
                "historical_backfill_unresolved",
                "legacy_unresolved_identity",
            ),
        )
        self.env.cr.execute(
            """
            SELECT normalization_state, ctid::text
              FROM project_funding_actual_event_allocation
             WHERE id = %s
            """,
            [funding_allocation.id],
        )
        funding_values = self.env.cr.fetchone()
        self.assertEqual(funding_values[0], "legacy_unresolved_relation")
        self.assertEqual(opm.contract_actual_paid_amount_map(self.env, [contract.id]), {})
        request.invalidate_recordset(["paid_amount_total", "unpaid_amount", "is_fully_paid"])
        self.assertEqual(request.paid_amount_total, 0)
        self.assertEqual(request.unpaid_amount, 29)
        self.assertFalse(request.is_fully_paid)
        with self.assertRaisesRegex(UserError, "身份待确认或身份冲突"):
            request._check_can_done()
        with self.assertRaisesRegex(UserError, "身份待确认或身份冲突"):
            request._assert_payment_execution_ready()
        native_summary = PaymentSliceNativeAdapter(self.env).summary(self.project)
        self.assertEqual(native_summary["ledger_count"], 0)
        self.assertEqual(native_summary["executed_payment_amount"], 0)
        baseline.invalidate_recordset(["allocated_amount", "remaining_amount"])
        plan_line.invalidate_recordset(["allocated_amount", "remaining_amount"])
        ledger.invalidate_recordset(["fund_plan_allocated_amount", "fund_plan_unallocated_amount"])
        self.assertEqual((baseline.allocated_amount, baseline.remaining_amount), (0, 29))
        self.assertEqual((plan_line.allocated_amount, plan_line.remaining_amount), (0, 29))
        self.assertEqual((ledger.fund_plan_allocated_amount, ledger.fund_plan_unallocated_amount), (0, 29))
        recon = self.env["sc.contract.recon.summary"].create({"contract_id": contract.id})
        self.assertEqual((recon.payment_total, recon.payment_ids_count), (0, 0))
        position = self.env["sc.contract.execution.position"].search(
            [("contract_id", "=", contract.id)]
        )
        self.assertEqual(position.cash_executed_amount, 0)
        evidence_action = position.action_open_cash_evidence()
        self.assertFalse(
            self.env["payment.ledger.allocation"].search(evidence_action["domain"])
        )
        self.assertFalse(
            self.env["payment.ledger"].with_user(self.finance_manager).search(
                [("id", "=", ledger.id)]
            )
        )
        self.assertFalse(
            self.env["payment.ledger.allocation"].with_user(self.finance_manager).search(
                [("id", "=", allocation.id)]
            )
        )
        self.assertFalse(
            self.env["payment.ledger"].with_user(other_manager).search(
                [("id", "=", ledger.id)]
            )
        )
        self.assertFalse(
            self.env["payment.ledger.allocation"].with_user(other_manager).search(
                [("id", "=", allocation.id)]
            )
        )
        evidence_action = self.env.ref(
            "smart_construction_core.action_payment_ledger_allocation_evidence"
        )
        evidence_menu = self.env.ref(
            "smart_construction_core.menu_payment_ledger_allocation_evidence"
        )
        self.assertEqual(evidence_action.res_model, "payment.ledger.allocation")
        self.assertEqual(evidence_menu.action, evidence_action)

        for migrate in migrations:
            migrate(self.env.cr, "17.0.0.155")
        self.env.cr.execute(
            "SELECT ctid::text FROM payment_ledger WHERE id = %s",
            [ledger.id],
        )
        self.assertEqual(self.env.cr.fetchone()[0], ledger_values[6])
        self.env.cr.execute(
            "SELECT ctid::text FROM payment_ledger_allocation WHERE id = %s",
            [allocation.id],
        )
        self.assertEqual(self.env.cr.fetchone()[0], allocation_values[6])
        self.env.cr.execute(
            "SELECT ctid::text FROM project_funding_actual_event_allocation WHERE id = %s",
            [funding_allocation.id],
        )
        self.assertEqual(self.env.cr.fetchone()[0], funding_values[1])

    def test_observed_payment_identity_mismatch_blocks_totals_and_new_execution(self):
        contract = self.env["construction.contract"].create(
            {
                "subject": "P1 observed mismatch contract",
                "type": "in",
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "company_id": self.env.company.id,
                "currency_id": self.env.company.currency_id.id,
            }
        )
        request = self.env["payment.request"].create(
            {
                "name": "P1 observed mismatch request",
                "type": "pay",
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "contract_id": contract.id,
                "amount": 31,
                "currency_id": self.env.company.currency_id.id,
                "state": "draft",
            }
        )
        request.flush_recordset(["state"])
        self.env.cr.execute(
            "UPDATE payment_request SET state = 'approved' WHERE id = %s", [request.id]
        )
        request.invalidate_recordset(["state"])
        ledger = request._ensure_payment_ledger(amount=31)
        self.env.cr.execute(
            """
            UPDATE payment_ledger
               SET currency_id = %s,
                   normalization_state = 'legacy_observed_identity'
             WHERE id = %s
            """,
            [self.other_currency.id, ledger.id],
        )
        ledger.invalidate_recordset(["currency_id", "normalization_state"])
        request.invalidate_recordset(["paid_amount_total", "unpaid_amount", "is_fully_paid"])
        self.assertEqual((request.paid_amount_total, request.unpaid_amount), (0, 31))
        self.assertFalse(request.is_fully_paid)
        with self.assertRaisesRegex(UserError, "身份待确认或身份冲突"):
            request._assert_payment_execution_ready()
        with self.assertRaisesRegex(UserError, "身份待确认或身份冲突"):
            self.env["payment.ledger"]._create_authoritative(
                {
                    "payment_request_id": request.id,
                    "amount": 1,
                    "state": "posted",
                }
            )

    def test_existing_ambiguous_ledger_blocks_payment_action_before_state_change(self):
        contract = self.env["construction.contract"].create(
            {
                "subject": "P1 existing ambiguous ledger contract",
                "type": "in",
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "company_id": self.env.company.id,
                "currency_id": self.env.company.currency_id.id,
            }
        )
        request = self.env["payment.request"].create(
            {
                "name": "P1 existing ambiguous ledger request",
                "type": "pay",
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "contract_id": contract.id,
                "amount": 29,
                "currency_id": self.env.company.currency_id.id,
                "payment_account_name": "P1 ambiguous payee",
                "payment_bank_name": "P1 ambiguous bank",
                "payment_account_no": "P1-AMBIGUOUS-ACCOUNT",
            }
        )
        self.env.cr.execute(
            "UPDATE payment_request SET state = 'approved', validation_status = 'validated' WHERE id = %s",
            [request.id],
        )
        request.invalidate_recordset(["state", "validation_status"])
        execution = self.env["sc.payment.execution"].create(
            {"payment_request_id": request.id, "state": "confirmed", "paid_amount": 29}
        )
        ledger = request._ensure_payment_ledger(amount=29, execution=execution)
        self.env.cr.execute(
            "UPDATE payment_ledger SET normalization_state = 'legacy_unresolved_identity' WHERE id = %s",
            [ledger.id],
        )
        ledger.invalidate_recordset(["normalization_state"])
        with self.assertRaisesRegex(UserError, "身份待确认或身份冲突"):
            request._ensure_payment_ledger(amount=29, execution=execution)
        with self.assertRaisesRegex(UserError, "身份待确认或身份冲突"):
            execution.action_paid()
        execution.invalidate_recordset(["state"])
        self.assertEqual(execution.state, "confirmed")

    def test_replayed_index_migrations_do_not_rebuild_matching_indexes(self):
        migrations_root = Path(__file__).resolve().parents[1] / "migrations"
        migrations = [
            runpy.run_path(str(migrations_root / version / "post-migration.py"))[
                "migrate"
            ]
            for version in ("17.0.0.150", "17.0.0.151")
        ]
        for migrate in migrations:
            migrate(self.env.cr, "17.0.0.149")
        index_names = [
            "sc_treasury_ledger_posted_payment_identity_idx",
            "sc_expense_claim_one_canonical_terminal_per_request_idx",
        ]
        self.env.cr.execute(
            "SELECT relname, pg_relation_filenode(oid) FROM pg_class WHERE relname = ANY(%s)",
            [index_names],
        )
        before = dict(self.env.cr.fetchall())
        self.assertEqual(set(before), set(index_names))
        for migrate in migrations:
            migrate(self.env.cr, "17.0.0.151")
        self.env.cr.execute(
            "SELECT relname, pg_relation_filenode(oid) FROM pg_class WHERE relname = ANY(%s)",
            [index_names],
        )
        self.assertEqual(dict(self.env.cr.fetchall()), before)

    def test_contract_receipt_position_requires_exact_owned_ledger(self):
        request = self.env["payment.request"].create(
            {
                "name": "P1 exact receipt ledger",
                "type": "receive",
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "contract_id": self.receipt_contract.id,
                "amount": 50,
                "currency_id": self.env.company.currency_id.id,
            }
        )
        receipt = self.env["sc.receipt.income"].create(
            {
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "contract_id": self.receipt_contract.id,
                "payment_request_id": request.id,
                "amount": 50,
                "currency_id": request.currency_id.id,
            }
        )
        request._claim_terminal_cash_source(receipt)
        rogue = self.env["sc.treasury.ledger"]._create_authoritative(
            {
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "payment_request_id": request.id,
                "source_model": "p1.rogue.source",
                "source_res_id": request.id,
                "direction": "in",
                "amount": 999,
                "currency_id": request.currency_id.id,
                "state": "posted",
            }
        )
        receipt._write_finance_authority({"state": "received", "treasury_ledger_id": rogue.id})
        position = self.env["sc.contract.execution.position"].search(
            [("contract_id", "=", self.receipt_contract.id)]
        )
        self.assertEqual(position.cash_executed_amount, 0)
        evidence = self.env["sc.treasury.ledger"].search(
            position.action_open_cash_evidence()["domain"]
        )
        self.assertNotIn(rogue, evidence)
        self.assertEqual(sum(evidence.mapped("amount")), position.cash_executed_amount)

    def test_concurrent_terminal_cash_sources_serialize_to_one_owner(self):
        registry = Registry(self.env.cr.dbname)
        with registry.cursor() as setup_cursor:
            setup_env = api.Environment(setup_cursor, SUPERUSER_ID, {})
            contract = setup_env["construction.contract"].search(
                [
                    ("type", "=", "out"),
                    ("project_id", "!=", False),
                    ("partner_id", "!=", False),
                    ("company_id", "!=", False),
                ],
                order="id",
                limit=1,
            )
            self.assertTrue(
                contract,
                "governed local.dev fixture must provide an income contract",
            )
            project = contract.project_id
            partner = contract.partner_id
            request = setup_env["payment.request"].create(
                {
                    "name": "P1-CASH-SOURCE-RACE-" + uuid.uuid4().hex[:8],
                    "type": "receive",
                    "project_id": project.id,
                    "partner_id": partner.id,
                    "contract_id": contract.id,
                    "amount": 31,
                    "currency_id": project.company_id.currency_id.id,
                }
            )
            receipt_values = {
                "project_id": project.id,
                "company_id": project.company_id.id,
                "partner_id": partner.id,
                "contract_id": contract.id,
                "payment_request_id": request.id,
                "amount": 31,
                "currency_id": request.currency_id.id,
                "state": "legacy_confirmed",
            }
            expense_values = {
                "project_id": project.id,
                "company_id": project.company_id.id,
                "partner_id": partner.id,
                "payment_request_id": request.id,
                "business_category_id": setup_env.ref(
                    "smart_construction_core.business_category_finance_deduction_paid"
                ).id,
                "claim_type": "expense",
                "amount": 31,
                "currency_id": request.currency_id.id,
                "state": "legacy_confirmed",
            }
            request_id = request.id
            setup_cursor.commit()
        self.addCleanup(self._cleanup_committed_cash_source_race, request_id)

        started = threading.Event()
        finished = threading.Event()
        result = []
        errors = []
        serialization_failures = []

        def create_competing_expense():
            try:
                for attempt in range(2):
                    cursor = registry.cursor()
                    try:
                        started.set()
                        env = api.Environment(cursor, SUPERUSER_ID, {})
                        env["sc.expense.claim"]._create_legacy_authoritative(
                            expense_values
                        )
                        cursor.commit()
                        result.append("created")
                        return
                    except SerializationFailure:
                        cursor.rollback()
                        serialization_failures.append(attempt)
                        if attempt:
                            raise
                    except UserError:
                        cursor.rollback()
                        result.append("rejected")
                        return
                    finally:
                        cursor.close()
            except Exception as exc:  # pragma: no cover - asserted by parent
                errors.append(exc)
            finally:
                finished.set()

        first_cursor = registry.cursor()
        try:
            first_env = api.Environment(first_cursor, SUPERUSER_ID, {})
            first_env["sc.receipt.income"]._create_legacy_authoritative(
                receipt_values
            )
            competing = threading.Thread(target=create_competing_expense)
            competing.start()
            self.assertTrue(started.wait(5))
            self.assertFalse(
                finished.wait(0.2),
                "competing terminal source must wait for the payment-request authority lock",
            )
            first_cursor.commit()
            competing.join(10)
            self.assertFalse(competing.is_alive())
            self.assertFalse(errors)
            self.assertEqual(result, ["rejected"])
            self.assertEqual(
                serialization_failures,
                [0],
                "the blocked old-snapshot contender must prove a real serialization retry",
            )
        finally:
            first_cursor.close()

        with registry.cursor() as verify_cursor:
            verify_env = api.Environment(verify_cursor, SUPERUSER_ID, {})
            self.assertEqual(
                verify_env["sc.receipt.income"].search_count(
                    [("payment_request_id", "=", request_id)]
                ),
                1,
            )
            self.assertEqual(
                verify_env["sc.expense.claim"].search_count(
                    [("payment_request_id", "=", request_id)]
                ),
                0,
            )

    def test_cash_source_currency_must_match_request(self):
        request = self.env["payment.request"].create(
            {
                "name": "P1 currency locked request",
                "type": "receive",
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "contract_id": self.receipt_contract.id,
                "amount": 10,
                "currency_id": self.env.company.currency_id.id,
            }
        )
        receipt = self.env["sc.receipt.income"].create(
            {
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "payment_request_id": request.id,
                "amount": 10,
                "currency_id": self.other_currency.id,
            }
        )
        with self.assertRaisesRegex(UserError, "币种不一致"):
            request._claim_terminal_cash_source(receipt)

    def test_legacy_terminal_create_requires_private_import_authority(self):
        cases = (
            ("sc.expense.claim", {"amount": 1, "state": "legacy_confirmed"}),
            ("sc.receipt.income", {"amount": 1, "state": "legacy_confirmed"}),
            (
                "sc.self.funding.registration",
                {"partner_id": self.partner.id, "amount": 1, "state": "done"},
            ),
            (
                "sc.tax.deduction.registration",
                {"deduction_amount": 1, "state": "legacy_confirmed"},
            ),
        )
        for model_name, values in cases:
            with self.subTest(model=model_name), self.assertRaisesRegex(UserError, "受治理迁移载体"):
                self.env[model_name].create(dict(values, project_id=self.project.id, source_origin="legacy"))

        unresolved = self.env["sc.receipt.income"]._create_legacy_authoritative(
            {
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "amount": 9,
                "state": "legacy_confirmed",
            }
        )
        self.assertEqual(unresolved.finance_identity_state, "legacy_unresolved_identity")
        self.assertFalse(
            self.env["sc.finance.business.fact"].search(
                [("source_model", "=", unresolved._name), ("source_res_id", "=", unresolved.id)]
            )
        )

    def test_deduction_paid_uses_authoritative_handling_kind(self):
        category = self.env.ref("smart_construction_core.business_category_finance_deduction_paid")
        request = self.env["payment.request"].create(
            {
                "name": "P1 deduction paid request",
                "type": "receive",
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "amount": 12,
                "currency_id": self.env.company.currency_id.id,
            }
        )
        claim = self.env["sc.expense.claim"].create(
            {
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "business_category_id": category.id,
                "claim_type": "expense",
                "amount": 12,
                "currency_id": request.currency_id.id,
                "payment_request_id": request.id,
            }
        )
        self.assertEqual(claim.handling_kind, "deduction_paid")
        request._claim_terminal_cash_source(claim)
        ledger = request._ensure_treasury_ledger(amount=12)
        claim._write_finance_authority({"state": "done"})
        fact = self.env["sc.finance.business.fact"].search(
            [("source_model", "=", claim._name), ("source_res_id", "=", claim.id)]
        )
        self.assertEqual(fact.fact_type, "deduction_paid")
        self.assertEqual(fact.cash_in_amount, ledger.amount)

    def test_native_actions_preserve_identity_and_source_acl(self):
        receipt, _ledger = self._receipt(18)
        fact = self.env["sc.finance.business.fact"].search(
            [("source_model", "=", receipt._name), ("source_res_id", "=", receipt.id)]
        )
        self.assertEqual(fact.action_open_source_record()["res_id"], receipt.id)
        self.assertEqual(
            fact.with_user(self.finance_manager).action_open_source_record()["res_id"],
            receipt.id,
        )
        with self.assertRaises(AccessError):
            fact.with_user(self.reader).action_open_source_record()

        fact_action = self.env.ref("smart_construction_core.action_sc_finance_business_fact")
        summary_action = self.env.ref("smart_construction_core.action_sc_finance_business_project_summary")
        for action in (fact_action, summary_action):
            context = action.context
            self.assertIn("search_default_group_company", context)
            self.assertIn("search_default_group_currency", context)
            self.assertIn("search_default_group_project", context)
        summary_selection = dict(self.env["sc.finance.business.project.summary"]._fields["business_domain"].selection)
        self.assertIn("deduction_registration", summary_selection)

    def test_interfund_drilldown_keeps_company_and_currency_slice(self):
        position = self.env["sc.finance.project.counterparty.position"].new(
            {
                "project_id": self.project.id,
                "company_id": self.env.company.id,
                "currency_id": self.env.company.currency_id.id,
                "counterparty_type": "unknown",
            }
        )
        domain = position._interfund_fact_counterparty_domain()
        self.assertIn(("company_id", "=", self.env.company.id), domain)
        self.assertIn(("currency_id", "=", self.env.company.currency_id.id), domain)
