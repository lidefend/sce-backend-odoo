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
        first.action_generate_wbs_draft()
        first_work = first_line.work_id
        self.assertEqual(first_work.level_type, "sub_section")

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

    def test_wbs_draft_groups_boq_items_and_preserves_user_planning(self):
        version = self._version("WBS-DRAFT")
        first = self._line(version, code="010101003001")
        second = self._line(version, code="010101003002")
        version.action_validate()
        version.action_publish()
        self.assertFalse(first.work_id | second.work_id)

        version.action_generate_wbs_draft()
        self.assertEqual(first.work_id, second.work_id)
        self.assertEqual(first.work_id.level_type, "sub_section")
        self.assertEqual(len(first.work_id.boq_line_ids.filtered(lambda line: line.version_id == version)), 2)
        self.assertEqual(len(first.allocation_ids), 1)
        self.assertEqual(len(second.allocation_ids), 1)
        self.assertTrue(first.allocation_balanced)
        self.assertTrue(second.allocation_balanced)

        planned_parent = self.env["construction.work.breakdown"].create(
            {
                "project_id": self.project.id,
                "name": "现场确认的工作包分组",
                "code": "PLAN-01",
                "level_type": "other",
                "source_type": "manual",
                "placement_mode": "planned",
            }
        )
        first.work_id.write({"parent_id": planned_parent.id})
        self.assertEqual(first.work_id.placement_mode, "planned")
        version.action_generate_wbs_draft()
        self.assertEqual(first.work_id.parent_id, planned_parent, "同步不得覆盖用户规划位置")

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
                "wbs_id": first.work_id.id,
                "location_id": floor.id,
                "source_type": "manual",
            }
        )
        first.allocation_ids.write({"execution_scope_id": located_scope.id})
        self.assertEqual(first.allocation_ids.execution_scope_id.location_id, floor)
        self.assertEqual(first.allocation_ids.boq_line_id, first)
        self.assertTrue(first.allocation_balanced)

    def test_boq_allocation_supports_quantity_amount_and_ratio_bases(self):
        version = self._version("ALLOCATION-BASES")
        line = self._line(version)
        version.action_validate()
        version.action_publish()
        version.action_generate_wbs_draft()
        generated = line.allocation_ids
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
                "wbs_id": line.work_id.id,
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
