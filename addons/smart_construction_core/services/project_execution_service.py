# -*- coding: utf-8 -*-
from __future__ import annotations

import logging

from odoo import fields

from odoo.addons.smart_construction_core.services.project_state_explain_service import lifecycle_state_label
from odoo.addons.smart_construction_core.services.project_execution_builders import BUILDERS
from odoo.addons.smart_construction_core.services.project_authorization_service import (
    CallerScopedProjectServiceMixin,
)


_logger = logging.getLogger(__name__)


class ProjectExecutionService(CallerScopedProjectServiceMixin):
    """Provide business-truth-backed execution data for orchestration carriers."""

    SOURCE_KIND = "project_execution_business_fact_projection"
    SOURCE_AUTHORITIES = (
        "project.project",
        "project.task",
        "project.milestone",
        "mail.activity",
        "odoo.orm",
        "odoo.read_group",
    )
    RUNTIME_BLOCK_MAP = {
        "execution_tasks": "block.project.execution_tasks",
        "readiness_precheck": "block.project.execution_readiness_precheck",
        # Compatibility key for older orchestration clients; new callers use readiness_precheck.
        "pilot_precheck": "block.project.execution_readiness_precheck",
        "next_actions": "block.project.execution_next_actions",
    }

    def __init__(self, env):
        self._initialize_project_authorization(env)
        self._bind_caller_env(env)

    def _bind_caller_env(self, env):
        self.env = env
        self._builders = [builder_cls(env) for builder_cls in BUILDERS]
        self._builder_map = {builder.block_key: builder for builder in self._builders}

    def build_block(self, block_key, project=None, context=None):
        normalized_key = str(block_key or "").strip().lower()
        builder_key = self.RUNTIME_BLOCK_MAP.get(normalized_key)
        if not builder_key:
            return self.error_block(normalized_key or "unknown", "UNSUPPORTED_BLOCK_KEY")

        builder = self._builder_map.get(builder_key)
        if builder is None:
            block = self.error_block(builder_key, "BLOCK_BUILDER_NOT_FOUND")
        else:
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
            }
        return {
            "id": int(project.id),
            "name": _safe_text(_safe_field(project, "name")),
            "project_code": _safe_text(_safe_field(project, "project_code")),
            "manager_name": _safe_rel_name(project, "user_id"),
            "stage_name": lifecycle_state_label(project),
            "date_start": str(_safe_field(project, "date_start") or ""),
            "date_end": str(_safe_field(project, "date") or _safe_field(project, "date_end") or ""),
            "today": str(fields.Date.today()),
        }

    @classmethod
    def source_authority_contract(cls):
        return {
            "kind": cls.SOURCE_KIND,
            "authorities": list(cls.SOURCE_AUTHORITIES),
            "projection_only": True,
            "runtime_carrier": "scene_entry_and_block_contract",
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
