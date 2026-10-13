"""Actual native XML rules on the payroll chain; fixtures roll back entirely."""
import os
from copy import deepcopy
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from lxml import etree
from odoo import Command, SUPERUSER_ID
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged
from odoo.tools.convert import convert_xml_import


@tagged('post_install', '-at_install', 'payroll_data_space_rules')
class TestPayrollDataSpaceRules(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        secret = 'd' * 64
        maintenance = patch.dict(os.environ, {'SC_TENANT_PAYLOAD_MAINTENANCE_CAPABILITY': secret})
        maintenance.start()
        cls.addClassCleanup(maintenance.stop)
        Registration = cls.env['sc.tenant.company.registration'].with_user(SUPERUSER_ID).with_context(
            sc_tenant_payload_import=True, sc_tenant_payload_maintenance_capability=secret,
        )
        cls.demo = Registration._create_non_customer_space(
            tenant_key='payroll-rule-demo', purpose='demo', company_name='Synthetic payroll demo')
        cls.test_space = Registration._create_non_customer_space(
            tenant_key='payroll-rule-test', purpose='test', company_name='Synthetic payroll test')
        customer = cls.env['res.company'].create({'name': 'Synthetic payroll customer'})
        cls.customer = Registration.create({
            'tenant_key': 'payroll-rule-customer', 'company_id': customer.id,
            'source_module': 'customer_scope_test', 'source_external_key': 'customer',
        })
        cls.unknown = cls.env['res.company'].create({'name': 'Synthetic payroll unknown'})
        cls.companies = cls.demo.company_id | cls.test_space.company_id | customer | cls.unknown
        business_group = cls.env.ref('smart_construction_core.group_sc_cap_business_config_admin')

        def actor(login, company, extra=()):
            return cls.env['res.users'].with_context(no_reset_password=True).create({
                'name': login, 'login': login, 'company_id': company.id,
                'company_ids': [Command.set(cls.companies.ids)],
                'groups_id': [Command.set(business_group.ids + list(extra))],
            })

        cls.admin = actor('synthetic_payroll_admin', cls.demo.company_id,
                          cls.env.ref('smart_core.group_smart_core_admin').ids)
        cls.customer_user = actor('synthetic_payroll_customer', customer)
        cls.test_user = actor('synthetic_payroll_tester', cls.test_space.company_id,
                              cls.env.ref('smart_core.group_smart_core_non_customer_data_user').ids)
        cls.payrolls = cls.env['sc.hr.payroll.document'].create([
            {'fact_type': 'salary_registration', 'company_id': company.id,
             'employee_name': 'Synthetic boundary employee', 'period_year': 2026,
             'period_month': 10, 'payer_unit': 'Synthetic boundary payer',
             'gross_amount': amount, 'net_salary': amount}
            for company, amount in zip(cls.companies, (11, 101, 1001, 10001))
        ])
        cls.payrolls.action_submit()
        cls.payrolls.action_done()
        cls.payments = cls.env['sc.hr.salary.payment'].create([
            {'payroll_document_id': payroll.id, 'payment_amount': 1}
            for payroll in cls.payrolls
        ])
        cls.env.flush_all()
        cls.env['sc.salary.summary'].init()
        # Load only the exact three changed records through Odoo's XML loader.
        # No duplicated domain literals and no persistent runtime activation.
        source = etree.parse(str(Path(__file__).resolve().parents[1] / 'security/sc_record_rules.xml'))
        root = etree.Element('odoo')
        data = etree.SubElement(root, 'data')
        for xmlid in ('rule_sc_hr_payroll_document_company', 'rule_sc_hr_salary_payment_company',
                      'rule_sc_salary_summary_company'):
            nodes = source.xpath("//record[@id='%s']" % xmlid)
            if len(nodes) != 1:
                raise AssertionError('Native rule declaration must be unique: ' + xmlid)
            data.append(deepcopy(nodes[0]))
        xml_input = BytesIO(etree.tostring(root))
        xml_input.name = 'sc_record_rules.xml.selected-payroll-rules'
        convert_xml_import(cls.env, 'smart_construction_core', xml_input,
                           {}, mode='update', noupdate=False)

    def model(self, name, actor, companies=None):
        return self.env[name].with_user(actor).with_context(
            allowed_company_ids=self.companies.ids if companies is None else companies.ids,
        )

    def test_actual_root_detail_and_summary_search_are_bidirectional(self):
        for actor, allowed in (
            (self.admin, self.demo.company_id | self.test_space.company_id),
            (self.test_user, self.demo.company_id | self.test_space.company_id),
            (self.customer_user, self.customer.company_id),
        ):
            for name in ('sc.hr.payroll.document', 'sc.hr.salary.payment', 'sc.salary.summary'):
                with self.subTest(actor=actor.login, model=name):
                    Model = self.model(name, actor)
                    rows = Model.search([('company_id', 'in', self.companies.ids)])
                    self.assertEqual(set(rows.company_id.ids), set(allowed.ids))
                    self.assertEqual(Model.search_count([('company_id', 'in', self.companies.ids)]), len(allowed))

    def test_direct_read_and_export_cannot_bypass_purpose(self):
        (self.admin | self.customer_user).write({
            'groups_id': [Command.link(self.env.ref('base.group_allow_export').id)],
        })
        for actor, forbidden in ((self.admin, self.customer.company_id),
                                 (self.customer_user, self.demo.company_id)):
            for name, sources in (('sc.hr.payroll.document', self.payrolls),
                                  ('sc.hr.salary.payment', self.payments),
                                  ('sc.salary.summary', self.env['sc.salary.summary'].search([]))):
                row = sources.filtered(lambda record: record.company_id == forbidden)
                self.assertTrue(row)
                target = self.model(name, actor).browse(row.ids)
                with self.subTest(actor=actor.login, model=name):
                    allowed = self.model(name, actor).search([('company_id', '=', actor.company_id.id)])
                    self.assertTrue(allowed)
                    self.assertEqual(len(allowed.export_data(['company_id'])['datas']), len(allowed))
                    with self.assertRaises(AccessError):
                        target.read(['company_id'])
                    with self.assertRaises(AccessError):
                        target.export_data(['company_id'])

    def test_native_summary_aggregate_does_not_include_denied_sources(self):
        for actor, expected in ((self.admin, 112), (self.customer_user, 1001)):
            rows = self.model('sc.salary.summary', actor).read_group(
                [('company_id', 'in', self.companies.ids)], ['net_salary:sum'], [],
            )
            self.assertEqual(rows[0]['net_salary'], expected)

    def test_business_create_and_write_are_bounded_by_purpose(self):
        for actor, allowed, denied in (
            (self.admin, self.demo.company_id, self.customer.company_id),
            (self.customer_user, self.customer.company_id, self.test_space.company_id),
        ):
            Payroll = self.model('sc.hr.payroll.document', actor)
            accepted = Payroll.create({'fact_type': 'salary_registration', 'company_id': allowed.id})
            accepted.write({'description': 'Synthetic allowed edit'})
            self.assertEqual(accepted.description, 'Synthetic allowed edit')
            with self.assertRaises(AccessError), self.env.cr.savepoint():
                Payroll.create({'fact_type': 'salary_registration', 'company_id': denied.id})
            forbidden = self.payrolls.filtered(lambda record: record.company_id == denied)
            with self.assertRaises(AccessError), self.env.cr.savepoint():
                Payroll.browse(forbidden.id).write({'description': 'Synthetic denied edit'})

    def test_payment_create_cannot_use_denied_parent(self):
        for actor, allowed, denied in (
            (self.admin, self.demo.company_id, self.customer.company_id),
            (self.customer_user, self.customer.company_id, self.demo.company_id),
        ):
            Payment = self.model('sc.hr.salary.payment', actor)
            parent = self.payrolls.filtered(lambda row: row.company_id == allowed)
            accepted = Payment.create({'payroll_document_id': parent.id, 'payment_amount': 1})
            self.assertEqual(accepted.company_id, allowed.with_env(Payment.env))
            forbidden = self.payrolls.filtered(lambda row: row.company_id == denied)
            with self.assertRaises(AccessError), self.env.cr.savepoint():
                Payment.create({'payroll_document_id': forbidden.id, 'payment_amount': 1})

    def test_selected_company_and_registration_revocation(self):
        Model = self.model('sc.hr.payroll.document', self.admin, self.test_space.company_id)
        self.assertEqual(Model.search([]).company_id.ids, self.test_space.company_id.ids)
        self.test_space.write({'active': False})
        self.assertFalse(Model.search([]))

    def test_unregistered_company_is_denied_even_when_authorized_company(self):
        for actor in (self.admin, self.customer_user, self.test_user):
            Model = self.model('sc.hr.payroll.document', actor, self.unknown)
            self.assertFalse(Model.search([]))
            with self.assertRaises(AccessError), self.env.cr.savepoint():
                Model.create({'fact_type': 'salary_registration', 'company_id': self.unknown.id})
