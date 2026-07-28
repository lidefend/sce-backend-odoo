#!/usr/bin/env python3
from __future__ import annotations

import ast
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RULES = ROOT / "addons/smart_construction_core/security/sc_record_rules.xml"
MODEL = ROOT / "addons/smart_construction_core/models/core/cost_domain.py"
VIEWS = ROOT / "addons/smart_construction_core/views/core/cost_domain_views.xml"

MEMBER_DOMAIN = (
    "['&', ('company_id', 'in', company_ids), '|', "
    "('project_id.user_id', '=', user.id), "
    "('project_id.message_is_follower', '=', True)]"
)
EXPECTED = {
    "rule_sc_project_cost_ledger_company": (
        None,
        "[('company_id', 'in', company_ids)]",
        ("True", "True", "True", "True"),
        True,
    ),
    "rule_sc_cost_read_project_cost_ledger": (
        "group_sc_cap_cost_read",
        MEMBER_DOMAIN,
        ("True", "False", "False", "False"),
        False,
    ),
    "rule_sc_cost_user_project_cost_ledger": (
        "group_sc_cap_cost_user",
        MEMBER_DOMAIN,
        ("True", "True", "True", "False"),
        False,
    ),
    "rule_sc_cost_manager_project_cost_ledger": (
        "group_sc_cap_cost_manager",
        MEMBER_DOMAIN,
        ("True", "True", "True", "True"),
        False,
    ),
}


def _rule_fields():
    result = {}
    for record in ET.parse(RULES).getroot().iter("record"):
        if record.get("id") in EXPECTED:
            result[record.get("id")] = {
                field.get("name"): field for field in record.findall("field")
            }
    return result


class TestUmP1CostLedgerVisibilityBoundaries(unittest.TestCase):
    def test_rule_topology_enforces_company_and_project_membership(self):
        rules = _rule_fields()
        self.assertEqual(set(rules), set(EXPECTED))
        for rule_id, (group_ref, domain, permissions, global_rule) in EXPECTED.items():
            fields = rules[rule_id]
            self.assertEqual(
                fields["model_id"].get("ref"),
                "model_project_cost_ledger",
            )
            self.assertEqual((fields["domain_force"].text or "").strip(), domain)
            self.assertEqual(
                tuple(
                    fields[name].get("eval")
                    for name in (
                        "perm_read",
                        "perm_write",
                        "perm_create",
                        "perm_unlink",
                    )
                ),
                permissions,
            )
            if global_rule:
                self.assertEqual(fields["global"].get("eval"), "True")
                self.assertNotIn("groups", fields)
            else:
                self.assertIn(group_ref, fields["groups"].get("eval") or "")

    def test_manager_and_creator_fields_are_not_authority(self):
        domains = "\n".join(
            (fields["domain_force"].text or "").strip()
            for fields in _rule_fields().values()
        )
        self.assertNotIn("project_id.manager_id", domains)
        self.assertNotIn("create_uid", domains)
        self.assertIn("project_id.user_id", domains)
        self.assertIn("project_id.message_is_follower", domains)

    def test_caller_scoped_project_guard_precedes_period_sudo(self):
        source = MODEL.read_text(encoding="utf-8")
        tree = ast.parse(source)
        ledger = next(
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == "ProjectCostLedger"
        )
        methods = {
            node.name: node
            for node in ledger.body
            if isinstance(node, ast.FunctionDef)
        }
        guard = ast.get_source_segment(
            source,
            methods["_require_visible_project_scope"],
        ) or ""
        self.assertIn('self.env["project.project"]', guard)
        self.assertIn('"message_is_follower"', guard)
        self.assertIn('"company_id"', guard)
        self.assertNotIn(".sudo(", guard)
        self.assertNotIn(".browse(", guard)
        self.assertNotIn(".exists(", guard)

        create_source = ast.get_source_segment(source, methods["create"]) or ""
        self.assertLess(
            create_source.index("_require_visible_project_scope"),
            create_source.index("_get_or_create_period"),
        )
        write_source = ast.get_source_segment(source, methods["write"]) or ""
        self.assertLess(
            write_source.index("_require_visible_project_scope"),
            write_source.index("_get_or_create_period"),
        )

    def test_frontend_manager_filter_does_not_define_backend_authority(self):
        views = ET.parse(VIEWS).getroot()
        action = next(
            record
            for record in views.iter("record")
            if record.get("id") == "action_project_cost_ledger_my"
        )
        fields = {field.get("name"): field for field in action.findall("field")}
        self.assertIn("project_id.manager_id", fields["domain"].text or "")
        for _, domain, _, _ in EXPECTED.values():
            self.assertNotIn("manager_id", domain)


if __name__ == "__main__":
    unittest.main()
