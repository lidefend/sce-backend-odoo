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
COMPANY_DOMAIN = "[('company_id', 'in', company_ids)]"
EXPECTED = {
    "rule_sc_settlement_read_order": (
        "group_sc_cap_settlement_read",
        PROJECT_MEMBER_DOMAIN,
        ("True", "True", "False", "False"),
    ),
    "rule_sc_settlement_user_order": (
        "group_sc_cap_settlement_user",
        PROJECT_MEMBER_DOMAIN,
        ("True", "True", "True", "False"),
    ),
    "rule_sc_settlement_manager_order": (
        "group_sc_cap_settlement_manager",
        COMPANY_DOMAIN,
        ("True", "True", "True", "True"),
    ),
    "rule_sc_config_admin_settlement_order_all": (
        "group_sc_cap_business_config_admin",
        "[(1,'=',1)]",
        ("True", "True", "True", "True"),
    ),
}


def _rules():
    result = {}
    for record in ET.parse(RULES).getroot().iter("record"):
        rule_id = record.get("id")
        if rule_id not in EXPECTED:
            continue
        result[rule_id] = {
            field.get("name"): field for field in record.findall("field")
        }
    return result


class TestUmP1ContractSettlementVisibilityBoundaries(unittest.TestCase):
    def test_complete_order_rule_topology_is_explicit(self):
        rules = _rules()
        self.assertEqual(set(rules), set(EXPECTED))
        for rule_id, (group_ref, domain, permissions) in EXPECTED.items():
            fields = rules[rule_id]
            self.assertEqual(
                fields["model_id"].get("ref"),
                "model_sc_settlement_order",
            )
            self.assertEqual((fields["domain_force"].text or "").strip(), domain)
            self.assertIn(group_ref, fields["groups"].get("eval") or "")
            self.assertEqual(
                tuple(fields[name].get("eval") for name in (
                    "perm_read",
                    "perm_write",
                    "perm_create",
                    "perm_unlink",
                )),
                permissions,
            )

    def test_ordinary_visibility_uses_company_and_project_membership(self):
        for rule_id in (
            "rule_sc_settlement_read_order",
            "rule_sc_settlement_user_order",
        ):
            self.assertEqual(EXPECTED[rule_id][1], PROJECT_MEMBER_DOMAIN)

    def test_entry_user_is_audit_metadata_not_authority(self):
        for _, domain, _ in EXPECTED.values():
            self.assertNotIn("entry_user_id", domain)
            self.assertNotIn("create_uid", domain)

    def test_manager_and_config_admin_contracts_remain_distinct(self):
        self.assertEqual(
            EXPECTED["rule_sc_settlement_manager_order"][1],
            COMPANY_DOMAIN,
        )
        self.assertEqual(
            EXPECTED["rule_sc_config_admin_settlement_order_all"][1],
            "[(1,'=',1)]",
        )


if __name__ == "__main__":
    unittest.main()
