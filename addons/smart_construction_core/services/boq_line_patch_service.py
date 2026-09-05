# -*- coding: utf-8 -*-
"""BOQ 行内联编辑（工程量 patch）服务纯函数（G7.2，G7_LAUNCH_SCOPING §4 切片 3）。

设计决策（G7.2-A 审计 + 用户批准，见 G7_LAUNCH_SCOPING §11）：
- 仅开放 quantity 编辑：改工程量 → 服务端 compute 链权威重算
  （amount/amount_leaf/qty_remain/version.total_amount），前端不形成金额事实；
- expected 基线值并发防护：请求携带客户端视角的当前工程量，服务端与
  DB 当前值比对，不一致即 BASELINE_MISMATCH（409 语义）——比 ETag 轻，
  与 confirm_token 摘要比对同思路；
- 权限复用既有组：cost_user / cost_manager（boq.line ACL 已是读写改/全权，
  单行常规写与 replace/update 批量重写不同风险级，不新造组）；
- 无 kill switch：回退面 = 版本状态闸（published 即锁）+ ACL + intent 不注册
  即不可达；写入范围仅 quantity 单字段。

幂等 + 审计：claim/complete_write_idempotency（event_code=BOQ_LINE_PATCH）
+ sc.audit.log before/after（utils/idempotency.py G7-INFRA 定式）。

模块级依赖纯标准库，Odoo 依赖由 handler 注入：桩测试（无 Odoo 环境）
只测工程量归一化/基线比对纯函数。
"""
from __future__ import annotations

PATCH_SCHEMA = "sc.boq.line.patch.v1"
EVENT_CODE = "BOQ_LINE_PATCH"
MUTABLE_VERSION_STATES = ("draft", "validated")
EDITABLE_FIELD = "quantity"
QTY_COMPARE_DIGITS = 6


def normalize_quantity(raw):
    """工程量归一化：None/非法/NaN/Inf → None；合法 → float。

    缺参（None）与非法（"abc"/NaN）都返回 None，由 handler 统一按
    MISSING_PARAMS 结构化拒绝——错误码不区分两者，避免探测面。
    """
    if raw is None:
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    if value != value:  # NaN
        return None
    if value in (float("inf"), float("-inf")):
        return None
    return value


def quantity_baseline_matches(expected, actual, digits=QTY_COMPARE_DIGITS) -> bool:
    """基线比对：round 到 digits 位后相等即一致。

    Float 直接 == 会被表示误差误伤（前端 JSON 往返）；digits=6 与
    Odoo 工程量字段的常规精度对齐。
    """
    try:
        return round(float(expected), digits) == round(float(actual), digits)
    except (TypeError, ValueError):
        return False


def qty_below_done(new_quantity, qty_done, digits=QTY_COMPARE_DIGITS) -> bool:
    """预检口径：新工程量低于累计完成量（ORM constraint 兜底前的友好降级）。"""
    try:
        return round(float(new_quantity), digits) < round(float(qty_done) or 0.0, digits)
    except (TypeError, ValueError):
        return True


def build_audit_payload(
    *,
    line_id,
    version_id,
    project_id,
    quantity_before,
    quantity_after,
    qty_done,
    amount_before,
    amount_after,
    idempotency_key,
    idempotency_fingerprint,
    trace_id,
    duration_ms,
    result,
):
    """sc.audit.log 事件载荷（before/after 工程量与重算合价 + 幂等键）。"""
    return {
        "field": EDITABLE_FIELD,
        "line_id": int(line_id or 0),
        "version_id": int(version_id or 0),
        "project_id": int(project_id or 0),
        "quantity_before": float(quantity_before or 0.0),
        "quantity_after": float(quantity_after or 0.0),
        "qty_done": float(qty_done or 0.0),
        "amount_before": round(float(amount_before or 0.0), 2),
        "amount_after": round(float(amount_after or 0.0), 2),
        "idempotency_key": str(idempotency_key or ""),
        "idempotency_fingerprint": str(idempotency_fingerprint or ""),
        "trace_id": str(trace_id or ""),
        "duration_ms": int(duration_ms or 0),
        "result_summary": {
            "success": bool((result or {}).get("success")),
            "quantity_delta": round(
                float((result or {}).get("quantity_after") or 0.0)
                - float((result or {}).get("quantity_before") or 0.0),
                6,
            ),
        },
    }
