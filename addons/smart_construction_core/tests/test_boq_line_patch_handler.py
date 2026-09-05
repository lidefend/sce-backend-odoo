# -*- coding: utf-8 -*-
"""BOQ 行内联编辑 handler 单测（G7.2，G7_LAUNCH_SCOPING §4 切片 3）。

桩加载模式：不依赖 Odoo 数据库，验证
- 服务纯函数：normalize_quantity（None/非法/NaN/Inf）/ quantity_baseline_matches
  （round(6) 精度容差）/ qty_below_done
- handler：缺参/非法→MISSING_PARAMS/INVALID_QUANTITY（claim 前不占幂等行）；
  行不存在→LINE_NOT_FOUND；published→VERSION_NOT_MUTABLE；冻结→BOQ_FROZEN；
  基线漂移→BASELINE_MISMATCH（claim 后，幂等行落 failed）；低于完成量→
  QTY_BELOW_DONE；成功→write(quantity) + 服务端重算投影（amount/qty_remain/
  version.total_amount）+ complete(done) + audit before/after；replay→重放
  信封（无重复写）；conflict/in_flight→409 信封；执行异常→PATCH_ERROR +
  complete(failed)
"""
import datetime as _dt
import importlib.util
import sys
import types
import unittest
from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1]


class _FakeDatetime:
    @staticmethod
    def now():
        return _dt.datetime(2026, 9, 6, 12, 0, 0)

    @staticmethod
    def to_string(value):
        if isinstance(value, str):
            return value
        return value.strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def from_string(value):
        if isinstance(value, _dt.datetime):
            return value
        return _dt.datetime.strptime(value, "%Y-%m-%d %H:%M:%S")


# handler 通过 fields.Datetime.now()/from_string()/to_string() 访问，
# 将类自身挂为 Datetime 属性即可同时满足两种访问面。
_FakeDatetime.Datetime = _FakeDatetime


def _install_module(name, **attrs):
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


# ---------------------------------------------------------------------------
# smart_core.utils.idempotency 桩（handler 导入面）
# ---------------------------------------------------------------------------


def _stub_apply_idempotency_identity(data, **kw):
    data = dict(data or {})
    data.update(
        {
            "request_id": kw.get("request_id"),
            "idempotency_key": kw.get("idempotency_key"),
            "idempotency_fingerprint": kw.get("idempotency_fingerprint"),
            "trace_id": kw.get("trace_id"),
        }
    )
    return data


def _stub_enrich_replay_contract(data, **kw):
    data = dict(data or {})
    for key, value in kw.items():
        data[key] = value
    return data


def _stub_build_conflict_response(**kw):
    return {
        "ok": False,
        "error": {
            "code": "IDEMPOTENCY_CONFLICT",
            "message": "同键异指纹冲突",
            "suggested_action": "use_new_request_id",
        },
        "data": {},
        "meta": {"intent": kw.get("intent_type")},
    }


def _stub_build_in_flight_response(**kw):
    return {
        "ok": False,
        "error": {
            "code": "IDEMPOTENCY_IN_FLIGHT",
            "message": "并发执行中",
            "suggested_action": "retry_same_key_later",
        },
        "data": {},
        "meta": {"intent": kw.get("intent_type")},
    }


def _install_idempotency_stub():
    return _install_module(
        "odoo.addons.smart_core.utils.idempotency",
        apply_idempotency_identity=_stub_apply_idempotency_identity,
        enrich_replay_contract=_stub_enrich_replay_contract,
        build_idempotency_conflict_response=_stub_build_conflict_response,
        build_idempotency_in_flight_response=_stub_build_in_flight_response,
        build_idempotency_fingerprint=lambda payload, **kw: "fp_sha1_stub",
        claim_write_idempotency=lambda env, **kw: {"mode": "claimed"},
        complete_write_idempotency=lambda env, **kw: {"recorded": True},
        normalize_request_id=lambda raw, prefix="": str(raw or "") or (prefix + "_stub"),
        record_entry_as_replay_evidence=lambda entry: entry,
        replay_window_seconds=lambda default, env_key=None: default,
    )


