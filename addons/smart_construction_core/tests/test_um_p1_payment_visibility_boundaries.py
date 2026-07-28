#!/usr/bin/env python3
from __future__ import annotations

import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RULES = ROOT / "addons/smart_construction_core/security/sc_record_rules.xml"

PROJECT_MEMBER_DOMAIN = (
    "['&', ('company_id', 'in', company_ids), '|', "
    "('project_id.user_id', '=', user.id), "
    "('project_id.message_is_follower', '=', True)]"
)
EXPECTED = {
    "rule_sc_business_initiator_payment_request": (
        "model_payment_request",
        "group_sc_cap_business_initiator",
        PROJECT_MEMBER_DOMAIN,
    ),
    "rule_sc_finance_read_payment_request": (
        "model_payment_request",
        "group_sc_cap_finance_read",
        PROJECT_MEMBER_DOMAIN,
    ),
    "rule_sc_finance_user_payment_request": (
        "model_payment_request",
        "group_sc_cap_finance_user",
        PROJECT_MEMBER_DOMAIN,
    ),
    "rule_sc_finance_manager_payment_request": (
        "model_payment_request",
        "group_sc_cap_finance_manager",
        "[('company_id', 'in', company_ids)]",
    ),
    "rule_sc_executive_payment_request": (
        "model_payment_request",
        "group_sc_role_executive",
        "[('company_id', 'in', company_ids)]",
    ),
    "rule_sc_config_admin_payment_request": (
        "model_payment_request",
        "group_sc_cap_business_config_admin",
        "[(1,'=',1)]",
    ),
    "rule_sc_business_initiator_payment_execution": (
        "model_sc_payment_execution",
        "group_sc_cap_business_initiator",
        PROJECT_MEMBER_DOMAIN,
    ),
    "rule_sc_finance_read_payment_execution": (
        "model_sc_payment_execution",
        "group_sc_cap_finance_read",
        PROJECT_MEMBER_DOMAIN,
    ),
    "rule_sc_finance_user_payment_execution": (
        "model_sc_payment_execution",
        "group_sc_cap_finance_user",
        PROJECT_MEMBER_DOMAIN,
    ),
    "rule_sc_finance_manager_payment_execution": (
        "model_sc_payment_execution",
        "group_sc_cap_finance_manager",
        "[('company_id', 'in', company_ids)]",
    ),
}


def _rules():
    result = {}
    for record in ET.parse(RULES).getroot().iter("record"):
        rule_id = record.get("id")
        if rule_id not in EXPECTED:
            continue
        fields = {field.get("name"): field for field in record.findall("field")}
        result[rule_id] = fields
    return result


class TestUmP1PaymentVisibilityBoundaries(unittest.TestCase):
    def test_complete_payment_rule_topology_is_explicit(self):
        rules = _rules()
        self.assertEqual(set(rules), set(EXPECTED))

        for rule_id, (model_ref, group_ref, domain) in EXPECTED.items():
            fields = rules[rule_id]
            self.assertEqual(fields["model_id"].get("ref"), model_ref)
            self.assertEqual((fields["domain_force"].text or "").strip(), domain)
            self.assertIn(group_ref, fields["groups"].get("eval") or "")

    def test_ordinary_rules_combine_company_and_project_membership(self):
        for rule_id, (_, _, domain) in EXPECTED.items():
            if "business_initiator" not in rule_id and "finance_read" not in rule_id and "finance_user" not in rule_id:
                continue
            self.assertEqual(domain, PROJECT_MEMBER_DOMAIN)

    def test_manager_and_executive_rules_do_not_cross_allowed_companies(self):
        for rule_id in (
            "rule_sc_finance_manager_payment_request",
            "rule_sc_executive_payment_request",
            "rule_sc_finance_manager_payment_execution",
        ):
            self.assertEqual(EXPECTED[rule_id][2], "[('company_id', 'in', company_ids)]")

    def test_business_config_all_rule_is_payment_request_only(self):
        config_rules = {
            rule_id: values
            for rule_id, values in EXPECTED.items()
            if values[1] == "group_sc_cap_business_config_admin"
        }
        self.assertEqual(
            config_rules,
            {
                "rule_sc_config_admin_payment_request": (
                    "model_payment_request",
                    "group_sc_cap_business_config_admin",
                    "[(1,'=',1)]",
                )
            },
        )


if __name__ == "__main__":
    unittest.main()
