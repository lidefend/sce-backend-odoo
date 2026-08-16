# -*- coding: utf-8 -*-
"""Construction-standard terminal semantics for professional payment execution."""

from __future__ import annotations


def payment_execution_task_profile_v1() -> dict:
    return {
        "profile_version": "v1",
        "task": {
            "key": "finance.payment_execution.process",
            "goal": "核对付款事实并完成当前合法支付步骤",
            "outcome": "形成可审批、可实付、可冲销且可追溯的付款执行事实",
        },
        "facts": [
            {"key": "execution_identity", "label": "付款登记", "group": "identity", "importance": "primary"},
            {"key": "handling_subject", "label": "办理事项", "group": "identity", "importance": "primary"},
            {"key": "lifecycle_state", "label": "当前状态", "group": "identity", "importance": "primary"},
            {"key": "approval_state", "label": "审批状态", "group": "identity", "importance": "primary"},
            {"key": "source_request", "label": "来源申请", "group": "source", "importance": "primary"},
            {"key": "project", "label": "项目", "group": "source", "importance": "primary"},
            {"key": "payee", "label": "收款对象", "group": "source", "importance": "primary"},
            {"key": "contract", "label": "合同", "group": "source", "importance": "secondary"},
            {"key": "planned_amount", "label": "申请金额", "group": "amount", "importance": "primary"},
            {"key": "paid_amount", "label": "本次实付", "group": "amount", "importance": "primary"},
            {"key": "payment_method", "label": "付款方式", "group": "payment", "importance": "primary"},
            {"key": "receipt_account_name", "label": "收款户名", "group": "receipt_account", "importance": "primary"},
            {"key": "receipt_bank_name", "label": "收款开户行", "group": "receipt_account", "importance": "secondary"},
            {"key": "receipt_account_no", "label": "收款账号", "group": "receipt_account", "importance": "primary"},
            {"key": "payment_account_name", "label": "付款户名", "group": "payment_account", "importance": "primary"},
            {"key": "payment_bank_name", "label": "付款开户行", "group": "payment_account", "importance": "secondary"},
            {"key": "payment_account_no", "label": "付款账号", "group": "payment_account", "importance": "primary"},
            {"key": "responsibility_state", "label": "资金责任状态", "group": "responsibility", "importance": "secondary"},
            {"key": "cancellation_kind", "label": "撤销类型", "group": "audit", "importance": "secondary"},
        ],
        "inputs": [
            {"key": "payment_date", "label": "付款日期", "group": "payment", "input_kind": "date"},
            {"key": "actual_amount", "label": "本次实付", "group": "payment", "input_kind": "money"},
            {"key": "payment_method_input", "label": "付款方式", "group": "payment", "input_kind": "text"},
            {"key": "payment_account_name_input", "label": "付款户名", "group": "payment_account", "input_kind": "text"},
            {"key": "payment_bank_name_input", "label": "付款开户行", "group": "payment_account", "input_kind": "text"},
            {"key": "payment_account_no_input", "label": "付款账号", "group": "payment_account", "input_kind": "text"},
            {"key": "note", "label": "办理说明", "group": "evidence", "input_kind": "multiline"},
            {"key": "reversal_reason", "label": "冲销原因", "group": "audit", "input_kind": "multiline"},
        ],
        "blockers": [
            {
                "key": "payment_fact_readiness",
                "label": "付款事实完整度",
                "repair_capability_key": "payment_execution.complete_facts",
                "owner": "finance_operator",
            },
        ],
        "capabilities": [
            {"key": "payment_execution.submit", "label": "提交审批", "presentation": "primary", "safety": "confirm", "idempotency": "record_transition", "outcome": "submitted", "blocked_by": ["payment_fact_readiness"]},
            {"key": "payment_execution.approve", "label": "审批通过", "presentation": "primary", "safety": "confirm", "idempotency": "record_transition", "outcome": "confirmed", "blocked_by": [], "handoff": "finance_approver"},
            {"key": "payment_execution.reject", "label": "审批驳回", "presentation": "secondary", "safety": "reason_required", "idempotency": "record_transition", "outcome": "rejected", "blocked_by": [], "handoff": "finance_operator"},
            {"key": "payment_execution.mark_paid", "label": "登记已付款", "presentation": "primary", "safety": "confirm", "idempotency": "ledger_posting", "outcome": "paid", "blocked_by": ["payment_fact_readiness"], "handoff": "finance_manager"},
            {"key": "payment_execution.cancel", "label": "取消付款登记", "presentation": "secondary", "safety": "confirm", "idempotency": "record_transition", "outcome": "cancelled", "blocked_by": [], "handoff": "finance_manager"},
            {"key": "payment_execution.reverse", "label": "冲销付款", "presentation": "secondary", "safety": "reason_required", "idempotency": "ledger_reversal", "outcome": "reversed", "blocked_by": [], "handoff": "finance_manager"},
            {"key": "payment_execution.complete_facts", "label": "补全付款事实", "presentation": "recommended", "safety": "safe_navigation", "idempotency": "read_only", "outcome": "payment_facts_edit_opened", "blocked_by": []},
        ],
        "evidence": [
            {"key": "attachments", "label": "付款凭证", "kind": "attachment", "group": "evidence"},
            {"key": "approval_audit", "label": "审批与审计", "kind": "audit", "group": "audit"},
        ],
        "relations": [
            {"key": "request_anchor", "label": "付款申请", "kind": "anchor", "group": "source"},
            {"key": "project_anchor", "label": "项目", "kind": "anchor", "group": "source"},
            {"key": "payee_anchor", "label": "往来单位", "kind": "anchor", "group": "source"},
            {"key": "contract_anchor", "label": "合同", "kind": "anchor", "group": "source"},
        ],
    }
