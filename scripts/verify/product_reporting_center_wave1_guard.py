#!/usr/bin/env python3
"""Static guard for reporting-center P1 wave-one navigation."""
from __future__ import annotations
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WAVE = ROOT / "addons/smart_construction_core/views/menu_product_reporting_wave1.xml"
MANIFEST = ROOT / "addons/smart_construction_core/__manifest__.py"
EXPECTED = {
    "menu_sc_project_operation_statistics_report": ("项目报表", "10"),
    "menu_sc_comprehensive_cost_statistics_report": ("成本报表", "20"),
    "menu_sc_fund_daily_summary": ("资金报表", "30"),
}

def validate() -> list[str]:
    errors: list[str] = []
    if "'views/menu_product_reporting_wave1.xml'" not in MANIFEST.read_text(encoding="utf-8"):
        errors.append("reporting wave must be loaded by the industry module")
    records = {node.attrib.get("id"): node for node in ET.parse(WAVE).getroot().findall(".//record")}
    for xmlid, (name, sequence) in EXPECTED.items():
        node = records.get(xmlid)
        if node is None:
            errors.append(f"missing {xmlid}"); continue
        data = {field.attrib.get("name"): (field.text or "").strip() for field in node.findall("field")}
        parent = next((field.attrib.get("ref") for field in node.findall("field") if field.attrib.get("name") == "parent_id"), None)
        if (data.get("name"), data.get("sequence"), data.get("active"), parent) != (name, sequence, "True", "smart_construction_core.menu_sc_data_center"):
            errors.append(f"{xmlid} must be an active direct report-center L2 menu")
    visible = {item[0] for item in EXPECTED.values()}
    if visible & {"税务报表", "劳务分包报表"}:
        errors.append("partial report domains must remain unpublished")
    return errors

if __name__ == "__main__":
    failures = validate()
    if failures:
        print("\n".join(f"[FAIL] {item}" for item in failures)); sys.exit(1)
    print("[PASS] P1 report-center wave one publishes only unified drillable report facts")
