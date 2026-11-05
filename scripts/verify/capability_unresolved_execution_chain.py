#!/usr/bin/env python3
"""CAP-02D-04 batch 2: execution-chain verification for 6 unresolved candidates."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCENES = ROOT / "docs/product/scene_catalog_v2.json"
ACCEPTANCE = ROOT / "addons/smart_construction_core/data/capability_acceptance_contracts_v1.json"

DOMAIN_MODELS = {
    "project.risk.list": ["project.risk", "project.risk.action", "sc.risk.item", "sc.risk.library"],
    "material.procurement.list": ["project.material.plan", "sc.material.purchase.request", "sc.material.catalog"],
    "finance.exception.monitor": [],
    "finance.plan.funding": ["project.funding.baseline", "sc.fund.account", "sc.self.funding.registration"],
    "finance.settlement.order": ["project.settlement", "sc.settlement.adjustment"],
    "analytics.lifecycle.monitor": [],
}


def verify(runtime: dict, scenes: list[dict], acceptance: set[str]) -> dict:
    models = {o.get("model") for o in (runtime.get("model_ownership") or {}).get("items", [])}
    scene_caps: dict[str, list[str]] = {}
    for s in scenes:
        for cap in s.get("primary_capabilities", []) or []:
            scene_caps.setdefault(cap, []).append(s.get("scene_key"))
    rows = []
    for key, expected in DOMAIN_MODELS.items():
        found = sorted(m for m in expected if m in models)
        co = set()
        for s_key in scene_caps.get(key, []):
            for s in scenes:
                if s.get("scene_key") == s_key:
                    for c in s.get("primary_capabilities", []) or []:
                        if c in acceptance:
                            co.add(c)
        if key == "analytics.lifecycle.monitor" and "project.lifecycle.transition" in co:
            verdict = "absorbed_by_existing"
        elif found:
            verdict = "composite_member" if key.endswith(".list") else "provider_found"
        elif co:
            verdict = "absorbed_by_existing"
        else:
            verdict = "unresolved"
        rows.append({
            "capability_key": key,
            "runtime_models": found,
            "co_referenced_contract_ready": sorted(co),
            "scene_count": len(scene_caps.get(key, [])),
            "verdict": verdict,
        })
    return {"schema": "cap02d.unresolved.execution_chain.v1", "items": rows}


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, required=True)
    args = parser.parse_args()
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
    scenes = json.loads(SCENES.read_text(encoding="utf-8"))["scenes"]
    acceptance = set(json.loads(ACCEPTANCE.read_text(encoding="utf-8"))["capabilities"].keys())
    report = verify(runtime, scenes, acceptance)
    out = ROOT / "artifacts/backend/capability_unresolved_execution_chain.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
