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
        for duty in surface["duties"]:
            self.assertTrue(duty.get("label"), duty)
            self.assertTrue(duty.get("description"), duty)
            self.assertTrue(duty.get("state_label"), duty)
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
            payload = row["default_payload"]
            self.assertTrue(payload.get("route") or payload.get("intent") or payload.get("action_xmlid"))

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
            {"is_platform_control_admin", "is_tenant_config_admin", "namespace_id", "action_routes"},
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

    def test_system_init_publishes_duty_actions_into_route_authority(self):
        """A duty route without a menu must still be executable by the SPA.

        The platform-control navigation is deliberately minimal.  If the duty
        action is absent from route authority, the SPA denies ``/a/<id>`` even
        though the duty panel rendered the entry.  The duty declaration owns
        that route authority for the verified platform audience.
        """
        source = (ROOT / "handlers" / "system_init.py").read_text(encoding="utf-8")
        self.assertIn("merge_platform_duty_route_authority", source)
        self.assertIn('surface=(data.get("user") or {}).get("platform_duty")', source)

        contract = _load_contract()
        surface = contract.build_platform_duty_surface(
            is_platform_control_admin=True,
            is_tenant_config_admin=False,
            action_routes={"smart_core.action_sc_ops_job": "/a/42"},
        )
        action = types.SimpleNamespace(
            _name="ir.actions.act_window",
            id=42,
            name="运营任务",
            res_model="sc.ops.job",
            view_mode="tree,form",
            view_id=types.SimpleNamespace(id=7),
            domain="[]",
            context="{}",
        )
        env = types.SimpleNamespace(
            ref=lambda xmlid, raise_if_not_found=False: (
                action if xmlid == "smart_core.action_sc_ops_job" else None
            ),
        )
        authority = {
            "admin_actions": [],
            "primary_actions": [],
            "role_home_actions": [],
            "contextual_actions": [],
            "denied_actions": [],
            "menu_containers": [],
        }
        merged = contract.merge_platform_duty_route_authority(authority, env=env, surface=surface)
        rows = [row for row in merged["admin_actions"] if row["action_id"] == 42]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["route_kind"], "ADMIN_ROUTE")
        self.assertEqual(rows[0]["menu_id"], 0)
        self.assertEqual(rows[0]["action_xmlid"], "smart_core.action_sc_ops_job")
        self.assertEqual(rows[0]["route"], "/a/42")
        self.assertEqual(rows[0]["model"], "sc.ops.job")
        self.assertEqual(rows[0]["view_modes"], ["tree", "form"])

        # Re-merging must not duplicate the same executable action.
        merged_again = contract.merge_platform_duty_route_authority(merged, env=env, surface=surface)
        self.assertEqual(
            len([row for row in merged_again["admin_actions"] if row["action_id"] == 42]),
            1,
        )

    def test_tenant_surface_never_publishes_platform_duty_routes(self):
        contract = _load_contract()
        surface = contract.build_platform_duty_surface(
            is_platform_control_admin=False,
            is_tenant_config_admin=True,
        )
        action = types.SimpleNamespace(_name="ir.actions.act_window", id=42)
        env = types.SimpleNamespace(ref=lambda xmlid, raise_if_not_found=False: action)
        self.assertEqual(
            contract.build_platform_duty_route_authority_entries(env=env, surface=surface),
            [],
        )

    def test_unresolvable_duty_action_fails_closed(self):
        contract = _load_contract()
        surface = contract.build_platform_duty_surface(
            is_platform_control_admin=True,
            is_tenant_config_admin=False,
        )
        env = types.SimpleNamespace(ref=lambda xmlid, raise_if_not_found=False: None)
        self.assertEqual(
            contract.build_platform_duty_route_authority_entries(env=env, surface=surface),
            [],
        )

    def test_tenants_endpoint_is_registry_driven(self):
        ops_source = (CONTROLLERS / "platform_ops_controller.py").read_text(encoding="utf-8")
        self.assertIn('"/api/ops/tenants"', ops_source)
        self.assertIn("sc.platform.namespace", ops_source)
        self.assertIn('("audience", "=", "tenant")', ops_source)
        self.assertIn("sc.tenant.company.registration", ops_source)
        # `res.company` is no longer enumerated as the tenant list.
        self.assertNotIn("res.company\"]", ops_source)
        self.assertNotIn("Company.search([])", ops_source)

    def test_job_status_duty_is_readable_without_a_job_id(self):
        """The declared ``platform.job_status.read`` duty is a list entry.

        The platform panel consumes the declared route as a read action without
        a job id.  Requiring ``job_id`` there turned the declared duty into a
        400 on the first click, so the route must answer with a bounded list
        and keep the single-job detail behind an explicit id.
        """
        ops_source = (CONTROLLERS / "platform_ops_controller.py").read_text(encoding="utf-8")
        self.assertNotIn('"job_id required"', ops_source)
        self.assertIn("sc.ops.job", ops_source)
        self.assertIn('"jobs": [self._serialize_job(job) for job in jobs]', ops_source)
        self.assertIn('"count": len(jobs)', ops_source)
        self.assertIn('"job_id must be an integer"', ops_source)

    def test_job_status_duty_uses_the_official_action_renderer(self):
        """The job list is rendered by ActionViewShell, not a hand-built table."""
        contract = _load_contract()
        surface = contract.build_platform_duty_surface(
            is_platform_control_admin=True,
            is_tenant_config_admin=False,
            action_routes={"smart_core.action_sc_ops_job": "/a/321"},
        )
        job = next(row for row in surface["duties"] if row["key"] == "platform.job_status")
        self.assertEqual(job["action_xmlid"], "smart_core.action_sc_ops_job")
        self.assertEqual(job["route"], "/a/321")

        web = Path(__file__).resolve().parents[3] / "frontend" / "apps" / "web" / "src"
        action_source = (web / "components" / "platform-duty" / "dutyAction.ts").read_text(encoding="utf-8")
        panel_source = (web / "components" / "platform-duty" / "PlatformDutyPanel.vue").read_text(encoding="utf-8")
        self.assertIn("'/a/'", action_source)
        self.assertIn("router.push(action.route)", panel_source)
        # No hand-built job table or direct data fetch remains in the panel.
        self.assertNotIn("data-job-status-table", panel_source)
        self.assertNotIn("loadJobStatus", panel_source)

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
        self.assertIn("SPA_ROUTE_PREFIXES = ['/admin/', '/a/']", action_source)

        self.assertIn("resolveDutyAction", panel_source)
        self.assertEqual(1, panel_source.count("router.push("))
        self.assertIn("router.push(action.route)", panel_source)
        self.assertIn("action.kind !== 'navigate'", panel_source)
        # The pre-fix shape: a route of any kind was pushed straight to the router.
        self.assertNotIn('@click="open(duty.route)"', panel_source)
        self.assertNotIn("router.push(route)", panel_source)

    def test_tenant_registry_uses_the_official_action_surface(self):
        contract = _load_contract()
        surface = contract.build_platform_duty_surface(
            is_platform_control_admin=True,
            is_tenant_config_admin=False,
            action_routes={"smart_core.action_sc_platform_namespace": "/a/222"},
        )
        registry = next(
            row for row in surface["duties"] if row["key"] == "platform.tenant_registry"
        )
        self.assertEqual(
            registry["action_xmlid"], "smart_core.action_sc_platform_namespace"
        )
        self.assertEqual(registry["route"], "/a/222")

        web = Path(__file__).resolve().parents[3] / "frontend" / "apps" / "web" / "src"
        panel_source = (web / "components" / "platform-duty" / "PlatformDutyPanel.vue").read_text(encoding="utf-8")
        self.assertNotIn("PlatformTenantRegistry", panel_source)
        self.assertNotIn("TENANT_COLUMNS", panel_source)
        self.assertNotIn("data-tenant-registry-table", panel_source)
        self.assertNotIn("TENANT_REGISTRY_ENDPOINT", panel_source)
        # The registry is the platform namespace model, never a cross-database company read.
        self.assertNotIn("res.company", panel_source)

        views = (ROOT / "views" / "platform_company_access_views.xml").read_text(encoding="utf-8")
        self.assertIn('id="view_sc_platform_namespace_tree"', views)
        self.assertIn('id="view_sc_platform_namespace_form"', views)
        self.assertIn('id="action_sc_platform_namespace"', views)
        self.assertIn('res_model">sc.platform.namespace', views)

    def test_every_platform_duty_opens_an_official_surface(self):
        """No platform duty may fall back to raw API JSON or a bare intent.

        The owner ruling is that the platform console is usable at login: a
        duty either opens a declared window action (rendered by the official
        action shell) or a declared SPA route.  An ``/api/`` route would render
        raw JSON, and an intent is a concept rather than a usable entry.
        """
        contract = _load_contract()
        action_xmlids = contract.declared_platform_action_xmlids()
        self.assertEqual(
            action_xmlids,
            sorted(
                [
                    "smart_core.action_sc_ops_job",
                    "smart_core.action_sc_platform_maintenance_access",
                    "smart_core.action_sc_platform_namespace",
                    "smart_core.action_sc_subscription",
                ]
            ),
        )
        action_routes = {xmlid: "/a/%s" % (900 + index,) for index, xmlid in enumerate(action_xmlids)}
        surface = contract.build_platform_duty_surface(
            is_platform_control_admin=True,
            is_tenant_config_admin=False,
            action_routes=action_routes,
        )
        for duty in surface["duties"]:
            route = str(duty.get("route") or "")
            self.assertTrue(route.startswith("/"), duty)
            self.assertFalse(route.startswith("/api/"), duty)
            self.assertNotIn("intent", duty, duty)

        views = (ROOT / "views" / "platform_company_access_views.xml").read_text(encoding="utf-8")
        self.assertIn('id="view_sc_platform_maintenance_access_tree"', views)
        self.assertIn('id="view_sc_platform_maintenance_access_form"', views)
        self.assertIn('id="action_sc_platform_maintenance_access"', views)
        self.assertIn('res_model">sc.platform.maintenance.access', views)
        # The platform administrator works with logical namespace identity and
        # operator-facing labels; physical database names and internal access
        # ids stay out of the list/form projections.
        namespace_tree = views.split('id="view_sc_platform_namespace_tree"', 1)[1].split('</record>', 1)[0]
        self.assertIn('name="primary_alias"', namespace_tree)
        self.assertNotIn('name="database_name"', namespace_tree)
        maintenance_tree = views.split('id="view_sc_platform_maintenance_access_tree"', 1)[1].split('</record>', 1)[0]
        self.assertIn('name="access_label"', maintenance_tree)
        self.assertNotIn('<field name="name"/>', maintenance_tree)

        web = Path(__file__).resolve().parents[3] / "frontend" / "apps" / "web" / "src"
        panel_source = (web / "components" / "platform-duty" / "PlatformDutyPanel.vue").read_text(encoding="utf-8")
        self.assertNotIn("apiRequest", panel_source)
        self.assertNotIn("<pre", panel_source)
        self.assertNotIn("JSON.stringify", panel_source)

    def test_demo_tenant_name_is_declared_in_the_platform_registry(self):
        seed = (ROOT / "data" / "sc_platform_namespace_seed.xml").read_text(encoding="utf-8")
        self.assertIn("<field name=\"display_name\">四川智汇建设集团有限公司</field>", seed)
        self.assertNotIn("Demo tenant", seed)
        migration = ROOT / "migrations" / "17.0.1.1.16" / "post-migration.py"
        self.assertTrue(migration.exists())
        migration_source = migration.read_text(encoding="utf-8")
        self.assertIn('DEMO_TENANT_NAME = "四川智汇建设集团有限公司"', migration_source)
        self.assertIn("sc_platform_namespace", migration_source)
        self.assertIn("<field name=\"display_name\">平台控制台</field>", seed)
        platform_migration = ROOT / "migrations" / "17.0.1.1.17" / "post-migration.py"
        self.assertTrue(platform_migration.exists())
        platform_source = platform_migration.read_text(encoding="utf-8")
        self.assertIn('PLATFORM_NAMESPACE_NAME = "平台控制台"', platform_source)
        self.assertIn("sc_platform_namespace", platform_source)

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
