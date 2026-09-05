# -*- coding: utf-8 -*-
"""BOQ 行内联编辑（工程量 patch）handler（G7.2，G7_LAUNCH_SCOPING §4 切片 3）。

数据契约：contracts/domain/boq-line-patch.yaml v1。
单阶段协议（区别于危险导入的两阶段确认——单行单字段常规写，expected
基线已承担并发防护，无需 preview 干跑）：
- project.boq.line.patch：expected_quantity 基线比对（并发漂移防护）→
  claim/complete 幂等（G7-INFRA 定式，claim 前置于基线比对——响应丢失后
  的原样重试命中 replay 分支直接返回首次结果，基线比对仅对首次执行生效，
  与 G7.1 层序修正同源）→ savepoint 内 write(quantity) → 服务端 compute
  链权威重算（amount/amount_leaf/qty_remain/version.total_amount）→
  sc.audit.log before/after。

安全边界：
- 复用既有组 cost_user / cost_manager（boq.line ACL 已读写改/全权；
  单行常规写不新造组——G7.2-A 审计 §11.1）；
- 无 kill switch：回退面 = 版本状态闸（published/superseded 即锁，
  ORM write 守卫兜底）+ ACL + intent 不注册即不可达；
- 仅 draft/validated 版本可写；冻结项目拒绝（P0_BOQ_FROZEN 同源）；
- 写入口径仅 quantity 单字段（price/imported_amount 维持导入通道）。
"""
from __future__ import annotations

import time
from uuid import uuid4

from odoo import fields
from odoo.addons.smart_core.core.base_handler import BaseIntentHandler
from odoo.addons.smart_core.utils.idempotency import (
    apply_idempotency_identity,
    build_idempotency_conflict_response,
    build_idempotency_fingerprint,
    build_idempotency_in_flight_response,
    claim_write_idempotency,
    complete_write_idempotency,
    enrich_replay_contract,
    normalize_request_id,
    record_entry_as_replay_evidence,
    replay_window_seconds,
)

from odoo.addons.smart_construction_core.services import boq_line_patch_service as svc


def _unwrap_params(payload, fallback):
    """intent 信封解包：router 传给 handle 的是 {intent, params, ...} 信封。"""
    params = payload or fallback or {}
    if isinstance(params, dict) and isinstance(params.get("params"), dict):
        params = params.get("params") or {}
    return params


def _to_int(value):
    try:
        return int(str(value or "0").strip() or 0)
    except (TypeError, ValueError):
        return 0


