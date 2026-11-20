from __future__ import annotations

import json
import re
import unittest

from scripts.audit import build_scenario_product_organization as builder


class ScenarioProductOrganizationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.product_pages = builder.flatten_product_pages()
        cls.payload = builder.build_payload(cls.product_pages)

    def test_every_released_page_has_exactly_one_primary_organization_row(self):
        validation = self.payload["validation"]
        self.assertTrue(validation["ok"], validation["errors"])
        self.assertEqual(
            validation["unique_page_count"],
            len(self.product_pages),
        )
        self.assertEqual(validation["duplicate_page_count"], 0)
        self.assertEqual(validation["unassigned_page_count"], 0)

    def test_center_skeleton_is_one_workbench_plus_ten_centers(self):
        self.assertEqual(len(builder.PRODUCT_CENTERS), 11)
        self.assertEqual(
            builder.PRODUCT_CENTERS[0]["stable_key"],
            "workspace.home.workbench",
        )
        self.assertTrue(all(
            any(
                row["center_key"] == center["stable_key"]
                for row in self.product_pages.values()
            )
            for center in builder.PRODUCT_CENTERS
        ))

    def test_every_scenario_has_user_result_and_ordered_page_use(self):
        for scenario_row in self.payload["scenarios"]:
            with self.subTest(scenario=scenario_row["key"]):
                self.assertTrue(scenario_row["objective"])
                self.assertTrue(scenario_row["roles"])
                self.assertTrue(scenario_row["prerequisites"])
                self.assertTrue(scenario_row["result"])
                self.assertTrue(scenario_row["pages"])
                self.assertTrue(all(row["purpose"] for row in scenario_row["pages"]))
                self.assertTrue(all(
                    row["mode"] in {
                        "先办", "办理", "并列", "并列选择",
                        "辅助办理", "依据", "回读", "查看", "独立",
                    }
                    for row in scenario_row["pages"]
                ))
                self.assertTrue(all(row["page_output"] for row in scenario_row["pages"]))

    def test_workbench_and_cross_center_paths_use_stable_identities(self):
        self.assertTrue(self.payload["workbench_routes"])
        self.assertTrue(self.payload["cross_center_links"])
        known_menu_xmlids = set(self.product_pages)
        scenario_keys = {row["key"] for row in self.payload["scenarios"]}
        for row in self.payload["cross_center_links"]:
            with self.subTest(source=row["source_entry"], target=row["target_menu_xmlid"]):
                self.assertIn(row["source_menu_xmlid"], known_menu_xmlids)
                self.assertTrue(row["source_model"])
                self.assertTrue(row["source_record_id"])
                self.assertTrue(row["condition"])
                self.assertTrue(row["target_menu_xmlid"])
                self.assertIn(row["target_menu_xmlid"], known_menu_xmlids)
                self.assertTrue(row["carried_object"])
                self.assertTrue(row["result_location"])
                self.assertTrue(row["return"])
                self.assertTrue(row["availability"])
        for scenario_row in self.payload["scenarios"]:
            self.assertIn(scenario_row["key"], scenario_keys)
            self.assertTrue(all(
                row["menu_xmlid"] in known_menu_xmlids
                for row in scenario_row["pages"]
            ))
        for gap in self.payload["gaps"]:
            with self.subTest(gap=gap["issue"]):
                self.assertTrue(gap["evidence"])
                self.assertTrue(gap["id"])
                self.assertTrue(gap["status"])
                self.assertTrue(gap["impact"])
                self.assertTrue(gap["recommendation"])
                self.assertTrue(gap["affected_paths"])

    def test_generated_artifacts_are_current(self):
        self.assertEqual(
            json.loads(builder.JSON_OUTPUT.read_text(encoding="utf-8")),
            self.payload,
        )
        runtime_surface = builder.build_runtime_surface(self.payload)
        self.assertEqual(
            json.loads(builder.SURFACE_OUTPUT.read_text(encoding="utf-8")),
            runtime_surface,
        )
        self.assertEqual(
            builder.MARKDOWN_OUTPUT.read_text(encoding="utf-8"),
            builder.render_markdown(self.payload),
        )
        markdown = builder.MARKDOWN_OUTPUT.read_text(encoding="utf-8")
        table = markdown.split("## 一、完整组织总表", 1)[1].split(
            "## 二、按中心展开的完整目录", 1
        )[0]
        row_xmlids = re.findall(r"`((?:smart_construction_core|account)\.[^`]+)`", table)
        self.assertEqual(len(row_xmlids), len(self.product_pages))
        self.assertEqual(set(row_xmlids), set(self.product_pages))
        directory = markdown.split("## 二、按中心展开的完整目录", 1)[1].split(
            "## 三、工作台入口安排", 1
        )[0]
        directory_xmlids = re.findall(
            r"`((?:smart_construction_core|account)\.[^`]+)`",
            directory,
        )
        self.assertEqual(len(directory_xmlids), len(self.product_pages))
        self.assertEqual(set(directory_xmlids), set(self.product_pages))

    def test_approved_design_generates_the_complete_runtime_scenario_seed(self):
        self.assertEqual(self.payload["status"], "APPROVED_FOR_IMPLEMENTATION")
        surface = builder.build_runtime_surface(self.payload)
        self.assertEqual(surface["status"], "APPROVED_AS_PROJECTION_INPUT")
        self.assertEqual(
            surface["source_design"][0],
            "config/product_scenario_organization_v1.json",
        )
        scenarios = surface["scenarios"]
        self.assertEqual(len(scenarios), 46)
        direct_pages = surface["direct_platform_pages"]
        self.assertEqual(len(direct_pages), 16)
        self.assertEqual(
            len({row["menu_xmlid"] for row in direct_pages}),
            16,
        )
        self.assertEqual(
            {row["kind"] for row in direct_pages},
            {"workbench_direct", "configuration", "platform_initialization"},
        )
        self.assertEqual(surface["validation"]["direct_platform_count"], 16)
        self.assertEqual(
            [row["key"] for row in scenarios],
            [row["key"] for row in self.payload["scenarios"]],
        )
        self.assertEqual(
            [row["sequence"] for row in scenarios],
            list(range(1, 47)),
        )
        bindings = [
            binding
            for scenario in scenarios
            for binding in scenario["bindings"]
        ]
        self.assertEqual(len(bindings), 132)
        self.assertEqual(len({row["menu_key"] for row in bindings}), 132)
        self.assertEqual(
            {row["menu_key"] for row in bindings},
            set(self.product_pages),
        )
        self.assertTrue(all(
            row["intent"] in {"handle", "view", "approve", "report", "master_data"}
            for row in bindings
        ))
        self.assertFalse({
            "workspace.home",
            "governance.organization",
            "governance.configuration",
            "project.management",
            "contract.performance",
            "cost.budget",
            "procurement.supplier",
            "material.management",
            "subcontract.management",
            "labor.management",
            "quality.management",
            "safety.management",
            "payment.capital",
            "receipt.payment.ledger",
            "tax.management",
            "accounting.management",
            "analytics.decision",
            "equipment.management",
            "administration.office",
        } & {row["key"] for row in scenarios})

    def test_owner_centers_contain_cross_center_business_steps(self):
        by_key = {row["key"]: row for row in self.payload["scenarios"]}
        expected = {
            "resource.labor": {
                "smart_construction_core.menu_sc_product_labor_realname_v1",
                "smart_construction_core.menu_sc_product_labor_cost_v1",
                "smart_construction_core.menu_sc_product_labor_deduction_v1",
            },
            "resource.equipment": {
                "smart_construction_core.menu_sc_product_equipment_shift_v1",
            },
            "resource.subcontract": {
                "smart_construction_core.menu_sc_product_subcontract_cost_v1",
                "smart_construction_core.menu_sc_product_subcontract_variation_v1",
            },
            "finance.intercompany": {
                "smart_construction_core.menu_sc_product_team_loan_deduction_v1",
            },
            "admin.payroll": {
                "smart_construction_core.menu_sc_product_project_payroll_v1",
                "smart_construction_core.menu_sc_product_project_salary_payment_v1",
            },
        }
        for scenario_key, menu_xmlids in expected.items():
            scenario_row = by_key[scenario_key]
            with self.subTest(scenario=scenario_key):
                actual = {(row["menu_xmlid"], row["center_key"]) for row in scenario_row["pages"]}
                for menu_xmlid in menu_xmlids:
                    location = next(row for row in actual if row[0] == menu_xmlid)
                    self.assertNotEqual(location[1], scenario_row["owner_center"])

    def test_actions_are_not_downgraded_to_readback_and_alternatives_have_no_common_root(self):
        page_rows = {
            row["menu_xmlid"]: row
            for scenario_row in self.payload["scenarios"]
            for row in scenario_row["pages"]
        }
        for page_row in page_rows.values():
            self.assertNotIn("共同承接", page_row["preceding_or_related"])
        for xmlid in (
            "smart_construction_core.menu_sc_plan_report",
            "smart_construction_core.menu_sc_quality_recheck",
            "smart_construction_core.menu_sc_safety_recheck",
            "smart_construction_core.menu_sc_labor_settlement",
            "smart_construction_core.menu_sc_equipment_settlement",
            "smart_construction_core.menu_sc_material_rental_settlement",
            "smart_construction_core.menu_sc_subcontract_settlement",
            "smart_construction_core.menu_sc_product_project_salary_payment_v1",
            "smart_construction_core.menu_sc_product_tax_filing_v1",
            "smart_construction_core.menu_sc_product_data_permission_v1",
            "smart_construction_core.menu_sc_product_social_fund_v1",
        ):
            self.assertEqual(page_rows[xmlid]["mode"], "办理", xmlid)
        for xmlid in (
            "smart_construction_core.menu_sc_project_quick_create",
            "smart_construction_core.menu_sc_p1_expense_contract",
            "smart_construction_core.menu_sc_p1_daily_contract",
            "smart_construction_core.menu_sc_p1_expense_settlement",
            "smart_construction_core.menu_sc_product_general_contract_settlement_v1",
            "smart_construction_core.menu_sc_advance_fund",
        ):
            self.assertEqual(page_rows[xmlid]["mode"], "并列选择", xmlid)
            self.assertNotIn("共同承接", page_rows[xmlid]["preceding_or_related"])

    def test_workbench_routes_separate_result_from_navigation_return(self):
        for row in self.payload["workbench_routes"]:
            with self.subTest(entry=row["entry"]):
                self.assertTrue(row["result_location"])
                self.assertTrue(row["navigation_return"])
                self.assertTrue(row["availability"])
        by_entry = {row["entry"]: row for row in self.payload["workbench_routes"]}
        for entry in (
            "快捷办理：新建项目",
            "快捷办理：登记合同",
            "快捷办理：付款申请",
            "快捷办理：材料计划",
            "快捷办理：费用报销",
        ):
            self.assertIn("从工作台发起时回工作台", by_entry[entry]["navigation_return"])
        self.assertIn("项目按费用归属可选", by_entry["快捷办理：费用报销"]["context"])

    def test_conditional_steps_and_remaining_false_predecessors_are_removed(self):
        page_rows = {
            row["menu_xmlid"]: row
            for scenario_row in self.payload["scenarios"]
            for row in scenario_row["pages"]
        }
        self.assertIn("无扣款可直接结算", page_rows[
            "smart_construction_core.menu_sc_labor_settlement"
        ]["preceding_or_related"])
        self.assertIn("无签证可直接结算", page_rows[
            "smart_construction_core.menu_sc_subcontract_settlement"
        ]["preceding_or_related"])
        for xmlid in (
            "smart_construction_core.menu_sc_company_finance_expense",
            "smart_construction_core.menu_sc_product_numbering_rule_v1",
            "smart_construction_core.menu_sc_product_policy_document_v1",
            "smart_construction_core.menu_sc_material_outbound",
            "smart_construction_core.menu_sc_material_transfer",
            "smart_construction_core.menu_sc_product_material_return_v1",
            "smart_construction_core.menu_sc_material_loss",
        ):
            self.assertNotIn("共同承接", page_rows[xmlid]["preceding_or_related"])
        customer = page_rows["smart_construction_core.menu_sc_customer_partner"]
        self.assertNotIn("项目必填字段", customer["entry_context_and_return"])
        quick_create = page_rows["smart_construction_core.menu_sc_project_quick_create"]
        self.assertNotIn("前置办理：新项目立项", quick_create["entry_context_and_return"])
        quality_standard = page_rows["smart_construction_core.menu_sc_quality_standard_v2"]
        self.assertNotIn("检查责任人", quality_standard["entry_context_and_return"])
        self.assertNotIn("现场检查范围", quality_standard["entry_context_and_return"])
        labor_realname = page_rows[
            "smart_construction_core.menu_sc_product_labor_realname_v1"
        ]
        self.assertNotIn("实际用量", labor_realname["entry_context_and_return"])
        labor_plan = page_rows["smart_construction_core.menu_sc_labor_plan"]
        self.assertIn("实际用量不作为计划前置", labor_plan["entry_context_and_return"])
        equipment_plan = page_rows["smart_construction_core.menu_sc_equipment_plan"]
        self.assertIn("实际台班不作为计划前置", equipment_plan["entry_context_and_return"])

    def test_relation_overrides_do_not_leave_contradictory_required_predecessors(self):
        page_rows = {
            row["menu_xmlid"]: row
            for scenario_row in self.payload["scenarios"]
            for row in scenario_row["pages"]
        }
        for menu_xmlid, relation in builder.RELATION_OVERRIDES.items():
            if "不要求先办" not in relation and "条件步骤" not in relation:
                continue
            with self.subTest(menu_xmlid=menu_xmlid):
                context = page_rows[menu_xmlid]["entry_context_and_return"]
                self.assertIn(relation, context)
                self.assertNotIn("前置办理：", context)

    def test_cross_center_parameter_names_are_consistent(self):
        user_link = next(
            row for row in self.payload["cross_center_links"]
            if row["source_menu_xmlid"]
            == "smart_construction_core.menu_sc_runtime_user_management"
        )
        self.assertEqual(user_link["source_record_id"], "user_id")
        self.assertIn("user_id", user_link["carried_object"])
        self.assertNotIn("res.users_id", user_link["carried_object"])
        page_rows = {
            row["menu_xmlid"]: row
            for scenario_row in self.payload["scenarios"]
            for row in scenario_row["pages"]
        }
        subcontract_register = page_rows[
            "smart_construction_core.menu_sc_product_subcontract_cost_v1"
        ]
        self.assertEqual(
            subcontract_register["source_menu_name"],
            "分包成本登记",
        )
        self.assertIn("分包登记与成本确认", subcontract_register["menu_name"])
        settlement_order = page_rows[
            "smart_construction_core.menu_sc_settlement_order"
        ]
        self.assertEqual(settlement_order["mode"], "回读")
        self.assertIn("不在此新建业务记录", settlement_order["purpose"])
        income_settlement = page_rows[
            "smart_construction_core.menu_sc_p1_income_settlement"
        ]
        expense_settlement = page_rows[
            "smart_construction_core.menu_sc_p1_expense_settlement"
        ]
        self.assertIn("收款登记", income_settlement["following"])
        self.assertNotIn("付款申请", income_settlement["following"])
        self.assertIn("付款申请", expense_settlement["following"])
        self.assertNotIn("收款登记", expense_settlement["following"])

    def test_cross_center_sources_and_review_gates_are_visible(self):
        markdown = builder.MARKDOWN_OUTPUT.read_text(encoding="utf-8")
        links = markdown.split("## 四、跨中心与跨分组衔接", 1)[1].split(
            "## 五、组织缺口清单", 1
        )[0]
        for row in self.payload["cross_center_links"]:
            self.assertIn(row["source_menu_xmlid"], links)
            self.assertIn(row["target_menu_xmlid"], links)
        gap_status = {row["id"]: row["status"] for row in self.payload["gaps"]}
        self.assertEqual(
            gap_status,
            {
                "GAP-01": "release_scope_change_required",
                "GAP-02": "resolved_reuse_existing_page",
                "GAP-03": "connection_fix_required",
                "GAP-04": "connection_fix_required",
                "GAP-05": "release_scope_or_connection_required",
            },
        )
        gates = markdown.split("## 定稿与实施门禁", 1)[1]
        self.assertIn("组织设计已定稿", gates)
        self.assertIn("候选种子与发布组合生成", gates)
        self.assertIn("可运行发布", gates)
        self.assertNotIn("组织缺口关闭前，不进入场景种子", gates)


if __name__ == "__main__":
    unittest.main()
