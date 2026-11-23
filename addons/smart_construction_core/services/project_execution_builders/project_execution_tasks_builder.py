# -*- coding: utf-8 -*-
from __future__ import annotations

from odoo import fields

from odoo.addons.smart_construction_core.services.project_dashboard_builders.base import BaseProjectBlockBuilder
from odoo.addons.smart_construction_core.services.project_task_state_support import (
    ProjectTaskStateSupport,
)


class ProjectExecutionTasksBuilder(BaseProjectBlockBuilder):
    block_key = "block.project.execution_tasks"
    block_type = "execution_task_list"
    title = "执行任务"
    required_groups = ()

    def build(self, project=None, context=None):
        visibility = self._visibility()
        empty_data = {
            "items": [],
            "summary": {
                "count": 0,
                "open_count": 0,
                "blocked_count": 0,
                "overdue_count": 0,
                "in_progress_count": 0,
                "done_count": 0,
                "cancelled_count": 0,
                "task_completion_percent": 0.0,
                "explicit_count": 0,
                "source_model": "project.task",
                "state_field": "state",
                "empty_hint": "当前项目还没有施工执行任务。合同、付款和结算属于业务待办，不在此处以任务呈现。",
            },
        }
        if not visibility.get("allowed"):
            return self._envelope(state="forbidden", visibility=visibility, data=empty_data)
        if not project:
            return self._envelope(state="empty", visibility=visibility, data=empty_data)

        model = self._model("project.task")
        if model is None:
            return self._envelope(state="empty", visibility=visibility, data=empty_data)

        domain = self._project_domain("project.task", project)
        rows = []
        try:
            rows = model.search(domain, order="priority desc, write_date desc, id desc", limit=6)
        except Exception:
            rows = []

        items = []
        metrics = ProjectTaskStateSupport.native_metrics(rows, model)
        open_states = set(ProjectTaskStateSupport.native_open_states(model))
        overdue_count = 0
        explicit_count = 0
        today = fields.Date.today()
        state_selection = dict(
            (model.fields_get(["state"]).get("state") or {}).get("selection") or []
        )
        for task in rows:
            explicit_count += 1
            task_state = str(getattr(task, "state", "") or "")
            is_open = task_state in open_states
            deadline_value = getattr(task, "date_deadline", False)
            deadline = str(deadline_value or "")
            if is_open and deadline_value and deadline_value < today:
                overdue_count += 1
            items.append(
                {
                    "task_id": int(task.id),
                    "task_kind": "explicit",
                    "source_model": "project.task",
                    "source_id": int(task.id),
                    "name": str(getattr(task, "name", "") or ""),
                    "assignee_name": str(getattr(getattr(task, "user_ids", False)[:1], "display_name", "") or ""),
                    "stage_name": str(getattr(getattr(task, "stage_id", None), "display_name", "") or ""),
                    "deadline": deadline,
                    "state": task_state,
                    "state_label": str(state_selection.get(task_state) or task_state),
                }
            )

        return self._envelope(
            state="ready" if items else "empty",
            visibility=visibility,
            data={
                "items": items,
                "summary": {
                    "count": len(items),
                    "open_count": metrics["task_open_count"],
                    "blocked_count": metrics["task_waiting_count"],
                    "in_progress_count": metrics["task_in_progress_count"],
                    "overdue_count": overdue_count,
                    "done_count": metrics["task_done_count"],
                    "cancelled_count": metrics["task_cancelled_count"],
                    "task_completion_percent": metrics["task_completion_percent"],
                    "explicit_count": explicit_count,
                    "source_model": "project.task",
                    "state_field": "state",
                    "empty_hint": "当前项目还没有施工执行任务。合同、付款和结算属于业务待办，不在此处以任务呈现。",
                },
            },
        )
