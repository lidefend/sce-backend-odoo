#!/usr/bin/env python3
"""CAP-02D-04 batch 3/4: composite convergence + 13 no-provider decisions."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "docs/product/capability_candidate_catalog_v1.json"
ACCEPTANCE = ROOT / "addons/smart_construction_core/data/capability_acceptance_contracts_v1.json"

NO_PROVIDER_MODELS = {
    "construction.diary.open": ["sc.construction.diary"],
    "equipment.request.list": ["sc.equipment.request"],
    "equipment.settlement.list": ["sc.equipment.settlement"],
    "equipment.usage.list": ["sc.equipment.usage"],
    "labor.attendance.list": ["sc.attendance.checkin"],
    "labor.request.list": ["sc.labor.request"],
    "labor.settlement.list": ["sc.labor.settlement"],
    "quality.issue.list": ["sc.quality.issue"],
    "quality.recheck.list": ["sc.quality.recheck"],
    "quality.rectification.list": ["sc.quality.rectification"],
    "safety.issue.list": ["sc.safety.issue"],
    "safety.recheck.list": ["sc.safety.recheck"],
    "safety.rectification.list": ["sc.safety.rectification"],
}


def build(catalog: list[dict], acceptance: set[str], runtime: dict) -> dict:
    models = {o.get("model") for o in (runtime.get("model_ownership") or {}).get("items", [])}
    composite = []
    for c in catalog:
        if c["capability_key"] not in acceptance and c.get("layer") == "composite":
            deps = c.get("dependencies", [])
            composite.append({
                "capability_key": c["capability_key"],
                "dependencies": deps,
                "composition_resolved": all(d in {x["capability_key"] for x in catalog} for d in deps),
                "verdict": "composite_entry" if deps else "unresolved",
                "reuse_atomic": deps,
            })
    decisions = []
    for key, expected in NO_PROVIDER_MODELS.items():
        found = sorted(m for m in expected if m in models)
        verdict = "retain" if found else "confirm"
        decisions.append({
            "capability_key": key,
            "runtime_models": found,
            "verdict": verdict,
            "evidence": f"runtime model {found[0]} exists" if found else "no direct model",
        })
    return {
        "schema": "cap02d.composite.and.decision.v1",
        "composite_convergence": composite,
        "no_provider_decisions": decisions,
    }


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, required=True)
    args = parser.parse_args()
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))["capabilities"]
    acceptance = set(json.loads(ACCEPTANCE.read_text(encoding="utf-8"))["capabilities"].keys())
    raw = args.runtime.read_text(encoding="utf-8")
    idx = raw.find('"schema": "module.runtime.facts.v1"')
    start = raw.rfind("{", 0, idx)
    depth = 0
    for i in range(start, len(raw)):
        if raw[i] == "{":
            depth += 1
        elif raw[i] == "}":
            depth -= 1
            if depth == 0:
                runtime = json.loads(raw[start:i + 1])
                break
    report = build(catalog, acceptance, runtime)
    out = ROOT / "artifacts/backend/capability_composite_and_decision.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    from collections import Counter
    c = Counter(r["verdict"] for r in report["no_provider_decisions"])
    comp = Counter(r["verdict"] for r in report["composite_convergence"])
    print(json.dumps({"composite": dict(comp), "no_provider_decision": dict(c)},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
