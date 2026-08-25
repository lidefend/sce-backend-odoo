"""Resolve the governed local.dev reporting target without writes."""

import hashlib
import json


def xmlid(record):
    return record.get_external_id().get(record.id, "")


user = env.ref("smart_construction_demo.sc_demo_user_test_admin")
security_user = env.ref("smart_construction_demo.user_demo_role_project_a_member")
if not user.active or not security_user.active:
    raise RuntimeError("governed reporting principals are unavailable")
menu = env.ref("smart_construction_core.menu_sc_project_operation_statistics_report")
action = env.ref("smart_construction_core.action_sc_project_operation_statistics_report")
if menu.action != action or action.res_model != "sc.operating.metrics.project":
    raise RuntimeError("reporting menu/action authority mismatch")
security_menu = env.ref("smart_construction_core.menu_sc_product_tax_report_v1")
security_action = env.ref("smart_construction_core.action_sc_product_tax_report_v1")
if security_menu.action != security_action or security_action.res_model != "sc.tax.filing":
    raise RuntimeError("reporting security menu/action authority mismatch")
record_env = (
    env["sc.operating.metrics.project"].with_user(user).with_company(user.company_id)
    .with_context(allowed_company_ids=user.company_ids.ids, active_test=False)
)
visible_ids = record_env.search([], order="id").ids
user_menu_ids = set(env["ir.ui.menu"].with_user(user)._visible_menu_ids())
security_menu_ids = set(env["ir.ui.menu"].with_user(security_user)._visible_menu_ids())
payload = {
    "database": env.cr.dbname,
    "user": {"id": int(user.id), "login": user.login, "xmlid": xmlid(user)},
    "security_user": {"id": int(security_user.id), "login": security_user.login, "xmlid": xmlid(security_user)},
    "menu": {"id": int(menu.id), "xmlid": xmlid(menu)},
    "action": {"id": int(action.id), "xmlid": xmlid(action), "model": action.res_model},
    "security_menu": {"id": int(security_menu.id), "xmlid": xmlid(security_menu)},
    "security_action": {
        "id": int(security_action.id), "xmlid": xmlid(security_action), "model": security_action.res_model,
    },
    "visible_record_count": len(visible_ids),
    "user_menu_visible": int(menu.id) in user_menu_ids,
    "security_menu_visible": int(security_menu.id) in security_menu_ids,
    "business_fingerprint": hashlib.sha256(
        json.dumps({"visible_ids": visible_ids}, sort_keys=True).encode("utf-8")
    ).hexdigest(),
}
print("LOCAL_DEV_REPORTING_CENTER_JSON=%s" % json.dumps(payload, ensure_ascii=True, separators=(",", ":")))
