"""Read-only probe for governed action scopes on the local.dev project create form."""

import json

from odoo.addons.smart_core.handlers.ui_contract_v2 import UiContractV2Handler


user = env.ref("smart_construction_demo.sc_demo_user_test_admin")
action = env.ref("smart_construction_core.action_project_initiation")
menu = env.ref("smart_construction_core.menu_sc_project_initiation")
payment_action = env.ref("smart_construction_core.action_payment_request_user_payment_apply")
payment_menu = env.ref("smart_construction_core.menu_sc_user_payment_apply")
payment_record = env["payment.request"].sudo().search([
    ("name", "=", "DEMO-PR-FLOORPLAN-001"),
], limit=1)
if not payment_record:
    raise RuntimeError("governed payment request DriverHost probe fixture is missing")
user_env = env(user=user.id, context={
    **env.context,
    "allowed_company_ids": user.company_ids.ids,
})
payload = {
    "op": "action_open",
    "action_id": int(action.id),
    "menu_id": int(menu.id),
    "model": "project.project",
    "view_type": "form",
    "record_id": "new",
    "render_profile": "create",
    "client_type": "web_pc",
    "delivery_profile": "full",
}
result = UiContractV2Handler(user_env, payload=payload).run(payload=payload)
data = result.data if hasattr(result, "data") and isinstance(result.data, dict) else {}
if not getattr(result, "ok", False):
    raise RuntimeError("project create Contract V2 failed: %s" % result)

rules = ((data.get("actionContract") or {}).get("actionRuleList") or [])
record_bound = [
    row for row in rules
    if isinstance(row, dict) and row.get("sourceChannel") == "bound_model_action"
]
if record_bound:
    raise AssertionError("create contract exposed record-bound actions: %s" % [
        row.get("actionId") for row in record_bound
    ])
mode_actions = [
    row for row in rules
    if isinstance(row, dict) and str(row.get("sourceWidgetId") or "").startswith("mode.")
]
if not mode_actions or any(row.get("targetScope") != "runtime" for row in mode_actions):
    raise AssertionError("mode-local actions must remain in Contract V2 runtime scope: %s" % [
        {
            "actionId": row.get("actionId"),
            "sourceChannel": row.get("sourceChannel"),
            "sourceWidgetId": row.get("sourceWidgetId"),
            "targetScope": row.get("targetScope"),
            "intent": row.get("intent"),
        }
        for row in mode_actions
    ])
statuses = {
    str(row.get("btnId") or ""): row
    for row in ((data.get("statusContract") or {}).get("buttonStatus") or [])
    if isinstance(row, dict)
}
rows = []
for rule in rules:
    if not isinstance(rule, dict):
        continue
    action_id = str(rule.get("actionId") or "")
    status = statuses.get("btn.%s" % action_id.removeprefix("action."), {})
    row = {
        "actionId": action_id,
        "actionKey": rule.get("actionKey"),
        "label": rule.get("label"),
        "intent": rule.get("intent"),
        "sourceWidgetId": rule.get("sourceWidgetId"),
        "targetScope": rule.get("targetScope"),
        "dispatchMode": rule.get("dispatchMode"),
        "sourceChannel": rule.get("sourceChannel"),
        "entitlementEvaluated": rule.get("entitlementEvaluated"),
        "visible": status.get("visible"),
        "disabled": status.get("disabled"),
        "reasonCode": status.get("reasonCode"),
    }
    if (
        str(row.get("sourceWidgetId") or "").startswith("mode.")
        or row.get("sourceChannel") == "governed_platform_action"
        or (row.get("targetScope") == "page" and row.get("visible") is True)
    ):
        rows.append(row)

print("LOCAL_DEV_PROJECT_CREATE_ACTION_SCOPE_JSON=" + json.dumps({
    "database": env.cr.dbname,
    "login": user.login,
    "user_xmlid": user.get_external_id().get(user.id, ""),
    "action_id": int(action.id),
    "menu_id": int(menu.id),
    "payment_action_id": int(payment_action.id),
    "payment_menu_id": int(payment_menu.id),
    "payment_record_id": int(payment_record.id),
    "rules": rows,
    "record_bound_create_actions": len(record_bound),
    "mode_runtime_actions": len(mode_actions),
}, ensure_ascii=False, sort_keys=True))
