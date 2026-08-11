#!/usr/bin/env python3
"""Static guard for administration-center P1 wave-one navigation."""
from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WAVE = ROOT / "addons/smart_construction_core/views/menu_product_administration_wave1.xml"
MANIFEST = ROOT / "addons/smart_construction_core/__manifest__.py"
ADMIN_PARENT = "smart_construction_core.menu_sc_hr_admin_center"
EXPECTED_RECORD_MENUS = {
    "menu_sc_organization_department": ("部门管理", "10"),
    "menu_sc_runtime_user_management": ("人员档案", "30"),
    "menu_sc_certificate_registration": ("证书管理", "40"),
}
UNPUBLISHED = {
    "menu_sc_social_person_registration",
    "menu_sc_social_registration",
    "menu_sc_company_document_archive",
    "menu_sc_document_borrow",
}


def _fields(node: ET.Element) -> dict[str, str]:
    return {field.attrib.get("name", ""): (field.text or "").strip() for field in node.findall("field")}


def validate() -> list[str]:
    errors: list[str] = []
    if "'views/menu_product_administration_wave1.xml'" not in MANIFEST.read_text(encoding="utf-8"):
        errors.append("administration wave must be loaded by the industry module")
    root = ET.parse(WAVE).getroot()
    records = {node.attrib.get("id"): node for node in root.findall(".//record")}
    menuitems = {node.attrib.get("id"): node for node in root.findall(".//menuitem")}
    center = records.get("menu_sc_hr_admin_center")
    if center is None or (_fields(center).get("name"), _fields(center).get("sequence")) != ("行政中心", "90"):
        errors.append("administration center must use the locked primary-center name and sequence")
    for xmlid, (name, sequence) in EXPECTED_RECORD_MENUS.items():
        node = records.get(xmlid)
        if node is None:
            errors.append(f"missing {xmlid}")
            continue
        data = _fields(node)
        parent = next((field.attrib.get("ref") for field in node.findall("field") if field.attrib.get("name") == "parent_id"), None)
        if (data.get("name"), data.get("sequence"), data.get("active"), parent) != (name, sequence, "True", ADMIN_PARENT):
            errors.append(f"{xmlid} must be an active direct administration-center L2 menu")
    payroll_action = records.get("action_sc_payroll_management")
    payroll_menu = menuitems.get("menu_sc_payroll_management")
    if payroll_action is None or payroll_menu is None:
        errors.append("工资薪酬 requires one secured aggregate action and direct L2 menu")
    else:
        action = _fields(payroll_action)
        domain = action.get("domain", "")
        if action.get("res_model") != "sc.hr.payroll.document" or any(item not in domain for item in ("salary_registration", "subsidy", "bonus")):
            errors.append("工资薪酬 action must aggregate salary, subsidy and bonus facts")
        if payroll_menu.attrib.get("parent") != ADMIN_PARENT or payroll_menu.attrib.get("sequence") != "60":
            errors.append("工资薪酬 must be a direct administration-center L2 menu")
    for xmlid in UNPUBLISHED:
        node = records.get(xmlid)
        if node is None or _fields(node).get("active") != "False":
            errors.append(f"incomplete administration capability must remain unpublished: {xmlid}")
    return errors


if __name__ == "__main__":
    failures = validate()
    if failures:
        print("\n".join(f"[FAIL] {item}" for item in failures))
        sys.exit(1)
    print("[PASS] P1 administration wave one publishes only closed people/admin facts")
