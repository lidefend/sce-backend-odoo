# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "sc_gate", "product_reports")
class TestProductReports(TransactionCase):
    def test_report_actions_and_labor_projection(self):
        project = self.env["project.project"].create({"name": "劳务报表测试项目", "company_id": self.env.company.id})
        usage = self.env["sc.labor.usage"].create({"name": "LAB-RPT-1", "project_id": project.id, "usage_date": "2026-07-10", "labor_team": "木工班组", "work_content": "模板安装", "worker_qty": 2, "work_hours": 8, "price_unit": 50})
        usage.action_submit()
        usage.action_confirm()
        partner = self.env["res.partner"].create({"name": "报表测试分包单位"})
        register = self.env["sc.subcontract.register"].create({"name": "SUB-REG-1", "project_id": project.id, "register_date": "2026-07-12", "subcontract_scope": "模板工程", "subcontractor_id": partner.id, "line_ids": [(0, 0, {"work_scope": "模板工程", "contract_qty": 1, "registered_amount": 1200})]})
        register.action_register()
        settlement = self.env["sc.subcontract.settlement"].create({"name": "SUB-SET-1", "project_id": project.id, "subcontractor_id": partner.id, "settlement_date": "2026-07-20", "line_ids": [(0, 0, {"work_scope": "模板工程", "qty": 1, "unit_price": 900})]})
        settlement._write_approval_state({"state": "confirmed"})
        self.env.flush_all()
        row = self.env["sc.labor.subcontract.report"].search([("source_model", "=", "sc.labor.usage"), ("source_res_id", "=", usage.id)], limit=1)
        self.assertTrue(row)
        self.assertEqual(row.fact_type, "labor_usage")
        self.assertEqual(row.labor_amount, 800)
        register_row = self.env["sc.labor.subcontract.report"].search([("source_model", "=", "sc.subcontract.register"), ("source_res_id", "=", register.id)], limit=1)
        settlement_row = self.env["sc.labor.subcontract.report"].search([("source_model", "=", "sc.subcontract.settlement"), ("source_res_id", "=", settlement.id)], limit=1)
        self.assertEqual(register_row.subcontract_registered_amount, 1200)
        self.assertEqual(register_row.company_id, project.company_id)
        self.assertEqual(settlement_row.subcontract_settled_amount, 900)
        labor_action = self.env.ref("smart_construction_core.action_sc_product_labor_subcontract_report_v1")
        tax_action = self.env.ref("smart_construction_core.action_sc_product_tax_report_v1")
        self.assertEqual(labor_action.res_model, "sc.labor.subcontract.report")
        self.assertEqual(tax_action.res_model, "sc.tax.filing")
        self.assertEqual(self.env.ref("smart_construction_core.business_config_contract_labor_subcontract_report_list_v1").action_id, labor_action)
        self.assertEqual(self.env.ref("smart_construction_core.business_config_contract_tax_report_list_v1").action_id, tax_action)

    def test_analysis_contract_projects_native_labels_and_selection(self):
        from odoo.addons.smart_core.handlers.ui_contract_v2 import UiContractV2Handler
        env = self.env(context=dict(self.env.context, lang="zh_CN"))
        for action_key in ("action_sc_product_labor_subcontract_report_v1", "action_sc_product_tax_report_v1"):
            action = env.ref("smart_construction_core." + action_key)
            metadata = env[action.res_model].fields_get()
            for view_type in ("pivot", "graph"):
                with self.subTest(action=action_key, view_type=view_type):
                    response = UiContractV2Handler(env, su_env=env["ir.model"].sudo().env).handle({
                        "op": "action_open", "action_id": action.id, "view_type": view_type,
                        "contract_surface": "user",
                    })
                    response = response.to_legacy_dict() if hasattr(response, "to_legacy_dict") else response
                    self.assertTrue(response.get("ok"), response)
                    profile = response["data"]["layoutContract"][view_type + "Profile"]
                    self.assertTrue(profile["dimensions"])
                    self.assertTrue(profile["measures"])
                    for field in profile["dimensions"] + profile["measures"]:
                        native = metadata[field["name"]]
                        self.assertEqual(field["label"], native["string"])
                        self.assertEqual(field["fieldType"], native["type"])
                        if native["type"] == "selection":
                            self.assertEqual([list(pair) for pair in field["selection"]],
                                             [list(pair) for pair in native["selection"]])
