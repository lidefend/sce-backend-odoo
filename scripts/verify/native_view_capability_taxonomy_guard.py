#!/usr/bin/env python3
"""Fail-closed native node and attribute taxonomy coverage guard."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.contract.product_view_capability_ledger_common import classify_structure, load_yaml  # noqa: E402


def validate_taxonomy(structure: dict, taxonomy: dict) -> tuple[list[str], dict]:
    errors = []
    if taxonomy.get("schema") != "native_view_capability_taxonomy/v1":
        errors.append("taxonomy schema mismatch")
    for key in ("node_rules", "attribute_rules"):
        rules = taxonomy.get(key) if isinstance(taxonomy.get(key), list) else []
        ids = [str(rule.get("id") or "") for rule in rules if isinstance(rule, dict)]
        if not rules or not all(ids) or len(ids) != len(set(ids)):
            errors.append(f"{key} must have unique non-empty ids")
    classified = classify_structure(structure, taxonomy)
    if classified["unknown"]:
        errors.append(f"unclassified native candidates: {len(classified['unknown'])}")
    if classified["ambiguous"]:
        errors.append(f"ambiguous native candidates: {len(classified['ambiguous'])}")
    atoms = classified["atoms"]
    surface_refs = {atom["contract_ref"] for atom in atoms}
    expected_refs = {surface["contract_ref"] for entry in structure.get("entries") or [] for surface in entry.get("surfaces") or []}
    if surface_refs != expected_refs:
        errors.append("classified surface coverage differs from structure authority")
    summary = {
        "surface_count": len(surface_refs), "classified_atom_count": len(atoms),
        "unclassified_native_count": len(classified["unknown"]),
        "ambiguous_native_count": len(classified["ambiguous"]),
    }
    return errors, {"summary": summary, "unknown": classified["unknown"][:50], "ambiguous": classified["ambiguous"][:50]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--structure", default="contracts/generated/product_view_structure_contract.json")
    parser.add_argument("--taxonomy", default="contracts/product/native-view-capability-taxonomy-v1.yaml")
    parser.add_argument("--report", default="artifacts/backend/native_view_capability_taxonomy_guard.json")
    args = parser.parse_args()
    structure = json.loads((ROOT / args.structure).read_text(encoding="utf-8"))
    taxonomy = load_yaml(ROOT / args.taxonomy)
    errors, report = validate_taxonomy(structure, taxonomy)
    report = {"ok": not errors, "errors": errors, **report}
    path = ROOT / args.report
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], sort_keys=True))
    if errors:
        print("[native_view_capability_taxonomy_guard] FAIL")
        for error in errors:
            print(f" - {error}")
        for row in report["unknown"] + report["ambiguous"]:
            print(f" - {row}")
        return 1
    print("[native_view_capability_taxonomy_guard] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
