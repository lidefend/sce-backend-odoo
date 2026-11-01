# -*- coding: utf-8 -*-
"""Request-scoped shared parsed-view cache (BNVA-019 Stage 3B).

Within one request the Layout Adapter (app.view.config) and the Business
Structure Adapter (native_view_projection) must consume the same merged arch
without calling ``get_view()`` or ``etree.fromstring()`` twice.

The cache is keyed by the live cursor identity plus user and context so a
permission-pruned view never leaks across a user, company or effective context
boundary.  It is bounded and evicts oldest-first; it is an internal optimization,
not a permission authority and not a public schema.
"""
from __future__ import annotations

from collections import OrderedDict
from typing import Any

_MAX_ENTRIES = 32
_CONTEXT_KEYS = ("lang", "tz", "allowed_company_ids", "contract_action_id")
_cache: "OrderedDict[tuple, dict[str, Any]]" = OrderedDict()


def _context_digest(env: Any) -> tuple[tuple[str, str], ...]:
    context = dict(getattr(env, "context", {}) or {})
    return tuple(
        sorted(
            (key, str(context[key]))
            for key in _CONTEXT_KEYS
            if key in context
        )
    )


def _key(env: Any, model: str, view_type: str, view_id: int) -> tuple:
    cursor = getattr(env, "cr", None)
    if cursor is None:
        # Environments without a live cursor (pure unit-test fakes) never share
        # a parsed view.
        return ()
    return (id(cursor), int(env.uid or 0), model, view_type, view_id, _context_digest(env))


def store_parsed_view(env: Any, model: str, view_type: str, view_id: int, view_data: dict[str, Any]) -> None:
    """Store the L0 parsed view (arch + _arch_root + fields) for this request."""
    key = _key(env, model, view_type, view_id)
    if not key:
        return
    _cache[key] = view_data
    _cache.move_to_end(key)
    while len(_cache) > _MAX_ENTRIES:
        _cache.popitem(last=False)


def fetch_parsed_view(env: Any, model: str, view_type: str, view_id: int) -> dict[str, Any] | None:
    """Return the request-scoped parsed view, or None when absent."""
    key = _key(env, model, view_type, view_id)
    if not key:
        return None
    return _cache.get(key)


def clear_request(env: Any) -> None:
    """Drop entries belonging to one cursor (request boundary cleanup)."""
    cursor = getattr(env, "cr", None)
    if cursor is None:
        return
    cursor_id = id(cursor)
    for key in [k for k in _cache if k[0] == cursor_id]:
        _cache.pop(key, None)


def clear_all() -> None:
    _cache.clear()

