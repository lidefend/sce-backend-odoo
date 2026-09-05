# -*- coding: utf-8 -*-
"""BOQ 危险导入（replace/update）服务纯函数（G7.1，ADR-004 决策 4）。

四件套（G7_LAUNCH_SCOPING §5）：
- 专用权限组：smart_construction_core.group_sc_cap_boq_dangerous_import（handler 侧
  REQUIRED_GROUPS 声明，不并入既有业务组）；
- kill switch：ir.config_parameter sc.boq.dangerous_import.enabled，默认关闭
  （fail-closed：参数缺失/非真值一律视为关闭，§14「默认关闭」契约）；
- 确认摘要：preview 干跑产出影响摘要 + confirm_token（sha256 绑定
  version/mode/类别/文件摘要/摘要指纹/主体）；execute 重算比对，防
  TOCTOU 与并发版本漂移（摘要逐位一致才放行）；
- 幂等 + 审计：claim/complete_write_idempotency（event_code=BOQ_IMPORT_DANGEROUS）
  + sc.audit.log before/after 摘要（utils/idempotency.py G7-INFRA 定式）。

模式语义：
- replace：整版重写——删除目标版本（draft/validated）全部明细行后按导入文件重建；
- update：按清单编码匹配——编码在版本中唯一→更新该行；编码不存在→新增行；
  编码在版本中重复出现且出现在文件中→fail-closed 拒绝（AMBIGUOUS_CODES）。

模块级依赖纯标准库（hashlib/json），Odoo 依赖由 handler 注入：
桩测试（无 Odoo 环境）只测影响摘要/令牌/开关纯函数。
"""
from __future__ import annotations

import hashlib
import json

DANGEROUS_IMPORT_SCHEMA = "sc.boq.dangerous.import.v1"
FLAG_KEY = "sc.boq.dangerous_import.enabled"
EVENT_CODE = "BOQ_IMPORT_DANGEROUS"
CONFIRM_TOKEN_SALT = "sc.boq.dangerous.import.confirm.v1"
MUTABLE_VERSION_STATES = ("draft", "validated")
MODES = ("replace", "update")
AMBIGUOUS_CODE_SAMPLE_LIMIT = 20


def flag_enabled(raw_param_value) -> bool:
    """kill switch 判定：fail-closed，仅显式真值为开。"""
    return str(raw_param_value or "").strip().lower() in ("1", "true", "yes", "on")


def normalize_mode(raw) -> str:
    mode = str(raw or "").strip().lower()
    return mode if mode in MODES else ""


def row_amount(row) -> float:
    """行金额口径（与向导预检一致）：来源合价优先，否则数量×单价。"""
    try:
        if row.get("has_imported_amount"):
            return float(row.get("imported_amount") or 0.0)
        return float(row.get("quantity") or 0.0) * float(row.get("price") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _parsed_item_rows(parsed_rows):
    return [
        row for row in (parsed_rows or []) if (row.get("line_type") or "item") == "item"
    ]


def summarize_impact(mode, existing_lines, parsed_rows):
    """影响摘要纯函数。

    existing_lines: [{id, code, quantity, price, imported_amount,
    has_imported_amount}, ...]（handler 从 project.boq.line 投影）。
    parsed_rows: 向导 _parse_file 输出行。
    返回 (summary_dict, ambiguous_codes_in_file)。
    """
    existing = list(existing_lines or [])
    item_rows = _parsed_item_rows(parsed_rows)
    amount_before = sum(row_amount(row) for row in existing)
    base = {
        "mode": mode,
        "existing_line_count": len(existing),
        "parsed_item_count": len(item_rows),
        "amount_before": round(amount_before, 2),
    }
    if mode == "replace":
        amount_after = sum(row_amount(row) for row in item_rows)
        summary = dict(
            base,
            lines_to_delete=len(existing),
            lines_to_create=len(item_rows),
            amount_after=round(amount_after, 2),
            amount_delta=round(amount_after - amount_before, 2),
        )
        return summary, []

    # update：按 code 匹配；版本内重复 code 视为歧义（fail-closed）
    counts = {}
    for row in existing:
        code = str(row.get("code") or "").strip()
        if code:
            counts[code] = counts.get(code, 0) + 1
    file_rows = {}
    for row in item_rows:
        code = str(row.get("code") or "").strip()
        if code:
            file_rows.setdefault(code, row)
    ambiguous_in_file = sorted(
        code for code, count in counts.items() if count > 1 and code in file_rows
    )
    if ambiguous_in_file:
        return dict(base, ambiguous_codes=ambiguous_in_file), ambiguous_in_file

    file_codes = set(file_rows)
    amount_after = 0.0
    to_update = 0
    to_keep = 0
    for row in existing:
        code = str(row.get("code") or "").strip()
        if code and code in file_rows:
            amount_after += row_amount(file_rows[code])
            to_update += 1
        else:
            amount_after += row_amount(row)
            to_keep += 1
    to_create = sum(1 for code in file_codes if code not in counts)
    amount_after += sum(
        row_amount(row) for code, row in file_rows.items() if code not in counts
    )
    summary = dict(
        base,
        lines_to_update=to_update,
        lines_to_create=to_create,
        lines_to_keep=to_keep,
        amount_after=round(amount_after, 2),
        amount_delta=round(amount_after - amount_before, 2),
    )
    return summary, []


def build_confirm_token(
    *,
    version_id,
    mode,
    boq_category,
    file_digest,
    summary,
    user_id,
    company_id,
) -> str:
    """确认令牌：绑定版本/模式/类别/文件摘要/影响摘要/操作主体。

    execute 阶段以同参数重算并逐位比对；任何漂移（文件被换、版本行被并发
    修改、主体被换）都导致 CONFIRM_TOKEN_MISMATCH 拒绝执行。
    """
    payload = {
        "salt": CONFIRM_TOKEN_SALT,
        "version_id": int(version_id or 0),
        "mode": str(mode or ""),
        "boq_category": str(boq_category or ""),
        "file_digest": str(file_digest or ""),
        "summary": summary,
        "user_id": int(user_id or 0),
        "company_id": int(company_id or 0),
    }
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def confirm_token_matches(expected, actual) -> bool:
    return str(expected or "") == str(actual or "") and bool(str(actual or "").strip())


def build_audit_payload(
    *,
    mode,
    version_id,
    project_id,
    file_digest,
    idempotency_key,
    idempotency_fingerprint,
    trace_id,
    summary_before,
    summary_after,
    result,
    duration_ms,
):
    """sc.audit.log 事件载荷（before/after 摘要 + 幂等键 + 变更统计）。"""
    return {
        "mode": mode,
        "version_id": int(version_id or 0),
        "project_id": int(project_id or 0),
        "file_digest": str(file_digest or ""),
        "idempotency_key": str(idempotency_key or ""),
        "idempotency_fingerprint": str(idempotency_fingerprint or ""),
        "trace_id": str(trace_id or ""),
        "duration_ms": int(duration_ms or 0),
        "before": summary_before or {},
        "after": summary_after or {},
        "result_summary": {
            "success": bool((result or {}).get("success")),
            "lines_deleted": int((result or {}).get("lines_deleted") or 0),
            "lines_updated": int((result or {}).get("lines_updated") or 0),
            "lines_created": int((result or {}).get("lines_created") or 0),
        },
    }
