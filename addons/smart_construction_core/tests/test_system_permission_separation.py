"""AUTH-01 owning-layer regressions; all synthetic data rolls back with the case."""
from odoo.tests.common import tagged
from odoo.exceptions import UserError, AccessError, ValidationError
from .business_case import BusinessTransactionCase


@tagged('post_install', '-at_install', 'system_permission_separation')
class TestSystemPermissionSeparation(BusinessTransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.write({'company_ids': [(4, cls.env.company.id)]})
        cls.internal = cls.env.ref('base.group_user')
        cls.manager = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Synthetic role maintainer', 'login': 'auth01_role_maintainer',
            'company_id': cls.env.company.id, 'company_ids': [(6, 0, cls.env.company.ids)],
            'groups_id': [(6, 0, (cls.internal | cls.env.ref('smart_construction_core.group_sc_cap_business_config_admin')).ids)],
        })
        cls.job_a = cls.env['hr.job'].create({'name': 'Synthetic position A', 'company_id': cls.env.company.id})
        cls.job_b = cls.env['hr.job'].create({'name': 'Synthetic position B', 'company_id': cls.env.company.id})

    def _group(self, suffix):
        return self.env.ref('smart_construction_core.group_sc_role_' + suffix)

    def _subject(self, suffix, extra=None):
        group = self._group(suffix)
        self.assertTrue(group.sc_assignable_user_permission)
        groups = self.internal | group
        if extra:
            groups |= self._group(extra)
        return self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Synthetic separation ' + suffix, 'login': 'auth01_separation_' + suffix,
            'company_id': self.env.company.id, 'company_ids': [(6, 0, self.env.company.ids)],
            'groups_id': [(6, 0, groups.ids)],
        })

    def _managed(self, user):
        return user.with_user(self.manager).with_context(sc_runtime_user_management=True)

    def _check_position_independence(self, suffix):
        user = self._subject(suffix)
        before = set(user.groups_id.ids)
        self._managed(user).write({'sc_personnel_job_id': self.job_a.id})
        user.invalidate_recordset()
        self.assertEqual(user.sc_personnel_job_id, self.job_a)
        self.assertEqual(set(user.groups_id.ids), before, 'position must not grant or revoke permission')
        self._managed(user).write({'sc_personnel_job_id': self.job_b.id})
        user.invalidate_recordset()
        self.assertEqual(user.sc_personnel_job_id, self.job_b)
        self.assertEqual(set(user.groups_id.ids), before)
        self._managed(user).write({'sc_user_role_group_ids': [(6, 0, [])]})
        user.invalidate_recordset()
        self.assertEqual(user.sc_personnel_job_id, self.job_b, 'role change must not change position')

    def test_accounting_manager_position_independence(self):
        self._check_position_independence('accounting_manager')

    def test_accounting_read_position_independence(self):
        self._check_position_independence('accounting_read')

    def test_accounting_user_position_independence(self):
        self._check_position_independence('accounting_user')

    def test_business_admin_position_independence(self):
        self._check_position_independence('business_admin')

    def test_general_user_position_independence(self):
        self._check_position_independence('general_user')

    def test_partner_manager_position_independence(self):
        self._check_position_independence('partner_manager')

    def test_settlement_manager_position_independence(self):
        self._check_position_independence('settlement_manager')

    def test_revoking_only_role_removes_its_exclusive_capability(self):
        user = self._subject('partner_manager')
        capability = self.env.ref('smart_construction_core.group_sc_cap_contact_manager')
        self.assertIn(capability, user.groups_id)
        self._managed(user).write({'sc_user_role_group_ids': [(6, 0, [])]})
        user.invalidate_recordset()
        self.assertNotIn(self._group('partner_manager'), user.groups_id)
        self.assertNotIn(capability, user.groups_id, 'revoked role must not leave its sole capability source active')

    def test_revocation_preserves_other_role_without_retaining_manager(self):
        user = self._subject('material_manager', extra='material_user')
        remaining = self._group('material_user')
        capability = self.env.ref('smart_construction_core.group_sc_cap_material_manager')
        self.assertIn(capability, user.groups_id)
        self._managed(user).write({'sc_user_role_group_ids': [(6, 0, remaining.ids)]})
        user.invalidate_recordset()
        self.assertIn(remaining, user.groups_id)
        self.assertNotIn(self._group('material_manager'), user.groups_id)
        self.assertNotIn(capability, user.groups_id)

    def test_native_membership_cannot_recover_explicit_grant_origin(self):
        inherited_only = self._subject('partner_manager')
        capability = self.env.ref('smart_construction_core.group_sc_cap_contact_manager')
        explicit_too = self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Synthetic explicit capability origin', 'login': 'auth01_explicit_origin',
            'company_id': self.env.company.id, 'company_ids': [(6, 0, self.env.company.ids)],
            'groups_id': [(6, 0, (self.internal | self._group('partner_manager') | capability).ids)],
        })
        self.assertEqual(set(inherited_only.groups_id.ids), set(explicit_too.groups_id.ids),
                         'distinct grant histories collapse to the same native membership')

    def test_revoked_role_cannot_blacklist_partner(self):
        user = self._subject('partner_manager')
        partner = self.env['res.partner'].create({
            'name': 'Synthetic revoked-role blacklist target', 'company_id': self.env.company.id,
        })
        actor_partner = partner.with_user(user)
        self.assertFalse(actor_partner.env.su)
        actor_partner.action_sc_add_blacklist()
        self.assertTrue(partner.sc_blacklisted, 'positive control must perform the actual action')
        actor_partner.action_sc_remove_blacklist()
        self.assertFalse(partner.sc_blacklisted)
        epoch_before = user.token_version
        self._managed(user).write({'sc_user_role_group_ids': [(6, 0, [])]})
        user.invalidate_recordset()
        self.assertNotIn(self._group('partner_manager'), user.groups_id)
        self.assertGreater(user.token_version, epoch_before, 'role revocation must invalidate old token epoch')
        # New environment after revocation: not an old recordset permission cache.
        self.env.registry.clear_cache()
        with self.assertRaises(UserError):
            partner.with_user(user).action_sc_add_blacklist()

    def test_explicit_capability_survives_role_revocation(self):
        user = self._subject('partner_manager')
        capability = self.env.ref('smart_construction_core.group_sc_cap_contact_manager')
        # Explicitly grant a second source, even though membership already exists.
        user.write({'groups_id': [(4, capability.id)]})
        self._managed(user).write({'sc_user_role_group_ids': [(6, 0, [])]})
        user.invalidate_recordset()
        self.assertNotIn(self._group('partner_manager'), user.groups_id)
        self.assertIn(capability, user.groups_id)

    def test_legacy_unknown_origin_refuses_without_changing_groups(self):
        user = self._subject('partner_manager')
        user._sc_store_group_authority(None, 'legacy fixture')
        before = set(user.groups_id.ids)
        with self.assertRaisesRegex(UserError, 'GROUP_AUTHORITY_ORIGIN_UNRESOLVED'):
            self._managed(user).write({'sc_user_role_group_ids': [(6, 0, [])]})
        self.assertEqual(set(user.groups_id.ids), before)

    def test_reverse_membership_write_invalidates_origin(self):
        user = self._subject('partner_manager')
        capability = self.env.ref('smart_construction_core.group_sc_cap_contact_manager')
        capability.write({'users': [(4, user.id)]})
        with self.assertRaisesRegex(UserError, 'GROUP_AUTHORITY_ORIGIN_UNRESOLVED'):
            self._managed(user).write({'sc_user_role_group_ids': [(6, 0, [])]})

    def test_client_cannot_supply_authority_state(self):
        user = self._subject('partner_manager')
        with self.assertRaisesRegex(AccessError, 'GROUP_AUTHORITY_STATE_SERVER_OWNED'):
            user.write({'sc_group_authority_state': {'version': 1, 'status': 'tracked', 'roots': [], 'observed': []}})

    def test_incremental_unlink_keeps_other_role(self):
        user = self._subject('material_manager', extra='material_user')
        self._managed(user).write({'sc_user_role_group_ids': [(3, self._group('material_manager').id)]})
        self.assertIn(self._group('material_user'), user.groups_id)
        self.assertNotIn(self.env.ref('smart_construction_core.group_sc_cap_material_manager'), user.groups_id)

    def test_client_context_cannot_skip_token_revocation(self):
        user = self._subject('partner_manager')
        before = user.token_version
        self._managed(user).with_context(sc_skip_token_epoch_bump=True).write({
            'sc_user_role_group_ids': [(6, 0, [])],
        })
        self.assertGreater(user.token_version, before)

    def test_client_cannot_rewrite_token_epoch(self):
        user = self._subject('partner_manager')
        before = user.token_version
        for vals in ({'token_version': before}, {'token_version': before, 'groups_id': [(6, 0, self.internal.ids)]}):
            with self.assertRaisesRegex(AccessError, 'TOKEN_EPOCH_SERVER_OWNED'), self.env.cr.savepoint():
                user.write(vals)
        self.assertEqual(user.token_version, before)
        self.assertIn(self._group('partner_manager'), user.groups_id)

    def test_private_token_revocation_increments_each_time(self):
        user = self._subject('partner_manager')
        before = user.token_version
        user._sc_bump_token_epoch()
        user._sc_bump_token_epoch()
        self.assertEqual(user.token_version, before + 2)

    def test_reverse_member_removal_invalidates_epoch(self):
        user = self._subject('partner_manager')
        before = user.token_version
        self._group('partner_manager').write({'users': [(3, user.id)]})
        self.assertNotIn(self._group('partner_manager'), user.groups_id)
        self.assertEqual(user.sc_group_authority_state['status'], 'unresolved')
        self.assertGreater(user.token_version, before)

    def test_reverse_member_addition_invalidates_epoch(self):
        user = self._subject('general_user')
        before = user.token_version
        self._group('partner_manager').write({'users': [(4, user.id)]})
        self.assertIn(self._group('partner_manager'), user.groups_id)
        self.assertEqual(user.sc_group_authority_state['status'], 'unresolved')
        self.assertGreater(user.token_version, before)

    def test_implied_definition_write_invalidates_epoch(self):
        user = self._subject('general_user')
        group = self.env['res.groups'].create({'name': 'Synthetic AUTH01 definition root'})
        user.write({'groups_id': [(4, group.id)]})
        before = user.token_version
        group.write({'implied_ids': [(4, self.env.ref('smart_construction_core.group_sc_cap_contact_manager').id)]})
        self.assertEqual(user.sc_group_authority_state['status'], 'unresolved')
        self.assertGreater(user.token_version, before)

    def test_native_boolean_group_removal_invalidates_epoch(self):
        user = self._subject('partner_manager')
        before = user.token_version
        user.write({'in_group_%s' % self._group('partner_manager').id: False})
        self.assertNotIn(self._group('partner_manager'), user.groups_id)
        self.assertEqual(user.sc_group_authority_state['status'], 'unresolved')
        self.assertGreater(user.token_version, before)

    def test_group_create_with_members_invalidates_authority_and_epoch(self):
        user = self._subject('general_user')
        other = self._subject('partner_manager')
        before, other_before = user.token_version, other.token_version
        group = self.env['res.groups'].create({
            'name': 'Synthetic AUTH01 lifecycle root', 'users': [(4, user.id)],
        })
        self.assertIn(group, user.groups_id)
        self.assertGreater(user.token_version, before)
        self.assertEqual(user.sc_group_authority_state['status'], 'unresolved')
        self.assertEqual(other.token_version, other_before)

    def test_group_delete_invalidates_authority_and_epoch(self):
        user = self._subject('general_user')
        other = self._subject('partner_manager')
        group = self.env['res.groups'].create({'name': 'Synthetic AUTH01 lifecycle root'})
        user.write({'groups_id': [(4, group.id)]})
        before, other_before = user.token_version, other.token_version
        group.unlink()
        self.assertFalse(group.exists())
        self.assertGreater(user.token_version, before)
        self.assertEqual(user.sc_group_authority_state['status'], 'unresolved')
        self.assertEqual(other.token_version, other_before)

    def test_native_selection_downgrade_invalidates_authority_and_epoch(self):
        category = self.env['ir.module.category'].create({'name': 'Synthetic AUTH01 selection category'})
        low = self.env['res.groups'].create({
            'name': 'Synthetic AUTH01 selection low', 'category_id': category.id,
        })
        high = self.env['res.groups'].create({
            'name': 'Synthetic AUTH01 selection high', 'category_id': category.id,
            'implied_ids': [(4, low.id)],
        })
        user = self._subject('general_user')
        user.write({'groups_id': [(4, high.id)]})
        fields = self.env['res.users'].fields_get(['sel_groups_%s' % '_'.join(map(str, sorted((low | high).ids)))])
        names = [name for name, value in fields.items() if name.startswith('sel_groups_') and value['type'] == 'selection']
        self.assertEqual(len(names), 1, 'test must consume an actual native selection declaration')
        before = user.token_version
        user.write({names[0]: low.id})
        self.assertNotIn(high, user.groups_id)
        self.assertIn(low, user.groups_id)
        self.assertGreater(user.token_version, before)
        self.assertEqual(user.sc_group_authority_state['status'], 'unresolved')

    def test_batch_group_delete_invalidates_only_affected_users(self):
        user = self._subject('general_user')
        other = self._subject('partner_manager')
        groups = self.env['res.groups'].create([
            {'name': 'Synthetic AUTH01 lifecycle root'},
            {'name': 'Synthetic AUTH01 lifecycle second'},
        ])
        user.write({'groups_id': [(4, group.id) for group in groups]})
        before, other_before = user.token_version, other.token_version
        groups.unlink()
        self.assertFalse(groups.exists())
        self.assertGreater(user.token_version, before)
        self.assertEqual(user.sc_group_authority_state['status'], 'unresolved')
        self.assertEqual(other.token_version, other_before)

    def test_denied_group_delete_preserves_authority_and_epoch(self):
        user = self._subject('general_user')
        group = self.env['res.groups'].create({'name': 'Synthetic AUTH01 lifecycle root'})
        user.write({'groups_id': [(4, group.id)]})
        before, state = user.token_version, dict(user.sc_group_authority_state)
        with self.assertRaises(AccessError), self.env.cr.savepoint():
            group.with_user(user).unlink()
        self.assertTrue(group.exists())
        self.assertIn(group, user.groups_id)
        self.assertEqual(user.token_version, before)
        self.assertEqual(user.sc_group_authority_state, state)

    def test_client_context_cannot_bypass_native_group_authority(self):
        subject = self._subject('partner_manager')
        system = self.env.ref('base.group_system')
        before = set(subject.groups_id.ids)
        for context in ({}, {'sc_runtime_user_management': True, 'sc_runtime_user_management_sudo': True}):
            with self.subTest(context=context), self.env.cr.savepoint():
                try:
                    with self.env.cr.savepoint():
                        subject.with_user(self.manager).with_context(context).write({'groups_id': [(4, system.id)]})
                except (AccessError, ValidationError):
                    pass
                subject.invalidate_recordset()
                self.assertEqual(set(subject.groups_id.ids), before)

    def test_company_relation_commands_cannot_write_company_records(self):
        subject = self._subject('partner_manager')
        company = self.env.company
        before = company.name
        try:
            with self.env.cr.savepoint():
                self._managed(subject).write({'company_ids': [(1, company.id, {'name': 'Unauthorized synthetic rename'})]})
        except (AccessError, ValidationError):
            pass
        company.invalidate_recordset()
        self.assertEqual(company.name, before, 'user administration must not sudo-write company records')

    def test_company_relation_rejects_related_record_crud(self):
        subject = self._subject('partner_manager')
        for command in ((0, 0, {'name': 'Synthetic forbidden company'}),
                        (1, self.env.company.id, {'name': 'Synthetic forbidden rename'}),
                        (2, self.env.company.id, 0), (9, 0, 0), (4, True, 0)):
            with self.subTest(command=command), self.assertRaises(ValidationError), self.env.cr.savepoint():
                self._managed(subject).write({'company_ids': [command]})

    def test_forged_sudo_context_cannot_create_privileged_user(self):
        import secrets
        system = self.env.ref('base.group_system')
        for index, context in enumerate(({}, {'sc_runtime_user_management': True, 'sc_runtime_user_management_sudo': True})):
            with self.subTest(context=context), self.env.cr.savepoint():
                user = self.env['res.users'].with_user(self.manager).with_context(
                    dict(context, no_reset_password=True)
                ).create({
                    'name': 'Synthetic context authority', 'login': 'auth01_context_' + str(index),
                    'password': secrets.token_urlsafe(24),
                    'company_id': self.env.company.id, 'company_ids': [(6, 0, self.env.company.ids)],
                    'groups_id': [(6, 0, (self.internal | system).ids)],
                })
                self.assertNotIn(system, user.sudo().groups_id)
                self.assertFalse(user.env.su)

    def test_business_manager_can_save_native_self_preferences(self):
        self.manager.write({'tz': 'Asia/Shanghai'})
        before = self.manager.sc_runtime_user_managed
        self.manager.with_user(self.manager).with_context({}).write({'tz': 'UTC'})
        self.manager.invalidate_recordset()
        self.assertEqual(self.manager.tz, 'UTC')
        self.assertEqual(self.manager.sc_runtime_user_managed, before)

    def test_delegated_create_cannot_inject_existing_partner_default(self):
        import secrets
        protected = self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Synthetic protected default target', 'login': 'auth01_default_protected',
            'company_id': self.env.company.id, 'company_ids': [(6, 0, self.env.company.ids)],
            'groups_id': [(6, 0, (self.internal | self.env.ref('base.group_system')).ids)],
        })
        before_name = protected.partner_id.name
        try:
            with self.env.cr.savepoint():
                created = self.env['res.users'].with_user(self.manager).with_context(
                    sc_runtime_user_management=True, default_partner_id=protected.partner_id.id,
                    no_reset_password=True,
                ).create({
                    'name': 'Synthetic injected partner default', 'login': 'auth01_default_created',
                    'password': secrets.token_urlsafe(24), 'company_id': self.env.company.id,
                    'company_ids': [(6, 0, self.env.company.ids)],
                })
                self.assertNotEqual(created.sudo().partner_id, protected.partner_id)
        except (AccessError, ValidationError):
            pass
        protected.partner_id.invalidate_recordset()
        self.assertEqual(protected.partner_id.name, before_name)

    def test_delegated_create_cannot_inject_project_assignment_default(self):
        import secrets
        project = self.env['project.project'].create({
            'name': 'Synthetic AUTH01 default project', 'company_id': self.env.company.id,
        })
        try:
            with self.env.cr.savepoint():
                created = self.env['res.users'].with_user(self.manager).with_context(
                    sc_runtime_user_management=True, no_reset_password=True,
                    default_sc_project_member_assignment_ids=[(0, 0, {'project_id': project.id, 'source': 'manual'})],
                ).create({
                    'name': 'Synthetic default assignment', 'login': 'auth01_default_assignment',
                    'password': secrets.token_urlsafe(24), 'company_id': self.env.company.id,
                    'company_ids': [(6, 0, self.env.company.ids)],
                })
                self.assertFalse(created.sudo().sc_project_member_assignment_ids)
        except (AccessError, ValidationError):
            pass

    def test_delegated_write_respects_native_record_rule(self):
        subject = self._subject('partner_manager')
        self.env['ir.rule'].create({
            'name': 'Synthetic AUTH01 user write denial',
            'model_id': self.env['ir.model']._get_id('res.users'),
            'domain_force': "[('id', '!=', %d)]" % subject.id,
            'perm_read': False, 'perm_write': True, 'perm_create': False, 'perm_unlink': False,
        })
        before = subject.name
        with self.assertRaises(AccessError), self.env.cr.savepoint():
            self._managed(subject).write({'name': 'Forbidden synthetic user edit'})
        subject.invalidate_recordset()
        self.assertEqual(subject.name, before)
        allowed = self._subject('general_user')
        self._managed(allowed).write({'name': 'Synthetic allowed rule edit'})
        self.assertEqual(allowed.name, 'Synthetic allowed rule edit')

    def test_delegated_create_respects_native_record_rule(self):
        import secrets
        login = 'auth01_rule_denied_create'
        self.env['ir.rule'].create({
            'name': 'Synthetic AUTH01 user create denial',
            'model_id': self.env['ir.model']._get_id('res.users'),
            'domain_force': "[('login', '!=', '%s')]" % login,
            'perm_read': False, 'perm_write': False, 'perm_create': True, 'perm_unlink': False,
        })
        with self.assertRaises(AccessError):
            self.env['res.users'].with_user(self.manager).with_context(
                sc_runtime_user_management=True, no_reset_password=True,
            ).create({
                'name': 'Synthetic rule denied create', 'login': login,
                'password': secrets.token_urlsafe(24), 'company_id': self.env.company.id,
                'company_ids': [(6, 0, self.env.company.ids)],
            })
        self.assertFalse(self.env['res.users'].search([('login', '=', login)]))
        self.assertFalse(self.env['res.partner'].search([('name', '=', 'Synthetic rule denied create')]))
        allowed = self.env['res.users'].with_user(self.manager).with_context(
            sc_runtime_user_management=True, no_reset_password=True,
        ).create({
            'name': 'Synthetic rule allowed create', 'login': 'auth01_rule_allowed_create',
            'password': secrets.token_urlsafe(24), 'company_id': self.env.company.id,
            'company_ids': [(6, 0, self.env.company.ids)],
        })
        self.assertTrue(allowed.exists())
        self.assertFalse(allowed.env.su)

    def test_personnel_relations_reject_other_company(self):
        subject = self._subject('partner_manager')
        other = self.env['res.company'].create({'name': 'Synthetic AUTH01 personnel other company'})
        self.register_business_company(other)
        for field, model in (('sc_personnel_department_id', 'hr.department'), ('sc_personnel_job_id', 'hr.job')):
            related = self.env[model].create({'name': 'Synthetic AUTH01 other ' + model, 'company_id': other.id})
            with self.subTest(field=field), self.assertRaises(UserError), self.env.cr.savepoint():
                self._managed(subject).write({field: related.id})
            self.assertFalse(self.env['hr.employee'].search([('user_id', '=', subject.id)]))

    def test_personnel_relations_respect_native_read_rules(self):
        subject = self._subject('partner_manager')
        for field, model in (('sc_personnel_department_id', 'hr.department'), ('sc_personnel_job_id', 'hr.job')):
            related = self.env[model].create({'name': 'Synthetic AUTH01 hidden ' + model, 'company_id': self.env.company.id})
            self.env['ir.rule'].create({
                'name': 'Synthetic AUTH01 personnel denial ' + model,
                'model_id': self.env['ir.model']._get_id(model),
                'domain_force': "[('id', '!=', %d)]" % related.id,
                'perm_read': True, 'perm_write': False, 'perm_create': False, 'perm_unlink': False,
            })
            with self.subTest(field=field), self.assertRaises(AccessError), self.env.cr.savepoint():
                self._managed(subject).write({field: related.id})
            self.assertFalse(self.env['hr.employee'].search([('user_id', '=', subject.id)]))

    def test_personnel_relations_allow_same_company_and_clear(self):
        subject = self._subject('partner_manager')
        department = self.env['hr.department'].create({
            'name': 'Synthetic AUTH01 allowed department', 'company_id': self.env.company.id,
        })
        self._managed(subject).write({'sc_personnel_department_id': department.id, 'sc_personnel_job_id': self.job_a.id})
        self.assertEqual(subject.employee_id.department_id, department)
        self.assertEqual(subject.employee_id.job_id, self.job_a)
        self._managed(subject).write({'sc_personnel_department_id': False, 'sc_personnel_job_id': False})
        self.assertFalse(subject.employee_id.department_id)
        self.assertFalse(subject.employee_id.job_id)

    def test_personnel_hidden_relation_is_rejected_before_create(self):
        import secrets
        self.env['ir.rule'].create({
            'name': 'Synthetic AUTH01 personnel create denial',
            'model_id': self.env['ir.model']._get_id('hr.job'),
            'domain_force': "[('id', '!=', %d)]" % self.job_a.id,
            'perm_read': True, 'perm_write': False, 'perm_create': False, 'perm_unlink': False,
        })
        with self.assertRaises(AccessError):
            self.env['res.users'].with_user(self.manager).with_context(no_reset_password=True).create({
                'name': 'Synthetic hidden personnel create', 'login': 'auth01_personnel_denied_create',
                'password': secrets.token_urlsafe(24), 'company_id': self.env.company.id,
                'company_ids': [(6, 0, self.env.company.ids)], 'sc_personnel_job_id': self.job_a.id,
            })
        self.assertFalse(self.env['res.users'].search([('login', '=', 'auth01_personnel_denied_create')]))

    def test_public_profile_action_respects_user_write_rule(self):
        subject = self._subject('partner_manager')
        self.env['ir.rule'].create({
            'name': 'Synthetic AUTH01 public profile user denial',
            'model_id': self.env['ir.model']._get_id('res.users'),
            'domain_force': "[('id', '!=', %d)]" % subject.id,
            'perm_read': False, 'perm_write': True, 'perm_create': False, 'perm_unlink': False,
        })
        with self.assertRaises(AccessError), self.env.cr.savepoint():
            subject.with_user(self.manager).action_sc_ensure_employee_profile()
        self.assertFalse(self.env['hr.employee'].search([('user_id', '=', subject.id)]))

    def test_public_profile_action_rejects_privileged_target(self):
        subject = self._subject('partner_manager')
        subject.write({'groups_id': [(4, self.env.ref('base.group_system').id)]})
        with self.assertRaises(UserError), self.env.cr.savepoint():
            subject.with_user(self.manager).action_sc_ensure_employee_profile()
        self.assertFalse(self.env['hr.employee'].search([('user_id', '=', subject.id)]))

    def test_public_profile_action_does_not_apply_client_defaults(self):
        subject = self._subject('partner_manager')
        self.env['ir.rule'].create({
            'name': 'Synthetic AUTH01 public profile job denial',
            'model_id': self.env['ir.model']._get_id('hr.job'),
            'domain_force': "[('id', '!=', %d)]" % self.job_a.id,
            'perm_read': True, 'perm_write': False, 'perm_create': False, 'perm_unlink': False,
        })
        subject.with_user(self.manager).with_context(default_job_id=self.job_a.id).action_sc_ensure_employee_profile()
        employee = self.env['hr.employee'].search([('user_id', '=', subject.id)])
        self.assertEqual(len(employee), 1)
        self.assertFalse(employee.job_id)

    def test_public_profile_action_checks_whole_target_set(self):
        allowed = self._subject('partner_manager')
        protected = self._subject('general_user')
        protected.write({'groups_id': [(4, self.env.ref('base.group_system').id)]})
        targets = allowed | protected
        with self.assertRaises(UserError):
            targets.with_user(self.manager).action_sc_ensure_employee_profile()
        self.assertFalse(self.env['hr.employee'].search([('user_id', 'in', targets.ids)]))

    def test_public_profile_action_is_idempotent(self):
        subject = self._subject('partner_manager')
        caller = subject.with_user(self.manager)
        self.assertTrue(caller.action_sc_ensure_employee_profile())
        first = self.env['hr.employee'].search([('user_id', '=', subject.id)])
        self.assertEqual(len(first), 1)
        self.assertTrue(caller.action_sc_ensure_employee_profile())
        self.assertEqual(self.env['hr.employee'].search([('user_id', '=', subject.id)]), first)
