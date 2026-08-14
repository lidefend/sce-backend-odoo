# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any


def _nested_get(mapping: dict[str, Any], key: str, default: Any = None) -> Any:
    if key in mapping:
        return mapping.get(key, default)
    for nested_key in ("payload", "params", "data", "args"):
        nested = mapping.get(nested_key)
        if isinstance(nested, dict) and key in nested:
            return nested.get(key, default)
    return default


def client_requested_sudo(params: dict[str, Any]) -> bool:
    if not isinstance(params, dict):
        return False
    value = _nested_get(params, "sudo", False)
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "y", "on")
    return False


def resolve_api_data_sudo(params: dict[str, Any]) -> bool:
    """api.data must not let client payloads choose an elevated ORM environment."""
    return False


def authoritative_context_default_fields(
    context: dict[str, Any],
    model_fields: Any,
) -> tuple[str, ...]:
    """Return context defaults that map to real ORM fields.

    An Odoo action may intentionally create a record entirely from its
    ``default_*`` context.  Unknown keys do not establish create authority.
    """
    if not isinstance(context, dict):
        return ()
    field_names = set(model_fields.keys()) if hasattr(model_fields, "keys") else set(model_fields or ())
    return tuple(sorted({
        str(key)[len("default_"):]
        for key in context
        if str(key).startswith("default_")
        and str(key)[len("default_"):]
        and str(key)[len("default_"):] in field_names
    }))


def merge_orm_create_defaults(env_model: Any, vals: dict[str, Any]) -> dict[str, Any]:
    """Filter client values and resolve Odoo defaults for all missing fields."""
    model_fields = env_model._fields or {}
    safe_vals = {key: value for key, value in (vals or {}).items() if key in model_fields}
    missing = [
        name
        for name in model_fields
        if name not in safe_vals and not str(name or "").startswith("__")
    ]
    if not missing:
        return safe_vals
    try:
        defaults = env_model.default_get(missing) or {}
    except Exception:
        defaults = {}
    if isinstance(defaults, dict):
        for name in missing:
            if name in defaults and defaults.get(name) is not None:
                safe_vals[name] = defaults.get(name)
    return safe_vals
