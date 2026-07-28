# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "admin_vis_p3_project_record_rule_orm")
class TestUmP1OwnershipVisibilityContractOrm(TransactionCase):
    """Real-registry baseline for the six approved UM-P1 entry families."""

    MODEL_FIELDS = {
        "sc.receipt.income": {"project_id", "company_id"},
        "payment.request": {"project_id", "company_id"},
        "sc.payment.execution": {"project_id", "company_id"},
        "sc.invoice.registration": {"project_id", "company_id"},
        "sc.tax.deduction.registration": {"project_id", "company_id"},
        "sc.fund.account.operation": {"project_id", "company_id"},
        "sc.financing.loan": {"project_id", "company_id"},
        "sc.settlement.order": {"project_id", "company_id", "entry_user_id"},
        "project.cost.ledger": {"project_id", "company_id"},
    }
    MODELS_WITHOUT_RECORD_RULES = set()
    REQUIRED_RULE_XMLIDS = {
        "smart_construction_core.rule_sc_business_initiator_payment_request",
        "smart_construction_core.rule_sc_finance_read_payment_request",
        "smart_construction_core.rule_sc_finance_user_payment_request",
        "smart_construction_core.rule_sc_finance_manager_payment_request",
        "smart_construction_core.rule_sc_business_initiator_payment_execution",
        "smart_construction_core.rule_sc_finance_read_payment_execution",
        "smart_construction_core.rule_sc_finance_user_payment_execution",
        "smart_construction_core.rule_sc_finance_manager_payment_execution",
        "smart_construction_core.rule_sc_settlement_read_order",
        "smart_construction_core.rule_sc_settlement_user_order",
        "smart_construction_core.rule_sc_settlement_manager_order",
        "smart_construction_core.rule_sc_fund_account_operation_company",
        "smart_construction_core.rule_sc_finance_read_fund_account_operation",
        "smart_construction_core.rule_sc_finance_user_fund_account_operation",
        "smart_construction_core.rule_sc_finance_manager_fund_account_operation",
        "smart_construction_core.rule_sc_business_initiator_fund_account_operation",
        "smart_construction_core.rule_sc_financing_loan_company",
        "smart_construction_core.rule_sc_finance_read_financing_loan",
        "smart_construction_core.rule_sc_finance_user_financing_loan",
        "smart_construction_core.rule_sc_finance_manager_financing_loan",
        "smart_construction_core.rule_sc_business_initiator_financing_loan",
        "smart_construction_core.rule_sc_business_initiator_receipt_income",
        "smart_construction_core.rule_sc_finance_read_receipt_income",
        "smart_construction_core.rule_sc_finance_user_receipt_income",
        "smart_construction_core.rule_sc_finance_manager_receipt_income",
        "smart_construction_core.rule_sc_invoice_registration_company",
        "smart_construction_core.rule_sc_finance_read_invoice_registration",
        "smart_construction_core.rule_sc_finance_user_invoice_registration",
        "smart_construction_core.rule_sc_finance_manager_invoice_registration",
        "smart_construction_core.rule_sc_business_initiator_invoice_registration",
        "smart_construction_core.rule_sc_tax_deduction_registration_company",
        "smart_construction_core.rule_sc_finance_read_tax_deduction_registration",
        "smart_construction_core.rule_sc_finance_user_tax_deduction_registration",
        "smart_construction_core.rule_sc_finance_manager_tax_deduction_registration",
        "smart_construction_core.rule_sc_business_initiator_tax_deduction_registration",
        "smart_construction_core.rule_sc_config_admin_tax_deduction_registration",
        "smart_construction_core.rule_sc_project_cost_ledger_company",
        "smart_construction_core.rule_sc_cost_read_project_cost_ledger",
        "smart_construction_core.rule_sc_cost_user_project_cost_ledger",
        "smart_construction_core.rule_sc_cost_manager_project_cost_ledger",
    }

    def test_real_registry_contains_the_six_entry_model_anchors(self):
        for model_name, field_names in self.MODEL_FIELDS.items():
            model = self.env[model_name]
            self.assertEqual(model._name, model_name)
            self.assertTrue(
                field_names.issubset(model._fields),
                f"{model_name} missing {sorted(field_names - set(model._fields))}",
            )

        self.assertTrue(self.env["sc.receipt.income"]._fields["project_id"].required)
        self.assertTrue(self.env["payment.request"]._fields["project_id"].required)
        self.assertTrue(self.env["sc.payment.execution"]._fields["project_id"].required)
        self.assertTrue(self.env["sc.invoice.registration"]._fields["project_id"].required)
        self.assertTrue(self.env["sc.tax.deduction.registration"]._fields["project_id"].required)
        self.assertFalse(self.env["sc.fund.account.operation"]._fields["project_id"].required)
        self.assertTrue(self.env["sc.settlement.order"]._fields["project_id"].required)
        self.assertTrue(self.env["project.cost.ledger"]._fields["project_id"].required)

    def test_real_registry_preserves_record_rule_topology_and_explicit_gaps(self):
        rules = self.env["ir.rule"].sudo().search(
            [("model_id.model", "in", list(self.MODEL_FIELDS))]
        )
        rules_by_model = {
            model_name: rules.filtered(lambda rule, name=model_name: rule.model_id.model == name)
            for model_name in self.MODEL_FIELDS
        }
        xmlids = set(rules.get_external_id().values())

        self.assertTrue(self.REQUIRED_RULE_XMLIDS.issubset(xmlids))
        for model_name in self.MODELS_WITHOUT_RECORD_RULES:
            self.assertFalse(
                rules_by_model[model_name],
                f"{model_name} gained a record rule and requires S01 reconciliation",
            )

        payment_domains = " ".join(rules_by_model["payment.request"].mapped("domain_force"))
        execution_domains = " ".join(rules_by_model["sc.payment.execution"].mapped("domain_force"))
        receipt_domains = " ".join(rules_by_model["sc.receipt.income"].mapped("domain_force"))
        settlement_domains = " ".join(rules_by_model["sc.settlement.order"].mapped("domain_force"))
        fund_domains = " ".join(rules_by_model["sc.fund.account.operation"].mapped("domain_force"))
        financing_domains = " ".join(
            rules_by_model["sc.financing.loan"].mapped("domain_force")
        )
        invoice_domains = " ".join(
            rules_by_model["sc.invoice.registration"].mapped("domain_force")
        )
        deduction_domains = " ".join(
            rules_by_model["sc.tax.deduction.registration"].mapped("domain_force")
        )
        cost_ledger_domains = " ".join(
            rules_by_model["project.cost.ledger"].mapped("domain_force")
        )
        for domains in (payment_domains, execution_domains, receipt_domains, settlement_domains):
            self.assertIn("project_id.user_id", domains)
            self.assertIn("project_id.message_is_follower", domains)
            self.assertIn("company_id", domains)
        for domains in (fund_domains, financing_domains):
            self.assertIn("company_id", domains)
            self.assertNotIn("project_id.user_id", domains)
            self.assertNotIn("project_id.message_is_follower", domains)
        for domains in (invoice_domains, deduction_domains):
            self.assertIn("company_id", domains)
            self.assertNotIn("project_id.user_id", domains)
            self.assertNotIn("project_id.message_is_follower", domains)
        self.assertIn("company_id", cost_ledger_domains)
        self.assertIn("project_id.user_id", cost_ledger_domains)
        self.assertIn("project_id.message_is_follower", cost_ledger_domains)
        self.assertNotIn("project_id.manager_id", cost_ledger_domains)
        self.assertNotIn("create_uid", cost_ledger_domains)

    def test_real_registry_has_acl_evidence_for_every_entry_model(self):
        accesses = self.env["ir.model.access"].sudo().search(
            [("model_id.model", "in", list(self.MODEL_FIELDS))]
        )
        covered_models = set(accesses.mapped("model_id.model"))

        self.assertEqual(set(self.MODEL_FIELDS) - covered_models, set())
        for model_name in self.MODEL_FIELDS:
            model_accesses = accesses.filtered(
                lambda access, name=model_name: access.model_id.model == name
            )
            self.assertTrue(any(model_accesses.mapped("perm_read")), model_name)

    def test_contract_does_not_treat_audit_fields_as_personal_authority(self):
        settlement = self.env["sc.settlement.order"]
        self.assertIn("entry_user_id", settlement._fields)
        settlement_rules = self.env["ir.rule"].sudo().search(
            [("model_id.model", "=", settlement._name)]
        )
        self.assertNotIn(
            "entry_user_id",
            " ".join(settlement_rules.mapped("domain_force")),
        )


