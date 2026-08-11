# -*- coding: utf-8 -*-
from odoo import Command
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "sc_gate", "tax_filing")
class TestTaxFiling(TransactionCase):
    def test_period_source_calculation_and_contract(self):
        self.env.ref("smart_construction_core.group_sc_cap_finance_manager").write({"users": [Command.link(self.env.user.id)]})
        project = self.env["project.project"].create({"name": "税务申报测试项目", "company_id": self.env.company.id})
        common = {"project_id": project.id, "invoice_date": "2026-07-15", "state": "confirmed", "amount_total": 1000}
        self.env["sc.invoice.registration"].create({**common, "name": "OUT-1", "direction": "output", "source_kind": "output_invoice_tax", "tax_amount": 100, "surcharge_amount": 5})
        self.env["sc.invoice.registration"].create({**common, "name": "PRE-1", "direction": "prepaid", "source_kind": "prepaid_tax", "tax_amount": 10, "tax_certificate_no": "CERT-1"})
        self.env["sc.tax.deduction.registration"].create({"name": "DED-1", "project_id": project.id, "state": "confirmed", "document_date": "2026-07-20", "deduction_tax_amount": 30})
        filing = self.env["sc.tax.filing"].create({"company_id": self.env.company.id, "period_start": "2026-07-01", "period_end": "2026-07-31"})
        filing.action_calculate()
        self.assertEqual(filing.output_tax_amount, 100)
        self.assertEqual(filing.prepaid_tax_amount, 10)
        self.assertEqual(filing.deductible_tax_amount, 30)
        self.assertEqual(filing.vat_payable_amount, 60)
        filing.action_submit(); filing.action_accept()
        self.assertEqual(filing.state, "accepted")
        action = self.env.ref("smart_construction_core.action_sc_product_tax_filing_v1")
        self.assertEqual(action.res_model, "sc.tax.filing")
        self.assertEqual(self.env.ref("smart_construction_core.business_config_contract_tax_filing_form_v1").action_id, action)
