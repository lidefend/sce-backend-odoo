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
request = payment_env.search([("name", "=", "DEMO-PR-FLOORPLAN-001")], limit=1)
if not request or request.state != "draft":
    raise RuntimeError("governed settlement-introduction payment fixture is missing or not draft")
request.check_access_rights("read")
request.check_access_rule("read")

settlement_env = env["sc.settlement.order"].with_company(user.company_id).with_context(
    allowed_company_ids=user.company_ids.ids,
    active_test=False,
)
domain = [("active", "=", True)]
if request.project_id:
    domain += ["|", ("project_id", "=", request.project_id.id), ("project_id", "=", False)]
if request.contract_id:
    domain += ["|", ("contract_id", "=", request.contract_id.id), ("contract_id", "=", False)]

selected_settlement = settlement_env.browse()
selected_line = env["sc.settlement.order.line"].browse()
for settlement in settlement_env.search(domain, order="id desc"):
    for line in settlement.line_ids.sorted(key=lambda row: row.id):
        applied = sum(
            env["payment.request.line"].search([
                ("settlement_line_id", "=", line.id),
                ("active", "=", True),
            ]).mapped("current_pay_amount")
        )
        if float(line.amount or 0.0) - float(applied or 0.0) > 0.01:
            selected_settlement = settlement
            selected_line = line
            break
    if selected_line:
        break
if not selected_settlement or not selected_line:
    raise RuntimeError("no compatible settlement line with remaining amount is available")

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
        "line_count": len(request.outflow_line_ids),
        "settlement_line_count": len(introduced_lines),
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
