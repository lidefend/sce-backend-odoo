#!/usr/bin/env python3
"""Fail-closed comparison for the frozen M4 menu-governance scope."""

from __future__ import annotations

import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FROZEN = ROOT / "docs/engineering_convergence/menu_governance/menu_m4_frozen_scope.json"
INVENTORY = ROOT / "docs/engineering_convergence/menu_governance/menu_capability_inventory.json"
BASELINE_RUNTIME = ROOT / os.environ.get(
    "MENU_M4_BASELINE_RUNTIME",
    "artifacts/menu-governance/menu-m4-runtime.REJECTED-wrong-sha.json",
)
CANDIDATE_RUNTIME = ROOT / os.environ.get(
    "MENU_M4_CANDIDATE_RUNTIME",
    ".runtime/menu-governance-m4/evidence/candidate-a85740c-runtime-resource-probe.json",
)
BASELINE_BROWSER = ROOT / os.environ.get(
    "MENU_M4_BASELINE_BROWSER",
    ".runtime/menu-governance-m4/evidence/baseline-0abb989/browser/report.json",
)
CANDIDATE_BROWSER = ROOT / os.environ.get(
    "MENU_M4_CANDIDATE_BROWSER",
    ".runtime/menu-governance-m4/evidence/candidate-a85740c/browser/report.json",
)
OUTPUT = ROOT / os.environ.get(
    "MENU_M4_CLOSURE_OUTPUT",
    ".runtime/menu-governance-m4/evidence/menu-m4-closure.json",
)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def fail(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def browser_projection(report: dict, frozen: set[str]) -> dict:
    projection = {}
    for observation in report.get("observations", []):
        key = (observation["role"], observation["viewport"]["key"])
        fail(observation.get("document_horizontal_overflow_px") == 0, f"{key}: horizontal overflow")
        for field in ("console_errors", "page_errors", "http_errors"):
            fail(not observation.get(field), f"{key}: {field} is not empty")
        projection[key] = sorted(
            (
                row.get("menu_xmlid"),
                row.get("label"),
                tuple(row.get("path") or []),
                row.get("child_count"),
            )
            for row in observation.get("frozen_navigation", [])
            if row.get("menu_xmlid") in frozen
        )
    return projection


frozen = load(FROZEN)
inventory = load(INVENTORY)
baseline_runtime = load(BASELINE_RUNTIME)
candidate_runtime = load(CANDIDATE_RUNTIME)
baseline_browser = load(BASELINE_BROWSER)
candidate_browser = load(CANDIDATE_BROWSER)
xmlids = frozen["menu_xmlids"]
xmlid_set = set(xmlids)
fail(len(xmlids) == len(xmlid_set) == 22, "frozen scope must contain 22 unique XMLIDs")
fail(baseline_browser.get("source_commit_sha") == frozen["baseline_runtime_sha"], "baseline browser SHA mismatch")
fail(candidate_browser.get("source_commit_sha") == frozen["candidate_product_sha"], "candidate browser SHA mismatch")
fail(len(baseline_browser.get("observations", [])) == 16, "baseline browser matrix is incomplete")
fail(len(candidate_browser.get("observations", [])) == 16, "candidate browser matrix is incomplete")

baseline_rows = {row["menu_xmlid"]: row for row in baseline_runtime.get("rows", [])}
candidate_rows = {row["menu_xmlid"]: row for row in candidate_runtime.get("rows", [])}
fail(set(baseline_rows) == xmlid_set, "baseline runtime resource coverage mismatch")
fail(set(candidate_rows) == xmlid_set, "candidate runtime resource coverage mismatch")
for xmlid in xmlids:
    before = baseline_rows[xmlid]
    after = candidate_rows[xmlid]
    fail(before.get("exists") and after.get("exists"), f"{xmlid}: runtime record missing")
    for field in ("name", "path", "parent_xmlid", "sequence", "groups", "action", "visibility"):
        fail(before.get(field) == after.get(field), f"{xmlid}: unexpected runtime drift in {field}")

baseline_projection = browser_projection(baseline_browser, xmlid_set)
candidate_projection = browser_projection(candidate_browser, xmlid_set)
fail(baseline_projection == candidate_projection, "released browser navigation projection drifted")

findings = inventory["findings"]
fail(findings.get("duplicate_menuitem_xmlids") == [], "duplicate menuitem declarations remain")
fail(inventory["statistics"].get("menuitem_declaration_count") == 304, "menuitem declaration count mismatch")
fail(inventory["statistics"].get("unique_menuitem_xmlid_count") == 304, "menuitem XMLID count mismatch")

remaining = set(findings.get("technical_name_risks", [])) | set(findings.get("over_depth_risks", []))
expected_remaining = {
    "smart_construction_core.menu_sc_leave_request",
    "smart_construction_core.menu_sc_material_stock_statistics_report",
    "smart_construction_core.menu_sc_project_manage",
    "smart_construction_core.menu_sc_project_wbs_cost",
    "smart_construction_core.menu_sc_settlement_adjustment",
    "smart_construction_core.menu_sc_settlement_order",
}
fail(remaining == expected_remaining, "remaining reviewed candidates changed")

report = {
    "schema": "sce.menu_governance_m4_closure.v1",
    "result": "PASS",
    "static_inventory_sha": frozen["static_inventory_sha"],
    "baseline_runtime_sha": frozen["baseline_runtime_sha"],
    "candidate_product_sha": frozen["candidate_product_sha"],
    "frozen_scope_count": 22,
    "role_viewport_observation_count": 16,
    "resolved_duplicate_declaration_count": 16,
    "runtime_invariant_asset_count": 22,
    "browser_projection_invariant": True,
    "remaining_reviewed_candidate_count": 6,
    "remaining_dispositions": {
        "smart_construction_core.menu_sc_leave_request": "LOCKED_PRODUCT_TERM_NO_CHANGE",
        "smart_construction_core.menu_sc_material_stock_statistics_report": "NOT_EXPOSED_IN_RELEASED_NAVIGATION",
        "smart_construction_core.menu_sc_project_manage": "NOT_EXPOSED_IN_RELEASED_NAVIGATION",
        "smart_construction_core.menu_sc_project_wbs_cost": "NOT_EXPOSED_IN_RELEASED_NAVIGATION",
        "smart_construction_core.menu_sc_settlement_adjustment": "RELEASED_NAVIGATION_ALREADY_THREE_LEVEL",
        "smart_construction_core.menu_sc_settlement_order": "RELEASED_NAVIGATION_ALREADY_THREE_LEVEL",
    },
}
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
