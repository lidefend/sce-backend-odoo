#!/usr/bin/env python3
"""Fail-closed guard for the locked product primary-center target baseline."""

from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE_PATH = REPO_ROOT / "config/product_primary_center_baseline_v1.json"
RELEASE_MANIFEST_PATH = REPO_ROOT / "config/product_menu_release_manifest_v2.json"

EXPECTED_CENTERS = (
    ("workbench", 10, "工作台"),
    ("project", 20, "项目中心"),
    ("contract", 30, "合同中心"),
    ("cost", 40, "成本中心"),
    ("finance", 50, "财务中心"),
    ("tax", 60, "税务中心"),
    ("accounting", 70, "会计账务中心"),
    ("reporting", 80, "报表中心"),
    ("administration", 90, "行政中心"),
    ("product_configuration", 100, "产品配置"),
)
EXPECTED_RUNTIME_CENTERS = (
    "工作台", "项目中心", "合同中心", "成本中心", "财务中心",
    "税务中心", "会计账务中心", "报表中心", "行政中心", "产品配置",
)
EXPECTED_TRANSITIONS = {
    ("物资与分包", "项目中心"),
    ("施工管理", "项目中心"),
    ("组织行政", "行政中心"),
    ("产品配置", "产品配置"),
    ("财务中心（会计核算能力）", "会计账务中心"),
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(baseline: dict, release_manifest: dict) -> list[str]:
    errors: list[str] = []
    expected_scalars = {
        "schema": "sce.product_primary_center_baseline.v1",
        "status": "LOCKED",
        "formal_product_layer": "P1",
        "layer_target": "L2",
        "module": "smart_construction_core",
        "scope": "TARGET_INFORMATION_ARCHITECTURE",
        "maximum_business_depth": 3,
        "center_level_maturity_policy": "CAPABILITY_LEVEL_ONLY",
    }
    for key, expected in expected_scalars.items():
        if baseline.get(key) != expected:
            errors.append(f"baseline.{key} must be {expected!r}")

    actual_centers = tuple(
        (item.get("key"), item.get("sequence"), item.get("name"))
        for item in baseline.get("primary_centers", [])
    )
    if actual_centers != EXPECTED_CENTERS:
        errors.append("primary_centers must match the locked ten-center name/order contract")
    for item in baseline.get("primary_centers", []):
        if not str(item.get("responsibility", "")).strip():
            errors.append(f"center {item.get('name')!r} must define a responsibility boundary")

    runtime_centers = tuple(baseline.get("current_runtime_primary_centers", []))
    release_runtime_centers = tuple(
        release_manifest.get("navigation_rules", {}).get("primary_centers", [])
    )
    if runtime_centers != EXPECTED_RUNTIME_CENTERS:
        errors.append("current_runtime_primary_centers no longer matches the audited release snapshot")
    if runtime_centers != release_runtime_centers:
        errors.append("baseline runtime snapshot must equal release manifest primary_centers")

    target_ref = release_manifest.get("target_primary_center_baseline", {})
    expected_ref = {
        "ref": "config/product_primary_center_baseline_v1.json",
        "status": "LOCKED",
        "runtime_alignment_status": "ALIGNED",
        "current_runtime_semantics": "LOCKED_TARGET_RUNTIME",
    }
    if target_ref != expected_ref:
        errors.append("release manifest must explicitly link the locked target as ALIGNED")

    if baseline.get("menu_contract") != {
        "ref": "config/product_menu_contract_v1.json",
        "status": "LOCKED",
        "runtime_alignment_status": "ALIGNED",
    }:
        errors.append("primary-center baseline must link the locked full menu contract as ALIGNED")

    transitions = baseline.get("legacy_center_transitions", [])
    transition_pairs = {(item.get("source"), item.get("target")) for item in transitions}
    if transition_pairs != EXPECTED_TRANSITIONS:
        errors.append("legacy_center_transitions must exactly cover the approved convergence set")
    for item in transitions:
        if not str(item.get("rule", "")).strip():
            errors.append(f"transition {item.get('source')!r} must define a migration rule")

    if baseline.get("non_primary_centers") != [
        {"name": "系统管理", "classification": "INTERNAL_GOVERNANCE"}
    ]:
        errors.append("系统管理 must remain a non-primary internal-governance center")
    if baseline.get("runtime_migration_status") != "ALIGNED":
        errors.append("runtime_migration_status must remain ALIGNED after ten-center promotion")
    return errors


def main() -> int:
    try:
        errors = validate(load_json(BASELINE_PATH), load_json(RELEASE_MANIFEST_PATH))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[FAIL] product primary-center baseline guard: {exc}")
        return 1
    if errors:
        for error in errors:
            print(f"[FAIL] {error}")
        return 1
    print("[PASS] locked product primary-center baseline and aligned runtime snapshot are consistent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
