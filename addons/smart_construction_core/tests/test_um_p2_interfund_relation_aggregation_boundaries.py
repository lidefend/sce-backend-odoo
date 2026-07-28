#!/usr/bin/env python3
from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
OPERATION = ROOT / "addons/smart_construction_core/models/core/fund_account_operation.py"
FACT = ROOT / "addons/smart_construction_core/models/projection/interfund_movement_fact.py"
POSITION = (
    ROOT
    / "addons/smart_construction_core/models/projection/"
    "finance_project_counterparty_position.py"
)


def class_methods(path, class_name):
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    class_node = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == class_name
    )
    return source, {
        node.name: node
        for node in class_node.body
        if isinstance(node, ast.FunctionDef)
    }


class TestUmP2InterfundRelationAggregationBoundaries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.operation_source, cls.methods = class_methods(
            OPERATION,
            "ScFundAccountOperation",
        )
        cls.fact_source = FACT.read_text(encoding="utf-8")
        cls.position_source = POSITION.read_text(encoding="utf-8")

    def _method(self, name):
        return ast.get_source_segment(
            self.operation_source,
            self.methods[name],
        )

    def test_account_relations_are_caller_scoped_and_company_bound(self):
        source = self._method("_caller_visible_fund_account")
        self.assertIn('self.env["sc.fund.account"].search(', source)
        self.assertIn('("company_id", "=", company_id)', source)
        self.assertIn('("project_id.company_id", "=", company_id)', source)
        for forbidden in (".sudo(", ".browse(", ".exists(", "name_search", "ilike"):
            self.assertNotIn(forbidden, source)

    def test_create_and_write_validate_both_transfer_endpoints(self):
        normalizer = self._method("_normalize_fund_relation_values")
        self.assertIn('relation_id("source_account_id")', normalizer)
        self.assertIn('relation_id("target_account_id")', normalizer)
        for method_name in ("create", "write"):
            self.assertIn(
                "_normalize_fund_relation_values",
                self._method(method_name),
            )

    def test_fact_projects_are_derived_from_account_endpoints(self):
        self.assertIn("src.project_id AS source_project_id", self.fact_source)
        self.assertIn("dst.project_id AS target_project_id", self.fact_source)
        self.assertIn("op.source_account_id", self.fact_source)
        self.assertIn("op.target_account_id", self.fact_source)
        self.assertIn("NULL::integer AS partner_id", self.fact_source)
        self.assertIn("NULL::varchar AS partner_name", self.fact_source)

    def test_counterparty_is_the_opposite_project_company_or_internal_scope(self):
        self.assertIn(
            "f.target_project_id AS counterparty_project_id",
            self.position_source,
        )
        self.assertIn(
            "f.source_project_id AS counterparty_project_id",
            self.position_source,
        )
        self.assertIn("THEN 'company'", self.position_source)
        self.assertIn("'internal' AS counterparty_type", self.position_source)
        self.assertNotIn("name_search(", self.position_source)


if __name__ == "__main__":
    unittest.main()
