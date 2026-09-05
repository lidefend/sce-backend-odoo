# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import timedelta
from uuid import uuid4

from odoo import fields
_logger = logging.getLogger(__name__)

from .reason_codes import (
    REASON_IDEMPOTENCY_CONFLICT,
    REASON_IDEMPOTENCY_IN_FLIGHT,
    failure_meta_for_reason,
)

SOURCE_KIND = "idempotency_audit_replay_projection"
SOURCE_AUTHORITIES = ("sc.audit.log", "idempotency_key", "request_fingerprint")
NO_BUSINESS_FACT_AUTHORITY = True


def source_authority_contract():
    return {
        "kind": SOURCE_KIND,
        "authorities": list(SOURCE_AUTHORITIES),
        "projection_only": True,
        "rebuildable": True,
        "no_business_fact_authority": NO_BUSINESS_FACT_AUTHORITY,
        "runtime_carrier": "idempotency_utils",
    }


def normalize_request_id(raw_value, *, prefix="req"):
    value = str(raw_value or "").strip()
    if value:
        return value
    return f"{prefix}_{uuid4().hex[:12]}"


def normalize_ids_for_fingerprint(values):
    normalized = []
    for raw_id in values or []:
        token = str(raw_id or "").strip()
        if not token:
            continue
        try:
            normalized.append(int(token))
        except Exception:
            normalized.append(f"raw:{token}")
    return list(sorted(normalized, key=lambda item: str(item)))


def sha1_json(payload):
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, default=str)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def build_idempotency_fingerprint(payload, *, normalize_id_keys=None):
    data = dict(payload or {})
    for key in normalize_id_keys or []:
        data[key] = normalize_ids_for_fingerprint(data.get(key) or [])
    return sha1_json(data)


def idempotency_replay_or_conflict(recent_entry, *, fingerprint, replay_payload_key="result"):
    entry = recent_entry if isinstance(recent_entry, dict) else None
    if not entry:
        return {"conflict": False, "replay_entry": None, "replay_payload": None}
    payload = entry.get("payload") or {}
    old_fingerprint = str(payload.get("idempotency_fingerprint") or "")
    if old_fingerprint and old_fingerprint != str(fingerprint or ""):
        return {"conflict": True, "replay_entry": None, "replay_payload": None}
    replay_payload = payload.get(replay_payload_key)
    if old_fingerprint and isinstance(replay_payload, dict):
        return {"conflict": False, "replay_entry": entry, "replay_payload": replay_payload}
    return {"conflict": False, "replay_entry": None, "replay_payload": None}


def replay_window_seconds(default_seconds, *, env_key):
    raw = str(os.getenv(env_key, "")).strip()
    if raw:
        try:
            return max(0, int(raw))
        except Exception:
            pass
    return max(0, int(default_seconds))


def _idempotency_security_domain(env, *, enforce_company=True, enforce_actor=True):
    domain = []
    user = getattr(env, "user", None)
    if enforce_actor and user:
        uid = int(getattr(user, "id", 0) or 0)
        if uid > 0:
            domain.append(("actor_uid", "=", uid))
    if enforce_company and user and getattr(user, "company_id", None):
        cid = int(getattr(user.company_id, "id", 0) or 0)
        if cid > 0:
            domain.append(("company_id", "=", cid))
    return domain


def _find_audit_entry(
    env,
    *,
    event_code,
    idempotency_key,
    limit=20,
    extra_domain=None,
    enforce_company=True,
    enforce_actor=True,
):
    if not idempotency_key:
        return None
    # 注意：env.get 对已注册模型返回空记录集，空记录集 bool() 为 False，
    # 存在性判定必须用 `is None`，否则会误判模型缺失而走回退路径。
    Audit = env.get("sc.audit.log")
    if Audit is None:
        return None
    try:
        domain = [("event_code", "=", event_code)]
        domain.extend(_idempotency_security_domain(env, enforce_company=enforce_company, enforce_actor=enforce_actor))
        if extra_domain:
            domain.extend(list(extra_domain))
        logs = Audit.sudo().search(domain, order="id desc", limit=max(1, int(limit)))
        for log in logs:
            after_raw = log.after_json or ""
            if not after_raw:
                continue
            try:
                payload = json.loads(after_raw)
            except Exception:
                continue
            if str(payload.get("idempotency_key") or "") != str(idempotency_key):
                continue
            return {
                "audit_id": int(log.id or 0),
                "trace_id": str(log.trace_id or ""),
                "ts": log.ts,
                "payload": payload,
            }
    except Exception:
        return None
    return None


