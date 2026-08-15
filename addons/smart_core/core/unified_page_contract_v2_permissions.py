# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any


RIGHT_KEYS = ("read", "write", "create", "unlink", "admin")


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _explicit_rights(value: Any) -> dict[str, Any]:
    source = _dict(value)
    return {key: source[key] for key in RIGHT_KEYS if isinstance(source.get(key), bool)}


def resolve_permission_rights(permission_contract: Any) -> dict[str, Any]:
    """Resolve the canonical rights map from supported permission envelopes."""

    root = _dict(permission_contract)
    effective = _dict(root.get("effective"))
    for candidate in (
        _dict(effective.get("rights")),
        effective,
        _dict(root.get("rights")),
        root,
    ):
        rights = _explicit_rights(candidate)
        if rights:
            return rights
    return {}


def permission_auth_level(rights: Any, *, fallback: str = "read") -> str:
    resolved = _explicit_rights(rights)
    if resolved.get("admin") is True:
        return "admin"
    if resolved.get("write") is True or resolved.get("create") is True:
        return "edit"
    if resolved.get("read") is True:
        return "read"
    if resolved and not any(resolved.values()):
        return "none"
    return fallback if fallback in {"none", "read", "edit", "admin"} else "read"
