"""P1 ownership of construction product-center identity and policy edits."""

from __future__ import annotations

from typing import Any, Iterable

from odoo.addons.smart_core.delivery.product_center_policy import (
    ProductCenterPolicyError,
    apply_product_center_updates as _apply_product_center_updates,
    normalize_product_policy,
    product_center_index as _product_center_index,
)

from .product_menu_source import (
    center_for_primary_key,
    center_identity,
    center_identity_contract,
)


def _text(value: Any) -> str:
    return str(value or "").strip()


def resolve_legacy_center(group: dict[str, Any], index: int) -> dict[str, Any] | None:
    """Resolve a persisted legacy construction group to its stable center."""
    candidate = _text(
        group.get("center_key")
        or group.get("group_key")
        or group.get("key")
    )
    label = _text(
        group.get("group_label")
        or group.get("label")
        or group.get("title")
    )
    center = center_identity(candidate) or center_identity(label)
    if not center:
        return None
    return {
        "stable_key": _text(center.get("stable_key")),
        "key": _text(center.get("key")),
        "name": _text(center.get("name")),
        "sequence": int(center.get("sequence") or (index + 1) * 10),
    }


def normalize_construction_product_policy(
    policy: dict[str, Any] | None,
) -> dict[str, Any]:
    return normalize_product_policy(
        policy,
        legacy_center_resolver=resolve_legacy_center,
    )


def construction_product_center_index(
    policy: dict[str, Any] | None,
) -> dict[str, Any]:
    return _product_center_index(
        policy,
        legacy_center_resolver=resolve_legacy_center,
    )


def apply_construction_product_center_updates(
    policy: dict[str, Any] | None,
    *,
    center_updates: Iterable[dict[str, Any]] | None = None,
    entry_placements: Iterable[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return _apply_product_center_updates(
        policy,
        center_updates=center_updates,
        entry_placements=entry_placements,
        legacy_center_resolver=resolve_legacy_center,
    )


def released_center_projection(policy: dict[str, Any] | None) -> dict[str, Any]:
    """Return the menu-to-center facts consumed by navigation and diagnostics."""
    index = construction_product_center_index(policy)
    centers = []
    for row in index["centers"]:
        center = {
            **row,
            "source": "published_product_policy",
            "policy_source": "sc.edition.release.snapshot.policy.menu_groups",
        }
        centers.append(center)
    by_menu = {
        menu_xmlid: {
            **entry,
            "source": "published_product_policy",
        }
        for menu_xmlid, entry in index["by_menu"].items()
    }
    return {
        "centers": centers,
        "by_menu": by_menu,
        "source": "published_product_policy",
        "center_contract": {
            "schema": center_identity_contract()["schema"],
            "baseline_id": center_identity_contract()["baseline_id"],
        },
    }


def center_contract_options() -> list[dict[str, Any]]:
    return [
        {
            "center_key": _text(center.get("stable_key")),
            "primary_key": _text(center.get("key")),
            "label": _text(center.get("name")),
            "sequence": int(center.get("sequence") or 10),
        }
        for center in center_identity_contract()["centers"]
    ]


def center_definition(center_key: str) -> dict[str, Any] | None:
    center = center_identity(center_key)
    if not center:
        return None
    return {
        "center_key": _text(center.get("stable_key")),
        "primary_key": _text(center.get("key")),
        "label": _text(center.get("name")),
        "sequence": int(center.get("sequence") or 10),
    }


def normalize_hook_result(policy: dict[str, Any] | None) -> dict[str, Any]:
    """Structured extension-hook payload; errors remain visible to P0 callers."""
    try:
        normalized = normalize_construction_product_policy(policy)
    except ProductCenterPolicyError as exc:
        return {"status": "error", "code": exc.code, "detail": exc.detail}
    except (TypeError, ValueError) as exc:
        return {
            "status": "error",
            "code": "PRODUCT_CENTER_POLICY_INVALID",
            "detail": _text(exc),
        }
    return {"status": "ok", "policy": normalized}


def add_catalog_entry_to_product_policy(
    policy,
    *,
    menu_id: int,
    center_key: str,
    release_state: str = "preview",
) -> dict[str, Any]:
    """Maintain one native entry in an existing product draft."""
    if not policy:
        raise ProductCenterPolicyError(
            "PRODUCT_POLICY_REQUIRED",
            "target product policy does not exist",
        )
    return policy.set_native_menu_publication(
        int(menu_id),
        _text(center_key),
        release_state=_text(release_state) or "preview",
    )
