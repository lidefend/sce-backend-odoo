# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import date

from odoo.addons.smart_construction_core.services.project_state_explain_service import lifecycle_state_label


def operation_strategy_label(value):
    labels = {
        "direct": "公司直营",
        "joint": "联营项目",
    }
    return labels.get(str(value or "").strip(), "")


def select_project_milestone(project):
    if not project or "milestone_ids" not in getattr(project, "_fields", {}):
        return False
    milestones = getattr(project, "milestone_ids", False)
    if not milestones:
        return False
    unreached = milestones.filtered(lambda row: not getattr(row, "is_reached", False))
    if unreached:
        return unreached.sorted(
            lambda row: (
                getattr(row, "deadline", False) or date.max,
                int(row.id or 0),
            )
        )[:1]
    reached = milestones.filtered(lambda row: getattr(row, "is_reached", False))
    if reached:
        return reached.sorted(
            lambda row: (
                getattr(row, "reached_date", False) or date.min,
                int(row.id or 0),
            ),
            reverse=True,
        )[:1]
    return False


def build_project_context(project):
    if not project:
        return {
            "company_id": 0,
            "company_name": "",
            "project_id": 0,
            "project_name": "",
            "operation_strategy": "",
            "operation_strategy_label": "",
            "execution_stage": "",
            "execution_stage_label": "",
            "stage": "",
            "stage_label": "",
            "milestone": "",
            "milestone_label": "",
            "project_condition": "",
            "status": "",
        }
    execution_stage = str(getattr(project, "lifecycle_state", "") or "").strip()
    operation_strategy = str(getattr(project, "operation_strategy", "") or "").strip()
    company = getattr(project, "company_id", None)
    execution_stage_label = lifecycle_state_label(project, default="")
    milestone_record = select_project_milestone(project)
    milestone = str(milestone_record.display_name or "").strip() if milestone_record else ""
    milestone_label = milestone
    project_condition = str(getattr(project, "health_state", "") or getattr(project, "state", "") or "").strip()
    return {
        "company_id": int(getattr(company, "id", 0) or 0),
        "company_name": str(getattr(company, "display_name", "") or getattr(company, "name", "") or "").strip(),
        "project_id": int(getattr(project, "id", 0) or 0),
        "project_name": str(getattr(project, "display_name", "") or getattr(project, "name", "") or "").strip(),
        "operation_strategy": operation_strategy,
        "operation_strategy_label": operation_strategy_label(operation_strategy) or operation_strategy,
        "execution_stage": execution_stage,
        "execution_stage_label": execution_stage_label or execution_stage,
        "stage": execution_stage,
        "stage_label": execution_stage_label or execution_stage,
        "milestone": milestone,
        "milestone_label": milestone_label or milestone,
        "project_condition": project_condition,
        "status": project_condition,
    }


def attach_project_context_to_scene_payload(data, project):
    payload = dict(data or {})
    project_context = build_project_context(project)
    payload["project_context"] = project_context
    runtime_fetch_hints = payload.get("runtime_fetch_hints")
    blocks = runtime_fetch_hints.get("blocks") if isinstance(runtime_fetch_hints, dict) else None
    if isinstance(blocks, dict):
        for row in blocks.values():
            if not isinstance(row, dict):
                continue
            params = dict(row.get("params") or {})
            params.setdefault("project_id", project_context.get("project_id") or 0)
            params["project_context"] = project_context
            row["params"] = params
    return payload


def attach_project_context_to_runtime_payload(data, project):
    payload = dict(data or {})
    payload["project_context"] = build_project_context(project)
    return payload
