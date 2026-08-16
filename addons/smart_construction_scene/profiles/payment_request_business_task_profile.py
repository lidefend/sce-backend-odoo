# -*- coding: utf-8 -*-
"""Construction-standard task semantics for a professional payment request.

This profile contains wording, grouping and task relationships only. Values,
state, blockers and capability verdicts are supplied by authoritative domain
services before the scene compiler is invoked.
"""

from __future__ import annotations


def payment_request_task_profile_v1() -> dict:
    return {
        "profile_version": "v1",
        "task": {
            "key": "finance.payment_request.process",
            "goal": "核对付款依据并完成当前合法办理步骤",
            "outcome": "形成可审批、可支付且可追溯的付款事实",
        },
        "facts": [
            {"key": "request_identity", "label": "付款申请", "group": "identity", "importance": "primary", "source_binding": {"field": "name"}},
            {"key": "handling_subject", "label": "办理事项", "group": "identity", "importance": "primary", "source_binding": {"field": "payment_flow_label"}},
            {"key": "lifecycle_state", "label": "当前状态", "group": "identity", "importance": "primary", "source_binding": {"field": "state"}},
            {"key": "project", "label": "项目", "group": "counterparty", "importance": "primary", "source_binding": {"field": "project_id"}},
            {"key": "payee", "label": "收款对象", "group": "counterparty", "importance": "primary", "source_binding": {"field": "partner_id"}},
            {"key": "payment_basis", "label": "付款依据", "group": "basis", "importance": "primary", "source_binding": {"field": "payment_basis_type"}},
            {"key": "requested_amount", "label": "申请金额", "group": "amount", "importance": "primary", "source_binding": {"field": "amount"}},
            {"key": "payable_balance", "label": "可付余额", "group": "amount", "importance": "primary", "source_binding": {"field": "unpaid_amount"}},
            {"key": "account_readiness", "label": "账户完整度", "group": "account", "importance": "primary", "source_binding": {"field": "payee_account_completeness"}},
            {"key": "account_source", "label": "账户来源", "group": "account", "importance": "secondary", "source_binding": {"field": "payee_account_source_display"}},
            {"key": "execution_status", "label": "付款执行状态", "group": "execution", "importance": "primary", "source_binding": {"field": "payment_execution_status_display"}},
            {"key": "blocking_summary", "label": "业务阻断", "group": "status", "importance": "primary", "source_binding": {"field": "payment_blocking_reason_display"}},
            {"key": "legal_next_step", "label": "下一步", "group": "status", "importance": "primary", "source_binding": {"field": "legal_next_action_display"}},
        ],
        "inputs": [
            {"key": "application_note", "label": "办理说明", "group": "evidence", "input_kind": "multiline", "source_binding": {"field": "note"}},
        ],
        "blockers": [
            {
                "key": "counterparty_eligibility",
                "label": "往来单位办理资格",
                "repair_capability_key": "counterparty.resolve_eligibility",
                "owner": "counterparty_maintainer",
            },
            {
                "key": "payment_basis_readiness",
                "label": "付款依据完整度",
                "repair_capability_key": "payment_request.complete_basis",
                "owner": "business_initiator",
            },
            {
                "key": "payee_account_readiness",
                "label": "收款账户完整度",
                "repair_capability_key": "counterparty.maintain_settlement_account",
                "owner": "counterparty_maintainer",
            },
        ],
        "capabilities": [
            {
                "key": "payment_request.submit",
                "label": "提交审批",
                "presentation": "primary",
                "safety": "confirm",
                "idempotency": "record_transition",
                "outcome": "submitted",
                "blocked_by": ["counterparty_eligibility", "payment_basis_readiness"],
            },
            {
                "key": "payment_request.approve",
                "label": "审批通过",
                "presentation": "primary",
                "safety": "confirm",
                "idempotency": "record_transition",
                "outcome": "approved",
                "blocked_by": ["counterparty_eligibility", "payment_basis_readiness"],
                "handoff": "finance_approver",
            },
            {
                "key": "payment_request.reject",
                "label": "审批驳回",
                "presentation": "secondary",
                "safety": "reason_required",
                "idempotency": "record_transition",
                "outcome": "rejected",
                "blocked_by": [],
                "handoff": "business_initiator",
            },
            {
                "key": "payment_execution.create",
                "label": "生成付款登记",
                "presentation": "primary",
                "safety": "confirm",
                "idempotency": "single_active_execution",
                "outcome": "payment_execution_created",
                "blocked_by": ["counterparty_eligibility", "payment_basis_readiness", "payee_account_readiness"],
                "handoff": "finance_operator",
            },
            {
                "key": "payment_execution.open",
                "label": "查看付款登记",
                "presentation": "primary",
                "safety": "safe_read",
                "idempotency": "read_only",
                "outcome": "payment_execution_opened",
                "blocked_by": [],
            },
            {
                "key": "payment_request.cancel",
                "label": "取消申请",
                "presentation": "secondary",
                "safety": "reason_required",
                "idempotency": "record_transition",
                "outcome": "cancelled",
                "blocked_by": [],
            },
            {
                "key": "counterparty.resolve_eligibility",
                "label": "处理往来单位资格",
                "presentation": "recommended",
                "safety": "safe_navigation",
                "idempotency": "read_only",
                "outcome": "eligibility_resolution_opened",
                "blocked_by": [],
                "handoff": "counterparty_maintainer",
            },
            {
                "key": "payment_request.complete_basis",
                "label": "补充付款依据",
                "presentation": "recommended",
                "safety": "safe_navigation",
                "idempotency": "read_only",
                "outcome": "payment_basis_edit_opened",
                "blocked_by": [],
                "handoff": "business_initiator",
            },
            {
                "key": "counterparty.maintain_settlement_account",
                "label": "维护结算账户",
                "presentation": "recommended",
                "safety": "safe_navigation",
                "idempotency": "read_only",
                "outcome": "settlement_account_opened",
                "blocked_by": [],
                "handoff": "counterparty_maintainer",
            },
        ],
        "evidence": [
            {"key": "attachments", "label": "附件", "kind": "attachment", "group": "evidence"},
            {"key": "approval_audit", "label": "审批与审计", "kind": "audit", "group": "audit"},
        ],
        "relations": [
            {"key": "project_anchor", "label": "项目", "kind": "anchor", "group": "source"},
            {"key": "payee_anchor", "label": "往来单位", "kind": "anchor", "group": "source"},
            {"key": "contract_anchor", "label": "合同", "kind": "anchor", "group": "source"},
            {"key": "settlement_anchor", "label": "结算依据", "kind": "anchor", "group": "source"},
            {"key": "payment_execution_relation", "label": "付款登记", "kind": "trace", "group": "execution"},
        ],
    }
