# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from odoo.addons.smart_core.core.base_handler import BaseIntentHandler

from ..services.product_configuration_capability import (
    build_catalog,
    build_user_capabilities,
    load_manifest,
    resolve_audiences,
)


MODULE_MANIFEST = (
    Path(__file__).resolve().parents[1]
    / "data/product_configuration_capability_v1.json"
)


class ProductConfigurationCapabilityCatalogHandler(BaseIntentHandler):
    INTENT_TYPE = "product.configuration.capability.catalog"
    DESCRIPTION = "Project the product configuration capability catalog for the current user"
    VERSION = "1.0.0"
    ETAG_ENABLED = False
    REQUIRED_GROUPS = ["base.group_user"]

    def _trace_id(self) -> str:
        if isinstance(self.context, dict):
            value = str(self.context.get("trace_id") or "").strip()
            if value:
                return value
        return "product_cap_%s" % uuid4().hex[:12]

    @staticmethod
    def source_authority_contract() -> dict:
        return {
            "kind": "product_configuration_capability_projection",
            "authorities": [
                "config/product_configuration_capability_v1.json",
                "res.groups",
                "ir.model.access",
                "smart_core.core.capability_provider",
            ],
            "projection_only": True,
            "runtime_carrier": "smart_construction_core.handlers.product_configuration_capability",
        }

    def handle(self, payload=None, ctx=None):
        trace_id = self._trace_id()
        try:
            manifest = load_manifest(MODULE_MANIFEST)
        except Exception as exc:
            reason = "PRODUCT_CAPABILITY_MANIFEST_MISSING"
            message = str(exc) or "product capability manifest is unavailable"
            return {
                "ok": False,
                "data": {
                    "success": False,
                    "reason_code": reason,
                    "message": message,
                },
                "error": {
                    "code": reason,
                    "reason_code": reason,
                    "message": message,
                },
                "code": 500,
                "meta": {
                    "intent": self.INTENT_TYPE,
                    "trace_id": trace_id,
                    "source_authority": self.source_authority_contract(),
                },
            }
        audiences = resolve_audiences(self.env.user)
        data = build_catalog(manifest, audiences)
        from odoo.addons.smart_core.core.capability_provider import load_capabilities_for_user
        data["user_capabilities"] = build_user_capabilities(
            load_capabilities_for_user(self.env, self.env.user))
        data["success"] = True
        data["reason_code"] = "OK"
        return {
            "ok": True,
            "data": data,
            "meta": {
                "intent": self.INTENT_TYPE,
                "trace_id": trace_id,
                "source_authority": self.source_authority_contract(),
            },
        }
