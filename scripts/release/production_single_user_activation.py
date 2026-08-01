#!/usr/bin/env python3
"""Governed RC12 production activation for one explicitly approved user.

Plan and verify are transaction-read-only. Apply may set the two activation
bindings, append the activation-admin group to the sole internal ``admin``,
activate the sole target user when necessary, issue one digest-only credential,
and deliver its one-time plaintext directly through the registered TLS mail
channel. The plaintext is never written to evidence or stdout.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import tempfile
from collections.abc import Mapping
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Any


TARGET_DATABASE = "sc_production"
TARGET_TAG = "v1.0.0-rc.12"
TARGET_COMMIT = "3fb17948feacb34c2574668eaba7ddb2ad4bef26"
TARGET_DIGEST = "sha256:cecdeb03ea68a1d2ddead0cf3f3ffb7a391948ba7de92e3919b752b7635d3a1d"
DEPLOYMENT_ID = "rc12_upgrade_20260801"
TARGET_LOGIN = "wutao"
TARGET_ADMIN_LOGIN = "admin"
GROUP_XMLID = "smart_core.group_smart_core_user_activation_admin"
TENANT_PARAMETER = "sc.runtime.tenant_key"
ENVIRONMENT_PARAMETER = "sc.runtime.environment_type"
TARGET_ENVIRONMENT = "production"
PURPOSE = "enterprise_activation"
TTL_HOURS = 24
CONFIRMATION = "YES_ACTIVATE_ONLY_WUTAO_IN_PRODUCTION"
EVIDENCE_ROOT = Path("/opt/sce-runtime/logs")
DEPLOYMENT_ROOT = Path("/opt/sce/deployment-tools")
RUN_ID_PATTERN = re.compile(r"^[0-9]{8}T[0-9]{6}Z-[a-z0-9]{6,32}$")
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
TENANT_PATTERN = re.compile(r"^[a-z][a-z0-9_]{2,62}$")
SCHEMA_VERSION = "production-single-user-activation.v1"


class SingleUserActivationError(RuntimeError):
    pass


def _digest(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _plan_digest(plan: Mapping[str, Any]) -> str:
    return _digest({key: value for key, value in plan.items() if key not in {"plan_sha256", "transaction"}})


def _mode(active_env: Mapping[str, str]) -> str:
    mode = active_env.get("SINGLE_USER_ACTIVATION_MODE", "").strip()
    if mode not in {"plan", "apply", "verify"}:
        raise SingleUserActivationError("mode must be plan, apply, or verify")
    return mode


def _evidence_path(active_env: Mapping[str, str], mode: str) -> Path:
    run_id = active_env.get("SINGLE_USER_ACTIVATION_RUN_ID", "")
    if not RUN_ID_PATTERN.fullmatch(run_id):
        raise SingleUserActivationError("run ID must be a UTC timestamp plus safe suffix")
    raw = active_env.get("SINGLE_USER_ACTIVATION_OUTPUT", "").strip()
    path = Path(raw)
    if not raw or not path.is_absolute() or path.parent.resolve(strict=False) != EVIDENCE_ROOT:
        raise SingleUserActivationError(f"evidence must be directly under {EVIDENCE_ROOT}")
    if path.name != f"single-user-activation-{run_id}-{mode}.json":
        raise SingleUserActivationError("evidence filename must bind run ID and mode")
    if path.exists() or path.is_symlink():
        raise SingleUserActivationError("evidence output must be a new non-symlink path")
    return path


def _tool_binding(active_env: Mapping[str, str]) -> dict[str, str]:
    source_sha = active_env.get("SINGLE_USER_ACTIVATION_TOOL_SOURCE_SHA", "")
    deployed_raw = active_env.get("SINGLE_USER_ACTIVATION_DEPLOYED_PATH", "")
    if not SHA_PATTERN.fullmatch(source_sha) or not deployed_raw:
        raise SingleUserActivationError("immutable deployment-tool identity is required")
    deployed = Path(deployed_raw)
    try:
        resolved = deployed.resolve(strict=True)
        root = DEPLOYMENT_ROOT.resolve(strict=True)
    except OSError as exc:
        raise SingleUserActivationError("deployment-tool path is unavailable") from exc
    marker = resolved / "DEPLOYMENT_TOOL_SHA"
    script = resolved / "scripts/release/production_single_user_activation.py"
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
        raise SingleUserActivationError("deployment-tool identity differs")
    observed = hashlib.sha256(script.read_bytes()).hexdigest()
    if active_env.get("SINGLE_USER_ACTIVATION_SCRIPT_SHA256") != observed:
        raise SingleUserActivationError("deployed script digest differs")
    return {"source_sha": source_sha, "deployed_path": str(resolved), "script_sha256": observed}


def validate_control_plane(active_env: Mapping[str, str]) -> tuple[str, Path, dict[str, str]]:
    mode = _mode(active_env)
    required = {
        "ENV": "prod",
        "TARGET_DB": TARGET_DATABASE,
        "TARGET_TAG": TARGET_TAG,
        "TARGET_COMMIT": TARGET_COMMIT,
        "REGISTRY_DIGEST": TARGET_DIGEST,
        "DEPLOYMENT_ID": DEPLOYMENT_ID,
        "SINGLE_USER_ACTIVATION_LOGIN": TARGET_LOGIN,
        "ACTIVATION_ADMIN_LOGIN": TARGET_ADMIN_LOGIN,
    }
    for key, expected in required.items():
        if active_env.get(key) != expected:
            raise SingleUserActivationError(f"{key} must equal the frozen single-user contract")
    if not TENANT_PATTERN.fullmatch(active_env.get("TENANT_KEY", "")):
        raise SingleUserActivationError("stable production TENANT_KEY is required")
    public_url = active_env.get("ACTIVATION_PUBLIC_URL", "")
    if not public_url.startswith("https://") or not public_url.endswith("/activate-account"):
        raise SingleUserActivationError("HTTPS activation public URL is required")
    if mode in {"plan", "verify"}:
        if active_env.get("PROD_READONLY_VERIFY") != "1":
            raise SingleUserActivationError("PROD_READONLY_VERIFY=1 is required")
    elif active_env.get("PROD_DANGER") != "1" or active_env.get("CONFIRM_SINGLE_USER_ACTIVATION") != CONFIRMATION:
        raise SingleUserActivationError("exact production apply authorization is required")
    return mode, _evidence_path(active_env, mode), _tool_binding(active_env)


def _enable_read_only(odoo_env: Any) -> dict[str, str]:
    odoo_env.cr.rollback()
    odoo_env.cr.execute("SET TRANSACTION READ ONLY")
    odoo_env.cr.execute("SHOW transaction_read_only")
    value = str((odoo_env.cr.fetchone() or ("",))[0]).strip().lower()
    if value not in {"on", "true", "1"}:
        raise SingleUserActivationError("transaction_read_only is not on")
    return {"transaction_read_only": "on", "verification": "PASS"}


def _record_xmlids(records: Any) -> list[str]:
    if not records:
        return []
    mapping = records.get_external_id()
    return sorted(mapping.get(record.id) or f"{record._name}:dbid:{record.id}" for record in records)


def _user_snapshot(user: Any) -> dict[str, Any]:
    return {
        "login": user.login,
        "name_digest": _digest(user.name or ""),
        "active": bool(user.active),
        "share": bool(user.share),
        "groups": _record_xmlids(user.groups_id),
        "primary_company": _record_xmlids(user.company_id),
        "allowed_companies": _record_xmlids(user.company_ids),
    }


def _target_user(odoo_env: Any, tenant_key: str) -> tuple[Any, str, dict[str, Any]]:
    users = odoo_env["res.users"].sudo().with_context(active_test=False)
    target = users.search([("login", "=", TARGET_LOGIN)])
    internal = odoo_env.ref("base.group_user", raise_if_not_found=False)
    portal = odoo_env.ref("base.group_portal", raise_if_not_found=False)
    if len(target) != 1:
        raise SingleUserActivationError("wutao must resolve to exactly one user")
    if target.share or not internal or internal not in target.groups_id or (portal and portal in target.groups_id):
        raise SingleUserActivationError("wutao must be an internal non-portal user")
    identities = odoo_env["sc.tenant.payload.external.identity"].sudo().search(
        [("tenant_key", "=", tenant_key), ("model_name", "=", "res.users"), ("res_id", "=", target.id)]
    )
    if len(identities) != 1 or not identities.external_key:
        raise SingleUserActivationError("wutao immutable identity must resolve uniquely")
    snapshot = _user_snapshot(target)
    return target, identities.external_key, {
        "login": TARGET_LOGIN,
        "immutable_user_id_sha256": _digest(identities.external_key),
        "name_sha256": snapshot["name_digest"],
        "active": snapshot["active"],
        "share": snapshot["share"],
        "internal": True,
        "scope_snapshot_sha256": _digest({key: snapshot[key] for key in ("groups", "primary_company", "allowed_companies")}),
    }


def _target_admin(odoo_env: Any) -> tuple[Any, Any, dict[str, Any]]:
    users = odoo_env["res.users"].sudo().with_context(active_test=False)
    admin = users.search([("login", "=", TARGET_ADMIN_LOGIN)])
    group = odoo_env.ref(GROUP_XMLID, raise_if_not_found=False)
    if len(admin) != 1 or not admin.active or admin.share or not group or group.implied_ids:
        raise SingleUserActivationError("unique internal activation administrator differs")
    other_members = group.users.filtered(lambda user: user.active and not user.share and user != admin)
    if other_members:
        raise SingleUserActivationError("activation administrator group has an unexpected member")
    return admin, group, {"login": TARGET_ADMIN_LOGIN, "group_xmlid": GROUP_XMLID, "currently_has_group": group in admin.groups_id}


def _delivery_channel(odoo_env: Any, target: Any) -> tuple[Any, dict[str, Any]]:
    email = str(target.partner_id.email or "").strip()
    servers = odoo_env["ir.mail_server"].sudo().search([("active", "=", True)], order="sequence,id")
    secure = servers.filtered(lambda server: str(server.smtp_encryption or "").lower() in {"starttls", "ssl"})
    if not email or "@" not in email or len(secure) != 1:
        raise SingleUserActivationError("verified registered email and exactly one TLS mail server are required")
    server = secure[0]
    sender = str(
        odoo_env["ir.config_parameter"].sudo().get_param("mail.default.from", "")
        or server.smtp_user
        or ""
    ).strip()
    if not sender or "@" not in sender:
        raise SingleUserActivationError("governed mail sender is unavailable")
    return server, {
        "channel_type": "registered-email-tls",
        "recipient_sha256": _digest(email.lower()),
        "sender_sha256": _digest(sender.lower()),
        "smtp_encryption": str(server.smtp_encryption or "").lower(),
        "identity_verification_method": "registered-contact-plus-explicit-single-user-approval",
        "ready": True,
    }


def _capabilities(odoo_env: Any) -> dict[str, Any]:
    from odoo.addons.smart_core.models import user_activation

    if "sc.user.activation.credential" not in odoo_env.registry.models:
        raise SingleUserActivationError("activation credential model is unavailable")
    fields = odoo_env["sc.user.activation.credential"]._fields
    checks = {
        "model_present": True,
        "purpose": user_activation.PURPOSE_ENTERPRISE_ACTIVATION,
        "ttl_hours": int(user_activation.TOKEN_TTL_HOURS),
        "digest_only": "token_digest" in fields and "activation_token" not in fields and "raw_token" not in fields,
        "single_use": hasattr(odoo_env["sc.user.activation.credential"], "_begin_activation") and hasattr(odoo_env["sc.user.activation.credential"], "_complete_activation"),
    }
    if checks != {"model_present": True, "purpose": PURPOSE, "ttl_hours": TTL_HOURS, "digest_only": True, "single_use": True}:
        raise SingleUserActivationError("production activation capability contract differs")
    return checks


def _plan(odoo_env: Any, tenant_key: str, transaction: Mapping[str, str]) -> dict[str, Any]:
    capabilities = _capabilities(odoo_env)
    target, immutable_user_id, target_state = _target_user(odoo_env, tenant_key)
    admin, group, admin_state = _target_admin(odoo_env)
    _server, delivery = _delivery_channel(odoo_env, target)
    params = odoo_env["ir.config_parameter"].sudo()
    current_tenant = str(params.get_param(TENANT_PARAMETER, "") or "").strip()
    current_environment = str(params.get_param(ENVIRONMENT_PARAMETER, "") or "").strip()
    parameter_writes = int(current_tenant != tenant_key) + int(current_environment != TARGET_ENVIRONMENT)
    group_writes = int(group not in admin.groups_id)
    active_writes = int(not target.active)
    credentials = odoo_env["sc.user.activation.credential"].sudo()
    existing = credentials.search_count([("user_id", "=", target.id), ("purpose", "=", PURPOSE), ("state", "=", "pending")])
    if existing:
        raise SingleUserActivationError("wutao already has a pending credential")
    plan = {
        "database": TARGET_DATABASE,
        "transaction": dict(transaction),
        "tenant_key_sha256": _digest(tenant_key),
        "target": target_state,
        "administrator": admin_state,
        "delivery": delivery,
        "capabilities": capabilities,
        "parameters": [
            {"name": TENANT_PARAMETER, "current_sha256": _digest(current_tenant), "target_sha256": _digest(tenant_key)},
            {"name": ENVIRONMENT_PARAMETER, "current_value": current_environment, "target_value": TARGET_ENVIRONMENT},
        ],
        "expected_writes": {
            "activation_runtime_parameter_rows": parameter_writes,
            "activation_admin_group_relation_rows": group_writes,
            "wutao_active_state_rows": active_writes,
            "activation_batch_rows": 1,
            "wutao_activation_credential_rows": 1,
            "delivery_audit_rows": 1,
            "other_user_rows": 0,
            "login_rows": 0,
            "role_rows": 0,
            "company_scope_rows": 0,
            "business_data_rows": 0,
        },
        "before": {
            "target_snapshot": _user_snapshot(target),
            "target_credential_count": credentials.search_count([("user_id", "=", target.id)]),
            "all_other_users_sha256": _digest([
                {"id": user.id, "login": user.login, "active": bool(user.active), "groups": sorted(user.groups_id.ids), "company": user.company_id.id, "companies": sorted(user.company_ids.ids), "write_date": str(user.write_date or "")}
                for user in odoo_env["res.users"].sudo().with_context(active_test=False).search([("id", "not in", [target.id, admin.id])], order="id")
            ]),
            "immutable_user_id_sha256": _digest(immutable_user_id),
        },
    }
    if parameter_writes > 2 or group_writes > 1 or active_writes > 1:
        raise SingleUserActivationError("write boundary exceeds explicit authorization")
    plan["plan_sha256"] = _plan_digest(plan)
    return plan


def _load_plan(active_env: Mapping[str, str]) -> dict[str, Any]:
    raw = active_env.get("SINGLE_USER_ACTIVATION_PLAN_PATH", "")
    path = Path(raw)
    if not raw or not path.is_absolute() or path.parent.resolve(strict=False) != EVIDENCE_ROOT or not path.is_file() or path.is_symlink() or stat.S_IMODE(path.stat().st_mode) != 0o600:
        raise SingleUserActivationError("root-only reviewed plan evidence is required")
    payload = json.loads(path.read_text(encoding="utf-8"))
    expected = active_env.get("SINGLE_USER_ACTIVATION_PLAN_SHA256", "")
    plan = {key: value for key, value in payload.items() if key not in {"schema_version", "generated_at_utc", "run_id", "mode", "tool_binding", "status"}}
    if payload.get("plan_sha256") != expected or _plan_digest(plan) != expected:
        raise SingleUserActivationError("reviewed plan digest differs")
    return payload


def _other_users_digest(odoo_env: Any, target: Any, admin: Any) -> str:
    return _digest([
        {"id": user.id, "login": user.login, "active": bool(user.active), "groups": sorted(user.groups_id.ids), "company": user.company_id.id, "companies": sorted(user.company_ids.ids), "write_date": str(user.write_date or "")}
        for user in odoo_env["res.users"].sudo().with_context(active_test=False).search([("id", "not in", [target.id, admin.id])], order="id")
    ])


def _send_activation(server: Any, target: Any, sender: str, public_url: str, raw_token: str) -> None:
    message = EmailMessage()
    message["Subject"] = "智能施工生产账号一次性激活"
    message["From"] = sender
    message["To"] = str(target.partner_id.email).strip()
    message.set_content(
        "您好，请打开以下生产激活页面并输入一次性激活码。\n\n"
        f"激活页面：{public_url}\n"
        f"登录名：{TARGET_LOGIN}\n"
        f"一次性激活码：{raw_token}\n\n"
        "该激活码24小时内有效且仅可使用一次。请勿转发。"
    )
    result = server.send_email(message)
    if result is False:
        raise SingleUserActivationError("TLS point-to-point delivery failed")


def _verify_after(odoo_env: Any, reviewed: Mapping[str, Any], tenant_key: str) -> dict[str, Any]:
    target, _identity, _state = _target_user(odoo_env, tenant_key)
    admin, group, _admin_state = _target_admin(odoo_env)
    params = odoo_env["ir.config_parameter"].sudo()
    credentials = odoo_env["sc.user.activation.credential"].sudo().search(
        [("user_id", "=", target.id), ("purpose", "=", PURPOSE)], order="issued_at desc", limit=1
    )
    if len(credentials) != 1:
        raise SingleUserActivationError("exactly one latest wutao credential is required")
    audits = odoo_env["sc.user.activation.delivery.audit"].sudo().search_count([("credential_id", "=", credentials.id)])
    current = _user_snapshot(target)
    before = reviewed["before"]["target_snapshot"]
    scope_keys = ("login", "name_digest", "share", "groups", "primary_company", "allowed_companies")
    checks = {
        "PRODUCTION_ACTIVATION_BASELINE_READY": params.get_param(TENANT_PARAMETER, "") == tenant_key and params.get_param(ENVIRONMENT_PARAMETER, "") == TARGET_ENVIRONMENT and len(group.users.filtered(lambda user: user.active and not user.share)) == 1 and group in admin.groups_id,
        "LOGIN": TARGET_LOGIN,
        "UNIQUE_USER_MATCH": True,
        "INTERNAL_USER": not target.share,
        "USER_ACTIVE": bool(target.active),
        "ACTIVATION_CREDENTIAL_ISSUED": 1,
        "ACTIVATION_TTL_HOURS": TTL_HOURS,
        "TOKEN_SINGLE_USE": True,
        "TOKEN_STORED_AS_DIGEST_ONLY": bool(credentials.token_digest),
        "SECURE_DELIVERY": "PASS" if audits == 1 else "FAIL",
        "EXISTING_ROLE_SCOPE_PRESERVED": all(current[key] == before[key] for key in scope_keys),
        "EXISTING_COMPANY_SCOPE_PRESERVED": current["primary_company"] == before["primary_company"] and current["allowed_companies"] == before["allowed_companies"],
        "credential_pending": credentials.state == "pending",
        "credential_batch_matches_run": credentials.batch_id.batch_key == f"wutao-{reviewed['run_id']}",
        "OTHER_USER_WRITES": 0 if _other_users_digest(odoo_env, target, admin) == reviewed["before"]["all_other_users_sha256"] else -1,
    }
    if not all((checks["PRODUCTION_ACTIVATION_BASELINE_READY"], checks["USER_ACTIVE"], checks["TOKEN_STORED_AS_DIGEST_ONLY"], checks["SECURE_DELIVERY"] == "PASS", checks["credential_pending"], checks["credential_batch_matches_run"], checks["EXISTING_ROLE_SCOPE_PRESERVED"], checks["EXISTING_COMPANY_SCOPE_PRESERVED"], checks["OTHER_USER_WRITES"] == 0)):
        raise SingleUserActivationError("write-after verification differs")
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
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    try:
        mode, output, binding = validate_control_plane(os.environ)
        if "env" not in globals():
            print("[production.single_user_activation] PREFLIGHT PASS")
            return 0
        odoo_env = globals()["env"]
        if getattr(odoo_env.cr, "dbname", "") != TARGET_DATABASE:
            raise SingleUserActivationError("live database identity differs")
        tenant_key = os.environ["TENANT_KEY"]
        transaction = _enable_read_only(odoo_env) if mode in {"plan", "verify"} else {"transaction_read_only": "off", "verification": "APPLY_AUTHORIZED"}
        if mode == "plan":
            body = _plan(odoo_env, tenant_key, transaction)
            odoo_env.cr.rollback()
        else:
            reviewed = _load_plan(os.environ)
            if mode == "apply":
                current = _plan(odoo_env, tenant_key, transaction)
                if current["plan_sha256"] != reviewed["plan_sha256"]:
                    raise SingleUserActivationError("production state drifted after reviewed plan")
                target, immutable_user_id, _target_state = _target_user(odoo_env, tenant_key)
                admin, group, _admin_state = _target_admin(odoo_env)
                server, delivery = _delivery_channel(odoo_env, target)
                params = odoo_env["ir.config_parameter"].sudo()
                writes = {"activation_runtime_parameter_rows": 0, "activation_admin_group_relation_rows": 0, "wutao_active_state_rows": 0, "activation_batch_rows": 0, "wutao_activation_credential_rows": 0, "delivery_audit_rows": 0, "other_user_rows": 0, "login_rows": 0, "role_rows": 0, "company_scope_rows": 0, "business_data_rows": 0}
                if params.get_param(TENANT_PARAMETER, "") != tenant_key:
                    params.set_param(TENANT_PARAMETER, tenant_key)
                    writes["activation_runtime_parameter_rows"] += 1
                if params.get_param(ENVIRONMENT_PARAMETER, "") != TARGET_ENVIRONMENT:
                    params.set_param(ENVIRONMENT_PARAMETER, TARGET_ENVIRONMENT)
                    writes["activation_runtime_parameter_rows"] += 1
                if group not in admin.groups_id:
                    admin.write({"groups_id": [(4, group.id)]})
                    writes["activation_admin_group_relation_rows"] += 1
                    admin.invalidate_recordset()
                if not target.active:
                    target.write({"active": True})
                    writes["wutao_active_state_rows"] += 1
                service = odoo_env["sc.user.activation.credential"].with_user(admin)
                batch = service._create_batch(batch_key=f"wutao-{os.environ['SINGLE_USER_ACTIVATION_RUN_ID']}", tenant_key=tenant_key, environment_type=TARGET_ENVIRONMENT, purpose=PURPOSE)
                writes["activation_batch_rows"] = 1
                issued = service._issue_once(user=target, immutable_user_id=immutable_user_id, target_login=TARGET_LOGIN, tenant_key=tenant_key, environment_type=TARGET_ENVIRONMENT, batch=batch, purpose=PURPOSE, ttl_hours=TTL_HOURS)
                writes["wutao_activation_credential_rows"] = 1
                credential = odoo_env["sc.user.activation.credential"].sudo().search([("credential_id", "=", issued["credential_id"])])
                sender = str(odoo_env["ir.config_parameter"].sudo().get_param("mail.default.from", "") or server.smtp_user or "").strip()
                _send_activation(server, target, sender, os.environ["ACTIVATION_PUBLIC_URL"], issued.pop("activation_token"))
                credential.with_user(admin)._record_delivery(operator_identity=os.environ.get("ACTIVATION_DELIVERY_OPERATOR", "production-operator:codex"), channel_type=delivery["channel_type"], verification_method=delivery["identity_verification_method"])
                writes["delivery_audit_rows"] = 1
                if writes != reviewed["expected_writes"]:
                    raise SingleUserActivationError("observed write count differs from reviewed plan")
                checks = _verify_after(odoo_env, reviewed, tenant_key)
                odoo_env.cr.commit()
                body = {"plan_sha256": reviewed["plan_sha256"], "observed_writes": writes, "verification": checks, "result": "PENDING_USER_PASSWORD_SETUP_AND_LOGIN_VERIFICATION"}
            else:
                checks = _verify_after(odoo_env, reviewed, tenant_key)
                odoo_env.cr.rollback()
                body = {"plan_sha256": reviewed["plan_sha256"], "verification": checks, "write_audit": {"database_write_statement_count": 0}}
        report = {"schema_version": SCHEMA_VERSION, "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "run_id": os.environ["SINGLE_USER_ACTIVATION_RUN_ID"], "mode": mode, "tool_binding": binding, "status": "PASS", **body}
        serialized = json.dumps(report, ensure_ascii=False, sort_keys=True)
        if "activation_token" in serialized or "raw_token" in serialized:
            raise SingleUserActivationError("plaintext credential field reached evidence")
        _atomic_json(output, report)
        print(json.dumps({"tool": "production.single_user_activation", "status": "PASS", "mode": mode, "evidence": str(output), "plan_sha256": report.get("plan_sha256", ""), "plaintext_credential_output": False}, sort_keys=True))
        return 0
    except SingleUserActivationError as exc:
        if "env" in globals():
            globals()["env"].cr.rollback()
        raise SystemExit(f"[production.single_user_activation] BLOCKED: {exc}") from exc


if __name__ == "__main__":
    raise SystemExit(main())
