# -*- coding: utf-8 -*-
"""ADR-007 batch B: tenant configuration admin vs platform control admin.

The first batch-B attempt made ``user_is_platform_admin`` mean "group AND
platform-control instance" and applied it everywhere.  That closed every
product/industry bypass on a Demo database, because the Demo ``admin`` holds
the configuration group but is not running on the platform-control instance.

These tests pin the corrected split:

``user_is_tenant_config_admin``   -> group check in the current tenant database
``user_is_platform_control_admin``-> group + declared platform-control instance

Namespace isolation is NOT implemented here.
"""

import importlib.util
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADDONS = Path(__file__).resolve().parents[2]

DEMO_DB = "sc_demo"
PLATFORM_DB = "sc_platform_control"
DEMO_PERMISSION = "payment.request.approve"


def _install_module(name, **attrs):
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


def _install_packages():
    odoo_mod = _install_module(
        "odoo",
        SUPERUSER_ID=1,
        api=types.SimpleNamespace(
            Environment=lambda cr, uid, context: None,
            model=lambda fn: fn,
        ),
    )
    odoo_mod.__path__ = []
    for name, path in (
        ("odoo.addons", ADDONS),
        ("odoo.addons.smart_core", ROOT),
        ("odoo.addons.smart_core.security", ROOT / "security"),
        ("odoo.addons.smart_core.core", ROOT / "core"),
        ("odoo.addons.smart_core.utils", ROOT / "utils"),
        ("odoo.addons.smart_core.app_config_engine", ROOT / "app_config_engine"),
        (
            "odoo.addons.smart_core.app_config_engine.services",
            ROOT / "app_config_engine" / "services",
        ),
        (
            "odoo.addons.smart_core.app_config_engine.services.dispatchers",
            ROOT / "app_config_engine" / "services" / "dispatchers",
        ),
        ("odoo.addons.smart_construction_core", ADDONS / "smart_construction_core"),
        (
            "odoo.addons.smart_construction_core.handlers",
            ADDONS / "smart_construction_core" / "handlers",
        ),
    ):
        module = _install_module(name)
        module.__path__ = [str(path)]


def _load(name, path):
    sys.modules.pop(name, None)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _resolve_instance(env):
    """Stand-in for batch C's namespace resolver in this pure-unit world."""

    database = str(getattr(getattr(env, "cr", None), "dbname", "") or "")
    platform = database == PLATFORM_DB
    return types.SimpleNamespace(
        namespace_id="ns_000000000001" if platform else "ns_000000000002",
        alias="platform" if platform else "demo",
        database_name=database,
        duty_key="platform_control" if platform else "demo",
        audience="platform-admin" if platform else "tenant",
        lifecycle_state="active",
    )


def _load_world():
    _install_packages()
    # Batch C resolves the audience from the instance namespace.  This suite
    # loads smart_core modules without Odoo, so the resolver is stubbed here
    # exactly as the registry would answer for the platform and Demo databases.
    _install_module(
        "odoo.addons.smart_core.security.namespace_resolver",
        resolve_instance=_resolve_instance,
    )
    _install_module("odoo.http", request=types.SimpleNamespace(env=None, httprequest=None))
    predicates = _load(
        "odoo.addons.smart_core.security.platform_admin",
        ROOT / "security" / "platform_admin.py",
    )
    _install_module(
        "odoo.addons.smart_core.core.base_handler",
        BaseIntentHandler=type("BaseIntentHandler", (), {}),
    )
    _install_module(
        "odoo.addons.smart_core.core.source_authority",
        build_source_authority_contract=lambda **kwargs: dict(kwargs),
    )
    _install_module(
        "odoo.addons.smart_core.utils.reason_codes",
        REASON_PERMISSION_DENIED="PERMISSION_DENIED",
        failure_meta_for_reason=lambda reason: {"reason": reason},
    )
    _install_module(
        "odoo.addons.smart_core.app_config_engine.services.dispatchers.action_dispatcher",
        ActionDispatcher=type("ActionDispatcher", (), {}),
    )
    _install_module(
        "odoo.addons.smart_core.app_config_engine.services.contract_service",
        ContractService=type("ContractService", (), {}),
    )
    catalog = _load(
        "odoo.addons.smart_construction_core.handlers.app_catalog",
        ADDONS / "smart_construction_core" / "handlers" / "app_catalog.py",
    )
    opener = _load(
        "odoo.addons.smart_construction_core.handlers.app_open",
        ADDONS / "smart_construction_core" / "handlers" / "app_open.py",
    )
    payload = _load(
        "odoo.addons.smart_core.core.system_init_identity_payload",
        ROOT / "core" / "system_init_identity_payload.py",
    )
    return predicates, catalog, opener, payload


class _FakeConfig:
    def __init__(self, params=None):
        self._params = dict(params or {})

    def sudo(self):
        return self

    def get_param(self, key, default=None):
        return self._params.get(key, default)


class _FakeEnv(dict):
    def __init__(self, dbname, params=None):
        self.cr = types.SimpleNamespace(dbname=dbname)
        self.context = {}
        super().__init__({"ir.config_parameter": _FakeConfig(params)})


class _FakeUser:
    def __init__(self, groups, env):
        self._groups = set(groups)
        self.env = env
        self.id = 7
        self.name = "Admin"
        self.lang = "zh_CN"
        self.tz = "Asia/Shanghai"
        self.company_id = None

    def has_group(self, xmlid):
        return xmlid in self._groups


