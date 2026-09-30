# -*- coding: utf-8 -*-
"""Rollback-only smoke for low-code approval policy runtime consumption.

This intentionally uses one current-contract-valid business document. Broad
multi-document approval regressions stay in the dedicated finance/document
approval smoke targets.
"""

from base64 import b64encode

from odoo.exceptions import UserError


def _env():
    return globals()["env"]


def _policy(model_name):
    policy = _env()["sc.approval.policy"].sudo().search([("target_model", "=", model_name)], limit=1)
    if not policy:
        raise AssertionError("missing approval policy for %s" % model_name)
    return policy


def _set_policy(model_name, enabled):
    policy = _policy(model_name)
    policy.write(
        {
            "active": True,
            "approval_required": bool(enabled),
            "mode": "single" if enabled else "none",
            "runtime_state": "tier_validation",
        }
    )
    policy.sync_tier_definitions()
    return policy


def _project(name):
    return _env()["project.project"].sudo().create({"name": name, "code": name.upper().replace(" ", "-")[:32], "company_id": _env().company.id})


def _partner(name):
    return _env()["res.partner"].sudo().create({"name": name})


def _attach(record, label):
    attachment = _env()["ir.attachment"].sudo().create(
        {
            "name": "%s.txt" % label,
            "datas": b64encode(("business-config-approval-runtime:%s" % label).encode("utf-8")).decode("ascii"),
            "res_model": record._name,
            "res_id": record.id,
            "mimetype": "text/plain",
        }
    )
    if "attachment_ids" in record._fields:
        record.write({"attachment_ids": [(4, attachment.id)]})
    return attachment


def _expense(project, partner, suffix):
    claim = _env()["sc.expense.claim"].sudo().create(
        {
            "claim_type": "project_company_repay",
            "expense_type": "还款登记",
            "project_id": project.id,
            "partner_id": partner.id,
            "amount": 100.0,
            "approved_amount": 100.0,
            "paid_amount": 0.0,
            "summary": "Business config approval runtime smoke %s" % suffix,
            "payment_account_name": "Business config smoke payer",
            "payer_account": "BUSINESS-CONFIG-SMOKE-PAYER-%s" % suffix,
            "receipt_account_name": "Business config smoke receiver",
            "payee_account": "BUSINESS-CONFIG-SMOKE-RECEIVER-%s" % suffix,
        }
    )
    _attach(claim, "business-config-approval-runtime-%s" % suffix)
    return claim


def _approve_existing_reviews(record):
    """Use actual reviewers and native decisions; never write review outcomes."""
    for _step in range(32):
        record.invalidate_recordset()
        if record.validation_status == "validated":
            return
        assert record.review_ids, "approval instance missing"
        before = [(review.id, review.status) for review in record.review_ids]
        users = record.review_ids.mapped("reviewer_ids").filtered(lambda user: user.active and not user.share)
        actor = next((record.with_user(user) for user in users if record.with_user(user).can_review), None)
        assert actor is not None, "no authorized reviewer for current step"
        actor.validate_tier()
        record.invalidate_recordset()
        after = [(review.id, review.status) for review in record.review_ids]
        assert after != before, "native approval did not progress (possibly requires comment wizard)"
    raise AssertionError("approval chain exceeded bounded step count")


