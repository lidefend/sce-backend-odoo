#!/usr/bin/env python3
"""Fail-closed coverage guard for the native-view frontend capability map."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.contract.product_view_capability_ledger_common import classify_structure, load_yaml


ROOT = Path(__file__).resolve().parents[2]


def _matches(atom: dict[str, Any], mapping: dict[str, Any]) -> bool:
    return atom["capability_key"] in mapping.get("capability_keys", []) and atom["view_type"] in mapping.get("view_types", [])


def validate_frontend_map(
    structure: dict[str, Any],
    taxonomy: dict[str, Any],
    frontend_map: dict[str, Any],
    reason_registry: dict[str, Any],
    root: Path = ROOT,
) -> tuple[list[str], dict[str, int]]:
    errors: list[str] = []
    if frontend_map.get("schema") != "native_view_frontend_capability_map/v1":
        errors.append("frontend map schema mismatch")
    if frontend_map.get("authority") != "p4_evidence_classification_only":
        errors.append("frontend map authority mismatch")
    if frontend_map.get("unknown_capability_policy") != "fail_closed":
        errors.append("frontend map must fail closed")
    if frontend_map.get("static_ready_allowed") is not False:
        errors.append("static ready must be disabled")

    symbols = frontend_map.get("symbols") if isinstance(frontend_map.get("symbols"), dict) else {}
    for symbol_id, symbol in symbols.items():
        path_value = str(symbol.get("path") or "") if isinstance(symbol, dict) else ""
        selector = str(symbol.get("selector") or "") if isinstance(symbol, dict) else ""
        path = (root / path_value).resolve()
        if not path_value or not path.is_relative_to(root.resolve()) or not path.is_file():
            errors.append(f"symbol {symbol_id} path is not a governed file")
            continue
        symbol_name = selector.removeprefix("symbol:") if selector.startswith("symbol:") else ""
        vue_component_match = path.suffix == ".vue" and path.stem == symbol_name
        source_symbol_match = bool(symbol_name) and symbol_name in path.read_text(encoding="utf-8")
        if not vue_component_match and not source_symbol_match:
            errors.append(f"symbol {symbol_id} selector is not resolvable")

    reasons = {}
    for item in reason_registry.get("entries", []):
        code = item.get("code") if isinstance(item, dict) else None
        if not code or code in reasons:
            errors.append(f"reason registry duplicate or empty code: {code}")
        else:
            reasons[code] = item

    mappings = frontend_map.get("mappings") if isinstance(frontend_map.get("mappings"), list) else []
    mapping_ids: set[str] = set()
    for mapping in mappings:
        mapping_id = str(mapping.get("id") or "") if isinstance(mapping, dict) else ""
        if not mapping_id or mapping_id in mapping_ids:
            errors.append(f"mapping duplicate or empty id: {mapping_id}")
            continue
        mapping_ids.add(mapping_id)
        if mapping.get("consumer_symbol") not in symbols:
            errors.append(f"mapping {mapping_id} consumer symbol is not registered")
        reason = reasons.get(mapping.get("reason_code"))
        if reason is None:
            errors.append(f"mapping {mapping_id} reason is not registered")
        elif reason.get("status") != mapping.get("terminal_status"):
            errors.append(f"mapping {mapping_id} terminal status disagrees with reason")
        if mapping.get("terminal_status") == "ready":
            errors.append(f"mapping {mapping_id} illegally declares static ready")

    classified = classify_structure(structure, taxonomy)
    if classified["unknown"]:
        errors.append(f"taxonomy has {len(classified['unknown'])} unclassified candidates")
    if classified["ambiguous"]:
        errors.append(f"taxonomy has {len(classified['ambiguous'])} ambiguous candidates")
    missing = 0
    ambiguous = 0
    for atom in classified["atoms"]:
        match_count = sum(1 for mapping in mappings if _matches(atom, mapping))
        if match_count == 0:
            missing += 1
        elif match_count != 1:
            ambiguous += 1
    if missing:
        errors.append(f"frontend map has {missing} unmapped atoms")
    if ambiguous:
        errors.append(f"frontend map has {ambiguous} ambiguously mapped atoms")
    summary = {
        "classified_atom_count": len(classified["atoms"]),
        "unmapped_atom_count": missing,
        "ambiguous_atom_count": ambiguous,
        "mapping_count": len(mappings),
    }
    return errors, summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--structure", default="contracts/generated/product_view_structure_contract.json")
    parser.add_argument("--taxonomy", default="contracts/product/native-view-capability-taxonomy-v1.yaml")
    parser.add_argument("--frontend-map", default="contracts/product/native-view-frontend-capability-map-v1.yaml")
    parser.add_argument("--reasons", default="contracts/product/native-view-capability-reason-codes-v1.yaml")
    args = parser.parse_args()
    structure = json.loads((ROOT / args.structure).read_text(encoding="utf-8"))
    errors, summary = validate_frontend_map(
        structure,
        load_yaml(ROOT / args.taxonomy),
        load_yaml(ROOT / args.frontend_map),
        load_yaml(ROOT / args.reasons),
    )
    print(json.dumps({"status": "FAIL" if errors else "PASS", "summary": summary, "errors": errors}, ensure_ascii=True, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
