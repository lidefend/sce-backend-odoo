# -*- coding: utf-8 -*-
"""Construction-standard semantics for one approval work item."""

from __future__ import annotations


def approval_work_item_task_profile_v1() -> dict:
    return {
        "profile_version": "v1",
        "task": {
            "key": "governance.approval_work_item.process",
            "goal": "核对业务依据并完成当前审批决定",
            "outcome": "形成有结论、有意见且可追溯的审批事实",
        },
        "facts": [
            {"key": "work_item_identity", "label": "审批事项", "group": "identity", "importance": "primary"},
            {"key": "business_subject", "label": "业务主题", "group": "identity", "importance": "primary"},
            {"key": "current_stage", "label": "当前审批阶段", "group": "status", "importance": "primary"},
            {"key": "applicant", "label": "发起人", "group": "responsibility", "importance": "primary"},
            {"key": "responsible_company", "label": "责任公司", "group": "responsibility", "importance": "secondary"},
            {"key": "submitted_at", "label": "提交时间", "group": "timeline", "importance": "secondary"},
            {"key": "due_state", "label": "办理时效", "group": "timeline", "importance": "primary"},
        ],
        "inputs": [
            {"key": "decision_comment", "label": "审批意见", "group": "decision", "input_kind": "multiline"},
        ],
        "blockers": [
            {
                "key": "evidence_readiness",
                "label": "审批依据完整度",
                "repair_capability_key": "approval_work_item.open_source",
                "owner": "business_initiator",
            },
        ],
        "capabilities": [
            {"key": "approval_work_item.open_source", "label": "查看业务依据", "presentation": "recommended", "safety": "safe_read", "idempotency": "read_only", "outcome": "source_opened", "blocked_by": []},
            {"key": "approval_work_item.approve", "label": "审批通过", "presentation": "primary", "safety": "confirm", "idempotency": "record_transition", "outcome": "approved", "blocked_by": ["evidence_readiness"]},
            {"key": "approval_work_item.reject", "label": "审批驳回", "presentation": "secondary", "safety": "reason_required", "idempotency": "record_transition", "outcome": "rejected", "blocked_by": []},
            {"key": "approval_work_item.handoff", "label": "转交有权审批人", "presentation": "recommended", "safety": "confirm", "idempotency": "record_transition", "outcome": "handed_off", "blocked_by": [], "handoff": "next_approver"},
        ],
        "evidence": [
            {"key": "source_documents", "label": "业务依据", "kind": "document", "group": "evidence"},
            {"key": "approval_history", "label": "审批历史", "kind": "audit", "group": "audit"},
        ],
        "relations": [
            {"key": "source_record", "label": "来源业务", "kind": "anchor", "group": "source"},
            {"key": "workflow_instance", "label": "审批流程", "kind": "trace", "group": "audit"},
        ],
    }
