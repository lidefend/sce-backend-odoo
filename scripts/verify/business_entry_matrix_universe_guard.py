#!/usr/bin/env python3
"""Fail closed when the business-entry matrix drifts from the 132-page product surface."""

from __future__ import annotations

import ast
import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCENARIO_PATH = ROOT / "config/product_scenario_organization_v1.json"
MATRIX_PATH = ROOT / "docs/product/frontend_business_entry_acceptance_v1.csv"
EXPOSURE_PATH = ROOT / "config/frontend/role_surface_exposure_declarations_v1.json"
POLICY_PATH = ROOT / "scripts/verify/baselines/formal_business_product_menu_policy_v1.json"
FIXTURE_PATH = (
    ROOT
    / "addons/smart_construction_acceptance_fixture/tools/frontend_productization_fixture.py"
)

SCHEMA = "business_entry_acceptance_universe_guard.v1"
EXPECTED_PAGES = 132
EXPECTED_ACTION_ROWS = 131
EXPECTED_SCENE_ROWS = 1


def _rows_by_menu(rows):
    out = {}
    duplicates = []
    for row in rows:
        menu = str(row.get("menu_xmlid") or "").strip()
        if not menu:
            continue
        if menu in out:
            duplicates.append(menu)
        out[menu] = row
    return out, sorted(set(duplicates))


def fixture_scenario_keys(path=FIXTURE_PATH):
    tree = ast.parse(Path(path).read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == "FIXTURE_BUSINESS_SCENARIOS" for target in node.targets):
            continue
        value = ast.literal_eval(node.value)
        return tuple(str(item).strip() for item in value if str(item).strip())
    raise ValueError("FIXTURE_BUSINESS_SCENARIOS is missing")


def validate_documents(scenario, matrix_rows, exposure, policy, fixture_scenarios=None):
    errors = []
    warnings = []

    scenario_rows = {}
    scenario_duplicates = []
    for scenario_row in scenario.get("scenarios") or []:
        for page in scenario_row.get("pages") or []:
            menu = str(page.get("menu_xmlid") or "").strip()
            if not menu:
                errors.append("scenario page has no menu_xmlid")
                continue
            if menu in scenario_rows:
                scenario_duplicates.append(menu)
            scenario_rows[menu] = (scenario_row, page)
    errors.extend(f"duplicate scenario page: {menu}" for menu in sorted(set(scenario_duplicates)))

    action_by_menu, action_duplicates = _rows_by_menu(matrix_rows)
    errors.extend(f"duplicate matrix action row: {menu}" for menu in action_duplicates)
    scene_rows = exposure.get("non_action_delivery_entries") or {}
    if not isinstance(scene_rows, dict):
        errors.append("non_action_delivery_entries must be an object")
        scene_rows = {}

    action_set = set(action_by_menu)
    scene_set = {str(menu).strip() for menu in scene_rows}
    declared_union = action_set | scene_set
    overlap = action_set & scene_set
    if overlap:
        errors.append(f"action and scene carriers overlap: {sorted(overlap)}")

    if len(scenario_rows) != EXPECTED_PAGES:
        errors.append(f"scenario pages={len(scenario_rows)} expected={EXPECTED_PAGES}")
    if len(action_by_menu) != EXPECTED_ACTION_ROWS:
        errors.append(f"matrix action rows={len(action_by_menu)} expected={EXPECTED_ACTION_ROWS}")
    if len(scene_set) != EXPECTED_SCENE_ROWS:
        errors.append(f"declared scene rows={len(scene_set)} expected={EXPECTED_SCENE_ROWS}")

    missing = sorted(set(scenario_rows) - declared_union)
    extra = sorted(declared_union - set(scenario_rows))
    if missing:
        errors.append(f"scenario pages missing from matrix universe: {missing}")
    if extra:
        errors.append(f"matrix universe contains undeclared pages: {extra}")

    for menu, row in sorted(action_by_menu.items()):
        for field in ("action_xmlid", "model", "label", "domain", "rendering_path", "query_responsibility"):
            if not str(row.get(field) or "").strip():
                errors.append(f"{menu}: empty {field}")
        try:
            authority = json.loads(str(row.get("role_authority") or ""))
        except (TypeError, ValueError):
            errors.append(f"{menu}: role_authority is not valid JSON")
            continue
        if not isinstance(authority, dict):
            errors.append(f"{menu}: role_authority must be an object")
            continue
        if authority.get("semantics") != "all_restricted_layers_must_match_one_group":
            errors.append(f"{menu}: unexpected role authority semantics")
        if not isinstance(authority.get("menu_chain"), list) or not authority.get("menu_chain"):
            errors.append(f"{menu}: menu_chain is required")
        if not isinstance(authority.get("action_groups"), list):
            errors.append(f"{menu}: action_groups must be a list")
        if str(row.get("acceptance_status") or "") not in {"pending", "passed", "failed"}:
            errors.append(f"{menu}: invalid acceptance_status")

    for menu in sorted(scene_set):
        declaration = scene_rows.get(menu) or {}
        if menu not in scenario_rows:
            continue
        if not str(declaration.get("scene_key") or "").strip():
            errors.append(f"{menu}: scene_key is required")
        if not str(declaration.get("route") or "").strip():
            errors.append(f"{menu}: route is required")
        if str(declaration.get("entry_target_type") or "") != "scene":
            errors.append(f"{menu}: entry_target_type must be scene")

    strategy = policy.get("policy_strategy") or {}
    if int(strategy.get("effective_menu_count_per_product") or 0) != EXPECTED_PAGES:
        errors.append("formal product policy effective menu count is not 132")
    counts = strategy.get("menu_count_by_product") or {}
    if int(counts.get("construction.standard") or 0) != EXPECTED_PAGES:
        errors.append("construction.standard policy menu count is not 132")

    if fixture_scenarios is not None:
        scenario_keys = {str(row.get("key") or "").strip() for row in scenario.get("scenarios") or []}
        fixture_keys = {str(key).strip() for key in fixture_scenarios if str(key).strip()}
        if fixture_keys != scenario_keys:
            errors.append(
                "acceptance fixture scenario keys drift "
                f"missing={sorted(scenario_keys - fixture_keys)} "
                f"extra={sorted(fixture_keys - scenario_keys)}"
            )

    if not any(menu in scene_set for menu in scenario_rows):
        warnings.append("no scene carrier is represented in the scenario organization")

    return {
        "schema": SCHEMA,
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "counts": {
            "scenario_pages": len(scenario_rows),
            "matrix_action_rows": len(action_by_menu),
            "scene_rows": len(scene_set),
            "declared_units": len(declared_union),
            "fixture_scenarios": len(fixture_scenarios or []),
            "pending_rows": sum(
                1 for row in action_by_menu.values()
                if str(row.get("acceptance_status") or "") == "pending"
            ),
        },
        "missing": missing,
        "extra": extra,
    }


def build_report():
    scenario = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))
    with MATRIX_PATH.open(encoding="utf-8", newline="") as handle:
        matrix_rows = list(csv.DictReader(handle))
    exposure = json.loads(EXPOSURE_PATH.read_text(encoding="utf-8"))
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    return validate_documents(
        scenario,
        matrix_rows,
        exposure,
        policy,
        fixture_scenarios=fixture_scenario_keys(),
    )


def main():
    report = build_report()
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
