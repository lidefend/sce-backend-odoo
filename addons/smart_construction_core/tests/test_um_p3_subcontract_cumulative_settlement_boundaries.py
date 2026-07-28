# -*- coding: utf-8 -*-
import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
MODEL = (
    ROOT
    / "addons/smart_construction_core/models/core/subcontract_management.py"
)


def class_source(class_name):
    source = MODEL.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(MODEL))
    node = next(
        item
        for item in tree.body
        if isinstance(item, ast.ClassDef) and item.name == class_name
    )
    methods = {
        item.name: ast.get_source_segment(source, item) or ""
        for item in node.body
        if isinstance(item, ast.FunctionDef)
    }
    return ast.get_source_segment(source, node) or "", methods


class TestUmP3SubcontractCumulativeSettlementBoundaries(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.register_line, cls.register_line_methods = class_source(
            "ScSubcontractRegisterLine"
        )
        cls.settlement, cls.settlement_methods = class_source(
            "ScSubcontractSettlement"
        )
        cls.settlement_line, cls.settlement_line_methods = class_source(
            "ScSubcontractSettlementLine"
        )

    def test_quantity_uses_formal_precision_and_only_confirmed_state(self):
        method = self.settlement_methods[
            "_sc_validate_cumulative_registered_quantities"
        ]
        self.assertIn("float_compare(", method)
        self.assertIn('"Product Unit of Measure"', method)
        self.assertIn('settlement.state = %s', method)
        self.assertIn('[register_line_ids, "confirmed"]', method)
        self.assertIn(
            'digits="Product Unit of Measure"', self.register_line
        )
        self.assertIn(
            'digits="Product Unit of Measure"', self.settlement_line
        )

    def test_register_line_lock_precedes_complete_database_aggregate(self):
        method = self.settlement_methods[
            "_sc_validate_cumulative_registered_quantities"
        ]
        lock_position = method.index("FOR UPDATE")
        aggregate_position = method.index("COALESCE(SUM(line.qty)")
        self.assertLess(lock_position, aggregate_position)
        self.assertIn("ORDER BY id", method)
        self.assertIn("line.register_line_id IN %s", method)
        self.assertIn('error.pgcode == "40001"', method)
        self.assertIn("请刷新后按最新剩余数量重试", method)

    def test_exact_free_text_unit_is_required_without_invented_conversion(self):
        method = self.settlement_methods[
            "_sc_validate_cumulative_registered_quantities"
        ]
        self.assertIn("not register_line.unit_name", method)
        self.assertIn(
            "settlement_unit != register_line.unit_name", method
        )
        for forbidden in (
            "_compute_quantity",
            "uom.uom",
            "unit_name.lower(",
            "unit_name.strip(",
        ):
            self.assertNotIn(forbidden, method)

    def test_all_mutation_paths_revalidate_final_quantity_state(self):
        for method_name in ("create", "write"):
            self.assertIn(
                "_sc_validate_cumulative",
                self.settlement_methods[method_name],
            )
            self.assertIn(
                "_sc_validate_cumulative",
                self.settlement_line_methods[method_name],
            )
        self.assertIn(
            "_sc_validate_cumulative",
            self.register_line_methods["write"],
        )

    def test_amount_and_historical_inference_remain_outside_hard_limit(self):
        method = self.settlement_methods[
            "_sc_validate_cumulative_registered_quantities"
        ]
        for forbidden in (
            "registered_amount",
            "amount_total",
            "amount_untaxed",
            "tax_amount",
            "name_search",
            "ilike",
            "settlement_date",
            "register_date",
            ".sudo(",
        ):
            self.assertNotIn(forbidden, method)


if __name__ == "__main__":
    unittest.main()
