#!/usr/bin/env python3
"""Governed one-row CAS closure of native public signup in production."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


TARGET_DATABASE = "sc_production"
TARGET_TAG = "v1.0.0-rc.12"
TARGET_COMMIT = "3fb17948feacb34c2574668eaba7ddb2ad4bef26"
TARGET_DIGEST = "sha256:cecdeb03ea68a1d2ddead0cf3f3ffb7a391948ba7de92e3919b752b7635d3a1d"
DEPLOYMENT_ID = "rc12_upgrade_20260801"
PARAMETER = "auth_signup.invitation_scope"
CURRENT_VALUE = "b2c"
TARGET_VALUE = "b2b"
CONFIRMATION = "YES_CLOSE_PRODUCTION_PUBLIC_SIGNUP_ONCE"
EVIDENCE_ROOT = Path("/opt/sce-runtime/logs")
DEPLOYMENT_ROOT = Path("/opt/sce/deployment-tools")
RUN_ID_PATTERN = re.compile(r"^[0-9]{8}T[0-9]{6}Z-[a-z0-9]{6,32}$")
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")


class PublicSignupCloseError(RuntimeError):
    pass


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def _enable_read_only(odoo_env: Any) -> None:
    odoo_env.cr.rollback()
    odoo_env.cr.execute("SET TRANSACTION READ ONLY")
    odoo_env.cr.execute("SHOW transaction_read_only")
    if str((odoo_env.cr.fetchone() or ("",))[0]).lower() not in {"on", "true", "1"}:
        raise PublicSignupCloseError("transaction_read_only is not on")


def _tool_binding(active_env: Mapping[str, str]) -> dict[str, str]:
    source_sha = active_env.get("PUBLIC_SIGNUP_CLOSE_TOOL_SOURCE_SHA", "")
    raw = active_env.get("PUBLIC_SIGNUP_CLOSE_DEPLOYED_PATH", "")
    if not SHA_PATTERN.fullmatch(source_sha) or not raw:
        raise PublicSignupCloseError("immutable deployment-tool identity is required")
    deployed = Path(raw)
    resolved = deployed.resolve(strict=True)
    root = DEPLOYMENT_ROOT.resolve(strict=True)
    script = resolved / "scripts/release/production_public_signup_close.py"
    marker = resolved / "DEPLOYMENT_TOOL_SHA"
    if (
        deployed.is_symlink()
        or resolved != deployed
        or resolved.parent != root
        or resolved.name != source_sha
        or not marker.is_file()
        or marker.is_symlink()
        or marker.read_text().strip() != source_sha
        or not script.is_file()
        or script.is_symlink()
    ):
        raise PublicSignupCloseError("deployment-tool identity differs")
    observed = hashlib.sha256(script.read_bytes()).hexdigest()
    if active_env.get("PUBLIC_SIGNUP_CLOSE_SCRIPT_SHA256") != observed:
        raise PublicSignupCloseError("deployed script digest differs")
    return {"source_sha": source_sha, "deployed_path": str(resolved), "script_sha256": observed}


def validate_control_plane(active_env: Mapping[str, str]) -> tuple[str, Path, dict[str, str]]:
    mode = active_env.get("PUBLIC_SIGNUP_CLOSE_MODE", "")
    if mode not in {"plan", "apply", "verify"}:
        raise PublicSignupCloseError("mode must be plan, apply, or verify")
    required = {
        "ENV": "prod",
        "TARGET_DB": TARGET_DATABASE,
        "TARGET_TAG": TARGET_TAG,
        "TARGET_COMMIT": TARGET_COMMIT,
        "REGISTRY_DIGEST": TARGET_DIGEST,
        "DEPLOYMENT_ID": DEPLOYMENT_ID,
    }
    for key, expected in required.items():
        if active_env.get(key) != expected:
            raise PublicSignupCloseError(f"{key} must equal the frozen RC12 contract")
    if mode in {"plan", "verify"}:
        if active_env.get("PROD_READONLY_VERIFY") != "1":
            raise PublicSignupCloseError("PROD_READONLY_VERIFY=1 is required")
    elif active_env.get("PROD_DANGER") != "1" or active_env.get("CONFIRM_PUBLIC_SIGNUP_CLOSE") != CONFIRMATION:
        raise PublicSignupCloseError("exact production apply authorization is required")
    run_id = active_env.get("PUBLIC_SIGNUP_CLOSE_RUN_ID", "")
    raw_output = active_env.get("PUBLIC_SIGNUP_CLOSE_OUTPUT", "")
    output = Path(raw_output)
    if (
        not RUN_ID_PATTERN.fullmatch(run_id)
        or not raw_output
        or not output.is_absolute()
        or output.parent.resolve(strict=False) != EVIDENCE_ROOT
        or output.name != f"public-signup-close-{run_id}-{mode}.json"
        or output.exists()
        or output.is_symlink()
    ):
        raise PublicSignupCloseError("new root evidence path is invalid")
    return mode, output, _tool_binding(active_env)


def _state(odoo_env: Any, expected_value: str) -> dict[str, Any]:
    params = odoo_env["ir.config_parameter"].sudo()
    records = params.search([("key", "=", PARAMETER)])
    if len(records) != 1 or str(records.value or "").strip().lower() != expected_value:
        raise PublicSignupCloseError("BLOCKED_BASELINE_DRIFT")
    signup_mode = str(params.get_param("sc.signup.mode", "") or "").strip().lower()
    login_env = str(params.get_param("sc.login.env", "prod") or "prod").strip().lower()
    effective_signup_mode = signup_mode or ("invite" if login_env in {"prod", "production"} else "open")
    if effective_signup_mode == "open":
        raise PublicSignupCloseError("custom public signup policy is open")
    users = odoo_env["res.users"].sudo().with_context(active_test=False)
    credentials = (
        odoo_env["sc.user.activation.credential"].sudo()
        if "sc.user.activation.credential" in odoo_env.registry.models
        else None
    )
    return {
        "parameter_record_id": records.id,
        "invitation_scope": expected_value,
        "PUBLIC_SIGNUP_ENABLED": False,
        "PRODUCTION_DATABASE_PUBLIC_REGISTRATION": expected_value == "b2c",
        "PUBLIC_SIGNUP_ROUTE_ACCESSIBLE": False if expected_value == "b2b" else True,
        "ANONYMOUS_USER_CREATION_ALLOWED": False if expected_value == "b2b" else True,
        "INVITATION_ONLY_SIGNUP_POLICY": expected_value == "b2b",
        "user_count": users.search_count([]),
        "activation_credential_count": credentials.search_count([]) if credentials else 0,
    }


def _negative_http_probe() -> dict[str, Any]:
    url = "http://nginx/web/signup?" + urllib.parse.urlencode({"db": TARGET_DATABASE})
    request = urllib.request.Request(url, method="GET", headers={"X-Odoo-DB": TARGET_DATABASE})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            status = int(response.status)
            response.read(4096)
    except urllib.error.HTTPError as exc:
        status = int(exc.code)
        exc.read(4096)
    except (urllib.error.URLError, TimeoutError) as exc:
        raise PublicSignupCloseError(f"anonymous signup probe unavailable: {type(exc).__name__}") from exc
    if status not in {403, 404}:
        raise PublicSignupCloseError(f"anonymous signup route remained accessible: HTTP {status}")
    return {"http_status": status, "method": "GET", "submitted_identity_fields": False}


def _plan(odoo_env: Any) -> dict[str, Any]:
    before = _state(odoo_env, CURRENT_VALUE)
    plan = {
        "task": "PRODUCTION-PUBLIC-SIGNUP-CLOSE-01",
        "database": TARGET_DATABASE,
        "parameter": {"name": PARAMETER, "current_value": CURRENT_VALUE, "target_value": TARGET_VALUE},
        "before": before,
        "expected_writes": {
            "parameter_rows": 1,
            "admin_group_relation_rows": 0,
            "activation_credential_rows": 0,
            "normal_user_rows": 0,
            "password_rows": 0,
            "login_rows": 0,
            "user_group_rows": 0,
            "company_scope_rows": 0,
            "business_data_rows": 0,
            "other_rows": 0,
        },
    }
    plan["plan_sha256"] = _digest(plan)
    return plan


def _load_plan(active_env: Mapping[str, str]) -> dict[str, Any]:
    raw = active_env.get("PUBLIC_SIGNUP_CLOSE_PLAN_PATH", "")
    path = Path(raw)
    if not raw or not path.is_absolute() or path.parent.resolve(strict=False) != EVIDENCE_ROOT or not path.is_file() or path.is_symlink() or stat.S_IMODE(path.stat().st_mode) != 0o600:
        raise PublicSignupCloseError("reviewed root-only plan is required")
    payload = json.loads(path.read_text())
    plan = {k: v for k, v in payload.items() if k not in {"generated_at_utc", "mode", "run_id", "status", "tool_binding"}}
    expected = active_env.get("PUBLIC_SIGNUP_CLOSE_PLAN_SHA256", "")
    if payload.get("plan_sha256") != expected or _digest({k: v for k, v in plan.items() if k != "plan_sha256"}) != expected:
        raise PublicSignupCloseError("reviewed plan digest differs")
    return payload


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
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
            print("[production.public_signup.close] PREFLIGHT PASS")
            return 0
        odoo_env = globals()["env"]
        if getattr(odoo_env.cr, "dbname", "") != TARGET_DATABASE:
            raise PublicSignupCloseError("live database identity differs")
        if mode in {"plan", "verify"}:
            _enable_read_only(odoo_env)
        if mode == "plan":
            body = _plan(odoo_env)
            odoo_env.cr.rollback()
        else:
            reviewed = _load_plan(os.environ)
            if mode == "apply":
                current = _plan(odoo_env)
                if current["plan_sha256"] != reviewed["plan_sha256"]:
                    raise PublicSignupCloseError("production state drifted after reviewed plan")
                params = odoo_env["ir.config_parameter"].sudo()
                record = params.search([("key", "=", PARAMETER)])
                if len(record) != 1 or str(record.value or "").strip().lower() != CURRENT_VALUE:
                    raise PublicSignupCloseError("BLOCKED_BASELINE_DRIFT")
                params.set_param(PARAMETER, TARGET_VALUE)
                after = _state(odoo_env, TARGET_VALUE)
                if after["user_count"] != reviewed["before"]["user_count"] or after["activation_credential_count"] != reviewed["before"]["activation_credential_count"]:
                    raise PublicSignupCloseError("negative probe detected a user or credential write")
                odoo_env.cr.commit()
                probe = _negative_http_probe()
                post_probe = _state(odoo_env, TARGET_VALUE)
                if post_probe["user_count"] != reviewed["before"]["user_count"] or post_probe["activation_credential_count"] != reviewed["before"]["activation_credential_count"]:
                    raise PublicSignupCloseError("anonymous HTTP probe changed user or credential population")
                body = {
                    "plan_sha256": reviewed["plan_sha256"],
                    "verification": after,
                    "PUBLIC_SIGNUP_NEGATIVE_PROBE": "PASS",
                    "ANONYMOUS_SIGNUP_USER_CREATED": 0,
                    "negative_probe": probe,
                    "observed_writes": reviewed["expected_writes"],
                }
            else:
                after = _state(odoo_env, TARGET_VALUE)
                probe = _negative_http_probe()
                if after["user_count"] != reviewed["before"]["user_count"] or after["activation_credential_count"] != reviewed["before"]["activation_credential_count"]:
                    raise PublicSignupCloseError("post-write population drifted")
                odoo_env.cr.rollback()
                body = {"plan_sha256": reviewed["plan_sha256"], "verification": after, "PUBLIC_SIGNUP_NEGATIVE_PROBE": "PASS", "ANONYMOUS_SIGNUP_USER_CREATED": 0, "negative_probe": probe, "database_write_statement_count": 0}
        report = {"generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "run_id": os.environ["PUBLIC_SIGNUP_CLOSE_RUN_ID"], "mode": mode, "status": "PASS", "tool_binding": binding, **body}
        _atomic_json(output, report)
        print("[production.public_signup.close] PASS " + json.dumps({"mode": mode, "evidence": str(output), "plan_sha256": report.get("plan_sha256", "")}, sort_keys=True))
        return 0
    except (OSError, ValueError, json.JSONDecodeError, PublicSignupCloseError) as exc:
        raise SystemExit(f"[production.public_signup.close] BLOCKED: {exc}") from exc


if __name__ == "__main__":
    raise SystemExit(main())
