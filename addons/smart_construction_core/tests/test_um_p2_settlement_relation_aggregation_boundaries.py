#!/usr/bin/env python3
from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SETTLEMENT = ROOT / "addons/smart_construction_core/models/core/settlement_order.py"
MATERIAL = ROOT / "addons/smart_construction_core/models/core/material_acceptance.py"


def class_methods(path, class_name):
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    model = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == class_name
    )
    methods = {
        node.name: ast.get_source_segment(source, node) or ""
        for node in model.body
        if isinstance(node, ast.FunctionDef)
    }
    return source, methods


class TestUmP2SettlementRelationAggregationBoundaries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.header_source, cls.header_methods = class_methods(
            SETTLEMENT, "ScSettlementOrder"
        )
        cls.line_source, cls.line_methods = class_methods(
            SETTLEMENT, "ScSettlementOrderLine"
        )
        cls.material_header_source, _methods = class_methods(
            MATERIAL, "ScMaterialSettlement"
        )
        cls.material_line_source, _methods = class_methods(
            MATERIAL, "ScMaterialSettlementLine"
        )

    def test_complete_detail_set_is_the_contract_authority(self):
        method = self.header_methods["_synchronize_detail_contract_projection"]
        self.assertIn('lines.filtered("contract_id")', method)
        self.assertIn("set(contracts.ids) != contract_ids", method)
        self.assertIn("len(contracts) == 1", method)
        self.assertIn('updates["contract_id"] = projected_contract', method)
        self.assertIn("显式头部合同与完整结算明细合同集合冲突", method)

    def test_multi_contract_projection_is_empty_not_first_match(self):
        method = self.header_methods["_synchronize_detail_contract_projection"]
        self.assertIn(
            "unique_contract = contracts if len(contracts) == 1 else contracts[:0]",
            method,
        )
        self.assertNotIn("limit=1", method)
        for token in ("sorted(", "max(", "invoice_no", "amount_total", "order="):
            self.assertNotIn(token, method)

    def test_header_default_is_limited_to_existing_unique_projection(self):
        create = self.line_methods["create"]
        self.assertIn("not vals.get(\"contract_id\") and settlement.contract_id", create)
        self.assertIn('vals["contract_id"] = settlement.contract_id.id', create)
        self.assertIn("_ensure_contract_required", create)

    def test_header_and_direct_line_mutations_revalidate_final_state(self):
        header_create = self.header_methods["create"]
        header_write = self.header_methods["write"]
        line_create = self.line_methods["create"]
        line_write = self.line_methods["write"]
        line_unlink = self.line_methods["unlink"]
        self.assertIn("_synchronize_detail_contract_projection", header_create)
        self.assertIn("_synchronize_detail_contract_projection", header_write)
        self.assertIn("_synchronize_detail_contract_projection", line_create)
        self.assertIn("_synchronize_detail_contract_projection", line_write)
        self.assertIn("_synchronize_detail_contract_projection", line_unlink)

    def test_relation_reads_are_caller_scoped(self):
        helper = self.header_methods["_caller_visible_settlement_relation"]
        line_match = self.line_methods["_ensure_contract_match"]
        line_create = self.line_methods["create"]
        combined = helper + line_match + line_create
        self.assertIn("self.env[model_name].search(", helper)
        self.assertIn('self.env["construction.contract"].search(', line_match)
        self.assertIn('self.env["sc.settlement.order"].search(', line_create)
        for forbidden in (".sudo(", ".browse(", ".exists(", "ilike", "name_search"):
            self.assertNotIn(forbidden, combined)

    def test_project_company_type_and_counterparty_are_consistent(self):
        method = self.header_methods["_synchronize_detail_contract_projection"]
        self.assertIn("contract.project_id != order.project_id", method)
        self.assertIn("contract.company_id != order.company_id", method)
        self.assertIn("contract.type != expected_type", method)
        self.assertIn("len(counterparties) > 1", method)
        self.assertIn("order.partner_id != counterparty", method)

    def test_legacy_missing_contract_is_not_backfilled_or_inferred(self):
        method = self.header_methods["_synchronize_detail_contract_projection"]
        self.assertIn("missing_lines and not order.legacy_fact_model", method)
        self.assertIn("if not contract_ids:", method)
        for token in ("legacy_contract_no", "legacy_counterparty_name", "name_search"):
            self.assertNotIn(token, method)

    def test_material_settlement_has_no_contract_bearing_detail(self):
        self.assertNotIn("contract_id = fields.Many2one", self.material_header_source)
        self.assertNotIn("contract_id = fields.Many2one", self.material_line_source)
        self.assertIn(
            'purchase_order_id = fields.Many2one("purchase.order"',
            self.material_header_source,
        )
        self.assertIn(
            'supplier_id = fields.Many2one("res.partner"',
            self.material_header_source,
        )


if __name__ == "__main__":
    unittest.main()
