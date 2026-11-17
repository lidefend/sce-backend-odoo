# -*- coding: utf-8 -*-
"""Project business payloads for generic native embedded-widget nodes."""
from __future__ import annotations

from typing import Any

def _text(value: Any) -> str:
    return str(value or "").strip()


def _positive_int(value: Any, default: int = 0) -> int:
    try:
        parsed = int(value or 0)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


class ProjectNativeViewWidgetPayloadService:
    """Read-only adapter from existing project services to generic node payloads."""

    SOURCE_AUTHORITY = {
        "kind": "smart_construction_core_native_view_widget_payload",
        "module": "smart_construction_core",
        "projectionOnly": False,
        "noBusinessFactAuthority": False,
    }

    def __init__(self, env):
        self.env = env

    def build(self, request):
        request = request if isinstance(request, dict) else {}
        if _text(request.get("model")) != "project.project":
            return {"widgets": {}}
        record_id = _positive_int(request.get("recordId"))
        if not record_id:
            return {"widgets": {}}
        project = self.env["project.project"].browse(record_id).exists()
        if not project:
            return {"widgets": {}}
        project.check_access_rights("read")
        project.check_access_rule("read")
        widgets = {}
        for declared in request.get("widgets") or []:
            if not isinstance(declared, dict):
                continue
            occurrence_key = _text(declared.get("occurrenceKey"))
            native_widget = _text(declared.get("nativeWidget"))
            if not occurrence_key:
                continue
            if native_widget == "sc_insight_banner":
                widgets[occurrence_key] = {
                    "payloadSchema": "insight_summary.v1",
                    "payload": self._insight_payload(project),
                    "sourceAuthority": dict(self.SOURCE_AUTHORITY),
                }
            elif native_widget == "sc_stage_requirements":
                widgets[occurrence_key] = {
                    "payloadSchema": "action_list.v1",
                    "payload": self._stage_requirement_payload(project, declared),
                    "sourceAuthority": dict(self.SOURCE_AUTHORITY),
                }
            elif native_widget == "sc_next_actions":
                widgets[occurrence_key] = {
                    "payloadSchema": "action_list.v1",
                    "payload": self._next_action_payload(project, declared),
                    "sourceAuthority": dict(self.SOURCE_AUTHORITY),
                }
        return {"widgets": widgets}

    def _insight_payload(self, project):
        from odoo.addons.smart_construction_core.services.insight.project_insight_service import (
            ProjectInsightService,
        )

        insight = ProjectInsightService(self.env).get_insight(project, scene="project.entry")
        initiation = insight.get("initiation") or {}
        ui_model = initiation.get("ui_model") or {}
        hero = ui_model.get("hero") or {}
        risk_count = _positive_int(initiation.get("risk_count"))
        next_best = ui_model.get("next_best") or {}
        next_item = next_best.get("item") if isinstance(next_best, dict) else {}
        detail_parts = [
            _text((next_item or {}).get("because")),
            _text((ui_model.get("footer") or {}).get("text")),
        ]
        return {
            "tone": "warning" if risk_count else "success",
            "title": _text(hero.get("title")) or "项目洞察",
            "message": _text(hero.get("subtitle")),
            "detail": "；".join(part for part in detail_parts if part),
        }

    def _stage_requirement_payload(self, project, declared):
        limit = self._limit(declared)
        rows = project.sc_get_stage_requirements(limit=limit) or []
        items = []
        for index, row in enumerate(rows, start=1):
            done = row.get("done") is True
            required = row.get("required") is True
            title = _text(row.get("title"))
            items.append({
                "id": f"stage-requirement-{index}",
                "title": title,
                "description": "完成即可进入下一阶段" if required else "建议在推进过程中持续补齐",
                "state": "done" if done else ("required" if required else "available"),
                "tone": "success" if done else ("warning" if required else "info"),
                "actionType": "" if done else _text(row.get("action_type")),
                "actionRef": "" if done else _text(row.get("action_ref")),
                "actionLabel": "" if done else "去处理",
                "actionPayload": {} if done else dict(row.get("payload") or {}),
                "enabled": not done and bool(_text(row.get("action_ref"))),
            })
        return {
            "title": "阶段要求",
            "emptyText": "当前阶段没有额外要求",
            "items": items,
        }

    def _next_action_payload(self, project, declared):
        limit = self._limit(declared)
        response = project.sc_get_next_actions(limit=limit) or {}
        rows = list(response.get("actions") or [])
        if not rows and isinstance(response.get("fallback"), dict):
            rows = [response["fallback"]]
        items = []
        for index, row in enumerate(rows, start=1):
            action_ref = _text(row.get("action_ref") or row.get("ref"))
            items.append({
                "id": f"next-action-{index}",
                "title": _text(row.get("title") or row.get("name")) or "继续办理",
                "description": _text(row.get("hint")),
                "state": "available",
                "tone": "info",
                "actionType": _text(row.get("action_type") or row.get("type")),
                "actionRef": action_ref,
                "actionLabel": "进入处理",
                "actionPayload": dict(row.get("payload") or {}),
                "enabled": bool(action_ref),
            })
        return {
            "title": "下一步动作",
            "emptyText": "当前没有建议动作",
            "items": items,
        }

    @staticmethod
    def _limit(declared):
        options = declared.get("options")
        return _positive_int(options.get("limit") if isinstance(options, dict) else 0, 3)
