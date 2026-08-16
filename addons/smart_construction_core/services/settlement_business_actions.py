# -*- coding: utf-8 -*-
"""Authoritative settlement action verdicts for the normalized form contract."""

from __future__ import annotations


def _text(value) -> str:
    return str(value or "").strip()


def _has_group(record, xmlid: str) -> bool:
    try:
        return bool(record.env.user.has_group(xmlid))
    except Exception:
        return False


def _precheck(record, *, strict: bool) -> tuple[bool, str]:
    try:
        record._check_business_anchor_or_raise()
        record._check_line_contracts_or_raise()
        record._check_contract_consistency_or_raise(strict=strict)
        record._check_purchase_orders_or_raise(strict=strict)
    except Exception as exc:
        return False, _text(exc) or "结算事实尚未满足办理条件。"
    return True, ""


def _cancel_precheck(record) -> tuple[bool, str]:
    try:
        record._check_payments_before_cancel()
    except Exception as exc:
        return False, _text(exc) or "结算单存在不可取消的付款事实。"
    return True, ""


def build_settlement_task_semantics(record) -> dict:
    """Materialize blocker verdicts beside the model-owned action verdicts."""

    if not record or _text(getattr(record, "_name", "")) != "sc.settlement.order":
        return {}
    missing_scope = [
        label
        for value, label in (
            (getattr(record, "project_id", None), "项目"),
            (getattr(record, "partner_id", None) or getattr(record, "legacy_fact_model", None), "往来单位"),
            (getattr(record, "line_ids", None), "结算明细"),
        )
        if not value
    ]
    state = _text(getattr(record, "state", ""))
    scope_ready = not missing_scope
    scope_message = ""
    if scope_ready:
        try:
            record._check_line_contracts_or_raise()
            record._check_contract_consistency_or_raise(strict=state in {"submit", "approve", "done"})
            record._check_purchase_orders_or_raise(strict=state in {"submit", "approve", "done"})
        except Exception as exc:
            scope_ready = False
            scope_message = _text(exc) or "合同、项目或结算明细范围不一致。"
    elif missing_scope:
        scope_message = "请补齐" + "、".join(missing_scope) + "。"
    amount = getattr(record, "amount_total", None)
    amount_ready = isinstance(amount, (int, float)) and amount > 0
    return {
        "version": "v1",
        "source_authority": "settlement_order_model_prechecks",
        "blockers": {
            "contract_scope_consistency": {
                "active": not scope_ready,
                "reason_code": "SETTLEMENT_SCOPE_INCOMPLETE" if not scope_ready else "",
                "message": scope_message if not scope_ready else "",
                "missing_items": missing_scope,
                "source_authority": "settlement_order_model_prechecks.scope",
            },
            "amount_readiness": {
                "active": not amount_ready,
                "reason_code": "SETTLEMENT_AMOUNT_INCOMPLETE" if not amount_ready else "",
                "message": "结算金额必须大于零。" if not amount_ready else "",
                "missing_items": ["结算金额"] if not amount_ready else [],
                "source_authority": "settlement_order_model_prechecks.amount",
            },
        },
    }


def _action(
    *,
    key: str,
    label: str,
    method: str,
    business_available: bool,
    authorization_allowed: bool,
    reason_code: str = "",
    blocked_message: str = "",
    primary: bool = False,
    requires_reason: bool = False,
) -> dict:
    executable = bool(business_available and authorization_allowed)
    if business_available and not authorization_allowed:
        reason_code = "ROLE_HANDOFF_REQUIRED"
        blocked_message = blocked_message or "请移交具有当前结算办理能力的人员。"
    elif not executable and not reason_code:
        reason_code = "ACTION_NOT_ALLOWED"
    return {
        "key": f"settlement_order_{key}",
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
        "presentation_authority": "settlement_order_capability",
        "presentation_priority": 370 if primary else 320,
        "action_safety": {
            "classification": "danger" if requires_reason else "normal",
            "requires_confirm": True,
            "reason_code": "BUSINESS_STATE_TRANSITION",
        },
        "refresh_policy": {
            "on_success": ["scene_projection"],
            "mode": "reload_record",
            "scope": "record",
        },
    }


def build_settlement_form_actions(record) -> list[dict]:
    """Return applicable actions; never turn a role hint into authorization."""

    if not record or _text(getattr(record, "_name", "")) != "sc.settlement.order":
        return []
    state = _text(getattr(record, "state", ""))
    validation_status = _text(getattr(record, "validation_status", ""))
    can_submit = _has_group(record, "smart_construction_core.group_sc_cap_business_initiator") or _has_group(
        record,
        "smart_construction_core.group_sc_cap_settlement_user",
    )
    can_manage = _has_group(record, "smart_construction_core.group_sc_cap_settlement_manager")
    can_review = bool(getattr(record, "can_review", False)) and can_manage
    approval_pending = validation_status in {"waiting", "pending"}
    actions: list[dict] = []

    if state == "draft" and not approval_pending and validation_status != "validated":
        ready, message = _precheck(record, strict=False)
        actions.append(_action(
            key="submit",
            label="提交审批",
            method="action_submit",
            business_available=ready,
            authorization_allowed=can_submit,
            reason_code="SETTLEMENT_FACTS_INCOMPLETE" if not ready else "",
            blocked_message=message,
            primary=True,
        ))
    if state == "submit" and approval_pending:
        ready, message = _precheck(record, strict=True)
        actions.extend((
            _action(
                key="approve",
                label="审批通过",
                method="validate_tier",
                business_available=ready,
                authorization_allowed=can_review,
                reason_code="SETTLEMENT_FACTS_INCOMPLETE" if not ready else "",
                blocked_message=message,
                primary=True,
            ),
            _action(
                key="reject",
                label="审批驳回",
                method="reject_tier",
                business_available=True,
                authorization_allowed=can_review,
                requires_reason=True,
            ),
        ))
    if state == "submit" and validation_status == "validated":
        ready, message = _precheck(record, strict=True)
        actions.append(_action(
            key="record_approval",
            label="批准",
            method="action_approve",
            business_available=ready,
            authorization_allowed=can_manage,
            reason_code="SETTLEMENT_FACTS_INCOMPLETE" if not ready else "",
            blocked_message=message,
            primary=True,
        ))
    if state == "approve":
        ready, message = _precheck(record, strict=True)
        actions.append(_action(
            key="complete",
            label="完成结算",
            method="action_done",
            business_available=ready,
            authorization_allowed=can_manage,
            reason_code="SETTLEMENT_FACTS_INCOMPLETE" if not ready else "",
            blocked_message=message,
            primary=True,
        ))
    if state in {"draft", "submit", "approve"}:
        ready, message = _cancel_precheck(record)
        actions.append(_action(
            key="cancel",
            label="取消结算",
            method="action_cancel",
            business_available=ready,
            authorization_allowed=can_manage,
            reason_code="SETTLEMENT_PAYMENT_EXISTS" if not ready else "",
            blocked_message=message,
            requires_reason=True,
        ))
    return actions
