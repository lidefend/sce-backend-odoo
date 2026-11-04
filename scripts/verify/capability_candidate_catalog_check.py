#!/usr/bin/env python3
"""Generate and/or validate the CAP-01B capability candidate catalog.

Offline verification tool. By default it is a pure read-only checker: it reads
the candidate catalog and B2 reconciliation matrix and reports violations with a
non-zero exit code, without writing anything. ``--generate`` explicitly writes
the candidate catalog; ``--check`` runs the full semantic gates (also used in CI).
It never modifies the formal catalog, release states, qualifications or runtime.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/product/capability_candidate_catalog_v1.json"
B2 = ROOT / "docs/product/capability_reconciliation_matrix_v1.md"

# disposition: keep / defer / exclude ; layer: atomic / composite ; canonical
# key overrides represent rename with the old key retained as compatibility alias.
CLASSIFICATION = {
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

# Verified providers must point to locatable repository assets. Descriptive text
# (e.g. "project lifecycle rules") is NOT verified evidence.
PROVIDERS = {
    "project.initiation.create": [
        {"provider_type": "odoo_intent", "provider_ref": "project.initiation.enter", "contract_ref": "addons/smart_construction_core/handlers/project_initiation_enter.py", "provider_status": "verified"},
        {"provider_type": "odoo_action", "provider_ref": "smart_construction_core.action_project_initiation", "contract_ref": "addons/smart_construction_core/views/menu.xml", "provider_status": "verified"},
        {"provider_type": "odoo_model", "provider_ref": "project.project", "contract_ref": "addons/smart_construction_core/models/core/project_core.py", "provider_status": "verified"},
    ],
    "project.list.open": [
        {"provider_type": "odoo_action", "provider_ref": "smart_construction_core.action_sc_project_list", "contract_ref": "addons/smart_construction_core/actions/project_list_actions.xml", "provider_status": "verified"},
        {"provider_type": "odoo_model", "provider_ref": "project.project", "contract_ref": "addons/smart_construction_core/models/core/project_core.py", "provider_status": "verified"},
    ],
    # model existence alone does not prove a full business capability.
    "project.lifecycle.transition": [
        {"provider_type": "unknown", "provider_ref": "", "contract_ref": "", "provider_status": "unverified", "pending_reason": "lifecycle transition contract not yet located as a code asset"},
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


def _unknown_provider() -> list[dict]:
    return [{"provider_type": "unknown", "provider_ref": "", "contract_ref": "",
             "provider_status": "unverified", "pending_reason": "provider not yet reconciled"}]


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
        providers = PROVIDERS.get(canonical, _unknown_provider())
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
        "closure_note": "reference closure is verified here; qualification closure is deferred to CAP-01C",
        "capabilities": capabilities,
    }


def _b2_counts() -> dict[str, int]:
    text = B2.read_text(encoding="utf-8")
    keep = len(re.findall(r"^\| (?:[a-z][a-z0-9_.-]+) \| keep", text, re.M))
    defer = len(re.findall(r"^\| (?:[a-z][a-z0-9_.-]+) \| defer", text, re.M))
    exclude = len(re.findall(r"^\| (?:[a-z][a-z0-9_.-]+) \| exclude", text, re.M))
    return {"keep": keep, "defer": defer, "exclude": exclude}


def validate(catalog: dict) -> list[str]:
    errors = []
    caps = catalog["capabilities"]
    keys = [c["capability_key"] for c in caps]
    if len(keys) != len(set(keys)):
        errors.append("duplicate capability_key")
    key_set = set(keys)

    keep = sum(1 for c in caps if c["disposition"] == "keep")
    defer = sum(1 for c in caps if c["disposition"] == "defer")
    b2 = _b2_counts()
    if keep != b2["keep"] or defer != b2["defer"]:
        errors.append(f"B2/B6 count mismatch: catalog keep={keep} defer={defer}, B2 keep={b2['keep']} defer={b2['defer']}")

    # cycle detection over composite dependency edges.
    deps = {c["capability_key"]: c.get("dependencies", []) for c in caps}
    color = {}
    def visit(n, stack):
        color[n] = 1
        for m in deps.get(n, []):
            if m in stack:
                errors.append("dependency cycle: " + " -> ".join(stack + [n, m]))
            elif color.get(m, 0) == 0 and m in deps:
                visit(m, stack + [n])
        color[n] = 2
    for n in deps:
        if color.get(n, 0) == 0:
            visit(n, [])

    for c in caps:
        if not c.get("source_refs"):
            errors.append("missing source_ref: " + c["capability_key"])
        if c.get("qualification") != "unreleased":
            errors.append("qualification not unreleased: " + c["capability_key"])
        if c.get("release_state") != "candidate":
            errors.append("release_state must be candidate: " + c["capability_key"])
        if c.get("contract_status") not in {"unverified", "verified"}:
            errors.append("invalid contract_status: " + c["capability_key"])
        for dep in c.get("dependencies", []):
            if dep not in key_set:
                errors.append("unresolved dependency: " + c["capability_key"] + " -> " + dep)
        if c.get("layer") == "composite" and c.get("disposition") == "keep" and not c.get("dependencies"):
            errors.append("kept composite without dependencies: " + c["capability_key"])
        for p in c.get("providers", []):
            st = p.get("provider_status")
            if st not in {"verified", "unverified"}:
                errors.append("invalid provider_status: " + c["capability_key"])
            if st == "verified":
                ref = p.get("contract_ref") or ""
                if not ref or ref.startswith(".") or not (ROOT / ref).is_file():
                    errors.append("verified provider contract_ref not locatable: " + c["capability_key"] + " -> " + ref)
            if p.get("provider_type") == "unknown" and p.get("provider_ref"):
                errors.append("unknown provider must not carry provider_ref: " + c["capability_key"])
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--generate", action="store_true", help="write the candidate catalog (default: read-only check)")
    parser.add_argument("--check", action="store_true", help="run full semantic gates")
    args = parser.parse_args()

    if args.generate:
        catalog = build_catalog()
        OUT.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("generated", OUT)
    else:
        catalog = json.loads(OUT.read_text(encoding="utf-8"))

    errors = validate(catalog)
    if errors:
        print("FAIL")
        for e in errors:
            print(" -", e)
        return 1
    keep = sum(1 for c in catalog["capabilities"] if c["disposition"] == "keep")
    defer = sum(1 for c in catalog["capabilities"] if c["disposition"] == "defer")
    print(f"PASS keep={keep} defer={defer} total={len(catalog['capabilities'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
