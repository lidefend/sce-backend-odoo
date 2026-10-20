# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from odoo.addons.smart_core.core.base_handler import BaseIntentHandler

from ..services.product_system_parameter_catalog import (
    build_catalog,
    impact_preview,
    load_manifest,
)


MODULE_MANIFEST = (
    Path(__file__).resolve().parents[1]
    / "data/product_system_parameter_catalog_v1.json"
)

CONFIG_ADMIN_GROUPS = (
    "smart_construction_core.group_sc_cap_business_config_admin",
    "smart_construction_core.group_sc_cap_config_admin",
    "smart_construction_core.group_sc_super_admin",
)


def _has_group(user, xmlid: str) -> bool:
    checker = getattr(user, "has_group", None)
    if not callable(checker):
        return False
    try:
        return bool(checker(xmlid))
    except Exception:
        return False


def _cost_ledger_source_current(env) -> str:
    company = env.company
    enabled = {
        "account_move": company.sc_cost_from_account_move,
        "purchase_order": company.sc_cost_from_purchase,
        "stock_move": company.sc_cost_from_stock,
    }
    selected = [key for key, value in enabled.items() if value]
    return selected[0] if len(selected) == 1 else "disabled"


class ProductSystemParameterCatalogHandler(BaseIntentHandler):
    INTENT_TYPE = "sc.product.system_parameter.catalog"
    DESCRIPTION = "Project the controlled product system parameter catalog"
    VERSION = "1.0.0"
    ETAG_ENABLED = False
    REQUIRED_GROUPS = ["base.group_user"]

    def _trace_id(self) -> str:
        if isinstance(self.context, dict):
            value = str(self.context.get("trace_id") or "").strip()
            if value:
                return value
        return "param_cat_%s" % uuid4().hex[:12]

    @staticmethod
    def source_authority_contract() -> dict:
        return {
            "kind": "product_system_parameter_catalog_projection",
            "authorities": [
                "config/product_system_parameter_catalog_v1.json",
                "res.company",
                "res.groups",
            ],
            "projection_only": True,
            "runtime_carrier": "smart_construction_core.handlers.product_system_parameter_catalog",
        }

    def handle(self, payload=None, ctx=None):
        trace_id = self._trace_id()
        try:
            manifest = load_manifest(MODULE_MANIFEST)
        except Exception as exc:
            reason = "PRODUCT_SYSTEM_PARAMETER_MANIFEST_MISSING"
            message = str(exc) or "product system parameter catalog is unavailable"
            return {
                "ok": False,
                "data": {"success": False, "reason_code": reason, "message": message},
                "error": {"code": reason, "reason_code": reason, "message": message},
                "code": 500,
                "meta": {
                    "intent": self.INTENT_TYPE,
                    "trace_id": trace_id,
                    "source_authority": self.source_authority_contract(),
                },
            }
        data = build_catalog(manifest)
        for row in data["parameters"]:
            if row["key"] == "cost_ledger_source" and row["available"]:
                row["current_value"] = _cost_ledger_source_current(self.env)
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


class ProductSystemParameterPreviewHandler(BaseIntentHandler):
    INTENT_TYPE = "sc.product.system_parameter.preview"
    DESCRIPTION = "Preview the impact of a proposed system parameter change"
    VERSION = "1.0.0"
    ETAG_ENABLED = False
    REQUIRED_GROUPS = list(CONFIG_ADMIN_GROUPS)

    def _trace_id(self) -> str:
        if isinstance(self.context, dict):
            value = str(self.context.get("trace_id") or "").strip()
            if value:
                return value
        return "param_preview_%s" % uuid4().hex[:12]

    @staticmethod
    def source_authority_contract() -> dict:
        return {
            "kind": "product_system_parameter_preview",
            "authorities": [
                "config/product_system_parameter_catalog_v1.json",
                "res.groups",
            ],
            "projection_only": True,
            "runtime_carrier": "smart_construction_core.handlers.product_system_parameter_catalog",
        }

    def handle(self, payload=None, ctx=None):
        trace_id = self._trace_id()
        if not any(_has_group(self.env.user, group) for group in CONFIG_ADMIN_GROUPS):
            reason = "PERMISSION_DENIED"
            message = "只有行业配置管理员可以预览系统参数影响。"
            return {
                "ok": False,
                "data": {"success": False, "reason_code": reason, "message": message},
                "error": {"code": reason, "reason_code": reason, "message": message},
                "code": 403,
                "meta": {
                    "intent": self.INTENT_TYPE,
                    "trace_id": trace_id,
                    "source_authority": self.source_authority_contract(),
                },
            }
        try:
            manifest = load_manifest(MODULE_MANIFEST)
        except Exception as exc:
            reason = "PRODUCT_SYSTEM_PARAMETER_MANIFEST_MISSING"
            message = str(exc) or "product system parameter catalog is unavailable"
            return {
                "ok": False,
                "data": {"success": False, "reason_code": reason, "message": message},
                "error": {"code": reason, "reason_code": reason, "message": message},
                "code": 500,
                "meta": {
                    "intent": self.INTENT_TYPE,
                    "trace_id": trace_id,
                    "source_authority": self.source_authority_contract(),
                },
            }
        params = payload if isinstance(payload, dict) else {}
        result = impact_preview(
            manifest,
            params.get("parameter_key"),
            params.get("proposed_value"),
        )
        result["success"] = bool(result.get("ok"))
        result["reason_code"] = "OK" if result.get("ok") else str(result.get("reason") or "REJECTED").upper()
        return {
            "ok": True,
            "data": result,
            "meta": {
                "intent": self.INTENT_TYPE,
                "trace_id": trace_id,
                "source_authority": self.source_authority_contract(),
            },
        }
