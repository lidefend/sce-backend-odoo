"""Resolve stable FE-B06 browser targets without hard-coded database ids."""

import json


def target(menu_xmlid, record_xmlid, *, declared_action_xmlid="", expect=None):
    menu = env.ref(menu_xmlid)
    action = menu.action
    action_xmlid = str(action.get_external_id().get(action.id, "") or "").strip()
    if declared_action_xmlid and action_xmlid != declared_action_xmlid:
        raise AssertionError(
            "declared action mismatch for %s: expected %s, resolved %s"
            % (menu_xmlid, declared_action_xmlid, action_xmlid or int(action.id))
        )
    record = env.ref(record_xmlid)
    record_identity = next(
        (
            str(value).strip()
            for field_name in ("name", "code", "number", "reference", "document_no", "contract_no", "project_code")
            if field_name in record._fields
            for value in (record[field_name],)
            if value
        ),
        str(record.display_name).strip(),
    )
    resolved = {
        "menu_id": int(menu.id),
        "menu_xmlid": menu_xmlid,
        "action_id": int(action.id),
        "action_xmlid": action_xmlid,
        "model": action.res_model,
        "record_id": int(record.id),
        "record_xmlid": record_xmlid,
        "record_identity": record_identity,
        "display_name": str(record.display_name),
    }
    # A lane that mutates real product state also declares the boundary it acts
    # on, so the browser probe can fail closed before its first write instead of
    # trusting whichever record the route happened to open.
    for key, value in (expect or {}).items():
        resolved[key] = value(record) if callable(value) else value
    return resolved


# Browser matrix targets must be the *released* navigation entry of the role that
# owns the surface; the publication projection removes legacy menus, and a route
# missing from a role's released navigation is denied with NAVIGATION_AUTHORITY_DENIED.
# Every binding below therefore names its declared menu/action pair, and the resolver
# fails closed when the resolved pair differs from the declaration.
PROJECT_MENU_XMLID = "smart_construction_core.menu_sc_project_project"
PROJECT_ACTION_XMLID = "smart_construction_core.action_sc_project_list"
CONTRACT_MENU_XMLID = "smart_construction_core.menu_sc_p1_daily_contract"
CONTRACT_ACTION_XMLID = "smart_construction_core.action_sc_general_contract"
SETTLEMENT_MENU_XMLID = "smart_construction_core.menu_sc_expense_contract_settlement"
SETTLEMENT_ACTION_XMLID = "smart_construction_core.action_sc_settlement_order_expense"
PAYMENT_REQUEST_MENU_XMLID = "smart_construction_core.menu_sc_user_payment_apply"
PAYMENT_REQUEST_ACTION_XMLID = "smart_construction_core.action_payment_request_user_payment_apply"
PAYMENT_EXECUTION_MENU_XMLID = "smart_construction_core.menu_sc_payment_execution"
PAYMENT_EXECUTION_ACTION_XMLID = "smart_construction_core.action_sc_payment_execution_actual_outflow"
LIFECYCLE_MENU_XMLID = "smart_construction_core.menu_sc_product_project_lifecycle_v1"
LIFECYCLE_ACTION_XMLID = "smart_construction_core.action_sc_product_project_lifecycle_v1"
LIFECYCLE_RECORD_XMLID = "smart_construction_acceptance_fixture.fe_project_lifecycle"
LIFECYCLE_COMPANY_XMLID = "smart_construction_acceptance_fixture.fe_company_a"

# pm's released project surface is the single 项目台账 record entry
# (menu_sc_project_project / action_sc_project_list). The duplicate
# 项目信息编辑 entry was retired and its master-data composition was carried
# into that entry's record form.
payload = {
    "project": target(
        PROJECT_MENU_XMLID,
        "smart_construction_acceptance_fixture.fe_project_a",
        declared_action_xmlid=PROJECT_ACTION_XMLID,
    ),
    "contract": target(
        CONTRACT_MENU_XMLID,
        "smart_construction_acceptance_fixture.fe_general_contract_a",
        declared_action_xmlid=CONTRACT_ACTION_XMLID,
    ),
    "settlement": target(
        SETTLEMENT_MENU_XMLID,
        "smart_construction_acceptance_fixture.fe_settlement_a",
        declared_action_xmlid=SETTLEMENT_ACTION_XMLID,
    ),
    "payment_request": target(
        PAYMENT_REQUEST_MENU_XMLID,
        "smart_construction_acceptance_fixture.fe_delivery_hardening_payment_request_a",
        declared_action_xmlid=PAYMENT_REQUEST_ACTION_XMLID,
    ),
    "payment_request_company_b": target(
        PAYMENT_REQUEST_MENU_XMLID,
        "smart_construction_acceptance_fixture.fe_request_c_001",
        declared_action_xmlid=PAYMENT_REQUEST_ACTION_XMLID,
    ),
    "payment_execution": target(
        PAYMENT_EXECUTION_MENU_XMLID,
        "smart_construction_acceptance_fixture.fe_execution_a",
        declared_action_xmlid=PAYMENT_EXECUTION_ACTION_XMLID,
    ),
    "journey_request": target(
        PAYMENT_REQUEST_MENU_XMLID,
        "smart_construction_acceptance_fixture.fe_delivery_hardening_payment_request_a",
        declared_action_xmlid=PAYMENT_REQUEST_ACTION_XMLID,
    ),
    "work_settlement": target(
        SETTLEMENT_MENU_XMLID,
        "smart_construction_acceptance_fixture.fe_b05_work_settlement_a",
        declared_action_xmlid=SETTLEMENT_ACTION_XMLID,
    ),
    "lifecycle_project": target(
        LIFECYCLE_MENU_XMLID,
        LIFECYCLE_RECORD_XMLID,
        declared_action_xmlid=LIFECYCLE_ACTION_XMLID,
        expect={
            "record_code": lambda record: str(record.code or "").strip(),
            "company_id": lambda record: int(record.company_id.id),
            "company_xmlid": LIFECYCLE_COMPANY_XMLID,
            "declared_start_state": {"lifecycle_state": "draft", "sc_approval_state": "draft"},
        },
    ),
}
payload["companies"] = {
    "a": int(env.ref("smart_construction_acceptance_fixture.fe_company_a").id),
    "b": int(env.ref("smart_construction_acceptance_fixture.fe_company_b").id),
}
print("FRONTEND_DELIVERY_HARDENING_TARGETS_JSON=" + json.dumps(payload, ensure_ascii=True, separators=(",", ":")))
