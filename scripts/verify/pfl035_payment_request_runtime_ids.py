"""Resolve PFL-035 acceptance identities from authoritative XML IDs."""

import json


def xmlid(record):
    return record.get_external_id().get(record.id, "")


menu = env.ref("smart_construction_core.menu_sc_user_payment_apply")
action = env.ref("smart_construction_core.action_payment_request_user_payment_apply")
company = env.ref("smart_construction_acceptance_fixture.fe_company_a")
records = {
    "approved": env.ref("smart_construction_acceptance_fixture.fe_request_pfl035_001"),
    "draft": env.ref("smart_construction_acceptance_fixture.fe_request_pfl035_002"),
    "receive": env.ref("smart_construction_acceptance_fixture.fe_pfl035_receive_request"),
    "incomplete": env.ref("smart_construction_acceptance_fixture.fe_pfl035_incomplete_request"),
}
users = {
    "manager": env.ref("smart_construction_acceptance_fixture.fe_user_finance"),
    "user": env.ref("smart_construction_acceptance_fixture.fe_user_pfl035_finance_user"),
    "empty": env.ref("smart_construction_acceptance_fixture.fe_user_pfl035_empty_finance"),
    "forbidden": env.ref("smart_construction_acceptance_fixture.fe_user_project_a_member"),
}
journey_settlement = env.ref("smart_construction_acceptance_fixture.fe_b05_work_settlement_a")
journey_menu = env.ref("smart_construction_core.menu_sc_settlement_order")
journey_action = journey_menu.action
module = env["ir.module.module"].sudo().search(
    [("name", "=", "smart_construction_core")], limit=1
)
payload = {
    "database": env.cr.dbname,
    "module": {
        "name": module.name,
        "state": module.state,
        "version": module.installed_version,
    },
    "company": {"id": int(company.id), "name": company.name, "xmlid": xmlid(company)},
    "menu": {"id": int(menu.id), "xmlid": xmlid(menu), "action_id": int(menu.action.id)},
    "action": {
        "id": int(action.id),
        "xmlid": xmlid(action),
        "model": action.res_model,
        "domain": action.domain,
    },
    "records": {
        key: {
            "id": int(record.id),
            "xmlid": xmlid(record),
            "state": record.state,
            "type": record.type,
            "account": record.payee_account_completeness,
            "eligibility": record.partner_transaction_eligibility,
        }
        for key, record in records.items()
    },
    "users": {
        key: {
            "id": int(user.id),
            "login": user.login,
            "xmlid": xmlid(user),
            "company_id": int(user.company_id.id),
            "company_name": user.company_id.name,
        }
        for key, user in users.items()
    },
    "journey": {
        "settlement": {
            "id": int(journey_settlement.id),
            "xmlid": xmlid(journey_settlement),
            "model": journey_settlement._name,
            "menu_id": int(journey_menu.id),
            "menu_xmlid": xmlid(journey_menu),
            "action_id": int(journey_action.id),
            "action_xmlid": xmlid(journey_action),
        }
    },
}
if menu.action != action or action.res_model != "payment.request":
    raise RuntimeError("PFL-035 menu/action identity mismatch")
if env["sc.payment.execution"].sudo().search_count(
    [
        ("payment_request_id", "=", records["approved"].id),
        ("active", "=", True),
        ("state", "!=", "cancel"),
    ]
):
    raise RuntimeError("PFL-035 positive request must not have an active execution before acceptance")
if journey_action.res_model != "sc.settlement.order" or journey_settlement.state != "approve":
    raise RuntimeError("PFL-035 create journey settlement identity mismatch")
print("PFL035_RUNTIME_TARGETS_JSON=%s" % json.dumps(payload, ensure_ascii=True, separators=(",", ":")))
