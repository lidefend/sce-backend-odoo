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
ODOO_SHELL_EXEC = ROOT / "scripts/ops/odoo_shell_exec.sh"

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
REQUIRED_REPORT_XMLIDS = {
    "menu_sc_project_operation_statistics_report",
    "menu_sc_company_operation_summary_report",
}
EXPECTED_PROJECT_LEVEL_TWO = [
    "项目总览", "项目前期", "项目立项", "项目台账", "项目组织",
    "里程碑管理", "项目协同", "项目资料", "风险与问题", "项目收尾",
]
ALLOWED_PROJECT_RELEASE_STATUS = {"RELEASED", "READY_TO_CONVERGE", "FOLLOWUP"}


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

    project_ia = payload.get("project_center_information_architecture") or {}
    project_level_two = project_ia.get("level_two_order") or []
    project_level_two_names = [row.get("name") for row in project_level_two]
    if project_ia.get("locked") is not True:
        errors.append("project center information architecture must be locked")
    if project_ia.get("empty_roadmap_menus_visible_to_business_users") is not False:
        errors.append("empty project roadmap menus must stay out of business navigation")
    if project_level_two_names != EXPECTED_PROJECT_LEVEL_TWO:
        errors.append("project center level-two order mismatch")
    for index, row in enumerate(project_level_two):
        status = row.get("release_status")
        if status not in ALLOWED_PROJECT_RELEASE_STATUS:
            errors.append(f"project level-two[{index}] invalid release status")
        if status == "FOLLOWUP" and not row.get("launch_note"):
            errors.append(f"project level-two[{index}] follow-up item missing launch note")

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
    shell_exec = ODOO_SHELL_EXEC.read_text(encoding="utf-8")
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
    for xmlid in REQUIRED_REPORT_XMLIDS:
        token = f'"smart_construction_core.{xmlid}"'
        if token not in policy:
            errors.append(f"released reporting capability missing from policy: {xmlid}")
    for group in ("进度与施工", "质量管理", "安全管理", "行政审批", "人事薪酬"):
        if f'name="{group}"' not in xml:
            errors.append(f"level-two product group missing: {group}")
    for group in EXPECTED_PROJECT_LEVEL_TWO:
        if (
            f'name="{group}"' not in xml
            and f'name="{group}（后续上线）"' not in xml
            and f'>{group}</field>' not in xml
        ):
            errors.append(f"locked project level-two group missing: {group}")
    for group in [row["name"] for row in project_level_two if row.get("release_status") == "FOLLOWUP"]:
        if f'name="{group}（后续上线）"' not in xml:
            errors.append(f"follow-up project group missing launch label: {group}")
    for token in (
        "release.daily_product_navigation.snapshot:",
        'test "$(ENV)" = "dev"',
        'test "$(DB_NAME)" = "sc_demo"',
        "CONFIRM_DAILY_PRODUCT_NAVIGATION_SNAPSHOT",
        "initialize_colocated_platform_snapshot.py",
    ):
        if token not in dev_make:
            errors.append(f"daily navigation release boundary missing: {token}")
    for token in ("PLATFORM_RELEASE_*", "SC_COLOCATED_PLATFORM_SNAPSHOT_APPLY"):
        if token not in shell_exec:
            errors.append(f"daily navigation release env forwarding missing: {token}")

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
