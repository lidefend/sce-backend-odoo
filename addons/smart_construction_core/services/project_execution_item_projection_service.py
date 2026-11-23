# -*- coding: utf-8 -*-
from __future__ import annotations

from odoo import fields
from odoo.addons.smart_core.core.project_context import selected_project_id_from_context
from odoo.addons.smart_construction_scene.services.capability_scene_targets import (
    resolve_execution_projection_scene_key,
)


class ProjectExecutionItemProjectionService:
    """Source-preserving project business-pending projection.

    This service feeds the work inbox only. Contract, payment and settlement
    records remain business documents and are never materialized as tasks.
    """

    SOURCE_CONFIG = {
        "construction.contract": {
            "title_prefix": "合同事项",
            "pending_states": ("draft", "confirmed", "running"),
            "deadline_field": "date_end",
            "fallback_deadline_field": "date_contract",
            "title_field": "subject",
            "action_label": "查看合同",
            "reason_code": "SYSTEM_EXECUTION_PENDING",
            "priority": "high",
        },
        "payment.request": {
            "title_prefix": "付款事项",
            "pending_states": ("draft", "submit", "approve", "approved"),
            "deadline_field": "date_request",
            "title_field": "name",
            "action_label": "查看付款申请",
            "reason_code": "SYSTEM_EXECUTION_PENDING",
            "priority": "high",
        },
        "sc.settlement.order": {
            "title_prefix": "结算事项",
            "pending_states": ("draft", "submit", "approve"),
            "deadline_field": "date_settlement",
            "title_field": "name",
            "action_label": "查看结算单",
            "reason_code": "SYSTEM_EXECUTION_PENDING",
            "priority": "medium",
        },
    }

    def __init__(self, env, context=None):
        self.env = env
        self.context = context if isinstance(context, dict) else {}

    def _model(self, model_name):
        try:
            return self.env[model_name]
        except Exception:
            return None

    def _project_responsible_domain(self, user):
        Project = self._model("project.project")
        if Project is None:
            return []
        fields_map = Project._fields
        clauses = []
        for field_name in ("user_id", "manager_id", "cost_manager_id", "doc_manager_id"):
            if field_name in fields_map:
                clauses.append((field_name, "=", int(user.id)))
        if "user_ids" in fields_map:
            clauses.append(("user_ids", "in", [int(user.id)]))
        if not clauses:
            return []
        if len(clauses) == 1:
            return [clauses[0]]
        return (["|"] * (len(clauses) - 1)) + clauses

    def _project_ids_for_user(self, user):
        Project = self._model("project.project")
        if Project is None or int(user.id) != int(self.env.user.id):
            return []
        current_project_id = selected_project_id_from_context({}, self.context)
        if current_project_id:
            try:
                if Project.search_count(
                    [("id", "=", int(current_project_id))] + self._project_responsible_domain(user)
                ):
                    return [int(current_project_id)]
            except Exception:
                return []
            return []
        try:
            projects = Project.search(self._project_responsible_domain(user), order="id desc")
        except Exception:
            return []
        return [int(project.id) for project in projects]

    @staticmethod
    def _deadline_text(record, primary_field, fallback_field=""):
        value = getattr(record, primary_field, False) if primary_field else False
        if not value and fallback_field:
            value = getattr(record, fallback_field, False)
        return fields.Date.to_string(value) if value else ""

    @staticmethod
    def _safe_text(value):
        return str(value or "").strip()

    def _item_title(self, record, config):
        raw_title = self._safe_text(getattr(record, str(config.get("title_field") or "name"), ""))
        if not raw_title:
            raw_title = "%s#%s" % (record._name, int(record.id))
        prefix = self._safe_text(config.get("title_prefix"))
        return "%s：%s" % (prefix, raw_title) if prefix else raw_title

    def user_items(self, user, *, limit=8):
        if int(user.id) != int(self.env.user.id):
            return []
        safe_limit = max(0, int(limit or 0))
        if safe_limit <= 0:
            return []
        project_ids = self._project_ids_for_user(user)
        if not project_ids:
            return []
        rows = []
        per_source_limit = max(1, (safe_limit + len(self.SOURCE_CONFIG) - 1) // len(self.SOURCE_CONFIG))
        for model_name, config in self.SOURCE_CONFIG.items():
            Model = self._model(model_name)
            if Model is None:
                continue
            domain = [
                ("project_id", "in", project_ids),
                ("state", "in", list(config.get("pending_states") or ())),
            ]
            try:
                records = Model.search(domain, order="write_date desc, id desc", limit=per_source_limit)
            except Exception:
                continue
            for record in records:
                try:
                    rows.append(
                        {
                            "id": int(record.id),
                            "title": self._item_title(record, config),
                            "model": model_name,
                            "record_id": int(record.id),
                            "deadline": self._deadline_text(
                                record,
                                str(config.get("deadline_field") or ""),
                                str(config.get("fallback_deadline_field") or ""),
                            ),
                            "scene_key": resolve_execution_projection_scene_key(model_name),
                            "source": model_name,
                            "action_label": self._safe_text(config.get("action_label")),
                            "action_key": "%s.open" % model_name,
                            "reason_code": self._safe_text(config.get("reason_code")),
                            "priority": self._safe_text(config.get("priority") or "medium"),
                        }
                    )
                except Exception:
                    rows.append(
                        {
                            "id": int(record.id),
                            "title": "%s#%s" % (model_name, int(record.id)),
                            "model": model_name,
                            "record_id": int(record.id),
                            "deadline": "",
                            "scene_key": resolve_execution_projection_scene_key(model_name),
                            "source": model_name,
                            "action_label": self._safe_text(config.get("action_label")),
                            "action_key": "%s.open" % model_name,
                            "reason_code": self._safe_text(config.get("reason_code")),
                            "priority": self._safe_text(config.get("priority") or "medium"),
                        }
                    )
        rows.sort(key=lambda row: (str(row.get("deadline") or ""), int(row.get("id") or 0)), reverse=True)
        return rows[:safe_limit]
