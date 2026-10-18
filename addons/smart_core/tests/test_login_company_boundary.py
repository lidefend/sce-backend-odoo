# -*- coding: utf-8 -*-
import importlib.util
import sys
import types
import unittest
from dataclasses import dataclass
from pathlib import Path


class _BaseIntentHandler:
    def __init__(self, env=None, params=None):
        self.env = env
        self.params = params or {}

    def err(self, code, message):
        return {"ok": False, "error": {"code": code, "message": message}, "code": code}


class _Config:
    def __init__(self, values=None):
        self.values = dict(values or {})

    def sudo(self):
        return self

    def get_param(self, key, default=None):
        return self.values.get(key, default)


class _NamespaceRecord:
    namespace_id = "ns_000000000002"
    database_name = "sc_demo"
    duty_key = "demo"
    audience = "tenant"
    lifecycle_state = "active"


class _NamespaceModel:
    def sudo(self):
        return self

    def resolve_alias(self, alias):
        if alias != "demo":
            raise AssertionError("unexpected namespace alias: " + str(alias))
        return _NamespaceRecord()


class _Env(dict):
    cr = types.SimpleNamespace(dbname="sc_demo")

    def __init__(self, route=None):
        data = {
            "ir.config_parameter": _Config(
                {"sc.entry.shared_secret": "test-secret", "sc.entry.route_version": "c1"}
            ),
            "sc.platform.namespace": _NamespaceModel(),
        }
        if route is not None:
            data["sc.login.route"] = route
        super().__init__(data)


@dataclass(frozen=True)
class _Principal:
    principal_type: str = "human"
    auth_method: str = "password"
    credential_id: str = ""
    scopes: tuple = ("interactive",)
    company_id: int = 1
    allowed_company_ids: tuple = (1, 2)
    role_xmlids: tuple = ("base.group_user",)


def _principal(company_id=1):
    return _Principal(
        principal_type="human",
        auth_method="password",
        credential_id="",
        scopes=("interactive",),
        company_id=company_id,
        allowed_company_ids=(1, 2),
    )


_ENTRY_HEADERS = {
    "X-SC-Namespace": "demo",
    "X-SC-Audience": "tenant",
    "X-SC-Route-Version": "c1",
    "X-SC-Entry-Secret": "test-secret",
}


def _install_module(name, **attrs):
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


def _load_handler():
    root = Path(__file__).resolve().parents[1]
    api_mod = types.SimpleNamespace(Environment=lambda cr, uid, context: None)
    odoo_mod = _install_module("odoo", SUPERUSER_ID=1, api=api_mod)
    # ``from odoo.http import request`` needs ``odoo`` to behave as a package.
    odoo_mod.__path__ = []
    _install_module(
        "odoo.http",
        request=types.SimpleNamespace(
            session=None, httprequest=types.SimpleNamespace(headers=dict(_ENTRY_HEADERS))
        ),
    )
    _install_module("odoo.modules")
    _install_module("odoo.modules.registry", Registry=lambda db_name: None)
    _install_module("odoo.addons")
    smart_core_mod = _install_module("odoo.addons.smart_core")
    handlers_mod = _install_module("odoo.addons.smart_core.handlers")
    core_mod = _install_module("odoo.addons.smart_core.core")
    security_mod = _install_module("odoo.addons.smart_core.security")
    smart_core_mod.__path__ = [str(root)]
    handlers_mod.__path__ = [str(root / "handlers")]
    core_mod.__path__ = [str(root / "core")]
    security_mod.__path__ = [str(root / "security")]
    _install_module("odoo.addons.smart_core.core.base_handler", BaseIntentHandler=_BaseIntentHandler)
    _install_module("odoo.addons.smart_core.core.handler_registry", HANDLER_REGISTRY={})
    _install_module(
        "odoo.addons.smart_core.security.auth",
        authenticate_user=lambda login, password, db=None: {"id": 5, "db": db or "test", "principal": _principal()},
        generate_token=lambda user_id=None, token_version=0, db=None, **kwargs: "token",
        get_token_exp_seconds=lambda: 3600,
        get_user_from_token=lambda: None,
    )

    module_name = "odoo.addons.smart_core.handlers.login"
    sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(module_name, root / "handlers" / "login.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    module._load_user_profile = lambda db_name, user_id: {
        "id": user_id,
        "name": "Demo",
        "login": "demo",
        "groups": ["base.group_user"],
        "lang": "zh_CN",
        "tz": "Asia/Shanghai",
        "company_id": 1,
        "company_name": "Main",
        "company": {"id": 1, "name": "Main"},
        "allowed_company_ids": [1, 2],
        "token_version": 0,
    }
    return module


