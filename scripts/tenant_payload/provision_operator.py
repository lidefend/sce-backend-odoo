from __future__ import annotations

import hashlib
import json
import os

from odoo.exceptions import UserError


def _required(name):
    value = str(os.environ.get(name, "") or "").strip()
    if not value:
        raise UserError(f"TPV1_ENV_REQUIRED:{name}")
    return value


identity_type = _required("SC_TENANT_PAYLOAD_OPERATOR_IDENTITY_TYPE")
identity_key = _required("SC_TENANT_PAYLOAD_OPERATOR_IDENTITY_KEY")
tenant_key = _required("SC_TENANT_PAYLOAD_TENANT_KEY")
target_group_xmlid = _required("SC_TENANT_PAYLOAD_TARGET_GROUP_XMLID")
customer_modules = tuple(
    item.strip()
    for item in _required("SC_PRODUCTION_CUSTOMER_MODULES").split(",")
    if item.strip()
)
expected_before = int(_required("SC_TENANT_PAYLOAD_EXPECTED_MEMBERSHIP_BEFORE"))
expected_after = int(_required("SC_TENANT_PAYLOAD_EXPECTED_MEMBERSHIP_AFTER"))
expected_company_scope = int(_required("SC_TENANT_PAYLOAD_EXPECTED_COMPANY_SCOPE"))
grant_scope_version = int(_required("SC_TENANT_PAYLOAD_GRANT_SCOPE_VERSION"))
approved_by = _required("SC_TENANT_PAYLOAD_APPROVED_BY")
allowlist = {item.strip() for item in _required("SC_TENANT_PAYLOAD_DB_ALLOWLIST").split(",") if item.strip()}
if env.cr.dbname not in allowlist:
    raise UserError("TPV1_DATABASE_NOT_ALLOWLISTED")
if identity_type != "external_xmlid" or grant_scope_version != 1:
    raise UserError("TPV1_IMPORT_OPERATOR_IDENTITY_CONTRACT_INVALID")
if env["ir.config_parameter"].sudo().get_param("sc.tenant.bound_tenant_key") != tenant_key:
    raise UserError("TPV1_DATABASE_TENANT_UNAUTHORIZED")
customer_module = env["ir.module.module"].sudo().search(
    [("name", "in", list(customer_modules))]
)
if (
    not customer_modules
    or len(customer_module) != len(customer_modules)
    or set(customer_module.mapped("name")) != set(customer_modules)
    or any(state != "installed" for state in customer_module.mapped("state"))
):
    raise UserError("TPV1_CUSTOMER_MODULE_CONTRACT_MISMATCH")
snapshot = env["sc.edition.release.snapshot"].sudo().search(
    [
        ("product_key", "=", "construction.standard"),
        ("state", "=", "released"),
        ("is_active", "=", True),
        ("active", "=", True),
    ]
)
if len(snapshot) != 1:
    raise UserError("TPV1_PLATFORM_SNAPSHOT_CONTRACT_MISMATCH")
operator = env.ref(identity_key, raise_if_not_found=False)
if not operator or operator._name != "res.users" or not operator.active:
    raise UserError("TPV1_IMPORT_OPERATOR_IDENTITY_NOT_UNIQUE")
if len(operator.company_ids) != expected_company_scope:
    raise UserError("TPV1_IMPORT_OPERATOR_COMPANY_SCOPE_DRIFT")
group = env.ref(target_group_xmlid, raise_if_not_found=False)
if not group or group._name != "res.groups":
    raise UserError("TPV1_IMPORT_OPERATOR_GROUP_NOT_UNIQUE")
user_state_before = (
    operator.active,
    operator.login,
    operator.name,
    operator.company_id.id,
    tuple(sorted(operator.company_ids.ids)),
)
before_groups = set(operator.groups_id.ids)
current = int(group.id in before_groups)
if current not in {expected_before, expected_after}:
    raise UserError("TPV1_IMPORT_OPERATOR_MEMBERSHIP_PRECONDITION_DRIFT")
changed = current == expected_before
if changed:
    operator.write({"groups_id": [(4, group.id)]})
after_groups = set(operator.groups_id.ids)
if int(group.id in after_groups) != expected_after:
    raise UserError("TPV1_IMPORT_OPERATOR_MEMBERSHIP_POSTCONDITION_FAILED")
if after_groups - before_groups != ({group.id} if changed else set()):
    raise UserError("TPV1_IMPORT_OPERATOR_UNRELATED_MEMBERSHIP_CHANGED")
user_state_after = (
    operator.active,
    operator.login,
    operator.name,
    operator.company_id.id,
    tuple(sorted(operator.company_ids.ids)),
)
if user_state_after != user_state_before:
    raise UserError("TPV1_IMPORT_OPERATOR_UNRELATED_FIELDS_CHANGED")
env.cr.commit()
print(
    json.dumps(
        {
            "schema_version": "tenant_payload_v1",
            "status": "PASS",
            "database": env.cr.dbname,
            "operator_identity_type": identity_type,
            "operator_identity_key": identity_key,
            "target_group_xmlid": target_group_xmlid,
            "membership_before": current,
            "membership_after": int(group.id in after_groups),
            "changed": changed,
            "unrelated_membership_changes": 0,
            "company_scope_count": len(operator.company_ids),
            "approval_fingerprint": hashlib.sha256(approved_by.encode("utf-8")).hexdigest()[:12],
        },
        sort_keys=True,
    )
)
