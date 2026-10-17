# -*- coding: utf-8 -*-
from unittest.mock import patch

from odoo.exceptions import AccessError, UserError
from odoo.tests.common import tagged
from odoo.addons.smart_construction_core.tests.business_case import BusinessTransactionCase



@tagged("post_install", "-at_install", "sc_gate", "company_project_refund_workspace")
class TestCompanyProjectRefundWorkspace(BusinessTransactionCase):
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
            "refund_workspace_finance_user",
            "smart_construction_core.group_sc_role_finance_user",
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
        from odoo.addons.smart_core.handlers.system_init import _resolve_startup_delivery_identity, _load_platform_release_gate
        from odoo.addons.smart_core.delivery.product_policy_service import ProductPolicyService
        identity = _resolve_startup_delivery_identity(workspace.env, {})
        self.assertEqual(identity["product_key"], "construction.standard", identity)
        gate = _load_platform_release_gate(workspace.env, product_key=identity["product_key"])
        self.assertFalse(gate.get("fail_closed"), gate)
        policy = ProductPolicyService(workspace.env).get_policy(product_key=identity["product_key"], enforce_release=True, enforce_access=True)
        self.assertTrue(policy.get("menu_groups"), policy)
        self.assertTrue(workspace._sc_route_authority(), "published route authority empty after successful policy/gate")
        cases = (
            (workspace.action_deduction_refund, "sc.expense.claim", "finance.deduction.refund"),
            (workspace.action_bid_deposit_return, "sc.expense.claim", "finance.deposit.bid.return"),
            (workspace.action_contract_deposit_return, "sc.expense.claim", "finance.deposit.contract.return"),
            (workspace.action_self_funding_refund, "sc.self.funding.registration", "finance.self_funding.refund"),
        )
        resolved = 0
        for call, model, category in cases:
            action = call()
            resolved += 1
            self.assertEqual(action["res_model"], model)
            self.assertEqual(action["view_mode"], "form")
            self.assertEqual(action["context"]["default_project_id"], self.project.id)
            self.assertEqual(action["context"]["default_partner_id"], self.partner.id)
            self.assertEqual(action["context"]["default_business_category_code"], category)
            self.assertEqual(action["menu_id"], self.env.ref("smart_construction_core.menu_sc_product_company_project_refund_v1").id)
        self.assertEqual(resolved, len(cases), "every declared handling carrier must be operable")

        ledger_action = workspace.action_view_refund_account()
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
        deduction_action = without_partner.action_deduction_refund()
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

    def test_shared_ledger_cannot_borrow_another_workspace_carrier(self):
        workspace = self._workspace()
        own_menu = self.env.ref(workspace._sc_dispatch_menu_xmlid)
        routes = workspace._sc_route_authority()
        ledger_id = self.env.ref("smart_construction_core.action_sc_finance_project_counterparty_position").id
        other_routes = [row for row in routes if row.get("action_id") == ledger_id and row.get("menu_id") != own_menu.id]
        self.assertTrue(other_routes, "negative requires a real published sibling carrier")
        with patch.object(type(workspace), "_sc_route_authority", return_value=other_routes):
            with self.assertRaisesRegex(UserError, "正式入口"):
                workspace.action_view_refund_account()
        with patch.object(type(workspace), "_sc_route_authority", return_value=[]):
            with self.assertRaisesRegex(UserError, "正式入口"):
                workspace.action_view_refund_account()
