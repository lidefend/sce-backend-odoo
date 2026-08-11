#!/usr/bin/env python3
"""Static guard for tax-center P1 wave-one navigation."""
from __future__ import annotations
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WAVE = ROOT / "addons/smart_construction_core/views/menu_product_tax_wave1.xml"
MANIFEST = ROOT / "addons/smart_construction_core/__manifest__.py"
EXPECTED = {
    "menu_sc_tax_certificate_registration_user": ("外经证", "10"),
    "menu_sc_invoice_prepaid_tax_user": ("预缴登记", "20"),
    "menu_sc_invoice_application_user": ("开票申请", "30"),
    "menu_sc_invoice_registration_user": ("销项开票", "40"),
    "menu_sc_output_invoice_change_registration": ("发票红冲", "50"),
    "menu_sc_invoice_input": ("进项发票", "60"),
    "menu_sc_tax_deduction_registration_user": ("税额抵扣", "70"),
}

def values(node: ET.Element) -> tuple[str, str, str, str | None]:
    data = {field.attrib.get("name"): (field.text or "").strip() for field in node.findall("field")}
    parent = next((field.attrib.get("ref") for field in node.findall("field") if field.attrib.get("name") == "parent_id"), None)
    return data.get("name", ""), data.get("sequence", ""), data.get("active", ""), parent

def validate() -> list[str]:
    errors: list[str] = []
    if "'views/menu_product_tax_wave1.xml'" not in MANIFEST.read_text(encoding="utf-8"):
        errors.append("tax wave must be loaded by the industry module")
    records = {node.attrib.get("id"): node for node in ET.parse(WAVE).getroot().findall(".//record")}
    for xmlid, (name, sequence) in EXPECTED.items():
        node = records.get(xmlid)
        if node is None:
            errors.append(f"missing {xmlid}")
        elif values(node) != (name, sequence, "True", "smart_construction_core.menu_sc_tax_center"):
            errors.append(f"{xmlid} must be an active direct tax-center L2 menu")
    visible = {name for name, _ in EXPECTED.values()}
    if visible & {"项目专项抵扣", "税务申报"}:
        errors.append("incomplete tax capabilities must remain unpublished")
    return errors

if __name__ == "__main__":
    failures = validate()
    if failures:
        print("\n".join(f"[FAIL] {item}" for item in failures)); sys.exit(1)
    print("[PASS] P1 tax-center wave one preserves identities and publishes only closed tax facts")
