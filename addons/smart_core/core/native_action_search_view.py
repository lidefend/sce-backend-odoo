"""Pure native Search View identity normalization."""
from __future__ import annotations

from typing import Any


ACTION_SEARCH_VIEW_AUTHORITY = "action_search_view"
MODEL_SEARCH_VIEW_AUTHORITY = "model_default_search_view"
ACTION_SEARCH_VIEW_SOURCE = "ir.actions.act_window.search_view_id"
MODEL_SEARCH_VIEW_SOURCE = "ir.ui.view:search"


def _positive_int(value: Any) -> int:
    try:
        parsed = int(value or 0)
    except (TypeError, ValueError):
        return 0
    return parsed if parsed > 0 else 0


def build_search_native_identity(
    *,
    model: Any,
    action_id: Any = 0,
    view_id: Any = 0,
    view_xmlid: Any = "",
    authority: Any = "",
) -> dict[str, Any]:
    """Build the runtime native Search View identity.

    This function does not resolve Odoo views. It only normalizes the identity
    already established by ActionResolver or app.view.config.
    """
    normalized_model = str(model or "").strip()
    normalized_authority = str(authority or "").strip()
    normalized_view_id = _positive_int(view_id)
    normalized_action_id = _positive_int(action_id)
    if not normalized_model:
        raise ValueError("native search identity requires a model")
    if normalized_authority not in {
        ACTION_SEARCH_VIEW_AUTHORITY,
        MODEL_SEARCH_VIEW_AUTHORITY,
    }:
        raise ValueError("native search identity authority is invalid")
    if normalized_view_id <= 0:
        raise ValueError("native search identity requires a resolved view id")
    if normalized_authority == ACTION_SEARCH_VIEW_AUTHORITY and normalized_action_id <= 0:
        raise ValueError("Action-bound search identity requires an action id")
    source_locator = (
        ACTION_SEARCH_VIEW_SOURCE
        if normalized_authority == ACTION_SEARCH_VIEW_AUTHORITY
        else MODEL_SEARCH_VIEW_SOURCE
    )
    return {
        "model": normalized_model,
        "actionId": normalized_action_id or None,
        "viewId": normalized_view_id,
        "viewXmlId": str(view_xmlid or "").strip(),
        "authority": normalized_authority,
        "sourceLocator": source_locator,
    }
