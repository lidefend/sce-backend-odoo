"""Pure native Window Action View Set normalization.

The effective ``ir.actions.act_window.views`` sequence is the ordering authority.
This module does not query Odoo and never sorts views by Smart Core policy.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any


ACTION_VIEW_ORDER_AUTHORITY = "ir.actions.act_window.views"
ACTION_VIEW_REQUEST_OVERRIDE_DENIED = "ACTION_VIEW_REQUEST_OVERRIDE_DENIED"
NATIVE_ACTION_VIEW_OVERRIDE_AUTHORIZED = "native_action_view_override_authorized"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _positive_int(value: Any, default: int = 0) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def canonical_view_type(value: Any) -> str:
    view_type = _text(value).lower()
    return "tree" if view_type == "list" else view_type


def has_authorized_action_view_override(context: Any) -> bool:
    """Return whether the verified projection authority marked this request.

    Tokens or caller-supplied booleans are deliberately not authority. The
    existing preview verifier sets the internal marker only after validating
    the token owner, company, database, role and expiry.
    """
    return (
        isinstance(context, dict)
        and context.get(NATIVE_ACTION_VIEW_OVERRIDE_AUTHORIZED) is True
    )


def _view_kind(view_type: str) -> dict[str, Any]:
    if view_type == "form":
        return {
            "surfaceRole": "record_detail",
            "selectable": False,
            "profile": "form",
        }
    return {
        "surfaceRole": "collection",
        "selectable": True,
        "profile": canonical_view_type(view_type) or "unknown",
    }


def _normalized_view_row(raw: Any, sequence: int, *, source: str) -> dict[str, Any] | None:
    view_id = 0
    raw_view_type = ""
    if isinstance(raw, dict):
        view_id = _positive_int(
            raw.get("viewId")
            or raw.get("view_id")
            or raw.get("id"),
            0,
        )
        raw_view_type = (
            raw.get("viewType")
            or raw.get("view_type")
            or raw.get("view_mode")
            or raw.get("type")
            or ""
        )
    elif isinstance(raw, (list, tuple)) and len(raw) >= 2:
        view_id = _positive_int(raw[0], 0)
        raw_view_type = raw[1]
    view_type = canonical_view_type(raw_view_type)
    if not view_type:
        return None
    return {
        "viewType": view_type,
        "viewId": view_id,
        "actionViewSequence": sequence,
        **(_view_kind(view_type)),
        "source": source,
    }


def build_action_view_set(
    *,
    views: Any = None,
    view_mode: Any = "",
    action_view_id: Any = 0,
    action_view_type: Any = "",
) -> dict[str, Any]:
    """Normalize Odoo's effective Action views plus missing view_mode types.

    ``views`` must be the effective ``action.views`` sequence exposed by Odoo.
    Rows are retained as an array, including duplicate same-type candidates.
    ``view_mode`` only appends types absent from that sequence.
    """
    ordered: list[dict[str, Any]] = []
    for raw in views if isinstance(views, (list, tuple)) else []:
        row = _normalized_view_row(raw, len(ordered) + 1, source="action_views")
        if row:
            ordered.append(row)

    effective_types = {row["viewType"] for row in ordered}
    default_view_id = _positive_int(action_view_id, 0)
    default_view_type = canonical_view_type(action_view_type)
    raw_modes = view_mode if isinstance(view_mode, (list, tuple)) else _text(view_mode).split(",")
    supplemented_types: list[str] = []
    for raw_mode in raw_modes:
        view_type = canonical_view_type(raw_mode)
        if not view_type or view_type in effective_types:
            continue
        effective_types.add(view_type)
        supplemented_types.append(view_type)
        view_id = default_view_id if view_type == default_view_type else 0
        ordered.append({
            "viewType": view_type,
            "viewId": view_id,
            "actionViewSequence": len(ordered) + 1,
            **_view_kind(view_type),
            "source": "view_mode_supplement",
        })

    default = ordered[0] if ordered else {}
    return {
        "orderAuthority": ACTION_VIEW_ORDER_AUTHORITY,
        "defaultViewType": _text(default.get("viewType")),
        "defaultViewId": _positive_int(default.get("viewId"), 0),
        "orderedViews": deepcopy(ordered),
        "supplementedViewTypes": supplemented_types,
        "complete": bool(default),
    }


def resolve_requested_action_view(
    view_set: dict[str, Any] | None,
    *,
    requested_view_id: Any = 0,
    requested_view_type: Any = "",
    authorized_override: bool = False,
) -> dict[str, Any]:
    """Resolve one requested View against the Action View Set.

    An explicit View ID is accepted only when it names an Action candidate.
    A caller may pass ``authorized_override=True`` only from an existing
    preview/config authority; this helper does not grant that authority.
    """
    normalized = view_set if isinstance(view_set, dict) else {}
    rows = [
        row for row in normalized.get("orderedViews") or []
        if isinstance(row, dict) and _text(row.get("viewType"))
    ]
    request_id = _positive_int(requested_view_id, 0)
    request_type = canonical_view_type(requested_view_type)
    if request_id:
        candidates = [
            row for row in rows
            if _positive_int(row.get("viewId"), 0) == request_id
            and (not request_type or canonical_view_type(row.get("viewType")) == request_type)
        ]
        if candidates:
            return {
                "allowed": True,
                "authorizedOverride": False,
                "reasonCode": "",
                "view": deepcopy(candidates[0]),
            }
        if authorized_override:
            return {
                "allowed": True,
                "authorizedOverride": True,
                "reasonCode": "",
                "view": {
                    "viewType": request_type,
                    "viewId": request_id,
                    "source": "authorized_override",
                },
            }
        return {
            "allowed": False,
            "authorizedOverride": False,
            "reasonCode": ACTION_VIEW_REQUEST_OVERRIDE_DENIED,
            "view": {
                "viewType": request_type,
                "viewId": request_id,
                "source": "request",
            },
        }

    selected = next(
        (
            row for row in rows
            if request_type and canonical_view_type(row.get("viewType")) == request_type
        ),
        None,
    )
    if selected is None and rows:
        selected = rows[0]
    if selected is None:
        return {
            "allowed": False,
            "authorizedOverride": False,
            "reasonCode": "ACTION_VIEW_SET_UNRESOLVED",
            "view": {},
        }
    return {
        "allowed": True,
        "authorizedOverride": False,
        "reasonCode": "",
        "view": deepcopy(selected),
    }
