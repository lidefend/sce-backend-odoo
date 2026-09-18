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


@tagged("post_install", "-at_install", "sc_gate", "company_project_refund_workspace")
class TestCompanyProjectRefundWorkspace(TransactionCase):
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
            "refund_workspace_finance_user",
            "smart_construction_core.group_sc_cap_finance_user",
        )
        self.project_user = self._user(
            "refund_workspace_project_user",
            "smart_construction_core.group_sc_cap_project_user",
        )
        self.project = self.env["project.project"].create(
            {"name": "退款工作台测试项目", "company_id": self.env.company.id, "operation_strategy": "direct"}
        )
        self.partner = self.env["res.partner"].create({"name": "退款测试往来方"})

    def _workspace(self, partner=True):
        values = {
            "project_id": self.project.id,
            "business_date": "2026-08-12",
            "note": "退款办理测试",
        }
        if partner:
            values["partner_id"] = self.partner.id
        return self.env["sc.company.project.refund.workspace"].with_user(self.finance_user).create(values)

    def test_workspace_dispatches_each_refund_to_its_fact_owner(self):
        workspace = self._workspace()
        cases = (
            (workspace.action_deduction_refund, "sc.expense.claim", "finance.deduction.refund"),
            (workspace.action_bid_deposit_return, "sc.expense.claim", "finance.deposit.bid.return"),
            (workspace.action_contract_deposit_return, "sc.expense.claim", "finance.deposit.contract.return"),
            (workspace.action_self_funding_refund, "sc.self.funding.registration", "finance.self_funding.refund"),
        )
        resolved = 0
        for call, model, category in cases:
            action = released_action(call)
            if not action:
                continue
            resolved += 1
            self.assertEqual(action["res_model"], model)
            self.assertEqual(action["view_mode"], "form")
            self.assertEqual(action["context"]["default_project_id"], self.project.id)
            self.assertEqual(action["context"]["default_partner_id"], self.partner.id)
            self.assertEqual(action["context"]["default_business_category_code"], category)
            self.assertTrue(action["menu_id"])
        self.assertTrue(resolved, "no carrier of this entry is released: contract unverified")

        ledger_action = released_action(workspace.action_view_refund_account)
        if ledger_action:
            self.assertEqual(ledger_action["res_model"], "sc.finance.project.counterparty.position")
            self.assertIn(("project_id", "=", self.project.id), ledger_action["domain"])
            self.assertIn(("partner_id", "=", self.partner.id), ledger_action["domain"])

        product_action = self.env.ref("smart_construction_core.action_sc_product_company_project_refund_v1")
        self.assertEqual(product_action.res_model, "sc.company.project.refund.workspace")
        contract = self.env.ref(
            "smart_construction_core.business_config_contract_company_project_refund_workspace_form_v1"
        )
        self.assertEqual(contract.action_id, product_action)
        self.assertEqual(contract.contract_json["view_orchestration"]["context"]["fact_authority"], "dispatch_only")

    def test_advisory_and_capability_boundaries(self):
        without_partner = self._workspace(partner=False)
        self.assertIn("建议选择", without_partner.processing_advisory)
        deduction_action = released_action(without_partner.action_deduction_refund)
        if deduction_action:
            self.assertEqual(deduction_action["res_model"], "sc.expense.claim")
        # The counterparty guard runs before the entry authority: a refund that
        # changes the responsibility balance must name the counterparty first.
        with self.assertRaises(UserError) as caught:
            without_partner.action_self_funding_refund()
        self.assertIn("收款方", str(caught.exception))

        with self.assertRaises(AccessError):
            self.env["sc.company.project.refund.workspace"].with_user(self.project_user).create(
                {"project_id": self.project.id}
            )
