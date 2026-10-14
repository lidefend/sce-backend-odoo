"""Onboarding owns the operator identity realm, not only the registration row.

A data space whose operators were never enrolled is readable by nobody: the
identity realm is an explicit grant, never inferred from company membership.
These cases drive the real authority and the real ORM.
"""
import os
from unittest.mock import patch

from odoo import Command, SUPERUSER_ID
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.smart_core.security import data_space_provisioning as provisioning


@tagged('post_install', '-at_install', 'data_space_identity_enrollment')
class TestDataSpaceIdentityEnrollment(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.maintenance_secret = 'e' * 64
        maintenance = patch.dict(
            os.environ, {'SC_TENANT_PAYLOAD_MAINTENANCE_CAPABILITY': cls.maintenance_secret})
        maintenance.start()
        cls.addClassCleanup(maintenance.stop)
        cls.Registration = cls.env['sc.tenant.company.registration'].with_user(SUPERUSER_ID)

    def _operator(self, login, company, *, portal=False):
        # A portal identity is one that carries the portal audience group; the
        # stored ``share`` flag is derived from it, never asserted by hand.
        audience = 'base.group_portal' if portal else 'base.group_user'
        return self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Identity enrollment %s' % login,
            'login': login,
            'company_id': company.id,
            'company_ids': [Command.set([company.id])],
            'groups_id': [Command.set([self.env.ref(audience).id])],
        })

    def _space(self, purpose, tenant_key, name):
        return self.Registration._create_non_customer_space(
            tenant_key=tenant_key, purpose=purpose, company_name=name)

    def test_enrollment_is_part_of_the_onboarding_act_and_idempotent(self):
        registration = self._space('demo', 'identity-enroll-idem', 'Identity enrollment space')
        operator = self._operator('identity_enroll_idem_operator', registration.company_id)

        receipt = provisioning.enroll_data_space_identities(self.env, purpose='demo')
        self.assertIn(operator.login, receipt['enrolled'])
        self.assertIn(registration.company_id.id, receipt['companies'])

        again = provisioning.enroll_data_space_identities(self.env, purpose='demo')
        self.assertNotIn(operator.login, again['enrolled'])
        self.assertIn(operator.login, again['already_effective'])

    def test_enrolled_operator_reads_the_space_and_non_enrolled_operator_does_not(self):
        registration = self._space('demo', 'identity-enroll-scope', 'Identity enrollment scope')
        company = registration.company_id
        enrolled = self._operator('identity_enroll_in_scope', company)
        provisioning.enroll_data_space_identities(self.env, purpose='demo')

        caller = enrolled.with_user(enrolled).with_context(allowed_company_ids=[company.id])
        self.assertEqual(caller._sc_data_company_ids(), [company.id])

        pending = self._operator('identity_enroll_out_of_scope', company)
        pending_caller = pending.with_user(pending).with_context(
            allowed_company_ids=[company.id])
        self.assertEqual(pending_caller._sc_data_company_ids(), [])

    def test_readiness_fails_closed_until_every_operator_is_enrolled(self):
        registration = self._space('demo', 'identity-enroll-ready', 'Identity enrollment ready')
        provisioning.enroll_data_space_identities(self.env, purpose='demo')
        self.assertTrue(provisioning.assert_data_space_identities_enrolled(
            self.env, purpose='demo'))

        pending = self._operator('identity_enroll_pending', registration.company_id)
        with self.assertRaises(ValueError) as ctx:
            provisioning.assert_data_space_identities_enrolled(self.env, purpose='demo')
        self.assertIn('DATA_SPACE_IDENTITY_ENROLLMENT_INCOMPLETE', str(ctx.exception))
        self.assertIn(pending.login, str(ctx.exception))

        provisioning.enroll_data_space_identities(self.env, purpose='demo')
        self.assertTrue(provisioning.assert_data_space_identities_enrolled(
            self.env, purpose='demo'))

    def test_a_plain_customer_identity_is_never_enrolled(self):
        registration = self._space('demo', 'identity-enroll-customer', 'Identity enrollment cust')
        other = self.env['res.company'].create({'name': 'Identity enrollment outsider'})
        outsider = self._operator('identity_enroll_outsider', other)
        provisioning.enroll_data_space_identities(self.env, purpose='demo')

        group = self.env.ref('smart_core.group_smart_core_non_customer_data_user')
        self.assertNotIn(group, outsider.groups_id)
        self.assertEqual(
            outsider.with_user(outsider).with_context(
                allowed_company_ids=[other.id])._sc_data_company_ids(),
            [],
        )
        self.assertEqual(registration.company_id.id, registration.company_id.id)

    def test_portal_identities_are_never_data_space_operators(self):
        registration = self._space('demo', 'identity-enroll-portal', 'Identity enrollment portal')
        self.assertFalse(registration.company_id.is_platform_bootstrap_company)
        portal = self._operator('identity_enroll_portal', registration.company_id, portal=True)
        receipt = provisioning.enroll_data_space_identities(self.env, purpose='demo')
        self.assertNotIn(portal.login, receipt['enrolled'])
        self.assertNotIn(portal.login, receipt['already_effective'])

    def test_a_customer_space_can_never_be_relabelled_as_non_customer(self):
        company = self.env['res.company'].create({'name': 'Identity enrollment customer space'})
        customer = self.Registration.with_context(
            sc_tenant_payload_import=True,
            sc_tenant_payload_maintenance_capability=self.maintenance_secret,
        ).create({
            'tenant_key': 'identity-enroll-customer-space',
            'company_id': company.id,
            'source_module': 'customer_space_unit',
            'source_external_key': 'identity-enroll-customer-space',
        })
        with self.assertRaises(ValueError):
            provisioning.enroll_data_space_identities(self.env, purpose='customer')
        self.assertEqual(customer.data_purpose, 'customer')

    def test_a_product_admin_even_with_sudo_cannot_enroll_identities(self):
        registration = self._space('demo', 'identity-enroll-admin', 'Identity enrollment admin')
        admin = self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Identity enrollment product admin',
            'login': 'identity_enroll_product_admin',
            'company_id': registration.company_id.id,
            'company_ids': [Command.set([registration.company_id.id])],
            'groups_id': [Command.set([
                self.env.ref('base.group_user').id,
                self.env.ref('smart_core.group_smart_core_admin').id,
            ])],
        })
        registrations = self.env['sc.tenant.company.registration'].sudo().search(
            [('company_id', '=', registration.company_id.id)])
        for su in (False, True):
            with self.subTest(su=su), self.assertRaises(AccessError):
                registrations.with_user(admin).sudo(su)._enroll_data_space_operators(registrations)
        group = self.env.ref('smart_core.group_smart_core_non_customer_data_user')
        self.assertNotIn(group, admin.groups_id)