def _load_service_module():
    _install_module("odoo", fields=_FakeDatetime)
    _install_module("odoo.addons")
    _install_module("odoo.addons.smart_construction_core")
    services_pkg = _install_module("odoo.addons.smart_construction_core.services")
    name = "odoo.addons.smart_construction_core.services.boq_line_patch_service"
    sys.modules.pop(name, None)
    spec = importlib.util.spec_from_file_location(
        name, _ROOT / "services" / "boq_line_patch_service.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    setattr(services_pkg, "boq_line_patch_service", module)
    spec.loader.exec_module(module)
    return module


svc = _load_service_module()


def _load_handler_module():
    odoo_mod = _install_module("odoo", fields=_FakeDatetime)
    odoo_mod.__path__ = []
    _install_module("odoo.addons")
    _install_module("odoo.addons.smart_construction_core")
    handlers_pkg = _install_module("odoo.addons.smart_construction_core.handlers")
    smart_core_mod = _install_module("odoo.addons.smart_core")
    core_mod = _install_module("odoo.addons.smart_core.core")
    utils_mod = _install_module("odoo.addons.smart_core.utils")
    smart_core_mod.__path__ = [str(_ROOT.parent / "smart_core")]
    core_mod.__path__ = [str(_ROOT.parent / "smart_core" / "core")]
    utils_mod.__path__ = [str(_ROOT.parent / "smart_core" / "utils")]

    class _BaseIntentHandler:
        def __init__(self, env=None, params=None, payload=None, context=None):
            self.env = env or {}
            self.params = params or {}
            self.payload = payload or {}
            self.context = context or {}

    _install_module(
        "odoo.addons.smart_core.core.base_handler", BaseIntentHandler=_BaseIntentHandler
    )
    _install_idempotency_stub()
    _load_service_module()

    module_name = "odoo.addons.smart_construction_core.handlers.boq_line_patch"
    sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(
        module_name,
        _ROOT / "handlers" / "boq_line_patch.py",
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    setattr(handlers_pkg, "boq_line_patch", module)
    spec.loader.exec_module(module)
    return module


mod = _load_handler_module()


# ---------------------------------------------------------------------------
# 桩环境
# ---------------------------------------------------------------------------


class _RecSet(list):
    """记录集语义：bool()=False（len==0），属性代理到首条。"""

    def __getattr__(self, name):
        if not self:
            raise AttributeError(name)
        return getattr(self[0], name)


class _FakeProject:
    def __init__(self, pid=3, frozen=False, name="演示项目"):
        self.id = pid
        self.display_name = name
        self._frozen = frozen

    def is_boq_frozen(self):
        return self._frozen


class _FakeCompany:
    def __init__(self, cid=1):
        self.id = cid


class _FakeUser:
    def __init__(self, uid=9):
        self.id = uid
        self.company_id = _FakeCompany()


class _FakeCr:
    dbname = "sc_test"

    class _Savepoint:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def savepoint(self):
        return _FakeCr._Savepoint()


class _FakeVersion:
    def __init__(self, vid=5, code="V1", state="draft", project=None, total_amount=0.0):
        self.id = vid
        self.code = code
        self.state = state
        self.project_id = project or _FakeProject()
        self.total_amount = total_amount


class _FakeLine:
    """带联动重算的行桩：write(quantity) 后按 compute 链口径刷新投影字段。"""

    def __init__(self, model, lid, vals=None, version=None, project=None):
        vals = vals or {}
        self._model = model
        self.id = lid
        self.version_id = version
        self.project_id = project or (version.project_id if version else _FakeProject())
        self.code = vals.get("code") or ""
        self.name = vals.get("name") or ""
        self.quantity = float(vals.get("quantity") or 0.0)
        self.price = float(vals.get("price") or 0.0)
        self.qty_done = float(vals.get("qty_done") or 0.0)
        self.has_imported_amount = bool(vals.get("has_imported_amount"))
        self.imported_amount = float(vals.get("imported_amount") or 0.0)
        self.writes = []
        self.fail_write = False
        self._recompute()

    def _recompute(self):
        # 模拟服务端 compute 链：amount（叶子=qty*price，来源合价优先）+
        # qty_remain + version.total_amount（聚合）。
        if self.has_imported_amount:
            self.amount = self.imported_amount
        else:
            self.amount = self.quantity * self.price
        self.qty_remain = self.quantity - self.qty_done
        if self.version_id is not None:
            self.version_id.total_amount = sum(
                line.amount for line in self._model.records
            )

    def write(self, vals):
        self.writes.append(dict(vals))
        if self.fail_write:
            raise RuntimeError("write blocked by orm guard")
        for key, value in (vals or {}).items():
            setattr(self, key, value)
        self._recompute()
        return True


class _FakeLineModel:
    def __init__(self):
        self.records = []
        self._next_id = 100

    def search(self, domain, order=None, limit=None):
        line_id = None
        for term in domain or []:
            if term[0] == "id":
                line_id = term[2]
        matched = [
            line for line in self.records if line_id is None or line.id == line_id
        ]
        return _RecSet(matched)

    def seed(self, lid, code, quantity, price, *, version, qty_done=0.0):
        line = _FakeLine(
            self,
            lid,
            {"code": code, "quantity": quantity, "price": price, "qty_done": qty_done},
            version=version,
            project=version.project_id,
        )
        self.records.append(line)
        line._recompute()
        return line


class _FakeAuditModel:
    def __init__(self):
        self.events = []

    def write_event(self, **kw):
        self.events.append(dict(kw))
        return True


class _FakeEnv:
    def __init__(self, *, lines=None, audit=True, user=None):
        self._models = {
            "project.boq.line": lines or _FakeLineModel(),
        }
        if audit:
            self._models["sc.audit.log"] = _FakeAuditModel()
        self.user = user or _FakeUser()
        self.cr = _FakeCr()

    def get(self, name):
        return self._models.get(name)

    def __getitem__(self, name):
        if name not in self._models:
            raise KeyError(name)
        return self._models[name]

    @property
    def line_model(self):
        return self._models["project.boq.line"]

    @property
    def audit_model(self):
        return self._models.get("sc.audit.log")


def _seeded_env(*, state="draft", frozen=False, quantity=3.0, price=10.0,
                qty_done=0.0, version_id=5):
    project = _FakeProject(frozen=frozen)
    version = _FakeVersion(vid=version_id, state=state, project=project)
    lines = _FakeLineModel()
    line = lines.seed(11, "A", quantity, price, version=version, qty_done=qty_done)
    env = _FakeEnv(lines=lines)
    return env, version, line


def _handler(env, params):
    return mod.BoqLinePatchHandler(env=env, params=params, payload={}, context={})


def _run(env, params):
    return _handler(env, params).handle({"params": params})


class _PatchedClaim:
    """替换 handler 模块级 claim/complete 以注入幂等分支并记录调用。"""

    def __init__(self, mode="claimed", replay_payload=None):
        self.mode = mode
        self.replay_payload = replay_payload
        self.claim_calls = []
        self.complete_calls = []
        self._orig_claim = mod.claim_write_idempotency
        self._orig_complete = mod.complete_write_idempotency

    def __enter__(self):
        tester = self

        def _claim(env, **kw):
            tester.claim_calls.append(kw)
            result = {"mode": tester.mode}
            if tester.replay_payload is not None:
                result["replay_payload"] = tester.replay_payload
                result["replay_entry"] = {"id": 77}
            return result

        def _complete(env, **kw):
            tester.complete_calls.append(kw)
            return {"recorded": True}

        mod.claim_write_idempotency = _claim
        mod.complete_write_idempotency = _complete
        return self

    def __exit__(self, *args):
        mod.claim_write_idempotency = self._orig_claim
        mod.complete_write_idempotency = self._orig_complete
        return False


# ---------------------------------------------------------------------------
# 服务纯函数
# ---------------------------------------------------------------------------


class ServicePureFunctions(unittest.TestCase):
    def test_normalize_quantity(self):
        self.assertIsNone(svc.normalize_quantity(None))
        self.assertIsNone(svc.normalize_quantity("abc"))
        self.assertIsNone(svc.normalize_quantity(float("nan")))
        self.assertIsNone(svc.normalize_quantity(float("inf")))
        self.assertEqual(svc.normalize_quantity("3.5"), 3.5)
        self.assertEqual(svc.normalize_quantity(3.5), 3.5)
        self.assertEqual(svc.normalize_quantity(0), 0.0)
        self.assertEqual(svc.normalize_quantity(True), 1.0)

    def test_quantity_baseline_matches(self):
        self.assertTrue(svc.quantity_baseline_matches(3.0, 3.0))
        self.assertTrue(svc.quantity_baseline_matches("3.0", 3.0))
        # 表示误差容差（round 6 位）
        self.assertTrue(svc.quantity_baseline_matches(3.0000001, 3.0000002))
        self.assertFalse(svc.quantity_baseline_matches(3.0, 3.1))
        self.assertFalse(svc.quantity_baseline_matches(None, 3.0))
        self.assertFalse(svc.quantity_baseline_matches("abc", 3.0))

    def test_qty_below_done(self):
        self.assertTrue(svc.qty_below_done(1.0, 2.0))
        self.assertFalse(svc.qty_below_done(2.0, 2.0))
        self.assertFalse(svc.qty_below_done(3.0, 2.0))
        self.assertTrue(svc.qty_below_done("abc", 2.0))


# ---------------------------------------------------------------------------
# handler：参数与前置门（claim 之前）
# ---------------------------------------------------------------------------


class HandlerParamGates(unittest.TestCase):
    def test_missing_params_no_claim(self):
        env, _version, _line = _seeded_env()
        with _PatchedClaim() as patched:
            for params in (
                {"expected_quantity": 3.0, "new_quantity": 5.0},  # 缺 line_id
                {"line_id": 11, "new_quantity": 5.0},  # 缺 expected
                {"line_id": 11, "expected_quantity": 3.0},  # 缺 new
                {"line_id": 11, "expected_quantity": "abc", "new_quantity": 5.0},
                {"line_id": 11, "expected_quantity": 3.0, "new_quantity": None},
            ):
                result = _run(env, params)
                self.assertFalse(result["ok"])
                self.assertEqual(result["error"]["code"], "MISSING_PARAMS")
            # 缺参在 claim 之前拒绝：不占幂等行
            self.assertEqual(len(patched.claim_calls), 0)

    def test_invalid_quantity_negative(self):
        env, _version, _line = _seeded_env()
        result = _run(env, {"line_id": 11, "expected_quantity": 3.0, "new_quantity": -1.0})
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "INVALID_QUANTITY")

    def test_line_not_found(self):
        env, _version, _line = _seeded_env()
        result = _run(env, {"line_id": 999, "expected_quantity": 3.0, "new_quantity": 5.0})
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "LINE_NOT_FOUND")

    def test_version_not_mutable(self):
        env, _version, _line = _seeded_env(state="published")
        result = _run(env, {"line_id": 11, "expected_quantity": 3.0, "new_quantity": 5.0})
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "VERSION_NOT_MUTABLE")

    def test_boq_frozen(self):
        env, _version, _line = _seeded_env(frozen=True)
        result = _run(env, {"line_id": 11, "expected_quantity": 3.0, "new_quantity": 5.0})
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "BOQ_FROZEN")