def find_recent_audit_entry(
    env,
    *,
    event_code,
    idempotency_key,
    window_seconds,
    limit=20,
    extra_domain=None,
    enforce_company=True,
    enforce_actor=True,
):
    now = fields.Datetime.now()
    window_start = fields.Datetime.to_string(
        fields.Datetime.from_string(now) - timedelta(seconds=max(0, int(window_seconds)))
    )
    domain = [("ts", ">=", window_start)]
    if extra_domain:
        domain.extend(list(extra_domain))
    return _find_audit_entry(
        env,
        event_code=event_code,
        idempotency_key=idempotency_key,
        limit=limit,
        extra_domain=domain,
        enforce_company=enforce_company,
        enforce_actor=enforce_actor,
    )


def find_latest_audit_entry(
    env,
    *,
    event_code,
    idempotency_key,
    limit=20,
    extra_domain=None,
    enforce_company=True,
    enforce_actor=True,
):
    return _find_audit_entry(
        env,
        event_code=event_code,
        idempotency_key=idempotency_key,
        limit=limit,
        extra_domain=extra_domain,
        enforce_company=enforce_company,
        enforce_actor=enforce_actor,
    )


def has_latest_fingerprint_match(
    env,
    *,
    event_code,
    idempotency_key,
    fingerprint,
    limit=20,
    extra_domain=None,
    enforce_company=True,
    enforce_actor=True,
):
    entry = find_latest_audit_entry(
        env,
        event_code=event_code,
        idempotency_key=idempotency_key,
        limit=limit,
        extra_domain=extra_domain,
        enforce_company=enforce_company,
        enforce_actor=enforce_actor,
    )
    if not entry:
        return False
    payload = entry.get("payload") or {}
    old_fingerprint = str(payload.get("idempotency_fingerprint") or "")
    return bool(old_fingerprint and old_fingerprint == str(fingerprint or ""))


def resolve_idempotency_decision(
    env,
    *,
    event_code,
    idempotency_key,
    fingerprint,
    window_seconds,
    replay_payload_key="result",
    limit=20,
    recent_extra_domain=None,
    latest_extra_domain=None,
    enforce_company=True,
    enforce_actor=True,
):
    recent_entry = find_recent_audit_entry(
        env,
        event_code=event_code,
        idempotency_key=idempotency_key,
        window_seconds=window_seconds,
        limit=limit,
        extra_domain=recent_extra_domain,
        enforce_company=enforce_company,
        enforce_actor=enforce_actor,
    )
    decision = idempotency_replay_or_conflict(
        recent_entry,
        fingerprint=fingerprint,
        replay_payload_key=replay_payload_key,
    )
    conflict = bool(decision.get("conflict"))
    replay_entry = decision.get("replay_entry")
    replay_payload = decision.get("replay_payload")
    if conflict or replay_payload:
        return {
            "conflict": conflict,
            "replay_entry": replay_entry,
            "replay_payload": replay_payload,
            "replay_window_expired": False,
        }
    replay_window_expired = has_latest_fingerprint_match(
        env,
        event_code=event_code,
        idempotency_key=idempotency_key,
        fingerprint=fingerprint,
        limit=limit,
        extra_domain=latest_extra_domain if latest_extra_domain is not None else recent_extra_domain,
        enforce_company=enforce_company,
        enforce_actor=enforce_actor,
    )
    return {
        "conflict": False,
        "replay_entry": None,
        "replay_payload": None,
        "replay_window_expired": bool(replay_window_expired),
    }


def ids_summary(rows, *, sample_limit=20):
    normalized = []
    for value in rows or []:
        token = str(value or "").strip()
        if not token:
            continue
        try:
            normalized.append(int(token))
        except Exception:
            continue
    sample = normalized[: max(1, int(sample_limit))]
    payload = "|".join(sorted([str(x) for x in normalized]))
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest() if payload else ""
    return {"count": len(normalized), "sample": sample, "hash": digest}


