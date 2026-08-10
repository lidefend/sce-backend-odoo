#!/usr/bin/env python3
"""Static guard for P1 workbench wave-one navigation."""
from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WAVE = ROOT / "addons/smart_construction_core/views/menu_product_workbench_wave1.xml"
MANIFEST = ROOT / "addons/smart_construction_core/__manifest__.py"
PARENT = "smart_construction_core.menu_sc_workspace_center"
EXPECTED = {
    "menu_sc_operating_metrics_project": ("数据总览", "10"),
    "menu_sc_project_kanban": ("项目看板", "20"),
    "menu_sc_workbench_my_todo_fact": ("待办事项", "30"),
}


def _fields(node: ET.Element) -> dict[str, str]:
    return {field.attrib.get("name", ""): (field.text or "").strip() for field in node.findall("field")}


def validate() -> list[str]:
    errors: list[str] = []
    if "'views/menu_product_workbench_wave1.xml'" not in MANIFEST.read_text(encoding="utf-8"):
        errors.append("workbench wave must be loaded by the industry module")
    records = {node.attrib.get("id"): node for node in ET.parse(WAVE).getroot().findall(".//record")}
    for xmlid, (name, sequence) in EXPECTED.items():
        node = records.get(xmlid)
        if node is None:
            errors.append(f"missing {xmlid}")
            continue
        data = _fields(node)
        parent = next((field.attrib.get("ref") for field in node.findall("field") if field.attrib.get("name") == "parent_id"), None)
        if (data.get("name"), data.get("sequence"), data.get("active"), parent) != (name, sequence, "True", PARENT):
            errors.append(f"{xmlid} must be an active direct workbench L2 menu")
    approval = records.get("menu_sc_workbench_my_approval_fact")
    if approval is None or _fields(approval).get("active") != "False":
        errors.append("approval work must converge into the task surface instead of a duplicate menu")
    return errors


if __name__ == "__main__":
    failures = validate()
    if failures:
        print("\n".join(f"[FAIL] {item}" for item in failures))
        sys.exit(1)
    print("[PASS] P1 workbench wave one publishes three closed direct work surfaces")
