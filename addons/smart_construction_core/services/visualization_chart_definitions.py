# -*- coding: utf-8 -*-
"""真实 chart 登记（G6.1 Task #100 起，G6.2 扩展批次）。

已登记 chart：
- project.cost.structure（G6.1）：成本结构，预算目标 vs 实际成本，
  按成本科目分组的双系列柱状图；
- project.payment.execution（G6.2）：付款执行趋势，申请金额 vs 已付
  金额，按月双系列折线图；
- project.contract.distribution（G6.2）：合同金额方向分布，
  按合同方向分组的饼图。

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

from typing import Any, Dict, List, Tuple

from odoo.addons.smart_construction_core.services import visualization_chart_registry as registry

COST_LEDGER_MODEL = "project.cost.ledger"
BUDGET_ALLOC_MODEL = "project.budget.cost.alloc"
PAYMENT_REQUEST_MODEL = "payment.request"
PAYMENT_LEDGER_MODEL = "payment.ledger"
GENERAL_CONTRACT_MODEL = "sc.general.contract"

COST_STRUCTURE_CHART_KEY = "project.cost.structure"
PAYMENT_EXECUTION_CHART_KEY = "project.payment.execution"
CONTRACT_DISTRIBUTION_CHART_KEY = "project.contract.distribution"
COST_STRUCTURE_FETCH_INTENT = "project.dashboard.chart.fetch"

_DIMENSION_KEY = "cost_code"
_DIMENSION_LABEL = "成本科目"

_MONTH_DIMENSION_KEY = "month"
_MONTH_DIMENSION_LABEL = "月份"


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


# ---------------------------------------------------------------------------
# G6.2：付款执行趋势（project.payment.execution，line）
# ---------------------------------------------------------------------------


def _safe_monthly_sums(env, model_name, domain, date_field, sum_field) -> Dict[str, float]:
    """按自然月聚合金额；返回 {ISO 月标签: 合计}。

    月桶刻意用 search_read + Python 归桶（而非 read_group ``:month``）：
    read_group 的月分组标签是本地化显示名（如「2026年9月」），无法字典序
    排序；ISO 标签 ``YYYY-MM`` 字典序即时间序，line 图类目顺序才确定。
    聚合仍全部在后端 dataset_builder 内完成（后端权威不变）。

    模型/字段缺失或查询异常一律返回空映射（降级空态，chart.yaml
    safe_degradation 语义）。
    """
    try:
        model = env[model_name]
    except Exception:  # noqa: BLE001 - 模型缺失（模块未装）按空数据处理
        return {}
    try:
        fields_map = getattr(model, "_fields", {})
        if date_field not in fields_map or sum_field not in fields_map:
            return {}
        rows = model.search_read(domain, [date_field, sum_field])
    except Exception:  # noqa: BLE001 - 查询异常按空数据处理（不抛给 handler）
        return {}

    sums: Dict[str, float] = {}
    for row in rows or []:
        raw = row.get(date_field)
        label = str(raw or "")[:7] if raw else ""
        if len(label) != 7 or label[4] != "-" or not label[:4].isdigit():
            continue
        sums[label] = sums.get(label, 0.0) + float(row.get(sum_field) or 0.0)
    return sums


def _month_points(sums: Dict[str, float]) -> List[Dict[str, Any]]:
    """月度求和映射 → 升序时间序点位（ISO 标签字典序即时间序）。"""
    return [
        {"dimension_value": label, "value": round(float(sums[label]), 2)}
        for label in sorted(sums)
        if sums.get(label)
    ]


def payment_execution_dataset_builder(env, project_id) -> List[Dict[str, Any]]:
    """付款执行 dataset 构建：申请金额 vs 已付金额（按月，line 双系列）。

    - 申请金额：payment.request（排除已取消），按 date_request 月桶；
    - 已付金额：payment.ledger（仅 posted 有效台账），按 paid_at 月桶；
    - 两系列共用月份并集（缺失月不造点，与 cost.structure 同纪律）。
    """
    pid = int(project_id or 0)

    requested = _safe_monthly_sums(
        env,
        PAYMENT_REQUEST_MODEL,
        [("project_id", "=", pid), ("state", "!=", "cancel")],
        "date_request",
        "amount",
    )
    paid = _safe_monthly_sums(
        env,
        PAYMENT_LEDGER_MODEL,
        [("project_id", "=", pid), ("state", "=", "posted")],
        "paid_at",
        "amount",
    )

    if not requested and not paid:
        return []

    return [
        {
            "name": "申请金额",
            "metric": {"key": "amount", "label": "申请金额"},
            "dimensions": {"key": _MONTH_DIMENSION_KEY, "label": _MONTH_DIMENSION_LABEL},
            "points": _month_points(requested),
        },
        {
            "name": "已付金额",
            "metric": {"key": "amount", "label": "已付金额"},
            "dimensions": {"key": _MONTH_DIMENSION_KEY, "label": _MONTH_DIMENSION_LABEL},
            "points": _month_points(paid),
        },
    ]


def _payment_execution_definition() -> Dict[str, Any]:
    return {
        "key": PAYMENT_EXECUTION_CHART_KEY,
        "label": "付款执行趋势（申请 vs 已付）",
        "chart_type": "line",
        "unit": "CNY",
        "metric": {"key": "amount", "label": "金额"},
        "dimensions": [{"key": _MONTH_DIMENSION_KEY, "label": _MONTH_DIMENSION_LABEL}],
        "source_authority": {
            "kind": "project_payment_readonly_projection",
            "authorities": [
                PAYMENT_REQUEST_MODEL,
                PAYMENT_LEDGER_MODEL,
                "odoo.orm",
                "odoo.search_read",
                "ir.model.access",
                "record_rule",
            ],
            "projection_only": True,
            "no_business_fact_authority": True,
        },
        "dataset_builder": payment_execution_dataset_builder,
    }


# ---------------------------------------------------------------------------
# G6.2：合同方向金额分布（project.contract.distribution，pie）
# ---------------------------------------------------------------------------


def _safe_read_group_by_direction(env, model_name, domain, sum_field) -> Tuple[Dict[str, float], Dict[str, str]]:
    """按 contract_direction read_group 求和；返回 ({原始键: 合计}, {原始键: 展示名})。"""
    try:
        model = env[model_name]
    except Exception:  # noqa: BLE001 - 模型缺失（模块未装）按空数据处理
        return {}, {}
    try:
        fields_map = getattr(model, "_fields", {})
        if "contract_direction" not in fields_map or sum_field not in fields_map:
            return {}, {}
        rows = model.read_group(domain, [sum_field], ["contract_direction"])
        direction_field = fields_map.get("contract_direction")
        selection = getattr(direction_field, "selection", None) or []
        if callable(selection):
            selection = selection(model)
        labels = {str(key): str(label) for key, label in selection}
    except Exception:  # noqa: BLE001 - 查询异常按空数据处理（不抛给 handler）
        return {}, {}

    sums: Dict[str, float] = {}
    for row in rows or []:
        raw_key = row.get("contract_direction")
        key = str(raw_key or "").strip()
        if not key or key == "False":
            continue
        sums[key] = sums.get(key, 0.0) + float(row.get(sum_field) or 0.0)
    return sums, labels


def contract_distribution_dataset_builder(env, project_id) -> List[Dict[str, Any]]:
    """合同方向金额分布 dataset 构建（pie 单系列）。

    - sc.general.contract（排除已取消），按 contract_direction 分组求
      amount_total；点位用选择项展示名（收入合同/支出合同/…）；
    - 方向缺失（False）的合同不造点（与 cost.structure 缺失侧纪律一致）。
    """
    pid = int(project_id or 0)
    sums, labels = _safe_read_group_by_direction(
        env,
        GENERAL_CONTRACT_MODEL,
        [("project_id", "=", pid), ("state", "!=", "cancel")],
        "amount_total",
    )
    if not sums:
        return []

    points = [
        {
            "dimension_value": labels.get(key) or key,
            "value": round(float(sums[key]), 2),
        }
        for key in sorted(sums)
    ]
    return [
        {
            "name": "合同金额",
            "metric": {"key": "amount_total", "label": "合同金额"},
            "dimensions": {"key": "contract_direction", "label": "合同方向"},
            "points": points,
        }
    ]


def _contract_distribution_definition() -> Dict[str, Any]:
    return {
        "key": CONTRACT_DISTRIBUTION_CHART_KEY,
        "label": "合同金额方向分布",
        "chart_type": "pie",
        "unit": "CNY",
        "metric": {"key": "amount_total", "label": "合同金额"},
        "dimensions": [{"key": "contract_direction", "label": "合同方向"}],
        "source_authority": {
            "kind": "project_contract_readonly_projection",
            "authorities": [
                GENERAL_CONTRACT_MODEL,
                "odoo.orm",
                "odoo.read_group",
                "ir.model.access",
                "record_rule",
            ],
            "projection_only": True,
            "no_business_fact_authority": True,
        },
        "dataset_builder": contract_distribution_dataset_builder,
    }


registry.register_chart(_payment_execution_definition())
registry.register_chart(_contract_distribution_definition())
