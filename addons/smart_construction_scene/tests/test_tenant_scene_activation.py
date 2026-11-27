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
workspace_scenario_projection = _load(
    "odoo.addons.smart_construction_scene.services.workspace_scenario_projection",
    SCENE_DIR / "services" / "workspace_scenario_projection.py",
)

product_menu_source = _load(
    "odoo.addons.smart_construction_core.services.product_menu_source",
    SCENE_DIR.parent / "smart_construction_core/services/product_menu_source.py",
)
scenario_product_declarations = _load(
    "odoo.addons.smart_construction_core.services.scenario_product_declarations",
    SCENE_DIR.parent
    / "smart_construction_core/services/scenario_product_declarations.py",
)
scene_registry_content = _load(
    "odoo.addons.smart_construction_scene.profiles.scene_registry_content",
    SCENE_DIR / "profiles/scene_registry_content.py",
)

navigation_identity = _load(
    "odoo.addons.smart_core.core.navigation_identity",
    SCENE_DIR.parent / "smart_core/core/navigation_identity.py",
)
smart_core_pkg = sys.modules.setdefault(
    "odoo.addons.smart_core",
    types.ModuleType("odoo.addons.smart_core"),
)
smart_core_pkg.__path__ = []
delivery_pkg = sys.modules.setdefault(
    "odoo.addons.smart_core.delivery",
    types.ModuleType("odoo.addons.smart_core.delivery"),
)
delivery_pkg.__path__ = []
product_center_policy = _load(
    "odoo.addons.smart_core.delivery.product_center_policy",
    SCENE_DIR.parent / "smart_core/delivery/product_center_policy.py",
)

scenario_surface = _load(
    "odoo.addons.smart_construction_core.services.scenario_surface_projection",
    SCENE_DIR.parent / "smart_construction_core/services/scenario_surface_projection.py",
)
smart_core_pkg.__path__ = [str(SCENE_DIR.parent / "smart_core")]
delivery_pkg.__path__ = [str(SCENE_DIR.parent / "smart_core/delivery")]


route_authority = _load(
    "odoo.addons.smart_core.delivery.runtime_route_authority",
    SCENE_DIR.parent / "smart_core/delivery/runtime_route_authority.py",
)
backend_contract_boundaries = _load(
    "odoo.addons.smart_core.utils.backend_contract_boundaries",
    SCENE_DIR.parent / "smart_core/utils/backend_contract_boundaries.py",
)


class ContextEnv:
    """Controlled ORM transport retaining principal while changing context."""
    context = {"lang": "zh_CN", "allowed_company_ids": [1]}

    def __call__(self, *, context):
        bound = copy.copy(self)
        bound.context = context
        bound.company = types.SimpleNamespace(id=context["allowed_company_ids"][0])
        return bound


class NativeRecordsetDouble(list):
    def mapped(self, path):
        rows = list(self)
        for part in path.split('.'):
            values = [getattr(row, part) for row in rows]
            rows = [item for value in values for item in (value if isinstance(value, list) else [value])]
        return type(self)(rows)

    def get_external_id(self):
        return {record.id: record.get_external_id().get(record.id, '') for record in self}


def _native_xmlid_model(mapping):
    return types.SimpleNamespace(_xmlid_to_res_model_res_id=lambda reference, raise_if_not_found=False:
        ('ir.ui.menu', mapping[reference]) if reference in mapping else (False, False))


def _native_menu_browse(ids, existing):
    return types.SimpleNamespace(exists=lambda: types.SimpleNamespace(
        ids=[mid for mid in ids if mid in existing]))


def _runtime_model(name, env):
    """ORM transport fixture; production readers never consult this seed file."""
    if name not in ("sc.product.scenario", "ir.ui.menu", "ir.model.data"):
        return None
    surface = scenario_surface.load_surface()
    index = scenario_surface.build_menu_index(surface, parent_by_menu={
        child: root for root, children in getattr(env, "roots", {}).items() for child in children})
    menus = {}
    for number, (key, location) in enumerate(index.items(), 1):
        menu = types.SimpleNamespace(id=number, action=types.SimpleNamespace(id=number),
                                     sc_scenario_exempt=location["location"] != "scenario")
        menu.get_external_id = lambda number=number, key=key: {number: key}
        menus[key] = menu
    if name == "ir.model.data":
        return _native_xmlid_model({key: menu.id for key, menu in menus.items()})
    records = list(menus.values())
    if name == "sc.product.scenario":
        records = []
        center_by_menu = {}
        for center in product_menu_source.load_source()["product_contract"]["centers"]:
            for item in center["level_two"]:
                for leaf in item.get("children") or [item]:
                    menu_xmlid = (leaf.get("binding") or {}).get("menu_xmlid")
                    if menu_xmlid:
                        center_by_menu[menu_xmlid] = center
        for row in surface["scenarios"]:
            bindings = [
                types.SimpleNamespace(
                    menu_id=menus[key],
                    intent=intent,
                    sequence=10,
                    center_key=center_by_menu.get(key, {}).get("center_key", ""),
                    center_name=center_by_menu.get(key, {}).get("name", ""),
                    center_sequence=center_by_menu.get(key, {}).get("sequence", 10),
                )
                for intent, keys in row.get("intents", {}).items()
                for key in keys
            ]
            records.append(types.SimpleNamespace(code=row["key"], name=row.get("name", row["key"]),
                                                 active=True, sequence=10, entry_ids=bindings))
    model = types.SimpleNamespace(search=lambda domain: NativeRecordsetDouble(records),
        browse=lambda ids: _native_menu_browse(ids, {row.id for row in records}))
    model.sudo = lambda: model
    model.with_context = lambda **kwargs: model
    return model


