"""Verify FE-B04 is carried by the real ui.contract.v2 response."""

import json

from odoo.addons.smart_core.handlers.ui_contract_v2 import UiContractV2Handler


user = env["res.users"].sudo().search([("login", "=", "fixture_role_finance")], limit=1)
request = env.ref("smart_construction_acceptance_fixture.fe_journey_payment_request_a")
menu = env.ref("smart_construction_core.menu_sc_user_payment_apply_acceptance")
finance_env = env(user=user.id, context={**env.context, "allowed_company_ids": user.company_ids.ids})
params = {
    "op": "action_open",
    "action_id": int(menu.action.id),
    "menu_id": int(menu.id),
    "record_id": int(request.id),
    "render_profile": "edit",
    "client_type": "web_pc",
    "delivery_profile": "full",
}
result = UiContractV2Handler(finance_env, payload=params).run(payload=params)
data = result.data if hasattr(result, "data") and isinstance(result.data, dict) else (
    result.get("data") if isinstance(result, dict) else {}
)
runtime = data.get("runtimeContract") if isinstance(data, dict) and isinstance(data.get("runtimeContract"), dict) else {}
workspace = runtime.get("businessWorkspace") if isinstance(runtime.get("businessWorkspace"), dict) else {}
actions = runtime.get("businessActions") if isinstance(runtime.get("businessActions"), list) else []
submit = next((row for row in actions if isinstance(row, dict) and row.get("action_key") == "submit" and row.get("method") == "action_submit"), None)
assert (result.ok if hasattr(result, "ok") else result.get("ok")) is True
assert workspace.get("kind") == "payment_request" and workspace.get("record_id") == request.id
assert workspace.get("version") == "2.0"
assert (workspace.get("identity") or {}).get("object_label") == "付款申请"
assert (workspace.get("state") or {}).get("semantic")
assert submit and submit.get("allowed") is True
assert (submit.get("presentation") or {}).get("tier") == "primary"
assert (submit.get("mutation") or {}).get("operation") == "submit"
assert (submit.get("action_safety") or {}).get("requires_confirm") is True

settlement = env.ref("smart_construction_acceptance_fixture.fe_b05_work_settlement_a")
settlement_menu = env.ref("smart_construction_core.menu_sc_settlement_order")
settlement_params = {
    "op": "action_open",
    "action_id": int(settlement_menu.action.id),
    "menu_id": int(settlement_menu.id),
    "record_id": int(settlement.id),
    "render_profile": "readonly",
    "client_type": "web_pc",
    "delivery_profile": "full",
}
settlement_result = UiContractV2Handler(finance_env, payload=settlement_params).run(payload=settlement_params)
settlement_data = settlement_result.data if hasattr(settlement_result, "data") and isinstance(settlement_result.data, dict) else (
    settlement_result.get("data") if isinstance(settlement_result, dict) else {}
)
settlement_runtime = settlement_data.get("runtimeContract") if isinstance(settlement_data.get("runtimeContract"), dict) else {}
settlement_actions = settlement_runtime.get("businessActions") if isinstance(settlement_runtime.get("businessActions"), list) else []
create_payment = next((row for row in settlement_actions if isinstance(row, dict) and row.get("key") == "create_payment_request"), None)
assert create_payment and create_payment.get("kind") == "open"
assert create_payment.get("level") == "header"
assert create_payment.get("source_widget_id") == "page.header"
assert (create_payment.get("presentation") or {}).get("tier") == "secondary"
assert create_payment.get("target") == "self"
assert create_payment.get("visible_profiles") == ["readonly"]
assert str(create_payment.get("url") or "").startswith("/f/payment.request/new?")
assert "default_settlement_id=%s" % settlement.id in create_payment["url"]
print("[verify.frontend.financial_workspace.v2_contract] PASS")
print(json.dumps({"runtime_keys": sorted(runtime), "submit": submit, "create_payment": create_payment}, ensure_ascii=False, indent=2, default=str))