class BoqLinePatchHandler(BaseIntentHandler):
    INTENT_TYPE = "project.boq.line.patch"
    DESCRIPTION = "BOQ 行内联编辑（工程量 patch，服务端权威重算）"
    MACHINE_ACCESS = "write"
    VERSION = "1.0.0"
    ETAG_ENABLED = False
    REQUIRED_GROUPS = [
        "smart_construction_core.group_sc_cap_cost_user",
        "smart_construction_core.group_sc_cap_cost_manager",
    ]
    ACL_MODE = "record_rule"
    IDEMPOTENCY_WINDOW_SECONDS = 3600

    SOURCE_AUTHORITY = {
        "kind": "boq_line_patch_write",
        "authorities": [
            "project.boq.version",
            "project.boq.line",
            "sc.idempotency.record",
            "sc.audit.log",
            "ir.model.access",
            "ir.rule",
            "odoo.orm",
        ],
        "projection_only": False,
        "write_authority": "project.boq.line",
        "idempotency_authority": "sc.idempotency.record + sc.audit.log",
        "editable_fields": [svc.EDITABLE_FIELD],
    }

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

    def _idempotency_window_seconds(self):
        return replay_window_seconds(
            self.IDEMPOTENCY_WINDOW_SECONDS,
            env_key="SC_BOQ_LINE_PATCH_REPLAY_WINDOW_SEC",
        )

    def _fingerprint(self, *, line_id, expected_quantity, new_quantity, idem_key):
        payload = {
            "intent": self.INTENT_TYPE,
            "db": self.env.cr.dbname,
            "user_id": int(self.env.user.id or 0),
            "company_id": (
                int(self.env.user.company_id.id or 0)
                if self.env.user and self.env.user.company_id
                else 0
            ),
            "line_id": int(line_id or 0),
            "expected_quantity": round(float(expected_quantity), svc.QTY_COMPARE_DIGITS),
            "new_quantity": round(float(new_quantity), svc.QTY_COMPARE_DIGITS),
            "idempotency_key": idem_key,
        }
        return build_idempotency_fingerprint(payload)

    def handle(self, payload=None, ctx=None):
        ts0 = time.time()
        env = self.env
        params = _unwrap_params(payload, self.params)
        request_id = normalize_request_id(params.get("request_id"), prefix="boqlp_req")
        idem_key = str(params.get("idempotency_key") or "").strip() or request_id
        trace_id = f"boq_lp_{uuid4().hex[:12]}"

        line_id = _to_int(params.get("line_id"))
        expected_quantity = svc.normalize_quantity(params.get("expected_quantity"))
        new_quantity = svc.normalize_quantity(params.get("new_quantity"))

        # ---- 参数与语义校验（claim 之前：无业务写，不占幂等行）----
        if line_id <= 0 or expected_quantity is None or new_quantity is None:
            return self._error(
                "MISSING_PARAMS",
                "缺少或非法参数：line_id / expected_quantity / new_quantity 必填且为合法数值",
                "fix_input",
                ts0,
            )
        if new_quantity < 0:
            return self._error(
                "INVALID_QUANTITY",
                "新工程量不能为负数",
                "fix_input",
                ts0,
            )

        # ---- 行加载（search 语义：无权限与不存在同响应）----
        line = env["project.boq.line"].search([("id", "=", line_id)], limit=1)
        if not line:
            return self._error(
                "LINE_NOT_FOUND",
                "未找到可访问的清单行",
                "check_params",
                ts0,
            )
        version = line.version_id
        if not version or version.state not in svc.MUTABLE_VERSION_STATES:
            return self._error(
                "VERSION_NOT_MUTABLE",
                "仅草稿/已校验版本允许内联编辑（当前状态：%s）"
                % ((version.state if version else "") or ""),
                "create_new_version",
                ts0,
            )
        project = line.project_id
        if project and project.is_boq_frozen():
            return self._error(
                "BOQ_FROZEN",
                "项目[%s]已进入结算/支付关键节点，清单编辑被冻结"
                % (project.display_name or ""),
                "check_project_state",
                ts0,
            )

        # ---- 幂等前置（G7-INFRA claim 定式，先于基线比对）----
        # 指纹绑定「客户端提供的 expected/new + 行 id」：响应丢失后的原样
        # 重试（同键同指纹）命中 replay 分支，直接返回首次结果；基线比对
        # 仅对首次执行生效——首次执行后 DB 已变，基线必然漂移，这正是并发
        # 防护语义，与重放通道互不冲突（G7.1 层序修正同源）。
        fingerprint = self._fingerprint(
            line_id=line.id,
            expected_quantity=expected_quantity,
            new_quantity=new_quantity,
            idem_key=idem_key,
        )
        claim = claim_write_idempotency(
            env,
            event_code=svc.EVENT_CODE,
            idempotency_key=idem_key,
            fingerprint=fingerprint,
            trace_id=trace_id,
            window_seconds=self._idempotency_window_seconds(),
            model="project.boq.line",
            res_id=line.id,
        )

        def _release_failed(error_msg):
            """claim 后的降级路径统一释放幂等行（failed 允许接管重试）。"""
            try:
                complete_write_idempotency(
                    env,
                    event_code=svc.EVENT_CODE,
                    idempotency_key=idem_key,
                    fingerprint=fingerprint,
                    result={"error": error_msg, "trace_id": trace_id},
                    trace_id=trace_id,
                    status="failed",
                    model="project.boq.line",
                    res_id=line.id,
                )
            except Exception:
                pass

        if claim.get("mode") == "conflict":
            payload_resp = build_idempotency_conflict_response(
                intent_type=self.INTENT_TYPE,
                request_id=request_id,
                idempotency_key=idem_key,
                trace_id=trace_id,
                include_replay_evidence=True,
            )
            payload_resp.setdefault("meta", {})["source_authority"] = self.SOURCE_AUTHORITY
            return payload_resp
        if claim.get("mode") == "in_flight":
            payload_resp = build_idempotency_in_flight_response(
                intent_type=self.INTENT_TYPE,
                request_id=request_id,
                idempotency_key=idem_key,
                trace_id=trace_id,
            )
            payload_resp.setdefault("meta", {})["source_authority"] = self.SOURCE_AUTHORITY
            return payload_resp
        replay = claim.get("replay_payload") or {}
        replay_entry = claim.get("replay_entry") or {}
        if replay:
            replay_data = apply_idempotency_identity(
                dict(replay or {}),
                request_id=request_id,
                idempotency_key=idem_key,
                idempotency_fingerprint=fingerprint,
                trace_id=trace_id,
            )
            replay_data = enrich_replay_contract(
                replay_data,
                idempotent_replay=True,
                replay_window_expired=False,
                replay_reason_code="",
                replay_entry=record_entry_as_replay_evidence(replay_entry) or replay_entry,
                include_replay_evidence=True,
            )
            return {
                "ok": True,
                "data": replay_data,
                "meta": {"intent": self.INTENT_TYPE, "source_authority": self.SOURCE_AUTHORITY},
            }

        # ---- expected 基线比对（claim 之后：漂移路径释放幂等行为 failed）----
        if not svc.quantity_baseline_matches(expected_quantity, line.quantity):
            _release_failed("baseline mismatch")
            return self._error(
                "BASELINE_MISMATCH",
                "工程量基线不一致：该行已被并发修改（expected=%s，实际=%s），请刷新后重试"
                % (round(expected_quantity, svc.QTY_COMPARE_DIGITS),
                   round(float(line.quantity or 0.0), svc.QTY_COMPARE_DIGITS)),
                "reload_and_retry",
                ts0,
            )
        qty_done = float(line.qty_done or 0.0)
        if svc.qty_below_done(new_quantity, qty_done):
            _release_failed("qty below done")
            return self._error(
                "QTY_BELOW_DONE",
                "新工程量（%.6g）不能低于累计完成量（%.6g）"
                % (new_quantity, qty_done),
                "fix_input",
                ts0,
            )

        # ---- 执行（savepoint 原子包裹；compute 链由 ORM 权威重算）----
        quantity_before = float(line.quantity or 0.0)
        amount_before = float(line.amount or 0.0)
        try:
            with env.cr.savepoint():
                line.write({"quantity": new_quantity})
        except Exception as exc:
            complete_write_idempotency(
                env,
                event_code=svc.EVENT_CODE,
                idempotency_key=idem_key,
                fingerprint=fingerprint,
                result={"error": str(exc), "trace_id": trace_id},
                trace_id=trace_id,
                status="failed",
                model="project.boq.line",
                res_id=line.id,
            )
            return self._error(
                "PATCH_ERROR",
                "工程量更新失败（已整体回滚）：%s" % exc,
                "retry",
                ts0,
            )

        # ---- after 投影（DB/ORM 重读为权威，不信执行侧计数）----
        quantity_after = float(line.quantity or 0.0)
        amount_after = float(line.amount or 0.0)
        qty_remain = float(line.qty_remain or 0.0)
        version_total = float(version.total_amount or 0.0)
        duration_ms = int((time.time() - ts0) * 1000)

        data = apply_idempotency_identity(
            {
                "schema": svc.PATCH_SCHEMA,
                "field": svc.EDITABLE_FIELD,
                "line_id": line.id,
                "version_id": version.id,
                "version_state": version.state,
                "project_id": project.id if project else 0,
                "quantity_before": quantity_before,
                "quantity_after": quantity_after,
                "amount_before": round(amount_before, 2),
                "amount_after": round(amount_after, 2),
                "qty_remain": qty_remain,
                "version_total_amount": round(version_total, 2),
                "success": True,
                "reason_code": "DONE",
                "message": "工程量已更新（服务端权威重算）",
                "done_at": fields.Datetime.to_string(fields.Datetime.now()),
            },
            request_id=request_id,
            idempotency_key=idem_key,
            idempotency_fingerprint=fingerprint,
            trace_id=trace_id,
        )
        data = enrich_replay_contract(
            data,
            idempotent_replay=False,
            replay_window_expired=False,
            replay_reason_code="",
            include_replay_evidence=False,
        )
        complete_write_idempotency(
            env,
            event_code=svc.EVENT_CODE,
            idempotency_key=idem_key,
            fingerprint=fingerprint,
            result=data,
            trace_id=trace_id,
            model="project.boq.line",
            res_id=line.id,
        )

        Audit = env.get("sc.audit.log")
        if Audit is not None:
            try:
                Audit.write_event(
                    event_code=svc.EVENT_CODE,
                    model="project.boq.line",
                    res_id=line.id,
                    action="patch_quantity",
                    before=svc.build_audit_payload(
                        line_id=line.id,
                        version_id=version.id,
                        project_id=(project.id if project else 0),
                        quantity_before=quantity_before,
                        quantity_after=quantity_before,
                        qty_done=qty_done,
                        amount_before=amount_before,
                        amount_after=amount_before,
                        idempotency_key=idem_key,
                        idempotency_fingerprint=fingerprint,
                        trace_id=trace_id,
                        duration_ms=duration_ms,
                        result={},
                    ),
                    after=svc.build_audit_payload(
                        line_id=line.id,
                        version_id=version.id,
                        project_id=(project.id if project else 0),
                        quantity_before=quantity_before,
                        quantity_after=quantity_after,
                        qty_done=qty_done,
                        amount_before=amount_before,
                        amount_after=amount_after,
                        idempotency_key=idem_key,
                        idempotency_fingerprint=fingerprint,
                        trace_id=trace_id,
                        duration_ms=duration_ms,
                        result=data,
                    ),
                    reason="boq line inline patch (quantity)",
                    trace_id=trace_id,
                    project_id=(project.id if project else None),
                    company_id=(
                        env.user.company_id.id if env.user.company_id else None
                    ),
                )
            except Exception:
                pass

        return {
            "ok": True,
            "data": data,
            "meta": {"intent": self.INTENT_TYPE, "source_authority": self.SOURCE_AUTHORITY},
        }
