#!/usr/bin/env python3
"""Fail-closed guard for the locked Baosheng product menu contract."""

from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = REPO_ROOT / "config/product_menu_contract_v1.json"
BASELINE_PATH = REPO_ROOT / "config/product_primary_center_baseline_v1.json"

EXPECTED_CENTERS = (
    ("workbench", 10, "工作台"), ("project", 20, "项目中心"),
    ("contract", 30, "合同中心"), ("cost", 40, "成本中心"),
    ("finance", 50, "财务中心"), ("tax", 60, "税务中心"),
    ("accounting", 70, "会计账务中心"), ("reporting", 80, "报表中心"),
    ("administration", 90, "行政中心"), ("product_configuration", 100, "产品配置"),
)
EXPECTED_CONTRACT_LEVEL_TWO = ("收入合同", "支出合同", "合同变更", "日常合同", "日常合同结算", "收入结算", "支出结算")
ALLOWED_DELIVERY = {"RELEASED_FOUNDATION", "ADAPTATION_REQUIRED", "NEW_CAPABILITY_REQUIRED"}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(contract: dict, baseline: dict) -> list[str]:
    errors: list[str] = []
    for key, expected in {
        "schema": "sce.product_menu_contract.v1", "status": "LOCKED",
        "product_layer": "P1", "module": "smart_construction_core",
        "runtime_migration_status": "NOT_STARTED",
    }.items():
        if contract.get(key) != expected:
            errors.append(f"contract.{key} must be {expected!r}")
    rules = contract.get("rules", {})
    if rules.get("maximum_business_depth") != 3 or not rules.get("project_center_is_only_center_with_level_three"):
        errors.append("only 项目中心 may use the locked third menu level")
    if rules.get("all_non_project_centers_maximum_depth") != 2:
        errors.append("all non-project centers must be limited to two business levels")
    centers = contract.get("centers", [])
    actual_centers = tuple((item.get("key"), item.get("sequence"), item.get("name")) for item in centers)
    if actual_centers != EXPECTED_CENTERS:
        errors.append("centers must exactly match the locked ten-center baseline")
    baseline_centers = tuple((item.get("key"), item.get("sequence"), item.get("name")) for item in baseline.get("primary_centers", []))
    if actual_centers != baseline_centers:
        errors.append("menu contract centers must match product primary-center baseline")
    for center in centers:
        level_two = center.get("level_two", [])
        if not level_two:
            errors.append(f"{center.get('name')!r} must define level-two menus")
            continue
        for item in level_two:
            children = item.get("children", [])
            if center.get("key") == "project":
                if not children:
                    errors.append(f"project level-two menu {item.get('name')!r} must define its third-level pages")
                for child in children:
                    if child.get("delivery") not in ALLOWED_DELIVERY:
                        errors.append(f"invalid delivery for project page {child.get('name')!r}")
            elif children:
                errors.append(f"non-project center {center.get('name')!r} must not define a third menu level")
            elif item.get("delivery") not in ALLOWED_DELIVERY:
                errors.append(f"invalid delivery for menu {item.get('name')!r}")
    contract_center = next((item for item in centers if item.get("key") == "contract"), {})
    names = tuple(item.get("name") for item in contract_center.get("level_two", []))
    if names != EXPECTED_CONTRACT_LEVEL_TWO:
        errors.append("合同中心二级菜单 must exactly use the approved daily-contract structure")
    if "通用合同" in names or "通用合同结算" in names:
        errors.append("customer-facing contract menus must use 日常合同 and 日常合同结算")
    if contract.get("runtime_migration_status") != baseline.get("runtime_migration_status"):
        errors.append("menu contract and primary-center baseline runtime migration status must match")
    return errors


def main() -> int:
    try:
        errors = validate(load_json(CONTRACT_PATH), load_json(BASELINE_PATH))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[FAIL] product menu contract guard: {exc}")
        return 1
    if errors:
        print("\n".join(f"[FAIL] {error}" for error in errors))
        return 1
    print("[PASS] locked product menu contract is internally consistent and migration remains explicit")
    return 0


if __name__ == "__main__":
    sys.exit(main())
