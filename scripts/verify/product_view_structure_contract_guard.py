#!/usr/bin/env python3
"""Fail-closed integrity and drift guard for product-view structure evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.contract.complete_worktree_fingerprint import validate_fingerprint  # noqa: E402
from scripts.contract.product_view_structure_common import (  # noqa: E402
    CANONICAL_VIEW_TYPES, SCHEMA, collect_occurrences, collect_references,
    content_digest, file_sha256, policy_menu_rows, sha256_json,
)


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"cannot load {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def validate_manifest(manifest: dict[str, Any], policy: dict[str, Any], policy_sha256: str, database_policy_sha256: str, fingerprint: dict[str, Any]) -> list[str]:
    errors = list(validate_fingerprint(fingerprint))
    if manifest.get("schema") != SCHEMA:
        errors.append(f"schema must be {SCHEMA}")
    expected_rows = policy_menu_rows(policy)
    expected = {row["menu_xmlid"]: row for row in expected_rows}
    entries = manifest.get("entries") if isinstance(manifest.get("entries"), list) else []
    actual = [str(row.get("menu_xmlid") or "") for row in entries if isinstance(row, dict)]
    if set(actual) != set(expected):
        errors.append("formal menu coverage differs from policy")
    if len(actual) != len(set(actual)):
        errors.append("menu entries must be unique")
    surfaces = []
    refs = set()
    for row in entries:
        if not isinstance(row, dict):
            errors.append("entry must be an object")
            continue
        menu = str(row.get("menu_xmlid") or "")
        if menu in expected and row.get("res_model") != expected[menu]["res_model"]:
            errors.append(f"{menu}: policy model mismatch")
        status = row.get("status")
        row_surfaces = row.get("surfaces") if isinstance(row.get("surfaces"), list) else []
        if status == "resolved_view_action" and not row_surfaces:
            errors.append(f"{menu}: resolved action has zero surfaces")
        if status == "non_view_action" and row_surfaces:
            errors.append(f"{menu}: non-view action has surfaces")
        if status not in {"resolved_view_action", "non_view_action"}:
            errors.append(f"{menu}: invalid status")
        declared = row.get("declared_view_types") or []
        resolved = [surface.get("view_type") for surface in row_surfaces if isinstance(surface, dict)]
        if status == "resolved_view_action" and declared != resolved:
            errors.append(f"{menu}: declared/resolved order differs")
        for surface in row_surfaces:
            if not isinstance(surface, dict):
                errors.append(f"{menu}: surface must be an object")
                continue
            surfaces.append(surface)
            view_type = str(surface.get("view_type") or "")
            ref = str(surface.get("contract_ref") or "")
            if view_type not in CANONICAL_VIEW_TYPES or view_type == "list":
                errors.append(f"{ref}: non-canonical view type")
            if ref != f"{menu}::{view_type}" or ref in refs:
                errors.append(f"{menu}: invalid or duplicate contract_ref {ref!r}")
            refs.add(ref)
            resolved_structure = surface.get("resolved_structure")
            semantic_structure = surface.get("semantic_structure")
            if not isinstance(resolved_structure, dict) or not isinstance(semantic_structure, dict):
                errors.append(f"{ref}: resolved and semantic structures are required")
                continue
            hashes = surface.get("hashes") if isinstance(surface.get("hashes"), dict) else {}
            if hashes.get("resolved_arch_sha256") != sha256_json(resolved_structure):
                errors.append(f"{ref}: resolved arch hash is stale")
            if hashes.get("semantic_structure_sha256") != sha256_json(semantic_structure):
                errors.append(f"{ref}: semantic structure hash is stale")
            view_ref = str(surface.get("view_ref") or "")
            occurrences = collect_occurrences(semantic_structure, view_ref)
            if surface.get("occurrences") != occurrences:
                errors.append(f"{ref}: occurrence inventory is stale")
            if surface.get("references") != collect_references(occurrences):
                errors.append(f"{ref}: occurrence references are stale")
            graph = surface.get("source_graph") if isinstance(surface.get("source_graph"), dict) else {}
            graph_body = {key: graph.get(key) for key in ("root_ref", "contributors", "edges", "application_order")}
            graph_hash = sha256_json(graph_body)
            if graph.get("graph_sha256") != graph_hash or hashes.get("source_graph_sha256") != graph_hash:
                errors.append(f"{ref}: source graph hash is stale")
            contributors = graph.get("contributors") if isinstance(graph.get("contributors"), list) else []
            contributor_refs = [item.get("view_ref") for item in contributors if isinstance(item, dict)]
            if not contributors or graph.get("application_order") != contributor_refs or graph.get("root_ref") not in contributor_refs:
                errors.append(f"{ref}: source graph is empty or order is unproven")
            if surface.get("parse_outcome") != {"primary": "success", "fallback": "inactive"}:
                errors.append(f"{ref}: parse outcome is not primary success")
    summary = manifest.get("summary") if isinstance(manifest.get("summary"), dict) else {}
    expected_summary = {
        "formal_menu_count": len(expected), "resolved_view_action_count": sum(row.get("status") == "resolved_view_action" for row in entries if isinstance(row, dict)),
        "non_view_action_count": sum(row.get("status") == "non_view_action" for row in entries if isinstance(row, dict)), "error_count": 0,
        "resolved_surface_count": len(surfaces), "model_count": len({surface.get("model") for surface in surfaces}),
        "view_type_counts": {kind: sum(surface.get("view_type") == kind for surface in surfaces) for kind in sorted({surface.get("view_type") for surface in surfaces})},
    }
    if summary != expected_summary:
        errors.append("summary does not equal recomputed facts")
    if not surfaces:
        errors.append("resolved surface count must be non-zero")
    authority = manifest.get("authority") if isinstance(manifest.get("authority"), dict) else {}
    expected_identity = {"runtime_profile": "local.clean", "compose_project": "sc-local-clean", "database": "sc_clean", "database_filter": "^sc_clean$", "demo_data": False}
    for key, value in expected_identity.items():
        if authority.get(key) != value:
            errors.append(f"authority.{key} mismatch")
    expected_fp = {key: fingerprint.get(key) for key in ("algorithm", "git_head", "baseline_sha", "scope_manifest_sha256", "digest")}
    if authority.get("candidate_fingerprint") != expected_fp or authority.get("branch") != fingerprint.get("branch"):
        errors.append("authority candidate fingerprint mismatch")
    if authority.get("formal_menu_policy_sha256") != policy_sha256:
        errors.append("formal menu policy hash mismatch")
    if authority.get("database_policy_sha256") != database_policy_sha256:
        errors.append("database policy hash mismatch")
    modules = authority.get("module_set") if isinstance(authority.get("module_set"), list) else []
    if not modules or authority.get("module_set_sha256") != sha256_json(modules):
        errors.append("module set is empty or hash is stale")
    if not authority.get("user") or not authority.get("company") or not authority.get("language") or not authority.get("group_profile"):
        errors.append("runtime identity context is incomplete")
    if manifest.get("manifest_sha256") != content_digest(manifest, "manifest_sha256"):
        errors.append("manifest hash is stale")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="contracts/generated/product_view_structure_contract.json")
    parser.add_argument("--policy", default="scripts/verify/baselines/formal_business_product_menu_policy_v1.json")
    parser.add_argument("--database-policy", default="docs/governance/database_architecture_policy.md")
    parser.add_argument("--fingerprint", default="artifacts/contract/candidate_fingerprint.json")
    parser.add_argument("--candidate", default="")
    parser.add_argument("--report", default="artifacts/backend/product_view_structure_contract_guard.json")
    args = parser.parse_args()
    errors = []
    try:
        policy_path, database_path = ROOT / args.policy, ROOT / args.database_policy
        policy, fingerprint = _load(policy_path), _load(ROOT / args.fingerprint)
        baseline = _load(ROOT / args.manifest)
        errors.extend(validate_manifest(baseline, policy, file_sha256(policy_path), file_sha256(database_path), fingerprint))
        if args.candidate:
            candidate = _load(ROOT / args.candidate)
            errors.extend(f"candidate: {error}" for error in validate_manifest(candidate, policy, file_sha256(policy_path), file_sha256(database_path), fingerprint))
            if baseline != candidate:
                errors.append("candidate differs from tracked structure baseline")
    except (ValueError, OSError) as exc:
        errors.append(str(exc))
    report = {"ok": not errors, "errors": errors, "manifest": args.manifest, "candidate": args.candidate or None}
    report_path = ROOT / args.report
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if errors:
        print("[product_view_structure_contract_guard] FAIL")
        for error in errors:
            print(f" - {error}")
        return 1
    print("[product_view_structure_contract_guard] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
