# -*- coding: utf-8 -*-
"""驾驶舱付款执行图表块（G6.2，G6.1 ProjectChartBuilder 同款纪律镜像）。

只读投影块：本块不携带业务事实，仅声明受权数据引用
（fetch intent + chart_key + project_id）与展示文案。图表事实源由
``project.dashboard.chart.fetch`` intent 经 visualization_chart_registry
权威输出（payment.request / payment.ledger 只读聚合，无写入面）。

块状态语义（与 block.project.chart 同款纪律）：
- forbidden：required_groups 未满足；
- empty：无项目上下文，或 chart_key 未登记（CHART_NOT_REGISTERED 的
  块级前置表达，面板层仍会在 fetch 时二次降级）；
- ready：项目上下文与登记均就绪（数据本身可能为空，空 series 由
  面板渲染通用空态，不白屏）。
"""
from __future__ import annotations

from .base import BaseProjectBlockBuilder
from .project_chart_builder import ProjectChartBuilder

CHART_FETCH_INTENT = "project.dashboard.chart.fetch"
PAYMENT_EXECUTION_CHART_KEY = "project.payment.execution"


class ProjectPaymentChartBuilder(BaseProjectBlockBuilder):
    """付款执行图表块（visualization.chart capability 的驾驶舱挂接）。"""

    block_key = "block.project.chart.payment"
    block_type = "chart_dataset"
    title = "付款执行图表"
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
        chart_registered = ProjectChartBuilder._chart_registered(PAYMENT_EXECUTION_CHART_KEY)
        state = "ready" if chart_registered else "empty"
        return self._envelope(
            state=state,
            visibility=visibility,
            data=self._projection_data(project_id, chart_registered),
        )

    @staticmethod
    def _projection_data(project_id, chart_registered):
        return {
            "project_id": int(project_id or 0),
            "chart_key": PAYMENT_EXECUTION_CHART_KEY,
            "chart_registered": bool(chart_registered),
            "fetch_intent": CHART_FETCH_INTENT,
            "fetch_params": {
                "chart_key": PAYMENT_EXECUTION_CHART_KEY,
                "project_id": int(project_id or 0),
            },
            "loading_message": "正在加载付款执行图表...",
            "empty_message": "该项目暂无付款执行数据（图表未配置或无付款记录）。",
            "empty_message_no_context": "当前未指定项目上下文，无法展示付款执行图表。",
            "readonly": True,
        }
