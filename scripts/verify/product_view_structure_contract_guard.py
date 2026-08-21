#!/usr/bin/env python3
"""Fail-closed validation and drift guard for product view structures."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.contract.product_view_structure_common import SCHEMA, manifest_digest, policy_menu_rows  # noqa: E402


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"cannot load {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def validate_manifest(manifest: dict[str, Any], policy: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if manifest.get("schema") != SCHEMA:
        errors.append(f"schema must be {SCHEMA}")
    expected_menus = {row["menu_xmlid"] for row in policy_menu_rows(policy)}
    entries = manifest.get("entries") if isinstance(manifest.get("entries"), list) else []
    actual_menus = {str(row.get("menu_xmlid") or "") for row in entries if isinstance(row, dict)}
    missing = sorted(expected_menus - actual_menus)
    extra = sorted(actual_menus - expected_menus)
    if missing:
        errors.append(f"missing formal menus: {missing}")
    if extra:
        errors.append(f"unexpected formal menus: {extra}")
    if len(entries) != len(actual_menus):
        errors.append("menu entries must be unique")

    contract_refs: set[str] = set()
    all_surfaces = []
    for row in entries:
        if not isinstance(row, dict):
            errors.append("entry must be an object")
            continue
        menu_xmlid = str(row.get("menu_xmlid") or "")
        status = str(row.get("status") or "")
        if status not in {"resolved_view_action", "non_view_action"}:
            errors.append(f"{menu_xmlid}: invalid or failed status {status!r}")
        surfaces = row.get("surfaces") if isinstance(row.get("surfaces"), list) else []
        if status == "resolved_view_action" and not surfaces:
            errors.append(f"{menu_xmlid}: resolved view action has zero surfaces")
        if status == "non_view_action" and surfaces:
            errors.append(f"{menu_xmlid}: non-view action cannot have surfaces")
        declared = set(row.get("declared_view_types") or [])
        resolved = {str(surface.get("view_type") or "") for surface in surfaces if isinstance(surface, dict)}
        if status == "resolved_view_action" and declared != resolved:
            errors.append(f"{menu_xmlid}: declared/resolved view types differ")
        for surface in surfaces:
            if not isinstance(surface, dict):
                errors.append(f"{menu_xmlid}: surface must be an object")
                continue
            all_surfaces.append(surface)
            ref = str(surface.get("contract_ref") or "")
            if not ref or ref in contract_refs:
                errors.append(f"{menu_xmlid}: duplicate or empty contract_ref {ref!r}")
            contract_refs.add(ref)
            hashes = surface.get("hashes") if isinstance(surface.get("hashes"), dict) else {}
            for key in ("source_graph_sha256", "resolved_arch_sha256", "semantic_structure_sha256"):
                value = str(hashes.get(key) or "")
                if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
                    errors.append(f"{ref}: invalid {key}")
            if not isinstance(surface.get("semantic_structure"), dict):
                errors.append(f"{ref}: semantic_structure is required")

    summary = manifest.get("summary") if isinstance(manifest.get("summary"), dict) else {}
    formal_menu_count = summary.get("formal_menu_count")
    resolved_surface_count = summary.get("resolved_surface_count")
    error_count = summary.get("error_count")
    if type(formal_menu_count) is not int or formal_menu_count != len(expected_menus):
        errors.append("summary.formal_menu_count does not match policy")
    if type(resolved_surface_count) is not int or resolved_surface_count != len(all_surfaces):
        errors.append("summary.resolved_surface_count does not match entries")
    if type(error_count) is not int or error_count != 0:
        errors.append("summary.error_count must be zero")
    if not all_surfaces:
        errors.append("resolved surface count must be non-zero")
    if manifest.get("manifest_sha256") != manifest_digest(entries):
        errors.append("manifest_sha256 is stale")
    authority = manifest.get("authority") if isinstance(manifest.get("authority"), dict) else {}
    if authority.get("database_role") != "clean_install" or authority.get("demo_data") is not False:
        errors.append("authority must bind clean_install with demo_data=false")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="contracts/generated/product_view_structure_contract.json")
    parser.add_argument("--policy", default="scripts/verify/baselines/formal_business_product_menu_policy_v1.json")
    parser.add_argument("--candidate", default="")
    parser.add_argument("--report", default="artifacts/backend/product_view_structure_contract_guard.json")
    args = parser.parse_args()
    errors = []
    try:
        manifest = _load(ROOT / args.manifest)
        policy = _load(ROOT / args.policy)
        errors.extend(validate_manifest(manifest, policy))
        if args.candidate:
            candidate = _load(ROOT / args.candidate)
            errors.extend(f"candidate: {error}" for error in validate_manifest(candidate, policy))
            if manifest != candidate:
                errors.append("candidate differs from tracked product view-structure baseline")
    except ValueError as exc:
        errors.append(str(exc))
    report = {"ok": not errors, "manifest": args.manifest, "candidate": args.candidate or None, "errors": errors}
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
