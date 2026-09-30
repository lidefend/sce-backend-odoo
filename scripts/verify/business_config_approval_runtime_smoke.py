# -*- coding: utf-8 -*-
"""Rollback-only smoke for low-code approval policy runtime consumption.

This covers the shared configuration chain and newly adopted contract events, plans and construction diaries.
It does not claim full business-document coverage; every write is rolled back.
"""

from base64 import b64encode

from odoo.exceptions import AccessError, UserError


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


def _contract_event_checks(project, group, created):
    """Exercise the newly adopted document in the same rollback transaction."""
    env = _env()
    Policy = env["sc.approval.policy"].sudo()
    assert not Policy.with_context(active_test=False).search_count([
        ("target_model", "=", "sc.contract.event"),
        ("company_id", "in", [False, env.company.id]),
    ]), "existing contract-event configuration must not be overwritten"

    def event(label):
        record = env["sc.contract.event"].sudo().create({
            "name": "Approval runtime " + label, "event_type": "design_change",
            "project_id": project.id, "amount_impact": 100,
        })
        created.append((record._name, record.id))
        return record

    automatic = event("automatic")
    automatic.action_submit()
    assert automatic.state == "approved" and not automatic.review_ids
    assert automatic.state != "done"
    print("APPROVAL_CHECK=contract_event_unconfigured_submission_only_approves")
    policy = Policy.create({
        "name": "Runtime contract event", "code": "runtime_contract_event_smoke",
        "target_model": "sc.contract.event", "company_id": env.company.id,
        "approval_required": True, "mode": "single", "manager_group_id": group.id,
        "runtime_state": "tier_validation",
    })
    created.append((policy._name, policy.id))
    env["sc.approval.step"].sudo().create({
        "policy_id": policy.id, "name": "Contract event review", "sequence": 10,
        "approval_scope_key": policy._approval_scope_for_group(group), "approve_group_id": group.id,
    })
    policy.sync_tier_definitions()
    required = event("required")
    required.action_submit()
    assert required.state == "submitted" and required.review_ids
    assert required.validation_status in ("waiting", "pending")
    print("APPROVAL_CHECK=contract_event_configured_submission_creates_real_review")
    _approve_existing_reviews(required)
    assert required.state == "approved" and required.validation_status == "validated"
    required.action_done()
    assert required.state == "done"
    print("APPROVAL_CHECK=contract_event_real_approval_then_explicit_completion")
    rejected = event("rejection")
    rejected.action_submit()
    previous_ids = set(rejected.review_ids.ids)
    users = rejected.review_ids.mapped("reviewer_ids")
    actor = next((rejected.with_user(user) for user in users if rejected.with_user(user).can_review), None)
    assert actor is not None
    actor.env["sc.approval.policy"]._reject_submission_review(actor, reason="Runtime contract event rejection")
    rejected.invalidate_recordset()
    assert rejected.state == "rejected" and rejected.reject_reason == "Runtime contract event rejection"
    print("APPROVAL_CHECK=contract_event_real_rejection_preserves_reason")
    rejected.action_submit()
    assert rejected.state == "submitted" and previous_ids.isdisjoint(rejected.review_ids.ids)
    _approve_existing_reviews(rejected)
    assert rejected.state == "approved" and rejected.validation_status == "validated"
    print("APPROVAL_CHECK=contract_event_resubmission_uses_new_real_chain")


def _draft_confirmation_checks(project, group, created, model):
    assert model in ("sc.plan", "sc.construction.diary")
    is_plan = model == "sc.plan"
    label_prefix = "plan" if is_plan else "diary"
    env = _env()
    Policy = env["sc.approval.policy"].sudo()
    assert not Policy.with_context(active_test=False).search_count([
        ("target_model", "=", model), ("company_id", "in", [False, env.company.id]),
    ]), "existing %s configuration must not be overwritten" % model

    def plan(label):
        values = {"project_id": project.id}
        if is_plan:
            values.update(name="Approval runtime " + label, company_id=env.company.id,
                          planned_start="2026-09-30", planned_finish="2026-10-01")
        else:
            values.update(title="Approval runtime " + label, diary_type="施工日志",
                          description="Runtime approval content")
        record = env[model].sudo().create(values)
        created.append((record._name, record.id))
        return record

    automatic = plan("automatic")
    automatic.action_confirm()
    assert automatic.state == "confirmed" and not automatic.review_ids and (not is_plan or not automatic.actual_start)
    print("APPROVAL_CHECK=%s_unconfigured_confirmation_does_not_execute" % label_prefix)
    policy = Policy.create({
        "name": "Runtime " + label_prefix, "code": "runtime_%s_smoke" % label_prefix, "target_model": model,
        "company_id": env.company.id, "approval_required": True, "mode": "single",
        "manager_group_id": group.id, "runtime_state": "tier_validation",
    })
    created.append((policy._name, policy.id))
    env["sc.approval.step"].sudo().create({
        "policy_id": policy.id, "name": "Plan review", "sequence": 10,
        "approval_scope_key": policy._approval_scope_for_group(group), "approve_group_id": group.id,
    })
    policy.sync_tier_definitions()
    required = plan("required")
    required.action_confirm()
    assert required.state == "draft" and required.review_ids
    assert required.validation_status in ("waiting", "pending")
    denied = False
    try:
        with env.cr.savepoint():
            required.action_start() if is_plan else required.action_done()
    except UserError:
        denied = True
    assert denied and required.state == "draft" and (not is_plan or not required.actual_start)
    print("APPROVAL_CHECK=%s_pending_approval_cannot_execute" % label_prefix)
    _approve_existing_reviews(required)
    assert required.state == "confirmed" and required.validation_status == "validated" and (not is_plan or not required.actual_start)
    if is_plan:
        required.action_start()
        assert required.state == "in_progress" and required.actual_start
    required.action_done()
    assert required.state == "done" and (not is_plan or required.actual_finish)
    print("APPROVAL_CHECK=%s_real_approval_then_explicit_execution" % label_prefix)
    rejected = plan("rejection")
    rejected.action_confirm()
    previous_ids = set(rejected.review_ids.ids)
    users = rejected.review_ids.mapped("reviewer_ids")
    actor = next((rejected.with_user(user) for user in users if rejected.with_user(user).can_review), None)
    assert actor is not None
    actor.env["sc.approval.policy"]._reject_submission_review(actor, reason="Runtime %s rejection" % label_prefix)
    rejected.invalidate_recordset()
    assert rejected.state == "draft" and rejected.reject_reason == "Runtime %s rejection" % label_prefix
    print("APPROVAL_CHECK=%s_real_rejection_preserves_reason" % label_prefix)
    rejected.action_confirm()
    assert rejected.state == "draft" and rejected.review_ids and previous_ids.isdisjoint(rejected.review_ids.ids)
    _approve_existing_reviews(rejected)
    assert rejected.state == "confirmed" and rejected.validation_status == "validated" and not rejected.reject_reason
    print("APPROVAL_CHECK=%s_resubmission_completes_new_review_chain" % label_prefix)


