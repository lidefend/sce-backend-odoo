# -*- coding: utf-8 -*-
"""BOQ 导出请求 handler（G6.3，ADR-004 决策 1/2/3）。

数据契约：contracts/domain/boq-export.yaml v1（只读导出投影）。
事实源：project.boq.version / project.boq.line（search 语义，
ir.model.access + 记录规则判定，不可访问与不存在同响应）。
生成引擎：services/boq_export_service.py（xlsxwriter，惰性导入）。
文件载体：ir.attachment（sudo 建档挂版本记录，请求者对版本有读权即可下载）。
观测：sc.ops.job 记录（job_type=boq.export，status=done + result_json），
状态可经 /api/ops/job/status 查询；异步执行路径按 G7 首切片立项。
安全降级：MISSING_PARAMS / VERSION_NOT_FOUND / EXPORT_EMPTY /
EXPORT_TOO_LARGE / EXPORT_ERROR 全部结构化返回，不向前端抛异常。
"""
from __future__ import annotations

import time

from odoo import fields
from odoo.addons.smart_core.core.base_handler import BaseIntentHandler

from odoo.addons.smart_construction_core.services import boq_export_service as svc

COST_FULL_GROUPS = (
    "smart_construction_core.group_sc_cap_cost_manager",
    "smart_construction_core.group_sc_cap_cost_user",
)


class BoqExportRequestHandler(BaseIntentHandler):
    INTENT_TYPE = "project.boq.export.request"
    DESCRIPTION = "后端生成工程量清单 xlsx 导出（列按授权组裁剪）"
    VERSION = "1.0.0"
    ETAG_ENABLED = False
    REQUIRED_GROUPS = ["base.group_user"]
    ACL_MODE = "record_rule"
    MACHINE_ACCESS = "read"
    SOURCE_AUTHORITY = {
        "kind": "boq_export_readonly_projection",
        "authorities": [
            "project.boq.version",
            "project.boq.line",
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

    def _has_cost_access(self, env):
        user = env.user
        for group_xmlid in COST_FULL_GROUPS:
            if user.has_group(group_xmlid):
                return True
        return False

    @staticmethod
    def _section_label_resolver(env):
        field = env["project.boq.line"]._fields["section_type"]
        selection = field.selection
        if callable(selection):
            selection = selection(env)
        mapping = dict(selection or [])
        return lambda value: mapping.get(value, value or "")

    # ------------------------------------------------------------------
    # 入口
    # ------------------------------------------------------------------
    def handle(self, payload=None, ctx=None):
        ts0 = time.time()
        params = payload or self.params or {}
        if isinstance(params, dict) and isinstance(params.get("params"), dict):
            params = params.get("params") or {}

        project_id = self._to_int(params.get("project_id"))
        version_id = self._to_int(params.get("version_id"))
        if project_id <= 0:
            return self._error(
                "MISSING_PARAMS",
                "缺少参数：project_id 必填",
                "fix_input",
                ts0,
            )

        env = self.env
        Version = env["project.boq.version"]
        domain = [("project_id", "=", project_id)]
        if version_id > 0:
            domain.append(("id", "=", version_id))
        # search（而非 browse）确保 ir.model.access 与记录规则参与判定：
        # 无权限与不存在同语义，避免版本枚举侧信道。
        version = Version.search(domain, order="id desc", limit=1)
        if not version:
            return self._error(
                "VERSION_NOT_FOUND",
                "未找到可访问的清单版本",
                "check_params",
                ts0,
            )

        Line = env["project.boq.line"]
        lines = Line.search(
            [("version_id", "=", version.id)], order="parent_path, sequence, id"
        )
        if not lines:
            return self._error(
                "EXPORT_EMPTY",
                "该清单版本下没有可导出的明细行",
                "check_data",
                ts0,
            )
        if len(lines) > svc.EXPORT_ROW_LIMIT:
            return self._error(
                "EXPORT_TOO_LARGE",
                "导出行数 %d 超过上限 %d；异步 job 路径尚未开放" % (len(lines), svc.EXPORT_ROW_LIMIT),
                "wait_for_job_path",
                ts0,
            )

        columns, cropped_keys, crop_reason = svc.resolve_columns(
            self._has_cost_access(env)
        )
        label_resolver = self._section_label_resolver(env)
        row_values = [svc.build_row_values(line, label_resolver) for line in lines]

        try:
            payload_bytes = svc.build_workbook_bytes(columns, row_values)
        except Exception as exc:  # 引擎异常结构化降级，不向前端抛异常
            return self._error(
                "EXPORT_ERROR",
                "导出文件生成失败：%s" % exc,
                "retry",
                ts0,
            )

        digest = svc.digest_bytes(payload_bytes)
        filename = svc.build_filename(version.project_id.name, version.code)
        attachment = env["ir.attachment"].sudo().create(
            {
                **svc.attachment_values(filename, payload_bytes),
                "res_model": "project.boq.version",
                "res_id": version.id,
            }
        )

        now = fields.Datetime.now()
        job = env["sc.ops.job"].sudo().create(
            {
                "name": "BOQ 导出 %s" % filename,
                "job_type": "boq.export",
                "status": "done",
                "started_at": now,
                "finished_at": now,
                "payload_json": {
                    "project_id": project_id,
                    "version_id": version.id,
                    "requested_by": env.user.id,
                },
                "result_json": {
                    "attachment_id": attachment.id,
                    "filename": filename,
                    "row_count": len(lines),
                    "file_digest": digest,
                    "cropped_columns": cropped_keys,
                },
                "trace_id": str((self.context or {}).get("trace_id") or ""),
            }
        )

        data = {
            "schema": svc.EXPORT_SCHEMA,
            "readonly": True,
            "export": {
                "version_id": version.id,
                "version_code": version.code,
                "project_id": project_id,
                "row_count": len(lines),
                "columns": [key for key, _label, _amt in columns],
                "cropped_columns": cropped_keys,
                "crop_reason": crop_reason,
                "file_digest": digest,
                "row_limit": svc.EXPORT_ROW_LIMIT,
            },
            "attachment": {
                "id": attachment.id,
                "filename": filename,
                "mimetype": svc.XLSX_MIMETYPE,
                "size": len(payload_bytes),
                "download_url": (
                    "/web/content?model=ir.attachment&id=%d"
                    "&field=datas&filename_field=name&download=true" % attachment.id
                ),
            },
            "job_id": job.id,
        }
        return {"ok": True, "data": data, "meta": self._meta(ts0)}
