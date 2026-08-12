# -*- coding: utf-8 -*-
import ast

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "sc_gate", "project_special_tax_deduction")
class TestProjectSpecialTaxDeduction(TransactionCase):
    def _user(self, login, group_xmlid):
        return self.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": login,
                "login": login,
                "email": "%s@invalid.local" % login,
                "groups_id": [(6, 0, [self.env.ref("base.group_user").id, self.env.ref(group_xmlid).id])],
            }
        )

    def setUp(self):
        super().setUp()
        self.finance_manager = self._user(
            "project_special_tax_manager",
            "smart_construction_core.group_sc_cap_finance_manager",
        )
        self.project = self.env["project.project"].create(
            {"name": "专项抵扣测试项目", "company_id": self.env.company.id, "operation_strategy": "direct"}
        )

    def _values(self, invoice_no):
        return {
            "project_id": self.project.id,
            "invoice_no": invoice_no,
            "invoice_amount_untaxed": 100,
            "invoice_tax_amount": 9,
            "deduction_amount": 100,
            "deduction_tax_amount": 9,
            "deduction_confirm_date": "2026-08-12",
        }

    def test_general_and_project_special_entries_are_mutually_isolated(self):
        general = self.env["sc.tax.deduction.registration"].create(self._values("GENERAL-001"))
        special = self.env["sc.tax.deduction.registration"].with_context(
            default_deduction_scope="project_special",
            default_business_category_code="tax.deduction.project_special",
        ).create(self._values("SPECIAL-001"))

        self.assertEqual(general.deduction_scope, "general")
        self.assertEqual(general.business_category_id.code, "tax.deduction.registration")
        self.assertEqual(special.deduction_scope, "project_special")
        self.assertEqual(special.business_category_id.code, "tax.deduction.project_special")
        self.assertEqual(special.deduction_flow_label, "项目专项抵扣")

        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            general.write({"deduction_scope": "project_special"})

        general_action = self.env.ref("smart_construction_core.action_sc_tax_deduction_registration_user")
        special_action = self.env.ref("smart_construction_core.action_sc_product_project_tax_deduction_v1")
        self.assertIn("deduction_scope", general_action.domain)
        self.assertIn("general", general_action.domain)
        self.assertIn("deduction_scope", special_action.domain)
        self.assertIn("project_special", special_action.domain)
        special_context = ast.literal_eval(special_action.context)
        self.assertEqual(special_context["default_business_category_code"], "tax.deduction.project_special")

        contract = self.env.ref(
            "smart_construction_core.business_config_contract_project_special_tax_deduction_form_v1"
        )
        self.assertEqual(contract.action_id, special_action)
        self.assertEqual(
            contract.contract_json["view_orchestration"]["context"]["fact_authority"],
            "sc.tax.deduction.registration",
        )

    def test_project_special_deduction_keeps_existing_tax_fact_chain(self):
        special = self.env["sc.tax.deduction.registration"].with_context(
            default_deduction_scope="project_special",
            default_business_category_code="tax.deduction.project_special",
        ).create(self._values("SPECIAL-FACT-001"))
        special.with_user(self.finance_manager).action_deduct()
        self.assertEqual(special.state, "deducted")
        fact = self.env["sc.finance.business.fact"].search(
            [("source_model", "=", special._name), ("source_res_id", "=", special.id)],
            limit=1,
        )
        self.assertEqual(fact.fact_type, "tax_deducted")
        self.assertEqual(fact.project_id, self.project)
        self.assertEqual(fact.balance_effect, 0)
