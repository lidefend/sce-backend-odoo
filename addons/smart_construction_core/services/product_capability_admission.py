"""Pure capability merge rules for catalog-entry admission."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


ADMISSION_OWNED_FIELDS = (
    "group_key",
    "group_label",
    "group_sequence",
    "enabled",
    "release_state",
    "access_level",
    "menu_xmlid",
    "action_id",
    "res_model",
)
ADMISSION_DEFAULT_FIELDS = (
    "capability_key",
    "label",
    "target_page_key",
    "source_kind",
    "entry_target_policy",
)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _matches(capability: dict[str, Any], menu_xmlid: str) -> bool:
    identities = {
        _text(capability.get("menu_xmlid")),
        _text(capability.get("target_page_key")),
    }
    return bool(menu_xmlid and menu_xmlid in identities)


def merge_admission_capability(
    existing_capabilities: Any,
    generated_target: dict[str, Any],
    *,
    menu_xmlid: str,
) -> list[Any]:
    """Update only the admitted entry and preserve every unrelated fact."""

    capabilities = (
        [deepcopy(row) for row in existing_capabilities]
        if isinstance(existing_capabilities, list)
        else []
    )
    matches = [
        index
        for index, row in enumerate(capabilities)
        if isinstance(row, dict) and _matches(row, menu_xmlid)
    ]
    if not matches:
        capabilities.append(deepcopy(generated_target))
        return capabilities
    first = matches[0]
    merged = deepcopy(capabilities[first])
    for field in ADMISSION_OWNED_FIELDS:
        if field in generated_target:
            merged[field] = deepcopy(generated_target[field])
    for field in ADMISSION_DEFAULT_FIELDS:
        if not merged.get(field) and generated_target.get(field):
            merged[field] = deepcopy(generated_target[field])
    capabilities[first] = merged
    for index in reversed(matches[1:]):
        del capabilities[index]
    return capabilities
