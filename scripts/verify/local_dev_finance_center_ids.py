"""Resolve the governed local.dev finance target without writes."""

import hashlib
import json


def xmlid(record):
    return record.get_external_id().get(record.id, "")


user = env.ref("smart_construction_demo.user_demo_role_finance")
security_user = env.ref("smart_construction_demo.user_demo_e2e_smoke")
if not user.active or not security_user.active:
    raise RuntimeError("governed finance principals are unavailable")
menu = env.ref("smart_construction_core.menu_sc_receipt_income")
action = env.ref("smart_construction_core.action_sc_receipt_income")
if menu.action != action or action.res_model != "sc.receipt.income":
    raise RuntimeError("finance menu/action authority mismatch")
record_env = (
    env["sc.receipt.income"].with_user(user).with_company(user.company_id)
    .with_context(allowed_company_ids=user.company_ids.ids, active_test=False)
)
visible_ids = record_env.search([], order="id").ids
payload = {
    "database": env.cr.dbname,
    "user": {"id": int(user.id), "login": user.login, "xmlid": xmlid(user)},
    "security_user": {
        "id": int(security_user.id), "login": security_user.login, "xmlid": xmlid(security_user),
    },
    "menu": {"id": int(menu.id), "xmlid": xmlid(menu)},
    "action": {"id": int(action.id), "xmlid": xmlid(action), "model": action.res_model},
    "visible_record_count": len(visible_ids),
    "business_fingerprint": hashlib.sha256(
        json.dumps({"visible_ids": visible_ids}, sort_keys=True).encode("utf-8")
    ).hexdigest(),
}
print("LOCAL_DEV_FINANCE_CENTER_JSON=%s" % json.dumps(payload, ensure_ascii=True, separators=(",", ":")))
