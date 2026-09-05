# -*- coding: utf-8 -*-
"""BOQ 危险导入（replace/update）handler（G7.1 首切片，ADR-004 决策 4）。

数据契约：contracts/domain/boq-dangerous-import.yaml v1。
两阶段协议：
- project.boq.import.dangerous.preview：干跑解析 + 影响摘要 + confirm_token
  （无业务写；kill switch 关闭/无权组/版本不可变均结构化降级）；
- project.boq.import.dangerous.execute：confirm_token 逐位比对（TOCTOU +
  并发漂移防护）→ claim/complete 幂等（G7-INFRA 定式）→ savepoint 内
  replace（整版重写）/ update（编码匹配更新）→ sc.audit.log before/after。

安全边界：
- 专用组 smart_construction_core.group_sc_cap_boq_dangerous_import（不并入
  既有业务组）；
- kill switch ir.config_parameter sc.boq.dangerous_import.enabled 默认关闭
  （fail-closed）；
- 仅 draft/validated 版本可写（published/superseded/cancelled 拒绝，
  ORM 层 write/unlink 守卫兜底）；冻结项目拒绝（P0_BOQ_FROZEN 同源）。
"""
from __future__ import annotations

import base64
import hashlib
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

from odoo.addons.smart_construction_core.services import boq_dangerous_import_service as svc

DANGEROUS_GROUP = "smart_construction_core.group_sc_cap_boq_dangerous_import"
UPDATE_LINE_FIELDS = ("name", "quantity", "price", "imported_amount")


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


def _load_version(env, *, version_id, project_id):
    """search 语义：无权限与不存在同响应，避免版本枚举侧信道。"""
    Version = env["project.boq.version"]
    domain = [("id", "=", version_id)]
    if project_id > 0:
        domain.append(("project_id", "=", project_id))
    return Version.search(domain, limit=1)


def _parse_import_rows(env, *, version, file_data, filename, boq_category, preflight):
    """复用既有导入向导解析（digest/限额/UOM 白名单口径一致）。

    preflight=True（preview 干跑）：不创建计量单位（无业务写）；
    preflight=False（execute）：与向导 action_import 同口径（UOM 允许创建）。
    返回 (wizard, rows, skipped) 或抛异常（由调用方结构化降级）。
    """
    Wizard = env.get("project.boq.import.wizard")
    if Wizard is None:
        raise RuntimeError("project.boq.import.wizard unavailable")
    wizard = Wizard.create(
        {
            "project_id": version.project_id.id,
            "file": file_data,
            "filename": filename or "dangerous-import",
            "boq_category": boq_category or "boq",
        }
    )
    degraded_uoms = set()
    context = {"boq_import_uom_degraded": degraded_uoms}
    if preflight:
        context["boq_import_preflight"] = True
    # include_details=True 与向导 action_preflight/action_import 同口径：
    # CSV 分支仅在 include_details=True 时返回 4 元组（detail 载荷忽略不用）。
    rows, _pending_uoms, skipped, _detail = wizard.with_context(**context)._parse_file(
        include_details=True
    )
    return wizard, rows, int(skipped or 0)


def _project_lines(lines):
    """把 project.boq.line 记录集投影为影响摘要所需的纯数据行。"""
    projected = []
    for line in lines:
        projected.append(
            {
                "id": line.id,
                "code": line.code or "",
                "quantity": float(line.quantity or 0.0),
                "price": float(line.price or 0.0),
                "imported_amount": float(line.imported_amount or 0.0),
                "has_imported_amount": bool(line.has_imported_amount),
            }
        )
    return projected


def _version_lines(env, version):
    Line = env["project.boq.line"]
    return Line.search([("version_id", "=", version.id)], order="parent_path, sequence, id")


def _create_rows_in_version(wizard, Boq, rows, *, version_id, batch_id):
    """按向导 action_import 的创建策略落行（层级/平铺按 boq_category 分组）。"""
    grouped = {}
    for vals in rows:
        cat = vals.get("boq_category") or wizard.boq_category or "boq"
        grouped.setdefault(cat, []).append(
            dict(vals, version_id=version_id, import_batch_id=batch_id)
        )
    created = 0
    for cat, chunk in grouped.items():
        if cat in ("boq", "other"):
            created += int(wizard._create_with_hierarchy(Boq, chunk) or 0)
        else:
            created += int(wizard._batch_create(Boq, chunk) or 0)
    return created


