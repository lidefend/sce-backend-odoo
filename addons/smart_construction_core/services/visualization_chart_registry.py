# -*- coding: utf-8 -*-
"""visualization.chart capability 只读契约登记（G6.1，ADR-002 条件 4「契约先行」）。

纪律（ADR-002 / custom-frontend-integration 总控 §3 表格禁令）：
- 只有本模块登记的 chart 定义可被前端消费；前端不得自由聚合财务/项目
  事实、不得向渲染层传任意 option。
- 每个 chart 定义必须声明 metric / dimensions / dataset 权威来源；
  未带 source_authority 的定义一律拒绝登记。
- 未登记 chart_key → handler 结构化降级（CHART_NOT_REGISTERED），
  前端渲染通用空态（复用 G3.2 四态状态机），不白屏。

数据契约：contracts/domain/chart.yaml v1（只读域，schema 版本
sc.visualization.chart.v1）。

本模块刻意保持纯 Python（不 import odoo），供 hermetic 桩加载测试
与 split guard 直接消费；数据构建回调在注册时注入。
"""
from __future__ import annotations

import re
from typing import Any, Callable, Dict, List, Optional

CHART_SCHEMA_VERSION = "sc.visualization.chart.v1"

CHART_KEY_REGEX = re.compile(r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")

ALLOWED_CHART_TYPES = ("bar", "line", "pie")

# dataset builder 回调签名：build(env, project_id) -> List[dict]（series 投影）
DatasetBuilder = Callable[[Any, int], List[Dict[str, Any]]]

_REQUIRED_TOP_FIELDS = ("key", "label", "chart_type", "metric", "dimensions")


def validate_chart_definition(defn: Dict[str, Any]) -> List[str]:
    """校验 chart 定义纪律；返回问题清单（空列表 = 合法）。"""
    issues: List[str] = []
    if not isinstance(defn, dict):
        return ["chart definition must be a dict"]

    for field in _REQUIRED_TOP_FIELDS:
        if not defn.get(field):
            issues.append(f"missing required field: {field}")

    key = defn.get("key")
    if isinstance(key, str) and not CHART_KEY_REGEX.match(key):
        issues.append(f"invalid chart key (expect domain.entity.name): {key}")

    chart_type = defn.get("chart_type")
    if chart_type not in ALLOWED_CHART_TYPES:
        issues.append(f"invalid chart_type (allowed {ALLOWED_CHART_TYPES}): {chart_type}")

    metric = defn.get("metric")
    if not (isinstance(metric, dict) and metric.get("key") and metric.get("label")):
        issues.append("metric must be a dict with key + label")

    dimensions = defn.get("dimensions")
    if not (isinstance(dimensions, list) and dimensions):
        issues.append("dimensions must be a non-empty list")
    elif isinstance(dimensions, list):
        for dim in dimensions:
            if not (isinstance(dim, dict) and dim.get("key") and dim.get("label")):
                issues.append(f"dimension must be a dict with key + label: {dim!r}")
                break

    source_authority = defn.get("source_authority")
    if not (
        isinstance(source_authority, dict)
        and source_authority.get("authorities")
        and source_authority.get("projection_only") is True
        and source_authority.get("no_business_fact_authority") is True
    ):
        issues.append(
            "source_authority must declare authorities + projection_only=True "
            "+ no_business_fact_authority=True"
        )

    if not callable(defn.get("dataset_builder")):
        issues.append("dataset_builder must be callable (backend authority)")

    return issues


_CHARTS: Dict[str, Dict[str, Any]] = {}


def register_chart(defn: Dict[str, Any]) -> None:
    """登记一个 chart 定义；违反契约纪律立即抛 ValueError（fail fast）。"""
    issues = validate_chart_definition(defn)
    if issues:
        raise ValueError(f"invalid chart definition {defn.get('key')!r}: {'; '.join(issues)}")
    key = defn["key"]
    if key in _CHARTS:
        raise ValueError(f"chart already registered: {key}")
    _CHARTS[key] = dict(defn)


def unregister_chart(key: str) -> None:
    """仅供测试/演示重建用；生产路径不应卸载已登记 capability。"""
    _CHARTS.pop(key, None)


def reset_charts() -> None:
    """清空注册表（测试隔离用）。"""
    _CHARTS.clear()


def get_chart(key: str) -> Optional[Dict[str, Any]]:
    """按 chart_key 取登记定义；未登记返回 None（handler 据此降级）。"""
    return _CHARTS.get(str(key or "").strip())


def list_chart_keys() -> List[str]:
    """已登记 chart key 清单（稳定排序，供清单/守卫消费）。"""
    return sorted(_CHARTS)
