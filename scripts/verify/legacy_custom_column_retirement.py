#!/usr/bin/env python3
"""Fail-closed retirement qualification for legacy public custom columns.

The tool never connects to a database or drops a column. Database evidence is
supplied as a machine-readable probe produced from an explicitly isolated
database. The default mode is therefore always read-only and dry-run.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path


REQUIRED_ZERO_METRICS = (
    "effective_value_count",
    "database_view_reference_count",
    "odoo_view_reference_count",
    "business_logic_reference_count",
    "external_contract_reference_count",
    "module_recreation_source_count",
)
SAFE_IDENT = re.compile(r"^[a-z][a-z0-9_]*$")
TYPE_DDL = {
    "date": "date",
    "varchar": "character varying",
    "double precision": "double precision",
}


def load_inventory(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    required = {
        "database_table",
        "model",
        "column_name",
        "field_type",
        "sql_type",
        "nullable",
        "default",
        "index",
        "constraint",
        "nonempty_record_count",
    }
    if not rows or required - set(rows[0]):
        raise ValueError("RETIREMENT_INVENTORY_SCHEMA_INVALID")
    identities = set()
    for row in rows:
        identity = (row["database_table"], row["column_name"])
        if identity in identities:
            raise ValueError("RETIREMENT_INVENTORY_DUPLICATE_COLUMN")
        identities.add(identity)
        if not all(SAFE_IDENT.fullmatch(value) for value in identity):
            raise ValueError("RETIREMENT_INVENTORY_IDENTIFIER_INVALID")
        if row["sql_type"] not in TYPE_DDL:
            raise ValueError("RETIREMENT_INVENTORY_SQL_TYPE_UNSUPPORTED")
    return rows


def rollback_ddl(rows: list[dict[str, str]]) -> str:
    statements = [
        "-- Generated from immutable field architecture evidence.",
        "-- Apply only to the matching isolated database after identity checks.",
    ]
    for row in rows:
        nullability = "" if row["nullable"].lower() == "true" else " NOT NULL"
        statements.append(
            f'ALTER TABLE "{row["database_table"]}" '
            f'ADD COLUMN "{row["column_name"]}" {TYPE_DDL[row["sql_type"]]}'
            f"{nullability};"
        )
    return "\n".join(statements) + "\n"


def evaluate(
    inventory: list[dict[str, str]],
    probe: dict[str, object],
) -> list[dict[str, object]]:
    probe_rows = {
        (str(row["database_table"]), str(row["column_name"])): row
        for row in probe.get("columns", [])
        if isinstance(row, dict)
    }
    output = []
    for source in inventory:
        identity = (source["database_table"], source["column_name"])
        observed = probe_rows.get(identity)
        reasons = []
        archived_nonempty = bool(
            observed
            and observed.get("selected_disposition")
            == "ARCHIVE_AS_UNRESOLVED_AUDIT_VALUE"
            and observed.get("unresolved_archive_verified") is True
            and observed.get("value_reconciliation") == "PASS"
            and int(observed.get("ordinary_user_discovery", -1)) == 0
            and int(observed.get("formal_contract_publication", -1)) == 0
        )
        if not observed:
            reasons.append("RUNTIME_PROBE_MISSING")
        else:
            for metric in REQUIRED_ZERO_METRICS:
                if metric == "effective_value_count" and archived_nonempty:
                    continue
                if int(observed.get(metric, -1)) != 0:
                    reasons.append(f"{metric.upper()}_NONZERO_OR_UNKNOWN")
            if observed.get("installation_dependency") is not False:
                reasons.append("INSTALLATION_DEPENDENCY_UNKNOWN_OR_TRUE")
            if observed.get("upgrade_dependency") is not False:
                reasons.append("UPGRADE_DEPENDENCY_UNKNOWN_OR_TRUE")
            if observed.get("rollback_ddl_ready") is not True:
                reasons.append("ROLLBACK_DDL_NOT_READY")
            if observed.get("isolated_drop_rehearsal") != "PASS":
                reasons.append("ISOLATED_DROP_REHEARSAL_NOT_PASS")
            if observed.get("registry_after_drop") != "PASS":
                reasons.append("REGISTRY_AFTER_DROP_NOT_PASS")
            if observed.get("upgrade_after_drop") != "PASS":
                reasons.append("UPGRADE_AFTER_DROP_NOT_PASS")
            if observed.get("rollback_ddl_verification") != "PASS":
                reasons.append("ROLLBACK_DDL_VERIFICATION_NOT_PASS")
        evidence_nonempty = int(source["nonempty_record_count"] or 0)
        if evidence_nonempty and not archived_nonempty:
            reasons.append("NONEMPTY_VALUE_NOT_SAFELY_ARCHIVED")
        if not reasons and evidence_nonempty:
            status = "READY_FOR_CONTROLLED_DROP_AFTER_ARCHIVE"
        elif not reasons:
            status = "READY_FOR_CONTROLLED_DROP"
        else:
            status = "BLOCKED_INCOMPLETE_EVIDENCE"
        if any("REFERENCE_COUNT" in reason for reason in reasons):
            status = "DEFER_REFERENCE_REMEDIATION"
        if "MODULE_RECREATION_SOURCE_COUNT_NONZERO_OR_UNKNOWN" in reasons:
            status = "DEFER_RECREATION_SOURCE"
        output.append(
            {
                "database_table": identity[0],
                "model": source["model"],
                "column_name": identity[1],
                "immutable_nonempty_count": evidence_nonempty,
                "status": status,
                "reason_codes": reasons,
            }
        )
    if len(probe_rows) != len(inventory):
        inventoried = {(row["database_table"], row["column_name"]) for row in inventory}
        if set(probe_rows) - inventoried:
            raise ValueError("RETIREMENT_PROBE_HAS_UNINVENTORIED_COLUMNS")
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--inventory",
        type=Path,
        default=Path("docs/audit/field_arch_p0_03/public-custom-column-inventory.csv"),
    )
    parser.add_argument("--probe", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--rollback-ddl", type=Path)
    parser.add_argument("--mode", choices=("dry-run",), default="dry-run")
    args = parser.parse_args()
    inventory = load_inventory(args.inventory)
    probe = (
        json.loads(args.probe.read_text(encoding="utf-8"))
        if args.probe
        else {"columns": []}
    )
    rows = evaluate(inventory, probe)
    report = {
        "schema_version": "field-arch-p0-03r.retirement.v1",
        "mode": "dry-run",
        "custom_columns_total": len(inventory),
        "ready_columns": sum(row["status"].startswith("READY_FOR_CONTROLLED_DROP") for row in rows),
        "blocked_columns": sum(
            not row["status"].startswith("READY_FOR_CONTROLLED_DROP") for row in rows
        ),
        "columns": rows,
        "destructive_database_changes": 0,
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if args.rollback_ddl:
        args.rollback_ddl.parent.mkdir(parents=True, exist_ok=True)
        args.rollback_ddl.write_text(rollback_ddl(inventory), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if not args.probe or not report["blocked_columns"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
