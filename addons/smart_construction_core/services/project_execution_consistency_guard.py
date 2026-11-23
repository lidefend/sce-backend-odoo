# -*- coding: utf-8 -*-
from __future__ import annotations

from odoo.addons.smart_construction_core.services.project_execution_state_machine import (
    ProjectExecutionStateMachine,
)
from odoo.addons.smart_construction_core.services.project_task_state_support import (
    ProjectTaskStateSupport,
)


class ProjectExecutionConsistencyGuard:
    FOLLOWUP_SUMMARY = "执行推进跟进"
    SCOPE = "multi_task_native_dependency_execution"
    REQUIRED_PROJECT_FIELDS = (
        ("name", "项目名称"),
        ("project_code", "项目编码"),
        ("date_start", "计划开工日"),
        ("lifecycle_state", "生命周期状态"),
    )

    def __init__(self, env):
        self.env = env

    def _project_tasks(self, project):
        task_model = self.env["project.task"]
        if not project:
            return task_model.browse([])
        return task_model.search([("project_id", "=", int(project.id))], order="priority desc, id asc")

    def _followup_activities(self, project):
        activity_model = self.env["mail.activity"] if "mail.activity" in self.env else None
        if activity_model is None or not project:
            return self.env["mail.activity"].browse([])
        return activity_model.search(
            [
                ("res_model", "=", "project.project"),
                ("res_id", "=", int(project.id)),
                ("summary", "=", self.FOLLOWUP_SUMMARY),
            ],
            order="id asc",
        )

    def summary(self, project) -> dict:
        tasks = self._project_tasks(project)
        counts = ProjectTaskStateSupport.native_metrics(tasks, self.env["project.task"])
        counts["followup_activity_count"] = len(self._followup_activities(project))
        counts["scope"] = self.SCOPE
        return counts

    def _required_project_field_summary(self, project) -> dict:
        missing = []
        for field_name, label in self.REQUIRED_PROJECT_FIELDS:
            if field_name not in getattr(project, "_fields", {}):
                continue
            value = getattr(project, field_name, False)
            if not value:
                missing.append({"field": field_name, "label": label})
        manager_assigned = False
        for field_name in ("user_id", "manager_id"):
            if field_name in getattr(project, "_fields", {}) and getattr(project, field_name, False):
                manager_assigned = True
                break
        if not manager_assigned:
            missing.append({"field": "manager_assignment", "label": "项目经理/负责人"})
        return {
            "missing": missing,
            "missing_fields": [str(item.get("field") or "") for item in missing],
        }

    def validate_scope(self, project, *, from_state: str, to_state: str) -> tuple[bool, str, dict]:
        summary = self.summary(project)
        if from_state == "done":
            return True, "", summary
        if int(summary.get("task_total") or 0) <= 0:
            return False, "EXECUTION_TASK_MISSING", summary
        if to_state in {"ready", "in_progress"} and int(summary.get("task_open_count") or 0) <= 0:
            return False, "EXECUTION_TASK_NOT_OPEN", summary
        return True, "", summary

    def validate_state_alignment(self, project) -> tuple[bool, str, dict]:
        summary = self.summary(project)
        summary["project_execution_state_authoritative"] = False
        summary["project_execution_state_compatibility"] = (
            ProjectExecutionStateMachine.normalize_state(
                getattr(project, "sc_execution_state", "ready")
            )
        )
        return True, "", summary

    def validate_followup_activity(self, project) -> tuple[bool, str, dict]:
        summary = self.summary(project)
        activity_count = int(summary.get("followup_activity_count") or 0)
        if activity_count > 1:
            return False, "EXECUTION_PROJECT_ACTIVITY_DRIFT", summary
        return True, "", summary

    def readiness_precheck(self, project) -> dict:
        summary = self.summary(project)
        field_summary = self._required_project_field_summary(project)
        activity_ok, activity_reason_code, _ = self.validate_followup_activity(project)
        lifecycle_state = str(getattr(project, "lifecycle_state", "") or "").strip().lower()
        open_task_count = int(summary.get("task_open_count") or 0)
        checks = [
            {
                "key": "execution_task",
                "label": "存在开放施工执行任务",
                "status": "pass" if open_task_count > 0 else "fail",
                "reason_code": "" if open_task_count > 0 else "EXECUTION_TASK_NOT_OPEN",
                "message": "已检测到开放施工执行任务。"
                if open_task_count > 0
                else "当前项目没有可推进的开放施工任务。",
            },
            {
                "key": "required_fields",
                "label": "关键字段完整",
                "status": "pass" if not field_summary["missing_fields"] else "fail",
                "reason_code": "" if not field_summary["missing_fields"] else "READINESS_REQUIRED_FIELDS_MISSING",
                "message": "上线前必填字段已完整。"
                if not field_summary["missing_fields"]
                else "仍缺少关键字段：%s。"
                % "、".join(str(item.get("label") or item.get("field") or "") for item in field_summary["missing"]),
            },
            {
                "key": "activity_rule",
                "label": "Activity 规则一致",
                "status": "pass" if activity_ok else "fail",
                "reason_code": "" if activity_ok else activity_reason_code,
                "message": "mail.activity 跟进规则一致。"
                if activity_ok
                else "mail.activity 数量或状态与当前执行态不一致。",
            },
            {
                "key": "lifecycle_state",
                "label": "项目生命周期允许执行上线",
                "status": "pass" if lifecycle_state not in {"paused", "closed", "done", "closing", "warranty"} else "fail",
                "reason_code": ""
                if lifecycle_state not in {"paused", "closed", "done", "closing", "warranty"}
                else "READINESS_LIFECYCLE_STATE_BLOCKED",
                "message": "当前生命周期允许执行上线推进。"
                if lifecycle_state not in {"paused", "closed", "done", "closing", "warranty"}
                else "当前项目生命周期不允许进入执行上线。",
            },
        ]
        failed = [item for item in checks if str(item.get("status") or "") != "pass"]
        primary = failed[0] if failed else {}
        return {
            "checks": checks,
            "summary": {
                **summary,
                "overall_state": "ready" if not failed else "blocked",
                "passed_count": len(checks) - len(failed),
                "failed_count": len(failed),
                "failed_reason_codes": [str(item.get("reason_code") or "") for item in failed if str(item.get("reason_code") or "")],
                "primary_reason_code": str(primary.get("reason_code") or ""),
                "primary_message": str(primary.get("message") or "上线前检查通过，可进入执行推进。"),
                "missing_fields": list(field_summary["missing_fields"]),
                "execution_scope": self.SCOPE,
                "project_execution_state_authoritative": False,
            },
        }

    def pilot_precheck(self, project) -> dict:
        """Compatibility method for older callers; use readiness_precheck for new code."""
        return self.readiness_precheck(project)

    def reconcile_followup_activity(self, project, *, project_state: str | None = None) -> tuple[bool, str, dict]:
        if not project or not hasattr(project, "activity_schedule"):
            return True, "", self.summary(project)
        activities = self._followup_activities(project)
        summary = self.summary(project)
        expected_count = 1 if int(summary.get("task_open_count") or 0) > 0 else 0
        if expected_count <= 0:
            try:
                if activities:
                    activities.unlink()
            except Exception:
                return False, "EXECUTION_PROJECT_ACTIVITY_DRIFT", self.summary(project)
            return True, "", self.summary(project)

        activity_type = self.env.ref("mail.mail_activity_data_todo", raise_if_not_found=False)
        if not activity_type:
            return False, "EXECUTION_PROJECT_ACTIVITY_DRIFT", summary
        user_id = int(getattr(getattr(project, "user_id", None), "id", 0) or self.env.user.id or 0)
        if user_id <= 0:
            return False, "EXECUTION_PROJECT_ACTIVITY_DRIFT", summary
        try:
            if len(activities) <= 0:
                project.sudo().activity_schedule(
                    activity_type_id=int(activity_type.id),
                    summary=self.FOLLOWUP_SUMMARY,
                    note="项目存在开放施工任务，请继续按任务推进。",
                    user_id=user_id,
                )
            elif len(activities) > 1:
                activities[1:].unlink()
        except Exception:
            return False, "EXECUTION_PROJECT_ACTIVITY_DRIFT", self.summary(project)
        return True, "", self.summary(project)
