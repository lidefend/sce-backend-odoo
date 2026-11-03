#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from odoo.addons.smart_core.core.base_handler import BaseIntentHandler
from odoo.addons.smart_construction_scene.services.workspace_scenario_projection import (
    bind_company_context, resolve_request_company,
)


class ScenarioDependencyDiagnosisGetHandler(BaseIntentHandler):
    INTENT_TYPE = "scenario.dependency.diagnosis.get"
    DESCRIPTION = "企业业务场景依赖诊断（只读）"
    VERSION = "1.0.0"
    ETAG_ENABLED = False
    SOURCE_AUTHORITY = {
        "kind": "scenario_dependency_diagnosis_projection",
        "authorities": ["sc.scene", "sc.scene.version", "res.company"],
        "projection_only": True,
        "no_business_fact_authority": True,
    }

    def handle(self, payload=None, params=None, ctx=None):
        params = payload if payload is not None else params if params is not None else self.params
        if not isinstance(params, dict):
            return {"ok": False, "error": {"code": 400, "message": "invalid diagnosis parameters"}}
        scene_key = params.get("scene_key")
        if not isinstance(scene_key, str) or not scene_key.strip():
            return {"ok": False, "error": {"code": 400, "message": "scene_key must be a nonempty string"}}
        scene_key = scene_key.strip()
        company_id, error = resolve_request_company(
            params.get("company_id"), self.env.user.company_ids.ids, self.env.company.id
        )
        if error:
            return {"ok": False, "error": error}
        env = bind_company_context(self.env, company_id)
        from odoo.addons.smart_construction_scene.services.scenario_dependency_diagnosis import (
            diagnose_scenario_dependencies,
        )

        return {
            "ok": True,
            "data": diagnose_scenario_dependencies(
                env, scene_key=scene_key, company_id=company_id
            ),
            "meta": {},
        }
