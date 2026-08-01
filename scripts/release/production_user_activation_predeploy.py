#!/usr/bin/env python3
"""Governed RC12 production activation-baseline plan, apply, and verification.

The only database mutations permitted by this tool are two runtime parameters
and one activation-administrator group relation.  Plan and verify modes make
the PostgreSQL transaction read-only before the first ORM query.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import os
import re
import stat
import tempfile
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TARGET_DATABASE = "sc_production"
TARGET_TAG = "v1.0.0-rc.12"
TARGET_COMMIT = "3fb17948feacb34c2574668eaba7ddb2ad4bef26"
TARGET_DIGEST = "sha256:cecdeb03ea68a1d2ddead0cf3f3ffb7a391948ba7de92e3919b752b7635d3a1d"
DEPLOYMENT_ID = "rc12_upgrade_20260801"
TARGET_ADMIN_LOGIN = "admin"
GROUP_XMLID = "smart_core.group_smart_core_user_activation_admin"
TENANT_PARAMETER = "sc.runtime.tenant_key"
ENVIRONMENT_PARAMETER = "sc.runtime.environment_type"
TARGET_ENVIRONMENT = "production"
APPROVED_FORMAL_USERS = 62
TECHNICALLY_ELIGIBLE_USERS_TOTAL = 76
ADDITIONAL_ELIGIBLE_USERS = 14
TOKEN_TTL_HOURS = 24
CONFIRMATION = "YES_APPLY_PRODUCTION_USER_ACTIVATION_PREDEPLOY_BASELINE"
EVIDENCE_ROOT = Path("/opt/sce-runtime/logs")
DEPLOYMENT_ROOT = Path("/opt/sce/deployment-tools")
RUN_ID_PATTERN = re.compile(r"^[0-9]{8}T[0-9]{6}Z-[a-z0-9]{6,32}$")
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
TENANT_PATTERN = re.compile(r"^[a-z][a-z0-9_]{2,62}$")
SCHEMA_VERSION = "production-user-activation-predeploy.v1"


class ActivationPredeployError(RuntimeError):
    pass


def _digest(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _plan_digest(plan: Mapping[str, Any]) -> str:
    return _digest(
        {
            key: value
            for key, value in plan.items()
            if key not in {"plan_sha256", "transaction"}
        }
    )


def _mode(active_env: Mapping[str, str]) -> str:
    mode = active_env.get("USER_ACTIVATION_PREDEPLOY_MODE", "").strip()
    if mode not in {"plan", "apply", "verify"}:
        raise ActivationPredeployError("mode must be plan, apply, or verify")
    return mode


def _evidence_path(active_env: Mapping[str, str], mode: str) -> Path:
    run_id = active_env.get("USER_ACTIVATION_PREDEPLOY_RUN_ID", "")
    if not RUN_ID_PATTERN.fullmatch(run_id):
        raise ActivationPredeployError("run ID must be a UTC timestamp plus safe suffix")
    raw = active_env.get("USER_ACTIVATION_PREDEPLOY_OUTPUT", "").strip()
    path = Path(raw)
    if not raw or not path.is_absolute() or path.parent.resolve(strict=False) != EVIDENCE_ROOT:
        raise ActivationPredeployError(f"evidence must be directly under {EVIDENCE_ROOT}")
    if path.name != f"user-activation-predeploy-{run_id}-{mode}.json":
        raise ActivationPredeployError("evidence filename must bind run ID and mode")
    if path.exists() or path.is_symlink():
        raise ActivationPredeployError("evidence output must be a new non-symlink path")
    return path


def _tool_binding(active_env: Mapping[str, str]) -> dict[str, str]:
    source_sha = active_env.get("USER_ACTIVATION_PREDEPLOY_TOOL_SOURCE_SHA", "")
    deployed_raw = active_env.get("USER_ACTIVATION_PREDEPLOY_DEPLOYED_PATH", "")
    if not SHA_PATTERN.fullmatch(source_sha) or not deployed_raw:
        raise ActivationPredeployError("immutable deployment-tool identity is required")
    deployed = Path(deployed_raw)
    try:
        resolved = deployed.resolve(strict=True)
        root = DEPLOYMENT_ROOT.resolve(strict=True)
    except OSError as exc:
        raise ActivationPredeployError("deployment-tool path is unavailable") from exc
    marker = resolved / "DEPLOYMENT_TOOL_SHA"
    script = resolved / "scripts/release/production_user_activation_predeploy.py"
    if (
        deployed.is_symlink()
        or resolved != deployed
        or resolved.parent != root
        or resolved.name != source_sha
        or not marker.is_file()
        or marker.is_symlink()
        or marker.read_text(encoding="utf-8").strip() != source_sha
        or not script.is_file()
        or script.is_symlink()
    ):
        raise ActivationPredeployError("deployment-tool identity differs")
    script_sha256 = hashlib.sha256(script.read_bytes()).hexdigest()
    expected_script_sha256 = active_env.get(
        "USER_ACTIVATION_PREDEPLOY_SCRIPT_SHA256", ""
    )
    if expected_script_sha256 != script_sha256:
        raise ActivationPredeployError("deployed predeploy script digest differs")
    return {
        "source_sha": source_sha,
        "deployed_path": str(resolved),
        "script_sha256": script_sha256,
    }


def validate_control_plane(active_env: Mapping[str, str]) -> tuple[str, Path, dict[str, str]]:
    mode = _mode(active_env)
    required = {
        "ENV": "prod",
        "TARGET_DB": TARGET_DATABASE,
        "TARGET_TAG": TARGET_TAG,
        "TARGET_COMMIT": TARGET_COMMIT,
        "REGISTRY_DIGEST": TARGET_DIGEST,
        "DEPLOYMENT_ID": DEPLOYMENT_ID,
        "ACTIVATION_ADMIN_LOGIN": TARGET_ADMIN_LOGIN,
    }
    for key, expected in required.items():
        if active_env.get(key) != expected:
            raise ActivationPredeployError(f"{key} must equal the frozen RC12 contract")
    tenant_key = active_env.get("TENANT_KEY", "")
    if not TENANT_PATTERN.fullmatch(tenant_key):
        raise ActivationPredeployError("TENANT_KEY is missing or invalid")
    if mode in {"plan", "verify"}:
        if active_env.get("PROD_READONLY_VERIFY") != "1":
            raise ActivationPredeployError("PROD_READONLY_VERIFY=1 is required")
    else:
        if active_env.get("PROD_DANGER") != "1" or active_env.get(
            "CONFIRM_USER_ACTIVATION_PREDEPLOY"
        ) != CONFIRMATION:
            raise ActivationPredeployError("exact production apply authorization is required")
    return mode, _evidence_path(active_env, mode), _tool_binding(active_env)


def _enable_read_only(odoo_env: Any) -> dict[str, str]:
    odoo_env.cr.rollback()
    odoo_env.cr.execute("SET TRANSACTION READ ONLY")
    odoo_env.cr.execute("SHOW transaction_read_only")
    value = str((odoo_env.cr.fetchone() or ("",))[0]).strip().lower()
    if value not in {"on", "true", "1"}:
        raise ActivationPredeployError("transaction_read_only is not on")
    return {"transaction_read_only": "on", "verification": "PASS"}


def _installed_capabilities(odoo_env: Any) -> dict[str, Any]:
    from odoo.addons.smart_core.models import user_activation as activation
    from odoo.addons.smart_construction_core.controllers.auth_signup import ScAuthSignup

    registry = getattr(odoo_env, "registry", None)
    models = set(getattr(registry, "models", {}))
    if "sc.user.activation.credential" not in models:
        raise ActivationPredeployError("BLOCKED_RC12_CAPABILITY_MISSING")
    credential = odoo_env["sc.user.activation.credential"].sudo()
    fields = set(credential._fields)
    issue_source = inspect.getsource(activation.ScUserActivationCredential._issue_once)
    begin_source = inspect.getsource(activation.ScUserActivationCredential._begin_activation)
    complete_source = inspect.getsource(activation.ScUserActivationCredential._complete_activation)
    binding_source = inspect.getsource(
        activation.ScUserActivationCredential._runtime_binding_is_current
    )
    signup_source = inspect.getsource(ScAuthSignup)
    group = odoo_env.ref(GROUP_XMLID, raise_if_not_found=False)
    config = odoo_env["ir.config_parameter"].sudo()
    signup_mode = str(config.get_param("sc.signup.mode", "") or "").strip().lower()
    login_env = str(config.get_param("sc.login.env", "prod") or "prod").strip().lower()
    effective_signup_mode = signup_mode or (
        "invite" if login_env in {"prod", "production"} else "open"
    )
    native_scope = str(
        config.get_param("auth_signup.invitation_scope", "b2b") or "b2b"
    ).strip().lower()
    checks = {
        "ACTIVATION_CREDENTIAL_MODEL_PRESENT": "sc.user.activation.credential" in models,
        "ENTERPRISE_ACTIVATION_PURPOSE_PRESENT": getattr(
            activation, "PURPOSE_ENTERPRISE_ACTIVATION", None
        ) == "enterprise_activation",
        "DIGEST_ONLY_TOKEN_STORAGE_PRESENT": "token_digest" in fields
        and "activation_token" not in fields
        and "raw_token" not in fields,
        "TOKEN_SINGLE_USE_ENFORCED": all(
            token in begin_source + complete_source
            for token in ("state", "pending", "used", "ACTIVATION_REQUEST_REJECTED")
        ),
        "TOKEN_TTL_HOURS": int(getattr(activation, "TOKEN_TTL_HOURS", 0)),
        "TENANT_BINDING_SUPPORTED": "tenant_key" in fields
        and "sc.runtime.tenant_key" in binding_source,
        "ENVIRONMENT_BINDING_SUPPORTED": "environment_type" in fields
        and "sc.runtime.environment_type" in binding_source,
        "ACTIVATION_ADMIN_GROUP_XMLID": GROUP_XMLID if group else "",
        "ACTIVATION_RUNTIME_PARAMETER_NAMES": [TENANT_PARAMETER, ENVIRONMENT_PARAMETER],
        "SIGNUP_RESET_POLICY_ISOLATION_PRESENT": all(
            token in signup_source
            for token in ("_assert_open_allowed", "web_auth_reset_password", "_password_recovery_self_service_enabled")
        ),
        "PUBLIC_SIGNUP_ENABLED": effective_signup_mode == "open",
        "PRODUCTION_DATABASE_PUBLIC_REGISTRATION": native_scope == "b2c",
        "issue_method_present": "_issue_once" in dir(credential) and "token_digest" in issue_source,
        "revoke_method_present": "_revoke" in dir(credential),
        "group_has_no_implied_groups": bool(group) and not bool(group.implied_ids),
    }
    required_true = (
        "ACTIVATION_CREDENTIAL_MODEL_PRESENT",
        "ENTERPRISE_ACTIVATION_PURPOSE_PRESENT",
        "DIGEST_ONLY_TOKEN_STORAGE_PRESENT",
        "TOKEN_SINGLE_USE_ENFORCED",
        "TENANT_BINDING_SUPPORTED",
        "ENVIRONMENT_BINDING_SUPPORTED",
        "SIGNUP_RESET_POLICY_ISOLATION_PRESENT",
        "issue_method_present",
        "revoke_method_present",
        "group_has_no_implied_groups",
    )
    if (
        not all(checks[key] is True for key in required_true)
        or checks["TOKEN_TTL_HOURS"] != TOKEN_TTL_HOURS
        or checks["PUBLIC_SIGNUP_ENABLED"]
        or checks["PRODUCTION_DATABASE_PUBLIC_REGISTRATION"]
    ):
        public_checks = {
            key: checks[key]
            for key in (
                "ACTIVATION_CREDENTIAL_MODEL_PRESENT",
                "ENTERPRISE_ACTIVATION_PURPOSE_PRESENT",
                "DIGEST_ONLY_TOKEN_STORAGE_PRESENT",
                "TOKEN_SINGLE_USE_ENFORCED",
                "TOKEN_TTL_HOURS",
                "TENANT_BINDING_SUPPORTED",
                "ENVIRONMENT_BINDING_SUPPORTED",
                "ACTIVATION_ADMIN_GROUP_XMLID",
                "ACTIVATION_RUNTIME_PARAMETER_NAMES",
                "SIGNUP_RESET_POLICY_ISOLATION_PRESENT",
                "PUBLIC_SIGNUP_ENABLED",
                "PRODUCTION_DATABASE_PUBLIC_REGISTRATION",
            )
        }
        raise ActivationPredeployError(
            "BLOCKED_RC12_CAPABILITY_MISSING "
            + json.dumps(public_checks, ensure_ascii=True, sort_keys=True)
        )
    return checks


def _eligible_users(odoo_env: Any) -> Any:
    users = odoo_env["res.users"].sudo().with_context(active_test=False)
    public_user = odoo_env.ref("base.public_user", raise_if_not_found=False)
    portal = odoo_env.ref("base.group_portal", raise_if_not_found=False)
    candidates = users.search(
        [("active", "=", True), ("share", "=", False), ("login", "!=", TARGET_ADMIN_LOGIN)],
        order="id asc",
    )
    return candidates.filtered(
        lambda user: (not public_user or user != public_user)
        and (not portal or portal not in user.groups_id)
    )


def _user_roster(odoo_env: Any, tenant_key: str, eligible: Any) -> dict[str, Any]:
    identities = odoo_env["sc.tenant.payload.external.identity"].sudo().search(
        [("tenant_key", "=", tenant_key), ("model_name", "=", "res.users")],
        order="res_id asc, id asc",
    )
    by_user: dict[int, Any] = {}
    for identity in identities:
        if identity.res_id in by_user:
            raise ActivationPredeployError("approved user identity is ambiguous")
        by_user[identity.res_id] = identity
    eligible_ids = set(eligible.ids)
    approved_ids = eligible_ids & set(by_user)
    additional = eligible.filtered(lambda user: user.id not in approved_ids)
    if (
        len(eligible) != TECHNICALLY_ELIGIBLE_USERS_TOTAL
        or len(approved_ids) != APPROVED_FORMAL_USERS
        or len(additional) != ADDITIONAL_ELIGIBLE_USERS
    ):
        raise ActivationPredeployError("62/76 approved-roster assertion differs")
    Employee = odoo_env.get("hr.employee") if hasattr(odoo_env, "get") else None
    if Employee is None and "hr.employee" in getattr(odoo_env.registry, "models", {}):
        Employee = odoo_env["hr.employee"]
    rows = []
    for user in additional:
        employee = Employee.sudo().search([("user_id", "=", user.id)], limit=1) if Employee else False
        rows.append(
            {
                "immutable_user_id": f"{TARGET_DATABASE}:res.users:{user.id}",
                "name": user.name,
                "login": user.login,
                "user_category": "internal",
                "active": bool(user.active),
                "share": bool(user.share),
                "job": str(employee.job_id.name if employee and employee.job_id else ""),
                "primary_company": user.company_id.name,
                "allowed_companies": sorted(user.company_ids.mapped("name")),
                "data_source": "production_res_users_without_signed_tenant_payload_identity",
                "reason_not_in_original_62": "no immutable approved external identity in signed tenant payload",
                "business_approval_required": True,
            }
        )
    return {
        "APPROVED_FORMAL_USERS": len(approved_ids),
        "TECHNICALLY_ELIGIBLE_USERS_TOTAL": len(eligible),
        "ADDITIONAL_ELIGIBLE_USERS": len(additional),
        "ADDITIONAL_14_USERS_APPROVED": False,
        "approved_identity_source": "sc.tenant.payload.external.identity",
        "approved_identity_set_sha256": _digest(sorted(approved_ids)),
        "additional_users": rows,
    }


def _target_admin(odoo_env: Any) -> tuple[Any, Any, dict[str, Any]]:
    users = odoo_env["res.users"].sudo().with_context(active_test=False)
    target = users.search([("login", "=", TARGET_ADMIN_LOGIN)])
    group = odoo_env.ref(GROUP_XMLID, raise_if_not_found=False)
    if len(target) != 1 or not target.active or target.share or not group:
        raise ActivationPredeployError("unique active internal activation administrator differs")
    identity = target.get_external_id().get(target.id) or f"{TARGET_DATABASE}:res.users:{target.id}"
    state = {
        "immutable_user_id": identity,
        "login": target.login,
        "group_xmlid": GROUP_XMLID,
        "currently_has_group": group in target.groups_id,
        "already_system_admin": target.has_group("base.group_system")
        or target.has_group("smart_core.group_smart_core_admin"),
    }
    return target, group, state


def _normal_user_fingerprint(users: Any) -> str:
    return _digest(
        [
            {
                "id": user.id,
                "login": user.login,
                "active": bool(user.active),
                "share": bool(user.share),
                "groups": sorted(user.groups_id.ids),
                "company": user.company_id.id,
                "companies": sorted(user.company_ids.ids),
                "password_write_date": str(user.write_date or ""),
            }
            for user in users
        ]
    )


def _plan(odoo_env: Any, tenant_key: str, transaction: Mapping[str, str]) -> dict[str, Any]:
    capabilities = _installed_capabilities(odoo_env)
    eligible = _eligible_users(odoo_env)
    roster = _user_roster(odoo_env, tenant_key, eligible)
    target, group, admin = _target_admin(odoo_env)
    config = odoo_env["ir.config_parameter"].sudo()
    current_tenant = str(config.get_param(TENANT_PARAMETER, "") or "").strip()
    current_environment = str(config.get_param(ENVIRONMENT_PARAMETER, "") or "").strip()
    parameter_writes = int(current_tenant != tenant_key) + int(
        current_environment != TARGET_ENVIRONMENT
    )
    group_writes = int(group not in target.groups_id)
    if parameter_writes > 2 or group_writes > 1:
        raise ActivationPredeployError("write boundary exceeds authorization")
    credentials = odoo_env["sc.user.activation.credential"].sudo()
    all_normal = odoo_env["res.users"].sudo().with_context(active_test=False).search(
        [("id", "!=", target.id)], order="id asc"
    )
    credential_count = credentials.search_count([])
    activation_admin_members = group.users.filtered(
        lambda user: user.active and not user.share
    )
    if credential_count != 0 or set(activation_admin_members.ids) - {target.id}:
        raise ActivationPredeployError("activation baseline is not empty or uniquely administered")
    plan = {
        "database": TARGET_DATABASE,
        "transaction": dict(transaction),
        "release": {
            "tag": TARGET_TAG,
            "commit": TARGET_COMMIT,
            "registry_digest": TARGET_DIGEST,
            "deployment_id": DEPLOYMENT_ID,
        },
        "capabilities": capabilities,
        "roster": roster,
        "parameters": [
            {
                "name": TENANT_PARAMETER,
                "current_value": current_tenant,
                "target_value": tenant_key,
                "source": "root-owned production runtime TENANT_KEY/SC_TENANT_PAYLOAD_TENANT_KEY",
                "validation": TENANT_PATTERN.pattern,
                "rollback_value": current_tenant,
                "rollback_entry": "separately approved governed rollback; not authorized in this run",
            },
            {
                "name": ENVIRONMENT_PARAMETER,
                "current_value": current_environment,
                "target_value": TARGET_ENVIRONMENT,
                "source": "frozen production environment identity",
                "validation": "exactly production",
                "rollback_value": current_environment,
                "rollback_entry": "separately approved governed rollback; not authorized in this run",
            },
        ],
        "administrator": admin,
        "expected_writes": {
            "parameter_rows": parameter_writes,
            "admin_group_relation_rows": group_writes,
            "normal_user_rows": 0,
            "password_rows": 0,
            "login_rows": 0,
            "business_data_rows": 0,
            "activation_credential_rows": 0,
        },
        "before": {
            "activation_credential_count": credential_count,
            "activation_admin_members": len(activation_admin_members),
            "normal_user_fingerprint": _normal_user_fingerprint(all_normal),
        },
        "permission_isolation_contract": {
            "principal": "isolated TransactionCase user with base.group_user plus activation group only",
            "can_issue": True,
            "can_revoke": True,
            "can_view_non_secret_status": True,
            "can_change_user_roles": False,
            "can_change_user_companies": False,
            "can_read_token_plaintext": False,
            "system_admin": False,
            "importer": False,
            "data_operator": False,
            "cross_company_access": False,
            "evidence_test": "addons/smart_core/tests/test_user_activation.py::test_activation_admin_is_minimal_and_isolated",
        },
    }
    plan["plan_sha256"] = _plan_digest(plan)
    return plan


def _load_plan(active_env: Mapping[str, str]) -> dict[str, Any]:
    raw = active_env.get("USER_ACTIVATION_PREDEPLOY_PLAN_PATH", "")
    path = Path(raw)
    if (
        not raw
        or not path.is_absolute()
        or path.parent.resolve(strict=False) != EVIDENCE_ROOT
        or not path.is_file()
        or path.is_symlink()
        or stat.S_IMODE(path.stat().st_mode) != 0o600
    ):
        raise ActivationPredeployError("root-only reviewed plan evidence is required")
    payload = json.loads(path.read_text(encoding="utf-8"))
    expected = active_env.get("USER_ACTIVATION_PREDEPLOY_PLAN_SHA256", "")
    plan = {
        key: value
        for key, value in payload.items()
        if key not in {"schema_version", "generated_at_utc", "run_id", "mode", "tool_binding", "status"}
    }
    if payload.get("plan_sha256") != expected or _plan_digest(plan) != expected:
        raise ActivationPredeployError("reviewed plan digest differs")
    return payload


def _verify_after(odoo_env: Any, plan: Mapping[str, Any], tenant_key: str) -> dict[str, Any]:
    config = odoo_env["ir.config_parameter"].sudo()
    target, group, _admin = _target_admin(odoo_env)
    eligible = _eligible_users(odoo_env)
    all_normal = odoo_env["res.users"].sudo().with_context(active_test=False).search(
        [("id", "!=", target.id)], order="id asc"
    )
    credentials = odoo_env["sc.user.activation.credential"].sudo()
    tenant_value = str(config.get_param(TENANT_PARAMETER, "") or "").strip()
    environment_value = str(config.get_param(ENVIRONMENT_PARAMETER, "") or "").strip()
    credential_count = credentials.search_count([])
    normal_fingerprint = _normal_user_fingerprint(all_normal)
    before = plan["before"]
    checks = {
        "ACTIVATION_RUNTIME_PARAMETERS_CONFIGURED": tenant_value == tenant_key
        and environment_value == TARGET_ENVIRONMENT,
        "ACTIVATION_ENVIRONMENT_BINDING": environment_value,
        "ACTIVATION_TENANT_BINDING_RESOLVED": tenant_value == tenant_key,
        "ACTIVATION_ADMIN_MEMBERS": len(
            group.users.filtered(lambda user: user.active and not user.share)
        ),
        "ACTIVATION_CREDENTIAL_COUNT": credential_count,
        "TECHNICALLY_ELIGIBLE_USERS_TOTAL": len(eligible),
        "normal_user_fingerprint_unchanged": normal_fingerprint
        == before["normal_user_fingerprint"],
        "credential_count_unchanged": credential_count
        == before["activation_credential_count"],
        "target_has_activation_group": group in target.groups_id,
    }
    if (
        checks["ACTIVATION_RUNTIME_PARAMETERS_CONFIGURED"] is not True
        or checks["ACTIVATION_TENANT_BINDING_RESOLVED"] is not True
        or checks["ACTIVATION_ADMIN_MEMBERS"] != 1
        or checks["ACTIVATION_CREDENTIAL_COUNT"] != 0
        or checks["TECHNICALLY_ELIGIBLE_USERS_TOTAL"] != TECHNICALLY_ELIGIBLE_USERS_TOTAL
        or checks["normal_user_fingerprint_unchanged"] is not True
        or checks["credential_count_unchanged"] is not True
        or checks["target_has_activation_group"] is not True
    ):
        raise ActivationPredeployError("write-after verification differs")
    return checks


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        if stat.S_IMODE(path.stat().st_mode) != 0o600:
            raise ActivationPredeployError("evidence mode differs")
    finally:
        temporary.unlink(missing_ok=True)


def _report(
    *, mode: str, run_id: str, binding: Mapping[str, str], body: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "run_id": run_id,
        "mode": mode,
        "tool_binding": dict(binding),
        "status": "PASS",
        **body,
    }


def main() -> int:
    try:
        mode, output, binding = validate_control_plane(os.environ)
        if "env" not in globals():
            print("[production.user_activation.predeploy] PREFLIGHT PASS")
            return 0
        odoo_env = globals()["env"]
        if getattr(odoo_env.cr, "dbname", "") != TARGET_DATABASE:
            raise ActivationPredeployError("live database identity differs")
        tenant_key = os.environ["TENANT_KEY"]
        transaction = (
            _enable_read_only(odoo_env)
            if mode in {"plan", "verify"}
            else {"transaction_read_only": "off", "verification": "APPLY_AUTHORIZED"}
        )
        if mode == "plan":
            plan = _plan(odoo_env, tenant_key, transaction)
            body = dict(plan)
            odoo_env.cr.rollback()
        else:
            reviewed = _load_plan(os.environ)
            if mode == "apply":
                current = _plan(odoo_env, tenant_key, transaction)
                if current["plan_sha256"] != reviewed["plan_sha256"]:
                    raise ActivationPredeployError("production state drifted after reviewed plan")
                config = odoo_env["ir.config_parameter"].sudo()
                target, group, _admin = _target_admin(odoo_env)
                writes = {"parameter_rows": 0, "admin_group_relation_rows": 0}
                if config.get_param(TENANT_PARAMETER, "") != tenant_key:
                    config.set_param(TENANT_PARAMETER, tenant_key)
                    writes["parameter_rows"] += 1
                if config.get_param(ENVIRONMENT_PARAMETER, "") != TARGET_ENVIRONMENT:
                    config.set_param(ENVIRONMENT_PARAMETER, TARGET_ENVIRONMENT)
                    writes["parameter_rows"] += 1
                if group not in target.groups_id:
                    target.write({"groups_id": [(4, group.id)]})
                    writes["admin_group_relation_rows"] += 1
                if writes != {
                    "parameter_rows": reviewed["expected_writes"]["parameter_rows"],
                    "admin_group_relation_rows": reviewed["expected_writes"]["admin_group_relation_rows"],
                }:
                    raise ActivationPredeployError("observed write count differs from reviewed plan")
                checks = _verify_after(odoo_env, reviewed, tenant_key)
                odoo_env.cr.commit()
                body = {
                    "plan_sha256": reviewed["plan_sha256"],
                    "observed_writes": {
                        **writes,
                        "normal_user_rows": 0,
                        "password_rows": 0,
                        "login_rows": 0,
                        "business_data_rows": 0,
                        "activation_credential_rows": 0,
                    },
                    "verification": checks,
                }
            else:
                _installed_capabilities(odoo_env)
                _user_roster(odoo_env, tenant_key, _eligible_users(odoo_env))
                _target_admin(odoo_env)
                checks = _verify_after(odoo_env, reviewed, tenant_key)
                odoo_env.cr.rollback()
                body = {
                    "plan_sha256": reviewed["plan_sha256"],
                    "verification": checks,
                    "write_audit": {"database_write_statement_count": 0},
                }
        report = _report(
            mode=mode,
            run_id=os.environ["USER_ACTIVATION_PREDEPLOY_RUN_ID"],
            binding=binding,
            body=body,
        )
        _atomic_json(output, report)
        print(
            "[production.user_activation.predeploy] PASS "
            + json.dumps(
                {
                    "mode": mode,
                    "evidence": str(output),
                    "plan_sha256": report.get("plan_sha256", ""),
                    "identity_values_recorded_in_stdout": False,
                },
                sort_keys=True,
            )
        )
        return 0
    except ActivationPredeployError as exc:
        raise SystemExit(f"[production.user_activation.predeploy] BLOCKED: {exc}") from exc


if __name__ == "__main__":
    raise SystemExit(main())
