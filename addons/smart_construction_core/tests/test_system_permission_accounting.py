"""Actual journal operations under SC accounting roles, in rollback-only fixtures."""
from odoo.exceptions import AccessError
from odoo.tests.common import tagged

from .business_case import BusinessTransactionCase


@tagged('post_install', '-at_install', 'system_permission_accounting')
class TestSystemPermissionAccounting(BusinessTransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.write({'company_ids': [(4, cls.env.company.id)]})
        cls.journal = cls.env['account.journal'].create({
            'name': 'Synthetic AUTH01 journal', 'code': 'AUT01',
            'type': 'general', 'company_id': cls.env.company.id,
        })

    def _subject(self, suffix):
        role = self.env.ref('smart_construction_core.group_sc_role_' + suffix)
        self.assertTrue(role.sc_assignable_user_permission)
        return self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Synthetic accounting ' + suffix,
            'login': 'auth01_accounting_' + suffix,
            'company_id': self.env.company.id,
            'company_ids': [(6, 0, self.env.company.ids)],
            'groups_id': [(6, 0, (self.env.ref('base.group_user') | role).ids)],
        })

    def _readonly_configuration(self, suffix):
        user = self._subject(suffix)
        journal = self.journal.with_user(user)
        self.assertFalse(journal.env.su)
        self.assertEqual(journal.read(['name'])[0]['name'], self.journal.name)
        with self.assertRaises(AccessError), self.env.cr.savepoint():
            journal.write({'name': 'Forbidden journal configuration'})
        self.assertEqual(self.journal.name, 'Synthetic AUTH01 journal')
        with self.assertRaises(AccessError), self.env.cr.savepoint():
            self.env['account.journal'].with_user(user).create({
                'name': 'Forbidden AUTH01 journal', 'code': 'AUT02',
                'type': 'general', 'company_id': self.env.company.id,
            })
        self.assertFalse(self.env['account.journal'].search([
            ('code', '=', 'AUT02'), ('company_id', '=', self.env.company.id)]))

    def test_accounting_read_cannot_configure_journal(self):
        self._readonly_configuration('accounting_read')

    def test_accounting_user_cannot_configure_journal(self):
        self._readonly_configuration('accounting_user')

    def test_accounting_manager_write_then_revoke(self):
        user = self._subject('accounting_manager')
        journal = self.env['account.journal'].with_user(user)
        self.assertFalse(journal.env.su)
        created = journal.create({
            'name': 'Synthetic AUTH01 manager journal', 'code': 'AUT03',
            'type': 'general', 'company_id': self.env.company.id,
        })
        created.write({'name': 'Synthetic AUTH01 manager changed'})
        self.assertEqual(created.with_env(self.env).name, 'Synthetic AUTH01 manager changed')
        user.with_context(sc_runtime_user_management=True).write({
            'sc_user_role_group_ids': [(6, 0, [])],
        })
        self.env.registry.clear_cache()
        with self.assertRaises(AccessError), self.env.cr.savepoint():
            created.with_user(user).write({'name': 'Forbidden after revoke'})
        self.assertEqual(created.with_env(self.env).name, 'Synthetic AUTH01 manager changed')

    def test_accounting_user_posts_entry_reader_and_revoked_user_cannot_create(self):
        user = self._subject('accounting_user')
        reader = self._subject('accounting_read')
        debit = self.env['account.account'].create({
            'name': 'Synthetic AUTH01 debit', 'code': 'AUTH0101',
            'account_type': 'asset_current', 'company_id': self.env.company.id,
        })
        credit = self.env['account.account'].create({
            'name': 'Synthetic AUTH01 credit', 'code': 'AUTH0102',
            'account_type': 'liability_current', 'company_id': self.env.company.id,
        })
        values = {
            'ref': 'Synthetic AUTH01 journal entry',
            'journal_id': self.journal.id, 'company_id': self.env.company.id,
            'move_type': 'entry',
            'line_ids': [
                (0, 0, {'name': 'Synthetic AUTH01 debit line', 'account_id': debit.id, 'debit': 100}),
                (0, 0, {'name': 'Synthetic AUTH01 credit line', 'account_id': credit.id, 'credit': 100}),
            ],
        }
        model = self.env['account.move'].with_user(user)
        self.assertFalse(model.env.su)
        move = model.create(values)
        self.assertEqual(move.state, 'draft')
        move.action_post()
        self.assertEqual(move.with_env(self.env).state, 'posted')
        self.assertEqual(sum(move.with_env(self.env).line_ids.mapped('balance')), 0)
        self.assertEqual(move.with_user(reader).read(['state'])[0]['state'], 'posted')
        with self.assertRaises(AccessError), self.env.cr.savepoint():
            self.env['account.move'].with_user(reader).create(values)
        user.with_context(sc_runtime_user_management=True).write({
            'sc_user_role_group_ids': [(6, 0, [])],
        })
        self.env.registry.clear_cache()
        with self.assertRaises(AccessError), self.env.cr.savepoint():
            self.env['account.move'].with_user(user).create(values)
        self.assertEqual(self.env['account.move'].search_count([
            ('ref', '=', values['ref']), ('company_id', '=', self.env.company.id)]), 1)
        self.assertEqual(move.with_env(self.env).state, 'posted')
