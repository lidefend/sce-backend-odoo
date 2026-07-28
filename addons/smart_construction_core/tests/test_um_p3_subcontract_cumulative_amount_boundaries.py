# -*- coding: utf-8 -*-
import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
MODEL = (
    ROOT
    / "addons/smart_construction_core/models/core/subcontract_management.py"
)
CONTRACT = (
    ROOT / "addons/smart_construction_core/models/core/general_contract.py"
)


def class_methods(class_name):
    source = MODEL.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(MODEL))
    node = next(
        item
        for item in tree.body
        if isinstance(item, ast.ClassDef) and item.name == class_name
    )
    return {
        item.name: ast.get_source_segment(source, item) or ""
        for item in node.body
        if isinstance(item, ast.FunctionDef)
    }


class TestUmP3SubcontractCumulativeAmountBoundaries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.register = class_methods("ScSubcontractRegister")
        cls.register_line = class_methods("ScSubcontractRegisterLine")
        cls.settlement = class_methods("ScSubcontractSettlement")
        cls.settlement_line = class_methods(
            "ScSubcontractSettlementLine"
        )
        cls.contract = class_methods(
            "ConstructionContractSubcontractAuthority"
        )

    def test_existing_tax_included_currency_anchors_are_used(self):
        contract_source = CONTRACT.read_text(encoding="utf-8")
        model_source = MODEL.read_text(encoding="utf-8")
        self.assertIn("amount_total = fields.Monetary", contract_source)
        self.assertIn("currency_id = fields.Many2one(", contract_source)
        self.assertIn(
            'registered_amount = fields.Monetary', model_source
        )
        self.assertIn(
            'amount_total = fields.Monetary(string="含税金额"',
            model_source,
        )

    def test_contract_lock_precedes_complete_effective_aggregates(self):
        lock = self.register["_sc_lock_cumulative_amount_contracts"]
        register = self.register[
            "_sc_validate_cumulative_registered_amounts"
        ]
        settlement = self.settlement[
            "_sc_validate_cumulative_settlement_amounts"
        ]
        self.assertIn("FOR UPDATE", lock)
        self.assertIn("ORDER BY id", lock)
        self.assertIn('error.pgcode == "40001"', lock)
        self.assertIn('state IN %s', register)
        self.assertIn('("active", "closed")', register)
        self.assertIn("COALESCE(SUM(registered_amount)", register)
        self.assertIn("COALESCE(SUM(amount_total)", settlement)
        self.assertIn('state = %s', settlement)
        self.assertIn('"confirmed"', settlement)

    def test_currency_rounding_and_no_inference_are_frozen(self):
        methods = "\n".join(
            [
                self.register["_sc_validate_cumulative_registered_amounts"],
                self.settlement[
                    "_sc_validate_cumulative_settlement_amounts"
                ],
            ]
        )
        self.assertIn("currency_id != contract.currency_id.id", methods)
        self.assertIn("contract.currency_id.compare_amounts(", methods)
        for forbidden in (
            "_convert(",
            "currency._convert",
            "abs(",
            "tax_rate",
            "exchange_rate",
            ".sudo(",
            "name_search",
            "ilike",
        ):
            self.assertNotIn(forbidden, methods)

    def test_all_existing_mutation_entries_revalidate(self):
        for method_name in ("create", "write"):
            self.assertIn(
                "_sc_validate_cumulative_registered_amounts",
                self.register[method_name],
            )
            self.assertIn(
                "_sc_validate_cumulative_registered_amounts",
                self.register_line[method_name],
            )
            self.assertIn(
                "_sc_validate_cumulative_settlement_amounts",
                self.settlement[method_name],
            )
            self.assertIn(
                "_sc_validate_cumulative_settlement_amounts",
                self.settlement_line[method_name],
            )
        self.assertIn(
            "_sc_validate_cumulative_registered_amounts",
            self.contract["write"],
        )


if __name__ == "__main__":
    unittest.main()
