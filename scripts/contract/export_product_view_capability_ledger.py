#!/usr/bin/env python3
"""Build the deterministic product native-view capability loss ledger."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from scripts.contract.product_view_capability_ledger_common import classify_structure, load_yaml
from scripts.contract.product_view_contract_carriers_common import atomic_write_json, with_manifest
from scripts.contract.product_view_structure_common import file_sha256, sha256_json


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "product_view_capability_ledger/v1"


def _mapping(atom: dict[str, Any], mappings: list[dict[str, Any]]) -> tuple[int, dict[str, Any]]:
    matches = []
    for index, mapping in enumerate(mappings):
        if atom["view_type"] not in mapping.get("view_types", []):
            continue
        key = atom["capability_key"]
        if key in mapping.get("excluded_capability_keys", []):
            continue
        if key in mapping.get("capability_keys", []) or any(key.startswith(prefix) for prefix in mapping.get("capability_prefixes", [])):
            matches.append((index, mapping))
    if len(matches) != 1:
        raise ValueError(f"{atom['atom_id']}: expected one mapping, got {len(matches)}")
    return matches[0]


def _frontend_mapping(atom: dict[str, Any], mappings: list[dict[str, Any]]) -> tuple[int, dict[str, Any]]:
    matches = [
        (index, mapping) for index, mapping in enumerate(mappings)
        if atom["view_type"] in mapping.get("view_types", []) and atom["capability_key"] in mapping.get("capability_keys", [])
    ]
    if len(matches) != 1:
        raise ValueError(f"{atom['atom_id']}: expected one frontend mapping, got {len(matches)}")
    return matches[0]


def _fingerprint_subset(value: dict[str, Any]) -> dict[str, Any]:
    return {key: value[key] for key in ("algorithm", "git_head", "baseline_sha", "scope_manifest_sha256", "digest")}


def build_ledger(
    structure: dict[str, Any], carrier: dict[str, Any], fingerprint: dict[str, Any], taxonomy: dict[str, Any],
    normalized_map: dict[str, Any], frontend_map: dict[str, Any], reasons: dict[str, Any], paths: dict[str, Path],
) -> dict[str, Any]:
    path_hashes = {name: file_sha256(ROOT / path) for name, path in paths.items()}
    if structure["authority"]["candidate_fingerprint"]["digest"] != fingerprint["digest"]:
        raise ValueError("structure fingerprint mismatch")
    if carrier["authority"]["candidate_fingerprint"]["digest"] != fingerprint["digest"]:
        raise ValueError("carrier fingerprint mismatch")
    classified = classify_structure(structure, taxonomy)
    if classified["unknown"] or classified["ambiguous"]:
        raise ValueError("native taxonomy is not closed")
    atoms_by_ref: dict[str, list[dict[str, Any]]] = {}
    for atom in classified["atoms"]:
        atoms_by_ref.setdefault(atom["contract_ref"], []).append(atom)
    carriers = {entry["contract_ref"]: entry for entry in carrier["entries"]}
    reason_codes = {entry["code"] for entry in reasons["entries"]}
    entries = []
    terminal_counts: Counter[str] = Counter()
    for entry_index, structure_entry in enumerate(structure["entries"]):
        for surface_index, surface in enumerate(structure_entry["surfaces"]):
            contract_ref = surface["contract_ref"]
            carrier_entry = carriers.get(contract_ref)
            if carrier_entry is None:
                raise ValueError(f"missing carrier: {contract_ref}")
            contributors = surface["source_graph"]["contributors"]
            source_proven = len(contributors) == 1 and contributors[0].get("applicability") == "applied"
            synthetic = surface.get("source_kind") == "synthetic_default_view"
            surface_atoms = []
            for atom in atoms_by_ref.get(contract_ref, []):
                normalized_index, normalized_mapping = _mapping(atom, normalized_map["mappings"])
                if normalized_mapping.get("mapping_status") != "mapping_unproven":
                    raise ValueError("ledger v1 does not accept an unimplemented proven matcher")
                frontend_index, frontend_mapping = _frontend_mapping(atom, frontend_map["mappings"])
                if synthetic:
                    origin_status, origin_ref = "synthetic_default", ""
                elif source_proven:
                    origin_status, origin_ref = "proven", contributors[0]["view_ref"]
                else:
                    origin_status, origin_ref = "unproven", ""
                terminal_status = "unsupported"
                reason_code = (
                    "CAPABILITY_NATIVE_OCCURRENCE_ORIGIN_UNPROVEN"
                    if origin_status == "unproven"
                    else "CAPABILITY_NORMALIZED_MAPPING_UNPROVEN"
                )
                if reason_code not in reason_codes:
                    raise ValueError(f"unregistered reason: {reason_code}")
                terminal_counts[terminal_status] += 1
                normalized_refs = [item["source_selector"] for item in carrier_entry["normalized_carriers"]]
                surface_atoms.append({
                    "atom_id": atom["atom_id"], "capability_key": atom["capability_key"],
                    "native": {
                        "occurrence_index": atom["occurrence_index"], "resolved_view_ref": atom["resolved_view_ref"],
                        "origin_view_ref": origin_ref, "origin_status": origin_status, "locator": atom["locator"],
                        "canonical_value": atom["canonical_value"], "value_hash": atom["value_hash"],
                    },
                    "normalized": {"status": "unproven", "count": 0, "carrier_refs": normalized_refs, "value_hash": "", "source_authority": "normalized_contract"},
                    "semantic": {"status": "missing", "count": 0, "carrier_refs": [], "value_hash": "", "source_authority": "none"},
                    "frontend": {
                        "status": frontend_mapping["frontend_status"], "canonical_atom_ref": atom["atom_id"],
                        "projection_atom_ref": "", "consumer_symbol": frontend_mapping["consumer_symbol"],
                        "renderer_key": frontend_mapping["renderer_key"], "interaction_symbol": frontend_mapping["interaction_symbol"],
                        "value_hash": sha256_json(frontend_mapping), "source_authority": "compatibility_projection", "source_count": 1,
                    },
                    "terminal_status": terminal_status, "reason_code": reason_code,
                    "evidence_refs": [
                        {"path": str(paths["structure"]), "sha256": path_hashes["structure"], "candidate_fingerprint": fingerprint["digest"], "stage": "native", "selector": f"json-pointer:{atom['source_selector']}"},
                        *[
                            {"path": str(paths["carrier"]), "sha256": path_hashes["carrier"], "candidate_fingerprint": fingerprint["digest"], "stage": "normalized", "selector": f"json-pointer:{item['artifact_selector']}"}
                            for item in carrier_entry["normalized_carriers"]
                        ],
                        {"path": str(paths["normalized_map"]), "sha256": path_hashes["normalized_map"], "candidate_fingerprint": fingerprint["digest"], "stage": "normalized", "selector": f"json-pointer:/mappings/{normalized_index}"},
                        {"path": str(paths["frontend_map"]), "sha256": path_hashes["frontend_map"], "candidate_fingerprint": fingerprint["digest"], "stage": "frontend", "selector": f"json-pointer:/mappings/{frontend_index}"},
                    ],
                })
            entries.append({
                "contract_ref": contract_ref, "menu_xmlid": surface["menu_xmlid"], "action_xmlid": surface["action_xmlid"],
                "model": surface["model"], "view_type": surface["view_type"], "view_ref": surface["view_ref"],
                "hashes": surface["hashes"], "source_graph": surface["source_graph"], "parse_outcome": surface["parse_outcome"],
                "atoms": surface_atoms,
            })
    authority_source = structure["authority"]
    authority = {
        "branch": authority_source["branch"], "candidate_fingerprint": _fingerprint_subset(fingerprint),
        "fingerprint_evidence_path": str(paths["fingerprint"]), "fingerprint_evidence_sha256": path_hashes["fingerprint"],
        "database_policy_path": authority_source["database_policy_path"], "database_policy_sha256": authority_source["database_policy_sha256"],
        "formal_menu_policy_path": authority_source["formal_menu_policy_path"], "formal_menu_policy_sha256": authority_source["formal_menu_policy_sha256"],
        "reason_registry_path": str(paths["reasons"]), "reason_registry_sha256": path_hashes["reasons"],
        "taxonomy_path": str(paths["taxonomy"]), "taxonomy_sha256": path_hashes["taxonomy"],
        "normalized_map_path": str(paths["normalized_map"]), "normalized_map_sha256": path_hashes["normalized_map"],
        "frontend_map_path": str(paths["frontend_map"]), "frontend_map_sha256": path_hashes["frontend_map"],
        "view_structure_evidence_path": str(paths["structure"]), "view_structure_evidence_sha256": path_hashes["structure"], "view_structure_manifest_sha256": structure["manifest_sha256"],
        "carrier_evidence_path": str(paths["carrier"]), "carrier_evidence_sha256": path_hashes["carrier"], "carrier_evidence_manifest_sha256": carrier["manifest_sha256"],
        "runtime_profile": authority_source["runtime_profile"], "compose_project": authority_source["compose_project"], "database": authority_source["database"], "database_filter": authority_source["database_filter"], "demo_data": authority_source["demo_data"],
        "module_set": authority_source["module_set"], "module_set_sha256": authority_source["module_set_sha256"], "user": authority_source["user"], "company": authority_source["company"], "language": authority_source["language"], "group_profile": authority_source["group_profile"], "exporter_version": SCHEMA,
    }
    summary_source = structure["summary"]
    return with_manifest({
        "schema": SCHEMA, "authority": authority,
        "summary": {
            "formal_menu_count": summary_source["formal_menu_count"], "model_count": summary_source["model_count"], "resolved_surface_count": summary_source["resolved_surface_count"],
            "native_candidate_count": len(classified["atoms"]), "classified_atom_count": len(classified["atoms"]), "excluded_native_count": 0, "unclassified_native_count": 0, "ambiguous_native_count": 0,
            "capability_atom_count": len(classified["atoms"]), "ready_count": 0, "fallback_count": terminal_counts["fallback"], "unsupported_count": terminal_counts["unsupported"], "silent_loss_count": 0,
            "view_type_counts": summary_source["view_type_counts"],
        }, "entries": entries,
    })


def main() -> int:
    parser = argparse.ArgumentParser()
    for name in ("structure", "carrier", "fingerprint", "taxonomy", "normalized_map", "frontend_map", "reasons", "output"):
        parser.add_argument(f"--{name.replace('_', '-')}", required=True)
    args = parser.parse_args()
    output = ROOT / args.output
    output.unlink(missing_ok=True)
    paths = {name: Path(getattr(args, name)) for name in ("structure", "carrier", "fingerprint", "taxonomy", "normalized_map", "frontend_map", "reasons")}
    ledger = build_ledger(
        json.loads((ROOT / paths["structure"]).read_text()), json.loads((ROOT / paths["carrier"]).read_text()), json.loads((ROOT / paths["fingerprint"]).read_text()),
        load_yaml(ROOT / paths["taxonomy"]), load_yaml(ROOT / paths["normalized_map"]), load_yaml(ROOT / paths["frontend_map"]), load_yaml(ROOT / paths["reasons"]), paths,
    )
    atomic_write_json(output, ledger)
    print(json.dumps({"status": "PASS", "atom_count": ledger["summary"]["capability_atom_count"], "manifest_sha256": ledger["manifest_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
