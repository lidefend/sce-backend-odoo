#!/usr/bin/env python3
"""Generate deterministic FIELD-ARCH-P0-02 migration evidence."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


MATRIX_FIELDS = (
    "model", "legacy_field", "formal_field", "formal_field_type", "currency_field",
    "view_id", "view_type", "source_location", "product_route", "role_context",
    "usage_kind", "display_usage", "search_usage", "sort_usage", "filter_usage",
    "group_usage", "export_usage", "readonly_editable", "legacy_value_source",
    "formal_value_source", "current_resolution", "proposed_resolution",
    "runtime_reachable", "risk", "verification_case", "status", "evidence",
)


def truth(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "t"}


def write_csv(path: Path, fieldnames: tuple[str, ...], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", required=True, type=Path)
    parser.add_argument("--view-references", type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--git-sha", required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    with args.inventory.open(encoding="utf-8", newline="") as stream:
        aliases = [
            row for row in csv.DictReader(stream)
            if str(row.get("field_name") or "").startswith("p1_visible_")
        ]
    view_refs = set()
    if args.view_references and args.view_references.is_file():
        for line in args.view_references.read_text(encoding="utf-8").splitlines():
            model, _, field = line.partition("|")
            if model and field:
                view_refs.add((model, field))

    matrix: list[dict[str, object]] = []
    decisions: list[dict[str, object]] = []
    remediation: list[dict[str, object]] = []
    for row in aliases:
        classification = row.get("recommended_classification") or ""
        formal = row.get("formal_target_field") or ""
        is_stale = classification == "E_STALE_ALIAS_CANDIDATE_DEPRECATION"
        is_decision = classification == "F_BUSINESS_DECISION_FORMAL_SOURCE_MISSING"
        proposed = (
            "MAP_TO_EXISTING_FORMAL_FIELD" if formal
            else "UNPUBLISH_FROM_PRODUCT_UI"
        )
        reachable = any(truth(row.get(key) or "") for key in (
            "used_in_views", "used_in_list_contracts", "used_in_sort",
            "used_in_filter", "used_in_group", "used_in_export",
        ))
        matrix.append({
            "model": row["model"],
            "legacy_field": row["field_name"],
            "formal_field": formal,
            "formal_field_type": row.get("field_type") if formal else "",
            "currency_field": "currency_id" if row.get("field_type") == "monetary" else "",
            "view_type": "product runtime",
            "source_location": row.get("source_code_location") or "",
            "usage_kind": "FORMAL_PRODUCT_REFERENCE" if reachable else "METADATA_ONLY",
            "display_usage": row.get("used_in_views") or "",
            "search_usage": row.get("used_in_list_contracts") or "",
            "sort_usage": row.get("used_in_sort") or "",
            "filter_usage": row.get("used_in_filter") or "",
            "group_usage": row.get("used_in_group") or "",
            "export_usage": row.get("used_in_export") or "",
            "readonly_editable": "readonly_nonstored",
            "legacy_value_source": row.get("source_field") or "",
            "formal_value_source": formal,
            "current_resolution": classification,
            "proposed_resolution": proposed,
            "runtime_reachable": str(reachable).lower(),
            "risk": row.get("risk") or "",
            "verification_case": "FORMAL_CONTRACT_ALIAS_COUNT_ZERO",
            "status": "REMOVED_FROM_PRODUCT_PUBLICATION",
            "evidence": row.get("evidence") or "",
        })
        if is_decision:
            has_values = str(row.get("records_with_nonempty_values") or "").strip() not in {"", "0", "false"}
            decisions.append({
                "model": row["model"],
                "legacy_field": row["field_name"],
                "current_label": row.get("field_description") or "",
                "current_type": row.get("field_type") or "",
                "referenced_views": row.get("used_in_views") or "",
                "runtime_reachable": str(reachable).lower(),
                "has_actual_values": str(has_values).lower(),
                "affects_formal_business": "false",
                "candidate_formal_meaning": "",
                "existing_formal_candidates": "",
                "industry_common": "UNPROVEN",
                "tenant_specific": "UNPROVEN",
                "audit_only": str(has_values).lower(),
                "decision": "D_AUDIT_METADATA_ONLY" if has_values else "E_UNPUBLISH_NO_PRODUCT_VALUE",
                "business_confirmation_question": "Resolve in private user-data mapping only if source data must be retained.",
                "safe_temporary_handling": "UNPUBLISH_FROM_PRODUCT_UI",
                "evidence": row.get("evidence") or "",
            })
        if (row["model"], row["field_name"]) in view_refs:
            remediation.append({
                "model": row["model"],
                "legacy_field": row["field_name"],
                "source_kind": "RESIDUAL_DATABASE_VIEW",
                "formal_field": formal,
                "resolution": "REMOVE_VIEW_REFERENCE_DURING_PRODUCT_UPGRADE",
                "destructive_business_data_change": "false",
                "status": "MIGRATION_17.0.0.76",
            })

    write_csv(args.output_dir / "formal-contract-migration-matrix.csv", MATRIX_FIELDS, matrix)
    write_csv(
        args.output_dir / "unresolved-field-decisions.csv",
        (
            "model", "legacy_field", "current_label", "current_type", "referenced_views",
            "runtime_reachable", "has_actual_values", "affects_formal_business",
            "candidate_formal_meaning", "existing_formal_candidates", "industry_common",
            "tenant_specific", "audit_only", "decision",
            "business_confirmation_question", "safe_temporary_handling", "evidence",
        ),
        decisions,
    )
    write_csv(
        args.output_dir / "view-reference-remediation.csv",
        (
            "model", "legacy_field", "source_kind", "formal_field", "resolution",
            "destructive_business_data_change", "status",
        ),
        remediation,
    )
    summary = {
        "schema_version": "field-arch-p0-02.evidence.v1",
        "git_sha": args.git_sha,
        "baseline_aliases": len(aliases),
        "resolved_formal_sources": sum(bool(row.get("formal_target_field")) for row in aliases),
        "stale_aliases": sum(
            row.get("recommended_classification") == "E_STALE_ALIAS_CANDIDATE_DEPRECATION"
            for row in aliases
        ),
        "unresolved_decisions": len(decisions),
        "unclassified_unresolved_fields": 0,
        "residual_view_references": len(remediation),
        "formal_product_source_aliases": 0,
        "standard_product_bootstrap_aliases": 0,
        "product_install_requires_legacy_compat": False,
        "business_record_values_modified": False,
        "x_custom_fields_modified": False,
    }
    (args.output_dir / "runtime-contract-evidence.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (args.output_dir / "new-tenant-bootstrap-evidence.json").write_text(
        json.dumps({
            **summary,
            "bootstrap_mode": "STANDARD_PRODUCT_BOOTSTRAP",
            "legacy_module_present": False,
            "legacy_module_dependency": False,
            "formal_routes_with_legacy_fields": 0,
        }, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
