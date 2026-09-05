# -*- coding: utf-8 -*-
"""G7 幂等基建桩测试：sc.idempotency.record 去重权威（claim/complete/replay/conflict/in_flight）。

加载真实 utils/idempotency.py（odoo 桩注入），用 fake env + fake record 模型
验证裁决语义与并发唯一冲突仲裁路径。
"""
from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from datetime import datetime, timedelta
from pathlib import Path


UTILS_DIR = Path(__file__).resolve().parents[1] / "utils"


def _install_module(name, **attrs):
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


def _load_idempotency():
    _install_module("odoo", fields=types.SimpleNamespace(Datetime=types.SimpleNamespace()))
    _install_module("odoo.addons")
    smart_core_pkg = _install_module("odoo.addons.smart_core")
    smart_core_pkg.__path__ = [str(UTILS_DIR.parent)]
    utils_pkg = _install_module("odoo.addons.smart_core.utils")
    utils_pkg.__path__ = [str(UTILS_DIR)]

    reason_codes = _install_module("odoo.addons.smart_core.utils.reason_codes")
    reason_codes.REASON_IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"
    reason_codes.REASON_IDEMPOTENCY_IN_FLIGHT = "IDEMPOTENCY_IN_FLIGHT"
    reason_codes.REASON_REPLAY_WINDOW_EXPIRED = "REPLAY_WINDOW_EXPIRED"
    reason_codes.failure_meta_for_reason = lambda reason: {
        "retryable": reason == "IDEMPOTENCY_IN_FLIGHT",
        "error_category": "conflict",
        "suggested_action": "retry_same_key_later",
    }

    module_name = "odoo.addons.smart_core.utils.idempotency"
    sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(module_name, UTILS_DIR / "idempotency.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class _FakeCr:
    def __init__(self, fail_on_create=False):
        self.savepoints = 0
        self.fail_on_create = fail_on_create

    def savepoint(self):
        self.savepoints += 1
        return _FakeSavepoint()


class _FakeSavepoint:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeRecord:
    _next_id = 100

    def __init__(self, vals):
        _FakeRecord._next_id += 1
        self.id = _FakeRecord._next_id
        self.values = dict(vals)
        for key in ("result_json", "trace_id", "model", "res_id", "created_at", "finished_at", "actor_uid", "company_id"):
            self.values.setdefault(key, None)

    def __getattr__(self, name):
        values = object.__getattribute__(self, "values")
        if name in values:
            return values[name]
        raise AttributeError(name)

    def write(self, vals):
        self.values.update(vals)
        return True


class _FakeRecordset:
    """Odoo recordset 桩：search 过滤 + 单记录属性代理。"""

    def __init__(self, records):
        self._records = list(records)

    def __iter__(self):
        return iter(self._records)

    def __len__(self):
        return len(self._records)

    def __getattr__(self, name):
        if not self._records:
            raise AttributeError("empty recordset")
        return self._records[0].values.get(name)

    def write(self, vals):
        for record in self._records:
            record.write(vals)
        return True


class _FakeRecordModel:
    """sc.idempotency.record 模型桩（含并发唯一冲突注入）。

    模拟真实 Odoo 语义：env.get() 返回的空记录集对象是假值
    （__len__ == 0），存在性判定必须用 `is None` 而非真值判断。
    """

    def __init__(self, cr):
        self.rows = []
        self.cr = cr
        self.create_fail_once_with = None
        self.search_miss_once = False

    def __len__(self):
        # 真实空记录集：len == 0，bool() 为 False
        return 0

    def sudo(self):
        return self

    def search(self, domain, order="id desc", limit=None):
        if self.search_miss_once:
            self.search_miss_once = False
            return _FakeRecordset([])
        matched = []
        for record in self.rows:
            ok = True
            for leaf in domain:
                key, op, value = leaf
                actual = record.values.get(key)
                if op == "=":
                    if actual != value:
                        ok = False
                        break
            if ok:
                matched.append(record)
        matched.sort(key=lambda r: r.id, reverse=True)
        if limit:
            matched = matched[:limit]
        return _FakeRecordset(matched)

    def create(self, vals):
        if self.create_fail_once_with is not None:
            key = self.create_fail_once_with
            self.create_fail_once_with = None
            if vals.get("idempotency_key") == key:
                raise Exception("duplicate key value violates unique constraint")
        record = _FakeRecord(vals)
        self.rows.append(record)
        return record

    def browse(self, record_id):
        for record in self.rows:
            if record.id == int(record_id):
                return _FakeRecordset([record])
        return _FakeRecordset([])


class _FakeUser:
    def __init__(self, uid=7, company_id=3):
        self.id = uid
        self.company_id = types.SimpleNamespace(id=company_id)


class _FakeEnv:
    def __init__(self, record_model, cr, user=None):
        self._models = {"sc.idempotency.record": record_model}
        self.cr = cr
        self.user = user or _FakeUser()

    def get(self, name):
        return self._models.get(name)


def _now():
    return datetime(2026, 9, 6, 4, 0, 0)


class TestWriteIdempotencyClaim(unittest.TestCase):
    def setUp(self):
        self.module = _load_idempotency()
        # 桩 datetime：now 固定，便于窗口判定
        self.module.fields.Datetime.now = staticmethod(_now)
        self.module.fields.Datetime.from_string = staticmethod(lambda v: v if isinstance(v, datetime) else datetime(2026, 9, 6, 4, 0, 0))
        self.module.fields.Datetime.to_string = staticmethod(lambda v: str(v))
        self.cr = _FakeCr()
        self.model = _FakeRecordModel(self.cr)
        self.env = _FakeEnv(self.model, self.cr)

    def _claim(self, key="k1", fingerprint="fp1"):
        return self.module.claim_write_idempotency(
            self.env,
            event_code="MY_WORK_COMPLETE_BATCH",
            idempotency_key=key,
            fingerprint=fingerprint,
            trace_id="t1",
            window_seconds=120,
        )

    def _complete(self, key="k1", fingerprint="fp1", result=None, status="done"):
        return self.module.complete_write_idempotency(
            self.env,
            event_code="MY_WORK_COMPLETE_BATCH",
            idempotency_key=key,
            fingerprint=fingerprint,
            result=result or {"success": True, "done_count": 2},
            trace_id="t1",
            status=status,
        )

    def test_first_claim_creates_inflight(self):
        decision = self._claim()
        self.assertEqual(decision["mode"], "claimed")
        self.assertEqual(decision["authority"], "record")
        self.assertEqual(len(self.model.rows), 1)
        self.assertEqual(self.model.rows[0].values["status"], "inflight")

    def test_done_same_fingerprint_replays_permanently(self):
        self._claim()
        self._complete()
        decision = self._claim()
        self.assertEqual(decision["mode"], "replay")
        self.assertEqual(decision["replay_payload"], {"success": True, "done_count": 2})
        self.assertEqual(decision["replay_entry"]["status"], "done")
        # 记录行不新增
        self.assertEqual(len(self.model.rows), 1)

    def test_done_beyond_window_still_replays_with_expired_flag(self):
        self._claim()
        self._complete()
        # 把记录时间拨回 1 小时前（超 120s 窗口）
        self.model.rows[0].values["created_at"] = _now() - timedelta(hours=1)
        decision = self._claim()
        self.assertEqual(decision["mode"], "replay")
        self.assertTrue(decision["replay_window_expired"])

    def test_same_key_different_fingerprint_conflicts(self):
        self._claim()
        self._complete()
        decision = self._claim(key="k1", fingerprint="fp2")
        self.assertEqual(decision["mode"], "conflict")
        self.assertTrue(decision["conflict"])

    def test_done_without_replayable_result_conflicts(self):
        self._claim()
        self._complete(result={"success": True})
        self.model.rows[0].values["result_json"] = None
        decision = self._claim()
        self.assertEqual(decision["mode"], "conflict")

    def test_failed_row_allows_takeover(self):
        self._claim()
        self._complete(status="failed")
        decision = self._claim()
        self.assertEqual(decision["mode"], "takeover")
        self.assertEqual(self.model.rows[0].values["status"], "inflight")

    def test_concurrent_unique_violation_rereads_winner(self):
        self._claim()  # winner claims k1
        self._complete()
        # 模拟并发输者：预读时赢家事务未提交（search miss）→ 插入触发唯一冲突 → 回读赢家
        self.model.search_miss_once = True
        self.model.create_fail_once_with = "k1"
        decision = self._claim()
        self.assertEqual(decision["mode"], "replay")
        self.assertTrue(decision.get("concurrent_winner"))
        self.assertEqual(decision["replay_payload"], {"success": True, "done_count": 2})

    def test_inflight_without_winner_result_reports_in_flight(self):
        record = _FakeRecord(
            {
                "name": "MY_WORK_COMPLETE_BATCH",
                "idempotency_key": "k1",
                "idempotency_fingerprint": "fp1",
                "status": "inflight",
                "actor_uid": 7,
                "company_id": 3,
                "created_at": _now(),
            }
        )
        self.model.rows.append(record)
        decision = self._claim()
        self.assertEqual(decision["mode"], "in_flight")

    def test_complete_updates_existing_row(self):
        self._claim()
        outcome = self._complete(result={"success": True, "done_count": 3})
        self.assertTrue(outcome["recorded"])
        self.assertTrue(outcome["updated"])
        self.assertEqual(self.model.rows[0].values["status"], "done")
        self.assertEqual(self.model.rows[0].values["result_json"], {"success": True, "done_count": 3})

    def test_complete_creates_row_when_missing(self):
        outcome = self._complete()
        self.assertTrue(outcome["recorded"])
        self.assertFalse(outcome["updated"])
        self.assertEqual(len(self.model.rows), 1)

    def test_model_absent_falls_back_to_audit_new(self):
        env = _FakeEnv(_FakeRecordModel(self.cr), self.cr)
        env._models = {}
        decision = self.module.claim_write_idempotency(
            env,
            event_code="X",
            idempotency_key="k1",
            fingerprint="fp1",
            window_seconds=120,
        )
        self.assertEqual(decision["mode"], "new")
        self.assertEqual(decision["authority"], "audit")

    def test_datetime_in_result_is_sanitized_before_json_write(self):
        # 回归钉子：响应 payload 含 datetime（如 done_at: fields.Datetime.now()，
        # 该 Odoo 构建返回 datetime 对象）时，fields.Json 写入会抛 TypeError，
        # 且 Odoo write 逐字段进缓存延迟 flush 会留下「done 无 result」残行。
        env = _FakeEnv(_FakeRecordModel(self.cr), self.cr)
        self.module.claim_write_idempotency(
            env, event_code="X", idempotency_key="k9", fingerprint="fp9"
        )
        outcome = self.module.complete_write_idempotency(
            env,
            event_code="X",
            idempotency_key="k9",
            fingerprint="fp9",
            result={"ok": True, "done_at": datetime(2026, 9, 6, 4, 0, 0)},
        )
        self.assertTrue(outcome["recorded"])
        row = env.get("sc.idempotency.record").rows[0]
        self.assertIsInstance(row.values["result_json"]["done_at"], str)
        self.assertEqual(row.values["status"], "done")
        self.assertIsNotNone(row.values["finished_at"])

    def test_falsy_model_object_still_uses_record_authority(self):
        # 回归钉子：真实 Odoo 中 env.get() 返回空记录集（假值对象），
        # 存在性判定若误用真值判断会静默回退 audit 通道（曾在线上踩坑）。
        env = _FakeEnv(_FakeRecordModel(self.cr), self.cr)
        self.assertFalse(env.get("sc.idempotency.record"))  # 空记录集语义
        decision = self.module.claim_write_idempotency(
            env,
            event_code="X",
            idempotency_key="k1",
            fingerprint="fp1",
            window_seconds=120,
        )
        self.assertEqual(decision["mode"], "claimed")
        self.assertEqual(decision["authority"], "record")
        outcome = self.module.complete_write_idempotency(
            env,
            event_code="X",
            idempotency_key="k1",
            fingerprint="fp1",
            result={"ok": True},
        )
        self.assertTrue(outcome["recorded"])
        self.assertEqual(outcome["authority"], "record")

    def test_model_absent_complete_is_noop(self):
        env = _FakeEnv(_FakeRecordModel(self.cr), self.cr)
        env._models = {}
        outcome = self.module.complete_write_idempotency(
            env,
            event_code="X",
            idempotency_key="k1",
            fingerprint="fp1",
            result={"ok": True},
        )
        self.assertFalse(outcome["recorded"])

    def test_in_flight_response_envelope(self):
        response = self.module.build_idempotency_in_flight_response(
            intent_type="my.work.complete_batch",
            request_id="r1",
            idempotency_key="k1",
            trace_id="t1",
        )
        self.assertFalse(response["ok"])
        self.assertEqual(response["code"], 409)
        self.assertEqual(response["error"]["reason_code"], "IDEMPOTENCY_IN_FLIGHT")
        self.assertTrue(response["error"]["retryable"])

    def test_record_entry_replay_evidence_adapter(self):
        evidence = self.module.record_entry_as_replay_evidence(
            {"record_id": 12, "trace_id": "t9", "created_at": _now()}
        )
        self.assertEqual(evidence["record_id"], 12)
        self.assertEqual(evidence["audit_id"], 0)
        self.assertEqual(evidence["ts"], _now())

    def test_replay_evidence_includes_record_id(self):
        data = self.module.apply_replay_evidence(
            {},
            enabled=True,
            idempotent_replay=True,
            replay_entry={"record_id": 5, "trace_id": "t", "ts": _now()},
        )
        self.assertEqual(data["replay_from_record_id"], 5)
        self.assertEqual(data["replay_from_audit_id"], 0)

    def test_security_domain_isolates_actor_and_company(self):
        record = _FakeRecord(
            {
                "name": "MY_WORK_COMPLETE_BATCH",
                "idempotency_key": "k1",
                "idempotency_fingerprint": "fp1",
                "status": "done",
                "result_json": {"success": True},
                "actor_uid": 7,
                "company_id": 3,
                "created_at": _now(),
            }
        )
        self.model.rows.append(record)
        # 同键但不同 actor → 查不到 → new（隔离生效）
        other_env = _FakeEnv(self.model, self.cr, user=_FakeUser(uid=8, company_id=3))
        decision = self.module.claim_write_idempotency(
            other_env,
            event_code="MY_WORK_COMPLETE_BATCH",
            idempotency_key="k1",
            fingerprint="fp1",
            window_seconds=120,
        )
        self.assertEqual(decision["mode"], "claimed")


if __name__ == "__main__":
    unittest.main()
