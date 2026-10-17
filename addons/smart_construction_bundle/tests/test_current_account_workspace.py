# -*- coding: utf-8 -*-
from unittest.mock import patch

from odoo.exceptions import AccessError, UserError
from odoo.tests.common import tagged
from odoo.addons.smart_construction_core.tests.business_case import BusinessTransactionCase



@tagged("post_install", "-at_install", "sc_gate", "current_account_workspace")
class TestCurrentAccountWorkspace(BusinessTransactionCase):
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
        from odoo.addons.smart_core.delivery.edition_release_snapshot_service import EditionReleaseSnapshotService
        self.env["ir.config_parameter"].sudo().set_param("smart_core.platform_release_db", self.env.cr.dbname)
        self.env["ir.config_parameter"].sudo().set_param("smart_core.release_operator.catalog_source_db", self.env.cr.dbname)
        EditionReleaseSnapshotService(self.env).freeze_release_surface(
            product_key="construction.standard", version="synthetic-workspace-test", replace_active=True)
        self.finance_user = self._user(
            "current_account_finance_user",
            "smart_construction_core.group_sc_role_finance_user",
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
            action = call()
            resolved += 1
            self.assertEqual(action["res_model"], model)
            self.assertEqual(action["view_mode"], "form")
            self.assertEqual(action["context"]["default_project_id"], self.project.id)
            self.assertEqual(action["context"]["default_business_category_code"], category)
            self.assertEqual(action["menu_id"], self.env.ref("smart_construction_core.menu_sc_product_current_account_v1").id)
            if needs_partner:
                self.assertEqual(action["context"]["default_partner_id"], self.partner.id)
        self.assertEqual(resolved, len(cases), "every declared handling carrier must be operable")

        ledger_action = workspace.action_view_current_account()
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
        borrow_action = without_partner.action_project_borrow_company()
        self.assertEqual(borrow_action["res_model"], "sc.financing.loan")

        with self.assertRaises(AccessError):
            self.env["sc.current.account.workspace"].with_user(self.project_user).create(
                {"project_id": self.project.id}
            )

    def test_shared_ledger_cannot_borrow_another_workspace_carrier(self):
        workspace = self._workspace()
        own_menu = self.env.ref(workspace._sc_dispatch_menu_xmlid)
        routes = workspace._sc_route_authority()
        ledger_id = self.env.ref("smart_construction_core.action_sc_finance_project_counterparty_position").id
        other_routes = [row for row in routes if row.get("action_id") == ledger_id and row.get("menu_id") != own_menu.id]
        self.assertTrue(other_routes, "negative requires a real published sibling carrier")
        with patch.object(type(workspace), "_sc_route_authority", return_value=other_routes):
            with self.assertRaisesRegex(UserError, "正式入口"):
                workspace.action_view_current_account()
        with patch.object(type(workspace), "_sc_route_authority", return_value=[]):
            with self.assertRaisesRegex(UserError, "正式入口"):
                workspace.action_view_current_account()
