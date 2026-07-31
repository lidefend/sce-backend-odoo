from __future__ import annotations

import json
import os
from pathlib import Path

from odoo import api
from odoo.exceptions import AccessError, UserError

from odoo.addons.smart_core.utils.tenant_payload_import_service import (
    TenantPayloadImportError,
    TenantPayloadImportService,
    TenantPayloadInterrupted,
)


def _required(name: str) -> str:
    value = str(os.environ.get(name, "") or "").strip()
    if not value:
        raise UserError(f"TPV1_ENV_REQUIRED:{name}")
    return value


action = _required("SC_TENANT_PAYLOAD_ACTION")
tenant_key = _required("SC_TENANT_PAYLOAD_TENANT_KEY")
operator_identity_type = _required("SC_TENANT_PAYLOAD_OPERATOR_IDENTITY_TYPE")
operator_identity_key = _required("SC_TENANT_PAYLOAD_OPERATOR_IDENTITY_KEY")
try:
    direct_grant_targets = json.loads(
        _required("SC_TENANT_PAYLOAD_DIRECT_GRANT_TARGETS")
    )
except json.JSONDecodeError as exc:
    raise UserError("TPV1_NARROW_IMPORT_OPERATOR_CONTRACT_INVALID") from exc
maintenance_capability = _required(
    "SC_TENANT_PAYLOAD_MAINTENANCE_CAPABILITY"
)
allowed_databases = {item.strip() for item in _required("SC_TENANT_PAYLOAD_DB_ALLOWLIST").split(",") if item.strip()}
if env.cr.dbname not in allowed_databases:
    raise UserError("TPV1_DATABASE_NOT_ALLOWLISTED")

lock_namespace = f"tenant_payload_v1:{env.cr.dbname}"
env.cr.execute(
    "SELECT pg_try_advisory_lock(hashtext(%s), hashtext(%s))",
    (lock_namespace, tenant_key),
)
if not bool(env.cr.fetchone()[0]):
    raise UserError("TPV1_EXCLUSIVE_IMPORT_LOCK_UNAVAILABLE")

bound_tenant = str(env["ir.config_parameter"].get_param("sc.tenant.bound_tenant_key", "") or "").strip()
if bound_tenant != tenant_key:
    raise UserError("TPV1_DATABASE_TENANT_UNAUTHORIZED")

if operator_identity_type != "external_xmlid":
    raise UserError("TPV1_IMPORT_OPERATOR_IDENTITY_CONTRACT_INVALID")
operator = env.ref(operator_identity_key, raise_if_not_found=False)
if direct_grant_targets != [
    "smart_core.group_smart_core_tenant_payload_importer"
]:
    raise UserError("TPV1_NARROW_IMPORT_OPERATOR_CONTRACT_INVALID")
group = env.ref(direct_grant_targets[0], raise_if_not_found=False)
if not operator or operator._name != "res.users" or not operator.active:
    raise UserError("TPV1_IMPORT_OPERATOR_IDENTITY_NOT_UNIQUE")
if not group or group._name != "res.groups" or group not in operator.groups_id:
    raise UserError("TPV1_IMPORT_OPERATOR_AUTHORIZATION_MISSING")

operator_env = api.Environment(
    env.cr,
    operator.id,
    {
        "allowed_company_ids": operator.company_ids.ids,
        "sc_tenant_payload_import": True,
        "sc_tenant_payload_maintenance_capability": maintenance_capability,
    },
)
service = TenantPayloadImportService(
    operator_env,
    Path("/mnt/tenant-payload"),
    tenant_key,
    approved_payload_checksum=str(os.environ.get("SC_TENANT_PAYLOAD_APPROVED_CHECKSUM", "") or "").strip(),
)

try:
    if action == "plan":
        report = service.plan()
        if report["status"] != "PASS":
            print(json.dumps(report, ensure_ascii=True, sort_keys=True))
            raise UserError("TPV1_PLAN_HAS_UNAPPROVED_CONFLICTS")
    elif action == "import":
        report = service.import_payload(
            chunk_size=int(os.environ.get("SC_TENANT_PAYLOAD_CHUNK_SIZE", "100") or "100"),
            interrupt_after=str(os.environ.get("SC_TENANT_PAYLOAD_INTERRUPT_AFTER", "") or "").strip(),
            resume_failed=os.environ.get("SC_TENANT_PAYLOAD_RESUME_FAILED") == "1",
        )
    elif action == "verify":
        report = service.verify(finalize_failed=True)
    elif action == "reconcile":
        report = service.reconcile_filestore(
            confirmed=os.environ.get("SC_TENANT_PAYLOAD_CONFIRM_FILESTORE_RECONCILE") == "1"
        )
    else:
        raise UserError("TPV1_ACTION_UNSUPPORTED")
except TenantPayloadInterrupted as exc:
    print(json.dumps({"schema_version": "tenant_payload_v1", "status": "INTERRUPTED", "rule": str(exc)}, sort_keys=True))
    raise
except (TenantPayloadImportError, AccessError, UserError) as exc:
    operator_env.cr.rollback()
    recovery_env = api.Environment(
        env.cr,
        operator.id,
        {
            "allowed_company_ids": operator.company_ids.ids,
            "sc_tenant_payload_import": True,
            "sc_tenant_payload_maintenance_capability": maintenance_capability,
        },
    )
    batch = recovery_env["sc.tenant.payload.import.batch"].search(
        [("tenant_key", "=", tenant_key), ("state", "in", ["importing", "verifying"])],
        order="id desc",
        limit=1,
    )
    if batch:
        batch.action_fail(str(exc))
        recovery_env.cr.commit()
    print(json.dumps({"schema_version": "tenant_payload_v1", "status": "BLOCKER", "rule": str(exc)}, sort_keys=True))
    raise

env.cr.execute(
    "SELECT pg_advisory_unlock(hashtext(%s), hashtext(%s))",
    (lock_namespace, tenant_key),
)
if not bool(env.cr.fetchone()[0]):
    raise UserError("TPV1_EXCLUSIVE_IMPORT_LOCK_RELEASE_FAILED")
report["exclusive_import_lock"] = True
report["import_lock_released"] = True
print(json.dumps(report, ensure_ascii=True, sort_keys=True))
