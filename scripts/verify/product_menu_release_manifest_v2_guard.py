#!/usr/bin/env python3
"""Validate visible navigation v2 and its truthful release checklist."""
from __future__ import annotations

import json
from pathlib import Path
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "config/product_menu_release_manifest_v2.json"
LOCKED_BASELINE = ROOT / "scripts/verify/baselines/formal_business_product_menu_policy_v1.json"
MENU_XML = ROOT / "addons/smart_construction_core/views/menu_product_navigation_v2.xml"
BASE_MENU_XML = ROOT / "addons/smart_construction_core/views/menu.xml"
NATIVE_MENU_LOAD_ORDER = [
    ROOT / "addons/smart_construction_core/views/menu_business_taxonomy_groups.xml",
    BASE_MENU_XML,
    ROOT / "addons/smart_construction_core/views/support/menu_config_policy_views.xml",
    ROOT / "addons/smart_construction_core/views/menu_business_taxonomy.xml",
    ROOT / "addons/smart_construction_core/views/menu_user_acceptance_cleanup.xml",
    MENU_XML,
]
POLICY_SYNC = ROOT / "addons/smart_construction_core/models/support/product_policy_sync.py"
HOOK_FACTS = ROOT / "addons/smart_construction_core/core_extension_hook_facts.py"
MENU_SERVICE = ROOT / "addons/smart_core/delivery/menu_service.py"
DEV_MAKE = ROOT / "make/dev.mk"
ODOO_SHELL_EXEC = ROOT / "scripts/ops/odoo_shell_exec.sh"
ACCEPTANCE_ENVIRONMENTS = ROOT / "config/frontend/acceptance_environments_v1.json"

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
EXPECTED_FOLLOWUP_BY_CENTER = {
    "合同中心": ["履约与预警"],
    "成本中心": ["成本预测", "现金流预测"],
    "物资与分包": ["供应链协同"],
    "施工管理": ["现场移动", "BIM协同"],
    "财务中心": ["资金预测"],
    "税务中心": ["税务申报", "发票查验"],
    "报表中心": ["预测预警"],
    "组织行政": ["人员生命周期", "资源能力"],
}


