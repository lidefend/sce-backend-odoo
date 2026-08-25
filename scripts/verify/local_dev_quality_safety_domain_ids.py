"""Resolve one governed local.dev quality-safety browser target without writes."""

import hashlib
import json


def xmlid(record):
    return record.get_external_id().get(record.id, "")


users = env["res.users"].sudo().search([("login", "=", "demo_full"), ("active", "=", True)])
if len(users) != 1:
    raise RuntimeError("governed demo_full principal is not uniquely available")
user = users.ensure_one()
if not user.has_group("smart_construction_core.group_sc_cap_project_manager"):
    raise RuntimeError("governed project-manager principal is unavailable")
security_user = env.ref("smart_construction_demo.user_demo_role_finance")
menu = env.ref("smart_construction_core.menu_sc_safety_issue")
action = env.ref("smart_construction_core.action_sc_safety_issue")

record_env = (
    env["sc.safety.issue"]
    .with_user(user)
    .with_company(user.company_id)
    .with_context(allowed_company_ids=user.company_ids.ids, active_test=False)
)
record = env.ref("smart_construction_demo.sc_demo_safety_issue_089_high_support").with_env(record_env.env)
record.check_access_rights("read")
record.check_access_rule("read")
record.check_access_rights("write")
record.check_access_rule("write")
if menu.action != action or action.res_model != "sc.safety.issue":
    raise RuntimeError("quality-safety menu/action authority mismatch")

fingerprint_payload = {
    "id": int(record.id),
    "write_date": record.write_date.isoformat() if record.write_date else "",
    "state": str(record.state or ""),
    "name": str(record.name or ""),
    "description": str(record.description or ""),
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
    "action": {
        "id": int(action.id),
        "xmlid": xmlid(action),
        "views": [
            [int(view_id or 0), str(view_type or "")]
            for view_id, view_type in (action.views or [])
        ],
    },
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
    "LOCAL_DEV_QUALITY_SAFETY_DOMAIN_JSON=%s"
    % json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
)
