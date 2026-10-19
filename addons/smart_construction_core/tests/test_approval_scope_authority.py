"""Approval personnel are a role projection, never an alternative grant path."""
import secrets

from odoo.exceptions import UserError
from odoo.tests.common import tagged

from .business_case import BusinessTransactionCase


@tagged('post_install', '-at_install', 'approval_scope_authority')
class TestApprovalScopeAuthority(BusinessTransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.write({'company_ids': [(4, cls.env.company.id)]})
        cls.role = cls.env.ref('smart_construction_core.group_sc_role_partner_manager')
        internal = cls.env.ref('base.group_user')
        cls.subject = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Synthetic approval subject', 'login': 'auth01_approval_subject',
            'company_id': cls.env.company.id, 'company_ids': [(6, 0, cls.env.company.ids)],
            'groups_id': [(6, 0, internal.ids)],
        })
        cls.manager = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Synthetic approval maintainer', 'login': 'auth01_approval_maintainer',
            'company_id': cls.env.company.id, 'company_ids': [(6, 0, cls.env.company.ids)],
            'groups_id': [(6, 0, (internal | cls.env.ref(
                'smart_construction_core.group_sc_cap_business_config_admin')).ids)],
        })
        cls.scope = cls.env.ref('smart_construction_core.approval_scope_partner_manager').with_user(cls.manager)

    def _wizard(self, login):
        return self.env['sc.approval.scope.user.wizard'].with_user(self.manager).create({
            'scope_id': self.scope.id, 'name': 'Synthetic approval wizard user',
            'login': login, 'password': secrets.token_urlsafe(24),
        })

    def test_scope_write_cannot_grant_or_revoke_groups(self):
        before = set(self.role.users.ids)
        self.assertFalse(self.scope.env.su)
        with self.assertRaises(UserError), self.cr.savepoint():
            self.scope.write({'user_ids': [(6, 0, self.subject.ids)]})
        self.assertEqual(set(self.role.users.ids), before)
        self.assertNotIn(self.role, self.subject.groups_id)

    def test_old_wizard_cannot_grant_existing_account(self):
        before = set(self.subject.groups_id.ids)
        with self.assertRaises(UserError), self.cr.savepoint():
            self._wizard(self.subject.login).action_create_user()
        self.assertEqual(set(self.subject.groups_id.ids), before)

    def test_old_wizard_cannot_create_account(self):
        login = 'auth01_approval_forbidden_new'
        with self.assertRaises(UserError), self.cr.savepoint():
            self._wizard(login).action_create_user()
        self.assertFalse(self.env['res.users'].search([('login', '=', login)]))

    def test_old_open_action_is_rejected(self):
        with self.assertRaises(UserError):
            self.scope.action_open_add_user_wizard()

    def test_projection_follows_explicit_system_role(self):
        managed = self.subject.with_user(self.manager).with_context(sc_runtime_user_management=True)
        managed.write({'sc_user_role_group_ids': [(6, 0, self.role.ids)]})
        self.scope.invalidate_recordset(['user_ids'])
        self.assertIn(self.subject, self.scope.user_ids)
        managed.write({'sc_user_role_group_ids': [(6, 0, [])]})
        self.scope.invalidate_recordset(['user_ids'])
        self.assertNotIn(self.subject, self.scope.user_ids)


    def test_runtime_view_declares_readonly_without_grant_actions(self):
        from lxml import etree
        fields = self.scope.fields_get(['user_ids'])
        self.assertTrue(fields['user_ids']['readonly'])
        view = self.env.ref('smart_construction_core.view_sc_approval_scope_form')
        arch = etree.fromstring(self.scope.get_view(view_id=view.id, view_type='form')['arch'])
        users = arch.xpath("//field[@name='user_ids']")
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0].get('readonly'), '1')
        self.assertFalse(arch.xpath("//button[@name='action_open_add_user_wizard']"))
        wizard = self.env['sc.approval.scope.user.wizard'].with_user(self.manager)
        view = self.env.ref('smart_construction_core.view_sc_approval_scope_user_wizard_form')
        arch = etree.fromstring(wizard.get_view(view_id=view.id, view_type='form')['arch'])
        self.assertFalse(arch.xpath("//button[@name='action_create_user']"))
        self.assertFalse(arch.xpath("//field[@name='password']"))
