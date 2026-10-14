"""Real-principal delivery of sc.dictionary startup scope, not source text.

The startup contract is built per principal, so a company-level dictionary row
is delivered only to a principal whose data-space authority includes that
company. These cases exercise the one scope vocabulary through the startup
helper with real users and real registrations; no source token is treated as
proof of behaviour.
"""
import os
from unittest.mock import patch

from odoo import Command, SUPERUSER_ID
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.smart_core.core.system_init_dictionary_data_helper import (
    apply_dictionary_startup_data,
)


@tagged('post_install', '-at_install', 'dictionary_scope_delivery')
class TestDictionaryScopeDelivery(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.maintenance_secret = 'd' * 64
        maintenance = patch.dict(
            os.environ, {'SC_TENANT_PAYLOAD_MAINTENANCE_CAPABILITY': cls.maintenance_secret}
        )
        maintenance.start()
        cls.addClassCleanup(maintenance.stop)
        cls.Registration = cls.env['sc.tenant.company.registration'].with_user(
            SUPERUSER_ID
        ).with_context(
            sc_tenant_payload_import=True,
            sc_tenant_payload_maintenance_capability=cls.maintenance_secret,
        )
        cls.demo = cls.Registration._create_non_customer_space(
            tenant_key='dict-scope-demo', purpose='demo', company_name='Dict scope demo'
        )
        cls.customer_company = cls.env['res.company'].create({'name': 'Dict scope customer'})
        cls.customer_registration = cls.Registration.with_context(
            sc_tenant_payload_import=True
        ).create({
            'tenant_key': 'dict-scope-customer',
            'company_id': cls.customer_company.id,
            'source_module': 'dictionary_scope_unit',
            'source_external_key': 'unit-customer',
        })
        cls.unregistered_company = cls.env['res.company'].create({'name': 'Dict scope unregistered'})

        Dictionary = cls.env['sc.dictionary'].sudo()
        cls.rows = {
            'global': Dictionary.create({
                'name': 'Global entry', 'code': 'dsl.global.entry', 'type': 'role_entry',
                'scope_type': 'global', 'value_json': {'entry_type': 'menu'}, 'sequence': 10,
            }),
            'role': Dictionary.create({
                'name': 'Role entry', 'code': 'dsl.role.entry', 'type': 'role_entry',
                'scope_type': 'role', 'scope_ref': 'pm',
                'value_json': {'entry_type': 'menu'}, 'sequence': 20,
            }),
            'customer': Dictionary.create({
                'name': 'Customer company entry', 'code': 'dsl.customer.entry',
                'type': 'role_entry', 'scope_type': 'company',
                'scope_ref': str(cls.customer_company.id),
                'value_json': {'entry_type': 'menu'}, 'sequence': 30,
            }),
            'demo': Dictionary.create({
                'name': 'Demo company entry', 'code': 'dsl.demo.entry', 'type': 'role_entry',
                'scope_type': 'company', 'scope_ref': str(cls.demo.company_id.id),
                'value_json': {'entry_type': 'menu'}, 'sequence': 40,
            }),
            'unregistered': Dictionary.create({
                'name': 'Unregistered company entry', 'code': 'dsl.unregistered.entry',
                'type': 'role_entry', 'scope_type': 'company',
                'scope_ref': str(cls.unregistered_company.id),
                'value_json': {'entry_type': 'menu'}, 'sequence': 50,
            }),
            'global_block': Dictionary.create({
                'name': 'Global block', 'code': 'dsl.global.block', 'type': 'home_block',
                'scope_type': 'global', 'value_json': {'is_enabled': True}, 'sequence': 10,
            }),
            'customer_block': Dictionary.create({
                'name': 'Customer block', 'code': 'dsl.customer.block', 'type': 'home_block',
                'scope_type': 'company', 'scope_ref': str(cls.customer_company.id),
                'value_json': {'is_enabled': True}, 'sequence': 20,
            }),
            'blank_ref_block': Dictionary.create({
                'name': 'Blank reference block', 'code': 'dsl.blank.block', 'type': 'home_block',
                'scope_type': 'company', 'scope_ref': False,
                'value_json': {'is_enabled': True}, 'sequence': 30,
            }),
        }

        cls.orphan_user = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Dict scope orphan user', 'login': 'dict-scope-orphan-user',
            'company_id': cls.unregistered_company.id,
            'company_ids': [Command.set([cls.unregistered_company.id])],
            'groups_id': [Command.set([cls.env.ref('base.group_user').id])],
        })
        cls.customer_user = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Dict scope customer user', 'login': 'dict-scope-customer-user',
            'company_id': cls.customer_company.id,
            'company_ids': [Command.set([cls.customer_company.id])],
            'groups_id': [Command.set([cls.env.ref('base.group_user').id])],
        })
        cls.non_customer_user = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Dict scope non customer user', 'login': 'dict-scope-non-customer-user',
            'company_id': cls.demo.company_id.id,
            'company_ids': [Command.set([cls.demo.company_id.id])],
            'groups_id': [Command.set([
                cls.env.ref('base.group_user').id,
                cls.env.ref('smart_core.group_smart_core_non_customer_data_user').id,
            ])],
        })

    def principal_env(self, user):
        context = dict(self.env.context, allowed_company_ids=user.company_ids.ids)
        return self.env(user=user, context=context)

    def delivered_role_entries(self, data):
        return {
            group.get('role_code'): sorted(
                entry.get('entry_key') for entry in group.get('entries') or []
            )
            for group in data.get('role_entries') or []
        }

    def delivered_home_blocks(self, data):
        return {
            group.get('role_code'): sorted(group.get('blocks') or [])
            for group in data.get('home_blocks') or []
        }

    def meta(self, data):
        return data.get('dictionary_data_meta') or {}

    def insert_legacy_scope_row(self):
        """A scope value the selection no longer offers, as legacy rows carry it."""
        self.env.cr.execute(
            """
            INSERT INTO sc_dictionary
                (name, code, type, scope_type, scope_ref, value_json, sequence, active)
            VALUES
                ('Legacy scope entry', 'dsl.legacy.entry', 'role_entry', 'tenant', 'acme',
                 '{}'::jsonb, 70, true)
            """
        )

    def startup_data(self, user):
        return apply_dictionary_startup_data(self.principal_env(user), {})

    def test_customer_principal_receives_only_its_own_company_scope(self):
        data = self.startup_data(self.customer_user)
        entries = self.delivered_role_entries(data)
        self.assertEqual(
            entries.get('__global__'), ['dsl.customer.entry', 'dsl.global.entry'])
        self.assertEqual(entries.get('pm'), ['dsl.role.entry'])
        shipped = [key for keys in entries.values() for key in keys]
        self.assertNotIn('dsl.demo.entry', shipped)
        self.assertNotIn('dsl.unregistered.entry', shipped)
        self.assertEqual(
            self.delivered_home_blocks(data).get('__global__'),
            ['dsl.customer.block', 'dsl.global.block'],
        )
        meta = self.meta(data)
        self.assertEqual(
            meta.get('withheld_scope_counts'),
            {'company:missing_reference': 1, 'company:unauthorized_company': 2},
        )
        self.assertEqual(meta.get('undelivered_scope_counts'), {})
        self.assertEqual(
            meta.get('company_scope_authority'),
            {'source': 'res_users_sc_data_company_ids', 'authorized_company_count': 1},
        )
        self.assertEqual(meta.get('delivered_scopes'), ['global', 'company', 'role'])

    def test_non_customer_principal_receives_only_the_demo_space(self):
        data = self.startup_data(self.non_customer_user)
        entries = self.delivered_role_entries(data)
        self.assertEqual(entries.get('__global__'), ['dsl.demo.entry', 'dsl.global.entry'])
        shipped = [key for keys in entries.values() for key in keys]
        self.assertNotIn('dsl.customer.entry', shipped)
        self.assertEqual(
            self.delivered_home_blocks(data).get('__global__'), ['dsl.global.block'])
        self.assertEqual(
            self.meta(data).get('withheld_scope_counts'),
            {'company:missing_reference': 1, 'company:unauthorized_company': 3},
        )

    def test_company_delivery_follows_the_registration_not_the_scope_name(self):
        self.customer_registration.with_context(sc_tenant_payload_import=True).write(
            {'active': False})
        data = self.startup_data(self.customer_user)
        entries = self.delivered_role_entries(data)
        self.assertEqual(entries.get('__global__'), ['dsl.global.entry'])
        self.assertEqual(
            self.meta(data).get('withheld_scope_counts'),
            {'company:missing_reference': 1, 'company:unauthorized_company': 4},
        )
        self.assertEqual(
            self.meta(data).get('company_scope_authority').get('authorized_company_count'), 0)

    def test_a_legacy_scope_without_a_delivery_meaning_is_counted_not_published(self):
        self.insert_legacy_scope_row()
        data = self.startup_data(self.customer_user)
        entries = self.delivered_role_entries(data)
        self.assertEqual(
            entries.get('__global__'), ['dsl.customer.entry', 'dsl.global.entry'])
        shipped = [key for keys in entries.values() for key in keys]
        self.assertNotIn('dsl.legacy.entry', shipped)
        self.assertEqual(self.meta(data).get('undelivered_scope_counts'), {'tenant': 1})

    def test_a_principal_with_no_registered_company_gets_no_company_row(self):
        data = self.startup_data(self.orphan_user)
        entries = self.delivered_role_entries(data)
        self.assertEqual(entries.get('__global__'), ['dsl.global.entry'])
        self.assertEqual(self.delivered_home_blocks(data).get('__global__'), ['dsl.global.block'])
        self.assertEqual(
            self.meta(data).get('withheld_scope_counts'),
            {'company:missing_reference': 1, 'company:unauthorized_company': 4},
        )
        self.assertEqual(
            self.meta(data).get('company_scope_authority'),
            {'source': 'res_users_sc_data_company_ids', 'authorized_company_count': 0},
        )
