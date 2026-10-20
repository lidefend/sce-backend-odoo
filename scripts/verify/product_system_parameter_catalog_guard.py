#!/usr/bin/env python3
"""Validate the controlled product system parameter catalog declaration.

The catalog is the single machine-readable fact for which product parameters a
company may control, with full metadata and an impact preview. This guard checks
structure and boundaries only: no raw ir.config_parameter, no credential or
deployment identity, change-set/impact/audit/rollback required.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = ROOT / "config/product_system_parameter_catalog_v1.json"
MODULE_MANIFEST = ROOT / "addons/smart_construction_core/data/product_system_parameter_catalog_v1.json"
SCHEMA_VERSION = "product_system_parameter_catalog.v1"

REQUIRED_CATEGORIES = {
    "business_rules",
    "finance_accounting",
    "notification_collaboration",
    "data_attachment",
    "integration",
    "feature_switches",
}
ALLOWED_STATUSES = {"available", "planned"}
ALLOWED_TYPES = {"selection", "boolean", "number"}
REQUIRED_GUARDRAILS = {
    "no_raw_ir_config_parameter_in_user_entry",
    "change_set_required_for_mutation",
    "impact_preview_required",
    "audit_and_rollback_required",
}
SECRET_TERMS = (
    "password",
    "secret",
    "token",
    "api_key",
    "private_key",
    "db_host",
    "database_url",
    "dsn",
)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _iter_strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from _iter_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_strings(item)


def validate(manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if manifest.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version must be %s" % SCHEMA_VERSION)
    if manifest.get("status") != "locked":
        errors.append("status must be locked")

    categories = {
        _text(row.get("key"))
        for row in manifest.get("categories", [])
        if isinstance(row, dict)
    }
    missing = sorted(REQUIRED_CATEGORIES - categories)
    if missing:
        errors.append("missing categories: %s" % ", ".join(missing))
    for row in manifest.get("categories", []):
        if isinstance(row, dict) and not _text(row.get("label")):
            errors.append("category %s missing label" % (_text(row.get("key")) or "<empty>"))

    parameters = manifest.get("parameters")
    if not isinstance(parameters, list) or not parameters:
        errors.append("parameters must be a non-empty list")
        parameters = []
    seen: set[str] = set()
    available_count = 0
    for row in parameters:
        if not isinstance(row, dict):
            errors.append("parameter row must be an object")
            continue
        key = _text(row.get("key"))
        if not key:
            errors.append("parameter row missing key")
            continue
        if key in seen:
            errors.append("duplicate parameter key: %s" % key)
        seen.add(key)
        for field in ("label", "description", "type", "scope", "maintainer_role", "status", "authority"):
            if not _text(row.get(field)):
                errors.append("parameter %s missing %s" % (key, field))
        category = _text(row.get("category"))
        if category not in REQUIRED_CATEGORIES:
            errors.append("parameter %s has unknown category %r" % (key, category))
        status = _text(row.get("status"))
        if status not in ALLOWED_STATUSES:
            errors.append("parameter %s has invalid status" % key)
        if status == "available":
            available_count += 1
        kind = _text(row.get("type"))
        if kind not in ALLOWED_TYPES:
            errors.append("parameter %s has invalid type" % key)
            continue
        if "ir.config_parameter" in _text(row.get("authority")).lower():
            errors.append("parameter %s must not expose raw ir.config_parameter" % key)
        if kind == "selection":
            allowed = list(row.get("allowed_values") or [])
            if not allowed:
                errors.append("parameter %s selection missing allowed_values" % key)
            if row.get("default") not in allowed:
                errors.append("parameter %s default not in allowed_values" % key)
        elif kind == "boolean":
            if not isinstance(row.get("default"), bool):
                errors.append("parameter %s boolean default must be boolean" % key)
        elif kind == "number":
            default = row.get("default")
            if isinstance(default, bool) or not isinstance(default, (int, float)):
                errors.append("parameter %s number default must be numeric" % key)
                continue
            if row.get("min") is not None and default < row.get("min"):
                errors.append("parameter %s default below min" % key)
            if row.get("max") is not None and default > row.get("max"):
                errors.append("parameter %s default above max" % key)
        impact = row.get("impact") if isinstance(row.get("impact"), dict) else {}
        if not impact.get("surfaces") or not _text(impact.get("summary")):
            errors.append("parameter %s missing impact surfaces/summary" % key)
    if available_count < 1:
        errors.append("at least one parameter must be available")
    if "cost_ledger_source" not in seen:
        errors.append("missing required available parameter cost_ledger_source")

    guardrails = set(_text(item) for item in manifest.get("guardrails", []))
    missing_guardrails = sorted(REQUIRED_GUARDRAILS - guardrails)
    if missing_guardrails:
        errors.append("missing guardrails: %s" % ", ".join(missing_guardrails))

    for value in _iter_strings(manifest):
        lowered = value.lower()
        for term in SECRET_TERMS:
            if term in lowered:
                errors.append("secret-like term %r found in value %r" % (term, value))
    return errors


def validate_runtime_copy(
    config_path: Path = DEFAULT_MANIFEST,
    module_path: Path = MODULE_MANIFEST,
) -> list[str]:
    errors: list[str] = []
    if not module_path.is_file():
        errors.append("runtime module catalog is missing: %s" % module_path)
        return errors
    if module_path.read_bytes() != config_path.read_bytes():
        errors.append("runtime module catalog differs from product catalog")
    return errors


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    path = Path(args[0]) if args else DEFAULT_MANIFEST
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print("[product_system_parameter_catalog_guard] FAIL cannot read %s: %s" % (path, exc))
        return 1
    errors = validate(manifest)
    errors.extend(validate_runtime_copy(path))
    if errors:
        print("[product_system_parameter_catalog_guard] FAIL")
        for error in errors:
            print("- %s" % error)
        return 1
    print(
        "[product_system_parameter_catalog_guard] PASS categories=%s parameters=%s"
        % (
            len(manifest.get("categories", [])),
            len(manifest.get("parameters", [])),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
