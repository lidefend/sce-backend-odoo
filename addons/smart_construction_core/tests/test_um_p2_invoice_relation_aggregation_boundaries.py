#!/usr/bin/env python3
from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
INVOICE = ROOT / "addons/smart_construction_core/models/core/invoice_registration.py"
RECEIPT_LINE = ROOT / "addons/smart_construction_core/models/core/receipt_invoice_line.py"
DEDUCTION = ROOT / "addons/smart_construction_core/models/core/tax_deduction_registration.py"


def model_methods(path, class_name):
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


class TestUmP2InvoiceRelationAggregationBoundaries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.invoice_source, cls.invoice_methods = model_methods(
            INVOICE, "ScInvoiceRegistration"
        )
        cls.line_source, cls.line_methods = model_methods(
            RECEIPT_LINE, "ReceiptInvoiceLine"
        )
        cls.deduction_source = DEDUCTION.read_text(encoding="utf-8")

    def _invoice_method(self, name):
        return ast.get_source_segment(
            self.invoice_source, self.invoice_methods[name]
        )

    def _line_method(self, name):
        return ast.get_source_segment(self.line_source, self.line_methods[name])

    def test_exact_source_kinds_have_type_specific_dispatch(self):
        policy = self._invoice_method("_invoice_relation_policy")
        for source_kind in (
            "invoice_registration",
            "input_invoice_tax",
            "output_invoice_tax",
            "prepaid_tax",
        ):
            self.assertIn(source_kind, self.invoice_source)
        self.assertIn('source_kind == "input_invoice_tax"', policy)
        self.assertIn('source_kind == "output_invoice_tax"', policy)
        self.assertIn('source_kind == "prepaid_tax"', policy)

    def test_complete_strong_basis_precedes_contract_and_partner_derivation(self):
        normalizer = self._invoice_method("_normalize_invoice_relation_values")
        self.assertIn('"sc.settlement.order"', normalizer)
        self.assertIn("settlement.contract_id", normalizer)
        self.assertIn("settlement.settlement_unit_id", normalizer)
        self.assertIn("basis_contract.partner_id", normalizer)
        self.assertIn('values.setdefault("contract_id"', normalizer)
        self.assertIn('values.setdefault("partner_id"', normalizer)
        self.assertNotIn("limit=1", normalizer)

    def test_explicit_relation_conflicts_are_rejected_not_overwritten(self):
        normalizer = self._invoice_method("_normalize_invoice_relation_values")
        self.assertIn("显式合同与发票结算依据合同不一致", normalizer)
        self.assertIn("显式往来单位与发票权威关系不一致", normalizer)
        self.assertIn("切换发票业务类型时必须同步清理不一致的方向", normalizer)
        self.assertNotIn("values[\"contract_id\"] =", normalizer)
        self.assertNotIn("values[\"partner_id\"] =", normalizer)

    def test_all_relation_lookups_are_caller_scoped(self):
        helper = self._invoice_method("_caller_visible_invoice_relation")
        combined = helper + self._invoice_method(
            "_normalize_invoice_relation_values"
        )
        self.assertIn("self.env[model_name].search(", helper)
        for forbidden in (".sudo(", ".browse(", ".exists(", "ilike", "name_search"):
            self.assertNotIn(forbidden, combined)

    def test_create_and_write_share_the_relation_normalizer(self):
        create = self._invoice_method("create")
        write = self._invoice_method("write")
        self.assertIn("_normalize_invoice_relation_values(vals)", create)
        self.assertIn(
            "_normalize_invoice_relation_values(vals, current=rec)", write
        )
        self.assertLess(
            create.index("_normalize_invoice_relation_values(vals)"),
            create.index("super().create("),
        )
        self.assertLess(
            write.index("_normalize_invoice_relation_values(vals, current=rec)"),
            write.index("super(ScInvoiceRegistration, rec).write("),
        )

    def test_receipt_invoice_line_uses_receive_application_chain(self):
        helper = self._line_method("_require_receipt_application_relation")
        self.assertIn('"payment.request"', helper)
        self.assertIn('("type", "=", "receive")', helper)
        self.assertIn("request.contract_id", helper)
        self.assertIn("contract.partner_id != request.partner_id", helper)
        self.assertNotIn(".sudo(", helper)
        self.assertNotIn(".browse(", helper)
        self.assertNotIn(".exists(", helper)

    def test_tax_deduction_has_only_text_invoice_number_and_no_formal_anchor(self):
        self.assertIn('invoice_no = fields.Char(', self.deduction_source)
        self.assertNotIn("invoice_registration_id = fields.Many2one", self.deduction_source)
        self.assertNotIn("contract_id = fields.Many2one", self.deduction_source)
        self.assertNotIn("sc.invoice.registration", self.deduction_source)

    def test_no_heuristic_matching_or_historical_inference(self):
        combined = (
            self._invoice_method("_normalize_invoice_relation_values")
            + self._line_method("_require_receipt_application_relation")
        )
        for token in (
            "ilike",
            "name_search",
            "invoice_no",
            "invoice_date",
            "amount_total",
            "document_no",
            "order=",
        ):
            self.assertNotIn(token, combined)


if __name__ == "__main__":
    unittest.main()
