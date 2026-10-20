# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from odoo import fields
from odoo.addons.smart_core.core.base_handler import BaseIntentHandler

from ..services.product_system_parameter_catalog import (
    impact_preview,
    load_manifest,
)
from ..services.product_system_parameter_change import (
    apply_parameter_value,
    read_parameter_value,
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


def _trace_id(context, prefix: str) -> str:
    if isinstance(context, dict):
        value = str(context.get("trace_id") or "").strip()
        if value:
            return value
    return "%s_%s" % (prefix, uuid4().hex[:12])


def _error(handler, trace_id, status, reason, message):
    return {
        "ok": False,
        "data": {"success": False, "reason_code": reason, "message": message},
        "error": {"code": reason, "reason_code": reason, "message": message},
        "code": status,
        "meta": {
            "intent": handler.INTENT_TYPE,
            "trace_id": trace_id,
            "source_authority": handler.source_authority_contract(),
        },
    }


class ProductSystemParameterPublishHandler(BaseIntentHandler):
    INTENT_TYPE = "sc.product.system_parameter.publish"
    DESCRIPTION = "Publish a governed system parameter change with audit and rollback snapshot"
    VERSION = "1.0.0"
    ETAG_ENABLED = False
    REQUIRED_GROUPS = list(CONFIG_ADMIN_GROUPS)

    @staticmethod
    def source_authority_contract() -> dict:
        return {
            "kind": "product_system_parameter_publish",
            "authorities": [
                "config/product_system_parameter_catalog_v1.json",
                "res.company",
                "res.groups",
                "sc.product.system.parameter.change",
            ],
            "projection_only": False,
            "write_proxy": True,
            "runtime_carrier": "smart_construction_core.handlers.product_system_parameter_change",
        }

    def handle(self, payload=None, ctx=None):
        trace_id = _trace_id(self.context, "param_publish")
        if not any(_has_group(self.env.user, group) for group in CONFIG_ADMIN_GROUPS):
            return _error(self, trace_id, 403, "PERMISSION_DENIED", "只有行业配置管理员可以发布系统参数。")
        try:
            manifest = load_manifest(MODULE_MANIFEST)
        except Exception as exc:
            return _error(self, trace_id, 500, "PRODUCT_SYSTEM_PARAMETER_MANIFEST_MISSING", str(exc))
        params = payload if isinstance(payload, dict) else {}
        parameter_key = str(params.get("parameter_key") or "").strip()
        proposed_value = params.get("proposed_value")
        change_reason = str(params.get("change_reason") or "").strip()
        preview = impact_preview(manifest, parameter_key, proposed_value)
        if not preview.get("ok"):
            reason = str(preview.get("reason") or "REJECTED").upper()
            return _error(self, trace_id, 422, reason, "参数变更未通过影响预览，不能发布。")
        previous = read_parameter_value(self.env.company, parameter_key)
        apply_parameter_value(self.env.company, parameter_key, proposed_value)
        change = self.env["sc.product.system.parameter.change"].sudo().create(
            {
                "parameter_key": parameter_key,
                "proposed_value": proposed_value,
                "previous_value": previous,
                "state": "published",
                "company_id": self.env.company.id,
                "user_id": self.env.user.id,
                "change_reason": change_reason,
                "risk_level": str(preview.get("impact", {}).get("risk_level") or "low"),
                "published_at": fields.Datetime.now(),
                "audit_json": {
                    "impact": preview.get("impact") or {},
                    "reason": change_reason,
                },
            }
        )
        return {
            "ok": True,
            "data": {
                "success": True,
                "reason_code": "OK",
                "change": change.with_env(self.env).serialize(),
                "impact": preview.get("impact") or {},
            },
            "meta": {
                "intent": self.INTENT_TYPE,
                "trace_id": trace_id,
                "source_authority": self.source_authority_contract(),
            },
        }


class ProductSystemParameterRollbackHandler(BaseIntentHandler):
    INTENT_TYPE = "sc.product.system_parameter.rollback"
    DESCRIPTION = "Roll back a published system parameter change to its previous value"
    VERSION = "1.0.0"
    ETAG_ENABLED = False
    REQUIRED_GROUPS = list(CONFIG_ADMIN_GROUPS)

    @staticmethod
    def source_authority_contract() -> dict:
        return {
            "kind": "product_system_parameter_rollback",
            "authorities": [
                "sc.product.system.parameter.change",
                "res.company",
                "res.groups",
            ],
            "projection_only": False,
            "write_proxy": True,
            "runtime_carrier": "smart_construction_core.handlers.product_system_parameter_change",
        }

    def handle(self, payload=None, ctx=None):
        trace_id = _trace_id(self.context, "param_rollback")
        if not any(_has_group(self.env.user, group) for group in CONFIG_ADMIN_GROUPS):
            return _error(self, trace_id, 403, "PERMISSION_DENIED", "只有行业配置管理员可以回滚系统参数。")
        params = payload if isinstance(payload, dict) else {}
        change_id = int(params.get("change_id") or 0)
        if not change_id:
            return _error(self, trace_id, 400, "MISSING_CHANGE_ID", "缺少变更记录标识。")
        record = self.env["sc.product.system.parameter.change"].sudo().search(
            [("id", "=", change_id), ("company_id", "=", self.env.company.id)],
            limit=1,
        )
        if not record:
            return _error(self, trace_id, 404, "CHANGE_NOT_FOUND", "未找到当前公司的参数变更记录。")
        if record.state != "published":
            return _error(self, trace_id, 409, "CHANGE_NOT_ROLLBACKABLE", "只有已发布的变更可以回滚。")
        apply_parameter_value(self.env.company, record.parameter_key, record.previous_value)
        record.sudo().write(
            {
                "state": "rolled_back",
                "rolled_back_at": fields.Datetime.now(),
            }
        )
        return {
            "ok": True,
            "data": {
                "success": True,
                "reason_code": "OK",
                "change": record.with_env(self.env).serialize(),
                "restored_value": record.previous_value,
            },
            "meta": {
                "intent": self.INTENT_TYPE,
                "trace_id": trace_id,
                "source_authority": self.source_authority_contract(),
            },
        }
