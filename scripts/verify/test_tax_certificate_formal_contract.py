#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]
MODEL = ROOT / "addons/smart_construction_core/models/core/tax_certificate_registration.py"
VIEWS = ROOT / "addons/smart_construction_core/views/core/tax_certificate_registration_views.xml"
MENU = ROOT / "addons/smart_construction_core/views/menu_business_taxonomy.xml"
ACCESS = ROOT / "addons/smart_construction_core/security/ir.model.access.csv"
RULES = ROOT / "addons/smart_construction_core/security/sc_record_rules.xml"
CONTRACT = ROOT / "addons/smart_construction_core/services/locked_menu_policy_contract.py"
BASELINE = ROOT / "scripts/verify/baselines/formal_business_product_menu_policy_v1.json"
CHECKSUM = ROOT / "scripts/verify/baselines/formal_business_product_menu_policy_v1.json.sha256"


class TaxCertificateFormalContractTests(unittest.TestCase):
    def test_independent_formal_model_and_minimal_state_flow(self):
        source = MODEL.read_text(encoding="utf-8")
        self.assertIn('_name = "sc.tax.certificate.registration"', source)
        self.assertNotIn("sc.invoice.registration", source)
        self.assertNotIn("sc.legacy.payment.residual.fact", source)
        for field in (
            "company_id", "project_id", "taxpayer_name", "taxpayer_identifier",
            "tax_report_management_no", "cross_region_business_address",
            "validity_start_date", "validity_end_date", "prepaid_tax_date",
            "tax_payment_certificate_no", "handler_id", "attachment_ids", "note",
        ):
            self.assertIn(f"{field} = fields.", source)
        for transition in ("action_register", "action_complete", "action_cancel"):
            self.assertIn(f"def {transition}", source)
        self.assertIn('("draft", "草稿")', source)
        self.assertIn('("registered", "已登记")', source)
        self.assertIn('("completed", "已完成")', source)
        self.assertIn('("cancelled", "已取消")', source)

    def test_action_menu_and_views_use_stable_formal_identity(self):
        view_root = ET.parse(VIEWS).getroot()
        action = view_root.find(".//record[@id='action_sc_tax_certificate_registration_user']")
        self.assertIsNotNone(action)
        self.assertEqual(action.find("field[@name='res_model']").text, "sc.tax.certificate.registration")
        models = {node.find("field[@name='model']").text for node in view_root.findall(".//record") if node.find("field[@name='model']") is not None}
        self.assertEqual(models, {"sc.tax.certificate.registration"})

        menu_root = ET.parse(MENU).getroot()
        menu = menu_root.find(".//menuitem[@id='menu_sc_tax_certificate_registration_user']")
        self.assertIsNotNone(menu)
        self.assertEqual(menu.get("action"), "smart_construction_core.action_sc_tax_certificate_registration_user")
        self.assertEqual(menu.get("parent"), "smart_construction_core.menu_sc_invoice_tax_user_group")
        self.assertNotIn("base.group_user", menu.get("groups", ""))

    def test_acl_is_explicit_and_multicompany_rules_fail_closed(self):
        with ACCESS.open(encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        model_rows = [row for row in rows if row["model_id:id"] == "model_sc_tax_certificate_registration"]
        self.assertEqual(len(model_rows), 4)
        permissions = {row["group_id:id"]: tuple(row[f"perm_{name}"] for name in ("read", "write", "create", "unlink")) for row in model_rows}
        self.assertEqual(permissions["smart_construction_core.group_sc_cap_project_read"], ("1", "0", "0", "0"))
        self.assertEqual(permissions["smart_construction_core.group_sc_cap_finance_read"], ("1", "0", "0", "0"))
        self.assertEqual(permissions["smart_construction_core.group_sc_cap_finance_user"], ("1", "1", "1", "0"))
        self.assertEqual(permissions["smart_construction_core.group_sc_cap_finance_manager"], ("1", "1", "1", "1"))
        self.assertNotIn("base.group_user", permissions)

        rules = RULES.read_text(encoding="utf-8")
        self.assertIn('id="rule_sc_tax_certificate_registration_allowed_company"', rules)
        self.assertIn("('company_id', 'in', company_ids)", rules)
        self.assertIn('id="rule_sc_project_read_tax_certificate_registration"', rules)
        self.assertIn("('project_id.message_is_follower', '=', True)", rules)

    def test_both_97_entry_products_bind_the_new_model(self):
        raw = BASELINE.read_bytes()
        expected = CHECKSUM.read_text(encoding="utf-8").split()[0]
        self.assertEqual(hashlib.sha256(raw).hexdigest(), expected)
        payload = json.loads(raw)
        self.assertEqual(len(payload["products"]), 2)
        for product in payload["products"]:
            rows = [
                menu
                for group in product["menu_groups"]
                for menu in group["menus"]
                if menu.get("menu_xmlid") == "smart_construction_core.menu_sc_tax_certificate_registration_user"
            ]
            self.assertEqual(sum(len(group["menus"]) for group in product["menu_groups"]), 97)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["res_model"], "sc.tax.certificate.registration")
            self.assertEqual(rows[0]["fact_model"], "sc.tax.certificate.registration")
            self.assertEqual(rows[0]["entry_intent"], "handling")
            self.assertEqual(rows[0]["entry_target_policy"], "keep_list_form")

    def test_business_decision_blocker_is_removed_without_legacy_creation(self):
        source = CONTRACT.read_text(encoding="utf-8")
        decision_block = source.split("FORMAL_BUSINESS_DECISION_REQUIRED_TARGETS =", 1)[1].split("FORMAL_INITIALIZATION_ACTION_SPECS", 1)[0]
        self.assertIn("{}", decision_block)
        self.assertNotIn("menu_sc_tax_certificate_registration_user", decision_block)
        self.assertNotIn("sc.legacy.payment.residual.fact", MODEL.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
