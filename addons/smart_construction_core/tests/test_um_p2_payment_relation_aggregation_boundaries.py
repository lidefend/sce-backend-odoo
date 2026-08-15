#!/usr/bin/env python3
from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
EXECUTION = ROOT / "addons/smart_construction_core/models/core/payment_execution.py"
REQUEST = ROOT / "addons/smart_construction_core/models/core/payment_request.py"
LINE = ROOT / "addons/smart_construction_core/models/core/payment_request_line.py"


def methods(path, class_name):
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    model = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == class_name
    )
    return source, {
        node.name: node
        for node in model.body
        if isinstance(node, ast.FunctionDef)
    }


class TestUmP2PaymentRelationAggregationBoundaries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source, cls.execution_methods = methods(EXECUTION, "ScPaymentExecution")
        cls.request_source, cls.request_methods = methods(REQUEST, "PaymentRequest")
        cls.line_source, cls.line_methods = methods(LINE, "PaymentRequestLine")

    def _source(self, name):
        return ast.get_source_segment(self.source, self.execution_methods[name])

    def test_basis_set_is_built_before_unique_contract_selection(self):
        source = self._source("_payment_basis_contracts")
        self.assertIn('"payment.request.line"', source)
        self.assertIn('"settlement_id"', source)
        self.assertIn('"contract_id"', source)
        self.assertIn("line.settlement_id", source)
        self.assertIn("line.contract_id", source)
        self.assertIn("len(contracts) > 1", source)
        self.assertIn("多合同付款申请不得压缩到单值合同字段", source)

    def test_detail_set_is_authoritative_and_header_conflicts_fail(self):
        source = self._source("_payment_basis_contracts")
        self.assertIn("if lines:", source)
        self.assertIn("request.material_settlement_id", source)
        self.assertIn("request.settlement_id.id not in line_settlement_ids", source)
        self.assertNotIn("sorted(", source)
        self.assertNotIn("order=", source)
        self.assertNotIn("limit=1", source)

    def test_explicit_request_contract_is_a_valid_standalone_basis(self):
        source = self._source("_payment_basis_contracts")
        self.assertIn("if not contracts:", source)
        self.assertIn("contracts |= request_contract", source)
        self.assertIn("if request_contract != contracts:", source)

    def test_execution_contract_is_written_only_for_unique_basis(self):
        source = self._source("_normalize_payment_relation_values")
        unique_branch = source.index("if len(contracts) == 1:")
        multi_branch = source.index("elif len(contracts) > 1:")
        self.assertLess(unique_branch, multi_branch)
        self.assertIn('values.setdefault("contract_id", unique_contract.id)', source)
        self.assertIn('values["contract_id"] = False', source)
        self.assertIn("多合同付款依据不得写入任意单一执行合同", source)

    def test_actual_payee_is_independent_and_never_rewrites_application(self):
        source = self._source("_normalize_payment_relation_values")
        self.assertIn('actual_payee_id = relation_id("partner_id")', source)
        self.assertIn('"res.partner", actual_payee_id', source)
        self.assertIn('values.setdefault("partner_id", request.partner_id.id)', source)
        self.assertNotIn("request.write(", source)
        scope_source = self._source("_check_payment_request_scope_or_raise")
        self.assertNotIn("request.partner_id", scope_source)

    def test_all_business_relation_reads_are_caller_scoped_searches(self):
        helper = self._source("_caller_visible_payment_relation")
        combined = (
            self._source("_payment_basis_contracts")
            + self._source("_normalize_payment_relation_values")
            + self._source("create")
        )
        self.assertIn("self.env[model_name].search(", helper)
        for forbidden in (".sudo(", ".browse(", ".exists(", "ilike", "name_search"):
            self.assertNotIn(forbidden, helper + combined)

    def test_request_and_line_mutations_revalidate_linked_executions(self):
        request_constraint = ast.get_source_segment(
            self.request_source,
            self.request_methods["_check_payment_execution_basis_contract"],
        )
        line_constraint = ast.get_source_segment(
            self.line_source,
            self.line_methods["_check_payment_basis_relation"],
        )
        for source in (request_constraint, line_constraint):
            self.assertIn("_payment_basis_contracts(request)", source)
            self.assertIn("_normalize_payment_relation_values({}, current=execution)", source)

    def test_existing_execution_relation_anchors_are_immutable(self):
        guard = self._source("_assert_payment_relation_anchors_immutable")
        write = self._source("write")
        for field_name in ("payment_request_id", "contract_id", "partner_id", "project_id"):
            self.assertIn(field_name, guard)
        self.assertIn('self.env.context.get("history_surface_sync")', guard)
        self.assertIn("self.env.su", guard)
        self.assertIn('rec.source_origin == "legacy"', guard)
        self.assertIn("not current_id", guard)
        self.assertIn("incoming_id", guard)
        self.assertGreaterEqual(write.count("_assert_payment_relation_anchors_immutable"), 2)


if __name__ == "__main__":
    unittest.main()
