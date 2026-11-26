"""Enterprise-role administration uses native CRUD/import and company rules."""
from copy import deepcopy
from unittest.mock import patch
from ..services.business_role_capabilities import AUTHORIZATIONS

from odoo.exceptions import AccessError, UserError
from odoo.tests.common import tagged
from .business_case import BusinessTransactionCase


@tagged('post_install', '-at_install', 'business_role')
class TestBusinessRole(BusinessTransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.company_id = cls.env.company
        cls.company = cls.env.company
        cls.other = cls.env['res.company'].create({'name': 'AUTH02 other enterprise'})
        cls.register_business_company(cls.other)
        cls.admin = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Business role administrator', 'login': 'business_role_admin',
            'company_id': cls.company.id, 'company_ids': [(6, 0, cls.company.ids)],
            'groups_id': [(6, 0, [cls.env.ref('base.group_user').id,
                                 cls.env.ref('smart_construction_core.group_sc_cap_business_config_admin').id])],
        })
        cls.Roles = cls.env['sc.business.role'].with_user(cls.admin).with_context(allowed_company_ids=cls.company.ids)

    def _role(self, **extra):
        return self.Roles.create(dict(name='Project observer', code='observer', company_id=self.company.id, **extra))

    def test_configuration_admin_creates_draft_without_platform_admin(self):
        role = self._role()
        self.assertFalse(self.admin.has_group('base.group_system'))
        self.assertEqual((role.state, bool(role.current_version_id)), ('enabled', False))

    def test_native_batch_load_creates_roles(self):
        result = self.Roles.load(['name', 'code'], [['Observer', 'observer'], ['Coordinator', 'coordinator']])
        self.assertFalse(result['messages'], result)
        roles = self.Roles.browse(result['ids'])
        self.assertEqual(len(roles), 2)
        self.assertEqual(set(roles.mapped('state')), {'enabled'})
        self.assertEqual(roles.company_id, self.company)

    def test_native_import_cannot_publish_or_forge_version(self):
        for field, value in [('state', 'published'), ('current_version_id', '9')]:
            with self.subTest(field=field):
                result = self.Roles.load(['name', 'code', field], [['Forged', 'forged_' + field, value]])
                self.assertFalse(result['ids'], result)
                self.assertTrue(result['messages'], result)
                self.assertFalse(self.Roles.search([('code', '=', 'forged_' + field)]))

    def test_cross_company_create_and_read_are_denied(self):
        with self.assertRaises(AccessError):
            self.Roles.create({'name': 'Foreign', 'code': 'foreign', 'company_id': self.other.id})
        foreign = self.env['sc.business.role'].create({'name': 'Foreign', 'code': 'foreign', 'company_id': self.other.id})
        self.assertFalse(self.Roles.search([('id', '=', foreign.id)]))
        with self.assertRaises(AccessError):
            foreign.with_user(self.admin).read(['name'])

    def test_empty_role_cannot_publish(self):
        role = self._role()
        with self.assertRaises(UserError):
            self.env['sc.business.role.version'].with_user(self.admin).create({'role_id': role.id}).action_publish()
        self.assertEqual((role.state, bool(role.current_version_id)), ('enabled', False))
        self.assertFalse(role.assignment_ids)

    def test_import_cannot_forge_assignment_state(self):
        role = self._role()
        result = self.env['sc.user.role.assignment'].with_user(self.admin).load(
            ['role_id/.id', 'user_id/.id', 'state'], [[str(role.id), str(self.admin.id), 'active']],
        )
        self.assertFalse(result['ids'], result)
        self.assertTrue(result['messages'], result)
        self.assertFalse(role.assignment_ids)

    def test_audit_cannot_be_forged(self):
        with self.assertRaises(AccessError):
            self.env['sc.business.role.event'].with_user(self.admin).create({
                'company_id': self.company.id, 'actor_id': self.admin.id,
                'action': 'publish',
            })


    def _qualified_mapping(self):
        # Isolate platform mapping mutations; the unpatched journey below checks
        # production admission and the real native navigation/access boundary.
        contract = deepcopy(AUTHORIZATIONS['project.list.open'])
        contract['state'] = 'verified'
        return patch.dict(AUTHORIZATIONS, {'project.list.open': contract})

    def _version(self, role):
        return self.env['sc.business.role.version'].with_user(self.admin).create({
            'role_id': role.id,
            'capability_line_ids': [(0, 0, {'capability_key': 'project.list.open'})],
        })

    def _subject(self, login='role_version_subject'):
        return self.env['res.users'].with_context(no_reset_password=True).create({
            'name': login, 'login': login, 'company_id': self.company.id,
            'company_ids': [(6, 0, self.company.ids)],
            'groups_id': [(6, 0, self.env.ref('base.group_user').ids)],
        })

    def _assignment(self, role, user):
        return self.env['sc.user.role.assignment'].with_user(self.admin).create({
            'role_id': role.id, 'user_id': user.id,
        })

    def test_publication_is_separate_from_existing_user_effect(self):
        with self._qualified_mapping():
            role = self._role()
            v1 = self._version(role)
            v1.action_publish()
            user = self._subject()
            assignment = self._assignment(role, user)
            assignment.action_activate()
            before = deepcopy(user.sc_group_authority_state)
            v2 = self._version(role)
            v2.action_publish()
            self.assertEqual(role.current_version_id, v2)
            self.assertEqual(assignment.version_id, v1)
            self.assertEqual(user.sc_group_authority_state, before)
            self.assertEqual(self._assignment(role, self._subject('new_version_user')).version_id, v2)

    def test_published_version_and_its_lines_are_immutable(self):
        with self._qualified_mapping():
            role = self._role()
            version = self._version(role)
            version.action_publish()
            for operation in (
                lambda: version.write({'description': 'rewrite'}),
                lambda: version.write({'state': 'draft'}),
                lambda: version.unlink(),
                lambda: version.capability_line_ids.unlink(),
                lambda: version.capability_line_ids.write({'capability_key': 'project.list.open'}),
            ):
                with self.assertRaises(UserError):
                    operation()
            role.write({'name': 'Renamed role', 'description': 'Updated identity description'})
            self.assertEqual(version.state, 'published')
            self.assertEqual(version.published_role_name, 'Project observer')
            self.assertIn('项目列表', version.published_capabilities_text)

    def test_assignment_version_cannot_be_changed_by_crud(self):
        with self._qualified_mapping():
            role = self._role()
            v1 = self._version(role)
            v1.action_publish()
            assignment = self._assignment(role, self._subject())
            v2 = self._version(role)
            v2.action_publish()
            with self.assertRaises(AccessError):
                assignment.write({'version_id': v2.id})
            self.assertEqual(assignment.version_id, v1)

    def test_mapping_change_does_not_rewrite_published_authority(self):
        with self._qualified_mapping():
            version = self._version(self._role())
            version.action_publish()
            with patch.dict(AUTHORIZATIONS['project.list.open'], {'verification_refs': ['changed-evidence']}):
                with self.assertRaises(UserError):
                    version._grant_roots()

    def test_unreviewed_group_without_acl_cannot_enter_capability_closure(self):
        with self._qualified_mapping():
            version = self._version(self._role())
            group = self.env['res.groups'].create({'name': 'Unreviewed method authority'})
            self.env.ref('smart_construction_core.group_sc_cap_project_read').write({
                'implied_ids': [(4, group.id)],
            })
            with self.assertRaisesRegex(UserError, '原生组继承'):
                version.action_publish()
            self.assertEqual(version.state, 'draft')

    def test_extra_model_read_permission_blocks_publication(self):
        with self._qualified_mapping():
            version = self._version(self._role())
            self.env['ir.model.access'].create({
                'name': 'Unreviewed equipment visibility',
                'model_id': self.env['ir.model']._get_id('sc.equipment.price'),
                'group_id': self.env.ref('smart_construction_core.group_sc_cap_project_read').id,
                'perm_read': True, 'perm_write': False, 'perm_create': False, 'perm_unlink': False,
            })
            with self.assertRaisesRegex(UserError, '模型权限'):
                version.action_publish()
            self.assertEqual(version.state, 'draft')

    def test_native_write_permission_requires_explicit_platform_qualification(self):
        with self._qualified_mapping():
            version = self._version(self._role())
            access = self.env.ref('smart_construction_core.access_project_project_sc_read')
            access.write({'perm_write': True})
            with self.assertRaisesRegex(UserError, '模型权限'):
                version.action_publish()
            # Synthetic platform admission proves the validator is not hardcoded
            # to read-only roles; this is not production qualification of write.
            qualified = deepcopy(AUTHORIZATIONS['project.list.open'])
            qualified['operations'] = ['read', 'write']
            qualified['native_model_access']['project.project'] = ['read', 'write']
            with patch.dict(AUTHORIZATIONS, {'project.list.open': qualified}):
                version.action_publish()
            self.assertEqual(version.state, 'published')

    def test_published_mapping_rechecks_acl_boundary_before_grant(self):
        with self._qualified_mapping():
            version = self._version(self._role())
            version.action_publish()
            # Same declared model, newly expanded operation: a frozen role must
            # reject it again when granting, not only at initial publication.
            self.env.ref('smart_construction_core.access_project_project_sc_read').write({'perm_create': True})
            with self.assertRaisesRegex(UserError, '模型权限'):
                version._grant_roots()

    def test_released_project_capability_uses_native_access_and_scope_without_mapping_patch(self):
        from ..services import capability_registry
        from odoo.addons.smart_core.delivery.effective_delivery_service import EffectiveDeliveryService
        role = self._role()
        version = self._version(role)
        version.action_publish()
        user = self._subject()
        baseline_groups = set(user.groups_id.ids)
        baseline_read = self.env['project.project'].with_user(user).check_access_rights('read', raise_exception=False)
        assignment = self._assignment(role, user)
        assignment.action_activate()
        actor = user.with_user(user).with_context(allowed_company_ids=self.company.ids)
        if 'sc.scene.company.enablement' in self.env:
            # The composed product requires enterprise scenario activation in
            # addition to native role authority. Exercise the real intent path;
            # granting a role must not silently enable a company's business.
            self.assertEqual(capability_registry.capability_authorization_for_user(
                actor, 'project.list.open')['reason_code'], 'NAVIGATION_AUTHORITY_DENIED')
            from odoo.addons.smart_core.delivery.edition_release_snapshot_service import EditionReleaseSnapshotService
            from odoo.addons.smart_construction_scene.handlers.scenario_activation import ScenarioActivationSetHandler
            EditionReleaseSnapshotService(self.env).freeze_release_surface(
                product_key='construction.standard', version='synthetic-auth02-role-journey',
                note='Rolled-back role navigation fixture', replace_active=True)
            assigned_groups = set(user.groups_id.ids)
            activation = ScenarioActivationSetHandler(self.Roles.env).run(payload={
                'intent': 'scenario.activation.set', 'params': {
                    'company_id': self.company.id, 'scene_key': 'project.initiation',
                    'enablement_scope': 'business.v1', 'enabled': True}})
            self.assertTrue(activation['ok'], activation)
            self.assertEqual(set(user.groups_id.ids), assigned_groups)
        delivery = EffectiveDeliveryService(actor.env).resolve()
        verdict = capability_registry.capability_authorization_for_user(actor, 'project.list.open')
        self.assertEqual(verdict['state'], 'allow', verdict)
        action_id = self.env.ref('smart_construction_core.action_sc_project_list').id
        from odoo.addons.smart_core.delivery.runtime_route_authority import published_pairs
        pair = next(pair for pair in published_pairs(delivery.route_authority) if pair[1] == action_id)
        from odoo.addons.smart_core.handlers.route_authority_validate import RouteAuthorityValidateHandler
        route = {'menu_id': pair[0], 'action_id': pair[1]}
        gate = RouteAuthorityValidateHandler(actor.env, su_env=actor.env['ir.model'].sudo().env)
        self.assertTrue(gate.handle(route).ok)
        from odoo.addons.smart_core.app_config_engine.services.dispatchers.action_dispatcher import ActionDispatcher
        from odoo.addons.smart_core.core.unified_page_contract_v2_assembler import assemble_unified_page_contract_v2
        source, _versions = ActionDispatcher(actor.env, actor.env['ir.model'].sudo().env).dispatch({
            'subject': 'action', 'action_id': action_id, 'view_type': 'tree',
        })
        contract = assemble_unified_page_contract_v2(
            source, source_type='ui.contract', request_id='auth02.project.readonly',
            node_actor_env=actor.env,
        )
        self.assertEqual(contract['statusContract']['globalStatus']['pageAuth'], 'read')
        rights = contract['statusContract']['globalStatus']['effectiveRecordCapabilities']
        self.assertTrue(rights['read'])
        for operation in ('create', 'write', 'unlink'):
            self.assertFalse(rights[operation])
        for create in (row for row in contract['actionContract']['actionRuleList']
                       if row['actionId'] == 'action.list.create'):
            self.assertFalse(create['authorizationAllowed'])
            self.assertFalse(create['allowed'])
        projects = self.env['project.project'].create([
            {'name': 'Allowed project', 'company_id': self.company.id,
             'user_id': self.env.uid, 'privacy_visibility': 'followers'},
            {'name': 'Private project', 'company_id': self.company.id,
             'user_id': self.env.uid, 'privacy_visibility': 'followers'},
            {'name': 'Other company project', 'company_id': self.other.id,
             'user_id': self.env.uid, 'privacy_visibility': 'followers'},
        ])
        # Entry authority is a permission fact, not a count of accessible rows.
        # Before membership there are no visible records in this sample, yet
        # the read-authorized project entry must remain available.
        self.assertFalse(actor.env['project.project'].search([('id', 'in', projects.ids)]))
        self.assertEqual(capability_registry.capability_authorization_for_user(
            actor, 'project.list.open')['state'], 'allow')
        self.assertTrue(gate.handle(route).ok)
        self.env['sc.project.member.assignment'].create({'project_id': projects[0].id, 'user_id': user.id})
        with self.assertRaisesRegex(UserError, '项目公司'), self.env.cr.savepoint():
            self.env['sc.project.member.assignment'].create({'project_id': projects[2].id, 'user_id': user.id})
        visible = actor.env['project.project'].search([('id', 'in', projects.ids)])
        self.assertEqual(visible.ids, projects[0].ids)
        # Reading must not silently include Odoo's independent export authority.
        with self.assertRaisesRegex(UserError, '导出'):
            visible.export_data(['name'])
        export_group = self.env.ref('base.group_allow_export')
        user.write({'groups_id': [(4, export_group.id)]})
        self.assertEqual(visible.export_data(['name'])['datas'], [['Allowed project']])
        for hidden in projects[1:]:
            target = hidden.with_env(actor.env)
            with self.assertRaises(AccessError):
                target.read(['name'])
            with self.assertRaises(AccessError):
                target.export_data(['name'])
        for operation in ('write', 'create', 'unlink'):
            self.assertFalse(visible.check_access_rights(operation, raise_exception=False))
        assignment.action_revoke()
        self.assertIn(export_group, user.groups_id)
        self.assertEqual(set(user.groups_id.ids), baseline_groups | set((export_group | export_group.trans_implied_ids).ids))
        self.assertEqual(actor.env['project.project'].check_access_rights('read', raise_exception=False), baseline_read)
        verdict = capability_registry.capability_authorization_for_user(actor, 'project.list.open')
        self.assertEqual(verdict['state'], 'deny', verdict)
        remaining = EffectiveDeliveryService(actor.env).resolve()
        self.assertFalse(any(pair[1] == action_id for pair in published_pairs(remaining.route_authority)))
        self.assertFalse(gate.handle(route).ok)

    def test_source_snapshot_binds_version_and_revocation_removes_it(self):
        with self._qualified_mapping():
            role = self._role()
            version = self._version(role)
            version.action_publish()
            user = self._subject()
            assignment = self._assignment(role, user)
            assignment.action_activate()
            source = assignment._source()
            self.assertIn(':version:%s' % version.id, source)
            self.assertIn(source, user.sc_group_authority_state['sources'])
            assignment.action_revoke()
            self.assertNotIn(source, user.sc_group_authority_state['sources'])
            self.assertIn(self.env.ref('base.group_user'), user.groups_id)


    def _change(self, role, assignments, operation='migrate'):
        return self.env['sc.business.role.change'].with_user(self.admin).create({
            'name': 'Explicit user authority change', 'role_id': role.id,
            'operation': operation, 'assignment_ids': [(6, 0, assignments.ids)],
        })

    def test_native_multi_selection_splits_51_users_without_applying_authority(self):
        role = self._role()
        self._version(role).action_publish()
        users = self.env['res.users'].with_context(no_reset_password=True).create([
            {'name': 'Bulk subject %s' % i, 'login': 'auth02_bulk_%s' % i,
             'company_id': self.company.id, 'company_ids': [(6, 0, self.company.ids)],
             'groups_id': [(6, 0, self.env.ref('base.group_user').ids)]}
            for i in range(51)
        ])
        assignments = self.env['sc.user.role.assignment'].with_user(self.admin).create([
            {'role_id': role.id, 'user_id': user.id} for user in users
        ])
        action = assignments.action_activate()
        batches = self.env['sc.business.role.change'].with_user(self.admin).search(action['domain'])
        self.assertEqual(sorted(len(batch.assignment_ids) for batch in batches), [1, 50])
        self.assertEqual(set(batches.assignment_ids.ids), set(assignments.ids))
        self.assertEqual(set(batches.mapped('state')), {'draft'})
        self.assertEqual(set(assignments.mapped('state')), {'draft'})
        self.assertFalse(users.filtered(lambda user: user.has_group('smart_construction_core.group_sc_cap_project_read')))

    def _queued_grant(self):
        role = self._role()
        self._version(role).action_publish()
        assignment = self._assignment(role, self._subject())
        batch = self._change(role, assignment, 'grant')
        batch.action_preview()
        batch.action_schedule()
        return batch, assignment, batch.sudo().scheduled_job_id

    def test_native_scheduler_uses_initiator_and_is_idempotent(self):
        batch, assignment, job = self._queued_grant()
        before = deepcopy(assignment.user_id.sc_group_authority_state)
        self.assertEqual(batch.scheduled_by, self.admin)
        self.assertEqual(job.user_id, self.env.ref('base.user_root'))
        self.assertEqual(job.numbercall, 1)
        batch.action_schedule()
        self.assertEqual(batch.sudo().scheduled_job_id, job)
        self.assertEqual(assignment.user_id.sc_group_authority_state, before)
        job.method_direct_trigger()
        self.assertEqual((batch.state, assignment.state, batch.queue_state), ('done', 'active', 'dispatched'))
        self.assertEqual(batch.confirmed_by, self.admin)
        after = deepcopy(assignment.user_id.sc_group_authority_state)
        job.method_direct_trigger()
        self.assertEqual(assignment.user_id.sc_group_authority_state, after)

    def test_cancelling_queued_batch_leaves_authority_unchanged(self):
        batch, assignment, job = self._queued_grant()
        before = deepcopy(assignment.user_id.sc_group_authority_state)
        batch.action_cancel()
        job.method_direct_trigger()
        self.assertEqual((batch.state, batch.queue_state, assignment.state), ('cancelled', 'cancelled', 'draft'))
        self.assertEqual(assignment.user_id.sc_group_authority_state, before)

    def test_scheduler_cannot_retain_removed_administrator_authority(self):
        batch, assignment, job = self._queued_grant()
        self.admin.write({'groups_id': [(6, 0, self.env.ref('base.group_user').ids)]})
        job.method_direct_trigger()
        self.assertEqual(batch.sudo().state, 'failed')
        self.assertEqual(assignment.sudo().state, 'draft')
        self.assertFalse(assignment.sudo().user_id.has_group('smart_construction_core.group_sc_cap_project_read'))

    def test_scheduled_batch_uses_configured_approval_without_premature_effect(self):
        self._approval_policy()
        batch, assignment, job = self._queued_grant()
        job.method_direct_trigger()
        self.assertTrue(batch.review_ids)
        self.assertEqual((batch.state, assignment.state), ('preview', 'draft'))

    def test_stale_second_scheduled_batch_does_not_undo_first_batch(self):
        first, assignment, job = self._queued_grant()
        second_assignment = self._assignment(first.role_id, self._subject('second_scheduled'))
        second = self._change(first.role_id, second_assignment, 'grant')
        second.action_preview()
        second.action_schedule()
        extra = self.env['res.groups'].create({'name': 'Independent authority after queued preview'})
        self.assertNotIn(extra, second_assignment.user_id.groups_id)
        second_assignment.user_id.sudo().write({'groups_id': [(4, extra.id)]})
        self.assertNotEqual(second._plan(), second.sudo().preview_snapshot)
        job.method_direct_trigger()
        second.sudo().scheduled_job_id.method_direct_trigger()
        second.invalidate_recordset()
        second_assignment.invalidate_recordset()
        self.assertEqual((first.state, assignment.state), ('done', 'active'))
        self.assertEqual((second.state, second_assignment.state), ('failed', 'draft'))
        self.assertIn(extra, second_assignment.user_id.groups_id)

    def test_explicit_adjustment_changes_only_selected_users_and_is_idempotent(self):
        with self._qualified_mapping():
            role = self._role()
            v1 = self._version(role)
            v1.action_publish()
            first, second = self._subject('first'), self._subject('second')
            a1, a2 = self._assignment(role, first), self._assignment(role, second)
            a1.action_activate()
            a2.action_activate()
            before_second = deepcopy(second.sc_group_authority_state)
            v2 = self._version(role)
            v2.action_publish()
            change = self._change(role, a1)
            change.action_preview()
            self.assertEqual((change.affected_count, change.retained_count), (1, 1))
            self.assertEqual(a1.version_id, v1)
            change.action_execute()
            self.assertEqual(change.state, 'done', change.result_text)
            self.assertEqual(a1.version_id, v2)
            self.assertEqual(a2.version_id, v1)
            self.assertEqual(second.sc_group_authority_state, before_second)
            after = deepcopy(first.sc_group_authority_state)
            change.action_execute()
            self.assertEqual(first.sc_group_authority_state, after)
            self.assertEqual(change.executed_count, 1)

    def test_stale_preview_does_not_overwrite_new_native_authority(self):
        with self._qualified_mapping():
            role = self._role()
            old = self._version(role)
            old.action_publish()
            user = self._subject()
            assignment = self._assignment(role, user)
            assignment.action_activate()
            self._version(role).action_publish()
            change = self._change(role, assignment)
            change.action_preview()
            extra = self.env['res.groups'].create({'name': 'New explicit authorization'})
            user.write({'groups_id': [(4, extra.id)]})
            changed = deepcopy(user.sc_group_authority_state)
            change.action_execute()
            self.assertEqual(change.state, 'failed')
            self.assertEqual(change.executed_count, 0)
            self.assertEqual(assignment.version_id, old)
            self.assertEqual(user.sc_group_authority_state, changed)
            self.assertIn(extra, user.groups_id)

    def test_emergency_revocation_preserves_other_role_and_shows_no_false_removal(self):
        with self._qualified_mapping():
            first = self._role()
            second = self.Roles.create({'name': 'Independent role', 'code': 'independent'})
            self._version(first).action_publish()
            self._version(second).action_publish()
            user = self._subject()
            a1, a2 = self._assignment(first, user), self._assignment(second, user)
            a1.action_activate()
            a2.action_activate()
            before = set(user.groups_id.ids)
            change = self._change(first, a1, 'revoke')
            change.action_preview()
            self.assertEqual(change.sudo().preview_snapshot['users'][0]['model_permission_delta'], [])
            change.action_execute()
            self.assertEqual(change.state, 'done', change.result_text)
            self.assertEqual(a1.state, 'revoked')
            self.assertEqual(a2.state, 'active')
            self.assertEqual(set(user.groups_id.ids), before)

    def test_failure_mid_batch_rolls_back_all_users_and_bindings(self):
        with self._qualified_mapping():
            role = self._role()
            old = self._version(role)
            old.action_publish()
            first, second = self._subject('first'), self._subject('second')
            a1, a2 = self._assignment(role, first), self._assignment(role, second)
            a1.action_activate()
            a2.action_activate()
            self._version(role).action_publish()
            change = self._change(role, a1 | a2)
            change.action_preview()
            before = {u.id: deepcopy(u.sc_group_authority_state) for u in first | second}
            users_type = type(first)
            original = users_type._sc_replace_group_authority_source
            def fail_second(record, source, roots):
                if record.id == second.id:
                    raise UserError('Synthetic failure after first user')
                return original(record, source, roots)
            with patch.object(users_type, '_sc_replace_group_authority_source', fail_second):
                change.action_execute()
            self.assertEqual((change.state, change.executed_count, change.failed_count), ('failed', 0, 2))
            self.assertEqual((a1 | a2).version_id, old)
            for user in first | second:
                self.assertEqual(user.sc_group_authority_state, before[user.id])

    def test_preview_cannot_be_forged_or_edited_after_confirmation_basis_is_frozen(self):
        with self._qualified_mapping():
            role = self._role()
            self._version(role).action_publish()
            assignment = self._assignment(role, self._subject())
            assignment.action_activate()
            change = self._change(role, assignment, 'revoke')
            with self.assertRaises(AccessError):
                change.write({'state': 'done'})
            change.action_preview()
            with self.assertRaises(AccessError):
                change.write({'assignment_ids': [(5, 0, 0)]})
            with self.assertRaises(AccessError):
                change.unlink()


    def test_authority_history_preserves_business_facts_after_role_rename(self):
        with self._qualified_mapping():
            role = self._role()
            version = self._version(role)
            version.action_publish()
            event = self.env['sc.business.role.event'].search([('role_id', '=', role.id), ('action', '=', 'publish')])
            snapshot = deepcopy(event.details)
            role.write({'name': 'Different current role name'})
            self.assertEqual(event.details, snapshot)
            self.assertEqual(event.details['role_name'], 'Project observer')
            self.assertEqual(event.details['actor_name'], self.admin.name)
            self.assertEqual(event.details['capability_facts']['project.list.open']['label'], '项目列表')
            self.assertIn('项目列表', event.summary)

    def test_adjustment_cannot_mix_roles_or_companies(self):
        with self._qualified_mapping():
            role = self._role()
            self._version(role).action_publish()
            assignment = self._assignment(role, self._subject())
            other = self.Roles.create({'name': 'Other role', 'code': 'other'})
            with self.assertRaises(UserError), self.env.cr.savepoint():
                self._change(other, assignment)

    def test_confirming_admin_must_be_the_previewing_admin(self):
        with self._qualified_mapping():
            role = self._role()
            self._version(role).action_publish()
            assignment = self._assignment(role, self._subject())
            assignment.action_activate()
            change = self._change(role, assignment, 'revoke')
            change.action_preview()
            before = deepcopy(assignment.user_id.sudo().sc_group_authority_state)
            with self.assertRaises(UserError):
                change.with_user(self.env.user).action_execute()
            self.assertEqual(assignment.state, 'active')
            self.assertEqual(assignment.user_id.sudo().sc_group_authority_state, before)


    def _approval_policy(self):
        group = self.env.ref('smart_construction_core.group_sc_cap_finance_manager')
        reviewer = self._subject('chosen_authority_reviewer')
        reviewer.write({'groups_id': [(4, group.id)]})
        policy = self.env['sc.approval.policy'].create({
            'name': 'User configured authority review', 'code': 'auth02_test_review',
            'target_model': 'sc.business.role.change', 'company_id': self.company.id,
            'approval_required': True, 'mode': 'single',
            'step_ids': [(0, 0, {'name': 'Enterprise chosen reviewer', 'sequence': 1, 'approval_scope_key': 'finance_manager'})],
        })
        return policy, reviewer

    def test_configured_approval_gates_grant_without_recursive_submission(self):
        with self._qualified_mapping():
            role = self._role()
            self._version(role).action_publish()
            user = self._subject()
            assignment = self._assignment(role, user)
            policy, reviewer = self._approval_policy()
            before = deepcopy(user.sc_group_authority_state)
            result = assignment.action_activate()
            batch = self.env['sc.business.role.change'].browse(result['res_id']).with_user(self.admin)
            self.assertEqual(assignment.state, 'draft')
            self.assertEqual(user.sc_group_authority_state, before)
            self.assertTrue(batch.review_ids)
            review_ids = batch.review_ids.ids
            duplicate = assignment.action_activate()
            self.assertEqual(duplicate['res_id'], batch.id)
            self.assertEqual(batch.validation_status, 'pending')
            with self.assertRaises(UserError):
                batch.action_execute()
            self.assertEqual(batch.review_ids.ids, review_ids)
            batch.with_user(reviewer).validate_tier()
            self.assertEqual(batch.validation_status, 'validated')
            self.assertEqual(batch.state, 'done', batch.result_text)
            self.assertEqual(assignment.state, 'active')
            self.assertTrue(batch.completed_review_text)
            batch.action_execute()
            self.assertEqual(batch.state, 'done', batch.result_text)
            self.assertEqual(assignment.state, 'active')
            self.assertEqual(batch.review_ids.ids, review_ids)
            self.assertEqual(self.env['sc.business.role.change'].search_count([('role_id', '=', role.id)]), 1)

    def test_pending_review_cannot_be_bypassed_by_disabling_policy(self):
        with self._qualified_mapping():
            role = self._role()
            self._version(role).action_publish()
            assignment = self._assignment(role, self._subject())
            policy, reviewer = self._approval_policy()
            result = assignment.action_activate()
            batch = self.env['sc.business.role.change'].browse(result['res_id']).with_user(self.admin)
            policy.write({'approval_required': False})
            with self.assertRaises(UserError):
                batch.action_execute()
            self.assertEqual(assignment.state, 'draft')
            self.assertTrue(batch.review_ids)

    def test_enabled_but_empty_approval_rule_does_not_fall_back_to_direct_effect(self):
        with self._qualified_mapping():
            role = self._role()
            self._version(role).action_publish()
            assignment = self._assignment(role, self._subject())
            policy, reviewer = self._approval_policy()
            policy.step_ids.write({'active': False})
            policy.step_ids.unlink()
            with self.assertRaises(UserError), self.env.cr.savepoint():
                assignment.action_activate()
            self.assertEqual(assignment.state, 'draft')

    def test_default_approval_path_applies_once_without_review_recursion(self):
        with self._qualified_mapping():
            role = self._role()
            self._version(role).action_publish()
            user = self._subject()
            assignment = self._assignment(role, user)
            before_epoch = user.token_version
            result = assignment.action_activate()
            batch = self.env['sc.business.role.change'].browse(result['res_id'])
            self.assertEqual(batch.state, 'done', batch.result_text)
            self.assertFalse(batch.review_ids)
            self.assertGreater(user.token_version, before_epoch)
            self.assertEqual(self.env['sc.business.role.change'].search_count([('role_id', '=', role.id)]), 1)
            after = user.token_version
            assignment.action_activate()
            self.assertEqual(user.token_version, after)


    def test_cancel_pending_approval_leaves_all_effective_authority_unchanged(self):
        with self._qualified_mapping():
            role = self._role()
            self._version(role).action_publish()
            user = self._subject()
            assignment = self._assignment(role, user)
            policy, reviewer = self._approval_policy()
            before = (deepcopy(user.sc_group_authority_state), set(user.groups_id.ids), user.token_version, assignment.version_id.id)
            result = assignment.action_activate()
            batch = self.env['sc.business.role.change'].browse(result['res_id']).with_user(self.admin)
            review_ids = batch.review_ids.ids
            self.assertTrue(review_ids)
            batch.action_cancel()
            self.assertEqual(batch.state, 'cancelled')
            self.assertFalse(batch.review_ids)
            self.assertEqual([row['id'] for row in batch.sudo().cancelled_review_snapshot], review_ids)
            self.assertTrue(batch.cancelled_review_text)
            self.assertEqual(batch.cancelled_by, self.admin)
            self.assertEqual((user.sc_group_authority_state, set(user.groups_id.ids), user.token_version, assignment.version_id.id), before)
            self.assertEqual(assignment.state, 'draft')
            with self.assertRaises(UserError):
                batch.action_execute()
            batch.action_cancel()
            self.assertEqual(user.token_version, before[2])

    def test_effective_authority_cannot_be_cancelled_as_pending(self):
        with self._qualified_mapping():
            role = self._role()
            self._version(role).action_publish()
            user = self._subject()
            assignment = self._assignment(role, user)
            result = assignment.action_activate()
            batch = self.env['sc.business.role.change'].browse(result['res_id']).with_user(self.admin)
            before = deepcopy(user.sc_group_authority_state)
            with self.assertRaises(UserError):
                batch.action_cancel()
            self.assertEqual(assignment.state, 'active')
            self.assertEqual(user.sc_group_authority_state, before)

    def test_context_defaults_cannot_forge_authorization_state(self):
        role = self._role()
        with self.assertRaises(AccessError):
            self.env['sc.business.role.version'].with_user(self.admin).with_context(default_state='published').create({'role_id': role.id})
        with self.assertRaises(AccessError):
            self.env['sc.business.role.change'].with_user(self.admin).with_context(default_state='done').create({'name': 'Forged', 'role_id': role.id})
        with self.assertRaises(AccessError):
            self.env['sc.user.role.assignment'].with_user(self.admin).with_context(default_state='active').create({'role_id': role.id, 'user_id': self.admin.id})


    def test_removing_effective_role_is_a_new_setting_and_preserves_prior_fact(self):
        with self._qualified_mapping():
            role = self._role()
            self._version(role).action_publish()
            user = self._subject()
            assignment = self._assignment(role, user)
            first = assignment.action_activate()
            grant = self.env['sc.business.role.change'].browse(first['res_id'])
            grant_facts = deepcopy(grant.preview_snapshot)
            second = assignment.action_revoke()
            removal = self.env['sc.business.role.change'].browse(second['res_id'])
            self.assertNotEqual(grant, removal)
            self.assertEqual((grant.state, removal.state), ('done', 'done'))
            self.assertEqual(grant.preview_snapshot, grant_facts)
            self.assertEqual(removal.operation, 'revoke')
            self.assertEqual(assignment.state, 'revoked')


    def test_project_read_binding_has_real_read_access_without_price_write_expansion(self):
        with self._qualified_mapping():
            role = self._role()
            self._version(role).action_publish()
            user = self._subject()
            self._assignment(role, user).action_activate()
            project = self.env['project.project'].create({
                'name': 'Authorized project information', 'company_id': self.company.id,
                'user_id': self.env.uid, 'privacy_visibility': 'followers',
            })
            self.env['sc.project.member.assignment'].create({'project_id': project.id, 'user_id': user.id})
            target = project.with_user(user).with_context(allowed_company_ids=self.company.ids)
            self.assertEqual(target.read(['name'])[0]['name'], project.name)
            with self.assertRaises(AccessError):
                target.write({'name': 'Unauthorized change'})
            for model in ('sc.labor.price', 'sc.equipment.price', 'sc.subcontract.price', 'sc.equipment.plan'):
                records = self.env[model].with_user(user)
                for operation in ('create', 'write', 'unlink'):
                    self.assertFalse(records.check_access_rights(operation, raise_exception=False), (model, operation))

    def test_native_list_buttons_reach_contract_with_explicit_multi_selection(self):
        view = self.env.ref('smart_construction_core.view_user_role_assignment_tree')
        projection = self.env['app.view.config'].with_user(self.admin).with_context(
            contract_view_id=view.id, contract_projection_readonly=True,
        )._generate_from_fields_view_get('sc.user.role.assignment', 'tree')
        actions = {row['name']: row for row in projection.arch_parsed.get('row_actions', [])}
        for name in ('action_activate', 'action_revoke', 'action_prepare_adjustment'):
            self.assertIn(name, actions)
            self.assertEqual(actions[name]['level'], 'toolbar')
            self.assertEqual(actions[name]['execution_scope'], 'recordset')
            self.assertEqual(actions[name]['selection'], 'multi')
            self.assertEqual(actions[name]['payload']['method'], name)
        batch_view = self.env.ref('smart_construction_core.view_business_role_change_tree')
        projection = self.env['app.view.config'].with_user(self.admin).with_context(
            contract_view_id=batch_view.id, contract_projection_readonly=True,
        )._generate_from_fields_view_get('sc.business.role.change', 'tree')
        actions = {row['name']: row for row in projection.arch_parsed.get('row_actions', [])}
        for name in ('action_preview', 'action_schedule'):
            self.assertEqual(actions[name]['level'], 'toolbar')
            self.assertEqual(actions[name]['execution_scope'], 'recordset')
            self.assertEqual(actions[name]['selection'], 'multi')
            self.assertEqual(actions[name]['payload']['method'], name)

    def test_collection_intent_executes_selected_assignments_through_fresh_contract(self):
        from odoo.addons.smart_core.handlers.execute_button import ExecuteButtonHandler
        role = self._role()
        self._version(role).action_publish()
        assignments = self._assignment(role, self._subject('intent_subject_a')) | self._assignment(role, self._subject('intent_subject_b'))
        action = self.env.ref('smart_construction_core.action_user_role_assignment')
        menu = self.env.ref('smart_construction_core.menu_user_role_assignment')
        handler = ExecuteButtonHandler(env=assignments.env, su_env=self.env, context={
            'allowed_company_ids': self.company.ids,
        }, payload={'params': {}, 'meta': {'action_id': action.id, 'menu_id': menu.id}})
        contract = handler._load_current_action_contract(model=assignments._name,
            record_id=assignments[0].id, action_id=action.id, menu_id=menu.id, view_type='tree')
        rules = [row for row in contract['actionContract']['actionRuleList']
                 if row.get('button', {}).get('name') == 'action_activate']
        self.assertEqual(len(rules), 1)
        rule = rules[0]
        self.assertEqual(rule['executionScope'], 'recordset')
        result = ExecuteButtonHandler(env=assignments.env, su_env=self.env, context={
            'allowed_company_ids': self.company.ids,
        }, payload={'params': {'model': assignments._name, 'res_id': assignments.ids,
            'button': {'name': 'action_activate', 'type': 'object', 'execution_scope': 'recordset',
                       'action_id': rule['actionId'], 'backend_identity': rule['backendIdentity'],
                       'source_widget_id': rule['sourceWidgetId']}},
            'meta': {'action_id': action.id, 'menu_id': menu.id}}).handle()
        self.assertTrue(result['ok'], result)
        assignments.invalidate_recordset()
        self.assertEqual(set(assignments.mapped('state')), {'active'})

    def test_native_import_intent_previews_and_creates_draft_assignments(self):
        import base64
        from odoo.addons.smart_core.handlers.api_data_import import ApiDataImportHandler
        role = self._role()
        self._version(role).action_publish()
        users = self._subject('import_intent_a') | self._subject('import_intent_b')
        Assignments = self.env['sc.user.role.assignment'].with_user(self.admin)
        csv = 'role_id/.id,user_id/.id,note\n' + ''.join(
            '%s,%s,Imported draft\n' % (role.id, user.id) for user in users)
        params = {'model': Assignments._name, 'file_name': 'role_assignments.csv',
                  'file_type': 'text/csv', 'file': base64.b64encode(csv.encode()).decode(),
                  'fields': ['role_id/.id', 'user_id/.id', 'note'],
                  'columns': ['role_id/.id', 'user_id/.id', 'note'], 'has_headers': True}
        # Separate pre-existing account facts from the native import savepoint,
        # as they are at the real HTTP request boundary (no test commit).
        self.env.flush_all()
        before = {user.id: deepcopy(user.sc_group_authority_state) for user in users}
        for phase in ('describe', 'inspect', 'validate', 'execute'):
            result = ApiDataImportHandler(env=Assignments.env, su_env=self.env,
                context={'allowed_company_ids': self.company.ids},
                payload={'params': dict(params, phase=phase)}).handle()
            self.assertTrue(result['ok'], result)
            if phase in ('validate', 'execute'):
                self.assertTrue(result['data']['valid'], result['data']['messages'])
            records = Assignments.search([('role_id', '=', role.id)])
            self.assertEqual(len(records), 2 if phase == 'execute' else 0)
        self.assertEqual(set(records.mapped('state')), {'draft'})
        self.assertEqual(set(records.user_id.ids), set(users.ids))
        for user in users:
            user.invalidate_recordset()
            self.assertEqual(user.sc_group_authority_state, before[user.id])
            self.assertFalse(user.has_group('smart_construction_core.group_sc_cap_project_read'))

    def test_native_import_intent_rejects_authority_and_company_injection(self):
        import base64
        from odoo.addons.smart_core.handlers.api_data_import import ApiDataImportHandler
        self.env.flush_all()
        for field, value in (('state', 'published'), ('company_id/.id', str(self.other.id))):
            with self.subTest(field=field):
                code = 'import_injection_' + field.split('/')[0]
                columns = ['name', 'code', field]
                content = ','.join(columns) + '\nInjected,' + code + ',' + value + '\n'
                result = ApiDataImportHandler(env=self.Roles.env, su_env=self.env,
                    context={'allowed_company_ids': self.company.ids}, payload={'params': {
                        'model': self.Roles._name, 'phase': 'execute', 'file_name': 'invalid_roles.csv',
                        'file_type': 'text/csv', 'file': base64.b64encode(content.encode()).decode(),
                        'fields': columns, 'columns': columns, 'has_headers': True,
                    }}).handle()
                self.assertFalse(result.get('ok') and result.get('data', {}).get('valid'), result)
                self.assertFalse(self.env['sc.business.role'].search([('code', '=', code)]))

    def test_empty_assignment_list_declares_native_import_capability(self):
        from odoo.addons.smart_core.handlers.execute_button import ExecuteButtonHandler
        action = self.env.ref('smart_construction_core.action_user_role_assignment')
        menu = self.env.ref('smart_construction_core.menu_user_role_assignment')
        handler = ExecuteButtonHandler(env=self.Roles.env, su_env=self.env,
            context={'allowed_company_ids': self.company.ids}, payload={'params': {}})
        contract = handler._load_current_action_contract(model='sc.user.role.assignment',
            record_id=0, action_id=action.id, menu_id=menu.id, view_type='tree')
        policies = contract['actionContract']['surfacePolicies']
        declarations = policies['collection_capabilities']['actions']
        imports = [row for row in declarations if row.get('action') == 'import']
        self.assertEqual(len(imports), 1)
        self.assertEqual(imports[0]['scope'], 'collection')
        self.assertEqual(imports[0]['intent'], 'api.data.import')
        self.assertIs(imports[0]['available'], True)
        self.assertNotIn('import', policies['batch_policy']['available_actions'])
        self.assertFalse(self.env['sc.user.role.assignment'].search([]))

    def test_role_initialization_entries_are_visible_and_keep_native_action_identity(self):
        from odoo.addons.smart_core.handlers.execute_button import ExecuteButtonHandler
        from odoo.addons.smart_core.delivery.native_config_menu_projection import native_config_delivery_groups
        actor = self.Roles.env
        menus = [self.env.ref('smart_construction_core.' + name) for name in (
            'menu_business_role', 'menu_user_role_assignment', 'menu_business_role_change', 'menu_business_role_event')]
        visible = actor['ir.ui.menu']._visible_menu_ids()
        self.assertTrue(all(menu.id in visible for menu in menus))
        projected = {row['menu_xmlid'] for group in native_config_delivery_groups(actor) for row in group['menus']}
        self.assertTrue({menu.get_external_id()[menu.id] for menu in menus}.issubset(projected))
        init = self.env.ref('smart_construction_core.menu_sc_enterprise_initialization')
        contract = ExecuteButtonHandler(env=actor, su_env=self.env,
            context={'allowed_company_ids': self.company.ids}, payload={'params': {}})._load_current_action_contract(
                model='res.company', record_id=self.company.id, action_id=init.action.id, menu_id=init.id)
        buttons = {str(row.get('button', {}).get('name')) for row in contract['actionContract']['actionRuleList']}
        self.assertTrue({str(menu.action.id) for menu in menus}.issubset(buttons), buttons)

    def test_initialization_scene_projects_all_native_entries_in_handling_order(self):
        from odoo.addons.smart_core.core.native_handling_entry_catalog import project_native_handling_catalog
        scene = {'code': 'enterprise.setup', 'extensions': {'native_handling_entry_source': {
            'view_xmlid': 'smart_construction_core.view_sc_enterprise_initialization_form'}}}
        catalog = project_native_handling_catalog(self.Roles.env, scene)
        self.assertEqual(catalog['item_count'], 16)
        self.assertEqual([g['key'] for g in catalog['groups']], [
            'enterprise_bootstrap', 'enterprise_business_foundation', 'enterprise_role_authority',
            'enterprise_approval_configuration', 'enterprise_scenario_configuration'])
        for group in catalog['groups']:
            for item in group['items']:
                self.assertEqual(item['target']['action_xmlid'], item['action_xmlid'])
                self.assertEqual(self.env.ref(item['action_xmlid']).res_model, item['model'])

    def test_complete_configuration_scene_keeps_native_menu_and_read_authority(self):
        from ..services.product_menu_source import load_source
        from odoo.addons.smart_core.delivery.native_config_menu_projection import native_config_delivery_groups
        actor = self.Roles.env
        visible = actor['ir.ui.menu']._visible_menu_ids()
        projected = {row['menu_xmlid'] for group in native_config_delivery_groups(actor) for row in group['menus']}
        pages = [page for row in load_source()['scenario_definitions'] for page in row['pages']]
        self.assertEqual(len(pages), 18)
        for page in pages:
            with self.subTest(menu=page['menu_xmlid']):
                menu = actor.ref(page['menu_xmlid'])
                self.assertIn(menu.id, visible)
                self.assertIn(page['menu_xmlid'], projected)
                action = menu.action.sudo()
                self.assertEqual(action.type, 'ir.actions.act_window')
                self.assertTrue(actor[action.res_model].check_access_rights('read', raise_exception=False))