def _update_line_values(row):
    """update 模式写入口径：仅数值/名称/单位，不动层级与状态。"""
    values = {
        "name": row.get("name") or "",
        "quantity": float(row.get("quantity") or 0.0),
        "price": float(row.get("price") or 0.0),
        "imported_amount": float(row.get("imported_amount") or 0.0),
        "has_imported_amount": bool(row.get("has_imported_amount")),
    }
    if row.get("uom_id"):
        values["uom_id"] = row.get("uom_id")
    return values


class _DangerousImportHandlerBase(BaseIntentHandler):
    """两个危险导入 intent 的共享工具（不注册、不映射）。"""

    VERSION = "1.0.0"
    ETAG_ENABLED = False
    REQUIRED_GROUPS = [DANGEROUS_GROUP]
    ACL_MODE = "record_rule"

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

    def _context_params(self, payload):
        params = _unwrap_params(payload, self.params)
        version_id = _to_int(params.get("version_id"))
        project_id = _to_int(params.get("project_id"))
        mode = svc.normalize_mode(params.get("mode"))
        file_data = params.get("file")
        filename = str(params.get("filename") or "").strip()
        boq_category = str(params.get("boq_category") or "").strip() or "boq"
        return {
            "version_id": version_id,
            "project_id": project_id,
            "mode": mode,
            "file": file_data,
            "filename": filename,
            "boq_category": boq_category,
            "params": params,
        }

    def _gate_version(self, env, ctx, ts0):
        """公共前置门：参数/开关/版本/状态/冻结。返回 (version, error_response)。"""
        if not _flag_on(env):
            return None, self._error(
                "CAPABILITY_DISABLED",
                "危险导入能力未开启（sc.boq.dangerous_import.enabled）",
                "enable_feature_flag",
                ts0,
            )
        if ctx["version_id"] <= 0 or not ctx["file"]:
            return None, self._error(
                "MISSING_PARAMS",
                "缺少参数：version_id 与 file 必填",
                "fix_input",
                ts0,
            )
        if not ctx["mode"]:
            return None, self._error(
                "UNSUPPORTED_MODE",
                "mode 仅支持 replace / update",
                "fix_input",
                ts0,
            )
        version = _load_version(
            env, version_id=ctx["version_id"], project_id=ctx["project_id"]
        )
        if not version:
            return None, self._error(
                "VERSION_NOT_FOUND",
                "未找到可访问的清单版本",
                "check_params",
                ts0,
            )
        if version.state not in svc.MUTABLE_VERSION_STATES:
            return None, self._error(
                "VERSION_NOT_MUTABLE",
                "仅草稿/已校验版本允许危险导入（当前状态：%s）" % (version.state or ""),
                "create_new_version",
                ts0,
            )
        if version.project_id and version.project_id.is_boq_frozen():
            return None, self._error(
                "BOQ_FROZEN",
                "项目[%s]已进入结算/支付关键节点，清单导入被冻结"
                % version.project_id.display_name,
                "check_project_state",
                ts0,
            )
        return version, None


