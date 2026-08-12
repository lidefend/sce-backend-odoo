# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "sc_gate", "social_fund")
class TestSocialFundCapability(TransactionCase):
    def test_social_fund_action_includes_distinct_provident_fact(self):
        action = self.env.ref("smart_construction_core.action_sc_product_social_fund_v1")
        for token in ("social_person_registration", "social_registration", "provident_fund_registration"):
            self.assertIn(token, action.domain)

        provident = self.env["sc.hr.payroll.document"].with_context(
            default_fact_type="provident_fund_registration"
        ).create({"provident_fund_account": "SC-TEST-001", "provident_fund_base": 5000})
        self.assertEqual(provident.fact_type, "provident_fund_registration")
        self.assertEqual(provident.name, "公积金登记")
        self.assertEqual(provident.state, "draft")
        provident.action_submit()
        self.assertEqual(provident.state, "in_progress")

        contract = self.env.ref("smart_construction_core.business_config_contract_social_fund_form_v1")
        self.assertEqual(contract.action_id, action)
        self.assertIn(
            "provident_fund_registration",
            contract.contract_json["view_orchestration"]["context"]["allowed_fact_types"],
        )

    def test_only_operational_contribution_consistency_blocks(self):
        invalid = self.env["sc.hr.payroll.document"].with_context(
            default_fact_type="provident_fund_registration"
        ).create({"company_contribution_rate": 101})
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            invalid.action_submit()