def apply_replay_evidence(
    data,
    *,
    enabled=False,
    idempotent_replay=False,
    replay_entry=None,
):
    payload = dict(data or {})
    if not enabled:
        return payload
    payload["replay_from_audit_id"] = 0
    payload["replay_from_record_id"] = 0
    payload["replay_original_trace_id"] = ""
    payload["replay_age_ms"] = 0
    if not idempotent_replay or not isinstance(replay_entry, dict):
        return payload
    payload["replay_from_audit_id"] = int(replay_entry.get("audit_id") or 0)
    payload["replay_from_record_id"] = int(replay_entry.get("record_id") or 0)
    payload["replay_original_trace_id"] = str(replay_entry.get("trace_id") or "")
    ts = replay_entry.get("ts")
    if isinstance(ts, str):
        try:
            ts = fields.Datetime.from_string(ts)
        except Exception:
            ts = None
    now_dt = fields.Datetime.from_string(fields.Datetime.now())
    if ts:
        payload["replay_age_ms"] = max(0, int((now_dt - ts).total_seconds() * 1000))
    return payload


def build_idempotency_conflict_response(
    *,
    intent_type,
    request_id,
    idempotency_key,
    trace_id,
    include_replay_evidence=False,
):
    failure_meta = failure_meta_for_reason(REASON_IDEMPOTENCY_CONFLICT)
    data = {
        "request_id": request_id,
        "idempotency_key": idempotency_key,
        "idempotent_replay": False,
        "replay_window_expired": False,
        "idempotency_replay_reason_code": "",
        "trace_id": trace_id,
    }
    data = apply_replay_evidence(
        data,
        enabled=bool(include_replay_evidence),
        idempotent_replay=False,
        replay_entry=None,
    )
    return {
        "ok": False,
        "code": 409,
        "error": {
            "code": 409,
            "message": "idempotency key payload mismatch",
            "reason_code": REASON_IDEMPOTENCY_CONFLICT,
            "retryable": bool(failure_meta.get("retryable")),
            "error_category": str(failure_meta.get("error_category") or ""),
            "suggested_action": str(failure_meta.get("suggested_action") or ""),
        },
        "data": data,
        "meta": {"intent": str(intent_type or "")},
    }


def apply_idempotency_identity(
    data,
    *,
    request_id,
    idempotency_key,
    idempotency_fingerprint,
    trace_id,
):
    payload = dict(data or {})
    payload["request_id"] = str(payload.get("request_id") or request_id or "")
    payload["idempotency_key"] = str(idempotency_key or "")
    payload["idempotency_fingerprint"] = str(idempotency_fingerprint or "")
    payload["trace_id"] = str(payload.get("trace_id") or trace_id or "")
    return payload


def enrich_replay_contract(
    data,
    *,
    idempotent_replay=False,
    replay_window_expired=False,
    replay_reason_code="",
    replay_entry=None,
    include_replay_evidence=False,
):
    payload = dict(data or {})
    payload["idempotent_replay"] = bool(idempotent_replay)
    payload["replay_window_expired"] = bool(replay_window_expired)
    payload["idempotency_replay_reason_code"] = str(replay_reason_code or "")
    return apply_replay_evidence(
        payload,
        enabled=bool(include_replay_evidence),
        idempotent_replay=bool(idempotent_replay),
        replay_entry=replay_entry,
    )


# ---------------------------------------------------------------------------
# G7 统一写动作幂等（DB 仲裁，sc.idempotency.record）
#
# 与审计日志投影路径（上方函数族）的区别：
# - 去重权威 = sc.idempotency.record 的部分唯一索引 (company_id, actor_uid,
#   idempotency_key)，并发同键插入由数据库仲裁（输者 savepoint 回滚后回读
#   winner → replay / conflict），关闭 search 查重的竞态窗口；
# - replay 不受窗口限制（键即逻辑操作，永久重放）；window_seconds 仅作
#   replay_window_expired 信息标记，保持信封可观测语义不变；
# - sc.audit.log 仍是审计轨迹权威，两者职责分离：去重看本模型，追溯看审计。
# ---------------------------------------------------------------------------

WRITE_IDEMPOTENCY_MODEL = "sc.idempotency.record"
WRITE_IDEMPOTENCY_SOURCE_KIND = "sc_idempotency_record_dedup_authority"


def write_idempotency_source_authority_contract():
    return {
        "kind": WRITE_IDEMPOTENCY_SOURCE_KIND,
        "dedup_authority": WRITE_IDEMPOTENCY_MODEL,
        "unique_scope": ["company_id", "actor_uid", "idempotency_key"],
        "audit_trail_authority": "sc.audit.log",
        "replay_policy": "permanent_for_key",
        "window_semantics": "informational_only",
    }


