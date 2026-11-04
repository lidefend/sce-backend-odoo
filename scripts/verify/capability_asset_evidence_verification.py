#!/usr/bin/env python3
"""CAP-02D-02-R1: evidence verification for 43 key capability assets (read-only).

Supplements each unresolved provider-only capability and each scene-only
candidate_missing reference with runtime/registry evidence and a recommendation.
It never creates capabilities, contracts, candidates or scenes.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CATALOG = ROOT / "docs/product/capability_candidate_catalog_v1.json"
ACCEPTANCE = ROOT / "addons/smart_construction_core/data/capability_acceptance_contracts_v1.json"
SCENES = ROOT / "docs/product/scene_catalog_v2.json"


def load_runtime(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    idx = raw.find('"schema": "module.runtime.facts.v1"')
    start = raw.rfind("{", 0, idx)
    depth = 0
    for i in range(start, len(raw)):
        if raw[i] == "{":
            depth += 1
        elif raw[i] == "}":
            depth -= 1
            if depth == 0:
                return json.loads(raw[start:i + 1])
    raise ValueError("runtime facts JSON not found")


def verify(catalog: list[dict], scenes: list[dict], acceptance: set[str],
           runtime: dict) -> dict:
    catalog_by_key = {c["capability_key"]: c for c in catalog}
    runtime_models = {o.get("model") for o in
                      (runtime.get("model_ownership") or {}).get("items", [])}
    runtime_actions = {a.get("xmlid") for a in (runtime.get("actions") or {}).get("items", [])
                       if a.get("xmlid")}
    runtime_intents = {h.get("intent") for h in
                       (runtime.get("intent_handlers") or {}).get("items", [])
                       if h.get("registered")}
    scene_to_caps: dict[str, list[str]] = {}
    for s in scenes:
        for cap in s.get("primary_capabilities", []) or []:
            scene_to_caps.setdefault(cap, []).append(s.get("scene_key"))

    unresolved_provider_only = [
        c for c in catalog
        if c["capability_key"] not in acceptance
        and c.get("layer") == "atomic"
        and c.get("disposition") == "defer"
        and not c["capability_key"].startswith("governance.")
    ]
    a_evidence = []
    for c in unresolved_provider_only:
        key = c["capability_key"]
        provider_resolution = []
        has_action = has_model = has_intent = False
        all_unreconciled = True
        for p in c.get("providers", []) or []:
            pt, ref = p.get("provider_type"), p.get("provider_ref")
            if pt in ("odoo_model", "odoo_action", "odoo_intent") and ref:
                all_unreconciled = False
                resolved = (ref in runtime_models if pt == "odoo_model"
                            else ref in runtime_actions if pt == "odoo_action"
                            else ref in runtime_intents)
            else:
                resolved = False
            has_action |= (pt == "odoo_action" and resolved)
            has_model |= (pt == "odoo_model" and resolved)
            has_intent |= (pt == "odoo_intent" and resolved)
            provider_resolution.append({"provider_type": pt, "provider_ref": ref, "resolved": resolved})
        scenes_hit = scene_to_caps.get(key, [])
        if all_unreconciled:
            verdict = "provider_unreconciled"
        elif has_action and scenes_hit:
            verdict = "contract_candidate"
        elif has_action and not scenes_hit:
            verdict = "composite" if c.get("layer") == "composite" else "unresolved"
        elif has_intent and has_model:
            verdict = "unresolved"
        else:
            verdict = "unresolved"
        a_evidence.append({
            "capability_key": key,
            "provider_resolution": provider_resolution,
            "scenes": scenes_hit,
            "frontend_delivery": has_action and bool(scenes_hit),
            "verdict": verdict,
        })

    catalog_keys = set(catalog_by_key)
    scene_only = sorted(set(scene_to_caps) - catalog_keys)
    b_evidence = []
    for key in scene_only:
        # runtime evidence by name fragments
        action_hits = sorted(a for a in runtime_actions
                             if any(frag in a for frag in key.split(".")[:3] if len(frag) > 3))
        intent_hit = key in runtime_intents
        b_evidence.append({
            "scene_capability": key,
            "scenes": scene_to_caps.get(key, []),
            "runtime_action_hits": action_hits[:6],
            "runtime_intent_hit": intent_hit,
            "verdict": "candidate_missing" if not action_hits and not intent_hit else "needs_human_review",
        })

    return {
        "schema": "cap02d.evidence.verification.v1",
        "A_provider_only_evidence": a_evidence,
        "B_scene_only_evidence": b_evidence,
    }


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--out", type=Path,
                        default=ROOT / "artifacts/backend/capability_asset_evidence_verification.json")
    args = parser.parse_args()
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))["capabilities"]
    scenes = json.loads(SCENES.read_text(encoding="utf-8"))["scenes"]
    acceptance = set(json.loads(ACCEPTANCE.read_text(encoding="utf-8"))["capabilities"].keys())
    runtime = load_runtime(args.runtime)
    report = verify(catalog, scenes, acceptance, runtime)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    va = {}
    for r in report["A_provider_only_evidence"]:
        va[r["verdict"]] = va.get(r["verdict"], 0) + 1
    vb = {}
    for r in report["B_scene_only_evidence"]:
        vb[r["verdict"]] = vb.get(r["verdict"], 0) + 1
    print(json.dumps({"A_verdicts": va, "B_verdicts": vb}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
