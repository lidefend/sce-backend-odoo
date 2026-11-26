"""P1 integration witnesses for the P0 explicit-origin reconciliation mechanism."""
from odoo.exceptions import AccessError, UserError
from odoo.tests.common import tagged
from .business_case import BusinessTransactionCase


@tagged('post_install', '-at_install', 'group_authority_reconciliation')
class TestGroupAuthorityReconciliation(BusinessTransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.write({'company_ids': [(4, cls.env.company.id)]})
        cls.internal = cls.env.ref('base.group_user')
        cls.role = cls.env.ref('smart_construction_core.group_sc_role_partner_manager')
        cls.capability = cls.env.ref('smart_construction_core.group_sc_cap_contact_manager')
        def user(suffix, groups):
            return cls.env['res.users'].with_context(no_reset_password=True).create({
                'name': 'Synthetic authority ' + suffix, 'login': 'auth01_reconcile_' + suffix,
                'company_id': cls.env.company.id, 'company_ids': [(6, 0, cls.env.company.ids)],
                'groups_id': [(6, 0, (cls.internal | groups).ids)],
            })
        cls.admin = user('admin', cls.env.ref('base.group_system'))
        cls.manager = user('manager', cls.env.ref('smart_construction_core.group_sc_cap_business_config_admin'))
        cls.subject = user('subject', cls.role)
        cls.subject._sc_store_group_authority(None, 'legacy synthetic origin')

    def _review(self, extra=None):
        action = self.subject.with_user(self.admin).action_sc_review_group_authority()
        review = self.env[action['res_model']].with_user(self.admin).browse(action['res_id'])
        self.assertFalse(review.env.su)
        self.assertFalse(review.root_group_ids, 'never infer roots from effective membership')
        roots = self.internal | self.role
        if extra:
            roots |= extra
        review.write({'root_group_ids': [(6, 0, roots.ids)], 'note': 'Synthetic explicit source confirmation'})
        return review

    def _managed(self):
        return self.subject.with_user(self.manager).with_context(sc_runtime_user_management=True)

    def test_native_xml_reload_preserves_known_role_and_capability_origins(self):
        from copy import deepcopy
        from odoo.tools.convert import convert_file
        operation = self.env.ref('smart_construction_core.group_sc_role_operation_user')
        self.subject.write({'groups_id': [(6, 0, (self.internal | operation).ids)]})
        users = self.subject | self.manager
        before = {user.id: (deepcopy(user.sc_group_authority_state), set(user.groups_id.ids)) for user in users}
        self.assertTrue(all(state['status'] == 'tracked' for state, groups in before.values()))
        for filename in ('sc_capability_groups.xml', 'contract_settlement_capability_bridge.xml',
                         'sc_role_groups.xml', 'sc_role_entry_groups.xml'):
            convert_file(self.env, 'smart_construction_core', 'security/' + filename, {}, mode='update')
        for user in users:
            self.assertEqual(user.sc_group_authority_state, before[user.id][0])
            self.assertEqual(set(user.groups_id.ids), before[user.id][1])
            user._sc_explicit_group_roots()

    def test_unchanged_definition_and_member_replay_preserve_confirmed_origin(self):
        self._review().action_confirm()
        before = dict(self.subject.sc_group_authority_state)
        epoch = self.subject.token_version
        self.role.write({'implied_ids': [(6, 0, self.role.implied_ids.ids)]})
        self.role.write({'users': [(6, 0, self.role.users.ids)]})
        self.assertEqual(self.subject.sc_group_authority_state, before)
        self.assertEqual(self.subject.token_version, epoch)
        self._managed().write({'sc_user_role_group_ids': [(6, 0, [])]})
        self.assertNotIn(self.capability, self.subject.groups_id)

    def test_unchanged_replay_never_recovers_unknown_origin(self):
        before = dict(self.subject.sc_group_authority_state)
        self.role.write({'implied_ids': [(6, 0, self.role.implied_ids.ids)]})
        self.assertEqual(self.subject.sc_group_authority_state, before)
        with self.assertRaises(UserError):
            self._managed().write({'sc_user_role_group_ids': [(6, 0, [])]})

    def test_actual_definition_change_still_invalidates_confirmed_origin(self):
        self._review().action_confirm()
        extra = self.env['res.groups'].create({'name': 'Synthetic new authority edge'})
        epoch = self.subject.token_version
        self.role.write({'implied_ids': [(4, extra.id)]})
        self.assertIn(extra, self.subject.groups_id)
        self.assertEqual(self.subject.sc_group_authority_state['status'], 'unresolved')
        self.assertGreater(self.subject.token_version, epoch)
        with self.assertRaises(UserError):
            self._managed().write({'sc_user_role_group_ids': [(6, 0, [])]})

    def test_actual_reverse_membership_change_still_invalidates_origin(self):
        self._review().action_confirm()
        extra = self.env['res.groups'].create({'name': 'Synthetic reverse membership'})
        extra.write({'users': [(4, self.subject.id)]})
        self.assertEqual(self.subject.sc_group_authority_state['status'], 'unresolved')
        with self.assertRaises(UserError):
            self._managed().write({'sc_user_role_group_ids': [(6, 0, [])]})

    def test_confirmation_preserves_permissions_and_enables_role_revocation(self):
        before = set(self.subject.groups_id.ids)
        review = self._review()
        review.action_confirm()
        self.assertEqual(set(self.subject.groups_id.ids), before)
        audit = self.env['sc.group.authority.confirmation'].with_user(self.admin).search([('user_id', '=', self.subject.id)])
        self.assertEqual(len(audit), 1)
        self.assertEqual(audit.actor_id, self.admin)
        self.assertEqual(audit.before_snapshot['state']['status'], 'unresolved')
        self.assertEqual(set(audit.root_group_ids_json), set((self.internal | self.role).ids))
        self._managed().write({'sc_user_role_group_ids': [(6, 0, [])]})
        self.assertNotIn(self.capability, self.subject.groups_id)
        self.assertTrue(audit.exists(), 'later role changes must not erase confirmation history')

    def test_explicit_independent_capability_survives_later_revocation(self):
        self._review(extra=self.capability).action_confirm()
        self._managed().write({'sc_user_role_group_ids': [(6, 0, [])]})
        self.assertIn(self.capability, self.subject.groups_id)

    def test_business_manager_cannot_open_or_create_review(self):
        with self.assertRaises(AccessError):
            self.subject.with_user(self.manager).action_sc_review_group_authority()
        with self.assertRaises(AccessError):
            self.env['sc.group.authority.reconcile'].with_user(self.manager).create({'user_id': self.subject.id})

    def test_forged_snapshot_and_target_rebinding_are_rejected(self):
        review = self._review()
        for vals in ({'snapshot': {}}, {'user_id': self.admin.id}, {'confirmed': True}, {'observed_group_ids': [(5, 0, 0)]}):
            with self.subTest(vals=vals), self.assertRaises(AccessError):
                review.write(vals)
        with self.assertRaises(AccessError):
            self.env['sc.group.authority.reconcile'].with_user(self.admin).create({'user_id': self.subject.id, 'snapshot': {}})

    def test_incomplete_and_expanding_roots_are_rejected(self):
        review = self._review()
        before = set(self.subject.groups_id.ids)
        for roots in (self.internal, self.internal | self.role | self.env.ref('base.group_system')):
            review.write({'root_group_ids': [(6, 0, roots.ids)]})
            with self.assertRaises(UserError):
                review.action_confirm()
            self.assertEqual(set(self.subject.groups_id.ids), before)
            self.assertEqual(self.subject.sc_group_authority_state['status'], 'unresolved')

    def test_blank_basis_is_rejected(self):
        review = self._review()
        review.write({'note': '   '})
        with self.assertRaises(UserError):
            review.action_confirm()

    def test_source_revision_drift_rejects_stale_review(self):
        review = self._review()
        self.subject._sc_store_group_authority(None, 'new synthetic source observation')
        with self.assertRaises(UserError):
            review.action_confirm()

    def test_membership_drift_rejects_stale_review(self):
        review = self._review()
        self.subject.write({'groups_id': [(4, self.env.ref('smart_construction_core.group_sc_role_material_user').id)]})
        with self.assertRaises(UserError):
            review.action_confirm()

    def test_double_confirmation_and_other_owner_are_rejected(self):
        review = self._review()
        with self.assertRaises(AccessError):
            review.with_user(self.manager).action_confirm()
        review.action_confirm()
        with self.assertRaises(UserError):
            review.action_confirm()

    def test_audit_cannot_be_forged_modified_or_deleted(self):
        self._review().action_confirm()
        Audit = self.env['sc.group.authority.confirmation'].with_user(self.admin)
        audit = Audit.search([('user_id', '=', self.subject.id)])
        with self.assertRaises(AccessError):
            Audit.create({'user_id': self.subject.id})
        with self.assertRaises(AccessError):
            audit.write({'note': 'forged'})
        with self.assertRaises(AccessError):
            audit.unlink()
        with self.assertRaises(AccessError):
            audit.with_user(self.manager).read(['note'])

    def test_runtime_view_exposes_explicit_confirmation(self):
        from lxml import etree
        review = self._review()
        view = self.env.ref('smart_core.view_group_authority_reconcile_form')
        arch = etree.fromstring(review.get_view(view_id=view.id, view_type='form')['arch'])
        self.assertEqual(len(arch.xpath("//button[@name='action_confirm']")), 1)
        metadata = review.fields_get(['observed_group_ids', 'root_group_ids', 'snapshot'])
        self.assertTrue(metadata['observed_group_ids']['readonly'])
        self.assertTrue(metadata['snapshot']['readonly'])
        self.assertFalse(metadata['root_group_ids']['readonly'])


    def test_group_definition_drift_rejects_stale_review(self):
        review = self._review()
        self.role.write({'implied_ids': [(4, self.internal.id)]})
        with self.assertRaises(UserError):
            review.action_confirm()

    def test_operator_loses_admin_authority_before_confirmation(self):
        review = self._review()
        self.admin.write({'groups_id': [(6, 0, self.internal.ids)]})
        with self.assertRaises(AccessError):
            review.action_confirm()

    def test_target_activation_drift_rejects_stale_review(self):
        review = self._review()
        self.subject.write({'active': False})
        with self.assertRaises(UserError):
            review.action_confirm()


    def test_native_user_entry_is_admin_only_and_history_is_readonly(self):
        from lxml import etree
        view = self.env.ref('base.view_users_form')
        for actor, expected in ((self.admin, 1), (self.manager, 0)):
            Users = self.env['res.users'].with_user(actor)
            arch = etree.fromstring(Users.get_view(view_id=view.id, view_type='form')['arch'])
            self.assertEqual(len(arch.xpath("//button[@name='action_sc_review_group_authority']")), expected)
            self.assertEqual(len(arch.xpath("//button[@name='action_sc_group_authority_confirmations']")), expected)
        action = self.subject.with_user(self.admin).action_sc_group_authority_confirmations()
        self.assertEqual(action['domain'], [('user_id', '=', self.subject.id)])
        Audit = self.env['sc.group.authority.confirmation'].with_user(self.admin)
        view = self.env.ref('smart_core.view_group_authority_confirmation_form')
        arch = etree.fromstring(Audit.get_view(view_id=view.id, view_type='form')['arch'])
        self.assertEqual(arch.get('edit'), '0')
        self.assertTrue(all(field['readonly'] for field in Audit.fields_get(['note', 'before_snapshot', 'after_state']).values()))

    def test_confirmed_review_cannot_change_roots_or_basis(self):
        review = self._review()
        review.action_confirm()
        roots, note = review.root_group_ids, review.note
        for values in ({'note': 'Changed after confirmation'}, {'root_group_ids': [(5, 0, 0)]}):
            with self.subTest(values=values), self.assertRaisesRegex(AccessError, 'GROUP_AUTHORITY_REVIEW_IMMUTABLE'), self.env.cr.savepoint():
                review.write(values)
        self.assertEqual(review.root_group_ids, roots)
        self.assertEqual(review.note, note)
        audit = self.env['sc.group.authority.confirmation'].search([('user_id', '=', self.subject.id)])
        self.assertEqual(len(audit), 1)
        self.assertEqual(audit.note, note)
        self.assertEqual(set(audit.root_group_ids_json), set(roots.ids))