def _write_record_domain(
    env,
    *,
    event_code,
    idempotency_key,
    enforce_company=True,
    enforce_actor=True,
):
    domain = [
        ("name", "=", str(event_code or "")),
        ("idempotency_key", "=", str(idempotency_key or "")),
    ]
    domain.extend(
        _idempotency_security_domain(
            env,
            enforce_company=enforce_company,
            enforce_actor=enforce_actor,
        )
    )
    return domain


def _write_record_to_entry(record):
    result = record.result_json
    return {
        "record_id": int(record.id or 0),
        "status": str(record.status or ""),
        "fingerprint": str(record.idempotency_fingerprint or ""),
        "result": result if isinstance(result, dict) else None,
        "trace_id": str(record.trace_id or ""),
        "created_at": record.created_at,
    }


def _write_replay_window_expired(entry, *, window_seconds):
    try:
        seconds = max(0, int(window_seconds or 0))
    except Exception:
        return False
    if seconds <= 0:
        return False
    created = entry.get("created_at") if isinstance(entry, dict) else None
    if not created:
        return False
    if isinstance(created, str):
        try:
            created = fields.Datetime.from_string(created)
        except Exception:
            return False
    try:
        now_dt = fields.Datetime.from_string(fields.Datetime.now())
        age = (now_dt - created).total_seconds()
    except Exception:
        return False
    return age > seconds


def _write_decision_from_entry(entry, *, fingerprint, window_seconds):
    if not isinstance(entry, dict):
        return {
            "mode": "new",
            "conflict": False,
            "replay_payload": None,
            "replay_entry": None,
            "replay_window_expired": False,
        }
    if str(entry.get("fingerprint") or "") != str(fingerprint or ""):
        return {
            "mode": "conflict",
            "conflict": True,
            "replay_payload": None,
            "replay_entry": None,
            "replay_window_expired": False,
        }
    status = str(entry.get("status") or "")
    if status == "done":
        payload = entry.get("result")
        if isinstance(payload, dict):
            return {
                "mode": "replay",
                "conflict": False,
                "replay_payload": payload,
                "replay_entry": entry,
                "replay_window_expired": _write_replay_window_expired(
                    entry, window_seconds=window_seconds
                ),
            }
        # done 但无可重放结果（异常历史）→ 视作冲突，避免静默重复执行
        return {
            "mode": "conflict",
            "conflict": True,
            "replay_payload": None,
            "replay_entry": entry,
            "replay_window_expired": False,
        }
    if status == "inflight":
        return {
            "mode": "in_flight",
            "conflict": False,
            "replay_payload": None,
            "replay_entry": entry,
            "replay_window_expired": False,
        }
    # failed → 允许接管重执行
    return {
        "mode": "new",
        "conflict": False,
        "replay_payload": None,
        "replay_entry": entry,
        "replay_window_expired": False,
        "takeover": True,
    }


def find_write_idempotency_record(
    env,
    *,
    event_code,
    idempotency_key,
    enforce_company=True,
    enforce_actor=True,
):
    Record = env.get(WRITE_IDEMPOTENCY_MODEL)
    if Record is None or not str(idempotency_key or "").strip():
        return None
    try:
        records = Record.sudo().search(
            _write_record_domain(
                env,
                event_code=event_code,
                idempotency_key=idempotency_key,
                enforce_company=enforce_company,
                enforce_actor=enforce_actor,
            ),
            order="id desc",
            limit=1,
        )
    except Exception:
        return None
    for record in records:
        return _write_record_to_entry(record)
    return None


def resolve_write_idempotency(
    env,
    *,
    event_code,
    idempotency_key,
    fingerprint,
    window_seconds=0,
    enforce_company=True,
    enforce_actor=True,
):
    """只读裁决：new / replay / conflict / in_flight（不动库）。"""
    entry = find_write_idempotency_record(
        env,
        event_code=event_code,
        idempotency_key=idempotency_key,
        enforce_company=enforce_company,
        enforce_actor=enforce_actor,
    )
    decision = _write_decision_from_entry(
        entry, fingerprint=fingerprint, window_seconds=window_seconds
    )
    decision["authority"] = "record" if entry else "none"
    return decision


