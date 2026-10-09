#!/usr/bin/env python3
"""Single source for the accepted navigation action count.

The acceptance lanes must not pin how many menus the product has.  A menu count
is only determinate once a concrete role is locked, because different roles see
different contracted surfaces.  The policy therefore declares which accepted
role is under test and which versioned contract field is authoritative for that
role (``navigation_policy.action_count_authority``); this module resolves the
count from that declaration, so adding or removing a contracted product entry
(or switching the principal role) is a contract data change rather than an edit
to a release constant.

Mechanism, not number:
  * a policy that pins ``min_actions``/``max_actions``/``action_count`` fails;
  * an authority that is not a versioned contract in exact mode fails;
  * a principal role with no declared authoritative surface fails closed;
  * a role surface whose declared count disagrees with its locked identity list
    fails;
  * an unresolvable or non-positive resolved value fails.
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/frontend/acceptance_environments_v1.json"
PINNED_COUNT_KEYS = ("min_actions", "max_actions", "action_count")

# A role that discovers its installed capability surface has no enumerated
# locked navigation list; its authoritative count is the versioned product
# contract's declared surface size.
SURFACE_KIND_INSTALLED_CAPABILITY = "installed_capability_surface"
# A role with an explicitly locked released-position list; its authoritative
# count is the length of that list, cross-checked against the declared count.
SURFACE_KIND_LOCKED_ROLE_MANIFEST = "locked_role_navigation_manifest"


class ActionCountAuthorityError(ValueError):
    """Raised when the accepted action count cannot be resolved from contract data."""


def _resolve_contract_field(contract: dict, field_path: str) -> int:
    value: object = contract
    for part in field_path.split("."):
        if not isinstance(value, dict) or part not in value:
            raise ActionCountAuthorityError(f"action_count_authority field not found: {field_path}")
        value = value[part]
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ActionCountAuthorityError(f"action_count_authority resolved a non-positive count: {value!r}")
    return value


def _load_json(base: Path, rel_path: str, what: str) -> dict:
    try:
        return json.loads((base / rel_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ActionCountAuthorityError(f"{what} unreadable: {rel_path} ({exc})") from exc


def _resolve_role_surface(entry: object, role: str, base: Path) -> int:
    if not isinstance(entry, dict):
        raise ActionCountAuthorityError(f"role surface for {role!r} must be an object")
    kind = entry.get("kind")
    if kind == SURFACE_KIND_INSTALLED_CAPABILITY:
        path = str(entry.get("path") or "").strip()
        field = str(entry.get("field") or "").strip()
        if not path or not field:
            raise ActionCountAuthorityError(f"installed capability surface for {role!r} requires path and field")
        return _resolve_contract_field(_load_json(base, path, f"capability contract for {role!r}"), field)
    if kind == SURFACE_KIND_LOCKED_ROLE_MANIFEST:
        path = str(entry.get("path") or "").strip()
        roles_field = str(entry.get("roles_field") or "").strip()
        count_field = str(entry.get("count_field") or "").strip()
        identity_field = str(entry.get("identity_field") or "").strip()
        if not path or not roles_field or not count_field or not identity_field:
            raise ActionCountAuthorityError(
                f"locked role manifest for {role!r} requires path, roles_field, count_field, identity_field"
            )
        manifest = _load_json(base, path, f"locked role manifest for {role!r}")
        roles = manifest.get(roles_field)
        lookup_role = str(entry.get("manifest_role") or role).strip()
        if not isinstance(roles, dict) or lookup_role not in roles or not isinstance(roles.get(lookup_role), dict):
            raise ActionCountAuthorityError(f"locked role manifest has no locked surface for role {role!r}")
        row = roles[lookup_role]
        identities = row.get(identity_field)
        if not isinstance(identities, list) or not identities:
            raise ActionCountAuthorityError(f"locked role manifest surface for {role!r} has no identity list")
        identity_count = len({str(item).split("|", 1)[0].strip() for item in identities if str(item).strip()})
        declared = row.get(count_field)
        if not isinstance(declared, int) or isinstance(declared, bool):
            raise ActionCountAuthorityError(f"locked role manifest surface for {role!r} has no declared count")
        if declared != identity_count:
            raise ActionCountAuthorityError(
                f"locked role manifest for {role!r}: declared {count_field}={declared} != locked identity count {identity_count}"
            )
        if identity_count <= 0:
            raise ActionCountAuthorityError(f"locked role manifest surface for {role!r} resolves a non-positive count")
        return identity_count
    raise ActionCountAuthorityError(f"unsupported role surface kind for {role!r}: {kind!r}")


def resolve_action_count(policy: dict, root: Path | None = None, principal_role: str | None = None) -> int:
    """Resolve the accepted action count from the declared contract authority."""
    base = root or ROOT
    navigation = (policy or {}).get("navigation_policy")
    if not isinstance(navigation, dict):
        raise ActionCountAuthorityError("daily navigation_policy must be an object")
    for pinned in PINNED_COUNT_KEYS:
        if pinned in navigation:
            raise ActionCountAuthorityError(
                f"daily navigation_policy must not pin a numeric menu count ({pinned})"
            )
    authority = navigation.get("action_count_authority")
    if not isinstance(authority, dict):
        raise ActionCountAuthorityError("daily navigation_policy must declare action_count_authority")
    if authority.get("kind") != "versioned_contract" or authority.get("mode") != "exact":
        raise ActionCountAuthorityError(
            "action_count_authority must be a versioned_contract in exact mode"
        )
    scope = authority.get("scope")
    if scope == "locked_role_surface":
        role = str(principal_role or authority.get("principal_role") or "").strip()
        if not role:
            raise ActionCountAuthorityError(
                "locked_role_surface authority must declare the locked principal_role under test"
            )
        surfaces = authority.get("role_surfaces")
        if not isinstance(surfaces, dict):
            raise ActionCountAuthorityError("locked_role_surface authority must declare role_surfaces")
        if role not in surfaces:
            raise ActionCountAuthorityError(
                f"principal role {role!r} has no declared authoritative navigation surface"
            )
        return _resolve_role_surface(surfaces[role], role, base)
    # Legacy single-surface authority: one contract field for the whole product.
    contract_path = str(authority.get("path") or "").strip()
    field_path = str(authority.get("field") or "").strip()
    if not contract_path or not field_path:
        raise ActionCountAuthorityError("action_count_authority requires path and field")
    return _resolve_contract_field(_load_json(base, contract_path, "action_count_authority contract"), field_path)


def resolve_daily_principal_role(root: Path | None = None) -> str:
    """Resolve the declared principal role for the daily acceptance profile."""
    base = root or ROOT
    policy = _load_json(base, "config/frontend/acceptance_environments_v1.json", "acceptance policy")
    authority = (((policy.get("profiles") or {}).get("daily") or {}).get("navigation_policy") or {}).get(
        "action_count_authority"
    )
    if not isinstance(authority, dict):
        raise ActionCountAuthorityError("daily navigation_policy must declare action_count_authority")
    role = str(authority.get("principal_role") or "").strip()
    if not role:
        raise ActionCountAuthorityError("daily action_count_authority must declare principal_role")
    return role


def resolve_daily_action_count(root: Path | None = None) -> int:
    """Resolve the daily profile's accepted action count for its locked principal role."""
    base = root or ROOT
    policy = _load_json(base, "config/frontend/acceptance_environments_v1.json", "acceptance policy")
    return resolve_action_count(
        (policy.get("profiles") or {}).get("daily") or {},
        base,
        principal_role=resolve_daily_principal_role(base),
    )


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Resolve the accepted navigation action count from contract data.")
    parser.add_argument(
        "--role",
        action="store_true",
        help="print the locked principal role under test instead of the resolved count",
    )
    args = parser.parse_args(argv)
    print(resolve_daily_principal_role() if args.role else resolve_daily_action_count())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
