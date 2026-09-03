#!/usr/bin/env python3
"""Fail-closed coverage guard for native-to-normalized capability mappings."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import jsonschema

from scripts.contract.complete_worktree_fingerprint import build_fingerprint
from scripts.contract.product_view_capability_ledger_common import classify_structure, load_yaml, match_normalized_atom
from scripts.contract.product_view_structure_common import file_sha256, sha256_json
from scripts.verify.product_view_contract_carriers_guard import validate_carriers


ROOT = Path(__file__).resolve().parents[2]


def _matches(atom: dict[str, Any], mapping: dict[str, Any]) -> bool:
    if atom["view_type"] not in mapping.get("view_types", []):
        return False
    key = atom["capability_key"]
    if key in mapping.get("excluded_capability_keys", []):
        return False
    return key in mapping.get("capability_keys", []) or any(
        key.startswith(prefix) for prefix in mapping.get("capability_prefixes", [])
    )


def _pointer_tokens(pointer: str) -> list[str]:
    if pointer == "":
        return []
    if not pointer.startswith("/"):
        raise ValueError("RFC 6901 pointer must be empty or start with /")
    tokens = pointer[1:].split("/")
    if any(re.search(r"~(?![01])", token) for token in tokens):
        raise ValueError("RFC 6901 pointer contains an invalid escape")
    return [token.replace("~1", "/").replace("~0", "~") for token in tokens]


def _pointer_get(value: Any, pointer: str) -> Any:
    current = value
    for token in _pointer_tokens(pointer):
        if isinstance(current, dict) and token in current:
            current = current[token]
        elif isinstance(current, list) and token.isdigit() and int(token) < len(current):
            current = current[int(token)]
        else:
            raise KeyError(pointer)
    return current


def validate_normalized_map(
    structure: dict[str, Any],
    carrier: dict[str, Any],
    taxonomy: dict[str, Any],
    normalized_map: dict[str, Any],
    reason_registry: dict[str, Any],
    schema: dict[str, Any],
    carrier_guard_errors: list[str],
) -> tuple[list[str], dict[str, int]]:
    errors = [f"carrier: {error}" for error in carrier_guard_errors]
    validator = jsonschema.Draft202012Validator(schema)
    for error in sorted(validator.iter_errors(normalized_map), key=lambda item: list(item.path)):
        errors.append(f"schema: {'/'.join(str(part) for part in error.path)}: {error.message}")

    if normalized_map.get("schema") != "native_view_normalized_capability_map/v1":
        errors.append("normalized map schema mismatch")
    if normalized_map.get("authority") != "p0_normalized_evidence_mapping":
        errors.append("normalized map authority mismatch")
    if normalized_map.get("unknown_capability_policy") != "fail_closed":
        errors.append("normalized map must fail closed")

    classified = classify_structure(structure, taxonomy)
    if classified["unknown"]:
        errors.append(f"taxonomy has {len(classified['unknown'])} unclassified candidates")
    if classified["ambiguous"]:
        errors.append(f"taxonomy has {len(classified['ambiguous'])} ambiguous candidates")
    actual_view_types = sorted({atom["view_type"] for atom in classified["atoms"]})
    canonical_view_types = sorted(normalized_map.get("canonical_view_types", []))
    if canonical_view_types != sorted(taxonomy.get("canonical_view_types", [])) or canonical_view_types != actual_view_types:
        errors.append("canonical view types disagree with taxonomy or structure")
    capability_pairs = sorted({
        (atom["view_type"], atom["capability_key"]) for atom in classified["atoms"]
    })
    pair_digest = sha256_json([
        {"view_type": view_type, "capability_key": capability_key}
        for view_type, capability_key in capability_pairs
    ])
    if normalized_map.get("classified_capability_pairs_sha256") != pair_digest:
        errors.append("classified capability pair digest mismatch")

    structure_fingerprint = (structure.get("authority") or {}).get("candidate_fingerprint")
    carrier_authority_fingerprint = (carrier.get("authority") or {}).get("candidate_fingerprint")
    carrier_structure_fingerprint = (carrier.get("structure_input") or {}).get("candidate_fingerprint")
    if not structure_fingerprint or carrier_authority_fingerprint != structure_fingerprint or carrier_structure_fingerprint != structure_fingerprint:
        errors.append("carrier and structure candidate fingerprints differ")
    structure_surfaces: dict[str, dict[str, Any]] = {}
    for entry in structure.get("entries", []):
        for surface in entry.get("surfaces", []):
            contract_ref = str(surface.get("contract_ref") or "")
            if not contract_ref or contract_ref in structure_surfaces:
                errors.append(f"structure duplicate or empty contract_ref: {contract_ref}")
            else:
                structure_surfaces[contract_ref] = surface
    carrier_entries: dict[str, dict[str, Any]] = {}
    for entry in carrier.get("entries", []):
        contract_ref = str(entry.get("contract_ref") or "")
        if not contract_ref or contract_ref in carrier_entries:
            errors.append(f"carrier duplicate or empty contract_ref: {contract_ref}")
        else:
            carrier_entries[contract_ref] = entry
    if set(carrier_entries) != set(structure_surfaces):
        errors.append("carrier and structure contract_ref sets differ")
    for contract_ref in sorted(set(carrier_entries) & set(structure_surfaces)):
        if carrier_entries[contract_ref].get("view_type") != structure_surfaces[contract_ref].get("view_type"):
            errors.append(f"carrier view type mismatch: {contract_ref}")

    reasons: dict[str, dict[str, Any]] = {}
    for item in reason_registry.get("entries", []):
        code = item.get("code") if isinstance(item, dict) else None
        if not code or code in reasons:
            errors.append(f"reason registry duplicate or empty code: {code}")
        else:
            reasons[code] = item

    forbidden = tuple(normalized_map.get("forbidden_source_aliases", []))
    mappings = normalized_map.get("mappings") if isinstance(normalized_map.get("mappings"), list) else []
    mapping_ids: set[str] = set()
    for mapping in mappings:
        mapping_id = str(mapping.get("id") or "") if isinstance(mapping, dict) else ""
        if not mapping_id or mapping_id in mapping_ids:
            errors.append(f"mapping duplicate or empty id: {mapping_id}")
            continue
        mapping_ids.add(mapping_id)
        if not mapping.get("capability_keys") and not mapping.get("capability_prefixes"):
            errors.append(f"mapping {mapping_id} has no capability matcher")
        for selector in mapping.get("source_selectors", []):
            if any(str(selector).startswith(alias) for alias in forbidden):
                errors.append(f"mapping {mapping_id} uses forbidden source alias")
            for view_type in mapping.get("view_types", []):
                resolved = str(selector).replace("{view_type}", view_type)
                allowed = {f"/data/views/{view_type}"}
                if view_type == "search":
                    allowed.add("/data/search")
                if resolved not in allowed:
                    errors.append(f"mapping {mapping_id} source selector is outside its canonical carrier")
        for region in mapping.get("value_regions", []):
            try:
                _pointer_tokens(str(region))
            except ValueError as exc:
                errors.append(f"mapping {mapping_id} value region is invalid: {exc}")
        if mapping_id == "view_root" and mapping.get("value_regions") != [""]:
            errors.append("mapping view_root must use the RFC 6901 document-root pointer")
        for field, expected_status in (
            ("missing_reason_code", "unsupported"),
            ("reduced_reason_code", "fallback"),
            ("unproven_reason_code", "unsupported"),
        ):
            reason = reasons.get(mapping.get(field))
            if reason is None:
                errors.append(f"mapping {mapping_id} {field} is not registered")
            elif reason.get("stage") != "normalized" or reason.get("status") != expected_status or reason.get("gate_effect") != "classified_gap":
                errors.append(f"mapping {mapping_id} {field} has incompatible reason semantics")
        proven_shapes = {
            "form_modifier": ("recursive_native_occurrence", "exactly_one"),
            "form_behavior": ("surface_identity", "exactly_one"),
            "form_action": ("native_action_identity", "exactly_one"),
            "form_field_descriptor": ("native_field_descriptor_identity", "exactly_one"),
        }
        if mapping.get("mapping_status") == "proven" and (
            proven_shapes.get(mapping_id) != (mapping.get("matcher"), mapping.get("cardinality_policy"))
        ):
            errors.append(f"mapping {mapping_id} claims proven without the governed occurrence and value-equivalence matcher")
        if mapping.get("mapping_status") == "mapping_unproven" and mapping.get("unproven_reason_code") != "CAPABILITY_NORMALIZED_MAPPING_UNPROVEN":
            errors.append(f"mapping {mapping_id} lacks the normalized mapping gap reason")

    missing = 0
    ambiguous = 0
    used: set[str] = set()
    mapping_refs: dict[str, set[str]] = {}
    for atom in classified["atoms"]:
        matches = [mapping for mapping in mappings if _matches(atom, mapping)]
        if not matches:
            missing += 1
        elif len(matches) != 1:
            ambiguous += 1
        else:
            mapping_id = str(matches[0].get("id") or "")
            used.add(mapping_id)
            mapping_refs.setdefault(mapping_id, set()).add(atom["contract_ref"])
    if missing:
        errors.append(f"normalized map has {missing} unmapped atoms")
    if ambiguous:
        errors.append(f"normalized map has {ambiguous} ambiguously mapped atoms")
    unused = sorted(mapping_ids - used)
    if unused:
        errors.append(f"normalized map has unused mappings: {unused}")
    mappings_by_id = {str(mapping.get("id") or ""): mapping for mapping in mappings}
    for mapping_id, contract_refs in mapping_refs.items():
        mapping = mappings_by_id[mapping_id]
        for contract_ref in sorted(contract_refs):
            entry = carrier_entries.get(contract_ref)
            if entry is None:
                continue
            view_type = str(entry.get("view_type") or "")
            normalized = entry.get("normalized_carriers") if isinstance(entry.get("normalized_carriers"), list) else []
            for selector_template in mapping.get("source_selectors", []):
                selector = str(selector_template).replace("{view_type}", view_type)
                matched_carriers = [item for item in normalized if item.get("source_selector") == selector]
                if len(matched_carriers) != 1:
                    errors.append(f"mapping {mapping_id} source selector cardinality mismatch: {contract_ref}:{selector}")
                    continue
                for region in mapping.get("value_regions", []):
                    try:
                        _pointer_get(matched_carriers[0].get("value"), str(region))
                    except (KeyError, ValueError):
                        errors.append(f"mapping {mapping_id} value region is not resolvable: {contract_ref}:{region}")
    proven_match_counts = {
        str(mapping.get("id") or ""): 0
        for mapping in mappings if mapping.get("mapping_status") == "proven"
    }
    for atom in classified["atoms"]:
        atom_mappings = [mapping for mapping in mappings if _matches(atom, mapping)]
        if len(atom_mappings) != 1 or atom_mappings[0].get("mapping_status") != "proven":
            continue
        entry = carrier_entries.get(atom["contract_ref"], {})
        matches = match_normalized_atom(atom, atom_mappings[0], entry)
        if len(matches) > 1:
            errors.append(f"proven mapping is ambiguous: {atom['atom_id']}")
        if len(matches) == 1:
            proven_match_counts[str(atom_mappings[0].get("id") or "")] += 1
    for mapping_id, match_count in proven_match_counts.items():
        if match_count == 0:
            errors.append(f"proven mapping has no exact occurrence and value-equivalence matches: {mapping_id}")
    summary = {
        "classified_atom_count": len(classified["atoms"]),
        "unmapped_atom_count": missing,
        "ambiguous_atom_count": ambiguous,
        "mapping_count": len(mappings),
        "proven_mapping_count": sum(1 for mapping in mappings if mapping.get("mapping_status") == "proven"),
        "unproven_mapping_count": sum(1 for mapping in mappings if mapping.get("mapping_status") == "mapping_unproven"),
    }
    return errors, summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--structure", default="contracts/generated/product_view_structure_contract.json")
    parser.add_argument("--carrier", required=True)
    parser.add_argument("--fingerprint", required=True)
    parser.add_argument("--carrier-schema", default="contracts/schemas/product-view-contract-carriers-v1.yaml")
    parser.add_argument("--taxonomy", default="contracts/product/native-view-capability-taxonomy-v1.yaml")
    parser.add_argument("--normalized-map", default="contracts/product/native-view-normalized-capability-map-v1.yaml")
    parser.add_argument("--reasons", default="contracts/product/native-view-capability-reason-codes-v1.yaml")
    parser.add_argument("--schema", default="contracts/schemas/native-view-normalized-capability-map-v1.yaml")
    args = parser.parse_args()
    structure_path = ROOT / args.structure
    structure = json.loads(structure_path.read_text(encoding="utf-8"))
    carrier = json.loads((ROOT / args.carrier).read_text(encoding="utf-8"))
    fingerprint = json.loads((ROOT / args.fingerprint).read_text(encoding="utf-8"))
    carrier_guard_errors = validate_carriers(
        carrier, structure, fingerprint, load_yaml(ROOT / args.carrier_schema),
        file_sha256(structure_path), build_fingerprint(str(fingerprint.get("baseline_sha") or "")),
    )
    errors, summary = validate_normalized_map(
        structure,
        carrier,
        load_yaml(ROOT / args.taxonomy),
        load_yaml(ROOT / args.normalized_map),
        load_yaml(ROOT / args.reasons),
        load_yaml(ROOT / args.schema),
        carrier_guard_errors,
    )
    print(json.dumps({"status": "FAIL" if errors else "PASS", "summary": summary, "errors": errors}, ensure_ascii=True, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
