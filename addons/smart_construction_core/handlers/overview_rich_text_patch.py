# -*- coding: utf-8 -*-
"""项目概况受限富文本 patch handler（G7.4，ADR-006 批准后首切片）。

数据契约：contracts/domain/overview-rich-text-patch.yaml v1。
单阶段协议（与 G7.2 同型——单记录单字段常规写）：
- project.overview.rich_text.patch：kill switch gate（默认关，fail-closed）→
  参数/长度校验（claim 之前，纯输入错误不占幂等行）→ nh3
  sanitize-on-save（净化失败 fail-closed 不落库）→ claim/complete 幂等
  （G7-INFRA 定式，指纹绑定客户端摘要基线 + 新内容摘要——响应丢失后
  的原样重试命中 replay 分支）→ expected 摘要基线比对（仅对首次执行
  生效，与重放通道互不冲突）→ savepoint 内 write(overview_html) →
  sc.audit.log before/after（摘要 + 长度，不落全文）。

安全边界（ADR-006 决策 7 / G7.1 kill switch 模式）：
- 专用组 group_sc_cap_rich_text_editor（不并入既有业务组）；
- kill switch ir.config_parameter sc.rich_text_editor.enabled 默认关闭
  （noupdate 数据文件，运维显式开启；关闭时结构化 CAPABILITY_DISABLED）；
- intent 中间件对 is_write() 先组检查后 flag gate（无组+开关关 →
  PERMISSION_DENIED 而非 CAPABILITY_DISABLED，与 G7.1 同口径）；
- 回退面 = kill switch + ACL + intent 不注册即不可达 + 净化 fail-closed。
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

from odoo.addons.smart_construction_core.services import overview_rich_text_patch_service as svc


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


def _flag_on(env):
    Parameters = env.get("ir.config_parameter")
    if Parameters is None:
        return False
    try:
        raw = Parameters.sudo().get_param(svc.FLAG_KEY)
    except Exception:
        return False
    return svc.flag_enabled(raw)


class OverviewRichTextPatchHandler(BaseIntentHandler):
    INTENT_TYPE = "project.overview.rich_text.patch"
    DESCRIPTION = "项目概况受限富文本 patch（nh3 sanitize-on-save，服务端净化权威）"
    MACHINE_ACCESS = "write"
    VERSION = "1.0.0"
    ETAG_ENABLED = False
    REQUIRED_GROUPS = [
        "smart_construction_core.group_sc_cap_rich_text_editor",
    ]
    ACL_MODE = "record_rule"
    IDEMPOTENCY_WINDOW_SECONDS = 3600

    SOURCE_AUTHORITY = {
        "kind": "overview_rich_text_patch_write",
        "authorities": [
            "project.project",
            "sc.idempotency.record",
            "sc.audit.log",
            "ir.config_parameter",
            "ir.model.access",
            "ir.rule",
            "odoo.orm",
        ],
        "projection_only": False,
        "write_authority": "project.project.overview_html",
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
            env_key="SC_OVERVIEW_RICH_TEXT_PATCH_REPLAY_WINDOW_SEC",
        )

    def _fingerprint(self, *, project_id, expected_digest, new_digest, idem_key):
        payload = {
            "intent": self.INTENT_TYPE,
            "db": self.env.cr.dbname,
            "user_id": int(self.env.user.id or 0),
            "company_id": (
                int(self.env.user.company_id.id or 0)
                if self.env.user and self.env.user.company_id
                else 0
            ),
            "project_id": int(project_id or 0),
            "expected_overview_digest": str(expected_digest or ""),
            "new_overview_digest": str(new_digest or ""),
            "idempotency_key": idem_key,
        }
        return build_idempotency_fingerprint(payload)

    def handle(self, payload=None, ctx=None):
        ts0 = time.time()
        env = self.env
        params = _unwrap_params(payload, self.params)
        request_id = normalize_request_id(params.get("request_id"), prefix="ovrt_req")
        idem_key = str(params.get("idempotency_key") or "").strip() or request_id
        trace_id = f"ovrt_{uuid4().hex[:12]}"

        project_id = _to_int(params.get("project_id"))
        expected_digest = str(params.get("expected_overview_digest") or "").strip()
        raw_content = params.get("new_overview_html")
        raw_content = "" if raw_content is None else str(raw_content)

        # ---- kill switch gate（G7.1 模式：fail-closed，先于业务加载）----
        if not _flag_on(env):
            return self._error(
                "CAPABILITY_DISABLED",
                "受限富文本编辑能力未开启（sc.rich_text_editor.enabled）",
                "enable_feature_flag",
                ts0,
            )

        # ---- 参数与长度校验（claim 之前：纯输入错误不占幂等行）----
        if project_id <= 0 or not expected_digest or params.get("new_overview_html") is None:
            return self._error(
                "MISSING_PARAMS",
                "缺少或非法参数：project_id / expected_overview_digest / new_overview_html 必填",
                "fix_input",
                ts0,
            )
        if svc.content_over_limit(raw_content):
            return self._error(
                "CONTENT_TOO_LONG",
                "内容超出长度上限（%d 字符，净化前判定）" % svc.MAX_LENGTH,
                "fix_input",
                ts0,
            )

        # ---- sanitize-on-save（净化失败 fail-closed，claim 之前）----
        try:
            sanitized = svc.sanitize_overview_html(raw_content)
        except RuntimeError as exc:
            return self._error(
                "CAPABILITY_DISABLED",
                "服务端净化器不可用，写入通道关闭：%s" % exc,
                "contact_admin",
                ts0,
            )
        new_digest = svc.overview_digest(sanitized)

        # ---- 项目加载（search 语义：无权限与不存在同响应）----
        project = env["project.project"].search([("id", "=", project_id)], limit=1)
        if not project:
            return self._error(
                "PROJECT_NOT_FOUND",
                "未找到可访问的项目",
                "check_params",
                ts0,
            )

        # ---- 幂等前置（G7-INFRA claim 定式，先于基线比对）----
        fingerprint = self._fingerprint(
            project_id=project.id,
            expected_digest=expected_digest,
            new_digest=new_digest,
            idem_key=idem_key,
        )
        claim = claim_write_idempotency(
            env,
            event_code=svc.EVENT_CODE,
            idempotency_key=idem_key,
            fingerprint=fingerprint,
            trace_id=trace_id,
            window_seconds=self._idempotency_window_seconds(),
            model="project.project",
            res_id=project.id,
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
                    model="project.project",
                    res_id=project.id,
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

        # ---- expected 摘要基线比对（claim 之后：漂移路径释放幂等行为 failed）----
        stored_before = project.overview_html or ""
        digest_before = svc.overview_digest(stored_before)
        if not svc.baseline_matches(expected_digest, stored_before):
            _release_failed("baseline mismatch")
            return self._error(
                "BASELINE_MISMATCH",
                "项目概况已被并发修改（expected=%s，实际=%s），请刷新后重试"
                % (expected_digest, digest_before),
                "reload_and_retry",
                ts0,
            )

        # ---- 执行（savepoint 原子包裹；落库的永远是净化后内容）----
        try:
            with env.cr.savepoint():
                project.write({svc.EDITABLE_FIELD: sanitized})
        except Exception as exc:
            complete_write_idempotency(
                env,
                event_code=svc.EVENT_CODE,
                idempotency_key=idem_key,
                fingerprint=fingerprint,
                result={"error": str(exc), "trace_id": trace_id},
                trace_id=trace_id,
                status="failed",
                model="project.project",
                res_id=project.id,
            )
            return self._error(
                "PATCH_ERROR",
                "项目概况更新失败（已整体回滚）：%s" % exc,
                "retry",
                ts0,
            )

        # ---- after 投影（DB/ORM 重读为权威）----
        stored_after = project.overview_html or ""
        digest_after = svc.overview_digest(stored_after)
        duration_ms = int((time.time() - ts0) * 1000)

        data = apply_idempotency_identity(
            {
                "schema": svc.PATCH_SCHEMA,
                "field": svc.EDITABLE_FIELD,
                "project_id": project.id,
                "content_digest_before": digest_before,
                "content_digest_after": digest_after,
                "length_before": len(stored_before),
                "length_after": len(stored_after),
                "content_modified": sanitized != stored_before,
                "sanitized_input_changed": sanitized != raw_content,
                "content_after": stored_after,
                "max_length": svc.MAX_LENGTH,
                "success": True,
                "reason_code": "DONE",
                "message": "项目概况已更新（服务端净化后落库）",
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
            result={
                key: value
                for key, value in data.items()
                if key != "content_after"
            },
            trace_id=trace_id,
            model="project.project",
            res_id=project.id,
        )

        Audit = env.get("sc.audit.log")
        if Audit is not None:
            try:
                audit_common = {
                    "project_id": project.id,
                    "idempotency_key": idem_key,
                    "idempotency_fingerprint": fingerprint,
                    "trace_id": trace_id,
                    "duration_ms": duration_ms,
                }
                Audit.write_event(
                    event_code=svc.EVENT_CODE,
                    model="project.project",
                    res_id=project.id,
                    action="patch_overview_rich_text",
                    before=svc.build_audit_payload(
                        digest_before=digest_before,
                        digest_after=digest_before,
                        length_before=len(stored_before),
                        length_after=len(stored_before),
                        content_modified=False,
                        result={},
                        **audit_common,
                    ),
                    after=svc.build_audit_payload(
                        digest_before=digest_before,
                        digest_after=digest_after,
                        length_before=len(stored_before),
                        length_after=len(stored_after),
                        content_modified=sanitized != stored_before,
                        result={
                            key: value
                            for key, value in data.items()
                            if key != "content_after"
                        },
                        **audit_common,
                    ),
                    reason="project overview rich text patch (restricted_html)",
                    trace_id=trace_id,
                    project_id=project.id,
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
