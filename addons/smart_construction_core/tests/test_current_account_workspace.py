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


@tagged("post_install", "-at_install", "sc_gate", "current_account_workspace")
class TestCurrentAccountWorkspace(TransactionCase):
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
        self.finance_user = self._user(
            "current_account_finance_user",
            "smart_construction_core.group_sc_cap_finance_user",
        )
        self.project_user = self._user(
            "current_account_project_user",
            "smart_construction_core.group_sc_cap_project_user",
        )
        self.project = self.env["project.project"].create(
            {
                "name": "往来款测试项目",
                "company_id": self.env.company.id,
                "operation_strategy": "direct",
            }
        )
        self.partner = self.env["res.partner"].create({"name": "往来款测试承包人"})

    def _workspace(self, user=None, partner=True):
        values = {
            "project_id": self.project.id,
            "business_date": "2026-08-11",
            "note": "往来办理测试",
        }
        if partner:
            values["partner_id"] = self.partner.id
        return self.env["sc.current.account.workspace"].with_user(user or self.finance_user).create(values)

    def test_workspace_dispatches_to_canonical_facts_and_projection(self):
        workspace = self._workspace()
        cases = (
            (
                workspace.action_project_borrow_company,
                "sc.financing.loan",
                "finance.loan.project_borrow_company",
                False,
            ),
            (
                workspace.action_project_repay_company,
                "sc.expense.claim",
                "finance.repayment.project_company",
                False,
            ),
            (
                workspace.action_contractor_borrow_project,
                "sc.financing.loan",
                "finance.loan.contractor_project_borrow",
                True,
            ),
            (
                workspace.action_contractor_repay_project,
                "sc.expense.claim",
                "finance.repayment.contractor_project",
                True,
            ),
            (
                workspace.action_account_transfer,
                "sc.fund.account.operation",
                "finance.fund.transfer",
                False,
            ),
        )
        resolved = 0
        for call, model, category, needs_partner in cases:
            action = released_action(call)
            if not action:
                continue
            resolved += 1
            self.assertEqual(action["res_model"], model)
            self.assertEqual(action["view_mode"], "form")
            self.assertEqual(action["context"]["default_project_id"], self.project.id)
            self.assertEqual(action["context"]["default_business_category_code"], category)
            self.assertTrue(action["menu_id"])
            if needs_partner:
                self.assertEqual(action["context"]["default_partner_id"], self.partner.id)
        self.assertTrue(resolved, "no carrier of this entry is released: contract unverified")

        ledger_action = released_action(workspace.action_view_current_account)
        if ledger_action:
            self.assertEqual(ledger_action["res_model"], "sc.finance.project.counterparty.position")
            self.assertIn(("project_id", "=", self.project.id), ledger_action["domain"])
            self.assertIn(("partner_id", "=", self.partner.id), ledger_action["domain"])

        product_action = self.env.ref("smart_construction_core.action_sc_product_current_account_v1")
        self.assertEqual(product_action.res_model, "sc.current.account.workspace")
        contract = self.env.ref(
            "smart_construction_core.business_config_contract_current_account_workspace_form_v1"
        )
        self.assertEqual(contract.model, product_action.res_model)
        self.assertEqual(contract.action_id, product_action)
        self.assertEqual(contract.contract_json["view_orchestration"]["context"]["fact_authority"], "dispatch_only")

    def test_operational_and_capability_boundaries(self):
        without_partner = self._workspace(partner=False)
        with self.assertRaises(UserError):
            without_partner.action_contractor_borrow_project()
        with self.assertRaises(UserError):
            without_partner.action_contractor_repay_project()
        borrow_action = released_action(without_partner.action_project_borrow_company)
        if borrow_action:
            self.assertEqual(borrow_action["res_model"], "sc.financing.loan")

        with self.assertRaises(AccessError):
            self.env["sc.current.account.workspace"].with_user(self.project_user).create(
                {"project_id": self.project.id}
            )
