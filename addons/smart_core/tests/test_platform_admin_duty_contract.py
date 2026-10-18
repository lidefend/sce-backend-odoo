# -*- coding: utf-8 -*-
"""PLATFORM-ADMIN-DUTY-20261018: declared platform duty surface.

The platform administrator's identity domain, capability list and default
landing are a backend declaration (``core/platform_duty_contract.py``); the
frontend only renders them.  These tests pin:

* a verified platform-control admin gets a non-empty, declared surface;
* a tenant configuration admin gets tenant duties and never ``platform.*``;
* a plain user gets nothing and the audience is explicitly ``none``;
* the projection never carries a physical database name;
* break-glass / group-only input cannot manufacture platform duty;
* the identity projection and the ``/api/ops/platform-duty`` route consume the
  contract and the shared platform-control predicate;
* ``/api/ops/tenants`` is registry-driven, not a ``res.company`` scan.

Namespace isolation itself is not implemented here.
"""

import importlib.util
import inspect
import json
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADDONS = Path(__file__).resolve().parents[2]
CONTROLLERS = ROOT / "controllers"
PLATFORM_DB = "sc_platform_control"
DEMO_DB = "sc_demo"


def _install_module(name, **attrs):
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


def _load(name, path):
    sys.modules.pop(name, None)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _load_contract():
    return _load("platform_duty_contract_under_test", ROOT / "core" / "platform_duty_contract.py")


def _load_predicates():
    return _load("platform_admin_under_test", ROOT / "security" / "platform_admin.py")


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
        super().__init__({"ir.config_parameter": _FakeConfig(params)})


class _FakeUser:
    def __init__(self, groups, env=None, uid=2, name="admin"):
        self._groups = set(groups)
        self.env = env
        self.id = uid
        self.name = name
        self.lang = "zh_CN"
        self.tz = "Asia/Shanghai"
        self.company_id = None

    def has_group(self, xmlid):
        return xmlid in self._groups


