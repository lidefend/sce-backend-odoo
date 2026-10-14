"""Managed fixture provenance is created, never inferred from an existing name."""
import os
from unittest.mock import patch

from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged

from ..tools.frontend_productization_fixture import (
    DATA_SPACE_TENANT_KEY, MODULE, _activity_journal, _activity_move,
    _bind_xmlid, _company, _partner, _tax, _user,
)


@tagged('post_install', '-at_install', 'acceptance_fixture_data_space')
class TestAcceptanceFixtureDataSpace(TransactionCase):
    def test_activity_existing_foreign_journal_is_not_migrated(self):
        company = _company(self.env, 'TARGETJOURNAL')
        foreign = self.env['res.company'].create({'name': 'Synthetic historical journal owner'})
        journal = self.env['account.journal'].create({
            'name': 'Synthetic historical journal', 'code': 'FEOLD',
            'type': 'general', 'company_id': foreign.id,
        })
        _bind_xmlid(self.env, 'fe_activity_journal', journal)
        with self.assertRaisesRegex(RuntimeError, 'journal ownership mismatch'):
            _activity_journal(self.env, company)
        self.assertEqual(journal.company_id, foreign)

    def test_activity_existing_foreign_move_is_not_migrated(self):
        company = _company(self.env, 'TARGETMOVE')
        journal = _activity_journal(self.env, company)
        foreign = self.env['res.company'].create({'name': 'Synthetic historical move owner'})
        old_journal = self.env['account.journal'].create({
            'name': 'Synthetic historical move journal', 'code': 'FEOLD',
            'type': 'general', 'company_id': foreign.id,
        })
        move = self.env['account.move'].with_company(foreign).create({
            'journal_id': old_journal.id, 'company_id': foreign.id, 'move_type': 'entry',
        })
        _bind_xmlid(self.env, 'fe_activity_journal_entry', move)
        with self.assertRaisesRegex(RuntimeError, 'move ownership mismatch'):
            _activity_move(self.env, company, _partner(self.env, 'TARGETMOVE', company), journal)
        self.assertEqual(move.company_id, foreign)
        self.assertEqual(move.journal_id, old_journal)

    def test_activity_journal_and_move_stay_in_owned_test_company(self):
        company = _company(self.env, 'JOURNALSPACE')
        journal = _activity_journal(self.env, company)
        self.assertEqual(journal.company_id, company)
        self.assertEqual(journal.type, 'general')
        self.assertEqual(_activity_journal(self.env, company), journal)
        move = _activity_move(self.env, company, _partner(self.env, 'JOURNALSPACE', company), journal)
        self.assertEqual(move.company_id, company)
        self.assertEqual(move.journal_id, journal)
        self.assertEqual(self.env.ref(MODULE + '.fe_activity_journal'), journal)

    def test_activity_journal_rejects_unregistered_company(self):
        company = self.env['res.company'].create({'name': 'Synthetic unregistered journal company'})
        with self.assertRaisesRegex(RuntimeError, 'own registered test company'):
            _activity_journal(self.env, company)
        self.assertFalse(self.env.ref(MODULE + '.fe_activity_journal', raise_if_not_found=False))

    def test_activity_journal_does_not_adopt_same_code(self):
        company = _company(self.env, 'JOURNALCONFLICT')
        journal = self.env['account.journal'].create({
            'name': 'Synthetic operator journal', 'code': 'FEACT',
            'type': 'general', 'company_id': company.id,
        })
        with self.assertRaisesRegex(RuntimeError, 'refuses to adopt unowned'):
            _activity_journal(self.env, company)
        self.assertEqual(journal.name, 'Synthetic operator journal')

    def test_tax_consumes_company_native_reference_without_ownership(self):
        company = _company(self.env, 'NATIVETAX')
        other = _company(self.env, 'OTHERTAX')
        before = self.env['account.tax'].search_count([])
        tax = _tax(self.env, 'NATIVETAX', company)
        tax.write({'sequence': 9876})
        self.assertEqual(_tax(self.env, 'NATIVETAX', company), tax)
        self.assertEqual(tax.sequence, 9876)
        self.assertEqual(tax.company_id, company)
        self.assertNotEqual(_tax(self.env, 'OTHERTAX', other), tax)
        self.assertEqual(self.env['account.tax'].search_count([]), before)
        self.assertFalse(self.env.ref(MODULE + '.fe_tax_nativetax', raise_if_not_found=False))

    def test_tax_missing_native_reference_is_not_synthesized(self):
        company = _company(self.env, 'MISSINGTAX')
        _tax(self.env, 'MISSINGTAX', company).active = False
        before = self.env['account.tax'].with_context(active_test=False).search_count([])
        with self.assertRaisesRegex(RuntimeError, 'one active native company contract tax'):
            _tax(self.env, 'MISSINGTAX', company)
        self.assertEqual(self.env['account.tax'].with_context(active_test=False).search_count([]), before)

    def test_tax_ambiguous_native_reference_is_not_guessed(self):
        company = _company(self.env, 'AMBIGUOUSTAX')
        group = self.env['account.tax.group'].create({
            'name': 'Synthetic non-contract tax group', 'company_id': company.id,
        })
        tax = _tax(self.env, 'AMBIGUOUSTAX', company)
        duplicate = tax.copy({
            'name': 'Synthetic sale tax', 'type_tax_use': 'sale', 'tax_group_id': group.id,
        })
        self.assertNotEqual(duplicate, tax)
        duplicate.write({'type_tax_use': 'none'})
        with self.assertRaisesRegex(RuntimeError, 'one active native company contract tax'):
            _tax(self.env, 'AMBIGUOUSTAX', company)

    def test_new_company_has_native_test_registration(self):
        company = _company(self.env, 'SPACE')
        registration = self.env['sc.tenant.company.registration'].search([('company_id', '=', company.id)])
        self.assertEqual(len(registration), 1)
        self.assertEqual(registration.data_purpose, 'test')
        self.assertEqual(registration.tenant_key, DATA_SPACE_TENANT_KEY)
        self.assertFalse(company.is_platform_bootstrap_company)
        self.assertEqual(company.currency_id, self.env.ref('base.CNY'))

    def test_registered_fixture_is_idempotent(self):
        first = _company(self.env, 'REPEATSPACE')
        before = self.env['sc.tenant.company.registration'].search_count([])
        self.assertEqual(_company(self.env, 'REPEATSPACE'), first)
        self.assertEqual(self.env['sc.tenant.company.registration'].search_count([]), before)

    def test_existing_unregistered_fixture_is_not_relabelled(self):
        company = self.env['res.company'].create({'name': 'FE Company UNSCOPED'})
        _bind_xmlid(self.env, 'fe_company_unscoped', company)
        with self.assertRaisesRegex(RuntimeError, 'active owned test space'):
            _company(self.env, 'UNSCOPED')
        self.assertFalse(self.env['sc.tenant.company.registration'].search([('company_id', '=', company.id)]))

    def test_matching_unowned_name_is_not_adopted(self):
        self.env['res.company'].create({'name': 'FE Company UNOWNEDSPACE'})
        with self.assertRaisesRegex(RuntimeError, 'refuses to adopt'):
            _company(self.env, 'UNOWNEDSPACE')
        self.assertFalse(self.env.ref(MODULE + '.fe_company_unownedspace', raise_if_not_found=False))

    def test_foreign_registered_space_is_not_adopted(self):
        registration = self.env['sc.tenant.company.registration']._create_non_customer_space(
            tenant_key='other-managed-fixture', purpose='test', company_name='FE Company FOREIGN',
        )
        _bind_xmlid(self.env, 'fe_company_foreign', registration.company_id)
        with self.assertRaisesRegex(RuntimeError, 'active owned test space'):
            _company(self.env, 'FOREIGN')
        self.assertEqual(registration.tenant_key, 'other-managed-fixture')

    def test_fixture_actor_has_non_customer_purpose_without_business_grants(self):
        company = _company(self.env, 'ACTORSPACE')
        with patch.dict(os.environ, {'SC_ACCEPTANCE_FIXTURE_PASSWORD': 'scdevpass'}):
            actor = _user(self.env, 'fixture_scope_only', 'Synthetic scope-only actor', company, [company], [])
        caller = actor.with_user(actor).with_context(allowed_company_ids=company.ids)
        self.assertTrue(caller.has_group('smart_core.group_smart_core_non_customer_data_user'))
        self.assertFalse(caller.has_group('smart_construction_core.group_sc_cap_business_config_admin'))
        self.assertEqual(caller._sc_data_company_ids(), company.ids)

    def test_product_admin_sudo_cannot_create_fixture_space(self):
        actor = self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Synthetic fixture non-maintenance actor', 'login': 'fixture_non_maintenance_actor',
            'groups_id': [Command.set(self.env.ref('smart_core.group_smart_core_admin').ids)],
        })
        with self.assertRaises(AccessError), self.env.cr.savepoint():
            _company(self.env(user=actor.id, su=True), 'DENIEDSPACE')
