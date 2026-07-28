# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "admin_vis_p3_project_record_rule_orm")
class TestUmP2ReceiptRelationAggregationOrm(TransactionCase):
    """Real-ORM evidence for the receipt application/contract authority chain."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        base_user = cls.env.ref("base.group_user")
        initiator = cls.env.ref(
            "smart_construction_core.group_sc_cap_business_initiator"
        )
        cls.caller = cls.env["res.users"].with_context(
            no_reset_password=True
        ).create(
            {
                "name": "UM-P2 S01 receipt caller",
                "login": "um_p2_s01_receipt_caller",
                "email": "um_p2_s01@example.invalid",
                "company_id": cls.company.id,
                "company_ids": [(6, 0, [cls.company.id])],
                "groups_id": [(6, 0, [base_user.id, initiator.id])],
            }
        )
        setup_context = {
            **cls.env.context,
            "allowed_company_ids": [cls.company.id],
            "mail_create_nosubscribe": True,
            "mail_notify_noemail": True,
            "mail_auto_subscribe_no_notify": True,
            "tracking_disable": True,
        }
        Project = cls.env["project.project"].with_context(setup_context)
        cls.visible_project = Project.create(
            {
                "name": "UM-P2 S01 visible project",
                "company_id": cls.company.id,
                "privacy_visibility": "followers",
                "user_id": cls.caller.id,
            }
        )
        cls.hidden_project = Project.create(
            {
                "name": "UM-P2 S01 hidden project",
                "company_id": cls.company.id,
                "privacy_visibility": "followers",
                "user_id": cls.env.user.id,
            }
        )
        cls.partners = [
            cls.env["res.partner"].create({"name": f"UM-P2 S01 partner {index}"})
            for index in (1, 2)
        ]
        tax = cls.env["account.tax"].search(
            [("type_tax_use", "in", ("sale", "none"))],
            limit=1,
        )
        if not tax:
            tax = cls.env["account.tax"].create(
                {
                    "name": "UM-P2 S01 contract tax",
                    "amount": 0.0,
                    "amount_type": "percent",
                    "type_tax_use": "sale",
                }
            )

        def create_contract(project, partner, label):
            return cls.env["construction.contract"].with_context(
                setup_context
            ).create(
                {
                    "subject": f"UM-P2 S01 {label} contract",
                    "type": "out",
                    "project_id": project.id,
                    "partner_id": partner.id,
                    "tax_id": tax.id,
                }
            )

        cls.visible_contract = create_contract(
            cls.visible_project, cls.partners[0], "visible"
        )
        cls.alternate_contract = create_contract(
            cls.visible_project, cls.partners[1], "alternate"
        )
        cls.hidden_contract = create_contract(
            cls.hidden_project, cls.partners[1], "hidden"
        )

        def create_request(project, contract, partner, label):
            return cls.env["payment.request"].with_context(setup_context).create(
                {
                    "name": f"UM-P2 S01 {label} request",
                    "type": "receive",
                    "project_id": project.id,
                    "contract_id": contract.id,
                    "partner_id": partner.id,
                    "amount": 100.0,
                }
            )

        cls.visible_request = create_request(
            cls.visible_project,
            cls.visible_contract,
            cls.partners[0],
            "visible",
        )
        cls.alternate_request = create_request(
            cls.visible_project,
            cls.alternate_contract,
            cls.partners[1],
            "alternate",
        )
        cls.hidden_request = create_request(
            cls.hidden_project,
            cls.hidden_contract,
            cls.partners[1],
            "hidden",
        )
        cls.caller_env = cls.env(
            user=cls.caller,
            context={**setup_context, "allowed_company_ids": [cls.company.id]},
        )

    def _receipt_values(self, **overrides):
        values = {
            "project_id": self.visible_project.id,
            "amount": 100.0,
        }
        values.update(overrides)
        return values

    def test_application_is_primary_and_derives_contract_counterparty(self):
        receipt = self.caller_env["sc.receipt.income"].create(
            self._receipt_values(payment_request_id=self.visible_request.id)
        )
        self.assertEqual(receipt.contract_id, self.visible_contract)
        self.assertEqual(receipt.partner_id, self.partners[0])

    def test_contract_is_secondary_and_derives_counterparty(self):
        receipt = self.caller_env["sc.receipt.income"].create(
            self._receipt_values(contract_id=self.visible_contract.id)
        )
        self.assertFalse(receipt.payment_request_id)
        self.assertEqual(receipt.partner_id, self.partners[0])

    def test_conflicting_explicit_contract_or_counterparty_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.caller_env["sc.receipt.income"].create(
                self._receipt_values(
                    payment_request_id=self.visible_request.id,
                    contract_id=self.alternate_contract.id,
                )
            )
        with self.assertRaises(ValidationError):
            self.caller_env["sc.receipt.income"].create(
                self._receipt_values(
                    contract_id=self.visible_contract.id,
                    partner_id=self.partners[1].id,
                )
            )

    def test_write_revalidates_complete_authority_chain(self):
        receipt = self.caller_env["sc.receipt.income"].create(
            self._receipt_values(payment_request_id=self.visible_request.id)
        )
        with self.assertRaises(ValidationError):
            receipt.write({"payment_request_id": self.alternate_request.id})
        receipt.write(
            {
                "payment_request_id": self.alternate_request.id,
                "contract_id": self.alternate_contract.id,
                "partner_id": self.partners[1].id,
            }
        )
        self.assertEqual(receipt.contract_id, self.alternate_contract)
        self.assertEqual(receipt.partner_id, self.partners[1])

    def test_unlinked_record_stays_unaggregated(self):
        receipt = self.caller_env["sc.receipt.income"].create(
            self._receipt_values()
        )
        self.assertFalse(receipt.payment_request_id)
        self.assertFalse(receipt.contract_id)
        self.assertFalse(receipt.partner_id)

    def test_hidden_and_nonexistent_application_are_observably_equivalent(self):
        nonexistent_id = self.hidden_request.id + 1000000
        observations = []
        for request_id in (self.hidden_request.id, nonexistent_id):
            with self.assertRaises(ValidationError) as raised:
                self.caller_env["sc.receipt.income"].create(
                    self._receipt_values(payment_request_id=request_id)
                )
            observations.append((type(raised.exception), str(raised.exception)))
        self.assertEqual(observations[0], observations[1])

    def test_application_contract_partner_and_project_conflicts_are_rejected(self):
        with self.assertRaises(ValidationError):
            self.visible_request.write({"partner_id": self.partners[1].id})
            self.caller_env["sc.receipt.income"].create(
                self._receipt_values(payment_request_id=self.visible_request.id)
            )
