#!/usr/bin/env python3
"""Guarded first-production administrator identity baseline.

The operation consumes the installed identity resolver policy.  It does not
define a second role matrix and it never weakens the restricted-user policy.
"""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any


TARGET_DATABASE = "sc_production"
TARGET_LOGIN = "admin"
EXPECTED_USER_COUNT = 1
EXPECTED_CURRENT_ROLE = "restricted"
EXPECTED_CURRENT_EVIDENCE = "no_authoritative_role"
EXPECTED_ROLE_AFTER = "system_admin"
EXPECTED_EVIDENCE_AFTER = "explicit"
CANONICAL_ROLE_XMLIDS = ("smart_core.group_smart_core_admin",)
FORMAL_MODULE_COUNT = 10
CONFIRMATION = "YES_APPLY_FRESH_PRODUCTION_ADMIN_IDENTITY_BASELINE"
EVIDENCE_ROOT = Path("/opt/sce-runtime/logs")


class AdminIdentityBaselineError(RuntimeError):
    pass


def _mode(active_env: Mapping[str, str]) -> str:
    value = active_env.get("ADMIN_IDENTITY_BASELINE_MODE", "dry-run").strip()
    if value not in {"dry-run", "apply"}:
        raise AdminIdentityBaselineError(
            "ADMIN_IDENTITY_BASELINE_MODE must be dry-run or apply"
        )
    return value


def _formal_modules(active_env: Mapping[str, str]) -> tuple[str, ...]:
    modules = tuple(
        item.strip()
        for item in active_env.get("FORMAL_MODULE_CONTRACT", "").split(",")
        if item.strip()
    )
    if len(modules) != FORMAL_MODULE_COUNT or len(set(modules)) != len(modules):
        raise AdminIdentityBaselineError(
            "FORMAL_MODULE_CONTRACT must contain 10 unique formal modules"
        )
    return modules


def _evidence_path(active_env: Mapping[str, str]) -> Path:
    raw = active_env.get("ADMIN_IDENTITY_EVIDENCE_OUTPUT", "").strip()
    if not raw:
        raise AdminIdentityBaselineError(
            "ADMIN_IDENTITY_EVIDENCE_OUTPUT is required"
        )
    path = Path(raw)
    if not path.is_absolute():
        raise AdminIdentityBaselineError(
            "ADMIN_IDENTITY_EVIDENCE_OUTPUT must be absolute"
        )
    resolved_parent = path.parent.resolve(strict=False)
    if resolved_parent != EVIDENCE_ROOT:
        raise AdminIdentityBaselineError(
            f"ADMIN_IDENTITY_EVIDENCE_OUTPUT must be directly under {EVIDENCE_ROOT}"
        )
    if path.name in {"", ".", ".."}:
        raise AdminIdentityBaselineError("invalid evidence output name")
    return path


def validate_control_plane(active_env: Mapping[str, str]) -> str:
    if active_env.get("ENV") != "prod":
        raise AdminIdentityBaselineError("ENV=prod is required")
    if active_env.get("TARGET_DB") != TARGET_DATABASE:
        raise AdminIdentityBaselineError("TARGET_DB must be sc_production")
    if active_env.get("ADMIN_IDENTITY_LOGIN", TARGET_LOGIN) != TARGET_LOGIN:
        raise AdminIdentityBaselineError("ADMIN_IDENTITY_LOGIN must be admin")
    if active_env.get("ADMIN_IDENTITY_EXPECTED_USER_COUNT", "1") != "1":
        raise AdminIdentityBaselineError(
            "ADMIN_IDENTITY_EXPECTED_USER_COUNT must be 1"
        )
    if (
        active_env.get("ADMIN_IDENTITY_EXPECTED_CURRENT_ROLE", EXPECTED_CURRENT_ROLE)
        != EXPECTED_CURRENT_ROLE
    ):
        raise AdminIdentityBaselineError(
            "ADMIN_IDENTITY_EXPECTED_CURRENT_ROLE must be restricted"
        )
    mode = _mode(active_env)
    _formal_modules(active_env)
    _evidence_path(active_env)
    if mode == "apply":
        if active_env.get("PROD_DANGER") != "1":
            raise AdminIdentityBaselineError("PROD_DANGER=1 is required for apply")
        if active_env.get("CONFIRM_ADMIN_IDENTITY_BASELINE") != CONFIRMATION:
            raise AdminIdentityBaselineError(
                "CONFIRM_ADMIN_IDENTITY_BASELINE="
                f"{CONFIRMATION} is required for apply"
            )
    return mode