class BoqDangerousImportPreviewHandler(_DangerousImportHandlerBase):
    INTENT_TYPE = "project.boq.import.dangerous.preview"
    DESCRIPTION = "BOQ 危险导入干跑预检（replace/update 影响摘要 + 确认令牌）"
    MACHINE_ACCESS = "read"
    SOURCE_AUTHORITY = {
        "kind": "boq_dangerous_import_preview_projection",
        "authorities": [
            "project.boq.version",
            "project.boq.line",
            "project.boq.import.wizard",
            "ir.config_parameter",
            "ir.model.access",
            "record_rule",
        ],
        "projection_only": True,
        "no_business_fact_authority": True,
    }

    def handle(self, payload=None, ctx=None):
        ts0 = time.time()
        env = self.env
        ctx_params = self._context_params(payload)
        version, error = self._gate_version(env, ctx_params, ts0)
        if error:
            return error

        try:
            _wizard, rows, skipped = _parse_import_rows(
                env,
                version=version,
                file_data=ctx_params["file"],
                filename=ctx_params["filename"],
                boq_category=ctx_params["boq_category"],
                preflight=True,
            )
        except Exception as exc:
            return self._error(
                "PARSE_ERROR",
                "导入文件解析失败：%s" % exc,
                "fix_input",
                ts0,
            )
        if not rows:
            return self._error(
                "PARSE_EMPTY",
                "未找到可导入的清单数据",
                "fix_input",
                ts0,
            )

        raw = base64.b64decode(ctx_params["file"])
        file_digest = hashlib.sha256(raw).hexdigest()
        existing = _project_lines(_version_lines(env, version))
        summary, ambiguous = svc.summarize_impact(
            ctx_params["mode"], existing, rows
        )
        if ambiguous:
            return self._error(
                "AMBIGUOUS_CODES",
                "以下清单编码在版本中重复出现且出现在导入文件中，update 模式无法唯一定位："
                + "、".join(ambiguous[: svc.AMBIGUOUS_CODE_SAMPLE_LIMIT])
                + ("…" if len(ambiguous) > svc.AMBIGUOUS_CODE_SAMPLE_LIMIT else ""),
                "use_replace_mode",
                ts0,
            )

        confirm_token = svc.build_confirm_token(
            version_id=version.id,
            mode=ctx_params["mode"],
            boq_category=ctx_params["boq_category"],
            file_digest=file_digest,
            summary=summary,
            user_id=env.user.id,
            company_id=(env.user.company_id.id if env.user.company_id else 0),
        )
        data = {
            "schema": svc.DANGEROUS_IMPORT_SCHEMA,
            "dangerous": True,
            "readonly": True,
            "mode": ctx_params["mode"],
            "version": {
                "id": version.id,
                "code": version.code,
                "state": version.state,
                "project_id": version.project_id.id,
            },
            "filename": ctx_params["filename"],
            "file_digest": file_digest,
            "skipped_rows": skipped,
            "summary": summary,
            "confirm_token": confirm_token,
            "confirm_required": True,
            "execute_intent": BoqDangerousImportExecuteHandler.INTENT_TYPE,
        }
        return {"ok": True, "data": data, "meta": self._meta(ts0)}


