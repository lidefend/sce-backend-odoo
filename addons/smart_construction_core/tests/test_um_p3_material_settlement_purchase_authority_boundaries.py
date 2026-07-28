#!/usr/bin/env python3
from __future__ import annotations

import ast
import csv
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
MATERIAL = ROOT / "addons/smart_construction_core/models/core/material_acceptance.py"
PURCHASE = ROOT / "addons/smart_construction_core/models/core/purchase_extend.py"
ACL = ROOT / "addons/smart_construction_core/security/ir.model.access.csv"
RULES = ROOT / "addons/smart_construction_core/security/sc_record_rules.xml"
VIEWS = ROOT / "addons/smart_construction_core/views/core/material_acceptance_views.xml"


def class_source(path, class_name):
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
    return ast.get_source_segment(source, model) or "", methods


class TestUmP3MaterialSettlementPurchaseAuthorityBoundaries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.settlement, cls.settlement_methods = class_source(
            MATERIAL, "ScMaterialSettlement"
        )
        cls.line, cls.line_methods = class_source(
            MATERIAL, "ScMaterialSettlementLine"
        )
        cls.scope, cls.scope_methods = class_source(
            MATERIAL, "ScMaterialSettlementPurchaseScope"
        )
        cls.purchase, cls.purchase_methods = class_source(
            PURCHASE, "PurchaseOrder"
        )
        cls.purchase_line, cls.purchase_line_methods = class_source(
            PURCHASE, "PurchaseOrderLine"
        )

    def test_scope_is_explicit_line_grain_and_not_weak_reference(self):
        self.assertIn(
            '_name = "sc.material.settlement.purchase.scope"', self.scope
        )
        self.assertIn('"sc.material.settlement.line"', self.scope)
        self.assertIn('"purchase.order.line"', self.scope)
        for forbidden in ("res_model", "res_id", "fields.Many2many("):
            self.assertNotIn(forbidden, self.scope)

    def test_complete_set_projects_only_unique_project_supplier_and_order(self):
        method = self.settlement_methods["_sc_validate_purchase_authority"]
        self.assertIn('mapped("purchase_order_line_id")', method)
        self.assertIn("len(projects) != 1", method)
        self.assertIn("len(suppliers) != 1", method)
        self.assertIn("len(companies) != 1", method)
        self.assertIn("len(purchase_orders) == 1", method)
        self.assertIn('"purchase_order_id": False', method)

    def test_explicit_header_conflicts_are_rejected(self):
        method = self.settlement_methods["_sc_validate_purchase_authority"]
        for field in ("project_id", "supplier_id", "purchase_order_id"):
            self.assertIn(f'"{field}" in explicit_fields', method)
        self.assertGreaterEqual(method.count("raise ValidationError"), 6)

    def test_all_mutation_paths_revalidate_final_state(self):
        self.assertIn(
            "_sc_validate_purchase_authority", self.settlement_methods["create"]
        )
        self.assertIn(
            "sc_material_purchase_authority_batch",
            self.settlement_methods["write"],
        )
        for name in ("create", "write", "unlink"):
            self.assertIn(
                "_sc_validate_purchase_authority", self.scope_methods[name]
            )
        for methods in (self.purchase_methods, self.purchase_line_methods):
            self.assertIn(
                "_sc_validate_purchase_authority", methods["write"]
            )

    def test_destructive_parent_deletion_preserves_audit_relation(self):
        self.assertIn("purchase_scope_ids", self.settlement_methods["unlink"])
        self.assertIn("purchase_scope_ids", self.line_methods["unlink"])
        self.assertIn(
            "material_settlement_purchase_scope_ids",
            self.purchase_methods["unlink"],
        )
        self.assertIn(
            "material_settlement_purchase_scope_ids",
            self.purchase_line_methods["unlink"],
        )
        self.assertIn('ondelete="restrict"', self.scope)

    def test_relation_resolution_is_caller_scoped_and_nonheuristic(self):
        helper = self.scope_methods["_sc_caller_visible_relation"]
        combined = "".join(self.scope_methods.values())
        self.assertIn("self.env[model_name].search(", helper)
        for forbidden in (
            ".sudo(",
            ".browse(",
            ".exists(",
            "name_search",
            "ilike",
            "amount_total",
            "settlement_date",
            "create_date",
            "current",
        ):
            if forbidden == "current":
                continue
            self.assertNotIn(forbidden, combined)

    def test_acl_rules_and_view_use_minimal_material_boundary(self):
        with ACL.open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        scoped = [
            row
            for row in rows
            if row["model_id:id"]
            == "model_sc_material_settlement_purchase_scope"
        ]
        self.assertEqual(len(scoped), 3)
        rules = RULES.read_text(encoding="utf-8")
        views = VIEWS.read_text(encoding="utf-8")
        self.assertGreaterEqual(
            rules.count("model_sc_material_settlement_purchase_scope"), 3
        )
        self.assertIn("[('company_id', 'in', company_ids)", rules)
        self.assertIn('name="purchase_scope_ids"', views)
        self.assertIn('name="create_uid"', views)
        self.assertIn('name="create_date"', views)

    def test_no_historical_or_automatic_purchase_matching(self):
        combined = (
            self.settlement_methods["_sc_validate_purchase_authority"]
            + "".join(self.scope_methods.values())
        )
        for forbidden in (
            "name_search",
            "ilike",
            "amount_total",
            "settlement_date",
            "search_count",
            "current_active",
            "post_init",
        ):
            self.assertNotIn(forbidden, combined)


if __name__ == "__main__":
    unittest.main()
