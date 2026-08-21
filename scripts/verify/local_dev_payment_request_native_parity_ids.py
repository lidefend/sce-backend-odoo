"""Resolve one governed local.dev payment-request parity target without writes."""

import hashlib
import json


def xmlid(record):
    return record.get_external_id().get(record.id, "")


user = env.ref("smart_construction_demo.user_demo_role_finance")
menu = env.ref("smart_construction_core.menu_sc_user_payment_apply")
action = env.ref("smart_construction_core.action_payment_request_user_payment_apply")
view = env.ref("smart_construction_core.view_payment_request_form")
candidate = env.ref("smart_construction_demo.sc_demo_payment_request_069_pay")
payment_env = env["payment.request"].with_user(user).with_company(user.company_id).with_context(
    allowed_company_ids=user.company_ids.ids,
    active_test=False,
)
record = payment_env.browse(candidate.id).exists()
if not record:
    raise RuntimeError("governed local.dev payment request is not readable by demo_role_finance")
record.check_access_rights("read")
record.check_access_rule("read")
if menu.action != action or action.res_model != "payment.request":
    raise RuntimeError("payment request menu/action authority mismatch")
if view.model != "payment.request" or view.type != "form":
    raise RuntimeError("payment request native form authority mismatch")

fingerprint_payload = {
    "id": int(record.id),
    "write_date": record.write_date.isoformat() if record.write_date else "",
    "state": str(record.state or ""),
    "name": str(record.name or ""),
    "amount": float(record.amount or 0.0),
    "payment_count": int(env["sc.payment.execution"].with_user(user).search_count([
        ("payment_request_id", "=", record.id),
    ])),
}
payload = {
    "database": env.cr.dbname,
    "user": {"id": int(user.id), "login": user.login, "xmlid": xmlid(user)},
    "menu": {"id": int(menu.id), "xmlid": xmlid(menu)},
    "action": {"id": int(action.id), "xmlid": xmlid(action)},
    "view": {"id": int(view.id), "xmlid": xmlid(view)},
    "record": {"id": int(record.id), "xmlid": xmlid(record), "name": record.name},
    "business_fingerprint": hashlib.sha256(
        json.dumps(fingerprint_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest(),
}
print("LOCAL_DEV_PAYMENT_PARITY_JSON=%s" % json.dumps(payload, ensure_ascii=True, separators=(",", ":")))
