# -*- coding: utf-8 -*-
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "sc_gate", "p1_master_data")
class TestP1MasterDataCapability(TransactionCase):
    def test_partner_business_trace_uses_authoritative_documents(self):
        project = self.env["project.project"].create({"name": "P1 Master Data Project"})
        partner = self.env["res.partner"].create(
            {"name": "P1 Master Data Counterparty", "customer_rank": 1}
        )
        receipt = self.env["sc.receipt.income"].create(
            {
                "project_id": project.id,
                "partner_id": partner.id,
                "name": "P1-MD-RECEIPT-001",
                "amount": 1250,
            }
        )
        self.env["sc.receipt.income"].flush_model()

        lines = self.env["sc.partner.business.fact.line"].search(
            [("partner_id", "=", partner.id)]
        )
        receipt_line = lines.filtered(
            lambda line: line.source_model == "sc.receipt.income"
            and line.source_res_id == receipt.id
        )
        self.assertEqual(len(receipt_line), 1)
        self.assertEqual(receipt_line.business_role, "customer")
        self.assertEqual(receipt_line.source_label, "收款登记")
        self.assertEqual(receipt_line.amount, 1250)
        self.assertEqual(partner.sc_source_fact_count, 1)

        action = partner.action_open_sc_partner_business_fact_lines()
        self.assertEqual(
            action["id"],
            self.env.ref("smart_construction_core.action_sc_partner_business_fact_line").id,
        )
        self.assertEqual(action["domain"], [("partner_id", "=", partner.id)])
        self.assertFalse(action["context"]["create"])

    def test_customer_native_form_exposes_trace_without_historical_aliases(self):
        form = self.env.ref("smart_construction_core.view_sc_customer_partner_form")
        self.assertIn('name="action_open_sc_partner_business_fact_lines"', form.arch_db)
        self.assertIn('name="sc_business_fact_line_ids"', form.arch_db)
        self.assertIn('name="sc_source_fact_count"', form.arch_db)
        self.assertIn('name="sc_transaction_eligibility"', form.arch_db)
        self.assertIn('name="action_open_source_record"', form.arch_db)
        self.assertNotIn('name="legacy_partner_id"', form.arch_db)
        self.assertNotIn('name="legacy_partner_source"', form.arch_db)

    def test_partner_transaction_eligibility_is_reusable_backend_control(self):
        partner = self.env["res.partner"].create(
            {"name": "P1 Eligibility Counterparty", "customer_rank": 1}
        )
        self.assertEqual(partner.sc_transaction_eligibility, "eligible")
        self.assertTrue(partner._sc_assert_transaction_eligible("收入合同"))

        partner.write(
            {
                "sc_blacklisted": True,
                "sc_blacklist_level": "restricted",
                "sc_blacklist_reason": "需复核授信条件",
            }
        )
        self.assertEqual(partner.sc_transaction_eligibility, "review_required")
        self.assertTrue(partner._sc_assert_transaction_eligible("收入合同"))

        partner.sc_blacklist_level = "blocked"
        self.assertEqual(partner.sc_transaction_eligibility, "blocked")
        with self.assertRaisesRegex(UserError, "无法发起收入合同"):
            partner._sc_assert_transaction_eligible("收入合同")

        partner.write({"sc_blacklisted": False, "active": False})
        self.assertEqual(partner.sc_transaction_eligibility, "blocked")
        self.assertIn("已归档", partner.sc_transaction_eligibility_reason)

    def test_default_tax_rate_has_authoritative_backend_boundary(self):
        with self.assertRaisesRegex(ValidationError, "0% 到 100%"):
            self.env["res.partner"].create(
                {
                    "name": "P1 Invalid Tax Rate Counterparty",
                    "customer_rank": 1,
                    "sc_default_tax_rate": 101,
                }
            )

    def test_duplicate_tax_identity_warns_without_destroying_recovery_path(self):
        original = self.env["res.partner"].create(
            {
                "name": "P1 Original Identity",
                "is_company": True,
                "customer_rank": 1,
                "vat": "P1DUPLICATE001",
            }
        )
        duplicate = self.env["res.partner"].create(
            {
                "name": "P1 Duplicate Identity",
                "is_company": True,
                "customer_rank": 1,
                "vat": "P1DUPLICATE001",
            }
        )
        self.assertTrue(duplicate.exists())
        self.assertEqual(duplicate.same_vat_partner_id, original)

    def test_invoice_is_included_in_counterparty_business_panorama(self):
        project = self.env["project.project"].create(
            {
                "name": "P1 Invoice Panorama Project",
                "company_id": self.env.company.id,
            }
        )
        partner = self.env["res.partner"].create(
            {"name": "P1 Invoice Panorama Counterparty", "customer_rank": 1}
        )
        invoice = self.env["sc.invoice.registration"].create(
            {
                "name": "P1-MD-INVOICE-001",
                "project_id": project.id,
                "partner_id": partner.id,
                "direction": "output",
                "source_kind": "output_invoice_tax",
                "invoice_no": "INV-P1-001",
                "amount_total": 2600,
            }
        )
        self.env["sc.invoice.registration"].flush_model()

        line = self.env["sc.partner.business.fact.line"].search(
            [
                ("source_model", "=", "sc.invoice.registration"),
                ("source_res_id", "=", invoice.id),
            ]
        )
        self.assertEqual(len(line), 1)
        self.assertEqual(line.source_label, "销项发票")
        self.assertEqual(line.business_role, "customer")
        self.assertEqual(line.company_id, project.company_id)
        self.assertEqual(line.amount, 2600)

    def test_business_panorama_has_company_scope_rule(self):
        rule = self.env.ref(
            "smart_construction_core.rule_sc_partner_business_fact_line_company"
        )
        self.assertEqual(rule.domain_force, "[('company_id', 'in', company_ids)]")

    def test_blocked_counterparty_cannot_activate_new_contract(self):
        project = self.env["project.project"].create(
            {
                "name": "P1 Contract Eligibility Project",
                "company_id": self.env.company.id,
            }
        )
        partner = self.env["res.partner"].create(
            {
                "name": "P1 Blocked Contract Counterparty",
                "customer_rank": 1,
                "sc_blacklisted": True,
                "sc_blacklist_level": "blocked",
                "sc_blacklist_reason": "停止新合作",
            }
        )
        contract = self.env["construction.contract"].create(
            {
                "subject": "P1 Blocked Income Contract",
                "type": "out",
                "project_id": project.id,
                "partner_id": partner.id,
            }
        )
        with self.assertRaisesRegex(UserError, "无法发起收入合同"):
            contract.action_confirm()
        self.assertEqual(contract.state, "draft")