class TestLoginCompanyBoundary(unittest.TestCase):
    def test_invalid_company_id_returns_bad_request(self):
        module = _load_handler()
        handler = module.LoginHandler(env=_Env(), params={"login": "demo", "password": "pw", "company_id": "bad"})

        result = handler.handle()

        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], 400)
        self.assertEqual(result["error"]["message"], "company_id 无效")

    def test_invalid_login_returns_bad_request(self):
        module = _load_handler()
        handler = module.LoginHandler(env=_Env(), params={"login": ["demo"], "password": "pw"})

        result = handler.handle()

        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], 400)
        self.assertEqual(result["error"]["message"], "login 无效")

    def test_invalid_password_returns_bad_request(self):
        module = _load_handler()
        handler = module.LoginHandler(env=_Env(), params={"login": "demo", "password": ["pw"]})

        result = handler.handle()

        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], 400)
        self.assertEqual(result["error"]["message"], "password 无效")

    def test_database_hint_is_a_conflict_not_a_route(self):
        module = _load_handler()
        handler = module.LoginHandler(env=_Env(), params={"login": "demo", "password": "pw", "db": "sc_demo"})

        result = handler.handle()

        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], 409)
        self.assertTrue(result["error"]["message"].startswith("NS_DATABASE_HINT_CONFLICT"))

    def test_database_hint_header_is_a_conflict_not_a_route(self):
        module = _load_handler()
        sys.modules["odoo.http"].request.httprequest.headers["X-Odoo-Database"] = "sc_demo"
        handler = module.LoginHandler(env=_Env(), params={"login": "demo", "password": "pw"})

        result = handler.handle()

        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], 409)
        self.assertTrue(result["error"]["message"].startswith("NS_DATABASE_HINT_CONFLICT"))

    def test_disallowed_company_id_returns_forbidden(self):
        module = _load_handler()
        handler = module.LoginHandler(env=_Env(), params={"login": "demo", "password": "pw", "company_id": 99})

        result = handler.handle()

        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], 403)
        self.assertEqual(result["error"]["message"], "公司不在当前用户允许范围内")

    def test_allowed_company_id_is_reflected_in_user_payload(self):
        module = _load_handler()
        handler = module.LoginHandler(env=_Env(), params={"login": "demo", "password": "pw", "company_id": 2})

        data, _meta = handler.handle()

        self.assertEqual(data["user"]["company_id"], 2)

    def test_login_without_db_uses_entry_namespace_contract(self):
        module = _load_handler()
        seen = {}

        def _auth(login, password, db=None):
            seen["db"] = db
            return {"id": 5, "db": db or "missing", "principal": _principal()}

        module.authenticate_user = _auth
        handler = module.LoginHandler(env=_Env(), params={"login": "demo", "password": "pw"})

        data, _meta = handler.handle()

        self.assertEqual(seen["db"], "sc_demo")
        self.assertEqual(data["session"]["db"], "sc_demo")
        self.assertEqual(data["login_route"]["source"], "entry_namespace")
        self.assertEqual(data["login_route"]["entry_kind"], "tenant")
        self.assertEqual(data["login_route"]["namespace_id"], "ns_000000000002")


if __name__ == "__main__":
    unittest.main()
