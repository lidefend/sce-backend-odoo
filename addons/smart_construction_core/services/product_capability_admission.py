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
MENU_ADMISSION_OWNED_FIELDS = (
    "menu_xmlid",
    "menu_id",
    "action_id",
    "action_xmlid",
    "res_model",
    "model",
    "enabled",
    "release_state",
)
MENU_ADMISSION_DEFAULT_FIELDS = (
    "menu_key",
    "page_key",
    "label",
    "page_label",
    "sequence",
    "access_level",
    "source_kind",
    "entry_target_policy",
)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _matches(
    capability: dict[str, Any],
    generated_target: dict[str, Any],
    menu_xmlid: str,
) -> bool:
    identities = {
        _text(capability.get("menu_xmlid")),
        _text(capability.get("target_page_key")),
    }
    if not menu_xmlid or menu_xmlid not in identities:
        return False
    identity_kind = _text(capability.get("identity_kind"))
    capability_key = _text(capability.get("capability_key"))
    target_key = _text(generated_target.get("capability_key"))
    is_alias = (
        identity_kind == "entry_compatibility_alias"
        or capability_key.startswith("construction.menu.")
    )
    return bool(is_alias and (not target_key or capability_key in {"", target_key}))


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
        if isinstance(row, dict)
        and _matches(row, generated_target, menu_xmlid)
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


def merge_admitted_menu_entry(
    existing_entry: Any,
    generated_entry: dict[str, Any],
) -> dict[str, Any]:
    """Preserve maintained menu fields while applying admission-owned facts."""

    if not isinstance(existing_entry, dict):
        return deepcopy(generated_entry)
    merged = deepcopy(existing_entry)
    for field in MENU_ADMISSION_OWNED_FIELDS:
        if field in generated_entry:
            merged[field] = deepcopy(generated_entry[field])
    for field in MENU_ADMISSION_DEFAULT_FIELDS:
        if (
            field not in merged
            or merged.get(field) in (None, "")
        ) and generated_entry.get(field) is not None:
            merged[field] = deepcopy(generated_entry[field])
    return merged
