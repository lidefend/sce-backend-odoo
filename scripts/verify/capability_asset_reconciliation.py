#!/usr/bin/env python3
"""CAP-02D-01: full-platform module capability asset reconciliation (read-only).

Reuses CAP-01B/01C/02B/02C artifacts: repository index (module_capability_index),
runtime facts (odoo_runtime_facts), candidate catalog, acceptance contracts,
scene catalog and SCE handler registry. It never creates a registry, scans
modules itself, promotes models to capabilities, or changes qualifications.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CATALOG = ROOT / "docs/product/capability_candidate_catalog_v1.json"
ACCEPTANCE = ROOT / "addons/smart_construction_core/data/capability_acceptance_contracts_v1.json"
SCENES = ROOT / "docs/product/scene_catalog_v2.json"


def load_runtime(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    idx = raw.find('"schema": "module.runtime.facts.v1"')
    if idx < 0:
        raise ValueError("runtime facts JSON marker not found")
    start = raw.rfind("{", 0, idx)
    depth = 0
    for i in range(start, len(raw)):
        if raw[i] == "{":
            depth += 1
        elif raw[i] == "}":
            depth -= 1
            if depth == 0:
                return json.loads(raw[start:i + 1])
    raise ValueError("runtime facts JSON object not found")


def _count_by_source(items: dict) -> dict:
    counts: dict[str, int] = {}
    for item in items.values():
        src = item.get("source") or "unknown"
        counts[src] = counts.get(src, 0) + 1
    return counts


def reconcile(index: dict, runtime: dict) -> dict:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))["capabilities"]
    acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))["capabilities"]
    scenes = json.loads(SCENES.read_text(encoding="utf-8"))["scenes"]

    reverse = index["reverse_index"]
    mechanism = index["mechanism_impact"]
    runtime_modules = (runtime.get("modules") or {}).get("items", {})
    catalog_keys = {c["capability_key"] for c in catalog}

    # scene -> capabilities from primary_capabilities
    capability_to_scenes: dict[str, set[str]] = {}
    for scene in scenes:
        for cap in scene.get("primary_capabilities", []) or []:
            capability_to_scenes.setdefault(cap, set()).add(scene.get("scene_key"))

    # A. module inventory: repo modules + full runtime module set
    from scripts.verify import module_capability_index as _mci
    inventory = {}
    runtime_inventory = {}
    for name, rt in runtime_modules.items():
        src = index["module_sources"].get(name, {}).get("source")
        if not src:
            src, _ = _mci._classify_external(name)
        runtime_inventory[name] = {
            "source": src,
            "installed": rt.get("state") == "installed",
            "version": rt.get("installed_version"),
        }
    for name, info in index["module_sources"].items():
        rt = runtime_modules.get(name, {})
        inventory[name] = {
            "source": info.get("source"),
            "installed": rt.get("state") == "installed",
            "version": rt.get("installed_version"),
            "capability_count": info.get("capability_count", 0),
        }

    # B. module -> provider/mechanism -> capability -> contract matrix
    matrix = {}
    for mod in sorted(set(reverse) | set(mechanism)):
        direct = sorted({e["capability_key"] for e in reverse.get(mod, [])})
        mech = sorted(mechanism.get(mod, []))
        caps = sorted(set(direct) | set(mech))
        matrix[mod] = {
            "direct_provider_capabilities": direct,
            "mechanism_dependency_capabilities": mech,
            "capability_count": len(caps),
            "contracts": sorted(c for c in caps if c in acceptance),
        }

    # C. capability / contract states
    cap_states = {}
    for c in catalog:
        key = c["capability_key"]
        providers = c.get("providers", []) or []
        has_contract = key in acceptance
        in_scene = key in capability_to_scenes
        if not providers:
            state = "unresolved"
        elif not has_contract:
            state = "provider_only"
        elif not in_scene:
            state = "scene_missing"
        else:
            state = "contract_ready"
        cap_states[key] = {
            "state": state,
            "provider_count": len(providers),
            "contract": has_contract,
            "in_scene": in_scene,
        }

    # D. scene / product bidirectional diff
    scene_caps = set(capability_to_scenes.keys())
    product_scenes = [s["scene_key"] for s in scenes if s.get("is_product_scene")]
    scene_diff = {
        "candidate_not_in_scene": sorted(catalog_keys - scene_caps),
        "scene_not_in_candidate": sorted(scene_caps - catalog_keys),
        "contract_without_candidate": sorted(set(acceptance) - catalog_keys),
        "multi_scene_capabilities": sorted(k for k, v in capability_to_scenes.items() if len(v) > 1),
        "product_scene_count": len(product_scenes),
    }

    # E. priority
    priority = {"P0": [], "P1": [], "P2": [], "P3": []}
    for key, st in cap_states.items():
        if st["state"] == "unresolved":
            priority["P0"].append(key)
        elif st["state"] == "provider_only":
            priority["P1"].append(key)
        elif st["state"] == "scene_missing":
            priority["P2"].append(key)
        else:
            priority["P3"].append(key)
    for key in scene_diff["scene_not_in_candidate"]:
        if key not in priority["P0"]:
            priority["P0"].append(key)

    by_source = {}
    for v in inventory.values():
        src = v.get("source") or "unknown"
        by_source[src] = by_source.get(src, 0) + 1
    return {
        "schema": "cap02d.asset.reconciliation.v1",
        "A_module_inventory": {
            "repo_modules": len(inventory),
            "installed_modules": sum(1 for v in inventory.values() if v["installed"]),
            "runtime_modules": len(runtime_inventory),
            "runtime_by_source": _count_by_source(runtime_inventory),
            "repo_by_source": by_source,
            "items": inventory,
            "runtime_items": runtime_inventory,
        },
        "B_module_provider_matrix": matrix,
        "C_capability_contract": cap_states,
        "D_scene_product_diff": scene_diff,
        "E_priority": priority,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--out", type=Path,
                        default=ROOT / "artifacts/backend/capability_asset_reconciliation.json")
    args = parser.parse_args()

    from scripts.verify import module_capability_index as mci
    index = mci.build()
    runtime = load_runtime(args.runtime)
    report = reconcile(index, runtime)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = {
        "modules": report["A_module_inventory"]["repo_modules"],
        "installed": report["A_module_inventory"]["installed_modules"],
        "runtime_modules": report["A_module_inventory"]["runtime_modules"],
        "runtime_by_source": report["A_module_inventory"]["runtime_by_source"],
        "repo_by_source": report["A_module_inventory"]["repo_by_source"],
        "capability_states": {k: sum(1 for v in report["C_capability_contract"].values() if v["state"] == k)
                              for k in ("provider_only", "contract_ready", "scene_missing", "unresolved")},
        "scene_diff": report["D_scene_product_diff"],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
