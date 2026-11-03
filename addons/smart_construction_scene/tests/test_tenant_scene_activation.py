# -*- coding: utf-8 -*-
import copy
import importlib.util
import json
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
from pathlib import Path


SCENE_DIR = Path(__file__).resolve().parents[1]


def _load(module_name, path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


odoo_mod = sys.modules.setdefault("odoo", types.ModuleType("odoo"))
odoo_mod._ = lambda value, *args, **kwargs: value
addons_pkg = sys.modules.setdefault("odoo.addons", types.ModuleType("odoo.addons"))
addons_pkg.__path__ = [str(SCENE_DIR.parent)]

business_enablement = _load(
    "odoo.addons.smart_construction_scene.services.business_scene_enablement",
    SCENE_DIR / "services/business_scene_enablement.py",
)

tenant_scene_activation = _load(
    "odoo.addons.smart_construction_scene.services.tenant_scene_activation",
    SCENE_DIR / "services" / "tenant_scene_activation.py",
)
scenario_activation_catalog = _load(
    "odoo.addons.smart_construction_scene.services.scenario_activation_catalog",
    SCENE_DIR / "services" / "scenario_activation_catalog.py",
)
workspace_scenario_projection = _load(
    "odoo.addons.smart_construction_scene.services.workspace_scenario_projection",
    SCENE_DIR / "services" / "workspace_scenario_projection.py",
)

product_menu_source = _load(
    "odoo.addons.smart_construction_core.services.product_menu_source",
    SCENE_DIR.parent / "smart_construction_core/services/product_menu_source.py",
)
scene_registry_content = _load(
    "odoo.addons.smart_construction_scene.profiles.scene_registry_content",
    SCENE_DIR / "profiles/scene_registry_content.py",
)


scenario_surface = _load(
    "odoo.addons.smart_construction_core.services.scenario_surface_projection",
    SCENE_DIR.parent / "smart_construction_core/services/scenario_surface_projection.py",
)


route_authority = _load(
    "odoo.addons.smart_core.delivery.runtime_route_authority",
    SCENE_DIR.parent / "smart_core/delivery/runtime_route_authority.py",
)


class ContextEnv:
    """Controlled ORM transport retaining principal while changing context."""
    context = {"lang": "zh_CN", "allowed_company_ids": [1]}

    def __call__(self, *, context):
        bound = copy.copy(self)
        bound.context = context
        bound.company = types.SimpleNamespace(id=context["allowed_company_ids"][0])
        return bound


class TestActualPublicationConsumers(unittest.TestCase):
    """Exercise real publication decoding; only the ORM transport is stubbed."""

    def setUp(self):
        # Keep the raw fixture discoverable by the isolated receipt scanner.
        source_path = SCENE_DIR.parent / "smart_construction_core/data/product_menu_source.json"
        self.assertEqual(source_path, product_menu_source.SOURCE_PATH)
        raw = json.loads(source_path.read_text())
        self.expected = {row["menu_xmlid"]: row["release_state"] for row in raw["entries"]}
        self.entries = scene_registry_content.list_scene_entries()

    def test_resolved_bindings_preserve_every_declared_release_state(self):
        self.assertNotIn("entries", product_menu_source.load_source())
        actual = product_menu_source.load_menu_release_states()
        self.assertEqual(actual, self.expected)
        self.assertIn("released", actual.values())
        self.assertIn("preview", actual.values())

    def test_activation_reads_real_source_without_injected_release_map(self):
        for state in ("released", "preview"):
            menu = next(key for key, value in self.expected.items() if value == state)
            entries = [{"code": "test.scene", "target": {"menu_xmlid": menu}}]
            self.assertEqual(tenant_scene_activation.resolve_product_released(
                "test.scene", entries=entries), state == "released")

    def test_unknown_entry_is_not_published(self):
        self.assertFalse(tenant_scene_activation.resolve_product_released(
            "test.unknown", entries=[{"code": "test.unknown", "target": {"menu_xmlid": "missing.menu"}}]))

    def test_invalid_source_is_not_silently_an_empty_publication(self):
        with patch.object(product_menu_source, "load_source", side_effect=ValueError("invalid publication")):
            with self.assertRaisesRegex(ValueError, "invalid publication"):
                product_menu_source.load_menu_release_states()

    def _handlers_and_env(self, scenes=None, can_manage=False):
        base = types.ModuleType("odoo.addons.smart_core.core.base_handler")
        base.BaseIntentHandler = type("BaseIntentHandler", (), {})
        with patch.dict(sys.modules, {base.__name__: base}):
            handlers = _load("nav01_scenario_activation_handler", SCENE_DIR / "handlers/scenario_activation.py")
        rows = [types.SimpleNamespace(scene_key=row["code"], enabled=True) for row in self.entries]

        class Env(ContextEnv):
            company = types.SimpleNamespace(id=1)
            user = types.SimpleNamespace(company_ids=types.SimpleNamespace(ids=[1]))

            def __getitem__(self, name):
                if name == "sc.scene.company.enablement":
                    return types.SimpleNamespace(search=lambda domain: rows, check_access_rights=lambda operation, raise_exception=False: can_manage)
                if name == "sc.scene":
                    model = types.SimpleNamespace(search=lambda domain: scenes or [])
                    model.sudo = lambda: model
                    return model
                raise AssertionError(f"unexpected ORM access: {name}")

        return handlers, Env()

    def test_catalog_handler_uses_actual_publication(self):
        handlers, env = self._handlers_and_env()
        result = handlers._catalog(env, company_id=1)
        expected = [self.expected.get(row.get("target", {}).get("menu_xmlid")) == "released"
                    for row in self.entries]
        self.assertTrue(any(expected))
        self.assertEqual([row["product_released"] for row in result["rows"]], expected)

    def test_activation_request_group_gate_allows_admin_and_rejects_ordinary_user(self):
        handlers, env = self._handlers_and_env()
        platform = types.ModuleType('odoo.addons.smart_core.security.platform_admin')
        platform.user_is_tenant_config_admin = lambda user: False
        exceptions = types.ModuleType('odoo.exceptions')
        exceptions.AccessError = type('AccessError', (Exception,), {})
        with patch.dict(sys.modules, {platform.__name__: platform, exceptions.__name__: exceptions}):
            policy = _load('activation_request_authorization',
                           SCENE_DIR.parent / 'smart_core/security/intent_authorization.py')
            operation = _load('odoo.addons.smart_core.core.intent_operation_policy',
                             SCENE_DIR.parent / 'smart_core/core/intent_operation_policy.py')
            # Exercise the same authorization function called before dispatch,
            # including its write-intent declaration requirement.
            policy.__package__ = 'odoo.addons.smart_core.security'
            with patch.object(policy, 'registered_handlers', return_value={
                    'scenario.activation.set': handlers.ScenarioActivationSetHandler}):
                self.assertTrue(operation.is_write_intent('scenario.activation.set', {}))
                env.user.has_group = lambda group: group == 'smart_construction_core.group_sc_cap_business_config_admin'
                self.assertTrue(policy.authorize_intent(env, 'scenario.activation.set', {})['allowed'])
                env.user.has_group = lambda group: False
                with self.assertRaises(exceptions.AccessError):
                    policy.authorize_intent(env, 'scenario.activation.set', {})

    def test_actual_catalog_actions_use_native_model_access_rights(self):
        for allowed in (False, True):
            with self.subTest(allowed=allowed):
                handlers, env = self._handlers_and_env(can_manage=allowed)
                result = handlers._catalog(env, company_id=1)
                self.assertEqual(result["company_id"], 1)
                self.assertEqual(len(result["business_scenarios"]), 17)
                actions = [action for row in result["business_scenarios"] for action in row["actions"]]
                self.assertEqual(bool(actions), allowed)

    def test_workspace_handler_uses_actual_publication(self):
        handlers, env = self._handlers_and_env()
        handler = handlers.WorkspaceScenarioProjectionGetHandler()
        handler.env, handler.params = env, {}
        handler._resolve_authorized_scene_candidates = lambda entries, company_id: [row["code"] for row in self.entries]
        result = handler.handle()["data"]
        index = scenario_surface.build_menu_index(scenario_surface.load_surface())
        expected = sum(self.expected.get(row.get("target", {}).get("menu_xmlid")) == "released"
                       and business_enablement.entry_business_enabled(row, index, {}) for row in self.entries)
        self.assertGreater(expected, 0)
        self.assertEqual(result["workspace_candidate_count"], expected)


    def test_actual_handlers_share_menu_bound_business_identity(self):
        handlers, env = self._handlers_and_env()
        catalog = handlers._catalog(env, company_id=1)
        workspace = handlers.WorkspaceScenarioProjectionGetHandler()
        workspace.env, workspace.params = env, {}
        workspace._resolve_authorized_scene_candidates = lambda entries, company_id: []
        projection = workspace.handle()["data"]
        index = scenario_surface.build_menu_index(scenario_surface.load_surface())
        self.assertEqual(len({value["scenario_key"] for value in index.values() if value["location"] == "scenario"}), 17)
        for entry, catalog_row, workspace_row in zip(self.entries, catalog["rows"], projection["rows"]):
            expected = index.get(entry.get("target", {}).get("menu_xmlid"))
            self.assertEqual(catalog_row["product_surface"], expected)
            self.assertEqual(workspace_row["product_surface"], expected)
            self.assertEqual(catalog_row["scene_key"], entry["code"])
            self.assertEqual(workspace_row["scene_key"], entry["code"])

    def test_invalid_surface_does_not_silently_emit_unmapped_catalog(self):
        handlers, env = self._handlers_and_env()
        with patch.object(scenario_surface, "load_surface", side_effect=ValueError("invalid surface")):
            with self.assertRaisesRegex(ValueError, "invalid surface"):
                handlers._catalog(env, company_id=1)

    def test_duplicate_business_keys_are_rejected_even_with_distinct_menus(self):
        surface = {"schema": scenario_surface.SCHEMA, "scenarios": [
            {"key": "same", "intents": {"view": ["test.one"]}},
            {"key": " same ", "intents": {"handle": ["test.two"]}},
        ]}
        with self.assertRaisesRegex(ValueError, "duplicate scenario key"):
            scenario_surface.build_menu_index(surface)
        projected = scenario_surface.project_scenario_navigation(surface=surface, authorized_leaves=[])
        self.assertFalse(projected["ok"])
        self.assertEqual(projected["error_code"], "SURFACE_INVALID")
        self.assertIsNone(projected["tree"])

    def test_invalid_business_keys_cannot_be_coerced_into_identity(self):
        for key in (None, "", "  ", True, 7, [], {}):
            with self.subTest(key=key):
                surface = {"schema": scenario_surface.SCHEMA, "scenarios": [
                    {"key": key, "intents": {"view": ["test.one"]}},
                ]}
                with self.assertRaises(ValueError):
                    scenario_surface.build_menu_index(surface)
        with self.assertRaises(ValueError):
            scenario_surface.build_menu_index({"scenarios": ["not-a-scenario"]})

    def test_catalog_and_workspace_reject_ambiguous_business_surface(self):
        handlers, env = self._handlers_and_env()
        workspace = handlers.WorkspaceScenarioProjectionGetHandler()
        workspace.env, workspace.params = env, {}
        workspace._resolve_authorized_scene_candidates = lambda entries, company_id: []
        surface = {"scenarios": [{"key": "same"}, {"key": "same"}]}
        with patch.object(scenario_surface, "load_surface", return_value=surface):
            with self.assertRaisesRegex(ValueError, "duplicate scenario key"):
                handlers._catalog(env, company_id=1)
            with self.assertRaisesRegex(ValueError, "duplicate scenario key"):
                workspace.handle()

    def test_business_key_cannot_alias_legacy_enablement_key(self):
        index = scenario_surface.build_menu_index(scenario_surface.load_surface())
        menu, location = next((key, value) for key, value in index.items()
                              if value["location"] == "scenario" and value["scenario_key"] != "project.management")
        entries = [{"code": "project.management", "target": {"menu_xmlid": menu}}]
        release = {menu: "released"}
        for enabled_key in ("project.management", location["scenario_key"]):
            with self.subTest(enabled_key=enabled_key):
                enabled = {enabled_key: True}
                catalog = scenario_activation_catalog.build_scenario_activation_catalog(
                    entries=entries, release_state_by_menu=release,
                    tenant_enablement_by_scene=enabled, surface_index=index)
                workspace = workspace_scenario_projection.project_workspace_scenes(
                    entries=entries, release_state_by_menu=release, tenant_enabled_by_scene=enabled,
                    role_scene_candidates=["project.management"], surface_index=index)
                self.assertEqual(catalog["rows"][0]["product_surface"], location)
                self.assertEqual(catalog["rows"][0]["tenant_enabled"], enabled_key == "project.management")
                self.assertEqual(workspace["rows"][0]["workspace_candidate"], enabled_key == "project.management")
                self.assertEqual(enabled, {enabled_key: True})

    def test_unmapped_entry_does_not_infer_identity_from_matching_scene_key(self):
        index = scenario_surface.build_menu_index(scenario_surface.load_surface())
        self.assertIsNone(tenant_scene_activation.resolve_entry_surface(
            {"code": "project.management", "target": {"menu_xmlid": "unknown.menu"}}, index))
        self.assertIsNone(tenant_scene_activation.resolve_entry_surface(
            {"code": "project.management"}, index))

    def test_catalog_scene_versions_do_not_override_menu_qualification(self):
        for version_state in ("STANDARD_RELEASE", "OPTIONAL_CAPABILITY", "PREVIEW", "NOT_READY"):
            with self.subTest(version_state=version_state):
                scenes = [types.SimpleNamespace(code=row["code"], active_version_id=types.SimpleNamespace(
                    product_release_state=version_state)) for row in self.entries]
                handlers, env = self._handlers_and_env(scenes=scenes)
                catalog = handlers._catalog(env, company_id=1)
                workspace = handlers.WorkspaceScenarioProjectionGetHandler()
                workspace.env, workspace.params = env, {}
                workspace._resolve_authorized_scene_candidates = lambda entries, company_id: [row["code"] for row in self.entries]
                projection = workspace.handle()["data"]
                for entry, catalog_row, workspace_row in zip(self.entries, catalog["rows"], projection["rows"]):
                    expected = self.expected.get(entry.get("target", {}).get("menu_xmlid")) == "released"
                    self.assertEqual(catalog_row["product_released"], expected)
                    self.assertEqual(workspace_row["product_released"], expected)
                    self.assertEqual(catalog_row["scene_version_release_state"], version_state)
                    self.assertEqual(catalog_row["release_state"],
                                     self.expected.get(entry.get("target", {}).get("menu_xmlid"), "preview"))

    def test_dependency_diagnosis_requires_menu_qualification_and_published_scene(self):
        diagnosis = _load("nav01_dependency_diagnosis", SCENE_DIR / "services/scenario_dependency_diagnosis.py")
        for menu_state in ("released", "preview"):
            entry = next(row for row in self.entries if self.expected.get(
                row.get("target", {}).get("menu_xmlid")) == menu_state)
            for scene_state in ("published", "draft", None):
                with self.subTest(menu_state=menu_state, scene_state=scene_state):
                    scene = types.SimpleNamespace(id=1, state=scene_state) if scene_state else False
                    company = types.SimpleNamespace(id=1)
                    company.exists = lambda: company
                    class Env(ContextEnv):
                        cr = types.SimpleNamespace(now=lambda: "controlled-clock")
                        def __getitem__(self, name):
                            if name == "sc.scene":
                                model = types.SimpleNamespace(search=lambda domain, limit: scene)
                                model.sudo = lambda: model
                                return model
                            if name == "res.company":
                                return types.SimpleNamespace(browse=lambda company_id: company)
                            raise AssertionError(name)
                    result = diagnosis.diagnose_scenario_dependencies(Env(), scene_key=entry["code"], company_id=1)
                    self.assertEqual(result["enable_allowed"], menu_state == "released" and scene_state == "published")
                    evidence = result["dependencies"][0]["evidence"]
                    self.assertEqual(evidence["product_released"], menu_state == "released")
                    self.assertEqual(evidence["scene_published"], scene_state == "published")

    def test_all_handlers_reject_invalid_company_before_read_or_write(self):
        handlers, env = self._handlers_and_env()
        class NoAccessEnv:
            company, user = env.company, env.user
            def __getitem__(self, name):
                raise AssertionError(f"rejected request accessed ORM: {name}")
        for handler_class in (handlers.ScenarioActivationCatalogGetHandler,
                              handlers.WorkspaceScenarioProjectionGetHandler,
                              handlers.ScenarioActivationSetHandler):
            for requested, code in ((9, 403), ("bad", 400), (True, 400),
                                    (False, 400), (1.5, 400), ([], 400)):
                with self.subTest(handler=handler_class.__name__, requested=requested):
                    handler = handler_class()
                    handler.env, handler.params = NoAccessEnv(), {}
                    result = handler.handle({"company_id": requested, "scene_key": "test.scene", "enabled": True})
                    self.assertFalse(result["ok"])
                    self.assertEqual(result["error"]["code"], code)

    def test_workspace_queries_the_requested_allowed_company(self):
        handlers, env = self._handlers_and_env()
        domains = []
        class CompanyEnv(ContextEnv):
            company = env.company
            user = types.SimpleNamespace(company_ids=types.SimpleNamespace(ids=[1, 2]))
            def __getitem__(self, name):
                self_name = name
                def search(domain):
                    domains.append((self_name, domain))
                    if self.company.id != 2 or self.context["allowed_company_ids"] != [2]:
                        raise AssertionError("enablement query did not switch ORM company")
                    return []
                return types.SimpleNamespace(search=search)
        handler = handlers.WorkspaceScenarioProjectionGetHandler()
        handler.env, handler.params = CompanyEnv(), {}
        handler._resolve_authorized_scene_candidates = lambda entries, company_id: []
        self.assertTrue(handler.handle({"company_id": 2})["ok"])
        self.assertEqual(domains, [("sc.scene.company.enablement", [("company_id", "=", 2)])])

    def test_activation_rejects_ambiguous_boolean_before_orm(self):
        handlers, env = self._handlers_and_env()
        class NoAccessEnv:
            company, user = env.company, env.user
            def __getitem__(self, name):
                raise AssertionError(f"invalid mutation accessed ORM: {name}")
        handler = handlers.ScenarioActivationSetHandler()
        handler.env, handler.params = NoAccessEnv(), {}
        for value in (None, "false", "true", "", 0, 1, 0.0, 1.0, [], {}, [False]):
            with self.subTest(value=value):
                result = handler.handle({"scene_key": "test.scene", "enabled": value})
                self.assertFalse(result["ok"])
                self.assertEqual(result["error"]["code"], 400)
        self.assertEqual(handler.handle({"scene_key": "test.scene"})["error"]["code"], 400)

    def test_activation_rejects_invalid_payload_without_fallback_mutation(self):
        handlers, _ = self._handlers_and_env()
        handler = handlers.ScenarioActivationSetHandler()
        # Even a populated fallback must not turn an explicit empty request into
        # a mutation. No env is installed: rejection precedes company/ORM reads.
        handler.params = {"scene_key": "test.scene", "enabled": True}
        for payload in ({}, [], "", "false", False, 0, [1]):
            with self.subTest(payload=payload):
                result = handler.handle(payload)
                self.assertFalse(result["ok"])
                self.assertEqual(result["error"]["code"], 400)

    def test_activation_rejects_coerced_scene_identifiers(self):
        handlers, _ = self._handlers_and_env()
        handler = handlers.ScenarioActivationSetHandler()
        handler.params = {}
        for key in (None, "", "  ", True, 1, [], {}, ["test.scene"]):
            with self.subTest(key=key):
                result = handler.handle({"scene_key": key, "enabled": False})
                self.assertFalse(result["ok"])
                self.assertEqual(result["error"]["code"], 400)

    def test_explicit_disable_reaches_existing_record_without_enable_diagnosis(self):
        handlers, env = self._handlers_and_env()
        calls = []
        record = types.SimpleNamespace(enabled=True)
        def set_enabled(value):
            calls.append(value)
            record.enabled = value
        record.set_enabled = set_enabled
        company = types.SimpleNamespace(id=1)
        company.exists = lambda: company
        class Env(ContextEnv):
            company, user = env.company, env.user
            def __getitem__(self, name):
                if name == "res.company":
                    return types.SimpleNamespace(browse=lambda company_id: company)
                if name == "sc.scene.company.enablement":
                    def search(domain, limit):
                        self_domain = [("company_id", "=", 1), ("scene_key", "=", "test.scene")]
                        if domain != self_domain or limit != 1:
                            raise AssertionError(domain)
                        return record
                    return types.SimpleNamespace(search=search)
                raise AssertionError(f"disable must not read enable dependencies: {name}")
        handler = handlers.ScenarioActivationSetHandler()
        handler.env, handler.params = Env(), {"scene_key": "test.scene", "enabled": False}
        for payload in ({"scene_key": " test.scene ", "enabled": False}, None):
            result = handler.handle(payload)
            self.assertTrue(result["ok"])
            self.assertIs(result["data"]["enabled"], False)
            self.assertEqual(result["data"]["scene_key"], "test.scene")
        self.assertEqual(calls, [False, False])

    def test_catalog_binds_company_without_changing_principal_or_language(self):
        handlers, env = self._handlers_and_env()
        env.user = types.SimpleNamespace(id=7, company_ids=types.SimpleNamespace(ids=[1, 2]))
        handler = handlers.ScenarioActivationCatalogGetHandler()
        handler.env, handler.params = env, {}
        calls = []
        def catalog(bound, company_id):
            calls.append((bound.company.id, company_id, bound.user, bound.context))
            return {"rows": []}
        with patch.object(handlers, "_catalog", side_effect=catalog):
            self.assertTrue(handler.handle({"company_id": 2})["ok"])
        self.assertEqual(calls, [(2, 2, env.user, {"lang": "zh_CN", "allowed_company_ids": [2]})])
        self.assertEqual(env.company.id, 1)
        self.assertEqual(env.context["allowed_company_ids"], [1])

    def test_activation_binds_diagnosis_create_and_write_to_requested_company(self):
        handlers, original = self._handlers_and_env()
        events = []
        class Env(ContextEnv):
            company = original.company
            user = types.SimpleNamespace(id=7, company_ids=types.SimpleNamespace(ids=[1, 2]))
            def __getitem__(self, name):
                if self.company.id != 2 or self.context["allowed_company_ids"] != [2]:
                    raise AssertionError("mutation used wrong company context")
                if name == "res.company":
                    company = types.SimpleNamespace(id=2)
                    company.exists = lambda: company
                    return types.SimpleNamespace(browse=lambda company_id: company)
                if name == "sc.scene.company.enablement":
                    def search(domain, limit):
                        events.append(("search", domain))
                        return False
                    def create(values):
                        events.append(("create", values))
                        record = types.SimpleNamespace(enabled=False)
                        def set_enabled(value):
                            events.append(("write", self.company.id, self.user.id, value))
                            record.enabled = value
                        record.set_enabled = set_enabled
                        return record
                    return types.SimpleNamespace(search=search, create=create)
                raise AssertionError(name)
        module = types.ModuleType("odoo.addons.smart_construction_scene.services.scenario_dependency_diagnosis")
        def diagnose(bound, *, scene_key, company_id):
            events.append(("diagnose", bound.company.id, company_id, bound.user.id))
            return {"enable_allowed": True}
        module.diagnose_scenario_dependencies = diagnose
        handler = handlers.ScenarioActivationSetHandler()
        handler.env, handler.params = Env(), {}
        with patch.dict(sys.modules, {module.__name__: module}):
            result = handler.handle({"company_id": 2, "scene_key": "test.scene", "enabled": True})
        self.assertTrue(result["ok"])
        self.assertEqual(events, [
            ("search", [("company_id", "=", 2), ("scene_key", "=", "test.scene")]),
            ("diagnose", 2, 2, 7),
            ("create", {"company_id": 2, "scene_key": "test.scene", "enabled": False}),
            ("write", 2, 7, True),
        ])
        self.assertEqual(handler.env.company.id, 1)

    def test_enablement_is_created_only_after_successful_diagnosis(self):
        handlers, env = self._handlers_and_env()
        module = types.ModuleType("odoo.addons.smart_construction_scene.services.scenario_dependency_diagnosis")
        for allowed in (False, True):
            with self.subTest(allowed=allowed):
                events = []
                record = types.SimpleNamespace(enabled=False)
                def set_enabled(value):
                    events.append("set_enabled")
                    record.enabled = value
                record.set_enabled = set_enabled
                def create(values):
                    events.append("create")
                    return record
                company = types.SimpleNamespace(id=1)
                company.exists = lambda: company
                class EnablementEnv(ContextEnv):
                    company, user = env.company, env.user
                    def __getitem__(self, name):
                        if name == "res.company":
                            return types.SimpleNamespace(browse=lambda company_id: company)
                        if name == "sc.scene.company.enablement":
                            return types.SimpleNamespace(search=lambda domain, limit: False, create=create)
                        raise AssertionError(name)
                def diagnose(*args, **kwargs):
                    events.append("diagnose")
                    return {"enable_allowed": allowed, "blocking_dependencies": ["missing"]}
                module.diagnose_scenario_dependencies = diagnose
                handler = handlers.ScenarioActivationSetHandler()
                handler.env, handler.params = EnablementEnv(), {}
                with patch.dict(sys.modules, {module.__name__: module}):
                    result = handler.handle({"scene_key": "test.scene", "enabled": True})
                self.assertEqual(result["ok"], allowed)
                self.assertEqual(events, ["diagnose", "create", "set_enabled"] if allowed else ["diagnose"])
                if not allowed:
                    self.assertEqual(result["error"]["code"], 409)


class TestDiagnosisCompanyContext(unittest.TestCase):
    def setUp(self):
        base = types.ModuleType("odoo.addons.smart_core.core.base_handler")
        base.BaseIntentHandler = type("BaseIntentHandler", (), {})
        with patch.dict(sys.modules, {base.__name__: base}):
            module = _load("nav01_dependency_handler", SCENE_DIR / "handlers/scenario_dependency.py")
        self.handler = module.ScenarioDependencyDiagnosisGetHandler()
        class Env(ContextEnv):
            company = types.SimpleNamespace(id=1)
            user = types.SimpleNamespace(id=7, company_ids=types.SimpleNamespace(ids=[1, 2]))
            def __getitem__(self, name):
                raise AssertionError(f"unexpected ORM access: {name}")
        self.handler.env = Env()
        self.handler.params = {"scene_key": "old.scene", "company_id": 1}

    def test_payload_precedence_and_company_binding(self):
        module = types.ModuleType("odoo.addons.smart_construction_scene.services.scenario_dependency_diagnosis")
        calls = []
        def diagnose(env, *, scene_key, company_id):
            calls.append((scene_key, company_id, env.company.id, env.user.id, env.context))
            return {"scene_key": scene_key, "company_id": company_id}
        module.diagnose_scenario_dependencies = diagnose
        with patch.dict(sys.modules, {module.__name__: module}):
            result = self.handler.handle({"scene_key": " new.scene ", "company_id": 2},
                                         params={"scene_key": "ignored.scene", "company_id": 1})
            self.assertEqual(result["data"], {"scene_key": "new.scene", "company_id": 2})
            self.assertTrue(self.handler.handle(params={"scene_key": "params.scene"})["ok"])
            self.assertTrue(self.handler.handle()["ok"])
        self.assertEqual(calls[0], ("new.scene", 2, 2, 7, {"lang": "zh_CN", "allowed_company_ids": [2]}))
        self.assertEqual([call[0] for call in calls], ["new.scene", "params.scene", "old.scene"])
        self.assertEqual(self.handler.env.company.id, 1)

    def test_invalid_company_is_rejected_before_service_or_orm(self):
        for company, code in ((9, 403), (True, 400), (False, 400), (1.2, 400), ([], 400), ("bad", 400)):
            with self.subTest(company=company):
                result = self.handler.handle({"scene_key": "test.scene", "company_id": company})
                self.assertFalse(result["ok"])
                self.assertEqual(result["error"]["code"], code)

    def test_invalid_payload_does_not_inherit_previous_parameters(self):
        for payload in ({}, [], False, 0, "", {"scene_key": True}, {"scene_key": ["test.scene"]}):
            with self.subTest(payload=payload):
                result = self.handler.handle(payload)
                self.assertFalse(result["ok"])
                self.assertEqual(result["error"]["code"], 400)

    def test_native_access_error_is_not_retried_with_elevation(self):
        module = types.ModuleType("odoo.addons.smart_construction_scene.services.scenario_dependency_diagnosis")
        def denied(*args, **kwargs):
            raise PermissionError("native company data scope denied")
        module.diagnose_scenario_dependencies = denied
        with patch.dict(sys.modules, {module.__name__: module}):
            with self.assertRaisesRegex(PermissionError, "native company data scope denied"):
                self.handler.handle({"scene_key": "test.scene", "company_id": 2})


class TestAuthorizedWorkspaceProjection(unittest.TestCase):
    def setUp(self):
        self.entries = [
            {"code": "project", "target": {"menu_xmlid": "test.project", "action_xmlid": "test.project_action"}},
            {"code": "finance", "target": {"menu_xmlid": "test.finance"}},
            {"code": "other", "target": {"menu_xmlid": "test.other"}},
        ]
        self.refs = {}
        for name, menu_id, action_id in (("project", 1, 11), ("finance", 2, 22), ("other", 3, 33)):
            action = types.SimpleNamespace(_name="ir.actions.act_window", id=action_id)
            self.refs[f"test.{name}_action"] = action
            self.refs[f"test.{name}"] = types.SimpleNamespace(_name="ir.ui.menu", id=menu_id, action=action)
        self.authority = {"primary_actions": [{"menu_id": 1, "action_id": 11}],
                          "contextual_actions": [{"menu_id": 2, "action_id": 22}]}

    def resolve_ref(self, xmlid, raise_if_not_found=False):
        return self.refs.get(xmlid, False)

    def project(self, authority=None, entries=None):
        return workspace_scenario_projection.authorized_scene_candidates(
            entries=self.entries if entries is None else entries,
            authority=self.authority if authority is None else authority,
            resolve_ref=self.resolve_ref,
        )

    def test_authorized_union_deduplicates_and_excludes_other_routes(self):
        self.assertEqual(self.project(entries=self.entries + self.entries), ["project", "finance"])

    def test_container_or_different_action_does_not_authorize_entry(self):
        self.assertEqual(self.project(authority={
            "primary_actions": [{"menu_id": 1, "action_id": 99}],
            "menu_containers": [{"menu_id": 2}],
        }), [])

    def test_unknown_or_wrong_reference_never_falls_back_to_menu_action(self):
        for ref in (False, self.refs["test.finance"], types.SimpleNamespace(_name="ir.actions.act_window", id=0)):
            with self.subTest(ref=ref):
                self.refs["test.project_action"] = ref
                self.assertEqual(self.project(), ["finance"])

    def test_missing_authority_does_not_resolve_native_menus(self):
        def forbidden(*args, **kwargs):
            raise AssertionError("native lookup cannot substitute for authority")
        for authority in ({}, None, []):
            self.assertEqual(workspace_scenario_projection.authorized_scene_candidates(
                entries=self.entries, authority=authority, resolve_ref=forbidden), [])

    def test_actual_handler_binds_company_and_observes_authority_revocation(self):
        fixture = TestActualPublicationConsumers()
        fixture.setUp()
        handlers, _ = fixture._handlers_and_env()
        authority_by_company = {1: self.authority, 2: {"primary_actions": [{"menu_id": 3, "action_id": 33}]}}
        queries = []
        context_calls = []
        refs = self.refs
        class Env(ContextEnv):
            def __init__(self, company_id):
                self.company = types.SimpleNamespace(id=company_id)
                self.user = types.SimpleNamespace(id=7, company_ids=types.SimpleNamespace(ids=[1, 2]))
            def ref(self, xmlid, raise_if_not_found=False):
                return refs.get(xmlid, False)
            def __getitem__(self, name):
                if name == "sc.product.policy":
                    def with_context(**kwargs):
                        context_calls.append(kwargs)
                        return types.SimpleNamespace(env=Env(kwargs["allowed_company_ids"][0]))
                    return types.SimpleNamespace(
                        with_context=with_context,
                        published_route_authority=lambda: authority_by_company[self.company.id],
                        _apply_company_route_scope=lambda authority: authority,
                    )
                if name == "sc.scene.company.enablement":
                    def search(domain):
                        queries.append(domain)
                        return [types.SimpleNamespace(scene_key=key, enabled=True)
                                for key in ("business.v1:project", "business.v1:finance", "business.v1:other")]
                    return types.SimpleNamespace(search=search)
                raise AssertionError(name)
        handler = handlers.WorkspaceScenarioProjectionGetHandler()
        handler.env, handler.params = Env(1), {}
        release = {f"test.{key}": "released" for key in ("project", "finance", "other")}
        with patch.object(scene_registry_content, "list_scene_entries", return_value=self.entries), \
             patch.object(product_menu_source, "load_menu_release_states", return_value=release), \
             patch.object(handlers, "_product_surface_index", return_value={
                 f"test.{key}": {"location": "scenario", "scenario_key": key}
                 for key in ("project", "finance", "other")}):
            def candidates(company_id):
                result = handler.handle({"company_id": company_id})
                self.assertTrue(result["ok"])
                return [row["scene_key"] for row in result["data"]["rows"] if row["workspace_candidate"]]
            self.assertEqual(candidates(1), ["project", "finance"])
            self.assertEqual(candidates(2), ["other"])
            authority_by_company[1] = {"primary_actions": [{"menu_id": 1, "action_id": 11}]}
            self.assertEqual(candidates(1), ["project"])
            authority_by_company[1] = {}
            self.assertEqual(candidates(1), [])
        self.assertEqual(context_calls, [{"allowed_company_ids": [cid]} for cid in (1, 2, 1, 1)])
        self.assertEqual(queries, [[("company_id", "=", cid)] for cid in (1, 2, 1, 1)])
        self.assertEqual(handler.env.user.id, 7)


class TestNativeAuthorityGuardScope(unittest.TestCase):
    def setUp(self):
        # Consume the source explicitly so isolated snapshots bind this
        # repository-level dependency as well as the addon module tree.
        guard_path = SCENE_DIR.parents[1] / "scripts/verify/fact_layer_authority_guard.py"
        self.guard = types.ModuleType("nav01_fact_guard")
        self.guard.__file__ = str(guard_path)
        exec(compile(guard_path.read_text(encoding="utf-8"), str(guard_path), "exec"),
             self.guard.__dict__)

    def test_native_field_groups_do_not_count_as_entry_lists(self):
        guard = self.guard
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "view.xml").write_text('<odoo><record id="view" model="ir.ui.view"><field name="arch" type="xml"><form><field name="x" groups="test.group_sc_role_executive"/></form></field></record></odoo>')
            with patch.object(guard, "MODULE_ROOT", root), patch.object(guard, "ROOT", root):
                self.assertEqual(guard._role_group_direct_authorization_violations(), [])

    def test_role_bound_entry_carriers_still_fail(self):
        guard = self.guard
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "entry.xml").write_text('<odoo><menuitem id="menu" groups="test.group_sc_role_manager"/><record id="action" model="ir.actions.act_window"><field name="groups_id" eval="test.group_sc_role_manager"/></record><record id="view" model="ir.ui.view"><field name="groups_id" eval="test.group_sc_role_manager"/></record></odoo>')
            with patch.object(guard, "MODULE_ROOT", root), patch.object(guard, "ROOT", root):
                self.assertEqual({row["carrier"] for row in guard._role_group_direct_authorization_violations()},
                                 {"menu", "action", "view"})


