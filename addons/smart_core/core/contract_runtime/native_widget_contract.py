# -*- coding: utf-8 -*-
"""Project parsed native widget facts into Contract V2 field semantics.

This is the single P0 responsibility boundary between the native Odoo view
projection and the platform contract. It deliberately does not execute or mount
an Odoo embedded component:

* the parsed native widget token remains an occurrence/presentation fact;
* explicit native widget semantic rules remain available for widgets such as
  ``statusbar`` and ``list_activity``;
* presentation variants such as ``daterange`` derive their meaning from the
  canonical field/control facts;
* Contract V2 structural semantics (date, datetime, monetary, boolean) are
  fixed by the field type and cannot be downgraded by a presentation token.

Business modules may declare native views and field meanings through the
existing registries. They must not add a second widget-to-component map here.
"""

from __future__ import annotations

from typing import Any

from .semantic_resolver import (
    component_key,
    component_key_for_semantic,
    derive_semantic_match,
    resolve_native_view_widget,
)


CANONICAL_WIDGET_BY_FIELD_TYPE = {
    "char": "input",
    "text": "textarea",
    "html": "html",
    "integer": "number",
    "float": "number",
    "monetary": "monetary",
    "boolean": "boolean",
    "date": "date",
    "datetime": "datetime",
    "selection": "select",
    "many2one": "many2one",
    "one2many": "one2many",
    "many2many": "many2many",
    "binary": "binary",
    "json": "json",
    "many2one_reference": "many2one",
    "reference": "many2one",
}

FIXED_SEMANTIC_BY_FIELD_TYPE = {
    "date": "date",
    "datetime": "datetime",
    "monetary": "money",
    "boolean": "boolean",
}


def _text(value: Any) -> str:
    return str(value if value is not None else "").strip()


def project_native_field_widget_contract(
    *,
    field_type: str,
    native_widget_type: str = "",
    fallback_widget_type: str = "",
    declared_semantic: str = "",
    legacy_descriptor: dict[str, Any] | None = None,
) -> dict[str, str]:
    """Return the contract projection for one parsed native widget occurrence.

    The returned ``widgetType`` is the descriptor identity (the native token
    when one was declared). ``canonicalWidgetType`` is the semantic derivation
    input and is intentionally exposed for audit/tests; it is not added to the
    wire descriptor by itself.
    """
    legacy = legacy_descriptor if isinstance(legacy_descriptor, dict) else {}
    normalized_field_type = _text(field_type).lower()
    native = _text(native_widget_type).lower()
    canonical = CANONICAL_WIDGET_BY_FIELD_TYPE.get(
        normalized_field_type,
        _text(fallback_widget_type).lower(),
    )
    widget_type = native or canonical

    semantic_type = FIXED_SEMANTIC_BY_FIELD_TYPE.get(normalized_field_type)
    if not semantic_type:
        semantic_type = _text(declared_semantic).lower()
    if not semantic_type:
        native_semantic, native_rule_matched = derive_semantic_match(legacy, widget_type)
        canonical_semantic, canonical_rule_matched = derive_semantic_match(
            legacy,
            canonical,
        )
        if native_rule_matched:
            semantic_type = native_semantic
        elif canonical_rule_matched:
            semantic_type = canonical_semantic
        else:
            semantic_type = native_semantic

    resolved_component_key = (
        component_key_for_semantic(semantic_type)
        or component_key(widget_type, legacy)
    )
    return {
        "widgetType": widget_type,
        "nativeWidgetType": native,
        "canonicalWidgetType": canonical,
        "semanticType": semantic_type,
        "componentKey": resolved_component_key,
    }


def project_native_embedded_widget_contract(widget_name: str = "") -> dict[str, Any]:
    """Project one parsed ``<widget>`` node into a platform node contract.

    The native node name is retained by the caller as occurrence evidence. This
    function only resolves the registered contract component and support state;
    it never loads or executes the embedded Odoo JavaScript component.
    """
    normalized_widget_name = _text(widget_name).lower()
    resolution = resolve_native_view_widget(normalized_widget_name)
    return {
        "nativeWidget": normalized_widget_name,
        "componentKey": _text(resolution.get("component")),
        "widgetStatus": _text(resolution.get("status")),
        "reasonCode": _text(resolution.get("reasonCode")),
        "payloadRequired": resolution.get("payloadRequired") is True,
    }
