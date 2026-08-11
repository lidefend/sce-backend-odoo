#!/usr/bin/env python3
"""Fail closed when locked-candidate hidden menus can be resurrected at runtime."""
from __future__ import annotations

import ast
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADDON = ROOT / "addons/smart_construction_core"
POLICY = ADDON / "models/support/product_policy_sync.py"
CORE_EXTENSION = ADDON / "core_extension.py"
CORE_INIT = ADDON / "__init__.py"
MENU_SERVICE = ROOT / "addons/smart_core/delivery/menu_service.py"
MENU_CONFIG_POLICY = ROOT / "addons/smart_core/model/ui_menu_config_policy.py"
NORM_MENU = ROOT / "addons/sc_norm_engine/views/norm_menu.xml"
WAVES = tuple((ADDON / "views").glob("menu_product_*_wave1.xml")) + (
    ADDON / "views/menu_product_primary_center_candidate_v1.xml",
)

HIDDEN_XMLIDS = {
    "menu_sc_workbench_my_approval_fact",
    "menu_sc_project_overview_group_v2",
    "menu_sc_project_ledger_group_v2",
    "menu_sc_project_planning_group_v2",
    "menu_sc_project_organization_group_v2",
    "menu_sc_project_milestone_group_v2",
    "menu_sc_project_collaboration_group_v2",
    "menu_sc_project_document_group_v2",
    "menu_sc_project_risk_group_v2",
    "menu_sc_project_closeout_group_v2",
    "menu_sc_project_quick_create",
    "menu_sc_tender_prepare",
    "menu_sc_tender_registration",
    "menu_sc_tender_registration_fee",
    "menu_sc_tender_opening",
    "menu_sc_field_mobile_roadmap_v2",
    "menu_sc_bim_collaboration_roadmap_v2",
    "menu_sc_schedule_delivery_group_v2",
    "menu_sc_quality_delivery_group_v2",
    "menu_sc_safety_delivery_group_v2",
    "menu_sc_material_management_group",
    "menu_sc_labor_management_group",
    "menu_sc_equipment_management_group",
    "menu_sc_material_rental_group",
    "menu_sc_subcontract_management_group",
    "menu_sc_supply_collaboration_roadmap_v2",
    "menu_sc_construction_contract",
    "menu_sc_contract_performance_roadmap_v2",
    "menu_sc_project_wbs_cost",
    "menu_sc_cost_forecast_roadmap_v2",
    "menu_sc_cost_cashflow_roadmap_v2",
    "menu_project_funding_actual_event_allocation",
    "menu_sc_noncash_business_group",
    "menu_sc_historical_payment_fact",
    "menu_sc_arrival_confirmation",
    "menu_sc_finance_interfund_analysis",
    "menu_sc_fund_forecast_roadmap_v2",
    "menu_sc_tax_filing_roadmap_v2",
    "menu_sc_invoice_verification_roadmap_v2",
    "menu_sc_business_entity",
    "menu_sc_report_prediction_roadmap_v2",
    "menu_sc_fuel_card_archive_group",
    "menu_sc_people_lifecycle_roadmap_v2",
    "menu_sc_resource_capacity_roadmap_v2",
}

RELEASED_CONTRACT_XMLIDS = {
    "menu_sc_p1_income_contract",
    "menu_sc_p1_expense_contract",
    "menu_sc_p1_contract_change",
    "menu_sc_p1_daily_contract",
}

RELEASED_SETTLEMENT_XMLIDS = {
    "menu_sc_p1_income_settlement",
    "menu_sc_p1_expense_settlement",
}


def _constant_values(source: str, name: str) -> set[str]:
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            value = ast.literal_eval(node.value)
            return {item.rsplit(".", 1)[-1] for item in value}
    return set()


def _hidden_overlay_values() -> set[str]:
    hidden: set[str] = set()
    for wave in WAVES:
        for node in ET.parse(wave).getroot().findall(".//record"):
            fields = {field.attrib.get("name"): (field.text or "").strip() for field in node.findall("field")}
            if fields.get("active") == "False":
                hidden.add(node.attrib.get("id", ""))
    return hidden


