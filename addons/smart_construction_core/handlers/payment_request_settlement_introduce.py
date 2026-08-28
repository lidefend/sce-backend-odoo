# -*- coding: utf-8 -*-
from __future__ import annotations

import time
from uuid import uuid4

from odoo.addons.smart_core.core.base_handler import BaseIntentHandler

_EDITABLE_STATES = ("draft", "rejected", "cancel")


def _pay_amount_currency(value):
    return round(float(value or 0.0), 2)


def _settlement_line_applied(env, settlement_line):
    """结算行已申请金额 = 关联付款申请明细 current_pay_amount 汇总（实时计算，动态一致）。"""
    lines = env["payment.request.line"].search(
        [
            ("settlement_line_id", "=", settlement_line.id),
            ("active", "=", True),
        ]
    )
    return _pay_amount_currency(sum(lines.mapped("current_pay_amount")))


def _settlement_related_payment_requests(env, settlement):
    """聚合结算单关联的付款申请（主表关联 + 明细关联），用于资金执行追溯展示。"""
    state_selection = dict(env["payment.request"]._fields["state"].selection)
    result = []
    seen = set()

    requests = settlement.payment_request_ids | settlement.payment_request_line_ids.mapped("request_id")
    for req in requests.sorted(key=lambda r: (r.date_request or r.create_date or r.id, r.id), reverse=True):
        if not req or req.id in seen:
            continue
        seen.add(req.id)
        applied = _pay_amount_currency(sum(req.outflow_line_ids.filtered(lambda l: l.settlement_id.id == settlement.id).mapped("current_pay_amount")))
        result.append(
            {
                "id": req.id,
                "name": req.name,
                "state": req.state,
                "state_label": state_selection.get(req.state, req.state or ""),
                "amount": _pay_amount_currency(req.amount),
                "applied_to_settlement": applied,
                "date_request": req.date_request.isoformat() if req.date_request else None,
            }
        )
    return result


class PaymentRequestSettlementSearchHandler(BaseIntentHandler):
    """按关键词搜索结算单，供明细引入弹窗选择来源。"""

    INTENT_TYPE = "payment.request.settlement.search"
    DESCRIPTION = "按关键词搜索结算单（引入明细时选择来源）"
    VERSION = "1.0.0"
    ETAG_ENABLED = False
    REQUIRED_GROUPS = ["base.group_user"]

    def handle(self, payload=None, ctx=None):
        ts0 = time.time()
        params = payload or self.params or {}
        if isinstance(params, dict) and isinstance(params.get("params"), dict):
            params = params.get("params") or {}
        keyword = str(params.get("keyword") or "").strip()
        try:
            limit = min(max(int(params.get("limit") or 20), 1), 50)
        except (TypeError, ValueError):
            limit = 20
        try:
            payment_request_id = int(params.get("payment_request_id") or 0)
        except (TypeError, ValueError):
            payment_request_id = 0

        domain = [("active", "=", True)]
        # 按付款申请项目+合同过滤：仅显示同项目同合同（或未绑定）的结算单，避免引入时校验失败
        if payment_request_id > 0:
            request = self.env["payment.request"].browse(payment_request_id)
            if request.exists() and request.project_id:
                domain = [
                    ("active", "=", True),
                    "|",
                    ("project_id", "=", request.project_id.id),
                    ("project_id", "=", False),
                ]
                if request.contract_id:
                    domain = [
                        ("active", "=", True),
                        "|",
                        ("project_id", "=", request.project_id.id),
                        ("project_id", "=", False),
                        "|",
                        ("contract_id", "=", request.contract_id.id),
                        ("contract_id", "=", False),
                    ]
        if keyword:
            domain = ["|", ("name", "ilike", keyword), ("display_name", "ilike", keyword)] + domain
        settlements = self.env["sc.settlement.order"].search(domain, limit=limit, order="id desc")
        items = []
        for s in settlements:
            items.append(
                {
                    "id": s.id,
                    "name": s.name,
                    "display_name": s.display_name,
                    "amount_total": _pay_amount_currency(s.amount_total),
                    "contract_id": s.contract_id.id,
                    "contract_name": s.contract_id.display_name or "",
                    "partner_name": s.partner_id.display_name or "",
                    "line_count": len(s.line_ids),
                }
            )
        return {
            "ok": True,
            "data": {"settlements": items, "count": len(items)},
            "meta": {
                "intent": self.INTENT_TYPE,
                "elapsed_ms": int((time.time() - ts0) * 1000),
                "trace_id": str((self.context or {}).get("trace_id") or ""),
            },
        }


