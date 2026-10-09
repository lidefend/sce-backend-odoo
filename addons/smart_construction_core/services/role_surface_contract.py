# -*- coding: utf-8 -*-
"""Role landing surface projected from the versioned product contract.

The released role landing policy is declarative contract data
(``formal_business_product_menu_policy.v1`` -> ``products[].role_surface``).
This service only projects that data into the P0 role-surface provider slot and
never derives landing behaviour from business facts, user data or code order.

Runtime reads stay fail-safe: when the contract cannot be read the projection
returns no overlay, and the P0 identity resolver still guarantees the
platform-safe landing scene, so a user can never be sent to a scene the
published route authority does not grant.
"""

from __future__ import annotations

from typing import Any

from odoo.addons.smart_construction_core.services.locked_menu_policy_contract import (
    PLATFORM_SAFE_LANDING_SCENE,
    REQUIRED_PRODUCT_KEYS,
    LockedMenuPolicyContractError,
    default_contract_paths,
    load_locked_menu_policy_contract,
    role_landing_candidates,
)

SOURCE_KIND = "formal_product_role_surface_contract_projection"
SOURCE_AUTHORITIES = ("formal_business_product_menu_policy.v1",)
NO_BUSINESS_FACT_AUTHORITY = True
PROVIDER_KEY = "role_surface_contract"

_CACHE: dict[str, Any] = {}


def _contract_stamp() -> tuple | None:
    baseline, checksum = default_contract_paths()
    try:
        baseline_stat = baseline.stat()
        checksum_stat = checksum.stat()
    except OSError:
        return None
    return (
        str(baseline),
        baseline_stat.st_mtime_ns,
        baseline_stat.st_size,
        str(checksum),
        checksum_stat.st_mtime_ns,
        checksum_stat.st_size,
    )


def load_role_surface_contract() -> dict:
    """Load the versioned contract, cached until the contract files change."""
    stamp = _contract_stamp()
    if stamp is not None and _CACHE.get("stamp") == stamp:
        return _CACHE["value"]
    result: dict[str, Any] = {"status": "unavailable", "reason": "contract_files_missing"}
    try:
        contract = load_locked_menu_policy_contract()
        declared: dict[str, list[str]] = {}
        for product_key in REQUIRED_PRODUCT_KEYS:
            for role_code, candidates in role_landing_candidates(contract, product_key).items():
                declared[role_code] = list(candidates)
        result = {
            "status": "ok",
            "sha256": contract.get("sha256"),
            "path": contract.get("path"),
            "roles": declared,
        }
    except LockedMenuPolicyContractError as exc:
        result = {"status": "unavailable", "reason": exc.code, "detail": exc.detail}
    except Exception as exc:  # pragma: no cover - defensive, never break login
        result = {"status": "unavailable", "reason": type(exc).__name__}
    if stamp is not None:
        _CACHE["stamp"] = stamp
        _CACHE["value"] = result
    return result


def apply_contract_role_landing(role_surface_overrides: dict | None) -> tuple[dict, dict]:
    """Overlay the contract-declared landing candidates onto the provider slot.

    Returns the overlaid overrides plus a projection receipt for diagnostics.
    """
    base: dict[str, dict] = {}
    for role_code, role_meta in (role_surface_overrides or {}).items():
        role_key = str(role_code or "").strip()
        if not role_key:
            continue
        base[role_key] = dict(role_meta) if isinstance(role_meta, dict) else {}

    contract = load_role_surface_contract()
    declared = contract.get("roles") if isinstance(contract.get("roles"), dict) else {}
    overlaid: list[str] = []
    for role_code, candidates in declared.items():
        role_key = str(role_code or "").strip()
        if not role_key or not candidates:
            continue
        target = base.setdefault(role_key, {})
        if list(target.get("landing_scene_candidates") or []) != list(candidates):
            target["landing_scene_candidates"] = list(candidates)
            overlaid.append(role_key)

    receipt = {
        "kind": SOURCE_KIND,
        "authorities": list(SOURCE_AUTHORITIES),
        "projection_only": True,
        "no_business_fact_authority": NO_BUSINESS_FACT_AUTHORITY,
        "provider_key": PROVIDER_KEY,
        "contract_status": contract.get("status"),
        "contract_sha256": contract.get("sha256"),
        "contract_reason": contract.get("reason"),
        "declared_role_count": len(declared),
        "overlaid_roles": sorted(overlaid),
        "platform_safe_landing_scene": PLATFORM_SAFE_LANDING_SCENE,
    }
    return base, receipt
