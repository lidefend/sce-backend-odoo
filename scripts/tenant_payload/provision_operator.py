from __future__ import annotations

import hashlib
import json
import os

from odoo.exceptions import UserError


DATA_OPERATOR_XMLID = "smart_core.group_smart_core_data_operator"
IMPORTER_XMLID = "smart_core.group_smart_core_tenant_payload_importer"


def _required(name):
    value = str(os.environ.get(name, "") or "").strip()
    if not value:
        raise UserError(f"TPV1_ENV_REQUIRED:{name}")
    return value


def _required_xmlid_list(name):
    raw = _required(name)
    try:
        values = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise UserError(f"TPV1_GROUP_SET_JSON_INVALID:{name}") from exc
    if (
        not isinstance(values, list)
        or any(not isinstance(value, str) or not value.strip() for value in values)
        or len(values) != len(set(values))
    ):
        raise UserError(f"TPV1_GROUP_SET_INVALID:{name}")
    return tuple(values)


def _resolve_groups(xmlids, rule):
    records = []
    for xmlid in xmlids:
        record = env.ref(xmlid, raise_if_not_found=False)
        if not record or record._name != "res.groups":
            raise UserError(rule)
        records.append(record)
    if len({record.id for record in records}) != len(records):
        raise UserError(rule)
    return records


def _group_xmlids(group_ids):
    rows = env["ir.model.data"].sudo().search(
        [("model", "=", "res.groups"), ("res_id", "in", sorted(group_ids))]
    )
    by_id = {}
    for row in rows:
        by_id.setdefault(row.res_id, []).append(f"{row.module}.{row.name}")
    if any(len(by_id.get(group_id, ())) != 1 for group_id in group_ids):
        raise UserError("TPV1_IMPORT_OPERATOR_GROUP_XMLID_NOT_UNIQUE")
    return {by_id[group_id][0] for group_id in group_ids}


def _transitive_implied_ids(groups):
    pending = list(groups.mapped("implied_ids"))
    result = set()
    while pending:
        group = pending.pop()
        if group.id in result:
            continue
        result.add(group.id)
        pending.extend(group.implied_ids)
    return result


identity_type = _required("SC_TENANT_PAYLOAD_OPERATOR_IDENTITY_TYPE")
identity_key = _required("SC_TENANT_PAYLOAD_OPERATOR_IDENTITY_KEY")
tenant_key = _required("SC_TENANT_PAYLOAD_TENANT_KEY")
direct_xmlids = _required_xmlid_list("SC_TENANT_PAYLOAD_DIRECT_GRANT_TARGETS")
declared_closure_xmlids = _required_xmlid_list(
    "SC_TENANT_PAYLOAD_TRANSITIVE_IMPLIED_CLOSURE"
)
required_existing_xmlids = _required_xmlid_list(
    "SC_TENANT_PAYLOAD_REQUIRED_EXISTING_GROUPS"
)
expected_direct_xmlids = _required_xmlid_list(
    "SC_TENANT_PAYLOAD_EXPECTED_DIRECT_ADDITIONS"
)
expected_effective_xmlids = _required_xmlid_list(
    "SC_TENANT_PAYLOAD_EXPECTED_EFFECTIVE_ADDITIONS"
)
expected_undeclared_xmlids = _required_xmlid_list(
    "SC_TENANT_PAYLOAD_EXPECTED_UNDECLARED_ADDITIONS"
)
customer_modules = tuple(
    item.strip()
    for item in _required("SC_PRODUCTION_CUSTOMER_MODULES").split(",")
    if item.strip()
)
expected_company_scope = int(
    _required("SC_TENANT_PAYLOAD_EXPECTED_COMPANY_SCOPE")
)
grant_scope_version = int(_required("SC_TENANT_PAYLOAD_GRANT_SCOPE_VERSION"))
approved_by = _required("SC_TENANT_PAYLOAD_APPROVED_BY")
allowlist = {
    item.strip()
    for item in _required("SC_TENANT_PAYLOAD_DB_ALLOWLIST").split(",")
    if item.strip()
}

if env.cr.dbname not in allowlist:
    raise UserError("TPV1_DATABASE_NOT_ALLOWLISTED")
if identity_type != "external_xmlid" or grant_scope_version != 3:
    raise UserError("TPV1_IMPORT_OPERATOR_IDENTITY_CONTRACT_INVALID")