def _env_with_user(dbname, user):
    env = _FakeEnv(dbname)
    env.user = user
    return env


class TestAdminPredicateSplit(unittest.TestCase):
    def setUp(self):
        self.predicates, self.catalog, self.opener, self.payload = _load_world()

    def _admin(self, dbname):
        env = _FakeEnv(dbname)
        return _FakeUser({self.predicates.PLATFORM_ADMIN_GROUP}, env), env

    # --- requirement 1/2/3: predicate values by instance ------------------

    def test_demo_admin_is_tenant_config_admin_but_not_platform_control(self):
        user, env = self._admin(DEMO_DB)

        self.assertTrue(self.predicates.user_is_tenant_config_admin(user))
        self.assertFalse(self.predicates.user_is_platform_control_admin(user))
        self.assertFalse(self.predicates.user_is_platform_admin(user))
        self.assertEqual(self.predicates.tenant_config_scope(user)["database"], DEMO_DB)

    def test_platform_control_instance_admin_is_platform_not_tenant(self):
        """PLATFORM-ADMIN-DUTY: the two responsibilities are mutually exclusive."""

        user, _env = self._admin(PLATFORM_DB)

        self.assertFalse(self.predicates.user_is_tenant_config_admin(user))
        self.assertTrue(
            self.predicates.user_is_platform_control_admin(
                user, identity_audience="platform-admin"
            )
        )
        scope = self.predicates.platform_control_scope(
            user, identity_audience="platform-admin"
        )
        self.assertTrue(scope["group_ok"])
        self.assertTrue(scope["instance_ok"])
        self.assertTrue(scope["audience_ok"])
        self.assertTrue(scope["is_platform_control_admin"])

    def test_plain_tenant_user_is_neither(self):
        env = _FakeEnv(DEMO_DB)
        user = _FakeUser(set(), env)

        self.assertFalse(self.predicates.user_is_tenant_config_admin(user))
        self.assertFalse(self.predicates.user_is_platform_control_admin(user))
        self.assertFalse(self.predicates.user_is_platform_admin(user))

    # --- requirement 4: product surfaces keep working on Demo ------------

    def test_app_catalog_bypass_uses_tenant_config_admin_on_demo(self):
        user, env = self._admin(DEMO_DB)
        env.user = user

        self.assertTrue(self.catalog._is_system_admin(env))

    def test_app_catalog_bypass_denied_for_plain_demo_user(self):
        env = _env_with_user(DEMO_DB, _FakeUser(set(), _FakeEnv(DEMO_DB)))

        self.assertFalse(self.catalog._is_system_admin(env))

    def test_app_open_required_permissions_bypass_on_demo(self):
        user, env = self._admin(DEMO_DB)
        env.user = user
        feature = {
            "required_permissions": [DEMO_PERMISSION],
            "open": {"internal_route": "/payment/request"},
        }

        self.assertTrue(
            self.opener._is_feature_openable(env, env, "payment", feature, set())
        )

    def test_app_open_required_permissions_denied_for_plain_demo_user(self):
        env = _env_with_user(DEMO_DB, _FakeUser(set(), _FakeEnv(DEMO_DB)))
        feature = {
            "required_permissions": [DEMO_PERMISSION],
            "open": {"internal_route": "/payment/request"},
        }

        self.assertFalse(
            self.opener._is_feature_openable(env, env, "payment", feature, set())
        )

    # --- requirement 6: negative control ---------------------------------

    def test_strict_platform_control_predicate_would_close_demo_product_surface(self):
        user, env = self._admin(DEMO_DB)
        env.user = user
        feature = {
            "required_permissions": [DEMO_PERMISSION],
            "open": {"internal_route": "/payment/request"},
        }

        # Pre-migration wiring: the strict predicate is False on Demo, so the
        # same bypass branch closes and the demo cannot open the feature.
        strict_allows = self.predicates.user_is_platform_control_admin(user)
        self.assertFalse(strict_allows)
        strict_denied = bool(feature["required_permissions"]) and not strict_allows
        self.assertTrue(strict_denied)

        # Post-migration wiring: the tenant predicate restores the bypass.
        self.assertTrue(self.predicates.user_is_tenant_config_admin(user))
        self.assertTrue(
            self.opener._is_feature_openable(env, env, "payment", feature, set())
        )
        self.assertTrue(self.catalog._is_system_admin(env))

    # --- requirement 5: identity payload exposes both ---------------------

    def test_identity_payload_separates_the_two_flags(self):
        demo_user, _env = self._admin(DEMO_DB)

        payload = self.payload.SystemInitIdentityPayload.build(
            demo_user, [self.predicates.PLATFORM_ADMIN_GROUP]
        )

        self.assertTrue(payload["is_tenant_config_admin"])
        self.assertFalse(payload["is_platform_admin"])

    def test_identity_payload_platform_admin_is_true_only_on_platform_instance(self):
        platform_user, _env = self._admin(PLATFORM_DB)

        payload = self.payload.SystemInitIdentityPayload.build(
            platform_user, [self.predicates.PLATFORM_ADMIN_GROUP]
        )

        self.assertFalse(payload["is_tenant_config_admin"])
        self.assertTrue(payload["is_platform_admin"])


if __name__ == "__main__":
    unittest.main()
