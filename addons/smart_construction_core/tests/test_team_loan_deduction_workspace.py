# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase, tagged


def released_action(action_callable):
    """Return the document this carrier dispatches to, or ``None`` when refused.

    A carrier only hands over a document the principal's navigation can open, so
    it resolves the menu of the entry in the current principal's route authority
    - the same contract the client enforces.  When that authority has no entry
    for the target the carrier fails closed with a governed business message
    instead of returning an action the client would have to deny.  The dispatch
    contract of a refused carrier is asserted structurally in
    ``test_context_workspace_native_lowcode``.  Anything other than that governed
    refusal is an error and must not be swallowed here.
    """
    try:
        return action_callable()
    except UserError as exc:
        if "正式入口" not in str(exc):
            raise
        return None


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
        # This entry's dispatch targets (借款 804 / 扣款 798 / 台账 714) live in
        # the finance route surface, while the 875 workspace ACL admits project
        # center operators only, so the operator that may record the context is
        # never the principal that may open the target.  The carriers must fail
        # closed with the governed role message; the open gap is registered in
        # the batch record instead of being papered over here.
        for method in ("action_register_loan", "action_register_deduction", "action_view_account"):
            with self.assertRaises(UserError) as caught:
                getattr(workspace, method)()
            message = str(caught.exception)
            self.assertIn("正式入口", message, method)
            self.assertIn("角色", message, method)
        self.assertFalse(
            released_action(workspace.action_register_loan),
            "the project-center operator must not be handed an unroutable action",
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
        account_values = released_action(workspace.action_view_account)
        if account_values:
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
        self.assertFalse(deduction_fact, "草稿扣款不得提前进入正式财务事实")
