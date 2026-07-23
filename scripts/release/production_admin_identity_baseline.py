#!/usr/bin/env python3
"""Guarded first-production administrator identity baseline.

Dry-run is protected by a PostgreSQL read-only transaction before any target
identity or formal-state query.  The planned identity is computed by the same
installed identity resolver used at runtime; it is never simulated by writing
and rolling back production data.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import tempfile
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
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
DEPLOYMENT_ROOT = Path("/opt/sce/deployment-tools")
DEPLOYMENT_METADATA_NAME = "deployment-tool-metadata.json"
PLANNED_WRITE_MODEL = "res_users_groups_rel"
PRODUCT_FINGERPRINT_MODELS = (
    "sc.product.policy",
    "ui.business.config.contract",
)
RUN_ID_PATTERN = re.compile(r"^[0-9]{8}T[0-9]{6}Z-[a-z0-9]{6,32}$")
SOURCE_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
EVIDENCE_SCHEMA_VERSION = "admin-identity-baseline-evidence-v3"


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
    if path.exists() or path.is_symlink():
        raise AdminIdentityBaselineError(
            "evidence output must be a new non-symlink path"
        )
    return path


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _execution_binding(
    active_env: Mapping[str, str], mode: str
) -> dict[str, Any]:
    run_id = active_env.get("ADMIN_IDENTITY_RUN_ID", "")
    if not RUN_ID_PATTERN.fullmatch(run_id):
        raise AdminIdentityBaselineError(
            "ADMIN_IDENTITY_RUN_ID must be UTC timestamp plus safe random suffix"
        )
    source_sha = active_env.get("ADMIN_IDENTITY_TOOL_SOURCE_SHA", "")
    if not SOURCE_SHA_PATTERN.fullmatch(source_sha):
        raise AdminIdentityBaselineError(
            "ADMIN_IDENTITY_TOOL_SOURCE_SHA must be 40 lowercase hexadecimal characters"
        )
    raw_deployed_path = active_env.get("ADMIN_IDENTITY_DEPLOYED_PATH", "")
    if not raw_deployed_path or not Path(raw_deployed_path).is_absolute():
        raise AdminIdentityBaselineError(
            "ADMIN_IDENTITY_DEPLOYED_PATH must be an absolute versioned path"
        )
    deployed_path = Path(raw_deployed_path)
    if deployed_path.is_symlink():
        raise AdminIdentityBaselineError("deployed tool path must not be a symlink")
    try:
        resolved_path = deployed_path.resolve(strict=True)
        resolved_root = DEPLOYMENT_ROOT.resolve(strict=True)
    except OSError as exc:
        raise AdminIdentityBaselineError(
            "deployed tool path or deployment root is unavailable"
        ) from exc
    if (
        resolved_path != deployed_path
        or resolved_path.parent != resolved_root
        or resolved_path.name != source_sha
    ):
        raise AdminIdentityBaselineError(
            "source SHA, deployed directory, and deployment root do not match"
        )

    marker = resolved_path / "DEPLOYMENT_TOOL_SHA"
    metadata_path = resolved_path / DEPLOYMENT_METADATA_NAME
    script_path = resolved_path / "scripts/release/production_admin_identity_baseline.py"
    release_mk_path = resolved_path / "make/release.mk"
    for candidate in (marker, metadata_path, script_path, release_mk_path):
        if (
            not candidate.is_file()
            or candidate.is_symlink()
            or not stat.S_ISREG(candidate.stat().st_mode)
        ):
            raise AdminIdentityBaselineError(
                f"deployed tool identity file is missing or unsafe: {candidate.name}"
            )
    if marker.read_text(encoding="utf-8").strip() != source_sha:
        raise AdminIdentityBaselineError("deployment source marker does not match")
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AdminIdentityBaselineError("deployment metadata is invalid") from exc
    required_metadata = {
        "schema_version": "admin-identity-tool-deployment.v1",
        "source_sha": source_sha,
    }
    if any(metadata.get(key) != value for key, value in required_metadata.items()):
        raise AdminIdentityBaselineError("deployment metadata identity does not match")
    script_sha256 = _sha256_file(script_path)
    release_mk_sha256 = _sha256_file(release_mk_path)
    if metadata.get("script_sha256") != script_sha256:
        raise AdminIdentityBaselineError("deployed script digest does not match metadata")
    if metadata.get("release_mk_sha256") != release_mk_sha256:
        raise AdminIdentityBaselineError(
            "deployed release.mk digest does not match metadata"
        )

    evidence_path = _evidence_path(active_env)
    expected_name = re.compile(
        rf"^admin-identity-baseline-{re.escape(run_id)}-"
        rf"{re.escape(mode)}(?:-[a-z0-9-]+)?\.json$"
    )
    if not expected_name.fullmatch(evidence_path.name):
        raise AdminIdentityBaselineError(
            "evidence filename must bind the exact run ID and execution mode"
        )
    return {
        "run_id": run_id,
        "source_sha": source_sha,
        "deployed_path": str(resolved_path),
        "script_sha256": script_sha256,
        "release_mk_sha256": release_mk_sha256,
    }


def _validated_control_plane(
    active_env: Mapping[str, str],
) -> tuple[str, dict[str, Any]]:
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
    binding = _execution_binding(active_env, mode)
    if mode == "apply":
        if active_env.get("PROD_DANGER") != "1":
            raise AdminIdentityBaselineError("PROD_DANGER=1 is required for apply")
        if active_env.get("CONFIRM_ADMIN_IDENTITY_BASELINE") != CONFIRMATION:
            raise AdminIdentityBaselineError(
                "CONFIRM_ADMIN_IDENTITY_BASELINE="
                f"{CONFIRMATION} is required for apply"
            )
    return mode, binding


def validate_control_plane(active_env: Mapping[str, str]) -> str:
    mode, _binding = _validated_control_plane(active_env)
    return mode


def _resolver_factory(odoo_env: Any) -> Any:
    from odoo.addons.smart_core.identity.identity_resolver import IdentityResolver

    return IdentityResolver(odoo_env)


def _enable_dry_run_read_only(odoo_env: Any) -> dict[str, str]:
    """Enable database-enforced safety before any target/business query."""
    try:
        # Odoo shell has already created an Environment.  End any initialization
        # transaction so the control can be the first statement of the business
        # transaction governed by this tool.
        odoo_env.cr.rollback()
        odoo_env.cr.execute("SET TRANSACTION READ ONLY")
        odoo_env.cr.execute("SHOW transaction_read_only")
        value = str((odoo_env.cr.fetchone() or ("",))[0]).casefold()
    except Exception as exc:
        raise AdminIdentityBaselineError(
            "cannot establish the dry-run read-only transaction"
        ) from exc
    if value != "on":
        raise AdminIdentityBaselineError(
            "transaction_read_only must be verified as on"
        )
    try:
        odoo_env.flush_all()
    except Exception as exc:
        raise AdminIdentityBaselineError(
            "dry-run environment contains an unexpected pending write"
        ) from exc
    return {"transaction_read_only": value, "verification": "PASS"}


def _role_state_for_xmlids(resolver: Any, xmlids: set[str]) -> dict[str, Any]:
    role_code, evidence = resolver.resolve_role_code_with_evidence(set(xmlids))
    surface = resolver.build_role_surface(set(xmlids), [], {"workspace.home"})
    return {
        "xmlids": set(xmlids),
        "role_code": role_code,
        "role_evidence": str((evidence or {}).get("source") or ""),
        "matched_groups": sorted((evidence or {}).get("matched_groups") or []),
        "candidate_roles": sorted((evidence or {}).get("candidate_roles") or []),
        "deny_all_navigation": bool(surface.get("deny_all_navigation")),
    }


def _role_state(resolver: Any, user: Any) -> dict[str, Any]:
    return _role_state_for_xmlids(resolver, resolver.user_group_xmlids(user))


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


def _validate_modules(
    odoo_env: Any, formal_modules: tuple[str, ...]
) -> dict[str, Any]:
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
        raise AdminIdentityBaselineError("pending module operations must be zero")
    return {"states": dict(sorted(state_by_name.items())), "pending": pending}


def _target_user(odoo_env: Any) -> Any:
    users = odoo_env["res.users"].sudo().with_context(active_test=False)
    target = users.search([("login", "=", TARGET_LOGIN)])
    if len(target) != EXPECTED_USER_COUNT:
        raise AdminIdentityBaselineError(
            "expected exactly one initial administrator login=admin"
        )
    if not target.active or target.share:
        raise AdminIdentityBaselineError("target must be an active internal user")
    internal_group = odoo_env.ref("base.group_user", raise_if_not_found=False)
    if not internal_group or internal_group.id not in target.groups_id.ids:
        raise AdminIdentityBaselineError("target must have the internal-user base group")
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
        "internal": not bool(user.share),
        "share": bool(user.share),
        "company_id": user.company_id.id,
        "company_ids": tuple(sorted(user.company_ids.ids)),
    }


def _digest(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), default=str
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _configuration_summary(odoo_env: Any) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    available = set(getattr(getattr(odoo_env, "registry", None), "models", {}))
    for model_name in PRODUCT_FINGERPRINT_MODELS:
        if model_name not in available:
            summary[model_name] = {"available": False}
            continue
        model = odoo_env[model_name].sudo()
        fields = getattr(model, "_fields", {})
        row = {"available": True, "count": model.search_count([])}
        if "active" in fields:
            row["active_count"] = model.search_count([("active", "=", True)])
        summary[model_name] = row
    return summary


def _fingerprint(
    odoo_env: Any,
    user: Any,
    role_state: Mapping[str, Any],
    authoritative: set[str],
    module_state: Mapping[str, Any],
) -> dict[str, Any]:
    user_summary = _safe_snapshot(user)
    user_summary["authoritative_group_xmlids"] = sorted(
        set(role_state["xmlids"]) & authoritative
    )
    user_summary["role_code"] = role_state["role_code"]
    user_summary["role_evidence"] = role_state["role_evidence"]
    user_summary["deny_all_navigation"] = role_state["deny_all_navigation"]
    menu_model = odoo_env["ir.ui.menu"].sudo()
    menu_summary = {
        "count": menu_model.search_count([]),
        "active_count": menu_model.search_count([("active", "=", True)]),
    }
    product_summary = _configuration_summary(odoo_env)
    return {
        "user_sha256": _digest(user_summary),
        "formal_modules_sha256": _digest(module_state),
        "menu_definition": menu_summary,
        "menu_definition_sha256": _digest(menu_summary),
        "product_configuration": product_summary,
        "product_configuration_sha256": _digest(product_summary),
    }


def _state_evidence(
    role_state: Mapping[str, Any],
    *,
    canonical_relation_present: bool,
) -> dict[str, Any]:
    evidence = role_state["role_evidence"]
    matched = list(role_state["matched_groups"])
    rendered_evidence = (
        f"{evidence}:{','.join(matched)}" if matched else str(evidence)
    )
    return {
        "role_code": role_state["role_code"],
        "role_evidence": rendered_evidence,
        "deny_all_navigation": role_state["deny_all_navigation"],
        "canonical_relation_present": canonical_relation_present,
    }


def _write_evidence(path: Path, payload: Mapping[str, Any]) -> None:
    if not verify_payload_digest(payload):
        raise AdminIdentityBaselineError(
            "evidence payload digest must be valid before publication"
        )
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.exists() or path.is_symlink():
        raise AdminIdentityBaselineError("evidence output must not already exist")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=path.parent
    )
    temporary = Path(temporary_name)
    published = False
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(dict(payload), handle, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        temporary_stat = temporary.lstat()
        persisted = json.loads(temporary.read_text(encoding="utf-8"))
        if (
            not stat.S_ISREG(temporary_stat.st_mode)
            or stat.S_IMODE(temporary_stat.st_mode) != 0o600
            or temporary_stat.st_uid != os.geteuid()
            or not verify_payload_digest(persisted)
        ):
            raise AdminIdentityBaselineError(
                "temporary evidence integrity, ownership, or mode is unsafe"
            )
        os.replace(temporary, path)
        published = True
        final_stat = path.lstat()
        if (
            not stat.S_ISREG(final_stat.st_mode)
            or stat.S_IMODE(final_stat.st_mode) != 0o600
            or final_stat.st_uid != os.geteuid()
        ):
            raise AdminIdentityBaselineError(
                "final evidence ownership or mode is unsafe"
            )
        final_payload = json.loads(path.read_text(encoding="utf-8"))
        if not verify_payload_digest(final_payload):
            raise AdminIdentityBaselineError(
                "persisted evidence payload digest is invalid"
            )
    except Exception:
        temporary.unlink(missing_ok=True)
        if published:
            path.unlink(missing_ok=True)
        raise
    finally:
        temporary.unlink(missing_ok=True)


def _apply_canonical_relation(
    target: Any,
    canonical: set[str],
    canonical_groups: Mapping[str, Any],
    write_audit: dict[str, int],
) -> None:
    write_audit["orm_write_method_count"] += 1
    write_audit["database_write_statement_count"] += 1
    target.write(
        {
            "groups_id": [
                (4, canonical_groups[xmlid].id)
                for xmlid in sorted(canonical)
            ]
        }
    )
    write_audit["relation_rows_added"] += len(canonical)


def _payload_digest(payload: Mapping[str, Any]) -> str:
    core = {key: value for key, value in payload.items() if key != "integrity"}
    return _digest(core)


def verify_payload_digest(payload: Mapping[str, Any]) -> bool:
    integrity = payload.get("integrity")
    return bool(
        isinstance(integrity, Mapping)
        and integrity.get("algorithm") == "sha256"
        and integrity.get("coverage") == "canonical-json-excluding-integrity"
        and integrity.get("payload_sha256") == _payload_digest(payload)
    )


def baseline_admin_identity(
    odoo_env: Any,
    active_env: Mapping[str, str],
    *,
    resolver_factory: Callable[[Any], Any] = _resolver_factory,
) -> dict[str, Any]:
    mode, binding = _validated_control_plane(active_env)
    started_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    if getattr(odoo_env.cr, "dbname", None) != TARGET_DATABASE:
        raise AdminIdentityBaselineError(
            "live database identity must be sc_production"
        )

    transaction = {
        "transaction_read_only": "not_applicable",
        "verification": "NOT_APPLICABLE",
    }
    if mode == "dry-run":
        transaction = _enable_dry_run_read_only(odoo_env)

    formal_modules = _formal_modules(active_env)
    module_state = _validate_modules(odoo_env, formal_modules)
    target = _target_user(odoo_env)
    before_snapshot = _safe_snapshot(target)
    resolver = resolver_factory(odoo_env)
    canonical, authoritative = _canonical_contract(resolver)
    canonical_groups = _validate_xmlids(odoo_env, canonical)
    current = _role_state(resolver, target)
    authoritative_hits = current["xmlids"] & authoritative
    unexpected_hits = authoritative_hits - canonical

    if unexpected_hits or current["candidate_roles"]:
        raise AdminIdentityBaselineError(
            "target has unknown, conflicting, or excessive authoritative roles"
        )

    already_applied = authoritative_hits == canonical
    if already_applied:
        if (
            current["role_code"] != EXPECTED_ROLE_AFTER
            or current["role_evidence"] != EXPECTED_EVIDENCE_AFTER
            or current["deny_all_navigation"]
        ):
            raise AdminIdentityBaselineError(
                "canonical group is present but resolved identity is inconsistent"
            )
    elif (
        current["role_code"] != EXPECTED_CURRENT_ROLE
        or current["role_evidence"] != EXPECTED_CURRENT_EVIDENCE
        or not current["deny_all_navigation"]
        or authoritative_hits
    ):
        raise AdminIdentityBaselineError(
            "target is not the approved no_authoritative_role baseline"
        )

    planned_xmlids = set(current["xmlids"]) | canonical
    expected_after = _role_state_for_xmlids(resolver, planned_xmlids)
    if (
        expected_after["role_code"] != EXPECTED_ROLE_AFTER
        or expected_after["role_evidence"] != EXPECTED_EVIDENCE_AFTER
        or expected_after["deny_all_navigation"]
        or set(expected_after["matched_groups"]) != canonical
    ):
        raise AdminIdentityBaselineError(
            "shared identity policy does not produce the approved planned state"
        )

    append_count = 0 if already_applied else len(canonical)
    plan = {
        "action": "NOOP" if already_applied else "ADD_MISSING_CANONICAL_ROLE",
        "canonical_role_xmlid": CANONICAL_ROLE_XMLIDS[0],
        "canonical_role_record_present": True,
        "canonical_relation_present_before": already_applied,
        "planned_write_model": PLANNED_WRITE_MODEL,
        "planned_relation_append_count": append_count,
        "planned_unrelated_write_count": 0,
    }
    before_fingerprint = _fingerprint(
        odoo_env, target, current, authoritative, module_state
    )
    write_audit = {
        "database_write_statement_count": 0,
        "orm_write_method_count": 0,
        "relation_rows_added": 0,
    }

    status = "NOOP" if already_applied else (
        "DRY_RUN" if mode == "dry-run" else "APPLIED"
    )
    observed_after = current
    if mode == "apply" and not already_applied:
        try:
            with odoo_env.cr.savepoint():
                _apply_canonical_relation(
                    target, canonical, canonical_groups, write_audit
                )
                observed_after = _role_state(resolver_factory(odoo_env), target)
                if (
                    observed_after["role_code"] != EXPECTED_ROLE_AFTER
                    or observed_after["role_evidence"] != EXPECTED_EVIDENCE_AFTER
                    or observed_after["deny_all_navigation"]
                    or set(observed_after["matched_groups"]) != canonical
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
        try:
            odoo_env.flush_all()
        except Exception as exc:
            raise AdminIdentityBaselineError(
                "dry-run encountered an unexpected ORM flush write"
            ) from exc
        observed_after = _role_state(resolver_factory(odoo_env), target)
        if observed_after != current or _safe_snapshot(target) != before_snapshot:
            raise AdminIdentityBaselineError(
                "dry-run observed state changed inside the read-only transaction"
            )

    after_fingerprint = _fingerprint(
        odoo_env, target, observed_after, authoritative, module_state
    )
    fingerprints_unchanged = before_fingerprint == after_fingerprint
    if mode == "dry-run" and not fingerprints_unchanged:
        raise AdminIdentityBaselineError("dry-run state fingerprints changed")

    completed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    payload = {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "result": "PASS",
        "status": status,
        "mode": mode,
        "execution": {
            "run_id": binding["run_id"],
            "mode": mode,
            "started_at_utc": started_at,
            "completed_at_utc": completed_at,
        },
        "tool": {
            "source_sha": binding["source_sha"],
            "deployed_path": binding["deployed_path"],
            "script_sha256": binding["script_sha256"],
            "release_mk_sha256": binding["release_mk_sha256"],
        },
        "target": {
            "database": TARGET_DATABASE,
            "login_fingerprint": _digest({"login": TARGET_LOGIN}),
            "expected_user_count": EXPECTED_USER_COUNT,
        },
        "database": {
            "name": TARGET_DATABASE,
            "formal_module_count": len(module_state["states"]),
            "pending_module_operations": module_state["pending"],
        },
        "subject": {
            "login": TARGET_LOGIN,
            "active": bool(target.active),
            "internal": not bool(target.share),
            "share": bool(target.share),
            "allowed_company_count": len(target.company_ids.ids),
            "company_identity_sha256": _digest(
                {
                    "current": target.company_id.id,
                    "allowed": sorted(target.company_ids.ids),
                }
            ),
        },
        "transaction": transaction,
        "current": _state_evidence(
            current, canonical_relation_present=already_applied
        ),
        "plan": plan,
        "expected_after_apply": _state_evidence(
            expected_after, canonical_relation_present=True
        ),
        "observed_after_dry_run": (
            _state_evidence(
                observed_after, canonical_relation_present=already_applied
            )
            if mode == "dry-run"
            else None
        ),
        "write_audit": {
            **write_audit,
            "database_transaction_read_only": (
                "PASS" if mode == "dry-run" else "NOT_APPLICABLE"
            ),
            "database_changed": mode == "apply" and not already_applied,
        },
        "fingerprints": {
            "before": before_fingerprint,
            "after_observed": after_fingerprint,
            "unchanged": fingerprints_unchanged,
        },
        "unrelated_user_fields_unchanged": _safe_snapshot(target) == before_snapshot,
    }
    payload["integrity"] = {
        "algorithm": "sha256",
        "coverage": "canonical-json-excluding-integrity",
        "payload_sha256": _payload_digest(payload),
    }
    if mode == "dry-run":
        odoo_env.cr.rollback()
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