class TestActualPublicationConsumers(unittest.TestCase):
    """Exercise real publication decoding; only the ORM transport is stubbed."""

    def setUp(self):
        # Keep the raw fixture discoverable by the isolated receipt scanner.
        source_path = SCENE_DIR.parent / "smart_construction_core/data/product_menu_source.json"
        self.assertEqual(source_path, product_menu_source.SOURCE_PATH)
        raw = json.loads(source_path.read_text())
        self.expected = {row["menu_xmlid"]: row["release_state"] for row in raw["entries"]}
        self.entries = scene_registry_content.list_scene_entries()
        gate = types.ModuleType("odoo.addons.smart_core.handlers.system_init")
        gate._load_platform_release_gate = lambda env, product_key: {"applied": True, "menu_release_states": self.expected}
        patcher = patch.dict(sys.modules, {gate.__name__: gate})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_resolved_bindings_preserve_every_declared_release_state(self):
        self.assertNotIn("entries", product_menu_source.load_source())
        actual = product_menu_source.load_menu_release_states()
        self.assertEqual(actual, self.expected)
        self.assertTrue(actual)
        self.assertEqual(set(actual.values()), {"released"})

    def test_activation_reads_real_source_without_injected_release_map(self):
        for state in ("released", "preview"):
            menu = "test.release.state"
            entries = [{"code": "test.scene", "target": {"menu_xmlid": menu}}]
            self.assertEqual(tenant_scene_activation.resolve_product_released(
                "test.scene", env=object(), entries=entries,
                release_state_by_menu={menu: state}), state == "released")

    def test_runtime_publication_never_falls_back_to_seed_or_draft(self):
        with patch.object(product_menu_source, 'load_source', side_effect=AssertionError('seed read')):
            gate = sys.modules['odoo.addons.smart_core.handlers.system_init']
            with patch.object(gate, '_load_platform_release_gate', return_value={'applied': False}):
                self.assertEqual(product_menu_source.load_published_menu_release_states(object()), {})
            with patch.object(gate, '_load_platform_release_gate', side_effect=[
                {'applied': True, 'menu_release_states': {'maintained.new': 'released'}},
                {'applied': True, 'menu_release_states': {'preview.only': 'released'}},
            ]):
                self.assertEqual(product_menu_source.load_published_menu_release_states(object()),
                                 {'maintained.new': 'released', 'preview.only': 'preview'})

    def test_unknown_entry_is_not_published(self):
        self.assertFalse(tenant_scene_activation.resolve_product_released(
            "test.unknown", env=object(), entries=[{"code": "test.unknown", "target": {"menu_xmlid": "missing.menu"}}]))

    def test_invalid_source_is_not_silently_an_empty_publication(self):
        with patch.object(product_menu_source, "load_source", side_effect=ValueError("invalid publication")):
            with self.assertRaisesRegex(ValueError, "invalid publication"):
                product_menu_source.load_menu_release_states()

    def _handlers_and_env(self, scenes=None, can_manage=False):
        base = types.ModuleType("odoo.addons.smart_core.core.base_handler")
        base.BaseIntentHandler = type("BaseIntentHandler", (), {})
        with patch.dict(sys.modules, {base.__name__: base}):
            handlers = _load("nav01_scenario_activation_handler", SCENE_DIR / "handlers/scenario_activation.py")
        params = {}

        class Env(ContextEnv):
            company = types.SimpleNamespace(id=1)
            user = types.SimpleNamespace(
                company_ids=types.SimpleNamespace(ids=[1]),
                has_group=lambda group: can_manage,
            )
            roots = {
                "smart_construction_core.menu_sc_workspace_center": [
                    "smart_construction_core.menu_sc_workspace_home",
                    "smart_construction_core.menu_sc_operating_metrics_project",
                    "smart_construction_core.menu_sc_project_kanban",
                    "smart_construction_core.menu_sc_workbench_my_todo_fact",
                    "smart_construction_core.menu_sc_product_message_notification_v1",
                ],
                "smart_construction_core.menu_sc_business_config_center": [
                    "smart_construction_core.menu_sc_business_config_workbench",
                    "smart_construction_core.menu_sc_approval_policy",
                    "smart_construction_core.menu_ui_form_field_policy_business_config",
                    "smart_construction_core.menu_ui_menu_config_policy_business_config",
                    "smart_construction_core.menu_sc_product_data_permission_v1",
                    "smart_construction_core.menu_sc_product_system_parameter_v1",
                    "smart_construction_core.menu_sc_product_numbering_rule_v1",
                ],
            }

            def ref(self, xmlid, raise_if_not_found=False):
                children = []
                for index, child_xmlid in enumerate(self.roots.get(xmlid, []), start=900):
                    child = types.SimpleNamespace(id=index, xmlid=child_xmlid)
                    child.get_external_id = lambda child=child: {child.id: child.xmlid}
                    children.append(child)
                return types.SimpleNamespace(child_id=children)

            def __getitem__(self, name):
                runtime = _runtime_model(name, self)
                if runtime is not None:
                    return runtime
                if name == "ir.config_parameter":
                    model = types.SimpleNamespace(
                        get_param=lambda key, default="0": params.get(key, default),
                        set_param=lambda key, value: params.__setitem__(key, value),
                    )
                    return types.SimpleNamespace(sudo=lambda: model)
                if name == "sc.scene":
                    model = types.SimpleNamespace(search=lambda domain: scenes or [])
                    model.sudo = lambda: model
                    return model
                raise AssertionError(f"unexpected ORM access: {name}")

        return handlers, Env()

    def test_catalog_handler_uses_actual_publication(self):
        handlers, env = self._handlers_and_env()
        result = handlers._catalog(env, company_id=1)
        self.assertEqual(result["contract_version"], "scenario_activation_catalog.v3")
        self.assertEqual(result["catalog_status"], "ready")
        self.assertEqual(result["published_page_count"], len(self.expected))
        cardinality = result["catalog_cardinality"]
        self.assertEqual(
            cardinality["center_count"],
            len(product_menu_source.center_identity_contract()["centers"]),
        )
        self.assertEqual(
            result["catalog_presentation"]["summary"],
            f"已发布产品页面 {len(self.expected)} 项"
            f" · 可选业务中心 {len(result['business_centers'])} 个"
            " · 页面均已纳入办理场景",
        )
        self.assertEqual(cardinality["published_page_count"], len(self.expected))
        self.assertEqual(
            cardinality["business_scenario_count"],
            len(result["business_scenarios"]),
        )
        self.assertEqual(
            cardinality["actionable_business_scenario_count"],
            len([row for row in result["business_scenarios"] if row["actions"]]),
        )
        centers = result["business_centers"]
        self.assertEqual(
            [center["key"] for center in centers],
            [
                "workspace.home.workbench",
                "construction.center.project",
                "construction.center.contract",
                "construction.center.cost",
                "construction.center.supply_chain",
                "construction.center.finance",
                "construction.center.tax",
                "construction.center.accounting",
                "construction.center.reporting",
                "construction.center.administration",
            ],
        )
        self.assertNotIn(
            "construction.center.product_configuration",
            {center["key"] for center in centers},
        )
        self.assertEqual(centers[0]["scene_keys"], ["work.my_queue"])
        self.assertEqual(centers[0]["scene_count"], 1)
        self.assertTrue(centers[0]["default_selected"])
        self.assertEqual(
            result["center_activation"]["recommended_center_keys"],
            [
                "workspace.home.workbench",
                "construction.center.project",
                "construction.center.contract",
                "construction.center.cost",
                "construction.center.finance",
                "construction.center.reporting",
            ],
        )
        self.assertEqual(
            sum(center["scene_count"] for center in centers),
            len({
                scene_key
                for center in centers
                for scene_key in center["scene_keys"]
            }),
        )

    def test_activation_request_group_gate_allows_admin_and_rejects_ordinary_user(self):
        handlers, env = self._handlers_and_env()
        platform = types.ModuleType('odoo.addons.smart_core.security.platform_admin')
        platform.user_is_tenant_config_admin = lambda user: False
        exceptions = types.ModuleType('odoo.exceptions')
        exceptions.AccessError = type('AccessError', (Exception,), {})
        with patch.dict(sys.modules, {
            platform.__name__: platform,
            backend_contract_boundaries.__name__: backend_contract_boundaries,
            exceptions.__name__: exceptions,
        }):
            policy = _load('activation_request_authorization',
                           SCENE_DIR.parent / 'smart_core/security/intent_authorization.py')
            operation = _load('odoo.addons.smart_core.core.intent_operation_policy',
                             SCENE_DIR.parent / 'smart_core/core/intent_operation_policy.py')
            # Exercise the same authorization function called before dispatch,
            # including its write-intent declaration requirement.
            policy.__package__ = 'odoo.addons.smart_core.security'
            with patch.object(policy, 'registered_handlers', return_value={
                    'scenario.activation.set': handlers.ScenarioActivationSetHandler,
                    'scenario.activation.centers.set': handlers.ScenarioCenterActivationSetHandler}):
                for intent in ('scenario.activation.set', 'scenario.activation.centers.set'):
                    self.assertTrue(operation.is_write_intent(intent, {}))
                    env.user.has_group = lambda group: group == 'smart_construction_core.group_sc_cap_business_config_admin'
                    self.assertTrue(policy.authorize_intent(env, intent, {})['allowed'])
                    env.user.has_group = lambda group: False
                    with self.assertRaises(exceptions.AccessError):
                        policy.authorize_intent(env, intent, {})

    def test_actual_catalog_actions_use_native_model_access_rights(self):
        for allowed in (False, True):
            with self.subTest(allowed=allowed):
                handlers, env = self._handlers_and_env(can_manage=allowed)
                published = {
                    **scenario_surface.load_surface(),
                    "runtime_scope": "published_release",
                }
                with patch.object(
                    scenario_surface,
                    "load_runtime_surface",
                    return_value=published,
                ):
                    result = handlers._catalog(env, company_id=1)
                self.assertEqual(result["company_id"], 1)
                self.assertEqual(
                    len(result["business_scenarios"]),
                    len(scenario_surface.load_surface()["scenarios"]),
                )
                actions = [action for row in result["business_scenarios"] for action in row["actions"]]
                self.assertEqual(bool(actions), allowed)

    def test_actual_catalog_disable_action_round_trips_saved_selection(self):
        handlers, base_env = self._handlers_and_env(can_manage=True)
        scene_key = "project.initiation"
        stored_key = business_enablement.business_key(scene_key)
        storage_key = "sc.scene.tenant.enablement.1." + stored_key
        params = {storage_key: "1"}

        class Env(ContextEnv):
            company = base_env.company
            user = base_env.user
            roots = base_env.roots

            def ref(self, xmlid, raise_if_not_found=False):
                return base_env.ref(xmlid, raise_if_not_found=raise_if_not_found)

            def __getitem__(self, name):
                runtime = _runtime_model(name, self)
                if runtime is not None:
                    return runtime
                if name == "res.company":
                    company = types.SimpleNamespace(id=1)
                    company.exists = lambda: company
                    return types.SimpleNamespace(browse=lambda company_id: company)
                if name == "ir.config_parameter":
                    def set_param(key, value):
                        params[key] = value

                    model = types.SimpleNamespace(
                        set_param=set_param,
                        get_param=lambda key, default="0": params.get(key, default),
                    )
                    return types.SimpleNamespace(sudo=lambda: model)
                return base_env[name]

        env = Env()
        surface = copy.deepcopy(scenario_surface.load_surface())
        surface["runtime_scope"] = "published_release"
        focus = next(scene for scene in surface["scenarios"] if scene["key"] == scene_key)
        focus["active"] = False

        with patch.object(scenario_surface, "load_runtime_surface", return_value=surface):
            catalog = handlers._catalog(env, company_id=1)
            row = next(item for item in catalog["business_scenarios"]
                       if item["scene_key"] == scene_key)
            self.assertTrue(row["tenant_enabled"])
            self.assertFalse(row["product_released"])
            self.assertEqual(row["status_label"], "企业已启用")
            self.assertEqual(row["actions"], [
                {"key": "disable", "label": "停用", "enabled": False},
            ])

            handler = handlers.ScenarioActivationSetHandler()
            handler.env, handler.params = env, {}
            action = row["actions"][0]
            result = handler.handle({
                "company_id": 1,
                "scene_key": row["scene_key"],
                "enablement_scope": row["enablement_scope"],
                "enabled": action["enabled"],
            })
            self.assertTrue(result["ok"])
            self.assertFalse(result["data"]["enabled"])
            self.assertFalse(result["data"]["readback"]["enabled"])
            self.assertEqual(result["data"]["stored_scene_key"], stored_key)
            self.assertEqual(params[storage_key], "0")

            reread = handlers._catalog(env, company_id=1)
            reread_row = next(item for item in reread["business_scenarios"]
                              if item["scene_key"] == scene_key)
            self.assertFalse(reread_row["tenant_enabled"])
            self.assertEqual(reread_row["status_label"], "未启用")
            self.assertEqual(reread_row["actions"], [])

            rejected = handler.handle({
                "company_id": 1,
                "scene_key": scene_key,
                "enablement_scope": business_enablement.BUSINESS_SCOPE,
                "enabled": True,
            })
            self.assertFalse(rejected["ok"])
            self.assertEqual(rejected["error"]["code"], 409)
            self.assertEqual(params[storage_key], "0")

            focus["active"] = True
            reactivated = handlers._catalog(env, company_id=1)
            reactivated_row = next(item for item in reactivated["business_scenarios"]
                                   if item["scene_key"] == scene_key)
            self.assertFalse(reactivated_row["tenant_enabled"])
            self.assertEqual(reactivated_row["actions"], [
                {"key": "enable", "label": "启用", "enabled": True},
            ])

    def test_workspace_handler_uses_actual_publication(self):
        handlers, env = self._handlers_and_env()
        handler = handlers.WorkspaceScenarioProjectionGetHandler()
        handler.env, handler.params = env, {}
        result = handler.handle()["data"]
        self.assertEqual(result["contract_version"], "workspace_scenario_projection.v2")
        expected_count = len(scenario_surface.load_surface()["scenarios"])
        self.assertEqual(result["row_count"], expected_count)
        self.assertEqual(len(result["rows"]), expected_count)
        self.assertEqual(
            {row["scene_key"] for row in result["rows"]},
            {row["key"] for row in scenario_surface.load_surface()["scenarios"]},
        )


    def test_actual_handlers_share_menu_bound_business_identity(self):
        handlers, env = self._handlers_and_env()
        catalog = handlers._catalog(env, company_id=1)
        workspace = handlers.WorkspaceScenarioProjectionGetHandler()
        workspace.env, workspace.params = env, {}
        projection = workspace.handle()["data"]
        surface = scenario_surface.load_surface()
        index = scenario_surface.runtime_menu_scope(env)[0]
        expected_keys = {row["key"] for row in surface["scenarios"]}
        self.assertEqual(
            {
                value["scenario_key"]
                for value in index.values()
                if value["location"] == "scenario"
            },
            expected_keys,
        )
        self.assertEqual(
            {row["scene_key"] for row in catalog["business_scenarios"]},
            expected_keys,
        )
        self.assertEqual(
            {row["scene_key"] for row in projection["rows"]},
            expected_keys,
        )

    def test_invalid_surface_does_not_silently_emit_unmapped_catalog(self):
        handlers, env = self._handlers_and_env()
        with patch.object(scenario_surface, "load_runtime_surface", side_effect=ValueError("invalid surface")):
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
        with patch.object(scenario_surface, "load_runtime_surface", return_value=surface):
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
                workspace = workspace_scenario_projection.project_workspace_scenes(
                    entries=entries, release_state_by_menu=release, tenant_enabled_by_scene=enabled,
                    role_scene_candidates=["project.management"], surface_index=index)
                self.assertEqual(workspace["rows"][0]["workspace_candidate"], enabled_key == "project.management")
                self.assertEqual(enabled, {enabled_key: True})

    def test_unmapped_entry_does_not_infer_identity_from_matching_scene_key(self):
        index = scenario_surface.build_menu_index(scenario_surface.load_surface())
        self.assertIsNone(tenant_scene_activation.resolve_entry_surface(
            {"code": "project.management", "target": {"menu_xmlid": "unknown.menu"}}, index))
        self.assertIsNone(tenant_scene_activation.resolve_entry_surface(
            {"code": "project.management"}, index))

    def test_catalog_scene_versions_do_not_override_menu_qualification(self):
        baseline_handlers, baseline_env = self._handlers_and_env()
        baseline = baseline_handlers._catalog(baseline_env, company_id=1)
        for version_state in ("STANDARD_RELEASE", "OPTIONAL_CAPABILITY", "PREVIEW", "NOT_READY"):
            with self.subTest(version_state=version_state):
                scenes = [types.SimpleNamespace(code=row["code"], active_version_id=types.SimpleNamespace(
                    product_release_state=version_state)) for row in self.entries]
                handlers, env = self._handlers_and_env(scenes=scenes)
                catalog = handlers._catalog(env, company_id=1)
                self.assertEqual(
                    catalog["catalog_cardinality"],
                    baseline["catalog_cardinality"],
                )
                self.assertEqual(
                    catalog["published_snapshot"],
                    baseline["published_snapshot"],
                )

    def test_native_entry_diagnosis_does_not_require_duplicate_scene_publication(self):
        diagnosis = _load("nav01_dependency_diagnosis", SCENE_DIR / "services/scenario_dependency_diagnosis.py")
        entry = self.entries[0]
        for menu_state in ("released", "preview"):
            for scene_state in ("published", "draft", None):
                with self.subTest(menu_state=menu_state, scene_state=scene_state):
                    scene = types.SimpleNamespace(id=1, state=scene_state) if scene_state else False
                    company = types.SimpleNamespace(id=1)
                    company.exists = lambda: company
                    class Env(ContextEnv):
                        cr = types.SimpleNamespace(now=lambda: "controlled-clock")
                        def ref(self, xmlid, raise_if_not_found=False):
                            action = types.SimpleNamespace(id=10, _name="ir.actions.act_window")
                            if xmlid == entry["target"]["action_xmlid"]:
                                return action
                            if xmlid == entry["target"]["menu_xmlid"]:
                                return types.SimpleNamespace(_name="ir.ui.menu", action=action)
                            return False
                        def __getitem__(self, name):
                            runtime = _runtime_model(name, self)
                            if runtime is not None:
                                return runtime
                            if name == "sc.scene":
                                raise AssertionError("native entry must not depend on orchestration publication")
                            if name == "res.company":
                                return types.SimpleNamespace(browse=lambda company_id: company)
                            raise AssertionError(name)
                    with patch.object(diagnosis, "_is_native_entry", return_value=True), patch.object(
                        diagnosis, "resolve_product_released", return_value=menu_state == "released",
                    ):
                        result = diagnosis.diagnose_scenario_dependencies(Env(), scene_key=entry["code"], company_id=1)
                    self.assertEqual(result["enable_allowed"], menu_state == "released")
                    evidence = result["dependencies"][0]["evidence"]
                    self.assertEqual(evidence["product_released"], menu_state == "released")
                    self.assertIsNone(evidence["scene_published"])
                    self.assertEqual(evidence["readiness_kind"], "native_action")
                    self.assertFalse(result["publication"]["scene_composition"]["applicable"])
                    self.assertIsNone(result["publication"]["scene_composition"]["standard_released"])

    def test_orchestration_lifecycle_is_still_required(self):
        diagnosis = _load("nav01_dependency_diagnosis", SCENE_DIR / "services/scenario_dependency_diagnosis.py")
        entry = {"code": "composed", "target": {"menu_xmlid": "test.menu", "route": "/s/composed"}}
        for released in (False, True):
            for state in ("draft", "published", None):
                class Env:
                    cr = types.SimpleNamespace(now=lambda: "controlled-clock")
                    def __getitem__(self, name):
                        if name == "sc.scene":
                            scene = types.SimpleNamespace(id=1, state=state, active_version_id=types.SimpleNamespace(id=2, product_release_state="STANDARD_RELEASE")) if state else False
                            if scene and scene.active_version_id:
                                scene.active_version_id.scene_id = scene
                                scene.active_version_id.product_edition = "construction.standard"
                            model = types.SimpleNamespace(search=lambda domain, limit: scene)
                            model.sudo = lambda: model
                            return model
                        company = types.SimpleNamespace(id=1)
                        company.exists = lambda: company
                        return types.SimpleNamespace(browse=lambda company_id: company)
                with patch.object(scene_registry_content, "list_scene_entries", return_value=[entry]), \
                     patch.object(diagnosis, "resolve_product_released", return_value=released):
                    result = diagnosis.diagnose_scenario_dependencies(Env(), scene_key="composed", company_id=1)
                self.assertEqual(result["enable_allowed"], released and state == "published")
                self.assertEqual(result["dependencies"][0]["evidence"]["readiness_kind"], "orchestration")

    def test_composition_snapshot_does_not_substitute_for_standard_product_release(self):
        diagnosis = _load("nav01_dependency_diagnosis", SCENE_DIR / "services/scenario_dependency_diagnosis.py")
        # An explicit intent remains composition even when an action is declared.
        entry = {"code": "composed", "target": {"menu_xmlid": "test.menu", "action_xmlid": "test.action", "intent": "test.compose"}}
        for version_state in ("PREVIEW", "OPTIONAL_CAPABILITY", "NOT_READY", "STANDARD_RELEASE", None):
            version = types.SimpleNamespace(id=2, product_release_state=version_state) if version_state else False
            scene = types.SimpleNamespace(id=1, state="published", active_version_id=version)
            company = types.SimpleNamespace(id=1)
            company.exists = lambda: company
            class Env:
                cr = types.SimpleNamespace(now=lambda: "controlled-clock")
                def __getitem__(self, name):
                    if name == "sc.scene":
                        if scene and scene.active_version_id:
                            scene.active_version_id.scene_id = scene
                            scene.active_version_id.product_edition = "construction.standard"
                        model = types.SimpleNamespace(search=lambda domain, limit: scene)
                        model.sudo = lambda: model
                        return model
                    return types.SimpleNamespace(browse=lambda company_id: company)
            with patch.object(scene_registry_content, "list_scene_entries", return_value=[entry]), \
                 patch.object(diagnosis, "resolve_product_released", return_value=True):
                result = diagnosis.diagnose_scenario_dependencies(Env(), scene_key="composed", company_id=1)
            self.assertEqual(result["enable_allowed"], version_state == "STANDARD_RELEASE")
            self.assertTrue(result["publication"]["native_capability"]["entry_qualified"])
            self.assertEqual(result["publication"]["scene_composition"]["standard_released"], version_state == "STANDARD_RELEASE")

    def test_real_dashboard_declarations_cannot_be_classified_as_native(self):
        import ast
        from xml.etree import ElementTree
        diagnosis = _load("nav01_dependency_diagnosis", SCENE_DIR / "services/scenario_dependency_diagnosis.py")
        entries = {entry["code"]: entry for entry in self.entries}
        dashboard = _load("diagnosis_dashboard_provider", SCENE_DIR / "profiles/project_dashboard_scene_content.py")
        self.assertFalse(diagnosis._declares_native_delivery(
            entries["project.dashboard"], entries["project.dashboard"], dashboard.build()))
        tree = ElementTree.parse(SCENE_DIR / "data/sc_scene_layout.xml")
        payloads = [ast.literal_eval(field.attrib["eval"]) for field in tree.findall(".//field[@name='payload_json']")]
        focus = next(row for row in payloads if row.get("code") == "projects.dashboard_focus")
        self.assertFalse(diagnosis._declares_native_delivery(entries["projects.dashboard_focus"], focus, {}))
        self.assertFalse(diagnosis._declares_native_delivery(entries["projects.list"], {}, {}))
        _load("odoo.addons.smart_construction_scene.services.workflow_rollout_handoff",
              SCENE_DIR / "services/workflow_rollout_handoff.py")
        direct = _load("diagnosis_direct_provider", SCENE_DIR / "providers/projects_list_provider.py")
        self.assertTrue(diagnosis._declares_native_delivery(entries["projects.list"], entries["projects.list"], direct.build()))
        for changed in ({"primary_action": {"action_xmlid": "other.action"}},
                        {"delivery_handoff": {**direct.build()["delivery_handoff"], "final_scene": "other.scene"}}):
            self.assertFalse(diagnosis._declares_native_delivery(entries["projects.list"], entries["projects.list"], {**direct.build(), **changed}))
        self.assertFalse(diagnosis._declares_native_delivery(entries["projects.list"],
            {**entries["projects.list"], "target": {**entries["projects.list"]["target"], "intent": "composed.execute"}}, direct.build()))
        self.assertFalse(diagnosis._declares_native_delivery(entries["projects.list"],
            {**entries["projects.list"], "page": {"blocks": [{"key": "composed"}]}}, direct.build()))
        native = {"source": "native_fact_projection", "target": entries["enterprise.setup"]["target"]}
        self.assertTrue(diagnosis._declares_native_delivery(entries["enterprise.setup"], native, {}))
        self.assertFalse(diagnosis._declares_native_delivery(entries["enterprise.setup"], {**native, "tiles": [{"key": "composed"}]}, {}))

    def test_native_binding_mismatch_and_missing_action_block_diagnosis(self):
        diagnosis = _load("nav01_dependency_diagnosis", SCENE_DIR / "services/scenario_dependency_diagnosis.py")
        entry = {"code": "native", "target": {"menu_xmlid": "test.menu", "action_xmlid": "test.action"}}
        company = types.SimpleNamespace(id=1)
        company.exists = lambda: company
        for action in (False, types.SimpleNamespace(id=1, _name="ir.actions.act_window")):
            class Env:
                cr = types.SimpleNamespace(now=lambda: "controlled-clock")
                def __getitem__(self, name):
                    if name != "res.company":
                        raise AssertionError(name)
                    return types.SimpleNamespace(browse=lambda company_id: company)
                def ref(self, xmlid, raise_if_not_found=False):
                    return action if xmlid == "test.action" else types.SimpleNamespace(_name="ir.ui.menu", action=False)
            with patch.object(scene_registry_content, "list_scene_entries", return_value=[entry]), \
                 patch.object(diagnosis, "resolve_product_released", return_value=True), \
                 patch.object(diagnosis, "_is_native_entry", return_value=True):
                result = diagnosis.diagnose_scenario_dependencies(Env(), scene_key="native", company_id=1)
            self.assertFalse(result["enable_allowed"])
            self.assertFalse(result["dependencies"][0]["evidence"]["structure_ready"])

    def test_all_handlers_reject_invalid_company_before_read_or_write(self):
        handlers, env = self._handlers_and_env()
        class NoAccessEnv:
            company, user = env.company, env.user
            def __getitem__(self, name):
                runtime = _runtime_model(name, self)
                if runtime is not None:
                    return runtime
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
                runtime = _runtime_model(name, self)
                if runtime is not None:
                    return runtime
                if name == "ir.config_parameter":
                    def get_param(key, default="0"):
                        domains.append((name, key))
                        if self.company.id != 2 or self.context["allowed_company_ids"] != [2]:
                            raise AssertionError("enablement query did not switch ORM company")
                        return "0"
                    return types.SimpleNamespace(sudo=lambda: types.SimpleNamespace(get_param=get_param))
                if name == "sc.scene":
                    return types.SimpleNamespace(sudo=lambda: types.SimpleNamespace(search=lambda domain: []))
                raise AssertionError(name)
        handler = handlers.WorkspaceScenarioProjectionGetHandler()
        handler.env, handler.params = CompanyEnv(), {}
        handler._resolve_authorized_scene_candidates = lambda entries, company_id: []
        self.assertTrue(handler.handle({"company_id": 2})["ok"])
        self.assertTrue(domains and all(name == "ir.config_parameter" for name, _key in domains))

    def test_activation_rejects_ambiguous_boolean_before_orm(self):
        handlers, env = self._handlers_and_env()
        class NoAccessEnv:
            company, user = env.company, env.user
            def __getitem__(self, name):
                runtime = _runtime_model(name, self)
                if runtime is not None:
                    return runtime
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
        params = {}
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
                runtime = _runtime_model(name, self)
                if runtime is not None:
                    return runtime
                if name == "res.company":
                    return types.SimpleNamespace(browse=lambda company_id: company)
                if name == "ir.config_parameter":
                    def set_param(key, value):
                        params[key] = value
                        calls.append(value)
                    model = types.SimpleNamespace(
                        set_param=set_param,
                        get_param=lambda key, default="0": params.get(key, default),
                    )
                    return types.SimpleNamespace(sudo=lambda: model)
                raise AssertionError(f"disable must not read enable dependencies: {name}")
        handler = handlers.ScenarioActivationSetHandler()
        handler.env, handler.params = Env(), {"scene_key": "test.scene", "enabled": False}
        for payload in ({"scene_key": " test.scene ", "enabled": False}, None):
            result = handler.handle(payload)
            self.assertTrue(result["ok"])
            self.assertIs(result["data"]["enabled"], False)
            self.assertEqual(result["data"]["scene_key"], "test.scene")
            readback = result["data"]["readback"]
            self.assertEqual(readback["source"], "ir.config_parameter")
            self.assertEqual(
                readback["storage_key"],
                "sc.scene.tenant.enablement.1.test.scene",
            )
            self.assertIs(readback["target_state"], False)
            self.assertEqual(readback["company_id"], 1)
            self.assertEqual(readback["stored_scene_key"], "test.scene")
            self.assertEqual(readback["enablement_scope"], "scene_entry.v1")
        self.assertEqual(calls, ["0", "0"])

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
        params = {}
        class Env(ContextEnv):
            company = original.company
            user = types.SimpleNamespace(id=7, company_ids=types.SimpleNamespace(ids=[1, 2]))
            def __getitem__(self, name):
                runtime = _runtime_model(name, self)
                if runtime is not None:
                    return runtime
                if self.company.id != 2 or self.context["allowed_company_ids"] != [2]:
                    raise AssertionError("mutation used wrong company context")
                if name == "res.company":
                    company = types.SimpleNamespace(id=2)
                    company.exists = lambda: company
                    return types.SimpleNamespace(browse=lambda company_id: company)
                if name == "ir.config_parameter":
                    def set_param(key, value):
                        params[key] = value
                        events.append(("set_param", key, value))
                    model = types.SimpleNamespace(
                        set_param=set_param,
                        get_param=lambda key, default="0": params.get(key, default),
                    )
                    return types.SimpleNamespace(sudo=lambda: model)
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
        self.assertEqual(result["data"]["target_scope"]["company_id"], 2)
        self.assertFalse(result["data"]["target_scope"]["is_global_product_release"])
        self.assertEqual(
            result["data"]["target_scope"]["target_role_scope"]["mode"],
            "not_role_scoped",
        )
        self.assertTrue(result["data"]["readback"]["enabled"])
        self.assertFalse(result["data"]["readback"]["access_granted"])
        self.assertEqual(
            result["data"]["readback"]["source"],
            "ir.config_parameter",
        )
        self.assertEqual(
            result["data"]["readback"]["storage_key"],
            "sc.scene.tenant.enablement.2.test.scene",
        )
        self.assertIs(result["data"]["readback"]["target_state"], True)
        self.assertIn("actor", result["data"])
        self.assertEqual(events, [
            ("diagnose", 2, 2, 7),
            ("set_param", "sc.scene.tenant.enablement.2.test.scene", "1"),
        ])
        self.assertEqual(handler.env.company.id, 1)

    def test_enablement_is_created_only_after_successful_diagnosis(self):
        handlers, env = self._handlers_and_env()
        module = types.ModuleType("odoo.addons.smart_construction_scene.services.scenario_dependency_diagnosis")
        for allowed in (False, True):
            with self.subTest(allowed=allowed):
                events = []
                params = {}
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
                        runtime = _runtime_model(name, self)
                        if runtime is not None:
                            return runtime
                        if name == "res.company":
                            return types.SimpleNamespace(browse=lambda company_id: company)
                        if name == "ir.config_parameter":
                            def set_param(key, value):
                                params[key] = value
                                events.append("set_param")
                            model = types.SimpleNamespace(
                                set_param=set_param,
                                get_param=lambda key, default="0": params.get(key, default),
                            )
                            return types.SimpleNamespace(sudo=lambda: model)
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
                self.assertEqual(events, ["diagnose", "set_param"] if allowed else ["diagnose"])
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
                runtime = _runtime_model(name, self)
                if runtime is not None:
                    return runtime
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
        authority_by_company = {
            1: {
                "primary_actions": [{
                    "menu_xmlid": "test.project",
                    "menu_id": 1,
                    "action_id": 11,
                    "allowed": True,
                }],
                "contextual_actions": [{
                    "menu_xmlid": "test.finance",
                    "menu_id": 2,
                    "action_id": 22,
                    "allowed": True,
                }],
            },
            2: {
                "primary_actions": [{
                    "menu_xmlid": "test.other",
                    "menu_id": 3,
                    "action_id": 33,
                    "allowed": True,
                }],
            },
        }
        queries = []
        context_calls = []
        surface = {
            "schema": scenario_surface.SCHEMA,
            "runtime_scope": "published_release",
            "scenarios": [
                {
                    "key": key,
                    "name": key,
                    "active": True,
                    "bindings": [{
                        "menu_key": f"test.{key}",
                        "menu_id": index,
                        "source_db": "test",
                    }],
                }
                for index, key in enumerate(("project", "finance", "other"), start=1)
            ],
        }
        menu_index = {
            f"test.{key}": {
                "location": "scenario",
                "scenario_key": key,
                "scenario_locations": [{
                    "location": "scenario",
                    "scenario_key": key,
                }],
            }
            for key in ("project", "finance", "other")
        }
        class Env(ContextEnv):
            def __init__(self, company_id):
                self.company = types.SimpleNamespace(id=company_id)
                self.user = types.SimpleNamespace(id=7, company_ids=types.SimpleNamespace(ids=[1, 2]))

            def __call__(self, *, context):
                context_calls.append(context)
                return Env(context["allowed_company_ids"][0])

            def __getitem__(self, name):
                runtime = _runtime_model(name, self)
                if runtime is not None:
                    return runtime
                if name == "ir.config_parameter":
                    def get_param(key, default="0"):
                        queries.append(key)
                        rest = key[len("sc.scene.tenant.enablement."):]
                        scene_key = rest.split(".", 1)[1] if "." in rest else rest
                        return "1" if scene_key in ("business.v1:project", "business.v1:finance", "business.v1:other") else "0"
                    return types.SimpleNamespace(sudo=lambda: types.SimpleNamespace(get_param=get_param))
                raise AssertionError(name)
        handler = handlers.WorkspaceScenarioProjectionGetHandler()
        handler.env, handler.params = Env(1), {}
        with patch.object(scenario_surface, "load_runtime_surface", return_value=surface), \
             patch.object(scenario_surface, "runtime_menu_scope", return_value=(menu_index, {}, {})), \
             patch.object(
                 route_authority,
                 "published_route_authority",
                 side_effect=lambda env: authority_by_company[env.company.id],
             ):
            def candidates(company_id):
                result = handler.handle({"company_id": company_id})
                self.assertTrue(result["ok"])
                return [row["scene_key"] for row in result["data"]["rows"] if row["workspace_candidate"]]
            self.assertEqual(candidates(1), ["project", "finance"])
            self.assertEqual(candidates(2), ["other"])
            authority_by_company[1] = {
                "primary_actions": [{
                    "menu_xmlid": "test.project",
                    "menu_id": 1,
                    "action_id": 11,
                    "allowed": True,
                }],
            }
            self.assertEqual(candidates(1), ["project"])
            authority_by_company[1] = {}
            self.assertEqual(candidates(1), [])
        self.assertEqual(
            context_calls,
            [
                {"lang": "zh_CN", "allowed_company_ids": [cid]}
                for cid in (1, 2, 1, 1)
            ],
        )
        self.assertTrue(queries)
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

    def test_shared_internal_target_survives_either_selected_scene(self):
        index = {"menu.A": {"location": "scenario", "scenario_key": "A"},
                 "menu.B": {"location": "scenario", "scenario_key": "B"}}
        entries = [{"code": key, "target": {"menu_xmlid": "menu." + key}} for key in ("A", "B")]
        authority = {"contextual_actions": [
            {"menu_id": 0, "action_id": 88, "scene_key": key, "item_key": "open",
             "source": "scene_internal_action_authority", "allowed": True}
            for key in ("A", "B")]}
        for enabled, expected in (({"A": True, "B": True}, {"A", "B"}),
                                  ({"A": False, "B": True}, {"B"}),
                                  ({"A": False, "B": False}, set())):
            with self.subTest(enabled=enabled):
                filtered = business_enablement.filter_business_authority(
                    authority, surface_index=index, enabled=enabled, entries=entries, menu_xmlids_by_id={})
                self.assertEqual({row["scene_key"] for row in filtered["contextual_actions"]}, expected)
                normalized = route_authority.coalesce_effective_route_authority(filtered)
                self.assertEqual(len(normalized["contextual_actions"]), int(bool(expected)))
                self.assertEqual(route_authority.published_pairs(normalized), {(0, 88)} if expected else set())

    def test_initialization_preserves_only_existing_authorized_internal_routes(self):
        self.entries.append({
            "code": "test.setup",
            "enablement_scope": "enterprise_initialization",
            "target": {"menu_xmlid": "test.project"},
        })
        row = {"action_id": 88, "menu_id": 0, "scene_key": "test.setup",
               "source": "scene_internal_action_authority", "allowed": True}
        result = self.filtered({}, {"contextual_actions": [row]})
        self.assertEqual(result["contextual_actions"], [row])
        self.assertEqual(self.filtered({}, {})["contextual_actions"], [])
        for change in ({"allowed": False}, {"source": "client"},
                       {"menu_xmlid": "test.project"}, {"menu_xmlid": "missing.menu"}, {"menu_id": 999}):
            with self.subTest(change=change):
                result = self.filtered({}, {"contextual_actions": [{**row, **change}]})
                self.assertEqual(result["contextual_actions"], [])
        denied = {**row, "route_kind": "DENIED", "allowed_operation": "none"}
        self.assertEqual(self.filtered({}, {"denied_actions": [denied]})["denied_actions"], [denied])

    def test_initialization_preserves_native_menu_before_business_scene_selection(self):
        menu_xmlid = tenant_scene_activation.ENTERPRISE_SETUP_MENU_XMLID
        action_xmlid = tenant_scene_activation.ENTERPRISE_SETUP_ACTION_XMLID
        entries = [{
            "code": tenant_scene_activation.ENTERPRISE_SETUP_CODE,
            "enablement_scope": "enterprise_initialization",
            "target": {
                "menu_xmlid": menu_xmlid,
                "action_xmlid": action_xmlid,
            },
        }]
        surface_index = {
            menu_xmlid: {
                "location": "scenario",
                "scenario_key": "config.enterprise_initialization",
                "scenario_active": True,
            },
            "test.project": {
                "location": "scenario",
                "scenario_key": "project.management",
                "scenario_active": True,
            },
        }
        initialize = {
            "menu_id": 9,
            "action_id": 90,
            "menu_xmlid": menu_xmlid,
            "action_xmlid": action_xmlid,
            "allowed_operation": "read",
            "source": "native_business_config_menu_projection",
        }
        ordinary = {
            "menu_id": 1,
            "action_id": 11,
            "menu_xmlid": "test.project",
            "action_xmlid": "test.action.project",
            "allowed_operation": "read",
            "source": "native_business_config_menu_projection",
        }
        result = business_enablement.filter_business_authority(
            {"primary_actions": [initialize, ordinary]},
            surface_index=surface_index,
            enabled={},
            entries=entries,
            menu_xmlids_by_id={9: menu_xmlid, 1: "test.project"},
        )
        self.assertEqual(result["primary_actions"], [initialize])
        self.assertEqual(
            {row["reason_code"] for row in result["denied_actions"]},
            {"BUSINESS_SCENARIO_NOT_ENABLED"},
        )
        for change in (
            {"source": "client"},
            {"menu_xmlid": "test.project", "menu_id": 1},
            {"action_xmlid": "test.action.project", "action_id": 11},
            {"allowed_operation": "none"},
        ):
            with self.subTest(change=change):
                spoofed = {**initialize, **change}
                blocked = business_enablement.filter_business_authority(
                    {"primary_actions": [spoofed]},
                    surface_index=surface_index,
                    enabled={},
                    entries=entries,
                    menu_xmlids_by_id={9: menu_xmlid},
                )
                self.assertEqual(blocked["primary_actions"], [])

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

    def test_shared_menu_survives_through_any_selected_scenario(self):
        location = {
            "location": "scenario",
            "scenario_key": "scenario.a",
            "scenario_locations": [
                {
                    "location": "scenario",
                    "menu_id": 1,
                    "scenario_key": "scenario.a",
                    "scenario_active": True,
                    "scenario_sequence": 20,
                    "sequence": 10,
                    "intent": "handle",
                    "entry_id": 1,
                },
                {
                    "location": "scenario",
                    "menu_id": 1,
                    "scenario_key": "scenario.b",
                    "scenario_active": True,
                    "scenario_sequence": 10,
                    "sequence": 20,
                    "intent": "view",
                    "entry_id": 2,
                },
            ],
            "menu_id": 1,
        }
        source = {"primary_actions": [
            {"menu_id": 1, "action_id": 11, "menu_xmlid": "test.shared"}
        ]}
        for enabled, expected_scene in (
            ({"scenario.a": True}, "scenario.a"),
            ({"scenario.b": True}, "scenario.b"),
            ({"scenario.a": True, "scenario.b": True}, "scenario.b"),
        ):
            with self.subTest(enabled=enabled):
                result = business_enablement.filter_business_authority(
                    source,
                    surface_index={"test.shared": location},
                    enabled=enabled,
                    entries=[],
                    menu_xmlids_by_id={1: "test.shared"},
                    company_id=9,
                )
                self.assertEqual(result["primary_actions"], source["primary_actions"])
                self.assertFalse(result["denied_actions"])
                composition = result["scenario_composition"]
                self.assertEqual(composition["company_id"], 9)
                self.assertEqual(
                    composition["selected_by_menu"]["1"]["scenario_key"],
                    expected_scene,
                )

    def test_direct_exemption_preserves_route_and_projects_navigation_kind(self):
        location = {
            "location": "scenario",
            "scenario_key": "admin.organization",
            "scenario_active": True,
            "center_key": "construction.center.administration",
            "scenario_locations": [{
                "location": "scenario",
                "menu_id": 1,
                "scenario_key": "admin.organization",
                "scenario_active": True,
                "scenario_sequence": 10,
                "sequence": 10,
                "intent": "view",
                "center_key": "construction.center.administration",
            }],
            "menu_id": 1,
            "direct_platform_exempt": True,
            "direct_platform_kind": "platform_initialization",
        }
        source = {"primary_actions": [{
            "menu_id": 1,
            "action_id": 11,
            "menu_xmlid": "test.user",
        }]}
        result = business_enablement.filter_business_authority(
            source,
            surface_index={"test.user": location},
            enabled={"admin.organization": False},
            entries=[],
            menu_xmlids_by_id={1: "test.user"},
            company_id=9,
        )
        self.assertEqual(result["primary_actions"], source["primary_actions"])
        selected = result["scenario_composition"]["selected_by_menu"]["1"]
        self.assertTrue(selected["direct_exempt"])
        self.assertEqual(
            selected["direct_platform_kind"],
            "platform_initialization",
        )
        self.assertFalse(
            result["scenario_composition"]["center_enablement"][
                "construction.center.administration"
            ]
        )

    def test_unselected_shared_menu_is_denied_without_losing_composition(self):
        location = {
            "location": "scenario",
            "scenario_key": "scenario.b",
            "scenario_locations": [
                {
                    "location": "scenario",
                    "menu_id": 1,
                    "scenario_key": "scenario.a",
                    "scenario_active": True,
                    "scenario_sequence": 10,
                },
                {
                    "location": "scenario",
                    "menu_id": 1,
                    "scenario_key": "scenario.b",
                    "scenario_active": True,
                    "scenario_sequence": 20,
                },
            ],
            "menu_id": 1,
        }
        result = business_enablement.filter_business_authority(
            {"primary_actions": [
                {"menu_id": 1, "action_id": 11, "menu_xmlid": "test.shared"}
            ]},
            surface_index={"test.shared": location},
            enabled={"scenario.a": False, "scenario.b": False},
            entries=[],
            menu_xmlids_by_id={1: "test.shared"},
            company_id=9,
        )
        self.assertFalse(result["primary_actions"])
        self.assertEqual(
            result["denied_actions"][0]["reason_code"],
            "BUSINESS_SCENARIO_NOT_ENABLED",
        )
        selected = result["scenario_composition"]["selected_by_menu"]["1"]
        self.assertNotEqual(selected.get("location"), "scenario")
        self.assertEqual(
            selected["available_scenario_keys"],
            ["scenario.a", "scenario.b"],
        )

    def test_one_menu_can_be_declared_in_multiple_scenarios_but_not_twice_in_one(self):
        surface = {
            "scenarios": [
                {
                    "key": "scenario.a",
                    "sequence": 20,
                    "bindings": [{
                        "menu_id": 1,
                        "menu_key": "test.shared",
                        "intent": "handle",
                        "sequence": 10,
                    }],
                },
                {
                    "key": "scenario.b",
                    "sequence": 0,
                    "bindings": [{
                        "menu_id": 1,
                        "menu_key": "test.shared",
                        "intent": "view",
                        "sequence": 0,
                    }],
                },
            ]
        }
        index = scenario_surface.build_menu_index(surface)
        self.assertEqual(
            [row["scenario_key"] for row in index["test.shared"]["scenario_locations"]],
            ["scenario.b", "scenario.a"],
        )
        self.assertEqual(index["test.shared"]["scenario_locations"][0]["sequence"], 0)
        self.assertEqual(index["test.shared"]["scenario_locations"][0]["scenario_sequence"], 0)
        surface["scenarios"][1]["bindings"].append({
            "menu_id": 1,
            "menu_key": "test.shared",
            "intent": "handle",
        })
        with self.assertRaisesRegex(ValueError, "duplicate menu assignment"):
            scenario_surface.build_menu_index(surface)

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

    def test_unknown_explicit_menu_cannot_borrow_enabled_legacy_scope(self):
        for identity in ({"menu_id": 999}, {"menu_xmlid": "missing.menu"}):
            row = {"action_id": 11, "scene_key": "alias.project", **identity}
            result = self.filtered({"project.management": True}, {"contextual_actions": [row]})
            self.assertFalse(result["contextual_actions"])

    def test_unknown_legacy_binding_fails_closed(self):
        result = self.filtered({}, {"contextual_actions": [{"action_id": 99, "scene_key": "unknown.legacy"}]})
        self.assertEqual(result["contextual_actions"], [])

    def test_action_only_route_obeys_native_business_membership(self):
        row = {"menu_id": 0, "action_id": 11}
        for enabled, expected in (({}, []), ({"project.management": True}, [row]),
                                  ({"project.management": False}, [])):
            with self.subTest(enabled=enabled):
                result = business_enablement.filter_business_authority(
                    {"contextual_actions": [row], "primary_actions": [{"menu_xmlid": "test.project", "action_id": 11}]}, surface_index=self.index, enabled=enabled,
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
                source = {"contextual_actions": [row], "primary_actions": [
                    {"menu_xmlid": menu, "action_id": 11} for menu in menus]}
                original = copy.deepcopy(source)
                result = business_enablement.filter_business_authority(
                    source, surface_index=self.index, enabled=enabled,
                    entries=self.entries, menu_xmlids_by_id={}, menu_xmlids_by_action={11: menus})
                self.assertEqual(result["contextual_actions"], expected)
                self.assertEqual(source, original)

    def test_action_membership_does_not_override_explicit_disabled_menu_or_legacy(self):
        rows = [{"menu_id": 1, "action_id": 11},
                {"action_id": 11, "scene_key": "alias.project"},
                {"action_id": 11, "scene_key": "unknown.legacy"}]
        result = business_enablement.filter_business_authority(
            {"contextual_actions": rows}, surface_index=self.index, enabled={"finance": True},
            entries=self.entries, menu_xmlids_by_id={1: "test.project"},
            menu_xmlids_by_action={11: ["test.project", "test.finance"]})
        self.assertEqual(result["contextual_actions"], [])

    def test_action_scope_never_manufactures_routes_or_trusts_unconfigured_action(self):
        for source in ({}, {"admin_actions": [{"action_id": 99}]}):
            result = business_enablement.filter_business_authority(
                source, surface_index=self.index, enabled={"project.management": True},
                entries=self.entries, menu_xmlids_by_id={}, menu_xmlids_by_action={11: ["test.project"]})
            self.assertEqual(route_authority.published_pairs(result), set())

    def test_unpublished_exempt_alias_cannot_rescue_disabled_bare_action(self):
        source = {"primary_actions": [{"menu_xmlid": "test.project", "action_id": 11}],
                  "contextual_actions": [{"action_id": 11}]}
        result = business_enablement.filter_business_authority(
            source, surface_index=self.index, enabled={}, entries=self.entries,
            menu_xmlids_by_id={}, menu_xmlids_by_action={11: ["test.project", "test.admin"]})
        self.assertFalse(result["primary_actions"])
        self.assertFalse(result["contextual_actions"])

    def test_actual_catalog_separates_all_business_keys_from_legacy_records(self):
        surface = scenario_surface.load_surface()
        release = product_menu_source.load_menu_release_states()
        legacy = {row["key"]: True for row in surface["scenarios"]}
        rows = business_enablement.business_catalog(surface, release, legacy)
        self.assertEqual(len(rows), len(surface["scenarios"]))
        self.assertFalse(any(row["tenant_enabled"] for row in rows))
        key = next(row["scene_key"] for row in rows if row["product_released"])
        rows = business_enablement.business_catalog(surface, release, {business_enablement.business_key(key): True})
        self.assertEqual([row["scene_key"] for row in rows if row["tenant_enabled"]], [key])
        published = {**surface, "runtime_scope": "published_release"}
        with patch.object(
            scenario_surface,
            "load_runtime_surface",
            return_value=published,
        ):
            self.assertTrue(tenant_scene_activation.resolve_product_released(
                business_enablement.business_key(key),
                env=TestActualPublicationConsumers()._handlers_and_env()[1],
            ))
            self.assertFalse(tenant_scene_activation.resolve_product_released(
                "business.v1:unknown",
                env=TestActualPublicationConsumers()._handlers_and_env()[1],
            ))

    def test_workspace_uses_same_business_decision_without_native_grants(self):
        release = {menu: "released" for menu in self.index}
        for enabled in ({}, {"project.management": True}, {"project.management": False}):
            result = workspace_scenario_projection.project_workspace_scenes(
                entries=self.entries, release_state_by_menu=release, tenant_enabled_by_scene={"legacy.project": True},
                business_enabled_by_scene=enabled, role_scene_candidates=["legacy.project"], surface_index=self.index)
            self.assertEqual([row["scene_key"] for row in result["rows"] if row["workspace_candidate"]],
                             ["legacy.project"] if enabled.get("project.management") else [])

    def test_business_mutation_cannot_overwrite_same_named_legacy_record(self):
        fixture = TestActualPublicationConsumers()
        fixture.setUp()
        handlers, original = fixture._handlers_and_env()
        params = {}
        class Env(ContextEnv):
            company, user = original.company, original.user
            def __getitem__(self, name):
                runtime = _runtime_model(name, self)
                if runtime is not None:
                    return runtime
                if name == "res.company":
                    company = types.SimpleNamespace(id=1)
                    company.exists = lambda: company
                    return types.SimpleNamespace(browse=lambda cid: company)
                if name == "ir.config_parameter":
                    def set_param(key, value):
                        params[key] = value
                    def get_param(key, default="0"):
                        return params.get(key, default)
                    return types.SimpleNamespace(
                        sudo=lambda: types.SimpleNamespace(
                            set_param=set_param,
                            get_param=get_param,
                        )
                    )
                raise AssertionError(name)
        handler = handlers.ScenarioActivationSetHandler()
        handler.env, handler.params = Env(), {}
        catalog = {"business_scenarios": [{"scene_key": "project.management", "product_released": True}]}
        with patch.object(handlers, "_catalog", return_value=catalog):
            for enabled in (True, False):
                result = handler.handle({"scene_key": "project.management", "enablement_scope": "business.v1", "enabled": enabled})
                self.assertTrue(result["ok"])
                self.assertEqual(result["data"]["enablement_scope"], "business.v1")
            self.assertEqual(params["sc.scene.tenant.enablement.1.business.v1:project.management"], "0")
            self.assertNotIn("sc.scene.tenant.enablement.1.project.management", params)
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
        self.assertEqual(len(keys), len(surface["scenarios"]))
        for enabled_keys in (keys, [], *([key] for key in keys)):
            with self.subTest(enabled=enabled_keys):
                authority = business_enablement.filter_business_authority(
                    {"primary_actions": actions}, surface_index=index,
                    enabled={key: True for key in enabled_keys}, entries=[], menu_xmlids_by_id=by_id)
                filtered_nav = module.menu_service.MenuService.filter_nav_by_route_authority(nav, authority)
                projection = scenario_surface.project_authorized_nav(
                    nav=filtered_nav, route_authority=authority, surface=surface)
                self.assertTrue(projection["ok"])
                scenarios = [scene for center in projection["tree"]["centers"] for scene in center["scenarios"]]
                self.assertEqual({scene["key"] for scene in scenarios}, set(enabled_keys))
                for scene in scenarios:
                    for intent in scene["intents"]:
                        for entry in intent["entries"]:
                            self.assertIn((entry["menu_id"], entry["action_id"]),
                                          route_authority.published_pairs(authority))
        # Enabled scenarios cannot create entries when the native authority is empty.
        self.assertEqual(scenario_surface.project_authorized_nav(
            nav=[], route_authority={}, surface=surface)["tree"]["centers"], [])

    def test_inactive_saved_selection_is_disableable_but_never_navigable(self):
        surface = {
            "runtime_scope": "published_release",
            "scenarios": [{
                "key": "test.scene",
                "name": "Inactive scene",
                "active": False,
                "intents": {"view": ["test.menu"]},
            }],
        }
        stored = {business_enablement.business_key("test.scene"): True}
        rows = business_enablement.business_catalog(
            surface, {}, stored, can_manage=True,
        )
        row = rows[0]
        self.assertTrue(row["tenant_enabled"])
        self.assertFalse(row["product_released"])
        self.assertEqual(row["status_label"], "企业已启用")
        self.assertEqual(row["release_label"], "未发布")
        self.assertEqual(row["actions"], [
            {"key": "disable", "label": "停用", "enabled": False},
        ])
        self.assertEqual(stored, {business_enablement.business_key("test.scene"): True})

        index = scenario_surface.build_menu_index(surface)
        filtered = business_enablement.filter_business_authority(
            {"primary_actions": [{"menu_id": 1, "action_id": 11, "menu_xmlid": "test.menu"}]},
            surface_index=index,
            enabled={"test.scene": True},
            entries=[{"code": "test.scene", "target": {"menu_xmlid": "test.menu"}}],
            menu_xmlids_by_id={1: "test.menu"},
        )
        self.assertEqual(filtered["primary_actions"], [])
        self.assertEqual(
            filtered["denied_actions"][0]["reason_code"],
            "BUSINESS_SCENARIO_NOT_ENABLED",
        )

    def test_inactive_false_selection_has_no_enable_action(self):
        surface = {
            "runtime_scope": "published_release",
            "scenarios": [{
                "key": "test.scene",
                "active": False,
                "intents": {"view": ["test.menu"]},
            }],
        }
        rows = business_enablement.business_catalog(
            surface,
            {"test.menu": "released"},
            {business_enablement.business_key("test.scene"): False},
            can_manage=True,
        )
        self.assertFalse(rows[0]["tenant_enabled"])
        self.assertFalse(rows[0]["product_released"])
        self.assertEqual(rows[0]["actions"], [])

    def test_saved_selection_is_independent_of_current_product_availability(self):
        active = {
            "runtime_scope": "published_release",
            "scenarios": [{
                "key": "test.scene",
                "active": True,
                "intents": {"view": ["test.menu"]},
            }],
        }
        inactive = copy.deepcopy(active)
        inactive["scenarios"][0]["active"] = False
        for enabled in (False, True):
            with self.subTest(enabled=enabled):
                stored = {business_enablement.business_key("test.scene"): enabled}
                available = business_enablement.business_catalog(
                    active, {"test.menu": "hidden"}, stored, can_manage=True,
                )[0]
                unavailable = business_enablement.business_catalog(
                    inactive, {"test.menu": "released"}, stored, can_manage=True,
                )[0]
                self.assertIs(available["tenant_enabled"], enabled)
                self.assertIs(unavailable["tenant_enabled"], enabled)
                self.assertEqual(stored, {business_enablement.business_key("test.scene"): enabled})
                self.assertNotIn("enable", [action["key"] for action in unavailable["actions"]])

    def test_saved_true_without_qualified_menu_keeps_only_disable(self):
        surface = {
            "runtime_scope": "published_release",
            "scenarios": [{"key": "test.scene", "active": True, "intents": {}}],
        }
        row = business_enablement.business_catalog(
            surface,
            {},
            {business_enablement.business_key("test.scene"): True},
            can_manage=True,
        )[0]
        self.assertTrue(row["tenant_enabled"])
        self.assertFalse(row["product_released"])
        self.assertEqual(row["released_menu_count"], 0)
        self.assertEqual(row["actions"], [
            {"key": "disable", "label": "停用", "enabled": False},
        ])

    def test_saved_selection_is_readable_without_maintenance_rights(self):
        surface = {
            "runtime_scope": "published_release",
            "scenarios": [{
                "key": "test.scene",
                "active": False,
                "intents": {"view": ["test.menu"]},
            }],
        }
        row = business_enablement.business_catalog(
            surface,
            {},
            {business_enablement.business_key("test.scene"): True},
            can_manage=False,
        )[0]
        self.assertTrue(row["tenant_enabled"])
        self.assertEqual(row["status_label"], "企业已启用")
        self.assertEqual(row["actions"], [])

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

    def test_business_catalog_uses_published_composition_not_native_release_state(self):
        surface = {
            "runtime_scope": "published_release",
            "scenarios": [{
                "key": "project",
                "name": "Project",
                "active": True,
                "intents": {"view": ["project.menu"]},
            }],
        }
        rows = business_enablement.business_catalog(
            surface,
            {"project.menu": "hidden"},
            {},
        )
        self.assertTrue(rows[0]["product_released"])
        self.assertEqual(rows[0]["released_menu_count"], 1)

        draft = {**surface, "runtime_scope": "maintained_draft"}
        draft_rows = business_enablement.business_catalog(
            draft,
            {"project.menu": "released"},
            {},
        )
        self.assertFalse(draft_rows[0]["product_released"])

    def test_published_authority_is_final_without_company_refilter(self):
        policy = types.SimpleNamespace(published_route_authority=lambda: self.authority)
        policy._apply_company_route_scope = lambda authority: (_ for _ in ()).throw(
            AssertionError("company scene state was applied a second time")
        )
        env = {"sc.product.policy": policy}
        for _attempt in range(2):
            self.assertTrue(
                route_authority.menu_publication_decision(
                    route_authority.published_route_authority(env), 1, 11
                )
            )


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
    def test_write_invalidates_parameter_cache_after_save(self):
        events = []
        values = {}
        cached = {"value": None}

        class Config:
            def set_param(self, key, value):
                events.append(("set", key, value))
                values[key] = value

            def get_param(self, key, default=""):
                if cached["value"] is None:
                    cached["value"] = values.get(key, default)
                return cached["value"]

        class Registry:
            def clear_cache(self):
                events.append(("clear",))
                cached["value"] = None

        class Env:
            registry = Registry()

            def __getitem__(self, name):
                self_test.assertEqual(name, "ir.config_parameter")
                return types.SimpleNamespace(sudo=lambda: Config())

        self_test = self
        env = Env()
        tenant_scene_activation.write_tenant_enablement(env, 1, "project.management", True)
        self.assertTrue(tenant_scene_activation.read_tenant_enablement(env, 1, "project.management"))
        tenant_scene_activation.write_tenant_enablement(env, 1, "project.management", False)
        self.assertFalse(tenant_scene_activation.read_tenant_enablement(env, 1, "project.management"))
        self.assertEqual(events[-2], ("set", "sc.scene.tenant.enablement.1.project.management", "0"))
        self.assertEqual(events[-1], ("clear",))

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


class TestMaintainedScenarioScope(unittest.TestCase):
    def test_missing_archived_and_exempt_apply_to_menu_and_bare_action(self):
        authority = {"primary_actions": [{"menu_id": 1, "action_id": 11}],
                     "contextual_actions": [{"action_id": 11}]}
        cases = [({"location": "missing"}, False),
                 ({"location": "exempt"}, True),
                 ({"location": "scenario", "scenario_key": "new", "scenario_active": False}, False),
                 ({"location": "scenario", "scenario_key": "new", "scenario_active": True}, True)]
        for location, expected in cases:
            with self.subTest(location=location):
                result = business_enablement.filter_business_authority(
                    authority, surface_index={"test.menu": location}, enabled={"new": True}, entries=[],
                    menu_xmlids_by_id={1: "test.menu"}, menu_xmlids_by_action={11: ["test.menu"]})
                self.assertEqual(bool(result["primary_actions"]), expected)
                self.assertEqual(bool(result["contextual_actions"]), expected)
                self.assertEqual(authority["primary_actions"], [{"menu_id": 1, "action_id": 11}])

    def test_rebinding_uses_new_scenario_not_old_enabled_key(self):
        entry = {"target": {"menu_xmlid": "test.menu"}}
        index = {"test.menu": {"location": "scenario", "scenario_key": "new"}}
        self.assertFalse(business_enablement.entry_business_enabled(entry, index, {"old": True}))
        self.assertTrue(business_enablement.entry_business_enabled(entry, index, {"new": True}))

    def test_actionless_anchor_is_not_a_container_and_honors_explicit_exemption(self):
        menu = types.SimpleNamespace(id=7, action=False, child_id=[], sc_scenario_exempt=False,
                                     get_external_id=lambda: {7: "test.anchor"})
        class Env:
            def __getitem__(self, name):
                model = types.SimpleNamespace(search=lambda domain: [menu])
                model.sudo = lambda: model
                model.with_context = lambda **kwargs: model
                return model
        surface = {"scenarios": []}
        index, by_id, _ = scenario_surface.runtime_menu_scope(Env(), surface)
        self.assertEqual(index["test.anchor"]["location"], "missing")
        menu.sc_scenario_exempt = True
        index, _, _ = scenario_surface.runtime_menu_scope(Env(), surface)
        self.assertEqual(index["test.anchor"]["location"], "exempt")
        surface = {"scenarios": [{"key": "s", "active": True, "intents": {"view": ["test.anchor"]}}]}
        index, _, _ = scenario_surface.runtime_menu_scope(Env(), surface)
        self.assertEqual(index["test.anchor"]["location"], "scenario")
        self.assertFalse(business_enablement.location_business_enabled(index["test.anchor"], {}))
        self.assertTrue(business_enablement.location_business_enabled(index["test.anchor"], {"s": True}))

    def test_runtime_reader_has_no_file_fallback_and_keeps_archived_identity(self):
        menu = types.SimpleNamespace(id=7, action=types.SimpleNamespace(id=17), sc_scenario_exempt=False,
                                     get_external_id=lambda: {})
        entry = types.SimpleNamespace(menu_id=menu, intent="view", sequence=3)
        scenario = types.SimpleNamespace(code="maintained", name="Edited", active=False,
                                         sequence=4, entry_ids=[entry])
        class Env:
            def __getitem__(self, name):
                rows = {"ir.ui.menu": [menu], "sc.product.scenario": [scenario]}[name]
                model = types.SimpleNamespace(search=lambda domain: NativeRecordsetDouble(rows))
                model.sudo = lambda: model
                model.with_context = lambda **kwargs: model
                return model
        with patch.object(scenario_surface, "load_surface", side_effect=AssertionError("file read")):
            surface = scenario_surface.load_runtime_surface(Env())
            index, by_id, by_action = scenario_surface.runtime_menu_scope(Env(), surface)
        self.assertEqual(surface["scenarios"][0]["name"], "Edited")
        self.assertEqual(by_id, {7: "menu:7"})
        self.assertEqual(by_action, {17: ["menu:7"]})
        self.assertFalse(index["menu:7"]["scenario_active"])
        with self.assertRaises(ValueError):
            scenario_surface.load_runtime_surface(None)

    def test_runtime_reader_prefers_published_composition_and_empty_is_authoritative(self):
        published = {
            "schema": scenario_surface.SCHEMA,
            "scenarios": [{
                "key": "published",
                "name": "Published name",
                "active": True,
                "sequence": 0,
                "bindings": [{
                    "menu_key": "test.menu",
                    "menu_id": 7,
                    "intent": "view",
                    "sequence": 0,
                }],
            }],
        }
        with patch.object(
            scenario_surface,
            "load_published_runtime_surface",
            return_value=published,
        ), patch.object(
            scenario_surface,
            "load_maintained_runtime_surface",
            side_effect=AssertionError("live maintenance read"),
        ):
            self.assertEqual(scenario_surface.load_runtime_surface(object()), published)

        empty = {
            "schema": scenario_surface.SCHEMA,
            "scenarios": [],
            "runtime_scope": "published_release_without_composition",
        }
        with patch.object(
            scenario_surface,
            "load_published_runtime_surface",
            return_value=empty,
        ), patch.object(
            scenario_surface,
            "load_maintained_runtime_surface",
            side_effect=AssertionError("live maintenance read"),
        ):
            self.assertEqual(scenario_surface.load_runtime_surface(object()), empty)

    def test_published_composition_indexes_without_live_scenario_records(self):
        surface = {
            "schema": scenario_surface.SCHEMA,
            "scenarios": [{
                "key": "published",
                "name": "Published",
                "active": True,
                "sequence": 4,
                "bindings": [{
                    "menu_key": "test.menu",
                    "menu_id": 7,
                    "intent": "view",
                    "sequence": 0,
                    "center_key": "construction.center.project",
                    "center_name": "Project",
                    "center_sequence": 20,
                }],
            }],
        }

        indexed = scenario_surface._scenario_entries_by_menu(
            None,
            surface=surface,
        )

        self.assertEqual(indexed[7][0]["scenario_key"], "published")
        self.assertEqual(indexed[7][0]["sequence"], 0)

    def test_published_runtime_surface_reads_active_release_policy(self):
        composition = {
            "schema": scenario_surface.SCHEMA,
            "centers": [{
                "key": "construction.center.project",
                "name": "项目中心",
                "sequence": 20,
                "scenarios": ["published"],
            }],
            "scenarios": [{
                "key": "published",
                "name": "Published",
                "active": True,
                "sequence": 0,
                "bindings": [],
            }],
        }

        class PolicyService:
            def __init__(self, env):
                self.env = env

            def get_published_policy(self, **kwargs):
                return {
                    "product_key": kwargs["product_key"],
                    "business_scene_composition": composition,
                }

            def has_active_release_snapshot(self, **kwargs):
                return True

        policy_module = types.ModuleType(
            "odoo.addons.smart_core.delivery.product_policy_service"
        )
        policy_module.ProductPolicyService = PolicyService
        active = types.SimpleNamespace(id=31)
        snapshot_model = types.SimpleNamespace(
            search=lambda *args, **kwargs: types.SimpleNamespace(
                __bool__=lambda self: True,
            )
        )
        snapshot_model.sudo = lambda: snapshot_model

        class Env:
            registry = types.SimpleNamespace(
                models={"sc.edition.release.snapshot": object()}
            )

            def __getitem__(self, name):
                if name == "sc.edition.release.snapshot":
                    return snapshot_model
                raise KeyError(name)

        with patch.dict(
            sys.modules,
            {
                "odoo.addons.smart_core.delivery.product_policy_service": policy_module,
            },
        ):
            surface = scenario_surface.load_published_runtime_surface(Env())

        self.assertEqual(
            surface,
            {**composition, "runtime_scope": "published_release"},
        )
        class LegacyPolicyService:
            def __init__(self, env):
                self.env = env

            def get_published_policy(self, **kwargs):
                raise ValueError("LEGACY_PUBLISHED_POLICY_REQUIRES_REFREEZE")

            def has_active_release_snapshot(self, **kwargs):
                return True

        policy_module.ProductPolicyService = LegacyPolicyService
        with patch.dict(
            sys.modules,
            {
                "odoo.addons.smart_core.delivery.product_policy_service": policy_module,
            },
        ):
            legacy_surface = scenario_surface.load_published_runtime_surface(Env())
        self.assertEqual(
            legacy_surface,
            {
                "schema": scenario_surface.SCHEMA,
                "centers": [],
                "scenarios": [],
                "runtime_scope": "published_release_without_composition",
            },
        )

        class NoSnapshotPolicyService:
            def __init__(self, env):
                self.env = env

            def get_published_policy(self, **kwargs):
                return None

        policy_module.ProductPolicyService = NoSnapshotPolicyService
        with patch.dict(
            sys.modules,
            {
                "odoo.addons.smart_core.delivery.product_policy_service": policy_module,
            },
        ):
            no_snapshot_surface = scenario_surface.load_published_runtime_surface(Env())
        self.assertEqual(
            no_snapshot_surface,
            {
                "schema": scenario_surface.SCHEMA,
                "centers": [],
                "scenarios": [],
                "runtime_scope": "published_release_without_composition",
            },
        )

    def test_scenario_identity_uses_xmlid_cross_db_and_rejects_numeric_cross_db(self):
        menu = types.SimpleNamespace(id=121)

        class Env:
            cr = types.SimpleNamespace(dbname="execution_db")

            def __getitem__(self, name):
                if name == 'ir.model.data':
                    return _native_xmlid_model({'project.menu_ledger': menu.id})
                if name == 'ir.ui.menu':
                    return types.SimpleNamespace(browse=lambda ids: _native_menu_browse(ids, {menu.id}))
                raise KeyError(name)

            def ref(self, xmlid, raise_if_not_found=False):
                return menu if xmlid == "project.menu_ledger" else None

        xmlid_surface = {
            "schema": scenario_surface.SCHEMA,
            "source_db": "catalog_db",
            "scenarios": [{
                "key": "project",
                "bindings": [{
                    "menu_key": "project.menu_ledger",
                    "menu_id": 21,
                    "intent": "view",
                    "source_db": "catalog_db",
                }],
            }],
        }
        indexed = scenario_surface._scenario_entries_by_menu(
            Env(),
            surface=xmlid_surface,
        )
        self.assertIn(121, indexed)
        self.assertNotIn(21, indexed)

        numeric_surface = copy.deepcopy(xmlid_surface)
        numeric_surface["scenarios"][0]["bindings"][0]["menu_key"] = "menu:21"
        indexed = scenario_surface._scenario_entries_by_menu(
            Env(),
            surface=numeric_surface,
        )
        self.assertEqual(indexed, {})

    def test_scenario_selection_uses_the_same_resolved_menu_identity(self):
        def env_for(menu):
            class MenuModel:
                def sudo(self):
                    return self

                def with_context(self, **kwargs):
                    return self

                def browse(self, ids):
                    return _native_menu_browse(ids, {menu.id})

                def search(self, domain):
                    return [menu]

            class Env:
                cr = types.SimpleNamespace(dbname="tenant_db")

                def __getitem__(self, model_name):
                    if model_name == "ir.model.data":
                        return _native_xmlid_model({"project.menu_ledger": menu.id})
                    if model_name == "ir.ui.menu":
                        return MenuModel()
                    raise KeyError(model_name)

                def ref(self, xmlid, raise_if_not_found=False):
                    return menu if xmlid == "project.menu_ledger" else None

            return Env()

        def surface(source_db, menu_key="menu:21"):
            return {
                "schema": scenario_surface.SCHEMA,
                "source_db": source_db,
                "scenarios": [{
                    "key": "project",
                    "name": "Project",
                    "active": True,
                    "sequence": 0,
                    "bindings": [{
                        "menu_key": menu_key,
                        "menu_id": 21,
                        "source_db": source_db,
                        "intent": "view",
                        "sequence": 0,
                    }],
                }],
            }

        local_menu = types.SimpleNamespace(
            id=21,
            action=types.SimpleNamespace(id=99),
            child_id=[],
            sc_scenario_exempt=False,
            get_external_id=lambda: {},
        )
        local_env = env_for(local_menu)
        for source_db in ("platform_db", ""):
            with self.subTest(source_db=source_db):
                rejected_surface = surface(source_db)
                index, by_id, by_action = scenario_surface.runtime_menu_scope(
                    local_env,
                    rejected_surface,
                )
                self.assertEqual(index["menu:21"]["location"], "missing")
                self.assertEqual(
                    scenario_surface._scenario_entries_by_menu(
                        local_env,
                        surface=rejected_surface,
                    ),
                    {},
                )
                filtered = business_enablement.filter_business_authority(
                    {
                        "primary_actions": [{
                            "menu_id": 21,
                            "action_id": 99,
                            "allowed": True,
                        }]
                    },
                    surface_index=index,
                    enabled={"project": True},
                    entries=[],
                    menu_xmlids_by_id=by_id,
                    menu_xmlids_by_action=by_action,
                    company_id=9,
                )
                self.assertFalse(filtered["primary_actions"])
                self.assertNotIn(
                    "21",
                    filtered["scenario_composition"]["selected_by_menu"],
                )

        same_db_surface = surface("tenant_db")
        index, by_id, by_action = scenario_surface.runtime_menu_scope(
            local_env,
            same_db_surface,
        )
        self.assertEqual(index["menu:21"]["location"], "scenario")
        self.assertEqual(
            scenario_surface._scenario_entries_by_menu(
                local_env,
                surface=same_db_surface,
            )[21][0]["scenario_key"],
            "project",
        )
        filtered = business_enablement.filter_business_authority(
            {
                "primary_actions": [{
                    "menu_id": 21,
                    "action_id": 99,
                    "allowed": True,
                }]
            },
            surface_index=index,
            enabled={"project": True},
            entries=[],
            menu_xmlids_by_id=by_id,
            menu_xmlids_by_action=by_action,
            company_id=9,
        )
        self.assertTrue(filtered["primary_actions"])
        self.assertEqual(
            filtered["scenario_composition"]["selected_by_menu"]["21"]["scenario_key"],
            "project",
        )

        xmlid_menu = types.SimpleNamespace(
            id=121,
            action=types.SimpleNamespace(id=331),
            child_id=[],
            sc_scenario_exempt=False,
            get_external_id=lambda: {121: "project.menu_ledger"},
        )
        xmlid_env = env_for(xmlid_menu)
        xmlid_surface = surface("platform_db", "project.menu_ledger")
        index, by_id, by_action = scenario_surface.runtime_menu_scope(
            xmlid_env,
            xmlid_surface,
        )
        self.assertEqual(index["project.menu_ledger"]["location"], "scenario")
        self.assertEqual(
            scenario_surface._scenario_entries_by_menu(
                xmlid_env,
                surface=xmlid_surface,
            )[121][0]["scenario_key"],
            "project",
        )
        filtered = business_enablement.filter_business_authority(
            {
                "primary_actions": [{
                    "menu_id": 121,
                    "action_id": 331,
                    "menu_xmlid": "project.menu_ledger",
                    "allowed": True,
                }]
            },
            surface_index=index,
            enabled={"project": True},
            entries=[],
            menu_xmlids_by_id=by_id,
            menu_xmlids_by_action=by_action,
            company_id=9,
        )
        self.assertTrue(filtered["primary_actions"])
        self.assertEqual(
            filtered["scenario_composition"]["selected_by_menu"]["121"]["scenario_key"],
            "project",
        )

    def test_added_and_existing_leaves_share_scene_target_projection(self):
        scene_targets = {(21, 31): "finance.operating_metrics"}
        existing = {
            "menu_id": 21,
            "action_id": 31,
            "route": "/a/31?menu_id=21",
        }
        added = copy.deepcopy(existing)

        scenario_surface._apply_scene_target_projection(existing, scene_targets)
        scenario_surface._apply_scene_target_projection(added, scene_targets)

        self.assertEqual(existing["entry_target"], added["entry_target"])
        self.assertEqual(existing["entry_target"]["type"], "scene")
        self.assertEqual(
            existing["entry_target"]["scene_key"],
            "finance.operating_metrics",
        )


if __name__ == "__main__":
    unittest.main()