if (
    direct_xmlids != (IMPORTER_XMLID,)
    or expected_direct_xmlids != direct_xmlids
    or expected_effective_xmlids != direct_xmlids
    or expected_undeclared_xmlids
    or DATA_OPERATOR_XMLID
    in {
        *direct_xmlids,
        *declared_closure_xmlids,
        *required_existing_xmlids,
        *expected_effective_xmlids,
    }
):
    raise UserError("TPV1_NARROW_IMPORT_OPERATOR_CONTRACT_INVALID")
if env["ir.config_parameter"].sudo().get_param(
    "sc.tenant.bound_tenant_key"
) != tenant_key:
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

direct_groups = _resolve_groups(
    direct_xmlids, "TPV1_IMPORT_OPERATOR_DIRECT_GROUP_NOT_UNIQUE"
)
required_existing_groups = _resolve_groups(
    required_existing_xmlids,
    "TPV1_IMPORT_OPERATOR_REQUIRED_GROUP_NOT_UNIQUE",
)
_resolve_groups(
    expected_effective_xmlids,
    "TPV1_IMPORT_OPERATOR_EXPECTED_GROUP_NOT_UNIQUE",
)

actual_closure_ids = _transitive_implied_ids(
    env["res.groups"].browse([group.id for group in direct_groups])
)
actual_closure_xmlids = _group_xmlids(actual_closure_ids)
if actual_closure_xmlids != set(declared_closure_xmlids):
    raise UserError("TPV1_IMPORT_OPERATOR_TRANSITIVE_CLOSURE_DRIFT")
if DATA_OPERATOR_XMLID in actual_closure_xmlids:
    raise UserError("TPV1_IMPORT_OPERATOR_DATA_OPERATOR_FORBIDDEN")

user_state_before = (
    operator.active,
    operator.login,
    operator.name,
    operator.company_id.id,
    tuple(sorted(operator.company_ids.ids)),
)
before_groups = set(operator.groups_id.ids)
if any(group.id not in before_groups for group in required_existing_groups):
    raise UserError("TPV1_IMPORT_OPERATOR_REQUIRED_EXISTING_GROUP_MISSING")
if any(
    env.ref(DATA_OPERATOR_XMLID).id == group_id for group_id in before_groups
):
    # The approved baseline does not treat data_operator as a prerequisite.
    raise UserError("TPV1_IMPORT_OPERATOR_DATA_OPERATOR_BASELINE_DRIFT")

direct_ids = {group.id for group in direct_groups}
current_direct = direct_ids & before_groups
if current_direct not in (set(), direct_ids):
    raise UserError("TPV1_IMPORT_OPERATOR_MEMBERSHIP_PRECONDITION_DRIFT")
changed = not current_direct
if changed:
    operator.write({"groups_id": [(4, group.id) for group in direct_groups]})

after_groups = set(operator.groups_id.ids)
if not direct_ids <= after_groups:
    raise UserError("TPV1_IMPORT_OPERATOR_MEMBERSHIP_POSTCONDITION_FAILED")
if before_groups - after_groups:
    raise UserError("TPV1_IMPORT_OPERATOR_EXISTING_GROUP_REMOVED")

actual_addition_ids = after_groups - before_groups
actual_addition_xmlids = _group_xmlids(actual_addition_ids)
expected_additions = set(expected_effective_xmlids) if changed else set()
if actual_addition_xmlids != expected_additions:
    raise UserError("TPV1_IMPORT_OPERATOR_UNDECLARED_MEMBERSHIP_CHANGED")
if DATA_OPERATOR_XMLID in actual_addition_xmlids:
    raise UserError("TPV1_IMPORT_OPERATOR_DATA_OPERATOR_FORBIDDEN")

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
            "schema_version": "tenant_payload_operator_grant.v3",
            "status": "PASS",
            "database": env.cr.dbname,
            "operator_identity_type": identity_type,
            "operator_identity_key": identity_key,
            "direct_grant_targets": list(direct_xmlids),
            "transitive_implied_closure": sorted(actual_closure_xmlids),
            "required_existing_groups": list(required_existing_xmlids),
            "direct_membership_additions": list(
                expected_direct_xmlids if changed else ()
            ),
            "effective_group_additions": sorted(actual_addition_xmlids),
            "undeclared_group_additions": [],
            "data_operator_added": False,
            "changed": changed,
            "company_scope_count": len(operator.company_ids),
            "approval_fingerprint": hashlib.sha256(
                approved_by.encode("utf-8")
            ).hexdigest()[:12],
        },
        sort_keys=True,
    )
)
