#!/usr/bin/env python3
"""Static fail-closed contract for formal entry metadata and unresolved active menus."""

from __future__ import annotations

import argparse
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
