# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any


DOMAIN_OVERRIDE_REGISTRY: list[dict[str, Any]] = []


def _safe_text(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    if text.lower() in {"undefined", "null"}:
        text = ""
    return text or fallback


def register_contract_domain_override(
    name: str,
    handler: Any,
    *,
    priority: int = 100,
    native_authority_safe: bool = False,
) -> None:
    """Register a contract domain override.

    ``native_authority_safe`` marks an override whose only effect is a semantic
    declaration (``form_governance`` and friends) and which therefore stays valid
    when a native view owns the form structure. Overrides that rewrite structure
    keep the default ``False`` and stay out of the native-authority path.
    """
    if not callable(handler):
        return
    normalized_name = _safe_text(name, "unnamed_override")
    for row in DOMAIN_OVERRIDE_REGISTRY:
        if _safe_text(row.get("name")) == normalized_name:
            row["handler"] = handler
            row["priority"] = int(priority)
            row["native_authority_safe"] = bool(native_authority_safe)
            return
    DOMAIN_OVERRIDE_REGISTRY.append(
        {
            "name": normalized_name,
            "priority": int(priority),
            "handler": handler,
            "native_authority_safe": bool(native_authority_safe),
        }
    )
    DOMAIN_OVERRIDE_REGISTRY.sort(key=lambda item: int(item.get("priority") or 100))


def append_governance_diagnostic(data: dict, key: str, value: Any) -> None:
    diagnostic = data.get("diagnostic")
    if not isinstance(diagnostic, dict):
        diagnostic = {}
    diagnostic[key] = value
    data["diagnostic"] = diagnostic


def apply_domain_overrides(
    data: dict,
    contract_mode: str,
    *,
    native_authority_only: bool = False,
) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    for row in DOMAIN_OVERRIDE_REGISTRY:
        if native_authority_only and not row.get("native_authority_safe"):
            continue
        handler = row.get("handler")
        if not callable(handler):
            continue
        try:
            handler(data, contract_mode)
        except Exception as exc:
            failures.append(
                {
                    "name": _safe_text(row.get("name")),
                    "error_type": exc.__class__.__name__,
                    "message": _safe_text(str(exc))[:240],
                }
            )
            continue
    return failures
