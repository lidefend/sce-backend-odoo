#!/usr/bin/env python3
"""Validate the final source candidate for the locked ten primary centers."""
from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WAVE = ROOT / "addons/smart_construction_core/views/menu_product_primary_center_candidate_v1.xml"
MANIFEST = ROOT / "addons/smart_construction_core/__manifest__.py"
BASELINE = ROOT / "config/product_primary_center_baseline_v1.json"
XMLIDS = {
    "workbench": "menu_sc_workspace_center",
    "project": "menu_sc_project_center",
    "contract": "menu_sc_contract_center",
    "cost": "menu_sc_cost_center",
    "finance": "menu_sc_finance_center",
    "tax": "menu_sc_tax_center",
    "accounting": "menu_sc_accounting_center",
    "reporting": "menu_sc_data_center",
    "administration": "menu_sc_hr_admin_center",
    "product_configuration": "menu_sc_business_config_center",
}


def _fields(node: ET.Element) -> dict[str, str]:
    return {field.attrib.get("name", ""): (field.text or "").strip() for field in node.findall("field")}


def validate() -> list[str]:
    errors: list[str] = []
    manifest = MANIFEST.read_text(encoding="utf-8")
    token = "'views/menu_product_primary_center_candidate_v1.xml'"
    if token not in manifest:
        errors.append("primary-center candidate overlay must be loaded")
    elif manifest.rfind(token) < manifest.rfind("'views/menu_product_workbench_wave1.xml'"):
        errors.append("primary-center candidate overlay must load after all navigation waves")
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    expected = [(row["key"], row["name"], str(row["sequence"])) for row in baseline["primary_centers"]]
    records = {node.attrib.get("id"): node for node in ET.parse(WAVE).getroot().findall(".//record")}
    for key, name, sequence in expected:
        xmlid = XMLIDS[key]
        node = records.get(xmlid)
        data = _fields(node) if node is not None else {}
        if node is None or (data.get("name"), data.get("sequence"), data.get("active")) != (name, sequence, "True"):
            errors.append(f"primary center mismatch: {key}")
    accounting = records.get("menu_sc_accounting_center")
    if accounting is None:
        errors.append("accounting center must reserve a stable XMLID")
    else:
        data = _fields(accounting)
        action = next((field for field in accounting.findall("field") if field.attrib.get("name") == "action"), None)
        if action is None or action.attrib.get("eval") != "False" or data.get("action"):
            errors.append("accounting center must remain an actionless directory for released Odoo accounting capabilities")
    internal = records.get("menu_sc_config_center")
    if internal is None or (_fields(internal).get("name"), _fields(internal).get("sequence")) != ("系统管理（内部）", "990"):
        errors.append("system management must remain an explicitly internal non-primary entry")
    if "menu_sc_user_acceptance_root" in records:
        errors.append("customer acceptance belongs to the customer module and must not be declared by the product candidate")
    return errors


if __name__ == "__main__":
    failures = validate()
    if failures:
        print("\n".join(f"[FAIL] {item}" for item in failures))
        sys.exit(1)
    print("[PASS] source overlay locks ten runtime centers and keeps accounting as a governed directory")
