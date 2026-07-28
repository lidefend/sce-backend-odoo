#!/usr/bin/env python3
from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
MODEL = ROOT / "addons/smart_construction_core/models/core/funding_baseline.py"
RULES = ROOT / "addons/smart_construction_core/security/sc_record_rules.xml"


class TestUmP3FundingBaselineProjectVisibilityBoundaries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = MODEL.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source, filename=str(MODEL))
        cls.rules = RULES.read_text(encoding="utf-8")

    def test_project_resolution_is_caller_scoped_without_sudo_or_browse(self):
        model = next(
            node
            for node in self.tree.body
            if isinstance(node, ast.ClassDef)
            and node.name == "ProjectFundingBaseline"
        )
        methods = {
            node.name: ast.get_source_segment(self.source, node) or ""
            for node in model.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        resolver = methods["_caller_visible_project"]
        self.assertIn('self.env["project.project"].search', resolver)
        self.assertNotIn(".sudo(", resolver)
        self.assertNotIn(".browse(", resolver)
        self.assertNotIn(".exists(", resolver)
        self.assertIn("_caller_visible_project(project_id)", methods["create"])
        self.assertIn("_caller_visible_project(project_id)", methods["write"])

    def test_header_rules_reuse_company_and_project_boundaries(self):
        self.assertIn("rule_project_funding_baseline_company", self.rules)
        self.assertIn("model_project_funding_baseline", self.rules)
        self.assertIn("[('company_id', 'in', company_ids)]", self.rules)
        self.assertIn("project_id.user_id", self.rules)
        self.assertIn("project_id.message_is_follower", self.rules)
        for group in (
            "group_sc_cap_finance_read",
            "group_sc_cap_finance_user",
            "group_sc_cap_finance_manager",
        ):
            self.assertIn(group, self.rules)

    def test_no_matching_or_historical_inference_is_added(self):
        model_source = ast.get_source_segment(
            self.source,
            next(
                node
                for node in self.tree.body
                if isinstance(node, ast.ClassDef)
                and node.name == "ProjectFundingBaseline"
            ),
        ) or ""
        for token in (
            "name_search",
            "current_active",
            "similar",
            "history",
        ):
            self.assertNotIn(token, model_source)


if __name__ == "__main__":
    unittest.main()
