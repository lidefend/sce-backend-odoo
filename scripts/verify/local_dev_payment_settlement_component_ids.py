"""Resolve one governed local.dev settlement-introduction journey without writes."""

import json


def xmlid(record):
    return record.get_external_id().get(record.id, "")


user = env.ref("smart_construction_demo.user_demo_role_finance")
menu = env.ref("smart_construction_core.menu_sc_user_payment_apply")
action = env.ref("smart_construction_core.action_payment_request_user_payment_apply")
payment_env = env["payment.request"].with_user(user).with_company(user.company_id).with_context(
    allowed_company_ids=user.company_ids.ids,
    active_test=False,
)
request = env.ref(
    "smart_construction_demo.payment_request_floorplan_demo_record",
    raise_if_not_found=False,
)
if request:
    request = payment_env.browse(request.id).exists()
if not request or not str(request.name or "").startswith("DEMO-PR-FLOORPLAN-") or request.state != "draft":
    raise RuntimeError("governed settlement-introduction payment fixture is missing or not draft")
request.check_access_rights("read")
request.check_access_rule("read")

settlement_env = env["sc.settlement.order"].with_user(user).with_company(user.company_id).with_context(
    allowed_company_ids=user.company_ids.ids,
    active_test=False,
)
selected_settlement = env.ref(
    "smart_construction_demo.sc_demo_settlement_069_payment",
    raise_if_not_found=False,
)
selected_line = env.ref(
    "smart_construction_demo.sc_demo_settlement_line_069_payment",
    raise_if_not_found=False,
)
selected_settlement = settlement_env.browse(selected_settlement.id).exists() if selected_settlement else settlement_env.browse()
settlement_line_env = env["sc.settlement.order.line"].with_user(user).with_company(user.company_id).with_context(
    allowed_company_ids=user.company_ids.ids,
    active_test=False,
)
selected_line = settlement_line_env.browse(selected_line.id).exists() if selected_line else settlement_line_env.browse()
if not selected_settlement or not selected_line or selected_line.settlement_id != selected_settlement:
    raise RuntimeError("governed settlement-introduction source fixture is missing or inconsistent")
selected_settlement.check_access_rights("read")
selected_settlement.check_access_rule("read")
selected_line.check_access_rights("read")
selected_line.check_access_rule("read")
if not selected_settlement.active or selected_settlement.currency_id != request.currency_id:
    raise RuntimeError("governed settlement source is inactive or uses a different currency")
if selected_settlement.project_id and selected_settlement.project_id != request.project_id:
    raise RuntimeError("governed settlement source belongs to a different project")
if selected_settlement.contract_id and selected_settlement.contract_id != request.contract_id:
    raise RuntimeError("governed settlement source belongs to a different contract")

payment_line_env = env["payment.request.line"].with_user(user).with_company(user.company_id).with_context(
    allowed_company_ids=user.company_ids.ids,
    active_test=False,
)
applied = sum(
    payment_line_env.search([
        ("settlement_line_id", "=", selected_line.id),
        ("active", "=", True),
    ]).mapped("current_pay_amount")
)
remaining = float(selected_line.amount or 0.0) - float(applied or 0.0)
if selected_settlement.currency_id.compare_amounts(remaining, 0.0) <= 0:
    raise RuntimeError("governed settlement source line has no remaining amount")

introduced_lines = request.outflow_line_ids.filtered(
    lambda row: row.settlement_id == selected_settlement
)
payload = {
    "database": env.cr.dbname,
    "user": {"id": int(user.id), "login": user.login, "xmlid": xmlid(user)},
    "menu": {"id": int(menu.id), "xmlid": xmlid(menu)},
    "action": {"id": int(action.id), "xmlid": xmlid(action)},
    "request": {
        "id": int(request.id),
        "name": str(request.name or ""),
        "state": str(request.state or ""),
        "amount": float(request.amount or 0.0),
        "detail_amount_total": float(request.detail_amount_total or 0.0),
        "amount_uses_details": bool(request.amount_uses_details),
        "line_count": len(request.outflow_line_ids),
        "settlement_line_count": len(introduced_lines),
        "active_line_ids": [int(line.id) for line in request.outflow_line_ids.filtered("active")],
    },
    "settlement": {
        "id": int(selected_settlement.id),
        "name": str(selected_settlement.name or ""),
        "display_name": str(selected_settlement.display_name or ""),
        "line_id": int(selected_line.id),
        "line_name": str(selected_line.name or ""),
    },
}
print("LOCAL_DEV_PAYMENT_SETTLEMENT_COMPONENT_JSON=%s" % json.dumps(payload, ensure_ascii=True, separators=(",", ":")))
