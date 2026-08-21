#!/usr/bin/env python3
"""Independent fail-closed guard for the product view capability ledger."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import jsonschema

from scripts.contract.complete_worktree_fingerprint import build_fingerprint, validate_fingerprint
from scripts.contract.product_view_capability_ledger_common import (
    STATIC_FORM_MODIFIERS, classify_structure, load_yaml, match_normalized_atom, static_boolean_value,
)
from scripts.contract.product_view_structure_common import file_sha256, sha256_json
from scripts.verify.native_view_frontend_capability_map_guard import validate_frontend_map
from scripts.verify.native_view_normalized_capability_map_guard import validate_normalized_map
from scripts.verify.product_view_contract_carriers_guard import validate_carriers


ROOT = Path(__file__).resolve().parents[2]
NORMALIZED_REASON = "CAPABILITY_NORMALIZED_MAPPING_UNPROVEN"
NATIVE_ORIGIN_REASON = "CAPABILITY_NATIVE_OCCURRENCE_ORIGIN_UNPROVEN"
NORMALIZED_MISSING_REASON = "CAPABILITY_NORMALIZED_CARRIER_MISSING"
DYNAMIC_REASON = "CAPABILITY_DYNAMIC_VERDICT_NOT_EVALUATED"


def _pointer_get(value: Any, pointer: str) -> Any:
    if pointer == "":
        return value
    if not pointer.startswith("/"):
        raise ValueError("RFC 6901 pointer must be empty or start with slash")
    current = value
    for raw in pointer[1:].split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict) and token in current:
            current = current[token]
        elif isinstance(current, list) and token.isdigit() and int(token) < len(current):
            current = current[int(token)]
        else:
            raise KeyError(pointer)
    return current


def _load_evidence(path: Path) -> Any:
    if path.suffix in {".yaml", ".yml"}:
        return load_yaml(path)
    return json.loads(path.read_text(encoding="utf-8"))


def validate_evidence_ref(
    ref: dict[str, Any], fingerprint_digest: str, root: Path = ROOT,
    cache: dict[Path, tuple[str, Any]] | None = None,
) -> tuple[list[str], Any]:
    errors: list[str] = []
    relative = Path(str(ref.get("path") or ""))
    path = root / relative
    if (
        not str(relative)
        or relative.is_absolute()
        or ".." in relative.parts
        or not path.is_file()
    ):
        return ["evidence path is not a governed file"], None
    evidence_cache = cache if cache is not None else {}
    if path not in evidence_cache:
        evidence_cache[path] = (file_sha256(path), _load_evidence(path))
    actual_hash, document = evidence_cache[path]
    if ref.get("sha256") != actual_hash:
        errors.append("evidence file hash mismatch")
    if ref.get("candidate_fingerprint") != fingerprint_digest:
        errors.append("evidence candidate fingerprint mismatch")
    selector = str(ref.get("selector") or "")
    if not selector.startswith("json-pointer:"):
        return errors + ["evidence selector is not a JSON pointer"], None
    try:
        selected = _pointer_get(document, selector.removeprefix("json-pointer:"))
    except (ValueError, KeyError, json.JSONDecodeError) as exc:
        errors.append(f"evidence selector is not resolvable: {exc}")
        selected = None
    return errors, selected


def _mapping(atom: dict[str, Any], mappings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    key = atom["capability_key"]
    return [
        item for item in mappings
        if atom["view_type"] in item.get("view_types", [])
        and key not in item.get("excluded_capability_keys", [])
        and (key in item.get("capability_keys", []) or any(key.startswith(prefix) for prefix in item.get("capability_prefixes", [])))
    ]


def _frontend_mapping(atom: dict[str, Any], mappings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item for item in mappings if atom["view_type"] in item.get("view_types", []) and atom["capability_key"] in item.get("capability_keys", [])]


def _fingerprint_subset(value: dict[str, Any]) -> dict[str, Any]:
    return {key: value.get(key) for key in ("algorithm", "git_head", "baseline_sha", "scope_manifest_sha256", "digest")}


def _expected_authority(
    structure: dict[str, Any], carrier: dict[str, Any], fingerprint: dict[str, Any], paths: dict[str, Path], root: Path,
) -> dict[str, Any]:
    source = structure["authority"]
    hashes = {name: file_sha256(root / path) for name, path in paths.items()}
    return {
        "branch": source["branch"], "candidate_fingerprint": _fingerprint_subset(fingerprint),
        "fingerprint_evidence_path": str(paths["fingerprint"]), "fingerprint_evidence_sha256": hashes["fingerprint"],
        "database_policy_path": source["database_policy_path"], "database_policy_sha256": source["database_policy_sha256"],
        "formal_menu_policy_path": source["formal_menu_policy_path"], "formal_menu_policy_sha256": source["formal_menu_policy_sha256"],
        "reason_registry_path": str(paths["reasons"]), "reason_registry_sha256": hashes["reasons"],
        "taxonomy_path": str(paths["taxonomy"]), "taxonomy_sha256": hashes["taxonomy"],
        "normalized_map_path": str(paths["normalized_map"]), "normalized_map_sha256": hashes["normalized_map"],
        "frontend_map_path": str(paths["frontend_map"]), "frontend_map_sha256": hashes["frontend_map"],
        "view_structure_evidence_path": str(paths["structure"]), "view_structure_evidence_sha256": hashes["structure"],
        "view_structure_manifest_sha256": structure["manifest_sha256"],
        "carrier_evidence_path": str(paths["carrier"]), "carrier_evidence_sha256": hashes["carrier"],
        "carrier_evidence_manifest_sha256": carrier["manifest_sha256"],
        "runtime_profile": source["runtime_profile"], "compose_project": source["compose_project"],
        "database": source["database"], "database_filter": source["database_filter"], "demo_data": source["demo_data"],
        "module_set": source["module_set"], "module_set_sha256": source["module_set_sha256"],
        "user": source["user"], "company": source["company"], "language": source["language"],
        "group_profile": source["group_profile"], "exporter_version": "product_view_capability_ledger/v1",
    }


def _origin(surface: dict[str, Any]) -> tuple[str, str]:
    if surface.get("source_kind") == "synthetic_default_view":
        return "synthetic_default", ""
    contributors = surface["source_graph"]["contributors"]
    if len(contributors) == 1 and contributors[0].get("applicability") == "applied":
        return "proven", contributors[0]["view_ref"]
    return "unproven", ""


def validate_ledger(
    artifact: dict[str, Any], schema: dict[str, Any], fingerprint: dict[str, Any], current: dict[str, Any],
    structure: dict[str, Any], carrier: dict[str, Any], taxonomy: dict[str, Any], normalized_map: dict[str, Any],
    frontend_map: dict[str, Any], reasons: dict[str, Any], paths: dict[str, Path], root: Path = ROOT,
) -> list[str]:
    errors = [f"schema: {error.message}" for error in jsonschema.Draft202012Validator(schema).iter_errors(artifact)]
    errors.extend(f"fingerprint: {error}" for error in validate_fingerprint(fingerprint))
    if current != fingerprint:
        errors.append("fingerprint differs from current complete worktree")

    carrier_errors = validate_carriers(
        carrier, structure, fingerprint, load_yaml(root / "contracts/schemas/product-view-contract-carriers-v1.yaml"),
        file_sha256(root / paths["structure"]), current,
    )
    normalized_errors, _ = validate_normalized_map(
        structure, carrier, taxonomy, normalized_map, reasons,
        load_yaml(root / "contracts/schemas/native-view-normalized-capability-map-v1.yaml"), carrier_errors,
    )
    frontend_errors, _ = validate_frontend_map(structure, taxonomy, frontend_map, reasons, root)
    errors.extend(f"normalized-map: {item}" for item in normalized_errors)
    errors.extend(f"frontend-map: {item}" for item in frontend_errors)

    try:
        if artifact.get("authority") != _expected_authority(structure, carrier, fingerprint, paths, root):
            errors.append("ledger authority mismatch")
    except (KeyError, TypeError) as exc:
        errors.append(f"ledger authority cannot be recomputed: {exc}")

    classified = classify_structure(structure, taxonomy)
    if classified["unknown"] or classified["ambiguous"]:
        errors.append("native taxonomy is not closed")
    expected_atoms = {item["atom_id"]: item for item in classified["atoms"]}
    carrier_by_ref = {entry["contract_ref"]: entry for entry in carrier.get("entries", [])}
    reason_by_code = {item.get("code"): item for item in reasons.get("entries", []) if isinstance(item, dict)}
    if len(reason_by_code) != len(reasons.get("entries", [])):
        errors.append("reason registry contains duplicate or empty codes")

    seen_atoms: set[str] = set()
    seen_refs: set[str] = set()
    terminal_counts: Counter[str] = Counter()
    evidence_cache: dict[Path, tuple[str, Any]] = {}
    path_hashes = {name: file_sha256(root / path) for name, path in paths.items()}
    for entry in artifact.get("entries", []):
        contract_ref = entry.get("contract_ref")
        if not contract_ref or contract_ref in seen_refs:
            errors.append(f"duplicate or empty contract_ref: {contract_ref}")
        seen_refs.add(contract_ref)
        carrier_entry = carrier_by_ref.get(contract_ref, {})
        structure_surface = next((surface for source_entry in structure.get("entries", []) for surface in source_entry.get("surfaces", []) if surface.get("contract_ref") == contract_ref), None)
        if structure_surface is None:
            errors.append(f"unknown surface: {contract_ref}")
            continue
        expected_surface = {
            "contract_ref": contract_ref, "menu_xmlid": structure_surface["menu_xmlid"],
            "action_xmlid": structure_surface["action_xmlid"], "model": structure_surface["model"],
            "view_type": structure_surface["view_type"], "view_ref": structure_surface["view_ref"],
            "hashes": structure_surface["hashes"], "source_graph": structure_surface["source_graph"],
            "parse_outcome": structure_surface["parse_outcome"],
        }
        if {key: entry.get(key) for key in expected_surface} != expected_surface:
            errors.append(f"surface facts mismatch: {contract_ref}")
        origin_status, origin_ref = _origin(structure_surface)
        expected_carrier_refs = [item.get("source_selector") for item in carrier_entry.get("normalized_carriers", [])]
        for atom in entry.get("atoms", []):
            atom_id = atom.get("atom_id")
            expected = expected_atoms.get(atom_id)
            if expected is None or atom_id in seen_atoms:
                errors.append(f"unknown or duplicate atom: {atom_id}")
                continue
            seen_atoms.add(atom_id)
            if expected["contract_ref"] != contract_ref or atom.get("capability_key") != expected["capability_key"]:
                errors.append(f"atom identity mismatch: {atom_id}")
            native = atom.get("native", {})
            expected_native = {
                "occurrence_index": expected["occurrence_index"], "resolved_view_ref": expected["resolved_view_ref"],
                "origin_view_ref": origin_ref, "origin_status": origin_status, "locator": expected["locator"],
                "native_locator": expected["native_locator"],
                "canonical_value": expected["canonical_value"], "value_hash": expected["value_hash"],
            }
            if native != expected_native:
                errors.append(f"native occurrence mismatch: {atom_id}")
            normalized_matches = _mapping(expected, normalized_map.get("mappings", []))
            frontend_matches = _frontend_mapping(expected, frontend_map.get("mappings", []))
            if len(normalized_matches) != 1:
                errors.append(f"normalized mapping is not unique: {atom_id}")
            if len(frontend_matches) != 1:
                errors.append(f"frontend mapping is not unique: {atom_id}")
            normalized_mapping = normalized_matches[0] if len(normalized_matches) == 1 else {}
            exact_matches = match_normalized_atom(expected, normalized_mapping, carrier_entry)
            if len(exact_matches) > 1:
                errors.append(f"normalized occurrence is ambiguous: {atom_id}")
            exact = exact_matches[0] if len(exact_matches) == 1 else None
            expected_normalized = (
                {"status": "present", "count": 1, "carrier_refs": [exact["raw_selector"]], "value_hash": sha256_json(exact["raw_value"]), "source_authority": "normalized_contract"}
                if exact else
                {"status": "unproven" if normalized_mapping.get("mapping_status") != "proven" else "missing", "count": 0, "carrier_refs": expected_carrier_refs, "value_hash": "", "source_authority": "normalized_contract"}
            )
            expected_semantic = (
                {"status": "present", "count": 1, "carrier_refs": [exact["semantic_selector"]], "value_hash": sha256_json(exact["semantic_value"]), "source_authority": "normalized_contract"}
                if exact else
                {"status": "missing", "count": 0, "carrier_refs": [], "value_hash": "", "source_authority": "none"}
            )
            normalized = atom.get("normalized", {})
            semantic = atom.get("semantic", {})
            if normalized != expected_normalized:
                errors.append(f"normalized stage mismatch: {atom_id}")
            if semantic != expected_semantic:
                errors.append(f"semantic stage mismatch: {atom_id}")
            frontend_mapping = frontend_matches[0] if len(frontend_matches) == 1 else {}
            expected_frontend = {
                "status": frontend_mapping.get("frontend_status"), "canonical_atom_ref": atom_id,
                "projection_atom_ref": "", "consumer_symbol": frontend_mapping.get("consumer_symbol"),
                "renderer_key": frontend_mapping.get("renderer_key"), "interaction_symbol": frontend_mapping.get("interaction_symbol"),
                "value_hash": sha256_json(frontend_mapping),
                "source_authority": "normalized_contract" if frontend_mapping.get("frontend_status") == "present" else "compatibility_projection",
                "source_count": 1,
            }
            if atom.get("frontend") != expected_frontend:
                errors.append(f"frontend stage mismatch: {atom_id}")
            if origin_status == "unproven":
                status, reason_code = "unsupported", NATIVE_ORIGIN_REASON
            elif normalized_mapping.get("mapping_status") != "proven":
                status, reason_code = "unsupported", NORMALIZED_REASON
            elif exact is None:
                status, reason_code = "unsupported", NORMALIZED_MISSING_REASON
            elif (
                origin_status == "proven"
                and expected["capability_key"] in STATIC_FORM_MODIFIERS
                and static_boolean_value(expected["canonical_value"]) is not None
                and frontend_mapping.get("frontend_status") == "present"
            ):
                status, reason_code = "ready", ""
            else:
                status, reason_code = "fallback", DYNAMIC_REASON
            if atom.get("terminal_status") != status or atom.get("reason_code") != reason_code:
                errors.append(f"terminal stage mismatch: {atom_id}")
            if reason_code:
                reason = reason_by_code.get(reason_code)
                if not reason or reason.get("status") != status or reason.get("gate_effect") != "classified_gap" or not reason.get("exit_condition"):
                    errors.append(f"terminal reason semantics mismatch: {atom_id}")
            terminal_counts[status] += 1

            normalized_index = normalized_map.get("mappings", []).index(normalized_matches[0]) if len(normalized_matches) == 1 else -1
            frontend_index = frontend_map.get("mappings", []).index(frontend_mapping) if frontend_mapping else -1
            expected_carrier_evidence = (
                [
                    {"path": str(paths["carrier"]), "sha256": path_hashes["carrier"], "candidate_fingerprint": fingerprint["digest"], "stage": stage, "selector": f"json-pointer:{selector}"}
                    for stage, selector in (("normalized", exact["raw_selector"]), ("semantic", exact["semantic_selector"]))
                ] if exact else [
                    {"path": str(paths["carrier"]), "sha256": path_hashes["carrier"], "candidate_fingerprint": fingerprint["digest"], "stage": "normalized", "selector": f"json-pointer:{item['artifact_selector']}"}
                    for item in carrier_entry.get("normalized_carriers", [])
                ]
            )
            expected_evidence = [
                {"path": str(paths["structure"]), "sha256": path_hashes["structure"], "candidate_fingerprint": fingerprint["digest"], "stage": "native", "selector": f"json-pointer:{expected['source_selector']}"},
                *expected_carrier_evidence,
                {"path": str(paths["normalized_map"]), "sha256": path_hashes["normalized_map"], "candidate_fingerprint": fingerprint["digest"], "stage": "normalized", "selector": f"json-pointer:/mappings/{normalized_index}"},
                {"path": str(paths["frontend_map"]), "sha256": path_hashes["frontend_map"], "candidate_fingerprint": fingerprint["digest"], "stage": "frontend", "selector": f"json-pointer:/mappings/{frontend_index}"},
            ]
            if atom.get("evidence_refs") != expected_evidence:
                errors.append(f"evidence set mismatch: {atom_id}")
            for ref in atom.get("evidence_refs", []):
                ref_errors, selected = validate_evidence_ref(ref, fingerprint.get("digest", ""), root, evidence_cache)
                errors.extend(f"evidence {atom_id}: {item}" for item in ref_errors)
                if ref.get("stage") == "native" and ref.get("path") == str(paths["structure"]):
                    if expected["attribute"]:
                        equivalent = selected == expected["canonical_value"]
                    else:
                        equivalent = isinstance(selected, dict) and {key: selected[key] for key in ("tag", "text") if key in selected} == expected["canonical_value"]
                    if not equivalent:
                        errors.append(f"native evidence value mismatch: {atom_id}")
                if exact and ref.get("path") == str(paths["carrier"]):
                    expected_value = exact["raw_value"] if ref.get("stage") == "normalized" else exact["semantic_value"]
                    if selected != expected_value:
                        errors.append(f"carrier evidence value mismatch: {atom_id}")

    if seen_atoms != set(expected_atoms):
        errors.append("ledger atom set differs from classified native atoms")
    source_summary = structure.get("summary", {})
    expected_summary = {
        "formal_menu_count": source_summary.get("formal_menu_count"), "model_count": source_summary.get("model_count"),
        "resolved_surface_count": source_summary.get("resolved_surface_count"), "native_candidate_count": len(expected_atoms),
        "classified_atom_count": len(expected_atoms), "excluded_native_count": 0, "unclassified_native_count": 0,
        "ambiguous_native_count": 0, "capability_atom_count": len(expected_atoms), "ready_count": terminal_counts["ready"],
        "fallback_count": terminal_counts["fallback"], "unsupported_count": terminal_counts["unsupported"], "silent_loss_count": 0,
        "view_type_counts": source_summary.get("view_type_counts"),
    }
    if artifact.get("summary") != expected_summary:
        errors.append("ledger summary mismatch")
    if sum(terminal_counts.values()) != len(expected_atoms):
        errors.append("terminal entry conservation failed")
    body = dict(artifact)
    manifest = body.pop("manifest_sha256", None)
    if manifest != sha256_json(body):
        errors.append("ledger manifest hash mismatch")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    for name in ("artifact", "structure", "carrier", "fingerprint", "taxonomy", "normalized_map", "frontend_map", "reasons", "schema"):
        parser.add_argument(f"--{name.replace('_', '-')}", required=True)
    args = parser.parse_args()
    paths = {name: Path(getattr(args, name)) for name in ("structure", "carrier", "fingerprint", "taxonomy", "normalized_map", "frontend_map", "reasons")}
    fingerprint = json.loads((ROOT / paths["fingerprint"]).read_text(encoding="utf-8"))
    artifact = json.loads((ROOT / args.artifact).read_text(encoding="utf-8"))
    errors = validate_ledger(
        artifact, load_yaml(ROOT / args.schema), fingerprint, build_fingerprint(fingerprint["baseline_sha"]),
        json.loads((ROOT / paths["structure"]).read_text(encoding="utf-8")), json.loads((ROOT / paths["carrier"]).read_text(encoding="utf-8")),
        load_yaml(ROOT / paths["taxonomy"]), load_yaml(ROOT / paths["normalized_map"]), load_yaml(ROOT / paths["frontend_map"]),
        load_yaml(ROOT / paths["reasons"]), paths,
    )
    reported = errors[:100]
    if len(errors) > len(reported):
        reported.append(f"{len(errors) - len(reported)} additional errors omitted")
    print(json.dumps({"status": "FAIL" if errors else "PASS", "error_count": len(errors), "errors": reported, "summary": artifact.get("summary", {})}, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
