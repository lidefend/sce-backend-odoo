# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "sc_gate", "p1_income_contract")
class TestP1IncomeContractCapability(TransactionCase):
    def _create_contract(self):
        project = self.env["project.project"].create(
            {
                "name": "P1 Income Contract Project",
                "company_id": self.env.company.id,
            }
        )
        partner = self.env["res.partner"].create(
            {"name": "P1 Income Contract Counterparty", "customer_rank": 1}
        )
        contract = self.env["construction.contract"].create(
            {
                "subject": "P1 Income Contract",
                "type": "out",
                "project_id": project.id,
                "partner_id": partner.id,
            }
        )
        wrapper = self.env["construction.contract.income"].search(
            [("contract_id", "=", contract.id)]
        )
        return project, partner, contract, wrapper

    def test_income_contract_exposes_source_to_result_navigation(self):
        project, partner, contract, wrapper = self._create_contract()
        invoice = self.env["sc.invoice.registration"].create(
            {
                "name": "P1-CONTRACT-INVOICE-001",
                "project_id": project.id,
                "partner_id": partner.id,
                "contract_id": contract.id,
                "direction": "output",
                "source_kind": "output_invoice_tax",
                "amount_total": 3600,
            }
        )
        receipt = self.env["sc.receipt.income"].create(
            {
                "name": "P1-CONTRACT-RECEIPT-001",
                "project_id": project.id,
                "partner_id": partner.id,
                "contract_id": contract.id,
                "amount": 1800,
            }
        )
        self.assertEqual(contract.invoice_registration_count, 1)
        self.assertEqual(contract.receipt_income_count, 1)
        self.assertEqual(wrapper.invoice_registration_count, 1)
        self.assertEqual(wrapper.receipt_income_count, 1)

        invoice_action = wrapper.action_open_invoice_registrations()
        self.assertEqual(invoice_action["domain"], [("contract_id", "=", contract.id)])
        self.assertEqual(invoice_action["context"]["default_direction"], "output")
        self.assertEqual(invoice_action["context"]["default_partner_id"], partner.id)
        receipt_action = wrapper.action_open_receipt_incomes()
        self.assertEqual(receipt_action["domain"], [("contract_id", "=", contract.id)])
        self.assertEqual(receipt_action["context"]["default_partner_id"], partner.id)
        self.assertTrue(invoice.exists())
        self.assertTrue(receipt.exists())

    def test_income_contract_form_has_four_business_drilldowns(self):
        form = self.env.ref("smart_construction_core.view_construction_contract_income_form")
        for method_name in (
            "action_open_settlements",
            "action_open_payment_requests",
            "action_open_invoice_registrations",
            "action_open_receipt_incomes",
        ):
            self.assertIn(f'name="{method_name}"', form.arch_db)