class ContractDeclarationTests(unittest.TestCase):
    def setUp(self):
        self.contract = _load_contract()

    def test_platform_duty_keys_unique_and_sorted(self):
        keys = self.contract.declared_platform_duty_keys()
        self.assertTrue(keys)
        self.assertEqual(keys, sorted(keys))
        self.assertEqual(len(keys), len(set(keys)))

    def test_platform_control_surface_is_non_empty_and_declared(self):
        surface = self.contract.build_platform_duty_surface(
            is_platform_control_admin=True,
            is_tenant_config_admin=True,
            namespace_id="ns_000000000001",
        )
        self.assertEqual(surface["audience"], "platform-admin")
        self.assertTrue(surface["capabilities"])
        # The platform-control identity holds the platform duties only; a
        # tenant configuration identity holds the tenant duties only.
        self.assertEqual(surface["duty_keys"], self.contract.declared_platform_duty_keys())
        self.assertFalse([key for key in surface["duty_keys"] if key.startswith("tenant.")])
        self.assertIn("platform.home.open", surface["capabilities"])
        self.assertTrue(surface["trusted_instance_verified"])
        self.assertEqual(surface["namespace_id"], "ns_000000000001")
        self.assertEqual(surface["contract_version"], self.contract.CONTRACT_VERSION)
        self.assertIsNotNone(surface["default_landing"])
        self.assertEqual(surface["default_landing"]["route"], "/")

    def test_tenant_admin_has_no_platform_duty(self):
        surface = self.contract.build_platform_duty_surface(
            is_platform_control_admin=False,
            is_tenant_config_admin=True,
        )
        self.assertEqual(surface["audience"], "tenant")
        self.assertFalse([key for key in surface["duty_keys"] if key.startswith("platform.")])
        self.assertFalse([cap for cap in surface["capabilities"] if cap.startswith("platform.")])
        self.assertIsNone(surface["default_landing"])
        self.assertFalse(surface["trusted_instance_verified"])

    def test_plain_user_surface_is_empty(self):
        surface = self.contract.build_platform_duty_surface(
            is_platform_control_admin=False,
            is_tenant_config_admin=False,
        )
        self.assertEqual(surface["audience"], "none")
        self.assertEqual(surface["duty_keys"], [])
        self.assertEqual(surface["capabilities"], [])
        self.assertEqual(surface["duties"], [])
        self.assertIsNone(surface["default_landing"])

    def test_undeclared_capability_is_rejected(self):
        with self.assertRaises(ValueError):
            self.contract.validate_surface(
                {"audience": "tenant", "capabilities": ["platform.do_anything"]}
            )

    def test_surface_never_projects_a_physical_database(self):
        surface = self.contract.build_platform_duty_surface(
            is_platform_control_admin=True,
            is_tenant_config_admin=True,
            namespace_id="ns_000000000001",
        )
        encoded = json.dumps(surface, ensure_ascii=False)
        self.assertNotIn(PLATFORM_DB, encoded)
        self.assertNotIn(DEMO_DB, encoded)
        for forbidden in ("db_name", "database_name", "trusted_instance", "trusted_instance_database"):
            self.assertNotIn(forbidden, surface)
            self.assertNotIn('"%s":' % forbidden, encoded)
        # The only instance fact is a verified boolean, never a physical name.
        self.assertIs(surface["trusted_instance_verified"], True)

    def test_platform_capability_rows_cover_every_declared_capability(self):
        surface = self.contract.build_platform_duty_surface(
            is_platform_control_admin=True, is_tenant_config_admin=False
        )
        rows = self.contract.build_capability_rows(surface)
        self.assertEqual(
            sorted(row["key"] for row in rows),
            self.contract.declared_platform_capabilities(),
        )
        self.assertIn("READY", {row["state"] for row in rows})
        for row in rows:
            self.assertEqual(row["group_key"], "platform_control")
            self.assertIn(row["state"], {"READY", "PREVIEW"})
            self.assertTrue(row["ui_label"])
            self.assertTrue(row["default_payload"].get("route") or row["default_payload"].get("intent"))

    def test_tenant_and_plain_surfaces_produce_no_platform_rows(self):
        tenant = self.contract.build_platform_duty_surface(
            is_platform_control_admin=False, is_tenant_config_admin=True
        )
        plain = self.contract.build_platform_duty_surface(
            is_platform_control_admin=False, is_tenant_config_admin=False
        )
        self.assertEqual(self.contract.build_capability_rows(tenant), [])
        self.assertEqual(self.contract.build_capability_rows(plain), [])
        self.assertEqual(self.contract.build_capability_rows(None), [])

    def test_break_glass_cannot_manufacture_platform_duty(self):
        # The contract takes only the two verified booleans; there is no user,
        # group or break-glass parameter that could widen the surface.
        params = inspect.signature(self.contract.build_platform_duty_surface).parameters
        self.assertEqual(
            set(params),
            {"is_platform_control_admin", "is_tenant_config_admin", "namespace_id"},
        )
        self.assertTrue(all(param.kind is inspect.Parameter.KEYWORD_ONLY for param in params.values()))
        surface = self.contract.build_platform_duty_surface(
            is_platform_control_admin=False,
            is_tenant_config_admin=False,
            namespace_id="ns_000000000001",
        )
        self.assertEqual(surface["capabilities"], [])
        self.assertFalse(surface["trusted_instance_verified"])


