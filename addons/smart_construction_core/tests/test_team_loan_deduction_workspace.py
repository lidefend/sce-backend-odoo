# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "sc_gate", "team_loan_deduction_workspace")
class TestTeamLoanDeductionWorkspace(TransactionCase):
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
        self.project_user = self._user(
            "team_entry_project_user",
            "smart_construction_core.group_sc_cap_project_user",
        )
        self.finance_manager = self._user(
            "team_entry_finance_manager",
            "smart_construction_core.group_sc_cap_finance_manager",
        )
        self.project = self.env["project.project"].create(
            {
                "name": "班组借扣款测试项目",
                "user_id": self.project_user.id,
                "company_id": self.env.company.id,
                "operation_strategy": "direct",
            }
        )
        self.other_project = self.env["project.project"].create(
            {"name": "不可见项目", "company_id": self.env.company.id, "operation_strategy": "direct"}
        )
        self.partner = self.env["res.partner"].create({"name": "测试班组"})

    def test_workspace_dispatches_without_owning_financial_fact(self):
        workspace = self.env["sc.team.loan.deduction.workspace"].with_user(self.project_user).create(
            {"project_id": self.project.id, "partner_id": self.partner.id, "note": "现场办理"}
        )
        loan_action = workspace.action_register_loan()
        self.assertEqual(loan_action["res_model"], "sc.financing.loan")
        self.assertEqual(loan_action["view_mode"], "form")
        self.assertEqual(loan_action["context"]["default_project_id"], self.project.id)
        self.assertEqual(loan_action["context"]["default_partner_id"], self.partner.id)
        self.assertEqual(
            loan_action["context"]["default_business_category_code"],
            "finance.loan.contractor_project_borrow",
        )

        deduction_action = workspace.action_register_deduction()
        self.assertEqual(deduction_action["res_model"], "sc.expense.claim")
        self.assertEqual(deduction_action["context"]["default_project_id"], self.project.id)
        self.assertEqual(
            deduction_action["context"]["default_business_category_code"],
            "finance.deduction.bill",
        )

        product_action = self.env.ref("smart_construction_core.action_sc_product_team_loan_deduction_v1")
        self.assertEqual(product_action.res_model, "sc.team.loan.deduction.workspace")
        contract = self.env.ref(
            "smart_construction_core.business_config_contract_team_loan_deduction_workspace_form_v1"
        )
        self.assertEqual(contract.model, product_action.res_model)
        self.assertEqual(contract.action_id, product_action)
        self.assertEqual(contract.contract_json["view_orchestration"]["context"]["fact_authority"], "dispatch_only")
        account_action = self.env.ref(
            "smart_construction_core.action_sc_finance_project_counterparty_position"
        )
        self.assertIn(
            self.env.ref("smart_construction_core.group_sc_cap_project_user"),
            account_action.groups_id,
        )
        account_values = workspace.action_view_account()
        self.assertEqual(account_values["res_model"], "sc.finance.project.counterparty.position")
        self.assertIn(("project_id", "=", self.project.id), account_values["domain"])

    def test_project_scope_and_finance_completion_authority_are_enforced(self):
        with self.assertRaises(AccessError):
            workspace = self.env["sc.team.loan.deduction.workspace"].with_user(self.project_user).create(
                {"project_id": self.other_project.id, "partner_id": self.partner.id}
            )
            workspace.action_register_loan()

        loan_category = self.env["sc.business.category"].search(
            [("code", "=", "finance.loan.contractor_project_borrow")], limit=1
        )
        loan = self.env["sc.financing.loan"].with_user(self.project_user).create(
            {
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "loan_type": "borrowing_request",
                "direction": "borrowed_fund",
                "business_category_id": loan_category.id,
                "amount": 100,
                "document_date": "2026-08-11",
            }
        )
        with self.assertRaises(UserError):
            loan.action_done()
        loan.with_user(self.finance_manager).action_done()
        self.assertEqual(loan.state, "done")

        deduction_category = self.env["sc.business.category"].search(
            [("code", "=", "finance.deduction.bill")], limit=1
        )
        deduction = self.env["sc.expense.claim"].with_user(self.project_user).create(
            {
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "business_category_id": deduction_category.id,
                "claim_type": "expense",
                "expense_type": "扣款登记",
                "summary": "测试扣款",
                "amount": 100,
            }
        )
        with self.assertRaises(UserError):
            deduction.action_approve()
        deduction_fact = self.env["sc.finance.business.fact"].with_user(self.project_user).search(
            [("source_model", "=", "sc.expense.claim"), ("source_res_id", "=", deduction.id)],
            limit=1,
        )
        self.assertEqual(deduction_fact.fact_type, "deduction_bill")
        self.assertEqual(deduction_fact.balance_policy, "noncash_deduction")
        self.assertEqual(deduction_fact.deduction_amount, 100)
        self.assertEqual(deduction_fact.cash_in_amount, 0)
        self.assertEqual(deduction_fact.cash_out_amount, 0)
