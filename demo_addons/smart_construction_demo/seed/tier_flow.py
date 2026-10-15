# -*- coding: utf-8 -*-
"""Demo seed approvals share the scenario driver's declared business seats."""


def approve_tier_chain(record):
    """Consume actual pending reviews; no arbitrary reviewer or fallback seat."""
    from ..tools.scenario_loader import _demo_finish_reviews

    record.invalidate_recordset()
    _demo_finish_reviews(record.env, record)
    return record.validation_status == "validated"


def advance_settlement(settlement, *, complete=False, submitter_xmlid="smart_construction_demo.user_sc_settlement_user_cap"):
    """Submit and optionally finish through declared, non-superuser seats."""
    from odoo.exceptions import UserError
    from ..tools.scenario_loader import _demo_action_record

    if settlement.state == "draft":
        _demo_action_record(
            settlement.env, settlement, "action_submit",
            submitter_xmlid,
        ).action_submit()
        settlement.invalidate_recordset()
    if settlement.state == "submit":
        approve_tier_chain(settlement)
    if complete and settlement.state == "approve":
        _demo_action_record(
            settlement.env, settlement, "action_done",
            "smart_construction_demo.user_sc_settlement_manager_cap",
        ).action_done()
        settlement.invalidate_recordset()
    expected = ("done",) if complete else ("approve", "done")
    if settlement.state not in expected:
        raise UserError("Demo 结算单未能通过正式角色与审批状态机。")
    return settlement


def ensure_project_initiation_approved(project):
    """Carry a draft demo project through 立项 before any lifecycle change.

    ``action_set_lifecycle_state()`` asserts that initiation approval already
    passed, and ``sc_approval_state`` may only be written by the product's own
    actions, so a seed that starts a project must submit it first:
    ``action_sc_submit()`` completes initiation itself when no approval
    template is configured, and otherwise opens the tier chain, which is
    walked here.  Idempotent and never writes a state field directly.
    """
    from .business_roles import project_actor
    project = project_actor(project)
    if project.sc_approval_state != "draft":
        return project.sc_approval_state
    if not project.review_ids or project.validation_status == "rejected":
        project.action_sc_submit()
    project.invalidate_recordset()
    if project.sc_approval_state == "draft" and project.review_ids:
        approve_tier_chain(project)
        project.invalidate_recordset()
    return project.sc_approval_state
