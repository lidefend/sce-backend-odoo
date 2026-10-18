# -*- coding: utf-8 -*-
"""Batch B identity semantics: no implicit platform_admin entry.

Covers the four behaviours required by ADR-007 execution batch B:
unresolved fallback, tenant route labelling, platform-instance determination
and tenant accounts never being reported as platform administrators.

Namespace isolation is NOT implemented here; these tests only prove that the
old over-broad labelling is gone and that explicit ``db`` still works.
"""

import importlib.util
import sys
import types
import unittest
from pathlib import Path

PLATFORM_DB = "sc_platform_control"
TENANT_DB = "sc_demo"


class _BaseIntentHandler:
    def __init__(self, env=None, params=None):
        self.env = env
        self.params = params or {}

    def err(self, code, message):
        return {"ok": False, "error": {"code": code, "message": message}, "code": code}


class _Config:
    def __init__(self, params=None):
        self._params = dict(params or {})

    def sudo(self):
        return self

    def get_param(self, key, default=None):
        return self._params.get(key, default)


class _Env(dict):
    def __init__(self, dbname=TENANT_DB, route=None, params=None):
        self.cr = types.SimpleNamespace(dbname=dbname)
        data = {"ir.config_parameter": _Config(params)}
        if route is not None:
            data["sc.login.route"] = route
        super().__init__(data)


class _Principal:
    principal_type = "human"
    auth_method = "password"
    credential_id = ""
    scopes = ("interactive",)
    company_id = 1
    allowed_company_ids = (1, 2)
    role_xmlids = ("base.group_user",)


class _RouteRecord:
    """Minimal sc.login.route record using the real entry-kind normaliser."""

    def __init__(self, normalize, *, target_db=TENANT_DB, entry_kind="tenant", login="admin"):
        self._normalize = normalize
        self.target_db = target_db
        self.entry_kind = entry_kind
        self.login = login

    def to_runtime_dict(self, current_db=None):
        entry_kind = self.entry_kind
        if current_db is not None:
            entry_kind = self._normalize(self.entry_kind, current_db)
        return {
            "login": self.login,
            "target_db": self.target_db,
            "entry_kind": entry_kind,
            "product_key": "platform",
            "label": "Platform Admin" if entry_kind == "platform_admin" else "Tenant",
        }


class _RouteModel:
    def __init__(self, record):
        self._record = record

    def sudo(self):
        return self

    def search(self, domain, limit=1):
        return self._record


class _SeedModel:
    """Unbound-model harness for ensure_platform_default_login_routes()."""

    def __init__(self, dbname):
        self.env = _Env(dbname=dbname, params={"sc.login.platform_admin_logins": "admin,ops"})
        self.created = []

    def sudo(self):
        return self

    def search(self, domain, limit=1):
        return None

    def create(self, vals):
        self.created.append(dict(vals))
        return None


def _install_module(name, **attrs):
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


def _install_odoo(*, with_orm=False):
    if with_orm:
        fields_mod = types.SimpleNamespace(
            Boolean=lambda *a, **k: None,
            Integer=lambda *a, **k: None,
            Char=lambda *a, **k: None,
            Selection=lambda *a, **k: None,
            Text=lambda *a, **k: None,
        )
        models_mod = types.SimpleNamespace(Model=object)
        api_mod = types.SimpleNamespace(model=lambda fn: fn)
        odoo_mod = _install_module(
            "odoo", SUPERUSER_ID=1, api=api_mod, fields=fields_mod, models=models_mod
        )
    else:
        api_mod = types.SimpleNamespace(Environment=lambda cr, uid, context: None)
        odoo_mod = _install_module("odoo", SUPERUSER_ID=1, api=api_mod)
    # ``from odoo.http import request`` needs ``odoo`` to behave as a package.
    odoo_mod.__path__ = []
    return odoo_mod


def _install_odoo_http():
    """Stub ``odoo.http.request`` (only ``session`` is touched by login.py)."""

    return _install_module("odoo.http", request=types.SimpleNamespace(session=None))


