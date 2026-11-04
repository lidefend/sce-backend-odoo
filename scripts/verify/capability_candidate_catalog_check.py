#!/usr/bin/env python3
"""Generate and validate the CAP-01B capability candidate catalog.

Offline verification tool only. It never modifies the formal catalog, release
states, qualifications or any product runtime. It produces a candidate catalog
whose every entry is traceable to its historical source key and whose composite
dependencies close over candidate capability keys (internal model operations
are NOT published as capability dependencies).
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/product/capability_candidate_catalog_v1.json"

# disposition: keep / defer / exclude ; layer: atomic / composite ; canonical
# key overrides represent rename with the old key retained as compatibility alias.
CLASSIFICATION = {
    # --- keep ---
    "project.initiation.enter": {"disposition": "keep", "layer": "atomic", "canonical_key": "project.initiation.create"},
    "project.lifecycle.transition": {"disposition": "keep", "layer": "atomic"},
    "construction.plan.manage": {"disposition": "keep", "layer": "composite"},
    "construction.plan.report": {"disposition": "keep", "layer": "atomic"},
    "cost.budget.manage": {"disposition": "keep", "layer": "composite"},
    "cost.boq.manage": {"disposition": "keep", "layer": "composite"},
    "cost.profit.compare": {"disposition": "keep", "layer": "composite"},
    "cost.progress.report": {"disposition": "keep", "layer": "atomic"},
    "contract.expense.track": {"disposition": "keep", "layer": "atomic"},
    "contract.income.track": {"disposition": "keep", "layer": "atomic"},
    "contract.settlement.audit": {"disposition": "keep", "layer": "atomic"},
    "equipment.plan.manage": {"disposition": "keep", "layer": "composite"},
    "labor.plan.manage": {"disposition": "keep", "layer": "composite"},
    "governance.runtime.audit": {"disposition": "keep", "layer": "atomic"},
    # --- defer ---
    "project.list.open": {"disposition": "defer", "layer": "atomic"},
    "project.dashboard.enter": {"disposition": "defer", "layer": "atomic"},
    "project.risk.list": {"disposition": "defer", "layer": "atomic"},
    "project.structure.manage": {"disposition": "defer", "layer": "composite"},
    "project.plan_bootstrap.enter": {"disposition": "defer", "layer": "atomic"},
    "project.execution.enter": {"disposition": "defer", "layer": "atomic"},
    "project.execution.advance": {"disposition": "defer", "layer": "atomic"},
    "construction.diary.open": {"disposition": "defer", "layer": "atomic"},
    "equipment.request.list": {"disposition": "defer", "layer": "atomic"},
    "equipment.settlement.list": {"disposition": "defer", "layer": "atomic"},
    "equipment.usage.list": {"disposition": "defer", "layer": "atomic"},
    "labor.attendance.list": {"disposition": "defer", "layer": "atomic"},
    "labor.request.list": {"disposition": "defer", "layer": "atomic"},
    "labor.settlement.list": {"disposition": "defer", "layer": "atomic"},
    "quality.issue.list": {"disposition": "defer", "layer": "atomic"},
    "quality.recheck.list": {"disposition": "defer", "layer": "atomic"},
    "quality.rectification.list": {"disposition": "defer", "layer": "atomic"},
    "safety.issue.list": {"disposition": "defer", "layer": "atomic"},
    "safety.recheck.list": {"disposition": "defer", "layer": "atomic"},
    "safety.rectification.list": {"disposition": "defer", "layer": "atomic"},
    "material.procurement.list": {"disposition": "defer", "layer": "atomic"},
    "finance.exception.monitor": {"disposition": "defer", "layer": "atomic"},
    "finance.plan.funding": {"disposition": "defer", "layer": "atomic"},
    "finance.settlement.order": {"disposition": "defer", "layer": "atomic"},
    "analytics.lifecycle.monitor": {"disposition": "defer", "layer": "atomic"},
    "governance.scene.openability": {"disposition": "defer", "layer": "atomic"},
}

PROVIDERS = {
    "project.initiation.create": [
        {"provider_type": "odoo_intent", "provider_ref": "project.initiation.enter", "contract_ref": "addons/smart_construction_core/handlers/project_initiation_enter.py", "provider_status": "verified"},
        {"provider_type": "odoo_action", "provider_ref": "smart_construction_core.action_project_initiation", "contract_ref": "addons/smart_construction_core/views/menu.xml", "provider_status": "verified"},
        {"provider_type": "odoo_model", "provider_ref": "project.project", "contract_ref": "addons/smart_construction_core/models/core/project_core.py", "provider_status": "verified"},
    ],
    "project.lifecycle.transition": [
        {"provider_type": "odoo_model", "provider_ref": "project.project", "contract_ref": "project lifecycle rules", "provider_status": "verified"},
    ],
    "project.list.open": [
        {"provider_type": "odoo_action", "provider_ref": "smart_construction_core.action_sc_project_list", "contract_ref": "addons/smart_construction_core/actions/project_list_actions.xml", "provider_status": "verified"},
        {"provider_type": "odoo_model", "provider_ref": "project.project", "contract_ref": "addons/smart_construction_core/models/core/project_core.py", "provider_status": "verified"},
    ],
}

COMPOSITE_DEPENDENCIES = {
    "construction.plan.manage": ["project.list.open", "construction.plan.report"],
    "cost.budget.manage": ["project.list.open"],
    "cost.boq.manage": ["project.list.open"],
    "cost.profit.compare": ["project.list.open"],
    "equipment.plan.manage": ["project.list.open"],
    "labor.plan.manage": ["project.list.open"],
}


def _canonical(key: str, meta: dict) -> str:
    return meta.get("canonical_key") or key


def build_catalog() -> dict:
    capabilities = []
    seen = set()
    for old_key, meta in CLASSIFICATION.items():
        canonical = _canonical(old_key, meta)
        if meta["disposition"] == "exclude":
            continue
        if canonical in seen:
            raise ValueError("duplicate canonical key: " + canonical)
        seen.add(canonical)
        providers = PROVIDERS.get(canonical, [
            {"provider_type": "odoo_model", "provider_ref": "tbd", "contract_ref": "", "provider_status": "unverified"}
        ])
        dependencies = COMPOSITE_DEPENDENCIES.get(canonical, []) if meta["layer"] == "composite" else []
        capabilities.append({
            "capability_key": canonical,
            "layer": meta["layer"],
            "disposition": meta["disposition"],
            "qualification": "unreleased",
            "contract_status": "unverified",
            "release_state": "candidate",
            "providers": providers,
            "dependencies": dependencies,
            "source_refs": [old_key],
            "compatibility_aliases": [old_key] if old_key != canonical else [],
        })
    return {
        "schema": "capability.candidate.catalog.v1",
        "version": "v2",
        "stage": "CAP-01B candidate (not published)",
        "domain_vocabulary": ["project", "contract", "cost", "finance", "material", "construction", "quality", "safety", "labor", "equipment", "analytics", "governance", "workspace"],
        "domain_policy": "extensible via identity governance, not a permanently closed enum",
        "capabilities": capabilities,
    }


def validate(catalog: dict) -> list[str]:
    errors = []
    caps = catalog["capabilities"]
    keys = [c["capability_key"] for c in caps]
    if len(keys) != len(set(keys)):
        errors.append("duplicate capability_key")
    key_set = set(keys)
    for c in caps:
        if not c.get("source_refs"):
            errors.append("missing source_ref: " + c["capability_key"])
        if c.get("qualification") != "unreleased":
            errors.append("qualification not unreleased: " + c["capability_key"])
        for dep in c.get("dependencies", []):
            if dep not in key_set:
                errors.append("unresolved dependency: " + c["capability_key"] + " -> " + dep)
        for p in c.get("providers", []):
            if p.get("provider_status") not in {"verified", "unverified"}:
                errors.append("invalid provider_status: " + c["capability_key"])
    return errors


def main() -> int:
    catalog = build_catalog()
    errors = validate(catalog)
    if errors:
        print("FAIL")
        for e in errors:
            print(" -", e)
        return 1
    OUT.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    keep = sum(1 for c in catalog["capabilities"] if c["disposition"] == "keep")
    defer = sum(1 for c in catalog["capabilities"] if c["disposition"] == "defer")
    print(f"PASS keep={keep} defer={defer} total={len(catalog['capabilities'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
