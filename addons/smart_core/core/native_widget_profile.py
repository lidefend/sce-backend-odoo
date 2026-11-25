"""Native View Widget provenance without UI or ORM assumptions."""
from __future__ import annotations

from typing import Any

from .contract_runtime.semantic_resolver import (
    resolve_native_widget,
    semantic_of,
)


WIDGET_SOURCE_NATIVE_EXPLICIT = "native_explicit"
WIDGET_SOURCE_MODEL_DERIVED = "model_metadata_derived"
WIDGET_SOURCE_COMPATIBILITY = "compatibility_default"
WIDGET_SOURCES = frozenset({
    WIDGET_SOURCE_NATIVE_EXPLICIT,
    WIDGET_SOURCE_MODEL_DERIVED,
    WIDGET_SOURCE_COMPATIBILITY,
})


def _text(value: Any) -> str:
    return str(value or "").strip()


def widget_source_and_value(field: dict[str, Any] | None) -> tuple[str, str, str]:
    """Return ``(source, native_widget, declared_widget)``.

    A producer must mark an XML-declared Widget explicitly. A bare ``widget``
    value is retained for compatibility but never silently promoted to a native
    fact.
    """
    row = field if isinstance(field, dict) else {}
    declared = _text(row.get("widget"))
    explicit_marker = _text(row.get("native_widget") or row.get("nativeWidget"))
    source_raw = _text(row.get("widget_source") or row.get("widgetSource")).lower()

    if explicit_marker:
        return WIDGET_SOURCE_NATIVE_EXPLICIT, explicit_marker, declared or explicit_marker
    if source_raw == WIDGET_SOURCE_NATIVE_EXPLICIT:
        if declared:
            return WIDGET_SOURCE_NATIVE_EXPLICIT, declared, declared
        return WIDGET_SOURCE_MODEL_DERIVED, "", ""
    if source_raw == WIDGET_SOURCE_MODEL_DERIVED:
        return WIDGET_SOURCE_MODEL_DERIVED, "", declared
    if source_raw == WIDGET_SOURCE_COMPATIBILITY:
        return WIDGET_SOURCE_COMPATIBILITY, "", declared
    return WIDGET_SOURCE_COMPATIBILITY, "", declared


def build_widget_provenance(
    field: dict[str, Any] | None,
    *,
    resolved_widget_type: str,
) -> dict[str, Any]:
    source, native_widget, declared_widget = widget_source_and_value(field)
    resolved = _text(resolved_widget_type).lower()
    if native_widget:
        resolution = resolve_native_widget(native_widget)
    else:
        resolution = {"status": "not_applicable", "reasonCode": ""}
    return {
        "nativeWidget": native_widget,
        "widgetSource": source,
        "declaredWidget": declared_widget,
        "derivedWidgetType": "" if native_widget else resolved,
        "resolvedWidgetType": resolved,
        "resolutionStatus": resolution["status"],
        "reasonCode": resolution["reasonCode"],
    }


def resolve_widget_contract(
    field: dict[str, Any] | None,
    *,
    resolved_widget_type: str,
    semantic_widget_type: str,
) -> dict[str, Any]:
    provenance = build_widget_provenance(field, resolved_widget_type=resolved_widget_type)
    if provenance["resolutionStatus"] == "unsupported":
        semantic = "unsupported_native_widget"
    else:
        semantic = semantic_of(semantic_widget_type, field)
    return {
        "semantic": semantic,
        "provenance": provenance,
    }
