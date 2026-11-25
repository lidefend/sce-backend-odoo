# -*- coding: utf-8 -*-
"""Resolve client-independent field semantics.

Declaration authority: ``contracts/registry/semantic.yaml``. The runtime image
does not ship ``contracts/``, so ``semantic_registry_generated`` carries the
declaration into the addon.

Contract V2.7 deliberately contains no frontend component vocabulary. Renderer
selection, renderer versions and visual profiles belong to the frontend
implementation registry.

Two resolution sources are reported so a caller can tell a deliberate
declaration from a derived guess:

* ``declared`` - the field descriptor carries an explicit ``semantic``;
* ``derived``  - the ordered derivation rules resolved it from field facts.

There is deliberately no separate "readonly component": a component's read
profile is part of its registration (``render_profiles``), so declaring a second
key per semantic would create an undeclared, unconsumed capability.
"""

from __future__ import annotations

import logging
from typing import Any

from .domain_field_semantics_generated import DOMAIN_FIELD_SEMANTICS
from .semantic_registry_generated import (
    DERIVATION_DEFAULT,
    DERIVATION_RULES,
    FIELD_SEMANTICS,
    NODE_SEMANTICS,
    SEMANTIC_SPEC_VERSION,
    NATIVE_WIDGET_STATUS,
    NATIVE_VIEW_WIDGET_SEMANTICS,
    NATIVE_VIEW_WIDGET_DEFAULT,
)

_logger = logging.getLogger(__name__)

SOURCE_DECLARED = "declared"
SOURCE_PROJECTED = "projected"
SOURCE_DERIVED = "derived"

# The descriptor key the assembler writes when it annotates a field from the
# contract carrier projected out of the parsed model/view facts, so
# :func:`resolve` can report that projection distinctly from a declaration a
# runtime extension made itself.  Naming it here keeps the string out of call
# sites.
ORIGIN_KEY = "semanticOrigin"
ORIGIN_PROJECTED = "projected"

# Native Odoo widget names that are themselves the semantic signal: the rules in
# ``contracts/registry/semantic.yaml`` match these spellings directly, so they
# must survive widget canonicalisation.  ``statusbar`` folded into the generic
# ``display`` token would erase the fact that a selection field is a status, and
# the status rule would become unreachable.
SEMANTIC_WIDGET_HINTS = frozenset({
    "monetary", "percentage", "percentpie", "float_time", "statusbar", "badge",
    # Accounting-only display carriers: these native widgets put a computed
    # summary into an otherwise editable-typed field (binary/integer). Their
    # meaning is read-only display, so they must survive canonicalisation or
    # they would silently render as a file upload / number input.
    "account-tax-totals-field", "payment", "statinfo",
})

FALLBACK_SEMANTIC = DERIVATION_DEFAULT
SEMANTIC_SPEC_VERSION_VALUE = SEMANTIC_SPEC_VERSION


def _text(value: Any) -> str:
    return str(value if value is not None else "").strip()


def field_type_of(field: Any) -> str:
    descriptor = field if isinstance(field, dict) else {}
    return _text(descriptor.get("ttype") or descriptor.get("type")).lower()


def _matches(rule: dict, widget: str, field_type: str) -> bool:
    field_types = rule.get("field_types")
    if field_types and field_type not in field_types:
        return False
    widgets = rule.get("widgets")
    if widgets and widget not in widgets:
        return False
    excluded = rule.get("widgets_exclude")
    if excluded and widget in excluded:
        return False
    suffix = rule.get("widget_suffix")
    if suffix and not widget.endswith(_text(suffix)):
        return False
    return True


def derive_semantic_match(field: Any = None, widget_type: str = "") -> tuple[str, bool]:
    """Return the resolved semantic and whether an ordered rule matched it.

    Callers that combine native presentation facts with canonical field facts
    need to distinguish an explicit widget rule from the generic fallback.
    Returning only the semantic string makes those two cases indistinguishable.
    """
    widget = _text(widget_type).lower()
    field_type = field_type_of(field)
    for rule in DERIVATION_RULES:
        semantic = _text(rule.get("semantic"))
        if semantic and _matches(rule, widget, field_type):
            return semantic, True
    return FALLBACK_SEMANTIC, False


def derive_semantic(field: Any = None, widget_type: str = "") -> str:
    """First ordered rule whose conditions all hold, else the declared default."""
    semantic, _matched = derive_semantic_match(field, widget_type)
    return semantic


def semantic_widget_type(native_widget: str = "", canonical_widget_type: str = "") -> str:
    """The widget token the derivation rules are evaluated against.

    One implementation for the page assembler and for the projection generator,
    so the component a page renders and the component the contract carrier
    records can never come from two different readings of the same field facts.
    """
    native = _text(native_widget).lower()
    if native in SEMANTIC_WIDGET_HINTS:
        return native
    return _text(canonical_widget_type).lower()


