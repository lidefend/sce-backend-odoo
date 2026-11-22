# -*- coding: utf-8 -*-
"""P0-A page-block-data.v1 production helpers.

Only page-block-data is produced here. Attachment facts and page-block actions
remain owned by P0-B and P0-C and are intentionally absent.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable


PAGE_BLOCK_DATA_VERSION = "1.0.0"
PAGE_BLOCK_DATA_SCHEMA = "page-block-data.v1"
CURRENT_PAGE_ORCHESTRATION_VERSION = "2.1.0"
LEGACY_PAGE_ORCHESTRATION_VERSION = "2.0.0"

SOURCE_KIND = "page_block_data_producer"
SOURCE_AUTHORITIES = ("odoo_model_fields", "page_orchestration", "semantic_registry")


def _text(value: Any) -> str:
    return str(value or "").strip()


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def source_authority_contract() -> dict[str, Any]:
    return {
        "kind": SOURCE_KIND,
        "authorities": list(SOURCE_AUTHORITIES),
        "projectionOnly": True,
        "noFrontendDefaults": True,
        "carrier": PAGE_BLOCK_DATA_SCHEMA,
        "schemaVersion": PAGE_BLOCK_DATA_VERSION,
    }


def field_descriptor(
    *,
    field_code: str,
    label: str,
    field_type: str,
    widget_type: str,
    component_key: str,
    semantic_type: str,
    **semantics: Any,
) -> dict[str, Any]:
    descriptor = {
        "schemaVersion": PAGE_BLOCK_DATA_VERSION,
        "fieldCode": _text(field_code),
        "label": _text(label),
        "fieldType": _text(field_type),
        "widgetType": _text(widget_type),
        "componentKey": _text(component_key),
        "semanticType": _text(semantic_type),
    }
    for key, value in semantics.items():
        if value is not None:
            descriptor[key] = deepcopy(value)
    return descriptor


def descriptor_ref(*, descriptor_id: str, raw_value_path: str) -> dict[str, str]:
    return {
        "kind": "descriptor",
        "descriptorId": _text(descriptor_id),
        "rawValuePath": _text(raw_value_path) or "value",
    }


def widget_ref(*, widget_id: str, raw_value_path: str) -> dict[str, str]:
    return {
        "kind": "widget",
        "widgetId": _text(widget_id),
        "rawValuePath": _text(raw_value_path) or "value",
    }


def build_data_contract(
    *,
    rows: Iterable[dict[str, Any]],
    field_refs: dict[str, dict[str, str]],
    currencies: dict[str, Any] | None = None,
    timezone: str,
    source_authority: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_rows = []
    seen = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        row_key = _text(row.get("rowKey") or row.get("key") or row.get("id")) or f"row_{index + 1}"
        if row_key in seen:
            raise ValueError(f"duplicate page-block-data rowKey: {row_key}")
        seen.add(row_key)
        values = row.get("values") if isinstance(row.get("values"), dict) else row
        normalized_rows.append({"rowKey": row_key, "values": deepcopy(values)})
    if not normalized_rows:
        raise ValueError("page-block-data requires at least one row")
    if not field_refs:
        raise ValueError("page-block-data requires at least one fieldRef")
    return {
        "schemaVersion": PAGE_BLOCK_DATA_VERSION,
        "fieldRefs": deepcopy(field_refs),
        "rows": normalized_rows,
        "context": {
            "currencies": deepcopy(currencies or {}),
            "timezone": _text(timezone) or "UTC",
        },
        "sourceAuthority": deepcopy(source_authority or source_authority_contract()),
    }


def build_page_orchestration_page_block_data(
    *,
    descriptors: dict[str, dict[str, Any]],
    data_contracts: dict[str, dict[str, Any]],
    enabled: bool,
) -> dict[str, Any]:
    if not enabled:
        return {
            "contract_version": LEGACY_PAGE_ORCHESTRATION_VERSION,
            "schema_version": LEGACY_PAGE_ORCHESTRATION_VERSION,
        }
    return {
        "contract_version": CURRENT_PAGE_ORCHESTRATION_VERSION,
        "schema_version": CURRENT_PAGE_ORCHESTRATION_VERSION,
        "block_field_descriptors": deepcopy(descriptors),
        "block_data_contracts": deepcopy(data_contracts),
    }
