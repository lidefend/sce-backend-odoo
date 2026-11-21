# -*- coding: utf-8 -*-
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged

from ..tools import frontend_productization_fixture as fixture
from .test_business_scene_lifecycle import publish_scenarios


@tagged(
    "post_install",
    "-at_install",
    "sc_gate",
    "acceptance_business_scene_lifecycle",
    "fixture_scenario_identity",
)
class TestFixtureScenarioIdentity(TransactionCase):
    def test_current_scenario_choices_enable_on_a_fixture_owned_company(self):
        current_codes = set(self.env["sc.product.scenario"].sudo().with_context(
            active_test=False
        ).search([]).mapped("code"))
        self.assertEqual(
            set(fixture.FIXTURE_BUSINESS_SCENARIOS),
            current_codes,
        )
        self.assertTrue(all(
            scenario_code in current_codes
            for scenario_code, _menu_xmlid, _intent
            in fixture.ACCEPTANCE_SCENARIO_BINDINGS
        ))

        company = self.env.ref(
            fixture.MODULE + ".fe_company_a",
            raise_if_not_found=False,
        )
        if not company:
            company = self.env["res.company"].sudo().create({
                "name": "Fixture scenario identity company",
            })
            self.env["ir.model.data"].sudo().create({
                "module": fixture.MODULE,
                "name": "fe_company_a",
                "model": "res.company",
                "res_id": company.id,
                "noupdate": True,
            })
        with (
            patch.object(fixture, "_guard_acceptance_scope", return_value=None),
        ):
            publish_scenarios(self.env)
            count = fixture._ensure_business_scenarios(self.env, (company,))
        self.assertEqual(count, 46)
        enablements = self.env["sc.scene.company.enablement"].sudo().search([
            ("company_id", "=", company.id),
        ])
        self.assertEqual(len(enablements), 46)
        self.assertTrue(all(enablements.mapped("enabled")))
        self.assertEqual(
            set(enablements.mapped("scene_key")),
            {
                "business.v1:" + code
                for code in fixture.FIXTURE_BUSINESS_SCENARIOS
            },
        )
        preview = self.env["sc.scene.company.enablement"].sudo().create({
            "company_id": company.id,
            "scene_key": "finance.payment_ledger",
        })
        with self.assertRaises(UserError):
            preview.set_enabled(True)
