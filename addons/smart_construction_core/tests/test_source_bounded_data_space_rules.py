"""Installed data-purpose ceiling behind the ``source_bounded`` registration.

The declaration in ``scripts/verify/data_scope_declarations.json`` routes a
model whose company rule already exists in a security file through
``source_bounded`` instead of generating a second ceiling.  Two facts are proved
here, on the real rules and with real principals:

* every declared source rule is loaded from its own security file and carries
  both isolation facts on the declared anchor - the allowed-company selector and
  the purpose authority ``user._sc_data_company_ids()`` - so a company-only
  rule can never stand in for the ceiling an ``enforced`` model receives;
* two real principals reading representative business rows are separated
  bidirectionally: a customer identity cannot read a demo/test company's row and
  a non-customer identity cannot read the customer company's row.

Fixtures roll back entirely; no persistent runtime state is written.
"""
import json
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

MODULE_ROOT = Path(__file__).resolve().parents[1]
# A declaration path is repo-relative (``addons/<module>/...``). Inside the
# governed container the addons root is a different mount than the repo root, so
# resolve it from the addons root rather than from the repository root.
ADDONS_ROOT = Path(__file__).resolve().parents[2]
DECLARATIONS = Path(__file__).resolve().parents[3] / 'scripts/verify/data_scope_declarations.json'


