# -*- coding: utf-8 -*-
"""Business structure integrity validator (BNVA-02B-02A).

Shadow diagnostics only.  It checks whether a ``ui.business.config.contract``
declares enough explicit business structure for a formal page:

- ``views.form.sections[]`` must carry a stable key, a title and non-empty
  field membership (a title alone is not a business structure).
- ``views.form.identity_fields`` must be an explicit, non-empty, valid set and
  every identity field must be a member of some section.
- every business field must have one unambiguous primary section owner.
- an optional ``native_group`` mapping must resolve when the canonical native
  model is supplied.

This module is pure and has no Odoo import so it can run in offline unit tests.
It reuses the existing validation vocabulary and does not create a fourth
parallel configuration authority; publication blocking stays unchanged.
"""
from __future__ import annotations

from typing import Any


def _text(value: Any) -> str:
    return str(value or "").strip()


def _form_spec(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    orchestration = payload.get("view_orchestration")
    if not isinstance(orchestration, dict):
        return {}
    views = orchestration.get("views")
    if not isinstance(views, dict):
        return {}
    spec = views.get("form")
    return spec if isinstance(spec, dict) else {}


def _diagnostic(severity: str, code: str, target: str, message: str) -> dict[str, str]:
    return {
        "severity": severity,
        "code": code,
        "target": target,
        "message": message,
    }


def validate_business_structure(
    payload: dict[str, Any],
    *,
    model_fields: dict[str, Any] | None = None,
    native_groups: set[str] | None = None,
) -> list[dict[str, str]]:
    """Return ERROR/WARNING/NOT_VERIFIED diagnostics for a form structure config."""
    diagnostics: list[dict[str, str]] = []
    spec = _form_spec(payload)
    field_names = set(model_fields or {})

    mode = _text(spec.get("composition_mode") or spec.get("compositionMode"))
    sections = spec.get("sections")
    sections = sections if isinstance(sections, list) else []
    identity_fields = spec.get("identity_fields")
    identity_fields = identity_fields if isinstance(identity_fields, list) else []

    # A form config that declares neither a semantic surface nor sections nor
    # identity is an empty placeholder, not a formal business structure.
    if not mode and not sections and not identity_fields:
        diagnostics.append(_diagnostic(
            "ERROR",
            "FORM_STRUCTURE_EMPTY",
            "view_orchestration.views.form",
            "published form config declares no composition_mode, sections or identity_fields",
        ))
        return diagnostics

    explicit_sections = mode == "entry_semantic_surface"
    if explicit_sections and not sections:
        diagnostics.append(_diagnostic(
            "ERROR",
            "SECTION_MISSING",
            "view_orchestration.views.form.sections",
            "entry_semantic_surface requires an explicit sections declaration",
        ))

    section_field_owner: dict[str, str] = {}
    for index, row in enumerate(sections):
        if not isinstance(row, dict):
            diagnostics.append(_diagnostic(
                "ERROR", "SECTION_INVALID",
                "view_orchestration.views.form.sections[%s]" % index,
                "section entry must be an object",
            ))
            continue
        target = "view_orchestration.views.form.sections[%s]" % index
        key = _text(row.get("key"))
        title = _text(row.get("title") or row.get("label") or row.get("name"))
        fields = row.get("fields")
        fields = fields if isinstance(fields, list) else []
        if not key:
            diagnostics.append(_diagnostic(
                "ERROR", "SECTION_KEY_MISSING", target,
                "section requires a stable key",
            ))
        if not title:
            diagnostics.append(_diagnostic(
                "ERROR", "SECTION_TITLE_MISSING", target,
                "section requires a title",
            ))
        if not fields:
            diagnostics.append(_diagnostic(
                "ERROR", "SECTION_FIELDS_EMPTY", target,
                "section must declare non-empty field membership",
            ))
        for name in fields:
            code = _text(name)
            if not code:
                diagnostics.append(_diagnostic(
                    "ERROR", "SECTION_FIELD_INVALID", target,
                    "section field name is empty",
                ))
                continue
            if field_names and code not in field_names:
                diagnostics.append(_diagnostic(
                    "ERROR", "SECTION_FIELD_INVALID", target,
                    "section references unknown model field %s" % code,
                ))
            previous = section_field_owner.get(code)
            if previous is not None:
                diagnostics.append(_diagnostic(
                    "WARNING", "FIELD_MULTIPLE_SECTION", target,
                    "field %s already owned by %s; auxiliary projection must be explicit" % (code, previous),
                ))
            else:
                section_field_owner[code] = key or title or target
        native_group = row.get("native_group")
        if native_group is not None:
            groups = native_group if isinstance(native_group, list) else [native_group]
            for group in groups:
                group_name = _text(group)
                if not group_name:
                    continue
                if native_groups is not None and group_name not in native_groups:
                    diagnostics.append(_diagnostic(
                        "ERROR", "NATIVE_GROUP_UNRESOLVED", target,
                        "native_group %s not found in canonical native view" % group_name,
                    ))
                elif native_groups is None:
                    diagnostics.append(_diagnostic(
                        "NOT_VERIFIED", "NATIVE_GROUP_UNVERIFIED", target,
                        "native_group %s cannot be resolved without a canonical native model" % group_name,
                    ))

    if mode in {"entry_semantic_surface", "native_semantic_surface", "semantic_native_surface"} and not identity_fields:
        diagnostics.append(_diagnostic(
            "ERROR", "IDENTITY_MISSING",
            "view_orchestration.views.form.identity_fields",
            "formal business structure requires an explicit identity_fields declaration",
        ))
    for name in identity_fields:
        code = _text(name)
        if not code:
            continue
        if field_names and code not in field_names:
            diagnostics.append(_diagnostic(
                "ERROR", "IDENTITY_FIELD_INVALID",
                "view_orchestration.views.form.identity_fields",
                "identity references unknown model field %s" % code,
            ))
        if explicit_sections and code and code not in section_field_owner:
            diagnostics.append(_diagnostic(
                "ERROR", "IDENTITY_NOT_IN_SECTION",
                "view_orchestration.views.form.identity_fields",
                "identity field %s is not a member of any section" % code,
            ))

    return diagnostics
