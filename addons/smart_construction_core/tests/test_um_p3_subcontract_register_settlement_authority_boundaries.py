# -*- coding: utf-8 -*-
import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
MODEL = (
    ROOT
    / "addons/smart_construction_core/models/core/subcontract_management.py"
)
VIEWS = (
    ROOT
    / "addons/smart_construction_core/views/core/subcontract_management_views.xml"
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


class TestUmP3SubcontractRegisterSettlementAuthorityBoundaries(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.register, cls.register_methods = class_source(
            "ScSubcontractRegister"
        )
        cls.register_line, cls.register_line_methods = class_source(
            "ScSubcontractRegisterLine"
        )
        cls.settlement, cls.settlement_methods = class_source(
            "ScSubcontractSettlement"
        )
        cls.settlement_line, cls.settlement_line_methods = class_source(
            "ScSubcontractSettlementLine"
        )
        cls.contract, cls.contract_methods = class_source(
            "ConstructionContractSubcontractAuthority"
        )

    def test_relation_uses_formal_settlement_line_to_register_line_grain(self):
        self.assertIn(
            '"sc.subcontract.register.line"', self.settlement_line
        )
        self.assertIn('ondelete="restrict"', self.settlement_line)
        self.assertIn("settlement_line_ids = fields.One2many(", self.register_line)
        for forbidden in ("res_model", "res_id", "fields.Many2many("):
            self.assertNotIn(forbidden, self.settlement_line)

    def test_complete_set_converges_on_one_contract_scope(self):
        method = self.settlement_methods[
            "_sc_validate_register_settlement_authority"
        ]
        self.assertIn('filtered("register_line_id")', method)
        self.assertIn('mapped("register_id")', method)
        self.assertIn('mapped("contract_id")', method)
        self.assertIn("len(contracts) != 1", method)
        self.assertIn("register.project_id != contract.project_id", method)
        self.assertIn(
            "register.subcontractor_id != contract.partner_id", method
        )
        self.assertIn(
            "register.currency_id != contract.currency_id", method
        )

    def test_header_fields_are_projection_and_explicit_conflicts_reject(self):
        method = self.settlement_methods[
            "_sc_validate_register_settlement_authority"
        ]
        for field_name in (
            "project_id",
            "register_id",
            "contract_id",
            "subcontractor_id",
            "currency_id",
        ):
            self.assertIn(f'"{field_name}"', method)
        self.assertIn("explicit_fields", method)
        self.assertIn("raise ValidationError", method)
        self.assertIn('"register_id": False', method)

    def test_create_write_unlink_and_parent_commands_revalidate(self):
        self.assertIn(
            "_sc_validate_register_settlement_authority",
            self.settlement_methods["create"],
        )
        self.assertIn(
            "sc_subcontract_register_authority_batch",
            self.settlement_methods["write"],
        )
        for method_name in ("create", "write", "unlink"):
            self.assertIn(
                "_sc_validate_register_settlement_authority",
                self.settlement_line_methods[method_name],
            )
        self.assertIn(
            "_sc_validate_register_settlement_authority",
            self.register_line_methods["write"],
        )
        self.assertIn(
            "_sc_validate_register_settlement_authority",
            self.contract_methods["write"],
        )

    def test_relation_resolution_uses_caller_env_without_heuristics(self):
        resolver = self.register_methods["_sc_caller_visible_relation"]
        combined = "".join(
            self.settlement_line_methods[name]
            for name in (
                "_sc_resolve_register_relations",
                "_sc_validate_register_pair",
                "_sc_validate_register_relation_state",
            )
        ) + self.settlement_methods[
            "_sc_validate_register_settlement_authority"
        ]
        self.assertIn("self.env[model_name].search(", resolver)
        for forbidden in (
            ".sudo(",
            ".browse(",
            ".exists(",
            "name_search",
            "ilike",
            "amount_total",
            "settlement_date",
            "register_date",
            "create_date",
        ):
            self.assertNotIn(forbidden, combined)

    def test_destructive_parent_changes_preserve_explicit_relation(self):
        self.assertIn(
            "settlement_line_ids", self.register_methods["unlink"]
        )
        self.assertIn(
            "settlement_line_ids", self.register_line_methods["unlink"]
        )
        self.assertIn(
            "register_line_id", self.settlement_methods["unlink"]
        )
        self.assertIn(
            "register_line_id", self.settlement_line_methods["unlink"]
        )

    def test_amount_cumulative_policy_is_not_invented(self):
        combined = self.settlement + self.settlement_line
        for forbidden in (
            "registered_amount -",
            "amount_total >",
            "settled_qty",
            "remaining_amount",
            "amount_over_settlement",
        ):
            self.assertNotIn(forbidden, combined)

    def test_view_exposes_register_line_and_header_register_is_readonly(self):
        views = VIEWS.read_text(encoding="utf-8")
        self.assertIn('name="register_line_id"', views)
        self.assertIn('name="register_id" readonly="1"', views)


if __name__ == "__main__":
    unittest.main()
