"""Project one resolved Odoo Window Action into the V2 control-plane contract."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

NATIVE_ACTION_CONTRACT_VERSION = "1.0.0"
NATIVE_ACTION_ORDER_AUTHORITY = "ir.actions.act_window.views"
NATIVE_ACTION_SOURCE_KIND = "native_action_contract_projection"
PROJECTION_STATUSES = frozenset({"ready", "blocked", "unresolved"})
RENDERER_STATUSES = frozenset({"ready", "fallback", "unsupported", "unknown"})


def _text(value: Any) -> str:
    return str(value or "").strip()


def _positive_int(value: Any) -> int:
    try:
        parsed = int(value or 0)
    except (TypeError, ValueError):
        return 0
    return parsed if parsed > 0 else 0


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _canonical_view_type(value: Any) -> str:
    view_type = _text(value).lower()
    return "tree" if view_type == "list" else view_type


def _entry_refs(rows: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[tuple[int, str]] = set()
    for raw in _list(rows):
        row = _dict(raw)
        if _text(row.get("kind")) != "menu":
            continue
        menu_id = _positive_int(row.get("menuId") or row.get("menu_id"))
        menu_xmlid = _text(row.get("menuXmlId") or row.get("menu_xmlid"))
        key = (menu_id, menu_xmlid)
        if not menu_id or key in seen:
            continue
        seen.add(key)
        out.append({
            "kind": "menu",
            "menuId": menu_id,
            "menuXmlId": menu_xmlid,
        })
    return out


def _search_projection(raw: Any, *, model: str, action_id: int) -> dict[str, Any] | None:
    identity = _dict(raw)
    view_id = _positive_int(identity.get("viewId") or identity.get("view_id"))
    if not view_id:
        return None
    identity_model = _text(identity.get("model"))
    identity_action_id = _positive_int(identity.get("actionId") or identity.get("action_id"))
    if identity_model and identity_model != model:
        raise ValueError("native Action Search identity model mismatch")
    if identity_action_id and identity_action_id != action_id:
        raise ValueError("native Action Search identity action mismatch")
    authority = _text(identity.get("authority"))
    if authority not in {"action_search_view", "model_default_search_view"}:
        raise ValueError("native Action Search identity authority is invalid")
    return {
        "viewId": view_id,
        "viewXmlId": _text(identity.get("viewXmlId") or identity.get("view_xmlid")),
        "authority": authority,
        "profileRef": "searchContract",
    }


def _projection_status(row: dict[str, Any], *, complete: bool) -> str:
    status = _text(row.get("projectionStatus") or row.get("projection_status")).lower()
    if status in PROJECTION_STATUSES:
        return status
    return "ready" if complete else "unresolved"


def _renderer_status(row: dict[str, Any]) -> str:
    status = _text(row.get("rendererStatus") or row.get("renderer_status")).lower()
    return status if status in RENDERER_STATUSES else "unknown"


def build_native_action_contract(
    *,
    model: Any,
    active_view_type: Any,
    action_identity: Any,
    view_set: Any,
    search_identity: Any = None,
    domain: Any = None,
    domain_raw: Any = "",
    context: Any = None,
    context_raw: Any = "",
    access_policy: Any = None,
    entry_refs: Any = None,
) -> dict[str, Any] | None:
    """Build the contract from already-resolved Action facts only.

    The function performs no Odoo lookup and grants no permission. It preserves
    the effective View order supplied by ActionResolver/PageAssembler.
    """
    identity = _dict(action_identity)
    action_id = _positive_int(identity.get("action_id") or identity.get("actionId"))
    if not action_id:
        return None
    normalized_model = _text(model or identity.get("model"))
    if not normalized_model:
        raise ValueError("native Action contract requires a model")
    identity_model = _text(identity.get("model"))
    if identity_model and identity_model != normalized_model:
        raise ValueError("native Action contract model mismatch")

    normalized_view_set = _dict(view_set)
    rows = [
        row for row in _list(normalized_view_set.get("orderedViews"))
        if isinstance(row, dict) and _canonical_view_type(row.get("viewType") or row.get("view_type"))
    ]
    if not rows:
        # A first-class Action contract describes a usable ordered View Set.
        # An Action with no resolved rows remains on the existing page path;
        # publishing a placeholder View type would weaken the closed protocol.
        return None
    complete = bool(normalized_view_set.get("complete") and rows)
    ordered_views: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        view_type = _canonical_view_type(row.get("viewType") or row.get("view_type"))
        projection_status = _projection_status(row, complete=complete)
        reason_code = _text(row.get("reasonCode") or row.get("reason_code"))
        if projection_status != "ready" and not reason_code:
            reason_code = "ACTION_VIEW_PROJECTION_UNRESOLVED"
        ordered_views.append({
            "viewType": view_type,
            "viewId": _positive_int(row.get("viewId") or row.get("view_id")),
            "viewXmlId": _text(row.get("viewXmlId") or row.get("view_xmlid")),
            "actionViewSequence": _positive_int(
                row.get("actionViewSequence") or row.get("action_view_sequence") or index
            ) or index,
            "surfaceRole": (
                "record_detail"
                if view_type == "form"
                else _text(row.get("surfaceRole") or row.get("surface_role")) or "collection"
            ),
            "selectable": bool(row.get("selectable")) if "selectable" in row else view_type != "form",
            "projectionStatus": projection_status,
            "rendererStatus": _renderer_status(row),
            "reasonCode": reason_code,
            "profile": _text(row.get("profile")) or view_type,
        })

    active = _canonical_view_type(active_view_type)
    available_types = [row["viewType"] for row in ordered_views]
    if active not in available_types and ordered_views:
        active = _text(normalized_view_set.get("defaultViewType")) or ordered_views[0]["viewType"]
    active = _canonical_view_type(active)
    active_in_set = active in available_types
    active_row = next(
        (row for row in ordered_views if row["viewType"] == active),
        {},
    )

    policy = _dict(access_policy)
    policy_mode = _text(policy.get("mode")).lower()
    reason_code = ""
    if policy_mode == "block":
        projection_status = "blocked"
        reason_code = _text(policy.get("reason_code")) or "ACTION_PROJECTION_BLOCKED"
    elif active_row.get("rendererStatus") == "unsupported":
        projection_status = "blocked"
        reason_code = _text(active_row.get("reasonCode")) or "CLIENT_VIEW_CAPABILITY_MISSING"
    elif not complete or not active_in_set:
        projection_status = "unresolved"
        reason_code = "ACTION_VIEW_SET_UNRESOLVED"
    else:
        projection_status = "available"

    default_view_type = _canonical_view_type(normalized_view_set.get("defaultViewType"))
    if default_view_type not in available_types:
        default_view_type = ordered_views[0]["viewType"] if ordered_views else active
    search = _search_projection(search_identity, model=normalized_model, action_id=action_id)
    backend_status = "ready" if complete and active_in_set else "unresolved"
    backend_reasons = [] if backend_status == "ready" else ["ACTION_VIEW_SET_UNRESOLVED"]

    return {
        "schemaVersion": NATIVE_ACTION_CONTRACT_VERSION,
        "identity": {
            "actionType": "ir.actions.act_window",
            "actionId": action_id,
            "actionXmlId": _text(identity.get("action_xmlid") or identity.get("actionXmlId")),
            "model": normalized_model,
        },
        "entryRefs": _entry_refs(entry_refs),
        "actionScope": {
            "domainRaw": _text(domain_raw),
            "domain": deepcopy(domain if isinstance(domain, list) else []),
            "contextRaw": _text(context_raw),
            "context": deepcopy(_dict(context)),
            "sourceAuthority": {
                "kind": "ir.actions.act_window",
            },
        },
        "projectionAvailability": {
            "status": projection_status,
            "reasonCode": reason_code,
            "authorityRef": "existing_action_access_projection",
        },
        **({"search": search} if search else {}),
        "viewSet": {
            "orderAuthority": NATIVE_ACTION_ORDER_AUTHORITY,
            "defaultViewType": default_view_type,
            "activeViewType": active,
            "orderedViews": ordered_views,
        },
        "readiness": {
            "backendContract": {
                "status": backend_status,
                "reasonCodes": backend_reasons,
            },
            "clientRenderer": {
                "status": (
                    "ready" if active_row.get("rendererStatus") == "ready"
                    else "blocked" if active_row.get("rendererStatus") == "unsupported"
                    else "unknown"
                ),
                "reasonCodes": (
                    [_text(active_row.get("reasonCode")) or "CLIENT_VIEW_CAPABILITY_MISSING"]
                    if active_row.get("rendererStatus") == "unsupported"
                    else []
                ),
            },
            "businessExecution": {
                "status": "not_applicable",
                "reasonCodes": [],
            },
        },
        "capabilities": [
            "action_view_set.v1",
            *(["search_identity.v1"] if search else []),
        ],
        "sourceAuthority": {
            "kind": NATIVE_ACTION_SOURCE_KIND,
            "projectionOnly": True,
            "noBusinessFactAuthority": True,
        },
    }
