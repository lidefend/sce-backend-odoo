from odoo.tests.common import tagged

from odoo.addons.smart_construction_core.tests.business_case import BusinessTransactionCase
from odoo.addons.smart_core.delivery.edition_release_snapshot_service import EditionReleaseSnapshotService
from odoo.addons.smart_core.identity.identity_resolver import IdentityResolver


@tagged("post_install", "-at_install", "sc_gate")
class TestWorkspaceExclusiveRoleRoutes(BusinessTransactionCase):
    def test_business_full_has_all_workspace_routes_without_finance_role_inheritance(self):
        config = self.env["ir.config_parameter"].sudo()
        config.set_param("smart_core.platform_release_db", self.env.cr.dbname)
        config.set_param("smart_core.release_operator.catalog_source_db", self.env.cr.dbname)
        EditionReleaseSnapshotService(self.env).freeze_release_surface(
            product_key="construction.standard", version="synthetic-exclusive-workspaces", replace_active=True)
        actor = self.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Synthetic full business operator", "login": "synthetic-workspace-full",
            "company_id": self.env.company.id, "company_ids": [(6, 0, self.env.company.ids)],
            "groups_id": [(6, 0, [self.env.ref("smart_construction_core.group_sc_business_full").id])],
        })
        resolver = IdentityResolver(self.env(user=actor))
        _, evidence = resolver.resolve_role_codes_with_evidence(resolver.user_group_xmlids(actor))
        self.assertEqual(evidence["surface_roles"], ["business_full"])
        project = self.env["project.project"].create({
            "name": "Synthetic full business project", "user_id": actor.id,
            "company_id": self.env.company.id, "operation_strategy": "direct",
        })
        partner = self.env["res.partner"].create({"name": "Synthetic workspace counterparty"})
        cases = {
            "sc.current.account.workspace": (
                "action_project_borrow_company", "action_project_repay_company",
                "action_contractor_borrow_project", "action_contractor_repay_project",
                "action_account_transfer", "action_view_current_account"),
            "sc.company.project.refund.workspace": (
                "action_deduction_refund", "action_bid_deposit_return",
                "action_contract_deposit_return", "action_self_funding_refund", "action_view_refund_account"),
            "sc.team.loan.deduction.workspace": (
                "action_register_loan", "action_register_deduction", "action_view_account"),
        }
        observed = 0
        for model, methods in cases.items():
            workspace = self.env[model].with_user(actor).create({"project_id": project.id, "partner_id": partner.id})
            menu = self.env.ref(workspace._sc_dispatch_menu_xmlid)
            for method in methods:
                with self.subTest(model=model, method=method):
                    action = getattr(workspace, method)()
                    self.assertEqual(action["menu_id"], menu.id)
                    self.assertTrue(action["res_model"])
                    observed += 1
        self.assertEqual(observed, 14)