def validate() -> list[str]:
    errors: list[str] = []
    source = POLICY.read_text(encoding="utf-8")
    policy_hidden = _constant_values(source, "LOCKED_TARGET_UNPUBLISHED_MENU_XMLIDS")
    policy_contract = _constant_values(source, "FORMAL_CONTRACT_PRODUCT_MENU_XMLIDS")
    policy_settlement = _constant_values(source, "FORMAL_SETTLEMENT_PRODUCT_MENU_XMLIDS")
    overlay_hidden = _hidden_overlay_values()
    missing_overlay = HIDDEN_XMLIDS - overlay_hidden
    missing_policy = HIDDEN_XMLIDS - policy_hidden
    if missing_overlay:
        errors.append("missing active=False overlays: " + ", ".join(sorted(missing_overlay)))
    if missing_policy:
        errors.append("policy can resurrect hidden menus: " + ", ".join(sorted(missing_policy)))
    missing_contract = RELEASED_CONTRACT_XMLIDS - policy_contract
    missing_settlement = RELEASED_SETTLEMENT_XMLIDS - policy_settlement
    if missing_contract:
        errors.append("config-only policy can hide released contract menus: " + ", ".join(sorted(missing_contract)))
    if missing_settlement:
        errors.append("config-only policy can hide released settlement menus: " + ", ".join(sorted(missing_settlement)))
    if "menu_xmlid not in LOCKED_TARGET_UNPUBLISHED_MENU_XMLIDS" not in source:
        errors.append("policy convergence must explicitly preserve locked-target unpublished menus")
    manifest = (ADDON / "__manifest__.py").read_text(encoding="utf-8")
    if "menu_legacy_direct_project_acceptance.xml" in manifest:
        errors.append("product module must not load the customer acceptance menu authority")
    candidate = (ADDON / "views/menu_product_primary_center_candidate_v1.xml").read_text(encoding="utf-8")
    if "menu_sc_user_acceptance_root" in candidate:
        errors.append("product candidate must not declare or own the customer acceptance root")
    migration = ADDON / "migrations/17.0.0.110/post-migration.py"
    migration_source = migration.read_text(encoding="utf-8") if migration.exists() else ""
    if "menu_sc_user_acceptance_root" not in migration_source or '"active": False' not in migration_source:
        errors.append("upgrade migration must archive the legacy customer acceptance root when present")
    extension_source = CORE_EXTENSION.read_text(encoding="utf-8")
    init_source = CORE_INIT.read_text(encoding="utf-8")
    service_source = MENU_SERVICE.read_text(encoding="utf-8")
    menu_config_source = MENU_CONFIG_POLICY.read_text(encoding="utf-8")
    if "def smart_core_native_navigation_authority" in extension_source:
        errors.append("construction product release policy must not be bypassed by native-tree authority")
    if "smart_core_native_navigation_authority," in init_source:
        errors.append("construction product must not export the retired native-tree authority hook")
    if '"source": "native_product_navigation_authority"' not in service_source:
        errors.append("platform menu delivery must retain the generic native-navigation extension mechanism")
    if "if self._native_navigation_is_authoritative(policy, role_surface):" not in service_source:
        errors.append("platform menu delivery must retain the generic native-navigation extension point")
    if "self._native_authoritative_fact_nav()" not in service_source:
        errors.append("native authority must read the request user's ACL-visible Odoo menu facts")
    if "def _native_route_discovery_blocked" not in service_source or "reserved_pairs=reserved_pairs" not in service_source:
        errors.append("native product routes must preserve stable menu/action pair identity")
    if "product_baseline_authoritative = native_product_baseline_authoritative()" not in menu_config_source:
        errors.append("P2 menu configuration must recognize the P1 native product baseline")
    if "if not policy and not normalized_menu_id" not in menu_config_source:
        errors.append("legacy same-label policies must not bind to stable product menu ids")
    norm_root = ET.parse(NORM_MENU).getroot().find(".//menuitem[@id='menu_sc_norm_root']")
    if norm_root is None or norm_root.attrib.get("parent") != "smart_construction_core.menu_sc_config_center":
        errors.append("norm engine must remain under the internal system-management carrier")
    return errors


if __name__ == "__main__":
    failures = validate()
    if failures:
        print("\n".join(f"[FAIL] {item}" for item in failures))
        sys.exit(1)
    print(f"[PASS] {len(HIDDEN_XMLIDS)} unpublished menu facts are closed in XML and policy convergence")
