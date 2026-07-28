#!/usr/bin/env python3
from __future__ import annotations

import ast
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RULES = ROOT / "addons/smart_construction_core/security/sc_record_rules.xml"
MODEL_FILES = {
    "sc.invoice.registration": ROOT
    / "addons/smart_construction_core/models/core/invoice_registration.py",
    "sc.tax.deduction.registration": ROOT
    / "addons/smart_construction_core/models/core/tax_deduction_registration.py",
}
COMPANY_DOMAIN = "[('company_id', 'in', company_ids)]"
DENY_DOMAIN = "[('id', '=', False)]"
MODEL_REFS = {
    "invoice_registration": "model_sc_invoice_registration",
    "tax_deduction_registration": "model_sc_tax_deduction_registration",
}
FINANCE_RULES = {
    f"rule_sc_finance_{level}_{suffix}": (
        model_ref,
        f"group_sc_cap_finance_{level}",
    )
    for suffix, model_ref in MODEL_REFS.items()
    for level in ("read", "user", "manager")
}


def _rule_fields():
    wanted = {
        *FINANCE_RULES,
        "rule_sc_invoice_registration_company",
        "rule_sc_tax_deduction_registration_company",
        "rule_sc_business_initiator_invoice_registration",
        "rule_sc_business_initiator_tax_deduction_registration",
        "rule_sc_config_admin_tax_deduction_registration",
    }
    result = {}
    for record in ET.parse(RULES).getroot().iter("record"):
        if record.get("id") in wanted:
            result[record.get("id")] = {
                field.get("name"): field for field in record.findall("field")
            }
    return result


class TestUmP1InvoiceDeductionVisibilityBoundaries(unittest.TestCase):
    def test_global_company_intersection_is_mandatory_for_both_ledgers(self):
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

    def test_finance_capabilities_share_only_allowed_company_records(self):
        rules = _rule_fields()
        for rule_id, (model_ref, group_ref) in FINANCE_RULES.items():
            fields = rules[rule_id]
            self.assertEqual(fields["model_id"].get("ref"), model_ref)
            self.assertEqual(
                (fields["domain_force"].text or "").strip(),
                COMPANY_DOMAIN,
            )
            self.assertIn(group_ref, fields["groups"].get("eval") or "")

    def test_business_initiator_does_not_gain_finance_ledger_visibility(self):
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

    def test_tax_config_admin_keeps_company_scoped_existing_contract(self):
        fields = _rule_fields()["rule_sc_config_admin_tax_deduction_registration"]
        self.assertEqual(
            fields["model_id"].get("ref"),
            "model_sc_tax_deduction_registration",
        )
        self.assertEqual((fields["domain_force"].text or "").strip(), COMPANY_DOMAIN)
        self.assertIn("group_sc_cap_config_admin", fields["groups"].get("eval") or "")

    def test_project_validation_uses_caller_search_before_create_or_write(self):
        for model_name, path in MODEL_FILES.items():
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
            validator = next(
                node
                for node in tree.body
                if isinstance(node, ast.ClassDef)
                for node in node.body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == "_require_visible_company_project"
            )
            validator_source = ast.get_source_segment(source, validator) or ""
            self.assertIn('self.env["project.project"].search(', validator_source)
            self.assertIn("self.env.companies.ids", validator_source)
            self.assertNotIn(".sudo(", validator_source)
            self.assertNotIn(".browse(", validator_source)
            self.assertNotIn(".exists(", validator_source)
            self.assertIn("raise AccessError", validator_source)

            for method_name in ("create", "write"):
                method = next(
                    node
                    for node in tree.body
                    if isinstance(node, ast.ClassDef)
                    for node in node.body
                    if isinstance(node, ast.FunctionDef) and node.name == method_name
                )
                method_source = ast.get_source_segment(source, method) or ""
                self.assertIn(
                    "_require_visible_company_project",
                    method_source,
                    f"{model_name}.{method_name} must validate the caller-visible project",
                )

    def test_char_audit_names_are_not_security_anchors(self):
        relevant = "\n".join(
            (fields["domain_force"].text or "").strip()
            for fields in _rule_fields().values()
        )
        for field_name in (
            "applicant_name",
            "source_created_by",
            "creator_name",
            "project_id.user_id",
            "project_id.message_is_follower",
        ):
            self.assertNotIn(field_name, relevant)


if __name__ == "__main__":
    unittest.main()