@tagged('post_install', '-at_install', 'source_bounded_data_space_rules')
class TestSourceBoundedDataSpaceRules(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if not DECLARATIONS.is_file():
            raise AssertionError('source_bounded declaration is missing: ' + str(DECLARATIONS))
        cls.declaration = json.loads(DECLARATIONS.read_text(encoding='utf-8'))
        cls.bounded = list(cls.declaration.get('source_bounded') or [])
        if not cls.bounded:
            raise AssertionError('source_bounded declaration is empty')

        secret = 'd' * 64
        maintenance = patch.dict(os.environ, {'SC_TENANT_PAYLOAD_MAINTENANCE_CAPABILITY': secret})
        maintenance.start()
        cls.addClassCleanup(maintenance.stop)
        Registration = cls.env['sc.tenant.company.registration'].with_user(SUPERUSER_ID).with_context(
            sc_tenant_payload_import=True, sc_tenant_payload_maintenance_capability=secret,
        )
        cls.demo = Registration._create_non_customer_space(
            tenant_key='source-bounded-demo', purpose='demo', company_name='Synthetic bounded demo')
        cls.test_space = Registration._create_non_customer_space(
            tenant_key='source-bounded-test', purpose='test', company_name='Synthetic bounded test')
        customer = cls.env['res.company'].create({'name': 'Synthetic bounded customer'})
        cls.customer = Registration.create({
            'tenant_key': 'source-bounded-customer', 'company_id': customer.id,
            'source_module': 'customer_scope_test', 'source_external_key': 'customer',
        })
        cls.unknown = cls.env['res.company'].create({'name': 'Synthetic bounded unknown'})
        cls.companies = cls.demo.company_id | cls.test_space.company_id | customer | cls.unknown
        groups = (
            cls.env.ref('smart_construction_core.group_sc_cap_business_config_admin')
            | cls.env.ref('smart_construction_core.group_sc_cap_project_manager')
        )

        def actor(login, company, extra=()):
            return cls.env['res.users'].with_context(no_reset_password=True).create({
                'name': login, 'login': login, 'company_id': company.id,
                'company_ids': [Command.set(cls.companies.ids)],
                'groups_id': [Command.set(groups.ids + list(extra))],
            })

        cls.admin = actor('synthetic_bounded_admin', cls.demo.company_id,
                          cls.env.ref('smart_core.group_smart_core_admin').ids)
        cls.customer_user = actor('synthetic_bounded_customer', customer)
        cls.test_user = actor('synthetic_bounded_tester', cls.test_space.company_id,
                              cls.env.ref('smart_core.group_smart_core_non_customer_data_user').ids)
        cls.purpose_term = {
            entry['rule']: "('{0}', 'in', user._sc_data_company_ids())".format(entry['anchor'])
            for entry in cls.bounded
        }
        cls._load_declared_source_rules()
        cls.projects = cls.env['project.project'].sudo().create([
            {'name': 'Synthetic bounded project %s' % index, 'company_id': company.id}
            for index, company in enumerate(cls.companies)
        ])
        cls.partners = cls.env['res.partner'].sudo().create([
            {'name': 'Synthetic bounded partner %s' % index, 'company_id': company.id}
            for index, company in enumerate(cls.companies)
        ])
        cls.opportunities = cls.env['tender.opportunity'].sudo().create([
            {'name': 'Synthetic bounded tender %s' % index, 'company_id': project.company_id.id}
            for index, project in enumerate(cls.projects)
        ])
        cls.contracts = cls.env['construction.contract'].sudo().create([
            {'subject': 'Synthetic bounded contract %s' % index, 'type': 'out',
             'project_id': project.id, 'partner_id': cls.partners[index].id,
             'company_id': project.company_id.id}
            for index, project in enumerate(cls.projects)
        ])
        cls.env.flush_all()

    @classmethod
    def _load_declared_source_rules(cls):
        """Install exactly the declared source rules from their own file.

        No duplicated domain literal lives in this test: the rule text that runs
        is the text the module ships.  ``noupdate`` is cleared for the load so the
        current declaration is what the assertions read back.
        """
        by_file = {}
        for entry in cls.bounded:
            by_file.setdefault(entry['file'], set()).add(entry['rule'])
        for relative, xmlids in sorted(by_file.items()):
            source_path = ADDONS_ROOT / relative.split('addons/', 1)[-1]
            source = etree.parse(str(source_path))
            root = etree.Element('odoo')
            data = etree.SubElement(root, 'data')
            for xmlid in sorted(xmlids):
                nodes = source.xpath("//record[@id='%s']" % xmlid)
                if len(nodes) != 1:
                    raise AssertionError('Native rule declaration must be unique: ' + xmlid)
                data.append(deepcopy(nodes[0]))
            xml_input = BytesIO(etree.tostring(root))
            xml_input.name = relative
            convert_xml_import(cls.env, 'smart_construction_core', xml_input,
                               {}, mode='update', noupdate=False)

    def model(self, name, actor, companies=None):
        return self.env[name].with_user(actor).with_context(
            allowed_company_ids=self.companies.ids if companies is None else companies.ids,
        )

    def test_every_declared_source_rule_carries_the_purpose_authority(self):
        """The installed rule set, not the declaration prose, is the evidence."""
        for entry in self.bounded:
            rule = self.env.ref('smart_construction_core.' + entry['rule'])
            with self.subTest(model=entry['model'], rule=entry['rule']):
                self.assertTrue(getattr(rule, 'global'),
                                'source rule must stay global: ' + entry['rule'])
                self.assertIn("('{0}', 'in', company_ids)".format(entry['anchor']),
                              rule.domain_force)
                self.assertIn(self.purpose_term[entry['rule']], rule.domain_force)

    def test_customer_and_non_customer_reads_are_bidirectionally_separated(self):
        """Two real principals, two real business models, both directions."""
        read_scope = {
            self.admin: self.demo.company_id | self.test_space.company_id,
            self.test_user: self.demo.company_id | self.test_space.company_id,
            self.customer_user: self.customer.company_id,
        }
        for name, rows in (('tender.opportunity', self.opportunities),
                           ('construction.contract', self.contracts)):
            for actor, allowed in read_scope.items():
                Model = self.model(name, actor)
                visible = Model.search([('company_id', 'in', self.companies.ids)])
                with self.subTest(actor=actor.login, model=name):
                    self.assertEqual(set(visible.company_id.ids), set(allowed.ids))
                    self.assertEqual(Model.search_count([('company_id', 'in', self.companies.ids)]),
                                     len(allowed))

    def test_denied_company_row_read_raises(self):
        """A deny must be an access error on the row, not a silent empty set."""
        for actor, denied in ((self.customer_user, self.demo.company_id),
                              (self.test_user, self.customer.company_id)):
            for name, rows in (('tender.opportunity', self.opportunities),
                               ('construction.contract', self.contracts)):
                target = rows.filtered(lambda record: record.company_id == denied)
                self.assertTrue(target, 'fixture row must exist for ' + name)
                with self.subTest(actor=actor.login, model=name), self.assertRaises(AccessError):
                    self.model(name, actor).browse(target.id).read(['company_id'])

    def test_unregistered_company_rows_stay_invisible_to_every_principal(self):
        for actor in (self.admin, self.test_user, self.customer_user):
            for name in ('tender.opportunity', 'construction.contract'):
                Model = self.model(name, actor, self.unknown)
                with self.subTest(actor=actor.login, model=name):
                    self.assertFalse(Model.search([]))
