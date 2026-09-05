# -*- coding: utf-8 -*-
"""首个真实 chart 登记（G6.1 Task #100，ADR-002 条件 4 契约先行）。

chart_key: project.cost.structure（成本结构：预算目标 vs 实际成本，
按成本科目分组的双系列柱状图）。

事实源（source_authority 声明的权威模型/服务）：
- project.budget.cost.alloc（预算清单×成本科目分摊，amount_budget）
- project.cost.ledger（成本台账，amount）
- 两者均经 ir.model.access + 记录规则判定可见性（read_group 走 ORM，
  项目不可访问在 handler 层已以 search 语义拦截）。

纪律：
- 本模块只登记定义；数据聚合全部在 dataset_builder 内以 read_group
  完成（后端权威投影），前端不得聚合、不得补点、不得改写数值；
- 任何模型/字段缺失或查询异常一律返回空 series（handler 正常返回，
  前端渲染空态，不抛异常、不白屏——chart.yaml safe_degradation 语义）；
- 类目按展示名稳定排序，两系列共用同一类目全集（缺失侧不造点）。
"""
from __future__ import annotations

from typing import Any, Dict, List

from odoo.addons.smart_construction_core.services import visualization_chart_registry as registry

COST_LEDGER_MODEL = "project.cost.ledger"
BUDGET_ALLOC_MODEL = "project.budget.cost.alloc"

COST_STRUCTURE_CHART_KEY = "project.cost.structure"
COST_STRUCTURE_FETCH_INTENT = "project.dashboard.chart.fetch"

_DIMENSION_KEY = "cost_code"
_DIMENSION_LABEL = "成本科目"


def _safe_read_group_by_cost_code(env, model_name, domain, sum_field):
    """按成本科目 read_group 求和；异常/字段缺失返回空映射（降级为空态）。"""
    try:
        model = env[model_name]
    except Exception:  # noqa: BLE001 - 模型缺失（模块未装）按空数据处理
        return {}
    try:
        model_fields = getattr(model, "_fields", {})
        if "cost_code_id" not in model_fields or sum_field not in model_fields:
            return {}
        rows = model.read_group(domain, [sum_field], ["cost_code_id"])
    except Exception:  # noqa: BLE001 - 查询异常按空数据处理（不抛给 handler）
        return {}

    grouped: Dict[int, float] = {}
    labels: Dict[int, str] = {}
    for row in rows or []:
        group = row.get("cost_code_id")
        value = row.get(sum_field) or 0.0
        if isinstance(group, (list, tuple)) and len(group) >= 2:
            code_id = int(group[0] or 0)
            label = str(group[1] or "").strip()
        elif isinstance(group, (int, float)) or (isinstance(group, str) and str(group).isdigit()):
            code_id = int(group or 0)
            label = ""
        else:
            continue
        if code_id <= 0:
            continue
        grouped[code_id] = grouped.get(code_id, 0.0) + float(value or 0.0)
        if label:
            labels[code_id] = label
    return {"sums": grouped, "labels": labels}


def _series_points(sums, labels, categories):
    """把按 code_id 的求和映射对齐到类目全集（缺失侧不造点、不伪造 0）。"""
    by_label = {}
    for code_id, total in sums.items():
        label = labels.get(code_id) or f"科目#{code_id}"
        by_label[label] = by_label.get(label, 0.0) + float(total or 0.0)
    return [
        {"dimension_value": label, "value": round(float(by_label[label]), 2)}
        for label in categories
        if label in by_label
    ]


def cost_structure_dataset_builder(env, project_id) -> List[Dict[str, Any]]:
    """成本结构 dataset 构建（后端权威聚合）。

    签名由 visualization_chart_registry.DatasetBuilder 钉死：
    build(env, project_id) -> List[series 投影]。
    """
    pid = int(project_id or 0)

    budget = _safe_read_group_by_cost_code(
        env, BUDGET_ALLOC_MODEL, [("project_id", "=", pid)], "amount_budget"
    )
    actual = _safe_read_group_by_cost_code(
        env, COST_LEDGER_MODEL, [("project_id", "=", pid)], "amount"
    )

    all_labels: Dict[int, str] = {}
    all_labels.update(budget.get("labels") or {})
    all_labels.update(actual.get("labels") or {})

    budget_sums = budget.get("sums") or {}
    actual_sums = actual.get("sums") or {}
    known_ids = set(budget_sums) | set(actual_sums)
    if not known_ids:
        return []

    label_by_id = {
        code_id: all_labels.get(code_id) or f"科目#{code_id}" for code_id in known_ids
    }
    categories = sorted(label_by_id.values())

    return [
        {
            "name": "预算目标",
            "metric": {"key": "amount_budget", "label": "预算金额"},
            "dimensions": {"key": _DIMENSION_KEY, "label": _DIMENSION_LABEL},
            "points": _series_points(budget_sums, all_labels, categories),
        },
        {
            "name": "实际成本",
            "metric": {"key": "amount", "label": "实际金额"},
            "dimensions": {"key": _DIMENSION_KEY, "label": _DIMENSION_LABEL},
            "points": _series_points(actual_sums, all_labels, categories),
        },
    ]


def _cost_structure_definition() -> Dict[str, Any]:
    return {
        "key": COST_STRUCTURE_CHART_KEY,
        "label": "成本结构（预算 vs 实际）",
        "chart_type": "bar",
        "unit": "CNY",
        "metric": {"key": "amount", "label": "金额"},
        "dimensions": [{"key": _DIMENSION_KEY, "label": _DIMENSION_LABEL}],
        "source_authority": {
            "kind": "project_cost_readonly_projection",
            "authorities": [
                BUDGET_ALLOC_MODEL,
                COST_LEDGER_MODEL,
                "odoo.orm",
                "odoo.read_group",
                "ir.model.access",
                "record_rule",
            ],
            "projection_only": True,
            "no_business_fact_authority": True,
        },
        "dataset_builder": cost_structure_dataset_builder,
    }


registry.register_chart(_cost_structure_definition())
