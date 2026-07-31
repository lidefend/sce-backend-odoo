#!/usr/bin/env python3
"""Static fail-closed guard for the signed tenant-payload importer group."""

from __future__ import annotations

import csv
import json
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
IMPORTER = "smart_core.group_smart_core_tenant_payload_importer"
DATA_OPERATOR = "smart_core.group_smart_core_data_operator"
ALLOWED_ACLS = {
    ("smart_core", "model_sc_tenant_payload_import_batch", "1", "1", "1", "0"),
    ("smart_core", "model_sc_tenant_payload_external_identity", "1", "1", "1", "0"),
    ("smart_core", "model_sc_tenant_company_registration", "1", "1", "1", "0"),
    ("smart_core", "base.model_ir_module_module", "1", "0", "0", "0"),
    (
        "smart_construction_core",
        "model_sc_historical_payment_fact",
        "1",
        "0",
        "1",
        "0",
    ),
}


def importer_implied_expression() -> str:
    root = ET.parse(
        ROOT / "addons/smart_core/security/smart_core_security.xml"
    ).getroot()
    for record in root.findall(".//record"):
        if record.get("id") != "group_smart_core_tenant_payload_importer":
            continue
        fields = {
            field.get("name"): field for field in record.findall("field")
        }
        return str(fields["implied_ids"].get("eval") or "")
    raise AssertionError("NARROW_IMPORTER_GROUP_MISSING")


def importer_acls() -> set[tuple[str, str, str, str, str, str]]:
    result = set()
    for module in ("smart_core", "smart_construction_core"):
        path = ROOT / f"addons/{module}/security/ir.model.access.csv"
        with path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                if row["group_id:id"] == IMPORTER:
                    result.add(
                        (
                            module,
                            row["model_id:id"],
                            row["perm_read"],
                            row["perm_write"],
                            row["perm_create"],
                            row["perm_unlink"],
                        )
                    )
    return result


def main() -> int:
    expression = importer_implied_expression()
    if "group_smart_core_data_operator" in expression:
        raise SystemExit("NARROW_IMPORTER_DATA_OPERATOR_DEPENDENCY_PRESENT")
    if expression.replace(" ", "") != "[(5,0,0)]":
        raise SystemExit("NARROW_IMPORTER_IMPLIED_CLOSURE_NOT_EMPTY")
    actual_acls = importer_acls()
    if actual_acls != ALLOWED_ACLS:
        raise SystemExit("NARROW_IMPORTER_ACL_SCOPE_DRIFT")

    models_source = (
        ROOT
        / "addons/smart_core/models/tenant_payload_import_batch.py"
    ).read_text(encoding="utf-8")
    maintenance_source = (
        ROOT / "scripts/release/production_maintenance.sh"
    ).read_text(encoding="utf-8")
    action_source = (
        ROOT / "scripts/tenant_payload/odoo_action.py"
    ).read_text(encoding="utf-8")
    required_markers = (
        "TPV1_SIGNED_IMPORT_CONTEXT_REQUIRED",
        "TPV1_SIGNED_MAINTENANCE_CAPABILITY_REQUIRED",
        "SC_TENANT_PAYLOAD_MAINTENANCE_CAPABILITY",
    )
    combined = models_source + maintenance_source + action_source
    if any(marker not in combined for marker in required_markers):
        raise SystemExit("NARROW_IMPORTER_SIGNED_ENTRY_BOUNDARY_MISSING")

    generic_capability_files = []
    for path in (ROOT / "addons").rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        if IMPORTER in source and any(
            marker in source
            for marker in (
                'INTENT_TYPE = "api.data.',
                'INTENT_TYPE = "execute_button"',
                "class FileUpload",
                "class Chatter",
                "class RiskAction",
                "class MyWork",
            )
        ):
            generic_capability_files.append(str(path.relative_to(ROOT)))
    if generic_capability_files:
        raise SystemExit("NARROW_IMPORTER_GENERAL_MUTATION_CAPABILITY_PRESENT")

    print(
        json.dumps(
            {
                "status": "PASS",
                "data_operator_dependency_removed": True,
                "importer_transitive_implied_closure": [],
                "allowed_acl_count": len(actual_acls),
                "signed_maintenance_boundary": True,
                "general_business_mutation_capabilities": 0,
                "general_file_upload_capability": 0,
                "general_button_execution_capability": 0,
                "general_chatter_activity_write_capability": 0,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
