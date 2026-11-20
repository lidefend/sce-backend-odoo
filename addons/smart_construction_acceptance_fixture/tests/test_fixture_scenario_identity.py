# -*- coding: utf-8 -*-
from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged

from ..tools import frontend_productization_fixture as fixture


@tagged("post_install", "-at_install", "sc_gate", "fixture_scenario_identity")
class TestFixtureScenarioIdentity(TransactionCase):
    def test_current_scenario_choices_enable_on_a_fixture_owned_company(self):
        current_codes = set(self.env["sc.product.scenario"].sudo().with_context(
            active_test=False
        ).search([]).mapped("code"))
        self.assertEqual(
            set(fixture.FIXTURE_BUSINESS_SCENARIOS),
            current_codes,
        )

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
            patch(
                "odoo.addons.smart_construction_scene.services."
                "tenant_scene_activation.resolve_product_released",
                return_value=True,
            ),
        ):
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
