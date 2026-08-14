# -*- coding: utf-8 -*-
from __future__ import annotations

from copy import deepcopy
from typing import Any


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _text(value: Any, default: str = "") -> str:
    normalized = str(value or "").strip()
    return normalized or default


def _positive_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def normalize_runtime_business_actions(
    rows: Any,
    *,
    existing_keys: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Normalize finalizer actions as fail-closed inputs to the V2 assembler."""
    seen = set(existing_keys or set())
    normalized: list[dict[str, Any]] = []
    for raw in rows if isinstance(rows, list) else []:
        if not isinstance(raw, dict):
            continue
        row = deepcopy(raw)
        key = _text(row.get("key") or row.get("action_key") or row.get("intent"))
        if not key or key in seen:
            continue
        kind = _text(row.get("kind"), "open").lower()
        target = deepcopy(_dict(row.get("target")))
        raw_target = row.get("target")
        for source_key, target_key in (
            ("action_id", "action_id"),
            ("ref", "ref"),
            ("url", "url"),
            ("route", "route"),
        ):
            if row.get(source_key) not in (None, ""):
                target[target_key] = deepcopy(row.get(source_key))
        if isinstance(raw_target, str) and raw_target.strip():
            target["target"] = raw_target.strip()

        button = deepcopy(_dict(row.get("button")))
        method = _text(row.get("method") or _dict(row.get("mutation")).get("operation"))
        if method and kind in {"mutation", "object"}:
            button.setdefault("name", method)
            button.setdefault("type", "object")

        permission_resolved = isinstance(row.get("allowed"), bool) and isinstance(row.get("enabled"), bool)
        allowed = row.get("allowed") is True if permission_resolved else False
        enabled = row.get("enabled") is True if permission_resolved else False
        raw_scope = _text(row.get("target_scope"), "page")
        target_scope = raw_scope if raw_scope in {"widget", "container", "page", "dataSource", "runtime"} else "page"
        normalized.append({
            **row,
            "key": key,
            "target": target,
            "button": button,
            "level": _text(row.get("level"), "header"),
            "target_scope": target_scope,
            "source_widget_id": _text(row.get("source_widget_id"), "page.header"),
            "source_channel": "runtime_business_action",
            "presentation_authority": _text(row.get("presentation_authority"), "product_contract"),
            "presentation_priority": _positive_int(row.get("presentation_priority"), 300),
            "allowed": allowed,
            "enabled": enabled,
            "disabled": row.get("disabled") is True or not allowed or not enabled,
            "reason_code": _text(
                row.get("reason_code"),
                "ACTION_PERMISSION_UNRESOLVED" if not permission_resolved else "ACTION_NOT_ALLOWED",
            ) if not allowed or not enabled else _text(row.get("reason_code")),
            "entitlement_evaluated": permission_resolved,
        })
        seen.add(key)
    return normalized
