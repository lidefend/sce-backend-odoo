# -*- coding: utf-8 -*-
"""BOQ 导入批次只读预检快照投影（G3.1）。

数据契约：contracts/domain/boq.yaml v1（只读域，安全降级语义见
safe_degradation 节）。
事实源：project.boq.import.batch.preview_payload（结构化快照
sc.boq.import.preview.v1，由既有导入向导在导入时写入）。
安全降级：批次不存在/不可访问 → 结构化 ok=false（不抛异常）；
preview_payload 非对象 → 空快照。访问判定交给 ir.model.access +
记录规则（search 语义，无权限与不存在同响应，避免批次枚举侧信道）。
"""
from __future__ import annotations

import time

from odoo.addons.smart_core.core.base_handler import BaseIntentHandler

PREVIEW_SCHEMA = "sc.boq.import.preview.v1"


class BoqImportPreviewFetchHandler(BaseIntentHandler):
    INTENT_TYPE = "project.boq.import.preview.fetch"
    DESCRIPTION = "返回工程量清单导入批次的只读预检快照"
    VERSION = "1.0.0"
    ETAG_ENABLED = False
    REQUIRED_GROUPS = ["base.group_user"]
    ACL_MODE = "record_rule"
    MACHINE_ACCESS = "read"
    SOURCE_AUTHORITY = {
        "kind": "boq_import_preview_readonly_projection",
        "authorities": [
            "project.boq.import.batch.preview_payload",
            "ir.model.access",
            "record_rule",
        ],
        "projection_only": True,
        "no_business_fact_authority": True,
    }

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------
    def _meta(self, ts0):
        return {
            "intent": self.INTENT_TYPE,
            "elapsed_ms": int((time.time() - ts0) * 1000),
            "trace_id": str((self.context or {}).get("trace_id") or ""),
            "source_authority": self.SOURCE_AUTHORITY,
        }

    def _error(self, code, message, suggested_action, ts0):
        return {
            "ok": False,
            "error": {
                "code": code,
                "message": message,
                "suggested_action": suggested_action,
            },
            "data": {},
            "meta": self._meta(ts0),
        }

    @staticmethod
    def _to_int(value):
        try:
            return int(str(value or "0").strip() or 0)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _serialize_batch(batch):
        preview = batch.preview_payload
        if not isinstance(preview, dict):
            # 安全降级：快照缺失/类型异常时以空对象表达，前端渲染空态。
            preview = {}
        return {
            "id": batch.id,
            "name": batch.name,
            "project_id": batch.project_id.id,
            "version_id": batch.version_id.id,
            "state": batch.state,
            "filename": batch.filename,
            "file_digest": batch.file_digest,
            "parser_schema": batch.parser_schema,
            "row_count": batch.row_count,
            "item_count": batch.item_count,
            "skipped_count": batch.skipped_count,
            "warning_count": batch.warning_count,
            "imported_at": batch.imported_at.isoformat() if batch.imported_at else False,
            "imported_by": batch.imported_by.id,
            "preview_payload": preview,
        }

    # ------------------------------------------------------------------
    # 入口
    # ------------------------------------------------------------------
    def handle(self, payload=None, ctx=None):
        ts0 = time.time()
        params = payload or self.params or {}
        if isinstance(params, dict) and isinstance(params.get("params"), dict):
            params = params.get("params") or {}

        batch_id = self._to_int(params.get("batch_id"))
        project_id = self._to_int(params.get("project_id"))
        if batch_id <= 0 and project_id <= 0:
            return self._error(
                "MISSING_PARAMS",
                "缺少参数：batch_id 或 project_id 至少提供一个",
                "fix_input",
                ts0,
            )

        Batch = self.env["project.boq.import.batch"]
        # search（而非 browse）确保 ir.model.access 与记录规则参与判定：
        # 无权限与不存在同语义，避免批次枚举侧信道。
        if batch_id > 0:
            batch = Batch.search([("id", "=", batch_id)], limit=1)
        else:
            batch = Batch.search(
                [("project_id", "=", project_id)],
                order="id desc",
                limit=1,
            )
        if not batch:
            return self._error(
                "BATCH_NOT_FOUND",
                "未找到可访问的清单导入批次",
                "check_params",
                ts0,
            )

        data = {
            "batch": self._serialize_batch(batch),
            "preview_schema": PREVIEW_SCHEMA,
            "safe_degradation": {
                "missing_payload_policy": (
                    "preview_payload 非对象时以空快照降级，前端须可渲染空态"
                ),
            },
        }
        return {"ok": True, "data": data, "meta": self._meta(ts0)}