class PaymentRequestSettlementPreviewHandler(BaseIntentHandler):
    """结算单 → 结算行预览：返回每行金额、已申请、剩余可申请，支持同一结算多次支付。"""

    INTENT_TYPE = "payment.request.settlement.preview"
    DESCRIPTION = "预览结算单明细行及其已申请/剩余可申请金额"
    VERSION = "1.0.0"
    ETAG_ENABLED = False
    REQUIRED_GROUPS = ["base.group_user"]
    ACCESS_GROUPS = [
        "smart_construction_core.group_sc_cap_finance_user",
        "smart_construction_core.group_sc_cap_finance_manager",
        "smart_core.group_smart_core_finance_approver",
        "smart_construction_core.group_sc_role_executive",
    ]

    def _assert_access(self):
        from odoo.addons.smart_core.security.platform_admin import user_is_platform_admin

        if user_is_platform_admin(self.env.user):
            return
        for xmlid in self.ACCESS_GROUPS:
            try:
                if self.env.user.has_group(xmlid):
                    return
            except Exception:
                continue
        from odoo.exceptions import AccessError

        raise AccessError("PERMISSION_DENIED: missing required group")

    def handle(self, payload=None, ctx=None):
        ts0 = time.time()
        params = payload or self.params or {}
        if isinstance(params, dict) and isinstance(params.get("params"), dict):
            params = params.get("params") or {}

        def _err(code, message, action="fix_input"):
            return {
                "ok": False,
                "error": {"code": code, "message": message, "suggested_action": action},
                "meta": {
                    "intent": self.INTENT_TYPE,
                    "elapsed_ms": int((time.time() - ts0) * 1000),
                    "trace_id": str((self.context or {}).get("trace_id") or ""),
                },
            }

        try:
            self._assert_access()
        except Exception:
            return _err("PERMISSION_DENIED", "当前账号无权限访问结算明细", "contact_admin")

        try:
            settlement_id = int(params.get("settlement_id") or 0)
        except (TypeError, ValueError):
            settlement_id = 0
        if settlement_id <= 0:
            return _err("MISSING_PARAMS", "缺少参数：settlement_id")

        settlement = self.env["sc.settlement.order"].browse(settlement_id)
        if not settlement.exists():
            return _err("SETTLEMENT_NOT_FOUND", "结算单不存在")

        lines = []
        applied_total = 0.0
        remaining_total = 0.0
        for line in settlement.line_ids.sorted(key=lambda l: l.id):
            amount = _pay_amount_currency(line.amount)
            applied = _settlement_line_applied(self.env, line)
            remaining = round(amount - applied, 2)
            applied_total += applied
            remaining_total += remaining
            lines.append(
                {
                    "id": line.id,
                    "name": line.name,
                    "contract_id": line.contract_id.id,
                    "contract_name": line.contract_id.display_name or "",
                    "qty": float(line.qty or 0.0),
                    "price_unit": _pay_amount_currency(line.price_unit),
                    "amount": amount,
                    "applied": applied,
                    "remaining": remaining,
                    "is_fully_applied": remaining <= 0.0001,
                }
            )

        data = {
            "settlement": {
                "id": settlement.id,
                "name": settlement.name,
                "display_name": settlement.display_name,
                "contract_id": settlement.contract_id.id,
                "contract_name": settlement.contract_id.display_name or "",
                "partner_id": settlement.partner_id.id,
                "partner_name": settlement.partner_id.display_name or "",
                "amount_total": _pay_amount_currency(settlement.amount_total),
            },
            "lines": lines,
            "related_payment_requests": _settlement_related_payment_requests(self.env, settlement),
            "totals": {
                "settlement_amount": _pay_amount_currency(settlement.amount_total),
                "line_amount_total": round(applied_total + remaining_total, 2),
                "applied_total": round(applied_total, 2),
                "remaining_total": round(remaining_total, 2),
            },
        }
        return {
            "ok": True,
            "data": data,
            "meta": {
                "intent": self.INTENT_TYPE,
                "elapsed_ms": int((time.time() - ts0) * 1000),
                "trace_id": str((self.context or {}).get("trace_id") or ""),
            },
        }