def _write_claim_values(env, *, event_code, idempotency_key, fingerprint, trace_id, model, res_id):
    user = getattr(env, "user", None)
    uid = int(getattr(user, "id", 0) or 0) or None
    cid = None
    if user and getattr(user, "company_id", None):
        cid = int(getattr(user.company_id, "id", 0) or 0) or None
    return {
        "name": str(event_code or ""),
        "idempotency_key": str(idempotency_key or ""),
        "idempotency_fingerprint": str(fingerprint or ""),
        "status": "inflight",
        "trace_id": str(trace_id or ""),
        "model": str(model or ""),
        "res_id": int(res_id or 0),
        "actor_uid": uid,
        "company_id": cid,
        "created_at": fields.Datetime.now(),
    }


def claim_write_idempotency(
    env,
    *,
    event_code,
    idempotency_key,
    fingerprint,
    trace_id="",
    window_seconds=0,
    model="",
    res_id=0,
    enforce_company=True,
    enforce_actor=True,
    fallback_to_audit=True,
):
    """写动作幂等 claim（执行前调用）。

    返回 mode：
    - replay      → 重放既有结果（键已执行成功且指纹一致）
    - conflict    → 同键异指纹（409 IDEMPOTENCY_CONFLICT）
    - in_flight   → 并发赢家已提交但尚无可重放结果（409 可重试）
    - claimed     → 本请求获得执行权（新建 claim 行）
    - takeover    → 本请求获得执行权（接管既有 failed 行）
    - new         → 审计投影回退路径下放行执行（无去重记录落库）
    """
    Record = env.get(WRITE_IDEMPOTENCY_MODEL)
    key = str(idempotency_key or "").strip()
    if Record is None or not key:
        if not fallback_to_audit:
            return {"mode": "new", "authority": "none"}
        decision = resolve_idempotency_decision(
            env,
            event_code=event_code,
            idempotency_key=key,
            fingerprint=fingerprint,
            window_seconds=window_seconds,
            enforce_company=enforce_company,
            enforce_actor=enforce_actor,
        )
        if decision.get("conflict"):
            return {
                "mode": "conflict",
                "authority": "audit",
                "conflict": True,
                "replay_payload": None,
                "replay_entry": decision.get("replay_entry"),
                "replay_window_expired": False,
            }
        if decision.get("replay_payload"):
            return {
                "mode": "replay",
                "authority": "audit",
                "conflict": False,
                "replay_payload": decision.get("replay_payload"),
                "replay_entry": decision.get("replay_entry"),
                "replay_window_expired": False,
            }
        return {
            "mode": "new",
            "authority": "audit",
            "conflict": False,
            "replay_payload": None,
            "replay_entry": None,
            "replay_window_expired": bool(decision.get("replay_window_expired")),
        }

    decision = resolve_write_idempotency(
        env,
        event_code=event_code,
        idempotency_key=key,
        fingerprint=fingerprint,
        window_seconds=window_seconds,
        enforce_company=enforce_company,
        enforce_actor=enforce_actor,
    )
    if decision["mode"] in ("replay", "conflict", "in_flight"):
        return decision

    vals = _write_claim_values(
        env,
        event_code=event_code,
        idempotency_key=key,
        fingerprint=fingerprint,
        trace_id=trace_id,
        model=model,
        res_id=res_id,
    )
    try:
        with env.cr.savepoint():
            if decision.get("takeover") and (decision.get("replay_entry") or {}).get("record_id"):
                record = Record.sudo().browse(decision["replay_entry"]["record_id"])
                record.write(
                    {
                        "idempotency_fingerprint": vals["idempotency_fingerprint"],
                        "status": "inflight",
                        "trace_id": vals["trace_id"],
                        "created_at": vals["created_at"],
                    }
                )
                record_id = int(record.id or 0)
            else:
                record = Record.sudo().create(vals)
                record_id = int(record.id or 0)
    except Exception:
        # 唯一索引仲裁：并发赢家已插入/接管 → 回读裁决；无法回读则原样抛出
        winner = find_write_idempotency_record(
            env,
            event_code=event_code,
            idempotency_key=key,
            enforce_company=enforce_company,
            enforce_actor=enforce_actor,
        )
        if winner:
            arbitration = _write_decision_from_entry(
                winner, fingerprint=fingerprint, window_seconds=window_seconds
            )
            arbitration["authority"] = "record"
            arbitration["concurrent_winner"] = True
            if arbitration["mode"] == "new":
                arbitration["mode"] = "in_flight"
            return arbitration
        raise

    outcome = dict(decision)
    outcome["record_id"] = record_id
    outcome["authority"] = "record"
    if decision.get("takeover"):
        outcome["mode"] = "takeover"
    else:
        outcome["mode"] = "claimed"
    return outcome


