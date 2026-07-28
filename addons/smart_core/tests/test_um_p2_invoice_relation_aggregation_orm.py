# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "admin_vis_p3_project_record_rule_orm")
class TestUmP2InvoiceRelationAggregationOrm(TransactionCase):
    """Real-ORM coverage for type-specific invoice relation aggregation."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.ref("base.main_company")
        cls.company_b = cls.env["res.company"].create(
            {"name": "UM-P2 S04 company B"}
        )
        base_user = cls.env.ref("base.group_user")
        finance_user = cls.env.ref(
            "smart_construction_core.group_sc_role_finance_user"
        )
        cls.caller = cls.env["res.users"].with_context(
            no_reset_password=True
        ).create(
            {
                "name": "UM-P2 S04 finance caller",
                "login": "um_p2_s04_invoice_caller",
                "email": "um_p2_s04@example.invalid",
                "company_id": cls.company_a.id,
                "company_ids": [(6, 0, [cls.company_a.id])],
                "groups_id": [(6, 0, [base_user.id, finance_user.id])],
            }
        )
        cls.context = {
            **cls.env.context,
            "allowed_company_ids": [cls.company_a.id, cls.company_b.id],
            "mail_create_nosubscribe": True,
            "mail_notify_noemail": True,
            "mail_auto_subscribe_no_notify": True,
            "tracking_disable": True,
        }
        Project = cls.env["project.project"].with_context(cls.context)
        cls.project_a = Project.create(
            {
                "name": "UM-P2 S04 project A",
                "company_id": cls.company_a.id,
                "privacy_visibility": "followers",
                "user_id": cls.caller.id,
            }
        )
        cls.project_b = Project.create(
            {
                "name": "UM-P2 S04 project B",
                "company_id": cls.company_b.id,
                "privacy_visibility": "followers",
                "user_id": cls.env.user.id,
            }
        )
        cls.partners = [
            cls.env["res.partner"].create(
                {"name": f"UM-P2 S04 partner {index}"}
            )
            for index in (1, 2)
        ]
        purchase_tax = cls.env["account.tax"].search(
            [("type_tax_use", "in", ("purchase", "none"))], limit=1
        )
        sale_tax = cls.env["account.tax"].search(
            [("type_tax_use", "in", ("sale", "none"))], limit=1
        )

        def contract(label, contract_type, project, partner, tax):
            return cls.env["construction.contract"].with_context(
                cls.context
            ).create(
                {
                    "subject": f"UM-P2 S04 {label} contract",
                    "type": contract_type,
                    "project_id": project.id,
                    "company_id": project.company_id.id,
                    "partner_id": partner.id,
                    "tax_id": tax.id,
                }
            )

        cls.input_contract = contract(
            "input", "in", cls.project_a, cls.partners[0], purchase_tax
        )
        cls.output_contract = contract(
            "output", "out", cls.project_a, cls.partners[1], sale_tax
        )
        cls.hidden_contract = contract(
            "hidden", "in", cls.project_b, cls.partners[0], purchase_tax
        )

        def settlement(label, settlement_type, contract_record, partner):
            return cls.env["sc.settlement.order"].with_context(
                cls.context
            ).create(
                {
                    "project_id": contract_record.project_id.id,
                    "company_id": contract_record.company_id.id,
                    "contract_id": contract_record.id,
                    "partner_id": partner.id,
                    "settlement_type": settlement_type,
                    "title": f"UM-P2 S04 {label} settlement",
                    "line_ids": [(0, 0, {"name": label, "amount": 100.0})],
                }
            )

        cls.input_settlement = settlement(
            "input", "out", cls.input_contract, cls.partners[0]
        )
        cls.output_settlement = settlement(
            "output", "in", cls.output_contract, cls.partners[1]
        )
        cls.receive_request = cls.env["payment.request"].with_context(
            cls.context
        ).create(
            {
                "name": "UM-P2 S04 receive request",
                "type": "receive",
                "project_id": cls.project_a.id,
                "contract_id": cls.output_contract.id,
                "partner_id": cls.partners[1].id,
                "amount": 100.0,
            }
        )
        cls.pay_request = cls.env["payment.request"].with_context(
            cls.context
        ).create(
            {
                "name": "UM-P2 S04 pay request",
                "type": "pay",
                "project_id": cls.project_a.id,
                "settlement_id": cls.input_settlement.id,
                "partner_id": cls.partners[0].id,
                "amount": 100.0,
            }
        )
        cls.caller_env = cls.env(
            user=cls.caller,
            context={
                **cls.env.context,
                "allowed_company_ids": [cls.company_a.id],
                "tracking_disable": True,
            },
        )

    def _invoice(self, source_kind, **values):
        directions = {
            "invoice_registration": "input",
            "input_invoice_tax": "input",
            "output_invoice_tax": "output",
            "prepaid_tax": "prepaid",
        }
        invoice_values = {
            "source_kind": source_kind,
            "direction": directions[source_kind],
            "project_id": self.project_a.id,
            "invoice_date": "2026-07-26",
            "invoice_no": f"UM-P2-S04-{source_kind}",
            "amount_total": 100.0,
        }
        if source_kind == "prepaid_tax":
            invoice_values.pop("invoice_no")
            invoice_values["tax_certificate_no"] = "UM-P2-S04-TAX"
        invoice_values.update(values)
        return self.caller_env["sc.invoice.registration"].create(
            invoice_values
        )

    def test_exact_source_kind_enum_and_type_specific_paths(self):
        self.assertEqual(
            [value for value, _label in self.env[
                "sc.invoice.registration"
            ]._fields["source_kind"].selection],
            [
                "invoice_registration",
                "input_invoice_tax",
                "output_invoice_tax",
                "prepaid_tax",
            ],
        )
        for source_kind in (
            "invoice_registration",
            "input_invoice_tax",
            "output_invoice_tax",
            "prepaid_tax",
        ):
            invoice = self._invoice(source_kind)
            self.assertEqual(invoice.source_kind, source_kind)

    def test_input_and_output_settlement_basis_derives_unique_relation(self):
        input_invoice = self._invoice(
            "input_invoice_tax", settlement_id=self.input_settlement.id
        )
        output_invoice = self._invoice(
            "output_invoice_tax", settlement_id=self.output_settlement.id
        )
        self.assertEqual(input_invoice.contract_id, self.input_contract)
        self.assertEqual(input_invoice.partner_id, self.partners[0])
        self.assertEqual(output_invoice.contract_id, self.output_contract)
        self.assertEqual(output_invoice.partner_id, self.partners[1])

    def test_explicit_contract_and_counterparty_conflicts_are_rejected(self):
        with self.assertRaises(UserError):
            self._invoice(
                "input_invoice_tax",
                settlement_id=self.input_settlement.id,
                contract_id=self.output_contract.id,
            )
        with self.assertRaises(UserError):
            self._invoice(
                "input_invoice_tax",
                settlement_id=self.input_settlement.id,
                partner_id=self.partners[1].id,
            )

    def test_prepaid_tax_without_formal_contract_stays_unaggregated(self):
        invoice = self._invoice(
            "prepaid_tax", partner_id=self.partners[0].id
        )
        self.assertFalse(invoice.contract_id)
        self.assertFalse(invoice.settlement_id)
        self.assertEqual(invoice.partner_id, self.partners[0])

    def test_source_kind_change_revalidates_stale_relations(self):
        invoice = self._invoice(
            "input_invoice_tax", settlement_id=self.input_settlement.id
        )
        with self.assertRaises(UserError):
            invoice.write({"source_kind": "output_invoice_tax"})
        with self.assertRaises(UserError):
            invoice.write(
                {
                    "source_kind": "output_invoice_tax",
                    "direction": "output",
                }
            )

    def test_receipt_invoice_line_uses_receive_request_chain(self):
        line = self.caller_env["sc.receipt.invoice.line"].create(
            {
                "request_id": self.receive_request.id,
                "legacy_invoice_line_id": "UM-P2-S04-LINE",
                "legacy_receipt_id": "UM-P2-S04-REQUEST",
                "invoice_no": "UM-P2-S04-OUTPUT",
                "invoice_amount": 100.0,
            }
        )
        self.assertEqual(line.project_id, self.project_a)
        self.assertEqual(line.contract_id, self.output_contract)
        self.assertEqual(line.partner_id, self.partners[1])
        with self.assertRaises(AccessError):
            self.caller_env["sc.receipt.invoice.line"].create(
                {
                    "request_id": self.pay_request.id,
                    "legacy_invoice_line_id": "UM-P2-S04-PAY-LINE",
                    "legacy_receipt_id": "UM-P2-S04-PAY",
                    "invoice_amount": 10.0,
                }
            )

    def test_cross_company_and_nonexistent_contracts_are_equivalent(self):
        nonexistent_id = self.hidden_contract.id + 1000000
        observations = []
        for contract_id in (self.hidden_contract.id, nonexistent_id):
            with self.assertRaises(AccessError) as raised:
                self._invoice(
                    "input_invoice_tax", contract_id=contract_id
                )
            observations.append((type(raised.exception), str(raised.exception)))
        self.assertEqual(observations[0], observations[1])

    def test_tax_deduction_text_invoice_number_never_creates_relation(self):
        invoice = self._invoice(
            "input_invoice_tax",
            contract_id=self.input_contract.id,
            invoice_no="UM-P2-S04-SAME-NUMBER",
        )
        deduction = self.caller_env[
            "sc.tax.deduction.registration"
        ].create(
            {
                "project_id": self.project_a.id,
                "partner_id": self.partners[0].id,
                "invoice_no": invoice.invoice_no,
                "deduction_amount": 10.0,
            }
        )
        self.assertEqual(deduction.invoice_no, invoice.invoice_no)
        self.assertNotIn("contract_id", deduction._fields)
        self.assertNotIn("invoice_registration_id", deduction._fields)


if __name__ == "__main__":
    import unittest

    unittest.main()
