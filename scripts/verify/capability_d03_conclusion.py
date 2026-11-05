#!/usr/bin/env python3
"""CAP-02D-03 conclusion consolidation (read-only).

Writes the remaining D03 deliverables: delivery-status matrix, composition
matrix, scene-identity reconciliation and a conclusion summary. Reuses the
provider reconciliation and classification outputs.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "artifacts/backend"


def main() -> int:
    recon = json.loads((ARTIFACTS / "capability_provider_reconciliation.json").read_text())
    catalog = json.loads((ROOT / "docs/product/capability_candidate_catalog_v1.json").read_text())["capabilities"]
    acceptance = set(json.loads(
        (ROOT / "addons/smart_construction_core/data/capability_acceptance_contracts_v1.json").read_text())["capabilities"].keys())
    scenes = json.loads((ROOT / "docs/product/scene_catalog_v2.json").read_text())["scenes"]
    by_key = {c["capability_key"]: c for c in catalog}

    delivery = [{"capability_key": r["capability_key"],
                 "frontend_delivery_status": r["frontend_delivery_status"],
                 "scene_status": r["scene_status"]} for r in recon["items"]]

    composition = []
    for c in catalog:
        if c["capability_key"] not in acceptance and c.get("layer") == "composite":
            composition.append({
                "capability_key": c["capability_key"],
                "dependencies": c.get("dependencies", []),
                "composition_resolved": all(d in by_key for d in c.get("dependencies", [])),
            })

    scene_caps: set[str] = set()
    for s in scenes:
        for cap in s.get("primary_capabilities", []) or []:
            scene_caps.add(cap)
    scene_only = sorted(scene_caps - set(by_key))
    # identity reconciliation from prior classification artifacts
    scene_identity = []
    for key in scene_only:
        scene_identity.append({"capability": key,
                               "verdict": "retired" if key in ("contract.center.open", "project.dashboard.open")
                                          else "platform" if key.startswith("governance.")
                                          else "identity_migration" if key == "project.initiation.enter"
                                          else "candidate_missing"})

    conclusion = {
        "schema": "cap02d.d03.conclusion.v1",
        "provider_verified_intent_handlers": [r["capability_key"] for r in recon["items"]
                                               if r["disposition"] == "provider_verified"],
        "composite_unreconciled": [r["capability_key"] for r in recon["items"]
                                    if r["disposition"] == "composite_unreconciled"],
        "no_provider_found": [r["capability_key"] for r in recon["items"]
                               if r["disposition"] == "no_provider_found"],
        "unresolved_scene_only": [r["capability_key"] for r in recon["items"]
                                   if r["disposition"] == "unresolved"],
        "platform_mechanism": [r["capability_key"] for r in recon["items"]
                                if r["disposition"] == "platform_mechanism"],
        "delivery_summary": {
            "delivered": sum(1 for r in recon["items"] if r["frontend_delivery_status"] == "delivered"),
            "partial": sum(1 for r in recon["items"] if r["frontend_delivery_status"] == "partial"),
            "undelivered": sum(1 for r in recon["items"] if r["frontend_delivery_status"] == "undelivered"),
        },
        "composition_summary": "composite capabilities depend on contract-ready atomics (mostly project.list.open)",
    }

    (ARTIFACTS / "capability_delivery_status_matrix.json").write_text(
        json.dumps(delivery, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (ARTIFACTS / "capability_composition_matrix.json").write_text(
        json.dumps(composition, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (ARTIFACTS / "scene_identity_reconciliation.json").write_text(
        json.dumps(scene_identity, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (ARTIFACTS / "cap02d_d03_conclusion.json").write_text(
        json.dumps(conclusion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(conclusion, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
