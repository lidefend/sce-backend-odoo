"""Resolve one governed local.dev payment-request parity target without writes."""

import hashlib
import json

from odoo.osv import expression
from odoo.tools.safe_eval import safe_eval
from odoo.addons.smart_construction_core.services.financial_workspace_contract import (
    build_financial_form_business_actions,
)
from odoo.addons.smart_core.delivery.menu_service import MenuService
from odoo.addons.smart_core.identity.identity_resolver import IdentityResolver


def xmlid(record):
    return record.get_external_id().get(record.id, "")


user = env.ref("smart_construction_demo.user_demo_role_finance")
security_user = env.ref("smart_construction_demo.user_demo_project_read")
project_create_user = env.ref("smart_construction_demo.sc_demo_user_test_admin")
menu = env.ref("smart_construction_core.menu_sc_user_payment_apply")
action = env.ref("smart_construction_core.action_payment_request_user_payment_apply")
project_create_action = env.ref("smart_construction_core.action_project_initiation")
project_create_menu = env.ref("smart_construction_core.menu_sc_project_initiation")
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
actionable_record = payment_env.search([("name", "=", "DEMO-PR-FLOORPLAN-001")], limit=1)
if not actionable_record:
    raise RuntimeError("governed submit-ready payment request fixture is missing")
actionable_record.check_access_rights("read")
actionable_record.check_access_rule("read")
actionable_funding_baseline = env["project.funding.baseline"].sudo().search(
    [
        ("project_id", "=", actionable_record.project_id.id),
        ("state", "=", "active"),
        ("normalization_state", "=", "normalized"),
    ],
    limit=2,
)
if len(actionable_funding_baseline) != 1:
    raise RuntimeError("submit-ready payment request requires one active normalized funding baseline")
if not actionable_record.date_request or not (
    actionable_funding_baseline.period_start
    <= actionable_record.date_request
    <= actionable_funding_baseline.period_end
):
    raise RuntimeError("submit-ready payment request date is outside the active funding baseline")
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
if not menu.active or menu.id not in env["ir.ui.menu"].with_user(user)._visible_menu_ids():
    raise RuntimeError("payment request menu is not active and visible to demo_role_finance")

action_domain = safe_eval(
    action.domain or "[]",
    {"uid": user.id, "user": user, "context": dict(payment_env.env.context)},
)
record_in_action_domain = payment_env.search_count(
    expression.AND([action_domain, [("id", "=", record.id)]])
)
if record_in_action_domain != 1:
    raise RuntimeError("governed local.dev payment request is outside the formal action domain")

identity_resolver = IdentityResolver(payment_env.env)
role_surface = identity_resolver.build_role_surface(
    identity_resolver.user_group_xmlids(user),
    [],
    {"workspace.home"},
)
route_authority = MenuService(payment_env.env).build_route_authority(role_surface)
route_matches = [
    (bucket, entry)
    for bucket in ("primary_actions", "role_home_actions", "contextual_actions", "admin_actions")
    for entry in route_authority.get(bucket) or []
    if int(entry.get("menu_id") or 0) == menu.id
    and int(entry.get("action_id") or 0) == action.id
]
if len(route_matches) != 1:
    raise RuntimeError("payment request route authority is not uniquely projected for demo_role_finance")


project_create_env = env["project.project"].with_user(project_create_user).with_company(
    project_create_user.company_id
).with_context(allowed_company_ids=project_create_user.company_ids.ids)
project_create_env.check_access_rights("create")
if project_create_action.res_model != "project.project" or project_create_menu.action != project_create_action:
    raise RuntimeError("project create action/menu authority mismatch")

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
actionable_fingerprint_payload = {
    "id": int(actionable_record.id),
    "write_date": actionable_record.write_date.isoformat() if actionable_record.write_date else "",
    "state": str(actionable_record.state or ""),
    "validation_status": str(actionable_record.validation_status or ""),
    "name": str(actionable_record.name or ""),
    "amount": float(actionable_record.amount or 0.0),
}
payload = {
    "database": env.cr.dbname,
    "user": {"id": int(user.id), "login": user.login, "xmlid": xmlid(user)},
    "security_user": {
        "id": int(security_user.id),
        "login": security_user.login,
        "xmlid": xmlid(security_user),
    },
    "project_create_user": {
        "id": int(project_create_user.id),
        "login": project_create_user.login,
        "xmlid": xmlid(project_create_user),
        "can_create_project": True,
    },
    "project_create_entry": {
        "action_id": int(project_create_action.id),
        "action_xmlid": xmlid(project_create_action),
        "menu_id": int(project_create_menu.id),
        "menu_xmlid": xmlid(project_create_menu),
    },
    "menu": {"id": int(menu.id), "xmlid": xmlid(menu)},
    "action": {"id": int(action.id), "xmlid": xmlid(action)},
    "view": {"id": int(view.id), "xmlid": xmlid(view)},
    "acceptance_authority": {
        "role_code": str(role_surface.get("role_code") or ""),
        "route_bucket": route_matches[0][0],
        "menu_active": bool(menu.active),
        "menu_visible": True,
        "record_in_action_domain": True,
        "action_domain": action_domain,
        "funding_baseline": {
            "id": int(actionable_funding_baseline.id),
            "period_start": str(actionable_funding_baseline.period_start),
            "period_end": str(actionable_funding_baseline.period_end),
            "request_date": str(actionable_record.date_request),
        },
    },
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
    "actionable_record": {
        "id": int(actionable_record.id),
        "name": str(actionable_record.name or ""),
        "state": str(actionable_record.state or ""),
        "validation_status": str(actionable_record.validation_status or ""),
        "amount": float(actionable_record.amount or 0.0),
        "legal_next_action": str(actionable_record.legal_next_action_display or ""),
        "blocking_reason": str(actionable_record.payment_blocking_reason_display or ""),
    },
    "business_fingerprint": hashlib.sha256(
        json.dumps(fingerprint_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest(),
    "actionable_fingerprint": hashlib.sha256(
        json.dumps(actionable_fingerprint_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest(),
    "candidate_inventory": candidate_rows,
}
print("LOCAL_DEV_PAYMENT_PARITY_JSON=%s" % json.dumps(payload, ensure_ascii=True, separators=(",", ":")))
