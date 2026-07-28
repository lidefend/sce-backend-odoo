#!/usr/bin/env python3
from __future__ import annotations

import ast
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RULES = ROOT / "addons/smart_construction_core/security/sc_record_rules.xml"
MODEL_FILES = {
    "fund_account_operation": ROOT
    / "addons/smart_construction_core/models/core/fund_account_operation.py",
    "financing_loan": ROOT
    / "addons/smart_construction_core/models/core/financing_loan.py",
}
MODEL_REFS = {
    "fund_account_operation": "model_sc_fund_account_operation",
    "financing_loan": "model_sc_financing_loan",
}
COMPANY_DOMAIN = "[('company_id', 'in', company_ids)]"
DENY_DOMAIN = "[('id', '=', False)]"


def _rule_fields():
    wanted = {
        *(f"rule_sc_{suffix}_company" for suffix in MODEL_REFS),
        *(
            f"rule_sc_finance_{level}_{suffix}"
            for suffix in MODEL_REFS
            for level in ("read", "user", "manager")
        ),
        *(f"rule_sc_business_initiator_{suffix}" for suffix in MODEL_REFS),
        "rule_sc_config_admin_fund_account_operation",
    }
    result = {}
    for record in ET.parse(RULES).getroot().iter("record"):
        if record.get("id") in wanted:
            result[record.get("id")] = {
                field.get("name"): field for field in record.findall("field")
            }
    return result


class TestUmP1InterfundFinancingVisibilityBoundaries(unittest.TestCase):
    def test_global_allowed_company_intersection_applies_to_both_models(self):
        rules = _rule_fields()
        for suffix, model_ref in MODEL_REFS.items():
            fields = rules[f"rule_sc_{suffix}_company"]
            self.assertEqual(fields["model_id"].get("ref"), model_ref)
            self.assertEqual(
                (fields["domain_force"].text or "").strip(),
                COMPANY_DOMAIN,
            )
            self.assertEqual(fields["global"].get("eval"), "True")
            self.assertNotIn("groups", fields)

    def test_each_acl_finance_capability_is_company_scoped(self):
        rules = _rule_fields()
        for suffix, model_ref in MODEL_REFS.items():
            for level in ("read", "user", "manager"):
                fields = rules[f"rule_sc_finance_{level}_{suffix}"]
                self.assertEqual(fields["model_id"].get("ref"), model_ref)
                self.assertEqual(
                    (fields["domain_force"].text or "").strip(),
                    COMPANY_DOMAIN,
                )
                self.assertIn(
                    f"group_sc_cap_finance_{level}",
                    fields["groups"].get("eval") or "",
                )

    def test_business_initiator_acl_does_not_open_finance_ledgers(self):
        rules = _rule_fields()
        for suffix in MODEL_REFS:
            fields = rules[f"rule_sc_business_initiator_{suffix}"]
            self.assertEqual(
                (fields["domain_force"].text or "").strip(),
                DENY_DOMAIN,
            )
            self.assertIn(
                "group_sc_cap_business_initiator",
                fields["groups"].get("eval") or "",
            )

    def test_project_company_validation_uses_caller_environment(self):
        method_names = {
            "fund_account_operation": "_require_visible_company_scope",
            "financing_loan": "_require_visible_company_project",
        }
        for suffix, path in MODEL_FILES.items():
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
            class_node = next(
                node
                for node in tree.body
                if isinstance(node, ast.ClassDef)
            )
            methods = {
                node.name: node
                for node in class_node.body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
            validator_name = method_names[suffix]
            validator_source = ast.get_source_segment(
                source,
                methods[validator_name],
            ) or ""
            self.assertIn('self.env["project.project"].search(', validator_source)
            self.assertIn("self.env.companies.ids", validator_source)
            self.assertIn("raise AccessError", validator_source)
            self.assertNotIn(".sudo(", validator_source)
            self.assertNotIn(".browse(", validator_source)
            self.assertNotIn(".exists(", validator_source)
            for operation in ("create", "write"):
                operation_source = ast.get_source_segment(
                    source,
                    methods[operation],
                ) or ""
                self.assertIn(validator_name, operation_source)

    def test_project_or_personal_fields_are_not_visibility_domains(self):
        domains = "\n".join(
            (fields["domain_force"].text or "").strip()
            for fields in _rule_fields().values()
        )
        for forbidden in (
            "project_id.user_id",
            "project_id.message_is_follower",
            "create_uid",
            "creator_name",
            "owner_user_id",
            "applicant_user_id",
        ):
            self.assertNotIn(forbidden, domains)


if __name__ == "__main__":
    unittest.main()