def main():
    model_name = "sc.expense.claim"
    policy = _policy(model_name)
    fields = ["active", "approval_required", "mode", "runtime_state", "manager_group_id", "step_ids"]
    baseline = policy.read(fields)
    step_fields = ["active", "sequence", "approve_group_id", "amount_min", "amount_max", "tier_definition_id"]
    step_baseline = policy.step_ids.read(step_fields)
    created = []
    passed = False
    try:
        project = _project("Business Config Approval Runtime")
        partner = _partner("Business Config Approval Runtime Partner")
        created.extend([(project._name, project.id), (partner._name, partner.id)])

        _set_policy(model_name, True)
        required = _expense(project, partner, "required")
        created.append((required._name, required.id))
        required.action_submit()
        required.invalidate_recordset()
        assert required.state == "submit", required.state
        assert required.review_ids and required.validation_status in ("pending", "waiting"), required.validation_status
        print("APPROVAL_CHECK=enabled_submission_has_real_reviews")

        _set_policy(model_name, False)
        try:
            with _env().cr.savepoint():
                required.action_on_tier_approved()
        except UserError:
            pass
        required.invalidate_recordset()
        assert required.state == "submit", "disabled configuration bypassed live instance"
        print("APPROVAL_CHECK=configuration_change_does_not_bypass_instance")
        _approve_existing_reviews(required)
        assert required.state == "approved", required.state
        assert required.validation_status == "validated"
        assert all(review.status == "approved" for review in required.review_ids)
        print("APPROVAL_CHECK=native_reviewers_complete_real_chain")

        optional = _expense(project, partner, "optional")
        created.append((optional._name, optional.id))
        optional.action_submit()
        optional.invalidate_recordset()
        assert optional.state == "approved", optional.state
        assert not optional.review_ids and optional.validation_status == "no"
        print("APPROVAL_CHECK=disabled_submission_auto_approves_without_fake_reviews")
        _set_policy(model_name, True)
        steps = policy.step_ids.filtered("active")
        assert steps, "missing active approval configuration"
        ranges = [(step, step.amount_min, step.amount_max) for step in steps]
        steps.write({"amount_min": 10000.0, "amount_max": 0.0})
        missing = _expense(project, partner, "missing-rule")
        created.append((missing._name, missing.id))
        denied = False
        try:
            with _env().cr.savepoint():
                missing.action_submit()
        except UserError as exc:
            assert "没有匹配" in str(exc), str(exc)
            denied = True
        assert denied, "enabled approval with no matching rule was accepted"
        missing.invalidate_recordset()
        assert missing.state == "draft" and not missing.review_ids
        print("APPROVAL_CHECK=missing_rule_fails_without_partial_submission")
        for step, minimum, maximum in ranges:
            step.write({"amount_min": minimum, "amount_max": maximum})

        retry = _expense(project, partner, "reject-resubmit")
        created.append((retry._name, retry.id))
        retry.action_submit()
        previous_ids = set(retry.review_ids.ids)
        users = retry.review_ids.mapped("reviewer_ids").filtered(lambda user: user.active and not user.share)
        actor = next((retry.with_user(user) for user in users if retry.with_user(user).can_review), None)
        assert actor is not None, "no reviewer available to reject"
        actor.env["sc.approval.policy"]._reject_submission_review(actor, reason="runtime rejection evidence")
        retry.invalidate_recordset()
        # Native tier.validation clears reviews when returning from submit to draft.
        # The document reason and business audit preserve the rejected decision.
        assert retry.state == "draft" and retry.validation_status == "no", (retry.state, retry.validation_status)
        assert not retry.review_ids and retry.reject_reason == "runtime rejection evidence"
        assert _env()["sc.audit.log"].sudo().search_count([
            ("model", "=", retry._name), ("res_id", "=", retry.id),
            ("event_code", "=", "expense_claim_rejected"),
        ]) == 1
        print("APPROVAL_CHECK=real_rejection_returns_document_to_draft")
        retry.action_submit()
        retry.invalidate_recordset()
        assert retry.state == "submit" and retry.review_ids
        assert previous_ids.isdisjoint(retry.review_ids.ids), "rejected attempt reused"
        _approve_existing_reviews(retry)
        assert retry.state == "approved" and retry.validation_status == "validated"
        print("APPROVAL_CHECK=resubmission_creates_and_completes_new_review_chain")
        passed = True
    finally:
        _env().cr.rollback()
        _env().invalidate_all()
        assert policy.read(fields) == baseline, "approval configuration was not restored"
        assert policy.step_ids.read(step_fields) == step_baseline, "approval steps were not restored"
        assert all(not _env()[model].sudo().browse(record_id).exists() for model, record_id in created), "temporary document remains"
        print("BUSINESS_CONFIG_APPROVAL_RUNTIME_ROLLBACK=VERIFIED")
    if passed:
        print("BUSINESS_CONFIG_APPROVAL_RUNTIME_SMOKE=PASS checks=8")


main()
