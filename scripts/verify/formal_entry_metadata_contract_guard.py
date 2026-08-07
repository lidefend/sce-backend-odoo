#!/usr/bin/env python3
"""Static fail-closed contract for formal entry metadata and orphan UI cleanup."""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path


EXTENSION_MODELS = (
    "project.funding.actual.event.allocation",
    "project.project",
    "sc.historical.payment.fact",
    "sc.tax.certificate.registration",
)
VIEW_CONTRACTS = {
    "addons/smart_construction_core/views/core/project_list_views.xml": ("source_created_by", "source_created_at"),
    "addons/smart_construction_core/views/core/project_views.xml": ("source_created_by", "source_created_at"),
    "addons/smart_construction_core/views/core/funding_actual_event_allocation_views.xml": ("source_created_by", "source_created_at"),
    "addons/smart_construction_core/views/core/historical_payment_fact_views.xml": ("source_created_by", "source_created_at"),
    "addons/smart_construction_core/views/core/tax_certificate_registration_views.xml": ("source_created_by", "source_created_at"),
    "addons/smart_construction_core/views/support/tender_views.xml": ("legacy_source_created_by", "legacy_source_created_at"),
}
ORPHAN_MODELS = (
    "sc.invoice.analysis.summary",
    "sc.invoice.cost.progress.summary",
    "sc.tender.guarantee.summary",
)
PRESERVED_RELATIONS = (
    "sc_invoice_analysis_summary",
    "sc_invoice_cost_progress_summary",
    "sc_tender_guarantee_summary",
    "sc_legacy_invoice_analysis_report_fact",
    "sc_legacy_invoice_cost_progress_report_fact",
    "sc_legacy_tender_guarantee_report_fact",
)


def scan(root: Path) -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []

    def require(path_name: str, token: str, reason: str) -> None:
        path = root / path_name
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        if token not in text:
            failures.append({"path": path_name, "reason": reason, "token": token})

    extension_path = "addons/smart_construction_core/models/support/formal_entry_metadata_extensions.py"
    for model_name in EXTENSION_MODELS:
        require(extension_path, '"%s"' % model_name, "missing_formal_entry_metadata_extension")

    for path_name, field_names in VIEW_CONTRACTS.items():
        for field_name in field_names:
            require(path_name, 'name="%s"' % field_name, "missing_visible_entry_metadata_field")

    audit_path = "scripts/verify/formal_entry_metadata_audit.py"
    require(audit_path, "active_unresolved_model_errors(env", "missing_active_orphan_fail_closed_guard")
    for token in ("def active_unresolved_model_errors", '"active_unresolved_model"', "model_name not in env"):
        require(extension_path, token, "missing_active_orphan_fail_closed_guard")

    migration_path = "addons/smart_construction_core/migrations/17.0.0.82/post-migration.py"
    for token in ORPHAN_MODELS + PRESERVED_RELATIONS + ("SNAPSHOT_KEY", "menus.unlink()", "actions.unlink()", "views.unlink()"):
        require(migration_path, token, "incomplete_orphan_ui_cleanup_migration")
    migration = (root / migration_path).read_text(encoding="utf-8") if (root / migration_path).is_file() else ""
    for forbidden in ("DROP TABLE", "DROP VIEW", "TRUNCATE", "DELETE FROM sc_legacy", "DELETE FROM sc_invoice"):
        if forbidden.lower() in migration.lower():
            failures.append({"path": migration_path, "reason": "business_data_destructive_cleanup", "token": forbidden})

    manifest_path = "addons/smart_construction_core/__manifest__.py"
    manifest_file = root / manifest_path
    try:
        manifest = ast.literal_eval(manifest_file.read_text(encoding="utf-8"))
        version = tuple(int(part) for part in str(manifest.get("version", "")).split("."))
    except (OSError, SyntaxError, ValueError, AttributeError):
        version = ()
    if version < (17, 0, 0, 82):
        failures.append(
            {
                "path": manifest_path,
                "reason": "module_version_not_bumped",
                "token": ">=17.0.0.82",
            }
        )
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    failures = scan(Path(args.root).resolve())
    result = {
        "status": "PASS" if not failures else "FAIL",
        "mode": "formal_entry_metadata_contract_guard",
        "failure_count": len(failures),
        "failures": failures,
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
