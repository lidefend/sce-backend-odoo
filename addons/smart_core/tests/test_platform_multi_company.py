from datetime import timedelta

from odoo import Command, fields
from odoo.exceptions import AccessDenied, AccessError
from odoo.tests import TransactionCase, tagged

from ..security.auth import _validated_token_principal
from ..security.credential_service import _principal_for_user, _role_xmlids


@tagged('post_install', '-at_install', 'auth02_multi_company')
class TestPlatformMultiCompany(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.a, cls.b, cls.c = cls.env['res.company'].create([
            {'name': 'AUTH02 home'}, {'name': 'AUTH02 granted'}, {'name': 'AUTH02 ungranted'},
        ])
        cls.plan = cls.env['sc.subscription.plan'].create({
            'name': 'AUTH02 platform grant', 'code': 'auth02-company-grant',
            'multi_company_enabled': False,
        })
        cls.subscription = cls.env['sc.subscription'].create({
            'company_id': cls.a.id, 'plan_id': cls.plan.id, 'state': 'active',
        })
        cls.user = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'AUTH02 member', 'login': 'auth02-company-member',
            'company_id': cls.a.id, 'company_ids': [Command.set((cls.a | cls.b).ids)],
            'groups_id': [Command.set([cls.env.ref('base.group_user').id])],
        })

    def principal(self):
        return _principal_for_user(
            self.user, database=self.env.cr.dbname, principal_type='human',
            auth_method='password', scopes=('interactive',),
            namespace_id='ns_auth02', audience='tenant',
        )

    def test_native_companies_do_not_grant_platform_license(self):
        self.assertEqual(set(self.user.company_ids.ids), {self.a.id, self.b.id})
        self.assertEqual(self.user._sc_authorized_company_ids(), [self.a.id])
        self.assertEqual(self.principal().allowed_company_ids, (self.a.id,))

    def test_platform_grant_intersects_native_scope(self):
        self.plan.multi_company_enabled = True
        self.assertEqual(set(self.principal().allowed_company_ids), {self.a.id, self.b.id})
        self.assertNotIn(self.c.id, self.principal().allowed_company_ids)

    def test_context_cannot_select_a_more_permissive_plan(self):
        other = self.plan.copy({'code': 'auth02-other-plan', 'multi_company_enabled': True})
        self.env['sc.subscription'].create({'company_id': self.b.id, 'plan_id': other.id, 'state': 'active'})
        user = self.user.with_context(allowed_company_ids=[self.b.id], force_company=self.b.id)
        self.assertEqual(user._sc_authorized_company_ids(), [self.a.id])

    def test_revocation_is_immediate_without_changing_native_grants(self):
        self.plan.multi_company_enabled = True
        self.assertIn(self.b.id, self.principal().allowed_company_ids)
        self.plan.multi_company_enabled = False
        self.assertEqual(self.principal().allowed_company_ids, (self.a.id,))
        self.assertIn(self.b.id, self.user.company_ids.ids)

    def test_old_multicompany_token_rejected_after_revoke(self):
        self.plan.multi_company_enabled = True
        principal = self.principal()
        payload = {
            'principal_type': 'human', 'auth_method': 'password', 'credential_id': '',
            'scope': ['interactive'], 'company_id': self.b.id,
            'allowed_company_ids': list(principal.allowed_company_ids),
            'role_xmlids': list(_role_xmlids(self.user)),
            'namespace_id': 'ns_auth02', 'aud': 'tenant',
        }
        self.plan.multi_company_enabled = False
        with self.assertRaisesRegex(AccessDenied, '公司范围已失效'):
            _validated_token_principal(payload, self.user, self.env)

    def test_expired_license_does_not_survive_cached_entitlement(self):
        self.plan.multi_company_enabled = True
        self.assertIn(self.b.id, self.principal().allowed_company_ids)
        self.subscription.end_date = fields.Date.today() - timedelta(days=1)
        self.assertEqual(self.principal().allowed_company_ids, (self.a.id,))

    def test_business_user_cannot_enable_platform_plan(self):
        with self.assertRaises(AccessError):
            self.plan.with_user(self.user).write({'multi_company_enabled': True})

    def test_future_subscription_does_not_enable_multiple_companies(self):
        self.plan.multi_company_enabled = True
        self.subscription.start_date = fields.Date.today() + timedelta(days=1)
        self.assertEqual(self.user._sc_authorized_company_ids(), [self.a.id])

    def test_archived_plan_revokes_license(self):
        self.plan.write({'multi_company_enabled': True, 'active': False})
        self.assertEqual(self.user._sc_authorized_company_ids(), [self.a.id])

    def test_caller_timezone_cannot_activate_future_subscription(self):
        from unittest.mock import patch
        today = fields.Date.today()
        self.plan.multi_company_enabled = True
        self.subscription.start_date = today + timedelta(days=1)
        def local_date(record, timestamp=None):
            return today if record.env.context.get('tz') == 'UTC' else today + timedelta(days=1)
        with patch.object(fields.Date, 'context_today', side_effect=local_date):
            self.assertEqual(self.user.with_context(tz='Pacific/Kiritimati')._sc_authorized_company_ids(), [self.a.id])

    def test_data_scope_cannot_include_unlicensed_company(self):
        # The common ceiling consumes the same platform upper bound before
        # looking up data-space registrations; an unregistered home grants none.
        caller = self.user.with_user(self.user).with_context(allowed_company_ids=[self.b.id])
        self.assertEqual(caller._sc_data_company_ids(), [])

    def test_native_rule_cache_observes_platform_revocation(self):
        partner = self.env['res.partner'].create({'name': 'AUTH02 other company', 'company_id': self.b.id})
        Partners = self.env['res.partner'].with_user(self.user).with_context(allowed_company_ids=[self.a.id, self.b.id])
        self.plan.multi_company_enabled = True
        self.assertEqual(Partners.search([('id', '=', partner.id)]).ids, partner.ids)
        self.plan.multi_company_enabled = False
        self.assertFalse(Partners.search([('id', '=', partner.id)]))
        with self.assertRaises(AccessError):
            partner.with_env(Partners.env).read(['name'])

    def test_native_rule_cache_observes_license_expiry(self):
        from unittest.mock import patch
        partner = self.env['res.partner'].create({'name': 'AUTH02 expiry', 'company_id': self.b.id})
        Partners = self.env['res.partner'].with_user(self.user).with_context(allowed_company_ids=[self.a.id, self.b.id])
        today = fields.Date.today()
        self.plan.multi_company_enabled = True
        self.subscription.end_date = today
        self.assertTrue(Partners.search([('id', '=', partner.id)]))
        # Move the business date without a write/cache clear, as a real expiry does.
        with patch.object(fields.Date, 'context_today', return_value=today + timedelta(days=1)):
            self.assertFalse(Partners.search([('id', '=', partner.id)]))

    def test_native_rpc_context_cannot_switch_to_unlicensed_company(self):
        Partners = self.env['res.partner'].with_user(self.user).with_context(allowed_company_ids=[self.b.id])
        with self.assertRaisesRegex(AccessError, 'PLATFORM_COMPANY_NOT_AUTHORIZED'):
            Partners.search([])
