#!/usr/bin/env python3
"""Static fail-closed checks for the P1 contract-center migration wave."""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
WAVE_PATH = REPO_ROOT / "addons/smart_construction_core/views/menu_product_contract_wave1.xml"
MANIFEST_PATH = REPO_ROOT / "addons/smart_construction_core/__manifest__.py"

EXPECTED = {
    "menu_sc_p1_income_contract": ("收入合同", "smart_construction_core.action_construction_contract_income", "10", "smart_construction_core.group_sc_cap_contract_read"),
    "menu_sc_p1_expense_contract": ("支出合同", "smart_construction_core.action_construction_contract_expense", "20", "smart_construction_core.group_sc_cap_contract_read"),
    "menu_sc_p1_contract_change": ("合同变更", "smart_construction_core.action_sc_settlement_adjustment", "25", "smart_construction_core.group_sc_cap_business_initiator,smart_construction_core.group_sc_cap_settlement_read,smart_construction_core.group_sc_cap_project_read,smart_construction_core.group_sc_cap_cost_read,smart_construction_core.group_sc_cap_finance_read"),
    "menu_sc_p1_daily_contract": ("日常合同", "smart_construction_core.action_sc_general_contract", "30", "smart_construction_core.group_sc_cap_business_initiator,smart_construction_core.group_sc_cap_contract_read,smart_construction_core.group_sc_cap_contract_user,smart_construction_core.group_sc_cap_contract_manager"),
    "menu_sc_p1_income_settlement": ("收入结算", "smart_construction_core.action_sc_settlement_order_income", "50", "smart_construction_core.group_sc_cap_settlement_read"),
    "menu_sc_p1_expense_settlement": ("支出结算", "smart_construction_core.action_sc_settlement_order_expense", "60", "smart_construction_core.group_sc_cap_settlement_read"),
}


def validate() -> list[str]:
    errors: list[str] = []
    manifest = MANIFEST_PATH.read_text(encoding="utf-8")
    if "'views/menu_product_contract_wave1.xml'" not in manifest:
        errors.append("wave-one contract navigation must be loaded by the industry module")
    root = ET.parse(WAVE_PATH).getroot()
    menus = {node.attrib.get("id"): node.attrib for node in root.findall(".//menuitem")}
    for xmlid, (name, action, sequence, groups) in EXPECTED.items():
        actual = menus.get(xmlid)
        if not actual:
            errors.append(f"missing {xmlid}")
            continue
        if (actual.get("name"), actual.get("action"), actual.get("sequence"), actual.get("groups")) != (name, action, sequence, groups):
            errors.append(f"{xmlid} must keep its approved name/action/sequence/groups")
        if actual.get("parent") != "smart_construction_core.menu_sc_contract_center":
            errors.append(f"{xmlid} must be a direct contract-center L2 menu")
    text = WAVE_PATH.read_text(encoding="utf-8")
    for forbidden in ("日常合同结算", "通用合同"):
        if f'name=\"{forbidden}\"' in text:
            errors.append(f"{forbidden} must not be prematurely published in wave one")
    for legacy in ("menu_sc_construction_contract", "menu_sc_income_contract_group", "menu_sc_expense_contract_group"):
        marker = f'<record id="{legacy}" model="ir.ui.menu">\n            <field name="active">False</field>'
        if marker not in text:
            errors.append(f"legacy menu group {legacy} must be inactive, not repurposed")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("\n".join(f"[FAIL] {error}" for error in errors))
        return 1
    print("[PASS] P1 contract-center wave one uses direct L2 workspaces and preserves legacy identities")
    return 0


if __name__ == "__main__":
    sys.exit(main())
