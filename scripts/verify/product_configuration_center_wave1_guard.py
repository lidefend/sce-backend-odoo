#!/usr/bin/env python3
"""Static guard for product-configuration P1 wave-one navigation."""
from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WAVE = ROOT / "addons/smart_construction_core/views/menu_product_configuration_wave1.xml"
MANIFEST = ROOT / "addons/smart_construction_core/__manifest__.py"
PARENT = "smart_construction_core.menu_sc_business_config_center"
EXPECTED = {
    "menu_sc_business_config_workbench": ("表单配置", "10"),
    "menu_sc_approval_policy": ("流程审批配置", "20"),
    "menu_ui_form_field_policy_business_config": ("字段管理", "30"),
}
SOURCE_BINDINGS = {
    "menu_sc_business_config_workbench": (
        ROOT / "addons/smart_construction_core/views/support/business_config_workbench_views.xml",
        "action_sc_business_config_workbench",
    ),
    "menu_sc_approval_policy": (
        ROOT / "addons/smart_construction_core/views/support/approval_policy_views.xml",
        "action_sc_approval_policy",
    ),
    "menu_ui_form_field_policy_business_config": (
        ROOT / "addons/smart_construction_core/views/support/form_field_policy_views.xml",
        "action_ui_form_field_policy_business_config",
    ),
}


def _fields(node: ET.Element) -> dict[str, str]:
    return {field.attrib.get("name", ""): (field.text or "").strip() for field in node.findall("field")}


def validate() -> list[str]:
    errors: list[str] = []
    if "'views/menu_product_configuration_wave1.xml'" not in MANIFEST.read_text(encoding="utf-8"):
        errors.append("product-configuration wave must be loaded by the industry module")
    records = {node.attrib.get("id"): node for node in ET.parse(WAVE).getroot().findall(".//record")}
    center = records.get("menu_sc_business_config_center")
    if center is None or (_fields(center).get("name"), _fields(center).get("sequence")) != ("产品配置", "100"):
        errors.append("product-configuration center must use the locked name and sequence")
    for xmlid, (name, sequence) in EXPECTED.items():
        node = records.get(xmlid)
        if node is None:
            errors.append(f"missing {xmlid}")
            continue
        data = _fields(node)
        parent = next((field.attrib.get("ref") for field in node.findall("field") if field.attrib.get("name") == "parent_id"), None)
        if (data.get("name"), data.get("sequence"), data.get("active"), parent) != (name, sequence, "True", PARENT):
            errors.append(f"{xmlid} must be an active direct product-configuration L2 menu")
        source, action_xmlid = SOURCE_BINDINGS[xmlid]
        source_text = source.read_text(encoding="utf-8")
        if f'id="{xmlid}"' not in source_text or f'id="{action_xmlid}"' not in source_text:
            errors.append(f"{xmlid} must preserve its secured source action identity")
    custom_field = records.get("menu_ui_form_custom_field_wizard_business_config")
    if custom_field is None or _fields(custom_field).get("active") != "False":
        errors.append("custom-field creation must be an operation inside field management, not a menu")
    return errors


if __name__ == "__main__":
    failures = validate()
    if failures:
        print("\n".join(f"[FAIL] {item}" for item in failures))
        sys.exit(1)
    print("[PASS] P1 product-configuration wave one exposes three governed configuration surfaces")
