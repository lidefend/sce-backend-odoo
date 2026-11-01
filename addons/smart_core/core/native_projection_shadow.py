# -*- coding: utf-8 -*-
"""Shadow observation for native projection fallback (BNVA-019 3C-03C-02A).

Diagnostic-only counters.  They never change contract output, never record
field values or credentials, and are not a product state.  The handler and the
assembler emit counter events so a runtime audit can prove whether the legacy
ownership catch-all still has real consumers.
"""
from __future__ import annotations

import threading
from collections import defaultdict
from typing import Any

_lock = threading.Lock()
_events: dict[tuple, dict[str, Any]] = {}


def _key(model: str, action_id: Any, view_id: Any) -> tuple:
    return (str(model or ""), int(action_id or 0), int(view_id or 0))


def _entry(model: str, action_id: Any, view_id: Any) -> dict[str, Any]:
    key = _key(model, action_id, view_id)
    if key not in _events:
        _events[key] = {
            "native_success": 0,
            "native_failure": 0,
            "default_fallback": 0,
            "catch_all_entered": 0,
            "catch_all_fields": 0,
            "authority": None,
            "failure_categories": defaultdict(int),
        }
    return _events[key]


def record_native_success(model: str, action_id: Any, view_id: Any, authority: str) -> None:
    with _lock:
        entry = _entry(model, action_id, view_id)
        entry["native_success"] += 1
        entry["authority"] = authority


def record_native_failure(model: str, action_id: Any, view_id: Any, category: str) -> None:
    with _lock:
        entry = _entry(model, action_id, view_id)
        entry["native_failure"] += 1
        entry["failure_categories"][category] += 1


def record_default_fallback(model: str, action_id: Any, view_id: Any) -> None:
    with _lock:
        _entry(model, action_id, view_id)["default_fallback"] += 1


def record_catch_all(model: str, action_id: Any, view_id: Any, field_count: int) -> None:
    with _lock:
        entry = _entry(model, action_id, view_id)
        entry["catch_all_entered"] += 1
        entry["catch_all_fields"] += int(field_count or 0)


def snapshot() -> dict[str, dict[str, Any]]:
    with _lock:
        out: dict[str, dict[str, Any]] = {}
        for (model, action_id, view_id), entry in sorted(_events.items()):
            out[f"{model}:{action_id}:{view_id}"] = {
                "native_success": entry["native_success"],
                "native_failure": entry["native_failure"],
                "default_fallback": entry["default_fallback"],
                "catch_all_entered": entry["catch_all_entered"],
                "catch_all_fields": entry["catch_all_fields"],
                "authority": entry["authority"],
                "failure_categories": dict(entry["failure_categories"]),
            }
        return out


def reset() -> None:
    with _lock:
        _events.clear()