@tagged("post_install", "-at_install", "admin_vis_p3_project_record_rule_orm")
class TestUmP1ProjectReceiptVisibilityOrm(TransactionCase):
    """Real record-rule behavior for the first document-order UM-P1 entry."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.ref("base.main_company")
        cls.company_b = cls.env["res.company"].create({"name": "UM-P1 S02 Company B"})
        base_user = cls.env.ref("base.group_user")
        finance_read = cls.env.ref("smart_construction_core.group_sc_cap_finance_read")
        finance_manager = cls.env.ref("smart_construction_core.group_sc_cap_finance_manager")

        def create_user(name, login, group):
            return cls.env["res.users"].with_context(no_reset_password=True).create(
                {
                    "name": name,
                    "login": login,
                    "email": f"{login}@example.invalid",
                    "company_id": cls.company_a.id,
                    "company_ids": [(6, 0, [cls.company_a.id])],
                    "groups_id": [(6, 0, [base_user.id, group.id])],
                }
            )

        cls.ordinary_user = create_user(
            "UM-P1 S02 ordinary finance reader",
            "um_p1_s02_ordinary",
            finance_read,
        )
        cls.manager_user = create_user(
            "UM-P1 S02 finance manager",
            "um_p1_s02_manager",
            finance_manager,
        )
        setup_context = {
            **cls.env.context,
            "allowed_company_ids": [cls.company_a.id, cls.company_b.id],
            "mail_create_nosubscribe": True,
            "mail_notify_noemail": True,
            "mail_auto_subscribe_no_notify": True,
            "tracking_disable": True,
        }
        Project = cls.env["project.project"].with_context(setup_context)
        project_values = {"privacy_visibility": "followers"}
        cls.authorized_project = Project.create(
            {
                **project_values,
                "name": "UM-P1 S02 authorized project",
                "company_id": cls.company_a.id,
                "user_id": cls.ordinary_user.id,
            }
        )
        cls.unauthorized_project = Project.create(
            {
                **project_values,
                "name": "UM-P1 S02 unauthorized project",
                "company_id": cls.company_a.id,
                "user_id": cls.env.user.id,
            }
        )
        cls.cross_company_project = Project.create(
            {
                **project_values,
                "name": "UM-P1 S02 cross-company project",
                "company_id": cls.company_b.id,
                "user_id": cls.env.user.id,
            }
        )
        Receipt = cls.env["sc.receipt.income"].with_context(setup_context)
        cls.authorized_receipt = Receipt.create(
            {"project_id": cls.authorized_project.id, "amount": 101.0}
        )
        cls.unauthorized_receipt = Receipt.create(
            {"project_id": cls.unauthorized_project.id, "amount": 202.0}
        )
        cls.cross_company_receipt = Receipt.create(
            {"project_id": cls.cross_company_project.id, "amount": 303.0}
        )
        cls.nonexistent_receipt_id = max(
            cls.authorized_receipt.id,
            cls.unauthorized_receipt.id,
            cls.cross_company_receipt.id,
        ) + 1000000
        cls.ordinary_receipts = cls.env(
            user=cls.ordinary_user,
            context={
                **cls.env.context,
                "allowed_company_ids": [cls.company_a.id],
                "tracking_disable": True,
            },
        )["sc.receipt.income"]
        cls.manager_receipts = cls.env(
            user=cls.manager_user,
            context={
                **cls.env.context,
                "allowed_company_ids": [cls.company_a.id],
                "tracking_disable": True,
            },
        )["sc.receipt.income"]

    def test_authorized_ordinary_user_sees_only_personal_project_receipt(self):
        visible = self.ordinary_receipts.search(
            [
                (
                    "id",
                    "in",
                    [
                        self.authorized_receipt.id,
                        self.unauthorized_receipt.id,
                        self.cross_company_receipt.id,
                    ],
                )
            ]
        )
        self.assertEqual(visible, self.authorized_receipt)

    def test_unauthorized_cross_user_cross_company_and_nonexistent_are_hidden(self):
        observations = []
        for record_id in (
            self.unauthorized_receipt.id,
            self.cross_company_receipt.id,
            self.nonexistent_receipt_id,
        ):
            result = self.ordinary_receipts.search([("id", "=", record_id)], limit=1)
            observations.append((bool(result), len(result)))

        self.assertEqual(observations, [(False, 0), (False, 0), (False, 0)])

    def test_finance_manager_is_limited_by_allowed_company_not_project_membership(self):
        same_company = self.manager_receipts.search(
            [
                (
                    "id",
                    "in",
                    [self.authorized_receipt.id, self.unauthorized_receipt.id],
                )
            ]
        )
        cross_company = self.manager_receipts.search(
            [("id", "=", self.cross_company_receipt.id)],
            limit=1,
        )

        self.assertEqual(set(same_company.ids), {self.authorized_receipt.id, self.unauthorized_receipt.id})
        self.assertFalse(cross_company)

    def test_direct_unauthorized_read_is_rejected_by_the_real_record_rule(self):
        with self.assertRaises(AccessError):
            self.ordinary_receipts.browse(self.unauthorized_receipt.id).read(["amount"])

    def test_no_scope_search_keeps_the_personal_visibility_rule(self):
        visible = self.ordinary_receipts.search([])
        self.assertIn(self.authorized_receipt, visible)
        self.assertNotIn(self.unauthorized_receipt, visible)
        self.assertNotIn(self.cross_company_receipt, visible)
