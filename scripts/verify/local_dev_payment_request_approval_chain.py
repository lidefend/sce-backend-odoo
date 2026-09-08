"""Resolve the actual configured reviewers for the submitted local.dev fixture."""

import json


def xmlid(record):
    return record.get_external_id().get(record.id, "")


request = env.ref("smart_construction_demo.payment_request_floorplan_demo_record")
if request.state != "submit" or request.validation_status not in ("waiting", "pending"):
    raise RuntimeError("payment approval-chain resolution requires the submitted governed fixture")
reviews = request.review_ids.sudo().sorted(lambda row: (row.sequence, row.id))
if not reviews:
    raise RuntimeError("submitted payment fixture generated no tier reviews")

chain = []
for review in reviews:
    candidates = review.reviewer_ids.sudo().filtered(lambda row: row.active and not row.share and row.login)
    if not candidates and review.reviewer_group_id:
        candidates = review.reviewer_group_id.sudo().users.filtered(
            lambda row: row.active and not row.share and row.login
        )
    governed = candidates.filtered(lambda row: xmlid(row).startswith("smart_construction_demo."))
    readable = env["res.users"]
    for candidate in governed.sorted("id"):
        scoped = request.with_user(candidate).with_company(candidate.company_id).with_context(
            allowed_company_ids=candidate.company_ids.ids
        )
        if not scoped.check_access_rights("read", raise_exception=False):
            continue
        try:
            scoped.check_access_rule("read")
        except Exception:
            continue
        readable |= candidate
    if not readable:
        raise RuntimeError(
            "tier review %s has no governed demo reviewer with record access" % review.id
        )
    actor = readable[0]
    chain.append(
        {
            "review_id": int(review.id),
            "sequence": int(review.sequence or 0),
            "status": str(review.status or ""),
            "group_id": int(review.reviewer_group_id.id or 0),
            "group_xmlid": xmlid(review.reviewer_group_id),
            "group_name": str(review.reviewer_group_id.display_name or ""),
            "actor_id": int(actor.id),
            "actor_login": str(actor.login or ""),
            "actor_xmlid": xmlid(actor),
            "candidate_logins": [str(row.login) for row in readable],
        }
    )

execution_policy = env["sc.approval.policy"].sudo().get_active_policy(
    "sc.payment.execution", company=request.company_id
)
if not execution_policy:
    raise RuntimeError("payment execution has no active approval policy authority")
execution_steps = execution_policy.step_ids.filtered("active").sorted("sequence")

payload = {
    "database": env.cr.dbname,
    "request_id": int(request.id),
    "request_name": str(request.name or ""),
    "validation_status": str(request.validation_status or ""),
    "chain": chain,
    "payment_execution_policy": {
        "id": int(execution_policy.id),
        "code": str(execution_policy.code or ""),
        "approval_required": bool(execution_policy.approval_required),
        "mode": str(execution_policy.mode or ""),
        "steps": [
            {
                "id": int(step.id),
                "sequence": int(step.sequence or 0),
                "group_id": int(step.approve_group_id.id or 0),
                "group_xmlid": xmlid(step.approve_group_id),
            }
            for step in execution_steps
        ],
    },
}
print("LOCAL_DEV_PAYMENT_APPROVAL_CHAIN_JSON=%s" % json.dumps(payload, ensure_ascii=True, separators=(",", ":")))
