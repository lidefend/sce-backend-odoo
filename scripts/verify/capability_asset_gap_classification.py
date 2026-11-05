#!/usr/bin/env python3
"""CAP-02D-02: capability asset gap classification (read-only, evidence-bound).

Workflow A classifies the 31 provider-only capabilities; workflow B reconciles
the 25 scene-only references. Every verdict is derived from existing evidence
(candidate layer/disposition/aliases, scene status, governance prefix,
deprecated registry entries). No capability, contract, candidate or scene is
created, edited or deleted.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CATALOG = ROOT / "docs/product/capability_candidate_catalog_v1.json"
ACCEPTANCE = ROOT / "addons/smart_construction_core/data/capability_acceptance_contracts_v1.json"
SCENES = ROOT / "docs/product/scene_catalog_v2.json"
REGISTRY = ROOT / "addons/smart_construction_core/services/capability_registry.py"


def _deprecated_keys() -> set[str]:
    text = REGISTRY.read_text(encoding="utf-8")
    keys: set[str] = set()
    # capture capability keys whose _cap(...) block carries status="deprecated"
    for block in re.findall(r'_cap\(\s*"([a-z][a-z0-9_.]+)"', text):
        pass
    for m in re.finditer(
            r'_cap\(\s*"([a-z][a-z0-9_.]+)"(.*?)(?=\n\s*_cap\(|\n\s*\]|\Z)', text, re.S):
        key, body = m.group(1), m.group(2)
        if re.search(r'status\s*=\s*"deprecated"', body):
            keys.add(key)
    return keys


def classify(catalog: list[dict], scenes: list[dict], acceptance: set[str]) -> dict:
    catalog_by_key = {c["capability_key"]: c for c in catalog}
    scene_caps: set[str] = set()
    for s in scenes:
        for c in s.get("primary_capabilities", []) or []:
            scene_caps.add(c)

    alias_map: dict[str, str] = {}
    for c in catalog:
        for alias in c.get("compatibility_aliases", []) or []:
            alias_map[alias] = c["capability_key"]
    deprecated = _deprecated_keys()

    provider_only = [c for c in catalog if c["capability_key"] not in acceptance]
    a_matrix = []
    for c in provider_only:
        key = c["capability_key"]
        layer = c.get("layer")
        disposition = c.get("disposition")
        if layer == "composite":
            verdict = "composite"
        elif key.startswith("governance."):
            verdict = "platform_mechanism"
        elif disposition == "defer":
            verdict = "unresolved"
        else:
            verdict = "unresolved"
        a_matrix.append({
            "capability_key": key,
            "layer": layer,
            "disposition": disposition,
            "dependencies": len(c.get("dependencies", []) or []),
            "in_scene": key in scene_caps,
            "verdict": verdict,
            "evidence": f"layer={layer}; disposition={disposition}",
        })

    scene_only = sorted(scene_caps - set(catalog_by_key))
    b_matrix = []
    for key in scene_only:
        if key in alias_map:
            verdict = "identity_migration"
            evidence = f"compatibility_alias of {alias_map[key]}"
        elif key in deprecated:
            verdict = "retired_capability"
            evidence = "registry status=deprecated"
        elif key.startswith("governance."):
            verdict = "platform_mechanism"
            evidence = "governance platform key"
        else:
            verdict = "candidate_missing"
            evidence = "scene references a non-catalog capability with no alias/deprecated marker"
        b_matrix.append({"scene_capability": key, "verdict": verdict, "evidence": evidence})

    contract_candidates = [r["capability_key"] for r in a_matrix if r["verdict"] == "contract_candidate"]
    not_contract = [
        {"capability_key": r["capability_key"], "reason": r["verdict"], "evidence": r["evidence"]}
        for r in a_matrix if r["verdict"] != "contract_candidate"
    ]
    return {
        "schema": "cap02d.gap.classification.v1",
        "A_workflow_A_31_provider_only": a_matrix,
        "B_workflow_B_25_scene_only": b_matrix,
        "C_recommended_contract_candidates": contract_candidates,
        "D_not_independently_contractualized": not_contract,
        "E_priority": {
            "P1_contract_candidates": contract_candidates,
            "P1_composite_to_review": [r["capability_key"] for r in a_matrix if r["verdict"] == "composite"],
            "P2_unresolved_to_review": [r["capability_key"] for r in a_matrix if r["verdict"] == "unresolved"],
            "P3_platform_and_legacy": [r["capability_key"] for r in a_matrix if r["verdict"] in ("platform_mechanism", "legacy")],
            "scene_identity_reconciliation": [
                {"capability": r["scene_capability"], "verdict": r["verdict"]}
                for r in b_matrix
            ],
        },
    }


def main() -> int:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))["capabilities"]
    scenes = json.loads(SCENES.read_text(encoding="utf-8"))["scenes"]
    acceptance = set(json.loads(ACCEPTANCE.read_text(encoding="utf-8"))["capabilities"].keys())
    report = classify(catalog, scenes, acceptance)
    out = ROOT / "artifacts/backend/capability_asset_gap_classification.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    verdicts_a = {}
    for r in report["A_workflow_A_31_provider_only"]:
        verdicts_a[r["verdict"]] = verdicts_a.get(r["verdict"], 0) + 1
    verdicts_b = {}
    for r in report["B_workflow_B_25_scene_only"]:
        verdicts_b[r["verdict"]] = verdicts_b.get(r["verdict"], 0) + 1
    print(json.dumps({"workflow_A": verdicts_a, "workflow_B": verdicts_b,
                      "contract_candidates": report["C_recommended_contract_candidates"]},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
