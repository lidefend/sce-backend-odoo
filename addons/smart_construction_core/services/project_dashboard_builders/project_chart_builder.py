# -*- coding: utf-8 -*-
"""驾驶舱成本结构图表块（G6.1 Task #100，G3.3 块挂接先例镜像）。

只读投影块：本块不携带业务事实，仅声明受权数据引用
（fetch intent + chart_key + project_id）与展示文案（行业语义归
P1 后端，共享层包装组件只保留通用 fallback）。图表事实源由
``project.dashboard.chart.fetch`` intent 经 visualization_chart_registry
权威输出，与 contracts/domain/chart.yaml v1 的 safe_degradation 语义一致。

块状态语义（与 boq_preview 块同款纪律）：
- forbidden：required_groups 未满足；
- empty：无项目上下文，或 chart_key 未登记（CHART_NOT_REGISTERED 的
  块级前置表达，面板层仍会在 fetch 时二次降级）；
- ready：项目上下文与登记均就绪（数据本身可能为空，空 series 由
  面板渲染通用空态，不白屏）。
"""
from __future__ import annotations

from .base import BaseProjectBlockBuilder

CHART_FETCH_INTENT = "project.dashboard.chart.fetch"
COST_STRUCTURE_CHART_KEY = "project.cost.structure"


class ProjectChartBuilder(BaseProjectBlockBuilder):
    """成本结构图表块（visualization.chart capability 的驾驶舱挂接）。"""

    block_key = "block.project.chart"
    block_type = "chart_dataset"
    title = "成本结构图表"
    required_groups = ()

    SOURCE_KIND = "visualization_chart_block_projection"
    SOURCE_AUTHORITIES = (
        "smart_construction_core.services.visualization_chart_registry",
        "project.dashboard.chart.fetch",
    )

    def build(self, project=None, context=None):
        visibility = self._visibility()
        if not visibility.get("allowed"):
            return self._envelope(
                state="forbidden",
                visibility=visibility,
                data=self._projection_data(0, False),
            )
        if not project:
            return self._envelope(
                state="empty",
                visibility=visibility,
                data=self._projection_data(0, False),
            )

        project_id = int(getattr(project, "id", 0) or 0)
        chart_registered = self._chart_registered(COST_STRUCTURE_CHART_KEY)
        state = "ready" if chart_registered else "empty"
        return self._envelope(
            state=state,
            visibility=visibility,
            data=self._projection_data(project_id, chart_registered),
        )

    @staticmethod
    def _chart_registered(chart_key):
        """调用时惰性解析注册表（避免 services 包初始化期的循环导入）。

        注册表不可达 / 未登记 / 异常一律按未登记降级（块级 empty）；
        未登记的最终事实由 fetch intent 层二次降级（CHART_NOT_REGISTERED）。
        """
        try:
            from odoo.addons.smart_construction_core.services import (
                visualization_chart_registry,
            )

            return visualization_chart_registry.get_chart(chart_key) is not None
        except Exception:  # noqa: BLE001 - 注册表不可达时按未登记降级
            return False

    @staticmethod
    def _projection_data(project_id, chart_registered):
        return {
            "project_id": int(project_id or 0),
            "chart_key": COST_STRUCTURE_CHART_KEY,
            "chart_registered": bool(chart_registered),
            "fetch_intent": CHART_FETCH_INTENT,
            "fetch_params": {
                "chart_key": COST_STRUCTURE_CHART_KEY,
                "project_id": int(project_id or 0),
            },
            "loading_message": "正在加载成本结构图表...",
            "empty_message": "该项目暂无成本结构数据（图表未配置或无成本记录）。",
            "empty_message_no_context": "当前未指定项目上下文，无法展示成本结构图表。",
            "readonly": True,
        }