def resolve_native_widget(native_widget: str = "") -> dict[str, str]:
    """Return the declared support state for an explicit Odoo XML Widget.

    This lookup is deliberately distinct from semantic derivation: an unknown
    explicit Widget must stay unsupported even though a field type could derive
    a valid generic control.
    """
    normalized = _text(native_widget).lower()
    if not normalized:
        return {"status": "not_applicable", "reasonCode": ""}
    declared = NATIVE_WIDGET_STATUS.get(normalized)
    if not isinstance(declared, dict):
        return {
            "status": "unsupported",
            "reasonCode": "NATIVE_WIDGET_UNRECOGNIZED",
        }
    return {
        "status": _text(declared.get("status")).lower(),
        "reasonCode": _text(declared.get("reasonCode")),
    }


def resolve_native_view_widget(widget_name: str = "") -> dict[str, Any]:
    """Resolve one embedded Form widget to its declared semantic and payload."""
    normalized = _text(widget_name).lower()
    entry = NATIVE_VIEW_WIDGET_SEMANTICS.get(normalized) or NATIVE_VIEW_WIDGET_DEFAULT
    return {
        "semantic": _text(entry.get("semantic")),
        "status": _text(entry.get("status")).lower(),
        "reasonCode": _text(entry.get("reasonCode")),
        "payloadRequired": entry.get("payloadRequired") is True,
        "payloadSchema": _text(entry.get("payloadSchema")),
    }


def resolve(field: Any = None, widget_type: str = "") -> dict[str, str]:
    """Resolve to ``{semantic, semanticSource}``.

    An explicit, declared semantic wins. An unknown explicit semantic is a
    producer defect and fails closed instead of silently changing meaning.
    """
    descriptor = field if isinstance(field, dict) else {}
    declared = _text(descriptor.get("semantic")).lower()
    if declared:
        if declared in FIELD_SEMANTICS:
            origin = _text(descriptor.get(ORIGIN_KEY)).lower()
            return {
                "semantic": declared,
                "semanticSource": SOURCE_PROJECTED if origin == ORIGIN_PROJECTED else SOURCE_DECLARED,
            }
        raise ValueError(
            "CONTRACT_SEMANTIC_UNDECLARED:"
            f"{declared}:"
            f"{_text(descriptor.get('name')) or '<unnamed field>'}"
        )
    semantic = derive_semantic(descriptor, widget_type)
    return {
        "semantic": semantic,
        "semanticSource": SOURCE_DERIVED,
    }


def is_field_semantic(semantic: str) -> bool:
    return _text(semantic).lower() in FIELD_SEMANTICS


def is_node_semantic(semantic: str) -> bool:
    return _text(semantic).lower() in NODE_SEMANTICS


def field_semantic_definition(semantic: str) -> dict[str, Any]:
    return dict(FIELD_SEMANTICS.get(_text(semantic).lower()) or {})


def projected_field_semantics(model: str, field_name: str) -> str:
    """The contract semantic of a model field, derived from model/view facts.

    The public backend input is the model metadata plus the parsed view arch, so
    the meaning of a field is read from those facts by
    ``contracts/registry/semantic.yaml`` and projected into the runtime carrier
    ``domain_field_semantics_generated`` (the runtime image does not ship
    ``contracts/``).  Nothing is authored by hand, so there is no second input
    for the meaning that could drift out of step with the model.  Callers
    annotate the field descriptor with the result; the descriptor stays the
    single input of :func:`resolve`.
    """
    entity = _text(model).lower()
    name = _text(field_name)
    if not entity or not name:
        return ""
    declared = DOMAIN_FIELD_SEMANTICS.get(entity) or {}
    return _text(declared.get(name)).lower()


def annotate_projected_semantics(model: str, fields: Any) -> int:
    """Annotate field descriptors with the projected contract semantic.

    Returns how many descriptors were annotated.  A descriptor that already
    carries an explicit ``semantic`` keeps it: a runtime extension is a more
    specific declaration than the entity default, and silently overwriting it
    would make the runtime observation unrepresentable.  A semantic that
    ``semantic.yaml`` does not declare is never written, so this can only add
    values the resolver can honour.
    """
    annotated = 0
    rows = fields if isinstance(fields, (list, tuple)) else []
    for row in rows:
        if not isinstance(row, dict):
            continue
        semantic = projected_field_semantics(model, _text(row.get("name") or row.get("field") or row.get("fieldCode")))
        if not semantic or _text(row.get("semantic")) or semantic not in FIELD_SEMANTICS:
            continue
        row["semantic"] = semantic
        row[ORIGIN_KEY] = ORIGIN_PROJECTED
        annotated += 1
    return annotated


def semantic_of(widget_type: str = "", field: Any = None) -> str:
    """The resolved semantic (``declared`` or ``derived``)."""
    return resolve(field, widget_type)["semantic"]
