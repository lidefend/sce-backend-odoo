# -*- coding: utf-8 -*-
from __future__ import annotations

import logging

from odoo import api, models
from odoo.addons.smart_construction_core.models.support import operating_metrics as opm
from odoo.tools.float_utils import float_compare

from odoo.addons.smart_construction_core.services.workflow_contract_profile_registry import (
    external_workflow_contract_profiles,
)

_logger = logging.getLogger(__name__)


def _simple_approval_profiles(model_names):
    """共享档案: 草稿 -> 已提交 -> 已确认/已取消.
    `submit`/`rejected` were unreachable, and `reopen` belongs to 已取消.
    See `test_the_shared_approval_family_declares_only_reachable_states`.
    """
    profile = {
        "state_field": "state",
        "state_phase": {
            "draft": "draft",
            "submitted": "under_review",
            "approved": "approved",
            "cancel": "cancelled",
        },
        "state_actions": {
            "draft": ["submit", "cancel"],
            "submitted": ["approve", "cancel"],
            "cancel": ["reopen"],
        },
        "method_by_action": {
            "submit": "action_submit",
            "approve": "action_approve",
            "reopen": "action_reset_draft",
            "cancel": "action_cancel",
        },
    }
    return {name: dict(profile) for name in model_names}


def _simple_close_issue_profiles(model_names):
    profile = {
        "state_field": "state",
        "state_phase": {
            "draft": "draft",
            "submitted": "submitted",
            "rectifying": "open",
            "rechecking": "under_review",
            "closed": "closed",
            "cancel": "cancelled",
        },
        "state_actions": {
            "draft": ["submit", "cancel"],
            "submitted": ["complete", "cancel"],
            "rectifying": ["complete", "cancel"],
            "rechecking": ["complete", "cancel"],
        },
        "method_by_action": {
            "submit": "action_submit",
            "complete": "action_close",
            "cancel": "action_cancel",
        },
    }
    return {name: dict(profile) for name in model_names}


def _submit_confirm_profiles(model_names):
    profile = {
        "state_field": "state",
        "state_phase": {
            "draft": "draft",
            "submitted": "submitted",
            "confirmed": "approved",
            "cancel": "cancelled",
        },
        "state_actions": {
            "draft": ["submit", "cancel"],
            "submitted": ["complete", "cancel"],
            "cancel": ["reopen"],
        },
        "method_by_action": {
            "submit": "action_submit",
            "complete": "action_confirm",
            "reopen": "action_reset_draft",
            "cancel": "action_cancel",
        },
        "label_by_action": {
            "complete": "确认",
            "reopen": "退回草稿",
        },
    }
    return {name: dict(profile) for name in model_names}


def _in_progress_done_profiles(model_names):
    profile = {
        "state_field": "state",
        "state_phase": {
            "draft": "draft",
            "in_progress": "open",
            "done": "done",
            "cancel": "cancelled",
        },
        "state_actions": {
            "draft": ["submit", "complete", "cancel"],
            "in_progress": ["complete", "reopen", "cancel"],
            "cancel": ["reopen"],
        },
        "method_by_action": {
            "submit": "action_submit",
            "complete": "action_done",
            "reopen": "action_reset_draft",
            "cancel": "action_cancel",
        },
    }
    return {name: dict(profile) for name in model_names}


def _confirm_done_profiles(model_names):
    profile = {
        "state_field": "state",
        "state_phase": {
            "draft": "draft",
            "confirmed": "approved",
            "in_progress": "open",
            "done": "done",
            "cancel": "cancelled",
            "cancelled": "cancelled",
            "legacy_confirmed": "legacy_confirmed",
        },
        "state_actions": {
            "draft": ["submit", "complete", "cancel"],
            "confirmed": ["complete", "reopen", "cancel"],
            "in_progress": ["complete", "reopen", "cancel"],
            "cancel": ["reopen"],
            "cancelled": ["reopen"],
        },
        "method_by_action": {
            "submit": "action_confirm",
            "complete": "action_done",
            "reopen": "action_reset_draft",
            "cancel": "action_cancel",
        },
        "label_by_action": {
            "submit": "确认",
        },
    }
    return {name: dict(profile) for name in model_names}


