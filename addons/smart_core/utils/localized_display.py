# -*- coding: utf-8 -*-
from __future__ import annotations

import ast
import json
from typing import Any, Mapping


DEFAULT_FALLBACK_LANGS = ("zh_CN", "en_US")


def normalize_lang(value: Any) -> str:
    text = str(value or "").strip().replace("-", "_")
    if not text:
        return ""
    parts = text.split("_", 1)
    return parts[0].lower() if len(parts) == 1 else f"{parts[0].lower()}_{parts[1].upper()}"


def _mapping_from_value(value: Any) -> Mapping[str, Any] | None:
    if isinstance(value, Mapping):
        return value
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not (text.startswith("{") and text.endswith("}")):
        return None
    for parser in (json.loads, ast.literal_eval):
        try:
            parsed = parser(text)
        except (ValueError, SyntaxError, TypeError, json.JSONDecodeError):
            continue
        if isinstance(parsed, Mapping):
            return parsed
    return None


def localized_display_value(
    value: Any,
    *,
    lang: Any = "",
    fallback_langs: tuple[str, ...] = DEFAULT_FALLBACK_LANGS,
    empty: str = "",
) -> Any:
    """Return a stable display scalar without modifying the stored source value."""

    mapping = _mapping_from_value(value)
    if mapping is None:
        if isinstance(value, Mapping):
            return empty
        if isinstance(value, str) and value.strip().startswith("{"):
            return empty
        return value

    normalized = {
        normalize_lang(key): str(item or "").strip()
        for key, item in mapping.items()
        if normalize_lang(key)
    }
    requested = normalize_lang(lang)
    candidates = [
        requested,
        requested.split("_", 1)[0] if requested else "",
        *(normalize_lang(item) for item in fallback_langs),
    ]
    for key in candidates:
        if key and normalized.get(key):
            return normalized[key]
    for item in normalized.values():
        if item:
            return item
    return empty
