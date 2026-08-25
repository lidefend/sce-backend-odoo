"""Resolve exact read-only targets for the final frontend public-metric audit."""

import hashlib
import json


def xmlid(record):
    return record.get_external_id().get(record.id, "")


user = env.ref("smart_construction_demo.sc_demo_user_test_admin")
if not user.active:
    raise RuntimeError("governed systemwide acceptance principal is unavailable")

payment_menu = env.ref("smart_construction_core.menu_sc_user_payment_apply")
payment_action = env.ref("smart_construction_core.action_payment_request_user_payment_apply")
payment = env.ref("smart_construction_demo.payment_request_floorplan_demo_record")
project_menu = env.ref("smart_construction_core.menu_sc_product_project_edit_v1")
project_action = env.ref("smart_construction_core.action_sc_product_project_edit_v1")
project_env = (
    env["project.project"].with_user(user).with_company(user.company_id)
    .with_context(allowed_company_ids=user.company_ids.ids, active_test=False)
)
project = project_env.search([], order="id", limit=1)
report_menu = env.ref("smart_construction_core.menu_sc_project_operation_statistics_report")
report_action = env.ref("smart_construction_core.action_sc_project_operation_statistics_report")

if payment_menu.action != payment_action or payment_action.res_model != "payment.request":
    raise RuntimeError("payment public-metric menu/action authority mismatch")
if project_menu.action != project_action or project_action.res_model != "project.project":
    raise RuntimeError("project public-metric menu/action authority mismatch")
if report_menu.action != report_action or report_action.res_model != "sc.operating.metrics.project":
    raise RuntimeError("reporting public-metric menu/action authority mismatch")
if not payment.exists() or not project.exists():
    raise RuntimeError("governed public-metric record sample is unavailable")

visible_menu_ids = set(env["ir.ui.menu"].with_user(user)._visible_menu_ids())
for menu in (payment_menu, project_menu, report_menu):
    if menu.id not in visible_menu_ids:
        raise RuntimeError("governed public-metric menu is not visible: %s" % xmlid(menu))

business_state = {
    "payment": payment.read(["name", "state", "amount"])[0],
    "project": project.read(["name", "active"])[0],
}
payload = {
    "database": env.cr.dbname,
    "user": {"id": int(user.id), "login": user.login, "xmlid": xmlid(user)},
    "targets": [
        {
            "key": "reporting-collection",
            "route": "/a/%s?menu_id=%s" % (report_action.id, report_menu.id),
            "menuId": int(report_menu.id),
            "actionId": int(report_action.id),
            "model": report_action.res_model,
            "pagePattern": "collection",
            "presentationMode": "collection",
            "renderProfile": "readonly",
        },
        {
            "key": "payment-task-edit",
            "route": "/f/payment.request/%s?menu_id=%s&action_id=%s&entry_intent=handling"
            % (payment.id, payment_menu.id, payment_action.id),
            "menuId": int(payment_menu.id),
            "actionId": int(payment_action.id),
            "model": "payment.request",
            "recordId": int(payment.id),
            "pagePattern": "task-form",
            "presentationMode": "task",
            "renderProfile": "edit",
        },
        {
            "key": "project-workspace-readonly",
            "route": "/r/project.project/%s?menu_id=%s&action_id=%s"
            % (project.id, project_menu.id, project_action.id),
            "menuId": int(project_menu.id),
            "actionId": int(project_action.id),
            "model": "project.project",
            "recordId": int(project.id),
            "pagePattern": "workspace-form",
            "presentationMode": "workspace",
            "renderProfile": "readonly",
        },
    ],
    "businessFingerprint": hashlib.sha256(
        json.dumps(business_state, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest(),
}
print("LOCAL_DEV_SYSTEMWIDE_PUBLIC_METRIC_JSON=%s" % json.dumps(payload, ensure_ascii=True, separators=(",", ":")))
