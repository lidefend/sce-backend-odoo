"""Generic product-center policy normalization.

This module owns reusable policy mechanics only. Product-specific legacy-name
mapping lives in the owning P1 extension and is supplied through a resolver.
"""

from __future__ import annotations

import copy
from typing import Any, Callable, Iterable


WORKBENCH_CENTER_KEY = "workspace.home.workbench"
MIN_SEQUENCE = 0
MAX_SEQUENCE = 9999
MAX_CENTER_LABEL_LENGTH = 80


class ProductCenterPolicyError(ValueError):
    """Fail-closed product-center conflict with an operator-safe reason code."""

    def __init__(self, code: str, detail: str = ""):
        self.code = str(code or "PRODUCT_CENTER_POLICY_INVALID").strip()
        self.detail = str(detail or "").strip()
        super().__init__(
            f"{self.code}: {self.detail}" if self.detail else self.code
        )


def _text(value: Any) -> str:
    return str(value or "").strip()


def _int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _declared_int(source: dict[str, Any], keys: tuple[str, ...], default: int) -> int:
    for key in keys:
        if key not in source:
            continue
        value = source.get(key)
        if value in (None, ""):
            continue
        return _int(value, default)
    return default


def stable_center_key(value: str) -> str:
    key = _text(value)
    if key.startswith("construction.") and not key.startswith("construction.center."):
        return ""
    return key


CenterResolver = Callable[[dict[str, Any], int], dict[str, Any] | None]


def _resolved_center(
    group: dict[str, Any],
    index: int,
    legacy_center_resolver: CenterResolver | None,
) -> dict[str, Any]:
    explicit = _text(group.get("center_key"))
    candidate = explicit or _text(group.get("group_key") or group.get("key"))
    label = _text(group.get("group_label") or group.get("label") or group.get("title"))
    center = None
    if candidate and stable_center_key(candidate):
        center = {
            "stable_key": candidate,
            "key": candidate,
            "name": label or candidate,
            "sequence": _declared_int(
                group,
                ("sequence", "center_sequence"),
                (index + 1) * 10,
            ),
        }
    elif legacy_center_resolver is not None:
        center = legacy_center_resolver(group, index)
    if center:
        return center
    if candidate.startswith("construction.") or candidate == WORKBENCH_CENTER_KEY:
        raise ProductCenterPolicyError(
            "PRODUCT_CENTER_IDENTITY_UNMAPPED",
            f"group_key={candidate!r} label={label!r}",
        )
    if not candidate:
        raise ProductCenterPolicyError(
            "PRODUCT_CENTER_IDENTITY_REQUIRED",
            f"group index {index} has no stable center key",
        )
    # Explicit non-construction groups remain valid product-extension points.
    return {
        "stable_key": candidate,
        "key": candidate,
        "name": label or candidate,
        "sequence": _declared_int(
            group,
            ("sequence", "center_sequence"),
            (index + 1) * 10,
        ),
        "extension_center": True,
    }


def _menu_identity(menu: dict[str, Any]) -> str:
    return _text(
        menu.get("menu_xmlid")
        or menu.get("menu_key")
        or menu.get("page_key")
        or menu.get("scene_key")
    )


def _sync_capabilities(
    policy: dict[str, Any], menu_centers: dict[str, dict[str, Any]]
) -> list[Any]:
    capabilities = policy.get("capabilities")
    if not isinstance(capabilities, list):
        return copy.deepcopy(capabilities)
    result = []
    for raw in capabilities:
        row = copy.deepcopy(raw)
        if isinstance(row, dict):
            center = menu_centers.get(_menu_identity(row))
            if center:
                row.update(
                    {
                        "center_key": center["center_key"],
                        "group_key": center["center_key"],
                        "group_label": center["group_label"],
                        "group_sequence": center["group_sequence"],
                    }
                )
        result.append(row)
    return result


