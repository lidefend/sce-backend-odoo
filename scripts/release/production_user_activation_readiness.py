#!/usr/bin/env python3
"""Read-only production readiness probe for enterprise user activation.

The probe records aggregate counts and irreversible fingerprints only.  It
never emits a login, person name, contact value, password, activation token,
or challenge.  The database transaction is made read-only before the first
ORM query.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TARGET_DATABASE = "sc_production"
EVIDENCE_ROOT = Path("/opt/sce-runtime/logs")
RUN_ID_PATTERN = re.compile(r"^[0-9]{8}T[0-9]{6}Z-[a-z0-9]{6,32}$")
SCHEMA_VERSION = "production-user-activation-readiness.v1"


class ActivationReadinessError(RuntimeError):
    pass


def _digest(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _evidence_path(active_env: Mapping[str, str]) -> Path:
    raw = active_env.get("USER_ACTIVATION_READINESS_OUTPUT", "").strip()
    if not raw:
        raise ActivationReadinessError("USER_ACTIVATION_READINESS_OUTPUT is required")
    path = Path(raw)
    if not path.is_absolute() or path.parent.resolve(strict=False) != EVIDENCE_ROOT:
        raise ActivationReadinessError(
            f"USER_ACTIVATION_READINESS_OUTPUT must be directly under {EVIDENCE_ROOT}"
        )
    run_id = active_env.get("USER_ACTIVATION_READINESS_RUN_ID", "")
    if not RUN_ID_PATTERN.fullmatch(run_id):
        raise ActivationReadinessError(
            "USER_ACTIVATION_READINESS_RUN_ID must be a UTC timestamp plus safe suffix"
        )
    if path.name != f"user-activation-readiness-{run_id}.json":
        raise ActivationReadinessError("evidence filename must bind the exact run ID")
    if path.exists() or path.is_symlink():
        raise ActivationReadinessError("evidence output must be a new non-symlink path")
    return path


def validate_control_plane(active_env: Mapping[str, str]) -> Path:
    if active_env.get("ENV") != "prod":
        raise ActivationReadinessError("ENV=prod is required")
    if active_env.get("TARGET_DB") != TARGET_DATABASE:
        raise ActivationReadinessError("TARGET_DB must be sc_production")
    if active_env.get("PROD_READONLY_VERIFY") != "1":
        raise ActivationReadinessError("PROD_READONLY_VERIFY=1 is required")
    return _evidence_path(active_env)


def _enable_read_only(odoo_env: Any) -> dict[str, str]:
    odoo_env.cr.execute("SET TRANSACTION READ ONLY")
    odoo_env.cr.execute("SHOW transaction_read_only")
    row = odoo_env.cr.fetchone()
    value = str(row[0] if row else "").strip().lower()
    if value not in {"on", "true", "1"}:
        raise ActivationReadinessError("database transaction is not read-only")
    return {"transaction_read_only": value, "verification": "PASS"}


def _model(odoo_env: Any, name: str) -> Any:
    try:
        return odoo_env[name].sudo()
    except KeyError as exc:
        raise ActivationReadinessError(f"required activation model unavailable: {name}") from exc


def collect_snapshot(odoo_env: Any) -> dict[str, Any]:
    transaction = _enable_read_only(odoo_env)
    if getattr(odoo_env.cr, "dbname", "") != TARGET_DATABASE:
        raise ActivationReadinessError("live database identity must be sc_production")

    module = _model(odoo_env, "ir.module.module").search([("name", "=", "smart_core")], limit=1)
    config = _model(odoo_env, "ir.config_parameter")
    users = _model(odoo_env, "res.users")
    credentials = _model(odoo_env, "sc.user.activation.credential")
    batches = _model(odoo_env, "sc.user.activation.batch")
    delivery_audits = _model(odoo_env, "sc.user.activation.delivery.audit")

    runtime_tenant = str(config.get_param("sc.runtime.tenant_key", "") or "").strip()
    runtime_environment = str(
        config.get_param("sc.runtime.environment_type", "") or ""
    ).strip()
    public_user = odoo_env.ref("base.public_user", raise_if_not_found=False)
    portal_group = odoo_env.ref("base.group_portal", raise_if_not_found=False)
    activation_admin_group = odoo_env.ref(
        "smart_core.group_smart_core_user_activation_admin", raise_if_not_found=False
    )

    candidates = users.with_context(active_test=False).search(
        [("active", "=", True), ("share", "=", False), ("login", "!=", "admin")]
    )
    eligible = candidates.filtered(
        lambda user: (not public_user or user != public_user)
        and (not portal_group or portal_group not in user.groups_id)
    )
    activation_admin_count = 0
    if activation_admin_group:
        activation_admin_count = len(
            activation_admin_group.users.filtered(lambda user: user.active and not user.share)
        )

    snapshot = {
        "database": TARGET_DATABASE,
        "transaction": transaction,
        "smart_core_state": str(module.state if len(module) == 1 else "missing"),
        "runtime_environment": runtime_environment,
        "runtime_tenant_configured": bool(runtime_tenant),
        "runtime_tenant_fingerprint": _digest({"tenant_key": runtime_tenant}) if runtime_tenant else "",
        "activation_admin_count": activation_admin_count,
        "eligible_internal_user_count": len(eligible),
        "active_batch_count": batches.search_count(
            [("purpose", "=", "enterprise_activation"), ("state", "=", "active")]
        ),
        "pending_credential_count": credentials.search_count(
            [("purpose", "=", "enterprise_activation"), ("state", "=", "pending")]
        ),
        "used_credential_count": credentials.search_count(
            [("purpose", "=", "enterprise_activation"), ("state", "=", "used")]
        ),
        "delivery_audit_count": delivery_audits.search_count([]),
    }
    odoo_env.cr.rollback()
    return snapshot


def evaluate(snapshot: Mapping[str, Any], *, run_id: str) -> dict[str, Any]:
    checks = {
        "database_exact": snapshot.get("database") == TARGET_DATABASE,
        "transaction_read_only": (snapshot.get("transaction") or {}).get("verification") == "PASS",
        "smart_core_installed": snapshot.get("smart_core_state") == "installed",
        "runtime_environment_production": snapshot.get("runtime_environment") == "production",
        "runtime_tenant_bound": bool(snapshot.get("runtime_tenant_configured")),
        "activation_admin_available": int(snapshot.get("activation_admin_count") or 0) >= 1,
        "pilot_user_available": int(snapshot.get("eligible_internal_user_count") or 0) >= 1,
    }
    blockers = sorted(name for name, passed in checks.items() if not passed)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "run_id": run_id,
        "status": "READY_FOR_PILOT_SELECTION" if not blockers else "NOT_READY",
        "checks": checks,
        "blockers": blockers,
        "counts": {
            key: int(snapshot.get(key) or 0)
            for key in (
                "activation_admin_count",
                "eligible_internal_user_count",
                "active_batch_count",
                "pending_credential_count",
                "used_credential_count",
                "delivery_audit_count",
            )
        },
        "runtime": {
            "environment": str(snapshot.get("runtime_environment") or ""),
            "tenant_configured": bool(snapshot.get("runtime_tenant_configured")),
            "tenant_fingerprint": str(snapshot.get("runtime_tenant_fingerprint") or ""),
        },
        "privacy": {
            "identity_values_recorded": False,
            "contact_values_recorded": False,
            "credential_values_recorded": False,
        },
        "write_audit": {"database_write_statement_count": 0, "database_changed": False},
    }


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main() -> int:
    try:
        evidence_path = validate_control_plane(os.environ)
        if "env" not in globals():
            print("[production.user_activation.readiness] PREFLIGHT PASS")
            return 0
        snapshot = collect_snapshot(globals()["env"])
        report = evaluate(
            snapshot, run_id=os.environ["USER_ACTIVATION_READINESS_RUN_ID"]
        )
        _atomic_json(evidence_path, report)
        print(
            "[production.user_activation.readiness] "
            + json.dumps(report, ensure_ascii=True, sort_keys=True)
        )
        return 0 if report["status"] == "READY_FOR_PILOT_SELECTION" else 3
    except ActivationReadinessError as exc:
        raise SystemExit(f"[production.user_activation.readiness] BLOCKED: {exc}") from exc


if __name__ == "__main__":
    raise SystemExit(main())
