# -*- coding: utf-8 -*-
"""可视化图表只读数据投影（G6.1，ADR-002 条件 4「契约先行」）。

数据契约：contracts/domain/chart.yaml v1（只读域，schema 版本
sc.visualization.chart.v1）。
事实源：visualization_chart_registry 登记的 dataset_builder（后端权威，
前端不得自由聚合、不得传任意 option）。
安全降级（ADR-002 回退策略）：
- chart 未登记 → 结构化 ok=false（CHART_NOT_REGISTERED，不抛异常），
  前端渲染通用空态（复用 G3.2 四态状态机），不白屏；
- 项目不可访问与不存在同语义（search 判定，避免枚举侧信道）；
- dataset_builder 异常 → CHART_DATASET_ERROR 同样降级。
"""
from __future__ import annotations

import time

from odoo.addons.smart_core.core.base_handler import BaseIntentHandler
from odoo.addons.smart_construction_core.services import visualization_chart_registry

PROJECT_MODEL = "project.project"


class VisualizationChartFetchHandler(BaseIntentHandler):
    INTENT_TYPE = "project.dashboard.chart.fetch"
    DESCRIPTION = "返回登记图表（visualization.chart capability）的只读数据投影"
    VERSION = "1.0.0"
    ETAG_ENABLED = False
    REQUIRED_GROUPS = ["base.group_user"]
    ACL_MODE = "record_rule"
    MACHINE_ACCESS = "read"
    SOURCE_AUTHORITY = {
        "kind": "visualization_chart_readonly_projection",
        "authorities": [
            "smart_construction_core.services.visualization_chart_registry",
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

    def _error(self, code, message, suggested_action, ts0, data=None):
        return {
            "ok": False,
            "error": {
                "code": code,
                "message": message,
                "suggested_action": suggested_action,
            },
            "data": data or {},
            "meta": self._meta(ts0),
        }

    @staticmethod
    def _to_int(value):
        try:
            return int(str(value or "0").strip() or 0)
        except (TypeError, ValueError):
            return 0

    # ------------------------------------------------------------------
    # 入口
    # ------------------------------------------------------------------
    def handle(self, payload=None, ctx=None):
        ts0 = time.time()
        params = payload or self.params or {}
        if isinstance(params, dict) and isinstance(params.get("params"), dict):
            params = params.get("params") or {}

        chart_key = str(params.get("chart_key") or "").strip()
        project_id = self._to_int(params.get("project_id"))
        if not chart_key or project_id <= 0:
            return self._error(
                "MISSING_PARAMS",
                "缺少参数：chart_key 与 project_id 必须同时提供",
                "fix_input",
                ts0,
            )

        chart = visualization_chart_registry.get_chart(chart_key)
        if not chart:
            # 未登记 capability → 结构化降级，前端渲染通用空态，不白屏。
            return self._error(
                "CHART_NOT_REGISTERED",
                f"图表未登记或不可用：{chart_key}",
                "fix_input",
                ts0,
                data={"chart_key": chart_key, "schema": visualization_chart_registry.CHART_SCHEMA_VERSION},
            )

        # search（而非 browse）确保 ir.model.access 与记录规则参与判定：
        # 无权限与不存在同语义，避免项目枚举侧信道。
        project = self.env[PROJECT_MODEL].search([("id", "=", project_id)], limit=1)
        if not project:
            return self._error(
                "PROJECT_NOT_FOUND",
                "项目不存在或当前账号不可访问",
                "check_params",
                ts0,
                data={"chart_key": chart_key},
            )

        try:
            series = chart["dataset_builder"](self.env, project_id)
        except Exception:  # noqa: BLE001 - 构建器异常一律结构化降级，不抛给前端
            return self._error(
                "CHART_DATASET_ERROR",
                "图表数据构建失败，已降级为空态",
                "retry_or_contact_admin",
                ts0,
                data={"chart_key": chart_key},
            )

        data = {
            "schema": visualization_chart_registry.CHART_SCHEMA_VERSION,
            "chart_key": chart["key"],
            "chart_type": chart["chart_type"],
            "title": chart["label"],
            "unit": str(chart.get("unit") or ""),
            "readonly": True,
            "series": list(series or []),
            "safe_degradation": {
                "chart_not_registered_policy": (
                    "未登记 chart_key 以结构化错误降级，前端须可渲染通用空态"
                ),
            },
        }
        return {"ok": True, "data": data, "meta": self._meta(ts0)}
