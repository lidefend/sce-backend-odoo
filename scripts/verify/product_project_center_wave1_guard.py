#!/usr/bin/env python3
"""Static guard for the P1 project-center wave-one L2/L3 contract."""
from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WAVE = ROOT / "addons/smart_construction_core/views/menu_product_project_wave1.xml"
MANIFEST = ROOT / "addons/smart_construction_core/__manifest__.py"
PROJECT = "smart_construction_core.menu_sc_project_center"
L2_RECORDS = {
    "menu_sc_project_management_group": ("项目创建", "10"),
    "menu_sc_tender_management_group": ("招投标管理", "30"),
    "menu_sc_construction_management_center": ("施工管理", "40"),
    "menu_sc_material_center": ("材料成本", "60"),
}
L3 = {
    "menu_sc_project_initiation": ("新项目立项", "smart_construction_core.menu_sc_project_management_group", "10"),
    "menu_sc_customer_partner": ("客户档案", "smart_construction_core.menu_sc_project_partner_group_wave1", "10"),
    "menu_sc_supplier_partner": ("供应商档案", "smart_construction_core.menu_sc_project_partner_group_wave1", "20"),
    "menu_sc_project_tender": ("投标项目", "smart_construction_core.menu_sc_tender_management_group", "20"),
    "menu_sc_tender_guarantee": ("投标保证金", "smart_construction_core.menu_sc_tender_management_group", "40"),
    "menu_sc_tender_won": ("中标管理", "smart_construction_core.menu_sc_tender_management_group", "50"),
    "menu_sc_safety_issue": ("安全检查", "smart_construction_core.menu_sc_construction_management_center", "10"),
    "menu_sc_project_documents": ("工程资料", "smart_construction_core.menu_sc_construction_management_center", "30"),
    "menu_sc_construction_diary": ("施工日志", "smart_construction_core.menu_sc_construction_management_center", "40"),
    "menu_sc_construction_progress": ("施工进度", "smart_construction_core.menu_sc_construction_management_center", "50"),
    "menu_sc_material_inbound": ("材料入库", "smart_construction_core.menu_sc_material_center", "10"),
    "menu_sc_material_outbound": ("材料出库", "smart_construction_core.menu_sc_material_center", "20"),
}
INCOMPLETE = {
    "menu_sc_project_quick_create",
    "menu_sc_tender_prepare",
    "menu_sc_tender_registration",
    "menu_sc_tender_registration_fee",
    "menu_sc_tender_opening",
    "menu_sc_labor_management_group",
    "menu_sc_equipment_management_group",
    "menu_sc_subcontract_management_group",
}


def _fields(node: ET.Element) -> dict[str, str]:
    return {field.attrib.get("name", ""): (field.text or "").strip() for field in node.findall("field")}


def _parent(node: ET.Element) -> str | None:
    return next((field.attrib.get("ref") for field in node.findall("field") if field.attrib.get("name") == "parent_id"), None)


def validate() -> list[str]:
    errors: list[str] = []
    if "'views/menu_product_project_wave1.xml'" not in MANIFEST.read_text(encoding="utf-8"):
        errors.append("project wave must be loaded by the industry module")
    root = ET.parse(WAVE).getroot()
    records = {node.attrib.get("id"): node for node in root.findall(".//record")}
    menuitems = {node.attrib.get("id"): node for node in root.findall(".//menuitem")}
    partner_group = menuitems.get("menu_sc_project_partner_group_wave1")
    if partner_group is None or (partner_group.attrib.get("name"), partner_group.attrib.get("parent"), partner_group.attrib.get("sequence")) != ("客商管理", PROJECT, "20"):
        errors.append("客商管理 must be a direct project-center L2 group")
    for xmlid, (name, sequence) in L2_RECORDS.items():
        node = records.get(xmlid)
        data = _fields(node) if node is not None else {}
        if node is None or (data.get("name"), _parent(node), data.get("sequence"), data.get("active")) != (name, PROJECT, sequence, "True"):
            errors.append(f"invalid project L2 group: {xmlid}")
    for xmlid, (name, parent, sequence) in L3.items():
        node = records.get(xmlid)
        data = _fields(node) if node is not None else {}
        if node is None or (data.get("name"), _parent(node), data.get("sequence"), data.get("active")) != (name, parent, sequence, "True"):
            errors.append(f"invalid released project L3 page: {xmlid}")
    for xmlid in INCOMPLETE:
        node = records.get(xmlid)
        if node is None or _fields(node).get("active") != "False":
            errors.append(f"incomplete project capability must remain unpublished: {xmlid}")
    return errors


if __name__ == "__main__":
    failures = validate()
    if failures:
        print("\n".join(f"[FAIL] {item}" for item in failures))
        sys.exit(1)
    print("[PASS] P1 project wave one uses only approved L2 groups and released L3 pages")
