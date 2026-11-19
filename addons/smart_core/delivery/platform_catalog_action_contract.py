"""Shared contract for admitting one native entry into a product draft."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


CATALOG_ENTRY_ADD_INTENT = "release.operator.add_catalog_entry"
CATALOG_ENTRY_ADD_ACCEPTED_FIELDS = (
    "product_key",
    "menu_id",
    "center_key",
    "release_state",
)
CATALOG_ENTRY_ADD_READBACK_FIELDS = (
    "action",
    "surface",
    "readback",
)
CATALOG_ENTRY_RELEASE_STATE_OPTIONS = (
    {"value": "preview", "label": "预览（推荐）"},
    {"value": "released", "label": "正式"},
)
CATALOG_ENTRY_RELEASE_STATES = frozenset(
    option["value"] for option in CATALOG_ENTRY_RELEASE_STATE_OPTIONS
)
CATALOG_ENTRY_DEFAULT_RELEASE_STATE = "preview"


def add_catalog_entry_action_contract(
    *,
    enabled: bool,
    reason_code: str,
) -> dict[str, Any]:
    """Return the complete executable/strict-consumer action declaration."""

    return {
        "intent": CATALOG_ENTRY_ADD_INTENT,
        "enabled": bool(enabled),
        "reason_code": str(reason_code or ""),
        "accepted_fields": list(CATALOG_ENTRY_ADD_ACCEPTED_FIELDS),
        "default_release_state": CATALOG_ENTRY_DEFAULT_RELEASE_STATE,
        "release_state_options": deepcopy(
            list(CATALOG_ENTRY_RELEASE_STATE_OPTIONS)
        ),
        "readback_fields": list(CATALOG_ENTRY_ADD_READBACK_FIELDS),
    }