def complete_write_idempotency(
    env,
    *,
    event_code,
    idempotency_key,
    fingerprint,
    result,
    trace_id="",
    status="done",
    model="",
    res_id=0,
    enforce_company=True,
    enforce_actor=True,
):
    """写动作幂等收尾（执行后调用）：落/更新结果，使后续同键请求可重放。"""
    Record = env.get(WRITE_IDEMPOTENCY_MODEL)
    key = str(idempotency_key or "").strip()
    if Record is None or not key:
        return {"recorded": False, "authority": "none"}
    now = fields.Datetime.now()
    safe_result = _json_safe_result(result)
    try:
        records = Record.sudo().search(
            _write_record_domain(
                env,
                event_code=event_code,
                idempotency_key=key,
                enforce_company=enforce_company,
                enforce_actor=enforce_actor,
            ),
            order="id desc",
            limit=1,
        )
        for record in records:
            # savepoint 包裹：write 逐字段进缓存后延迟 flush，
            # 中途失败须整体回滚，避免部分字段（如 status）残行落库。
            with env.cr.savepoint():
                record.write(
                    {
                        "status": str(status or "done"),
                        "result_json": safe_result,
                        "trace_id": str(trace_id or ""),
                        "finished_at": now,
                    }
                )
            return {
                "recorded": True,
                "updated": True,
                "record_id": int(record.id or 0),
                "authority": "record",
            }
        vals = _write_claim_values(
            env,
            event_code=event_code,
            idempotency_key=key,
            fingerprint=fingerprint,
            trace_id=trace_id,
            model=model,
            res_id=res_id,
        )
        vals.update(
            {
                "status": str(status or "done"),
                "result_json": safe_result,
                "finished_at": now,
            }
        )
        record = Record.sudo().create(vals)
        return {
            "recorded": True,
            "updated": False,
            "record_id": int(record.id or 0),
            "authority": "record",
        }
    except Exception:
        import traceback
        _logger.warning(
            "[write-idem][complete] failed key=%s\n%s", key, traceback.format_exc()
        )
        return {"recorded": False, "authority": "record"}


def _json_safe_result(result):
    """把执行结果净化为可安全写入 fields.Json 的 dict。

    响应 payload 可能携带 datetime/date 等非 JSON 原生类型
    （如 done_at: fields.Datetime.now()）——直接写入会在 convert_to_cache
    阶段抛 TypeError，且 Odoo 的 write 逐字段进缓存后延迟 flush，
    异常前已进缓存的字段（如 status）仍会随事务提交落库，
    留下「done 但无 result」的残行使后续同键请求被误判为冲突。
    """
    if not isinstance(result, dict):
        return {"result": result}
    try:
        json.dumps(result)
        return result
    except (TypeError, ValueError):
        return json.loads(json.dumps(result, default=str))


def build_idempotency_in_flight_response(
    *,
    intent_type,
    request_id,
    idempotency_key,
    trace_id,
):
    failure_meta = failure_meta_for_reason(REASON_IDEMPOTENCY_IN_FLIGHT)
    data = {
        "request_id": request_id,
        "idempotency_key": idempotency_key,
        "idempotent_replay": False,
        "replay_window_expired": False,
        "idempotency_replay_reason_code": REASON_IDEMPOTENCY_IN_FLIGHT,
        "trace_id": trace_id,
    }
    return {
        "ok": False,
        "code": 409,
        "error": {
            "code": 409,
            "message": "idempotency key execution still in flight",
            "reason_code": REASON_IDEMPOTENCY_IN_FLIGHT,
            "retryable": bool(failure_meta.get("retryable")),
            "error_category": str(failure_meta.get("error_category") or ""),
            "suggested_action": str(failure_meta.get("suggested_action") or ""),
        },
        "data": data,
        "meta": {"intent": str(intent_type or "")},
    }


def record_entry_as_replay_evidence(entry):
    """把幂等记录/审计条目统一适配为 replay 证据（apply_replay_evidence 形状）。"""
    if not isinstance(entry, dict):
        return None
    evidence = {
        "audit_id": int(entry.get("audit_id") or 0),
        "record_id": int(entry.get("record_id") or 0),
        "trace_id": str(entry.get("trace_id") or ""),
        "ts": entry.get("ts") if entry.get("ts") is not None else entry.get("created_at"),
    }
    return evidence
