# -*- coding: utf-8 -*-
"""Pure projection for the controlled product system parameter catalog."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "product_system_parameter_catalog.v1"
PLANNED_STATUS = "planned"


def load_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("product system parameter catalog must be an object")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unexpected product system parameter catalog schema")
    return payload


def _text(value: Any) -> str:
    return str(value or "").strip()


def _parameter_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "key": _text(row.get("key")),
        "category": _text(row.get("category")),
        "label": _text(row.get("label")),
        "description": _text(row.get("description")),
        "type": _text(row.get("type")),
        "default": row.get("default"),
        "allowed_values": list(row.get("allowed_values") or []),
        "min": row.get("min"),
        "max": row.get("max"),
        "scope": _text(row.get("scope")),
        "maintainer_role": _text(row.get("maintainer_role")),
        "status": _text(row.get("status")),
        "available": _text(row.get("status")) != PLANNED_STATUS,
        "authority": _text(row.get("authority")),
        "impact": dict(row.get("impact") or {}),
    }


def build_catalog(manifest: dict[str, Any]) -> dict[str, Any]:
    categories = [
        {
            "key": _text(row.get("key")),
            "label": _text(row.get("label")),
        }
        for row in manifest.get("categories", [])
        if isinstance(row, dict)
    ]
    parameters = [
        _parameter_row(row)
        for row in manifest.get("parameters", [])
        if isinstance(row, dict)
    ]
    return {
        "schema_version": _text(manifest.get("schema_version")),
        "status": _text(manifest.get("status")),
        "objective": _text(manifest.get("objective")),
        "categories": categories,
        "parameters": parameters,
        "guardrails": list(manifest.get("guardrails") or []),
    }


def _value_allowed(row: dict[str, Any], value: Any) -> bool:
    kind = _text(row.get("type"))
    if kind == "selection":
        return value in list(row.get("allowed_values") or [])
    if kind == "boolean":
        return isinstance(value, bool)
    if kind == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False
        low = row.get("min")
        high = row.get("max")
        if low is not None and value < low:
            return False
        if high is not None and value > high:
            return False
        return True
    return False


def impact_preview(
    manifest: dict[str, Any],
    parameter_key: str,
    proposed_value: Any,
) -> dict[str, Any]:
    """Deterministic impact preview for a proposed parameter change."""
    rows = {
        _text(row.get("key")): row
        for row in manifest.get("parameters", [])
        if isinstance(row, dict)
    }
    key = _text(parameter_key)
    row = rows.get(key)
    if row is None:
        return {
            "ok": False,
            "parameter": key,
            "reason": "unknown_parameter",
        }
    if _text(row.get("status")) == PLANNED_STATUS:
        return {
            "ok": False,
            "parameter": key,
            "reason": "not_implemented",
            "status": PLANNED_STATUS,
            "impact": dict(row.get("impact") or {}),
        }
    if not _value_allowed(row, proposed_value):
        return {
            "ok": False,
            "parameter": key,
            "reason": "value_not_allowed",
            "proposed_value": proposed_value,
            "allowed_values": list(row.get("allowed_values") or []),
            "min": row.get("min"),
            "max": row.get("max"),
            "impact": dict(row.get("impact") or {}),
        }
    return {
        "ok": True,
        "parameter": key,
        "proposed_value": proposed_value,
        "status": _text(row.get("status")),
        "impact": dict(row.get("impact") or {}),
        "audit_required": True,
        "rollback_required": True,
        "change_set_required": True,
    }
