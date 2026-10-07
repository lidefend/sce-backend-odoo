# -*- coding: utf-8 -*-
import ast

from lxml import etree
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "sc_gate", "data_permission_surface")
class TestDataPermissionSurface(TransactionCase):
    def test_entry_reuses_capability_model_without_contract_overlap(self):
        action = self.env.ref("smart_construction_core.action_sc_product_data_permission_v1")
        self.assertEqual(action.res_model, "res.users")
        self.assertIn("sc_runtime_company_maintainable", action.domain)
        context = ast.literal_eval(action.context)
        self.assertTrue(context["sc_runtime_user_management"])
        self.assertFalse(context["create"])
        views = {row.view_mode: row.view_id for row in action.view_ids}
        self.assertEqual(views["form"], self.env.ref("smart_construction_core.view_sc_data_permission_user_form"))
        contract = self.env.ref("smart_construction_core.business_config_contract_data_permission_form_v1")
        self.assertEqual(contract.action_id, action)
        authority = contract.contract_json["view_orchestration"]["context"]
        self.assertEqual(authority["role_authority"], "res.groups")
        self.assertEqual(authority["project_scope_authority"], "sc.project.member.assignment")

    def test_entry_authority_preserves_existing_business_admin_maintenance(self):
        personnel_action = self.env.ref("smart_construction_core.action_sc_runtime_user_management")
        permission_action = self.env.ref("smart_construction_core.action_sc_product_data_permission_v1")
        business_admin = self.env.ref("smart_construction_core.group_sc_cap_business_config_admin")
        industry_admin = self.env.ref("smart_construction_core.group_sc_cap_config_admin")

        self.assertIn(business_admin, personnel_action.groups_id)
        self.assertNotIn(industry_admin, business_admin.trans_implied_ids)
        self.assertIn(industry_admin, permission_action.groups_id)
        self.assertIn(business_admin, industry_admin.trans_implied_ids)
        self.assertEqual(personnel_action.res_model, permission_action.res_model)
        self.assertEqual(personnel_action.domain, permission_action.domain)

    def test_runtime_menu_visibility_delivers_product_config_to_business_admin(self):
        """Owner decision B (2026-10-07): the product-configuration entries
        (data permission / system parameters / numbering rules) are declared
        product functions, so they are delivered to the business-config
        capability instead of only the higher industry-config capability.

        The menu/action declarations keep ``group_sc_cap_config_admin`` and add
        ``group_sc_cap_business_config_admin``.  The industry group implies the
        business group, so the industry admin keeps its reach while the
        business admin now reaches the entries too.  No ACL, record rule or
        field permission was relaxed to make this true.
        """
        company = self.env.ref("base.main_company")
        business_group = self.env.ref(
            "smart_construction_core.group_sc_cap_business_config_admin"
        )
        industry_group = self.env.ref(
            "smart_construction_core.group_sc_cap_config_admin"
        )
        project_group = self.env.ref(
            "smart_construction_core.group_sc_cap_project_read"
        )

        def create_user(login, group):
            return self.env["res.users"].with_context(no_reset_password=True).create(
                {
                    "name": login,
                    "login": login,
                    "email": "%s@example.test" % login,
                    "company_id": company.id,
                    "company_ids": [(6, 0, [company.id])],
                    "groups_id": [(6, 0, [group.id])],
                }
            )

        business_admin = create_user("batch2a_business_admin", business_group)
        industry_admin = create_user("batch2a_industry_admin", industry_group)
        project_member = create_user("batch2a_project_member", project_group)
        personnel_menu = self.env.ref(
            "smart_construction_core.menu_sc_runtime_user_management"
        )
        config_menus = [
            self.env.ref("smart_construction_core.menu_sc_product_data_permission_v1"),
            self.env.ref("smart_construction_core.menu_sc_product_system_parameter_v1"),
            self.env.ref("smart_construction_core.menu_sc_product_numbering_rule_v1"),
        ]

        def visible(user):
            return self.env["ir.ui.menu"].with_user(user)._visible_menu_ids()

        business_visible = visible(business_admin)
        industry_visible = visible(industry_admin)
        member_visible = visible(project_member)

        self.assertIn(personnel_menu.id, business_visible)
        for menu in config_menus:
            with self.subTest(menu=menu.name):
                self.assertIn(menu.id, business_visible)
                self.assertIn(menu.id, industry_visible)
                self.assertNotIn(menu.id, member_visible)

    def test_personnel_form_separates_profile_account_and_compatible_authorization(self):
        action = self.env.ref("smart_construction_core.action_sc_runtime_user_management")
        view = self.env.ref("smart_construction_core.view_sc_runtime_user_form")
        arch = etree.fromstring(view.arch_db.encode())

        self.assertEqual(action.name, "人员档案")
        self.assertTrue(arch.xpath("//form[@string='人员档案']"))
        self.assertTrue(arch.xpath("//group[@name='sc_personnel_profile']//field[@name='name']"))
        self.assertTrue(arch.xpath("//group[@name='sc_account_management']//field[@name='password']"))
        self.assertTrue(arch.xpath("//group[@name='sc_account_management']//field[@name='active']"))
        self.assertTrue(arch.xpath("//group[@name='sc_company_scope']//field[@name='company_id']"))
        self.assertTrue(arch.xpath("//group[@name='sc_company_scope']//field[@name='company_ids']"))
        self.assertTrue(
            arch.xpath(
                "//page[@name='sc_compatible_authorization_maintenance']"
                "//field[@name='sc_user_role_group_ids']"
            )
        )
        self.assertTrue(
            arch.xpath(
                "//page[@name='sc_compatible_authorization_maintenance']"
                "//field[@name='sc_project_member_assignment_ids']"
            )
        )
        assignment_field = arch.xpath(
            "//page[@name='sc_compatible_authorization_maintenance']"
            "//field[@name='sc_project_member_assignment_ids']"
        )[0]
        project_field = assignment_field.xpath("./tree/field[@name='project_id']")[0]
        self.assertEqual(assignment_field.get("readonly"), "not id")
        self.assertEqual(project_field.get("readonly"), "id")

    def test_data_permission_form_keeps_identity_readonly_and_authority_editable(self):
        view = self.env.ref("smart_construction_core.view_sc_data_permission_user_form")
        arch = etree.fromstring(view.arch_db.encode())

        for field_name in ("name", "login", "active"):
            node = arch.xpath(
                "//group[@name='sc_permission_identity']/field[@name='%s']" % field_name
            )[0]
            self.assertEqual(node.get("readonly"), "1")
        for field_name in ("company_id", "company_ids"):
            node = arch.xpath(
                "//group[@name='sc_permission_company_scope']/field[@name='%s']" % field_name
            )[0]
            self.assertNotEqual(node.get("readonly"), "1")
        self.assertTrue(
            arch.xpath("//group[@name='sc_permission_business_roles']/field[@name='sc_user_permission_group_ids']")
        )
        self.assertTrue(
            arch.xpath("//group[@name='sc_permission_project_scope']/field[@name='sc_project_member_assignment_ids']")
        )
        assignment_field = arch.xpath(
            "//group[@name='sc_permission_project_scope']/field[@name='sc_project_member_assignment_ids']"
        )[0]
        project_field = assignment_field.xpath("./tree/field[@name='project_id']")[0]
        self.assertEqual(assignment_field.get("readonly"), "not id")
        self.assertEqual(project_field.get("readonly"), "id")
