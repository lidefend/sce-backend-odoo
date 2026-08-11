#!/usr/bin/env python3
"""Fail closed when the locked ten-center product menu drifts.

The product menu contract owns navigation shape. Capability maturity remains
metadata and is intentionally not allowed to hide a contracted entry.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "config/product_menu_contract_v1.json"
BASELINE = ROOT / "scripts/verify/baselines/formal_business_product_menu_policy_v1.json"
ACCEPTANCE = ROOT / "config/frontend/acceptance_environments_v1.json"
MANIFEST = ROOT / "addons/smart_construction_core/__manifest__.py"
COMPLETION_XML = ROOT / "addons/smart_construction_core/views/menu_product_contract_completion_v1.xml"

EXPECTED_CENTERS = [
    "工作台", "项目中心", "合同中心", "成本中心", "财务中心",
    "税务中心", "会计账务中心", "报表中心", "行政中心", "产品配置",
]
EXPECTED_CONTRACT_MENU_COUNT = 89
EXPECTED_ACCOUNTING_MENU_COUNT = 6
EXPECTED_FORMAL_MENU_COUNT = EXPECTED_CONTRACT_MENU_COUNT


def _contract_paths(payload: dict) -> set[tuple[str, ...]]:
    paths: set[tuple[str, ...]] = set()
    centers = payload.get("centers") or []
    if [row.get("name") for row in centers] != EXPECTED_CENTERS:
        raise ValueError("product contract center order mismatch")
    for center in centers:
        center_name = str(center.get("name") or "").strip()
        for level_two in center.get("level_two") or []:
            level_two_name = str(level_two.get("name") or "").strip()
            children = level_two.get("children") or []
            if center_name == "项目中心":
                if not children:
                    raise ValueError(f"project level-two menu has no level-three pages: {level_two_name}")
                for child in children:
                    paths.add((center_name, level_two_name, str(child.get("name") or "").strip()))
            else:
                if children:
                    raise ValueError(f"non-project center illegally uses level three: {center_name}/{level_two_name}")
                paths.add((center_name, level_two_name))
    return paths


def main() -> int:
    errors: list[str] = []
    try:
        contract_paths = _contract_paths(json.loads(CONTRACT.read_text(encoding="utf-8")))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(str(exc))
        contract_paths = set()
    if len(contract_paths) != EXPECTED_CONTRACT_MENU_COUNT:
        errors.append(f"product contract must contain exactly {EXPECTED_CONTRACT_MENU_COUNT} action pages")

    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    strategy = baseline.get("policy_strategy") or {}
    if strategy.get("effective_menu_count_per_product") != EXPECTED_FORMAL_MENU_COUNT:
        errors.append("locked policy menu count is not the complete 89-page product surface")
    if strategy.get("effective_capability_count_per_product") != EXPECTED_FORMAL_MENU_COUNT:
        errors.append("locked policy capability count is not 89")
    for product in baseline.get("products") or []:
        groups = product.get("menu_groups") or []
        if [row.get("group_label") for row in groups] != EXPECTED_CENTERS:
            errors.append(f"{product.get('product_key')} center order mismatch")
            continue
        rows = [menu for group in groups for menu in group.get("menus") or []]
        xmlids = [str(row.get("menu_xmlid") or "") for row in rows]
        if len(rows) != EXPECTED_FORMAL_MENU_COUNT or len(set(xmlids)) != EXPECTED_FORMAL_MENU_COUNT:
            errors.append(f"{product.get('product_key')} must contain 89 unique menu identities")
        actual_contract_paths: set[tuple[str, ...]] = set()
        accounting_count = 0
        for row in rows:
            parts = tuple(part.strip() for part in str(row.get("visible_menu_path") or "").split(" / ") if part.strip())
            if len(parts) < 3 or parts[0] != "智慧施工管理平台":
                errors.append(f"invalid visible path: {row.get('visible_menu_path')}")
                continue
            relative = parts[1:]
            if relative[0] == "会计账务中心":
                accounting_count += 1
                if len(relative) != 2:
                    errors.append("accounting must remain a flat center-to-page menu")
            actual_contract_paths.add(relative)
        if actual_contract_paths != contract_paths:
            errors.append(
                f"{product.get('product_key')} contract projection mismatch: "
                f"missing={sorted(contract_paths - actual_contract_paths)} "
                f"extra={sorted(actual_contract_paths - contract_paths)}"
            )
        if accounting_count != EXPECTED_ACCOUNTING_MENU_COUNT:
            errors.append(f"{product.get('product_key')} must retain six current accounting pages")
        capabilities = product.get("capabilities") or []
        if {row.get("menu_xmlid") for row in capabilities} != set(xmlids):
            errors.append(f"{product.get('product_key')} capability/menu identity mismatch")

    acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
    daily = (((acceptance.get("profiles") or {}).get("daily") or {}).get("navigation_policy") or {})
    if daily.get("min_actions") != EXPECTED_FORMAL_MENU_COUNT or daily.get("max_actions") != EXPECTED_FORMAL_MENU_COUNT:
        errors.append("daily acceptance must lock exactly 89 visible action pages")

    module_manifest = ast.literal_eval(MANIFEST.read_text(encoding="utf-8"))
    completion_path = "views/menu_product_contract_completion_v1.xml"
    if completion_path not in (module_manifest.get("data") or []):
        errors.append("complete product-menu XML is not installed by the module")
    try:
        root = ElementTree.parse(COMPLETION_XML).getroot()
        raw_xml = COMPLETION_XML.read_text(encoding="utf-8")
        if "base.group_" in raw_xml or "project.group_" in raw_xml or "account.group_" in raw_xml:
            errors.append("complete product menu must use SC capability groups only")
        declared_ids = {node.get("id") for node in root.iter() if node.get("id")}
        completion_xmlids = {
            row[2].split(".", 1)[1]
            for product in baseline.get("products") or []
            for group in product.get("menu_groups") or []
            for row in [(
                str(group.get("group_label") or ""),
                str((group.get("menus") or [{}])[0].get("name") or ""),
                str(menu.get("menu_xmlid") or ""),
            ) for menu in group.get("menus") or []]
            if row[2].startswith("smart_construction_core.menu_sc_product_")
        }
        missing_declarations = completion_xmlids - declared_ids
        if missing_declarations:
            errors.append(f"completion XML misses contracted menu records: {sorted(missing_declarations)}")
    except (OSError, ElementTree.ParseError) as exc:
        errors.append(f"complete product-menu XML invalid: {exc}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(
        "PRODUCT_MENU_RELEASE_MANIFEST_V2_GUARD=PASS "
        f"centers={len(EXPECTED_CENTERS)} contract_pages={len(contract_paths)} "
        f"accounting_pages={EXPECTED_ACCOUNTING_MENU_COUNT} total={EXPECTED_FORMAL_MENU_COUNT}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
