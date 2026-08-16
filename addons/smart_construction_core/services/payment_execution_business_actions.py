# -*- coding: utf-8 -*-
"""Authoritative payment-execution actions and terminal blocker semantics."""

from __future__ import annotations


def _text(value) -> str:
    return str(value or "").strip()


def _payment_fact_gaps(record) -> tuple[list[str], list[str]]:
    request = getattr(record, "payment_request_id", None)
    material_settlement = getattr(request, "material_settlement_id", None) if request else None
    has_basis = bool(getattr(record, "contract_id", None) or material_settlement)
    if request and not has_basis:
        checker = getattr(request, "_has_payment_basis", None)
        try:
            has_basis = bool(checker()) if callable(checker) else False
        except Exception:
            has_basis = False
    paid_amount = getattr(record, "paid_amount", None)
    amount_ready = isinstance(paid_amount, (int, float)) and paid_amount > 0
    missing = []
    repair_fields = []
    for value, label, repair_field in (
        (getattr(record, "project_id", None), "项目", ""),
        (request, "付款申请", ""),
        (has_basis, "合同或结算依据", ""),
        (getattr(record, "partner_id", None), "往来单位", ""),
        (amount_ready, "本次实付金额", "paid_amount"),
        (getattr(record, "payment_account_name", None), "付款户名", "payment_account_name"),
        (getattr(record, "payment_bank_name", None), "付款开户行", "payment_bank_name"),
        (getattr(record, "payment_account_no", None) or getattr(record, "bank_account", None), "付款账号", "payment_account_no"),
        (getattr(record, "receipt_account_name", None), "收款户名", ""),
        (getattr(record, "receipt_bank_name", None), "收款开户行", ""),
        (getattr(record, "receipt_account_no", None), "收款账号", ""),
        (_text(getattr(record, "payment_method", "")), "付款方式", "payment_method"),
    ):
        if not value:
            missing.append(label)
            if repair_field:
                repair_fields.append(repair_field)
    unpaid_amount = getattr(request, "unpaid_amount", None) if request else None
    if (
        isinstance(paid_amount, (int, float))
        and isinstance(unpaid_amount, (int, float))
        and paid_amount > unpaid_amount
    ):
        missing.append("剩余可付金额校验")
        repair_fields.append("paid_amount")
    return missing, repair_fields


def _payment_fact_precheck(record) -> tuple[bool, str]:
    try:
        record._check_business_anchor_or_raise()
        record._check_payment_request_scope_or_raise()
        record._check_company_contractor_payment_responsibility_or_raise()
    except Exception as exc:
        return False, _text(exc) or "付款事实尚未满足办理条件。"
    return True, ""


def build_payment_execution_task_semantics(record) -> dict:
    """Publish model-owned blocker facts without letting the terminal infer them."""

    if not record or _text(getattr(record, "_name", "")) != "sc.payment.execution":
        return {}
    state = _text(getattr(record, "state", ""))
    relevant = state in {"draft", "confirmed"} and _text(getattr(record, "source_origin", "")) != "legacy"
    ready, message = _payment_fact_precheck(record) if relevant else (True, "")
    missing_items, repair_fields = _payment_fact_gaps(record) if relevant and not ready else ([], [])
    return {
        "version": "v1",
        "source_authority": "payment_execution_model_prechecks",
        "blockers": {
            "payment_fact_readiness": {
                "active": bool(relevant and not ready),
                "reason_code": "PAYMENT_EXECUTION_FACTS_INCOMPLETE" if relevant and not ready else "",
                "message": message if relevant and not ready else "",
                "missing_items": missing_items,
                "repair_field_names": repair_fields,
                "source_authority": "payment_execution_model_prechecks.payment_facts",
            },
        },
    }