class ScWorkflowContractService(models.AbstractModel):
    _name = "sc.workflow.contract.service"
    _description = "施工业务表单状态与审批流统一投影服务"

    SOURCE_KIND = "sc_backend_workflow_contract"
    SOURCE_AUTHORITIES = (
        "odoo_model_state",
        "base_tier_validation",
        "sc.approval.policy",
        "business_model_methods",
    )

    PROFILE_BY_MODEL = {
        "payment.request": {
            "state_field": "state",
            "editable_phases": ["draft", "rejected"],
            "state_phase": {
                "draft": "draft",
                "submit": "under_review",
                "approve": "under_review",
                "approved": "approved",
                "rejected": "rejected",
                "done": "done",
                "cancel": "cancelled",
            },
            "state_actions": {
                "draft": ["save_draft", "submit", "cancel"],
                "submit": ["approve", "reject", "cancel"],
                "approve": ["approve", "reject", "cancel"],
                "approved": ["complete", "cancel"],
                "rejected": ["submit", "cancel"],
            },
            "method_by_action": {
                "submit": "action_submit",
                "approve": "action_approval_decision",
                "reject": "reject_tier",
                "complete": "action_done",
                "cancel": "action_cancel",
            },
        },
        "sc.settlement.order": {
            "state_field": "state",
            "state_phase": {
                "draft": "draft",
                "submit": "under_review",
                "approve": "approved",
                "done": "done",
                "cancel": "cancelled",
            },
            "state_actions": {
                "draft": ["save_draft", "submit", "cancel"],
                "submit": ["approve", "reject", "cancel"],
                "approve": ["complete", "cancel"],
            },
            "method_by_action": {
                "submit": "action_submit",
                "approve": "validate_tier",
                "reject": "reject_tier",
                "complete": "action_done",
                "cancel": "action_cancel",
            },
        },
        "sc.expense.claim": {
            "submission_requirements": [{
                "kind": "relation_required",
                "field": "attachment_ids",
                "requiredWhen": {"field": "submission_attachment_policy", "equals": "required"},
                "pendingSource": "native_attachment",
                "reasonCode": "EXPENSE_ATTACHMENT_REQUIRED",
                "message": "当前业务分类要求上传附件后才能提交、批准或完成。",
            }],
            "state_field": "state",
            "state_phase": {
                "draft": "draft",
                "submit": "under_review",
                "approved": "approved",
                "done": "done",
                "legacy_confirmed": "legacy_confirmed",
                "cancel": "cancelled",
            },
            "state_actions": {
                "draft": ["save_draft", "submit", "cancel"],
                "submit": ["approve", "reject", "cancel"],
                "approved": ["complete", "cancel"],
            },
            "method_by_action": {
                "submit": "action_submit",
                "approve": "validate_tier",
                "reject": "reject_tier",
                "complete": "action_done",
                "cancel": "action_cancel",
            },
        },
        "construction.contract": {
            "state_field": "state",
            "state_phase": {
                "draft": "draft",
                "confirmed": "approved",
                "running": "effective",
                "closed": "done",
                "cancel": "cancelled",
            },
            "state_actions": {
                "draft": ["submit", "cancel"],
                "confirmed": ["activate", "complete", "cancel"],
                "running": ["complete", "cancel"],
                "cancel": ["reopen"],
            },
            "approval_actions": ["approve", "reject"],
            "method_by_action": {
                "submit": "action_confirm",
                "approve": "validate_tier",
                "reject": "reject_tier",
                "activate": "action_set_running",
                "complete": "action_close",
                "cancel": "action_cancel",
                "reopen": "action_reset_draft",
            },
        },
        "construction.contract.expense": {
            "state_field": "state",
            "state_phase": {
                "draft": "draft",
                "confirmed": "approved",
                "running": "effective",
                "closed": "done",
                "cancel": "cancelled",
            },
            "state_actions": {
                "draft": ["submit", "cancel"],
                "confirmed": ["activate", "complete", "cancel"],
                "running": ["complete", "cancel"],
                "cancel": ["reopen"],
            },
            "approval_actions": ["approve", "reject"],
            "method_by_action": {
                "submit": "action_confirm",
                "approve": "validate_tier",
                "reject": "reject_tier",
                "activate": "action_set_running",
                "complete": "action_close",
                "cancel": "action_cancel",
                "reopen": "action_reset_draft",
            },
        },
        "construction.contract.income": {
            "state_field": "state",
            "state_phase": {
                "draft": "draft",
                "confirmed": "approved",
                "running": "effective",
                "closed": "done",
                "cancel": "cancelled",
            },
            "state_actions": {
                "draft": ["submit", "cancel"],
                "confirmed": ["activate", "complete", "cancel"],
                "running": ["complete", "cancel"],
                "cancel": ["reopen"],
            },
            "approval_actions": ["approve", "reject"],
            "method_by_action": {
                "submit": "action_confirm",
                "approve": "validate_tier",
                "reject": "reject_tier",
                "activate": "action_set_running",
                "complete": "action_close",
                "cancel": "action_cancel",
                "reopen": "action_reset_draft",
            },
        },
        "sc.payment.execution": {
            "state_field": "state",
            # A paid execution is terminal for its payment lifecycle, but the
            # finance manager must still be able to enter the reversal reason.
            # Native modifiers and the form policy remain the field-level
            # authority; this only prevents the workflow summary from locking
            # the entire page before those constraints are evaluated.
            "field_editable_phases": ["done"],
            "state_phase": {
                "draft": "draft",
                "confirmed": "approved",
                "paid": "done",
                "legacy_confirmed": "legacy_confirmed",
                "cancel": "cancelled",
            },
            "state_actions": {
                "draft": ["submit", "cancel"],
                "confirmed": ["complete", "cancel"],
                "paid": ["reverse_payment"],
            },
            "approval_actions": ["approve", "reject"],
            "method_by_action": {
                "submit": "action_confirm",
                "approve": "validate_tier",
                "reject": "reject_tier",
                "complete": "action_paid",
                "cancel": "action_cancel",
                "reverse_payment": "action_reverse_payment",
            },
            "label_by_action": {
                "complete": "已付款",
            },
        },
        "sc.receipt.income": {
            "state_field": "state",
            "state_phase": {
                "draft": "draft",
                "confirmed": "approved",
                "received": "done",
                "legacy_confirmed": "legacy_confirmed",
                "cancel": "cancelled",
            },
            "state_actions": {
                "draft": ["submit", "cancel"],
                "confirmed": ["complete", "cancel"],
            },
            "approval_actions": ["approve", "reject"],
            "method_by_action": {
                "submit": "action_confirm",
                "approve": "validate_tier",
                "reject": "reject_tier",
                "complete": "action_received",
                "cancel": "action_cancel",
            },
            "label_by_action": {
                "complete": "已收款",
            },
        },
        "sc.invoice.registration": {
            "state_field": "state",
            "state_phase": {
                "draft": "draft",
                "confirmed": "approved",
                "registered": "done",
                "legacy_confirmed": "legacy_confirmed",
                "cancel": "cancelled",
            },
            "state_actions": {
                "draft": ["submit", "complete", "cancel"],
                "confirmed": ["complete", "cancel"],
            },
            "approval_actions": ["approve", "reject"],
            "method_by_action": {
                "submit": "action_confirm",
                "approve": "validate_tier",
                "reject": "reject_tier",
                "complete": "action_register",
                "cancel": "action_cancel",
            },
            "label_by_action": {
                "complete": "已登记",
            },
        },
        "sc.self.funding.registration": {
            "state_field": "state",
            "state_phase": {
                "draft": "draft",
                "confirmed": "approved",
                "done": "done",
                "cancel": "cancelled",
            },
            "state_actions": {
                "draft": ["submit", "cancel"],
                "confirmed": ["complete", "cancel"],
            },
            "approval_actions": ["approve", "reject"],
            "method_by_action": {
                "submit": "action_confirm",
                "approve": "validate_tier",
                "reject": "reject_tier",
                "complete": "action_done",
                "cancel": "action_cancel",
            },
        },
        "sc.financing.loan": {
            "state_field": "state",
            "state_phase": {
                "draft": "draft",
                "confirmed": "approved",
                "done": "done",
                "legacy_confirmed": "legacy_confirmed",
                "cancel": "cancelled",
            },
            "state_actions": {
                "draft": ["submit", "cancel"],
                "confirmed": ["complete", "cancel"],
            },
            "approval_actions": ["approve", "reject"],
            "method_by_action": {
                "submit": "action_confirm",
                "approve": "validate_tier",
                "reject": "reject_tier",
                "complete": "action_done",
                "cancel": "action_cancel",
            },
        },
        "sc.treasury.reconciliation": {
            "state_field": "state",
            "state_phase": {
                "draft": "draft",
                "confirmed": "approved",
                "reconciled": "done",
                "legacy_confirmed": "legacy_confirmed",
                "cancel": "cancelled",
            },
            "state_actions": {
                "draft": ["submit", "cancel"],
                "confirmed": ["complete", "cancel"],
            },
            "approval_actions": ["approve", "reject"],
            "method_by_action": {
                "submit": "action_confirm",
                "approve": "validate_tier",
                "reject": "reject_tier",
                "complete": "action_reconcile",
                "cancel": "action_cancel",
            },
            "label_by_action": {
                "complete": "对账完成",
            },
        },
        "sc.general.contract": {
            "state_field": "state",
            "state_phase": {
                "draft": "draft",
                "confirmed": "approved",
                "signed": "effective",
                "legacy_confirmed": "legacy_confirmed",
                "cancel": "cancelled",
            },
            "state_actions": {
                "draft": ["submit", "complete", "cancel"],
                "confirmed": ["complete", "cancel"],
                # `action_cancel` refuses anything past `confirmed`, and
                # `test_p0_state_closure.test_general_contract_blocks_invalid_anchor_or_terminal_cancel`
                # locks that refusal as a terminal-state violation. Declaring
                # `cancel` here published a button whose only outcome was a
                # UserError, so a signed contract declares no transition at all.
                "signed": [],
            },
            "approval_actions": ["approve", "reject"],
            "method_by_action": {
                "submit": "action_confirm",
                "approve": "validate_tier",
                "reject": "reject_tier",
                "complete": "action_signed",
                "cancel": "action_cancel",
            },
            "label_by_action": {"complete": "已签署"},
        },
        "sc.settlement.adjustment": {
            "state_field": "state",
            "state_phase": {
                "draft": "draft",
                "confirmed": "approved",
                "legacy_confirmed": "legacy_confirmed",
                "cancel": "cancelled",
            },
            "state_actions": {
                "draft": ["submit"],
                "confirmed": ["cancel"],
            },
            "approval_actions": ["approve", "reject"],
            "method_by_action": {
                "submit": "action_confirm",
                "approve": "validate_tier",
                "reject": "reject_tier",
                "cancel": "action_cancel",
            },
        },
        "sc.subcontract.plan": {
            "state_field": "state",
            "state_phase": {"draft": "draft", "submitted": "under_review", "approved": "approved", "cancel": "cancelled"},
            "state_actions": {"draft": ["submit", "cancel"], "submitted": ["submit", "cancel"], "cancel": ["reopen"]},
            "action_domains": {"submit": [("validation_status", "not in", ["waiting", "pending", "validated"])]},
            "approval_actions": ["approve", "reject"],
            "method_by_action": {"submit": "action_submit", "approve": "validate_tier", "reject": "reject_tier", "cancel": "action_cancel", "reopen": "action_reset_draft"},
        },
        "sc.subcontract.request": {
            "state_field": "state",
            "state_phase": {"draft": "draft", "submitted": "under_review", "approved": "approved", "cancel": "cancelled"},
            "state_actions": {"draft": ["submit", "cancel"], "submitted": ["submit", "cancel"], "cancel": ["reopen"]},
            "action_domains": {"submit": [("validation_status", "not in", ["waiting", "pending", "validated"])]},
            "approval_actions": ["approve", "reject"],
            "method_by_action": {"submit": "action_submit", "approve": "validate_tier", "reject": "reject_tier", "cancel": "action_cancel", "reopen": "action_reset_draft"},
        },
        "sc.safety.plan": {
            "state_field": "state",
            "state_phase": {"draft": "draft", "submitted": "under_review", "approved": "approved", "cancel": "cancelled"},
            "state_actions": {"draft": ["submit", "cancel"], "submitted": ["submit", "cancel"], "cancel": ["reopen"]},
            "action_domains": {"submit": [("validation_status", "not in", ["waiting", "pending", "validated"])]},
            "approval_actions": ["approve", "reject"],
            "method_by_action": {"submit": "action_submit", "approve": "validate_tier", "reject": "reject_tier", "cancel": "action_cancel", "reopen": "action_reset_draft"},
        },
        "sc.safety.disclosure": {
            "state_field": "state",
            "state_phase": {"draft": "draft", "submitted": "under_review", "approved": "approved", "cancel": "cancelled"},
            "state_actions": {"draft": ["submit", "cancel"], "submitted": ["submit", "cancel"], "cancel": ["reopen"]},
            "action_domains": {"submit": [("validation_status", "not in", ["waiting", "pending", "validated"])]},
            "approval_actions": ["approve", "reject"],
            "method_by_action": {"submit": "action_submit", "approve": "validate_tier", "reject": "reject_tier", "cancel": "action_cancel", "reopen": "action_reset_draft"},
        },
        "sc.material.purchase.request": {
            "state_field": "state",
            "state_phase": {"draft": "draft", "submitted": "under_review", "approved": "approved", "cancel": "cancelled"},
            "state_actions": {"draft": ["submit", "cancel"], "submitted": ["submit", "cancel"], "cancel": ["reopen"]},
            "action_domains": {"submit": [("validation_status", "not in", ["waiting", "pending", "validated"])]},
            "approval_actions": ["approve", "reject"],
            "method_by_action": {"submit": "action_submit", "approve": "validate_tier", "reject": "reject_tier", "cancel": "action_cancel", "reopen": "action_reset_draft"},
        },
        "sc.equipment.plan": {
            "state_field": "state",
            "state_phase": {"draft": "draft", "submitted": "under_review", "approved": "approved", "cancel": "cancelled"},
            "state_actions": {"draft": ["submit", "cancel"], "submitted": ["submit", "cancel"], "cancel": ["reopen"]},
            "action_domains": {"submit": [("validation_status", "not in", ["waiting", "pending", "validated"])]},
            "approval_actions": ["approve", "reject"],
            "method_by_action": {"submit": "action_submit", "approve": "validate_tier", "reject": "reject_tier", "cancel": "action_cancel", "reopen": "action_reset_draft"},
        },
        "sc.equipment.request": {
            "state_field": "state",
            "state_phase": {"draft": "draft", "submitted": "under_review", "approved": "approved", "cancel": "cancelled"},
            "state_actions": {"draft": ["submit", "cancel"], "submitted": ["submit", "cancel"], "cancel": ["reopen"]},
            "action_domains": {"submit": [("validation_status", "not in", ["waiting", "pending", "validated"])]},
            "approval_actions": ["approve", "reject"],
            "method_by_action": {"submit": "action_submit", "approve": "validate_tier", "reject": "reject_tier", "cancel": "action_cancel", "reopen": "action_reset_draft"},
        },
        "sc.labor.plan": {
            "state_field": "state",
            "state_phase": {"draft": "draft", "submitted": "under_review", "approved": "approved", "cancel": "cancelled"},
            "state_actions": {"draft": ["submit", "cancel"], "submitted": ["submit", "cancel"], "cancel": ["reopen"]},
            "action_domains": {"submit": [("validation_status", "not in", ["waiting", "pending", "validated"])]},
            "approval_actions": ["approve", "reject"],
            "method_by_action": {"submit": "action_submit", "approve": "validate_tier", "reject": "reject_tier", "cancel": "action_cancel", "reopen": "action_reset_draft"},
        },
        "sc.material.rental.plan": {
            "state_field": "state",
            "state_phase": {"draft": "draft", "submitted": "under_review", "approved": "approved", "cancel": "cancelled"},
            "state_actions": {"draft": ["submit", "cancel"], "submitted": ["submit", "cancel"], "cancel": ["reopen"]},
            "action_domains": {"submit": [("validation_status", "not in", ["waiting", "pending", "validated"])]},
            "approval_actions": ["approve", "reject"],
            "method_by_action": {"submit": "action_submit", "approve": "validate_tier", "reject": "reject_tier", "cancel": "action_cancel", "reopen": "action_reset_draft"},
        },
        "sc.labor.request": {
            "state_field": "state",
            "state_phase": {"draft": "draft", "submitted": "under_review", "approved": "approved", "cancel": "cancelled"},
            "state_actions": {"draft": ["submit", "cancel"], "submitted": ["submit", "cancel"], "cancel": ["reopen"]},
            "action_domains": {"submit": [("validation_status", "not in", ["waiting", "pending", "validated"])]},
            "approval_actions": ["approve", "reject"],
            "method_by_action": {"submit": "action_submit", "approve": "validate_tier", "reject": "reject_tier", "cancel": "action_cancel", "reopen": "action_reset_draft"},
        },
        "project.material.plan": {
            "state_field": "state",
            "state_phase": {
                "draft": "draft",
                "submit": "under_review",
                "approved": "approved",
                "done": "done",
                "cancel": "cancelled",
            },
            "state_actions": {
                "draft": ["submit", "cancel"],
                "submit": ["approve", "reject", "cancel"],
                "approved": ["complete", "cancel"],
            },
            "approval_actions": ["approve", "reject"],
            "method_by_action": {
                "submit": "action_submit",
                "approve": "validate_tier",
                "reject": "reject_tier",
                "complete": "action_done",
                "cancel": "action_cancel",
            },
        },
        **_simple_close_issue_profiles((
            "sc.quality.issue",
            "sc.safety.issue",
        )),
        "sc.subcontract.settlement": {
            "state_field": "state",
            "state_phase": {"draft": "draft", "submitted": "under_review", "approved": "approved", "confirmed": "done", "cancel": "cancelled"},
            "state_actions": {"draft": ["submit", "cancel"], "submitted": ["submit", "cancel"], "approved": ["confirm_settlement", "cancel"], "cancel": ["reopen"]},
            "action_domains": {"submit": [("validation_status", "not in", ["waiting", "pending", "validated"])]},
            "approval_actions": ["approve", "reject"],
            "method_by_action": {"confirm_settlement": "action_confirm", "submit": "action_submit", "approve": "validate_tier", "reject": "reject_tier", "cancel": "action_cancel", "reopen": "action_reset_draft"},
        },
        **_in_progress_done_profiles((
            "sc.dashboard.cockpit.fact",
            "sc.document.admin.document",
            "sc.hr.payroll.document",
            "sc.office.admin.document",
            "sc.workbench.item",
        )),
        **_confirm_done_profiles((
            "sc.fund.account.operation",
        )),
        "sc.plan.version": {
            "state_field": "state",
            "state_phase": {"draft": "draft", "approved": "approved"},
            "state_actions": {"draft": ["submit"]},
            "action_domains": {"submit": [("validation_status", "not in", ["waiting", "pending", "validated"])]},
            "approval_actions": ["approve", "reject"],
            "method_by_action": {"submit": "action_submit", "approve": "validate_tier", "reject": "reject_tier"},
        },
        "sc.plan.report": {
            "state_field": "state",
            "editable_phases": ["draft", "rejected"],
            "state_phase": {"draft": "draft", "submitted": "under_review", "accepted": "approved", "rejected": "rejected"},
            "state_actions": {"draft": ["submit"], "rejected": ["submit"]},
            "approval_actions": ["approve", "reject"],
            "method_by_action": {"submit": "action_submit", "approve": "validate_tier", "reject": "reject_tier"},
        },
        "sc.plan": {
            "state_field": "state",
            "field_editable_phases": ["open"],
            "state_phase": {
                "draft": "draft", "confirmed": "approved", "in_progress": "open",
                "done": "done", "cancel": "cancelled",
            },
            "state_actions": {
                "draft": ["submit", "cancel"],
                "confirmed": ["activate", "cancel"],
                "in_progress": ["complete", "cancel"],
                "cancel": ["reopen"],
            },
            "approval_actions": ["approve", "reject"],
            "method_by_action": {
                "approve": "validate_tier", "reject": "reject_tier",
                "submit": "action_confirm", "activate": "action_start",
                "complete": "action_done", "cancel": "action_cancel",
                "reopen": "action_reset_draft",
            },
            "label_by_action": {"submit": "确认"},
        },
        "sc.construction.diary": {
            "state_field": "state",
            "state_phase": {
                "draft": "draft",
                "confirmed": "approved",
                "done": "done",
                "legacy_confirmed": "legacy_confirmed",
                "cancel": "cancelled",
            },
            "state_actions": {
                "draft": ["submit", "cancel"],
                "confirmed": ["complete", "cancel"],
            },
            "approval_actions": ["approve", "reject"],
            "method_by_action": {
                "approve": "validate_tier", "reject": "reject_tier",
                "submit": "action_confirm",
                "complete": "action_done",
                "cancel": "action_cancel",
            },
            "label_by_action": {
                "submit": "确认",
            },
        },
        "sc.contract.event": {
            "state_field": "state",
            "editable_phases": ["draft", "rejected"],
            "state_phase": {
                "draft": "draft",
                "submitted": "under_review",
                "approved": "approved",
                "rejected": "rejected",
                "done": "done",
                "cancel": "cancelled",
            },
            "state_actions": {
                "draft": ["submit", "cancel"],
                "submitted": ["cancel"],
                "approved": ["complete"],
                "rejected": ["submit", "cancel"],
            },
            "approval_actions": ["approve", "reject"],
            "method_by_action": {
                "submit": "action_submit",
                "approve": "validate_tier",
                "reject": "reject_tier",
                "complete": "action_done",
                "cancel": "action_cancel",
            },
        },
        "project.project": {
            "state_field": "lifecycle_state",
            "state_phase": {"draft": "draft", "in_progress": "effective", "paused": "paused", "done": "done", "closing": "closing", "warranty": "warranty", "closed": "closed"},
            "field_editable_phases": ["effective", "paused", "done", "closing", "warranty", "closed"],
            "state_actions": {
                "draft": ["submit", "activate", "close"],
                "in_progress": ["pause", "complete", "advance_closing", "close"],
                "paused": ["resume", "close"],
                "done": ["advance_closing", "advance_warranty", "close"],
                "closing": ["advance_warranty", "close"],
                "warranty": ["close"], "closed": [],
            },
            "approval_actions": ["approve", "reject"],
            "action_domains": {
                "submit": [("sc_approval_state", "=", "draft"), ("validation_status", "not in", ["waiting", "pending", "validated"])],
                "activate": [("sc_approval_state", "=", "approved")],
            },
            "method_by_action": {
                "submit": "action_sc_submit", "activate": "action_sc_start",
                "approve": "validate_tier", "reject": "reject_tier",
                "pause": "action_sc_pause", "resume": "action_sc_resume",
                "complete": "action_sc_mark_done", "advance_closing": "action_sc_begin_closing",
                "advance_warranty": "action_sc_start_warranty", "close": "action_sc_close",
            },
            "label_by_action": {"submit": "提交立项", "activate": "启动项目", "pause": "暂停项目", "resume": "恢复项目", "complete": "标记竣工", "advance_closing": "进入结算", "advance_warranty": "进入保修期", "close": "关闭项目"},
        },
        "project.task": {
            "state_field": "sc_state",
            "state_phase": {"draft": "draft", "ready": "approved", "in_progress": "effective", "done": "done", "cancelled": "cancelled"},
            "state_actions": {"draft": ["submit"], "ready": ["activate"], "in_progress": ["complete"]},
            "approval_actions": ["approve", "reject"],
            "method_by_action": {"submit": "action_prepare_task", "activate": "action_start_task", "complete": "action_mark_done", "approve": "validate_tier", "reject": "reject_tier"},
        },
        "sc.tax.deduction.registration": {
            "state_field": "state",
            "state_phase": {
                "draft": "draft",
                "confirmed": "approved",
                "deducted": "done",
                "legacy_confirmed": "legacy_confirmed",
                "cancel": "cancelled",
            },
            "state_actions": {
                "draft": ["submit", "cancel"],
                "confirmed": ["complete", "cancel"],
            },
            "approval_actions": ["approve", "reject"],
            "method_by_action": {
                "approve": "validate_tier", "reject": "reject_tier",
                "submit": "action_confirm",
                "complete": "action_deduct",
                "cancel": "action_cancel",
            },
            "label_by_action": {
                "submit": "确认",
                "complete": "已抵扣",
            },
        },
        "sc.subcontract.register": {
            "state_field": "state",
            "state_phase": {
                "draft": "draft",
                "active": "effective",
                "closed": "closed",
                "cancel": "cancelled",
            },
            # `已登记` 仍可调整事实（登记单是分包结算的合法来源）；`已关闭` 冻结后
            # 唯一合法的回到可调整状态的路径是 `重新打开`（closed -> active），
            # 与 `已取消` -> `草稿` 的 `退回草稿` 是两个不同的动作与标签。
            "state_actions": {
                "draft": ["submit", "cancel"],
                "active": ["complete", "cancel"],
                "closed": ["reactivate"],
                "cancel": ["reopen"],
            },
            "method_by_action": {
                "submit": "action_register",
                "complete": "action_close",
                "reopen": "action_reset_draft",
                "reactivate": "action_reopen",
                "cancel": "action_cancel",
            },
            "label_by_action": {
                "submit": "确认登记",
                "complete": "关闭",
                "reopen": "退回草稿",
                "reactivate": "重新打开",
            },
        },
        "project.progress.entry": {
            "state_field": "state",
            "state_phase": {"draft": "draft", "submitted": "submitted"},
            "state_actions": {"draft": ["submit"]},
            "method_by_action": {"submit": "action_submit_progress"},
            "label_by_action": {"submit": "提交"},
        },
        "project.risk.action": {
            "state_field": "state",
            "state_phase": {"open": "open", "claimed": "open", "escalated": "open", "closed": "closed"},
            "state_actions": {"open": ["complete"], "claimed": ["complete"], "escalated": ["complete"]},
            "method_by_action": {"complete": "action_close"},
            "label_by_action": {"complete": "关闭"},
        },
        "project.settlement": {
            "state_field": "state",
            "state_phase": {"draft": "draft", "confirmed": "approved", "done": "done", "cancel": "cancelled"},
            "state_actions": {"draft": ["submit", "cancel"], "confirmed": ["complete", "cancel"]},
            "method_by_action": {
                "submit": "action_confirm",
                "complete": "action_done",
                "cancel": "action_cancel",
            },
            "label_by_action": {"submit": "确认"},
        },
        "sc.edition.release.snapshot": {
            "state_field": "state",
            "state_phase": {"candidate": "draft", "approved": "approved", "released": "done", "superseded": "cancelled"},
            "state_actions": {
                "candidate": ["approve", "complete"],
                "approved": ["complete", "cancel"],
                "released": ["cancel"],
            },
            "method_by_action": {
                "approve": "action_approve",
                "complete": "action_release",
                "cancel": "action_supersede",
            },
            "label_by_action": {"complete": "发布", "cancel": "废弃"},
        },
        "sc.equipment.price": {
            "state_field": "state",
            "state_phase": {"draft": "draft", "active": "effective", "inactive": "cancelled"},
            "state_actions": {"draft": ["submit"], "active": ["complete"], "inactive": ["reopen"]},
            "method_by_action": {
                "submit": "action_activate",
                "complete": "action_deactivate",
                "reopen": "action_reset_draft",
            },
            "label_by_action": {"submit": "生效", "complete": "停用"},
        },
        "sc.labor.price": {
            "state_field": "state",
            "state_phase": {"draft": "draft", "active": "effective", "inactive": "cancelled"},
            "state_actions": {"draft": ["submit"], "active": ["complete"], "inactive": ["reopen"]},
            "method_by_action": {
                "submit": "action_activate",
                "complete": "action_deactivate",
                "reopen": "action_reset_draft",
            },
            "label_by_action": {"submit": "生效", "complete": "停用"},
        },
        "sc.subcontract.price": {
            "state_field": "state",
            "state_phase": {"draft": "draft", "active": "effective", "inactive": "cancelled"},
            "state_actions": {"draft": ["submit"], "active": ["complete"], "inactive": ["reopen"]},
            "method_by_action": {
                "submit": "action_activate",
                "complete": "action_deactivate",
                "reopen": "action_reset_draft",
            },
            "label_by_action": {"submit": "生效", "complete": "停用"},
        },
        "sc.hazard.source": {
            "state_field": "state",
            "state_phase": {"draft": "draft", "reported": "submitted", "controlled": "open", "closed": "closed"},
            "state_actions": {"draft": ["complete"], "reported": ["complete"], "controlled": ["complete"]},
            "method_by_action": {"complete": "action_close"},
            "label_by_action": {"complete": "关闭"},
        },
        "sc.material.acceptance": {
            "state_field": "state",
            "state_phase": {"draft": "draft", "submitted": "under_review", "approved": "approved", "accepted": "done", "rejected": "rejected", "cancel": "cancelled"},
            "state_actions": {"draft": ["submit", "cancel"], "submitted": ["submit", "approve", "reject", "cancel"], "approved": ["accept_result", "reject_result", "cancel"], "rejected": ["reopen"], "cancel": ["reopen"]},
            "field_editable_phases": ["approved"],
            "action_domains": {"submit": [("validation_status", "not in", ["waiting", "pending", "validated"])]},
            "approval_actions": ["approve", "reject"],
            "method_by_action": {
                "submit": "action_submit",
                "approve": "validate_tier",
                "accept_result": "action_accept",
                "reject": "reject_tier",
                "reject_result": "action_reject",
                "reopen": "action_reset_draft",
                "cancel": "action_cancel",
            },
            "label_by_action": {"accept_result": "验收通过", "reject_result": "验收不通过"},
        },
        "sc.material.inbound": {
            "state_field": "state",
            "state_phase": {"draft": "draft", "submitted": "under_review", "approved": "approved", "received": "done", "cancel": "cancelled"},
            "state_actions": {"draft": ["submit", "cancel"], "submitted": ["submit", "approve", "reject", "cancel"], "approved": ["complete", "cancel"], "cancel": ["reopen"]},
            "action_domains": {"submit": [("validation_status", "not in", ["waiting", "pending", "validated"])]},
            "approval_actions": ["approve", "reject"],
            "method_by_action": {
                "approve": "validate_tier",
                "reject": "reject_tier",
                "submit": "action_submit",
                "complete": "action_receive",
                "reopen": "action_reset_draft",
                "cancel": "action_cancel",
            },
            "label_by_action": {"complete": "确认入库"},
        },
        "sc.material.outbound": {
            "state_field": "state",
            "state_phase": {"draft": "draft", "submitted": "under_review", "approved": "approved", "issued": "done", "cancel": "cancelled"},
            "state_actions": {"draft": ["submit", "cancel"], "submitted": ["approve", "reject", "cancel"], "approved": ["complete", "cancel"], "cancel": ["reopen"]},
            "approval_actions": ["approve", "reject"],
            "method_by_action": {
                "submit": "action_submit",
                "approve": "validate_tier",
                "reject": "reject_tier",
                "complete": "action_issue",
                "reopen": "action_reset_draft",
                "cancel": "action_cancel",
            },
            "label_by_action": {"complete": "确认出库"},
        },
        "sc.material.rental.order": {
            "state_field": "state",
            "state_phase": {"draft": "draft", "submitted": "under_review", "approved": "approved", "active": "effective", "returned": "open", "settled": "done", "cancel": "cancelled"},
            "state_actions": {"draft": ["submit", "cancel"], "submitted": ["submit", "cancel"], "approved": ["activate", "cancel"], "active": ["return_rental", "cancel"], "returned": ["complete"]},
            "action_domains": {"submit": [("validation_status", "not in", ["waiting", "pending", "validated"])]},
            "approval_actions": ["approve", "reject"],
            "method_by_action": {"submit": "action_submit", "approve": "validate_tier", "reject": "reject_tier", "activate": "action_activate", "return_rental": "action_return", "complete": "action_settle", "cancel": "action_cancel"},
            "label_by_action": {"activate": "确认租赁", "return_rental": "确认退还", "complete": "完成结算"},
        },
        "sc.material.rental.settlement": {
            "state_field": "state",
            "state_phase": {"draft": "draft", "submitted": "under_review", "approved": "approved", "confirmed": "approved", "paid": "done", "cancel": "cancelled"},
            "state_actions": {"draft": ["submit", "cancel"], "submitted": ["submit", "cancel"], "approved": ["confirm_settlement", "cancel"], "confirmed": ["complete", "cancel"]},
            "action_domains": {"submit": [("validation_status", "not in", ["waiting", "pending", "validated"])]},
            "approval_actions": ["approve", "reject"],
            "method_by_action": {"submit": "action_submit", "approve": "validate_tier", "reject": "reject_tier", "confirm_settlement": "action_confirm", "complete": "action_paid", "cancel": "action_cancel"},
            "label_by_action": {"confirm_settlement": "确认结算", "complete": "确认支付"},
        },
        "sc.material.settlement": {
            "state_field": "state",
            "state_phase": {"draft": "draft", "submitted": "under_review", "approved": "approved", "confirmed": "done", "cancel": "cancelled"},
            "state_actions": {"draft": ["submit", "cancel"], "submitted": ["submit", "cancel"], "approved": ["complete", "cancel"], "cancel": ["reopen"]},
            "action_domains": {"submit": [("validation_status", "not in", ["waiting", "pending", "validated"])]},
            "approval_actions": ["approve", "reject"],
            "method_by_action": {"submit": "action_submit", "approve": "validate_tier", "reject": "reject_tier", "complete": "action_confirm", "cancel": "action_cancel", "reopen": "action_reset_draft"},
            "label_by_action": {"complete": "确认结算"},
        },
        "sc.equipment.usage": {
            "state_field": "state",
            "state_phase": {"draft": "draft", "submitted": "under_review", "approved": "approved", "confirmed": "done", "cancel": "cancelled"},
            "state_actions": {"draft": ["submit", "cancel"], "submitted": ["submit", "cancel"], "approved": ["complete", "cancel"], "cancel": ["reopen"]},
            "action_domains": {"submit": [("validation_status", "not in", ["waiting", "pending", "validated"])]},
            "approval_actions": ["approve", "reject"],
            "method_by_action": {"submit": "action_submit", "approve": "validate_tier", "reject": "reject_tier", "complete": "action_confirm", "cancel": "action_cancel", "reopen": "action_reset_draft"},
            "label_by_action": {"complete": "确认登记"},
        },
        "sc.equipment.settlement": {
            "state_field": "state",
            "state_phase": {"draft": "draft", "submitted": "under_review", "approved": "approved", "confirmed": "done", "cancel": "cancelled"},
            "state_actions": {"draft": ["submit", "cancel"], "submitted": ["submit", "cancel"], "approved": ["complete", "cancel"], "cancel": ["reopen"]},
            "action_domains": {"submit": [("validation_status", "not in", ["waiting", "pending", "validated"])]},
            "approval_actions": ["approve", "reject"],
            "method_by_action": {"submit": "action_submit", "approve": "validate_tier", "reject": "reject_tier", "complete": "action_confirm", "cancel": "action_cancel", "reopen": "action_reset_draft"},
            "label_by_action": {"complete": "确认结算"},
        },
        "sc.attendance.checkin": {
            "state_field": "state",
            "state_phase": {"draft": "draft", "submitted": "under_review", "approved": "approved", "confirmed": "done", "cancel": "cancelled"},
            "state_actions": {"draft": ["submit", "cancel"], "submitted": ["submit", "cancel"], "approved": ["complete", "cancel"], "cancel": ["reopen"]},
            "action_domains": {"submit": [("validation_status", "not in", ["waiting", "pending", "validated"])]},
            "approval_actions": ["approve", "reject"],
            "method_by_action": {"submit": "action_submit", "approve": "validate_tier", "reject": "reject_tier", "complete": "action_confirm", "cancel": "action_cancel", "reopen": "action_reset_draft"},
            "label_by_action": {"complete": "确认考勤"},
        },
        "sc.labor.usage": {
            "state_field": "state",
            "state_phase": {"draft": "draft", "submitted": "under_review", "approved": "approved", "confirmed": "done", "cancel": "cancelled"},
            "state_actions": {"draft": ["submit", "cancel"], "submitted": ["submit", "cancel"], "approved": ["complete", "cancel"], "cancel": ["reopen"]},
            "action_domains": {"submit": [("validation_status", "not in", ["waiting", "pending", "validated"])]},
            "approval_actions": ["approve", "reject"],
            "method_by_action": {"submit": "action_submit", "approve": "validate_tier", "reject": "reject_tier", "complete": "action_confirm", "cancel": "action_cancel", "reopen": "action_reset_draft"},
            "label_by_action": {"complete": "确认用工"},
        },
        "sc.labor.settlement": {
            "state_field": "state",
            "state_phase": {"draft": "draft", "submitted": "under_review", "approved": "approved", "confirmed": "done", "cancel": "cancelled"},
            "state_actions": {"draft": ["submit", "cancel"], "submitted": ["submit", "cancel"], "approved": ["complete", "cancel"], "cancel": ["reopen"]},
            "action_domains": {"submit": [("validation_status", "not in", ["waiting", "pending", "validated"])]},
            "approval_actions": ["approve", "reject"],
            "method_by_action": {"submit": "action_submit", "approve": "validate_tier", "reject": "reject_tier", "complete": "action_confirm", "cancel": "action_cancel", "reopen": "action_reset_draft"},
            "label_by_action": {"complete": "确认结算"},
        },
        "sc.material.rfq": {
            "state_field": "state",
            "state_phase": {"draft": "draft", "submitted": "under_review", "approved": "approved", "selected": "done", "cancel": "cancelled"},
            "state_actions": {"draft": ["submit", "cancel"], "submitted": ["submit", "cancel"], "approved": ["complete", "cancel"], "cancel": ["reopen"]},
            "action_domains": {"submit": [("validation_status", "not in", ["waiting", "pending", "validated"])]},
            "approval_actions": ["approve", "reject"],
            "field_editable_phases": ["approved"],
            "method_by_action": {
                "submit": "action_submit",
                "approve": "validate_tier",
                "reject": "reject_tier",
                "complete": "action_select",
                "reopen": "action_reset_draft",
                "cancel": "action_cancel",
            },
            "label_by_action": {"submit": "发起询价", "complete": "确定报价"},
        },
        "sc.output.invoice.adjustment": {
            "state_field": "state",
            "state_phase": {"draft": "draft", "submitted": "under_review", "approved": "approved", "rejected": "rejected", "confirmed": "done", "cancel": "cancelled"},
            "state_actions": {"draft": ["submit", "cancel"], "submitted": ["submit"], "approved": ["complete", "cancel"], "rejected": ["submit", "cancel"]},
            "action_domains": {"submit": [("validation_status", "not in", ["waiting", "pending", "validated"])], "cancel": [("validation_status", "not in", ["waiting", "pending"])]},
            "approval_actions": ["approve", "reject"],
            "method_by_action": {"submit": "action_submit", "approve": "validate_tier", "reject": "reject_tier", "complete": "action_confirm", "cancel": "action_cancel"},
            "label_by_action": {"complete": "确认红冲"},
        },
        "sc.project.document": {
            "state_field": "state",
            "state_phase": {"draft": "draft", "review": "under_review", "approved": "approved", "done": "done", "cancel": "cancelled"},
            "state_actions": {"draft": ["submit", "cancel"], "review": ["submit", "cancel"], "approved": ["complete", "cancel"], "done": ["reopen", "cancel"], "cancel": ["reopen"]},
            "action_domains": {"submit": [("validation_status", "not in", ["waiting", "pending", "validated"])]},
            "approval_actions": ["approve", "reject"],
            "method_by_action": {"submit": "action_submit", "approve": "validate_tier", "reject": "reject_tier", "complete": "action_archive", "cancel": "action_cancel", "reopen": "action_reset_to_draft"},
            "label_by_action": {"complete": "归档", "cancel": "作废"},
        },
        "sc.safety.patrol.task": {
            "state_field": "state",
            "state_phase": {"draft": "draft", "planned": "submitted", "done": "done", "cancel": "cancelled"},
            "state_actions": {"draft": ["complete", "cancel"], "planned": ["complete", "reopen", "cancel"], "cancel": ["reopen"]},
            "method_by_action": {"complete": "action_done", "reopen": "action_reset_draft", "cancel": "action_cancel"},
        },
        "sc.workflow.instance": {
            "state_field": "state",
            "state_phase": {"draft": "draft", "running": "under_review", "done": "done", "rejected": "rejected", "cancelled": "cancelled"},
            "state_actions": {"draft": ["submit", "cancel"], "running": ["approve", "reject", "cancel"]},
            "method_by_action": {"submit": "action_submit", "approve": "action_approve", "reject": "action_reject", "cancel": "action_cancel"},
        },
        "tender.doc.purchase": {
            "state_field": "state",
            "state_phase": {"draft": "draft", "submitted": "under_review", "approved": "approved", "rejected": "rejected"},
            "state_actions": {"draft": ["submit"], "submitted": ["submit"], "rejected": ["submit", "reopen"]},
            "action_domains": {"submit": [("validation_status", "not in", ["waiting", "pending", "validated"])]},
            "approval_actions": ["approve", "reject"],
            "method_by_action": {"submit": "action_submit", "approve": "validate_tier", "reject": "reject_tier", "reopen": "action_reset_draft"},
        },
        "tender.guarantee": {
            "state_field": "state",
            "state_phase": {"draft": "draft", "submitted": "under_review", "approved": "approved", "rejected": "rejected", "confirmed": "done", "cancel": "cancelled"},
            "state_actions": {"draft": ["submit", "cancel"], "submitted": ["submit"], "approved": ["complete"], "rejected": ["submit", "cancel", "reopen"], "cancel": ["reopen"]},
            "action_domains": {"submit": [("validation_status", "not in", ["waiting", "pending", "validated"])]},
            "approval_actions": ["approve", "reject"],
            "method_by_action": {"submit": "action_submit", "approve": "validate_tier", "reject": "reject_tier", "complete": "action_confirm", "reopen": "action_reset_draft", "cancel": "action_cancel"},
            "label_by_action": {"complete": "确认入账"},
        },
    }

    ACTIONS = {
        "return_rental": {"label": "确认退还", "kind": "transition", "action_semantics": {"kind": "business", "purpose": "complete", "executor": "contract.action", "origin": "workflow.contract.service"}},
        "confirm_settlement": {"label": "确认结算", "kind": "transition", "action_semantics": {"kind": "business", "purpose": "complete", "executor": "contract.action", "origin": "workflow.contract.service"}},
        "accept_result": {"label": "验收通过", "kind": "transition", "action_semantics": {"kind": "business", "purpose": "complete", "executor": "contract.action", "origin": "workflow.contract.service"}},
        "reject_result": {"label": "验收不通过", "kind": "transition", "action_semantics": {"kind": "business", "purpose": "complete", "executor": "contract.action", "origin": "workflow.contract.service"}},
        "pause": {"label": "暂停执行", "intent": "server.object", "kind": "transition", "action_semantics": {"kind": "business", "purpose": "pause_execution", "executor": "contract.action", "origin": "workflow.contract.service"}},
        "resume": {"label": "恢复执行", "intent": "server.object", "kind": "transition", "action_semantics": {"kind": "business", "purpose": "start_execution", "executor": "contract.action", "origin": "workflow.contract.service"}},
        "advance_closing": {"label": "推进阶段", "intent": "server.object", "kind": "transition", "action_semantics": {"kind": "business", "purpose": "advance_phase", "executor": "contract.action", "origin": "workflow.contract.service"}},
        "advance_warranty": {"label": "推进阶段", "intent": "server.object", "kind": "transition", "action_semantics": {"kind": "business", "purpose": "advance_phase", "executor": "contract.action", "origin": "workflow.contract.service"}},
        "close": {"label": "关闭记录", "intent": "server.object", "kind": "transition", "action_semantics": {"kind": "business", "purpose": "close_record", "executor": "contract.action", "origin": "workflow.contract.service"}},

        "save_draft": {"label": "保存草稿", "intent": "data.write", "method": None, "kind": "save"},
        "submit": {"label": "提交审批", "intent": "server.object", "kind": "transition", "action_semantics": {"kind": "business", "purpose": "submit", "executor": "contract.action", "origin": "workflow.contract.service"}},
        "approve": {"label": "审批通过", "intent": "server.object", "kind": "approval", "action_semantics": {"kind": "business", "purpose": "approve", "executor": "contract.action", "origin": "workflow.contract.service"}},
        "reject": {"label": "审批驳回", "intent": "server.object", "kind": "approval", "action_semantics": {"kind": "business", "purpose": "reject", "executor": "contract.action", "origin": "workflow.contract.service"}},
        "activate": {"label": "开始执行", "intent": "server.object", "kind": "transition", "action_semantics": {"kind": "business", "purpose": "start_execution", "executor": "contract.action", "origin": "workflow.contract.service"}},
        "complete": {"label": "完成", "intent": "server.object", "kind": "transition", "action_semantics": {"kind": "business", "purpose": "complete", "executor": "contract.action", "origin": "workflow.contract.service"}},
        "cancel": {"label": "取消", "intent": "server.object", "kind": "transition", "action_semantics": {"kind": "business", "purpose": "cancel_record", "executor": "contract.action", "origin": "workflow.contract.service"}},
        # A separate command from pre-execution cancellation: the model owns
        # reversing the posted ledger before entering the cancelled state.
        "reverse_payment": {"label": "撤销付款", "intent": "server.object", "kind": "transition", "action_semantics": {"kind": "business", "purpose": "cancel_record", "executor": "contract.action", "origin": "workflow.contract.service"}},
        # `reopen` 在本平台语义是「重置为草稿」（`cancel` -> `draft`）。分包登记
        # `已关闭` -> `已登记` 是另一个目标状态、另一个方法，所以用独立键，避免同一个
        # 键在 `已取消` 与 `已关闭` 两个状态上声明两个互斥的方法与标签。
        # 两者的 `purpose` 同为 `reopen`：它只声明“把记录恢复到可继续办理的状态”，
        # 具体目标状态仍由各自的 `method` / 动作规则承载。
        "reopen": {"label": "重置为草稿", "intent": "server.object", "kind": "transition", "action_semantics": {"kind": "business", "purpose": "reopen", "executor": "contract.action", "origin": "workflow.contract.service"}},
        "reactivate": {"label": "重新打开", "intent": "server.object", "kind": "transition", "action_semantics": {"kind": "business", "purpose": "reopen", "executor": "contract.action", "origin": "workflow.contract.service"}},
    }

    TERMINAL_PHASES = {"done", "cancelled", "legacy_confirmed"}
    STATUSBAR_BASE_STATES = (
        ("draft", "草稿"),
        ("submitted", "已提交"),
        ("under_review", "审批中"),
        ("approved", "已批准"),
        ("effective", "执行中"),
        ("done", "已完成"),
    )
    STATUSBAR_EXTRA_LABELS = {
        "cancelled": "已取消",
        "rejected": "已驳回",
        "legacy_confirmed": "历史确认",
        "closed": "已关闭",
        "paused": "停工",
        "closing": "结算中",
        "warranty": "保修期",
        "open": "处理中",
    }

    @api.model
    def source_authority_contract(self):
        return {
            "kind": self.SOURCE_KIND,
            "authorities": list(self.SOURCE_AUTHORITIES),
            "projection_only": True,
            "rebuildable": True,
            "runtime_carrier": self._name,
        }

    @api.model
    def supported_model_names(self):
        return sorted(self.profile_by_model())

    @api.model
    def is_model_supported(self, model_name):
        return str(model_name or "").strip() in self.profile_by_model()

    @api.model
    def _external_profile_by_model(self):
        """Profiles contributed by the module that owns the model.

        `smart_construction_core` owns the construction-industry projection.
        A model owned by a user/product module publishes its own profile
        through the P0 registry; the industry layer merges it instead of
        declaring rules for a model it does not own.
        """
        return external_workflow_contract_profiles()

    @api.model
    def _profile_is_executable(self, model_name, profile):
        if model_name not in self.env.registry:
            return False
        model = self.env[model_name]
        for method_name in (profile.get("method_by_action") or {}).values():
            # `hasattr` raises on a non-string name; treat that shape as
            # non-executable rather than letting the read fail behind a caller's
            # try/except.
            if method_name is None:
                continue
            if not isinstance(method_name, str):
                return False
            if method_name and not hasattr(model, method_name):
                return False
        return True

    @api.model
    def profile_by_model(self):
        merged = {name: dict(profile) for name, profile in self.PROFILE_BY_MODEL.items()}
        for model_name, profile in self._external_profile_by_model().items():
            if model_name in merged:
                continue
            if not self._profile_is_executable(model_name, profile):
                _logger.warning(
                    "[workflow.contract] external profile for %s does not resolve in this registry; "
                    "its actions stay undeclared",
                    model_name,
                )
                continue
            merged[model_name] = profile
        return merged

    @api.model
    def describe_model_actions(self, model_name):
        """Stable meanings for an unsaved form; never a record execution grant."""
        profile = self.profile_by_model().get(model_name)
        if not profile:
            return {}
        return {
            "model": model_name,
            "source": {"kind": "sc_backend_workflow_action_catalog", "projection_only": True},
            "availabilityScope": "declaration_only",
            "actions": self._declared_actions(profile),
            "submissionRequirements": list(profile.get("submission_requirements") or []),
        }

    @api.model
    def describe_record(self, record):
        if not record or len(record) != 1:
            return {}
        profile = self.profile_by_model().get(record._name)
        if not profile:
            return {}
        raw_state = str(getattr(record, profile["state_field"], "") or "").strip()
        business_phase = profile["state_phase"].get(raw_state, raw_state or "unknown")
        approval_phase = self._approval_phase(record, raw_state=raw_state, business_phase=business_phase)
        editability = self._editability(profile, business_phase, approval_phase)
        evidence_gate = self._evidence_gate(record)
        actions = self._available_actions(record, profile, raw_state, business_phase, approval_phase, evidence_gate)
        current_action_keys = {action["key"] for action in actions}
        visible_evidence_gate = [
            gate for gate in evidence_gate
            if not gate.get("actionKeys") or current_action_keys.intersection(gate["actionKeys"])
        ]
        return {
            "source": self.source_authority_contract(),
            "model": record._name,
            "record_id": record.id,
            "stateField": profile["state_field"],
            "rawState": raw_state,
            "businessPhase": business_phase,
            "approvalPhase": approval_phase,
            "editability": editability,
            "statusbar": self._statusbar_projection(business_phase, approval_phase),
            "evidenceGate": visible_evidence_gate,
            "submissionRequirements": list(profile.get("submission_requirements") or []),
            # Meaning is stable even when a transition is currently unavailable.
            # This catalog is not an execution grant; availableActions remains
            # the record/user/state-specific availability authority.
            "actions": self._declared_actions(profile),
            "availableActions": actions,
        }

    @api.model
    def _declared_actions(self, profile):
        actions = []
        for key, method in (profile.get("method_by_action") or {}).items():
            semantics = (self.ACTIONS.get(key) or {}).get("action_semantics")
            if method and semantics:
                actions.append({
                    "key": key,
                    "method": method,
                    "action_semantics": dict(semantics),
                })
        return actions

    @api.model
    def _statusbar_projection(self, business_phase, approval_phase):
        current = str(business_phase or "").strip()
        approval = str(approval_phase or "").strip()
        if current == "submitted" and approval in ("waiting", "pending"):
            current = "under_review"
        states = [{"value": value, "label": label} for value, label in self.STATUSBAR_BASE_STATES]
        if current and current not in {row["value"] for row in states}:
            states.append({"value": current, "label": self.STATUSBAR_EXTRA_LABELS.get(current, current)})
        return {
            "field": "__workflow_phase",
            "current": current,
            "states": states,
            "readonly": True,
            "source": "workflowContract",
        }

    @api.model
    def _approval_phase(self, record, *, raw_state, business_phase):
        status = str(getattr(record, "validation_status", "") or "").strip()
        if status in ("waiting", "pending"):
            return status
        if status in ("validated", "approved"):
            return "approved"
        if status in ("rejected",):
            return "rejected"
        if business_phase in ("under_review",) and raw_state in ("submit", "approve"):
            return "pending"
        if business_phase in ("approved", "done", "legacy_confirmed"):
            return "approved"
        return "none"

    @api.model
    def _editability(self, profile, business_phase, approval_phase):
        # Execution-field exceptions apply only outside an active review.
        if approval_phase in ("waiting", "pending"):
            return "readonly"
        field_editable_phases = {
            str(value or "").strip()
            for value in (profile.get("field_editable_phases") or [])
            if str(value or "").strip()
        }
        if business_phase in field_editable_phases:
            return "editable"
        if business_phase in self.TERMINAL_PHASES:
            return "locked"
        editable_phases = {
            str(value or "").strip()
            for value in (profile.get("editable_phases") or ["draft"])
            if str(value or "").strip()
        }
        if business_phase in editable_phases and approval_phase not in ("waiting", "pending", "approved"):
            return "editable"
        if business_phase in ("under_review", "approved", "rejected") or approval_phase in ("waiting", "pending", "approved"):
            return "readonly"
        return "editable"

    @api.model
    def _available_actions(self, record, profile, raw_state, business_phase, approval_phase, evidence_gate):
        del business_phase
        keys = list(profile.get("state_actions", {}).get(raw_state, []))
        if approval_phase in ("waiting", "pending"):
            for key in profile.get("approval_actions", []):
                if key not in keys:
                    keys.append(key)
        if approval_phase in ("waiting", "pending") and "approve" in keys:
            if not bool(getattr(record, "can_review", False)):
                keys.remove("approve")
        if approval_phase in ("waiting", "pending") and "reject" in keys:
            if not bool(getattr(record, "can_review", False)):
                keys.remove("reject")
        method_by_action = profile.get("method_by_action", {})
        actions = []
        for key in keys:
            domain = (profile.get("action_domains") or {}).get(key)
            if domain and not record.filtered_domain(domain):
                continue
            spec = dict(self.ACTIONS.get(key) or {})
            if not spec:
                continue
            method = method_by_action.get(key, spec.get("method"))
            blockers = [
                row for row in evidence_gate
                if row.get("blocking") and key in (row.get("actionKeys") or [])
            ]
            enabled = not blockers
            actions.append(
                {
                    "key": key,
                    "label": profile.get("label_by_action", {}).get(key) or spec.get("label") or key,
                    "intent": spec.get("intent") or "server.object",
                    "kind": spec.get("kind") or "transition",
                    **({"action_semantics": dict(spec["action_semantics"])} if spec.get("action_semantics") else {}),
                    "method": method,
                    "enabled": enabled,
                    "reason_code": blockers[0].get("reasonCode") if blockers else "",
                    "blocked_message": blockers[0].get("message") if blockers else "",
                    "target": {
                        "model": record._name,
                        "id": record.id,
                        "method": method,
                    },
                }
            )
        return actions

    @api.model
    def _evidence_gate(self, record):
        if record._name == "sc.material.rental.settlement":
            gates = []
            if record.state == "confirmed":
                blocker = record._payment_confirmation_blocker()
                if blocker:
                    gates.append(self._gate(blocker["reason_code"], blocker["message"], action_keys=["complete"]))
            if record.state in ("draft", "submitted", "approved", "confirmed"):
                blocker = record._payment_cancellation_blocker()
                if blocker:
                    gates.append(self._gate(blocker["reason_code"], blocker["message"], action_keys=["cancel"]))
            return gates
        if record._name == "sc.expense.claim":
            return self._expense_claim_evidence_gate(record)
        if record._name == "sc.settlement.order":
            return self._settlement_order_evidence_gate(record)
        if record._name == "payment.request":
            return self._payment_request_evidence_gate(record)
        if record._name in ("construction.contract", "construction.contract.expense", "construction.contract.income"):
            return self._construction_contract_evidence_gate(record)
        if record._name == "sc.payment.execution":
            return self._payment_execution_evidence_gate(record)
        if record._name == "sc.receipt.income":
            return self._receipt_income_evidence_gate(record)
        if record._name == "sc.workflow.instance":
            if not record._legacy_runtime_enabled():
                return [self._gate("LEGACY_WORKFLOW_RUNTIME_DISABLED", "历史流程运行已关闭；业务审批使用统一审批机制。", action_keys=["submit", "approve", "reject"])]
            return []
        if record._name == "sc.output.invoice.adjustment":
            gates = []
            blocker = record._original_invoice_eligibility_blocker()
            if blocker:
                gates.append(self._gate(blocker["reason_code"], blocker["message"], action_keys=["submit", "approve", "complete"]))
            duplicate = record._duplicate_red_flush_blocker()
            if duplicate:
                gates.append(self._gate(duplicate["reason_code"], duplicate["message"], action_keys=["submit", "approve", "complete"]))
            if not self.env["sc.invoice.registration"]._has_finance_register_access():
                gates.append(self._gate("INVOICE_REGISTER_ACCESS_DENIED", "你没有完成发票登记的财务确认权限。", action_keys=["complete"]))
            return gates
        if record._name == "sc.invoice.registration":
            return self._invoice_registration_evidence_gate(record)
        if record._name == "sc.self.funding.registration":
            return self._self_funding_registration_evidence_gate(record)
        if record._name == "sc.financing.loan":
            return self._financing_loan_evidence_gate(record)
        if record._name == "sc.treasury.reconciliation":
            return self._treasury_reconciliation_evidence_gate(record)
        if record._name == "sc.settlement.adjustment":
            return self._settlement_adjustment_evidence_gate(record)
        return []

    @api.model
    def _gate(self, reason_code, message, *, action_keys=None, blocking=True, severity="block"):
        return {
            "reasonCode": reason_code,
            "message": message,
            "actionKeys": list(action_keys or ["submit", "approve", "complete"]),
            "blocking": bool(blocking),
            "severity": severity,
        }

    @api.model
    def _expense_claim_evidence_gate(self, record):
        return [self._gate(code, message) for code, message in record._business_readiness_errors()]

    @api.model
    def _settlement_order_evidence_gate(self, record):
        gates = []
        if not record.project_id:
            gates.append(self._gate("SETTLEMENT_MISSING_PROJECT", "结算单必须关联项目。"))
        if not record.partner_id and not record.legacy_fact_model:
            gates.append(self._gate("SETTLEMENT_MISSING_PARTNER", "结算单必须选择往来单位。"))
        if not record.line_ids:
            gates.append(self._gate("SETTLEMENT_MISSING_LINES", "结算单必须维护结算明细。"))
        if (record.amount_total or 0.0) <= 0:
            gates.append(self._gate("SETTLEMENT_INVALID_AMOUNT", "结算金额必须大于 0。"))
        if any((line.qty or 0.0) <= 0 for line in record.line_ids):
            gates.append(self._gate("SETTLEMENT_INVALID_LINE_QTY", "结算行数量必须大于 0。"))
        if any((line.price_unit or 0.0) < 0 for line in record.line_ids):
            gates.append(self._gate("SETTLEMENT_INVALID_LINE_PRICE", "结算行单价不能为负数。"))
        return gates

    @api.model
    def _payment_request_evidence_gate(self, record):
        gates = []
        if not record.project_id:
            gates.append(self._gate("PAYMENT_MISSING_PROJECT", "付款/收款申请必须关联项目。"))
        if (record.amount or 0.0) <= 0:
            gates.append(self._gate("PAYMENT_INVALID_AMOUNT", "付款/收款申请金额必须大于 0。"))
        try:
            has_basis = record._has_payment_basis()
        except Exception:
            has_basis = bool(record.contract_id or record.settlement_id or record.material_settlement_id)
        if not has_basis:
            gates.append(self._gate("PAYMENT_MISSING_BASIS", "请先选择关联合同、结算单、材料结算单或历史关联依据。"))
        if record.type == "pay" and record.settlement_id:
            try:
                metrics = opm.compute_payment_payable_excluding_self(record)
            except Exception:
                metrics = {}
            payable = metrics.get("payable") if isinstance(metrics, dict) else None
            precision = metrics.get("precision") if isinstance(metrics, dict) else None
            if payable is not None:
                precision = precision or (record.currency_id.rounding if record.currency_id else 0.01)
                if float_compare(payable, 0.0, precision_rounding=precision) <= 0:
                    gates.append(self._gate("PAYMENT_SETTLEMENT_NO_PAYABLE_BALANCE", "结算单剩余额度不足。"))
                elif float_compare(record.amount or 0.0, payable, precision_rounding=precision) == 1:
                    gates.append(self._gate("PAYMENT_OVER_SETTLEMENT_BALANCE", "申请金额 %s 超过结算单剩余额度 %s。" % (record.amount or 0.0, payable)))
        if record.type == "pay" and record.material_settlement_id:
            settlement = record.material_settlement_id
            if getattr(settlement, "state", "") != "confirmed":
                gates.append(self._gate("PAYMENT_MATERIAL_SETTLEMENT_NOT_CONFIRMED", "材料结算单未确认。"))
            try:
                requested = record._material_settlement_requested_amount_excluding_self()
            except Exception:
                requested = 0.0
            payable = (settlement.amount_total or 0.0) - (requested or 0.0)
            precision = record.currency_id.rounding if record.currency_id else 0.01
            if float_compare(record.amount or 0.0, payable, precision_rounding=precision) == 1:
                gates.append(self._gate("PAYMENT_OVER_MATERIAL_SETTLEMENT_BALANCE", "本次申请金额 %s 超过材料结算剩余可申请金额 %s。" % (record.amount or 0.0, payable)))
        return gates

    @api.model
    def _construction_contract_evidence_gate(self, record):
        gates = []
        if not record.project_id:
            gates.append(self._gate("CONTRACT_MISSING_PROJECT", "项目合同必须关联项目。"))
        if not record.partner_id:
            gates.append(self._gate("CONTRACT_MISSING_PARTNER", "项目合同必须选择合同方。"))
        if getattr(record, "validation_status", "") in ("waiting", "pending"):
            gates.append(
                self._gate(
                    "CONTRACT_APPROVAL_IN_PROGRESS",
                    "项目合同已经在统一审批流程中，请等待审批完成后再重复提交。",
                    action_keys=["submit"],
                )
            )
        if getattr(record, "state", "") in ("confirmed", "running") and not record.line_ids:
            gates.append(
                self._gate(
                    "CONTRACT_MISSING_LINES_FOR_CLOSE",
                    "无合同明细的合同不可关闭，请补充明细。",
                    action_keys=["complete"],
                )
            )
        if getattr(record, "is_locked", False):
            gates.append(
                self._gate(
                    "CONTRACT_LOCKED_BY_DOWNSTREAM_FACTS",
                    "合同已被付款申请/结算单引用，禁止取消或重置为草稿。",
                    action_keys=["cancel", "reopen"],
                )
            )
        return gates

    @api.model
    def _payment_execution_evidence_gate(self, record):
        if getattr(record, "source_origin", "") == "legacy" and getattr(record, "state", "") == "legacy_confirmed":
            return []
        gates = []
        if not record.project_id:
            gates.append(self._gate("PAYMENT_EXECUTION_MISSING_PROJECT", "付款执行必须关联项目。"))
        if not record.payment_request_id:
            gates.append(self._gate("PAYMENT_EXECUTION_MISSING_REQUEST", "新系统付款执行必须关联已审批的付款申请。"))
        request = record.payment_request_id
        material_settlement = request.material_settlement_id if request else False
        if not record.contract_id and not material_settlement and not (request and request._has_payment_basis()):
            gates.append(self._gate("PAYMENT_EXECUTION_MISSING_CONTRACT", "新系统付款执行必须关联合同或结算依据。"))
        if not record.partner_id:
            gates.append(self._gate("PAYMENT_EXECUTION_MISSING_PARTNER", "付款执行必须选择往来单位。"))
        if (record.paid_amount or 0.0) <= 0:
            gates.append(self._gate("PAYMENT_EXECUTION_INVALID_AMOUNT", "实付金额必须大于 0。"))
        payer_account = record.payment_account_no or record.bank_account or record.payment_account_name
        payee_account = record.receipt_account_no or record.receipt_account_name
        if not payer_account:
            gates.append(self._gate("PAYMENT_EXECUTION_MISSING_PAYER_ACCOUNT", "新系统付款执行必须填写付款账户信息。"))
        if not payee_account:
            gates.append(self._gate("PAYMENT_EXECUTION_MISSING_PAYEE_ACCOUNT", "新系统付款执行必须填写收款账户信息。"))
        if getattr(record, "validation_status", "") in ("waiting", "pending"):
            gates.append(
                self._gate(
                    "PAYMENT_EXECUTION_APPROVAL_IN_PROGRESS",
                    "付款执行已经在统一审批流程中，请等待审批完成后再重复提交。",
                    action_keys=["submit"],
                )
            )
        return gates

    @api.model
    def _receipt_income_evidence_gate(self, record):
        if getattr(record, "source_origin", "") == "legacy" and getattr(record, "state", "") == "legacy_confirmed":
            return []
        gates = []
        if not record.project_id:
            gates.append(self._gate("RECEIPT_INCOME_MISSING_PROJECT", "收款收入必须关联项目。"))
        if not record.payment_request_id:
            gates.append(self._gate("RECEIPT_INCOME_MISSING_REQUEST", "新系统收款收入必须关联已审批的收款申请。"))
        if not record.contract_id:
            gates.append(self._gate("RECEIPT_INCOME_MISSING_CONTRACT", "新系统收款收入必须关联合同。"))
        if not record.partner_id:
            gates.append(self._gate("RECEIPT_INCOME_MISSING_PARTNER", "收款收入必须选择往来单位。"))
        if (record.amount or 0.0) <= 0:
            gates.append(self._gate("RECEIPT_INCOME_INVALID_AMOUNT", "收款金额必须大于 0。"))
        receiving_account = record.receiving_account_no or record.receiving_account or record.receiving_account_name
        if not receiving_account:
            gates.append(self._gate("RECEIPT_INCOME_MISSING_RECEIVING_ACCOUNT", "新系统收款收入必须填写收款账户信息。"))
        if getattr(record, "validation_status", "") in ("waiting", "pending"):
            gates.append(
                self._gate(
                    "RECEIPT_INCOME_APPROVAL_IN_PROGRESS",
                    "收款收入已经在统一审批流程中，请等待审批完成后再重复提交。",
                    action_keys=["submit"],
                )
            )
        return gates

    @api.model
    def _invoice_registration_evidence_gate(self, record):
        if getattr(record, "source_origin", "") == "legacy" and getattr(record, "state", "") == "legacy_confirmed":
            return []
        gates = []
        if not record.project_id:
            gates.append(self._gate("INVOICE_REGISTRATION_MISSING_PROJECT", "发票登记必须关联项目。"))
        if not record.invoice_date:
            gates.append(self._gate("INVOICE_REGISTRATION_MISSING_DATE", "发票登记必须填写发票日期。"))
        if (record.amount_total or 0.0) <= 0 and (record.tax_amount or 0.0) <= 0 and (record.surcharge_amount or 0.0) <= 0:
            gates.append(self._gate("INVOICE_REGISTRATION_INVALID_AMOUNT", "发票登记必须填写有效金额。"))
        if record.source_kind == "prepaid_tax" or record.direction == "prepaid":
            if not record.tax_certificate_no:
                gates.append(self._gate("INVOICE_REGISTRATION_MISSING_TAX_CERTIFICATE", "预缴税登记必须填写完税凭证号码。"))
        elif not record.invoice_no:
            gates.append(self._gate("INVOICE_REGISTRATION_MISSING_INVOICE_NO", "发票登记必须填写发票号码。"))
        if record.contract_id:
            if record.contract_id.project_id != record.project_id:
                gates.append(self._gate("INVOICE_REGISTRATION_CONTRACT_PROJECT_MISMATCH", "发票登记合同必须属于当前项目。"))
            if record.contract_id.partner_id and record.partner_id and record.contract_id.partner_id != record.partner_id:
                gates.append(self._gate("INVOICE_REGISTRATION_CONTRACT_PARTNER_MISMATCH", "发票登记往来单位必须与合同相对方一致。"))
        if record.settlement_id:
            if record.settlement_id.project_id != record.project_id:
                gates.append(self._gate("INVOICE_REGISTRATION_SETTLEMENT_PROJECT_MISMATCH", "发票登记结算单必须属于当前项目。"))
            if record.settlement_id.contract_id and record.contract_id and record.settlement_id.contract_id != record.contract_id:
                gates.append(self._gate("INVOICE_REGISTRATION_SETTLEMENT_CONTRACT_MISMATCH", "发票登记合同必须与结算单合同一致。"))
            if record.settlement_id.partner_id and record.partner_id and record.settlement_id.partner_id != record.partner_id:
                gates.append(self._gate("INVOICE_REGISTRATION_SETTLEMENT_PARTNER_MISMATCH", "发票登记往来单位必须与结算单往来单位一致。"))
        if getattr(record, "validation_status", "") in ("waiting", "pending"):
            gates.append(
                self._gate(
                    "INVOICE_REGISTRATION_APPROVAL_IN_PROGRESS",
                    "发票登记已经在统一审批流程中，请等待审批完成后再重复提交。",
                    action_keys=["submit", "cancel"],
                )
            )
        return gates

    @api.model
    def _self_funding_registration_evidence_gate(self, record):
        gates = []
        if not record.project_id:
            gates.append(self._gate("SELF_FUNDING_MISSING_PROJECT", "请先选择项目。"))
        if not record.partner_id:
            gates.append(self._gate("SELF_FUNDING_MISSING_PARTNER", "请先选择承包人。"))
        if not record.document_date:
            gates.append(self._gate("SELF_FUNDING_MISSING_DATE", "请先填写发生日期。"))
        if (record.amount or 0.0) <= 0:
            gates.append(self._gate("SELF_FUNDING_INVALID_AMOUNT", "自筹办理金额必须大于 0。"))
        if getattr(record, "source_origin", "") == "manual":
            if not record.attachment_ids:
                gates.append(self._gate("SELF_FUNDING_ATTACHMENT_REQUIRED", "请上传自筹办理附件，作为公司与承包人资金责任的办理依据。"))
            if not record.payment_account_name:
                gates.append(self._gate("SELF_FUNDING_MISSING_COMPANY_ACCOUNT", "请填写公司账户/户名。"))
            if not record.partner_account_name:
                gates.append(self._gate("SELF_FUNDING_MISSING_PARTNER_ACCOUNT", "请填写承包人账户/户名。"))
        if getattr(record, "validation_status", "") in ("waiting", "pending"):
            gates.append(
                self._gate(
                    "SELF_FUNDING_APPROVAL_IN_PROGRESS",
                    "自筹办理已经在统一审批流程中，请等待审批完成后再重复提交。",
                    action_keys=["submit"],
                )
            )
        return gates

    @api.model
    def _financing_loan_evidence_gate(self, record):
        if getattr(record, "source_origin", "") == "legacy" and getattr(record, "state", "") == "legacy_confirmed":
            return []
        gates = []
        if not record.project_id:
            gates.append(self._gate("FINANCING_LOAN_MISSING_PROJECT", "融资借款必须关联项目。"))
        if not record.partner_id:
            gates.append(self._gate("FINANCING_LOAN_MISSING_PARTNER", "请先选择往来单位后再完成融资借款。"))
        if not record.document_date:
            gates.append(self._gate("FINANCING_LOAN_MISSING_DATE", "请先填写单据日期后再完成融资借款。"))
        if (record.amount or 0.0) <= 0:
            gates.append(self._gate("FINANCING_LOAN_INVALID_AMOUNT", "融资借款金额必须大于 0。"))
        if record.loan_type == "borrowing_request" and record.direction == "borrowed_fund":
            allowed_codes = {
                "finance.loan.contractor_project_borrow",
                "finance.loan.project_borrow_company",
            }
            if record.business_category_id.code not in allowed_codes:
                gates.append(
                    self._gate(
                        "FINANCING_LOAN_INVALID_BORROWING_CATEGORY",
                        "借款办理必须选择“承包人借项目款”或“项目借公司款登记”业务分类后才能完成。",
                    )
                )
        if getattr(record, "validation_status", "") in ("waiting", "pending"):
            gates.append(
                self._gate(
                    "FINANCING_LOAN_APPROVAL_IN_PROGRESS",
                    "融资借款已经在统一审批流程中，请等待审批完成后再重复提交。",
                    action_keys=["submit"],
                )
            )
        return gates

    @api.model
    def _treasury_reconciliation_evidence_gate(self, record):
        if getattr(record, "source_origin", "") == "legacy" and getattr(record, "state", "") == "legacy_confirmed":
            return []
        gates = []
        for code, message in record._reconcile_readiness_errors():
            gates.append(self._gate(code, message))
        if getattr(record, "validation_status", "") in ("waiting", "pending"):
            gates.append(
                self._gate(
                    "TREASURY_RECONCILIATION_APPROVAL_IN_PROGRESS",
                    "资金对账已经在统一审批流程中，请等待审批完成后再重复提交。",
                    action_keys=["submit"],
                )
            )
        return gates

    @api.model
    def _settlement_adjustment_evidence_gate(self, record):
        if getattr(record, "source_origin", "") == "legacy" and getattr(record, "state", "") == "legacy_confirmed":
            return []
        gates = []
        for code, message in record._business_anchor_errors():
            gates.append(self._gate(code, message, action_keys=["submit", "approve"]))
        if getattr(record, "validation_status", "") in ("waiting", "pending"):
            gates.append(
                self._gate(
                    "SETTLEMENT_ADJUSTMENT_APPROVAL_IN_PROGRESS",
                    "结算调整已经在统一审批流程中，请等待审批完成后再重复提交。",
                    action_keys=["submit"],
                )
            )
        return gates
