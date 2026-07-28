#!/usr/bin/env python3
from __future__ import annotations

import ast
import csv
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
FUNDING = ROOT / "addons/smart_construction_core/models/core/funding_baseline.py"
LEDGER = ROOT / "addons/smart_construction_core/models/core/payment_ledger.py"
REQUEST = ROOT / "addons/smart_construction_core/models/core/payment_request.py"
ACL = ROOT / "addons/smart_construction_core/security/ir.model.access.csv"
RULES = ROOT / "addons/smart_construction_core/security/sc_record_rules.xml"
VIEWS = (
    ROOT
    / "addons/smart_construction_core/views/core/"
    "funding_actual_event_allocation_views.xml"
)


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


class TestUmP3FundPlanActualEventAllocationBoundaries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline_source, cls.baseline_methods = class_source(
            FUNDING,
            "ProjectFundingBaseline",
        )
        cls.line_source, cls.line_methods = class_source(
            FUNDING,
            "ProjectFundingBaselineLine",
        )
        cls.allocation_source, cls.allocation_methods = class_source(
            FUNDING,
            "ProjectFundingActualEventAllocation",
        )
        cls.ledger_source, cls.ledger_methods = class_source(
            LEDGER,
            "PaymentLedger",
        )

    def test_relation_is_amount_bearing_and_uses_explicit_models(self):
        source = self.allocation_source
        self.assertIn(
            '_name = "project.funding.actual.event.allocation"',
            source,
        )
        self.assertIn('"project.funding.baseline.line"', source)
        self.assertIn('"payment.ledger"', source)
        self.assertIn("allocated_amount = fields.Monetary(", source)
        for forbidden in ("res_model", "res_id", "fields.Many2many("):
            self.assertNotIn(forbidden, source)

    def test_plan_line_is_the_budget_bucket_not_the_header(self):
        self.assertIn(
            '_name = "project.funding.baseline.line"',
            self.line_source,
        )
        self.assertIn("planned_amount = fields.Monetary(", self.line_source)
        self.assertIn(
            '"project.funding.actual.event.allocation"',
            self.line_source,
        )
        self.assertIn("line_ids = fields.One2many(", self.baseline_source)

    def test_allocation_pair_enforces_company_project_currency_and_amount(self):
        method = self.allocation_methods["_validate_pair"]
        self.assertIn("plan_line.company_id != actual_event.project_id.company_id", method)
        self.assertIn("plan_line.project_id != actual_event.project_id", method)
        self.assertIn("plan_line.currency_id != actual_event.currency_id", method)
        self.assertIn("float_compare(", method)
        self.assertIn("资金计划分配金额必须大于 0", method)

    def test_actual_event_total_is_locked_and_cannot_be_overallocated(self):
        method = self.allocation_methods["_check_actual_event_totals"]
        self.assertIn("FOR UPDATE", method)
        self.assertIn("self.read_group(", method)
        self.assertIn("event.amount", method)
        self.assertIn("不得超过实际付款金额", method)

    def test_create_write_unlink_revalidate_final_state(self):
        for name in ("create", "write"):
            self.assertIn(
                "_validate_relation_state",
                self.allocation_methods[name],
            )
        self.assertIn(
            "_check_actual_event_totals",
            self.allocation_methods["unlink"],
        )
        self.assertIn(
            "_validate_relation_state",
            self.baseline_methods["write"],
        )
        self.assertIn(
            "_validate_relation_state",
            self.line_methods["write"],
        )
        self.assertIn(
            "_validate_relation_state",
            self.ledger_methods["write"],
        )

    def test_allocated_relations_block_destructive_parent_deletion(self):
        self.assertIn("line_ids.allocation_ids", self.baseline_methods["unlink"])
        self.assertIn("self.allocation_ids", self.line_methods["unlink"])
        self.assertIn(
            "self.fund_plan_allocation_ids",
            self.ledger_methods["unlink"],
        )
        self.assertIn('ondelete="restrict"', self.allocation_source)

    def test_relation_resolution_is_caller_scoped_and_non_heuristic(self):
        helper = self.allocation_methods["_caller_visible_relation"]
        combined = "".join(self.allocation_methods.values())
        self.assertIn("self.env[model_name].search(", helper)
        for forbidden in (
            ".sudo(",
            ".browse(",
            ".exists(",
            "name_search",
            "ilike",
            "paid_at",
            "create_date",
            "current_active",
        ):
            self.assertNotIn(forbidden, combined)

    def test_request_remains_intent_and_never_creates_allocations(self):
        source = REQUEST.read_text(encoding="utf-8")
        self.assertNotIn(
            'self.env["project.funding.actual.event.allocation"]',
            source,
        )
        self.assertNotIn("fund_plan_allocation_ids", source)

    def test_acl_is_the_finance_read_user_manager_intersection(self):
        with ACL.open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        for model_id in (
            "model_project_funding_baseline_line",
            "model_project_funding_actual_event_allocation",
        ):
            scoped = [row for row in rows if row["model_id:id"] == model_id]
            self.assertEqual(len(scoped), 3)
            groups = {row["group_id:id"] for row in scoped}
            self.assertEqual(
                groups,
                {
                    "smart_construction_core.group_sc_cap_finance_read",
                    "smart_construction_core.group_sc_cap_finance_user",
                    "smart_construction_core.group_sc_cap_finance_manager",
                },
            )

    def test_record_rules_and_audit_views_are_explicit(self):
        rules = RULES.read_text(encoding="utf-8")
        views = VIEWS.read_text(encoding="utf-8")
        for model_id in (
            "model_project_funding_baseline_line",
            "model_project_funding_actual_event_allocation",
        ):
            self.assertIn(model_id, rules)
        self.assertIn("[('company_id', 'in', company_ids)]", rules)
        self.assertIn("project_id.user_id", rules)
        self.assertIn("project_id.message_is_follower", rules)
        self.assertIn('name="create_uid"', views)
        self.assertIn('name="create_date"', views)


if __name__ == "__main__":
    unittest.main()
