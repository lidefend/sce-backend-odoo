# -*- coding: utf-8 -*-
"""项目概况受限富文本 patch handler 单测（G7.4 首切片，ADR-006 批准路径）。

桩加载模式：不依赖 Odoo 数据库，验证
- 服务纯函数：sanitize_overview_html（白名单接线 / nh3 缺失 fail-closed）/
  overview_digest / baseline_matches / content_over_limit / flag_enabled
- handler：kill switch 关→CAPABILITY_DISABLED（fail-closed）；缺参→
  MISSING_PARAMS；超长→CONTENT_TOO_LONG（claim 前不占幂等行）；
  nh3 缺失→CAPABILITY_DISABLED（净化通道关闭）；项目不存在→
  PROJECT_NOT_FOUND；摘要基线漂移→BASELINE_MISMATCH（claim 后幂等行落
  failed）；成功→write(overview_html=净化后) + 摘要/长度投影 + complete(done)
  + audit before/after（摘要不落全文）；replay→重放信封（无重复写）；
  conflict/in_flight→409 信封；执行异常→PATCH_ERROR + complete(failed)。

nh3 以假模块注入（真 nh3 行为已在 dev 容器实测：script/onclick 剥除、
javascript: scheme 剥除、http/https/mailto 保留、img/iframe 剥除、
style 剥除——见 G7_LAUNCH_SCOPING.md §15）。
"""
import importlib.util
import sys
import types
import unittest
from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# 假 nh3（记录白名单入参；可选内容变换以验证 sanitized_input_changed）
# ---------------------------------------------------------------------------


class _FakeNh3:
    last_kwargs = None

    @staticmethod
    def clean(text, **kwargs):
        _FakeNh3.last_kwargs = dict(kwargs)
        transform = kwargs.get("_transform")
        if transform:
            return transform(text)
        return text


def _install_fake_nh3(transform=None):
    module = types.ModuleType("nh3")

    def _clean(text, **kwargs):
        if transform is not None:
            return transform(text)
        return text

    module.clean = _clean
    module.__FakeNh3__ = _FakeNh3
    sys.modules["nh3"] = module
    return module


# ---------------------------------------------------------------------------
# 桩环境（同 test_boq_line_patch_handler 模式）
# ---------------------------------------------------------------------------


def _install_module(name, **attrs):
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


