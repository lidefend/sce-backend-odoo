# -*- coding: utf-8 -*-
"""BOQ 危险导入 handler 单测（G7.1，ADR-004 决策 4）。

桩加载模式：不依赖 Odoo 数据库与真实 openpyxl，验证
- 服务纯函数：flag_enabled / normalize_mode / summarize_impact（replace/
  update/歧义）/ build_confirm_token 稳定性与漂移敏感性
- preview：kill switch 关闭→CAPABILITY_DISABLED（fail-closed，参数缺失同）；
  缺参→MISSING_PARAMS；非法 mode→UNSUPPORTED_MODE；版本不可访问→
  VERSION_NOT_FOUND；非 draft/validated→VERSION_NOT_MUTABLE；冻结项目→
  BOQ_FROZEN；解析异常/空→PARSE_ERROR/PARSE_EMPTY；update 歧义编码→
  AMBIGUOUS_CODES；干跑成功→影响摘要 + confirm_token 且无业务写
- execute：缺 confirm_token→MISSING_PARAMS；令牌漂移→CONFIRM_TOKEN_MISMATCH；
  幂等 conflict/in_flight→409 信封；replay→重放信封；replace 成功→
  unlink+重建+batch 证据+audit 落档+complete(done)；update 成功→匹配行
  write+新码创建；执行异常→savepoint 回滚语义+complete(failed)+
  IMPORT_ERROR
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
    module = _install_module(
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
    return module


def _load_service_module():
    _install_module("odoo", fields=_FakeDatetime)
    _install_module("odoo.addons")
    _install_module("odoo.addons.smart_construction_core")
    services_pkg = _install_module("odoo.addons.smart_construction_core.services")
    name = "odoo.addons.smart_construction_core.services.boq_dangerous_import_service"
    sys.modules.pop(name, None)
    spec = importlib.util.spec_from_file_location(
        name, _ROOT / "services" / "boq_dangerous_import_service.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    setattr(services_pkg, "boq_dangerous_import_service", module)
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

    module_name = "odoo.addons.smart_construction_core.handlers.boq_dangerous_import"
    sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(
        module_name,
        _ROOT / "handlers" / "boq_dangerous_import.py",
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    setattr(handlers_pkg, "boq_dangerous_import", module)
    spec.loader.exec_module(module)
    return module


mod = _load_handler_module()


# ---------------------------------------------------------------------------
# 桩环境
# ---------------------------------------------------------------------------


class _RecSet(list):
    """空记录集语义：bool()=False（len==0），属性代理到首条。"""

    def __getattr__(self, name):
        if not self:
            raise AttributeError(name)
        return getattr(self[0], name)

    def unlink(self):
        # Odoo 记录集 unlink() 会删除全部成员，不能只代理首条。
        ok = True
        for record in list(self):
            ok = bool(record.unlink()) and ok
        return ok


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


class _FakeConfigParameter:
    def __init__(self, params=None):
        self._params = dict(params or {})

    def sudo(self):
        return self

    def get_param(self, key, default=None):
        return self._params.get(key, default)


class _FakeVersion:
    def __init__(self, vid=5, code="V1", state="draft", project=None):
        self.id = vid
        self.code = code
        self.state = state
        self.project_id = project or _FakeProject()


class _FakeVersionModel:
    def __init__(self, versions=None):
        self._versions = list(versions or [])

    def search(self, domain, limit=None, order=None):
        matched = list(self._versions)
        for term in domain or []:
            field, _op, value = term
            if field == "id":
                matched = [v for v in matched if v.id == value]
            elif field == "project_id":
                matched = [v for v in matched if v.project_id.id == value]
        if limit:
            matched = matched[:limit]
        return _RecSet(matched)


class _FakeLine:
    def __init__(self, model, lid, vals=None, version_id=5):
        vals = vals or {}
        self._model = model
        self.id = lid
        self.version_id = version_id
        self.code = vals.get("code") or ""
        self.name = vals.get("name") or ""
        self.quantity = vals.get("quantity") or 0.0
        self.price = vals.get("price") or 0.0
        self.imported_amount = vals.get("imported_amount") or 0.0
        self.has_imported_amount = bool(vals.get("has_imported_amount"))
        self.writes = []
        self.unlinked = False
        self.fail_unlink = False

    def write(self, vals):
        self.writes.append(dict(vals))
        for key, value in (vals or {}).items():
            setattr(self, key, value)
        return True

    def unlink(self):
        if self.fail_unlink:
            raise RuntimeError("unlink blocked by state guard")
        self.unlinked = True
        if self in self._model.records:
            self._model.records.remove(self)
        return True


class _FakeLineModel:
    def __init__(self, lines=None):
        self.records = list(lines or [])
        self._next_id = 100

    def search(self, domain, order=None, limit=None):
        version_id = None
        for term in domain or []:
            if term[0] == "version_id":
                version_id = term[2]
        matched = [
            line for line in self.records if version_id is None or line.version_id == version_id
        ]
        return _RecSet(matched)

    def create(self, vals_list):
        if isinstance(vals_list, dict):
            vals_list = [vals_list]
        created = []
        for vals in vals_list:
            line = _FakeLine(self, self._next_id, vals, version_id=vals.get("version_id"))
            self._next_id += 1
            self.records.append(line)
            created.append(line)
        return _RecSet(created)

    def seed(self, lid, code, quantity, price, version_id=5):
        line = _FakeLine(
            self,
            lid,
            {"code": code, "quantity": quantity, "price": price},
            version_id=version_id,
        )
        self.records.append(line)
        return line


class _FakeBatch:
    def __init__(self, bid, vals=None):
        self.id = bid
        self.vals = dict(vals or {})
        self.writes = []

    def write(self, vals):
        self.writes.append(dict(vals))
        self.vals.update(vals)
        return True


class _FakeBatchModel:
    def __init__(self):
        self.created = []
        self._next_id = 500

    def create(self, vals):
        batch = _FakeBatch(self._next_id, vals)
        self._next_id += 1
        self.created.append(batch)
        return batch


class _FakeWizard:
    def __init__(self, model, vals, rows=None, error=None):
        self._model = model
        self.id = model._next_id
        model._next_id += 1
        self.project_id = vals.get("project_id")
        self.file = vals.get("file")
        self.filename = vals.get("filename")
        self.boq_category = vals.get("boq_category") or "boq"
        self._rows = rows if rows is not None else []
        self._error = error
        self.contexts = []
        model.instances.append(self)

    def with_context(self, **kw):
        self.contexts.append(kw)
        return self

    def _parse_file(self, include_details=False):
        if self._error is not None:
            raise self._error
        return list(self._rows), set(), 0, {}

    def _create_with_hierarchy(self, model, vals_list):
        model.create(vals_list)
        return len(vals_list)

    def _batch_create(self, model, vals_list):
        model.create(vals_list)
        return len(vals_list)


class _FakeWizardModel:
    def __init__(self, rows=None, error=None):
        self.instances = []
        self._next_id = 1000
        self._rows = rows or []
        self._error = error

    def create(self, vals):
        return _FakeWizard(self, vals, rows=self._rows, error=self._error)


class _FakeAuditModel:
    def __init__(self):
        self.events = []

    def write_event(self, **kw):
        self.events.append(dict(kw))
        return True


class _FakeEnv:
    def __init__(self, *, params=None, versions=None, lines=None, wizard=None,
                 batches=None, audit=True, user=None):
        self._models = {
            "ir.config_parameter": _FakeConfigParameter(params or {}),
            "project.boq.version": _FakeVersionModel(versions),
            "project.boq.line": lines or _FakeLineModel(),
            "project.boq.import.wizard": wizard or _FakeWizardModel(),
            "project.boq.import.batch": batches or _FakeBatchModel(),
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

    # 便捷访问
    @property
    def line_model(self):
        return self._models["project.boq.line"]

    @property
    def wizard_model(self):
        return self._models["project.boq.import.wizard"]

    @property
    def batch_model(self):
        return self._models["project.boq.import.batch"]

    @property
    def audit_model(self):
        return self._models.get("sc.audit.log")


def _file_payload(rows):
    import base64 as _b64

    return _b64.b64encode(("stub-file-%d-rows" % len(rows)).encode("utf-8")).decode("ascii")


def _item_row(code, quantity=1.0, price=10.0, **extra):
    row = {
        "code": code,
        "name": "行 %s" % code,
        "line_type": "item",
        "boq_category": "boq",
        "quantity": quantity,
        "price": price,
        "imported_amount": 0.0,
        "has_imported_amount": False,
    }
    row.update(extra)
    return row


def _seeded_env(rows, *, mode="replace", flag="true", state="draft", version_id=5,
                wizard=None):
    version = _FakeVersion(vid=version_id, state=state)
    lines = _FakeLineModel()
    lines.seed(11, "A", 1.0, 10.0, version_id=version_id)
    lines.seed(12, "B", 2.0, 5.0, version_id=version_id)
    env = _FakeEnv(
        params={svc.FLAG_KEY: flag},
        versions=[version],
        lines=lines,
        wizard=wizard or _FakeWizardModel(rows=rows),
    )
    return env, version


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
    def test_flag_enabled_fail_closed(self):
        self.assertTrue(svc.flag_enabled("true"))
        self.assertTrue(svc.flag_enabled("True"))
        self.assertTrue(svc.flag_enabled("1"))
        self.assertTrue(svc.flag_enabled("yes"))
        self.assertTrue(svc.flag_enabled("on"))
        self.assertFalse(svc.flag_enabled("false"))
        self.assertFalse(svc.flag_enabled(""))
        self.assertFalse(svc.flag_enabled(None))
        self.assertFalse(svc.flag_enabled("garbage"))

    def test_normalize_mode(self):
        self.assertEqual(svc.normalize_mode("replace"), "replace")
        self.assertEqual(svc.normalize_mode(" UPDATE "), "update")
        self.assertEqual(svc.normalize_mode("delete"), "")
        self.assertEqual(svc.normalize_mode(None), "")

    def test_summarize_impact_replace(self):
        existing = [
            {"id": 11, "code": "A", "quantity": 1.0, "price": 10.0,
             "imported_amount": 0.0, "has_imported_amount": False},
            {"id": 12, "code": "B", "quantity": 2.0, "price": 5.0,
             "imported_amount": 0.0, "has_imported_amount": False},
        ]
        rows = [_item_row("A", 3.0, 2.0), _item_row("C", 1.0, 7.0)]
        summary, ambiguous = svc.summarize_impact("replace", existing, rows)
        self.assertEqual(ambiguous, [])
        self.assertEqual(summary["existing_line_count"], 2)
        self.assertEqual(summary["lines_to_delete"], 2)
        self.assertEqual(summary["lines_to_create"], 2)
        self.assertEqual(summary["amount_before"], 20.0)
        self.assertEqual(summary["amount_after"], 13.0)
        self.assertEqual(summary["amount_delta"], -7.0)

    def test_summarize_impact_update(self):
        existing = [
            {"id": 11, "code": "A", "quantity": 1.0, "price": 10.0,
             "imported_amount": 0.0, "has_imported_amount": False},
            {"id": 12, "code": "B", "quantity": 2.0, "price": 5.0,
             "imported_amount": 0.0, "has_imported_amount": False},
        ]
        rows = [_item_row("A", 2.0, 5.0), _item_row("C", 1.0, 7.0)]
        summary, ambiguous = svc.summarize_impact("update", existing, rows)
        self.assertEqual(ambiguous, [])
        self.assertEqual(summary["lines_to_update"], 1)
        self.assertEqual(summary["lines_to_create"], 1)
        self.assertEqual(summary["lines_to_keep"], 1)
        # A 更新为 2*5=10；B 保持 10；C 新增 7
        self.assertEqual(summary["amount_before"], 20.0)
        self.assertEqual(summary["amount_after"], 27.0)
        self.assertEqual(summary["amount_delta"], 7.0)

    def test_summarize_impact_update_ambiguous_fail_closed(self):
        existing = [
            {"id": 11, "code": "A", "quantity": 1.0, "price": 10.0,
             "imported_amount": 0.0, "has_imported_amount": False},
            {"id": 12, "code": "A", "quantity": 2.0, "price": 5.0,
             "imported_amount": 0.0, "has_imported_amount": False},
        ]
        rows = [_item_row("A", 3.0, 2.0)]
        summary, ambiguous = svc.summarize_impact("update", existing, rows)
        self.assertEqual(ambiguous, ["A"])
        self.assertEqual(summary.get("ambiguous_codes"), ["A"])

    def test_confirm_token_deterministic_and_drift_sensitive(self):
        summary = {"mode": "replace", "amount_before": 1.0}
        kwargs = dict(
            version_id=5, mode="replace", boq_category="boq",
            file_digest="d1", summary=summary, user_id=9, company_id=1,
        )
        token = svc.build_confirm_token(**kwargs)
        self.assertEqual(token, svc.build_confirm_token(**kwargs))
        drifted = dict(kwargs, file_digest="d2")
        self.assertNotEqual(token, svc.build_confirm_token(**drifted))
        drifted = dict(kwargs, summary={"mode": "replace", "amount_before": 2.0})
        self.assertNotEqual(token, svc.build_confirm_token(**drifted))
        drifted = dict(kwargs, user_id=10)
        self.assertNotEqual(token, svc.build_confirm_token(**drifted))

    def test_confirm_token_matches(self):
        self.assertTrue(svc.confirm_token_matches("abc", "abc"))
        self.assertFalse(svc.confirm_token_matches("abc", "abd"))
        self.assertFalse(svc.confirm_token_matches("", ""))
        self.assertFalse(svc.confirm_token_matches("abc", ""))

    def test_build_audit_payload_shape(self):
        payload = svc.build_audit_payload(
            mode="replace", version_id=5, project_id=3, file_digest="d1",
            idempotency_key="k1", idempotency_fingerprint="f1", trace_id="t1",
            summary_before={"a": 1}, summary_after={"b": 2},
            result={"success": True, "lines_deleted": 2}, duration_ms=12,
        )
        self.assertEqual(payload["mode"], "replace")
        self.assertEqual(payload["before"], {"a": 1})
        self.assertEqual(payload["after"], {"b": 2})
        self.assertEqual(payload["result_summary"]["lines_deleted"], 2)
        self.assertEqual(payload["idempotency_key"], "k1")


# ---------------------------------------------------------------------------
# preview handler
# ---------------------------------------------------------------------------


class PreviewHandlerTests(unittest.TestCase):
    def _handler(self, env, params):
        return mod.BoqDangerousImportPreviewHandler(env=env, params=params)

    def test_flag_off_fail_closed(self):
        env, _ = _seeded_env([_item_row("A")], flag="false")
        resp = self._handler(env, {"version_id": 5, "mode": "replace", "file": "xxx"}).handle()
        self.assertFalse(resp["ok"])
        self.assertEqual(resp["error"]["code"], "CAPABILITY_DISABLED")

    def test_flag_param_missing_fail_closed(self):
        rows = [_item_row("A")]
        env = _FakeEnv(
            params={},
            versions=[_FakeVersion()],
            lines=_FakeLineModel(),
            wizard=_FakeWizardModel(rows=rows),
        )
        resp = self._handler(env, {"version_id": 5, "mode": "replace", "file": "xxx"}).handle()
        self.assertFalse(resp["ok"])
        self.assertEqual(resp["error"]["code"], "CAPABILITY_DISABLED")

    def test_missing_params(self):
        env, _ = _seeded_env([_item_row("A")])
        resp = self._handler(env, {"mode": "replace", "file": "xxx"}).handle()
        self.assertEqual(resp["error"]["code"], "MISSING_PARAMS")
        resp = self._handler(env, {"version_id": 5, "mode": "replace"}).handle()
        self.assertEqual(resp["error"]["code"], "MISSING_PARAMS")

    def test_unsupported_mode(self):
        env, _ = _seeded_env([_item_row("A")])
        resp = self._handler(
            env, {"version_id": 5, "mode": "delete", "file": "xxx"}
        ).handle()
        self.assertEqual(resp["error"]["code"], "UNSUPPORTED_MODE")

    def test_version_not_found(self):
        env, _ = _seeded_env([_item_row("A")])
        resp = self._handler(
            env, {"version_id": 999, "mode": "replace", "file": "xxx"}
        ).handle()
        self.assertEqual(resp["error"]["code"], "VERSION_NOT_FOUND")

    def test_version_not_mutable(self):
        env, _ = _seeded_env([_item_row("A")], state="published")
        resp = self._handler(
            env, {"version_id": 5, "mode": "replace", "file": "xxx"}
        ).handle()
        self.assertEqual(resp["error"]["code"], "VERSION_NOT_MUTABLE")

    def test_boq_frozen(self):
        rows = [_item_row("A")]
        version = _FakeVersion(project=_FakeProject(frozen=True))
        env = _FakeEnv(
            params={svc.FLAG_KEY: "true"},
            versions=[version],
            lines=_FakeLineModel(),
            wizard=_FakeWizardModel(rows=rows),
        )
        resp = self._handler(
            env, {"version_id": 5, "mode": "replace", "file": "xxx"}
        ).handle()
        self.assertEqual(resp["error"]["code"], "BOQ_FROZEN")

    def test_parse_error(self):
        env, _ = _seeded_env([], wizard=_FakeWizardModel(error=RuntimeError("bad xlsx")))
        resp = self._handler(
            env, {"version_id": 5, "mode": "replace", "file": "xxx"}
        ).handle()
        self.assertEqual(resp["error"]["code"], "PARSE_ERROR")

    def test_parse_empty(self):
        env, _ = _seeded_env([])
        resp = self._handler(
            env, {"version_id": 5, "mode": "replace", "file": "xxx"}
        ).handle()
        self.assertEqual(resp["error"]["code"], "PARSE_EMPTY")

    def test_update_ambiguous_codes(self):
        rows = [_item_row("A", 3.0, 2.0)]
        lines = _FakeLineModel()
        lines.seed(11, "A", 1.0, 10.0)
        lines.seed(12, "A", 2.0, 5.0)
        env = _FakeEnv(
            params={svc.FLAG_KEY: "true"},
            versions=[_FakeVersion()],
            lines=lines,
            wizard=_FakeWizardModel(rows=rows),
        )
        resp = self._handler(
            env,
            {"version_id": 5, "mode": "update", "file": _file_payload(rows),
             "filename": "boq.xlsx"},
        ).handle()
        self.assertEqual(resp["error"]["code"], "AMBIGUOUS_CODES")

    def test_preview_happy_path_no_business_write(self):
        rows = [_item_row("A", 3.0, 2.0), _item_row("C", 1.0, 7.0)]
        env, version = _seeded_env(rows)
        resp = self._handler(
            env,
            {"version_id": 5, "mode": "replace", "file": _file_payload(rows),
             "filename": "boq.xlsx"},
        ).handle()
        self.assertTrue(resp["ok"])
        data = resp["data"]
        self.assertTrue(data["dangerous"])
        self.assertTrue(data["readonly"])
        self.assertEqual(data["summary"]["lines_to_delete"], 2)
        self.assertEqual(data["summary"]["lines_to_create"], 2)
        self.assertTrue(data["confirm_token"])
        self.assertEqual(data["execute_intent"], "project.boq.import.dangerous.execute")
        # 干跑不产生业务写：无 batch、无行变更、无审计
        self.assertEqual(env.batch_model.created, [])
        self.assertEqual(len(env.line_model.records), 2)
        for line in env.line_model.records:
            self.assertEqual(line.writes, [])
            self.assertFalse(line.unlinked)
        # 预检解析走 preflight 上下文（不创建计量单位）
        wizard = env.wizard_model.instances[-1]
        self.assertTrue(wizard.contexts)
        self.assertTrue(all("boq_import_preflight" in ctx for ctx in wizard.contexts))


# ---------------------------------------------------------------------------
# execute handler
# ---------------------------------------------------------------------------


class ExecuteHandlerTests(unittest.TestCase):
    def _handler(self, env, params):
        return mod.BoqDangerousImportExecuteHandler(env=env, params=params)

    def _base_params(self, rows, mode="replace", **extra):
        params = {
            "version_id": 5,
            "mode": mode,
            "file": _file_payload(rows),
            "filename": "boq.xlsx",
            "confirm_token": "token",
            "idempotency_key": "danger-key-1",
            "request_id": "boqdi_req_1",
        }
        params.update(extra)
        return params

    def test_missing_confirm_token(self):
        rows = [_item_row("A")]
        env, _ = _seeded_env(rows)
        params = self._base_params(rows)
        params.pop("confirm_token")
        with _PatchedClaim():
            resp = self._handler(env, params).handle()
        self.assertEqual(resp["error"]["code"], "MISSING_PARAMS")

    def test_confirm_token_mismatch(self):
        rows = [_item_row("A")]
        env, _ = _seeded_env(rows)
        with _PatchedClaim() as patched:
            resp = self._handler(env, self._base_params(rows)).handle()
        self.assertEqual(resp["error"]["code"], "CONFIRM_TOKEN_MISMATCH")
        # claim 先于令牌重算（重放通道要求），漂移路径须释放幂等行为 failed
        self.assertEqual(len(patched.claim_calls), 1)
        self.assertEqual(len(patched.complete_calls), 1)
        self.assertEqual(patched.complete_calls[0]["status"], "failed")
        # 令牌不匹配不得写业务数据
        self.assertEqual(env.batch_model.created, [])

    def test_idempotency_conflict(self):
        rows = [_item_row("A", 3.0, 2.0)]
        env, _ = _seeded_env(rows)
        # 先干跑拿正确令牌
        preview = mod.BoqDangerousImportPreviewHandler(
            env=env, params={}
        ).handle({"params": self._base_params(rows)})
        self.assertTrue(preview["ok"])
        params = self._base_params(rows)
        params["confirm_token"] = preview["data"]["confirm_token"]
        with _PatchedClaim(mode="conflict") as patched:
            resp = self._handler(env, params).handle()
        self.assertFalse(resp["ok"])
        self.assertEqual(resp["error"]["code"], "IDEMPOTENCY_CONFLICT")
        self.assertEqual(len(patched.claim_calls), 1)
        self.assertEqual(patched.claim_calls[0]["event_code"], svc.EVENT_CODE)
        self.assertEqual(env.batch_model.created, [])

    def test_idempotency_in_flight(self):
        rows = [_item_row("A", 3.0, 2.0)]
        env, _ = _seeded_env(rows)
        preview = mod.BoqDangerousImportPreviewHandler(
            env=env, params={}
        ).handle({"params": self._base_params(rows)})
        params = self._base_params(rows)
        params["confirm_token"] = preview["data"]["confirm_token"]
        with _PatchedClaim(mode="in_flight"):
            resp = self._handler(env, params).handle()
        self.assertFalse(resp["ok"])
        self.assertEqual(resp["error"]["code"], "IDEMPOTENCY_IN_FLIGHT")

    def test_idempotent_replay(self):
        rows = [_item_row("A", 3.0, 2.0)]
        env, _ = _seeded_env(rows)
        preview = mod.BoqDangerousImportPreviewHandler(
            env=env, params={}
        ).handle({"params": self._base_params(rows)})
        params = self._base_params(rows)
        params["confirm_token"] = preview["data"]["confirm_token"]
        replay_payload = {"schema": svc.DANGEROUS_IMPORT_SCHEMA, "success": True,
                          "lines_deleted": 2}
        with _PatchedClaim(mode="replay", replay_payload=replay_payload) as patched:
            resp = self._handler(env, params).handle()
        self.assertTrue(resp["ok"])
        self.assertTrue(resp["data"]["idempotent_replay"])
        # 重放不重复执行业务写
        self.assertEqual(env.batch_model.created, [])
        self.assertEqual(patched.complete_calls, [])
        for line in env.line_model.records:
            self.assertFalse(line.unlinked)

    def test_execute_replace_success(self):
        rows = [_item_row("A", 3.0, 2.0), _item_row("C", 1.0, 7.0)]
        env, version = _seeded_env(rows)
        preview = mod.BoqDangerousImportPreviewHandler(
            env=env, params={}
        ).handle({"params": self._base_params(rows)})
        self.assertTrue(preview["ok"])
        params = self._base_params(rows)
        params["confirm_token"] = preview["data"]["confirm_token"]
        old_line_ids = {line.id for line in env.line_model.records}

        with _PatchedClaim() as patched:
            resp = self._handler(env, params).handle()
        self.assertTrue(resp["ok"])
        data = resp["data"]
        self.assertTrue(data["dangerous"])
        self.assertTrue(data["success"])
        self.assertEqual(data["lines_deleted"], 2)
        self.assertEqual(data["lines_created"], 2)
        self.assertEqual(data["summary_after"]["amount_after"], 13.0)
        self.assertTrue(data["batch_id"] > 0)

        # 旧行全部删除、新行全部带版本与批次
        self.assertTrue(all(line.unlinked for line in env.line_model.records if line.id in old_line_ids))
        new_lines = [line for line in env.line_model.records if line.id not in old_line_ids]
        self.assertEqual(len(new_lines), 2)
        self.assertTrue(all(line.version_id == 5 for line in new_lines))
        # 批次证据：dangerous 标记 + 前后摘要 + imported 终态（经 write 收尾）
        batch = env.batch_model.created[0]
        self.assertEqual(batch.vals.get("state"), "imported")
        self.assertTrue(any(w.get("state") == "imported" for w in batch.writes))
        self.assertTrue(batch.vals["preview_payload"]["dangerous"])
        self.assertEqual(batch.vals["preview_payload"]["mode"], "replace")
        # 幂等收尾：成功路径不显式传 status（由 complete helper 默认置 done），
        # 失败路径才显式传 failed（见 test_execute_import_error_rollback_semantics）
        self.assertEqual(len(patched.complete_calls), 1)
        self.assertNotEqual(patched.complete_calls[0].get("status"), "failed")
        self.assertEqual(patched.complete_calls[0]["result"]["success"], True)
        events = env.audit_model.events
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event_code"], svc.EVENT_CODE)
        self.assertEqual(events[0]["action"], "replace")
        self.assertEqual(events[0]["res_id"], version.id)

    def test_execute_update_success(self):
        rows = [_item_row("A", 2.0, 5.0), _item_row("C", 1.0, 7.0)]
        env, version = _seeded_env(rows)
        preview = mod.BoqDangerousImportPreviewHandler(
            env=env, params={}
        ).handle({"params": self._base_params(rows, mode="update")})
        self.assertTrue(preview["ok"])
        self.assertEqual(preview["data"]["summary"]["lines_to_update"], 1)
        params = self._base_params(rows, mode="update")
        params["confirm_token"] = preview["data"]["confirm_token"]
        old_lines = {line.id: line for line in list(env.line_model.records)}

        with _PatchedClaim() as patched:
            resp = self._handler(env, params).handle()
        self.assertTrue(resp["ok"])
        data = resp["data"]
        self.assertEqual(data["mode"], "update")
        self.assertEqual(data["lines_updated"], 1)
        self.assertEqual(data["lines_created"], 1)
        self.assertEqual(data["summary_after"]["amount_after"], 27.0)

        # A 行被更新（write 而非删除重建），B 行保持原样
        line_a = old_lines[11]
        self.assertFalse(line_a.unlinked)
        self.assertEqual(len(line_a.writes), 1)
        self.assertEqual(line_a.quantity, 2.0)
        self.assertEqual(line_a.price, 5.0)
        line_b = old_lines[12]
        self.assertEqual(line_b.writes, [])
        new_lines = [
            line for line in env.line_model.records
            if line.id not in old_lines and not line.unlinked
        ]
        self.assertEqual(len(new_lines), 1)
        self.assertEqual(new_lines[0].code, "C")
        self.assertEqual(len(patched.complete_calls), 1)

    def test_execute_import_error_rollback_semantics(self):
        rows = [_item_row("A", 3.0, 2.0)]
        env, _ = _seeded_env(rows)
        preview = mod.BoqDangerousImportPreviewHandler(
            env=env, params={}
        ).handle({"params": self._base_params(rows)})
        params = self._base_params(rows)
        params["confirm_token"] = preview["data"]["confirm_token"]
        # 注入 unlink 失败（模拟 ORM 状态守卫拦截）
        for line in env.line_model.records:
            line.fail_unlink = True

        with _PatchedClaim() as patched:
            resp = self._handler(env, params).handle()
        self.assertFalse(resp["ok"])
        self.assertEqual(resp["error"]["code"], "IMPORT_ERROR")
        # 幂等行落 failed（允许接管重试）
        self.assertEqual(len(patched.complete_calls), 1)
        self.assertEqual(patched.complete_calls[0]["status"], "failed")
        # 审计不落档（业务写未发生）
        self.assertEqual(env.audit_model.events, [])

    def test_execute_flag_off(self):
        rows = [_item_row("A")]
        env, _ = _seeded_env(rows, flag="false")
        with _PatchedClaim() as patched:
            resp = self._handler(env, self._base_params(rows)).handle()
        self.assertEqual(resp["error"]["code"], "CAPABILITY_DISABLED")
        self.assertEqual(patched.claim_calls, [])

    def test_execute_version_not_mutable(self):
        rows = [_item_row("A")]
        env, _ = _seeded_env(rows, state="published")
        with _PatchedClaim() as patched:
            resp = self._handler(env, self._base_params(rows)).handle()
        self.assertEqual(resp["error"]["code"], "VERSION_NOT_MUTABLE")
        self.assertEqual(patched.claim_calls, [])


if __name__ == "__main__":
    unittest.main()
