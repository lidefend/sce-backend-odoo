# -*- coding: utf-8 -*-
from __future__ import annotations

from odoo import fields

from odoo.addons.smart_construction_core.services.project_task_state_support import (
    ProjectTaskStateSupport,
)

from .base import BaseProjectBlockBuilder


class ProjectProgressBuilder(BaseProjectBlockBuilder):
    block_key = "block.project.progress"
    block_type = "progress_summary"
    title = "项目进度"
    required_groups = ()

    def build(self, project=None, context=None):
        visibility = self._visibility()
        if not visibility.get("allowed"):
            return self._envelope(
                state="forbidden",
                visibility=visibility,
                data={
                    "task_total": 0,
                    "task_done": 0,
                    "task_open": 0,
                    "task_cancelled": 0,
                    "task_critical": 0,
                    "task_blocked": 0,
                    "task_overdue": 0,
                    "completion_percent": 0.0,
                    "project_progress_percent": 0.0,
                    "task_completion_percent": 0.0,
                    "milestone_total": 0,
                    "milestone_done": 0,
                    "milestone_delay": 0,
                    "milestone_progress": 0.0,
                    "milestone_upcoming_days": 0,
                    "critical_path_health": "unknown",
                },
            )
        if not project:
            return self._envelope(
                state="empty",
                visibility=visibility,
                data={
                    "task_total": 0,
                    "task_done": 0,
                    "task_open": 0,
                    "task_cancelled": 0,
                    "task_critical": 0,
                    "task_blocked": 0,
                    "task_overdue": 0,
                    "completion_percent": 0.0,
                    "project_progress_percent": 0.0,
                    "task_completion_percent": 0.0,
                    "milestone_total": 0,
                    "milestone_done": 0,
                    "milestone_delay": 0,
                    "milestone_progress": 0.0,
                    "milestone_upcoming_days": 0,
                    "critical_path_health": "unknown",
                },
            )

        task_domain = self._project_domain("project.task", project)
        task_model = self._model("project.task")
        tasks = task_model.search(task_domain) if task_model is not None else []
        task_metrics = ProjectTaskStateSupport.native_metrics(tasks, task_model)
        total = task_metrics["task_total"]
        done = task_metrics["task_done_count"]
        blocked = task_metrics["task_waiting_count"]
        critical = self._safe_count("project.task", task_domain + [("priority", "in", ["2", "3"])]) if self._model_has_fields("project.task", ["priority"]) else 0
        open_states = ProjectTaskStateSupport.native_open_states(task_model)
        now = fields.Datetime.now()
        overdue = len([
            task for task in tasks
            if str(getattr(task, "state", "") or "") in open_states
            and getattr(task, "date_deadline", False)
            and fields.Datetime.to_datetime(task.date_deadline) < now
        ])
        open_count = task_metrics["task_open_count"]
        task_completion_percent = task_metrics["task_completion_percent"]
        project_progress_percent = float(
            getattr(project, "dashboard_progress_rate", 0.0)
            or getattr(project, "progress_rate_latest", 0.0)
            or 0.0
        )

        milestone_domain = self._project_domain("project.milestone", project)
        milestone_total = self._safe_count("project.milestone", milestone_domain)
        milestone_done = self._safe_count("project.milestone", milestone_domain + [("is_reached", "=", True)])
        milestone_delay = self._safe_count(
            "project.milestone",
            milestone_domain + [
                ("is_reached", "=", False),
                ("deadline", "<", fields.Date.today()),
            ],
        )
        milestone_progress = self._safe_rate(milestone_done, milestone_total)
        milestone_upcoming_days = 0
        if self._model_has_fields("project.milestone", ["deadline", "is_reached"]):
            next_row = self.env["project.milestone"].search(
                milestone_domain + [
                    ("is_reached", "=", False),
                    ("deadline", "!=", False),
                ],
                order="deadline asc",
                limit=1,
            )
            if next_row and next_row.deadline:
                delta = (next_row.deadline - fields.Date.today()).days
                milestone_upcoming_days = int(delta)

        critical_path_health = "normal"
        if blocked > 0 or overdue > 0:
            critical_path_health = "risk"
        if blocked > 1 or overdue > 2:
            critical_path_health = "critical"

        data = {
            "task_total": total,
            "task_done": done,
            "task_open": open_count,
            "task_cancelled": task_metrics["task_cancelled_count"],
            "task_critical": critical,
            "task_blocked": blocked,
            "task_overdue": overdue,
            "completion_percent": project_progress_percent,
            "project_progress_percent": project_progress_percent,
            "task_completion_percent": task_completion_percent,
            "milestone_total": milestone_total,
            "milestone_done": milestone_done,
            "milestone_delay": milestone_delay,
            "milestone_progress": milestone_progress,
            "milestone_upcoming_days": milestone_upcoming_days,
            "critical_path_health": critical_path_health,
            "summary": {
                "project_progress_percent": project_progress_percent,
                "task_completion_rate": task_completion_percent,
                "milestone_progress": milestone_progress,
                "delayed_tasks": overdue,
                "delayed_milestones": milestone_delay,
                "critical_task_count": critical,
                "blocked_task_count": blocked,
                "open_task_count": open_count,
                "critical_path_health": critical_path_health,
            },
        }
        return self._envelope(state="ready", visibility=visibility, data=data)
