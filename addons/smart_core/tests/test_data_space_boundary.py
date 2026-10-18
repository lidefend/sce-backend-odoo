"""Persisted registration boundary; not yet whole-product data-rule acceptance."""
import os
from unittest.mock import patch
from odoo import Command, SUPERUSER_ID
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'data_space_boundary')
class TestDataSpaceBoundary(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.maintenance_secret = 'd' * 64  # exact native maintenance-capability format
        maintenance = patch.dict(os.environ, {'SC_TENANT_PAYLOAD_MAINTENANCE_CAPABILITY': cls.maintenance_secret})
        maintenance.start()
        cls.addClassCleanup(maintenance.stop)
        cls.Registration = cls.env['sc.tenant.company.registration'].with_user(SUPERUSER_ID).with_context(
            sc_tenant_payload_import=True,
            sc_tenant_payload_maintenance_capability=cls.maintenance_secret,
        )
        cls.demo = cls.Registration._create_non_customer_space(
            tenant_key='data-space-unit-demo', purpose='demo', company_name='Data space unit demo')
        cls.test_space = cls.Registration._create_non_customer_space(
            tenant_key='data-space-unit-test', purpose='test', company_name='Data space unit test')
        cls.customer_company = cls.env['res.company'].create({'name': 'Data space unit customer'})
        cls.customer = cls.Registration.with_context(sc_tenant_payload_import=True).create({
            'tenant_key': 'data-space-unit-customer', 'company_id': cls.customer_company.id,
            'source_module': 'customer_space_unit', 'source_external_key': 'unit-customer',
        })
        cls.unknown = cls.env['res.company'].create({'name': 'Data space unit unknown'})
        cls.admin = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Data space unit platform administrator', 'login': 'data-space-unit-admin',
            'company_id': cls.demo.company_id.id,
            'company_ids': [Command.set((cls.demo.company_id | cls.test_space.company_id | cls.customer_company | cls.unknown).ids)],
            'groups_id': [Command.set([cls.env.ref('base.group_user').id, cls.env.ref('smart_core.group_smart_core_admin').id])],
        })

    def caller(self, **context):
        return self.admin.with_user(self.admin).with_context(
            allowed_company_ids=self.admin.company_ids.ids, **context)

    def clear_active_registrations(self):
        """Make onboarding tests independent of any ambient environment onboarding."""
        self.Registration.with_context(active_test=False).search(
            [('active', '=', True)]).write({'active': False})

    def test_customer_default_is_preserved(self):
        self.assertEqual(self.customer.data_purpose, 'customer')

    def test_scope_excludes_customer_unknown_and_inactive(self):
        caller = self.caller()
        self.assertEqual(set(caller._sc_data_company_ids()), {self.demo.company_id.id, self.test_space.company_id.id})
        self.test_space.with_context(sc_tenant_payload_import=True).write({'active': False})
        self.assertEqual(caller._sc_data_company_ids(), [self.demo.company_id.id])

    def test_sudo_caller_cannot_expand_company_scope(self):
        foreign = self.Registration._create_non_customer_space(
            tenant_key='data-space-unit-foreign', purpose='demo', company_name='Foreign demo')
        caller = self.admin.with_user(self.admin).sudo().with_context(allowed_company_ids=[foreign.company_id.id])
        with self.assertRaises(AccessError):
            caller._sc_data_company_ids()

    def test_resolver_cannot_impersonate_another_user(self):
        with self.assertRaises(AccessError):
            self.admin.with_user(SUPERUSER_ID)._sc_data_company_ids()

    def test_product_admin_even_with_sudo_cannot_create_a_space(self):
        for su in (False, True):
            with self.subTest(su=su), self.assertRaises(AccessError):
                self.Registration.with_user(self.admin).sudo(su)._create_non_customer_space(
                    tenant_key='forged', purpose='demo', company_name='Forged space')

    def test_customer_import_cannot_select_demo(self):
        with self.assertRaises(ValidationError):
            self.Registration.with_context(sc_tenant_payload_import=True).create({
                'tenant_key': 'forged-customer', 'data_purpose': 'demo',
                'company_id': self.unknown.id, 'source_module': 'customer_space_unit',
                'source_external_key': 'forged',
            })

    def test_rpc_default_cannot_change_customer_purpose(self):
        registration = self.Registration.with_context(
            sc_tenant_payload_import=True, default_data_purpose='demo').create({
                'tenant_key': 'data-space-unit-context', 'company_id': self.unknown.id,
                'source_module': 'customer_space_unit', 'source_external_key': 'context',
            })
        self.assertEqual(registration.data_purpose, 'customer')

    def test_purpose_and_identity_are_immutable_even_for_maintenance(self):
        for values in ({'data_purpose': 'demo'}, {'company_id': self.demo.company_id.id}, {'tenant_key': 'new-tenant'}):
            with self.subTest(values=values), self.assertRaises(UserError):
                self.customer.with_context(sc_tenant_payload_import=True).write(values)

    def test_conflicting_tenant_purpose_rolls_back_new_company(self):
        before = self.env['res.company'].search_count([])
        with self.assertRaisesRegex(ValidationError, 'DATA_SPACE_TENANT_PURPOSE_CONFLICT'):
            self.Registration._create_non_customer_space(
                tenant_key=self.customer.tenant_key, purpose='demo', company_name='Rejected relabel')
        self.assertEqual(self.env['res.company'].search_count([]), before)

    def test_non_customer_entry_cannot_create_customer_space(self):
        with self.assertRaises(ValidationError):
            self.Registration._create_non_customer_space(
                tenant_key='new-customer', purpose='customer', company_name='Rejected customer')

    def test_existing_company_can_be_registered_without_relabel(self):
        company = self.env['res.company'].create({'name': 'Data space unit adoptable'})
        registration = self.Registration._register_non_customer_space(
            tenant_key='data-space-unit-adopt', purpose='demo', company_id=company.id)
        self.assertEqual(registration.company_id, company)
        self.assertEqual(registration.data_purpose, 'demo')
        self.assertEqual(company.name, 'Data space unit adoptable')
        self.assertFalse(company.is_platform_bootstrap_company)

    def test_adopted_company_joins_the_non_customer_realm(self):
        company = self.env['res.company'].create({'name': 'Data space unit adoptable realm'})
        self.Registration._register_non_customer_space(
            tenant_key='data-space-unit-adopt-realm', purpose='demo', company_id=company.id)
        self.admin.write({'company_ids': [Command.link(company.id)]})
        self.assertIn(company.id, self.caller()._sc_data_company_ids())

    def test_bootstrap_company_cannot_be_registered(self):
        carrier = self.env['res.company'].create({
            'name': 'Data space unit carrier', 'is_platform_bootstrap_company': True})
        with self.assertRaisesRegex(ValidationError, 'DATA_SPACE_BUSINESS_COMPANY_REQUIRED'):
            self.Registration._register_non_customer_space(
                tenant_key='data-space-unit-carrier', purpose='demo', company_id=carrier.id)

    def test_environment_main_company_onboarding_retires_the_carrier_marker(self):
        self.clear_active_registrations()
        carrier = self.env['res.company'].create({
            'name': 'Data space unit main carrier',
            'is_platform_bootstrap_company': True})
        Registration = self.Registration.with_context(allowed_company_ids=[carrier.id])
        registration = Registration._adopt_environment_main_company(
            tenant_key='data-space-unit-main', purpose='demo',
            company_id=carrier.id, environment_role='platform_internal_demo')
        self.assertEqual(registration.company_id, carrier)
        self.assertEqual(registration.data_purpose, 'demo')
        self.assertFalse(carrier.is_platform_bootstrap_company)

    def test_customer_role_cannot_onboard_its_main_company(self):
        carrier = self.env['res.company'].create({
            'name': 'Data space unit customer main carrier',
            'is_platform_bootstrap_company': True})
        Registration = self.Registration.with_context(allowed_company_ids=[carrier.id])
        with self.assertRaisesRegex(ValidationError, 'MAIN_COMPANY_IS_A_CARRIER'):
            Registration._adopt_environment_main_company(
                tenant_key='data-space-unit-main-customer', purpose='demo',
                company_id=carrier.id, environment_role='customer_production')
        self.assertTrue(carrier.is_platform_bootstrap_company)

    def test_non_main_company_cannot_be_onboarded_as_the_environment_space(self):
        other = self.env['res.company'].create({
            'name': 'Data space unit not main', 'is_platform_bootstrap_company': True})
        with self.assertRaisesRegex(ValidationError, 'ENVIRONMENT_MAIN_COMPANY_REQUIRED'):
            self.Registration._adopt_environment_main_company(
                tenant_key='data-space-unit-not-main', purpose='demo',
                company_id=other.id, environment_role='platform_internal_demo')

    def test_database_that_already_owns_a_registration_refuses_a_second_space(self):
        self.clear_active_registrations()
        owner = self.env['res.company'].create({'name': 'Data space unit first owner'})
        self.Registration._register_non_customer_space(
            tenant_key='data-space-unit-first', purpose='demo', company_id=owner.id)
        carrier = self.env['res.company'].create({
            'name': 'Data space unit second carrier',
            'is_platform_bootstrap_company': True})
        Registration = self.Registration.with_context(allowed_company_ids=[carrier.id])
        with self.assertRaisesRegex(ValidationError, 'ALREADY_OWNS_A_REGISTRATION'):
            Registration._adopt_environment_main_company(
                tenant_key='data-space-unit-second', purpose='demo',
                company_id=carrier.id, environment_role='platform_internal_demo')

    def test_environment_onboarding_adopts_an_existing_main_company(self):
        """A database that already owns a registration adopts its main company.

        The environment main company cannot be "the first onboarded business
        company" once an acceptance fixture space exists, so the entry that
        retires a carrier marker would refuse a database nobody can fix. The
        existing-company entry adopts it instead and never relabels it.
        """
        from odoo.addons.smart_core.security import data_space_provisioning as provisioning
        provisioning.declare_environment_role(self.env, 'platform_internal_demo')
        company = self.env['res.company'].create({'name': 'Data space unit environment main'})
        env = self.env(user=self.env.user, context={'allowed_company_ids': [company.id]})
        registration = provisioning.onboard_environment_business_company(
            env, tenant_key='data-space-unit-environment-main')
        self.assertEqual(registration.data_purpose, 'demo')
        self.assertEqual(registration.company_id, company)
        self.assertFalse(company.is_platform_bootstrap_company)
        self.assertEqual(company.name, 'Data space unit environment main')

    def test_environment_onboarding_replays_the_same_space_idempotently(self):
        from odoo.addons.smart_core.security import data_space_provisioning as provisioning
        provisioning.declare_environment_role(self.env, 'platform_internal_demo')
        company = self.env['res.company'].create({'name': 'Data space unit replay main'})
        env = self.env(user=self.env.user, context={'allowed_company_ids': [company.id]})
        first = provisioning.onboard_environment_business_company(
            env, tenant_key='data-space-unit-replay')
        second = provisioning.onboard_environment_business_company(
            env, tenant_key='data-space-unit-replay')
        self.assertEqual(first, second)
        self.assertEqual(self.Registration.with_context(active_test=False).search_count([
            ('company_id', '=', company.id)]), 1)

    def test_environment_onboarding_refuses_a_different_space_for_the_same_company(self):
        from odoo.addons.smart_core.security import data_space_provisioning as provisioning
        provisioning.declare_environment_role(self.env, 'platform_internal_demo')
        company = self.env['res.company'].create({'name': 'Data space unit relabel main'})
        env = self.env(user=self.env.user, context={'allowed_company_ids': [company.id]})
        provisioning.onboard_environment_business_company(
            env, tenant_key='data-space-unit-relabel')
        with self.assertRaisesRegex(ValueError, 'DATA_SPACE_COMPANY_ALREADY_REGISTERED'):
            provisioning.onboard_environment_business_company(
                env, tenant_key='data-space-unit-relabel-other')

    def test_environment_onboarding_refuses_a_carrier_main_company(self):
        from odoo.addons.smart_core.security import data_space_provisioning as provisioning
        provisioning.declare_environment_role(self.env, 'platform_internal_demo')
        carrier = self.env['res.company'].create({
            'name': 'Data space unit environment carrier',
            'is_platform_bootstrap_company': True,
        })
        env = self.env(user=self.env.user, context={'allowed_company_ids': [carrier.id]})
        with self.assertRaisesRegex(ValueError, 'IS_STILL_A_CARRIER'):
            provisioning.onboard_environment_business_company(
                env, tenant_key='data-space-unit-environment-carrier')
        self.assertTrue(carrier.is_platform_bootstrap_company)

    def test_environment_onboarding_never_onboards_a_customer_database(self):
        from odoo.addons.smart_core.security import data_space_provisioning as provisioning
        provisioning.declare_environment_role(self.env, 'customer_production')
        with self.assertRaisesRegex(ValueError, 'SIGNED_IMPORT'):
            provisioning.onboard_environment_business_company(
                self.env, tenant_key='data-space-unit-environment-customer')

    def test_already_registered_company_is_refused(self):
        with self.assertRaisesRegex(ValidationError, 'DATA_SPACE_COMPANY_ALREADY_REGISTERED'):
            self.Registration._register_non_customer_space(
                tenant_key='data-space-unit-adopt-again', purpose='demo',
                company_id=self.demo.company_id.id)

    def test_customer_purpose_cannot_be_registered_by_the_maintenance_entry(self):
        company = self.env['res.company'].create({'name': 'Data space unit adoptable customer'})
        for purpose in ('customer', '', None, 'unknown'):
            with self.subTest(purpose=purpose), self.assertRaisesRegex(
                    ValidationError, 'DATA_SPACE_NON_CUSTOMER_PURPOSE_REQUIRED'):
                self.Registration._register_non_customer_space(
                    tenant_key='data-space-unit-adopt-customer', purpose=purpose,
                    company_id=company.id)

    def test_product_admin_cannot_register_an_existing_company(self):
        company = self.env['res.company'].create({'name': 'Data space unit adoptable admin'})
        for su in (False, True):
            with self.subTest(su=su), self.assertRaises(AccessError):
                self.Registration.with_user(self.admin).sudo(su)._register_non_customer_space(
                    tenant_key='forged-adopt', purpose='demo', company_id=company.id)

    def test_customer_identity_excludes_demo_and_test(self):
        self.admin.write({'groups_id': [Command.set([self.env.ref('base.group_user').id])]})
        self.assertEqual(self.caller()._sc_data_company_ids(), [self.customer_company.id])

    def test_explicit_test_identity_excludes_customer(self):
        self.admin.write({'groups_id': [Command.set([
            self.env.ref('base.group_user').id,
            self.env.ref('smart_core.group_smart_core_non_customer_data_user').id,
        ])]})
        self.assertEqual(set(self.caller()._sc_data_company_ids()), {self.demo.company_id.id, self.test_space.company_id.id})

    def test_product_admin_cannot_delete_registration_with_forged_context(self):
        with self.assertRaises(AccessError):
            self.customer.with_user(self.admin).sudo().with_context(
                allow_audited_tenant_destroy=True, sc_tenant_payload_import=True).unlink()

    def test_public_registration_and_copy_reject_forged_admin_context(self):
        context = dict(sc_tenant_payload_import=True, sc_tenant_payload_maintenance_capability='forged')
        with self.assertRaises(AccessError):
            self.Registration.with_user(self.admin).sudo().with_context(**context).create({
                'tenant_key': 'forged-registration', 'company_id': self.unknown.id,
                'source_module': 'customer_forgery', 'source_external_key': 'forged',
            })
        with self.assertRaises(AccessError):
            self.customer.with_user(self.admin).sudo().with_context(**context).copy({'company_id': self.unknown.id})

    def test_same_tenant_same_purpose_supports_multiple_companies(self):
        second = self.Registration._create_non_customer_space(
            tenant_key=self.demo.tenant_key, purpose='demo', company_name='Second demo company')
        self.assertNotEqual(second.company_id, self.demo.company_id)
        self.assertEqual(second.data_purpose, self.demo.data_purpose)

    def test_inactive_registration_still_prevents_purpose_change(self):
        self.demo.with_context(sc_tenant_payload_import=True).write({'active': False})
        with self.assertRaises(ValidationError):
            self.Registration._create_non_customer_space(
                tenant_key=self.demo.tenant_key, purpose='test', company_name='Rejected inactive reuse')

    def test_current_company_scope_is_an_intersection(self):
        caller = self.admin.with_user(self.admin).with_context(allowed_company_ids=[self.test_space.company_id.id])
        self.assertEqual(caller._sc_data_company_ids(), [self.test_space.company_id.id])

    def test_serialization_rejects_stale_concurrent_snapshot(self):
        # Dedicated real cursors, not the TransactionCase savepoint cursor.
        # Only a namespaced technical synchronization row is committed; no
        # business/company/user fixtures escape the surrounding test rollback.
        import uuid
        import threading
        from concurrent.futures import ThreadPoolExecutor
        from odoo import api, sql_db
        from psycopg2.errors import SerializationFailure

        key = 'data-space-concurrency-test-' + uuid.uuid4().hex
        db = sql_db.db_connect(self.env.cr.dbname)
        ready = threading.Event()
        start = threading.Event()
        writing = threading.Event()

        def competing_write():
            with db.cursor() as cr:
                cr.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
                cr.execute('SELECT count(*) FROM sc_data_space_serialization WHERE tenant_key = %s', [key])
                ready.set()
                if not start.wait(10):
                    raise AssertionError('concurrent test start timed out')
                writing.set()
                try:
                    api.Environment(cr, SUPERUSER_ID, {})['sc.tenant.company.registration']._serialize_tenant_keys([key])
                    cr.commit()
                    return 'unexpected-success'
                except SerializationFailure:
                    cr.rollback()
                    return 'serialization-failure'

        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(competing_write)
                try:
                    self.assertTrue(ready.wait(10))
                    with db.cursor() as cr:
                        cr.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
                        api.Environment(cr, SUPERUSER_ID, {})['sc.tenant.company.registration']._serialize_tenant_keys([key])
                        start.set()
                        self.assertTrue(writing.wait(10))
                        cr.commit()
                    self.assertEqual(future.result(timeout=15), 'serialization-failure')
                finally:
                    start.set()
        finally:
            with db.cursor() as cr:
                cr.execute('DELETE FROM sc_data_space_serialization WHERE tenant_key = %s', [key])
                cr.commit()

    def test_unlink_requires_real_signature_at_the_entrypoint(self):
        with patch.object(type(self.env.registry), 'in_test_mode', return_value=False):
            for token in ('', 'wrong'):
                with self.subTest(token_present=bool(token)), self.assertRaises(AccessError):
                    self.customer.with_context(
                        allow_audited_tenant_destroy=True, sc_tenant_payload_import=True,
                        sc_tenant_payload_maintenance_capability=token).unlink()
            self.assertTrue(self.customer.exists())
            self.customer.with_context(
                allow_audited_tenant_destroy=True, sc_tenant_payload_import=True,
                sc_tenant_payload_maintenance_capability=self.maintenance_secret).unlink()
            self.assertFalse(self.customer.exists())

    def test_new_space_defaults_do_not_repair_another_company(self):
        if 'construction.contract' not in self.env:
            self.skipTest('industry tax defaults require the construction product')
        Tax = self.env['account.tax'].sudo().with_context(active_test=False)
        tax = Tax.search([('company_id', '=', self.customer_company.id), ('type_tax_use', '=', 'none')], limit=1)
        self.assertTrue(tax, 'registered customer must have its native product tax defaults')
        domain = [('company_id', '=', self.customer_company.id), ('amount', '=', tax.amount),
                  ('amount_type', '=', tax.amount_type), ('type_tax_use', '=', tax.type_tax_use)]
        tax.unlink()
        before = Tax.search_count(domain)
        self.Registration._create_non_customer_space(
            tenant_key='data-space-unit-tax-isolation', purpose='test', company_name='Tax isolation test')
        self.assertEqual(Tax.search_count(domain), before, 'new demo/test registration must not write customer defaults')

    def _native_purpose_company_rule(self):
        """Temporary native rule: mechanism proof, not a production company rule.

        Keep the selected company intersection explicit: Odoo evaluates the
        `user` variable with an empty context in its native rule evaluator.
        """
        return self.env['ir.rule'].create({
            'name': 'Synthetic native data-purpose ceiling',
            'model_id': self.env['ir.model']._get_id('res.company'),
            'domain_force': "[('id', 'in', company_ids), ('id', 'in', user._sc_data_company_ids())]",
        })

    def _companies_for(self, actor=None, company_ids=None):
        actor = actor if actor is not None else self.admin
        return self.env['res.company'].with_user(actor).with_context(
            allowed_company_ids=company_ids if company_ids is not None else actor.company_ids.ids,
        )

    def test_native_global_rule_restricts_group_allow_all(self):
        self._native_purpose_company_rule()
        self.env['ir.rule'].create({
            'name': 'Synthetic role allow all does not override global ceiling',
            'model_id': self.env['ir.model']._get_id('res.company'),
            'domain_force': "[(1, '=', 1)]",
            'groups': [Command.set(self.env.ref('smart_core.group_smart_core_admin').ids)],
        })
        Companies = self._companies_for()
        self.assertEqual(set(Companies.search([]).ids), {self.demo.company_id.id, self.test_space.company_id.id})
        self.assertEqual(Companies.search_count([]), 2)
        with self.assertRaises(AccessError):
            Companies.browse(self.customer_company.id).read(['name'])

    def test_native_rule_respects_selected_company_subset(self):
        self._native_purpose_company_rule()
        Companies = self._companies_for(company_ids=self.test_space.company_id.ids)
        self.assertEqual(Companies.search([]), self.test_space.company_id.with_env(Companies.env))

    def test_native_rule_customer_cannot_read_non_customer(self):
        actor = self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Synthetic customer data principal', 'login': 'native-rule-customer',
            'company_id': self.customer_company.id,
            'company_ids': [Command.set(self.admin.company_ids.ids)],
            'groups_id': [Command.set(self.env.ref('base.group_user').ids)],
        })
        self._native_purpose_company_rule()
        Companies = self._companies_for(actor)
        self.assertEqual(Companies.search([]).ids, self.customer_company.ids)
        with self.assertRaises(AccessError):
            Companies.browse(self.demo.company_id.id).read(['name'])

    def test_native_cached_rule_revokes_inactive_registration(self):
        self._native_purpose_company_rule()
        Companies = self._companies_for()
        self.assertIn(self.test_space.company_id.id, Companies.search([]).ids)
        self.test_space.write({'active': False})
        self.assertEqual(Companies.search([]).ids, self.demo.company_id.ids)

    def test_native_cached_rule_revokes_deleted_registration(self):
        self._native_purpose_company_rule()
        Companies = self._companies_for()
        removed_company_id = self.test_space.company_id.id
        self.assertIn(removed_company_id, Companies.search([]).ids)
        self.test_space.with_context(allow_audited_tenant_destroy=True).unlink()
        self.assertNotIn(removed_company_id, Companies.search([]).ids)

    def test_native_cached_rule_changes_with_principal_purpose(self):
        actor = self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Synthetic purpose-switch principal', 'login': 'native-rule-purpose-switch',
            'company_id': self.customer_company.id,
            'company_ids': [Command.set(self.admin.company_ids.ids)],
            'groups_id': [Command.set(self.env.ref('base.group_user').ids)],
        })
        self._native_purpose_company_rule()
        Companies = self._companies_for(actor)
        self.assertEqual(Companies.search([]).ids, self.customer_company.ids)
        actor.write({'groups_id': [Command.link(self.env.ref('smart_core.group_smart_core_non_customer_data_user').id)]})
        self.assertEqual(set(Companies.search([]).ids), {self.demo.company_id.id, self.test_space.company_id.id})

    def test_native_rule_revokes_company_membership_and_stale_context(self):
        self._native_purpose_company_rule()
        Companies = self._companies_for()
        removed_company_id = self.test_space.company_id.id
        self.assertIn(removed_company_id, Companies.search([]).ids)
        self.admin.write({'company_ids': [Command.unlink(removed_company_id)]})
        with self.assertRaises(AccessError):
            Companies.search([])  # Previously selected company is no longer authorized.
        current = self._companies_for()
        self.assertEqual(current.search([]).ids, self.demo.company_id.ids)
