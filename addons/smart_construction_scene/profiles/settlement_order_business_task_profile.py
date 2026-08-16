# -*- coding: utf-8 -*-
"""Construction-standard semantics for contract settlement handling."""

from __future__ import annotations


def settlement_order_task_profile_v1() -> dict:
    return {
        "profile_version": "v1",
        "task": {
            "key": "contract.settlement_order.process",
            "goal": "核对结算范围、金额与依据并完成当前合法办理步骤",
            "outcome": "形成可审批、可支付且与合同及项目一致的结算事实",
        },
        "facts": [
            {"key": "settlement_identity", "label": "结算单", "group": "identity", "importance": "primary"},
            {"key": "lifecycle_state", "label": "当前状态", "group": "identity", "importance": "primary"},
            {"key": "project", "label": "项目", "group": "source", "importance": "primary"},
            {"key": "contract", "label": "合同", "group": "source", "importance": "primary"},
            {"key": "counterparty", "label": "结算单位", "group": "source", "importance": "primary"},
            {"key": "submitted_amount", "label": "送审金额", "group": "amount", "importance": "primary"},
            {"key": "approved_amount", "label": "审定金额", "group": "amount", "importance": "primary"},
            {"key": "payable_balance", "label": "应付余额", "group": "amount", "importance": "primary"},
            {"key": "payment_progress", "label": "付款进度", "group": "payment", "importance": "secondary"},
            {"key": "legal_next_step", "label": "下一步", "group": "status", "importance": "primary"},
        ],
        "inputs": [
            {"key": "settlement_date", "label": "结算日期", "group": "basis", "input_kind": "date"},
            {"key": "submitted_amount_input", "label": "送审金额", "group": "amount", "input_kind": "money"},
            {"key": "approved_amount_input", "label": "审定金额", "group": "amount", "input_kind": "money"},
            {"key": "settlement_note", "label": "结算说明", "group": "evidence", "input_kind": "multiline"},
        ],
        "blockers": [
            {
                "key": "contract_scope_consistency",
                "label": "合同与项目范围一致性",
                "repair_capability_key": "settlement_order.repair_scope",
                "owner": "settlement_operator",
            },
            {
                "key": "amount_readiness",
                "label": "结算金额完整度",
                "repair_capability_key": "settlement_order.complete_amounts",
                "owner": "settlement_operator",
            },
        ],
        "capabilities": [
            {"key": "settlement_order.submit", "label": "提交审批", "presentation": "primary", "safety": "confirm", "idempotency": "record_transition", "outcome": "submitted", "blocked_by": ["contract_scope_consistency", "amount_readiness"]},
            {"key": "settlement_order.approve", "label": "审批通过", "presentation": "primary", "safety": "confirm", "idempotency": "record_transition", "outcome": "approved", "blocked_by": ["contract_scope_consistency", "amount_readiness"], "handoff": "settlement_approver"},
            {"key": "settlement_order.reject", "label": "审批驳回", "presentation": "secondary", "safety": "reason_required", "idempotency": "record_transition", "outcome": "rejected", "blocked_by": []},
            {"key": "settlement_order.complete", "label": "完成结算", "presentation": "primary", "safety": "confirm", "idempotency": "record_transition", "outcome": "completed", "blocked_by": ["contract_scope_consistency", "amount_readiness"]},
            {"key": "settlement_order.cancel", "label": "取消结算", "presentation": "secondary", "safety": "reason_required", "idempotency": "record_transition", "outcome": "cancelled", "blocked_by": []},
            {"key": "settlement_order.repair_scope", "label": "修正合同与项目", "presentation": "recommended", "safety": "safe_navigation", "idempotency": "read_only", "outcome": "scope_edit_opened", "blocked_by": []},
            {"key": "settlement_order.complete_amounts", "label": "补充结算金额", "presentation": "recommended", "safety": "safe_navigation", "idempotency": "read_only", "outcome": "amount_edit_opened", "blocked_by": []},
        ],
        "evidence": [
            {"key": "settlement_documents", "label": "结算依据", "kind": "attachment", "group": "evidence"},
            {"key": "approval_audit", "label": "审批与审计", "kind": "audit", "group": "audit"},
        ],
        "relations": [
            {"key": "project_anchor", "label": "项目", "kind": "anchor", "group": "source"},
            {"key": "contract_anchor", "label": "合同", "kind": "anchor", "group": "source"},
            {"key": "counterparty_anchor", "label": "往来单位", "kind": "anchor", "group": "source"},
            {"key": "payment_requests", "label": "付款申请", "kind": "trace", "group": "payment"},
        ],
    }