def _action(
    *,
    key,
    label,
    method,
    business_available,
    authorization_allowed,
    reason_code="",
    blocked_message="",
    primary=False,
    requires_reason=False,
):
    executable = bool(business_available and authorization_allowed)
    if business_available and not authorization_allowed:
        reason_code = "ROLE_HANDOFF_REQUIRED"
        blocked_message = blocked_message or "请移交具有当前付款办理能力的人员。"
    elif not executable and not reason_code:
        reason_code = "ACTION_NOT_ALLOWED"
    return {
        "key": f"payment_execution_{key}",
        "action_key": key,
        "label": label,
        "kind": "object",
        "level": "header",
        "target_scope": "page",
        "source_widget_id": "page.header",
        "selection": "none",
        "visible_profiles": ["edit", "readonly"],
        "method": method,
        "allowed": True,
        "enabled": executable,
        "disabled": not executable,
        "business_available": bool(business_available),
        "authorization_allowed": bool(authorization_allowed),
        "entitlement_evaluated": True,
        "reason_code": "" if executable else reason_code,
        "blocked_message": "" if executable else blocked_message,
        "requires_reason": bool(requires_reason),
        "primary": bool(primary and executable),
        "presentation": {
            "tier": "primary" if primary and executable else "secondary",
            "semantic": "primary_action" if primary and executable else "secondary_action",
        },
        "presentation_authority": "payment_execution_capability",
        "presentation_priority": 370 if primary else 320,
        "action_safety": {
            "classification": "danger" if requires_reason else "normal",
            "requires_confirm": True,
            "reason_code": "BUSINESS_STATE_TRANSITION",
        },
        "refresh_policy": {"on_success": ["scene_projection"], "mode": "reload_record", "scope": "record"},
    }


def build_payment_execution_form_actions(record, *, task_semantics=None) -> list[dict]:
    """Project model-owned state and exact capability verdicts."""

    if not record or _text(getattr(record, "_name", "")) != "sc.payment.execution":
        return []
    state = _text(record.state)
    validation_status = _text(record.validation_status)
    source_origin = _text(record.source_origin)
    finance_handler = bool(record._has_finance_handling_access())
    finance_manager = bool(record._has_finance_confirm_access())
    can_review = bool(record.can_review)
    actions = []

    semantics = task_semantics or build_payment_execution_task_semantics(record)
    blocker = (semantics.get("blockers") or {}).get("payment_fact_readiness") or {}
    precheck_ok = blocker.get("active") is False
    precheck_message = _text(blocker.get("message"))

    approval_pending = validation_status in {"waiting", "pending"}
    submit_applicable = state == "draft" and not approval_pending and validation_status != "validated"
    if submit_applicable:
        actions.append(_action(
            key="submit", label="提交审批", method="action_confirm",
            business_available=precheck_ok,
            authorization_allowed=finance_handler,
            reason_code="PAYMENT_EXECUTION_FACTS_INCOMPLETE" if not precheck_ok else "",
            blocked_message=precheck_message,
            primary=True,
        ))
    if approval_pending:
        actions.extend((
            _action(
                key="approve", label="审批通过", method="validate_tier",
                business_available=True, authorization_allowed=can_review,
                primary=True,
            ),
            _action(
                key="reject", label="审批驳回", method="reject_tier",
                business_available=True, authorization_allowed=can_review,
                requires_reason=True,
            ),
        ))
    if state == "confirmed":
        actions.append(_action(
            key="mark_paid", label="登记已付款", method="action_paid",
            business_available=precheck_ok,
            authorization_allowed=finance_manager,
            reason_code="PAYMENT_EXECUTION_FACTS_INCOMPLETE" if not precheck_ok else "",
            blocked_message=precheck_message,
            primary=True,
        ))
    if source_origin != "legacy" and state in {"draft", "confirmed"}:
        actions.append(_action(
            key="cancel", label="取消付款登记", method="action_cancel",
            business_available=True, authorization_allowed=finance_manager,
        ))
    if source_origin != "legacy" and state == "paid":
        reversal_ready = bool(_text(record.reversal_reason))
        actions.append(_action(
            key="reverse", label="冲销付款", method="action_reverse_payment",
            business_available=reversal_ready,
            authorization_allowed=finance_manager,
            reason_code="REVERSAL_REASON_REQUIRED" if not reversal_ready else "",
            blocked_message="请先填写冲销原因。" if not reversal_ready else "",
            requires_reason=True,
        ))
    return actions
