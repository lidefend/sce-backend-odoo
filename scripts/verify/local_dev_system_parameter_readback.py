"""Read existing governed principals and parameter authority; never mutate data."""
from odoo.addons.smart_construction_core.services.product_system_parameter_change import read_parameter_value

# Executed after the existing principal resolver in the same read-only shell.
actor_env = env["res.company"].with_user(user).with_company(user.company_id).env
facts = {
    "values": {key: read_parameter_value(actor_env, key) for key in ("approval_mode", "default_payment_terms")},
    "changes": env["sc.product.system.parameter.change"].sudo().search_read(
        [("company_id", "=", user.company_id.id)], ["id", "state", "parameter_key", "proposed_value", "previous_value", "user_id"], order="id"),
}
facts["purchase_default"] = actor_env["purchase.order"].default_get(["payment_term_id"]).get("payment_term_id", False)
facts["payment_terms"] = {key: actor_env.ref(xmlid).id for key, xmlid in {
    "net30": "account.account_payment_term_30days",
    "net60": "smart_construction_core.account_payment_term_60days",
    "advance": "account.account_payment_term_immediate",
}.items()}
Policy = actor_env["sc.approval.policy"].sudo()
policy = Policy.get_active_policy("payment.request", company=actor_env.company)
def config_rows(records):
    names = sorted(name for name, field in records._fields.items()
                   if field.store and not field.compute and field.type not in ("binary", "one2many")
                   and name not in ("create_date", "write_date", "create_uid", "write_uid"))
    return records.read(names)
facts["approval_configuration"] = {
    "policy": config_rows(policy),
    "steps": config_rows(policy.step_ids),
    "definitions": config_rows(policy.step_ids.mapped("tier_definition_id").sudo()),
}
facts["approval_required"] = Policy.is_approval_required("payment.request", company=actor_env.company)
from odoo.addons.smart_construction_core.handlers.product_system_parameter_catalog import CONFIG_ADMIN_GROUPS
security_user = env["res.users"].browse(payload["security_user"]["id"]).exists()
if len(security_user) != 1:
    raise RuntimeError("resolved security principal is unavailable")
payload["security_user"]["parameter_admin"] = any(security_user.has_group(group) for group in CONFIG_ADMIN_GROUPS)
payload["parameter_facts"] = facts
payload["business_fingerprint"] = hashlib.sha256(json.dumps(facts, sort_keys=True).encode()).hexdigest()
print("LOCAL_DEV_BASE_CONFIGURATION_DOMAIN_JSON=" + json.dumps(payload))
