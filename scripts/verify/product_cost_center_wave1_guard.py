#!/usr/bin/env python3
"""Static fail-closed checks for P1 cost-center wave-one navigation."""
from __future__ import annotations
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WAVE_PATH = REPO_ROOT / "addons/smart_construction_core/views/menu_product_cost_wave1.xml"
MANIFEST_PATH = REPO_ROOT / "addons/smart_construction_core/__manifest__.py"
EXPECTED = {
    "menu_sc_p1_project_budget": ("项目预算", "smart_construction_core.action_project_budget", "10", "smart_construction_core.group_sc_cap_cost_user,smart_construction_core.group_sc_cap_cost_manager"),
    "menu_sc_p1_cost_plan": ("成本计划编制", "smart_construction_core.action_project_cost_plan", "20", "smart_construction_core.group_sc_cap_cost_user,smart_construction_core.group_sc_cap_cost_manager"),
    "menu_sc_p1_cost_ledger": ("成本归集", "smart_construction_core.action_project_cost_ledger", "30", "smart_construction_core.group_sc_cap_cost_user,smart_construction_core.group_sc_cap_cost_manager"),
    "menu_sc_p1_profit_analysis": ("项目盈亏分析", "smart_construction_core.action_project_profit_compare", "40", "smart_construction_core.group_sc_cap_cost_user,smart_construction_core.group_sc_cap_cost_manager"),
}

def validate() -> list[str]:
    errors: list[str] = []
    if "'views/menu_product_cost_wave1.xml'" not in MANIFEST_PATH.read_text(encoding="utf-8"):
        errors.append("wave-one cost navigation must be loaded by the industry module")
    root = ET.parse(WAVE_PATH).getroot()
    menus = {node.attrib.get("id"): node.attrib for node in root.findall(".//menuitem")}
    for xmlid, expected in EXPECTED.items():
        actual = menus.get(xmlid)
        if not actual:
            errors.append(f"missing {xmlid}")
        elif (actual.get("name"), actual.get("action"), actual.get("sequence"), actual.get("groups")) != expected:
            errors.append(f"{xmlid} must keep approved name/action/sequence/groups")
        elif actual.get("parent") != "smart_construction_core.menu_sc_cost_center":
            errors.append(f"{xmlid} must be a direct cost-center L2 menu")
    text = WAVE_PATH.read_text(encoding="utf-8")
    for legacy in ("menu_sc_cost_target_budget_group", "menu_sc_cost_dynamic_group", "menu_sc_cost_analysis_group_v2"):
        if f'<record id="{legacy}" model="ir.ui.menu"><field name="active">False</field></record>' not in text:
            errors.append(f"legacy group {legacy} must be inactive, not repurposed")
    return errors

if __name__ == "__main__":
    failures = validate()
    if failures:
        print("\n".join(f"[FAIL] {item}" for item in failures))
        sys.exit(1)
    print("[PASS] P1 cost-center wave one uses direct L2 workspaces and preserves legacy identities")