def main() -> int:
    errors: list[str] = []
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    locked_baseline = json.loads(LOCKED_BASELINE.read_text(encoding="utf-8"))
    acceptance_environments = json.loads(ACCEPTANCE_ENVIRONMENTS.read_text(encoding="utf-8"))
    rules = payload.get("navigation_rules") or {}
    centers = rules.get("primary_centers") or []
    if payload.get("schema") != "sce.product_menu_release_manifest.v2":
        errors.append("manifest schema mismatch")
    if centers != EXPECTED_CENTERS or rules.get("primary_center_count") != len(EXPECTED_CENTERS):
        errors.append("primary center order/count mismatch")
    if rules.get("maximum_business_depth") != 3:
        errors.append("business menu depth must be exactly 3")
    if rules.get("followup_menu_sibling_position") != "last":
        errors.append("follow-up menus must be placed last within each sibling group")
    strategy = locked_baseline.get("policy_strategy") or {}
    if strategy.get("mode") != "FULL_FORMAL_PRODUCT_SCOPE":
        errors.append("locked product policy must declare full formal product scope")
    if strategy.get("effective_menu_count_per_product") != 150:
        errors.append("locked product policy must record the exact full menu count")
    if strategy.get("effective_capability_count_per_product") != 150:
        errors.append("locked product policy must record the exact full capability count")
    required_full_scope_xmlids = {
        "smart_construction_core.menu_sc_workbench_my_todo_fact",
        "smart_construction_core.menu_sc_workbench_my_approval_fact",
        "smart_construction_core.menu_sc_construction_progress",
        "smart_construction_core.menu_sc_quality_standard_v2",
        "smart_construction_core.menu_sc_quality_issue",
        "smart_construction_core.menu_sc_quality_rectification",
        "smart_construction_core.menu_sc_quality_recheck",
        "smart_construction_core.menu_sc_quality_site_photo_v2",
        "smart_construction_core.menu_sc_safety_plan_v2",
        "smart_construction_core.menu_sc_safety_disclosure_v2",
        "smart_construction_core.menu_sc_safety_risk_library_v2",
        "smart_construction_core.menu_sc_safety_hazard_source_v2",
        "smart_construction_core.menu_sc_safety_patrol_v2",
        "smart_construction_core.menu_sc_safety_issue",
        "smart_construction_core.menu_sc_safety_rectification",
        "smart_construction_core.menu_sc_safety_recheck",
    }
    full_baseline_xmlids = set()
    for product in locked_baseline.get("products") or []:
        rows = [menu for group in product.get("menu_groups") or [] for menu in group.get("menus") or []]
        xmlids = {menu.get("menu_xmlid") for menu in rows}
        full_baseline_xmlids.update(xmlids)
        if len(rows) != 150 or len(xmlids) != 150:
            errors.append(f"{product.get('product_key')} full baseline must contain 150 unique menus")
        capabilities = product.get("capabilities") or []
        capability_xmlids = {row.get("menu_xmlid") for row in capabilities}
        if len(capabilities) != 150 or capability_xmlids != xmlids:
            errors.append(f"{product.get('product_key')} capabilities must exactly match the full menu baseline")
        missing_xmlids = sorted(required_full_scope_xmlids - xmlids)
        if missing_xmlids:
            errors.append(f"{product.get('product_key')} missing full construction scope: {missing_xmlids}")
    daily_navigation = (
        ((acceptance_environments.get("profiles") or {}).get("daily") or {}).get("navigation_policy") or {}
    )
    if daily_navigation.get("max_actions") != 159:
        errors.append("daily acceptance maximum must lock the 159-action full user surface")
    daily_required_paths = set(daily_navigation.get("required_paths") or [])
    for path in (
        "系统菜单 / 施工管理 / 质量管理 / 质量标准",
        "系统菜单 / 施工管理 / 质量管理 / 现场影像",
        "系统菜单 / 施工管理 / 安全管理 / 安全方案",
        "系统菜单 / 施工管理 / 安全管理 / 安全巡检",
        "系统菜单 / 施工管理 / 安全管理 / 安全复验",
    ):
        if path not in daily_required_paths:
            errors.append(f"daily acceptance missing full construction path: {path}")

    project_ia = payload.get("project_center_information_architecture") or {}
    project_level_two = project_ia.get("level_two_order") or []
    project_level_two_names = [row.get("name") for row in project_level_two]
    if project_ia.get("locked") is not True:
        errors.append("project center information architecture must be locked")
    if project_ia.get("empty_roadmap_menus_visible_to_business_users") is not False:
        errors.append("empty project roadmap menus must stay out of business navigation")
    if project_ia.get("roadmap_menus_visible_roles") != ["business_config_admin"]:
        errors.append("project roadmap menus must be restricted to business_config_admin")
    if project_level_two_names != EXPECTED_PROJECT_LEVEL_TWO:
        errors.append("project center level-two order mismatch")
    for index, row in enumerate(project_level_two):
        status = row.get("release_status")
        if status not in ALLOWED_PROJECT_RELEASE_STATUS:
            errors.append(f"project level-two[{index}] invalid release status")
        if status == "FOLLOWUP" and not row.get("launch_note"):
            errors.append(f"project level-two[{index}] follow-up item missing launch note")

    center_ia = payload.get("center_information_architecture") or {}
    if list(center_ia) != list(EXPECTED_FOLLOWUP_BY_CENTER):
        errors.append("cross-center information architecture order mismatch")
    for center, followup_names in EXPECTED_FOLLOWUP_BY_CENTER.items():
        architecture = center_ia.get(center) or {}
        rows = architecture.get("level_two_order") or []
        if architecture.get("locked") is not True or not rows:
            errors.append(f"{center} information architecture must be locked and non-empty")
            continue
        actual_followup = [row.get("name") for row in rows if row.get("release_status") == "FOLLOWUP"]
        if actual_followup != followup_names:
            errors.append(f"{center} follow-up capability order mismatch")
        for row in rows:
            if row.get("release_status") not in ALLOWED_PROJECT_RELEASE_STATUS:
                errors.append(f"{center} invalid release status: {row.get('name')}")
            if row.get("release_status") == "FOLLOWUP" and not row.get("launch_note"):
                errors.append(f"{center} follow-up item missing launch note: {row.get('name')}")
    material_rows = (center_ia.get("物资与分包") or {}).get("level_two_order") or []
    if any(row.get("name") == "材料计划" for row in material_rows):
        errors.append("material plan must not remain a material-center level-two domain")
    material_management = next((row for row in material_rows if row.get("name") == "材料管理"), {})
    if "材料计划" not in (material_management.get("child_pages") or []):
        errors.append("material plan must be locked as a child page of material management")

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
    base_menu_root = ElementTree.parse(BASE_MENU_XML).getroot()
    policy = POLICY_SYNC.read_text(encoding="utf-8")
    hook_facts = HOOK_FACTS.read_text(encoding="utf-8")
    menu_service = MENU_SERVICE.read_text(encoding="utf-8")
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
    center_sequence = {}
    for record in xml_root.findall("record"):
        record_id = record.get("id")
        for field in record.findall("field"):
            if field.get("name") == "sequence" and (field.text or "").strip().isdigit():
                center_sequence[record_id] = int((field.text or "0").strip())
    if center_sequence.get("menu_sc_contract_center") + 10 != center_sequence.get("menu_sc_cost_center"):
        errors.append("cost center must be sequenced immediately after contract center")
    for xmlid in REQUIRED_COST_XMLIDS:
        if f"smart_construction_core.{xmlid}" not in full_baseline_xmlids:
            errors.append(f"released cost capability missing from policy: {xmlid}")
    for xmlid in REQUIRED_REPORT_XMLIDS:
        if f"smart_construction_core.{xmlid}" not in full_baseline_xmlids:
            errors.append(f"released reporting capability missing from policy: {xmlid}")
    for token in (
        '"smart_construction_core.menu_sc_project_project": "项目台账"',
        '"smart_construction_core.menu_sc_tender_registration": "项目前期"',
        '"smart_construction_core.menu_sc_tender_registration_fee": "项目前期"',
        '"project_center_locked_level_two_projection"',
    ):
        if token not in policy:
            errors.append(f"project center delivery projection missing: {token}")
    base_material_plan = next(
        (node for node in base_menu_root.findall("menuitem") if node.get("id") == "menu_project_material_plan"),
        None,
    )
    if base_material_plan is None:
        errors.append("base material-plan menu is missing")
    elif base_material_plan.get("parent") != "menu_sc_material_management_group":
        errors.append("base material-plan menu must belong to material management")

    # Rebuild the final native menu facts in module load order. Policy may
    # expose or hide these facts, but must never invent a different hierarchy.
    native_facts = {}
    for source in NATIVE_MENU_LOAD_ORDER:
        root = ElementTree.parse(source).getroot()
        for node in root.iter():
            menu_id = node.get("id")
            if not menu_id or node.tag not in {"menuitem", "record"}:
                continue
            if node.tag == "record" and node.get("model") != "ir.ui.menu":
                continue
            fact = native_facts.setdefault(menu_id, {})
            if node.tag == "menuitem":
                if node.get("name"):
                    fact["name"] = node.get("name")
                if node.get("parent"):
                    fact["parent"] = node.get("parent").split(".")[-1]
            else:
                for field in node.findall("field"):
                    if field.get("name") == "name" and (field.text or "").strip():
                        fact["name"] = (field.text or "").strip()
                    if field.get("name") == "parent_id" and field.get("ref"):
                        fact["parent"] = field.get("ref").split(".")[-1]
    required_native_parents = {
        "menu_project_material_plan": "menu_sc_material_management_group",
        "menu_sc_general_contract": "menu_sc_expense_contract_group",
        "menu_sc_project_budget": "menu_sc_cost_target_budget_group",
        "menu_sc_construction_diary": "menu_sc_schedule_delivery_group_v2",
        "menu_sc_construction_progress": "menu_sc_schedule_delivery_group_v2",
        "menu_sc_quality_standard_v2": "menu_sc_quality_delivery_group_v2",
        "menu_sc_quality_issue": "menu_sc_quality_delivery_group_v2",
        "menu_sc_quality_rectification": "menu_sc_quality_delivery_group_v2",
        "menu_sc_quality_recheck": "menu_sc_quality_delivery_group_v2",
        "menu_sc_quality_site_photo_v2": "menu_sc_quality_delivery_group_v2",
        "menu_sc_safety_plan_v2": "menu_sc_safety_delivery_group_v2",
        "menu_sc_safety_disclosure_v2": "menu_sc_safety_delivery_group_v2",
        "menu_sc_safety_risk_library_v2": "menu_sc_safety_delivery_group_v2",
        "menu_sc_safety_hazard_source_v2": "menu_sc_safety_delivery_group_v2",
        "menu_sc_safety_patrol_v2": "menu_sc_safety_delivery_group_v2",
        "menu_sc_safety_issue": "menu_sc_safety_delivery_group_v2",
        "menu_sc_safety_rectification": "menu_sc_safety_delivery_group_v2",
        "menu_sc_safety_recheck": "menu_sc_safety_delivery_group_v2",
        "menu_sc_user_payment_apply_acceptance": "menu_sc_payment_user_group",
        "menu_sc_fund_daily_user_report": "menu_sc_fund_account_group",
        "menu_sc_invoice_input": "menu_sc_invoice_tax_user_group",
        "menu_ui_menu_config_policy_business_config": "menu_sc_lowcode_system_config_group",
    }
    for menu_id, parent_id in required_native_parents.items():
        if native_facts.get(menu_id, {}).get("parent") != parent_id:
            errors.append(f"native hierarchy mismatch: {menu_id} must belong to {parent_id}")
    required_native_names = {
        "menu_sc_expense_contract_group": "合同管理",
        "menu_sc_cost_target_budget_group": "目标与预算",
        "menu_sc_cost_dynamic_group": "动态成本",
        "menu_sc_cost_analysis_group_v2": "成本分析",
        "menu_sc_payment_user_group": "付款管理",
        "menu_sc_fund_account_group": "账户资金",
        "menu_sc_invoice_tax_user_group": "发票管理",
    }
    for menu_id, name in required_native_names.items():
        if native_facts.get(menu_id, {}).get("name") != name:
            errors.append(f"native menu name mismatch: {menu_id} must be {name}")
    if "path_authority" in policy or "NATIVE_MENU_PATH_AUTHORITY_XMLIDS" in policy:
        errors.append("per-menu path authority forks are forbidden")
    locked_contract = (ROOT / "addons/smart_construction_core/services/locked_menu_policy_contract.py").read_text(encoding="utf-8")
    for forbidden in (
        "PRODUCT_NAVIGATION_V2_ADDITIVE_MENU_IDENTITIES",
        "_append_native_modeled_product_capability_menus",
        "_append_finance_interfund_analysis_product_menus",
        "_sync_user_confirmed_locked_construction_product_policies",
        "_release_all_construction_product_menus",
        "ProductPolicyCatalogSyncService",
    ):
        if forbidden in policy or forbidden in locked_contract:
            errors.append(f"dual-track product policy mechanism is forbidden: {forbidden}")
    if 'self.synchronize_locked_formal_menu_policy(product_key)' not in policy:
        errors.append("construction product policy sync must use the single locked baseline path")
    for token in (
        'native_visible_menu_path = self._native_visible_menu_path(menu_xmlid)',
        'native_group_label = native_path_parts[1]',
        '"visible_menu_path": native_visible_menu_path or',
        'def _node_followup_rank(self, node: dict) -> int:',
        'return (self._node_followup_rank(node), self._node_sequence(node) or 9999, index)',
    ):
        if token not in menu_service:
            errors.append(f"native menu runtime authority missing: {token}")
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
        "action_sc_project_organization_roadmap",
        "action_sc_project_milestone_roadmap",
        "action_sc_project_collaboration_roadmap",
        "action_sc_project_risk_roadmap",
        "action_sc_project_closeout_roadmap",
        "group_sc_cap_business_config_admin",
    ):
        if token not in xml:
            errors.append(f"project roadmap admin visibility binding missing: {token}")
    for center, names in EXPECTED_FOLLOWUP_BY_CENTER.items():
        for name in names:
            if f'name="{name}（后续上线）"' not in xml:
                errors.append(f"{center} roadmap menu missing: {name}")
    explicit_admin_bindings = sum(
        1 for record in xml_root.findall("record")
        if (record.get("id") or "").endswith("roadmap_v2")
        and any(
            field.get("name") == "groups_id" and "group_sc_cap_business_config_admin" in (field.get("eval") or "")
            for field in record.findall("field")
        )
    )
    if explicit_admin_bindings != 12:
        errors.append(f"cross-center roadmap menus require 12 explicit admin bindings, got {explicit_admin_bindings}")
    expected_center_ranks = {"工作台": 5, "项目中心": 10, "合同中心": 20, "成本中心": 30, "物资与分包": 40, "施工管理": 50, "财务中心": 60, "税务中心": 70, "报表中心": 80, "组织行政": 90}
    for center, expected_rank in expected_center_ranks.items():
        if f'"{center}": {expected_rank}' not in hook_facts:
            errors.append(f"delivery center order missing: {center}")
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
