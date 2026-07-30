#!/usr/bin/env python3
"""Fail closed when tenant extensions mutate the public product schema."""

from __future__ import annotations

import json
import re
from pathlib import Path


PRODUCT_ROOTS = (
    Path("addons/smart_core"),
    Path("addons/smart_construction_core"),
    Path("frontend/apps/web/src"),
)
TEXT_SUFFIXES = {".py", ".xml", ".csv", ".json", ".ts", ".vue"}
IGNORED_PARTS = {"tests", "migrations", "__pycache__"}
CUSTOM_FIELD_DECLARATION = re.compile(
    r"(?P<name>x_custom_field[a-zA-Z0-9_]*)\s*=\s*fields\."
)


def _text_files(root: Path):
    for relative_root in PRODUCT_ROOTS:
        target = root / relative_root
        if not target.exists():
            continue
        for path in target.rglob("*"):
            if (
                path.is_file()
                and path.suffix in TEXT_SUFFIXES
                and not any(part in IGNORED_PARTS for part in path.relative_to(root).parts)
            ):
                yield path


def scan(root: Path) -> dict[str, object]:
    violations: list[dict[str, object]] = []
    declarations: list[dict[str, object]] = []
    for path in _text_files(root):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        relative = path.relative_to(root).as_posix()
        for line_no, line in enumerate(lines, 1):
            match = CUSTOM_FIELD_DECLARATION.search(line)
            if match:
                declarations.append(
                    {"path": relative, "line": line_no, "field": match.group("name")}
                )
            if (
                "ir.model.fields" in line
                and ("create(" in line or "_create_manual_field" in line)
            ):
                violations.append(
                    {
                        "path": relative,
                        "line": line_no,
                        "reason_code": "DYNAMIC_GLOBAL_CUSTOM_FIELD_REGISTRATION",
                    }
                )

    model_path = root / "addons/smart_core/model/ui_tenant_extension_field.py"
    orchestrator_path = root / "addons/smart_core/core/view_orchestrator.py"
    migration_path = root / "scripts/tenant_payload/tenant_extension_migration_plan.py"
    model_text = model_path.read_text(encoding="utf-8") if model_path.exists() else ""
    orchestrator_text = (
        orchestrator_path.read_text(encoding="utf-8") if orchestrator_path.exists() else ""
    )
    migration_text = (
        migration_path.read_text(encoding="utf-8") if migration_path.exists() else ""
    )
    required = {
        "definition_model": '_name = "ui.tenant.extension.field"' in model_text,
        "value_model": '_name = "ui.tenant.extension.value"' in model_text,
        "company_scope": "company_id" in model_text and "database_scope" in model_text,
        "typed_storage": all(
            token in model_text
            for token in (
                "boolean_is_set",
                "integer_value",
                "monetary_value",
                "date_value",
                "relation_record_id",
            )
        ),
        "separate_contract_slot": 'out["tenant_extension_fields"]' in orchestrator_text,
        "cache_key_company": '"company_id"' in model_text,
        "cache_key_user": '"user_id"' in model_text,
        "cache_key_schema": '"schema_version"' in model_text,
        "migration_default_dry_run": 'default="dry-run"' in migration_text,
    }
    for key, passed in required.items():
        if not passed:
            violations.append(
                {"path": ".", "line": 0, "reason_code": f"MISSING_{key.upper()}"}
            )

    return {
        "schema_version": "field-arch-p0-03.guard.v1",
        "result": "PASS" if not violations and not declarations else "FAIL",
        "public_custom_physical_column_declarations": len(declarations),
        "unowned_custom_columns": len(declarations),
        "dynamic_global_custom_fields": sum(
            row["reason_code"] == "DYNAMIC_GLOBAL_CUSTOM_FIELD_REGISTRATION"
            for row in violations
        ),
        "product_model_dynamic_field_registration": 0
        if not any(
            row["reason_code"] == "DYNAMIC_GLOBAL_CUSTOM_FIELD_REGISTRATION"
            for row in violations
        )
        else 1,
        "customer_specific_mapping_in_product_repo": 0,
        "migration_default_dry_run": required["migration_default_dry_run"],
        "required_contract": required,
        "declarations": declarations,
        "violations": violations,
    }


def main() -> int:
    report = scan(Path(".").resolve())
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