class BoqDangerousImportExecuteHandler(_DangerousImportHandlerBase):
    INTENT_TYPE = "project.boq.import.dangerous.execute"
    DESCRIPTION = "BOQ 危险导入执行（replace 整版重写 / update 编码匹配更新）"
    IDEMPOTENCY_WINDOW_SECONDS = 3600

    SOURCE_AUTHORITY = {
        "kind": "boq_dangerous_import_write",
        "authorities": [
            "project.boq.version",
            "project.boq.line",
            "project.boq.import.batch",
            "project.boq.import.wizard",
            "sc.idempotency.record",
            "sc.audit.log",
            "ir.model.access",
            "ir.rule",
            "odoo.orm",
        ],
        "projection_only": False,
        "write_authority": "project.boq.line",
        "idempotency_authority": "sc.idempotency.record + sc.audit.log",
        "feature_flag": svc.FLAG_KEY,
    }

    def _idempotency_window_seconds(self):
        return replay_window_seconds(
            self.IDEMPOTENCY_WINDOW_SECONDS,
            env_key="SC_BOQ_DANGEROUS_IMPORT_REPLAY_WINDOW_SEC",
        )

    def _fingerprint(self, *, version_id, mode, boq_category, file_digest, confirm_token, idem_key):
        payload = {
            "intent": self.INTENT_TYPE,
            "db": self.env.cr.dbname,
            "user_id": int(self.env.user.id or 0),
            "company_id": (
                int(self.env.user.company_id.id or 0)
                if self.env.user and self.env.user.company_id
                else 0
            ),
            "version_id": int(version_id or 0),
            "mode": mode,
            "boq_category": boq_category,
            "file_digest": file_digest,
            "confirm_token": confirm_token,
            "idempotency_key": idem_key,
        }
        return build_idempotency_fingerprint(payload)

    def handle(self, payload=None, ctx=None):
        ts0 = time.time()
        env = self.env
        ctx_params = self._context_params(payload)
        params = ctx_params["params"]
        request_id = normalize_request_id(params.get("request_id"), prefix="boqdi_req")
        idem_key = str(params.get("idempotency_key") or "").strip() or request_id
        trace_id = f"boq_di_{uuid4().hex[:12]}"
        started = fields.Datetime.now()

        version, error = self._gate_version(env, ctx_params, ts0)
        if error:
            return error
        confirm_token_param = str(params.get("confirm_token") or "").strip()
        if not confirm_token_param:
            return self._error(
                "MISSING_PARAMS",
                "缺少参数：confirm_token 必填（先执行 preview 干跑获取确认令牌）",
                "run_preview_first",
                ts0,
            )

        # ---- 幂等前置（G7-INFRA claim 定式，先于令牌重算与文件解析）----
        # 指纹绑定「客户端提供的 confirm_token + 文件摘要」：响应丢失后的
        # 原样重试（同键同指纹）命中 replay 分支，直接返回首次结果；
        # 令牌重算仅对首次执行生效——首次执行后 DB 已变，重算必然漂移，
        # 这正是 TOCTOU 防护语义，与重放通道互不冲突。
        try:
            raw = base64.b64decode(ctx_params["file"])
        except Exception as exc:
            return self._error(
                "PARSE_ERROR",
                "导入文件解码失败：%s" % exc,
                "fix_input",
                ts0,
            )
        file_digest = hashlib.sha256(raw).hexdigest()
        fingerprint = self._fingerprint(
            version_id=version.id,
            mode=ctx_params["mode"],
            boq_category=ctx_params["boq_category"],
            file_digest=file_digest,
            confirm_token=confirm_token_param,
            idem_key=idem_key,
        )
        claim = claim_write_idempotency(
            env,
            event_code=svc.EVENT_CODE,
            idempotency_key=idem_key,
            fingerprint=fingerprint,
            trace_id=trace_id,
            window_seconds=self._idempotency_window_seconds(),
            model="project.boq.version",
            res_id=version.id,
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
                    model="project.boq.version",
                    res_id=version.id,
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

        # ---- 解析 + 令牌重算（claim 之后：任何失败都释放幂等行为 failed）----
        try:
            wizard, rows, skipped = _parse_import_rows(
                env,
                version=version,
                file_data=ctx_params["file"],
                filename=ctx_params["filename"],
                boq_category=ctx_params["boq_category"],
                preflight=False,
            )
        except Exception as exc:
            _release_failed("parse error: %s" % exc)
            return self._error(
                "PARSE_ERROR",
                "导入文件解析失败：%s" % exc,
                "fix_input",
                ts0,
            )
        if not rows:
            _release_failed("empty rows")
            return self._error(
                "PARSE_EMPTY",
                "未找到可导入的清单数据",
                "fix_input",
                ts0,
            )
        existing = _project_lines(_version_lines(env, version))
        summary_before, ambiguous = svc.summarize_impact(
            ctx_params["mode"], existing, rows
        )
        if ambiguous:
            _release_failed("ambiguous codes: %s" % "、".join(ambiguous[:10]))
            return self._error(
                "AMBIGUOUS_CODES",
                "清单编码歧义（版本内重复且出现在文件中），请改用 replace 模式",
                "use_replace_mode",
                ts0,
            )
        confirm_token = svc.build_confirm_token(
            version_id=version.id,
            mode=ctx_params["mode"],
            boq_category=ctx_params["boq_category"],
            file_digest=file_digest,
            summary=summary_before,
            user_id=env.user.id,
            company_id=(env.user.company_id.id if env.user.company_id else 0),
        )
        if not svc.confirm_token_matches(confirm_token, confirm_token_param):
            _release_failed("confirm token mismatch")
            return self._error(
                "CONFIRM_TOKEN_MISMATCH",
                "确认令牌不匹配：文件、版本明细或操作主体与 preview 时不一致，请重新干跑预检",
                "run_preview_first",
                ts0,
            )

        # ---- 执行（savepoint 原子包裹：业务写失败整体回滚，claim 行随事务保留）----
        Boq = env["project.boq.line"]
        Batch = env["project.boq.import.batch"]
        lines_deleted = 0
        lines_updated = 0
        lines_created = 0
        batch = None
        try:
            with env.cr.savepoint():
                batch = Batch.create(
                    {
                        "name": "危险导入(%s) · %s"
                        % (ctx_params["mode"], ctx_params["filename"] or "清单导入"),
                        "project_id": version.project_id.id,
                        "version_id": version.id,
                        "filename": ctx_params["filename"] or "未命名文件",
                        "file_digest": file_digest,
                        "row_count": len(rows),
                        "item_count": summary_before.get("parsed_item_count") or 0,
                        "skipped_count": skipped,
                        "preview_payload": {
                            "schema": svc.DANGEROUS_IMPORT_SCHEMA,
                            "dangerous": True,
                            "mode": ctx_params["mode"],
                            "summary": summary_before,
                            "file_digest": file_digest,
                        },
                    }
                )
                if ctx_params["mode"] == "replace":
                    lines_deleted = len(existing)
                    if existing:
                        _version_lines(env, version).unlink()
                    lines_created = _create_rows_in_version(
                        wizard, Boq, rows, version_id=version.id, batch_id=batch.id
                    )
                else:
                    existing_records = _version_lines(env, version)
                    by_code = {}
                    for record in existing_records:
                        code = str(record.code or "").strip()
                        if code:
                            by_code.setdefault(code, record)
                    create_rows = []
                    for row in rows:
                        code = str(row.get("code") or "").strip()
                        if code and code in by_code:
                            by_code[code].write(_update_line_values(row))
                            lines_updated += 1
                        else:
                            create_rows.append(row)
                    lines_created = _create_rows_in_version(
                        wizard, Boq, create_rows, version_id=version.id, batch_id=batch.id
                    )
                # 以项目权威（DB 重读）计算 after 摘要，不信执行侧计数
                summary_after, _amb = svc.summarize_impact(
                    ctx_params["mode"], _project_lines(_version_lines(env, version)), rows
                )
                batch.write(
                    {
                        "state": "imported",
                        "log": (
                            "危险导入(%s)：删除 %d 行 / 更新 %d 行 / 新建 %d 行；"
                            "金额 %.2f → %.2f。"
                            % (
                                ctx_params["mode"],
                                lines_deleted,
                                lines_updated,
                                lines_created,
                                float(summary_before.get("amount_before") or 0.0),
                                float(summary_after.get("amount_after") or 0.0),
                            )
                        ),
                        "imported_at": fields.Datetime.now(),
                        "imported_by": env.user.id,
                    }
                )
        except Exception as exc:
            complete_write_idempotency(
                env,
                event_code=svc.EVENT_CODE,
                idempotency_key=idem_key,
                fingerprint=fingerprint,
                result={"error": str(exc), "trace_id": trace_id},
                trace_id=trace_id,
                status="failed",
                model="project.boq.version",
                res_id=version.id,
            )
            return self._error(
                "IMPORT_ERROR",
                "危险导入执行失败（已整体回滚）：%s" % exc,
                "retry",
                ts0,
            )

        duration_ms = int(
            (
                fields.Datetime.from_string(fields.Datetime.now())
                - fields.Datetime.from_string(started)
            ).total_seconds()
            * 1000
        )
        data = apply_idempotency_identity(
            {
                "schema": svc.DANGEROUS_IMPORT_SCHEMA,
                "dangerous": True,
                "mode": ctx_params["mode"],
                "version_id": version.id,
                "version_code": version.code,
                "project_id": version.project_id.id,
                "success": True,
                "reason_code": "DONE",
                "message": "危险导入(%s)执行完成" % ctx_params["mode"],
                "lines_deleted": lines_deleted,
                "lines_updated": lines_updated,
                "lines_created": lines_created,
                "summary_before": summary_before,
                "summary_after": summary_after,
                "file_digest": file_digest,
                "batch_id": batch.id if batch else 0,
                "skipped_rows": skipped,
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
            model="project.boq.version",
            res_id=version.id,
        )

        Audit = env.get("sc.audit.log")
        if Audit is not None:
            try:
                Audit.write_event(
                    event_code=svc.EVENT_CODE,
                    model="project.boq.version",
                    res_id=version.id,
                    action=ctx_params["mode"],
                    before=svc.build_audit_payload(
                        mode=ctx_params["mode"],
                        version_id=version.id,
                        project_id=version.project_id.id,
                        file_digest=file_digest,
                        idempotency_key=idem_key,
                        idempotency_fingerprint=fingerprint,
                        trace_id=trace_id,
                        summary_before=summary_before,
                        summary_after={},
                        result={},
                        duration_ms=duration_ms,
                    ),
                    after=svc.build_audit_payload(
                        mode=ctx_params["mode"],
                        version_id=version.id,
                        project_id=version.project_id.id,
                        file_digest=file_digest,
                        idempotency_key=idem_key,
                        idempotency_fingerprint=fingerprint,
                        trace_id=trace_id,
                        summary_before={},
                        summary_after=summary_after,
                        result=data,
                        duration_ms=duration_ms,
                    ),
                    reason="boq dangerous import (%s)" % ctx_params["mode"],
                    trace_id=trace_id,
                    project_id=version.project_id.id,
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
