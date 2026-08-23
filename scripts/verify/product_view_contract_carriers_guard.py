#!/usr/bin/env python3
"""Fail-closed host guard for product-view contract carrier evidence."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from scripts.contract.complete_worktree_fingerprint import build_fingerprint, validate_fingerprint
from scripts.contract.product_view_contract_carriers_common import (
    expected_final_contract_selectors,
    expected_normalized_selectors,
    file_sha256,
    final_contract_value_errors,
    normalized_value_errors,
    pointer_get,
    sha256_json,
    stable_selector_payload,
)


ROOT = Path(__file__).resolve().parents[2]


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected object: {path}")
    return value


def _surfaces(structure: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [surface for entry in structure.get("entries", []) for surface in entry.get("surfaces", [])]
    return sorted(rows, key=lambda item: item["contract_ref"])


def validate_carriers(
    artifact: dict[str, Any],
    structure: dict[str, Any],
    fingerprint: dict[str, Any],
    schema: dict[str, Any],
    structure_sha256: str,
    current_fingerprint: dict[str, Any] | None = None,
) -> list[str]:
    errors = [f"schema: {error.message}" for error in Draft202012Validator(schema).iter_errors(artifact)]
    errors.extend(f"fingerprint: {error}" for error in validate_fingerprint(fingerprint))
    expected_fp = {key: fingerprint.get(key) for key in ("algorithm", "git_head", "baseline_sha", "scope_manifest_sha256", "digest")}
    current = current_fingerprint or build_fingerprint(str(fingerprint.get("baseline_sha") or ""))
    if current != fingerprint:
        errors.append("candidate fingerprint is stale for the current complete worktree")
    if artifact.get("authority", {}).get("candidate_fingerprint") != expected_fp:
        errors.append("authority candidate fingerprint mismatch")
    structure_input = artifact.get("structure_input", {})
    if structure_input.get("candidate_fingerprint") != expected_fp:
        errors.append("structure input candidate fingerprint mismatch")
    if structure.get("authority", {}).get("candidate_fingerprint") != expected_fp:
        errors.append("structure authority candidate fingerprint mismatch")
    if structure_input.get("sha256") != structure_sha256:
        errors.append("structure input file hash mismatch")
    if structure_input.get("manifest_sha256") != structure.get("manifest_sha256"):
        errors.append("structure input manifest mismatch")
    structure_body = dict(structure)
    structure_manifest = structure_body.pop("manifest_sha256", None)
    if structure_manifest != sha256_json(structure_body):
        errors.append("structure manifest hash mismatch")
    structure_summary = structure.get("summary", {})
    structure_authority = structure.get("authority", {})
    if structure_input.get("formal_menu_policy_sha256") != structure_authority.get("formal_menu_policy_sha256"):
        errors.append("structure formal menu policy hash mismatch")
    expected_counts = {
        "expected_formal_menu_count": structure_summary.get("formal_menu_count"),
        "expected_model_count": structure_summary.get("model_count"),
        "expected_surface_count": structure_summary.get("resolved_surface_count"),
    }
    for key, expected in expected_counts.items():
        if structure_input.get(key) != expected:
            errors.append(f"structure input {key} mismatch")
    manifest_value = dict(artifact)
    actual_manifest = manifest_value.pop("manifest_sha256", None)
    if actual_manifest != sha256_json(manifest_value):
        errors.append("carrier manifest hash mismatch")

    authority = artifact.get("authority", {})
    if authority.get("branch") != fingerprint.get("branch"):
        errors.append("authority branch mismatch")
    if authority.get("module_set_sha256") != sha256_json(authority.get("module_set")):
        errors.append("authority module set hash mismatch")
    for key in ("module_set_sha256", "user", "company", "language", "group_profile"):
        if authority.get(key) != structure_authority.get(key):
            errors.append(f"authority {key} differs from structure input")
    runtime_constants = {
        "runtime_profile": "local.clean", "compose_project": "sc-local-clean", "database": "sc_clean", "database_filter": "^sc_clean$", "demo_data": False,
        "handler": "odoo.addons.smart_core.handlers.load_contract.LoadContractHandler", "capture_mode": "final_response_rollback_sandbox", "force_refresh": True,
        "final_handler": "odoo.addons.smart_core.handlers.ui_contract_v2.UiContractV2Handler",
        "external_contract_service_absent": True, "capture_transaction_strategy": "dedicated_cursor_rollback", "exporter_version": "product_view_contract_carriers/v1",
    }
    for key, expected in runtime_constants.items():
        if authority.get(key) != expected:
            errors.append(f"authority runtime field mismatch: {key}")

    surfaces = _surfaces(structure)
    entries = artifact.get("entries") if isinstance(artifact.get("entries"), list) else []
    expected_refs = [row["contract_ref"] for row in surfaces]
    actual_refs = [row.get("contract_ref") for row in entries if isinstance(row, dict)]
    if actual_refs != expected_refs or len(set(actual_refs)) != len(actual_refs):
        errors.append("carrier surface coverage or order mismatch")
    surface_by_ref = {row["contract_ref"]: row for row in surfaces}
    normalized_count = 0
    semantic_count = 0
    complete_count = 0
    final_complete_count = 0
    final_not_applicable_count = 0
    final_carrier_count = 0
    for index, entry in enumerate(entries):
        ref = entry.get("contract_ref")
        surface = surface_by_ref.get(ref)
        if surface is None:
            continue
        for key in ("menu_xmlid", "action_xmlid", "model", "view_type", "view_ref", "source_kind", "hashes"):
            if entry.get(key) != surface.get(key):
                errors.append(f"{ref} structure field mismatch: {key}")
        binding = entry.get("runtime_binding", {})
        if binding.get("selector_sha256") != sha256_json(stable_selector_payload(entry, artifact["authority"])):
            errors.append(f"{ref} stable selector hash mismatch")
        request = entry.get("request", {})
        if request.get("menu_id") != binding.get("menu_id") or request.get("action_id") != binding.get("action_id"):
            errors.append(f"{ref} runtime binding mismatch")
        requested = request.get("context", {}).get("requested_view_id")
        if surface["source_kind"] == "database_view" and requested != binding.get("requested_view_id"):
            errors.append(f"{ref} requested view binding mismatch")
        if surface["source_kind"] == "synthetic_default_view" and (request.get("context") or binding.get("requested_view_id") != 0):
            errors.append(f"{ref} synthetic default fabricated a requested view")
        response = entry.get("response", {})
        if response.get("status") != "success" or response.get("code") != 200 or response.get("source_authority") != "load_contract_final_response" or response.get("degraded") is not False:
            errors.append(f"{ref} response authority mismatch")
        if any(str(item).startswith("view_contract_fallback:") for item in response.get("warnings", [])):
            errors.append(f"{ref} fallback warning is forbidden")
        actual_source_selectors = tuple(carrier.get("source_selector") for carrier in entry.get("normalized_carriers", []))
        try:
            expected_source_selectors = expected_normalized_selectors(entry.get("view_type"))
        except ValueError as exc:
            errors.append(f"{ref} {exc}")
            expected_source_selectors = ()
        if actual_source_selectors != expected_source_selectors:
            errors.append(f"{ref} normalized source selector set mismatch")
        for carrier_index, carrier in enumerate(entry.get("normalized_carriers", [])):
            normalized_count += 1
            expected_pointer = f"/entries/{index}/normalized_carriers/{carrier_index}/value"
            if carrier.get("artifact_selector") != expected_pointer:
                errors.append(f"{ref} normalized artifact selector mismatch")
            try:
                selected = pointer_get(artifact, expected_pointer)
            except (KeyError, IndexError, ValueError) as exc:
                errors.append(f"{ref} normalized selector failed: {exc}")
                continue
            if selected != carrier.get("value") or carrier.get("value_hash") != sha256_json(selected):
                errors.append(f"{ref} normalized carrier hash mismatch")
            for error in normalized_value_errors(entry["view_type"], entry["model"], carrier.get("source_selector"), selected):
                errors.append(f"{ref} {error}")
        for carrier_index, carrier in enumerate(entry.get("semantic_carriers", [])):
            semantic_count += 1
            expected_pointer = f"/entries/{index}/semantic_carriers/{carrier_index}/value"
            if carrier.get("artifact_selector") != expected_pointer:
                errors.append(f"{ref} semantic artifact selector mismatch")
            value = carrier.get("value")
            try:
                selected = pointer_get(artifact, expected_pointer)
            except (KeyError, IndexError, ValueError) as exc:
                errors.append(f"{ref} semantic selector failed: {exc}")
                continue
            if selected != value:
                errors.append(f"{ref} semantic selector value mismatch")
            if not isinstance(value, dict):
                errors.append(f"{ref} semantic carrier must be an object")
                continue
            if value.get("version") != "v1" or value.get("source") != "load_contract":
                errors.append(f"{ref} semantic producer mismatch")
            if carrier.get("value_hash") != sha256_json(value):
                errors.append(f"{ref} semantic carrier hash mismatch")
        outcome = entry.get("capture_outcome", {})
        if outcome.get("status") == "complete":
            complete_count += 1
            if len(entry.get("semantic_carriers", [])) != 1 or outcome.get("reason_code") != "":
                errors.append(f"{ref} complete outcome mismatch")
        elif outcome.get("status") == "normalized_only":
            if entry.get("semantic_carriers") or outcome.get("reason_code") != "CAPABILITY_SEMANTIC_CARRIER_MISSING":
                errors.append(f"{ref} normalized-only outcome mismatch")
        final_capture = entry.get("final_contract_capture", {})
        final_carriers = final_capture.get("carriers") if isinstance(final_capture.get("carriers"), list) else []
        actual_final_selectors = tuple(row.get("source_selector") for row in final_carriers if isinstance(row, dict))
        expected_final_selectors = expected_final_contract_selectors(entry.get("view_type"))
        if actual_final_selectors != expected_final_selectors:
            errors.append(f"{ref} final contract selector set mismatch")
        if entry.get("view_type") == "form":
            final_complete_count += 1
            if final_capture.get("status") != "complete" or final_capture.get("reason_code") != "":
                errors.append(f"{ref} final contract completion mismatch")
            final_request = final_capture.get("request", {})
            expected_request = {
                "menu_id": binding.get("menu_id"), "action_id": binding.get("action_id"),
                "model": entry.get("model"), "view_type": "form", "view_id": binding.get("requested_view_id"),
                "source_type": "ui.contract", "client_type": "web_pc", "delivery_profile": "full", "force_refresh": True,
            }
            if final_request != expected_request:
                errors.append(f"{ref} final contract request mismatch")
            final_response = final_capture.get("response", {})
            expected_response = {
                "ok": True, "intent": "ui.contract.v2", "client_type": "web_pc", "delivery_profile": "full",
                "model": entry.get("model"), "view_type": "form",
            }
            for key, expected in expected_response.items():
                if final_response.get(key) != expected:
                    errors.append(f"{ref} final contract response {key} mismatch")
            if not str(final_response.get("contract_version") or ""):
                errors.append(f"{ref} final contract response version missing")
        else:
            final_not_applicable_count += 1
            if final_capture != {"status": "not_applicable", "reason_code": "FINAL_CONTRACT_FORM_ONLY", "request": {}, "response": {}, "carriers": []}:
                errors.append(f"{ref} non-form final contract capture mismatch")
        for carrier_index, carrier in enumerate(final_carriers):
            final_carrier_count += 1
            expected_pointer = f"/entries/{index}/final_contract_capture/carriers/{carrier_index}/value"
            if carrier.get("artifact_selector") != expected_pointer or carrier.get("source_authority") != "ui_contract_v2_final_response":
                errors.append(f"{ref} final contract carrier authority mismatch")
            try:
                selected = pointer_get(artifact, expected_pointer)
            except (KeyError, IndexError, ValueError) as exc:
                errors.append(f"{ref} final contract selector failed: {exc}")
                continue
            if selected != carrier.get("value") or carrier.get("value_hash") != sha256_json(selected):
                errors.append(f"{ref} final contract carrier hash mismatch")
            for error in final_contract_value_errors(carrier.get("source_selector"), selected):
                errors.append(f"{ref} {error}")
    summary = artifact.get("summary", {})
    expected_summary = {
        "formal_menu_count": structure.get("summary", {}).get("formal_menu_count"),
        "model_count": structure.get("summary", {}).get("model_count"),
        "surface_count": len(entries),
        "complete_count": complete_count,
        "normalized_only_count": len(entries) - complete_count,
        "error_count": 0,
        "normalized_carrier_count": normalized_count,
        "semantic_carrier_count": semantic_count,
        "final_contract_complete_count": final_complete_count,
        "final_contract_not_applicable_count": final_not_applicable_count,
        "final_contract_carrier_count": final_carrier_count,
        "view_type_counts": dict(sorted(Counter(row.get("view_type") for row in entries).items())),
    }
    if summary != expected_summary:
        errors.append("carrier summary mismatch")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", default="artifacts/contract/product_view_contract_carriers_candidate.json")
    parser.add_argument("--structure", default="artifacts/contract/product_view_structure_contract.json")
    parser.add_argument("--fingerprint", default="artifacts/contract/product_view_candidate_fingerprint.json")
    parser.add_argument("--schema", default="contracts/schemas/product-view-contract-carriers-v1.yaml")
    args = parser.parse_args()
    artifact_path = ROOT / args.artifact
    structure_path = ROOT / args.structure
    try:
        artifact = _load_json(artifact_path)
        structure = _load_json(structure_path)
        fingerprint = _load_json(ROOT / args.fingerprint)
        schema = yaml.safe_load((ROOT / args.schema).read_text(encoding="utf-8"))
        current = build_fingerprint(fingerprint["baseline_sha"])
        errors = validate_carriers(artifact, structure, fingerprint, schema, file_sha256(structure_path), current)
    except Exception as exc:
        errors = [str(exc)]
    print(json.dumps({"status": "FAIL" if errors else "PASS", "errors": errors}, ensure_ascii=True, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