def _install_package_modules(root: Path):
    _install_module("odoo.addons")
    smart_core_mod = _install_module("odoo.addons.smart_core")
    smart_core_mod.__path__ = [str(root)]
    for name, path in (
        ("odoo.addons.smart_core.handlers", root / "handlers"),
        ("odoo.addons.smart_core.core", root / "core"),
        ("odoo.addons.smart_core.security", root / "security"),
        ("odoo.addons.smart_core.models", root / "models"),
    ):
        module = _install_module(name)
        module.__path__ = [str(path)]


def _load(module_name, path: Path):
    sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _load_login_routing():
    root = Path(__file__).resolve().parents[1]
    _install_odoo(with_orm=True)
    _install_package_modules(root)
    return _load("odoo.addons.smart_core.models.login_routing", root / "models" / "login_routing.py")


def _load_login_handler():
    root = Path(__file__).resolve().parents[1]
    _install_odoo()
    _install_odoo_http()
    _install_module("odoo.modules")
    _install_module("odoo.modules.registry", Registry=lambda db_name: None)
    _install_package_modules(root)
    _install_module("odoo.addons.smart_core.core.base_handler", BaseIntentHandler=_BaseIntentHandler)
    _install_module("odoo.addons.smart_core.core.handler_registry", HANDLER_REGISTRY={})
    _install_module(
        "odoo.addons.smart_core.security.auth",
        authenticate_user=lambda login, password, db=None: {"id": 5, "db": db, "principal": _Principal()},
        generate_token=lambda user_id=None, token_version=0, db=None, **kwargs: "token",
        get_token_exp_seconds=lambda: 3600,
        get_user_from_token=lambda: None,
    )
    module = _load("odoo.addons.smart_core.handlers.login", root / "handlers" / "login.py")
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


