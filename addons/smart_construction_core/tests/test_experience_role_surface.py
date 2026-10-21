from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.addons.smart_core.identity.identity_resolver import IdentityResolver
from ..core_extension_policy_maps import ROLE_SURFACE_OVERRIDES


@tagged('post_install', '-at_install', 'experience_role_contract')
class TestExperienceRoleContract(TransactionCase):
    def test_formal_catalog_resolves_experience_and_preserves_admin_precedence(self):
        resolver = IdentityResolver(self.env)
        marker = {'smart_construction_core.group_sc_role_experience'}
        self.assertEqual(resolver.resolve_role_code(marker), 'experience')
        self.assertEqual(resolver.resolve_role_code(marker | {'smart_construction_core.group_sc_role_finance_manager'}), 'experience')
        self.assertEqual(resolver.resolve_role_code(marker | {'smart_core.group_smart_core_admin'}), 'system_admin')
        self.assertNotEqual(resolver.resolve_role_code({'smart_construction_core.group_sc_role_finance_manager'}), 'experience')

    def test_surface_uses_declared_identity_and_existing_capability_discovery(self):
        resolver = IdentityResolver(self.env)
        surface = resolver.build_role_surface(
            {'smart_construction_core.group_sc_role_experience'}, [], {'workspace.home'}, ROLE_SURFACE_OVERRIDES)
        self.assertEqual(surface['role_code'], 'experience')
        self.assertEqual(surface['role_label'], '体验用户')
        self.assertTrue(surface['discover_installed_capabilities'])
        self.assertFalse(surface.get('is_platform_admin'))
        self.assertFalse(surface.get('is_business_config_admin'))


@tagged('post_install', '-at_install', 'experience_role_permissions')
class TestExperienceRolePermissions(TransactionCase):
    def test_marker_and_login_rename_do_not_grant_business_permissions(self):
        group = self.env.ref('smart_construction_core.group_sc_role_experience')
        self.assertEqual(set(group.implied_ids.ids), {self.env.ref('base.group_user').id})
        self.assertTrue(group.sc_assignable_user_permission)
        user = self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Role test', 'login': 'arbitrary-role-name', 'email': 'role@invalid.local',
            'groups_id': [(6, 0, [group.id])],
        })
        resolver = IdentityResolver(self.env)
        before = resolver.resolve(user.with_user(user).env)
        self.assertEqual(before['role_code'], 'experience')
        for model in ('payment.request', 'sc.approval.policy'):
            self.assertFalse(self.env[model].with_user(user).check_access_rights('write', raise_exception=False))
        user.login = 'renamed-without-experience-token'
        self.assertEqual(resolver.resolve(user.with_user(user).env)['role_code'], 'experience')
        user.groups_id = [(3, group.id)]
        self.assertNotEqual(resolver.resolve(user.with_user(user).env)['role_code'], 'experience')

    def test_role_switch_keeps_actual_finance_permissions(self):
        marker = self.env.ref('smart_construction_core.group_sc_role_experience')
        finance = self.env.ref('smart_construction_core.group_sc_role_finance_manager')
        user = self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Finance role test', 'login': 'role-switch-test', 'email': 'switch@invalid.local',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id, finance.id])],
        })
        resolver = IdentityResolver(self.env)
        def permissions():
            return {op: self.env['payment.request'].with_user(user).check_access_rights(op, raise_exception=False)
                    for op in ('read', 'create', 'write', 'unlink')}
        before = permissions()
        original_role = resolver.resolve(user.with_user(user).env)['role_code']
        self.assertNotEqual(original_role, 'experience')
        user.groups_id = [(4, marker.id)]
        self.assertEqual(resolver.resolve(user.with_user(user).env)['role_code'], 'experience')
        self.assertEqual(permissions(), before)
        user.groups_id = [(3, marker.id)]
        self.assertEqual(resolver.resolve(user.with_user(user).env)['role_code'], original_role)
        self.assertEqual(permissions(), before)


@tagged('post_install', '-at_install', 'experience_capability_authority')
class TestExperienceCapabilityAuthority(TransactionCase):
    def _actor(self, groups, login='capability-authority-test'):
        return self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Capability authority test', 'login': login, 'email': 'capability@invalid.local',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id] + [self.env.ref(x).id for x in groups])],
        })

    def test_unmatched_and_absent_user_never_become_owner(self):
        from ..services.capability_registry import _resolve_role_codes_for_user
        user = self._actor([])
        self.assertEqual(_resolve_role_codes_for_user(user), set())
        self.assertEqual(_resolve_role_codes_for_user(None), set())

    def test_experience_identity_preserves_real_finance_membership_without_owner_inference(self):
        from ..services.capability_registry import _resolve_role_codes_for_user, _capability_access
        user = self._actor(['smart_construction_core.group_sc_role_finance_user'])
        before = _resolve_role_codes_for_user(user)
        self.assertIn('finance', before)
        self.assertNotIn('owner', before)
        user.groups_id = [(4, self.env.ref('smart_construction_core.group_sc_role_experience').id)]
        after = _resolve_role_codes_for_user(user)
        self.assertEqual(after, before | {'experience'})
        self.assertEqual(IdentityResolver(self.env).resolve(user.with_user(user).env)['role_code'], 'experience')
        self.assertEqual(_capability_access({'required_roles': ['finance']}, after, user)[:2], (True, True))
        self.assertEqual(_capability_access({'required_roles': ['owner']}, after, user)[:2], (False, False))
        self.assertEqual(_capability_access({'required_roles': ['finance'], 'required_groups': ['smart_core.group_smart_core_admin']}, after, user)[:2], (True, False))

    def test_group_names_never_create_roles(self):
        from ..services.capability_registry import _resolve_role_codes_for_user
        group = self.env['res.groups'].create({'name': 'Owner-looking group'})
        self.env['ir.model.data'].create({'module': 'smart_construction_core',
            'name': 'group_sc_role_unregistered_owner', 'model': 'res.groups', 'res_id': group.id})
        user = self._actor([])
        user.groups_id = [(4, group.id)]
        self.assertEqual(_resolve_role_codes_for_user(user), set())

    def test_capability_rows_unchanged_when_identity_marker_is_added_or_removed(self):
        from ..services.capability_registry import list_capabilities_for_user
        user = self._actor(['smart_construction_core.group_sc_role_finance_user'])
        def facts():
            return {r['key']: (r['capability_state'], r['reason_code'])
                    for r in list_capabilities_for_user(user.with_user(user).env, user)}
        before = facts()
        self.assertTrue(before)
        marker = self.env.ref('smart_construction_core.group_sc_role_experience')
        user.groups_id = [(4, marker.id)]
        self.assertEqual(facts(), before)
        user.groups_id = [(3, marker.id)]
        self.assertEqual(facts(), before)