class TestBusinessEnablementAuthority(unittest.TestCase):
    def setUp(self):
        self.index = {"test.project": {"location": "scenario", "scenario_key": "project.management"},
                      "test.finance": {"location": "scenario", "scenario_key": "finance"},
                      "test.home": {"location": "horizontal", "scenario_key": ""},
                      "test.admin": {"location": "platform", "scenario_key": ""}}
        self.entries = [{"code": "legacy.project", "target": {"menu_xmlid": "test.project"}},
                        {"code": "alias.project", "target": {"menu_xmlid": "test.project"}},
                        {"code": "unknown.legacy", "target": {"menu_xmlid": "test.unknown"}}]
        self.authority = {"primary_actions": [
            {"menu_id": 1, "action_id": 11, "menu_xmlid": "test.project"},
            {"menu_id": 2, "action_id": 22, "menu_xmlid": "test.finance"},
            {"menu_id": 3, "action_id": 33, "menu_xmlid": "test.home"}],
            "admin_actions": [{"menu_id": 4, "action_id": 44, "menu_xmlid": "test.admin"}],
            "contextual_actions": [{"menu_id": 0, "action_id": 55, "scene_key": "alias.project"}]}

    def filtered(self, enabled, authority=None):
        return business_enablement.filter_business_authority(
            self.authority if authority is None else authority, surface_index=self.index,
            enabled=enabled, entries=self.entries, menu_xmlids_by_id={1: "test.project"})

    def test_initialization_preserves_only_existing_authorized_internal_routes(self):
        self.entries.append({"code": "test.setup", "enablement_scope": "enterprise_initialization"})
        row = {"action_id": 88, "menu_id": 0, "scene_key": "test.setup",
               "source": "scene_internal_action_authority", "allowed": True}
        result = self.filtered({}, {"contextual_actions": [row]})
        self.assertEqual(result["contextual_actions"], [row])
        self.assertEqual(self.filtered({}, {})["contextual_actions"], [])
        for change in ({"allowed": False}, {"source": "client"},
                       {"menu_xmlid": "test.project"}):
            with self.subTest(change=change):
                result = self.filtered({}, {"contextual_actions": [{**row, **change}]})
                self.assertEqual(result["contextual_actions"], [])
        denied = {**row, "route_kind": "DENIED", "allowed_operation": "none"}
        self.assertEqual(self.filtered({}, {"denied_actions": [denied]})["denied_actions"], [denied])

    def test_route_cannot_self_declare_initialization_scope(self):
        row = {"action_id": 88, "scene_key": "unknown.legacy", "allowed": True,
               "source": "scene_internal_action_authority", "enablement_scope": "enterprise_initialization"}
        self.assertEqual(self.filtered({}, {"contextual_actions": [row]})["contextual_actions"], [])

    def test_legacy_same_name_never_enables_business_scenario(self):
        states = business_enablement.business_states({"project.management": True, "legacy.project": True})
        self.assertEqual(states, {})
        result = self.filtered(states)
        self.assertEqual(route_authority.published_pairs(result), {(3, 33), (4, 44)})
        self.assertEqual(len(result["denied_actions"]), 3)

    def test_explicit_enable_then_disable_narrows_all_alias_routes(self):
        original = copy.deepcopy(self.authority)
        enabled = business_enablement.business_states({"business.v1:project.management": True})
        self.assertEqual(route_authority.published_pairs(self.filtered(enabled)), {(1, 11), (3, 33), (4, 44), (0, 55)})
        enabled["project.management"] = False
        self.assertEqual(route_authority.published_pairs(self.filtered(enabled)), {(3, 33), (4, 44)})
        self.assertEqual(self.authority, original)

    def test_every_bucket_is_narrowed_without_granting_authority(self):
        for bucket in business_enablement.AUTHORITY_BUCKETS:
            with self.subTest(bucket=bucket):
                authority = {bucket: [{"menu_id": 1, "action_id": 11}]}
                self.assertEqual(self.filtered({}, authority)[bucket], [])
                self.assertEqual(self.filtered({"project.management": True}, authority)[bucket], authority[bucket])
        self.assertEqual(route_authority.published_pairs(self.filtered({"project.management": True}, {})), set())

    def test_unknown_legacy_binding_fails_closed(self):
        result = self.filtered({}, {"contextual_actions": [{"action_id": 99, "scene_key": "unknown.legacy"}]})
        self.assertEqual(result["contextual_actions"], [])

    def test_action_only_route_obeys_native_business_membership(self):
        row = {"menu_id": 0, "action_id": 11}
        for enabled, expected in (({}, []), ({"project.management": True}, [row]),
                                  ({"project.management": False}, [])):
            with self.subTest(enabled=enabled):
                result = business_enablement.filter_business_authority(
                    {"contextual_actions": [row]}, surface_index=self.index, enabled=enabled,
                    entries=self.entries, menu_xmlids_by_id={},
                    menu_xmlids_by_action={11: ["test.project"]})
                self.assertEqual(result["contextual_actions"], expected)

    def test_shared_action_keeps_existing_authority_if_any_native_scope_enabled(self):
        row = {"action_id": 11}
        for menus, enabled, expected in (
            (["test.project", "test.finance"], {}, []),
            (["test.project", "test.finance"], {"finance": True}, [row]),
            (["test.project", "test.home"], {}, [row]),
            (["test.project", "test.admin"], {}, [row]),
        ):
            with self.subTest(menus=menus, enabled=enabled):
                source = {"contextual_actions": [row]}
                result = business_enablement.filter_business_authority(
                    source, surface_index=self.index, enabled=enabled,
                    entries=self.entries, menu_xmlids_by_id={}, menu_xmlids_by_action={11: menus})
                self.assertEqual(result["contextual_actions"], expected)
                self.assertEqual(source, {"contextual_actions": [row]})

    def test_action_membership_does_not_override_explicit_disabled_menu_or_legacy(self):
        rows = [{"menu_id": 1, "action_id": 11},
                {"action_id": 11, "scene_key": "alias.project"},
                {"action_id": 11, "scene_key": "unknown.legacy"}]
        result = business_enablement.filter_business_authority(
            {"contextual_actions": rows}, surface_index=self.index, enabled={"finance": True},
            entries=self.entries, menu_xmlids_by_id={1: "test.project"},
            menu_xmlids_by_action={11: ["test.project", "test.finance"]})
        self.assertEqual(result["contextual_actions"], [])

    def test_action_scope_never_manufactures_routes_or_denies_unrelated_platform_action(self):
        for source in ({}, {"admin_actions": [{"action_id": 99}]}):
            result = business_enablement.filter_business_authority(
                source, surface_index=self.index, enabled={"project.management": True},
                entries=self.entries, menu_xmlids_by_id={}, menu_xmlids_by_action={11: ["test.project"]})
            self.assertEqual(route_authority.published_pairs(result), route_authority.published_pairs(source))

    def test_actual_catalog_separates_all_business_keys_from_legacy_records(self):
        surface = scenario_surface.load_surface()
        release = product_menu_source.load_menu_release_states()
        legacy = {row["key"]: True for row in surface["scenarios"]}
        rows = business_enablement.business_catalog(surface, release, legacy)
        self.assertEqual(len(rows), 17)
        self.assertFalse(any(row["tenant_enabled"] for row in rows))
        key = next(row["scene_key"] for row in rows if row["product_released"])
        rows = business_enablement.business_catalog(surface, release, {business_enablement.business_key(key): True})
        self.assertEqual([row["scene_key"] for row in rows if row["tenant_enabled"]], [key])
        self.assertTrue(tenant_scene_activation.resolve_product_released(business_enablement.business_key(key)))
        self.assertFalse(tenant_scene_activation.resolve_product_released("business.v1:unknown"))

    def test_workspace_uses_same_business_decision_without_native_grants(self):
        release = {menu: "released" for menu in self.index}
        for enabled in ({}, {"project.management": True}, {"project.management": False}):
            result = workspace_scenario_projection.project_workspace_scenes(
                entries=self.entries, release_state_by_menu=release, tenant_enabled_by_scene={"legacy.project": True},
                business_enabled_by_scene=enabled, role_scene_candidates=["legacy.project"], surface_index=self.index)
            self.assertEqual([row["scene_key"] for row in result["rows"] if row["workspace_candidate"]],
                             ["legacy.project"] if enabled.get("project.management") else [])

    def test_p1_model_reads_current_company_and_preserves_native_principal(self):
        class Parent:
            def _apply_company_route_scope(self, authority):
                return authority
        with patch.object(odoo_mod, "api", types.SimpleNamespace(model=lambda fn: fn), create=True), \
             patch.object(odoo_mod, "models", types.SimpleNamespace(Model=Parent), create=True):
            module = _load("nav01_business_policy_model", SCENE_DIR / "models/product_policy.py")
        fixture = self
        states = {1: {"business.v1:project.management": True}, 2: {}}
        queries = []
        class Env:
            user = types.SimpleNamespace(id=7)
            def __init__(self, company_id):
                self.company = types.SimpleNamespace(id=company_id)
            def __getitem__(self, name):
                if name != "sc.scene.company.enablement":
                    raise AssertionError(name)
                def search(domain):
                    queries.append((self.company.id, self.user.id, domain))
                    return [types.SimpleNamespace(scene_key=key, enabled=value)
                            for key, value in states[self.company.id].items()]
                return types.SimpleNamespace(search=search)
            def ref(self, xmlid, raise_if_not_found=False):
                return types.SimpleNamespace(id=list(fixture.index).index(xmlid) + 1, _name="ir.ui.menu",
                                             action=types.SimpleNamespace(id=11 if xmlid == "test.project" else 99))
        record = module.ScProductPolicy()
        with patch.object(scenario_surface, "load_surface", return_value={}), \
             patch.object(scenario_surface, "build_menu_index", return_value=self.index), \
             patch.object(scene_registry_content, "list_scene_entries", return_value=self.entries):
            for company_id, expected in ((1, True), (2, False), (1, True)):
                record.env = Env(company_id)
                source = copy.deepcopy(self.authority)
                source["contextual_actions"].append({"action_id": 11})
                authority = record._apply_company_route_scope(source)
                self.assertEqual((0, 11) in route_authority.published_pairs(authority), expected)
                self.assertIs(route_authority.menu_publication_decision(authority, 1, 11), expected)
            states[1].clear()
            self.assertFalse(route_authority.menu_publication_decision(record._apply_company_route_scope(self.authority), 1, 11))
        self.assertEqual(queries, [(cid, 7, [("company_id", "=", cid)]) for cid in (1, 2, 1, 1)])

    def test_business_mutation_cannot_overwrite_same_named_legacy_record(self):
        fixture = TestActualPublicationConsumers()
        fixture.setUp()
        handlers, original = fixture._handlers_and_env()
        stored = {"project.management": True}
        class Env(ContextEnv):
            company, user = original.company, original.user
            def __getitem__(self, name):
                if name == "res.company":
                    company = types.SimpleNamespace(id=1)
                    company.exists = lambda: company
                    return types.SimpleNamespace(browse=lambda cid: company)
                if name == "sc.scene.company.enablement":
                    def create(values):
                        key = values["scene_key"]
                        stored[key] = values["enabled"]
                        return record(key)
                    def record(key):
                        result = types.SimpleNamespace(enabled=stored[key])
                        def set_enabled(value):
                            stored[key] = result.enabled = value
                        result.set_enabled = set_enabled
                        return result
                    def search(domain, limit):
                        key = next(value for field, op, value in domain if field == "scene_key")
                        return record(key) if key in stored else False
                    return types.SimpleNamespace(search=search, create=create)
                raise AssertionError(name)
        handler = handlers.ScenarioActivationSetHandler()
        handler.env, handler.params = Env(), {}
        catalog = {"business_scenarios": [{"scene_key": "project.management", "product_released": True}]}
        with patch.object(handlers, "_catalog", return_value=catalog):
            for enabled in (True, False):
                result = handler.handle({"scene_key": "project.management", "enablement_scope": "business.v1", "enabled": enabled})
                self.assertTrue(result["ok"])
                self.assertEqual(result["data"]["enablement_scope"], "business.v1")
                self.assertIs(stored["business.v1:project.management"], enabled)
                self.assertIs(stored["project.management"], True)
            self.assertEqual(handler.handle({"scene_key": "unknown", "enablement_scope": "business.v1", "enabled": True})["error"]["code"], 404)
            self.assertEqual(handler.handle({"scene_key": "business.v1:project.management", "enabled": False})["error"]["code"], 400)

    def test_actual_navigation_filter_matches_business_route_decisions(self):
        module = _load("nav01_native_navigation_fixture",
                       SCENE_DIR.parent / "smart_core/tests/test_delivery_menu_entry_target.py")
        nav = [{"menu_id": mid, "action_id": aid, "route": f"/a/{aid}", "children": []}
               for mid, aid in ((1, 11), (2, 22), (3, 33))]
        for states, expected in (({}, [3]), ({"project.management": True}, [1, 3]),
                                 ({"finance": True}, [2, 3])):
            with self.subTest(states=states):
                filtered = module.menu_service.MenuService.filter_nav_by_route_authority(nav, self.filtered(states))
                self.assertEqual([row["menu_id"] for row in filtered], expected)

    def test_all_business_scenarios_project_without_legacy_registry_entries(self):
        module = _load("nav01_workspace_native_navigation_fixture",
                       SCENE_DIR.parent / "smart_core/tests/test_delivery_menu_entry_target.py")
        surface = scenario_surface.load_surface()
        index = scenario_surface.build_menu_index(surface)
        nav, actions, by_id = [], [], {}
        for menu_id, (xmlid, location) in enumerate(index.items(), 1):
            if location["location"] != "scenario":
                continue
            action_id = menu_id + 1000
            row = {"menu_xmlid": xmlid, "menu_id": menu_id, "action_id": action_id}
            actions.append(row)
            by_id[menu_id] = xmlid
            nav.append({**row, "route": f"/a/{action_id}?menu_id={menu_id}",
                        "name": xmlid, "children": []})
        keys = [row["key"] for row in surface["scenarios"]]
        self.assertEqual(len(keys), 17)
        for enabled_keys in (keys, [], *([key] for key in keys)):
            with self.subTest(enabled=enabled_keys):
                authority = business_enablement.filter_business_authority(
                    {"primary_actions": actions}, surface_index=index,
                    enabled={key: True for key in enabled_keys}, entries=[], menu_xmlids_by_id=by_id)
                filtered_nav = module.menu_service.MenuService.filter_nav_by_route_authority(nav, authority)
                projection = scenario_surface.project_authorized_nav(
                    nav=filtered_nav, route_authority=authority, surface=surface)
                self.assertTrue(projection["ok"])
                scenarios = [scene for domain in projection["tree"]["domains"] for scene in domain["scenarios"]]
                self.assertEqual({scene["key"] for scene in scenarios}, set(enabled_keys))
                for scene in scenarios:
                    for intent in scene["intents"]:
                        for entry in intent["entries"]:
                            self.assertIn((entry["menu_id"], entry["action_id"]),
                                          route_authority.published_pairs(authority))
        # Enabled scenarios cannot create entries when the native authority is empty.
        self.assertEqual(scenario_surface.project_authorized_nav(
            nav=[], route_authority={}, surface=surface)["tree"]["domains"], [])

    def test_management_actions_follow_native_rights_and_release_state(self):
        surface = {"scenarios": [{"key": "test", "intents": {"view": ["test.menu"]}}]}
        for can_manage in (False, True):
            for released in (False, True):
                for enabled in (False, True):
                    with self.subTest(can_manage=can_manage, released=released, enabled=enabled):
                        rows = business_enablement.business_catalog(surface,
                            {"test.menu": "released" if released else "preview"},
                            {"business.v1:test": enabled}, can_manage=can_manage)
                        actions = rows[0]["actions"]
                        self.assertEqual(len(actions), int(can_manage and (enabled or released)))
                        if actions:
                            self.assertIs(actions[0]["enabled"], not enabled)
                            self.assertEqual(actions[0]["label"], "停用" if enabled else "启用")

    def test_live_company_filter_runs_even_when_publication_is_cached(self):
        state = {"project.management": True}
        calls = []
        policy = types.SimpleNamespace(published_route_authority=lambda: self.authority)
        def live(authority):
            calls.append("read-company-state")
            return self.filtered(state, authority)
        policy._apply_company_route_scope = live
        env = {"sc.product.policy": policy}
        self.assertTrue(route_authority.menu_publication_decision(route_authority.published_route_authority(env), 1, 11))
        state.clear()
        self.assertFalse(route_authority.menu_publication_decision(route_authority.published_route_authority(env), 1, 11))
        self.assertEqual(calls, ["read-company-state", "read-company-state"])
        policy._apply_company_route_scope = lambda authority: (_ for _ in ()).throw(PermissionError("denied"))
        self.assertEqual(route_authority.published_route_authority(env), {})