class PredicateBoundaryTests(unittest.TestCase):
    """Same login name, different instance: the duties must not follow the name."""

    def setUp(self):
        self.predicates = _load_predicates()
        self.group = self.predicates.PLATFORM_ADMIN_GROUP

    def test_demo_admin_is_tenant_config_admin_only(self):
        env = _FakeEnv(DEMO_DB)
        user = _FakeUser([self.group], env=env)
        self.assertTrue(self.predicates.user_is_tenant_config_admin(user))
        self.assertFalse(
            self.predicates.user_is_platform_control_admin(
                user, env=env, identity_audience="platform-admin"
            )
        )

    def test_platform_admin_needs_group_instance_and_audience(self):
        env = _FakeEnv(PLATFORM_DB)
        user = _FakeUser([self.group], env=env)
        self.assertTrue(
            self.predicates.user_is_platform_control_admin(
                user, env=env, identity_audience="platform-admin"
            )
        )
        self.assertFalse(
            self.predicates.user_is_platform_control_admin(
                user, env=env, identity_audience="tenant"
            )
        )

    def test_plain_user_holds_neither_duty(self):
        env = _FakeEnv(DEMO_DB)
        user = _FakeUser(["base.group_user"], env=env)
        self.assertFalse(self.predicates.user_is_tenant_config_admin(user))
        self.assertFalse(
            self.predicates.user_is_platform_control_admin(
                user, env=env, identity_audience="platform-admin"
            )
        )


