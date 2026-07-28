# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "admin_vis_p3_project_record_rule_orm")
class TestUmP2PaymentRelationAggregationOrm(TransactionCase):
    """Real-ORM coverage for payment basis aggregation and actual payees."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        base_user = cls.env.ref("base.group_user")
        initiator = cls.env.ref(
            "smart_construction_core.group_sc_cap_business_initiator"
        )
        material_read = cls.env.ref(
            "smart_construction_core.group_sc_cap_material_read"
        )
        cls.caller = cls.env["res.users"].with_context(
            no_reset_password=True
        ).create(
            {
                "name": "UM-P2 S02 payment caller",
                "login": "um_p2_s02_payment_caller",
                "email": "um_p2_s02@example.invalid",
                "company_id": cls.company.id,
                "company_ids": [(6, 0, [cls.company.id])],
                "groups_id": [
                    (6, 0, [base_user.id, initiator.id, material_read.id])
                ],
            }
        )
        cls.context = {
            **cls.env.context,
            "allowed_company_ids": [cls.company.id],
            "mail_create_nosubscribe": True,
            "mail_notify_noemail": True,
            "mail_auto_subscribe_no_notify": True,
            "tracking_disable": True,
        }
        cls.project = cls.env["project.project"].with_context(
            cls.context
        ).create(
            {
                "name": "UM-P2 S02 project",
                "company_id": cls.company.id,
                "privacy_visibility": "followers",
                "user_id": cls.caller.id,
            }
        )
        cls.partners = [
            cls.env["res.partner"].create({"name": f"UM-P2 S02 partner {index}"})
            for index in (1, 2, 3)
        ]
        tax = cls.env["account.tax"].search(
            [("type_tax_use", "in", ("purchase", "none"))],
            limit=1,
        )
        if not tax:
            tax = cls.env["account.tax"].create(
                {
                    "name": "UM-P2 S02 contract tax",
                    "amount": 0.0,
                    "amount_type": "percent",
                    "type_tax_use": "purchase",
                }
            )

        def contract(label, partner):
            return cls.env["construction.contract"].with_context(
                cls.context
            ).create(
                {
                    "subject": f"UM-P2 S02 {label} contract",
                    "type": "in",
                    "project_id": cls.project.id,
                    "partner_id": partner.id,
                    "tax_id": tax.id,
                }
            )

        cls.contract_a = contract("A", cls.partners[0])
        cls.contract_b = contract("B", cls.partners[1])

        def settlement(label, contract_record, partner):
            return cls.env["sc.settlement.order"].with_context(
                cls.context
            ).create(
                {
                    "project_id": cls.project.id,
                    "company_id": cls.company.id,
                    "contract_id": contract_record.id,
                    "partner_id": partner.id,
                    "settlement_type": "out",
                    "title": f"UM-P2 S02 {label} settlement",
                    "line_ids": [(0, 0, {"name": label, "amount": 100.0})],
                }
            )

        cls.settlement_a1 = settlement(
            "A1", cls.contract_a, cls.partners[0]
        )
        cls.settlement_a2 = settlement(
            "A2", cls.contract_a, cls.partners[0]
        )
        cls.settlement_b = settlement(
            "B", cls.contract_b, cls.partners[1]
        )
        cls.material_settlement = cls.env[
            "sc.material.settlement"
        ].with_context(cls.context).create(
            {
                "name": "UM-P2 S02 material settlement",
                "project_id": cls.project.id,
                "supplier_id": cls.partners[0].id,
                "state": "confirmed",
            }
        )
        cls.caller_env = cls.env(
            user=cls.caller,
            context=cls.context,
        )

    def _request(self, label, **values):
        request_values = {
            "name": f"UM-P2 S02 {label} request",
            "type": "pay",
            "project_id": self.project.id,
            "partner_id": self.partners[0].id,
            "amount": 100.0,
        }
        request_values.update(values)
        return self.env["payment.request"].with_context(self.context).create(
            request_values
        )

    def _line(self, request, label, settlement, contract=None):
        return self.env["payment.request.line"].with_context(
            self.context
        ).create(
            {
                "request_id": request.id,
                "legacy_line_id": f"UM-P2-S02-{label}",
                "legacy_parent_id": f"UM-P2-S02-{request.id}",
                "settlement_id": settlement.id,
                "contract_id": contract.id if contract else False,
                "amount": 100.0,
                "current_pay_amount": 100.0,
            }
        )

    def _execution(self, request, **values):
        execution_values = {
            "payment_request_id": request.id,
            "planned_amount": request.amount,
            "paid_amount": request.amount,
        }
        execution_values.update(values)
        return self.caller_env["sc.payment.execution"].create(
            execution_values
        )

    def test_single_standard_settlement_derives_unique_contract(self):
        request = self._request(
            "standard",
            settlement_id=self.settlement_a1.id,
        )
        execution = self._execution(request)
        self.assertEqual(execution.contract_id, self.contract_a)

    def test_material_settlement_without_contract_stays_unaggregated(self):
        request = self._request(
            "material",
            material_settlement_id=self.material_settlement.id,
        )
        execution = self._execution(request)
        self.assertFalse(execution.contract_id)

    def test_multiple_details_with_same_contract_derive_one_contract(self):
        request = self._request("same-contract-details")
        self._line(request, "same-a1", self.settlement_a1)
        self._line(request, "same-a2", self.settlement_a2)
        execution = self._execution(request)
        self.assertEqual(execution.contract_id, self.contract_a)

    def test_multiple_contract_details_preserve_lines_and_empty_execution_contract(self):
        request = self._request("multi-contract-details")
        line_a = self._line(request, "multi-a", self.settlement_a1)
        line_b = self._line(request, "multi-b", self.settlement_b)
        execution = self._execution(request)
        self.assertFalse(execution.contract_id)
        self.assertEqual(
            set(request.outflow_line_ids.mapped("contract_id").ids),
            set(),
        )
        self.assertEqual(
            set(request.outflow_line_ids.mapped("settlement_id").ids),
            {line_a.settlement_id.id, line_b.settlement_id.id},
        )

    def test_explicit_execution_contract_conflict_is_rejected(self):
        request = self._request(
            "contract-conflict",
            settlement_id=self.settlement_a1.id,
        )
        with self.assertRaises(ValidationError):
            self._execution(request, contract_id=self.contract_b.id)

    def test_contract_without_settlement_basis_is_rejected(self):
        with self.assertRaises(ValidationError):
            self._request(
                "contract-without-basis",
                contract_id=self.contract_a.id,
            )

    def test_header_detail_conflict_is_rejected(self):
        request = self._request("header-detail-conflict")
        self._line(request, "header-detail-a", self.settlement_a1)
        with self.assertRaises(ValidationError):
            request.write({"settlement_id": self.settlement_b.id})

    def test_same_and_different_actual_payees_are_both_valid(self):
        request = self._request(
            "payee",
            settlement_id=self.settlement_a1.id,
        )
        same = self._execution(request, partner_id=self.partners[0].id)
        different = self._execution(request, partner_id=self.partners[2].id)
        self.assertEqual(same.payment_request_partner_relation, "same_partner")
        self.assertEqual(
            different.payment_request_partner_relation,
            "actual_payee_differs",
        )
        self.assertEqual(request.partner_id, self.partners[0])
        self.assertEqual(request.contract_id, self.contract_a)

    def test_write_revalidates_basis_but_allows_actual_payee_change(self):
        request = self._request(
            "write",
            settlement_id=self.settlement_a1.id,
        )
        execution = self._execution(request)
        execution.write({"partner_id": self.partners[2].id})
        self.assertEqual(execution.partner_id, self.partners[2])
        with self.assertRaises(ValidationError):
            execution.write({"contract_id": self.contract_b.id})
