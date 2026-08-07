#!/usr/bin/env python3
"""Validate visible navigation v2 and its truthful release checklist."""
from __future__ import annotations

import json
from pathlib import Path
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "config/product_menu_release_manifest_v2.json"
MENU_XML = ROOT / "addons/smart_construction_core/views/menu_product_navigation_v2.xml"
POLICY_SYNC = ROOT / "addons/smart_construction_core/models/support/product_policy_sync.py"
DEV_MAKE = ROOT / "make/dev.mk"

EXPECTED_CENTERS = [
    "工作台", "项目中心", "合同中心", "成本中心", "物资与分包",
    "施工管理", "财务中心", "税务中心", "报表中心", "组织行政",
]
ALLOWED_MATURITY = {"GA", "PILOT", "ROADMAP", "INTERNAL"}
REQUIRED_COST_XMLIDS = {
    "menu_sc_project_budget",
    "menu_sc_budget_alloc",
    "menu_sc_project_progress",
    "menu_sc_project_cost_ledger",
    "menu_sc_cost_reports",
    "menu_sc_profit_reports",
}


def main() -> int:
    errors: list[str] = []
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    rules = payload.get("navigation_rules") or {}
    centers = rules.get("primary_centers") or []
    if payload.get("schema") != "sce.product_menu_release_manifest.v2":
        errors.append("manifest schema mismatch")
    if centers != EXPECTED_CENTERS or rules.get("primary_center_count") != len(EXPECTED_CENTERS):
        errors.append("primary center order/count mismatch")
    if rules.get("maximum_business_depth") != 3:
        errors.append("business menu depth must be exactly 3")

    checklist = payload.get("capability_release_checklist") or []
    if not checklist:
        errors.append("capability release checklist is empty")
    for index, row in enumerate(checklist):
        if row.get("maturity") not in ALLOWED_MATURITY:
            errors.append(f"checklist[{index}] invalid maturity")
        if not row.get("scope") or not row.get("evidence"):
            errors.append(f"checklist[{index}] missing scope/evidence")
        if row.get("maturity") != "GA" and not row.get("promotion_requirements"):
            errors.append(f"checklist[{index}] non-GA item missing promotion requirements")

    gaps = payload.get("benchmark_gap_backlog") or []
    if len(gaps) < 6 or not any(row.get("priority") == "P0" and row.get("status") != "DONE" for row in gaps):
        errors.append("benchmark gap backlog must retain real open P0 gaps")

    xml = MENU_XML.read_text(encoding="utf-8")
    xml_root = ElementTree.fromstring(xml)
    policy = POLICY_SYNC.read_text(encoding="utf-8")
    dev_make = DEV_MAKE.read_text(encoding="utf-8")
    for center in EXPECTED_CENTERS:
        if f">{center}</field>" not in xml:
            errors.append(f"visible menu XML missing center: {center}")
    cost_records = [
        record for record in xml_root.findall("record")
        if record.get("id") == "menu_sc_cost_center"
    ]
    cost_parent_refs = [
        field.get("ref") for record in cost_records
        for field in record.findall("field") if field.get("name") == "parent_id"
    ]
    if cost_parent_refs != ["smart_construction_core.menu_sc_root"]:
        errors.append("cost center is not explicitly rooted in the product application")
    for xmlid in REQUIRED_COST_XMLIDS:
        token = f'"smart_construction_core.{xmlid}"'
        if token not in policy:
            errors.append(f"released cost capability missing from policy: {xmlid}")
    for group in ("进度与施工", "质量管理", "安全管理", "行政审批", "人事薪酬"):
        if f'name="{group}"' not in xml:
            errors.append(f"level-two product group missing: {group}")
    for token in (
        "release.daily_product_navigation.snapshot:",
        'test "$(ENV)" = "dev"',
        'test "$(DB_NAME)" = "sc_demo"',
        "CONFIRM_DAILY_PRODUCT_NAVIGATION_SNAPSHOT",
        "initialize_colocated_platform_snapshot.py",
    ):
        if token not in dev_make:
            errors.append(f"daily navigation release boundary missing: {token}")

    if errors:
        print("[product_menu_release_manifest_v2_guard] FAIL")
        for error in errors:
            print(f"- {error}")
        return 2
    print(
        "[product_menu_release_manifest_v2_guard] PASS "
        f"centers={len(centers)} checklist={len(checklist)} gaps={len(gaps)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