class TestLoginIdentitySemantics(unittest.TestCase):
    # --- requirement 1: unresolved fallback is explicit -------------------

    def test_unresolved_fallback_is_explicit_and_never_platform_admin(self):
        module = _load_login_handler()

        contract = module._resolve_login_route(_Env(TENANT_DB), login="nobody")

        self.assertEqual(contract["mode"], "unresolved")
        self.assertFalse(contract["resolved"])
        self.assertEqual(contract["entry_kind"], "unresolved")
        self.assertEqual(contract["target_db"], "")
        self.assertEqual(contract["db_authority"], "none")
        self.assertEqual(contract["unresolved_reason"], "no_login_route_declared")
        self.assertNotEqual(contract["entry_kind"], "platform_admin")

    # --- requirement 2: tenant route labelling ---------------------------

    def test_tenant_database_admin_route_is_labelled_tenant(self):
        routing = _load_login_routing()
        module = _load_login_handler()
        record = _RouteRecord(routing.normalize_entry_kind, target_db=TENANT_DB, entry_kind="platform_admin")

        contract = module._resolve_login_route(_Env(TENANT_DB, route=_RouteModel(record)), login="admin")

        self.assertTrue(contract["resolved"])
        self.assertEqual(contract["entry_kind"], "tenant")
        self.assertEqual(contract["target_db"], TENANT_DB)

    def test_platform_database_admin_route_stays_platform_admin(self):
        routing = _load_login_routing()
        module = _load_login_handler()
        record = _RouteRecord(routing.normalize_entry_kind, target_db=PLATFORM_DB, entry_kind="platform_admin")

        contract = module._resolve_login_route(_Env(PLATFORM_DB, route=_RouteModel(record)), login="admin")

        self.assertEqual(contract["entry_kind"], "platform_admin")

    def test_normalize_entry_kind_degrades_platform_label_on_tenant_database(self):
        routing = _load_login_routing()

        self.assertEqual(routing.normalize_entry_kind("platform_admin", TENANT_DB), "tenant")
        self.assertEqual(routing.normalize_entry_kind("platform_admin", PLATFORM_DB), "platform_admin")
        self.assertEqual(routing.normalize_entry_kind("tenant", PLATFORM_DB), "tenant")

    def test_ensure_platform_routes_skips_tenant_database(self):
        routing = _load_login_routing()
        model = _SeedModel(TENANT_DB)

        created = routing.ScLoginRoute.ensure_platform_default_login_routes(model)

        self.assertFalse(created)
        self.assertEqual(model.created, [])

    def test_ensure_platform_routes_seeds_platform_database(self):
        routing = _load_login_routing()
        model = _SeedModel(PLATFORM_DB)

        routing.ScLoginRoute.ensure_platform_default_login_routes(model)

        self.assertEqual([row["login"] for row in model.created], ["admin", "ops"])
        for row in model.created:
            self.assertEqual(row["entry_kind"], "platform_admin")
            self.assertEqual(row["target_db"], PLATFORM_DB)

    # --- requirement 4 + 5: response contract and tenant accounts --------

    def test_tenant_login_response_never_reports_platform_admin(self):
        routing = _load_login_routing()
        module = _load_login_handler()
        record = _RouteRecord(routing.normalize_entry_kind, target_db=TENANT_DB, entry_kind="platform_admin")
        seen = {}

        def _auth(login, password, db=None):
            seen["db"] = db
            return {"id": 5, "db": db or TENANT_DB, "principal": _Principal()}

        module.authenticate_user = _auth
        handler = module.LoginHandler(
            env=_Env(TENANT_DB, route=_RouteModel(record)),
            params={"login": "admin", "password": "pw"},
        )

        data, _meta = handler.handle()

        self.assertEqual(seen["db"], TENANT_DB)
        self.assertEqual(data["session"]["entry_kind"], "tenant")
        self.assertEqual(data["login_route"]["entry_kind"], "tenant")
        self.assertEqual(data["contract"]["entry_resolution"], "resolved")
        self.assertFalse(data["contract"]["explicit_db_deprecated"])

    def test_platform_admin_login_still_works_on_platform_instance(self):
        routing = _load_login_routing()
        module = _load_login_handler()
        record = _RouteRecord(routing.normalize_entry_kind, target_db=PLATFORM_DB, entry_kind="platform_admin")
        seen = {}

        def _auth(login, password, db=None):
            seen["db"] = db
            return {"id": 5, "db": db or PLATFORM_DB, "principal": _Principal()}

        module.authenticate_user = _auth
        handler = module.LoginHandler(
            env=_Env(PLATFORM_DB, route=_RouteModel(record)),
            params={"login": "admin", "password": "pw"},
        )

        data, _meta = handler.handle()

        self.assertEqual(seen["db"], PLATFORM_DB)
        self.assertEqual(data["session"]["db"], PLATFORM_DB)
        self.assertEqual(data["session"]["entry_kind"], "platform_admin")
        self.assertEqual(data["login_route"]["entry_kind"], "platform_admin")

    def test_explicit_db_entry_is_kept_and_marked_deprecated(self):
        module = _load_login_handler()
        seen = {}

        def _auth(login, password, db=None):
            seen["db"] = db
            return {"id": 5, "db": db or TENANT_DB, "principal": _Principal()}

        module.authenticate_user = _auth
        handler = module.LoginHandler(
            env=_Env(TENANT_DB),
            params={"login": "demo", "password": "pw", "db": TENANT_DB},
        )

        data, _meta = handler.handle()

        self.assertEqual(seen["db"], TENANT_DB)
        self.assertEqual(data["login_route"]["mode"], "explicit_db")
        self.assertEqual(data["login_route"]["entry_kind"], "explicit")
        self.assertTrue(data["login_route"]["deprecated"])
        self.assertEqual(data["login_route"]["removal_batch"], "C")
        self.assertTrue(data["contract"]["explicit_db_deprecated"])

    def test_unresolved_entry_is_visible_and_does_not_block_login(self):
        module = _load_login_handler()
        seen = {}

        def _auth(login, password, db=None):
            seen["db"] = db
            return {"id": 5, "db": db or TENANT_DB, "principal": _Principal()}

        module.authenticate_user = _auth
        handler = module.LoginHandler(env=_Env(TENANT_DB), params={"login": "demo", "password": "pw"})

        data, _meta = handler.handle()

        self.assertEqual(data["contract"]["entry_resolution"], "unresolved")
        self.assertEqual(data["session"]["entry_kind"], "unresolved")
        self.assertEqual(seen["db"], "")
        self.assertEqual(data["session"]["db"], TENANT_DB)


if __name__ == "__main__":
    unittest.main()
