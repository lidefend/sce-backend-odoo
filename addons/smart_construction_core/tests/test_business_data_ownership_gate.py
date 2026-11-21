"""The upgrade-time ownership gate, on real ORM objects and real companies.

One defect motivated this file: company ceilings resolve row visibility through
the registered data space, so a database whose business rows predate the
data-space declaration upgraded silently into an empty product. Onboarding used
to be proven only before new writes. These tests pin the missing half - existing
rows whose owning company was never onboarded must refuse the upgrade - and the
governed way out: registering that owner clears exactly the reported company.

The ownership authority is the real ``sc.tenant.company.registration`` model and
the real maintenance principal rule, not a stub. Every fixture is rolled back.
"""

from odoo import SUPERUSER_ID, api
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.smart_construction_core.services import business_data_ownership
from odoo.addons.smart_core.security import data_space_provisioning as provisioning

#: Any company-owned model exercises the same decision path; ``res.partner`` is
#: used because a test can create exactly one owned row without touching
#: industry semantics.
PROBE_MODEL = 'res.partner'


@tagged('post_install', '-at_install', 'data_space_business_data_ownership')
class TestBusinessDataOwnershipGate(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Registration = cls.env['sc.tenant.company.registration']

    def _make_unregistered_owner(self):
        company = self.env['res.company'].sudo().create({
            'name': 'Ownership gate probe',
            'is_platform_bootstrap_company': False,
        })
        self.env[PROBE_MODEL].sudo().create({
            'name': 'Ownership gate probe row',
            'company_id': company.id,
        })
        return company

    def test_declared_probe_models_are_loaded_from_the_module(self):
        models = business_data_ownership.probe_models()
        self.assertGreaterEqual(len(models), 100)
        self.assertIn('payment.request', models)
        self.assertEqual(sorted(set(models)), sorted(models), 'no duplicates')
        # Scene is an optional downstream module. Core declares its ownership
        # ceiling without making Scene a mandatory installation dependency.
        optional = {"sc.scene.company.enablement"}
        self.assertEqual(sorted(set(models) - optional - set(self.env.registry)), [])
        self.assertIn("sc.scene.company.enablement", models)
        scene = self.env["ir.module.module"].search([("name", "=", "smart_construction_scene")])
        self.assertEqual("sc.scene.company.enablement" in self.env.registry, scene.state == "installed")

    def test_gate_reports_an_existing_row_whose_owner_was_never_onboarded(self):
        company = self._make_unregistered_owner()
        owners = provisioning.business_data_company_ids(self.env, [PROBE_MODEL])
        self.assertIn(company.id, owners)
        self.assertIn(
            company.id,
            provisioning.unregistered_business_companies(self.env, owners),
        )
        with self.assertRaises(ValueError) as ctx:
            provisioning.assert_business_data_ownership_registered(self.env, [PROBE_MODEL])
        message = str(ctx.exception)
        self.assertIn('DATA_SPACE_UNREGISTERED_BUSINESS_DATA_OWNER', message)
        self.assertIn(str(company.id), message)

    def test_onboarding_the_owner_clears_the_reported_company(self):
        company = self._make_unregistered_owner()
        owners = provisioning.business_data_company_ids(self.env, [PROBE_MODEL])
        before = set(provisioning.unregistered_business_companies(self.env, owners))
        self.Registration.sudo()._register_non_customer_space(
            tenant_key='ownership-gate-probe-%s' % company.id,
            purpose='demo', company_id=company.id,
        )
        self.assertEqual(
            set(provisioning.unregistered_business_companies(self.env, owners)),
            before - {company.id},
        )
        self.assertEqual(provisioning.unregistered_business_companies(self.env, company.ids), [])
        # This test owns one synthetic company. Bootstrap/other owners remain
        # rejected and must never be silently enrolled to make the probe green.
        self.assertIn(company.id, owners)
        if before - {company.id}:
            with self.assertRaisesRegex(ValueError, "DATA_SPACE_UNREGISTERED_BUSINESS_DATA_OWNER"):
                provisioning.assert_business_data_ownership_registered(self.env, [PROBE_MODEL])
        else:
            self.assertEqual(provisioning.assert_business_data_ownership_registered(self.env, [PROBE_MODEL]), owners)

    def test_gate_is_silent_while_no_business_row_exists(self):
        self.assertEqual(provisioning.business_data_company_ids(self.env, ['not.a.model']), [])
        self.assertEqual(
            provisioning.assert_business_data_ownership_registered(self.env, ['not.a.model']),
            [],
        )

    def test_industry_readiness_report_matches_the_platform_decision(self):
        report = business_data_ownership.ownership_readiness(self.env)
        self.assertEqual(report['probe_model_count'], len(business_data_ownership.probe_models()))
        self.assertEqual(report['passed'], not report['unregistered_business_data_company_ids'])
        self.assertEqual(
            report['business_data_company_ids'],
            provisioning.business_data_company_ids(
                self.env, business_data_ownership.probe_models()),
        )

    def test_bootstrap_carrier_owning_rows_is_reported_as_unknown_ownership(self):
        """The technical carrier is never registered, so its rows fail the gate.

        "Unknown ownership" and "the platform bootstrap company carries business
        data" are the same fail-closed answer; the gate must report it instead of
        silently resolving the carrier to an empty scope.
        """
        carrier = self.env['res.company'].sudo().create({
            'name': 'Ownership gate carrier',
            'is_platform_bootstrap_company': True,
        })
        self.env[PROBE_MODEL].sudo().create({
            'name': 'Ownership gate carrier row',
            'company_id': carrier.id,
        })
        owners = provisioning.business_data_company_ids(self.env, [PROBE_MODEL])
        self.assertIn(carrier.id, owners)
        with self.assertRaises(ValueError) as ctx:
            provisioning.assert_business_data_ownership_registered(self.env, [PROBE_MODEL])
        self.assertIn(str(carrier.id), str(ctx.exception))

    def test_shipped_probe_projection_matches_the_ceiling_declaration(self):
        """The module copy is a projection, not a second list to maintain.

        The container mounts addons, not the repository root, so the probe list
        has to ride inside the module. This derives the expected set straight
        from the declaration and compares, so a hand-edited copy fails here.
        """
        import json
        from pathlib import Path

        declaration_path = (
            Path(__file__).resolve().parents[3] / 'scripts/verify/data_scope_declarations.json'
        )
        declaration = json.loads(declaration_path.read_text(encoding='utf-8'))
        expected = {entry['model'] for entry in declaration['enforced']}
        for group in declaration['deferred']:
            expected.update(group['models'])
        expected.update(entry['model'] for entry in declaration['source_bounded'])
        self.assertEqual(sorted(expected), business_data_ownership.probe_models())

    def test_upgrade_gate_entry_delegates_to_the_platform_decision(self):
        """The industry layer owns the model list; the platform owns the meaning."""
        models = business_data_ownership.probe_models()
        owners = provisioning.business_data_company_ids(self.env, models)
        unregistered = provisioning.unregistered_business_companies(self.env, owners)
        if unregistered:
            with self.assertRaises(ValueError) as ctx:
                business_data_ownership.assert_existing_business_data_ownership(self.env)
            self.assertIn('DATA_SPACE_UNREGISTERED_BUSINESS_DATA_OWNER', str(ctx.exception))
        else:
            self.assertEqual(
                business_data_ownership.assert_existing_business_data_ownership(self.env),
                owners,
            )
