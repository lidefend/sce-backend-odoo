#!/usr/bin/env python3
"""CAP-02C-04 D3: capability impact propagation (read-only).

Consumes D1/D2 change results and propagates them through real associations:

  changed asset -> provider module -> capability -> contract -> scene/product.

Rules:
  * only real associations (``reverse_index`` / ``mechanism_impact`` /
    capability-to-scene mapping), never name-prefix guessing;
  * one asset may hit many capabilities and one capability many assets;
  * every result keeps a full ``evidence_path``;
  * anything that cannot be resolved is ``unresolved_impact``, never "no impact".

This module never changes capability maturity, release state, or triggers
re-certification.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

CATALOG = ROOT / "docs/product/capability_candidate_catalog_v1.json"
ACCEPTANCE = ROOT / "addons/smart_construction_core/data/capability_acceptance_contracts_v1.json"
SCENES = ROOT / "docs/product/scene_catalog_v2.json"


def _affected_modules(asset: dict) -> set[str]:
    mods = set(asset.get("asset_modules") or [])
    if asset.get("model_owner"):
        mods.add(asset["model_owner"])
    for m in (asset.get("model_extensions") or []):
        mods.add(m)
    return {m for m in mods if m}


def _dedupe(items: list[Any]) -> list[Any]:
    seen: set[str] = set()
    out: list[Any] = []
    for item in items:
        key = json.dumps(item, sort_keys=True, ensure_ascii=False, default=str)
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out


def propagate(changed_assets: list[dict], *, reverse_index: dict[str, list[dict]],
              mechanism_impact: dict[str, list[str]], acceptance_capabilities: set[str],
              capability_to_scenes: dict[str, list[str]], product_scene_keys: set[str],
              capability_dependencies: dict[str, list[str]] | None = None,
              repository_coverage: bool = True,
              runtime_coverage: bool = True,
              handler_registry_complete: bool = True,
              uncovered_runtime: list | None = None) -> dict:
    """Propagate changed assets into an impact report."""
    impacted: dict[str, dict] = {}
    unresolved: list[dict] = []
    capability_dependencies = capability_dependencies or {}
    associations_complete = repository_coverage and runtime_coverage and handler_registry_complete

    for asset in changed_assets:
        asset_id = asset.get("fact_identity") or asset.get("asset_type")
        if asset.get("asset_type") == "intent":
            intent_status = "runtime_unverified"
            if asset.get("handler_missing"):
                intent_status = "handler_missing"
            elif (asset.get("value", {}).get("handler")
                  and (asset.get("asset_modules") or asset.get("value", {}).get("module"))):
                intent_status = "handler_resolved"
            if intent_status != "handler_resolved":
                unresolved.append({"subject": asset_id, "reason": intent_status})
                continue
        if asset.get("model_extensions_incomplete"):
            unresolved.append({
                "subject": asset_id,
                "reason": "model_extensions_incomplete",
                "unaccounted_contributions": asset.get("unaccounted_contributions", []),
            })
        modules = _affected_modules(asset)
        if not modules:
            unresolved.append({"subject": asset_id, "reason": "no_resolvable_module"})
            continue
        for module in sorted(modules):
            provider_refs = [e.get("provider_ref") for e in reverse_index.get(module, [])
                             if e.get("provider_ref")]
            capabilities = {e.get("capability_key") for e in reverse_index.get(module, [])
                            if e.get("capability_key")}
            capabilities.update(mechanism_impact.get(module, []) or [])
            if not capabilities:
                reason = "no_association_confirmed" if associations_complete else "association_unresolved"
                unresolved.append({"subject": module, "asset": asset_id, "reason": reason})
                continue
            for cap in sorted(capabilities):
                contract = cap in acceptance_capabilities
                scenes = sorted(capability_to_scenes.get(cap, []) or [])
                product_scenes = sorted(s for s in scenes if s in product_scene_keys)
                dispositions = {
                    e.get("disposition")
                    for e in reverse_index.get(module, [])
                    if e.get("capability_key") == cap and e.get("disposition")
                }
                entry = impacted.setdefault(cap, {
                    "capability_key": cap,
                    "providers": [],
                    "evidence_paths": [],
                    "dependencies": capability_dependencies.get(cap, []),
                    "contract": contract,
                    "scenes": scenes,
                    "product_scenes": product_scenes,
                    "historical": "retire" in dispositions,
                })
                entry["providers"].append({"module": module,
                                           "provider_refs": sorted(set(provider_refs))})
                path = [asset_id, module, cap]
                if contract:
                    path.append("contract")
                path.extend(scenes)
                entry["evidence_paths"].append(path)
                if not contract:
                    unresolved.append({"subject": cap, "asset": asset_id, "reason": "contract_missing"})
                if not scenes:
                    unresolved.append({"subject": cap, "asset": asset_id, "reason": "scene_missing"})

    for entry in impacted.values():
        entry["providers"] = _dedupe(entry["providers"])
        entry["evidence_paths"] = _dedupe(entry["evidence_paths"])
    return {
        "impacted_capabilities": list(impacted.values()),
        "impacted_contracts": [e for e in impacted.values() if e["contract"]],
        "impacted_product_scenes": [
            {"capability_key": e["capability_key"], "scenes": e["product_scenes"]}
            for e in impacted.values() if e["product_scenes"]
        ],
        "unresolved": _dedupe(unresolved),
        "has_unresolved_impact": bool(unresolved),
        "association_coverage": {
            "repository_coverage": repository_coverage,
            "runtime_coverage": runtime_coverage,
            "handler_registry_complete": handler_registry_complete,
            "associations_complete": associations_complete,
        },
        "uncovered_runtime": uncovered_runtime or [],
    }


def build_context(reverse_index: dict | None = None,
                  mechanism_impact: dict | None = None,
                  runtime_snapshot: dict | None = None) -> dict:
    """Load the real SCE associations for a concrete propagation run."""
    if reverse_index is None:
        from scripts.verify import module_capability_index as mci
        reverse_index = mci._reverse_index()
        mechanism_impact = mci._mechanism_impact()
    acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))["capabilities"]
    scenes = json.loads(SCENES.read_text(encoding="utf-8"))["scenes"]
    product_scene_keys = {s.get("scene_key") for s in scenes if s.get("is_product_scene")}
    capability_to_scenes: dict[str, set[str]] = {}
    for scene in scenes:
        for cap in scene.get("primary_capabilities", []) or []:
            capability_to_scenes.setdefault(cap, set()).add(scene.get("scene_key"))
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))["capabilities"]
    runtime_coverage = False
    handler_registry_complete = False
    uncovered_runtime: list[dict] = []
    if runtime_snapshot is not None:
        coverage = compute_runtime_coverage(reverse_index, mechanism_impact, runtime_snapshot)
        runtime_coverage = coverage["runtime_coverage"]
        handler_registry_complete = coverage["handler_registry_complete"]
        uncovered_runtime = coverage["uncovered"]
    return {
        "reverse_index": reverse_index,
        "mechanism_impact": mechanism_impact or {},
        "acceptance_capabilities": set(acceptance.keys()),
        "capability_to_scenes": {k: sorted(v) for k, v in capability_to_scenes.items()},
        "product_scene_keys": product_scene_keys,
        "repository_coverage": True,
        "runtime_coverage": runtime_coverage,
        "handler_registry_complete": handler_registry_complete,
        "uncovered_runtime": uncovered_runtime,
        "capability_dependencies": {
            c["capability_key"]: c.get("dependencies", []) for c in catalog
        },
    }


def compute_runtime_coverage(reverse_index: dict[str, list[dict]],
                             mechanism_impact: dict[str, list[str]],
                             runtime_snapshot: dict) -> dict:
    """Coverage derived from actual provider/asset/handler facts, not module names."""
    runtime_modules = set((runtime_snapshot.get("modules") or {}).get("items", {}).keys())
    ownership = (runtime_snapshot.get("model_ownership") or {}).get("items", []) or []
    runtime_models = {o.get("model") for o in ownership}
    owner_by_model = {o.get("model"): o.get("model_owner") or "" for o in ownership}
    runtime_actions = {a.get("xmlid") for a in (runtime_snapshot.get("actions") or {}).get("items", [])
                       if a.get("xmlid")}
    runtime_views = {v.get("xmlid") for v in (runtime_snapshot.get("views") or {}).get("items", [])
                     if v.get("xmlid")}
    runtime_intents = {h.get("intent") for h in (runtime_snapshot.get("intent_handlers") or {}).get("items", [])
                       if h.get("registered")}
    handler_complete = (runtime_snapshot.get("intent_handlers") or {}).get("completeness") == "complete"

    uncovered: list[dict] = []
    catalog_modules = set(reverse_index.keys()) | set((mechanism_impact or {}).keys())
    for module in sorted(catalog_modules - runtime_modules):
        uncovered.append({"module": module, "kind": "module_not_in_runtime"})
    for module, entries in reverse_index.items():
        for entry in entries:
            provider_type = entry.get("provider_type")
            provider_ref = entry.get("provider_ref") or ""
            if not provider_ref:
                continue
            if provider_type == "odoo_model":
                if provider_ref not in runtime_models:
                    uncovered.append({"module": module, "kind": "provider_asset_missing",
                                      "provider_type": provider_type, "provider_ref": provider_ref})
                elif provider_ref in owner_by_model and not owner_by_model[provider_ref]:
                    uncovered.append({"module": module, "kind": "owner_unresolved",
                                      "provider_ref": provider_ref})
            elif provider_type == "odoo_action" and provider_ref not in runtime_actions:
                uncovered.append({"module": module, "kind": "provider_asset_missing",
                                  "provider_type": provider_type, "provider_ref": provider_ref})
            elif provider_type == "odoo_intent" and provider_ref not in runtime_intents:
                uncovered.append({"module": module, "kind": "intent_handler_missing",
                                  "provider_ref": provider_ref})
    return {
        "runtime_coverage": bool(not uncovered) and handler_complete,
        "handler_registry_complete": handler_complete,
        "uncovered": uncovered,
    }