def _resolver_factory(odoo_env: Any) -> Any:
    from odoo.addons.smart_core.identity.identity_resolver import IdentityResolver

    return IdentityResolver(odoo_env)


def _role_state(resolver: Any, user: Any) -> dict[str, Any]:
    xmlids = resolver.user_group_xmlids(user)
    role_code, evidence = resolver.resolve_role_code_with_evidence(xmlids)
    surface = resolver.build_role_surface(xmlids, [], {"workspace.home"})
    return {
        "xmlids": xmlids,
        "role_code": role_code,
        "role_evidence": str((evidence or {}).get("source") or ""),
        "matched_groups": sorted((evidence or {}).get("matched_groups") or []),
        "candidate_roles": sorted((evidence or {}).get("candidate_roles") or []),
        "deny_all_navigation": bool(surface.get("deny_all_navigation")),
    }


def _canonical_contract(resolver: Any) -> tuple[set[str], set[str]]:
    explicit = {
        str(role): {str(item) for item in (xmlids or set())}
        for role, xmlids in resolver._role_groups_explicit.items()
    }
    fallback = {
        str(role): {str(item) for item in (xmlids or set())}
        for role, xmlids in resolver._role_groups_capability_fallback.items()
    }
    canonical = explicit.get(EXPECTED_ROLE_AFTER) or set()
    if canonical != set(CANONICAL_ROLE_XMLIDS):
        raise AdminIdentityBaselineError(
            "installed identity policy does not expose the approved singleton "
            "system_admin role contract"
        )
    if not resolver._role_precedence or resolver._role_precedence[0] != EXPECTED_ROLE_AFTER:
        raise AdminIdentityBaselineError(
            "system_admin must remain first in authoritative role precedence"
        )
    authoritative = set().union(*explicit.values(), *fallback.values())
    if any(
        token in xmlid.casefold()
        for xmlid in canonical
        for token in ("demo", "fixture", "portal", "test")
    ):
        raise AdminIdentityBaselineError(
            "canonical role contract contains a forbidden group"
        )
    return canonical, authoritative


def _validate_modules(odoo_env: Any, formal_modules: tuple[str, ...]) -> None:
    modules = odoo_env["ir.module.module"].sudo()
    rows = modules.search([("name", "in", list(formal_modules))])
    state_by_name = {row.name: row.state for row in rows}
    if set(state_by_name) != set(formal_modules):
        raise AdminIdentityBaselineError("formal module inventory is incomplete")
    if any(state != "installed" for state in state_by_name.values()):
        raise AdminIdentityBaselineError("formal modules must be installed 10/10")
    pending = modules.search_count(
        [("state", "in", ["to install", "to upgrade", "to remove"])]
    )
    if pending:
        raise AdminIdentityBaselineError(
            "pending module operations must be zero"
        )


def _target_user(odoo_env: Any) -> Any:
    users = odoo_env["res.users"].sudo().with_context(active_test=False)
    target = users.search([("login", "=", TARGET_LOGIN)])
    if len(target) != EXPECTED_USER_COUNT:
        raise AdminIdentityBaselineError(
            "expected exactly one initial administrator login=admin"
        )
    if not target.active or target.share:
        raise AdminIdentityBaselineError(
            "target must be an active internal user"
        )
    internal_group = odoo_env.ref("base.group_user", raise_if_not_found=False)
    if not internal_group or internal_group.id not in target.groups_id.ids:
        raise AdminIdentityBaselineError(
            "target must have the internal-user base group"
        )
    return target


def _validate_xmlids(odoo_env: Any, canonical: set[str]) -> dict[str, Any]:
    groups: dict[str, Any] = {}
    for xmlid in sorted(canonical):
        group = odoo_env.ref(xmlid, raise_if_not_found=False)
        if not group or getattr(group, "_name", "res.groups") != "res.groups":
            raise AdminIdentityBaselineError(
                f"canonical role XML ID is missing or not a group: {xmlid}"
            )
        groups[xmlid] = group
    return groups


def _safe_snapshot(user: Any) -> dict[str, Any]:
    return {
        "login": user.login,
        "active": bool(user.active),
        "share": bool(user.share),
        "company_id": user.company_id.id,
        "company_ids": tuple(sorted(user.company_ids.ids)),
    }


