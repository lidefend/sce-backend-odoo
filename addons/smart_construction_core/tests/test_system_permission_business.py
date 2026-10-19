"""Role-bound business operations; synthetic fixtures roll back with each test."""
from odoo.exceptions import AccessError
from odoo.tests.common import tagged
from .business_case import BusinessTransactionCase


@tagged('post_install', '-at_install', 'system_permission_business')
class TestSystemPermissionBusiness(BusinessTransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.write({'company_ids': [(4, cls.env.company.id)]})

    def _subject(self, suffix):
        role = self.env.ref('smart_construction_core.group_sc_role_' + suffix)
        self.assertTrue(role.sc_assignable_user_permission)
        return self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Synthetic AUTH01 business ' + suffix,
            'login': 'auth01_business_' + suffix,
            'company_id': self.env.company.id,
            'company_ids': [(6, 0, self.env.company.ids)],
            'groups_id': [(6, 0, (self.env.ref('base.group_user') | role).ids)],
        })

    def _revoke(self, user):
        user.with_context(sc_runtime_user_management=True).write({
            'sc_user_role_group_ids': [(6, 0, [])],
        })
        self.env.registry.clear_cache()

    def test_general_user_dictionary_read_without_write(self):
        user = self._subject('general_user')
        row = self.env['project.dictionary'].create({
            'name': 'Synthetic AUTH01 dictionary', 'code': 'AUTH01_READ', 'type': 'project_type',
        })
        actor = row.with_user(user)
        self.assertFalse(actor.env.su)
        self.assertEqual(actor.read(['code'])[0]['code'], 'AUTH01_READ')
        with self.assertRaises(AccessError), self.env.cr.savepoint():
            actor.write({'name': 'Forbidden dictionary write'})
        self.assertEqual(row.name, 'Synthetic AUTH01 dictionary')
        with self.assertRaises(AccessError), self.env.cr.savepoint():
            self.env['project.dictionary'].with_user(user).create({
                'name': 'Forbidden dictionary create', 'code': 'AUTH01_DENY', 'type': 'project_type',
            })
        self.assertFalse(self.env['project.dictionary'].search([('code', '=', 'AUTH01_DENY')]))

    def test_business_admin_dictionary_write_then_revoke(self):
        user = self._subject('business_admin')
        model = self.env['project.dictionary'].with_user(user)
        self.assertFalse(model.env.su)
        row = model.create({'name': 'Synthetic AUTH01 dictionary', 'code': 'AUTH01_ADMIN', 'type': 'project_type'})
        row.write({'name': 'Synthetic AUTH01 dictionary changed'})
        self.assertEqual(row.with_env(self.env).name, 'Synthetic AUTH01 dictionary changed')
        self._revoke(user)
        with self.assertRaises(AccessError), self.env.cr.savepoint():
            row.with_user(user).write({'name': 'Forbidden revoked dictionary'})
        self.assertEqual(row.with_env(self.env).name, 'Synthetic AUTH01 dictionary changed')

    def test_settlement_manager_draft_write_without_contract_write_then_revoke(self):
        user = self._subject('settlement_manager')
        project = self.env['project.project'].create({
            'name': 'Synthetic AUTH01 settlement project', 'company_id': self.env.company.id,
            'user_id': user.id,
        })
        partner = self.env['res.partner'].create({'name': 'Synthetic AUTH01 settlement partner'})
        contract = self.env['construction.contract'].create({
            'subject': 'Synthetic AUTH01 settlement contract', 'type': 'in',
            'project_id': project.id, 'partner_id': partner.id,
            'company_id': self.env.company.id, 'currency_id': self.env.company.currency_id.id,
        })
        actor_contract = contract.with_user(user)
        self.assertFalse(actor_contract.env.su)
        self.assertEqual(actor_contract.read(['subject'])[0]['subject'], contract.subject)
        with self.assertRaises(AccessError), self.env.cr.savepoint():
            actor_contract.write({'subject': 'Forbidden contract write'})
        self.assertEqual(contract.subject, 'Synthetic AUTH01 settlement contract')
        model = self.env['sc.settlement.order'].with_user(user)
        self.assertFalse(model.env.su)
        settlement = model.create({
            'name': 'Synthetic AUTH01 settlement', 'project_id': project.id,
            'partner_id': partner.id, 'settlement_unit_id': partner.id,
            'contract_id': contract.id, 'company_id': self.env.company.id,
            'currency_id': self.env.company.currency_id.id, 'settlement_type': 'out',
        })
        line = self.env['sc.settlement.order.line'].with_user(user).create({
            'settlement_id': settlement.id, 'contract_id': contract.id,
            'name': 'Synthetic AUTH01 settlement line', 'qty': 2, 'price_unit': 50,
        })
        line.write({'qty': 3})
        self.assertEqual(line.with_env(self.env).qty, 3)
        self._revoke(user)
        with self.assertRaises(AccessError), self.env.cr.savepoint():
            line.with_user(user).write({'qty': 4})
        self.assertEqual(line.with_env(self.env).qty, 3)
