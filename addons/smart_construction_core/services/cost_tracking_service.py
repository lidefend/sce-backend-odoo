# -*- coding: utf-8 -*-
from __future__ import annotations

import logging

from odoo import fields

from odoo.addons.smart_construction_core.services.project_state_explain_service import lifecycle_state_label
from odoo.addons.smart_construction_core.services.cost_tracking_entry_service import CostTrackingEntryService
from odoo.addons.smart_construction_core.services.cost_tracking_builders import BUILDERS
from odoo.addons.smart_construction_core.services.cost_tracking_native_adapter import CostTrackingNativeAdapter
from odoo.addons.smart_construction_core.services.project_authorization_service import (
    CallerScopedProjectServiceMixin,
)


_logger = logging.getLogger(__name__)


class CostTrackingService(CallerScopedProjectServiceMixin):
    """Prepared cost tracking service backed by account.move facts."""

    SOURCE_KIND = "cost_tracking_business_fact_projection"
    SOURCE_AUTHORITIES = (
        "project.project",
        "project.cost.ledger",
        "project.budget",
        "account.move",
        "construction.contract",
        "odoo.orm",
        "odoo.read_group",
    )
    RUNTIME_BLOCK_MAP = {
        "cost_entry": "block.cost.tracking_entry_form",
        "cost_list": "block.cost.tracking_list",
        "cost_summary": "block.cost.tracking_summary",
        "next_actions": "block.cost.tracking_next_actions",
        "summary": "block.cost.tracking_summary",
        "recent_moves": "block.cost.tracking_move_list",
    }

    def __init__(self, env):
        self._initialize_project_authorization(env)
        self._bind_caller_env(env)

    def _bind_caller_env(self, env):
        self.env = env
        self._adapter = CostTrackingNativeAdapter(env)
        self._entry_service = CostTrackingEntryService(env)
        self._builders = [builder_cls(env) for builder_cls in BUILDERS]
        self._builder_map = {builder.block_key: builder for builder in self._builders}

    def build_block(self, block_key, project=None, context=None):
        normalized_key = str(block_key or "").strip().lower()
        builder_key = self.RUNTIME_BLOCK_MAP.get(normalized_key)
        if not builder_key:
            return self.error_block(normalized_key or "unknown", "UNSUPPORTED_BLOCK_KEY")
        builder = self._builder_map.get(builder_key)
        if builder is None:
            return self.error_block(builder_key, "BLOCK_BUILDER_NOT_FOUND")
        try:
            block = builder.build(project=project, context=dict(context or {}))
        except Exception:
            block = self.error_block(builder_key, "BLOCK_BUILD_FAILED")
        return block if isinstance(block, dict) else self.error_block(builder_key, "INVALID_BLOCK_PAYLOAD")

    def _model(self, model_name):
        try:
            return self.env[model_name]
        except Exception:
            return None

    def project_payload(self, project):
        def _safe_text(value):
            try:
                return str(value or "")
            except Exception:
                return ""

        def _safe_rel_name(record, field_name):
            try:
                relation = getattr(record, field_name, None)
            except Exception:
                return ""
            return _safe_text(getattr(relation, "display_name", ""))

        def _safe_field(record, field_name):
            try:
                return getattr(record, field_name, "")
            except Exception:
                return ""

        if not project:
            return {
                "id": 0,
                "name": "",
                "project_code": "",
                "manager_name": "",
                "stage_name": "",
                "date_start": "",
                "date_end": "",
                "today": str(fields.Date.today()),
            }
        summary = self._adapter.summary(project)
        record_count = int(summary.get("ledger_count") or summary.get("move_count") or 0)
        return {
            "id": int(project.id),
            "name": _safe_text(_safe_field(project, "name")),
            "project_code": _safe_text(_safe_field(project, "project_code")),
            "manager_name": _safe_rel_name(project, "user_id"),
            "stage_name": lifecycle_state_label(project),
            "date_start": str(_safe_field(project, "date_start") or ""),
            "date_end": str(_safe_field(project, "date") or _safe_field(project, "date_end") or ""),
            "move_count": int(summary.get("move_count") or 0),
            "draft_move_count": int(summary.get("draft_move_count") or 0),
            "cost_record_count": record_count,
            "cost_total_amount": str(summary.get("total_cost_amount") or 0.0),
            "draft_cost_amount": str(summary.get("draft_cost_amount") or 0.0),
            "currency_name": _safe_text(summary.get("currency_name") or ""),
            "today": str(fields.Date.today()),
        }

    def build_summary_rows(self, project):
        summary = self.project_payload(project)
        currency_name = str(summary.get("currency_name") or "").strip()

        def _amount(value):
            text = str(value or 0)
            return "%s %s" % (text, currency_name) if currency_name else text

        return [
            {
                "key": "project_code",
                "label": "项目编码",
                "value": str(summary.get("project_code") or "--"),
            },
            {
                "key": "manager_name",
                "label": "项目经理",
                "value": str(summary.get("manager_name") or "--"),
            },
            {
                "key": "stage_name",
                "label": "当前阶段",
                "value": str(summary.get("stage_name") or "--"),
            },
            {
                "key": "cost_record_count",
                "label": "成本记录数",
                "value": "%s 条" % str(summary.get("cost_record_count") or 0),
            },
            {
                "key": "cost_total_amount",
                "label": "成本合计",
                "value": _amount(summary.get("cost_total_amount")),
            },
            {
                "key": "draft_cost_amount",
                "label": "草稿金额",
                "value": _amount(summary.get("draft_cost_amount")),
            },
        ]

    def create_cost_entry(self, project=None, values=None, context=None):
        return self._entry_service.create(project=project, values=values, context=context)

    @classmethod
    def source_authority_contract(cls):
        return {
            "kind": cls.SOURCE_KIND,
            "authorities": list(cls.SOURCE_AUTHORITIES),
            "projection_only": True,
            "runtime_carrier": "scene_entry_and_block_contract",
        }

    @classmethod
    def write_source_authority_contract(cls):
        return {
            "kind": "cost_tracking_odoo_orm_write_proxy",
            "authorities": [
                "account.move",
                "account.move.line",
                "account.journal",
                "account.account",
                "project.project",
                "project.cost.code",
                "ir.model.access",
                "ir.rule",
                "odoo.orm",
            ],
            "projection_only": False,
            "runtime_authority": "odoo.orm",
            "write_authority": "account.move.create",
        }

    @classmethod
    def error_block(cls, block_key, code):
        return {
            "block_key": block_key,
            "block_type": "unknown",
            "title": block_key,
            "state": "error",
            "visibility": {"allowed": True, "reason_code": "OK", "reason": ""},
            "data": {},
            "error": {"code": code, "message": code},
            "source_authority": cls.source_authority_contract(),
        }
