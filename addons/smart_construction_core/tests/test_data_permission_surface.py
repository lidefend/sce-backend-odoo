# -*- coding: utf-8 -*-
import ast

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "sc_gate", "data_permission_surface")
class TestDataPermissionSurface(TransactionCase):
    def test_entry_reuses_capability_model_without_contract_overlap(self):
        action = self.env.ref("smart_construction_core.action_sc_product_data_permission_v1")
        self.assertEqual(action.res_model, "res.users")
        self.assertIn("sc_runtime_company_maintainable", action.domain)
        context = ast.literal_eval(action.context)
        self.assertTrue(context["sc_runtime_user_management"])
        self.assertFalse(context["create"])
        views = {row.view_mode: row.view_id for row in action.view_ids}
        self.assertEqual(views["form"], self.env.ref("smart_construction_core.view_sc_data_permission_user_form"))
        contract = self.env.ref("smart_construction_core.business_config_contract_data_permission_form_v1")
        self.assertEqual(contract.action_id, action)
        authority = contract.contract_json["view_orchestration"]["context"]
        self.assertEqual(authority["role_authority"], "res.groups")
        self.assertEqual(authority["project_scope_authority"], "sc.project.member.assignment")
