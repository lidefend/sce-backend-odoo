# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "sc_gate", "product_system_settings")
class TestProductSystemSettings(TransactionCase):
    KEYS = (
        "smart_construction_core.sc_cost_from_account_move",
        "smart_construction_core.sc_cost_from_purchase",
        "smart_construction_core.sc_cost_from_stock",
    )

    def test_action_uses_allowlisted_transient_facade(self):
        action = self.env.ref("smart_construction_core.action_sc_product_system_parameter_v1")
        self.assertEqual(action.res_model, "sc.product.system.settings")
        self.assertEqual(action.view_mode, "form")
        self.assertEqual(action.view_id, self.env.ref("smart_construction_core.view_sc_product_system_settings_form_v1"))
        contract = self.env.ref("smart_construction_core.business_config_contract_product_system_settings_form_v1")
        self.assertEqual(contract.action_id, action)
        context = contract.contract_json["view_orchestration"]["context"]
        self.assertEqual(context["secret_policy"], "deployment_only")

    def test_apply_maps_one_choice_to_existing_parameter_authority(self):
        params = self.env["ir.config_parameter"].sudo().with_company(self.env.company)
        settings = self.env["sc.product.system.settings"].create({"cost_ledger_source": "purchase_order"})
        settings.action_apply()
        self.assertEqual(params.get_param(self.KEYS[0]), "False")
        self.assertEqual(params.get_param(self.KEYS[1]), "True")
        self.assertEqual(params.get_param(self.KEYS[2]), "False")
        loaded = self.env["sc.product.system.settings"].default_get(["cost_ledger_source"])
        self.assertEqual(loaded["cost_ledger_source"], "purchase_order")
