#!/usr/bin/env python3
from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
MODEL = ROOT / "addons/smart_construction_core/models/core/receipt_income.py"


class TestUmP2ReceiptRelationAggregationBoundaries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = MODEL.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source, filename=str(MODEL))
        cls.model = next(
            node
            for node in cls.tree.body
            if isinstance(node, ast.ClassDef)
            and any(
                isinstance(statement, ast.Assign)
                and any(
                    isinstance(target, ast.Name) and target.id == "_name"
                    for target in statement.targets
                )
                and ast.literal_eval(statement.value) == "sc.receipt.income"
                for statement in node.body
            )
        )
        cls.methods = {
            node.name: node
            for node in cls.model.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }

    def _method_source(self, name):
        return ast.get_source_segment(self.source, self.methods[name])

    def test_relation_authority_chain_is_explicit(self):
        source = self._method_source("_normalize_receipt_relation_values")
        self.assertIn('"payment_request_id"', source)
        self.assertIn('"payment.request"', source)
        self.assertIn('[("type", "=", "receive")]', source)
        self.assertIn("request.contract_id", source)
        self.assertIn("request.contract_id.partner_id", source)
        self.assertIn('"construction.contract"', source)
        self.assertIn('[("type", "=", "out")]', source)
        self.assertIn("contract.partner_id", source)
        self.assertIn('values.setdefault("contract_id"', source)
        self.assertIn('values.setdefault("partner_id"', source)

    def test_caller_scoped_search_precedes_all_relation_reads(self):
        helper = self._method_source("_caller_visible_relation_record")
        normalizer = self._method_source("_normalize_receipt_relation_values")
        self.assertIn("self.env[model_name].search(", helper)
        self.assertNotIn(".sudo(", helper)
        self.assertNotIn(".browse(", helper)
        self.assertNotIn(".exists(", helper)
        self.assertNotIn(".sudo(", normalizer)
        self.assertNotIn(".browse(", normalizer)
        self.assertNotIn(".exists(", normalizer)

    def test_create_and_write_share_the_same_server_side_validator(self):
        create_source = self._method_source("create")
        write_source = self._method_source("write")
        self.assertIn("_normalize_receipt_relation_values(vals)", create_source)
        self.assertIn(
            "_normalize_receipt_relation_values(vals, current=rec)",
            write_source,
        )
        self.assertLess(
            create_source.index("_normalize_receipt_relation_values(vals)"),
            create_source.index("super().create("),
        )
        self.assertLess(
            write_source.index("_normalize_receipt_relation_values(vals, current=rec)"),
            write_source.index("super(ScReceiptIncome, rec).write("),
        )

    def test_no_heuristic_relation_matching_is_introduced(self):
        source = self._method_source("_normalize_receipt_relation_values")
        forbidden = (
            "ilike",
            "name_search",
            "search_count",
            "amount",
            "date_receipt",
            "note",
            "order=",
        )
        for token in forbidden:
            self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