def normalize_product_policy(
    policy: dict[str, Any] | None,
    *,
    strict: bool = True,
    legacy_center_resolver: CenterResolver | None = None,
) -> dict[str, Any]:
    """Normalize center identity while preserving labels, order and placement."""

    source = policy if isinstance(policy, dict) else {}
    groups = source.get("menu_groups")
    if not isinstance(groups, list):
        return copy.deepcopy(source)
    # Each output subtree is detached once. Copying the entire policy, then
    # every group and every menu again multiplies startup work for no benefit.
    normalized = copy.deepcopy({
        key: value for key, value in source.items()
        if key not in {"menu_groups", "capabilities"}
    })
    resolved_groups: dict[str, dict[str, Any]] = {}
    menu_centers: dict[str, dict[str, Any]] = {}
    for index, raw_group in enumerate(groups):
        if not isinstance(raw_group, dict):
            if strict:
                raise ProductCenterPolicyError(
                    "PRODUCT_CENTER_GROUP_INVALID", f"group index {index}"
                )
            continue
        center = _resolved_center(raw_group, index, legacy_center_resolver)
        key = _text(center["stable_key"])
        label = _text(
            raw_group.get("group_label")
            or raw_group.get("label")
            or raw_group.get("title")
            or center.get("name")
        ) or key
        sequence = _declared_int(
            raw_group,
            ("sequence", "center_sequence"),
            _int(center.get("sequence"), (index + 1) * 10),
        )
        existing = resolved_groups.get(key)
        if existing and (
            _text(existing.get("group_label")) != label
            or _int(existing.get("sequence"), sequence) != sequence
        ):
            raise ProductCenterPolicyError(
                "PRODUCT_CENTER_DEFINITION_CONFLICT",
                f"center {key!r} has different label or sequence",
            )
        group = copy.deepcopy({key: value for key, value in raw_group.items() if key != "menus"})
        group.update(
            {
                "center_key": key,
                "group_key": key,
                "group_label": label,
                "label": label,
                "title": _text(raw_group.get("title")) or label,
                "sequence": sequence,
            }
        )
        menus = raw_group.get("menus")
        next_menus = []
        for raw_menu in menus if isinstance(menus, list) else []:
            if not isinstance(raw_menu, dict):
                if strict:
                    raise ProductCenterPolicyError(
                        "PRODUCT_CENTER_MENU_INVALID",
                        f"center {key!r} contains a non-object menu",
                    )
                continue
            menu = copy.deepcopy(raw_menu)
            menu_identity = _menu_identity(menu)
            if not menu_identity:
                raise ProductCenterPolicyError(
                    "PRODUCT_CENTER_MENU_IDENTITY_REQUIRED", f"center {key!r}"
                )
            center_fact = {
                "center_key": key,
                "group_key": key,
                "group_label": label,
                "group_sequence": sequence,
            }
            previous = menu_centers.get(menu_identity)
            if previous and previous["center_key"] != key:
                raise ProductCenterPolicyError(
                    "PRODUCT_CENTER_ENTRY_CONFLICT",
                    f"{menu_identity!r} appears in both "
                    f"{previous['center_key']!r} and {key!r}",
                )
            menu_centers[menu_identity] = center_fact
            menu.update(center_fact)
            next_menus.append(menu)
        group["menus"] = next_menus
        if existing:
            existing.setdefault("menus", []).extend(next_menus)
        else:
            resolved_groups[key] = group
    normalized["menu_groups"] = sorted(
        resolved_groups.values(),
        key=lambda row: (
            _int(row.get("sequence"), MAX_SEQUENCE),
            _text(row.get("center_key")),
        ),
    )
    normalized["capabilities"] = _sync_capabilities(source, menu_centers)
    return normalized


def product_center_index(
    policy: dict[str, Any] | None,
    *,
    legacy_center_resolver: CenterResolver | None = None,
) -> dict[str, Any]:
    normalized = normalize_product_policy(
        policy,
        legacy_center_resolver=legacy_center_resolver,
    )
    centers = []
    entries = []
    by_menu: dict[str, dict[str, Any]] = {}
    for group in normalized.get("menu_groups") or []:
        if not isinstance(group, dict):
            continue
        center = {
            "center_key": _text(group.get("center_key") or group.get("group_key")),
            "label": _text(group.get("group_label") or group.get("label")),
            "sequence": _int(group.get("sequence"), MAX_SEQUENCE),
            "entry_count": len(
                [row for row in group.get("menus") or [] if isinstance(row, dict)]
            ),
        }
        centers.append(center)
        for menu in group.get("menus") or []:
            if not isinstance(menu, dict):
                continue
            menu_xmlid = _menu_identity(menu)
            if not menu_xmlid:
                continue
            entry = {
                "menu_xmlid": menu_xmlid,
                "label": _text(menu.get("label") or menu.get("page_label") or menu_xmlid),
                "center_key": center["center_key"],
                "center_label": center["label"],
                "center_sequence": center["sequence"],
            }
            entries.append(entry)
            by_menu[menu_xmlid] = entry
    return {"centers": centers, "entries": entries, "by_menu": by_menu}