# ---------------------------------------------------------------------------
# handler：claim 后的降级路径
# ---------------------------------------------------------------------------


class HandlerClaimGates(unittest.TestCase):
    def test_baseline_mismatch_releases_failed(self):
        env, _version, line = _seeded_env(quantity=3.0)
        with _PatchedClaim() as patched:
            # 客户端基线 5.0，DB 当前 3.0：漂移拒绝
            result = _run(
                env,
                {"line_id": 11, "expected_quantity": 5.0, "new_quantity": 7.0},
            )
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "BASELINE_MISMATCH")
        self.assertEqual(result["error"]["suggested_action"], "reload_and_retry")
        # claim 先于基线比对（重放通道要求），漂移路径须释放幂等行为 failed
        self.assertEqual(len(patched.claim_calls), 1)
        self.assertEqual(len(patched.complete_calls), 1)
        self.assertEqual(patched.complete_calls[0]["status"], "failed")
        # 未发生业务写
        self.assertEqual(line.writes, [])
        self.assertEqual(line.quantity, 3.0)

    def test_qty_below_done(self):
        env, _version, line = _seeded_env(quantity=3.0, qty_done=2.0)
        with _PatchedClaim() as patched:
            result = _run(
                env,
                {"line_id": 11, "expected_quantity": 3.0, "new_quantity": 1.0},
            )
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "QTY_BELOW_DONE")
        self.assertEqual(patched.complete_calls[0]["status"], "failed")
        self.assertEqual(line.writes, [])

    def test_qty_equal_done_allowed(self):
        env, _version, line = _seeded_env(quantity=3.0, qty_done=2.0)
        with _PatchedClaim() as patched:
            result = _run(
                env,
                {"line_id": 11, "expected_quantity": 3.0, "new_quantity": 2.0},
            )
        self.assertTrue(result["ok"])
        self.assertEqual(len(patched.complete_calls), 1)
        self.assertNotEqual(patched.complete_calls[0].get("status"), "failed")


