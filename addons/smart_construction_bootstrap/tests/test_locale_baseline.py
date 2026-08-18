# -*- coding: utf-8 -*-
"""
smart_construction_bootstrap minimal tests (PRODUCTIZATION-P0-SPRINT-001, R1).

post_init_hook establishes the fresh-DB locale baseline (lang/tz/currency).
Runs against the test DB inside a transaction (rolled back afterwards).

PENDING-ENV: to be executed in an Odoo test run (make mod.tests or CI).
"""

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.smart_construction_bootstrap.hooks import post_init_hook


@tagged("post_install", "-at_install", "smart_construction_bootstrap", "locale_baseline")
class TestBootstrapLocaleBaseline(TransactionCase):
    def test_post_init_hook_applies_baseline_params(self):
        post_init_hook(self.env)
        icp = self.env["ir.config_parameter"].sudo()
        self.assertEqual(icp.get_param("sc.bootstrap.lang"), "zh_CN")
        self.assertEqual(icp.get_param("sc.bootstrap.tz"), "Asia/Shanghai")
        self.assertEqual(icp.get_param("sc.bootstrap.currency"), "CNY")

    def test_post_init_hook_is_idempotent(self):
        post_init_hook(self.env)
        post_init_hook(self.env)  # second run must not raise
        icp = self.env["ir.config_parameter"].sudo()
        self.assertEqual(icp.get_param("sc.bootstrap.lang"), "zh_CN")

    def test_companies_end_up_on_configured_currency(self):
        post_init_hook(self.env)
        currency = self.env.ref("base.CNY", raise_if_not_found=False)
        if currency:  # base data availability guard for trimmed test DBs
            companies = self.env["res.company"].sudo().search([])
            self.assertTrue(companies)
            self.assertTrue(all(company.currency_id == currency for company in companies))
