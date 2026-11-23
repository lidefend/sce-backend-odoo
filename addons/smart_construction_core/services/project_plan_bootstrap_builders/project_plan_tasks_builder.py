# -*- coding: utf-8 -*-
from __future__ import annotations

from odoo.addons.smart_construction_core.services.project_dashboard_builders.base import BaseProjectBlockBuilder


class ProjectPlanTasksBuilder(BaseProjectBlockBuilder):
    block_key = "block.project.plan_tasks"
    block_type = "task_list"
    title = "计划任务"
    required_groups = ()

    def build(self, project=None, context=None):
        visibility = self._visibility()
        empty_data = {"items": [], "summary": {"count": 0, "source_model": "project.task"}}
        if not visibility.get("allowed"):
            return self._envelope(state="forbidden", visibility=visibility, data=empty_data)
        if not project:
            return self._envelope(state="empty", visibility=visibility, data=empty_data)

        model = self._model("project.task")
        if model is None:
            return self._envelope(state="empty", visibility=visibility, data=empty_data)

        plan_model = self._model("sc.plan.line")
        if plan_model is None:
            return self._envelope(state="empty", visibility=visibility, data=empty_data)
        rows = []
        try:
            plan_lines = plan_model.search(
                [
                    ("plan_id.project_id", "=", int(project.id)),
                    ("wbs_id", "!=", False),
                ],
                order="sequence asc, id asc",
            )
            wbs_ids = plan_lines.mapped("wbs_id").ids
            if wbs_ids:
                rows = model.search(
                    [
                        ("project_id", "=", int(project.id)),
                        ("work_id", "in", wbs_ids),
                    ],
                    order="sequence asc, id asc",
                    limit=10,
                )
        except Exception:
            rows = []
        plan_by_wbs = {
            int(line.wbs_id.id): line
            for line in plan_lines
            if line.wbs_id
        } if rows else {}
        items = []
        for task in rows:
            plan_line = plan_by_wbs.get(int(getattr(task, "work_id", False).id or 0))
            items.append(
                {
                    "task_id": int(task.id),
                    "source_model": "project.task",
                    "source_id": int(task.id),
                    "plan_line_id": int(plan_line.id or 0) if plan_line else 0,
                    "plan_line_name": str(getattr(plan_line, "name", "") or "") if plan_line else "",
                    "wbs_id": int(getattr(task, "work_id", False).id or 0),
                    "wbs_name": str(getattr(getattr(task, "work_id", None), "display_name", "") or ""),
                    "name": str(getattr(task, "name", "") or ""),
                    "stage_name": str(getattr(getattr(task, "stage_id", None), "display_name", "") or ""),
                    "deadline": str(getattr(task, "date_deadline", "") or ""),
                    "state": str(getattr(task, "state", "") or ""),
                }
            )
        return self._envelope(
            state="ready" if items else "empty",
            visibility=visibility,
            data={"items": items, "summary": {"count": len(items), "source_model": "project.task"}},
        )
