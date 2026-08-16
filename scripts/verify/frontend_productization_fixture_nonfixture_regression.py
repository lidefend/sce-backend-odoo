# -*- coding: utf-8 -*-
"""Transactional sentinel proving fixture initialization preserves foreign data."""

import json

from odoo.addons.smart_construction_acceptance_fixture.tools.frontend_productization_fixture import ensure_fixture


def fail(message):
    print("[verify.frontend.fixture.nonfixture] FAIL %s" % message)
    raise SystemExit(2)


savepoint = env.cr.savepoint()
savepoint.__enter__()
try:
    pm = env["res.users"].sudo().search([("login", "=", "fixture_role_pm")], limit=1)
    member = env["res.users"].sudo().search(
        [("login", "=", "fixture_role_project_a_member")], limit=1
    )
    company = env["res.company"].sudo().search([("name", "=", "FE Company A")], limit=1)
    if not pm or not member or not company:
        fail("fixture principals are missing")

    project = env["project.project"].sudo().create(
        {
            "name": "NON-FIXTURE SENTINEL (transactional)",
            "company_id": company.id,
            "user_id": pm.id,
            "manager_id": pm.id,
        }
    )
    project.message_subscribe(partner_ids=[pm.partner_id.id, member.partner_id.id])
    task = env["project.task"].sudo().create(
        {"name": "NON-FIXTURE BUSINESS SENTINEL", "project_id": project.id}
    )

    def snapshot():
        current = env["project.project"].sudo().browse(project.id).exists()
        current_task = env["project.task"].sudo().browse(task.id).exists()
        followers = env["mail.followers"].sudo().search(
            [("res_model", "=", "project.project"), ("res_id", "=", project.id)]
        )
        return {
            "project_exists": bool(current),
            "user_id": current.user_id.id if current else False,
            "manager_id": current.manager_id.id if current else False,
            "follower_partner_ids": sorted(followers.mapped("partner_id").ids),
            "business_record": {
                "exists": bool(current_task),
                "project_id": current_task.project_id.id if current_task else False,
                "name": current_task.name if current_task else False,
            },
        }

    before = snapshot()

    # A successful reject/correct/resubmit browser journey leaves this
    # fixture-owned request in a protected workflow state with changed facts.
    # The next governed reset must remain idempotent without weakening the
    # payment.request ORM immutability guard.
    reject_request = env.ref(
        "smart_construction_acceptance_fixture.fe_journey_payment_request_reject_a"
    )
    env.cr.execute(
        "UPDATE payment_request "
        "SET state='submit', validation_status='no', "
        "note=%s, reject_reason=NULL WHERE id=%s",
        ("fixture idempotency sentinel", reject_request.id),
    )
    reject_request.invalidate_recordset(
        ["state", "validation_status", "note", "reject_reason"]
    )
    ensure_fixture(env)
    reject_request.invalidate_recordset(
        ["state", "validation_status", "note", "reject_reason"]
    )
    if (
        reject_request.state != "submit"
        or reject_request.validation_status != "no"
        or reject_request.note != "FE-B05 isolated approval journey"
        or reject_request.reject_reason
    ):
        fail(
            "approval journey reset is not idempotent: state=%s validation=%s "
            "note=%s reject_reason=%s"
            % (
                reject_request.state,
                reject_request.validation_status,
                reject_request.note,
                reject_request.reject_reason,
            )
        )
    after = snapshot()
    if before != after:
        fail("foreign project changed: before=%s after=%s" % (before, after))

    print("[verify.frontend.fixture.nonfixture] PASS")
    print(json.dumps({"db": env.cr.dbname, "before": before, "after": after}, ensure_ascii=False, indent=2))
finally:
    savepoint.__exit__(Exception, Exception("rollback sentinel"), None)
