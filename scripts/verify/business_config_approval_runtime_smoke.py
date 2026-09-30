# -*- coding: utf-8 -*-
"""Rollback-only smoke for low-code approval policy runtime consumption.

This covers the shared configuration chain and newly adopted contract events, plans, construction diaries and tax registrations.
It does not claim full business-document coverage; every write is rolled back.
"""

import os
import json
from base64 import b64encode
from datetime import timedelta
from odoo import fields

from odoo.exceptions import AccessError, UserError
from psycopg2 import IntegrityError


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
    attachment = record.env["ir.attachment"].sudo().create(
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
        company = record.company_id if "company_id" in record._fields else record.project_id.company_id if "project_id" in record._fields else record.env.company
        users = record.review_ids.mapped("reviewer_ids").filtered(
            lambda user: user.active and not user.share and company in user.sudo().company_ids
        )
        candidates = [record.with_user(user).with_context(allowed_company_ids=[company.id]).with_company(company) for user in users]
        actor = next((candidate for candidate in candidates if candidate.can_review), None)
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

    def assert_content_locked(record, phase):
        names = ["project_id", "amount_impact", "description", "settlement_included"]
        before = record.read(names)
        for values in ({"amount_impact": 999}, {"project_id": False}, {"description": "rewritten"}, {"settlement_included": True}):
            refused = False
            try:
                with env.cr.savepoint():
                    record.with_context(skip_validation_check=True, sc_document_state_token=True).write(values)
            except UserError:
                refused = True
            assert refused, "reviewed event content write permitted"
        record.invalidate_recordset()
        assert record.read(names) == before
        print("APPROVAL_CHECK=contract_event_%s_content_locked" % phase)

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
    assert_content_locked(required, "pending")
    _approve_existing_reviews(required)
    assert required.state == "approved" and required.validation_status == "validated"
    assert_content_locked(required, "approved")
    required.action_done()
    assert required.state == "done"
    assert_content_locked(required, "done")
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
    rejected.write({"description": "Corrected event after real rejection"})
    rejected.invalidate_recordset()
    assert rejected.description == "Corrected event after real rejection"
    assert env["sc.workflow.contract.service"].describe_record(rejected)["editability"] == "editable"
    print("APPROVAL_CHECK=contract_event_rejected_content_and_contract_editable")
    rejected.action_submit()
    assert rejected.state == "submitted" and previous_ids.isdisjoint(rejected.review_ids.ids)
    _approve_existing_reviews(rejected)
    assert rejected.state == "approved" and rejected.validation_status == "validated"
    print("APPROVAL_CHECK=contract_event_resubmission_uses_new_real_chain")


def _contract_event_state_authority_checks(project, group, created):
    env = _env()
    Event = env["sc.contract.event"].sudo()
    values = {"name": "Runtime contract event state protection", "event_type": "design_change",
              "project_id": project.id, "amount_impact": 100}

    def denied(call):
        refused = False
        try:
            with env.cr.savepoint():
                call()
        except UserError:
            refused = True
        assert refused, "contract event state bypass unexpectedly permitted"

    for state in ("submitted", "approved", "rejected", "done", "cancel"):
        denied(lambda: Event.create(dict(values, state=state)))
        denied(lambda: Event.with_context(default_state=state).create(values))
    print("APPROVAL_CHECK=contract_event_external_state_create_and_defaults_denied")
    draft = Event.create(values)
    created.append((draft._name, draft.id))
    for context in ({}, {"sc_document_state_token": True}, {"skip_validation_check": True}):
        for state in ("submitted", "approved", "done"):
            denied(lambda: draft.with_context(**context).write({"state": state}))
    draft.invalidate_recordset()
    assert draft.state == "draft"
    print("APPROVAL_CHECK=contract_event_external_state_write_denied")
    draft.write({"description": "Edited draft content"})
    draft.action_cancel()
    draft.invalidate_recordset()
    assert draft.state == "cancel"
    print("APPROVAL_CHECK=contract_event_formal_cancel_and_draft_edit_preserved")
    _contract_event_checks(project, group, created)


def _plan_state_authority_checks(project, group, created):
    env = _env()
    Plan = env["sc.plan"].sudo()
    values = {"name": "Runtime plan state protection", "project_id": project.id,
              "planned_start": "2026-09-30", "planned_finish": "2026-10-01"}

    def denied(call):
        refused = False
        try:
            with env.cr.savepoint():
                call()
        except UserError:
            refused = True
        assert refused, "plan state bypass unexpectedly permitted"

    for state in ("confirmed", "in_progress", "done", "cancel"):
        denied(lambda: Plan.create(dict(values, state=state)))
        denied(lambda: Plan.with_context(default_state=state).create(values))
    print("APPROVAL_CHECK=plan_external_state_create_and_defaults_denied")
    draft = Plan.create(values)
    created.append((draft._name, draft.id))
    for context in ({}, {"sc_document_state_token": True}, {"skip_validation_check": True}):
        for state in ("confirmed", "in_progress", "done"):
            denied(lambda: draft.with_context(**context).write({"state": state}))
    draft.invalidate_recordset()
    assert draft.state == "draft" and not draft.actual_start and not draft.actual_finish
    print("APPROVAL_CHECK=plan_external_state_write_denied")
    draft.write({"note": "Edited draft content"})
    draft.action_cancel()
    draft.invalidate_recordset()
    assert draft.state == "cancel"
    draft.action_reset_draft()
    draft.invalidate_recordset()
    assert draft.state == "draft" and not draft.actual_start and not draft.actual_finish
    print("APPROVAL_CHECK=plan_formal_cancel_reset_and_draft_edit_preserved")
    node = env["sc.plan.line"].sudo().create({"plan_id": draft.id, "name": "Runtime reviewed node"})
    created.append((node._name, node.id))
    draft.action_confirm()
    baseline = node.read(["name", "plan_id", "planned_finish", "progress_rate"])
    denied(lambda: node.write({"name": "changed baseline"}))
    denied(lambda: draft.write({"line_ids": [(1, node.id, {"planned_finish": "2026-12-31"})]}))
    denied(lambda: node.unlink())
    denied(lambda: env["sc.plan.line"].sudo().create({"plan_id": draft.id, "name": "late node"}))
    denied(lambda: node.write({"progress_rate": 50}))
    node.invalidate_recordset()
    assert node.read(["name", "plan_id", "planned_finish", "progress_rate"]) == baseline
    print("APPROVAL_CHECK=plan_node_approved_baseline_and_structure_locked")
    draft.action_start()
    draft.write({"line_ids": [(1, node.id, {"progress_rate": 50, "state": "in_progress"})]})
    node.invalidate_recordset()
    assert node.progress_rate == 50 and node.state == "in_progress"
    denied(lambda: node.with_context(skip_validation_check=True).write({"name": "rewrite during execution"}))
    node.write({"progress_rate": 100, "state": "done"})
    draft.action_done()
    denied(lambda: node.write({"progress_rate": 0}))
    print("APPROVAL_CHECK=plan_node_execution_updates_preserved_and_terminal_locked")
    _draft_confirmation_checks(project, group, created, "sc.plan")


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

    def assert_document_content_locked(record, phase):
        fields = (["name", "project_id", "company_id", "planned_start", "planned_finish", "note"] if is_plan
                  else ["project_id", "title", "description", "date_diary", "note", "active"])
        changes = ({"name": "changed reviewed plan"}, {"project_id": False}, {"note": "changed plan"},
                   {"planned_finish": "2026-12-31"}) if is_plan else (
                       {"title": "changed reviewed title"}, {"description": "changed reviewed content"},
                       {"project_id": False}, {"note": "changed supporting content"}, {"active": False})
        baseline = record.read(fields)
        for values in changes:
            refused = False
            try:
                with env.cr.savepoint():
                    record.with_context(skip_validation_check=True, sc_document_state_token=True).write(values)
            except UserError:
                refused = True
            assert refused, "reviewed document content write permitted"
        record.invalidate_recordset()
        assert record.read(fields) == baseline
        print("APPROVAL_CHECK=%s_%s_content_locked" % (label_prefix, phase))

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
    assert_document_content_locked(required, "pending")
    _approve_existing_reviews(required)
    assert required.state == "confirmed" and required.validation_status == "validated" and (not is_plan or not required.actual_start)
    assert_document_content_locked(required, "approved")
    if is_plan:
        required.action_start()
        assert required.state == "in_progress" and required.actual_start
        assert_document_content_locked(required, "execution")
    required.action_done()
    assert required.state == "done" and (not is_plan or required.actual_finish)
    print("APPROVAL_CHECK=%s_real_approval_then_explicit_execution" % label_prefix)
    assert_document_content_locked(required, "done")
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
    if is_plan:
        rejected.write({"note": "Corrected plan after real rejection"})
        rejected.invalidate_recordset()
        assert rejected.note == "Corrected plan after real rejection"
        print("APPROVAL_CHECK=plan_rejected_content_edit_preserved")
    if not is_plan:
        rejected.write({"description": "Corrected content after real rejection"})
        rejected.invalidate_recordset()
        assert rejected.description == "Corrected content after real rejection"
        print("APPROVAL_CHECK=diary_rejected_content_edit_preserved")
    rejected.action_confirm()
    assert rejected.state == "draft" and rejected.review_ids and previous_ids.isdisjoint(rejected.review_ids.ids)
    _approve_existing_reviews(rejected)
    assert rejected.state == "confirmed" and rejected.validation_status == "validated" and not rejected.reject_reason
    print("APPROVAL_CHECK=%s_resubmission_completes_new_review_chain" % label_prefix)


def _diary_state_authority_checks(project, group, created):
    env = _env()
    Diary = env["sc.construction.diary"].sudo()
    values = {"project_id": project.id, "title": "Runtime diary state protection",
              "description": "Rollback-only diary content"}

    def denied(call):
        refused = False
        try:
            with env.cr.savepoint():
                call()
        except UserError:
            refused = True
        assert refused, "diary state bypass unexpectedly permitted"

    for state in ("confirmed", "done", "cancel"):
        denied(lambda: Diary.create(dict(values, state=state)))
        denied(lambda: Diary.with_context(default_state=state).create(values))
    print("APPROVAL_CHECK=diary_external_terminal_create_and_defaults_denied")
    draft = Diary.create(values)
    created.append((draft._name, draft.id))
    for context in ({}, {"sc_document_state_token": True}, {"skip_validation_check": True}):
        for change in ({"state": "confirmed"}, {"state": "done"}, {"source_origin": "legacy"}):
            denied(lambda: draft.with_context(**context).write(change))
    draft.invalidate_recordset()
    assert draft.state == "draft" and draft.source_origin == "manual"
    print("APPROVAL_CHECK=diary_external_state_and_origin_write_denied")
    draft.write({"description": "Edited draft content"})
    draft.action_cancel()
    draft.invalidate_recordset()
    assert draft.state == "cancel"
    print("APPROVAL_CHECK=diary_formal_cancel_and_draft_edit_preserved")
    _draft_confirmation_checks(project, group, created, "sc.construction.diary")


def _tax_approval_checks(project, group, created):
    env = _env()
    model = "sc.tax.deduction.registration"
    Policy = env["sc.approval.policy"].sudo()
    assert not Policy.with_context(active_test=False).search_count([
        ("target_model", "=", model), ("company_id", "in", [False, env.company.id]),
    ]), "existing tax approval configuration must not be overwritten"

    def document(label):
        record = env[model].sudo().create({
            "project_id": project.id, "invoice_no": "APPROVAL-RUNTIME-" + label,
            "invoice_amount_untaxed": 100.0, "invoice_tax_amount": 13.0,
        })
        created.append((record._name, record.id))
        return record

    automatic = document("automatic")
    automatic.action_confirm()
    assert automatic.state == "confirmed" and not automatic.review_ids
    assert not automatic.deduction_confirm_date
    assert (automatic.deduction_amount, automatic.deduction_tax_amount) == (100, 13)
    print("APPROVAL_CHECK=tax_unconfigured_prepares_amounts_without_deduction")
    policy = Policy.create({
        "name": "Runtime tax approval", "code": "runtime_tax_approval_smoke", "target_model": model,
        "company_id": env.company.id, "approval_required": True, "mode": "single",
        "manager_group_id": group.id, "runtime_state": "tier_validation",
    })
    created.append((policy._name, policy.id))
    step = env["sc.approval.step"].sudo().create({
        "policy_id": policy.id, "name": "Tax amount review", "sequence": 10,
        "approval_scope_key": policy._approval_scope_for_group(group), "approve_group_id": group.id,
        "amount_min": 50, "amount_max": 150,
    })
    policy.sync_tier_definitions()
    required = document("required")
    required.action_confirm()
    assert required.state == "draft" and required.review_ids
    assert required.validation_status in ("waiting", "pending")
    assert required.deduction_amount == 100
    print("APPROVAL_CHECK=tax_threshold_matches_prepared_invoice_amount")
    denied = False
    try:
        with env.cr.savepoint():
            required.action_deduct()
    except UserError:
        denied = True
    assert denied and required.state == "draft" and not required.deduction_confirm_date
    print("APPROVAL_CHECK=tax_pending_approval_cannot_deduct")
    _approve_existing_reviews(required)
    assert required.state == "confirmed" and required.validation_status == "validated"
    assert not required.deduction_confirm_date
    print("APPROVAL_CHECK=tax_real_approval_does_not_deduct")
    rejected = document("rejection")
    rejected.action_confirm()
    previous_ids = set(rejected.review_ids.ids)
    users = rejected.review_ids.mapped("reviewer_ids")
    actor = next((rejected.with_user(user) for user in users if rejected.with_user(user).can_review), None)
    assert actor is not None
    actor.env["sc.approval.policy"]._reject_submission_review(actor, reason="Runtime tax rejection")
    rejected.invalidate_recordset()
    assert rejected.state == "draft" and rejected.reject_reason == "Runtime tax rejection"
    assert env["sc.audit.log"].sudo().search_count([
        ("model", "=", model), ("res_id", "=", rejected.id), ("event_code", "=", "tax_deduction_rejected"),
    ]) == 1
    print("APPROVAL_CHECK=tax_rejection_preserves_reason_and_audit")
    rejected.action_confirm()
    assert rejected.review_ids and previous_ids.isdisjoint(rejected.review_ids.ids)
    _approve_existing_reviews(rejected)
    assert rejected.state == "confirmed" and not rejected.reject_reason and not rejected.deduction_confirm_date
    print("APPROVAL_CHECK=tax_resubmission_completes_new_chain")
    step.write({"amount_min": 1000, "amount_max": 0})
    policy.sync_tier_definitions()
    missing = document("missing-rule")
    denied = False
    try:
        with env.cr.savepoint():
            missing.action_confirm()
    except UserError as exc:
        assert "没有匹配" in str(exc), str(exc)
        denied = True
    missing.invalidate_recordset()
    assert denied and missing.state == "draft" and not missing.review_ids
    print("APPROVAL_CHECK=tax_unmatched_enabled_policy_fails_closed")


def _task_approval_checks(project, group, created):
    env = _env()
    model = "project.task"
    Policy = env["sc.approval.policy"].sudo()
    assert not Policy.with_context(active_test=False).search_count([
        ("target_model", "=", model), ("company_id", "in", [False, env.company.id]),
    ]), "existing task approval configuration must not be overwritten"

    def document(label):
        record = env[model].sudo().create({"project_id": project.id, "name": "Approval runtime " + label})
        created.append((record._name, record.id))
        return record

    automatic = document("automatic")
    automatic.action_prepare_task()
    assert automatic.sc_state == "ready" and not automatic.review_ids
    print("APPROVAL_CHECK=task_unconfigured_submission_ready_not_started")
    policy = Policy.create({
        "name": "Runtime task approval", "code": "runtime_task_approval_smoke", "target_model": model,
        "company_id": env.company.id, "approval_required": True, "mode": "single",
        "manager_group_id": group.id, "runtime_state": "tier_validation",
    })
    created.append((policy._name, policy.id))
    env["sc.approval.step"].sudo().create({
        "policy_id": policy.id, "name": "Task review", "sequence": 10,
        "approval_scope_key": policy._approval_scope_for_group(group), "approve_group_id": group.id,
    })
    policy.sync_tier_definitions()
    required = document("required")
    assert required._execution_approval_block() == "EXECUTION_TASK_APPROVAL_REQUIRED"
    required.action_prepare_task()
    assert required.sc_state == "draft" and required.review_ids
    assert required._execution_approval_block() == "EXECUTION_TASK_APPROVAL_PENDING"
    denied = False
    try:
        with env.cr.savepoint(): required.action_start_task()
    except UserError:
        denied = True
    assert denied and required.sc_state == "draft"
    print("APPROVAL_CHECK=task_pending_approval_cannot_start")
    _approve_existing_reviews(required)
    assert required.sc_state == "ready" and required.validation_status == "validated"
    assert not required._execution_approval_block()
    required.action_start_task()
    assert required.sc_state == "in_progress"
    print("APPROVAL_CHECK=task_real_approval_then_explicit_start")
    rejected = document("rejection")
    rejected.action_prepare_task()
    previous_ids = set(rejected.review_ids.ids)
    users = rejected.review_ids.mapped("reviewer_ids")
    actor = next((rejected.with_user(user) for user in users if rejected.with_user(user).can_review), None)
    assert actor is not None
    actor.env["sc.approval.policy"]._reject_submission_review(actor, reason="Runtime task rejection")
    rejected.invalidate_recordset()
    assert rejected.sc_state == "draft" and rejected.reject_reason == "Runtime task rejection"
    print("APPROVAL_CHECK=task_rejection_preserves_reason")
    rejected.action_prepare_task()
    assert rejected.review_ids and previous_ids.isdisjoint(rejected.review_ids.ids)
    _approve_existing_reviews(rejected)
    assert rejected.sc_state == "ready" and not rejected.reject_reason
    print("APPROVAL_CHECK=task_resubmission_completes_new_chain")


def _project_creation_state_checks(project, group, created):
    env = _env()
    Project = env["project.project"].sudo()
    for default_state in ("approved", "unknown", False):
        denied = False
        try:
            with env.cr.savepoint():
                Project.with_context(default_sc_approval_state=default_state).create({
                    "name": "Runtime unsubmitted project", "code": "RUNTIME-STATE-DENIED",
                    "company_id": env.company.id,
                })
        except UserError:
            denied = True
        assert denied, "context default must not create an approved or invalid project state"
        print("APPROVAL_CHECK=project_creation_default_%s_denied" % default_state)
    for label, context, values in (
        ("explicit", {"default_sc_approval_state": "approved"}, {"sc_approval_state": "draft"}),
        ("default", {"default_sc_approval_state": "draft"}, {}),
    ):
        record = Project.with_context(**context).create({
            "name": "Runtime project draft " + label, "code": "RUNTIME-DRAFT-" + label.upper(),
            "company_id": env.company.id, **values,
        })
        created.append((record._name, record.id))
        record.invalidate_recordset()
        assert record.sc_approval_state == "draft" and record.lifecycle_state == "draft"
        assert not record.review_ids
        print("APPROVAL_CHECK=project_creation_%s_draft_preserved" % label)


def _project_document_approval_checks(project, group, created):
    env = _env()
    model = "sc.project.document"
    Policy = env["sc.approval.policy"].sudo()
    assert not Policy.with_context(active_test=False).search_count([("target_model", "=", model), ("company_id", "in", [False, project.company_id.id])])
    doc_type = env["sc.dictionary"].sudo().search([("type", "=", "doc_type")], limit=1)
    assert doc_type, "existing document classification required"
    def document():
        record = env[model].sudo().create({"name": "Rollback project document", "project_id": project.id,
            "company_id": project.company_id.id, "doc_type_id": doc_type.id})
        created.append((record._name, record.id))
        return record
    def denied(action):
        refused = False
        try:
            with env.cr.savepoint(): action()
        except UserError:
            refused = True
        assert refused, "document approval boundary bypassed"
    automatic = document()
    denied(lambda: automatic.write({"state": "done"}))
    denied(lambda: env[model].sudo().with_context(default_state="done").create({"name": "Denied document", "project_id": project.id, "doc_type_id": doc_type.id}))
    denied(automatic.action_approve)
    print("APPROVAL_CHECK=project_document_external_state_and_early_archive_denied")
    automatic.action_submit()
    assert automatic.state == "approved" and not automatic.review_ids
    print("APPROVAL_CHECK=project_document_auto_approval_does_not_archive")
    denied(lambda: automatic.write({"name": "Changed reviewed content"}))
    automatic.action_archive()
    assert automatic.state == "done"
    denied(automatic.action_archive)
    automatic.action_reset_to_draft()
    assert automatic.state == "draft" and not automatic.review_ids
    print("APPROVAL_CHECK=project_document_explicit_archive_and_reopen")
    policy = Policy.create({"name": "Runtime document approval", "code": "runtime_project_document_approval", "target_model": model,
        "company_id": project.company_id.id, "approval_required": True, "mode": "single", "manager_group_id": group.id, "runtime_state": "tier_validation"})
    created.append((policy._name, policy.id))
    step = env["sc.approval.step"].sudo().create({"policy_id": policy.id, "name": "Document review", "sequence": 10,
        "approval_scope_key": policy._approval_scope_for_group(group), "approve_group_id": group.id})
    denied(lambda: step.write({"amount_min": 1}))
    policy.sync_tier_definitions()
    print("APPROVAL_CHECK=project_document_no_invented_amount_authority")
    required = document()
    required.action_submit()
    assert required.state == "review" and required.review_ids
    contract = env["sc.workflow.contract.service"].describe_record(required)
    assert contract["approvalPhase"] in ("waiting", "pending")
    assert any(action["method"] == "action_archive" and action["action_semantics"]["purpose"] == "complete" for action in contract["actions"])
    denied(required.action_archive)
    denied(required.action_reset_to_draft)
    policy.write({"approval_required": False})
    denied(required.action_submit)
    policy.write({"approval_required": True})
    print("APPROVAL_CHECK=project_document_pending_review_cannot_be_bypassed")
    _approve_existing_reviews(required)
    assert required.state == "approved"
    required.action_archive()
    assert required.state == "done"
    print("APPROVAL_CHECK=project_document_real_review_then_explicit_archive")
    required.action_reset_to_draft()
    required.action_submit()
    assert required.state == "review" and required.validation_status in ("waiting", "pending")
    print("APPROVAL_CHECK=project_document_reopen_requires_new_review")
    users = required.review_ids.mapped("reviewer_ids").filtered(lambda user: user.active and not user.share and required.company_id in user.sudo().company_ids)
    candidates = [required.with_user(user).with_context(allowed_company_ids=[required.company_id.id]).with_company(required.company_id) for user in users]
    actor = next((record for record in candidates if record.can_review), None)
    assert actor is not None
    previous = set(required.review_ids.ids)
    actor.env["sc.approval.policy"]._reject_submission_review(actor, reason="Runtime document rejection")
    required.invalidate_recordset()
    assert required.state == "draft" and required.reject_reason == "Runtime document rejection"
    required.action_submit()
    assert required.review_ids and previous.isdisjoint(required.review_ids.ids)
    _approve_existing_reviews(required)
    assert required.state == "approved" and not required.reject_reason
    print("APPROVAL_CHECK=project_document_rejected_resubmission_new_chain")


def _receipt_income_checks(group, created):
    """Actual finance handling against an existing approved source, rollback-only."""
    base = _env()
    finance = base["res.users"].sudo().search([("login", "=", "fixture_role_finance"), ("active", "=", True)], limit=1)
    assert finance, "existing finance fixture required"
    company = finance.company_id
    env = base["sc.receipt.income"].with_user(finance).with_company(company).with_context(allowed_company_ids=[company.id]).env
    assert not env.su
    request = env["payment.request"].search([
        ("company_id", "=", company.id), ("type", "=", "receive"),
        ("state", "=", "approved"), ("contract_id", "!=", False), ("amount", ">", 0),
    ], limit=1)
    assert request, "existing finance-visible approved receive request with contract required"
    request_fields = ["state", "amount", "contract_id", "partner_id", "project_id", "currency_id"]
    before = request.read(request_fields)
    model = "sc.receipt.income"
    Policy = env["sc.approval.policy"].sudo()
    policies = Policy.with_context(active_test=False).search([("target_model", "=", model), ("company_id", "in", [False, company.id])])

    def denied(call):
        refused = False
        try:
            with env.cr.savepoint():
                call()
        except UserError:
            refused = True
        assert refused, "receipt approval/content boundary bypassed"

    def document():
        record = env[model].create({
            "payment_request_id": request.id, "project_id": request.project_id.id,
            "contract_id": request.contract_id.id, "partner_id": request.partner_id.id,
            "currency_id": request.currency_id.id, "amount": request.amount,
            "receiving_account_name": "Rollback receipt account",
            "receiving_account_no": "ROLLBACK-RECEIPT-ACCOUNT",
        })
        created.append((record._name, record.id))
        _attach(record, "receipt-approval")
        return record

    try:
        policies.write({"approval_required": False, "mode": "none"})
        policies.sync_tier_definitions()
        automatic = document()
        automatic.action_confirm()
        assert automatic.state == "confirmed" and not automatic.review_ids and not automatic.treasury_ledger_id
        assert request.state == "approved"
        print("APPROVAL_CHECK=receipt_auto_approval_not_cash")
        automatic.action_cancel()
        policy = policies.filtered(lambda row: row.company_id == company)[:1]
        values = {"active": True, "approval_required": True, "mode": "single", "manager_group_id": group.id, "runtime_state": "tier_validation"}
        if policy:
            policy.write(values)
            policy.step_ids.write({"active": False})
        else:
            policy = Policy.create(dict(values, name="Rollback receipt", code="runtime_receipt_chain", target_model=model, company_id=company.id))
            created.append((policy._name, policy.id))
        env["sc.approval.step"].sudo().create({"policy_id": policy.id, "name": "Receipt review", "sequence": max(policy.step_ids.mapped("sequence") or [0]) + 10,
            "approval_scope_key": policy._approval_scope_for_group(group), "approve_group_id": group.id})
        policy.sync_tier_definitions()
        record = document()
        record.action_confirm()
        assert record.state == "draft" and record.review_ids and record.validation_status in ("waiting", "pending")
        denied(record.action_received)
        print("APPROVAL_CHECK=receipt_pending_cannot_receive")
        for change in ({"amount": request.amount + 1}, {"payment_request_id": False}, {"receiving_account_no": "changed"}, {"attachment_ids": [(5, 0, 0)]}):
            denied(lambda change=change: record.write(change))
        print("APPROVAL_CHECK=receipt_reviewed_content_frozen")
        _approve_existing_reviews(record)
        assert record.state == "confirmed" and not record.treasury_ledger_id and request.state == "approved"
        denied(lambda: record.write({"amount": request.amount + 1}))
        contract = env["sc.workflow.contract.service"].describe_record(record)
        assert contract["editability"] == "readonly"
        print("APPROVAL_CHECK=receipt_approved_readonly_not_cash")
        record.action_received()
        request.invalidate_recordset()
        ledger = record.treasury_ledger_id
        assert record.state == "received" and request.state == "done"
        assert ledger and ledger.state == "posted" and ledger.amount == request.amount
        assert ledger.company_id == company and ledger.project_id == request.project_id and ledger.currency_id == request.currency_id
        print("APPROVAL_CHECK=receipt_explicit_cash_posts_real_ledger")
        denied(record.action_received)
        denied(lambda: record.write({"amount": request.amount + 1}))
        denied(record.action_cancel)
        record.write({"note": "Rollback receipt supplement"})
        assert record.treasury_ledger_id == ledger and ledger.amount == request.amount
        print("APPROVAL_CHECK=receipt_terminal_fact_protected")
    finally:
        env.cr.rollback()
        env.invalidate_all()
        assert request.read(request_fields) == before, "receipt source request not restored"
        print("RECEIPT_SOURCE_ROLLBACK=VERIFIED")


def _finance_state_authority_checks(group, created, source_ledger=None, actor=None, adjustment_only=False):
    base = _env()
    finance = base["res.users"].sudo().search([("login", "=", "fixture_role_finance"), ("active", "=", True)], limit=1)
    assert finance, "existing finance fixture required"
    company = finance.company_id
    env = base["sc.approval.policy"].with_company(company).with_context(allowed_company_ids=[company.id]).env
    Policy = env["sc.approval.policy"].sudo()
    if adjustment_only:
        actor = base["res.users"].sudo().search([("login", "=", "fixture_role_project_a_member"), ("active", "=", True)], limit=1)
        assert actor and actor.company_id == company, "existing same-company business initiator required"
        Document = env["sc.settlement.adjustment"].with_user(actor)
        assert Document.check_access_rights("create", raise_exception=False) and Document.check_access_rights("write", raise_exception=False), "registered initiator lacks adjustment handling rights"
        Contract = env["construction.contract"].with_user(actor)
        contract = Contract.search([("company_id", "=", company.id)], limit=1)
        assert contract, "existing initiator-visible company-scoped contract required"
        ledger = None
        models = ("sc.settlement.adjustment",)
    else:
        contract = env["construction.contract"].sudo().search([("company_id", "=", company.id)], limit=1) if source_ledger is None else None
        ledger = source_ledger if source_ledger is not None else env["sc.treasury.ledger"].sudo().search([("company_id", "=", company.id), ("state", "=", "posted")], limit=1)
        assert ledger and ledger.company_id == company and ledger.state == "posted", "company-scoped posted ledger required"
        assert source_ledger is not None or contract, "existing company-scoped contract required"
        models = ("sc.treasury.reconciliation",) if source_ledger is not None else ("sc.settlement.adjustment", "sc.treasury.reconciliation")

    def denied(call):
        refused = False
        try:
            with env.cr.savepoint():
                call()
        except UserError:
            refused = True
        assert refused, "finance state authority bypassed"

    for model in models:
        policies = Policy.with_context(active_test=False).search([("target_model", "=", model), ("company_id", "in", [False, company.id])])
        policies.write({"approval_required": False, "mode": "none"})
        policies.sync_tier_definitions()
        Document = env[model].with_user(actor) if actor is not None else env[model].sudo()
        if actor is not None:
            assert not Document.env.su and Document.env.user == actor
        values = ({"project_id": contract.project_id.id, "contract_id": contract.id, "item_name": "Rollback state authority", "amount": 100}
                  if model == "sc.settlement.adjustment" else
                  {"project_id": ledger.project_id.id, "treasury_ledger_id": ledger.id, "system_difference": 0})
        settlement = None
        if adjustment_only:
            settlement = env["sc.settlement.order"].with_user(actor).create({
                "project_id": contract.project_id.id, "contract_id": contract.id,
                "partner_id": contract.partner_id.id, "currency_id": contract.currency_id.id,
                "settlement_type": "in" if contract.type == "out" else "out",
                "line_ids": [(0, 0, {"name": "Rollback adjustment basis", "contract_id": contract.id, "qty": 1, "price_unit": 1000})],
            })
            created.append((settlement._name, settlement.id))
            values.update(settlement_id=settlement.id, partner_id=contract.partner_id.id, currency_id=contract.currency_id.id)
            assert settlement.amount_total == 1000 and settlement.adjustment_total == 0
        def document():
            record = Document.create(dict(values))
            created.append((record._name, record.id))
            return record
        automatic = document()
        denied(lambda: Document.create(dict(values, state="confirmed")))
        denied(lambda: Document.with_context(default_state="confirmed").create(dict(values)))
        denied(lambda: automatic.with_context(sc_document_state_token=True).write({"state": "confirmed"}))
        denied(lambda: automatic.write({"source_origin": "legacy"}))
        print("APPROVAL_CHECK=%s_direct_state_denied" % model)
        automatic.action_confirm()
        assert automatic.state == "confirmed" and not automatic.review_ids
        print("APPROVAL_CHECK=%s_unconfigured_confirm" % model)
        if adjustment_only:
            assert settlement.adjustment_total == -100 and settlement.amount_after_adjustment == 900
            automatic.action_cancel()
            assert settlement.adjustment_total == 0 and settlement.amount_after_adjustment == 1000
            print("APPROVAL_CHECK=adjustment_deduction_confirmation_and_cancel_recompute")
        policy = policies.filtered(lambda row: row.company_id == company)[:1]
        configuration = {"active": True, "approval_required": True, "mode": "single",
            "manager_group_id": group.id, "runtime_state": "tier_validation"}
        if policy:
            policy.write(configuration)
            policy.step_ids.write({"active": False})
        else:
            policy = Policy.create(dict(configuration, name="Rollback finance state",
                code="runtime_" + model.replace(".", "_"), target_model=model, company_id=company.id))
            created.append((policy._name, policy.id))
        sequence = max(policy.step_ids.mapped("sequence") or [0]) + 10
        env["sc.approval.step"].sudo().create({"policy_id": policy.id, "name": "Finance review", "sequence": sequence,
            "approval_scope_key": policy._approval_scope_for_group(group), "approve_group_id": group.id})
        policy.sync_tier_definitions()
        required = document()
        required.action_confirm()
        assert required.state == "draft" and required.review_ids and required.validation_status in ("waiting", "pending")
        denied(lambda: required.write({"state": "confirmed"}))
        if model == "sc.treasury.reconciliation":
            denied(required.action_reconcile)
            if source_ledger is not None:
                for change in ({"account_balance": 200}, {"system_difference": 1}, {"treasury_ledger_id": False}, {"attachment_ids": [(5, 0, 0)]}):
                    denied(lambda change=change: required.write(change))
                print("APPROVAL_CHECK=reconciliation_reviewed_content_is_frozen")
        print("APPROVAL_CHECK=%s_configured_review_waits" % model)
        if adjustment_only:
            assert settlement.adjustment_total == 0 and settlement.amount_after_adjustment == 1000
            for changes in ({"amount": 200}, {"adjustment_type": "addition"}, {"contract_id": False}, {"active": False}):
                denied(lambda changes=changes: required.write(changes))
            original_partner = settlement.partner_id
            assert actor.partner_id != original_partner, "distinct existing partner required for source mismatch check"
            settlement.write({"partner_id": actor.partner_id.id})
            gates = env["sc.workflow.contract.service"]._settlement_adjustment_evidence_gate(required)
            assert any(gate["reasonCode"] == "SETTLEMENT_ADJUSTMENT_PARTNER_MISMATCH" and "approve" in gate["actionKeys"] for gate in gates)
            denied(lambda: _approve_existing_reviews(required))
            required.invalidate_recordset()
            assert required.state == "draft" and required.validation_status != "validated" and settlement.adjustment_total == 0
            settlement.write({"partner_id": original_partner.id})
            print("APPROVAL_CHECK=adjustment_changed_source_blocks_contract_and_real_approval")
        _approve_existing_reviews(required)
        assert required.state == "confirmed" and required.validation_status == "validated"
        if adjustment_only:
            denied(lambda: required.write({"amount": 200}))
            assert env["sc.workflow.contract.service"].describe_record(required)["editability"] == "readonly"
            required.write({"note": "Rollback adjustment supplement"})
            assert required.amount == 100 and required.signed_amount == -100
            assert settlement.adjustment_total == -100 and settlement.amount_after_adjustment == 900
            required.action_cancel()
            assert required.state == "cancel"
            assert settlement.adjustment_total == 0 and settlement.amount_after_adjustment == 1000
            print("APPROVAL_CHECK=settlement_adjustment_reviewed_content_and_explicit_cancel")
        if model == "sc.treasury.reconciliation":
            if source_ledger is not None:
                denied(lambda: required.write({"system_difference": 1}))
                assert env["sc.workflow.contract.service"].describe_record(required)["editability"] == "readonly"
            required.action_reconcile()
            assert required.state == "reconciled"
            if source_ledger is not None:
                for change in ({"confirmation_amount": 200}, {"bank_balance": 200}, {"treasury_ledger_id": False}, {"active": False}):
                    denied(lambda change=change: required.write(change))
                denied(required.action_cancel)
                required.write({"note": "Rollback reconciled supplement"})
                assert required.system_difference == 0 and required.treasury_ledger_id == source_ledger
                assert source_ledger.state == "posted" and source_ledger.amount == 100
                print("APPROVAL_CHECK=reconciliation_terminal_content_keeps_source_fact")
        print("APPROVAL_CHECK=%s_review_then_explicit_execution" % model)
        if adjustment_only:
            addition = Document.create(dict(values, adjustment_type="addition"))
            created.append((addition._name, addition.id))
            addition.action_confirm()
            assert addition.state == "draft" and settlement.adjustment_total == 0
            _approve_existing_reviews(addition)
            assert addition.state == "confirmed" and settlement.adjustment_total == 100 and settlement.amount_after_adjustment == 1100
            addition.action_cancel()
            assert settlement.adjustment_total == 0 and settlement.amount_after_adjustment == 1000
            print("APPROVAL_CHECK=adjustment_addition_real_review_and_cancel_recompute")


def _self_funding_reconciliation_checks(group, created):
    base = _env()
    finance = base["res.users"].sudo().search([("login", "=", "fixture_role_finance"), ("active", "=", True)], limit=1)
    assert finance, "existing finance fixture required"
    company = finance.company_id
    env = base["sc.self.funding.registration"].with_company(company).with_context(allowed_company_ids=[company.id]).env
    project = env["project.project"].sudo().create({"name": "Rollback self funding chain", "code": "SELF-FUNDING-CHAIN", "company_id": company.id, "manager_id": finance.id, "user_id": finance.id})
    partner = _partner("Rollback self funding partner")
    created.extend([(project._name, project.id), (partner._name, partner.id)])
    model = "sc.self.funding.registration"
    Policy = env["sc.approval.policy"].sudo()
    policies = Policy.with_context(active_test=False).search([("target_model", "=", model), ("company_id", "in", [False, company.id])])
    policies.write({"approval_required": False, "mode": "none"})
    policies.sync_tier_definitions()
    def document():
        record = env[model].with_user(finance).create({"project_id": project.id, "partner_id": partner.id,
            "amount": 100, "payment_account_name": "Rollback company account", "partner_account_name": "Rollback partner account"})
        assert not record.env.su and record.env.user == finance
        created.append((record._name, record.id))
        attachment = _attach(record, "self-funding-chain")
        created.append((attachment._name, attachment.id))
        return record
    def ledger_for(record):
        return env["sc.treasury.ledger"].sudo().search([("source_model", "=", model), ("source_res_id", "=", record.id)])
    def denied(call):
        refused = False
        try:
            with env.cr.savepoint(): call()
        except UserError:
            refused = True
        assert refused, "self funding authority bypassed"
    automatic = document()
    denied(lambda: automatic.write({"state": "confirmed"}))
    denied(lambda: env[model].sudo().with_context(default_state="confirmed").create({}))
    denied(lambda: automatic.with_context(sc_self_funding_authority_token=True).write({"state": "done"}))
    print("APPROVAL_CHECK=self_funding_direct_state_denied")
    automatic.action_confirm()
    assert automatic.state == "confirmed" and not automatic.review_ids and not ledger_for(automatic)
    print("APPROVAL_CHECK=self_funding_auto_approval_does_not_post")
    automatic.action_done()
    ledger = ledger_for(automatic)
    assert len(ledger) == 1 and ledger.state == "posted" and ledger.company_id == company and ledger.amount == 100
    created.append((ledger._name, ledger.id))
    print("APPROVAL_CHECK=self_funding_explicit_completion_posts_source_ledger")
    policy = policies.filtered(lambda row: row.company_id == company)[:1]
    configuration = {"active": True, "approval_required": True, "mode": "single", "manager_group_id": group.id, "runtime_state": "tier_validation"}
    if policy:
        policy.write(configuration)
        policy.step_ids.write({"active": False})
    else:
        policy = Policy.create(dict(configuration, name="Rollback self funding", code="runtime_self_funding_chain", target_model=model, company_id=company.id))
        created.append((policy._name, policy.id))
    env["sc.approval.step"].sudo().create({"policy_id": policy.id, "name": "Self funding review",
        "sequence": max(policy.step_ids.mapped("sequence") or [0]) + 10,
        "approval_scope_key": policy._approval_scope_for_group(group), "approve_group_id": group.id})
    policy.sync_tier_definitions()
    required = document()
    required.action_confirm()
    assert required.state == "draft" and required.review_ids and required.validation_status in ("waiting", "pending")
    denied(required.action_done)
    for values in ({"amount": 200}, {"funding_type": "refund"}, {"partner_id": False}, {"attachment_ids": [(5, 0, 0)]}):
        denied(lambda values=values: required.write(values))
    assert required.env["sc.workflow.contract.service"].describe_record(required)["editability"] == "readonly"
    assert not ledger_for(required)
    print("APPROVAL_CHECK=self_funding_pending_cannot_post")
    _approve_existing_reviews(required)
    assert required.state == "confirmed" and required.validation_status == "validated" and not ledger_for(required)
    print("APPROVAL_CHECK=self_funding_real_review_does_not_post")
    denied(lambda: required.write({"amount": 200}))
    denied(lambda: automatic.write({"amount": 200}))
    assert required.env["sc.workflow.contract.service"].describe_record(required)["editability"] == "readonly"
    assert required.amount == 100
    print("APPROVAL_CHECK=self_funding_reviewed_content_and_contract_agree")
    required.action_done()
    ledger = ledger_for(required)
    assert required.state == "done" and len(ledger) == 1 and ledger.state == "posted" and ledger.company_id == company and ledger.project_id == project and ledger.amount == required.amount
    created.append((ledger._name, ledger.id))
    print("APPROVAL_CHECK=self_funding_review_then_explicit_post")
    _finance_state_authority_checks(group, created, source_ledger=ledger, actor=finance)


def _financing_approval_checks(group, created):
    borrowing = os.environ.get("SC_APPROVAL_RUNTIME_SCOPE") == "financing-borrowing"
    base = _env()
    finance = base["res.users"].sudo().search([("login", "=", "fixture_role_finance"), ("active", "=", True)], limit=1)
    assert finance, "existing finance fixture required"
    company = finance.company_id
    env = base["sc.financing.loan"].with_company(company).with_context(allowed_company_ids=[company.id]).env
    project = env["project.project"].sudo().create({"name": "Rollback financing chain", "code": "FINANCING-CHAIN", "company_id": company.id, "manager_id": finance.id, "user_id": finance.id})
    partner = _partner("Rollback financing partner")
    created.extend([(project._name, project.id), (partner._name, partner.id)])
    model = "sc.financing.loan"
    Policy = env["sc.approval.policy"].sudo()
    policies = Policy.with_context(active_test=False).search([("target_model", "=", model), ("company_id", "in", [False, company.id])])
    policies.write({"approval_required": False, "mode": "none"})
    policies.sync_tier_definitions()
    def document(**overrides):
        record = env[model].with_user(finance).create({"project_id": project.id, "partner_id": partner.id, "amount": 100,
            "loan_type": "loan_registration", "direction": "financing_in", **overrides})
        assert not record.env.su
        created.append((record._name, record.id))
        return record
    def denied(call):
        refused = False
        try:
            with env.cr.savepoint(): call()
        except (UserError, AccessError):
            refused = True
        assert refused, "financing authority bypassed"
    if not borrowing:
        automatic = document()
        denied(lambda: automatic.write({"state": "confirmed"}))
        denied(lambda: env[model].with_user(finance).with_context(default_state="done").create({}))
        denied(lambda: automatic.with_context(sc_document_state_token=True).write({"state": "done"}))
        print("APPROVAL_CHECK=financing_direct_state_denied")
        automatic.action_confirm()
        assert automatic.state == "confirmed" and not automatic.review_ids
        print("APPROVAL_CHECK=financing_auto_approval_not_completion")
        automatic.action_done()
        assert automatic.state == "done"
        assert not env["sc.treasury.ledger"].sudo().search_count([("source_model", "=", model), ("source_res_id", "=", automatic.id)])
        print("APPROVAL_CHECK=financing_registration_completion_keeps_declared_no_ledger_semantics")
    policy = policies.filtered(lambda row: row.company_id == company)[:1]
    configuration = {"active": True, "approval_required": True, "mode": "single", "manager_group_id": group.id, "runtime_state": "tier_validation"}
    if policy:
        policy.write(configuration)
        policy.step_ids.write({"active": False})
    else:
        policy = Policy.create(dict(configuration, name="Rollback financing", code="runtime_financing_chain", target_model=model, company_id=company.id))
        created.append((policy._name, policy.id))
    env["sc.approval.step"].sudo().create({"policy_id": policy.id, "name": "Financing review", "sequence": max(policy.step_ids.mapped("sequence") or [0]) + 10,
        "approval_scope_key": policy._approval_scope_for_group(group), "approve_group_id": group.id})
    policy.sync_tier_definitions()
    if borrowing:
        for code, direction in (("finance.loan.contractor_project_borrow", "out"), ("finance.loan.project_borrow_company", "in")):
            category = env["sc.business.category"].sudo().search([("code", "=", code), ("active", "=", True)], limit=1)
            assert category and category.target_model == model, "existing authoritative borrowing category required: " + code
            record = document(loan_type="borrowing_request", direction="borrowed_fund", business_category_id=category.id)
            assert record.business_category_id == category and record.loan_type == "borrowing_request"
            def ledgers():
                return env["sc.treasury.ledger"].sudo().search([("source_model", "=", model), ("source_res_id", "=", record.id)])
            record.action_confirm()
            assert record.state == "draft" and record.review_ids and record.validation_status in ("waiting", "pending")
            denied(record.action_done)
            assert not ledgers()
            _approve_existing_reviews(record)
            assert record.state == "confirmed" and not ledgers()
            print("APPROVAL_CHECK=%s_real_review_does_not_post" % code)
            record.action_done()
            ledger = ledgers()
            assert record.state == "done" and len(ledger) == 1
            assert ledger.direction == direction and ledger.source_kind == "interfund" and ledger.state == "posted"
            assert ledger.project_id == project and ledger.company_id == company and ledger.partner_id == partner
            assert ledger.amount == record.amount == 100 and ledger.currency_id == record.currency_id
            created.append((ledger._name, ledger.id))
            print("APPROVAL_CHECK=%s_explicit_completion_posts_exact_direction" % code)
            denied(record.action_done)
            record._ensure_interfund_cash_ledger()
            assert ledgers().ids == ledger.ids
            denied(lambda: record.write({"amount": 200}))
            print("APPROVAL_CHECK=%s_no_duplicate_or_changed_posted_fact" % code)
        return
    required = document()
    required.action_confirm()
    assert required.state == "draft" and required.review_ids and required.validation_status in ("waiting", "pending")
    denied(required.action_done)
    denied(lambda: required.write({"amount": 200}))
    print("APPROVAL_CHECK=financing_pending_cannot_complete")
    _approve_existing_reviews(required)
    assert required.state == "confirmed" and required.validation_status == "validated"
    print("APPROVAL_CHECK=financing_real_review_not_completion")
    outsider = base["res.users"].sudo().search([("login", "=", "fixture_role_pm"), ("active", "=", True)], limit=1)
    assert outsider and not outsider.has_group("smart_construction_core.group_sc_cap_finance_manager") and not outsider.has_group("smart_construction_core.group_sc_super_admin")
    denied(required.with_user(outsider).action_done)
    print("APPROVAL_CHECK=financing_completion_requires_finance_permission")
    denied(lambda: required.write({"amount": 200}))
    assert required.env["sc.workflow.contract.service"].describe_record(required)["editability"] == "readonly"
    required.action_done()
    assert required.state == "done"
    for values in ({"amount": 200}, {"financing_loan_approved_amount": "200"}, {"direction": "borrowed_fund"}, {"active": False}):
        denied(lambda values=values: required.write(values))
    before_display = required.financing_loan_loan_type_display
    required.write({"note": "Rollback permitted supplement"})
    assert required.amount == 100 and required.financing_loan_loan_type_display == before_display
    assert required.env["sc.workflow.contract.service"].describe_record(required)["editability"] == "locked"
    print("APPROVAL_CHECK=financing_review_then_explicit_completion")
    print("APPROVAL_CHECK=financing_reviewed_final_content_matches_contract")
    retry = document()
    retry.action_confirm()
    old = set(retry.review_ids.ids)
    users = retry.review_ids.mapped("reviewer_ids").filtered(lambda user: user.active and not user.share and company in user.sudo().company_ids)
    candidates = [retry.with_user(user).with_context(allowed_company_ids=[company.id]).with_company(company) for user in users]
    actor = next((candidate for candidate in candidates if candidate.can_review), None)
    assert actor is not None
    actor.env["sc.approval.policy"]._reject_submission_review(actor, reason="Rollback financing rejection")
    retry.invalidate_recordset()
    assert retry.state == "draft" and retry.reject_reason
    retry.action_confirm()
    assert old.isdisjoint(retry.review_ids.ids)
    _approve_existing_reviews(retry)
    assert retry.state == "confirmed" and not retry.reject_reason
    print("APPROVAL_CHECK=financing_reject_resubmit_new_review")


def _legacy_workflow_boundary_checks():
    env = _env()
    key = "sc.workflow.legacy_runtime_enabled"
    params = env["ir.config_parameter"].sudo()
    finance = env["res.users"].sudo().search([("login", "=", "fixture_role_finance"), ("active", "=", True)], limit=1)
    assert finance, "existing fixture finance required"
    Model = env["sc.workflow.instance"].with_user(finance).with_context(allow_legacy_workflow_runtime=True)
    Definition = env["sc.workflow.def"].with_user(finance).with_context(allow_legacy_workflow_runtime=True)
    assert not Model.env.su
    params.set_param(key, "0")
    assert not Model._legacy_runtime_enabled() and not Definition._legacy_runtime_enabled()
    assert Model.sudo()._legacy_runtime_enabled(), "internal recovery context compatibility lost"
    print("APPROVAL_CHECK=legacy_workflow_untrusted_context_does_not_enable_runtime")
    for name in ("action_submit", "action_approve", "action_reject"):
        try:
            getattr(Model, name)()
        except UserError as error:
            assert "base_tier_validation" in str(error)
        else:
            raise AssertionError("disabled legacy transition executed: " + name)
    print("APPROVAL_CHECK=legacy_workflow_disabled_transitions_rejected")
    gates = env["sc.workflow.contract.service"]._evidence_gate(Model)
    gate = next(row for row in gates if row["reasonCode"] == "LEGACY_WORKFLOW_RUNTIME_DISABLED")
    assert set(gate["actionKeys"]) == {"submit", "approve", "reject"} and gate["blocking"]
    print("APPROVAL_CHECK=legacy_workflow_contract_matches_runtime_mode")
    params.set_param(key, "1")
    assert Model._legacy_runtime_enabled() and Definition._legacy_runtime_enabled()
    try:
        Model.action_submit()
    except UserError as error:
        assert "permission to manage workflow instances" in str(error)
    else:
        raise AssertionError("enabled legacy runtime granted administrator authority")
    print("APPROVAL_CHECK=legacy_workflow_enabled_mode_does_not_grant_admin")
    params.set_param(key, "0")
    try:
        Model.action_cancel()
    except UserError as error:
        assert "permission to manage workflow instances" in str(error)
    else:
        raise AssertionError("historical cancellation lost administrator restriction")
    print("APPROVAL_CHECK=legacy_workflow_cleanup_still_requires_admin")


def _red_flush_role_checks(_project_unused, group, created):
    base = _env()
    finance = base["res.users"].sudo().search([("login", "=", "fixture_role_finance"), ("active", "=", True)], limit=1)
    assert finance, "existing fixture finance required"
    company = finance.company_id
    actor_env = base["sc.output.invoice.adjustment"].with_user(finance).with_company(company).with_context(allowed_company_ids=[company.id]).env
    assert not actor_env.su
    actor_env["sc.invoice.registration"]._assert_finance_register_access()
    project = base["project.project"].sudo().with_company(company).create({"name": "Red flush role rollback project", "code": "RED-FLUSH-ROLE", "company_id": company.id, "manager_id": finance.id, "user_id": finance.id})
    created.append((project._name, project.id))
    _red_flush_approval_checks(project, group, created, actor_env=actor_env)
    print("APPROVAL_CHECK=red_flush_fixture_finance_business_actions_without_sudo")


def _red_flush_approval_checks(project, group, created, actor_env=None):
    env = actor_env or _env()
    model = "sc.output.invoice.adjustment"
    Document = env[model] if actor_env is not None else env[model].sudo()
    if actor_env is not None:
        assert not Document.env.su
        assert project.with_env(actor_env).search_count([("id", "=", project.id)]) == 1, "finance must see the owned source project"
    Policy = env["sc.approval.policy"].sudo()
    assert not Policy.with_context(active_test=False).search_count([("target_model", "=", model), ("company_id", "in", [False, project.company_id.id])])
    partner = _partner("Rollback red flush partner")
    created.append((partner._name, partner.id))
    registrar_group = env.ref("smart_construction_core.group_sc_cap_finance_manager")
    registrars = registrar_group.users.filtered(lambda user: user.active and not user.share and project.company_id in user.company_ids)
    assert registrars, "existing company-scoped finance registrar required"
    registrar = registrars.sorted("id")[:1]
    def confirm(record):
        # Existing financial role supplies the permission; elevated fixture
        # source access is preparation, not ordinary-role usability evidence.
        if actor_env is None:
            record.with_user(registrar).sudo().action_confirm()
        else:
            actor = record.with_env(actor_env)
            assert not actor.env.su
            actor.action_confirm()
        record.invalidate_recordset()
    def document(amount=100, register=True):
        source = env["sc.invoice.registration"].sudo().create({"project_id": project.id, "partner_id": partner.id, "direction": "output", "source_kind": "output_invoice_tax", "invoice_no": "RUNTIME-RED-SOURCE", "amount_total": amount, "amount_no_tax": amount})
        created.append((source._name, source.id))
        number = "RUNTIME-RED-%s" % source.id
        source.write({"invoice_no": number})
        if register:
            source.action_confirm()
            if source.review_ids:
                _approve_existing_reviews(source)
            assert source.state == "confirmed"
            source.with_user(registrar).sudo().action_register()
            source.invalidate_recordset()
            assert source.state == "registered"
        source.flush_recordset()
        ledger = env["sc.output.invoice.ledger"].sudo().search([("source_model", "=", source._name), ("source_record_id", "=", source.id)], limit=1)
        assert ledger, "existing ledger projection must include source invoice"
        record = Document.create({"original_ledger_id": ledger.id, "red_flush_invoice_no": number + "-R", "reason": "Rollback red flush approval"})
        created.append((record._name, record.id))
        if actor_env is not None:
            assert record.env.uid == actor_env.uid and not record.env.su
        return record
    def denied(action):
        refused = False
        try:
            with env.cr.savepoint(): action()
        except UserError:
            refused = True
        assert refused, "red flush boundary was bypassed"
    ineligible = document(register=False)
    denied(ineligible.action_submit)
    assert ineligible.state == "draft"
    contract = env["sc.workflow.contract.service"].describe_record(ineligible)
    assert "RED_FLUSH_SOURCE_NOT_REGISTERED" in str(contract)
    original = ineligible._original_source_record(ineligible.original_ledger_id)
    original.action_cancel()
    original.flush_recordset()
    ineligible.original_ledger_id.invalidate_recordset()
    denied(ineligible.action_submit)
    assert not ineligible.generated_invoice_id
    print("APPROVAL_CHECK=red_flush_draft_and_cancelled_originals_denied")
    automatic = document()
    denied(lambda: env["sc.invoice.registration"].sudo().create({"state": "registered", "project_id": project.id}))
    original = automatic._original_source_record(automatic.original_ledger_id)
    denied(lambda: original.write({"state": "draft"}))
    denied(lambda: original.with_context(sc_invoice_state_token=True).write({"state": "draft"}))
    denied(lambda: automatic.write({"state": "approved"}))
    denied(lambda: env[model].sudo().with_context(default_state="approved").create({"original_ledger_id": automatic.original_ledger_id.id}))
    denied(automatic.action_confirm)
    print("APPROVAL_CHECK=red_flush_external_state_and_direct_approval_denied")
    automatic.action_submit()
    assert automatic.state == "approved" and not automatic.review_ids
    assert not automatic.generated_invoice_id
    print("APPROVAL_CHECK=red_flush_no_policy_approval_does_not_post")
    denied(lambda: automatic.write({"original_invoice_amount": 1}))
    denied(automatic.action_submit)
    print("APPROVAL_CHECK=red_flush_approved_amount_and_reset_protected")
    non_registrar = env["res.users"].sudo().search([("login", "=", "fixture_role_pm")], limit=1)
    assert non_registrar and not env["sc.invoice.registration"].with_user(non_registrar)._has_finance_register_access(), "existing non-registrar role required"
    denied(lambda: automatic.with_user(non_registrar).sudo().action_confirm())
    confirm(automatic)
    ledger = automatic.generated_invoice_id
    assert ledger and ledger.state == "registered" and ledger.amount_total == -automatic.original_invoice_amount and ledger.direction == "output"
    assert ledger.red_flush_adjustment_id == automatic
    created.append((ledger._name, ledger.id))
    denied(automatic.action_cancel)
    denied(automatic.action_submit)
    denied(automatic.action_confirm)
    print("APPROVAL_CHECK=red_flush_explicit_posting_and_final_state_protection")
    policy = Policy.create({"name": "Runtime red flush", "code": "runtime_red_flush_approval", "target_model": model,
        "company_id": project.company_id.id, "approval_required": True, "mode": "single",
        "manager_group_id": group.id, "runtime_state": "tier_validation"})
    created.append((policy._name, policy.id))
    step = env["sc.approval.step"].sudo().create({"policy_id": policy.id, "name": "Red flush review", "sequence": 10,
        "approval_scope_key": policy._approval_scope_for_group(group), "approve_group_id": group.id, "amount_min": 200})
    policy.sync_tier_definitions()
    unmatched = document()
    denied(unmatched.action_submit)
    assert unmatched.state == "draft"
    print("APPROVAL_CHECK=red_flush_amount_rule_unmatched_denied")
    step.write({"amount_min": 0})
    policy.sync_tier_definitions()
    required = document()
    required.action_submit()
    assert required.state == "submitted" and required.review_ids
    contract = env["sc.workflow.contract.service"].describe_record(required)
    assert contract["rawState"] == "submitted" and contract["approvalPhase"] in ("waiting", "pending")
    assert {"validate_tier", "reject_tier"}.issubset({action["method"] for action in contract["actions"]})
    print("APPROVAL_CHECK=red_flush_configured_submission_has_real_review")
    policy.write({"approval_required": False})
    denied(required.action_submit)
    denied(required.action_confirm)
    denied(required.action_cancel)
    denied(lambda: required.write({"original_invoice_amount": 300}))
    policy.write({"approval_required": True})
    print("APPROVAL_CHECK=red_flush_pending_instance_cannot_be_bypassed")
    _approve_existing_reviews(required)
    assert required.state == "approved" and required.validation_status == "validated"
    assert not required.generated_invoice_id
    print("APPROVAL_CHECK=red_flush_real_approval_callback")
    confirm(required)
    ledger = required.generated_invoice_id
    assert required.state == "confirmed" and ledger and ledger.state == "registered"
    assert ledger.amount_total == -required.original_invoice_amount and ledger.red_flush_adjustment_id == required
    created.append((ledger._name, ledger.id))
    print("APPROVAL_CHECK=red_flush_review_then_explicit_posting")
    rejected = document()
    rejected.action_submit()
    previous = set(rejected.review_ids.ids)
    users = rejected.review_ids.mapped("reviewer_ids").filtered(lambda user: user.active and not user.share and rejected.company_id in user.sudo().company_ids)
    candidates = [rejected.with_user(user).with_context(allowed_company_ids=[rejected.company_id.id]).with_company(rejected.company_id) for user in users]
    actor = next((record for record in candidates if record.can_review), None)
    assert actor is not None
    actor.env["sc.approval.policy"]._reject_submission_review(actor, reason="Runtime red flush rejection")
    rejected.invalidate_recordset()
    assert rejected.state == "rejected" and rejected.reject_reason == "Runtime red flush rejection"
    rejected.action_submit()
    assert previous.isdisjoint(rejected.review_ids.ids) and rejected.review_ids
    _approve_existing_reviews(rejected)
    assert rejected.state == "approved" and not rejected.reject_reason
    print("APPROVAL_CHECK=red_flush_rejection_resubmission_new_review")
    changed = document()
    changed.action_submit()
    _approve_existing_reviews(changed)
    source = changed._original_source_record(changed.original_ledger_id)
    denied(lambda: source.write({"amount_total": changed.original_invoice_amount + 1}))
    assert not changed.generated_invoice_id
    assert source.amount_total == changed.original_invoice_amount
    print("APPROVAL_CHECK=red_flush_registered_source_amount_is_immutable")


    recoverable = document()
    recoverable.action_submit()
    _approve_existing_reviews(recoverable)
    reviews_before = recoverable.review_ids.ids
    recovery_contract = env["sc.workflow.contract.service"].describe_record(recoverable)
    assert any(action["method"] == "action_cancel" and not action.get("disabled", False) for action in recovery_contract["availableActions"])
    recoverable.action_cancel()
    assert recoverable.state == "cancel" and not recoverable.generated_invoice_id
    assert recoverable.review_ids.ids == reviews_before and recoverable.validation_status == "validated"
    denied(recoverable.action_submit)
    print("APPROVAL_CHECK=red_flush_approved_unexecuted_cancellation_preserves_review")
    replacement = Document.create({"original_ledger_id": recoverable.original_ledger_id.id, "red_flush_invoice_no": recoverable.red_flush_invoice_no + "-RETRY", "reason": "New application after cancellation"})
    created.append((replacement._name, replacement.id))
    replacement.action_submit()
    assert replacement.state == "submitted" and set(reviews_before).isdisjoint(replacement.review_ids.ids)
    _approve_existing_reviews(replacement)
    confirm(replacement)
    assert replacement.state == "confirmed" and replacement.generated_invoice_id
    created.append((replacement.generated_invoice_id._name, replacement.generated_invoice_id.id))
    print("APPROVAL_CHECK=red_flush_replacement_requires_new_approval_before_execution")
    constraint = "sc_output_invoice_adjustment_confirmed_source_unique"
    env.cr.execute("SELECT 1 FROM pg_constraint WHERE conname = %s AND conrelid = 'sc_output_invoice_adjustment'::regclass", (constraint,))
    assert env.cr.fetchone(), "red-flush unique constraint not installed"
    duplicate = env[model].sudo().create({"original_ledger_id": replacement.original_ledger_id.id, "red_flush_invoice_no": replacement.red_flush_invoice_no + "-DUP"})
    created.append((duplicate._name, duplicate.id))
    refused = False
    try:
        with env.cr.savepoint():
            # Exercise the database backstop separately from the ordinary
            # business duplicate check; this is not a two-session race test.
            duplicate._write_approval_state({"state": "confirmed"})
            duplicate.flush_recordset()
    except IntegrityError as error:
        assert error.diag.constraint_name == constraint
        refused = True
    assert refused, "database accepted a second confirmed adjustment for the same source"
    print("APPROVAL_CHECK=red_flush_database_unique_source_backstop")


def _tender_guarantee_approval_checks(project, group, created):
    env = _env()
    model = "tender.guarantee"
    Policy = env["sc.approval.policy"].sudo()
    assert not Policy.with_context(active_test=False).search_count([("target_model", "=", model), ("company_id", "in", [False, project.company_id.id])])
    bid = env["tender.bid"].sudo().create({"tender_name": "Rollback approval guarantee", "project_id": project.id})
    created.append((bid._name, bid.id))
    def document(amount=100):
        record = env[model].sudo().create({"bid_id": bid.id, "amount": amount})
        created.append((record._name, record.id))
        return record
    def denied(action):
        refused = False
        try:
            with env.cr.savepoint(): action()
        except UserError:
            refused = True
        assert refused, "tender guarantee boundary was bypassed"
    automatic = document()
    denied(lambda: automatic.write({"state": "approved"}))
    denied(lambda: env[model].sudo().with_context(default_state="approved").create({"bid_id": bid.id}))
    denied(automatic.action_confirm)
    print("APPROVAL_CHECK=tender_guarantee_external_state_and_direct_approval_denied")
    automatic.action_submit()
    assert automatic.state == "approved" and not automatic.review_ids
    assert not automatic.treasury_ledger_id
    print("APPROVAL_CHECK=tender_guarantee_no_policy_approval_does_not_post")
    denied(lambda: automatic.write({"amount": 1}))
    denied(automatic.action_reset_draft)
    print("APPROVAL_CHECK=tender_guarantee_approved_amount_and_reset_protected")
    automatic.action_confirm()
    ledger = automatic.treasury_ledger_id
    assert ledger and ledger.state == "posted" and ledger.amount == automatic.amount and ledger.direction == "out"
    assert ledger.source_model == model and ledger.source_res_id == automatic.id
    created.append((ledger._name, ledger.id))
    denied(automatic.action_cancel)
    denied(automatic.action_reset_draft)
    denied(automatic.action_confirm)
    print("APPROVAL_CHECK=tender_guarantee_explicit_posting_and_final_state_protection")
    policy = Policy.create({"name": "Runtime tender guarantee", "code": "runtime_tender_guarantee_approval", "target_model": model,
        "company_id": project.company_id.id, "approval_required": True, "mode": "single",
        "manager_group_id": group.id, "runtime_state": "tier_validation"})
    created.append((policy._name, policy.id))
    step = env["sc.approval.step"].sudo().create({"policy_id": policy.id, "name": "Tender guarantee review", "sequence": 10,
        "approval_scope_key": policy._approval_scope_for_group(group), "approve_group_id": group.id, "amount_min": 200})
    policy.sync_tier_definitions()
    unmatched = document()
    denied(unmatched.action_submit)
    assert unmatched.state == "draft"
    print("APPROVAL_CHECK=tender_guarantee_amount_rule_unmatched_denied")
    step.write({"amount_min": 0})
    policy.sync_tier_definitions()
    required = document()
    required.action_submit()
    assert required.state == "submitted" and required.review_ids
    contract = env["sc.workflow.contract.service"].describe_record(required)
    assert contract["rawState"] == "submitted" and contract["approvalPhase"] in ("waiting", "pending")
    assert {"validate_tier", "reject_tier"}.issubset({action["method"] for action in contract["actions"]})
    print("APPROVAL_CHECK=tender_guarantee_configured_submission_has_real_review")
    policy.write({"approval_required": False})
    denied(required.action_submit)
    denied(required.action_confirm)
    denied(required.action_cancel)
    denied(required.action_reset_draft)
    denied(lambda: required.write({"amount": 300}))
    policy.write({"approval_required": True})
    print("APPROVAL_CHECK=tender_guarantee_pending_instance_cannot_be_bypassed")
    _approve_existing_reviews(required)
    assert required.state == "approved" and required.validation_status == "validated"
    assert not required.treasury_ledger_id
    print("APPROVAL_CHECK=tender_guarantee_real_approval_callback")
    required.action_confirm()
    ledger = required.treasury_ledger_id
    assert required.state == "confirmed" and ledger and ledger.state == "posted"
    assert ledger.amount == required.amount and ledger.source_res_id == required.id
    created.append((ledger._name, ledger.id))
    print("APPROVAL_CHECK=tender_guarantee_review_then_explicit_posting")
    rejected = document()
    rejected.action_submit()
    previous = set(rejected.review_ids.ids)
    users = rejected.review_ids.mapped("reviewer_ids").filtered(lambda user: user.active and not user.share and rejected.company_id in user.sudo().company_ids)
    candidates = [rejected.with_user(user).with_context(allowed_company_ids=[rejected.company_id.id]).with_company(rejected.company_id) for user in users]
    actor = next((record for record in candidates if record.can_review), None)
    assert actor is not None
    actor.env["sc.approval.policy"]._reject_submission_review(actor, reason="Runtime tender guarantee rejection")
    rejected.invalidate_recordset()
    assert rejected.state == "rejected" and rejected.reject_reason == "Runtime tender guarantee rejection"
    rejected.action_submit()
    assert previous.isdisjoint(rejected.review_ids.ids) and rejected.review_ids
    _approve_existing_reviews(rejected)
    assert rejected.state == "approved" and not rejected.reject_reason
    print("APPROVAL_CHECK=tender_guarantee_rejection_resubmission_new_review")


def _tender_purchase_approval_checks(project, group, created):
    env = _env()
    model = "tender.doc.purchase"
    Policy = env["sc.approval.policy"].sudo()
    assert not Policy.with_context(active_test=False).search_count([("target_model", "=", model), ("company_id", "in", [False, project.company_id.id])])
    bid = env["tender.bid"].sudo().create({"tender_name": "Rollback approval purchase", "project_id": project.id})
    created.append((bid._name, bid.id))
    def document(amount=100):
        record = env[model].sudo().create({"bid_id": bid.id, "amount": amount})
        created.append((record._name, record.id))
        return record
    def denied(action):
        refused = False
        try:
            with env.cr.savepoint(): action()
        except UserError:
            refused = True
        assert refused, "tender purchase boundary was bypassed"
    automatic = document(0)
    denied(lambda: automatic.write({"state": "approved"}))
    denied(lambda: env[model].sudo().with_context(default_state="approved").create({"bid_id": bid.id}))
    denied(automatic.action_approve)
    print("APPROVAL_CHECK=tender_purchase_external_state_and_direct_approval_denied")
    automatic.action_submit()
    assert automatic.state == "approved" and not automatic.review_ids
    assert automatic.processing_advisory
    print("APPROVAL_CHECK=tender_purchase_no_policy_approves_with_advisory")
    denied(lambda: automatic.write({"amount": 1}))
    denied(automatic.action_reset_draft)
    print("APPROVAL_CHECK=tender_purchase_approved_amount_and_reset_protected")
    policy = Policy.create({"name": "Runtime tender purchase", "code": "runtime_tender_purchase_approval", "target_model": model,
        "company_id": project.company_id.id, "approval_required": True, "mode": "single",
        "manager_group_id": group.id, "runtime_state": "tier_validation"})
    created.append((policy._name, policy.id))
    step = env["sc.approval.step"].sudo().create({"policy_id": policy.id, "name": "Tender purchase review", "sequence": 10,
        "approval_scope_key": policy._approval_scope_for_group(group), "approve_group_id": group.id, "amount_min": 200})
    policy.sync_tier_definitions()
    unmatched = document()
    denied(unmatched.action_submit)
    assert unmatched.state == "draft"
    print("APPROVAL_CHECK=tender_purchase_amount_rule_unmatched_denied")
    step.write({"amount_min": 0})
    policy.sync_tier_definitions()
    required = document()
    required.action_submit()
    assert required.state == "submitted" and required.review_ids
    contract = env["sc.workflow.contract.service"].describe_record(required)
    assert contract["rawState"] == "submitted" and contract["approvalPhase"] in ("waiting", "pending")
    assert {"validate_tier", "reject_tier"}.issubset({action["method"] for action in contract["actions"]})
    print("APPROVAL_CHECK=tender_purchase_configured_submission_has_real_review")
    policy.write({"approval_required": False})
    denied(required.action_submit)
    denied(required.action_reset_draft)
    denied(lambda: required.write({"amount": 300}))
    policy.write({"approval_required": True})
    print("APPROVAL_CHECK=tender_purchase_pending_instance_cannot_be_bypassed")
    _approve_existing_reviews(required)
    assert required.state == "approved" and required.validation_status == "validated"
    print("APPROVAL_CHECK=tender_purchase_real_approval_callback")
    rejected = document()
    rejected.action_submit()
    previous = set(rejected.review_ids.ids)
    users = rejected.review_ids.mapped("reviewer_ids").filtered(lambda user: user.active and not user.share and rejected.company_id in user.sudo().company_ids)
    candidates = [rejected.with_user(user).with_context(allowed_company_ids=[rejected.company_id.id]).with_company(rejected.company_id) for user in users]
    actor = next((record for record in candidates if record.can_review), None)
    assert actor is not None
    actor.env["sc.approval.policy"]._reject_submission_review(actor, reason="Runtime tender purchase rejection")
    rejected.invalidate_recordset()
    assert rejected.state == "rejected" and rejected.reject_reason == "Runtime tender purchase rejection"
    rejected.action_submit()
    assert previous.isdisjoint(rejected.review_ids.ids) and rejected.review_ids
    _approve_existing_reviews(rejected)
    assert rejected.state == "approved" and not rejected.reject_reason
    print("APPROVAL_CHECK=tender_purchase_rejection_resubmission_new_review")


def _project_role_approval_checks(project, group, created):
    base = _env()
    pm = base["res.users"].sudo().search([("login", "=", "fixture_role_pm"), ("active", "=", True)], limit=1)
    assert pm, "existing PM fixture required"
    actor_env = base["project.project"].with_user(pm).with_company(pm.company_id).with_context(allowed_company_ids=[pm.company_id.id]).env
    assert not actor_env.su
    _project_approval_checks(group, created, actor_env=actor_env)


def _project_approval_checks(group, created, actor_env=None):
    env = actor_env or _env()
    model = "project.project"
    Policy = env["sc.approval.policy"].sudo()
    assert not Policy.with_context(active_test=False).search_count([
        ("target_model", "=", model), ("company_id", "in", [False, env.company.id]),
    ]), "existing project approval configuration must not be overwritten"

    def document(label):
        if actor_env is None:
            record = _project("Approval project " + label)
        else:
            record = env[model].sudo().create({
                "name": "Approval project " + label, "code": "ROLE-APPROVAL-" + label.upper(),
                "company_id": env.company.id, "manager_id": env.user.id, "user_id": env.user.id,
            }).with_env(actor_env)
            assert not record.env.su
            assert record.search([("id", "=", record.id)]) == record
        created.append((record._name, record.id))
        return record

    direct = document("direct")
    for values in ({"sc_approval_state": "approved"}, {"lifecycle_state": "in_progress"}, {"lifecycle_state": "paused"}):
        denied = False
        try:
            with env.cr.savepoint(): direct.write(values)
        except UserError:
            denied = True
        assert denied
        direct.invalidate_recordset()
        assert direct.lifecycle_state == "draft" and direct.sc_approval_state == "draft"
    print("APPROVAL_CHECK=project_direct_approval_and_draft_start_bypass_denied")
    automatic = document("automatic")
    automatic.action_sc_submit()
    assert automatic.sc_approval_state == "approved" and not automatic.review_ids
    assert automatic.lifecycle_state == "draft"
    print("APPROVAL_CHECK=project_unconfigured_approval_does_not_start")
    policy = Policy.create({
        "name": "Runtime project approval", "code": "runtime_project_approval_smoke", "target_model": model,
        "company_id": env.company.id, "approval_required": True, "mode": "single",
        "manager_group_id": group.id, "runtime_state": "tier_validation",
    })
    created.append((policy._name, policy.id))
    env["sc.approval.step"].sudo().create({
        "policy_id": policy.id, "name": "Project review", "sequence": 10,
        "approval_scope_key": policy._approval_scope_for_group(group), "approve_group_id": group.id,
    })
    policy.sync_tier_definitions()
    required = document("required")
    required.action_sc_submit()
    assert required.sc_approval_state == "draft" and required.review_ids
    assert required.validation_status in ("waiting", "pending")
    denied = False
    try:
        with env.cr.savepoint(): required.action_sc_start()
    except UserError:
        denied = True
    assert denied and required.lifecycle_state == "draft"
    print("APPROVAL_CHECK=project_pending_approval_cannot_start")
    _approve_existing_reviews(required)
    assert required.sc_approval_state == "approved" and required.validation_status == "validated"
    assert required.lifecycle_state == "draft"
    required.action_sc_start()
    assert required.lifecycle_state == "in_progress"
    print("APPROVAL_CHECK=project_real_approval_then_explicit_start")
    rejected = document("rejection")
    rejected.action_sc_submit()
    previous_ids = set(rejected.review_ids.ids)
    users = rejected.review_ids.mapped("reviewer_ids").filtered(
        lambda user: user.active and not user.share and rejected.company_id in user.sudo().company_ids
    )
    candidates = [rejected.with_user(user).with_context(allowed_company_ids=[rejected.company_id.id]).with_company(rejected.company_id) for user in users]
    actor = next((candidate for candidate in candidates if candidate.can_review), None)
    assert actor is not None
    actor.env["sc.approval.policy"]._reject_submission_review(actor, reason="Runtime project rejection")
    rejected.invalidate_recordset()
    assert rejected.lifecycle_state == "draft" and rejected.sc_approval_state == "draft"
    assert rejected.reject_reason == "Runtime project rejection"
    print("APPROVAL_CHECK=project_rejection_preserves_reason")
    rejected.action_sc_submit()
    assert rejected.review_ids and previous_ids.isdisjoint(rejected.review_ids.ids)
    _approve_existing_reviews(rejected)
    assert rejected.sc_approval_state == "approved" and not rejected.reject_reason and rejected.lifecycle_state == "draft"
    print("APPROVAL_CHECK=project_resubmission_completes_new_chain")



def _inbound_approval_checks(project, group, created):
    env = _env()
    model = "sc.material.inbound"
    Policy = env["sc.approval.policy"].sudo()
    assert not Policy.with_context(active_test=False).search_count([
        ("target_model", "=", model), ("company_id", "in", [False, env.company.id]),
    ]), "existing inbound approval configuration must not be overwritten"
    warehouse = env["stock.warehouse"].sudo().search([("company_id", "=", env.company.id)], limit=1)
    product = env["product.product"].sudo().search([("type", "in", ["product", "consu"])], limit=1)
    assert warehouse, "existing current-company warehouse required"
    if not product:
        # Transaction-local collaborator, never persisted as an acceptance fixture.
        product = env["product.product"].sudo().create({"name": "Rollback inbound material", "type": "consu"})
        created.extend([(product._name, product.id), (product.product_tmpl_id._name, product.product_tmpl_id.id)])

    def document():
        record = env[model].sudo().create({
            "project_id": project.id, "warehouse_id": warehouse.id,
            "dest_location_id": warehouse.lot_stock_id.id,
            "line_ids": [(0, 0, {"product_id": product.id, "product_uom_id": product.uom_id.id, "qty": 2, "unit_price": 10})],
        })
        created.append((record._name, record.id))
        return record

    def cannot_receive(record):
        denied = False
        try:
            with env.cr.savepoint(): record.action_receive()
        except UserError:
            denied = True
        assert denied
        record.invalidate_recordset()
        assert record.state == "submitted"

    automatic = document()
    for token in (False, True, "trusted"):
        denied = False
        try:
            with env.cr.savepoint(): automatic.with_context(sc_inbound_state_token=token).write({"state": "approved"})
        except UserError:
            denied = True
        assert denied
    print("APPROVAL_CHECK=inbound_direct_state_write_denied")
    automatic.action_submit()
    assert automatic.state == "approved" and not automatic.review_ids
    automatic.action_receive()
    assert automatic.state == "received"
    print("APPROVAL_CHECK=inbound_unconfigured_approval_then_explicit_receiving")
    policy = Policy.create({
        "name": "Runtime inbound approval", "code": "runtime_inbound_approval_smoke", "target_model": model,
        "company_id": env.company.id, "approval_required": True, "mode": "single",
        "manager_group_id": group.id, "runtime_state": "tier_validation",
    })
    created.append((policy._name, policy.id))
    env["sc.approval.step"].sudo().create({
        "policy_id": policy.id, "name": "Inbound review", "sequence": 10,
        "approval_scope_key": policy._approval_scope_for_group(group), "approve_group_id": group.id,
        "amount_min": 1,
    })
    policy.sync_tier_definitions()
    required = document()
    required.action_submit()
    assert required.state == "submitted" and required.review_ids
    cannot_receive(required)
    print("APPROVAL_CHECK=inbound_configured_amount_review_blocks_receiving")
    _set_policy(model, False)
    cannot_receive(required)
    _set_policy(model, True)
    print("APPROVAL_CHECK=inbound_pending_review_survives_configuration_change")
    _approve_existing_reviews(required)
    assert required.state == "approved" and required.validation_status == "validated"
    required.action_receive()
    assert required.state == "received"
    print("APPROVAL_CHECK=inbound_real_approval_then_explicit_receiving")
    rejected = document()
    rejected.action_submit()
    previous = set(rejected.review_ids.ids)
    actor = next((rejected.with_user(user) for user in rejected.review_ids.mapped("reviewer_ids") if rejected.with_user(user).can_review), None)
    assert actor is not None
    actor.env["sc.approval.policy"]._reject_submission_review(actor, reason="Runtime inbound rejection")
    rejected.invalidate_recordset()
    assert rejected.state == "draft" and rejected.reject_reason == "Runtime inbound rejection"
    rejected.action_submit()
    assert previous.isdisjoint(rejected.review_ids.ids) and rejected.review_ids
    _approve_existing_reviews(rejected)
    assert rejected.state == "approved" and not rejected.reject_reason
    print("APPROVAL_CHECK=inbound_rejection_and_new_review_chain")

    def transfer():
        outbound = env["sc.material.outbound"].sudo().create({
            "project_id": project.id, "outbound_type": "transfer", "dest_warehouse_id": warehouse.id,
            "dest_location_id": warehouse.lot_stock_id.id,
            "line_ids": [(0, 0, {"product_id": product.id, "product_uom_id": product.uom_id.id, "qty": 2, "unit_price": 10})],
        })
        created.append((outbound._name, outbound.id))
        inbound = outbound._sync_transfer_inbound_after_issue()
        created.append((inbound._name, inbound.id))
        assert outbound.transfer_inbound_id == inbound
        return inbound

    pending = transfer()
    assert pending.state == "submitted" and pending.review_ids
    _approve_existing_reviews(pending)
    assert pending.state == "approved"
    pending.action_receive()
    assert pending.state == "received"
    print("APPROVAL_CHECK=transfer_inbound_review_persists_until_explicit_receiving")
    _set_policy(model, False)
    completed = transfer()
    assert completed.state == "received" and not completed.review_ids
    print("APPROVAL_CHECK=transfer_unconfigured_existing_auto_receive_preserved")



def _acceptance_approval_checks(project, group, created):
    env = _env()
    model = "sc.material.acceptance"
    Policy = env["sc.approval.policy"].sudo()
    assert not Policy.with_context(active_test=False).search_count([
        ("target_model", "=", model), ("company_id", "in", [False, env.company.id]),
    ]), "existing material acceptance policy must not be overwritten"
    product = env["product.product"].sudo().search([("type", "in", ["product", "consu"])], limit=1)
    if not product:
        product = env["product.product"].sudo().create({"name": "Rollback acceptance material", "type": "consu"})
        created.extend([(product._name, product.id), (product.product_tmpl_id._name, product.product_tmpl_id.id)])

    def document():
        record = env[model].sudo().create({
            "project_id": project.id,
            "line_ids": [(0, 0, {"product_id": product.id, "product_uom_id": product.uom_id.id,
                                  "received_qty": 2, "accepted_qty": 2})],
        })
        created.append((record._name, record.id))
        return record

    def denied(call):
        refused = False
        try:
            with env.cr.savepoint(): call()
        except UserError:
            refused = True
        assert refused, "business operation unexpectedly permitted"

    automatic = document()
    for state in ("approved", "accepted", "rejected"):
        denied(lambda: automatic.with_context(sc_acceptance_state_token=True).write({"state": state}))
    print("APPROVAL_CHECK=acceptance_external_state_write_denied")
    automatic.action_submit()
    assert automatic.state == "approved" and not automatic.review_ids
    automatic.action_accept()
    assert automatic.state == "accepted"
    print("APPROVAL_CHECK=acceptance_unconfigured_approval_then_quality_decision")
    policy = Policy.create({
        "name": "Runtime material acceptance approval", "code": "runtime_acceptance_approval_smoke", "target_model": model,
        "company_id": env.company.id, "approval_required": True, "mode": "single",
        "manager_group_id": group.id, "runtime_state": "tier_validation",
    })
    created.append((policy._name, policy.id))
    step = env["sc.approval.step"].sudo().create({
        "policy_id": policy.id, "name": "Acceptance review", "sequence": 10,
        "approval_scope_key": policy._approval_scope_for_group(group), "approve_group_id": group.id,
    })
    policy.sync_tier_definitions()
    denied(lambda: step.write({"amount_min": 1}))
    step.invalidate_recordset()
    assert not step.amount_min
    print("APPROVAL_CHECK=acceptance_undefined_amount_condition_rejected")
    required = document()
    required.action_submit()
    assert required.state == "submitted" and required.review_ids
    denied(required.action_accept)
    denied(required.action_reject)
    print("APPROVAL_CHECK=acceptance_pending_review_blocks_both_quality_outcomes")
    _approve_existing_reviews(required)
    assert required.state == "approved" and required.validation_status == "validated"
    denied(lambda: required.line_ids.write({"accepted_qty": 3}))
    required.action_accept()
    assert required.state == "accepted"
    print("APPROVAL_CHECK=acceptance_real_approval_preserves_quantity_validation")
    negative = document()
    negative.action_submit()
    _approve_existing_reviews(negative)
    denied(negative.action_reject)
    negative.write({"rejection_reason": "Runtime quality mismatch"})
    negative.action_reject()
    assert negative.state == "rejected" and negative.rejection_reason == "Runtime quality mismatch" and not negative.reject_reason
    print("APPROVAL_CHECK=acceptance_quality_failure_has_separate_required_reason")
    rejected = document()
    rejected.action_submit()
    old = set(rejected.review_ids.ids)
    actor = next((rejected.with_user(user) for user in rejected.review_ids.mapped("reviewer_ids") if rejected.with_user(user).can_review), None)
    assert actor is not None
    actor.env["sc.approval.policy"]._reject_submission_review(actor, reason="Runtime approval rejection")
    rejected.invalidate_recordset()
    assert rejected.state == "draft" and rejected.reject_reason == "Runtime approval rejection" and not rejected.rejection_reason
    print("APPROVAL_CHECK=acceptance_approval_rejection_is_not_quality_failure")
    rejected.action_submit()
    assert rejected.review_ids and old.isdisjoint(rejected.review_ids.ids)
    _approve_existing_reviews(rejected)
    assert rejected.state == "approved" and not rejected.reject_reason
    print("APPROVAL_CHECK=acceptance_resubmission_completes_new_review_without_quality_decision")


def _purchase_request_approval_checks(project, group, created):
    env = _env()
    model = "sc.material.purchase.request"
    Policy = env["sc.approval.policy"].sudo()
    assert not Policy.with_context(active_test=False).search_count([
        ("target_model", "=", model), ("company_id", "in", [False, env.company.id]),
    ]), "existing purchase request policy must not be overwritten"
    product = env["product.product"].sudo().search([("type", "in", ["product", "consu"])], limit=1)
    if not product:
        product = env["product.product"].sudo().create({"name": "Rollback purchase material", "type": "consu"})
        created.extend([(product._name, product.id), (product.product_tmpl_id._name, product.product_tmpl_id.id)])
    supplier = _partner("Rollback purchase supplier")
    created.append((supplier._name, supplier.id))

    def document():
        record = env[model].sudo().create({
            "project_id": project.id, "supplier_id": supplier.id,
            "line_ids": [(0, 0, {"product_id": product.id, "product_uom_id": product.uom_id.id,
                                  "qty": 2, "estimated_unit_price": 10})],
        })
        created.append((record._name, record.id))
        return record

    def denied(call):
        refused = False
        try:
            with env.cr.savepoint(): call()
        except UserError:
            refused = True
        assert refused, "business operation unexpectedly permitted"

    def downstream(record):
        return (env["sc.material.rfq"].sudo().search([("purchase_request_id", "=", record.id)]),
                env["purchase.order"].sudo().search([("source_material_purchase_request_id", "=", record.id)]))

    automatic = document()
    denied(lambda: automatic.with_context(sc_purchase_request_state_token=True).write({"state": "approved"}))
    print("APPROVAL_CHECK=purchase_request_external_state_write_denied")
    automatic.action_submit()
    assert automatic.state == "approved" and not automatic.review_ids and not any(downstream(automatic))
    print("APPROVAL_CHECK=purchase_request_unconfigured_approval_does_not_generate_documents")
    policy = Policy.create({
        "name": "Runtime purchase request approval", "code": "runtime_purchase_request_approval_smoke", "target_model": model,
        "company_id": env.company.id, "approval_required": True, "mode": "single",
        "manager_group_id": group.id, "runtime_state": "tier_validation",
    })
    created.append((policy._name, policy.id))
    step = env["sc.approval.step"].sudo().create({
        "policy_id": policy.id, "name": "Purchase request review", "sequence": 10,
        "approval_scope_key": policy._approval_scope_for_group(group), "approve_group_id": group.id,
        "amount_min": 1,
    })
    policy.sync_tier_definitions()
    required = document()
    required.action_submit()
    assert required.amount_total == 20 and required.state == "submitted" and required.review_ids
    denied(required.action_create_rfq)
    denied(required.action_create_purchase_order)
    assert not any(downstream(required))
    print("APPROVAL_CHECK=purchase_request_amount_rule_and_pending_downstream_denial")
    policy.write({"approval_required": False})
    denied(required.action_submit)
    assert required.state == "submitted" and required.review_ids
    denied(required.action_create_purchase_order)
    policy.write({"approval_required": True})
    print("APPROVAL_CHECK=purchase_request_configuration_change_keeps_pending_authority")
    _approve_existing_reviews(required)
    assert required.state == "approved" and required.validation_status == "validated" and not any(downstream(required))
    print("APPROVAL_CHECK=purchase_request_real_approval_does_not_generate_documents")
    required.action_create_rfq()
    required.action_create_purchase_order()
    rfq, order = downstream(required)
    created.extend([(record._name, record.id) for record in rfq])
    created.extend([(record._name, record.id) for record in order])
    assert len(rfq) == len(order) == 1 and order.state == "draft"
    required.action_create_rfq()
    required.action_create_purchase_order()
    assert downstream(required) == (rfq, order)
    print("APPROVAL_CHECK=purchase_request_explicit_generation_is_idempotent_and_order_stays_draft")
    rejected = document()
    rejected.action_submit()
    old = set(rejected.review_ids.ids)
    actor = next((rejected.with_user(user) for user in rejected.review_ids.mapped("reviewer_ids") if rejected.with_user(user).can_review), None)
    assert actor is not None
    actor.env["sc.approval.policy"]._reject_submission_review(actor, reason="Runtime purchase rejection")
    rejected.invalidate_recordset()
    assert rejected.state == "draft" and rejected.reject_reason == "Runtime purchase rejection"
    denied(rejected.action_create_rfq)
    print("APPROVAL_CHECK=purchase_request_rejection_returns_draft_without_downstream")
    rejected.action_submit()
    assert rejected.review_ids and old.isdisjoint(rejected.review_ids.ids)
    _approve_existing_reviews(rejected)
    assert rejected.state == "approved" and not rejected.reject_reason and not any(downstream(rejected))
    print("APPROVAL_CHECK=purchase_request_resubmission_uses_new_review")


def _rfq_approval_checks(project, group, created):
    env = _env()
    model = "sc.material.rfq"
    Policy = env["sc.approval.policy"].sudo()
    assert not Policy.with_context(active_test=False).search_count([
        ("target_model", "=", model), ("company_id", "in", [False, env.company.id]),
    ]), "existing RFQ policy must not be overwritten"
    product = env["product.product"].sudo().search([("type", "in", ["product", "consu"])], limit=1)
    if not product:
        product = env["product.product"].sudo().create({"name": "Rollback RFQ material", "type": "consu"})
        created.extend([(product._name, product.id), (product.product_tmpl_id._name, product.product_tmpl_id.id)])
    supplier = _partner("Rollback RFQ supplier")
    created.append((supplier._name, supplier.id))

    def document():
        record = env[model].sudo().create({"project_id": project.id, "line_ids": [(0, 0, {
            "supplier_id": supplier.id, "product_id": product.id, "product_uom_id": product.uom_id.id,
            "qty": 2, "unit_price": 10,
        })]})
        created.append((record._name, record.id))
        return record

    def denied(call):
        refused = False
        try:
            with env.cr.savepoint(): call()
        except UserError:
            refused = True
        assert refused, "business operation unexpectedly permitted"

    def orders(record):
        return env["purchase.order"].sudo().search([("source_material_rfq_id", "=", record.id)])

    automatic = document()
    denied(lambda: automatic.with_context(sc_rfq_state_token=True).write({"state": "selected"}))
    denied(automatic.action_create_purchase_order)
    print("APPROVAL_CHECK=rfq_external_state_and_draft_order_denied")
    automatic.action_submit()
    assert automatic.state == "approved" and not automatic.review_ids and not automatic.selected_supplier_id and not orders(automatic)
    denied(automatic.action_create_purchase_order)
    print("APPROVAL_CHECK=rfq_unconfigured_approval_does_not_select_or_order")
    policy = Policy.create({
        "name": "Runtime RFQ approval", "code": "runtime_rfq_approval_smoke", "target_model": model,
        "company_id": env.company.id, "approval_required": True, "mode": "single",
        "manager_group_id": group.id, "runtime_state": "tier_validation",
    })
    created.append((policy._name, policy.id))
    step = env["sc.approval.step"].sudo().create({
        "policy_id": policy.id, "name": "RFQ review", "sequence": 10,
        "approval_scope_key": policy._approval_scope_for_group(group), "approve_group_id": group.id,
    })
    policy.sync_tier_definitions()
    denied(lambda: step.write({"amount_min": 1}))
    step.invalidate_recordset()
    assert not step.amount_min
    print("APPROVAL_CHECK=rfq_undefined_amount_condition_rejected")
    required = document()
    required.action_submit()
    assert required.state == "submitted" and required.review_ids
    denied(required.action_select)
    denied(required.action_create_purchase_order)
    policy.write({"approval_required": False})
    denied(required.action_submit)
    assert required.state == "submitted" and not orders(required)
    policy.write({"approval_required": True})
    print("APPROVAL_CHECK=rfq_pending_authority_blocks_selection_order_and_restart")
    _approve_existing_reviews(required)
    assert required.state == "approved" and required.validation_status == "validated" and not required.selected_supplier_id and not orders(required)
    denied(required.action_select)
    denied(required.action_create_purchase_order)
    print("APPROVAL_CHECK=rfq_real_approval_preserves_explicit_quote_requirement")
    required.line_ids.write({"selected": True})
    required.action_select()
    assert required.state == "selected" and required.selected_supplier_id == supplier and not orders(required)
    required.action_create_purchase_order()
    generated = orders(required)
    created.extend([(record._name, record.id) for record in generated])
    assert len(generated) == 1 and generated.state == "draft" and generated.partner_id == supplier
    print("APPROVAL_CHECK=rfq_explicit_selection_then_draft_order_generation")
    rejected = document()
    rejected.action_submit()
    old = set(rejected.review_ids.ids)
    actor = next((rejected.with_user(user) for user in rejected.review_ids.mapped("reviewer_ids") if rejected.with_user(user).can_review), None)
    assert actor is not None
    actor.env["sc.approval.policy"]._reject_submission_review(actor, reason="Runtime RFQ rejection")
    rejected.invalidate_recordset()
    assert rejected.state == "draft" and rejected.reject_reason == "Runtime RFQ rejection"
    denied(rejected.action_select)
    print("APPROVAL_CHECK=rfq_rejection_returns_draft_without_selection")
    rejected.action_submit()
    assert rejected.review_ids and old.isdisjoint(rejected.review_ids.ids)
    _approve_existing_reviews(rejected)
    assert rejected.state == "approved" and not rejected.reject_reason and not rejected.selected_supplier_id and not orders(rejected)
    print("APPROVAL_CHECK=rfq_resubmission_uses_new_review_without_selection")


def _material_settlement_approval_checks(project, group, created):
    env = _env()
    model = "sc.material.settlement"
    Policy = env["sc.approval.policy"].sudo()
    assert not Policy.with_context(active_test=False).search_count([
        ("target_model", "=", model), ("company_id", "in", [False, env.company.id]),
    ]), "existing material settlement policy must not be overwritten"
    product = env["product.product"].sudo().search([("type", "in", ["product", "consu"])], limit=1)
    if not product:
        product = env["product.product"].sudo().create({"name": "Rollback settlement material", "type": "consu"})
        created.extend([(product._name, product.id), (product.product_tmpl_id._name, product.product_tmpl_id.id)])
    supplier = _partner("Rollback settlement supplier")
    created.append((supplier._name, supplier.id))

    def document():
        record = env[model].sudo().create({"project_id": project.id, "supplier_id": supplier.id,
            "line_ids": [(0, 0, {"product_id": product.id, "product_uom_id": product.uom_id.id,
                                  "qty": 2, "unit_price": 10})]})
        created.append((record._name, record.id))
        return record

    def denied(call):
        refused = False
        try:
            with env.cr.savepoint(): call()
        except UserError:
            refused = True
        assert refused, "business operation unexpectedly permitted"

    def downstream(record):
        return (env["project.cost.ledger"].sudo().search([("source_model", "=", model), ("source_id", "=", record.id)]),
                env["payment.request"].sudo().search([("material_settlement_id", "=", record.id)]))

    automatic = document()
    denied(lambda: automatic.write({"state": "confirmed"}))
    denied(automatic.action_confirm)
    print("APPROVAL_CHECK=material_settlement_external_state_and_premature_confirmation_denied")
    automatic.action_submit()
    assert automatic.state == "approved" and not automatic.review_ids and not any(downstream(automatic))
    print("APPROVAL_CHECK=material_settlement_unconfigured_approval_has_no_downstream")
    policy = Policy.create({"name": "Runtime material settlement approval", "code": "runtime_material_settlement_approval_smoke",
        "target_model": model, "company_id": env.company.id, "approval_required": True, "mode": "single",
        "manager_group_id": group.id, "runtime_state": "tier_validation"})
    created.append((policy._name, policy.id))
    env["sc.approval.step"].sudo().create({"policy_id": policy.id, "name": "Settlement review", "sequence": 10,
        "approval_scope_key": policy._approval_scope_for_group(group), "approve_group_id": group.id, "amount_min": 1})
    policy.sync_tier_definitions()
    required = document()
    required.action_submit()
    assert required.amount_total == 20 and required.state == "submitted" and required.review_ids
    denied(required.action_confirm)
    denied(required.action_create_remaining_payment_request)
    assert not any(downstream(required))
    print("APPROVAL_CHECK=material_settlement_amount_rule_and_pending_downstream_denial")
    _approve_existing_reviews(required)
    assert required.state == "approved" and required.validation_status == "validated" and not any(downstream(required))
    print("APPROVAL_CHECK=material_settlement_real_approval_does_not_post_cost_or_payment")
    denied(lambda: required.write({"settlement_date": "2026-01-01"}))
    denied(lambda: required.line_ids.write({"qty": 3}))
    denied(required.line_ids.unlink)
    denied(required.unlink)
    print("APPROVAL_CHECK=material_settlement_approved_facts_remain_immutable")
    cost_enabled = required._sc_business_category_cost_trigger("material.settlement", "confirm_project_cost_ledger", default=True)
    payment_enabled = required._sc_business_category_cost_trigger("material.settlement", "confirm_payment_request", default=True)
    required.action_confirm()
    ledger, requests = downstream(required)
    created.extend([(record._name, record.id) for record in ledger])
    created.extend([(record._name, record.id) for record in requests])
    assert required.state == "confirmed" and bool(ledger) == cost_enabled and bool(requests) == payment_enabled
    if ledger:
        assert sum(ledger.mapped("source_amount")) == required.amount_untaxed
    if requests:
        assert len(requests) == 1 and requests.state == "draft" and requests.amount == required.amount_total
    denied(required.action_confirm)
    assert downstream(required) == (ledger, requests)
    print("APPROVAL_CHECK=material_settlement_explicit_confirmation_preserves_configured_downstream")
    rejected = document()
    rejected.action_submit()
    old = set(rejected.review_ids.ids)
    actor = next((rejected.with_user(user) for user in rejected.review_ids.mapped("reviewer_ids") if rejected.with_user(user).can_review), None)
    assert actor is not None
    actor.env["sc.approval.policy"]._reject_submission_review(actor, reason="Runtime settlement rejection")
    rejected.invalidate_recordset()
    assert rejected.state == "draft" and rejected.reject_reason == "Runtime settlement rejection" and not any(downstream(rejected))
    print("APPROVAL_CHECK=material_settlement_rejection_returns_draft_without_cost")
    rejected.action_submit()
    assert rejected.review_ids and old.isdisjoint(rejected.review_ids.ids)
    _approve_existing_reviews(rejected)
    assert rejected.state == "approved" and not rejected.reject_reason and not any(downstream(rejected))
    print("APPROVAL_CHECK=material_settlement_resubmission_uses_new_review_without_confirmation")


def _equipment_plan_request_checks(project, group, created):
    env = _env()
    Policy = env["sc.approval.policy"].sudo()
    plans = {}

    def denied(call):
        refused = False
        try:
            with env.cr.savepoint(): call()
        except UserError:
            refused = True
        assert refused, "business operation unexpectedly permitted"

    def document(model, **values):
        qty = "planned_qty" if model == "sc.equipment.plan" else "requested_qty"
        record = env[model].sudo().create({"project_id": project.id,
            "line_ids": [(0, 0, {"equipment_name": "Rollback equipment", qty: 1})], **values})
        created.append((record._name, record.id))
        return record

    for model in ("sc.equipment.plan", "sc.equipment.request"):
        assert not Policy.with_context(active_test=False).search_count([
            ("target_model", "=", model), ("company_id", "in", [False, env.company.id]),
        ]), "existing equipment policy must not be overwritten"
        automatic = document(model)
        denied(lambda: automatic.with_context(sc_equipment_approval_state_token=True).write({"state": "approved"}))
        print("APPROVAL_CHECK=%s_external_state_denied" % model)
        automatic.action_submit()
        assert automatic.state == "approved" and not automatic.review_ids
        if model == "sc.equipment.plan": plans["approved"] = automatic
        print("APPROVAL_CHECK=%s_unconfigured_submission_auto_approved" % model)
        policy = Policy.create({"name": "Runtime equipment approval", "code": "runtime_" + model.replace(".", "_"),
            "target_model": model, "company_id": env.company.id, "approval_required": True, "mode": "single",
            "manager_group_id": group.id, "runtime_state": "tier_validation"})
        created.append((policy._name, policy.id))
        step = env["sc.approval.step"].sudo().create({"policy_id": policy.id, "name": "Equipment review", "sequence": 10,
            "approval_scope_key": policy._approval_scope_for_group(group), "approve_group_id": group.id})
        policy.sync_tier_definitions()
        denied(lambda: step.write({"amount_min": 1}))
        step.invalidate_recordset()
        assert not step.amount_min
        print("APPROVAL_CHECK=%s_undefined_monetary_authority_rejected" % model)
        required = document(model, **({"plan_id": plans["approved"].id} if model.endswith("request") else {}))
        required.action_submit()
        assert required.state == "submitted" and required.review_ids
        required.action_on_tier_approved()
        assert required.state == "submitted"
        policy.write({"approval_required": False})
        denied(required.action_submit)
        policy.write({"approval_required": True})
        print("APPROVAL_CHECK=%s_pending_review_survives_configuration_change" % model)
        _approve_existing_reviews(required)
        assert required.state == "approved" and required.validation_status == "validated"
        print("APPROVAL_CHECK=%s_actual_review_approves_document" % model)
        rejected = document(model)
        rejected.action_submit()
        old = set(rejected.review_ids.ids)
        actor = next((rejected.with_user(user) for user in rejected.review_ids.mapped("reviewer_ids") if rejected.with_user(user).can_review), None)
        assert actor is not None
        actor.env["sc.approval.policy"]._reject_submission_review(actor, reason="Runtime equipment rejection")
        rejected.invalidate_recordset()
        assert rejected.state == "draft" and rejected.reject_reason == "Runtime equipment rejection"
        rejected.action_submit()
        assert rejected.review_ids and old.isdisjoint(rejected.review_ids.ids)
        _approve_existing_reviews(rejected)
        assert rejected.state == "approved" and not rejected.reject_reason
        print("APPROVAL_CHECK=%s_rejection_and_resubmission_use_new_review" % model)
    draft_plan = document("sc.equipment.plan")
    invalid = document("sc.equipment.request", plan_id=draft_plan.id)
    denied(invalid.action_submit)
    assert invalid.state == "draft" and not invalid.review_ids
    print("APPROVAL_CHECK=equipment_request_unapproved_source_plan_denied")
    other = _project("Rollback equipment other project")
    created.append((other._name, other.id))
    mismatch = document("sc.equipment.request", project_id=other.id, plan_id=plans["approved"].id)
    denied(mismatch.action_submit)
    assert mismatch.state == "draft" and not mismatch.review_ids
    print("APPROVAL_CHECK=equipment_request_cross_project_source_plan_denied")


def _equipment_execution_checks(project, group, created):
    env = _env()
    Policy = env["sc.approval.policy"].sudo()
    supplier = _partner("Rollback equipment execution supplier")
    created.append((supplier._name, supplier.id))
    confirmed_usage = None

    def denied(call):
        refused = False
        try:
            with env.cr.savepoint(): call()
        except UserError:
            refused = True
        assert refused, "business operation unexpectedly permitted"

    def document(model, usage=None):
        values = {"project_id": project.id, "supplier_id": supplier.id}
        if model.endswith("usage"):
            values.update(equipment_name="Rollback machine", usage_location="Rollback site", operator_name="Rollback operator", usage_qty=1, usage_hours=2, price_unit=10)
        else:
            values["line_ids"] = [(0, 0, {"equipment_name": "Rollback machine", "qty": 2, "unit_price": 10,
                                            "usage_id": usage.id if usage else False})]
        record = env[model].sudo().create(values)
        created.append((record._name, record.id))
        return record

    def ledger(record):
        return env["project.cost.ledger"].sudo().search([("source_model", "=", record._name), ("source_id", "=", record.id)])

    for model in ("sc.equipment.usage", "sc.equipment.settlement"):
        assert not Policy.with_context(active_test=False).search_count([
            ("target_model", "=", model), ("company_id", "in", [False, env.company.id]),
        ]), "existing equipment execution policy must not be overwritten"
        automatic = document(model, confirmed_usage)
        denied(lambda: automatic.write({"state": "confirmed"}))
        denied(automatic.action_confirm)
        print("APPROVAL_CHECK=%s_external_state_and_premature_confirmation_denied" % model)
        automatic.action_submit()
        assert automatic.state == "approved" and not automatic.review_ids and not ledger(automatic)
        print("APPROVAL_CHECK=%s_unconfigured_approval_does_not_confirm" % model)
        policy = Policy.create({"name": "Runtime equipment execution approval", "code": "runtime_" + model.replace(".", "_"),
            "target_model": model, "company_id": env.company.id, "approval_required": True, "mode": "single",
            "manager_group_id": group.id, "runtime_state": "tier_validation"})
        created.append((policy._name, policy.id))
        env["sc.approval.step"].sudo().create({"policy_id": policy.id, "name": "Equipment execution review", "sequence": 10,
            "approval_scope_key": policy._approval_scope_for_group(group), "approve_group_id": group.id, "amount_min": 1})
        policy.sync_tier_definitions()
        required = document(model, confirmed_usage)
        required.action_submit()
        assert (required.amount if model.endswith("usage") else required.amount_total) == 20
        assert required.state == "submitted" and required.review_ids
        denied(required.action_confirm)
        assert not ledger(required)
        print("APPROVAL_CHECK=%s_amount_rule_blocks_pending_confirmation" % model)
        _approve_existing_reviews(required)
        assert required.state == "approved" and required.validation_status == "validated" and not ledger(required)
        print("APPROVAL_CHECK=%s_real_approval_does_not_execute" % model)
        if model.endswith("usage"):
            denied(lambda: required.write({"usage_hours": 3}))
            denied(required.unlink)
            actor = env["res.users"].sudo().search([("login", "=", "fixture_role_finance")], limit=1)
            assert actor and not actor.has_group("smart_construction_core.group_sc_cap_project_manager") and not actor.has_group("smart_construction_core.group_sc_super_admin")
            denied(required.with_user(actor).action_confirm)
            denied(required.with_user(actor).action_cancel)
            print("APPROVAL_CHECK=equipment_usage_approved_fact_lock_and_manager_boundary")
        required.action_confirm()
        rows = ledger(required)
        created.extend([(row._name, row.id) for row in rows])
        assert required.state == "confirmed"
        if model.endswith("usage"):
            assert len(rows) == 1 and rows.source_amount == required.amount and rows.qty == 2
            confirmed_usage = required
        else:
            assert not rows
        denied(required.action_confirm)
        assert ledger(required) == rows
        print("APPROVAL_CHECK=%s_explicit_confirmation_preserves_execution" % model)
        rejected = document(model, confirmed_usage)
        rejected.action_submit()
        old = set(rejected.review_ids.ids)
        actor = next((rejected.with_user(user) for user in rejected.review_ids.mapped("reviewer_ids") if rejected.with_user(user).can_review), None)
        assert actor is not None
        actor.env["sc.approval.policy"]._reject_submission_review(actor, reason="Runtime equipment execution rejection")
        rejected.invalidate_recordset()
        assert rejected.state == "draft" and rejected.reject_reason == "Runtime equipment execution rejection"
        rejected.action_submit()
        assert rejected.review_ids and old.isdisjoint(rejected.review_ids.ids)
        _approve_existing_reviews(rejected)
        assert rejected.state == "approved" and not rejected.reject_reason and not ledger(rejected)
        print("APPROVAL_CHECK=%s_rejection_resubmission_stops_before_execution" % model)
    unconfirmed = document("sc.equipment.usage")
    invalid = document("sc.equipment.settlement", unconfirmed)
    denied(invalid.action_submit)
    assert invalid.state == "draft" and not invalid.review_ids
    print("APPROVAL_CHECK=equipment_settlement_unconfirmed_usage_denied")


def _labor_plan_request_checks(project, group, created):
    env = _env()
    Policy = env["sc.approval.policy"].sudo()

    def denied(call):
        refused = False
        try:
            with env.cr.savepoint(): call()
        except UserError:
            refused = True
        assert refused, "business operation unexpectedly permitted"

    def document(model, **values):
        qty = "planned_qty" if model == "sc.labor.plan" else "requested_qty"
        record = env[model].sudo().create({"project_id": project.id,
            "line_ids": [(0, 0, {"work_content": "Rollback labor", qty: 1})], **values})
        created.append((record._name, record.id))
        return record

    for model in ("sc.labor.plan", "sc.labor.request"):
        assert not Policy.with_context(active_test=False).search_count([
            ("target_model", "=", model), ("company_id", "in", [False, env.company.id]),
        ]), "existing labor policy must not be overwritten"
        automatic = document(model)
        denied(lambda: automatic.with_context(sc_labor_approval_state_token=True).write({"state": "approved"}))
        print("APPROVAL_CHECK=%s_external_state_denied" % model)
        automatic.action_submit()
        assert automatic.state == "approved" and not automatic.review_ids
        print("APPROVAL_CHECK=%s_unconfigured_submission_auto_approved" % model)
        policy = Policy.create({"name": "Runtime labor approval", "code": "runtime_" + model.replace(".", "_"),
            "target_model": model, "company_id": env.company.id, "approval_required": True, "mode": "single",
            "manager_group_id": group.id, "runtime_state": "tier_validation"})
        created.append((policy._name, policy.id))
        step = env["sc.approval.step"].sudo().create({"policy_id": policy.id, "name": "Labor review", "sequence": 10,
            "approval_scope_key": policy._approval_scope_for_group(group), "approve_group_id": group.id})
        policy.sync_tier_definitions()
        denied(lambda: step.write({"amount_min": 1}))
        step.invalidate_recordset()
        assert not step.amount_min
        print("APPROVAL_CHECK=%s_undefined_monetary_authority_rejected" % model)
        required = document(model)
        required.action_submit()
        assert required.state == "submitted" and required.review_ids
        required.action_on_tier_approved()
        assert required.state == "submitted"
        policy.write({"approval_required": False})
        denied(required.action_submit)
        policy.write({"approval_required": True})
        print("APPROVAL_CHECK=%s_pending_review_survives_configuration_change" % model)
        _approve_existing_reviews(required)
        assert required.state == "approved" and required.validation_status == "validated"
        print("APPROVAL_CHECK=%s_actual_review_approves_document" % model)
        for method in (required.action_submit, required.action_cancel, required.action_reset_draft):
            denied(method)
        assert required.state == "approved"
        print("APPROVAL_CHECK=%s_approved_document_cannot_bypass_state_machine" % model)
        cancelled = document(model)
        cancelled.action_cancel()
        assert cancelled.state == "cancel"
        cancelled.action_reset_draft()
        assert cancelled.state == "draft"
        print("APPROVAL_CHECK=%s_cancelled_document_can_reset" % model)
        rejected = document(model)
        rejected.action_submit()
        old = set(rejected.review_ids.ids)
        actor = next((rejected.with_user(user) for user in rejected.review_ids.mapped("reviewer_ids") if rejected.with_user(user).can_review), None)
        assert actor is not None
        actor.env["sc.approval.policy"]._reject_submission_review(actor, reason="Runtime labor rejection")
        rejected.invalidate_recordset()
        assert rejected.state == "draft" and rejected.reject_reason == "Runtime labor rejection"
        rejected.action_submit()
        assert rejected.review_ids and old.isdisjoint(rejected.review_ids.ids)
        _approve_existing_reviews(rejected)
        assert rejected.state == "approved" and not rejected.reject_reason
        print("APPROVAL_CHECK=%s_rejection_and_resubmission_use_new_review" % model)


def _rental_plan_checks(project, group, created):
    env = _env()
    Policy = env["sc.approval.policy"].sudo()

    def denied(call):
        refused = False
        try:
            with env.cr.savepoint(): call()
        except UserError:
            refused = True
        assert refused, "business operation unexpectedly permitted"

    def document(model, **values):
        record = env[model].sudo().create({"project_id": project.id,
            "line_ids": [(0, 0, {"material_name": "Rollback rental", "planned_qty": 2, "planned_days": 3, "daily_price": 10})], **values})
        created.append((record._name, record.id))
        return record

    for model in ("sc.material.rental.plan",):
        assert not Policy.with_context(active_test=False).search_count([
            ("target_model", "=", model), ("company_id", "in", [False, env.company.id]),
        ]), "existing rental policy must not be overwritten"
        automatic = document(model)
        denied(lambda: automatic.with_context(sc_rental_approval_state_token=True).write({"state": "approved"}))
        print("APPROVAL_CHECK=%s_external_state_denied" % model)
        automatic.action_submit()
        assert automatic.state == "approved" and not automatic.review_ids
        print("APPROVAL_CHECK=%s_unconfigured_submission_auto_approved" % model)
        policy = Policy.create({"name": "Runtime rental approval", "code": "runtime_" + model.replace(".", "_"),
            "target_model": model, "company_id": env.company.id, "approval_required": True, "mode": "single",
            "manager_group_id": group.id, "runtime_state": "tier_validation"})
        created.append((policy._name, policy.id))
        step = env["sc.approval.step"].sudo().create({"policy_id": policy.id, "name": "Labor review", "sequence": 10,
            "approval_scope_key": policy._approval_scope_for_group(group), "approve_group_id": group.id})
        policy.sync_tier_definitions()
        step.write({"amount_min": 10})
        policy.sync_tier_definitions()
        assert automatic.estimated_amount == 60
        print("APPROVAL_CHECK=%s_estimated_amount_authority" % model)
        unmatched = document(model, line_ids=[(0, 0, {"material_name": "Below threshold", "planned_qty": 1, "planned_days": 1, "daily_price": 1})])
        denied(unmatched.action_submit)
        unmatched.invalidate_recordset()
        assert unmatched.state == "draft"
        print("APPROVAL_CHECK=%s_unmatched_configured_amount_rejected" % model)
        empty = document(model, line_ids=[])
        denied(empty.action_submit)
        assert empty.state == "draft"
        print("APPROVAL_CHECK=%s_empty_lines_rejected" % model)
        required = document(model)
        required.action_submit()
        assert required.state == "submitted" and required.review_ids
        required.action_on_tier_approved()
        assert required.state == "submitted"
        policy.write({"approval_required": False})
        denied(required.action_submit)
        policy.write({"approval_required": True})
        print("APPROVAL_CHECK=%s_pending_review_survives_configuration_change" % model)
        _approve_existing_reviews(required)
        assert required.state == "approved" and required.validation_status == "validated"
        print("APPROVAL_CHECK=%s_actual_review_approves_document" % model)
        for method in (required.action_submit, required.action_cancel, required.action_reset_draft):
            denied(method)
        assert required.state == "approved"
        print("APPROVAL_CHECK=%s_approved_document_cannot_bypass_state_machine" % model)
        cancelled = document(model)
        cancelled.action_cancel()
        assert cancelled.state == "cancel"
        cancelled.action_reset_draft()
        assert cancelled.state == "draft"
        print("APPROVAL_CHECK=%s_cancelled_document_can_reset" % model)
        rejected = document(model)
        rejected.action_submit()
        old = set(rejected.review_ids.ids)
        actor = next((rejected.with_user(user) for user in rejected.review_ids.mapped("reviewer_ids") if rejected.with_user(user).can_review), None)
        assert actor is not None
        actor.env["sc.approval.policy"]._reject_submission_review(actor, reason="Runtime rental rejection")
        rejected.invalidate_recordset()
        assert rejected.state == "draft" and rejected.reject_reason == "Runtime rental rejection"
        rejected.action_submit()
        assert rejected.review_ids and old.isdisjoint(rejected.review_ids.ids)
        _approve_existing_reviews(rejected)
        assert rejected.state == "approved" and not rejected.reject_reason
        print("APPROVAL_CHECK=%s_rejection_and_resubmission_use_new_review" % model)


def _rental_settlement_cash_checks(_project_unused, _group_unused, created):
    base = _env()
    finance = base["res.users"].sudo().search([("login", "=", "fixture_role_finance"), ("active", "=", True)], limit=1)
    assert finance, "existing finance fixture required"
    company = finance.company_id
    env = base["res.company"].with_company(company).env
    actor_env = env["payment.request"].with_user(finance).with_company(company).with_context(allowed_company_ids=[company.id]).env
    assert not actor_env.su, "cash actions must use the fixture role without sudo"
    assert actor_env["payment.request"]._has_submit_access(), "finance fixture cannot submit requests"
    actor_env["sc.payment.execution"]._assert_finance_handling_access()
    actor_env["sc.payment.execution"]._assert_finance_confirm_access()
    actor_env["sc.payment.execution"]._assert_finance_cancel_access()
    project = env["project.project"].sudo().create({"name": "Rental cash rollback project", "code": "RENTAL-CASH-ROLLBACK", "company_id": company.id, "manager_id": finance.id, "funding_enabled": True})
    supplier = env["res.partner"].sudo().create({"name": "Rental cash rollback supplier", "supplier_rank": 1})
    created.extend([(project._name, project.id), (supplier._name, supplier.id)])
    today = fields.Date.context_today(project)
    baseline = env["project.funding.baseline"].sudo().create({"project_id": project.id, "total_amount": 1000,
        "period_start": today - timedelta(days=1), "period_end": today + timedelta(days=30),
        "line_ids": [(0, 0, {"name": "Rental cash rollback allocation", "planned_amount": 1000})]})
    created.append((baseline._name, baseline.id))
    baseline.action_activate()
    assert baseline.state == "active"
    print("APPROVAL_CHECK=rental_cash_registered_finance_and_active_funding")

    def denied(call, expected=None):
        refused = False
        try:
            with env.cr.savepoint(): call()
        except UserError as exc:
            if expected: assert expected in str(exc), str(exc)
            refused = True
        assert refused, "business operation unexpectedly permitted"

    source = env["sc.material.rental.settlement"].sudo().create({"project_id": project.id, "supplier_id": supplier.id,
        "line_ids": [(0, 0, {"material_name": "Rental cash rollback item", "qty": 2, "rental_days": 3, "daily_price": 10})]})
    created.append((source._name, source.id))
    source.action_submit()
    if source.review_ids: _approve_existing_reviews(source)
    assert source.state == "approved"
    source.action_confirm()
    print("APPROVAL_CHECK=rental_cash_source_approved_and_confirmed")

    def request_for(amount):
        request = actor_env["payment.request"].create({"type": "pay", "rental_settlement_id": source.id, "amount": amount,
            "payment_account_name": "Rollback rental payee", "payment_bank_name": "Rollback bank", "payment_account_no": "ROLLBACK-RENTAL-PAYEE",
            "payer_unit": "Rollback rental payer"})
        created.append((request._name, request.id))
        _attach(request, "rental-cash-request")
        return request

    request = request_for(60)
    request.action_submit()
    if request.review_ids: _approve_existing_reviews(request)
    request.invalidate_recordset()
    assert request.state == "approved" and request.funding_baseline_id == baseline
    print("APPROVAL_CHECK=rental_cash_finance_request_submission_and_approval")
    extra = request_for(1)
    denied(extra.action_submit, "未占用额度")
    denied(source.action_cancel, "付款申请")
    print("APPROVAL_CHECK=rental_cash_overbooking_and_live_source_cancel_denied")

    if os.environ.get("SC_APPROVAL_RUNTIME_SCOPE") == "rental-cancellation-contract":
        service = source.env["sc.workflow.contract.service"]
        contract = service.describe_record(source)
        cancel = next(row for row in contract["availableActions"] if row["key"] == "cancel")
        assert cancel["enabled"] is False
        assert cancel["reason_code"] == "RENTAL_PAYMENT_OBLIGATIONS_ACTIVE"
        assert cancel["blocked_message"] and cancel["target"]["id"] == source.id
        print("APPROVAL_CHECK=rental_cancel_contract_matches_active_obligation")
        request.action_cancel()
        source.invalidate_recordset()
        contract = service.describe_record(source)
        cancel = next(row for row in contract["availableActions"] if row["key"] == "cancel")
        assert cancel["enabled"] is True and not cancel["reason_code"]
        source.action_cancel()
        assert source.state == "cancel"
        print("APPROVAL_CHECK=rental_cancel_contract_recovers_after_release")
        return

    def pay(amount):
        action = request.action_create_payment_execution()
        execution = actor_env["sc.payment.execution"].with_context(action["context"]).create({"payment_request_id": request.id, "paid_amount": amount,
            "payment_account_name": "Rollback rental payer", "payment_bank_name": "Rollback bank",
            "payment_account_no": "ROLLBACK-RENTAL-PAYER", "payment_method": "银行转账"})
        created.append((execution._name, execution.id))
        _attach(execution, "rental-cash-execution")
        execution.action_confirm()
        if execution.review_ids: _approve_existing_reviews(execution)
        assert execution.state == "confirmed"
        execution.action_paid()
        execution.invalidate_recordset()
        assert execution.state == "paid"
        ledgers = env["payment.ledger"].sudo().search([("payment_execution_id", "=", execution.id), ("state", "=", "posted")])
        assert len(ledgers) == 1 and ledgers.amount == amount
        origin = ledgers.action_open_settlement()
        assert origin["res_model"] == source._name and origin["res_id"] == source.id
        created.extend((ledger._name, ledger.id) for ledger in ledgers)
        source.invalidate_recordset()
        request.invalidate_recordset()
        return execution

    first = pay(20)
    assert source.payment_paid_amount == 20 and source.payment_remaining_amount == 40
    denied(source.action_paid, "RENTAL_PAYMENT_NOT_FULLY_PAID")
    print("APPROVAL_CHECK=rental_cash_partial_payment_is_not_paid_settlement")
    second = pay(40)
    assert source.payment_paid_amount == 60 and source.payment_remaining_amount == 0
    source.action_paid()
    assert source.state == "paid"
    print("APPROVAL_CHECK=rental_cash_full_posted_payment_allows_explicit_confirmation")
    denied(lambda: request.write({"rental_settlement_id": False}), "归属")
    print("APPROVAL_CHECK=rental_cash_posted_attribution_is_immutable")
    second.write({"reversal_reason": "Rental cash rollback reversal"})
    second.action_reverse_payment()
    source.invalidate_recordset()
    request.invalidate_recordset()
    assert source.state == "confirmed" and source.payment_paid_amount == 20 and source.payment_remaining_amount == 40
    assert request.state == "approved"
    print("APPROVAL_CHECK=rental_cash_reversal_demotes_paid_confirmation")
    first.write({"reversal_reason": "Rental cash rollback remaining reversal"})
    first.action_reverse_payment()
    source.invalidate_recordset()
    assert source.payment_paid_amount == 0 and source.payment_remaining_amount == 60
    denied(source.action_paid, "RENTAL_PAYMENT_NOT_FULLY_PAID")
    denied(lambda: request.write({"rental_settlement_id": False}), "归属")
    print("APPROVAL_CHECK=rental_cash_all_reversed_history_keeps_attribution")
    request.action_cancel()
    source.action_cancel()
    assert source.state == "cancel"
    print("APPROVAL_CHECK=rental_cash_cancel_after_obligations_released")


def _subcontract_settlement_cash_checks(_project_unused, _group_unused, created):
    base = _env()
    finance = base["res.users"].sudo().search([("login", "=", "fixture_role_finance"), ("active", "=", True)], limit=1)
    assert finance, "existing finance fixture required"
    company = finance.company_id
    env = base["res.company"].with_company(company).env
    actor_env = env["payment.request"].with_user(finance).with_company(company).with_context(allowed_company_ids=[company.id]).env
    assert not actor_env.su, "cash actions must use the fixture role without sudo"
    assert actor_env["payment.request"]._has_submit_access(), "finance fixture cannot submit requests"
    actor_env["sc.payment.execution"]._assert_finance_handling_access()
    actor_env["sc.payment.execution"]._assert_finance_confirm_access()
    actor_env["sc.payment.execution"]._assert_finance_cancel_access()
    project = env["project.project"].sudo().create({"name": "Subcontract cash rollback project", "code": "SUBCONTRACT-CASH-ROLLBACK", "company_id": company.id, "manager_id": finance.id, "funding_enabled": True})
    supplier = env["res.partner"].sudo().create({"name": "Subcontract cash rollback supplier", "supplier_rank": 1})
    created.extend([(project._name, project.id), (supplier._name, supplier.id)])
    today = fields.Date.context_today(project)
    baseline = env["project.funding.baseline"].sudo().create({"project_id": project.id, "total_amount": 1000,
        "period_start": today - timedelta(days=1), "period_end": today + timedelta(days=30),
        "line_ids": [(0, 0, {"name": "Subcontract cash rollback allocation", "planned_amount": 1000})]})
    created.append((baseline._name, baseline.id))
    baseline.action_activate()
    assert baseline.state == "active"
    print("APPROVAL_CHECK=subcontract_cash_registered_finance_and_active_funding")

    def denied(call, expected=None):
        refused = False
        try:
            with env.cr.savepoint(): call()
        except UserError as exc:
            if expected: assert expected in str(exc), str(exc)
            refused = True
        assert refused, "business operation unexpectedly permitted"

    source = env["sc.subcontract.settlement"].sudo().create({"project_id": project.id, "subcontractor_id": supplier.id, "owner_id": finance.id,
        "line_ids": [(0, 0, {"work_scope": "Subcontract cash rollback item", "qty": 2, "unit_price": 30})]})
    created.append((source._name, source.id))
    assert actor_env[source._name].search([("id", "=", source.id)]) == source.with_env(actor_env), "source must be visible under existing owner/project rules"
    source.action_submit()
    if source.review_ids: _approve_existing_reviews(source)
    assert source.state == "approved"
    source.action_confirm()
    print("APPROVAL_CHECK=subcontract_cash_source_approved_and_confirmed")

    def request_for(amount):
        request = actor_env["payment.request"].create({"type": "pay", "subcontract_settlement_id": source.id, "amount": amount,
            "payment_account_name": "Rollback subcontract payee", "payment_bank_name": "Rollback bank", "payment_account_no": "ROLLBACK-SUBCONTRACT-PAYEE",
            "payer_unit": "Rollback subcontract payer"})
        created.append((request._name, request.id))
        _attach(request, "subcontract-cash-request")
        return request

    request = request_for(60)
    request.action_submit()
    if request.review_ids: _approve_existing_reviews(request)
    request.invalidate_recordset()
    assert request.state == "approved" and request.funding_baseline_id == baseline
    print("APPROVAL_CHECK=subcontract_cash_finance_request_submission_and_approval")
    extra = request_for(1)
    denied(extra.action_submit, "未占用额度")
    denied(source.action_cancel, "未确认")
    print("APPROVAL_CHECK=subcontract_cash_overbooking_and_live_source_cancel_denied")

    def pay(amount):
        action = request.action_create_payment_execution()
        execution = actor_env["sc.payment.execution"].with_context(action["context"]).create({"payment_request_id": request.id, "paid_amount": amount,
            "payment_account_name": "Rollback subcontract payer", "payment_bank_name": "Rollback bank",
            "payment_account_no": "ROLLBACK-SUBCONTRACT-PAYER", "payment_method": "银行转账"})
        created.append((execution._name, execution.id))
        _attach(execution, "subcontract-cash-execution")
        execution.action_confirm()
        if execution.review_ids: _approve_existing_reviews(execution)
        assert execution.state == "confirmed"
        execution.action_paid()
        execution.invalidate_recordset()
        assert execution.state == "paid"
        ledgers = env["payment.ledger"].sudo().search([("payment_execution_id", "=", execution.id), ("state", "=", "posted")])
        assert len(ledgers) == 1 and ledgers.amount == amount
        origin = ledgers.action_open_settlement()
        assert origin["res_model"] == source._name and origin["res_id"] == source.id
        created.extend((ledger._name, ledger.id) for ledger in ledgers)
        source.invalidate_recordset()
        request.invalidate_recordset()
        return execution

    first = pay(20)
    assert source.payment_paid_amount == 20 and source.payment_unpaid_amount == 40
    assert source.state == "confirmed"
    print("APPROVAL_CHECK=subcontract_cash_partial_payment_updates_authoritative_summary")
    second = pay(40)
    assert source.payment_paid_amount == 60 and source.payment_unpaid_amount == 0
    assert source.state == "confirmed"
    assert source.payment_requested_amount == 60 and source.payment_unrequested_amount == 0
    print("APPROVAL_CHECK=subcontract_cash_full_posted_payment_preserves_confirmed_settlement")
    denied(lambda: request.write({"subcontract_settlement_id": False}), "归属")
    print("APPROVAL_CHECK=subcontract_cash_posted_attribution_is_immutable")
    second.write({"reversal_reason": "Subcontract cash rollback reversal"})
    second.action_reverse_payment()
    source.invalidate_recordset()
    request.invalidate_recordset()
    assert source.state == "confirmed" and source.payment_paid_amount == 20 and source.payment_unpaid_amount == 40
    assert request.state == "approved"
    print("APPROVAL_CHECK=subcontract_cash_reversal_updates_paid_summary")
    first.write({"reversal_reason": "Subcontract cash rollback remaining reversal"})
    first.action_reverse_payment()
    source.invalidate_recordset()
    assert source.payment_paid_amount == 0 and source.payment_unpaid_amount == 60
    assert source.state == "confirmed"
    denied(lambda: request.write({"subcontract_settlement_id": False}), "归属")
    print("APPROVAL_CHECK=subcontract_cash_all_reversed_history_keeps_attribution")
    request.action_cancel()
    source.invalidate_recordset()
    assert source.state == "confirmed"
    assert source.payment_requested_amount == 0 and source.payment_unrequested_amount == 60
    print("APPROVAL_CHECK=subcontract_cash_request_cancel_releases_reserved_amount")


def _rental_settlement_checks(project, group, created):
    env = _env()
    model = "sc.material.rental.settlement"
    Policy = env["sc.approval.policy"].sudo()
    supplier = _partner("Rollback rental settlement supplier")
    created.append((supplier._name, supplier.id))
    assert not Policy.with_context(active_test=False).search_count([
        ("target_model", "=", model), ("company_id", "in", [False, env.company.id]),
    ]), "existing rental settlement policy must not be overwritten"

    def denied(call):
        refused = False
        try:
            with env.cr.savepoint(): call()
        except UserError:
            refused = True
        assert refused, "business operation unexpectedly permitted"

    def document(**values):
        record = env[model].sudo().create({"project_id": project.id, "supplier_id": supplier.id,
            "line_ids": [(0, 0, {"material_name": "Rollback rental settlement", "qty": 2, "rental_days": 3, "daily_price": 10})], **values})
        created.append((record._name, record.id))
        return record

    automatic = document()
    denied(lambda: automatic.with_context(sc_rental_approval_state_token=True).write({"state": "paid"}))
    print("APPROVAL_CHECK=rental_settlement_external_state_denied")
    denied(automatic.action_confirm)
    automatic.action_submit()
    assert automatic.state == "approved" and not automatic.review_ids and automatic.amount_total == 60
    print("APPROVAL_CHECK=rental_settlement_auto_approval_not_confirmation")
    denied(lambda: automatic.write({"supplier_id": False}))
    denied(lambda: automatic.line_ids.write({"qty": 100}))
    denied(automatic.line_ids.unlink)
    denied(lambda: env["sc.material.rental.settlement.line"].sudo().with_context(default_settlement_id=automatic.id).create({"material_name": "Unauthorized extra line"}))
    assert automatic.amount_total == 60
    print("APPROVAL_CHECK=rental_settlement_parent_and_direct_line_protection")
    automatic.action_confirm()
    assert automatic.state == "confirmed"
    denied(automatic.action_confirm)
    print("APPROVAL_CHECK=rental_settlement_explicit_confirmation")
    denied(automatic.action_paid)
    assert automatic.payment_paid_amount == 0 and automatic.payment_remaining_amount == 60
    assert automatic._payment_confirmation_blocker()["reason_code"] == "RENTAL_PAYMENT_ATTRIBUTION_MISSING"
    print("APPROVAL_CHECK=rental_settlement_missing_paid_facts_denied")
    request = env["payment.request"].sudo().create({"type": "pay", "rental_settlement_id": automatic.id})
    created.append((request._name, request.id))
    assert request.project_id == project and request.partner_id == supplier and request.amount == 60
    assert request.currency_id == automatic.currency_id and request._has_payment_basis()
    assert request.payment_basis_type == "rental_settlement" and request in automatic.payment_request_ids
    assert not env["sc.payment.execution"]._payment_basis_contracts(request)
    print("APPROVAL_CHECK=rental_settlement_request_defaults_and_basis")
    denied(lambda: request.write({"type": "receive"}))
    denied(lambda: request.write({"rental_settlement_id": False, "state": "approved"}))
    print("APPROVAL_CHECK=rental_settlement_request_identity_and_state_guard")

    policy = Policy.create({"name": "Runtime rental settlement approval", "code": "runtime_rental_settlement",
        "target_model": model, "company_id": env.company.id, "approval_required": True, "mode": "single",
        "manager_group_id": group.id, "runtime_state": "tier_validation"})
    created.append((policy._name, policy.id))
    step = env["sc.approval.step"].sudo().create({"policy_id": policy.id, "name": "Rental settlement review", "sequence": 10,
        "approval_scope_key": policy._approval_scope_for_group(group), "approve_group_id": group.id, "amount_min": 10})
    policy.sync_tier_definitions()
    unmatched = document(line_ids=[(0, 0, {"material_name": "Below threshold", "qty": 1, "rental_days": 1, "daily_price": 1})])
    denied(unmatched.action_submit)
    unmatched.invalidate_recordset()
    assert unmatched.state == "draft"
    print("APPROVAL_CHECK=rental_settlement_configured_amount_unmatched_denied")
    required = document()
    required.action_submit()
    assert required.state == "submitted" and required.review_ids
    policy.write({"approval_required": False})
    denied(required.action_submit)
    denied(required.action_confirm)
    policy.write({"approval_required": True})
    print("APPROVAL_CHECK=rental_settlement_pending_review_survives_config_change")
    _approve_existing_reviews(required)
    assert required.state == "approved"
    required.action_confirm()
    assert required.state == "confirmed"
    print("APPROVAL_CHECK=rental_settlement_actual_review_then_confirmation")
    rejected = document()
    rejected.action_submit()
    previous = set(rejected.review_ids.ids)
    actor = next((rejected.with_user(user) for user in rejected.review_ids.mapped("reviewer_ids") if rejected.with_user(user).can_review), None)
    assert actor is not None
    actor.env["sc.approval.policy"]._reject_submission_review(actor, reason="Runtime rental settlement rejection")
    rejected.invalidate_recordset()
    assert rejected.state == "draft" and rejected.reject_reason
    rejected.line_ids.write({"qty": 3})
    rejected.action_submit()
    assert previous.isdisjoint(rejected.review_ids.ids)
    _approve_existing_reviews(rejected)
    assert rejected.state == "approved" and rejected.amount_total == 90
    print("APPROVAL_CHECK=rental_settlement_reject_edit_and_resubmit")
    empty = document(line_ids=[])
    denied(empty.action_submit)
    empty.action_cancel()
    assert empty.state == "cancel"
    print("APPROVAL_CHECK=rental_settlement_empty_submission_and_draft_cancel")


def _rental_order_checks(project, group, created):
    env = _env()
    Policy = env["sc.approval.policy"].sudo()
    supplier = _partner("Rollback rental order supplier")
    created.append((supplier._name, supplier.id))

    def denied(call):
        refused = False
        try:
            with env.cr.savepoint(): call()
        except UserError:
            refused = True
        assert refused, "business operation unexpectedly permitted"

    def document(model, **values):
        record = env[model].sudo().create({"project_id": project.id, "supplier_id": supplier.id,
            "line_ids": [(0, 0, {"material_name": "Rollback rental", "qty": 2, "rental_days": 3, "daily_price": 10})], **values})
        created.append((record._name, record.id))
        return record

    for model in ("sc.material.rental.order",):
        assert not Policy.with_context(active_test=False).search_count([
            ("target_model", "=", model), ("company_id", "in", [False, env.company.id]),
        ]), "existing rental policy must not be overwritten"
        automatic = document(model)
        denied(lambda: automatic.with_context(sc_rental_approval_state_token=True).write({"state": "approved"}))
        print("APPROVAL_CHECK=%s_external_state_denied" % model)
        denied(automatic.action_activate)
        automatic.action_submit()
        assert automatic.state == "approved" and not automatic.review_ids
        print("APPROVAL_CHECK=%s_unconfigured_submission_auto_approved" % model)
        policy = Policy.create({"name": "Runtime rental approval", "code": "runtime_" + model.replace(".", "_"),
            "target_model": model, "company_id": env.company.id, "approval_required": True, "mode": "single",
            "manager_group_id": group.id, "runtime_state": "tier_validation"})
        created.append((policy._name, policy.id))
        step = env["sc.approval.step"].sudo().create({"policy_id": policy.id, "name": "Labor review", "sequence": 10,
            "approval_scope_key": policy._approval_scope_for_group(group), "approve_group_id": group.id})
        policy.sync_tier_definitions()
        step.write({"amount_min": 10})
        policy.sync_tier_definitions()
        assert automatic.amount_total == 60
        print("APPROVAL_CHECK=%s_amount_total_authority" % model)
        unmatched = document(model, line_ids=[(0, 0, {"material_name": "Below threshold", "qty": 1, "rental_days": 1, "daily_price": 1})])
        denied(unmatched.action_submit)
        unmatched.invalidate_recordset()
        assert unmatched.state == "draft"
        print("APPROVAL_CHECK=%s_unmatched_configured_amount_rejected" % model)
        empty = document(model, line_ids=[])
        denied(empty.action_submit)
        assert empty.state == "draft"
        print("APPROVAL_CHECK=%s_empty_lines_rejected" % model)
        required = document(model)
        required.action_submit()
        assert required.state == "submitted" and required.review_ids
        required.action_on_tier_approved()
        assert required.state == "submitted"
        policy.write({"approval_required": False})
        denied(required.action_submit)
        denied(required.action_activate)
        policy.write({"approval_required": True})
        print("APPROVAL_CHECK=%s_pending_review_survives_configuration_change" % model)
        _approve_existing_reviews(required)
        assert required.state == "approved" and required.validation_status == "validated"
        print("APPROVAL_CHECK=%s_actual_review_approves_document" % model)
        required.action_activate()
        assert required.state == "active"
        denied(required.action_activate)
        required.action_return()
        assert required.state == "returned" and required.actual_return_date
        denied(required.action_cancel)
        required.action_settle()
        assert required.state == "settled"
        denied(required.action_settle)
        print("APPROVAL_CHECK=%s_explicit_rental_return_settle_chain" % model)
        automatic.action_cancel()
        assert automatic.state == "cancel"
        print("APPROVAL_CHECK=%s_approved_cancellation_remains_explicit" % model)
        rejected = document(model)
        rejected.action_submit()
        old = set(rejected.review_ids.ids)
        actor = next((rejected.with_user(user) for user in rejected.review_ids.mapped("reviewer_ids") if rejected.with_user(user).can_review), None)
        assert actor is not None
        actor.env["sc.approval.policy"]._reject_submission_review(actor, reason="Runtime rental rejection")
        rejected.invalidate_recordset()
        assert rejected.state == "draft" and rejected.reject_reason == "Runtime rental rejection"
        rejected.action_submit()
        assert rejected.review_ids and old.isdisjoint(rejected.review_ids.ids)
        _approve_existing_reviews(rejected)
        assert rejected.state == "approved" and not rejected.reject_reason
        print("APPROVAL_CHECK=%s_rejection_and_resubmission_use_new_review" % model)


    plan = env["sc.material.rental.plan"].sudo().create({"project_id": project.id,
        "line_ids": [(0, 0, {"material_name": "Rollback source plan", "planned_qty": 1, "planned_days": 1, "daily_price": 20})]})
    created.append((plan._name, plan.id))
    linked = document("sc.material.rental.order", plan_id=plan.id)
    denied(linked.action_submit)
    assert linked.state == "draft"
    print("APPROVAL_CHECK=rental_order_unapproved_source_plan_rejected")
    plan.action_submit()
    if plan.review_ids: _approve_existing_reviews(plan)
    assert plan.state == "approved"
    linked.action_submit()
    _approve_existing_reviews(linked)
    linked.action_activate()
    assert linked.state == "active"
    print("APPROVAL_CHECK=rental_order_approved_source_plan_accepted")
    other = _project("Rollback rental other project")
    created.append((other._name, other.id))
    wrong = document("sc.material.rental.order", project_id=other.id, plan_id=plan.id)
    denied(wrong.action_submit)
    assert wrong.state == "draft"
    print("APPROVAL_CHECK=rental_order_cross_project_source_rejected")


def _labor_execution_checks(project, group, created):
    env = _env()
    Policy = env["sc.approval.policy"].sudo()
    contractor = _partner("Rollback labor contractor")
    created.append((contractor._name, contractor.id))
    source = None

    def denied(call):
        refused = False
        try:
            with env.cr.savepoint(): call()
        except UserError:
            refused = True
        assert refused, "business operation unexpectedly permitted"

    def document(model, usage=None, **overrides):
        values = {"project_id": project.id, "contractor_id": contractor.id}
        if model == "sc.attendance.checkin":
            values.update(labor_team="Rollback team", work_content="Rollback work", attendance_qty=1, work_hours=2)
        elif model == "sc.labor.usage":
            values.update(labor_team="Rollback team", work_content="Rollback work", worker_qty=1, work_hours=2, price_unit=10)
        else:
            if usage is None:
                usage = document("sc.labor.usage")
                usage.action_submit()
                if usage.review_ids:
                    _approve_existing_reviews(usage)
                usage.action_confirm()
            values["line_ids"] = [(0, 0, {"work_content": "Rollback work", "qty": 2, "unit_price": 10,
                                            "source_usage_id": usage.id if usage else False})]
        values.update(overrides)
        record = env[model].sudo().create(values)
        created.append((record._name, record.id))
        return record

    for model in ("sc.attendance.checkin", "sc.labor.usage", "sc.labor.settlement"):
        assert not Policy.with_context(active_test=False).search_count([
            ("target_model", "=", model), ("company_id", "in", [False, env.company.id]),
        ]), "existing labor execution policy must not be overwritten"
        automatic = document(model)
        denied(lambda: automatic.write({"state": "confirmed"}))
        denied(automatic.action_confirm)
        print("APPROVAL_CHECK=%s_external_state_and_premature_confirmation_denied" % model)
        automatic.action_submit()
        assert automatic.state == "approved" and not automatic.review_ids
        print("APPROVAL_CHECK=%s_unconfigured_approval_stops_before_confirmation" % model)
        policy = Policy.create({"name": "Runtime labor execution approval", "code": "runtime_" + model.replace(".", "_"),
            "target_model": model, "company_id": env.company.id, "approval_required": True, "mode": "single",
            "manager_group_id": group.id, "runtime_state": "tier_validation"})
        created.append((policy._name, policy.id))
        step = env["sc.approval.step"].sudo().create({"policy_id": policy.id, "name": "Labor execution review", "sequence": 10,
            "approval_scope_key": policy._approval_scope_for_group(group), "approve_group_id": group.id})
        policy.sync_tier_definitions()
        if model == "sc.attendance.checkin":
            denied(lambda: step.write({"amount_min": 1}))
            step.invalidate_recordset()
            assert not step.amount_min
        else:
            step.write({"amount_min": 1})
            policy.sync_tier_definitions()
        print("APPROVAL_CHECK=%s_monetary_rule_respects_authority" % model)
        required = document(model)
        required.action_submit()
        assert required.state == "submitted" and required.review_ids
        if model != "sc.attendance.checkin": assert required.amount_total == 20
        denied(required.action_confirm)
        policy.write({"approval_required": False})
        denied(required.action_submit)
        policy.write({"approval_required": True})
        print("APPROVAL_CHECK=%s_pending_review_blocks_confirmation_and_restart" % model)
        _approve_existing_reviews(required)
        assert required.state == "approved" and required.validation_status == "validated"
        print("APPROVAL_CHECK=%s_real_approval_does_not_confirm" % model)
        if model == "sc.labor.usage":
            denied(lambda: required.write({"work_hours": 3}))
            denied(required.unlink)
            actor = env["res.users"].sudo().search([("login", "=", "fixture_role_finance")], limit=1)
            assert actor and not actor.has_group("smart_construction_core.group_sc_cap_project_manager") and not actor.has_group("smart_construction_core.group_sc_super_admin")
            denied(required.with_user(actor).action_confirm)
            denied(required.with_user(actor).action_cancel)
            print("APPROVAL_CHECK=labor_usage_approved_fact_lock_and_manager_boundary")
        required.action_confirm()
        assert required.state == "confirmed"
        denied(required.action_confirm)
        if model == "sc.labor.usage": source = required
        print("APPROVAL_CHECK=%s_explicit_confirmation_preserved" % model)
        rejected = document(model)
        rejected.action_submit()
        old = set(rejected.review_ids.ids)
        actor = next((rejected.with_user(user) for user in rejected.review_ids.mapped("reviewer_ids") if rejected.with_user(user).can_review), None)
        assert actor is not None
        actor.env["sc.approval.policy"]._reject_submission_review(actor, reason="Runtime labor execution rejection")
        rejected.invalidate_recordset()
        assert rejected.state == "draft" and rejected.reject_reason == "Runtime labor execution rejection"
        rejected.action_submit()
        assert rejected.review_ids and old.isdisjoint(rejected.review_ids.ids)
        _approve_existing_reviews(rejected)
        assert rejected.state == "approved" and not rejected.reject_reason
        print("APPROVAL_CHECK=%s_rejection_resubmission_stops_before_confirmation" % model)
    other = _project("Rollback labor other project")
    created.append((other._name, other.id))
    denied(lambda: document("sc.labor.settlement", source, project_id=other.id).action_submit())
    print("APPROVAL_CHECK=labor_settlement_cross_project_source_denied")
    other_contractor = _partner("Rollback other contractor")
    created.append((other_contractor._name, other_contractor.id))
    denied(lambda: document("sc.labor.settlement", source, contractor_id=other_contractor.id).action_submit())
    print("APPROVAL_CHECK=labor_settlement_wrong_contractor_source_denied")
    source.write({"settlement_state": "settled"})
    already_settled = document("sc.labor.settlement", source)
    denied(already_settled.action_submit)
    assert already_settled.state == "draft" and not already_settled.review_ids
    print("APPROVAL_CHECK=labor_settlement_already_settled_source_denied")


def _safety_approval_checks(project, group, created):
    env = _env()
    Policy = env["sc.approval.policy"].sudo()
    approved_plan = None

    def denied(call):
        refused = False
        try:
            with env.cr.savepoint(): call()
        except UserError:
            refused = True
        assert refused, "business operation unexpectedly permitted"

    for model in ("sc.safety.plan", "sc.safety.disclosure"):
        assert not Policy.with_context(active_test=False).search_count([
            ("target_model", "=", model), ("company_id", "in", [False, env.company.id]),
        ]), "existing safety policy must not be overwritten"

        def document(**values):
            data = {"name": "Rollback safety approval", "project_id": project.id}
            if model == "sc.safety.plan":
                data["description"] = "Rollback safety plan"
            else:
                data.update(participant_note="Rollback participants", content="Rollback disclosure", safety_plan_id=approved_plan.id)
            record = env[model].sudo().create({**data, **values})
            created.append((record._name, record.id))
            return record

        automatic = document()
        denied(lambda: document(state="approved"))
        denied(lambda: automatic.with_context(sc_safety_approval_state_token=True).write({"state": "approved"}))
        print("APPROVAL_CHECK=%s_external_state_denied" % model)
        invalid = document(**({"description": False} if model.endswith("plan") else {"content": False}))
        denied(invalid.action_submit)
        invalid.action_cancel()
        invalid.action_reset_draft()
        assert invalid.state == "draft"
        print("APPROVAL_CHECK=%s_anchor_and_cancel_reset" % model)
        automatic.action_submit()
        assert automatic.state == "approved" and not automatic.review_ids
        denied(automatic.action_approve)
        if model.endswith("plan"): approved_plan = automatic
        print("APPROVAL_CHECK=%s_no_config_auto_approved" % model)

        policy = Policy.create({"name": "Runtime safety approval", "code": "runtime_" + model.replace(".", "_"),
            "target_model": model, "company_id": env.company.id, "approval_required": True, "mode": "single",
            "manager_group_id": group.id, "runtime_state": "tier_validation"})
        created.append((policy._name, policy.id))
        step = env["sc.approval.step"].sudo().create({"policy_id": policy.id, "name": "Safety review", "sequence": 10,
            "approval_scope_key": policy._approval_scope_for_group(group), "approve_group_id": group.id})
        policy.sync_tier_definitions()
        denied(lambda: step.write({"amount_min": 1}))
        step.invalidate_recordset()
        assert not step.amount_min
        step.write({"active": False})
        unmatched = document()
        denied(unmatched.action_submit)
        unmatched.invalidate_recordset()
        assert unmatched.state == "draft"
        print("APPROVAL_CHECK=%s_configured_unmatched_denied" % model)
        step.write({"active": True})
        policy.sync_tier_definitions()
        required = document()
        required.action_submit()
        assert required.state == "submitted" and required.review_ids
        contract = env["sc.workflow.contract.service"].describe_record(required)
        assert contract["approvalPhase"] in ("waiting", "pending")
        assert next(row for row in contract["actions"] if row["key"] == "approve")["method"] == "validate_tier"
        assert not any(row["key"] == "submit" for row in contract["availableActions"])
        print("APPROVAL_CHECK=%s_pending_contract_uses_real_review" % model)
        policy.write({"approval_required": False})
        denied(required.action_submit)
        assert required.state == "submitted"
        policy.write({"approval_required": True})
        print("APPROVAL_CHECK=%s_pending_survives_configuration_change" % model)
        _approve_existing_reviews(required)
        assert required.state == "approved"
        denied(required.action_submit)
        print("APPROVAL_CHECK=%s_actual_review_completes" % model)
        rejected = document()
        rejected.action_submit()
        old = set(rejected.review_ids.ids)
        actor = next((rejected.with_user(user) for user in rejected.review_ids.mapped("reviewer_ids") if rejected.with_user(user).can_review), None)
        assert actor is not None
        actor.env["sc.approval.policy"]._reject_submission_review(actor, reason="Runtime safety rejection")
        rejected.invalidate_recordset()
        assert rejected.state == "draft" and rejected.reject_reason
        rejected.action_submit()
        assert old.isdisjoint(rejected.review_ids.ids)
        _approve_existing_reviews(rejected)
        assert rejected.state == "approved" and not rejected.reject_reason
        print("APPROVAL_CHECK=%s_reject_resubmit_new_review" % model)


def _subcontract_approval_checks(project, group, created):
    env = _env()
    Policy = env["sc.approval.policy"].sudo()
    approved_plan = None

    def denied(call):
        refused = False
        try:
            with env.cr.savepoint(): call()
        except UserError:
            refused = True
        assert refused, "business operation unexpectedly permitted"

    for model in ("sc.subcontract.plan", "sc.subcontract.request"):
        assert not Policy.with_context(active_test=False).search_count([
            ("target_model", "=", model), ("company_id", "in", [False, env.company.id]),
        ]), "existing subcontract policy must not be overwritten"

        def document(**values):
            data = {"project_id": project.id, "subcontract_scope": "Rollback subcontract scope",
                "line_ids": [(0, 0, {"work_scope": "Rollback scope", "estimated_amount": 100})]}
            if model.endswith("request"):
                data["plan_id"] = approved_plan.id
            record = env[model].sudo().create({**data, **values})
            created.append((record._name, record.id))
            return record

        automatic = document()
        denied(lambda: document(state="approved"))
        denied(lambda: automatic.with_context(sc_subcontract_approval_state_token=True).write({"state": "approved"}))
        print("APPROVAL_CHECK=%s_external_state_denied" % model)
        invalid = document(line_ids=[])
        denied(invalid.action_submit)
        invalid.action_cancel()
        invalid.action_reset_draft()
        assert invalid.state == "draft"
        print("APPROVAL_CHECK=%s_anchor_and_cancel_reset" % model)
        automatic.action_submit()
        assert automatic.state == "approved" and not automatic.review_ids
        denied(automatic.action_approve)
        if model.endswith("plan"): approved_plan = automatic
        print("APPROVAL_CHECK=%s_no_config_auto_approved" % model)

        policy = Policy.create({"name": "Runtime subcontract approval", "code": "runtime_" + model.replace(".", "_"),
            "target_model": model, "company_id": env.company.id, "approval_required": True, "mode": "single",
            "manager_group_id": group.id, "runtime_state": "tier_validation"})
        created.append((policy._name, policy.id))
        step = env["sc.approval.step"].sudo().create({"policy_id": policy.id, "name": "Subcontract review", "sequence": 10,
            "approval_scope_key": policy._approval_scope_for_group(group), "approve_group_id": group.id})
        policy.sync_tier_definitions()
        step.write({"amount_min": 200})
        unmatched = document()
        denied(unmatched.action_submit)
        unmatched.invalidate_recordset()
        assert unmatched.state == "draft"
        print("APPROVAL_CHECK=%s_configured_unmatched_denied" % model)
        step.write({"amount_min": 0})
        policy.sync_tier_definitions()
        required = document()
        required.action_submit()
        assert required.state == "submitted" and required.review_ids
        denied(lambda: required.write({"subcontract_scope": "Unauthorized change"}))
        denied(lambda: required.line_ids.write({"estimated_amount": 1000}))
        denied(required.line_ids.unlink)
        parent = "plan_id" if model.endswith("plan") else "request_id"
        denied(lambda: env[model + ".line"].sudo().with_context(**{"default_" + parent: required.id}).create({"work_scope": "Unauthorized extra", "estimated_amount": 1000}))

        contract = env["sc.workflow.contract.service"].describe_record(required)
        assert contract["approvalPhase"] in ("waiting", "pending")
        assert next(row for row in contract["actions"] if row["key"] == "approve")["method"] == "validate_tier"
        assert not any(row["key"] == "submit" for row in contract["availableActions"])
        print("APPROVAL_CHECK=%s_pending_contract_uses_real_review" % model)
        policy.write({"approval_required": False})
        denied(required.action_submit)
        assert required.state == "submitted"
        policy.write({"approval_required": True})
        print("APPROVAL_CHECK=%s_pending_survives_configuration_change" % model)
        _approve_existing_reviews(required)
        assert required.state == "approved"
        denied(lambda: required.write({"contract_id": False}))
        denied(lambda: required.line_ids.write({"estimated_amount": 1000}))
        denied(required.unlink)
        denied(required.action_submit)
        print("APPROVAL_CHECK=%s_actual_review_completes" % model)
        rejected = document()
        rejected.action_submit()
        old = set(rejected.review_ids.ids)
        actor = next((rejected.with_user(user) for user in rejected.review_ids.mapped("reviewer_ids") if rejected.with_user(user).can_review), None)
        assert actor is not None
        actor.env["sc.approval.policy"]._reject_submission_review(actor, reason="Runtime subcontract rejection")
        rejected.invalidate_recordset()
        assert rejected.state == "draft" and rejected.reject_reason
        rejected.action_submit()
        assert old.isdisjoint(rejected.review_ids.ids)
        _approve_existing_reviews(rejected)
        assert rejected.state == "approved" and not rejected.reject_reason
        print("APPROVAL_CHECK=%s_reject_resubmit_new_review" % model)


def _subcontract_settlement_approval_checks(project, group, created):
    env = _env()
    Policy = env["sc.approval.policy"].sudo()
    supplier = _partner("Rollback subcontract settlement supplier")
    created.append((supplier._name, supplier.id))

    def denied(call):
        refused = False
        try:
            with env.cr.savepoint(): call()
        except UserError:
            refused = True
        assert refused, "business operation unexpectedly permitted"

    for model in ("sc.subcontract.settlement",):
        assert not Policy.with_context(active_test=False).search_count([
            ("target_model", "=", model), ("company_id", "in", [False, env.company.id]),
        ]), "existing subcontract policy must not be overwritten"

        def document(**values):
            data = {"project_id": project.id, "subcontractor_id": supplier.id,
                "line_ids": [(0, 0, {"work_scope": "Rollback settlement scope", "qty": 1, "unit_price": 100})]}
            record = env[model].sudo().create({**data, **values})
            created.append((record._name, record.id))
            return record

        automatic = document()
        denied(lambda: document(state="approved"))
        denied(lambda: automatic.with_context(sc_subcontract_approval_state_token=True).write({"state": "approved"}))
        print("APPROVAL_CHECK=%s_external_state_denied" % model)
        invalid = document(line_ids=[])
        denied(invalid.action_submit)
        invalid.action_cancel()
        invalid.action_reset_draft()
        assert invalid.state == "draft"
        print("APPROVAL_CHECK=%s_anchor_and_cancel_reset" % model)
        automatic.action_submit()
        assert automatic.state == "approved" and not automatic.review_ids
        denied(automatic.action_approve)
        denied(lambda: automatic.line_ids.write({"unit_price": 200}))
        automatic.action_confirm()
        assert automatic.state == "confirmed"
        denied(automatic.action_confirm)
        print("APPROVAL_CHECK=%s_no_config_auto_approved" % model)

        policy = Policy.create({"name": "Runtime subcontract approval", "code": "runtime_" + model.replace(".", "_"),
            "target_model": model, "company_id": env.company.id, "approval_required": True, "mode": "single",
            "manager_group_id": group.id, "runtime_state": "tier_validation"})
        created.append((policy._name, policy.id))
        step = env["sc.approval.step"].sudo().create({"policy_id": policy.id, "name": "Subcontract review", "sequence": 10,
            "approval_scope_key": policy._approval_scope_for_group(group), "approve_group_id": group.id})
        policy.sync_tier_definitions()
        step.write({"amount_min": 200})
        unmatched = document()
        denied(unmatched.action_submit)
        unmatched.invalidate_recordset()
        assert unmatched.state == "draft"
        print("APPROVAL_CHECK=%s_configured_unmatched_denied" % model)
        step.write({"amount_min": 0})
        policy.sync_tier_definitions()
        required = document()
        required.action_submit()
        assert required.state == "submitted" and required.review_ids
        denied(lambda: required.write({"subcontractor_id": False}))
        denied(lambda: required.line_ids.write({"unit_price": 1000}))
        denied(required.line_ids.unlink)
        parent = "settlement_id"
        denied(lambda: env[model + ".line"].sudo().with_context(**{"default_" + parent: required.id}).create({"work_scope": "Unauthorized extra", "unit_price": 1000}))

        contract = env["sc.workflow.contract.service"].describe_record(required)
        assert contract["approvalPhase"] in ("waiting", "pending")
        assert next(row for row in contract["actions"] if row["key"] == "approve")["method"] == "validate_tier"
        assert not any(row["key"] == "submit" for row in contract["availableActions"])
        print("APPROVAL_CHECK=%s_pending_contract_uses_real_review" % model)
        denied(required.action_confirm)
        policy.write({"approval_required": False})
        denied(required.action_submit)
        assert required.state == "submitted"
        policy.write({"approval_required": True})
        print("APPROVAL_CHECK=%s_pending_survives_configuration_change" % model)
        _approve_existing_reviews(required)
        assert required.state == "approved"
        denied(lambda: required.write({"contract_id": False}))
        denied(lambda: required.line_ids.write({"unit_price": 1000}))
        denied(required.unlink)
        denied(required.action_submit)
        required.action_confirm()
        assert required.state == "confirmed"
        denied(required.action_confirm)
        print("APPROVAL_CHECK=%s_actual_review_then_explicit_confirmation" % model)
        rejected = document()
        rejected.action_submit()
        old = set(rejected.review_ids.ids)
        actor = next((rejected.with_user(user) for user in rejected.review_ids.mapped("reviewer_ids") if rejected.with_user(user).can_review), None)
        assert actor is not None
        actor.env["sc.approval.policy"]._reject_submission_review(actor, reason="Runtime subcontract rejection")
        rejected.invalidate_recordset()
        assert rejected.state == "draft" and rejected.reject_reason
        rejected.action_submit()
        assert old.isdisjoint(rejected.review_ids.ids)
        _approve_existing_reviews(rejected)
        assert rejected.state == "approved" and not rejected.reject_reason
        print("APPROVAL_CHECK=%s_reject_resubmit_new_review" % model)


def _expense_cash_execution_checks(created):
    base = _env()
    finance = base["res.users"].sudo().search([("login", "=", "fixture_role_finance"), ("active", "=", True)], limit=1)
    assert finance, "existing finance fixture required"
    company = finance.company_id
    env = base["sc.expense.claim"].with_user(finance).with_company(company).with_context(allowed_company_ids=[company.id]).env
    assert not env.su
    request = env["payment.request"].search([("company_id", "=", company.id), ("type", "=", "pay"),
        ("state", "=", "approved"), ("terminal_cash_source_model", "=", False),
        ("project_id", "!=", False), ("partner_id", "!=", False), ("amount", ">", 0)], limit=1)
    assert request, "existing finance-visible unclaimed approved pay request required"
    request_fields = ["state", "project_id", "company_id", "partner_id", "currency_id", "amount",
        "terminal_cash_source_model", "terminal_cash_source_res_id"]
    before = request.read(request_fields)
    Ledger = env["payment.ledger"]
    domain = [("payment_request_id", "=", request.id)]
    ledger_before = Ledger.search(domain).ids
    assert not ledger_before, "selected source already has payment facts"
    policies = env["sc.approval.policy"].sudo().with_context(active_test=False).search([
        ("target_model", "=", "sc.expense.claim"), ("company_id", "in", [False, company.id])])
    try:
        policies.write({"approval_required": False, "mode": "none"})
        policies.sync_tier_definitions()
        rec = env["sc.expense.claim"].with_context(default_business_category_code="finance.expense.reimbursement").create({
            "claim_type": "expense", "expense_type": "报销申请", "payment_request_id": request.id,
            "project_id": request.project_id.id, "partner_id": request.partner_id.id,
            "currency_id": request.currency_id.id, "amount": request.amount, "approved_amount": request.amount,
            "payee_account": "EXPENSE-CASH-PAYEE", "payer_account": "EXPENSE-CASH-PAYER"})
        created.append((rec._name, rec.id))
        _attach(rec, "expense-cash-execution")
        rec.action_submit()
        assert rec.state == "approved" and request.state == "approved"
        assert not Ledger.search_count(domain) and not request.terminal_cash_source_model
        print("APPROVAL_CHECK=expense_cash_approval_preserves_source_without_payment")
        rec.action_done()
        request.invalidate_recordset()
        ledger = Ledger.search(domain)
        assert rec.state == "done" and request.state == "done"
        assert request.terminal_cash_source_model == rec._name and request.terminal_cash_source_res_id == rec.id
        assert len(ledger) == 1 and ledger.state == "posted" and ledger.amount == request.amount
        assert ledger.project_id == request.project_id and ledger.company_id == company
        assert ledger.partner_id == request.partner_id and ledger.currency_id == request.currency_id
        created.append((ledger._name, ledger.id))
        for attempt in (rec.action_done, lambda: rec.write({"payment_request_id": False})):
            denied = False
            try:
                with env.cr.savepoint(): attempt()
            except UserError:
                denied = True
            assert denied, "terminal cash expense changed or repeated"
        assert Ledger.search_count(domain) == 1
        print("APPROVAL_CHECK=expense_cash_finance_execution_claims_source_and_posts_unique_payment")
    finally:
        env.cr.rollback()
        env.invalidate_all()
        assert request.read(request_fields) == before, "expense cash source not restored"
        assert Ledger.search(domain).ids == ledger_before, "expense cash ledger not restored"
        print("EXPENSE_CASH_SOURCE_ROLLBACK=VERIFIED")


def _expense_finance_execution_checks(group, created):
    base = _env()
    finance = base["res.users"].sudo().search([("login", "=", "fixture_role_finance"), ("active", "=", True)], limit=1)
    assert finance, "existing finance fixture required"
    company = finance.company_id
    env = base["sc.expense.claim"].with_user(finance).with_company(company).with_context(allowed_company_ids=[company.id]).env
    assert not env.su
    model = "sc.expense.claim"
    Document = env[model]
    assert Document.check_access_rights("create", raise_exception=False) and Document.check_access_rights("write", raise_exception=False)
    project = env["project.project"].search([("company_id", "=", company.id)], limit=1)
    partner = env["res.partner"].search([("company_id", "in", [False, company.id]), ("is_company", "=", True)], limit=1)
    assert project and partner, "existing finance-visible project and partner required"
    Policy = env["sc.approval.policy"].sudo()
    policies = Policy.with_context(active_test=False).search([("target_model", "=", model), ("company_id", "in", [False, company.id])])
    policies.write({"approval_required": False, "mode": "none"})
    policies.sync_tier_definitions()
    def document():
        rec = Document.create({"claim_type": "project_company_repay", "expense_type": "还款登记",
            "project_id": project.id, "partner_id": partner.id, "amount": 100.0,
            "approved_amount": 100.0, "summary": "Finance role interfund execution check",
            "payment_account_name": "Existing scope execution", "payer_account": "EXECUTION-PAYER",
            "receipt_account_name": "Existing scope receipt", "payee_account": "EXECUTION-PAYEE"})
        created.append((rec._name, rec.id))
        assert not rec.env.su
        _attach(rec, "expense-finance-execution")
        return rec
    rec = document()
    ledger_domain = [("source_model", "=", model), ("source_res_id", "=", rec.id)]
    Ledger = env["sc.treasury.ledger"]
    rec.action_submit()
    assert rec.state == "approved" and not rec.review_ids
    assert not Ledger.search_count(ledger_domain), "approval created execution cash ledger"
    print("APPROVAL_CHECK=expense_finance_auto_approval_separate_from_execution")
    rec.action_done()
    assert rec.state == "done"
    ledger = Ledger.search(ledger_domain)
    assert len(ledger) == 1 and ledger.state == "posted"
    assert ledger.company_id == company and ledger.project_id == project and ledger.partner_id == partner
    assert ledger.currency_id == rec.currency_id and ledger.amount == 100.0
    assert ledger.direction == ("in" if rec.direction == "inflow" else "out")
    created.append((ledger._name, ledger.id))
    print("APPROVAL_CHECK=expense_finance_completion_posts_exact_interfund_ledger")
    for attempt in (rec.action_done, rec.action_cancel, lambda: rec.write({"amount": 101.0})):
        denied = False
        try:
            with env.cr.savepoint(): attempt()
        except UserError:
            denied = True
        assert denied, "completed expense execution was rewritten"
    assert Ledger.search_count(ledger_domain) == 1
    rec.write({"note": "Supplement after execution"})
    print("APPROVAL_CHECK=expense_finance_terminal_repeat_and_mutation_denied")
    policy = policies.filtered(lambda row: row.company_id == company)[:1]
    values = {"active": True, "approval_required": True, "mode": "single", "manager_group_id": group.id, "runtime_state": "tier_validation"}
    if policy:
        policy.write(values)
        policy.step_ids.write({"active": False})
    else:
        policy = Policy.create(dict(values, name="Rollback expense finance", code="runtime_expense_finance_chain", target_model=model, company_id=company.id))
        created.append((policy._name, policy.id))
    step = env["sc.approval.step"].sudo().create({"policy_id": policy.id, "name": "Expense finance review",
        "sequence": max(policy.step_ids.mapped("sequence") or [0]) + 10,
        "approval_scope_key": policy._approval_scope_for_group(group), "approve_group_id": group.id})
    created.append((step._name, step.id))
    policy.sync_tier_definitions()
    assert Policy.get_active_policy(model, company=company) == policy
    configured = document()
    configured.action_submit()
    assert configured.state == "submit" and configured.review_ids and configured.validation_status in ("waiting", "pending")
    configured_domain = [("source_model", "=", model), ("source_res_id", "=", configured.id)]
    service = env["sc.workflow.contract.service"]
    pending_contract = service.describe_record(configured)
    assert pending_contract["editability"] == "readonly"
    assert not any(row["key"] == "complete" for row in pending_contract["availableActions"])
    for attempt in (configured.action_done, lambda: configured.write({"amount": 101.0})):
        denied = False
        try:
            with env.cr.savepoint(): attempt()
        except UserError:
            denied = True
        assert denied, "pending finance expense bypassed review"
    assert not Ledger.search_count(configured_domain)
    print("APPROVAL_CHECK=expense_finance_configured_submission_waits_without_execution")
    _approve_existing_reviews(configured)
    assert configured.state == "approved" and configured.validation_status == "validated"
    assert all(review.status == "approved" for review in configured.review_ids)
    approved_contract = service.describe_record(configured)
    assert approved_contract["editability"] == "readonly"
    assert any(row["key"] == "complete" and row["enabled"] for row in approved_contract["availableActions"])
    assert not Ledger.search_count(configured_domain)
    print("APPROVAL_CHECK=expense_finance_real_approval_enables_explicit_execution")
    configured.action_done()
    configured_ledger = Ledger.search(configured_domain)
    assert configured.state == "done" and len(configured_ledger) == 1 and configured_ledger.state == "posted"
    assert configured_ledger.company_id == company and configured_ledger.project_id == project
    assert configured_ledger.partner_id == partner and configured_ledger.currency_id == configured.currency_id
    assert configured_ledger.amount == 100.0 and configured_ledger.direction == ("in" if configured.direction == "inflow" else "out")
    assert configured_ledger != ledger
    created.append((configured_ledger._name, configured_ledger.id))
    assert not any(row["key"] == "complete" for row in service.describe_record(configured)["availableActions"])
    print("APPROVAL_CHECK=expense_finance_configured_completion_posts_unique_ledger")



def _expense_readiness_checks(project, partner, created):
    env = _env()
    claim = env["sc.expense.claim"].sudo().with_context(
        default_business_category_code="finance.expense.reimbursement"
    ).create({"claim_type": "expense", "expense_type": "报销申请", "project_id": project.id,
        "partner_id": partner.id, "amount": 100.0, "approved_amount": 100.0,
        "payee_account": "READINESS-RECEIVER", "payer_account": "READINESS-PAYER"})
    created.append((claim._name, claim.id))
    _attach(claim, "expense-readiness-anchor")
    def denied_submission(record, code):
        gates = env["sc.workflow.contract.service"].describe_record(record)["evidenceGate"]
        gate = next((row for row in gates if row["reasonCode"] == code), None)
        assert gate and gate["blocking"], (code, gates)
        denied = False
        try:
            with env.cr.savepoint(): record.action_submit()
        except UserError as exc:
            assert gate["message"] in str(exc), str(exc)
            denied = True
        assert denied, "declared expense gate did not block real submission"
        record.invalidate_recordset()
        assert record.state == "draft" and not record.review_ids
    assert claim.payment_anchor_policy == "pay_request_required"
    denied_submission(claim, "EXPENSE_MISSING_PAYMENT_REQUEST")
    print("APPROVAL_CHECK=expense_missing_anchor_contract_and_execution_agree")
    # The existing repayment fixture is interfund, not a cash account case.
    # Reuse this cash reimbursement; its missing anchor remains an additional
    # declared error, while pure tests isolate each readiness condition.
    ready = claim
    ready.write({"partner_id": False})
    denied_submission(ready, "EXPENSE_MISSING_PARTNER")
    ready.write({"partner_id": partner.id})
    assert ready.financial_flow in ("cash_in", "cash_out"), ready.financial_flow
    ready.write({"payer_account": False, "payment_account_name": False})
    denied_submission(ready, "EXPENSE_MISSING_RECEIVING_ACCOUNT" if ready.financial_flow == "cash_in" else "EXPENSE_MISSING_PAYER_ACCOUNT")
    print("APPROVAL_CHECK=expense_missing_partner_account_contract_and_execution_agree")


def _expense_deduction_line_checks(project, partner, created):
    """Exercise real child CRUD against the existing approval lifecycle; rolled back by main."""
    env = _env()
    lines = env["sc.expense.claim.deduction.line"].sudo()
    def document():
        rec = env["sc.expense.claim"].sudo().with_context(
            default_business_category_code="finance.deduction.bill"
        ).create({"claim_type": "expense", "expense_type": "扣款登记",
                  "project_id": project.id, "partner_id": partner.id,
                  "amount": 100.0, "approved_amount": 100.0,
                  "deduction_line_ids": [(0, 0, {"item_name": "Approval content check",
                      "deduction_category": "other", "amount": 100.0})]})
        created.append((rec._name, rec.id))
        created.extend((line._name, line.id) for line in rec.deduction_line_ids)
        _attach(rec, "expense-deduction-review-content")
        assert rec._is_noncash_deduction_bill()
        return rec
    required, draft = document(), document()
    line, draft_line = required.deduction_line_ids, draft.deduction_line_ids
    def frozen():
        initial_ids = set(required.deduction_line_ids.ids)
        for attempt in (
            lambda: lines.create({"claim_id": required.id, "item_name": "Forbidden",
                "deduction_category": "other", "amount": 1.0}),
            lambda: lines.with_context(default_claim_id=required.id).create({"item_name": "Forbidden",
                "deduction_category": "other", "amount": 1.0}),
            lambda: line.write({"amount": 101.0}),
            lambda: line.write({"claim_id": draft.id}),
            lambda: draft_line.write({"claim_id": required.id}),
            line.unlink,
        ):
            denied = False
            try:
                with env.cr.savepoint(): attempt()
            except UserError as exc:
                assert "明细不可" in str(exc), str(exc)
                denied = True
            assert denied, "reviewed deduction child changed"
        required.invalidate_recordset()
        line.invalidate_recordset()
        draft_line.invalidate_recordset()
        assert set(required.deduction_line_ids.ids) == initial_ids
        assert line.claim_id == required and line.amount == 100.0 and draft_line.claim_id == draft
    required.action_submit()
    assert required.state == "submit" and required.review_ids
    frozen()
    print("APPROVAL_CHECK=deduction_pending_child_crud_and_reparent_denied")
    users = required.review_ids.mapped("reviewer_ids").filtered(lambda user: user.active and not user.share)
    actor = next((required.with_user(user) for user in users if required.with_user(user).can_review), None)
    assert actor is not None
    actor.env["sc.approval.policy"]._reject_submission_review(actor, reason="deduction content correction")
    required.invalidate_recordset()
    assert required.state == "draft" and not required.review_ids
    line.write({"item_name": "Corrected after real rejection"})
    extra = lines.create({"claim_id": required.id, "item_name": "Temporary correction",
        "deduction_category": "other", "amount": 1.0})
    extra.unlink()
    assert line.item_name == "Corrected after real rejection" and not extra.exists()
    print("APPROVAL_CHECK=deduction_real_rejection_restores_child_editing")
    required.action_submit()
    _approve_existing_reviews(required)
    assert required.state == "approved" and required.validation_status == "validated"
    frozen()
    print("APPROVAL_CHECK=deduction_approved_child_crud_and_reparent_denied")


def validate_expense_create_probe(probe):
    request = probe.get("request", {})
    source = probe.get("source", {})
    assert request.get("op") == "create" and request.get("model") == "sc.expense.claim"
    vals, context = request.get("vals", {}), request.get("context", {})
    allowed_vals = {"business_category_id", "date_claim", "fill_date", "amount", "project_id", "partner_id",
                    "payment_request_id", "guarantee_type", "payee_account", "payer_account", "is_returned", "summary", "attachment_ids"}
    allowed_context = {"company_id", "default_claim_type", "default_expense_type", "default_summary",
                       "default_business_category_code", "search_default_active_rows", "search_default_expense_reimbursement",
                       "search_default_group_project", "allowed_business_category_codes", "allowed_company_ids", "lang", "menu_id", "action_id"}
    assert set(vals) <= allowed_vals and set(context) <= allowed_context
    assert source.get("type") == "pay" and source.get("id", 0) > 0
    assert vals.get("payment_request_id") == source["id"]
    assert vals.get("project_id") == source["project_id"][0] and vals.get("partner_id") == source["partner_id"][0]
    assert vals.get("amount") == source["amount"] and vals["amount"] > 0
    assert vals.get("attachment_ids") == [[6, 0, []]], "probe cannot mutate attachments"
    assert context.get("default_business_category_code") == "finance.expense.reimbursement"
    assert context.get("company_id") == source["company_id"][0]
    assert len(probe.get("report_sha256", "")) == 64
    return request


def _expense_create_request_checks():
    from odoo.addons.smart_core.handlers.api_data import ApiDataHandler
    base = _env()
    assert base.cr.dbname == "sc_frontend_acceptance", "acceptance database required"
    probe = json.loads(os.environ["SC_EXPENSE_CREATE_PROBE_JSON"])
    request = validate_expense_create_probe(probe)
    finance = base["res.users"].sudo().search([("login", "=", "fixture_role_finance"), ("active", "=", True)], limit=1)
    assert finance and finance.company_id.id == request["context"]["company_id"]
    assert set(request["context"]["allowed_company_ids"]) <= set(finance.company_ids.ids)
    user_env = base["sc.expense.claim"].with_user(finance).with_context(request["context"]).env
    assert not user_env.su
    menu = user_env.ref("smart_construction_core.menu_sc_reimbursement_request")
    assert int(request["context"]["menu_id"]) == menu.id and int(request["context"]["action_id"]) == menu.action.id
    category = user_env["sc.business.category"].browse(request["vals"]["business_category_id"])
    assert category.code == "finance.expense.reimbursement"
    source = user_env["payment.request"].browse(probe["source"]["id"])
    fields_to_read = list(probe["source"])
    # HTTP JSON represents Odoo many2one tuples as arrays. Compare at the same
    # serialization boundary, preserving every captured field and value.
    current_source = json.loads(json.dumps(source.read(fields_to_read)[0]))
    assert current_source == probe["source"], "source changed since browser capture: %s" % current_source
    source_fields = fields_to_read + ["terminal_cash_source_model", "terminal_cash_source_res_id"]
    before = source.read(source_fields)
    ledger_domain = [("payment_request_id", "=", source.id)]
    ledger_before = user_env["payment.ledger"].search(ledger_domain).ids
    created_id = None
    attachment_ids = []
    try:
        result = ApiDataHandler(user_env, context=request["context"]).handle(**request)
        assert isinstance(result, tuple), "create handler rejected browser payload: %s" % (result,)
        data = result[0]
        created_id = data.get("id")
        assert created_id, data
        rec = user_env["sc.expense.claim"].browse(created_id)
        assert rec.project_id == source.project_id and rec.partner_id == source.partner_id and rec.payment_request_id == source
        assert rec.company_id == finance.company_id and rec.amount == source.amount and rec.financial_flow == "cash_out"
        print("APPROVAL_CHECK=expense_browser_payload_created_with_finance_scope")
        assert category.attachment_policy == "required", "current captured case requires an attachment"
        contract_before = user_env["sc.workflow.contract.service"].describe_record(rec)
        attachment_gate = next(gate for gate in contract_before["evidenceGate"] if gate["reasonCode"] == "EXPENSE_ATTACHMENT_REQUIRED")
        denied = False
        try:
            with user_env.cr.savepoint():
                rec.action_submit()
        except UserError as exc:
            denied = True
            assert str(exc) == attachment_gate["message"], (str(exc), attachment_gate)
        assert denied and rec.state == "draft", "missing attachment must preserve draft"
        print("APPROVAL_CHECK=expense_browser_payload_missing_attachment_matches_contract")
        # Separate runtime completion from the captured browser payload: the
        # browser did not upload this rollback-only supporting attachment.
        _attach(rec, "expense-browser-payload-runtime-support")
        attachment_ids = rec.attachment_ids.ids
        rec.action_submit()
        assert rec.state in ("submit", "approved"), (rec.state, rec.validation_status)
        contract = user_env["sc.workflow.contract.service"].describe_record(rec)
        assert contract["editability"] in ("readonly", "locked"), contract
        assert source.read(source_fields) == before and user_env["payment.ledger"].search(ledger_domain).ids == ledger_before
        print("APPROVAL_CHECK=expense_browser_payload_submit_projects_readonly_without_payment")
        print("EXPENSE_CREATE_PROBE_IDENTITY=" + json.dumps({"report_sha256": probe["report_sha256"], "uid": finance.id,
              "company_id": finance.company_id.id, "source_id": source.id, "expense_id": created_id,
              "state": rec.state, "validation_status": rec.validation_status}))
    finally:
        base.cr.rollback()
        base.invalidate_all()
        assert not created_id or not user_env["sc.expense.claim"].browse(created_id).exists()
        assert not user_env["ir.attachment"].browse(attachment_ids).exists()
        assert source.read(source_fields) == before and user_env["payment.ledger"].search(ledger_domain).ids == ledger_before
        print("EXPENSE_CREATE_PROBE_ROLLBACK=VERIFIED")
    print("BUSINESS_CONFIG_APPROVAL_RUNTIME_SMOKE=PASS checks=3 scope=expense-create-request")


def main():
    scope = os.environ.get("SC_APPROVAL_RUNTIME_SCOPE", "all")
    if scope == "expense-create-request":
        return _expense_create_request_checks()
    assert scope in ("plan-state-authority", "contract-event-state-authority", "diary-state-authority", "settlement-adjustment", "receipt-income", "financing-borrowing", "financing-approval", "self-funding-reconciliation", "expense-state-authority", "finance-state-authority", "legacy-workflow", "red-flush-role", "red-flush", "tender-guarantee", "project-document", "tender-purchase", "project-role-approval", "project-creation-state", "all", "inbound", "acceptance", "purchase-request", "rfq", "material-settlement", "equipment-plan-request", "equipment-execution", "labor-plan-request", "labor-execution", "rental-plan", "rental-order", "rental-settlement", "rental-settlement-cash", "rental-cancellation-contract", "safety-approval", "subcontract-approval", "subcontract-settlement", "subcontract-settlement-cash"), "unsupported approval runtime scope"
    model_name = "sc.expense.claim"
    policy = _policy(model_name)
    fields = ["active", "approval_required", "mode", "runtime_state", "manager_group_id", "step_ids"]
    baseline = policy.read(fields)
    step_fields = ["active", "sequence", "approval_scope_key", "approve_group_id", "amount_min", "amount_max", "tier_definition_id"]
    step_baseline = policy.step_ids.read(step_fields)
    created = []
    legacy_parameter_baseline = env["ir.config_parameter"].sudo().search([("key", "=", "sc.workflow.legacy_runtime_enabled")]).read(["key", "value"]) if scope == "legacy-workflow" else None
    finance_policies = env["sc.approval.policy"].sudo().with_context(active_test=False).search([("target_model", "in", ["sc.expense.claim", "sc.settlement.adjustment", "sc.treasury.reconciliation", "sc.self.funding.registration", "sc.financing.loan", "sc.receipt.income"])]) if scope in ("expense-state-authority", "settlement-adjustment", "receipt-income", "finance-state-authority", "self-funding-reconciliation", "financing-approval", "financing-borrowing") else env["sc.approval.policy"]
    finance_baseline = finance_policies.read(fields)
    finance_steps = finance_policies.step_ids.read(step_fields)
    passed = False
    try:
        if scope not in ("settlement-adjustment", "receipt-income", "legacy-workflow", "finance-state-authority", "self-funding-reconciliation", "financing-approval", "financing-borrowing"):
            project = _project("Business Config Approval Runtime")
            partner = _partner("Business Config Approval Runtime Partner")
            created.extend([(project._name, project.id), (partner._name, partner.id)])

        if scope == "plan-state-authority":
            group = policy.manager_group_id or policy.step_ids[:1].approve_group_id
            assert group, "existing reviewer group required"
            _plan_state_authority_checks(project, group, created)
        elif scope == "contract-event-state-authority":
            group = policy.manager_group_id or policy.step_ids[:1].approve_group_id
            assert group, "existing reviewer group required"
            _contract_event_state_authority_checks(project, group, created)
        elif scope == "diary-state-authority":
            group = policy.manager_group_id or policy.step_ids[:1].approve_group_id
            assert group, "existing reviewer group required"
            _diary_state_authority_checks(project, group, created)
        elif scope == "settlement-adjustment":
            group = policy.manager_group_id or policy.step_ids[:1].approve_group_id
            assert group, "existing reviewer group required"
            _finance_state_authority_checks(group, created, adjustment_only=True)
        elif scope == "receipt-income":
            group = policy.manager_group_id or policy.step_ids[:1].approve_group_id
            assert group, "existing reviewer group required"
            _receipt_income_checks(group, created)
        elif scope in ("financing-approval", "financing-borrowing"):
            group = policy.manager_group_id or policy.step_ids[:1].approve_group_id
            assert group, "existing reviewer group required"
            _financing_approval_checks(group, created)
        elif scope == "self-funding-reconciliation":
            group = policy.manager_group_id or policy.step_ids[:1].approve_group_id
            assert group, "existing reviewer group required"
            _self_funding_reconciliation_checks(group, created)
        elif scope == "finance-state-authority":
            group = policy.manager_group_id or policy.step_ids[:1].approve_group_id
            assert group, "existing reviewer group required"
            _finance_state_authority_checks(group, created)
        elif scope == "legacy-workflow":
            _legacy_workflow_boundary_checks()
        elif scope == "red-flush-role":
            group = policy.manager_group_id or policy.step_ids[:1].approve_group_id
            assert group, "existing reviewer group required"
            _red_flush_role_checks(project, group, created)
        elif scope == "red-flush":
            group = policy.manager_group_id or policy.step_ids[:1].approve_group_id
            assert group, "existing reviewer group required"
            _red_flush_approval_checks(project, group, created)
        elif scope == "tender-guarantee":
            group = policy.manager_group_id or policy.step_ids[:1].approve_group_id
            assert group, "existing reviewer group required"
            _tender_guarantee_approval_checks(project, group, created)
        elif scope == "project-document":
            group = policy.manager_group_id or policy.step_ids[:1].approve_group_id
            assert group, "existing reviewer group required"
            _project_document_approval_checks(project, group, created)
        elif scope == "tender-purchase":
            group = policy.manager_group_id or policy.step_ids[:1].approve_group_id
            assert group, "existing reviewer group required"
            _tender_purchase_approval_checks(project, group, created)
        elif scope == "project-role-approval":
            group = policy.manager_group_id or policy.step_ids[:1].approve_group_id
            assert group, "existing reviewer group required"
            _project_role_approval_checks(project, group, created)
        elif scope == "project-creation-state":
            _project_creation_state_checks(project, None, created)
        elif scope in ("inbound", "acceptance", "purchase-request", "rfq", "material-settlement", "equipment-plan-request", "equipment-execution", "labor-plan-request", "labor-execution", "rental-plan", "rental-order", "rental-settlement", "rental-settlement-cash", "rental-cancellation-contract", "safety-approval", "subcontract-approval", "subcontract-settlement", "subcontract-settlement-cash"):
            group = policy.manager_group_id or policy.step_ids[:1].approve_group_id
            assert group, "existing reviewer group required"
            checks = {"inbound": _inbound_approval_checks, "acceptance": _acceptance_approval_checks, "purchase-request": _purchase_request_approval_checks, "rfq": _rfq_approval_checks, "material-settlement": _material_settlement_approval_checks, "equipment-plan-request": _equipment_plan_request_checks, "equipment-execution": _equipment_execution_checks, "labor-plan-request": _labor_plan_request_checks, "labor-execution": _labor_execution_checks, "rental-plan": _rental_plan_checks, "rental-order": _rental_order_checks, "rental-settlement": _rental_settlement_checks, "rental-settlement-cash": _rental_settlement_cash_checks, "rental-cancellation-contract": _rental_settlement_cash_checks, "safety-approval": _safety_approval_checks, "subcontract-approval": _subcontract_approval_checks, "subcontract-settlement": _subcontract_settlement_approval_checks, "subcontract-settlement-cash": _subcontract_settlement_cash_checks}[scope]
            checks(project, group, created)
        else:
            _set_policy(model_name, True)
            required = _expense(project, partner, "required")
            created.append((required._name, required.id))
            if scope == "expense-state-authority":
                for attempt in (
                    lambda: required.write({"state": "approved"}),
                    lambda: required.with_context(sc_expense_fact_authority_token=True).write({"state": "approved"}),
                    lambda: _env()[model_name].sudo().create({"state": "approved"}),
                    lambda: _env()[model_name].sudo().with_context(default_state="approved").create({}),
                ):
                    denied = False
                    try:
                        with _env().cr.savepoint():
                            attempt()
                    except UserError:
                        denied = True
                    assert denied, "expense approval state bypassed"
                print("APPROVAL_CHECK=expense_external_approval_state_denied")
            required.action_submit()
            required.invalidate_recordset()
            assert required.state == "submit", required.state
            assert required.review_ids and required.validation_status in ("pending", "waiting"), required.validation_status
            print("APPROVAL_CHECK=enabled_submission_has_real_reviews")
            if scope == "expense-state-authority":
                for values in ({"amount": 101.0}, {"approved_amount": 101.0},
                               {"payee_account": "CHANGED"}, {"attachment_ids": [(5, 0, 0)]},
                               {"deduction_line_ids": [(5, 0, 0)]}, {"active": False}):
                    denied = False
                    try:
                        with _env().cr.savepoint():
                            required.with_context(sc_expense_fact_authority_token=True).write(values)
                    except UserError as exc:
                        assert "审核内容" in str(exc), str(exc)
                        denied = True
                    assert denied, "reviewed expense content changed: %s" % values
                required.write({"note": "Reviewed content protection smoke"})
                required.invalidate_recordset()
                assert required.amount == 100.0 and required.approved_amount == 100.0
                assert required.attachment_ids and required.active
                print("APPROVAL_CHECK=expense_pending_content_frozen_notes_preserved")


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
            if scope == "expense-state-authority":
                for values in ({"amount": 101.0}, {"approved_amount": 101.0},
                               {"payee_account": "CHANGED"}, {"attachment_ids": [(5, 0, 0)]},
                               {"deduction_line_ids": [(5, 0, 0)]}, {"active": False}):
                    denied = False
                    try:
                        with _env().cr.savepoint():
                            required.with_context(sc_expense_fact_authority_token=True).write(values)
                    except UserError as exc:
                        assert "审核内容" in str(exc), str(exc)
                        denied = True
                    assert denied, "reviewed expense content changed: %s" % values
                required.write({"note": "Reviewed content protection smoke"})
                required.invalidate_recordset()
                assert required.amount == 100.0 and required.approved_amount == 100.0
                assert required.attachment_ids and required.active
                print("APPROVAL_CHECK=expense_approved_content_frozen_notes_preserved")


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
            if scope == "expense-state-authority":
                _expense_deduction_line_checks(project, partner, created)
                _expense_readiness_checks(project, partner, created)
                _expense_finance_execution_checks(group, created)
                _expense_cash_execution_checks(created)
            if scope == "all":
                _contract_event_checks(project, group, created)
                _draft_confirmation_checks(project, group, created, "sc.plan")
                _draft_confirmation_checks(project, group, created, "sc.construction.diary")
                _tax_approval_checks(project, group, created)
                _task_approval_checks(project, group, created)
                _project_document_approval_checks(project, group, created)
                _tender_purchase_approval_checks(project, group, created)
                _tender_guarantee_approval_checks(project, group, created)
                _red_flush_approval_checks(project, group, created)
                _project_creation_state_checks(project, group, created)
                _project_approval_checks(group, created)
                _inbound_approval_checks(project, group, created)
                _acceptance_approval_checks(project, group, created)
                _purchase_request_approval_checks(project, group, created)
                _rfq_approval_checks(project, group, created)
                _material_settlement_approval_checks(project, group, created)
                _equipment_plan_request_checks(project, group, created)
                _equipment_execution_checks(project, group, created)
                _labor_plan_request_checks(project, group, created)
                _labor_execution_checks(project, group, created)
                _rental_plan_checks(project, group, created)
                _rental_order_checks(project, group, created)
                _rental_settlement_checks(project, group, created)
                _rental_settlement_cash_checks(project, group, created)
                _safety_approval_checks(project, group, created)
                _subcontract_approval_checks(project, group, created)
                _subcontract_settlement_approval_checks(project, group, created)
                _subcontract_settlement_cash_checks(project, group, created)
        passed = True
    finally:
        _env().cr.rollback()
        _env().invalidate_all()
        if legacy_parameter_baseline is not None:
            assert env["ir.config_parameter"].sudo().search([("key", "=", "sc.workflow.legacy_runtime_enabled")]).read(["key", "value"]) == legacy_parameter_baseline, "legacy runtime parameter not restored"
        assert finance_policies.read(fields) == finance_baseline, "finance policies not restored"
        assert finance_policies.step_ids.read(step_fields) == finance_steps, "finance steps not restored"
        assert policy.read(fields) == baseline, "approval configuration was not restored"
        assert policy.step_ids.read(step_fields) == step_baseline, "approval steps were not restored"
        assert all(not _env()[model].sudo().browse(record_id).exists() for model, record_id in created), "temporary document remains"
        print("BUSINESS_CONFIG_APPROVAL_RUNTIME_ROLLBACK=VERIFIED")
    if passed:
        print("BUSINESS_CONFIG_APPROVAL_RUNTIME_SMOKE=PASS checks=%s scope=%s" % (12 if scope in ("diary-state-authority", "contract-event-state-authority") else 15 if scope == "plan-state-authority" else 8 if scope == "settlement-adjustment" else 6 if scope == "receipt-income" else 6 if scope == "financing-borrowing" else 9 if scope == "financing-approval" else 13 if scope == "self-funding-reconciliation" else 27 if scope == "expense-state-authority" else 8 if scope == "finance-state-authority" else 5 if scope == "legacy-workflow" else 16 if scope == "red-flush-role" else 15 if scope == "red-flush" else 10 if scope == "tender-guarantee" else 8 if scope in ("project-document", "tender-purchase") else 6 if scope == "project-role-approval" else 5 if scope == "project-creation-state" else 10 if scope == "subcontract-settlement-cash" else 8 if scope == "subcontract-settlement" else 16 if scope in ("safety-approval", "subcontract-approval") else 6 if scope == "rental-cancellation-contract" else 10 if scope == "rental-settlement-cash" else 12 if scope == "rental-settlement" else 13 if scope == "rental-order" else 10 if scope == "rental-plan" else 25 if scope == "labor-execution" else 16 if scope == "labor-plan-request" else 14 if scope in ("equipment-plan-request", "equipment-execution", "labor-plan-request", "labor-execution", "rental-plan", "rental-order", "rental-settlement", "rental-settlement-cash", "rental-cancellation-contract", "safety-approval", "subcontract-approval", "subcontract-settlement", "subcontract-settlement-cash") else 8 if scope in ("inbound", "acceptance", "purchase-request", "rfq", "material-settlement", "equipment-plan-request", "equipment-execution", "labor-plan-request", "labor-execution", "rental-plan", "rental-order", "rental-settlement", "rental-settlement-cash", "rental-cancellation-contract", "safety-approval", "subcontract-approval", "subcontract-settlement", "subcontract-settlement-cash") else 308, scope))


main()
