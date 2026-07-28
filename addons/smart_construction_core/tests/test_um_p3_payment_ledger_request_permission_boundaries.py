# -*- coding: utf-8 -*-
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RULES = (
    ROOT
    / "addons/smart_construction_core/security/sc_record_rules.xml"
)
MODEL = (
    ROOT
    / "addons/smart_construction_core/models/core/payment_ledger.py"
)
ACL = ROOT / "addons/smart_construction_core/security/ir.model.access.csv"


def record_node(xml_id):
    root = ET.parse(RULES).getroot()
    record = root.find(f".//record[@id='{xml_id}']")
    if record is None:
        raise AssertionError(f"missing record rule {xml_id}")
    return record


def record_fields(xml_id):
    record = record_node(xml_id)
    return {
        field.attrib["name"]: (field.text or "").strip()
        for field in record.findall("field")
    }


class TestUmP3PaymentLedgerRequestPermissionBoundaries(
    unittest.TestCase
):
    def test_payment_request_relation_is_required_and_unique(self):
        source = MODEL.read_text(encoding="utf-8")
        field_start = source.index("payment_request_id = fields.Many2one(")
        field_end = source.index("project_id = fields.Many2one(", field_start)
        field_source = source[field_start:field_end]
        self.assertIn('\"payment.request\"', field_source)
        self.assertIn("required=True", field_source)
        self.assertIn("unique(payment_request_id)", source)

    def test_manager_rule_inherits_authoritative_request_company(self):
        fields = record_fields("rule_sc_finance_manager_payment_ledger")
        self.assertEqual(fields["model_id"], "")
        self.assertEqual(
            fields["domain_force"],
            "[('payment_request_id.company_id', 'in', company_ids)]",
        )
        self.assertNotIn("(1,'=',1)", fields["domain_force"])
        groups = record_node(
            "rule_sc_finance_manager_payment_ledger"
        ).find("field[@name='groups']")
        self.assertIn(
            "group_sc_cap_finance_manager",
            groups.attrib["eval"],
        )

    def test_payment_request_manager_rule_remains_unchanged_authority(self):
        fields = record_fields("rule_sc_finance_manager_payment_request")
        self.assertEqual(
            fields["domain_force"],
            "[('company_id', 'in', company_ids)]",
        )

    def test_acl_and_other_permission_surfaces_are_not_changed(self):
        acl = ACL.read_text(encoding="utf-8")
        self.assertIn(
            "access_payment_ledger_manager,payment.ledger.manager,"
            "model_payment_ledger,"
            "smart_construction_core.group_sc_cap_finance_manager,1,1,1,1",
            acl,
        )


if __name__ == "__main__":
    unittest.main()
