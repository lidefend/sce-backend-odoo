"""Real native projections retain independent source ownership through review."""
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'group_authority_sources')
class TestGroupAuthoritySources(TransactionCase):
    def setUp(self):
        super().setUp()
        self.base = self.env.ref('base.group_user')
        self.shared = self.env['res.groups'].create({'name': 'AUTH02 shared'})
        self.extra = self.env['res.groups'].create({'name': 'AUTH02 extra'})
        self.user = self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'AUTH02 source user', 'login': 'auth02_source_user',
            'groups_id': [(6, 0, self.base.ids)],
        })
        self.user._sc_replace_group_authority_source('role:1', self.shared.ids)

    def test_overlapping_roles_revoke_only_owned_grants(self):
        self.user._sc_replace_group_authority_source('role:2', (self.shared | self.extra).ids)
        self.user._sc_replace_group_authority_source('role:1', [])
        self.assertIn(self.shared, self.user.groups_id)
        self.user._sc_replace_group_authority_source('role:2', [])
        self.assertNotIn(self.shared, self.user.groups_id)
        self.assertNotIn(self.extra, self.user.groups_id)
        self.assertIn(self.base, self.user.groups_id)

    def test_explicit_native_grant_survives_role_revocation(self):
        self.user.write({'groups_id': [(4, self.shared.id)]})
        self.user._sc_replace_group_authority_source('role:1', [])
        self.assertIn(self.shared, self.user.groups_id)

    def test_native_replace_cannot_erase_managed_source(self):
        with self.assertRaises(UserError):
            self.user.write({'groups_id': [(6, 0, self.base.ids)]})
        self.assertIn(self.shared, self.user.groups_id)

    def _review(self):
        return self.env['sc.group.authority.reconcile'].create({
            'user_id': self.user.id,
            'root_group_ids': [(6, 0, (self.base | self.shared).ids)],
            'note': 'Retain native identity and existing role source.',
        })

    def test_confirmation_does_not_adopt_role_as_native_grant(self):
        self._review().action_confirm()
        self.user._sc_replace_group_authority_source('role:1', [])
        self.assertNotIn(self.shared, self.user.groups_id)

    def test_definition_invalidation_preserves_sources_for_review(self):
        self.shared.write({'implied_ids': [(4, self.extra.id)]})
        state = self.user.sc_group_authority_state
        self.assertEqual(state['status'], 'unresolved')
        self.assertEqual(state['sources']['role:1'], self.shared.ids)
        with self.assertRaises(UserError):
            self.user._sc_replace_group_authority_source('role:1', [])
        self._review().action_confirm()
        self.user._sc_replace_group_authority_source('role:1', [])
        self.assertNotIn(self.shared, self.user.groups_id)
        self.assertNotIn(self.extra, self.user.groups_id)
