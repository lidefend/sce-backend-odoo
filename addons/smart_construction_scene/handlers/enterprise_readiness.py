#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from odoo.addons.smart_core.core.base_handler import BaseIntentHandler


class EnterpriseReadinessDiagnosisGetHandler(BaseIntentHandler):
    INTENT_TYPE = "enterprise.readiness.diagnosis.get"
    DESCRIPTION = "企业业务就绪度诊断（只读）"
    VERSION = "1.0.0"
    ETAG_ENABLED = False
    SOURCE_AUTHORITY = {
        "kind": "enterprise_readiness_diagnosis_projection",
        "authorities": [
            "res.company",
            "hr.department",
            "hr.job",
            "res.users",
            "hr.employee",
            "res.groups",
            "sc.scene.company.enablement",
        ],
        "projection_only": True,
        "no_business_fact_authority": True,
    }

    def handle(self, payload=None, ctx=None):
        params = payload or self.params or {}
        from odoo.addons.smart_construction_scene.services.workspace_scenario_projection import (
            resolve_request_company, bind_company_context,
        )
        if not isinstance(params, dict):
            return {"ok": False, "error": {"code": 400, "message": "invalid diagnosis parameters"}}
        company_id, error = resolve_request_company(
            params.get("company_id"), set(self.env.user.company_ids.ids), self.env.company.id)
        if error:
            return {"ok": False, "error": error}
        if not self.env.user.has_group("smart_construction_core.group_sc_cap_business_config_admin"):
            return {
                "ok": False,
                "error": {"code": 403, "message": "business config admin required"},
            }
        from odoo.addons.smart_construction_scene.services.enterprise_readiness_diagnosis import (
            evaluate_enterprise_readiness,
        )

        return {
            "ok": True,
            "data": evaluate_enterprise_readiness(bind_company_context(self.env, company_id), company_id=company_id),
            "meta": {},
        }
