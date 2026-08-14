"""Resolve PFL-035 acceptance identities from authoritative XML IDs."""

import json


def xmlid(record):
    return record.get_external_id().get(record.id, "")


menu = env.ref("smart_construction_core.menu_sc_user_payment_apply_acceptance")
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
payload = {
    "database": env.cr.dbname,
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
        key: {"id": int(user.id), "login": user.login, "xmlid": xmlid(user)}
        for key, user in users.items()
    },
}
if menu.action != action or action.res_model != "payment.request":
    raise RuntimeError("PFL-035 menu/action identity mismatch")
if env["sc.payment.execution"].sudo().search_count(
    [("payment_request_id", "=", records["approved"].id)]
):
    raise RuntimeError("PFL-035 positive request must not have an execution before acceptance")
print("PFL035_RUNTIME_TARGETS_JSON=%s" % json.dumps(payload, ensure_ascii=True, separators=(",", ":")))
