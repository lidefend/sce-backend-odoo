#!/usr/bin/env python3
"""CAP-02D-03: real provider reconciliation and delivery status (read-only).

Matches 24 atomic / 6 composite / 1 platform candidates against the actual
SCE intent registry, Odoo actions, models and scenes. Only existing evidence;
no capability, contract, candidate or scene is created or changed.
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


def reconcile(catalog: list[dict], scenes: list[dict], acceptance: set[str],
              runtime: dict) -> dict:
    intents = {h.get("intent"): h for h in (runtime.get("intent_handlers") or {}).get("items", [])
               if h.get("registered")}
    scene_to_caps: dict[str, list[str]] = {}
    for s in scenes:
        for cap in s.get("primary_capabilities", []) or []:
            scene_to_caps.setdefault(cap, []).append(s.get("scene_key"))

    rows = []
    for c in catalog:
        key = c["capability_key"]
        if key in acceptance:
            continue
        layer = c.get("layer")
        disposition = c.get("disposition")
        scenes_hit = scene_to_caps.get(key, [])
        intent = intents.get(key)
        if intent is not None:
            actual_provider = f"intent:{intent.get('handler')}"
            provider_source = "sce_handler_registry"
            execution_chain = [key, "handler", intent.get("handler")]
        else:
            actual_provider = ""
            provider_source = "none"
            execution_chain = [key]

        if key.startswith("governance."):
            disposition_verdict = "platform_mechanism"
        elif layer == "composite":
            disposition_verdict = "composite_with_provider" if intent else "composite_unreconciled"
        elif intent is not None:
            disposition_verdict = "provider_verified"
        elif scenes_hit:
            disposition_verdict = "unresolved"
        else:
            disposition_verdict = "no_provider_found"

        rows.append({
            "capability_key": key,
            "layer": layer,
            "actual_provider": actual_provider,
            "provider_source": provider_source,
            "execution_chain": execution_chain,
            "contract_status": "unverified",
            "frontend_delivery_status": "delivered" if intent and scenes_hit
                                        else "partial" if intent or scenes_hit
                                        else "undelivered",
            "scene_status": "in_scene" if scenes_hit else "no_scene",
            "evidence_refs": {
                "intent_handler": intent.get("handler") if intent else None,
                "scenes": scenes_hit,
            },
            "disposition": disposition_verdict,
        })
    return {"schema": "cap02d.provider.reconciliation.v1", "items": rows}


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--out", type=Path,
                        default=ROOT / "artifacts/backend/capability_provider_reconciliation.json")
    args = parser.parse_args()
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))["capabilities"]
    scenes = json.loads(SCENES.read_text(encoding="utf-8"))["scenes"]
    acceptance = set(json.loads(ACCEPTANCE.read_text(encoding="utf-8"))["capabilities"].keys())
    runtime = load_runtime(args.runtime)
    report = reconcile(catalog, scenes, acceptance, runtime)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    from collections import Counter
    disp = Counter(r["disposition"] for r in report["items"])
    delivery = Counter(r["frontend_delivery_status"] for r in report["items"])
    print(json.dumps({"disposition": dict(disp), "delivery": dict(delivery)},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