def main():
    model_name = "sc.expense.claim"
    policy = _policy(model_name)
    fields = ["active", "approval_required", "mode", "runtime_state", "manager_group_id", "step_ids"]
    baseline = policy.read(fields)
    step_fields = ["active", "sequence", "approval_scope_key", "approve_group_id", "amount_min", "amount_max", "tier_definition_id"]
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
        # Reuse the current policy's reviewer group; two sequential decisions
        # remain two steps even when the same eligible reviewer handles both.
        group = policy.manager_group_id or policy.step_ids[:1].approve_group_id
        assert group, "missing reviewer group for linear approval"
        scope_key = policy._approval_scope_for_group(group)
        assert scope_key, "reviewer group lacks a configured approval scope"
        policy.step_ids.write({"active": False})
        linear_steps = []
        for sequence in (10, 20):
            linear_steps.append(_env()["sc.approval.step"].sudo().create({
                "policy_id": policy.id, "name": "Runtime linear step %s" % sequence,
                "active": True, "sequence": sequence, "approval_scope_key": scope_key, "approve_group_id": group.id,
            }))
        policy.write({"mode": "linear", "approval_required": True})
        policy.sync_tier_definitions()
        linear = _expense(project, partner, "linear")
        created.append((linear._name, linear.id))
        linear.action_submit()
        assert len(linear.review_ids) == 2 and all(linear.review_ids.mapped("approve_sequence")), [(r.id, r.sequence, r.name, r.definition_id.active, r.approve_sequence) for r in linear.review_ids]
        expected_definitions = [step.tier_definition_id.id for step in linear_steps]
        actual_definitions = linear.review_ids.sorted("sequence").mapped("definition_id").ids
        assert actual_definitions == expected_definitions, (actual_definitions, expected_definitions)
        print("APPROVAL_CHECK=linear_configuration_creates_two_sequential_reviews_in_configured_order")
        users = linear.review_ids.mapped("reviewer_ids")
        outsiders = _env()["res.users"].sudo().search([
            ("login", "=like", "fixture_role_%"), ("active", "=", True), ("share", "=", False),
            ("id", "not in", users.ids),
        ], limit=1)
        assert outsiders, "missing existing fixture non-reviewer"
        denied = False
        try:
            with _env().cr.savepoint():
                outsider = linear.with_user(outsiders)
                outsider.env["sc.approval.policy"]._approve_submission_review(outsider)
        except AccessError:
            denied = True
        assert denied and not linear.review_ids.filtered(lambda review: review.status == "approved")
        print("APPROVAL_CHECK=non_reviewer_cannot_approve")
        actor = next((linear.with_user(user) for user in users if linear.with_user(user).can_review), None)
        assert actor is not None
        actor.validate_tier()
        linear.invalidate_recordset()
        assert linear.state == "submit" and linear.validation_status in ("waiting", "pending")
        approved_reviews = linear.review_ids.filtered(lambda review: review.status == "approved")
        assert len(approved_reviews) == 1
        assert approved_reviews.definition_id.id == expected_definitions[0]
        print("APPROVAL_CHECK=first_linear_step_does_not_finish_document")
        _approve_existing_reviews(linear)
        assert linear.state == "approved" and linear.validation_status == "validated"
        assert all(review.status == "approved" for review in linear.review_ids)
        print("APPROVAL_CHECK=last_linear_step_finishes_document")
        _contract_event_checks(project, group, created)
        _draft_confirmation_checks(project, group, created, "sc.plan")
        _draft_confirmation_checks(project, group, created, "sc.construction.diary")
        passed = True
    finally:
        _env().cr.rollback()
        _env().invalidate_all()
        assert policy.read(fields) == baseline, "approval configuration was not restored"
        assert policy.step_ids.read(step_fields) == step_baseline, "approval steps were not restored"
        assert all(not _env()[model].sudo().browse(record_id).exists() for model, record_id in created), "temporary document remains"
        print("BUSINESS_CONFIG_APPROVAL_RUNTIME_ROLLBACK=VERIFIED")
    if passed:
        print("BUSINESS_CONFIG_APPROVAL_RUNTIME_SMOKE=PASS checks=27")


main()
