# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase
from odoo.tests.common import tagged


@tagged("post_install", "-at_install", "sc_perm", "project_progress_read_boundary")
class TestProjectProgressReadBoundary(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        company = cls.env.ref("base.main_company")
        read_group = cls.env.ref("smart_construction_core.group_sc_cap_cost_read")
        cls.read_group = read_group
        cls.read_user = cls.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "project_progress_read_boundary",
                "login": "project_progress_read_boundary",
                "email": "project_progress_read_boundary@example.com",
                "company_id": company.id,
                "company_ids": [(6, 0, [company.id])],
                "groups_id": [(6, 0, [read_group.id])],
            }
        )

    def test_read_role_can_resolve_progress_entry_surface(self):
        action = self.env.ref("smart_construction_core.action_project_progress_entry")
        menu = self.env.ref("smart_construction_core.menu_sc_project_progress")

        self.assertIn(self.read_group, action.groups_id)
        self.assertIn(self.read_group, menu.groups_id)
        payload = action.with_user(self.read_user).read(["res_model"])[0]
        self.assertEqual(payload["res_model"], "project.progress.entry")

    def test_read_role_has_read_only_model_access(self):
        model = self.env["project.progress.entry"].with_user(self.read_user)

        self.assertTrue(model.check_access_rights("read", raise_exception=False))
        self.assertFalse(model.check_access_rights("write", raise_exception=False))
        self.assertFalse(model.check_access_rights("create", raise_exception=False))
        self.assertFalse(model.check_access_rights("unlink", raise_exception=False))

    def test_read_rule_is_project_member_scoped(self):
        rule = self.env.ref("smart_construction_core.rule_sc_cost_read_project_progress_entry")

        self.assertEqual(rule.model_id.model, "project.progress.entry")
        self.assertIn("project_id.user_id", rule.domain_force)
        self.assertIn("project_id.message_follower_ids.partner_id", rule.domain_force)
        self.assertTrue(rule.perm_read)
        self.assertFalse(rule.perm_write)
        self.assertFalse(rule.perm_create)
        self.assertFalse(rule.perm_unlink)