import datetime as _dt


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
    name = "odoo.addons.smart_construction_core.services.overview_rich_text_patch_service"
    sys.modules.pop(name, None)
    spec = importlib.util.spec_from_file_location(
        name, _ROOT / "services" / "overview_rich_text_patch_service.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    setattr(services_pkg, "overview_rich_text_patch_service", module)
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

    module_name = "odoo.addons.smart_construction_core.handlers.overview_rich_text_patch"
    sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(
        module_name,
        _ROOT / "handlers" / "overview_rich_text_patch.py",
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    setattr(handlers_pkg, "overview_rich_text_patch", module)
    spec.loader.exec_module(module)
    return module


mod = _load_handler_module()


# ---------------------------------------------------------------------------
# 假记录集 / 假模型
# ---------------------------------------------------------------------------


class _RecSet(list):
    def __getattr__(self, name):
        if not self:
            raise AttributeError(name)
        return getattr(self[0], name)


class _FakeProject:
    def __init__(self, pid=3, overview_html="", name="演示项目"):
        self.id = pid
        self.display_name = name
        self.overview_html = overview_html
        self.writes = []
        self.fail_write = False

    def write(self, vals):
        self.writes.append(dict(vals))
        if self.fail_write:
            raise RuntimeError("write blocked by orm guard")
        for key, value in (vals or {}).items():
            setattr(self, key, value)
        return True


class _FakeProjectModel:
    def __init__(self, records=None):
        self.records = list(records or [])

    def search(self, domain, order=None, limit=None):
        project_id = None
        for term in domain or []:
            if term[0] == "id":
                project_id = term[2]
        matched = [
            project
            for project in self.records
            if project_id is None or project.id == project_id
        ]
        return _RecSet(matched)


class _FakeParamModel:
    def __init__(self, params=None):
        self.params = dict(params or {})

    def sudo(self):
        return self

    def get_param(self, key, default=None):
        return self.params.get(key, default)


class _FakeAuditModel:
    def __init__(self):
        self.events = []

    def write_event(self, **kw):
        self.events.append(dict(kw))
        return True


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


class _FakeEnv:
    def __init__(self, *, projects=None, params=None, audit=True, user=None):
        self._models = {
            "project.project": projects or _FakeProjectModel(),
        }
        if params is not None:
            self._models["ir.config_parameter"] = _FakeParamModel(params)
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
    def project_model(self):
        return self._models["project.project"]

    @property
    def audit_model(self):
        return self._models.get("sc.audit.log")


def _seeded_env(*, overview_html="", flag=True, audit=True):
    project = _FakeProject(pid=3, overview_html=overview_html)
    env = _FakeEnv(
        projects=_FakeProjectModel([project]),
        params={svc.FLAG_KEY: "true"} if flag else {},
        audit=audit,
    )
    return env, project


def _handler(env, params):
    return mod.OverviewRichTextPatchHandler(env=env, params=params, payload={}, context={})


def _run(env, params):
    return _handler(env, params).handle({"params": params})


def _base_params(**overrides):
    params = {
        "project_id": 3,
        "expected_overview_digest": "deadbeefdeadbeef",
        "new_overview_html": "<p>新的概况</p>",
        "idempotency_key": "ovrt_test_key",
    }
    params.update(overrides)
    return params


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
    def setUp(self):
        _install_fake_nh3()

    def tearDown(self):
        sys.modules.pop("nh3", None)

    def test_sanitize_whitelist_wiring(self):
        captured = {}

        def _capture(text, **kwargs):
            captured.update(kwargs)
            return text

        _install_fake_nh3()
        sys.modules["nh3"].clean = _capture
        svc.sanitize_overview_html("<p>x</p>")
        self.assertEqual(set(captured["tags"]), set(svc.CANONICAL_TAGS))
        self.assertEqual(
            captured["attributes"],
            {key: set(value) for key, value in svc.CANONICAL_ATTRIBUTES.items()},
        )
        self.assertEqual(set(captured["url_schemes"]), {"http", "https", "mailto"})
        self.assertEqual(captured["link_rel"], "noopener noreferrer")

    def test_sanitize_none_to_empty(self):
        self.assertEqual(svc.sanitize_overview_html(None), "")

    def test_sanitize_unavailable_fail_closed(self):
        sys.modules.pop("nh3", None)
        with self.assertRaises(RuntimeError):
            svc.sanitize_overview_html("<p>x</p>")

    def test_overview_digest(self):
        self.assertEqual(svc.overview_digest(""), svc.overview_digest(""))
        self.assertEqual(svc.overview_digest(None), svc.overview_digest(""))
        self.assertNotEqual(svc.overview_digest("a"), svc.overview_digest("b"))
        self.assertEqual(len(svc.overview_digest("x")), 16)

    def test_baseline_matches(self):
        stored = "<p>hello</p>"
        digest = svc.overview_digest(stored)
        self.assertTrue(svc.baseline_matches(digest, stored))
        self.assertTrue(svc.baseline_matches(digest.upper(), stored))
        self.assertFalse(svc.baseline_matches(digest, "<p>changed</p>"))
        self.assertFalse(svc.baseline_matches("", stored))
        self.assertFalse(svc.baseline_matches(None, stored))
        self.assertFalse(svc.baseline_matches(123, stored))

    def test_content_over_limit(self):
        self.assertFalse(svc.content_over_limit("x" * svc.MAX_LENGTH))
        self.assertTrue(svc.content_over_limit("x" * (svc.MAX_LENGTH + 1)))
        self.assertFalse(svc.content_over_limit(None))

    def test_flag_enabled(self):
        self.assertTrue(svc.flag_enabled("true"))
        self.assertTrue(svc.flag_enabled(" 1 "))
        self.assertTrue(svc.flag_enabled("Yes"))
        self.assertFalse(svc.flag_enabled("false"))
        self.assertFalse(svc.flag_enabled(None))
        self.assertFalse(svc.flag_enabled(True))
        self.assertFalse(svc.flag_enabled(""))


# ---------------------------------------------------------------------------
# handler：门控与输入校验（claim 前，无幂等行）
# ---------------------------------------------------------------------------


class HandlerGatingTests(unittest.TestCase):
    def setUp(self):
        _install_fake_nh3()

    def tearDown(self):
        sys.modules.pop("nh3", None)

    def test_flag_off_capability_disabled(self):
        # 参数模型缺失（env.get 返回 None）→ fail-closed
        env = _FakeEnv()
        with _PatchedClaim() as claim:
            resp = _run(env, _base_params())
        self.assertFalse(resp["ok"])
        self.assertEqual(resp["error"]["code"], "CAPABILITY_DISABLED")
        self.assertEqual(resp["error"]["suggested_action"], "enable_feature_flag")
        self.assertEqual(claim.claim_calls, [])

    def test_flag_explicitly_false_capability_disabled(self):
        env, _project = _seeded_env(flag=False)
        with _PatchedClaim() as claim:
            resp = _run(env, _base_params())
        self.assertFalse(resp["ok"])
        self.assertEqual(resp["error"]["code"], "CAPABILITY_DISABLED")
        self.assertEqual(claim.claim_calls, [])

    def test_missing_params(self):
        env, _project = _seeded_env()
        for overrides in (
            {"project_id": 0},
            {"expected_overview_digest": ""},
            {"new_overview_html": None},
        ):
            resp = _run(env, _base_params(**overrides))
            self.assertFalse(resp["ok"])
            self.assertEqual(resp["error"]["code"], "MISSING_PARAMS")

    def test_content_too_long(self):
        env, _project = _seeded_env()
        resp = _run(
            env,
            _base_params(new_overview_html="x" * (svc.MAX_LENGTH + 1)),
        )
        self.assertFalse(resp["ok"])
        self.assertEqual(resp["error"]["code"], "CONTENT_TOO_LONG")

    def test_sanitizer_unavailable_fail_closed(self):
        sys.modules.pop("nh3", None)
        env, _project = _seeded_env()
        with _PatchedClaim() as claim:
            resp = _run(env, _base_params())
        self.assertFalse(resp["ok"])
        self.assertEqual(resp["error"]["code"], "CAPABILITY_DISABLED")
        self.assertEqual(resp["error"]["suggested_action"], "contact_admin")
        self.assertEqual(claim.claim_calls, [])

    def test_project_not_found(self):
        env = _FakeEnv(params={svc.FLAG_KEY: "true"})
        resp = _run(env, _base_params(project_id=999))
        self.assertFalse(resp["ok"])
        self.assertEqual(resp["error"]["code"], "PROJECT_NOT_FOUND")


# ---------------------------------------------------------------------------
# handler：基线 / 执行 / 幂等 / 审计
# ---------------------------------------------------------------------------


class HandlerWriteTests(unittest.TestCase):
    def setUp(self):
        _install_fake_nh3()

    def tearDown(self):
        sys.modules.pop("nh3", None)

    def test_baseline_mismatch_releases_failed(self):
        env, project = _seeded_env(overview_html="<p>旧内容</p>")
        with _PatchedClaim() as claim:
            resp = _run(env, _base_params())  # digest 与旧内容不符
        self.assertFalse(resp["ok"])
        self.assertEqual(resp["error"]["code"], "BASELINE_MISMATCH")
        self.assertEqual(resp["error"]["suggested_action"], "reload_and_retry")
        self.assertEqual(len(claim.claim_calls), 1)
        self.assertEqual(claim.complete_calls[-1]["status"], "failed")
        self.assertEqual(project.writes, [])

    def test_success_write_sanitized_and_projection(self):
        env, project = _seeded_env(overview_html="<p>旧内容</p>")
        params = _base_params(
            expected_overview_digest=svc.overview_digest("<p>旧内容</p>"),
            new_overview_html="<p>新内容</p>",
        )
        with _PatchedClaim() as claim:
            resp = _run(env, params)
        self.assertTrue(resp["ok"])
        data = resp["data"]
        self.assertEqual(data["reason_code"], "DONE")
        self.assertEqual(data["field"], svc.EDITABLE_FIELD)
        self.assertEqual(data["content_after"], "<p>新内容</p>")
        self.assertEqual(data["content_digest_after"], svc.overview_digest("<p>新内容</p>"))
        self.assertEqual(data["content_digest_before"], svc.overview_digest("<p>旧内容</p>"))
        self.assertEqual(data["length_after"], len("<p>新内容</p>"))
        self.assertTrue(data["content_modified"])
        self.assertFalse(data["sanitized_input_changed"])
        self.assertEqual(project.writes, [{svc.EDITABLE_FIELD: "<p>新内容</p>"}])
        # 成功路径 complete 不带 status（缺省即 done）；失败路径才显式 failed
        self.assertNotIn("status", claim.complete_calls[-1])
        # 幂等结果不携带正文全文（审计/重放链路瘦身）
        self.assertNotIn("content_after", claim.complete_calls[-1]["result"])
        # 审计：摘要 + 长度，不落全文
        audit = env.audit_model.events[-1]
        self.assertEqual(audit["event_code"], svc.EVENT_CODE)
        self.assertNotIn("content_after", str(audit["after"]))
        self.assertEqual(audit["after"]["digest_after"], data["content_digest_after"])

    def test_success_sanitized_input_changed_flag(self):
        _install_fake_nh3(transform=lambda text: text.replace("<script>x</script>", ""))
        env, project = _seeded_env(overview_html="")
        params = _base_params(
            expected_overview_digest=svc.overview_digest(""),
            new_overview_html="<p>ok</p><script>x</script>",
        )
        resp = _run(env, params)
        self.assertTrue(resp["ok"])
        self.assertTrue(resp["data"]["sanitized_input_changed"])
        self.assertEqual(project.overview_html, "<p>ok</p>")

    def test_success_empty_content_clears(self):
        env, project = _seeded_env(overview_html="<p>旧</p>")
        params = _base_params(
            expected_overview_digest=svc.overview_digest("<p>旧</p>"),
            new_overview_html="",
        )
        resp = _run(env, params)
        self.assertTrue(resp["ok"])
        self.assertEqual(project.overview_html, "")

    def test_replay_returns_first_result_without_rewrite(self):
        env, project = _seeded_env(overview_html="<p>旧内容</p>")
        params = _base_params(
            expected_overview_digest=svc.overview_digest("<p>旧内容</p>"),
        )
        with _PatchedClaim(mode="replay", replay_payload={"reason_code": "DONE", "cached": True}):
            resp = _run(env, params)
        self.assertTrue(resp["ok"])
        self.assertTrue(resp["data"]["cached"])
        self.assertTrue(resp["data"]["idempotent_replay"])
        self.assertEqual(project.writes, [])

    def test_conflict_and_in_flight(self):
        env, project = _seeded_env(overview_html="<p>旧内容</p>")
        params = _base_params(
            expected_overview_digest=svc.overview_digest("<p>旧内容</p>"),
        )
        with _PatchedClaim(mode="conflict"):
            resp = _run(env, params)
        self.assertFalse(resp["ok"])
        self.assertEqual(resp["error"]["code"], "IDEMPOTENCY_CONFLICT")
        with _PatchedClaim(mode="in_flight"):
            resp = _run(env, params)
        self.assertFalse(resp["ok"])
        self.assertEqual(resp["error"]["code"], "IDEMPOTENCY_IN_FLIGHT")
        self.assertEqual(project.writes, [])

    def test_patch_error_rolls_back_and_releases_failed(self):
        env, project = _seeded_env(overview_html="<p>旧内容</p>")
        project.fail_write = True
        params = _base_params(
            expected_overview_digest=svc.overview_digest("<p>旧内容</p>"),
        )
        with _PatchedClaim() as claim:
            resp = _run(env, params)
        self.assertFalse(resp["ok"])
        self.assertEqual(resp["error"]["code"], "PATCH_ERROR")
        self.assertEqual(resp["error"]["suggested_action"], "retry")
        self.assertEqual(claim.complete_calls[-1]["status"], "failed")

    def test_audit_disabled_does_not_break(self):
        env, project = _seeded_env(overview_html="<p>旧内容</p>", audit=False)
        params = _base_params(
            expected_overview_digest=svc.overview_digest("<p>旧内容</p>"),
        )
        resp = _run(env, params)
        self.assertTrue(resp["ok"])


if __name__ == "__main__":
    unittest.main(verbosity=1)
