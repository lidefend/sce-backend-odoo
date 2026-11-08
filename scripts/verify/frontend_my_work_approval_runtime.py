from odoo.addons.smart_construction_core.services.payment_request_work_item_service import (
    PaymentRequestWorkItemService,
)
from odoo.exceptions import AccessError


def require(condition, message):
    if not condition:
        raise RuntimeError("[verify.frontend.my_work_approval.runtime] " + message)


def workspace(login, company=None):
    user = env["res.users"].sudo().search([("login", "=", login)], limit=1)
    require(user, "missing user %s" % login)
    scoped = env(user=user.id)
    if company:
        scoped = scoped(context={**scoped.context, "allowed_company_ids": [company.id]})
    return PaymentRequestWorkItemService(scoped, params={}, context=scoped.context).build()


company_a = env.ref("smart_construction_acceptance_fixture.fe_company_a")
company_b = env.ref("smart_construction_acceptance_fixture.fe_company_b")
finance_a = workspace("fixture_role_finance", company_a)
finance_b = workspace("fixture_role_finance", company_b)
finance_reviewer = env["res.users"].sudo().search(
    [("login", "=", "fixture_role_finance_reviewer")],
    limit=1,
)
require(finance_reviewer, "missing fixture_role_finance_reviewer")
reviewer_workspace = workspace("fixture_role_finance_reviewer", company_a)
member = workspace("fixture_role_project_a_member", company_a)


class _RollbackProbe(Exception):
    pass


def create_probe(login):
    user = env["res.users"].sudo().search([("login", "=", login)], limit=1)
    scoped = env(user=user.id, context={**env.context, "allowed_company_ids": [company_a.id], "current_project_id": env.ref("smart_construction_acceptance_fixture.fe_project_a").id})
    project = scoped["project.project"].browse(env.ref("smart_construction_acceptance_fixture.fe_project_a").id)
    project_read = True
    try:
        project.check_access_rule("read")
        project.display_name
    except AccessError:
        project_read = False
    values = {
                "type": "pay",
                "business_category_id": env.ref("smart_construction_core.business_category_finance_payment_apply_pay").id,
                "project_id": project.id,
                "contract_id": env.ref("smart_construction_acceptance_fixture.fe_contract_a").id,
                "settlement_id": env.ref("smart_construction_acceptance_fixture.fe_journey_settlement_a").id,
                "partner_id": env.ref("smart_construction_acceptance_fixture.fe_partner_a").id,
                "currency_id": company_a.currency_id.id,
                "amount": 1.0,
                "state": "draft",
    }
    outcomes = {}
    for label, target in (("project_context", scoped), ("company_context", env(user=user.id, context={**env.context, "allowed_company_ids": [company_a.id]}))):
        created = False
        failure = ""
        try:
            with env.cr.savepoint():
                target["payment.request"].create(values)
                created = True
                raise _RollbackProbe()
        except _RollbackProbe:
            pass
        except Exception as exc:
            failure = type(exc).__name__
        outcomes[label] = {"created": created, "failure": failure}
    return {"payment_create_acl": bool(scoped["payment.request"].check_access_rights("create", raise_exception=False)), "project_read": project_read, **outcomes}


def names(result, key):
    section = next((row for row in result["sections"] if row["key"] == key), {"items": []})
    require(section.get("count") == len(section.get("items") or []), "%s count/list mismatch" % key)
    return {item["record"]["label"] for item in section.get("items") or []}


approval_request = env.ref(
    "smart_construction_acceptance_fixture.fe_journey_payment_request_approval_a"
)
payment_policy = env["sc.approval.policy"].sudo().get_active_policy(
    "payment.request",
    company=company_a,
)
print(
    "[verify.frontend.my_work_approval.runtime] payment_policy=%s"
    % {
        "policy_id": int(payment_policy.id or 0),
        "code": str(payment_policy.code or ""),
        "active": bool(payment_policy.active),
        "approval_required": bool(payment_policy.approval_required),
        "mode": str(payment_policy.mode or ""),
        "runtime_state": str(payment_policy.runtime_state or ""),
        "company_id": int(payment_policy.company_id.id or 0),
        "manager_group": str(payment_policy.manager_group_id.name or ""),
        "steps": [
            {
                "name": str(step.name or ""),
                "active": bool(step.active),
                "sequence": int(step.sequence or 0),
                "scope": str(step.approval_scope_key or ""),
                "group": str(step.approve_group_id.name or ""),
            }
            for step in payment_policy.step_ids.sorted("sequence")
        ],
    }
)
review_diagnostic = []
for review in approval_request.sudo().review_ids.sorted("sequence"):
    reviewer_ids = review.reviewer_ids.mapped("id")
    review_diagnostic.append(
        {
            "review_id": int(review.id),
            "status": str(review.status or ""),
            "sequence": int(review.sequence or 0),
            "reviewer_group": str(review.reviewer_group_id.name or ""),
            "reviewer_ids": reviewer_ids,
            "reviewers": review.reviewer_ids.mapped("login"),
            "can_review": {
                user.login: bool(approval_request.with_user(user).can_review)
                for user in review.reviewer_ids
            },
        }
    )
print(
    "[verify.frontend.my_work_approval.runtime] approval_fixture=%s"
    % {
        "record_id": int(approval_request.id),
        "state": str(approval_request.state or ""),
        "validation_status": str(approval_request.validation_status or ""),
        "reviews": review_diagnostic,
    }
)
require(bool(approval_request.review_ids), "approval fixture has no pending review")
current_reviews = approval_request.review_ids.filtered(
    lambda review: review.status in ("waiting", "pending")
)
require(bool(current_reviews), "approval fixture has no current pending review")
require(
    finance_reviewer in current_reviews.mapped("reviewer_ids"),
    "approval fixture does not assign the finance reviewer",
)
require(
    bool(approval_request.with_user(finance_reviewer).can_review),
    "assigned finance reviewer lacks current-step approval authority",
)


require(any("FE-JOURNEY-PAYMENT-001" in name for name in names(finance_a, "todo")), "finance draft todo missing")
require(any("FE-JOURNEY-PAYMENT-001" in name for name in names(finance_a, "initiated")), "finance initiated missing")
require(any("FE-JOURNEY-APPROVAL-001" in name for name in names(reviewer_workspace, "todo")), "finance reviewer approval todo missing")
require(any("FE-JOURNEY-REJECT-001" in name for name in names(reviewer_workspace, "todo")), "finance reviewer rejection todo missing")
require("FE-JOURNEY-PAYMENT-001" not in str(finance_b), "company B leaked company A work")
require("FE-JOURNEY-PAYMENT-001" not in str(member), "project member leaked payment work")
require("100.0" not in str(member), "project member leaked payment amount")
permission_matrix = {
    login: create_probe(login)
    for login in (
        "fixture_role_finance",
        "fixture_role_project_a_member",
        "fixture_role_pm",
        "fixture_role_owner",
        "fixture_role_executive",
        "fixture_role_finance_reviewer",
    )
}
print("[verify.frontend.my_work_approval.runtime] create_permission_matrix=%s" % permission_matrix)
print("[verify.frontend.my_work_approval.runtime] PASS")
