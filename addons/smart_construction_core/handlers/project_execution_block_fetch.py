# -*- coding: utf-8 -*-
from __future__ import annotations

import time

from odoo.addons.smart_core.core.base_handler import BaseIntentHandler
from odoo.addons.smart_construction_core.services.project_context_contract import (
    attach_project_context_to_runtime_payload,
)
from odoo.addons.smart_core.orchestration.project_execution_scene_orchestrator import (
    ProjectExecutionSceneOrchestrator,
)
from odoo.addons.smart_construction_core.handlers.project_context_resolver import (
    ProjectContextResolverMixin,
)


class ProjectExecutionBlockFetchHandler(ProjectContextResolverMixin, BaseIntentHandler):
    INTENT_TYPE = "project.execution.block.fetch"
    DESCRIPTION = "按需返回 project.execution runtime block"
    VERSION = "1.0.0"
    ETAG_ENABLED = False
    REQUIRED_GROUPS = ["base.group_user"]
    PROJECT_ID_PARAM_RECORD_ID = False

    @staticmethod
    def _build_lifecycle_hints(project_id: int) -> Dict[str, Any]:
        if int(project_id or 0) > 0:
            return {
                "stage": "entry_params_missing",
                "first_action": "open_project_execution",
                "primary_action_label": "进入项目执行",
                "suggested_action_intent": "project.execution.enter",
                "suggested_action_title": "进入项目执行",
            }
        return {
            "stage": "no_project_context",
            "first_action": "create_project",
            "primary_action_label": "创建项目",
            "suggested_action_intent": "project.initiation.enter",
            "suggested_action_title": "创建项目",
        }

    def handle(self, payload=None, ctx=None):
        ts0 = time.time()
        params = payload or self.params or {}
        if isinstance(params, dict) and isinstance(params.get("params"), dict):
            params = params.get("params") or {}
        ctx = ctx or {}

        project_id = self._resolve_project_id(params, ctx)
        block_key = str(params.get("block_key") or "").strip().lower()
        orchestrator = ProjectExecutionSceneOrchestrator(self.env)
        source_authority = orchestrator.source_authority_contract()
        if project_id <= 0 or not block_key:
            return {
                "ok": False,
                "error": {
                    "code": "MISSING_PARAMS",
                    "message": "缺少参数：project_id 或 block_key",
                    "suggested_action": "fix_input",
                },
                "data": {
                    "lifecycle_hints": self._build_lifecycle_hints(0),
                },
                "meta": {
                    "intent": self.INTENT_TYPE,
                    "elapsed_ms": int((time.time() - ts0) * 1000),
                    "trace_id": str((self.context or {}).get("trace_id") or ""),
                    "source_authority": source_authority,
                },
            }

        resolution = self._resolve_project_scope(params, ctx)
        orchestrator = ProjectExecutionSceneOrchestrator(resolution.env)
        source_authority = orchestrator.source_authority_contract()
        if not resolution.available:
            return {
                "ok": False,
                "error": {
                    "code": "PROJECT_NOT_FOUND",
                    "message": "项目不存在或当前账号不可访问",
                    "suggested_action": "fix_input",
                },
                "data": {"lifecycle_hints": self._build_lifecycle_hints(0)},
                "meta": {
                    "intent": self.INTENT_TYPE,
                    "elapsed_ms": int((time.time() - ts0) * 1000),
                    "trace_id": str((self.context or {}).get("trace_id") or ""),
                    "source_authority": source_authority,
                },
            }

        project_id = int(resolution.project.id)
        orchestrator._service.bind_authorized_resolution(resolution)
        data = orchestrator.build_runtime_block(block_key=block_key, project_id=project_id, context=ctx)
        project, _diag = orchestrator._service.resolve_project_with_diagnostics(project_id)
        data = attach_project_context_to_runtime_payload(data, project)
        return {
            "ok": True,
            "data": data,
            "meta": {
                "intent": self.INTENT_TYPE,
                "elapsed_ms": int((time.time() - ts0) * 1000),
                "trace_id": str((self.context or {}).get("trace_id") or ""),
                "source_authority": source_authority,
            },
        }