class TestEnablementModelLifecycle(unittest.TestCase):
    """Execute the actual model overrides; only ORM persistence is controlled."""

    def setUp(self):
        self.events = []
        events = self.events
        class NativeModel:
            fail = False
            def ensure_one(self):
                return self
            def create(self, vals_list):
                events.append(("create", vals_list))
                if self.fail:
                    raise PermissionError("native create denied")
                return [object() for _ in vals_list]
            def write(self, vals):
                events.append(("write", vals))
                if self.fail:
                    raise PermissionError("native write denied")
                for key, value in vals.items():
                    setattr(self, key, value)
                return True
            def unlink(self):
                events.append(("unlink",))
                if self.fail:
                    raise PermissionError("native unlink denied")
                return True
        identity = lambda method: method
        api = types.SimpleNamespace(model=identity, model_create_multi=identity)
        fields = types.SimpleNamespace(**{key: lambda *args, **kwargs: None
                                         for key in ("Many2one", "Char", "Boolean")})
        exceptions = types.ModuleType("odoo.exceptions")
        class UserError(Exception):
            pass
        exceptions.UserError = UserError
        self.UserError = UserError
        with patch.object(odoo_mod, "api", api, create=True), \
             patch.object(odoo_mod, "fields", fields, create=True), \
             patch.object(odoo_mod, "models", types.SimpleNamespace(Model=NativeModel), create=True), \
             patch.dict(sys.modules, {"odoo.exceptions": exceptions}):
            module = _load("nav01_enablement_model", SCENE_DIR / "models/scene_company_enablement.py")
        self.record = module.ScSceneCompanyEnablement()
        self.record.env = types.SimpleNamespace(registry=types.SimpleNamespace(
            clear_cache=lambda: events.append(("invalidate",))))
        self.record.scene_key = "test.scene"
        self.record.enabled = False

    def test_create_and_delete_invalidate_only_after_native_success(self):
        values = [{"company_id": 1, "scene_key": "one"}, {"company_id": 2, "scene_key": "two"}]
        result = self.record.create(values)
        self.assertEqual(len(result), 2)
        self.assertEqual(self.events, [("create", values), ("invalidate",)])
        self.events.clear()
        self.assertTrue(self.record.unlink())
        self.assertEqual(self.events, [("unlink",), ("invalidate",)])

    def test_delivery_input_writes_invalidate_but_provenance_does_not(self):
        for values in ({"enabled": False}, {"enabled": True}, {"company_id": 2},
                       {"scene_key": "other"}, {"provenance": "tenant"}, {}):
            with self.subTest(values=values):
                self.events.clear()
                self.assertTrue(self.record.write(values))
                expected = [("write", values)]
                if set(values) & {"enabled", "company_id", "scene_key"}:
                    expected.append(("invalidate",))
                self.assertEqual(self.events, expected)

    def test_native_mutation_denial_is_not_hidden_or_invalidated(self):
        self.record.fail = True
        for operation in (lambda: self.record.create([{"scene_key": "one"}]),
                          lambda: self.record.write({"enabled": True}), self.record.unlink):
            with self.subTest(operation=operation):
                self.events.clear()
                with self.assertRaises(PermissionError):
                    operation()
                self.assertEqual(len(self.events), 1)
                self.assertNotIn(("invalidate",), self.events)

    def test_set_enabled_invalidates_once_per_state_transition(self):
        with patch.object(tenant_scene_activation, "resolve_product_released", return_value=True):
            for value in (True, True, False, False):
                self.assertIs(self.record.set_enabled(value), self.record)
        self.assertEqual(self.events, [
            ("write", {"enabled": True}), ("invalidate",),
            ("write", {"enabled": False}), ("invalidate",),
        ])
        self.assertIs(self.record.enabled, False)

    def test_model_rejects_coercion_even_without_intent_handler(self):
        with patch.object(tenant_scene_activation, "resolve_product_released",
                          side_effect=AssertionError("invalid input reached publication")):
            for value in ("false", "true", 0, 1, None, [], {}):
                with self.subTest(value=value):
                    with self.assertRaises(self.UserError):
                        self.record.set_enabled(value)
        self.assertEqual(self.events, [])
        self.assertIs(self.record.enabled, False)

    def test_preview_enable_is_blocked_but_disable_still_revokes(self):
        with patch.object(tenant_scene_activation, "resolve_product_released", return_value=False):
            with self.assertRaises(self.UserError):
                self.record.set_enabled(True)
            self.assertEqual(self.events, [])
            self.record.enabled = True
            self.record.set_enabled(False)
        self.assertEqual(self.events, [("write", {"enabled": False}), ("invalidate",)])


