"""The data-space ceiling reads membership facts, never the ORM cache helper.

``res.users.has_group`` is a ``tools.ormcache`` helper. A long-lived worker
keeps its last answer when membership is changed by an out-of-band writer
(``odoo shell``, cron, ops script) that never signals cache invalidation. The
deployed daily runtime returned 403 for a correctly enrolled operator exactly
this way, and the same window would keep serving a just-revoked principal.
The ceiling decides authorization, so it must read the persisted relation.
"""
from unittest.mock import patch

from odoo import Command, SUPERUSER_ID
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'data_space_uncached_membership')
class TestDataSpaceUncachedMembership(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Registration = cls.env['sc.tenant.company.registration'].sudo()

    def _space(self, purpose, tenant_key, name):
        return self.Registration._create_non_customer_space(
            tenant_key=tenant_key, purpose=purpose, company_name=name)

    def _operator(self, login, company, group_xmlids):
        return self.env['res.users'].with_user(SUPERUSER_ID).with_context(
            no_reset_password=True).create({
                'name': 'Uncached membership %s' % login,
                'login': login,
                'company_id': company.id,
                'company_ids': [Command.set([company.id])],
                'groups_id': [Command.set(
                    [self.env.ref(xmlid).id for xmlid in group_xmlids])],
            })

    def _caller(self, user, company):
        return user.with_user(user).with_context(allowed_company_ids=[company.id])

    def test_ceiling_does_not_consult_the_cached_group_helper(self):
        registration = self._space('test', 'uncached-membership-helper', 'Uncached membership A')
        company = registration.company_id
        operator = self._operator('uncached_membership_operator', company, [
            'base.group_user', 'smart_core.group_smart_core_non_customer_data_user',
        ])
        caller = self._caller(operator, company)
        self.assertEqual(caller._sc_data_company_ids(), [company.id])

        with patch.object(
            type(self.env['res.users']), 'has_group',
            side_effect=AssertionError('cached group helper consulted'),
        ):
            self.assertEqual(caller._sc_data_company_ids(), [company.id])

    def test_out_of_band_revocation_is_visible_without_a_cache_signal(self):
        registration = self._space('test', 'uncached-membership-revoke', 'Uncached membership B')
        company = registration.company_id
        group = self.env.ref('smart_core.group_smart_core_non_customer_data_user')
        operator = self._operator('uncached_membership_revoked', company, [
            'base.group_user', 'smart_core.group_smart_core_non_customer_data_user',
        ])
        caller = self._caller(operator, company)
        self.assertEqual(caller._sc_data_company_ids(), [company.id])

        self.env.cr.execute(
            'DELETE FROM res_groups_users_rel WHERE uid = %s AND gid = %s',
            (operator.id, group.id),
        )
        self.assertEqual(caller._sc_data_company_ids(), [])

    def test_out_of_band_grant_is_visible_without_a_cache_signal(self):
        registration = self._space('test', 'uncached-membership-grant', 'Uncached membership C')
        company = registration.company_id
        group = self.env.ref('smart_core.group_smart_core_non_customer_data_user')
        operator = self._operator('uncached_membership_granted', company, ['base.group_user'])
        caller = self._caller(operator, company)
        self.assertEqual(caller._sc_data_company_ids(), [])

        self.env.cr.execute(
            'INSERT INTO res_groups_users_rel (gid, uid) VALUES (%s, %s)',
            (group.id, operator.id),
        )
        self.assertEqual(caller._sc_data_company_ids(), [company.id])

    def test_platform_admin_identity_is_read_as_a_fact_too(self):
        registration = self._space('test', 'uncached-membership-admin', 'Uncached membership D')
        company = registration.company_id
        admin_group = self.env.ref('smart_core.group_smart_core_admin')
        operator = self._operator('uncached_membership_admin', company, ['base.group_user'])
        caller = self._caller(operator, company)
        self.assertEqual(caller._sc_data_company_ids(), [])

        self.env.cr.execute(
            'INSERT INTO res_groups_users_rel (gid, uid) VALUES (%s, %s)',
            (admin_group.id, operator.id),
        )
        self.assertEqual(caller._sc_data_company_ids(), [company.id])
