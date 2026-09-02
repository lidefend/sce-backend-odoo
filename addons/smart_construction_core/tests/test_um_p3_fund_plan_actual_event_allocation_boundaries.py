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

    def test_allocation_service_enforces_identity_amount_and_conservation(self):
        method = self.ledger_methods["action_allocate_funding"]
        self.assertIn("baseline.project_id.id != self.project_id.id", method)
        self.assertIn("baseline.company_id.id != self.project_id.company_id.id", method)
        self.assertIn("baseline.currency_id.id != self.currency_id.id", method)
        self.assertIn("float_compare(amount, 0.0", method)
        self.assertIn("资金分配金额必须大于 0", method)
        self.assertIn("Allocation.read_group(", method)
        self.assertIn("付款台账累计分配不得超过实付金额", method)
        self.assertIn("资金基线累计分配不得超过资金上限", method)

    def test_authority_lock_order_covers_every_mutable_tier(self):
        method = self.ledger_methods["_lock_funding_authority"]
        for table in (
            "payment_request",
            "project_project",
            "project_funding_baseline",
            "project_funding_baseline_line",
            "payment_ledger",
        ):
            self.assertIn(table, method)
        self.assertIn("ORDER BY id FOR UPDATE", method)

    def test_journal_crud_is_service_only_and_immutable(self):
        self.assertIn("_sc_funding_allocation_token", self.allocation_methods["create"])
        self.assertIn("raise AccessError", self.allocation_methods["write"])
        self.assertIn("raise AccessError", self.allocation_methods["unlink"])
        self.assertIn("action_allocate_funding", self.ledger_methods)
        self.assertIn("_reverse_funding_allocations", self.ledger_methods)

    def test_authority_and_journal_are_never_destructively_deleted(self):
        self.assertIn("不允许删除", self.baseline_methods["unlink"])
        self.assertIn("state != \"draft\"", self.line_methods["unlink"])
        self.assertIn("不可删除", self.allocation_methods["unlink"])
        self.assertIn("不允许删除", self.ledger_methods["unlink"])
        self.assertIn('ondelete="restrict"', self.allocation_source)

    def test_relation_resolution_is_caller_scoped_and_non_heuristic(self):
        combined = self.ledger_methods["action_allocate_funding"]
        self.assertIn('self.env["project.funding.baseline.line"].search(', combined)
        for forbidden in (
            ".exists(",
            "name_search",
            "ilike",
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
            if model_id == "model_project_funding_actual_event_allocation":
                self.assertTrue(all(row["perm_write"] == "0" for row in scoped))
                self.assertTrue(all(row["perm_create"] == "0" for row in scoped))
                self.assertTrue(all(row["perm_unlink"] == "0" for row in scoped))

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
        self.assertIn('create="false"', views)
        self.assertIn('name="allocation_key"', views)
        self.assertIn('name="effective_amount"', views)


if __name__ == "__main__":
    unittest.main()