class TestTenantSceneActivation(unittest.TestCase):
    def test_preview_scene_cannot_be_tenant_enabled(self):
        allowed, next_enabled = tenant_scene_activation.decide_tenant_enablement(
            product_released=False, currently_enabled=False, requested=True
        )
        self.assertFalse(allowed)
        self.assertFalse(next_enabled)

    def test_released_scene_can_be_enabled(self):
        allowed, next_enabled = tenant_scene_activation.decide_tenant_enablement(
            product_released=True, currently_enabled=False, requested=True
        )
        self.assertTrue(allowed)
        self.assertTrue(next_enabled)

    def test_disable_is_always_allowed(self):
        allowed, next_enabled = tenant_scene_activation.decide_tenant_enablement(
            product_released=True, currently_enabled=True, requested=False
        )
        self.assertTrue(allowed)
        self.assertFalse(next_enabled)

    def test_enable_is_idempotent(self):
        allowed, next_enabled = tenant_scene_activation.decide_tenant_enablement(
            product_released=True, currently_enabled=True, requested=True
        )
        self.assertTrue(allowed)
        self.assertTrue(next_enabled)

    def test_resolve_scene_menu(self):
        entries = [
            {"code": "projects.ledger", "target": {"menu_xmlid": "smart_construction_core.menu_sc_project_project"}},
            {"code": "finance.payment_ledger", "target": {"menu_xmlid": "smart_construction_core.menu_payment_ledger"}},
        ]
        self.assertEqual(
            tenant_scene_activation.resolve_scene_menu("projects.ledger", entries=entries),
            "smart_construction_core.menu_sc_project_project",
        )
        self.assertEqual(tenant_scene_activation.resolve_scene_menu("missing", entries=entries), "")

    def test_resolve_product_released_uses_release_state(self):
        entries = [
            {"code": "projects.ledger", "target": {"menu_xmlid": "smart_construction_core.menu_sc_project_project"}},
            {"code": "finance.payment_ledger", "target": {"menu_xmlid": "smart_construction_core.menu_payment_ledger"}},
        ]
        release = {
            "smart_construction_core.menu_sc_project_project": "released",
            "smart_construction_core.menu_payment_ledger": "preview",
        }
        self.assertTrue(tenant_scene_activation.resolve_product_released(
            "projects.ledger", entries=entries, release_state_by_menu=release
        ))
        self.assertFalse(tenant_scene_activation.resolve_product_released(
            "finance.payment_ledger", entries=entries, release_state_by_menu=release
        ))

    def test_scenario_activation_catalog_projection(self):
        entries = [
            {"code": "projects.ledger", "name": "项目台账", "target": {"menu_xmlid": "smart_construction_core.menu_sc_project_project"}},
            {"code": "finance.payment_ledger", "name": "收付款台账", "target": {"menu_xmlid": "smart_construction_core.menu_payment_ledger"}},
        ]
        release = {
            "smart_construction_core.menu_sc_project_project": "released",
            "smart_construction_core.menu_payment_ledger": "preview",
        }
        catalog = scenario_activation_catalog.build_scenario_activation_catalog(
            entries=entries,
            release_state_by_menu=release,
            tenant_enablement_by_scene={"projects.ledger": True},
            role_candidates_by_scene={"projects.ledger": ["pm", "business_config_admin"]},
        )
        self.assertEqual(catalog["contract_version"], "scenario_activation_catalog.v1")
        self.assertEqual(catalog["row_count"], 2)
        by_key = {row["scene_key"]: row for row in catalog["rows"]}
        self.assertTrue(by_key["projects.ledger"]["product_released"])
        self.assertTrue(by_key["projects.ledger"]["tenant_enabled"])
        self.assertEqual(by_key["projects.ledger"]["applicable_roles"], ["pm", "business_config_admin"])
        self.assertFalse(by_key["finance.payment_ledger"]["product_released"])
        self.assertFalse(by_key["finance.payment_ledger"]["tenant_enabled"])

    def test_workspace_projection_intersection(self):
        entries = [
            {"code": "projects.ledger", "name": "项目台账", "target": {"menu_xmlid": "smart_construction_core.menu_sc_project_project"}},
            {"code": "finance.payment_requests", "name": "付款申请", "target": {"menu_xmlid": "smart_construction_core.menu_sc_user_payment_apply"}},
        ]
        release = {
            "smart_construction_core.menu_sc_project_project": "released",
            "smart_construction_core.menu_sc_user_payment_apply": "released",
        }
        result = workspace_scenario_projection.project_workspace_scenes(
            entries=entries,
            release_state_by_menu=release,
            tenant_enabled_by_scene={"projects.ledger": True, "finance.payment_requests": False},
            role_scene_candidates=["projects.ledger", "finance.payment_requests"],
        )
        by_key = {row["scene_key"]: row for row in result["rows"]}
        self.assertTrue(by_key["projects.ledger"]["workspace_candidate"])
        self.assertFalse(by_key["finance.payment_requests"]["workspace_candidate"])
        self.assertEqual(result["workspace_candidate_count"], 1)

    def test_workspace_projection_excludes_non_assigned_role(self):
        entries = [
            {"code": "finance.payment_requests", "name": "付款申请", "target": {"menu_xmlid": "smart_construction_core.menu_sc_user_payment_apply"}},
        ]
        release = {"smart_construction_core.menu_sc_user_payment_apply": "released"}
        result = workspace_scenario_projection.project_workspace_scenes(
            entries=entries,
            release_state_by_menu=release,
            tenant_enabled_by_scene={"finance.payment_requests": True},
            role_scene_candidates=["projects.ledger"],
        )
        self.assertFalse(result["rows"][0]["role_assigned"])
        self.assertFalse(result["rows"][0]["workspace_candidate"])

    def test_resolve_allowed_company_id_rejects_foreign_company(self):
        self.assertEqual(
            workspace_scenario_projection.resolve_allowed_company_id(9, {1, 2}, 1),
            1,
        )
        self.assertEqual(
            workspace_scenario_projection.resolve_allowed_company_id(2, {1, 2}, 1),
            2,
        )

    def test_resolve_request_company_defaults_when_omitted(self):
        company_id, error = workspace_scenario_projection.resolve_request_company(
            None, {1, 2}, 1
        )
        self.assertIsNone(error)
        self.assertEqual(company_id, 1)

    def test_resolve_request_company_rejects_inaccessible_default(self):
        for requested in (None, "", 0, "0"):
            with self.subTest(requested=requested):
                company_id, error = workspace_scenario_projection.resolve_request_company(requested, {2}, 1)
                self.assertEqual(company_id, 0)
                self.assertEqual(error["code"], 403)

    def test_resolve_request_company_allows_authorized_company(self):
        company_id, error = workspace_scenario_projection.resolve_request_company(
            "2", {1, 2}, 1
        )
        self.assertIsNone(error)
        self.assertEqual(company_id, 2)

    def test_resolve_request_company_rejects_foreign_company(self):
        company_id, error = workspace_scenario_projection.resolve_request_company(
            "9", {1, 2}, 1
        )
        self.assertEqual(company_id, 0)
        self.assertEqual(error, {"code": 403, "message": "company not authorized"})

    def test_resolve_request_company_rejects_invalid_company_id(self):
        company_id, error = workspace_scenario_projection.resolve_request_company(
            "not-an-int", {1, 2}, 1
        )
        self.assertEqual(company_id, 0)
        self.assertEqual(error, {"code": 400, "message": "invalid company_id"})


if __name__ == "__main__":
    unittest.main()
