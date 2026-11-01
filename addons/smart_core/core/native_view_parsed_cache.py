# -*- coding: utf-8 -*-
"""Explicit request-scoped parsed-view carrier (BNVA-019 Stage 3C-02A).

Within one request the Layout Adapter (``app.view.config``) and the Business
Structure Adapter (``native_view_projection``) consume the same merged arch
without calling ``get_view()`` or ``etree.fromstring()`` twice.

The carrier is created at the request entry and passed explicitly to both
adapters.  It is NOT a module-level global and does not rely on ``id(cursor)``:
each cache entry is bound to one concrete cursor object plus the user and the
effective view context, and a closed or mismatched cursor can never hit.
"""
from __future__ import annotations

from collections import OrderedDict
from typing import Any

_MAX_ENTRIES = 32
_CONTEXT_KEYS = ("lang", "tz", "allowed_company_ids", "contract_action_id")


def _context_digest(env: Any) -> tuple[tuple[str, str], ...]:
    context = dict(getattr(env, "context", {}) or {})
    return tuple(
        sorted(
            (key, str(context[key]))
            for key in _CONTEXT_KEYS
            if key in context
        )
    )


class RequestScopedCarrier:
    """One request, one cursor, one user, one effective view context."""

    def __init__(self, env: Any):
        self._cursor = getattr(env, "cr", None)
        self._uid = int(getattr(env, "uid", 0) or 0)
        self._su = bool(getattr(env, "su", False))
        self._context_digest = _context_digest(env)
        self._entries: "OrderedDict[tuple, dict[str, Any]]" = OrderedDict()

    def _matches(self, env: Any) -> bool:
        cursor = getattr(env, "cr", None)
        if cursor is None or cursor is not self._cursor:
            return False
        if bool(getattr(cursor, "closed", False)):
            return False
        if int(getattr(env, "uid", 0) or 0) != self._uid:
            return False
        if bool(getattr(env, "su", False)) != self._su:
            return False
        return _context_digest(env) == self._context_digest

    def store(
        self,
        env: Any,
        model: str,
        view_type: str,
        view_id: int,
        view_data: dict[str, Any],
    ) -> None:
        if not self._matches(env):
            return
        key = (model, view_type, view_id)
        self._entries[key] = view_data
        self._entries.move_to_end(key)
        while len(self._entries) > _MAX_ENTRIES:
            self._entries.popitem(last=False)

    def fetch(
        self,
        env: Any,
        model: str,
        view_type: str,
        view_id: int,
    ) -> dict[str, Any] | None:
        if not self._matches(env):
            return None
        return self._entries.get((model, view_type, view_id))

    def close(self) -> None:
        self._entries.clear()
        self._cursor = None

