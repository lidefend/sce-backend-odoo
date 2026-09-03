# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "sc_gate", "product_system_settings")
class TestProductSystemSettings(TransactionCase):
    def test_action_uses_allowlisted_transient_facade(self):
        action = self.env.ref("smart_construction_core.action_sc_product_system_parameter_v1")
        self.assertEqual(action.res_model, "sc.product.system.settings")
        self.assertEqual(action.view_mode, "form")
        self.assertEqual(action.view_id, self.env.ref("smart_construction_core.view_sc_product_system_settings_form_v1"))
        contract = self.env.ref("smart_construction_core.business_config_contract_product_system_settings_form_v1")
        self.assertEqual(contract.action_id, action)
        context = contract.contract_json["view_orchestration"]["context"]
        self.assertEqual(context["secret_policy"], "deployment_only")

    def test_apply_maps_one_choice_to_company_authority(self):
        settings = self.env["sc.product.system.settings"].create({"cost_ledger_source": "purchase_order"})
        settings.action_apply()
        self.assertFalse(self.env.company.sc_cost_from_account_move)
        self.assertTrue(self.env.company.sc_cost_from_purchase)
        self.assertFalse(self.env.company.sc_cost_from_stock)
        loaded = self.env["sc.product.system.settings"].default_get(["cost_ledger_source"])
        self.assertEqual(loaded["cost_ledger_source"], "purchase_order")

    def test_each_company_has_independent_cost_authority(self):
        first_company = self.env.company
        second_company = self.env["res.company"].create(
            {"name": "独立成本来源公司", "currency_id": first_company.currency_id.id}
        )
        first_company.write({
            "sc_cost_from_account_move": False,
            "sc_cost_from_purchase": True,
            "sc_cost_from_stock": False,
        })
        second_settings = self.env["sc.product.system.settings"].with_company(
            second_company
        ).create({"cost_ledger_source": "stock_move"})
        second_settings.action_apply()
        self.assertTrue(first_company.sc_cost_from_purchase)
        self.assertFalse(first_company.sc_cost_from_stock)
        self.assertTrue(second_company.sc_cost_from_stock)
        self.assertFalse(second_company.sc_cost_from_purchase)

    def test_legacy_global_source_is_promoted_to_all_companies_once(self):
        second_company = self.env["res.company"].create(
            {"name": "旧配置迁移公司", "currency_id": self.env.company.currency_id.id}
        )
        params = self.env["ir.config_parameter"].sudo()
        keys = (
            "smart_construction_core.sc_cost_from_account_move",
            "smart_construction_core.sc_cost_from_purchase",
            "smart_construction_core.sc_cost_from_stock",
        )
        for key in keys:
            params.set_param(key, "True" if key.endswith("sc_cost_from_purchase") else "False")
        self.env["res.company"]._migrate_legacy_cost_source_parameters()
        companies = self.env.company | second_company
        self.assertTrue(all(companies.mapped("sc_cost_from_purchase")))
        self.assertFalse(any(companies.mapped("sc_cost_from_account_move")))
        self.assertFalse(any(companies.mapped("sc_cost_from_stock")))
        self.assertFalse(params.search_count([("key", "in", list(keys))]))
