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


@tagged("post_install", "-at_install", "sc_gate")
class TestPublishedRoleReplacementMenus(BusinessTransactionCase):
    def test_existing_read_capabilities_survive_formal_menu_replacement(self):
        from odoo.addons.smart_core.delivery.menu_fact_service import MenuFactService
        from odoo.addons.smart_core.delivery.delivery_engine import DeliveryEngine
        from odoo.addons.smart_construction_core.core_extension_policy_maps import ROLE_SURFACE_OVERRIDES

        config = self.env["ir.config_parameter"].sudo()
        config.set_param("smart_core.platform_release_db", self.env.cr.dbname)
        config.set_param("smart_core.release_operator.catalog_source_db", self.env.cr.dbname)
        EditionReleaseSnapshotService(self.env).freeze_release_surface(
            product_key="construction.standard", version="synthetic-role-replacements", replace_active=True)
        cases = {
            "owner": ("group_sc_role_owner", ["menu_sc_p1_daily_contract"]),
            "project_member": ("group_sc_cap_business_initiator", ["menu_sc_p1_daily_contract"]),
            "pm": ("group_sc_role_project_manager", ["menu_sc_p1_daily_contract",
                "menu_sc_p1_project_budget", "menu_sc_p1_expense_settlement", "menu_sc_p1_income_settlement"]),
        }
        old = {"menu_sc_general_contract", "menu_sc_project_budget",
               "menu_sc_expense_contract_settlement", "menu_sc_income_contract_settlement"}
        for role, (group, menus) in cases.items():
            with self.subTest(role=role):
                actor = self.env["res.users"].with_context(no_reset_password=True).create({
                    "name": "Synthetic navigation " + role, "login": "synthetic-nav-" + role,
                    "company_id": self.env.company.id, "company_ids": [(6, 0, self.env.company.ids)],
                    "groups_id": [(6, 0, [self.env.ref("base.group_user").id,
                        self.env.ref("smart_construction_core." + group).id,
                        self.env.ref("smart_construction_core.group_sc_cap_project_read").id])],
                })
                actor_env = self.env(user=actor)
                native = MenuFactService(actor_env).export_visible_menu_facts()
                resolver = IdentityResolver(actor_env)
                surface = resolver.build_role_surface(resolver.user_group_xmlids(actor), native.tree,
                    {"workspace.home"}, ROLE_SURFACE_OVERRIDES)
                self.assertEqual(surface["role_code"], role)
                delivery = DeliveryEngine(actor_env).build(
                    data={"role_surface": surface, "scenes": [], "capabilities": []},
                    product_key="construction.standard", edition_key="standard",
                    base_product_key="construction", native_nav=native.tree)
                nodes = list(resolver._walk_nav_nodes(delivery.get("nav") or []))
                by_xmlid = {str(n.get("xmlid") or n.get("xml_id") or n.get("menu_xmlid")
                    or (n.get("meta") or {}).get("menu_xmlid") or ""): n for n in nodes}
                for name in menus:
                    xmlid = "smart_construction_core." + name
                    self.assertIn(xmlid, by_xmlid)
                    menu = self.env.ref(xmlid)
                    self.assertTrue(menu.groups_id & actor.groups_id)
                    self.assertTrue(actor_env[menu.action.res_model].check_access_rights("read", raise_exception=False))
                self.assertFalse({"smart_construction_core." + x for x in old} & set(by_xmlid))
                home = by_xmlid["smart_construction_core.menu_sc_workspace_home"]
                self.assertEqual(home.get("route") or (home.get("meta") or {}).get("route"), "/s/workspace.home")
                if role == "owner":
                    self.assertFalse(actor_env["sc.general.contract"].check_access_rights("write", raise_exception=False))
