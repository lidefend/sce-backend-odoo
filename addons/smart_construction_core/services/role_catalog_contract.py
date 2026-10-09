# -*- coding: utf-8 -*-
"""Product default role catalog projected from the versioned contract.

The shipped default role set and the group binding of every role are
declarative contract data (``formal_business_product_menu_policy.v1`` ->
``role_catalog``).  This service only projects that data into the P0 identity
provider slot.  It never derives a role from business facts, code order or a
user-supplied name, and it never turns a role declaration into an
authorization: the delivered authority stays the intersection of the
declaration with the principal's real group and record-rule visibility.

The catalog is a *default* that a runtime may extend: a role added later binds
to real ``res.groups`` records and is resolved from the same declaration.  A
principal whose real groups match no declared role still fails closed to the
declared synthetic (restricted) role.
"""

from __future__ import annotations

from typing import Any

from odoo.addons.smart_construction_core.services.locked_menu_policy_contract import (
    LockedMenuPolicyContractError,
    default_contract_paths,
    load_locked_menu_policy_contract,
    role_catalog,
    role_catalog_bindings,
    role_catalog_resolution,
)

SOURCE_KIND = "formal_product_role_catalog_contract_projection"
SOURCE_AUTHORITIES = ("formal_business_product_menu_policy.v1",)
NO_BUSINESS_FACT_AUTHORITY = True
PROVIDER_KEY = "role_catalog_contract"

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


def load_role_catalog_contract() -> dict:
    """Project ``role_catalog`` into resolver-ready maps, cached by file stamp."""
    stamp = _contract_stamp()
    if stamp is not None and _CACHE.get("stamp") == stamp:
        return _CACHE["value"]
    result: dict[str, Any] = {"status": "unavailable", "reason": "contract_files_missing"}
    try:
        contract = load_locked_menu_policy_contract()
        catalog = role_catalog(contract)
        resolution = role_catalog_resolution(contract)
        if not catalog or not resolution.get("precedence"):
            result = {"status": "unavailable", "reason": "role_catalog_absent"}
        else:
            result = {
                "status": "ok",
                "sha256": contract.get("sha256"),
                "path": contract.get("path"),
                "catalog_version": resolution.get("catalog_version"),
                "role_precedence": tuple(resolution.get("precedence") or ()),
                "role_groups_explicit": {
                    role: tuple(groups) for role, groups in (resolution.get("bindings") or {}).items()
                },
                "role_groups_capability_fallback": {
                    role: tuple(groups)
                    for role, groups in (resolution.get("capability_groups") or {}).items()
                    if groups
                },
                "role_meta": {
                    role: dict(meta) for role, meta in (resolution.get("metadata") or {}).items()
                },
                "capability_role_codes": tuple(resolution.get("capability_role_codes") or ()),
                "capability_fallback_order": tuple(resolution.get("capability_fallback_order") or ()),
                "synthetic_role_codes": tuple(resolution.get("synthetic_role_codes") or ()),
                "role_count": len(role_catalog_bindings(contract)),
            }
    except LockedMenuPolicyContractError as exc:
        result = {"status": "unavailable", "reason": exc.code, "detail": exc.detail}
    except Exception as exc:  # pragma: no cover - defensive, never break login
        result = {"status": "unavailable", "reason": type(exc).__name__}
    if stamp is not None:
        _CACHE["stamp"] = stamp
        _CACHE["value"] = result
    return result


def _merged_order(declared, base) -> tuple:
    ordered: list[str] = []
    for role in list(declared or ()) + list(base or ()):
        role_key = str(role or "").strip()
        if role_key and role_key not in ordered:
            ordered.append(role_key)
    return tuple(ordered)


def apply_contract_role_catalog(base: dict | None) -> tuple[dict, dict]:
    """Overlay the contract-declared role catalog onto the provider slot.

    Roles declared by the contract are authoritative for their own group
    binding; roles only present in the provider's code declaration are kept so
    a provider can never lose a surface because the contract is narrower.  When
    the contract cannot be read, the code declaration is returned unchanged and
    the receipt records the reason, so login keeps working fail-safe.
    """
    source = base if isinstance(base, dict) else {}
    projected = {
        "role_precedence": tuple(source.get("role_precedence") or ()),
        "role_groups_explicit": {
            str(role): tuple(groups or ()) for role, groups in (source.get("role_groups_explicit") or {}).items()
        },
        "role_groups_capability_fallback": {
            str(role): tuple(groups or ())
            for role, groups in (source.get("role_groups_capability_fallback") or {}).items()
        },
        "role_meta": {str(role): dict(meta or {}) for role, meta in (source.get("role_meta") or {}).items()},
        "capability_role_codes": tuple(source.get("capability_role_codes") or ()),
        "capability_fallback_order": tuple(source.get("capability_fallback_order") or ()),
        "synthetic_role_codes": tuple(source.get("synthetic_role_codes") or ()),
        "role_count": len(source.get("role_precedence") or ()),
    }

    contract = load_role_catalog_contract()
    overlaid: list[str] = []
    if contract.get("status") == "ok":
        projected["role_precedence"] = _merged_order(contract.get("role_precedence"), projected["role_precedence"])
        for role, groups in (contract.get("role_groups_explicit") or {}).items():
            role_key = str(role or "").strip()
            if not role_key or not groups:
                continue
            if tuple(projected["role_groups_explicit"].get(role_key) or ()) != tuple(groups):
                overlaid.append(role_key)
            projected["role_groups_explicit"][role_key] = tuple(groups)
        for role, groups in (contract.get("role_groups_capability_fallback") or {}).items():
            role_key = str(role or "").strip()
            if role_key and groups:
                projected["role_groups_capability_fallback"][role_key] = tuple(groups)
        projected["role_meta"].update(
            {str(role): dict(meta or {}) for role, meta in (contract.get("role_meta") or {}).items()}
        )
        if contract.get("capability_role_codes"):
            projected["capability_role_codes"] = tuple(contract["capability_role_codes"])
        if contract.get("capability_fallback_order"):
            projected["capability_fallback_order"] = tuple(contract["capability_fallback_order"])
        if contract.get("synthetic_role_codes"):
            projected["synthetic_role_codes"] = tuple(contract["synthetic_role_codes"])
        projected["role_count"] = contract.get("role_count") or projected["role_count"]
        # A capability fallback order must never point at an undeclared role.
        declared_explicit = set(projected["role_groups_capability_fallback"])
        projected["capability_fallback_order"] = tuple(
            role for role in projected["capability_fallback_order"] if role in declared_explicit
        )

    receipt = {
        "kind": SOURCE_KIND,
        "authorities": list(SOURCE_AUTHORITIES),
        "projection_only": True,
        "no_business_fact_authority": NO_BUSINESS_FACT_AUTHORITY,
        "provider_key": PROVIDER_KEY,
        "contract_status": contract.get("status"),
        "contract_sha256": contract.get("sha256"),
        "contract_reason": contract.get("reason"),
        "catalog_version": contract.get("catalog_version"),
        "declared_role_count": contract.get("role_count"),
        "overlaid_roles": sorted(overlaid),
    }
    return projected, receipt
