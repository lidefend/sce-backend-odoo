"""Resolve one governed local.dev material-domain browser target without writes."""

import hashlib
import json


def xmlid(record):
    return record.get_external_id().get(record.id, "")


users = env["res.users"].sudo().search([("login", "=", "demo_full"), ("active", "=", True)])
if len(users) != 1:
    raise RuntimeError("governed demo_full principal is not uniquely available")
user = users.ensure_one()
if not user.has_group(
    "smart_construction_core.group_sc_cap_material_manager"
):
    raise RuntimeError("governed material-manager principal is unavailable")
security_user = env.ref("smart_construction_demo.user_demo_project_read")
menu = env.ref("smart_construction_core.menu_sc_material_inbound")
action = env.ref("smart_construction_core.action_sc_material_inbound_handling")

record_env = (
    env["sc.material.inbound"]
    .with_user(user)
    .with_company(user.company_id)
    .with_context(allowed_company_ids=user.company_ids.ids, active_test=False)
)
record = record_env.search([], order="id desc", limit=1)
if not record:
    raise RuntimeError("governed local.dev material inbound is unavailable")
record.check_access_rights("read")
record.check_access_rule("read")
record.check_access_rights("write")
record.check_access_rule("write")
if menu.action != action or action.res_model != "sc.material.inbound":
    raise RuntimeError("material menu/action authority mismatch")

fingerprint_payload = {
    "id": int(record.id),
    "write_date": record.write_date.isoformat() if record.write_date else "",
    "state": str(record.state or ""),
    "name": str(record.name or ""),
    "line_count": len(record.line_ids),
    "note": str(record.note or ""),
}
payload = {
    "database": env.cr.dbname,
    "user": {"id": int(user.id), "login": user.login, "xmlid": xmlid(user)},
    "security_user": {
        "id": int(security_user.id),
        "login": security_user.login,
        "xmlid": xmlid(security_user),
    },
    "menu": {"id": int(menu.id), "xmlid": xmlid(menu)},
    "action": {"id": int(action.id), "xmlid": xmlid(action)},
    "record": {
        "id": int(record.id),
        "xmlid": xmlid(record),
        "name": str(record.name or ""),
        "state": str(record.state or ""),
    },
    "business_fingerprint": hashlib.sha256(
        json.dumps(fingerprint_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest(),
}
print(
    "LOCAL_DEV_MATERIAL_DOMAIN_JSON=%s"
    % json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
)
