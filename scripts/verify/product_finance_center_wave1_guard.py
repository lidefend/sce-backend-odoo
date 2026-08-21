#!/usr/bin/env python3
"""Static guard for finance-center P1 wave-one navigation."""
from __future__ import annotations
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WAVE = ROOT / "addons/smart_construction_core/views/menu_product_finance_wave1.xml"
MANIFEST = ROOT / "addons/smart_construction_core/__manifest__.py"
NAVIGATION = ROOT / "config/frontend/authoritative_navigation.json"
FORMAL_PAYMENT_MENU = "smart_construction_core.menu_sc_user_payment_apply"
RETIRED_PAYMENT_MENU = "smart_construction_core.menu_sc_user_payment_apply_acceptance"
EXPECTED = {
    "menu_sc_receipt_income": ("收款登记", "10"),
    "menu_sc_user_payment_apply": ("付款申请", "20"),
    "menu_sc_payment_execution": ("实付登记", "30"),
    "menu_sc_reimbursement_request": ("费用报销", "40"),
    "menu_sc_user_income": ("公司收入", "60"),
    "menu_sc_company_finance_expense": ("公司支出", "70"),
    "menu_sc_deduction_bill": ("公司&项目扣款", "80"),
    "menu_sc_advance_fund": ("备用金", "100"),
    "menu_sc_funding_plan_summary": ("资金汇总", "110"),
}

def fields(node: ET.Element) -> dict[str, str]:
    return {item.attrib.get("name", ""): (item.text or "").strip() for item in node.findall("field")}

def validate() -> list[str]:
    errors: list[str] = []
    manifest = MANIFEST.read_text(encoding="utf-8")
    wave_marker = "'views/menu_product_finance_wave1.xml'"
    taxonomy_marker = "'views/menu_business_taxonomy.xml'"
    cleanup_marker = "'views/menu_user_acceptance_cleanup.xml'"
    if wave_marker not in manifest:
        errors.append("finance wave must be loaded by the industry module")
    elif not (
        manifest.find(taxonomy_marker) < manifest.find(wave_marker)
        and manifest.find(cleanup_marker) < manifest.find(wave_marker)
    ):
        errors.append("finance wave must load after historical taxonomy and acceptance cleanup")
    root = ET.parse(WAVE).getroot()
    records = {node.attrib.get("id"): node for node in root.findall(".//record")}
    for xmlid, (name, sequence) in EXPECTED.items():
        node = records.get(xmlid)
        if node is None:
            errors.append(f"missing {xmlid}")
            continue
        values = fields(node)
        parent = next((item.attrib.get("ref") for item in node.findall("field") if item.attrib.get("name") == "parent_id"), None)
        if (values.get("name"), values.get("sequence"), values.get("active"), parent) != (name, sequence, "True", "smart_construction_core.menu_sc_finance_center"):
            errors.append(f"{xmlid} must be an active direct finance-center L2 menu")
    retired = records.get("menu_sc_user_payment_apply_acceptance")
    if retired is None or fields(retired).get("active") != "False":
        errors.append("payment-request acceptance alias must be inactive in the final finance wave")
    navigation = NAVIGATION.read_text(encoding="utf-8")
    if RETIRED_PAYMENT_MENU in navigation:
        errors.append("authoritative navigation must not reference the retired payment-request acceptance alias")
    if FORMAL_PAYMENT_MENU not in navigation:
        errors.append("authoritative navigation must reference the formal payment-request menu")
    visible_names = {name for name, _ in EXPECTED.values()}
    if "往来款登记" in visible_names or "公司&项目退款" in visible_names:
        errors.append("incomplete finance adapters must not be published in wave one")
    return errors

if __name__ == "__main__":
    failures = validate()
    if failures:
        print("\n".join(f"[FAIL] {item}" for item in failures)); sys.exit(1)
    print("[PASS] P1 finance-center wave one preserves menu/action identities and direct L2 depth")
