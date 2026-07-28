#!/usr/bin/env python3
from __future__ import annotations

import ast
import csv
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
MODEL = ROOT / "addons/smart_construction_core/models/core/receipt_income.py"
RULES = ROOT / "addons/smart_construction_core/security/sc_record_rules.xml"
ACL = ROOT / "addons/smart_construction_core/security/ir.model.access.csv"

ORDINARY_RULE_IDS = {
    "rule_sc_business_initiator_receipt_income",
    "rule_sc_finance_read_receipt_income",
    "rule_sc_finance_user_receipt_income",
}
MANAGER_RULE_ID = "rule_sc_finance_manager_receipt_income"
RULE_GROUPS = {
    "rule_sc_business_initiator_receipt_income": "group_sc_cap_business_initiator",
    "rule_sc_finance_read_receipt_income": "group_sc_cap_finance_read",
    "rule_sc_finance_user_receipt_income": "group_sc_cap_finance_user",
    "rule_sc_finance_manager_receipt_income": "group_sc_cap_finance_manager",
}
PROJECT_MEMBER_DOMAIN = (
    "['&', ('company_id', 'in', company_ids), '|', "
    "('project_id.user_id', '=', user.id), "
    "('project_id.message_is_follower', '=', True)]"
)


def _rule_records():
    root = ET.parse(RULES).getroot()
    result = {}
    for record in root.iter("record"):
        rule_id = record.get("id")
        if rule_id not in ORDINARY_RULE_IDS | {MANAGER_RULE_ID}:
            continue
        result[rule_id] = {
            field.get("name"): {
                "text": (field.text or "").strip(),
                "eval": field.get("eval"),
            }
            for field in record.findall("field")
        }
    return result


class TestUmP1ProjectReceiptVisibilityBoundaries(unittest.TestCase):
    def test_receipt_model_reuses_existing_project_and_company_anchors(self):
        source = MODEL.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(MODEL))
        model_class = next(
            node
            for node in tree.body
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
        assignments = {
            statement.targets[0].id: ast.get_source_segment(source, statement.value)
            for statement in model_class.body
            if isinstance(statement, ast.Assign)
            and len(statement.targets) == 1
            and isinstance(statement.targets[0], ast.Name)
        }

        self.assertIn("project_id", assignments)
        self.assertIn("required=True", assignments["project_id"])
        self.assertIn("company_id", assignments)
        self.assertIn('related="project_id.company_id"', assignments["company_id"])

    def test_ordinary_rules_require_allowed_company_and_project_membership(self):
        rules = _rule_records()
        self.assertTrue(ORDINARY_RULE_IDS.issubset(rules))

        for rule_id in ORDINARY_RULE_IDS:
            fields = rules[rule_id]
            self.assertEqual(fields["model_id"]["text"], "")
            self.assertEqual(
                next(
                    field.get("ref")
                    for record in ET.parse(RULES).getroot().iter("record")
                    if record.get("id") == rule_id
                    for field in record.findall("field")
                    if field.get("name") == "model_id"
                ),
                "model_sc_receipt_income",
            )
            self.assertEqual(fields["domain_force"]["text"], PROJECT_MEMBER_DOMAIN)
            self.assertEqual(fields["perm_read"]["eval"], "True")
            self.assertEqual(fields["perm_unlink"]["eval"], "False")
            self.assertIn(RULE_GROUPS[rule_id], fields["groups"]["eval"])

        self.assertEqual(rules["rule_sc_finance_read_receipt_income"]["perm_write"]["eval"], "False")
        self.assertEqual(rules["rule_sc_finance_read_receipt_income"]["perm_create"]["eval"], "False")

    def test_manager_rule_is_limited_to_allowed_companies(self):
        fields = _rule_records()[MANAGER_RULE_ID]
        self.assertEqual(fields["domain_force"]["text"], "[('company_id', 'in', company_ids)]")
        for permission in ("perm_read", "perm_write", "perm_create", "perm_unlink"):
            self.assertEqual(fields[permission]["eval"], "True")
        self.assertIn(RULE_GROUPS[MANAGER_RULE_ID], fields["groups"]["eval"])

    def test_existing_acl_matrix_is_unchanged_and_complete_for_rule_groups(self):
        with ACL.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        receipt_rows = {
            row["group_id:id"]: row
            for row in rows
            if row["model_id:id"] == "model_sc_receipt_income"
        }
        expected = {
            "smart_construction_core.group_sc_cap_business_initiator": ("1", "1", "1", "0"),
            "smart_construction_core.group_sc_cap_finance_read": ("1", "0", "0", "0"),
            "smart_construction_core.group_sc_cap_finance_user": ("1", "1", "1", "0"),
            "smart_construction_core.group_sc_cap_finance_manager": ("1", "1", "1", "1"),
        }
        self.assertEqual(set(receipt_rows), set(expected))
        for group, permissions in expected.items():
            row = receipt_rows[group]
            self.assertEqual(
                (row["perm_read"], row["perm_write"], row["perm_create"], row["perm_unlink"]),
                permissions,
            )


if __name__ == "__main__":
    unittest.main()
