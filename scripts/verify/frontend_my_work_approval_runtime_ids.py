import json


def ref(xmlid):
    row = env.ref(xmlid, raise_if_not_found=False)
    if not row:
        raise RuntimeError("missing %s" % xmlid)
    return row


def target(menu_xmlid, record_xmlid):
    menu = ref(menu_xmlid)
    row = ref(record_xmlid)
    action = menu.action
    project = row.project_id if "project_id" in row._fields else row.browse([])
    return {
        "model": row._name,
        "record_id": int(row.id),
        "action_id": int(action.id),
        "menu_id": int(menu.id),
        "menu_xmlid": menu_xmlid,
        "name": str(row.display_name),
        "project_id": int(project.id or 0),
        "project_label": str(project.display_name or ""),
    }


payment_menu = "smart_construction_core.menu_sc_user_payment_apply"
company_a = ref("smart_construction_acceptance_fixture.fe_company_a")
company_b = ref("smart_construction_acceptance_fixture.fe_company_b")
payload = {
    "companies": {"a": int(company_a.id), "b": int(company_b.id)},
    "draft": target(payment_menu, "smart_construction_acceptance_fixture.fe_journey_payment_request_a"),
    "approval": target(payment_menu, "smart_construction_acceptance_fixture.fe_journey_payment_request_approval_a"),
    "reject": target(payment_menu, "smart_construction_acceptance_fixture.fe_journey_payment_request_reject_a"),
    "completed": target(payment_menu, "smart_construction_acceptance_fixture.fe_journey_payment_request_completed_a"),
    "settlement": target(
        "smart_construction_core.menu_sc_settlement_order",
        "smart_construction_acceptance_fixture.fe_journey_settlement_a",
    ),
    "work_settlement": target(
        "smart_construction_core.menu_sc_settlement_order",
        "smart_construction_acceptance_fixture.fe_b05_work_settlement_a",
    ),
}
print("FRONTEND_MY_WORK_APPROVAL_TARGETS_JSON=" + json.dumps(payload, ensure_ascii=True, separators=(",", ":")))
