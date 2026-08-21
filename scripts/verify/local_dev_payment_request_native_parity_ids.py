"""Resolve one governed local.dev payment-request parity target without writes."""

import hashlib
import json

from odoo.addons.smart_construction_core.services.financial_workspace_contract import (
    build_financial_form_business_actions,
)


def xmlid(record):
    return record.get_external_id().get(record.id, "")


user = env.ref("smart_construction_demo.user_demo_role_finance")
menu = env.ref("smart_construction_core.menu_sc_user_payment_apply")
action = env.ref("smart_construction_core.action_payment_request_user_payment_apply")
view = env.ref("smart_construction_core.view_payment_request_form")
candidate = env.ref("smart_construction_demo.sc_demo_pay_req_010_003")
execution_action = env.ref("smart_construction_core.action_sc_payment_execution_actual_outflow")
execution_menu = env.ref("smart_construction_core.menu_sc_payment_execution")
payment_env = env["payment.request"].with_user(user).with_company(user.company_id).with_context(
    allowed_company_ids=user.company_ids.ids,
    active_test=False,
)
record = payment_env.browse(candidate.id).exists()
if not record:
    raise RuntimeError("governed local.dev payment request is not readable by demo_role_finance")
record.check_access_rights("read")
record.check_access_rule("read")
execution_env = env["sc.payment.execution"].with_user(user).with_company(user.company_id).with_context(
    allowed_company_ids=user.company_ids.ids,
    active_test=False,
)
execution_record = execution_env.search([("source_kind", "=", "actual_outflow")], order="id desc", limit=1)
if not execution_record:
    raise RuntimeError("governed local.dev payment execution reuse target is missing")
execution_record.check_access_rights("read")
execution_record.check_access_rule("read")
if menu.action != action or action.res_model != "payment.request":
    raise RuntimeError("payment request menu/action authority mismatch")
if view.model != "payment.request" or view.type != "form":
    raise RuntimeError("payment request native form authority mismatch")

candidate_rows = []
for item in payment_env.search([("type", "=", "pay")], order="id"):
    item_xmlid = xmlid(item)
    if not item_xmlid.startswith("smart_construction_demo.") and not str(item.name or "").startswith("DEMO-PR-"):
        continue
    business_projection = build_financial_form_business_actions(payment_env.env, item._name, item.id) or {}
    submit_actions = [
        action for action in business_projection.get("actions", [])
        if action.get("action_key") == "submit" and action.get("method") == "action_submit"
    ]
    submit_action = submit_actions[0] if submit_actions else {}
    candidate_rows.append({
        "id": int(item.id),
        "xmlid": item_xmlid,
        "name": str(item.name or ""),
        "state": str(item.state or ""),
        "validation_status": str(item.validation_status or ""),
        "amount": float(item.amount or 0.0),
        "unpaid_amount": float(item.unpaid_amount or 0.0),
        "has_active_payment_execution": bool(item.has_active_payment_execution),
        "legal_next_action": str(item.legal_next_action_display or ""),
        "blocking_reason": str(item.payment_blocking_reason_display or ""),
        "has_contract": bool(item.contract_id),
        "has_settlement": bool(item.settlement_id),
        "submit_business_available": bool(submit_action.get("business_available")),
        "submit_authorization_allowed": bool(submit_action.get("authorization_allowed")),
        "submit_enabled": bool(submit_action.get("enabled")),
        "submit_reason_code": str(submit_action.get("reason_code") or ""),
    })

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
    "reuse_target": {
        "model": "sc.payment.execution",
        "action_id": int(execution_action.id),
        "action_xmlid": xmlid(execution_action),
        "menu_id": int(execution_menu.id),
        "menu_xmlid": xmlid(execution_menu),
        "record_id": int(execution_record.id),
        "name": str(execution_record.display_name or ""),
    },
    "execution_contract_inventory": [
        {
            "id": int(contract.id),
            "name": str(contract.name or ""),
            "active": bool(contract.active),
            "priority": int(contract.priority or 0),
            "action_id": int(contract.action_id.id or 0),
            "has_creator_name": "creator_name" in str(contract.contract_json or {}),
        }
        for contract in env["ui.business.config.contract"].sudo().search([
            ("model", "=", "sc.payment.execution"),
            ("view_type", "=", "form"),
        ], order="priority desc, id")
    ],
    "record": {
        "id": int(record.id),
        "xmlid": xmlid(record),
        "name": record.name,
        "state": str(record.state or ""),
        "validation_status": str(record.validation_status or ""),
        "type": str(record.type or ""),
        "amount": float(record.amount or 0.0),
        "has_active_payment_execution": bool(record.has_active_payment_execution),
        "payment_count": fingerprint_payload["payment_count"],
        "legal_next_action": str(record.legal_next_action_display or ""),
        "blocking_reason": str(record.payment_blocking_reason_display or ""),
    },
    "business_fingerprint": hashlib.sha256(
        json.dumps(fingerprint_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest(),
    "candidate_inventory": candidate_rows,
}
print("LOCAL_DEV_PAYMENT_PARITY_JSON=%s" % json.dumps(payload, ensure_ascii=True, separators=(",", ":")))
