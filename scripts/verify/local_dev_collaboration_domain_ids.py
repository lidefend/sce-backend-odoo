"""Resolve the governed local.dev collaboration list target without writes."""

import hashlib
import json


def xmlid(record):
    return record.get_external_id().get(record.id, "")


user = env.ref("smart_construction_demo.sc_demo_user_test_admin")
if not user.active or not user.has_group(
    "smart_construction_core.group_sc_cap_project_read"
):
    raise RuntimeError("governed collaboration principal is unavailable")
security_user = env.ref("smart_construction_demo.user_demo_role_finance")
menu = env.ref("smart_construction_core.menu_sc_product_message_notification_v1")
action = env.ref("smart_construction_core.action_sc_product_message_notification_v1")
if menu.action != action or action.res_model != "mail.notification":
    raise RuntimeError("collaboration menu/action authority mismatch")

record_env = (
    env["mail.notification"]
    .with_user(user)
    .with_company(user.company_id)
    .with_context(allowed_company_ids=user.company_ids.ids, active_test=False)
)
visible_ids = record_env.search(
    [("sc_is_current_recipient", "=", True), ("notification_type", "=", "inbox")],
    order="sc_message_date desc, id desc",
).ids
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
        "model": action.res_model,
        "views": [
            [int(view_id or 0), str(view_type or "")]
            for view_id, view_type in (action.views or [])
        ],
    },
    "visible_record_count": len(visible_ids),
    "business_fingerprint": hashlib.sha256(
        json.dumps({"visible_ids": visible_ids}, sort_keys=True).encode("utf-8")
    ).hexdigest(),
}
print(
    "LOCAL_DEV_COLLABORATION_DOMAIN_JSON=%s"
    % json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
)