class ProjectionAndRouteTests(unittest.TestCase):
    def test_identity_payload_projects_duty_surface(self):
        for name, path in (
            ("odoo", None),
            ("odoo.addons", ADDONS),
            ("odoo.addons.smart_core", ROOT),
            ("odoo.addons.smart_core.core", ROOT / "core"),
            ("odoo.addons.smart_core.security", ROOT / "security"),
        ):
            module = _install_module(name)
            module.__path__ = [] if path is None else [str(path)]
        _install_module(
            "odoo.addons.smart_core.core.source_authority",
            build_source_authority_contract=lambda **kwargs: dict(kwargs),
        )
        state = {"platform": False, "tenant": True}
        _install_module(
            "odoo.addons.smart_core.security.platform_admin",
            user_is_platform_control_admin=lambda user, **kwargs: state["platform"],
            user_is_tenant_config_admin=lambda user: state["tenant"],
        )
        payload_module = _load(
            "odoo.addons.smart_core.core.system_init_identity_payload",
            ROOT / "core" / "system_init_identity_payload.py",
        )
        user = _FakeUser(["smart_core.group_smart_core_admin"])

        tenant_payload = payload_module.SystemInitIdentityPayload.build(user, [])
        self.assertEqual(tenant_payload["platform_duty"]["audience"], "tenant")
        self.assertFalse(tenant_payload["is_platform_admin"])
        self.assertTrue(tenant_payload["is_tenant_config_admin"])

        state.update({"platform": True, "tenant": True})
        platform_payload = payload_module.SystemInitIdentityPayload.build(user, [])
        self.assertEqual(platform_payload["platform_duty"]["audience"], "platform-admin")
        self.assertTrue(platform_payload["platform_duty"]["capabilities"])

        state.update({"platform": False, "tenant": False})
        plain_payload = payload_module.SystemInitIdentityPayload.build(user, [])
        self.assertEqual(plain_payload["platform_duty"]["audience"], "none")
        self.assertEqual(plain_payload["platform_duty"]["capabilities"], [])

    def test_platform_duty_controller_uses_shared_authorization_path(self):
        source = (CONTROLLERS / "platform_duty_controller.py").read_text(encoding="utf-8")
        self.assertIn('"/api/ops/platform-duty"', source)
        self.assertIn("from odoo.addons.smart_core.controllers.platform_ops_controller import _platform_env", source)
        self.assertIn("build_platform_duty_surface", source)
        # No local group check may stand in for the verified platform decision.
        self.assertNotIn("has_group", source)
        ops_source = (CONTROLLERS / "platform_ops_controller.py").read_text(encoding="utf-8")
        self.assertIn("user_is_platform_control_admin", ops_source)

    def test_system_init_projects_platform_duties_into_top_level_capabilities(self):
        source = (ROOT / "handlers" / "system_init.py").read_text(encoding="utf-8")
        self.assertIn("_merge_platform_duty_capabilities", source)
        self.assertIn("build_platform_duty_capability_rows", source)
        self.assertIn('data["capability_groups"] = other_groups + platform_groups', source)

    def test_tenants_endpoint_is_registry_driven(self):
        ops_source = (CONTROLLERS / "platform_ops_controller.py").read_text(encoding="utf-8")
        self.assertIn('"/api/ops/tenants"', ops_source)
        self.assertIn("sc.platform.namespace", ops_source)
        self.assertIn('("audience", "=", "tenant")', ops_source)
        self.assertIn("sc.tenant.company.registration", ops_source)
        # `res.company` is no longer enumerated as the tenant list.
        self.assertNotIn("res.company\"]", ops_source)
        self.assertNotIn("Company.search([])", ops_source)

    def test_platform_duty_panel_never_routes_an_api_path(self):
        """A duty that is an API endpoint must be consumed, not navigated.

        ``router.push('/api/ops/tenants')`` would unmount the SPA and show raw
        JSON, so the panel may only navigate to a declared frontend route.
        """
        web = Path(__file__).resolve().parents[3] / "frontend" / "apps" / "web" / "src"
        action_source = (web / "components" / "platform-duty" / "dutyAction.ts").read_text(encoding="utf-8")
        panel_source = (web / "components" / "platform-duty" / "PlatformDutyPanel.vue").read_text(encoding="utf-8")

        self.assertIn("export function resolveDutyAction", action_source)
        self.assertIn("isApiEndpoint", action_source)
        self.assertIn("kind: 'inline'", action_source)
        self.assertIn("SPA_ROUTE_PREFIXES = ['/admin/']", action_source)

        self.assertIn("resolveDutyAction", panel_source)
        self.assertEqual(1, panel_source.count("router.push("))
        self.assertIn("router.push(action.route)", panel_source)
        self.assertIn("action.kind !== 'navigate'", panel_source)
        # The pre-fix shape: a route of any kind was pushed straight to the router.
        self.assertNotIn('@click="open(duty.route)"', panel_source)
        self.assertNotIn("router.push(route)", panel_source)

    def test_platform_duty_panel_renders_the_tenant_registry_table(self):
        web = Path(__file__).resolve().parents[3] / "frontend" / "apps" / "web" / "src"
        panel_source = (web / "components" / "platform-duty" / "PlatformDutyPanel.vue").read_text(encoding="utf-8")

        self.assertIn("const TENANT_REGISTRY_ENDPOINT = '/api/ops/tenants'", panel_source)
        self.assertIn("apiRequest<OpsTenantsResponse>(TENANT_REGISTRY_ENDPOINT)", panel_source)
        for field in ("namespace_id", "tenant_name", "lifecycle_state", "alias", "path_prefix", "billing_bound"):
            self.assertIn(field, panel_source)
        self.assertIn("data-tenant-registry-table", panel_source)
        self.assertIn("当前没有已登记的租户命名空间", panel_source)
        # The table is the platform registration, never a cross-database company read.
        self.assertNotIn("res.company", panel_source)

    def test_demo_tenant_name_is_declared_in_the_platform_registry(self):
        seed = (ROOT / "data" / "sc_platform_namespace_seed.xml").read_text(encoding="utf-8")
        self.assertIn("<field name=\"display_name\">Demo演示公司</field>", seed)
        self.assertNotIn("Demo tenant", seed)
        migration = ROOT / "migrations" / "17.0.1.1.16" / "post-migration.py"
        self.assertTrue(migration.exists())
        migration_source = migration.read_text(encoding="utf-8")
        self.assertIn('DEMO_TENANT_NAME = "Demo演示公司"', migration_source)
        self.assertIn("sc_platform_namespace", migration_source)

    def test_tenants_payload_uses_the_registry_name_and_no_cross_db_company(self):
        ops_source = (CONTROLLERS / "platform_ops_controller.py").read_text(encoding="utf-8")
        self.assertIn('"tenant_name": namespace.display_name', ops_source)
        # Unbound namespaces keep company_id/company_name empty instead of
        # borrowing the platform instance's own company.
        self.assertIn('"company_id": company.id if company is not None else None', ops_source)
        self.assertIn('"company_name": company.name if company is not None else None', ops_source)
        self.assertIn('"billing_bound": bool(company is not None)', ops_source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