class PaymentRequestAddSettlementLinesHandler(BaseIntentHandler):
    """从结算单引入付款申请明细：支持快速全引/勾选/按比例/按总金额，强制关联结算单与结算行。"""

    INTENT_TYPE = "payment.request.add.settlement.lines"
    DESCRIPTION = "从结算单引入明细行到付款申请（快速/勾选/比例/总金额），强制关联并校验剩余"
    VERSION = "1.0.0"
    ETAG_ENABLED = False
    REQUIRED_GROUPS = ["base.group_user"]
    ACCESS_GROUPS = [
        "smart_construction_core.group_sc_cap_finance_user",
        "smart_construction_core.group_sc_cap_finance_manager",
        "smart_core.group_smart_core_finance_approver",
        "smart_construction_core.group_sc_role_executive",
    ]

    def _assert_access(self):
        from odoo.addons.smart_core.security.platform_admin import user_is_platform_admin

        if user_is_platform_admin(self.env.user):
            return
        for xmlid in self.ACCESS_GROUPS:
            try:
                if self.env.user.has_group(xmlid):
                    return
            except Exception:
                continue
        from odoo.exceptions import AccessError

        raise AccessError("PERMISSION_DENIED: missing required group")

    def handle(self, payload=None, ctx=None):
        ts0 = time.time()
        params = payload or self.params or {}
        if isinstance(params, dict) and isinstance(params.get("params"), dict):
            params = params.get("params") or {}

        def _err(code, message, action="fix_input"):
            return {
                "ok": False,
                "error": {"code": code, "message": message, "suggested_action": action},
                "meta": {
                    "intent": self.INTENT_TYPE,
                    "elapsed_ms": int((time.time() - ts0) * 1000),
                    "trace_id": str((self.context or {}).get("trace_id") or ""),
                },
            }

        try:
            self._assert_access()
        except Exception:
            return _err("PERMISSION_DENIED", "当前账号无权限引入结算明细", "contact_admin")

        try:
            payment_request_id = int(params.get("payment_request_id") or 0)
        except (TypeError, ValueError):
            payment_request_id = 0
        try:
            settlement_id = int(params.get("settlement_id") or 0)
        except (TypeError, ValueError):
            settlement_id = 0
        if payment_request_id <= 0:
            return _err("MISSING_PARAMS", "缺少参数：payment_request_id")
        if settlement_id <= 0:
            return _err("MISSING_PARAMS", "缺少参数：settlement_id")

        request = self.env["payment.request"].browse(payment_request_id)
        if not request.exists():
            return _err("PAYMENT_REQUEST_NOT_FOUND", "付款申请不存在")
        if request.state not in _EDITABLE_STATES:
            return _err(
                "REQUEST_NOT_EDITABLE",
                "付款申请当前状态不允许修改明细（仅草稿/驳回/取消可编辑）",
                "change_state",
            )

        settlement = self.env["sc.settlement.order"].browse(settlement_id)
        if not settlement.exists():
            return _err("SETTLEMENT_NOT_FOUND", "结算单不存在")

        # 项目一致性校验：结算单项目与付款申请项目必须一致（或结算单未绑定项目）
        if (
            request.project_id
            and settlement.project_id
            and request.project_id.id != settlement.project_id.id
        ):
            return _err(
                "PROJECT_MISMATCH",
                "结算单「%s」所属项目与付款申请项目不一致，无法引入（请在付款申请同项目的结算单中选择）"
                % settlement.name,
                "fix_input",
            )

        # 合同一致性校验：结算单头合同与付款申请合同必须一致（或结算单未绑定合同）
        if (
            request.contract_id
            and settlement.contract_id
            and request.contract_id.id != settlement.contract_id.id
        ):
            return _err(
                "CONTRACT_MISMATCH",
                "结算单「%s」合同与付款申请合同不一致，无法引入（请在付款申请同合同的结算单中选择）"
                % settlement.name,
                "fix_input",
            )

        # ---- 解析选中结算行 ----
        raw_ids = params.get("settlement_line_ids") or []
        if isinstance(raw_ids, str):
            raw_ids = [x for x in raw_ids.split(",") if x.strip()]
        selected_ids = set()
        for x in raw_ids:
            try:
                selected_ids.add(int(x))
            except (TypeError, ValueError):
                continue
        if not selected_ids:
            return _err("MISSING_PARAMS", "缺少参数：settlement_line_ids（未选择结算行）")

        settlement_lines = settlement.line_ids.filtered(lambda l: l.id in selected_ids)
        if not settlement_lines:
            return _err("SETTLEMENT_LINE_NOT_FOUND", "所选结算行不存在")

        # ---- 解析分配模式 ----
        apply_mode = str(params.get("apply_mode") or "ratio").strip().lower()
        if apply_mode not in ("ratio", "amount", "lines"):
            return _err("INVALID_MODE", "apply_mode 仅支持 ratio / amount / lines")

        # ---- 每行可申请金额 ----
        items = []
        for line in settlement_lines:
            amount = _pay_amount_currency(line.amount)
            applied = _settlement_line_applied(self.env, line)
            remaining = round(amount - applied, 2)
            items.append(
                {
                    "line": line,
                    "amount": amount,
                    "applied": applied,
                    "remaining": remaining,
                    "apply": 0.0,
                }
            )

        # ---- 按模式计算每行申请金额 ----
        if apply_mode == "ratio":
            try:
                ratio = float(params.get("ratio") or 100.0)
            except (TypeError, ValueError):
                ratio = 100.0
            ratio = min(max(ratio, 0.0), 100.0)
            for item in items:
                item["apply"] = round(item["remaining"] * ratio / 100.0, 2)
        elif apply_mode == "amount":
            try:
                total_amount = float(params.get("total_amount") or 0.0)
            except (TypeError, ValueError):
                total_amount = 0.0
            total_amount = max(total_amount, 0.0)
            total_remaining = sum(item["remaining"] for item in items)
            if total_amount <= 0.0 or total_remaining <= 0.0:
                return _err("INVALID_AMOUNT", "总申请金额必须大于 0 且结算行存在剩余可申请金额")
            if total_amount > total_remaining + 0.0001:
                return _err(
                    "AMOUNT_EXCEEDS_REMAINING",
                    "总申请金额超过可申请余额（剩余可申请 %s）" % round(total_remaining, 2),
                )
            acc = 0.0
            for idx, item in enumerate(items):
                if idx == len(items) - 1:
                    item["apply"] = round(total_amount - acc, 2)
                else:
                    item["apply"] = round(total_amount * item["remaining"] / total_remaining, 2)
                acc += item["apply"]
        else:  # lines（显式指定每行金额）
            explicit = {}
            raw_lines = params.get("lines") or []
            if isinstance(raw_lines, dict):
                raw_lines = raw_lines.get("lines") or []
            for entry in raw_lines:
                if not isinstance(entry, dict):
                    continue
                try:
                    lid = int(entry.get("settlement_line_id") or entry.get("id") or 0)
                except (TypeError, ValueError):
                    continue
                try:
                    explicit[lid] = float(entry.get("amount") or entry.get("current_pay_amount") or 0.0)
                except (TypeError, ValueError):
                    explicit[lid] = 0.0
            for item in items:
                item["apply"] = round(explicit.get(item["line"].id, 0.0), 2)

        # ---- 校验 + 创建 ----
        created = []
        for item in items:
            if item["apply"] <= 0.0:
                continue
            if item["apply"] > item["remaining"] + 0.0001:
                return _err(
                    "AMOUNT_EXCEEDS_REMAINING",
                    "结算行「%s」申请金额超过剩余可申请（剩余 %s）"
                    % (item["line"].name, round(item["remaining"], 2)),
                    "fix_input",
                )
            line_vals = {
                "request_id": request.id,
                "settlement_id": settlement.id,
                "settlement_line_id": item["line"].id,
                "contract_id": item["line"].contract_id.id or settlement.contract_id.id or False,
                "source_document_no": settlement.name,
                "source_line_type": "结算单明细",
                "source_contract_no": (item["line"].contract_id.name or settlement.contract_id.name or ""),
                "amount": item["amount"],
                "paid_before_amount": item["applied"],
                "remaining_amount": item["remaining"],
                "current_pay_amount": item["apply"],
                "legacy_line_id": "settle_intro_%s_%s" % (item["line"].id, uuid4().hex[:8]),
                "legacy_parent_id": "settle_intro_%s" % settlement.id,
            }
            new_line = self.env["payment.request.line"].create(line_vals)
            created.append(
                {
                    "id": new_line.id,
                    "settlement_line_id": item["line"].id,
                    "name": item["line"].name,
                    "contract_id": new_line.contract_id.id,
                    "contract_name": new_line.contract_id.display_name or "",
                    "amount": item["amount"],
                    "paid_before_amount": item["applied"],
                    "remaining_amount": item["remaining"],
                    "current_pay_amount": item["apply"],
                    "source_document_no": settlement.name,
                }
            )

        total_applied = round(sum(x["current_pay_amount"] for x in created), 2)
        return {
            "ok": True,
            "data": {
                "created": created,
                "created_count": len(created),
                "settlement_id": settlement.id,
                "settlement_name": settlement.name,
                "total_applied": total_applied,
            },
            "meta": {
                "intent": self.INTENT_TYPE,
                "elapsed_ms": int((time.time() - ts0) * 1000),
                "trace_id": str((self.context or {}).get("trace_id") or ""),
            },
        }