# ---------------------------------------------------------------------------
# handler：成功路径与幂等分支
# ---------------------------------------------------------------------------


class HandlerExecutePaths(unittest.TestCase):
    def test_patch_success_with_recalc_projection(self):
        env, version, line = _seeded_env(quantity=3.0, price=10.0)
        with _PatchedClaim() as patched:
            result = _run(
                env,
                {
                    "line_id": 11,
                    "expected_quantity": 3.0,
                    "new_quantity": 5.0,
                    "request_id": "req-1",
                },
            )
        self.assertTrue(result["ok"])
        data = result["data"]
        self.assertEqual(data["schema"], svc.PATCH_SCHEMA)
        self.assertEqual(data["quantity_before"], 3.0)
        self.assertEqual(data["quantity_after"], 5.0)
        # 服务端权威重算投影：amount=5*10、qty_remain=5、version 汇总联动
        self.assertEqual(data["amount_before"], 30.0)
        self.assertEqual(data["amount_after"], 50.0)
        self.assertEqual(data["qty_remain"], 5.0)
        self.assertEqual(data["version_total_amount"], 50.0)
        # 单字段写入口径：仅 quantity
        self.assertEqual(line.writes, [{"quantity": 5.0}])
        # 幂等键缺省回退 request_id
        self.assertEqual(data["idempotency_key"], "req-1")
        # complete(done) + 审计 before/after 各一
        self.assertEqual(len(patched.complete_calls), 1)
        self.assertNotEqual(patched.complete_calls[0].get("status"), "failed")
        events = env.audit_model.events
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event_code"], svc.EVENT_CODE)
        self.assertEqual(events[0]["model"], "project.boq.line")
        self.assertEqual(events[0]["res_id"], 11)
        self.assertEqual(events[0]["before"]["quantity_before"], 3.0)
        self.assertEqual(events[0]["after"]["quantity_after"], 5.0)

    def test_replay_returns_first_result_without_rewrite(self):
        env, _version, line = _seeded_env(quantity=3.0)
        replay_payload = {
            "schema": svc.PATCH_SCHEMA,
            "line_id": 11,
            "quantity_before": 3.0,
            "quantity_after": 5.0,
            "success": True,
        }
        with _PatchedClaim(mode="replay", replay_payload=replay_payload) as patched:
            result = _run(
                env,
                {"line_id": 11, "expected_quantity": 3.0, "new_quantity": 5.0},
            )
        self.assertTrue(result["ok"])
        data = result["data"]
        # 重放信封：返回首次结果，且不重复写、不落新审计
        self.assertTrue(data.get("idempotent_replay"))
        self.assertEqual(data.get("quantity_after"), 5.0)
        self.assertEqual(line.writes, [])
        self.assertEqual(len(patched.complete_calls), 0)
        self.assertEqual(env.audit_model.events, [])

    def test_conflict_returns_409_envelope(self):
        env, _version, line = _seeded_env(quantity=3.0)
        with _PatchedClaim(mode="conflict"):
            result = _run(
                env,
                {"line_id": 11, "expected_quantity": 3.0, "new_quantity": 5.0},
            )
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "IDEMPOTENCY_CONFLICT")
        self.assertEqual(line.writes, [])

    def test_in_flight_returns_envelope(self):
        env, _version, line = _seeded_env(quantity=3.0)
        with _PatchedClaim(mode="in_flight"):
            result = _run(
                env,
                {"line_id": 11, "expected_quantity": 3.0, "new_quantity": 5.0},
            )
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "IDEMPOTENCY_IN_FLIGHT")
        self.assertEqual(line.writes, [])

    def test_patch_error_releases_failed(self):
        env, _version, line = _seeded_env(quantity=3.0)
        line.fail_write = True
        with _PatchedClaim() as patched:
            result = _run(
                env,
                {"line_id": 11, "expected_quantity": 3.0, "new_quantity": 5.0},
            )
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "PATCH_ERROR")
        self.assertEqual(result["error"]["suggested_action"], "retry")
        # 失败路径：幂等行落 failed（允许接管重试），无审计落档
        self.assertEqual(len(patched.complete_calls), 1)
        self.assertEqual(patched.complete_calls[0]["status"], "failed")
        self.assertEqual(env.audit_model.events, [])

    def test_audit_model_absent_does_not_break(self):
        env, _version, line = _seeded_env(quantity=3.0)
        env._models.pop("sc.audit.log", None)
        with _PatchedClaim():
            result = _run(
                env,
                {"line_id": 11, "expected_quantity": 3.0, "new_quantity": 5.0},
            )
        self.assertTrue(result["ok"])
        self.assertEqual(line.quantity, 5.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