def _validated_center_updates(
    center_updates: Iterable[dict[str, Any]] | None,
    by_key: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    updates: dict[str, dict[str, Any]] = {}
    for raw in center_updates or []:
        if not isinstance(raw, dict):
            raise ProductCenterPolicyError(
                "PRODUCT_CENTER_UPDATE_INVALID", "center update is not an object"
            )
        key = _text(raw.get("center_key") or raw.get("group_key"))
        if not key or key not in by_key:
            raise ProductCenterPolicyError("PRODUCT_CENTER_UNKNOWN", key or "<missing>")
        update: dict[str, Any] = {}
        if "label" in raw or "name" in raw or "group_label" in raw:
            label = _text(raw.get("label") or raw.get("name") or raw.get("group_label"))
            if not label:
                raise ProductCenterPolicyError("PRODUCT_CENTER_LABEL_REQUIRED", key)
            if len(label) > MAX_CENTER_LABEL_LENGTH:
                raise ProductCenterPolicyError("PRODUCT_CENTER_LABEL_TOO_LONG", key)
            update.update(
                {"group_label": label, "label": label, "title": label}
            )
        if "sequence" in raw:
            try:
                sequence = int(raw.get("sequence"))
            except (TypeError, ValueError) as exc:
                raise ProductCenterPolicyError(
                    "PRODUCT_CENTER_SEQUENCE_INVALID", key
                ) from exc
            if not MIN_SEQUENCE <= sequence <= MAX_SEQUENCE:
                raise ProductCenterPolicyError(
                    "PRODUCT_CENTER_SEQUENCE_OUT_OF_RANGE", key
                )
            update["sequence"] = sequence
        if update:
            updates[key] = update
    return updates


def apply_product_center_updates(
    policy: dict[str, Any] | None,
    *,
    center_updates: Iterable[dict[str, Any]] | None = None,
    entry_placements: Iterable[dict[str, Any]] | None = None,
    legacy_center_resolver: CenterResolver | None = None,
) -> dict[str, Any]:
    """Apply label/order/placement edits while preserving stable identities."""

    normalized = normalize_product_policy(
        policy,
        legacy_center_resolver=legacy_center_resolver,
    )
    groups = [
        copy.deepcopy(group)
        for group in normalized.get("menu_groups") or []
        if isinstance(group, dict)
    ]
    by_key = {
        _text(group.get("center_key") or group.get("group_key")): group
        for group in groups
    }
    for center_key, update in _validated_center_updates(
        center_updates, by_key
    ).items():
        group = by_key[center_key]
        group.update(update)
        for menu in group.get("menus") or []:
            if isinstance(menu, dict):
                menu.update(
                    {
                        "center_key": center_key,
                        "group_key": center_key,
                        "group_label": _text(group.get("group_label")),
                        "group_sequence": _int(group.get("sequence"), MAX_SEQUENCE),
                    }
                )

    indexed: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    for group in groups:
        for menu in group.get("menus") or []:
            if not isinstance(menu, dict):
                continue
            menu_xmlid = _menu_identity(menu)
            if menu_xmlid:
                indexed[menu_xmlid] = (group, menu)
    moved: set[str] = set()
    for raw in entry_placements or []:
        if not isinstance(raw, dict):
            raise ProductCenterPolicyError(
                "PRODUCT_CENTER_PLACEMENT_INVALID", "placement is not an object"
            )
        menu_xmlid = _text(raw.get("menu_xmlid") or raw.get("menu_key"))
        center_key = stable_center_key(
            _text(raw.get("center_key") or raw.get("group_key"))
        )
        if not menu_xmlid or not center_key:
            raise ProductCenterPolicyError(
                "PRODUCT_CENTER_PLACEMENT_IDENTITY_REQUIRED", menu_xmlid
            )
        if menu_xmlid not in indexed:
            raise ProductCenterPolicyError(
                "PRODUCT_CENTER_ENTRY_UNKNOWN", menu_xmlid
            )
        target = by_key.get(center_key)
        if not target:
            raise ProductCenterPolicyError("PRODUCT_CENTER_UNKNOWN", center_key)
        current_group, menu = indexed[menu_xmlid]
        if current_group is target:
            continue
        current_group["menus"] = [
            row for row in current_group.get("menus") or [] if row is not menu
        ]
        moved_menu = copy.deepcopy(menu)
        moved_menu.update(
            {
                "center_key": center_key,
                "group_key": center_key,
                "group_label": _text(target.get("group_label")),
                "group_sequence": _int(target.get("sequence"), MAX_SEQUENCE),
            }
        )
        target.setdefault("menus", []).append(moved_menu)
        indexed[menu_xmlid] = (target, moved_menu)
        moved.add(menu_xmlid)
    normalized["menu_groups"] = groups
    result = normalize_product_policy(
        normalized,
        legacy_center_resolver=legacy_center_resolver,
    )
    if moved:
        result["note"] = "product center placement updated from release operator"
    return result
