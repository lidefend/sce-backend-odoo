# -*- coding: utf-8 -*-
"""Pure database-selection normalization for the shared intent boundary."""

from __future__ import annotations

from typing import Any, Mapping


def normalize_database_params(
    raw_params: Mapping[str, Any] | None,
    *,
    effective_db: Any,
    trusted_lock: bool,
) -> tuple[dict[str, Any], Any]:
    """Return a request-local params copy and its canonical target database."""
    params = dict(raw_params or {})
    if trusted_lock:
        locked_db = str(effective_db or "").strip()
        if locked_db:
            params["db"] = locked_db
            if "database" in params:
                params["database"] = locked_db
            return params, locked_db

    if effective_db and not params.get("db"):
        params["db"] = effective_db
    target_db = params.get("db")
    if not target_db:
        target_db = params.get("database")
    if not target_db:
        target_db = effective_db
    return params, target_db