def _write_evidence(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.exists() or path.is_symlink():
        raise AdminIdentityBaselineError("evidence output must not already exist")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(dict(payload), handle, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def baseline_admin_identity(
    odoo_env: Any,
    active_env: Mapping[str, str],
    *,
    resolver_factory: Callable[[Any], Any] = _resolver_factory,
) -> dict[str, Any]:
    mode = validate_control_plane(active_env)
    if getattr(odoo_env.cr, "dbname", None) != TARGET_DATABASE:
        raise AdminIdentityBaselineError(
            "live database identity must be sc_production"
        )
    formal_modules = _formal_modules(active_env)
    _validate_modules(odoo_env, formal_modules)
    target = _target_user(odoo_env)
    before_snapshot = _safe_snapshot(target)
    resolver = resolver_factory(odoo_env)
    canonical, authoritative = _canonical_contract(resolver)
    canonical_groups = _validate_xmlids(odoo_env, canonical)
    before = _role_state(resolver, target)
    authoritative_hits = before["xmlids"] & authoritative
    unexpected_hits = authoritative_hits - canonical

    if unexpected_hits or before["candidate_roles"]:
        raise AdminIdentityBaselineError(
            "target has unknown, conflicting, or excessive authoritative roles"
        )

    already_applied = authoritative_hits == canonical
    if already_applied:
        if (
            before["role_code"] != EXPECTED_ROLE_AFTER
            or before["role_evidence"] != EXPECTED_EVIDENCE_AFTER
            or before["deny_all_navigation"]
        ):
            raise AdminIdentityBaselineError(
                "canonical group is present but resolved identity is inconsistent"
            )
    elif (
        before["role_code"] != EXPECTED_CURRENT_ROLE
        or before["role_evidence"] != EXPECTED_CURRENT_EVIDENCE
        or not before["deny_all_navigation"]
        or authoritative_hits
    ):
        raise AdminIdentityBaselineError(
            "target is not the approved no_authoritative_role baseline"
        )

    status = "NOOP" if already_applied else ("DRY_RUN" if mode == "dry-run" else "APPLIED")
    after = before
    if mode == "apply" and not already_applied:
        try:
            with odoo_env.cr.savepoint():
                target.write(
                    {
                        "groups_id": [
                            (4, canonical_groups[xmlid].id)
                            for xmlid in sorted(canonical)
                        ]
                    }
                )
                after = _role_state(resolver_factory(odoo_env), target)
                if (
                    after["role_code"] != EXPECTED_ROLE_AFTER
                    or after["role_evidence"] != EXPECTED_EVIDENCE_AFTER
                    or after["deny_all_navigation"]
                    or set(after["matched_groups"]) != canonical
                    or _safe_snapshot(target) != before_snapshot
                ):
                    raise AdminIdentityBaselineError(
                        "post-apply identity or unrelated user fields failed validation"
                    )
            odoo_env.cr.commit()
        except Exception:
            odoo_env.cr.rollback()
            raise
    elif mode == "dry-run":
        odoo_env.cr.rollback()

    payload = {
        "schema_version": "production_admin_identity_baseline.v1",
        "status": status,
        "mode": mode,
        "database": TARGET_DATABASE,
        "login": TARGET_LOGIN,
        "canonical_role_xmlids": sorted(canonical),
        "role_before": before["role_code"],
        "role_evidence_before": before["role_evidence"],
        "deny_all_navigation_before": before["deny_all_navigation"],
        "planned_additions": [] if already_applied else sorted(canonical),
        "role_after": after["role_code"],
        "role_evidence_after": after["role_evidence"],
        "deny_all_navigation_after": after["deny_all_navigation"],
        "unrelated_user_fields_unchanged": _safe_snapshot(target) == before_snapshot,
    }
    _write_evidence(_evidence_path(active_env), payload)
    return payload


def main() -> int:
    try:
        if "env" in globals():
            result = baseline_admin_identity(globals()["env"], os.environ)
            print(
                "[production.admin.identity_baseline] "
                + json.dumps(result, sort_keys=True)
            )
        else:
            mode = validate_control_plane(os.environ)
            print(
                "[production.admin.identity_baseline] PREFLIGHT PASS "
                f"database={TARGET_DATABASE} login={TARGET_LOGIN} mode={mode}"
            )
    except AdminIdentityBaselineError as exc:
        raise SystemExit(
            f"[production.admin.identity_baseline] BLOCKED: {exc}"
        ) from exc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
