"""Read-only readback of the approved product-scenario seed."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


SURFACE_PATH = Path(
    "/mnt/source-addons/smart_construction_core/data/scenario_product_surface.json"
)
LEGACY_SCENARIO_KEYS = {
    "workspace.home",
    "governance.organization",
    "governance.configuration",
    "project.management",
    "contract.performance",
    "cost.budget",
    "procurement.supplier",
    "material.management",
    "subcontract.management",
    "labor.management",
    "quality.management",
    "safety.management",
    "payment.capital",
    "receipt.payment.ledger",
    "tax.management",
    "accounting.management",
    "analytics.decision",
    "equipment.management",
    "administration.office",
}


surface = json.loads(SURFACE_PATH.read_text(encoding="utf-8"))
expected_scenarios = {row["key"]: row for row in surface["scenarios"]}
expected_bindings = {
    (scenario["key"], binding["menu_key"]): binding
    for scenario in surface["scenarios"]
    for binding in scenario["bindings"]
}

Scenario = env["sc.product.scenario"].sudo().with_context(active_test=False)
Entry = env["sc.product.scenario.entry"].sudo().with_context(active_test=False)
scenarios = Scenario.search([])
entries = Entry.search([])
menus = entries.mapped("menu_id")
menu_xmlids = menus.get_external_id()

actual_scenarios = {
    row.code: {
        "name": row.name,
        "active": bool(row.active),
        "sequence": int(row.sequence),
    }
    for row in scenarios
}
actual_bindings = {}
duplicate_bindings = []
binding_rows = []
for entry in entries:
    scenario_key = entry.scenario_id.code
    menu_xmlid = menu_xmlids.get(entry.menu_id.id, "")
    key = (scenario_key, menu_xmlid)
    if key in actual_bindings:
        duplicate_bindings.append(f"{scenario_key}:{menu_xmlid}")
    actual_bindings[key] = {
        "intent": str(entry.intent or ""),
        "sequence": int(entry.sequence or 0),
        "center_key": str(entry.center_key or ""),
    }
    binding_rows.append({
        "scenario_key": scenario_key,
        "menu_xmlid": menu_xmlid,
        "intent": entry.intent,
        "sequence": int(entry.sequence or 0),
        "center_key": str(entry.center_key or ""),
        "center_name": str(entry.center_name or ""),
    })

errors = []
if set(actual_scenarios) != set(expected_scenarios):
    errors.append({
        "code": "SCENARIO_IDENTITY_MISMATCH",
        "missing": sorted(set(expected_scenarios) - set(actual_scenarios)),
        "extra": sorted(set(actual_scenarios) - set(expected_scenarios)),
    })
legacy_remaining = sorted(LEGACY_SCENARIO_KEYS & set(actual_scenarios))
if legacy_remaining:
    errors.append({
        "code": "LEGACY_SCENARIO_REMAINS",
        "scenario_keys": legacy_remaining,
    })
for scenario_key, expected in expected_scenarios.items():
    actual = actual_scenarios.get(scenario_key)
    if not actual:
        continue
    if (
        actual["name"] != expected["name"]
        or not actual["active"]
        or actual["sequence"] != int(expected["sequence"])
    ):
        errors.append({
            "code": "SCENARIO_DECLARATION_MISMATCH",
            "scenario_key": scenario_key,
            "expected": {
                "name": expected["name"],
                "active": True,
                "sequence": int(expected["sequence"]),
            },
            "actual": actual,
        })

if set(actual_bindings) != set(expected_bindings):
    errors.append({
        "code": "SCENARIO_BINDING_IDENTITY_MISMATCH",
        "missing": [
            {"scenario_key": key[0], "menu_xmlid": key[1]}
            for key in sorted(set(expected_bindings) - set(actual_bindings))
        ],
        "extra": [
            {"scenario_key": key[0], "menu_xmlid": key[1]}
            for key in sorted(set(actual_bindings) - set(expected_bindings))
        ],
    })
for key, expected in expected_bindings.items():
    actual = actual_bindings.get(key)
    if not actual:
        continue
    if (
        actual["intent"] != expected["intent"]
        or actual["sequence"] != int(expected["sequence"])
        or actual["center_key"] != expected["center_key"]
    ):
        errors.append({
            "code": "SCENARIO_BINDING_DECLARATION_MISMATCH",
            "scenario_key": key[0],
            "menu_xmlid": key[1],
            "expected": {
                "intent": expected["intent"],
                "sequence": int(expected["sequence"]),
                "center_key": expected["center_key"],
            },
            "actual": actual,
        })
if duplicate_bindings:
    errors.append({
        "code": "DUPLICATE_SCENARIO_BINDING",
        "bindings": duplicate_bindings,
    })

intent_counts = Counter(row["intent"] for row in binding_rows)
result = {
    "status": "PASS" if not errors else "FAIL",
    "database": env.cr.dbname,
    "scenario_count": len(actual_scenarios),
    "binding_count": len(actual_bindings),
    "unique_menu_count": len({key[1] for key in actual_bindings}),
    "intent_counts": dict(sorted(intent_counts.items())),
    "legacy_scenario_keys": legacy_remaining,
    "errors": errors,
}
print("SCENARIO_SEED_RUNTIME_READBACK=" + json.dumps(
    result,
    ensure_ascii=False,
    sort_keys=True,
))
if errors:
    raise RuntimeError("SCENARIO_SEED_RUNTIME_READBACK_FAILED")
