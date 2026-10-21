#!/usr/bin/env python3
"""Prevent retired experimental views from returning to product declarations."""
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
RETIRED_P2_FORM_VIEW_XMLIDS = (
    "view_project_project_user_confirmed_form_fields",
    "view_project_overview_user_confirmed_form_fields",
    "view_tender_bid_user_confirmed_form_fields",
    "view_construction_contract_expense_user_confirmed_form_fields",
    "view_sc_settlement_order_user_confirmed_form_fields",
    "view_sc_construction_diary_user_confirmed_form_fields",
    "view_project_material_plan_user_confirmed_form_fields",
    "view_sc_labor_usage_user_confirmed_form_fields",
    "view_sc_subcontract_request_user_confirmed_form_fields",
    "view_sc_equipment_usage_user_confirmed_form_fields",
    "view_sc_material_rfq_user_confirmed_form_fields",
    "view_sc_material_inbound_user_confirmed_form_fields",
    "view_sc_hr_payroll_document_user_confirmed_form_fields",
    "view_sc_tax_deduction_registration_user_confirmed_form_fields",
    "view_sc_fund_account_operation_user_confirmed_form_fields",
    "view_sc_financing_loan_user_confirmed_form_fields",
    "view_payment_request_user_confirmed_form_fields",
    "view_sc_payment_execution_user_confirmed_form_fields",
    "view_tender_guarantee_user_confirmed_form_fields",
    "view_sc_office_admin_document_user_confirmed_form_fields",
    "view_sc_document_admin_document_user_confirmed_form_fields",
)


class RetiredProductViewDeclarationsTest(unittest.TestCase):
    def test_product_does_not_redeclare_retired_views(self):
        for path in (ROOT / "addons/smart_construction_core").rglob("*.xml"):
            for node in ET.parse(path).iter():
                xmlid = node.get("id", "").removeprefix("smart_construction_core.")
                with self.subTest(path=str(path), xmlid=xmlid):
                    self.assertNotIn(xmlid, RETIRED_P2_FORM_VIEW_XMLIDS)
                    self.assertFalse(xmlid.startswith("view_p1_daily_business_visible_"))

if __name__ == "__main__":
    unittest.main()
