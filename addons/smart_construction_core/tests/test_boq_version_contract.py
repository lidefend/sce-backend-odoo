# -*- coding: utf-8 -*-
import re
import uuid

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "sc_regression", "cost", "boq_version")
class TestBoqVersionContract(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls.env["project.project"].create({"name": "BOQ Version Contract"})
        cls.other_project = cls.env["project.project"].create({"name": "Other BOQ Project"})
        cls.uom = cls.env.ref("uom.product_uom_unit")

    def _version(self, code):
        return self.env["project.boq.version"].create(
            {
                "name": f"BOQ {code}",
                "code": code,
                "project_id": self.project.id,
                "source_type": "contract",
            }
        )

    def _line(self, version, code="010101001001", price=10.0):
        return self.env["project.boq.line"].create(
            {
                "project_id": self.project.id,
                "version_id": version.id,
                "code": code,
                "name": f"Line {code}",
                "uom_id": self.uom.id,
                "quantity": 2.0,
                "price": price,
                "line_type": "item",
            }
        )

    def test_import_version_default_contains_date_suffix(self):
        version_code = self.env["project.boq.import.wizard"].default_get(
            ["version_code"]
        )["version_code"]
        self.assertTrue(re.fullmatch(r"V1-\d{8}", version_code), version_code)

    def test_publish_supersede_restore_and_snapshot_immutability(self):
        first = self._version("V1")
        first_line = self._line(first)
        first.action_validate()
        first.action_publish()
        self.assertEqual(first.state, "published")
        self.assertEqual(first.total_amount, 20.0)
        self.assertFalse(first_line.work_id, "发布清单不得自动形成 WBS")
        work_count = self.env["construction.work.breakdown"].search_count(
            [("project_id", "=", self.project.id)]
        )
        action = first.action_open_wbs_planning()
        self.assertEqual(action["res_model"], "construction.work.breakdown")
        self.assertEqual(
            self.env["construction.work.breakdown"].search_count(
                [("project_id", "=", self.project.id)]
            ),
            work_count,
            "进入 WBS 计划不得从清单派生任何管理节点",
        )
        self.assertFalse(first_line.work_id)

        second = self._version("V2")
        self._line(second, code="010101001002", price=12.0)
        second.action_validate()
        second.action_publish()
        self.assertEqual(first.state, "superseded")
        self.assertEqual(first.replaced_by_id, second)
        self.assertEqual(second.previous_version_id, first)

        with self.assertRaises(UserError):
            first_line.write({"price": 99.0})
        with self.assertRaises(UserError):
            first_line.unlink()

        first.action_restore()
        self.assertEqual(first.state, "published")
        self.assertEqual(second.state, "superseded")

    def test_wbs_is_user_planned_and_can_group_independent_boq_items(self):
        version = self._version("WBS-PLAN")
        first = self._line(version, code="010101003001")
        second = self._line(version, code="020202004001")
        version.action_validate()
        version.action_publish()
        self.assertFalse(first.work_id | second.work_id)
        Work = self.env["construction.work.breakdown"]
        planned_root = Work.create(
            {
                "project_id": self.project.id,
                "name": "一期实施计划",
                "code": "PLAN-01",
                "level_type": "phase",
            }
        )
        planned_root.action_wbs_add_child()
        first_package = planned_root.child_ids
        first_package.write({"name": "公共区域提升工作包", "level_type": "work_package"})
        first_package.action_wbs_add_sibling()
        second_package = planned_root.child_ids - first_package
        self.assertEqual(second_package.parent_id, planned_root)
        second_package.action_wbs_indent()
        self.assertEqual(second_package.parent_id, first_package)
        second_package.action_wbs_outdent()
        self.assertEqual(second_package.parent_id, planned_root)
        self.assertFalse(first_package.can_move_up)
        self.assertTrue(first_package.can_move_down)
        self.assertFalse(first_package.can_indent)
        self.assertTrue(first_package.can_outdent)
        self.assertTrue(second_package.can_move_up)
        self.assertFalse(second_package.can_move_down)
        second_package.action_wbs_move_up()
        self.assertEqual(planned_root.child_ids.sorted(lambda rec: (rec.sequence, rec.id))[:1], second_package)
        self.assertFalse(second_package.can_move_up)
        self.assertTrue(second_package.can_move_down)

        floor = self.env["construction.location.breakdown"].create(
            {
                "project_id": self.project.id,
                "name": "地上一层",
                "code": "F01",
                "location_type": "floor",
            }
        )
        located_scope = self.env["construction.execution.scope"].create(
            {
                "project_id": self.project.id,
                "wbs_id": first_package.id,
                "location_id": floor.id,
                "source_type": "manual",
            }
        )
        Allocation = self.env["project.boq.allocation"]
        for line in first | second:
            Allocation.create(
                {
                    "boq_line_id": line.id,
                    "execution_scope_id": located_scope.id,
                    "allocation_basis": "ratio",
                    "allocation_ratio": 100.0,
                }
            )
        self.assertEqual(located_scope.allocation_ids.mapped("boq_line_id"), first | second)
        self.assertFalse(first.work_id | second.work_id, "BOQ 原结构不得被 WBS 管理结构改写")
        self.assertTrue(first.allocation_balanced)
        self.assertTrue(second.allocation_balanced)
        self.assertEqual(first_package.boq_line_count, 2)
        self.assertEqual(first_package.boq_amount_total, 40.0)

    def test_wbs_plan_lifecycle_preserves_published_version(self):
        Plan = self.env["construction.wbs.plan"]
        Work = self.env["construction.work.breakdown"]
        plan = Plan.create({
            "name": "项目管理 WBS",
            "version_code": "V9.0",
            "project_id": self.project.id,
        })
        root = Work.create({
            "project_id": self.project.id,
            "plan_id": plan.id,
            "name": "实施阶段",
            "code": "WBS-9",
            "level_type": "phase",
        })
        Work.create({
            "project_id": self.project.id,
            "plan_id": plan.id,
            "parent_id": root.id,
            "name": "施工工作包",
            "code": "WBS-9.1",
            "level_type": "work_package",
        })

        plan.action_validate_plan()
        self.assertEqual((plan.state, plan.validation_state), ("validated", "passed"))
        plan.action_publish_plan()
        self.assertEqual(plan.state, "published")
        with self.assertRaises(UserError):
            root.write({"name": "禁止修改已发布节点"})

        action = plan.action_start_adjustment()
        revision = Plan.search([("source_plan_id", "=", plan.id)], limit=1)
        self.assertTrue(revision)
        self.assertEqual((revision.version_code, revision.state), ("V9.1", "adjusting"))
        self.assertEqual(revision.node_count, 2)
        self.assertEqual(plan.state, "published")
        self.assertEqual(action["res_id"], revision.id)
        revision.node_ids.filtered(lambda node: node.code == "WBS-9.1").write({"name": "调整后的工作包"})

    def test_wbs_plan_failed_validation_remains_auditable(self):
        plan = self.env["construction.wbs.plan"].create({
            "name": "待完善 WBS",
            "version_code": "V8.0",
            "project_id": self.project.id,
        })

        self.assertFalse(plan.action_validate_plan())
        self.assertEqual((plan.state, plan.validation_state), ("draft", "failed"))
        self.assertIn("至少需要一个 WBS 节点", plan.validation_message)
        self.assertEqual(plan.validated_by_id, self.env.user)
        self.assertTrue(plan.validated_at)

    def test_boq_allocation_supports_quantity_amount_and_ratio_bases(self):
        version = self._version("ALLOCATION-BASES")
        line = self._line(version)
        version.action_validate()
        version.action_publish()
        work = self.env["construction.work.breakdown"].create(
            {
                "project_id": self.project.id,
                "name": "计划工作包",
                "code": "WP-01",
                "level_type": "work_package",
            }
        )
        initial_scope = self.env["construction.execution.scope"].create(
            {"project_id": self.project.id, "wbs_id": work.id, "source_type": "manual"}
        )
        generated = self.env["project.boq.allocation"].create(
            {
                "boq_line_id": line.id,
                "execution_scope_id": initial_scope.id,
                "allocation_basis": "ratio",
                "allocation_ratio": 100.0,
                "source_type": "manual",
            }
        )
        generated.write({"allocation_basis": "ratio", "allocation_ratio": 50.0})
        self.assertEqual(generated.allocated_quantity, 1.0)
        self.assertEqual(generated.allocated_amount, 10.0)

        floor = self.env["construction.location.breakdown"].create(
            {
                "project_id": self.project.id,
                "name": "二层",
                "code": "F02",
                "location_type": "floor",
            }
        )
        scope = self.env["construction.execution.scope"].create(
            {
                "project_id": self.project.id,
                "wbs_id": work.id,
                "location_id": floor.id,
                "source_type": "manual",
            }
        )
        by_quantity = self.env["project.boq.allocation"].create(
            {
                "boq_line_id": line.id,
                "execution_scope_id": scope.id,
                "allocation_basis": "quantity",
                "allocated_quantity": 1.0,
            }
        )
        self.assertEqual(by_quantity.allocated_amount, 10.0)
        self.assertEqual(by_quantity.allocation_ratio, 50.0)
        self.assertTrue(line.allocation_balanced)

        by_quantity.write({"allocation_basis": "amount", "allocated_amount": 5.0})
        self.assertEqual(by_quantity.allocated_quantity, 0.5)
        self.assertEqual(by_quantity.allocation_ratio, 25.0)
        generated.write({"allocation_ratio": 75.0})
        self.assertTrue(line.allocation_balanced)

    def test_line_and_import_batch_cannot_cross_project_or_version(self):
        first = self._version("V1-SCOPE")
        second = self._version("V2-SCOPE")
        parent = self._line(first, code="PARENT")
        with self.assertRaises(ValidationError):
            self.env["project.boq.line"].create(
                {
                    "project_id": self.project.id,
                    "version_id": second.id,
                    "parent_id": parent.id,
                    "code": "CHILD",
                    "name": "Cross-version child",
                    "uom_id": self.uom.id,
                }
            )
        with self.assertRaises(ValidationError):
            self.env["project.boq.import.batch"].create(
                {
                    "name": "Cross-project batch",
                    "project_id": self.other_project.id,
                    "version_id": first.id,
                    "filename": "boq.csv",
                    "file_digest": "deadbeef",
                }
            )

    def test_cost_user_can_evaluate_boq_freeze_without_finance_acl(self):
        cost_user = self.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "BOQ Cost Manager",
                "login": "boq_cost_manager",
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref(
                                "smart_construction_core.group_sc_cap_cost_manager"
                            ).id,
                        ],
                    )
                ],
            }
        )
        self.assertFalse(self.project.with_user(cost_user).is_boq_frozen())

        wizard = self.env["project.boq.import.wizard"].with_user(cost_user).create(
            {
                "project_id": self.project.id,
                "version_code": "ACL-UOM",
            }
        )
        unit_name = "boq-uom-" + uuid.uuid4().hex[:8]
        rows, created_uoms, skipped = wizard._build_rows_from_iter(
            [["010101001001", "ACL import line", unit_name, 1.0, 2.0, 2.0]],
            {
                "code": 0,
                "name": 1,
                "uom_id": 2,
                "quantity": 3,
                "price": 4,
                "amount": 5,
            },
        )
        self.assertEqual(skipped, 0)
        self.assertEqual(len(rows), 1)
        self.assertIn(unit_name, created_uoms)
        self.assertTrue(rows[0]["uom_id"])

    def test_boq_uom_aliases_and_missing_unit_use_business_item_unit(self):
        wizard = self.env["project.boq.import.wizard"].create(
            {"project_id": self.project.id, "version_code": "UOM-NORMALIZATION"}
        )
        self.assertEqual(wizard._canonical_uom("units"), "项")
        self.assertEqual(wizard._canonical_uom("item"), "项")

        rows, created_uoms, skipped = wizard._build_rows_from_iter(
            [["OTHER-001", "总价措施", "", 1.0, 20.0, 20.0]],
            {
                "code": 0,
                "name": 1,
                "uom_id": 2,
                "quantity": 3,
                "price": 4,
                "amount": 5,
            },
        )
        self.assertEqual(skipped, 0)
        self.assertEqual(len(rows), 1)
        self.assertEqual(
            self.env["uom.uom"].browse(rows[0]["uom_id"]).name,
            "项",
        )
        self.assertNotIn("Units", created_uoms)

    def test_xls_container_diagnostics_are_deduplicated_for_preflight(self):
        normalize = self.env["project.boq.import.wizard"]._normalize_xls_diagnostics
        diagnostics = normalize(
            "WARNING *** file size is inconsistent\n"
            "WARNING *** SSAT size is inconsistent\n"
            "WARNING *** file size is inconsistent\n"
        )
        self.assertEqual(
            diagnostics,
            [
                "WARNING *** file size is inconsistent",
                "WARNING *** SSAT size is inconsistent",
            ],
        )

    def test_engineering_header_supports_label_and_value_in_adjacent_cells(self):
        Wizard = self.env["project.boq.import.wizard"]
        payload = Wizard._engineering_header_payload(
            "工程名称：",
            ["", "建设项目 \\单项工程 【市政工程】", "标段："],
        )
        self.assertEqual(
            Wizard._split_engineering_header(payload),
            ("建设项目", "单项工程", "市政工程"),
        )

    def test_source_rows_keep_values_and_calculate_independent_comparison(self):
        wizard = self.env["project.boq.import.wizard"].create(
            {"project_id": self.project.id, "version_code": "SOURCE-COMPARE"}
        )
        version = self._version("SOURCE-COMPARE")
        item = self._line(version, price=10.005)
        item.write({"has_imported_amount": True, "imported_amount": 20.02, "calculated_amount": 20.01})
        subtotal = self.env["project.boq.line"].create(
            {
                "project_id": self.project.id,
                "version_id": version.id,
                "code": "SUMMARY-01",
                "name": "分部小计",
                "uom_id": self.uom.id,
                "line_type": "group",
                "source_row_type": "subtotal",
                "has_imported_amount": True,
                "imported_amount": 20.02,
            }
        )
        wizard._finalize_source_summary_calculations(item | subtotal)
        self.assertAlmostEqual(item.calculated_amount, 20.01, places=2)
        self.assertAlmostEqual(item.amount_variance, 0.01, places=2)
        self.assertAlmostEqual(subtotal.calculated_amount, 20.01, places=2)
        self.assertAlmostEqual(subtotal.amount_variance, 0.01, places=2)
        self.assertEqual(subtotal.calculation_scope_item_count, 1)

    def test_standard_unit_price_analysis_parser_keeps_norm_and_resource_facts(self):
        wizard = self.env["project.boq.import.wizard"].create(
            {"project_id": self.project.id, "version_code": "ANALYSIS-PARSER"}
        )
        rows = [
            ["项目编码", "(1) 010101001001", "", "项目名称", "", "基底钎探", "", "计量单位", "", "㎡", "", "工程量", "", 1294.84],
            ["定额编号", "定额项目名称", "定额单位", "数量", "单价", "", "", "", "", "合价", "", "", "", ""],
            ["", "", "", "", "人工费", "材料费", "机械费", "管理费", "利润", "人工费", "材料费", "机械费", "管理费", "利润"],
            ["AA0096换", "基底钎探", "100㎡", 0.01, 363.45, 91.42, 0, 15.74, 35.02, 3.63, 0.91, 0, 0.16, 0.35],
            ["清单项目综合单价", "", "", "", "", "", "", "", "", 5.06, "", "", "", ""],
            ["材\n料\n费\n明\n细", "主要材料名称、规格、型号", "", "", "", "", "", "单位", "数量", "单价（元）", "合价（元）", "暂估单价（元）", "", "暂估合价（元）"],
            ["", "钢钎 φ22～25", "", "", "", "", "", "kg", 0.082, 3.99, 0.33, "", "", ""],
            ["", "其他材料费", "", "", "", "", "", "", "", "-", 0.58, "-", "", ""],
            ["", "材料费小计", "", "", "", "", "", "", "-", "-", 0.91, "-", "", ""],
        ]
        analyses = wizard._parse_analysis_rows(
            rows,
            source_sheet_index=7,
            source_sheet_name="F.2.1 分部分项工程清单综合单价分析表",
            single_name="消防站项目",
            unit_name="消防站",
            major_name="建筑与装饰工程",
        )
        self.assertEqual(len(analyses), 1)
        analysis = analyses[0]
        self.assertEqual(analysis["boq_code"], "010101001001")
        self.assertEqual(analysis["source_unit_price"], 5.06)
        self.assertEqual(len(analysis["norm_lines"]), 1)
        self.assertEqual(analysis["norm_lines"][0]["norm_code"], "AA0096换")
        self.assertEqual(len(analysis["resource_lines"]), 2)
        self.assertEqual(analysis["resource_lines"][0]["budget_consumption"], 0.082)
        self.assertEqual(analysis["resource_lines"][1]["budget_unit_price"], 0.58)

    def test_published_analysis_generates_editable_versioned_cost_plan(self):
        version = self._version("COST-PLAN-SOURCE")
        line = self._line(version)
        analysis = self.env["project.boq.analysis"].create(
            {
                "name": line.name,
                "boq_line_id": line.id,
                "uom_raw": "m2",
                "source_quantity": 2.0,
                "source_unit_price": 10.0,
                "norm_line_ids": [
                    (
                        0,
                        0,
                        {
                            "norm_code": "AA0001",
                            "name": "测试定额",
                            "unit_raw": "100m2",
                            "budget_consumption": 0.01,
                            "amount_labor": 3.0,
                            "amount_material": 2.0,
                            "amount_machine": 2.0,
                            "amount_overhead": 0.5,
                            "amount_profit": 0.5,
                        },
                    )
                ],
                "resource_line_ids": [
                    (
                        0,
                        0,
                        {
                            "resource_type": "material",
                            "name": "测试材料",
                            "unit_raw": "kg",
                            "budget_consumption": 0.5,
                            "budget_unit_price": 4.0,
                            "budget_unit_amount": 2.0,
                        },
                    )
                ],
            }
        )
        version.action_validate()
        version.action_publish()
        with self.assertRaises(UserError):
            analysis.write({"source_unit_price": 11.0})

        plan = self.env["project.cost.plan"].create(
            {
                "name": "首版目标成本",
                "project_id": self.project.id,
                "boq_version_id": version.id,
                "version_code": "V1",
            }
        )
        plan.action_generate_from_boq()
        self.assertEqual(plan.line_count, 4)
        material = plan.line_ids.filtered(lambda rec: rec.cost_type == "material")
        self.assertEqual(material.budget_quantity, 1.0)
        self.assertEqual(material.budget_amount, 4.0)
        material.write({"target_unit_consumption": 0.4, "target_unit_price": 3.5})
        self.assertEqual(material.target_quantity, 0.8)
        self.assertAlmostEqual(material.target_amount, 2.8)
        line_action = plan.action_open_lines()
        self.assertEqual(line_action["res_model"], "project.cost.plan.line")
        self.assertEqual(line_action["domain"], [("plan_id", "=", plan.id)])
        self.assertEqual(line_action["context"]["default_plan_id"], plan.id)
        plan.action_validate()
        plan.action_publish()
        self.assertEqual(plan.state, "published")
        with self.assertRaises(UserError):
            material.write({"target_unit_price": 3.0})
        action = plan.action_start_adjustment()
        revision = self.env["project.cost.plan"].browse(action["res_id"])
        self.assertEqual(revision.state, "adjusting")
        self.assertEqual(revision.source_plan_id, plan)
        self.assertEqual(revision.line_count, plan.line_count)
        revision.line_ids.filtered(lambda rec: rec.cost_type == "material").target_unit_price = 3.0

    def test_fee_detail_is_preserved_without_double_count_and_enters_cost_plan(self):
        wizard = self.env["project.boq.import.wizard"].create(
            {"project_id": self.project.id, "version_code": "FEE-SOURCE"}
        )
        rows, _created_uoms, skipped = wizard._build_rows_from_iter(
            [
                ["1", "安全文明施工费", "分部分项人工费", 3.0, 300.0],
                ["①", "环境保护费", "分部分项人工费", 0.5, 50.0],
            ],
            {"code": 0, "name": 1, "calc_base": 2, "rate": 3, "amount": 4},
            boq_category="total_measure",
            sheet_index=9,
        )
        self.assertEqual(skipped, 0)
        self.assertEqual(len(rows), 2)
        self.assertFalse(rows[0].get("is_calculation_detail"))
        self.assertTrue(rows[1]["is_calculation_detail"])
        self.assertEqual(rows[1]["source_calc_base"], "分部分项人工费")
        self.assertEqual(rows[1]["source_rate"], 0.5)

        version = self._version("FEE-COST-PLAN")
        for values in rows:
            values.update({"version_id": version.id})
        source_lines = self.env["project.boq.line"].create(rows)
        self.assertEqual(sum(source_lines.mapped("amount_leaf")), 300.0)
        self.env["project.boq.summary.component"].create(
            {
                "version_id": version.id,
                "code": "7",
                "name": "销项增值税额",
                "component_type": "tax",
                "amount": 27.0,
                "source_sheet_name": "E.3 单位工程汇总表",
            }
        )
        version.action_validate()
        version.action_publish()
        plan = self.env["project.cost.plan"].create(
            {
                "name": "费用目标成本",
                "project_id": self.project.id,
                "boq_version_id": version.id,
                "version_code": "FEE-V1",
            }
        )
        plan.action_generate_from_boq()
        self.assertEqual(plan.line_count, 2)
        measure = plan.line_ids.filtered(lambda line: line.cost_type == "measure")
        tax = plan.line_ids.filtered(lambda line: line.cost_type == "tax")
        self.assertEqual(measure.calculation_mode, "rate")
        self.assertEqual(tax.budget_amount, 27.0)
        measure.target_rate = 2.7
        self.assertAlmostEqual(measure.target_amount, 270.0)

    def test_unit_project_summary_parser_keeps_fee_and_tax_outside_boq_rows(self):
        wizard = self.env["project.boq.import.wizard"].create(
            {"project_id": self.project.id, "version_code": "E3-SUMMARY"}
        )
        rows = [
            ["序号", "汇总内容", "金额（元）", "其中暂估价"],
            ["4", "规费", 480693.75, "-"],
            ["6", "税前不含税工程造价", 24781859.36, "-"],
            ["7", "销项增值税额", 2230367.34, "-"],
            ["8", "附加税", 77567.22, "-"],
            ["招标控制价/投标报价总价合计=税前不含税工程造价+销项增值税额+附加税", 27089793.92],
        ]
        parsed = wizard._parse_unit_summary_rows(
            rows,
            source_sheet_index=3,
            source_sheet_name="E.3 单位工程招标控制价投标报价汇总表",
            single_name="消防站项目",
            unit_name="消防站",
            major_name="建筑与装饰工程",
        )
        self.assertEqual(
            [row["component_type"] for row in parsed],
            ["fee", "pre_tax", "tax", "tax", "total"],
        )
        self.assertAlmostEqual(parsed[-1]["amount"], 27089793.92)
        self.assertAlmostEqual(parsed[2]["source_rate"], 9.0, places=4)

    def test_short_numeric_source_code_remains_a_priced_item(self):
        wizard = self.env["project.boq.import.wizard"].create(
            {"project_id": self.project.id, "version_code": "SHORT-CODE"}
        )
        version = self._version("SHORT-CODE")
        values = {
            "project_id": self.project.id,
            "version_id": version.id,
            "code": "001196",
            "source_code": "001196",
            "name": "车泵增加费",
            "uom_id": self.uom.id,
            "quantity": 1.0,
            "price": 12.0,
            "has_imported_amount": True,
            "imported_amount": 12.0,
            "source_row_type": "item",
            "boq_category": "boq",
        }
        wizard._create_with_hierarchy(self.env["project.boq.line"], [values])
        line = version.line_ids
        self.assertEqual(line.line_type, "item")
        self.assertEqual(line.amount_leaf, 12.0)

    def test_other_project_level_one_amount_is_a_cost_item_not_a_heading(self):
        wizard = self.env["project.boq.import.wizard"].create(
            {"project_id": self.project.id, "version_code": "OTHER-AMOUNT"}
        )
        rows, skipped = wizard._build_rows_other(
            [["1", "暂列金额", 1157198.36], ["2", "暂估价", ""]],
            sheet_index=10,
            sheet_name="G.1 其他项目清单与计价汇总表",
        )
        self.assertEqual(skipped, 0)
        self.assertEqual(rows[0]["line_type"], "item")
        self.assertEqual(rows[0]["source_row_type"], "item")
        self.assertTrue(rows[0]["has_imported_amount"])
        self.assertEqual(rows[0]["imported_amount"], 1157198.36)
        self.assertEqual(rows[1]["line_type"], "group")
