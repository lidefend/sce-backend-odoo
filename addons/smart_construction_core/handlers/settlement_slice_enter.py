# -*- coding: utf-8 -*-
from __future__ import annotations

import time

from odoo.addons.smart_core.core.base_handler import BaseIntentHandler
from odoo.addons.smart_core.core.scene_contract_builder import attach_release_surface_scene_contract
from odoo.addons.smart_construction_core.services.project_context_contract import (
    attach_project_context_to_scene_payload,
)
from odoo.addons.smart_core.orchestration.settlement_slice_contract_orchestrator import (
    SettlementSliceContractOrchestrator,
)
from odoo.addons.smart_construction_core.handlers.project_context_resolver import (
    ProjectContextResolverMixin,
)
from odoo.addons.smart_construction_scene.services.project_management_entry_target import (
    resolve_project_management_entry_target,
)


class SettlementSliceEnterHandler(ProjectContextResolverMixin, BaseIntentHandler):
    INTENT_TYPE = "settlement.enter"
    DESCRIPTION = "返回结算切片最小 scene-ready contract"
    VERSION = "1.0.0"
    ETAG_ENABLED = False
    REQUIRED_GROUPS = ["base.group_user"]

    def handle(self, payload=None, ctx=None):
        ts0 = time.time()
        params = payload or self.params or {}
        if isinstance(params, dict) and isinstance(params.get("params"), dict):
            params = params.get("params") or {}
        ctx = ctx or {}

        project_id = self._resolve_project_id(params, ctx)
        if project_id <= 0:
            source_authority = SettlementSliceContractOrchestrator(
                self.env
            ).source_authority_contract()
            return {
                "ok": False,
                "error": {
                    "code": "PROJECT_NOT_FOUND",
                    "message": "项目不存在或当前账号不可访问",
                    "suggested_action": "fix_input",
                },
                "meta": {
                    "intent": self.INTENT_TYPE,
                    "elapsed_ms": int((time.time() - ts0) * 1000),
                    "trace_id": str((self.context or {}).get("trace_id") or ""),
                    "source_authority": source_authority,
                },
            }
        resolution = self._resolve_project_scope(params, ctx)
        orchestrator = SettlementSliceContractOrchestrator(resolution.env)
        source_authority = orchestrator.source_authority_contract()
        if not resolution.available:
            return {
                "ok": False,
                "error": {
                    "code": "PROJECT_NOT_FOUND",
                    "message": "项目不存在或当前账号不可访问",
                    "suggested_action": "fix_input",
                },
                "meta": {
                    "intent": self.INTENT_TYPE,
                    "elapsed_ms": int((time.time() - ts0) * 1000),
                    "trace_id": str((self.context or {}).get("trace_id") or ""),
                    "source_authority": source_authority,
                },
            }
        project_id = int(resolution.project.id)
        orchestrator._service.bind_authorized_resolution(resolution)
        data = orchestrator.build_entry(project_id=project_id, context=ctx)
        project, _diag = orchestrator._service.resolve_project_with_diagnostics(project_id)
        data = attach_project_context_to_scene_payload(data, project)
        target = resolve_project_management_entry_target(resolution.env)
        data = attach_release_surface_scene_contract(
            data,
            product_key="fr5",
            capability="delivery.fr5.settlement_summary",
            route=str(target.get("route") or ""),
            diagnostics_ref=self.INTENT_TYPE,
            trace_id=str((self.context or {}).get("trace_id") or ""),
        )
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
