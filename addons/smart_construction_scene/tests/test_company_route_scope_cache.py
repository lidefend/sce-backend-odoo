# -*- coding: utf-8 -*-
from unittest.mock import patch
from copy import deepcopy

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.smart_construction_core.services import scenario_surface_projection


@tagged(
    "post_install",
    "-at_install",
    "sc_smoke",
    "company_route_scope_cache",
)
class TestCompanyRouteScopeCache(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param(
            "sc.core.extension_modules", "smart_construction_core,smart_construction_scene"
        )

    def test_scene_package_export_propagates_system_init_failure(self):
        from odoo.addons.smart_core.handlers import system_init
        from odoo.addons.smart_construction_scene.services.scene_package_service import (
            ScenePackageService,
        )

        captured = {}

        class _FailingSystemInit:
            def __init__(self, *args, **kwargs):
                captured["payload"] = kwargs.get("payload")

            def handle(self, payload=None, ctx=None):
                captured["payload"] = payload
                return {
                    "ok": False,
                    "error": {
                        "code": 409,
                        "message": "contract identity rejected",
                        "reason_code": "CONTRACT_VERSION_UNSUPPORTED",
                    },
                }

        with patch.object(system_init, "SystemInitHandler", _FailingSystemInit):
            with self.assertRaisesRegex(ValueError, "contract identity rejected"):
                ScenePackageService(self.env).export_package(
                    "protocol-export",
                    "1.0.0",
                )

        params = captured["payload"]["params"]
        self.assertEqual(params["client_type"], "web_pc")
        self.assertEqual(params["accepted_contract_versions"], ["2.7.x"])
        self.assertEqual(params["client_contract_capabilities"], [])

    def test_scene_state_is_not_a_second_route_authority(self):
        policy = self.env["sc.product.policy"]
        authority = {
            "primary_actions": [],
            "role_home_actions": [],
            "contextual_actions": [],
            "admin_actions": [],
            "menu_containers": [],
            "denied_actions": [],
        }
        self.env.registry.clear_cache()
        with patch.object(
            scenario_surface_projection,
            "load_runtime_surface",
            wraps=scenario_surface_projection.load_runtime_surface,
        ) as load_surface:
            first = policy._apply_company_route_scope(authority)
            second = policy._apply_company_route_scope(authority)
        self.assertEqual(load_surface.call_count, 0)
        self.assertEqual(first, second)
        self.assertEqual(first, authority)
        self.assertEqual(authority["denied_actions"], [])

    def test_internal_actions_preserve_initialization_lifecycle_and_native_denial(self):
        from odoo.addons.smart_core.delivery import effective_delivery_service as module
        from odoo.addons.smart_core.delivery.menu_service import MenuService
        from odoo.addons.smart_core.core import native_handling_entry_catalog, scene_ready_contract_builder
        service = module.EffectiveDeliveryService(self.env)
        source = {
            "code": "enterprise.setup",
            "enablement_scope": "enterprise_initialization",
        }
        catalog = {"groups": [{"items": [{"key": "open", "action_xmlid": "smart_construction_core.action_sc_project_list"}]}]}
        # Initialization actions do not need a business-scene nav node.
        authority = {}
        with patch.object(module, "call_extension_hook_first", return_value=[source]), \
                patch.object(native_handling_entry_catalog, "project_native_handling_catalog", return_value=None), \
                patch.object(scene_ready_contract_builder, "_resolve_scene_provider_payload", return_value={"handling_entry_catalog": catalog}):
            rows = service._internal_actions([], authority, MenuService(self.env), {})
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["source"], "scene_internal_action_authority")
        self.assertIs(rows[0]["allowed"], True)
        self.assertEqual(rows[0]["item_key"], "open")
        with patch.object(module, "call_extension_hook_first", return_value=[source]), \
                patch.object(native_handling_entry_catalog, "project_native_handling_catalog", return_value={"groups": []}), \
                patch.object(scene_ready_contract_builder, "_resolve_scene_provider_payload", side_effect=AssertionError("native denial must not fall back")):
            self.assertEqual(service._internal_actions([], authority, MenuService(self.env), {}), [])

    def test_internal_actions_do_not_promote_unscoped_business_scenes(self):
        from odoo.addons.smart_core.delivery import effective_delivery_service as module
        from odoo.addons.smart_core.delivery.menu_service import MenuService
        source = {"code": "project.management"}
        with patch.object(module, "call_extension_hook_first", return_value=[source]):
            self.assertEqual(
                module.EffectiveDeliveryService(self.env)._internal_actions(
                    [], {}, MenuService(self.env), {},
                ),
                [],
            )

    def test_native_enterprise_projection_keeps_initialization_scope(self):
        from odoo.addons.smart_construction_scene import scene_registry
        row = scene_registry._derive_native_config_scene(self.env)
        self.assertEqual(row.get("code"), "enterprise.setup")
        self.assertEqual(
            row.get("target", {}).get("record_id"),
            self.env.company.id,
        )
        self.assertEqual(
            row.get("enablement_scope"),
            "enterprise_initialization",
        )

    def test_config_admin_receives_initialization_entry_before_scene_enablement(self):
        from odoo.addons.smart_core.delivery.effective_delivery_service import EffectiveDeliveryService
        from odoo.addons.smart_core.delivery.native_config_menu_projection import native_config_delivery_groups
        from odoo.addons.smart_construction_scene.services.business_scene_enablement import business_key
        from odoo.addons.smart_construction_scene.services.tenant_scene_activation import write_tenant_enablement

        menu_xmlid = "smart_construction_core.menu_sc_enterprise_initialization"
        action_xmlid = "smart_construction_core.action_sc_enterprise_initialization"
        actor = self.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Initialization route admin",
            "login": "initialization-route-admin",
            "groups_id": [(6, 0, [
                self.env.ref("base.group_user").id,
                self.env.ref("smart_construction_core.group_sc_cap_business_config_admin").id,
            ])],
        })
        for scene in scenario_surface_projection.load_runtime_surface(self.env).get("scenarios") or []:
            write_tenant_enablement(
                self.env,
                self.env.company.id,
                business_key(scene["key"]),
                False,
            )
        env = actor.with_user(actor).with_context(allowed_company_ids=[self.env.company.id]).env
        projected_rows = [
            row
            for group in native_config_delivery_groups(env)
            for row in group.get("menus") or []
        ]
        projected = {row.get("menu_xmlid") for row in projected_rows}
        self.assertIn(menu_xmlid, projected)
        projected_initialize = [
            row for row in projected_rows if row.get("menu_xmlid") == menu_xmlid
        ]
        self.assertEqual(len(projected_initialize), 1)
        self.assertEqual(
            ((projected_initialize[0].get("entry_target") or {}).get("record_entry") or {}).get("record_id"),
            self.env.company.id,
        )

        admitted = EffectiveDeliveryService(env).resolve()
        initialize_rows = [
            row
            for bucket in ("primary_actions", "contextual_actions", "admin_actions")
            for row in admitted.route_authority.get(bucket) or []
            if row.get("menu_xmlid") == menu_xmlid
            and row.get("action_xmlid") == action_xmlid
        ]
        self.assertEqual(len(initialize_rows), 1)
        self.assertEqual(
            ((initialize_rows[0].get("entry_target") or {}).get("record_entry") or {}).get("model"),
            "res.company",
            initialize_rows,
        )
        self.assertEqual(
            ((initialize_rows[0].get("entry_target") or {}).get("record_entry") or {}).get("record_id"),
            self.env.company.id,
        )
        nav_rows = []
        pending = list(admitted.payload["nav"] or [])
        while pending:
            node = pending.pop(0)
            nav_rows.append(node)
            pending.extend(node.get("children") or [])
        initialize_nodes = [
            node for node in nav_rows
            if (node.get("meta") or {}).get("menu_xmlid") == menu_xmlid
        ]
        self.assertEqual(len(initialize_nodes), 1)
        self.assertEqual(
            ((initialize_nodes[0].get("entry_target") or {})
             .get("record_entry") or {}).get("record_id"),
            self.env.company.id,
        )

        ordinary = self.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Initialization route ordinary user",
            "login": "initialization-route-ordinary",
            "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
        })
        ordinary_env = ordinary.with_user(ordinary).with_context(
            allowed_company_ids=[self.env.company.id],
        ).env
        ordinary_authority = EffectiveDeliveryService(ordinary_env).resolve().route_authority
        self.assertFalse(any(
            row.get("menu_xmlid") == menu_xmlid
            for bucket in ("primary_actions", "contextual_actions", "admin_actions")
            for row in ordinary_authority.get(bucket) or []
        ))

    def test_imported_handling_override_reaches_page_authority_and_direct_gate(self):
        from odoo.addons.smart_core.delivery import effective_delivery_service as delivery
        from odoo.addons.smart_core.delivery import published_scene_surface_service as published_surface
        from odoo.addons.smart_core.delivery.menu_service import MenuService
        from odoo.addons.smart_core.delivery.runtime_route_authority import published_route_authority, published_pairs
        from odoo.addons.smart_core.handlers.route_authority_validate import RouteAuthorityValidateHandler
        from odoo.addons.smart_construction_scene import scene_registry
        from odoo.addons.smart_construction_scene.services.scene_package_service import ScenePackageService
        from odoo.addons.smart_construction_scene.services.business_scene_enablement import filter_business_authority
        menu_xmlid = "smart_construction_core.menu_sc_product_scenario_business_config"
        menu = self.env.ref(menu_xmlid)
        actions = []
        for name in ("old", "new"):
            action = self.env["ir.actions.act_window"].create({"name": name, "res_model": "project.project", "view_mode": "tree,form"})
            self.env["ir.model.data"].create({"module": "smart_construction_scene", "name": "test_import_" + name,
                                           "model": action._name, "res_id": action.id})
            actions.append(action)
        old_action, new_action = actions
        code = "effective.imported"
        original = {"code": code, "name": "Imported handling", "target": {"menu_xmlid": menu_xmlid},
                    "handling_entry_catalog": {"groups": [{"key": "operations", "label": "Operations", "items": [
                        {"key": "open", "label": "Open", "action_xmlid": "smart_construction_scene.test_import_old"}]}]}}
        imported = deepcopy(original)
        imported["handling_entry_catalog"]["groups"][0]["items"][0]["action_xmlid"] = "smart_construction_scene.test_import_new"
        main_xmlid = menu.action.get_external_id()[menu.action.id]
        main = MenuService(self.env)._route_entry_from_action_spec({"action_xmlid": main_xmlid, "menu_xmlid": menu_xmlid}, route_kind="PRIMARY_NAV")
        self.assertTrue(main)
        main["scene_key"] = code
        seed = {"product_key": "construction.standard", "nav": [{"key": "effective.imported", "menu_id": menu.id,
                "id": menu.id, "name": "Imported", "meta": dict(main), "children": []}],
                "route_authority": {"primary_actions": [main]}}
        real_hook = delivery.call_extension_hook_first
        def hook(env, name, *args, **kwargs):
            if name == "smart_core_navigation_authority_filter":
                return filter_business_authority(args[1], surface_index={menu_xmlid: {
                    "location": "scenario", "scenario_key": "effective", "scenario_active": True}},
                    enabled={"effective": True}, entries=[original], menu_xmlids_by_id={menu.id: menu_xmlid},
                    company_id=env.company.id)
            return real_hook(env, name, *args, **kwargs)
        with patch.object(scene_registry, "_load_scene_registry_content_entries_with_timings", side_effect=lambda: ([
                deepcopy(original),
                {"code": "workspace.home", "name": "角色首页", "target": {"route": "/s/workspace.home"}},
            ], {})), \
                patch.object(delivery.DeliveryEngine, "build", side_effect=lambda **kwargs: deepcopy(seed)), \
                patch.object(delivery, "_load_platform_release_gate", return_value={}), \
                patch.object(delivery, "call_extension_hook_first", side_effect=hook), \
                patch.object(published_surface, "call_extension_hook_first", side_effect=hook):
            self.env.registry.clear_cache()
            self.assertIn(
                (0, old_action.id),
                published_pairs(delivery.EffectiveDeliveryService(self.env).resolve().route_authority),
            )
            package_service = ScenePackageService(self.env)
            package = {"package_name": "effective-import-test", "package_version": "1.0.0", "schema_version": "v2",
                       "scene_version": "v2", "scenes": [imported], "profiles": {}, "defaults": {"scene_channel": "stable"},
                       "policies": {}, "compatibility": {}}
            package["checksum"] = package_service._checksum(package)
            package_service.import_package(package, "override_existing", "Verify effective handling target")
            page = next(row for row in scene_registry.load_scene_configs(self.env) if row["code"] == code)
            self.assertEqual(page["handling_entry_catalog"], imported["handling_entry_catalog"])
            solved = delivery.EffectiveDeliveryService(self.env).resolve()
            self.assertEqual(solved.payload["scene_internal_actions"][code + ":open"]["action_id"], new_action.id)
            pairs = published_pairs(solved.route_authority)
            self.assertIn((0, new_action.id), pairs)
            self.assertNotIn((0, old_action.id), pairs)
            self.assertEqual(published_pairs(published_route_authority(self.env)), pairs)
            for action, expected in ((new_action, True), (old_action, False)):
                result = RouteAuthorityValidateHandler(self.env, payload={"params": {"action_id": action.id}}).handle()
                self.assertEqual(result.ok, expected)

            # A published database definition takes precedence over the
            # imported declaration. Version switching must invalidate authority.
            scene = self.env["sc.scene"].create({"code": code, "name": "Versioned handling"})
            versions = [self.env["sc.scene.version"].create({
                "scene_id": scene.id, "version": str(index), "payload_json": definition,
            }) for index, definition in enumerate((original, imported), 1)]
            scene.write({"state": "published", "active_version_id": versions[0].id})
            for version, expected, denied in ((versions[0], old_action, new_action),
                                               (versions[1], new_action, old_action),
                                               (versions[0], old_action, new_action)):
                scene.active_version_id = version
                cached_pairs = published_pairs(published_route_authority(self.env))
                self.assertIn((0, expected.id), cached_pairs)
                self.assertNotIn((0, denied.id), cached_pairs)
                self.assertEqual(cached_pairs, published_pairs(delivery.EffectiveDeliveryService(self.env).resolve().route_authority))
                page = next(row for row in scene_registry.load_scene_configs(self.env) if row["code"] == code)
                self.assertEqual(page["handling_entry_catalog"], version.payload_json["handling_entry_catalog"])
            scene.active = False
            cached_pairs = published_pairs(published_route_authority(self.env))
            self.assertIn((0, new_action.id), cached_pairs)
            self.assertNotIn((0, old_action.id), cached_pairs)
            self.assertEqual(cached_pairs, published_pairs(delivery.EffectiveDeliveryService(self.env).resolve().route_authority))

    def test_scene_runtime_consumes_an_isolated_projection_of_the_request_snapshot(self):
        from odoo.addons.smart_construction_scene import scene_registry
        from odoo.addons.smart_core.core.scene_runtime_orchestrator import SceneRuntimeOrchestrator
        from odoo.addons.smart_core.core.scene_provider import load_scenes_from_db_or_fallback
        from odoo.addons.smart_core.core.system_init_request_context import SystemInitRequestContext
        from odoo.addons.smart_core.core.system_init_runtime_context import SystemInitRuntimeContext
        from odoo.addons.smart_core.governance.scene_normalizer import SceneNormalizer

        request_context = SystemInitRequestContext(self.env)
        scene_diagnostics = {
            "timings": {},
            "drift": [],
            "normalize_warnings": [],
            "resolve_errors": [],
        }
        runtime_ctx = SystemInitRuntimeContext(
            env=self.env,
            user=self.env.user,
            params={},
            data={"scenes": [], "capabilities": [], "nav": []},
            nav_tree=[],
            scene_channel="stable",
            rollback_active=False,
            trace_id="scene-snapshot-immutability",
            diagnostics_collector=None,
            scene_diagnostics=scene_diagnostics,
            load_scene_contract_fn=lambda env, channel, pinned: (None, "test/no-contract"),
            load_scenes_fallback_fn=load_scenes_from_db_or_fallback,
            merge_missing_scenes_fn=lambda *args, **kwargs: args[1],
            append_resolve_error_fn=lambda bucket, **kwargs: bucket.append(kwargs),
            request_context=request_context,
            published_authority={},
        )

        class NoopDriftEngine:
            @staticmethod
            def evaluate(scenes, diagnostics):
                del scenes, diagnostics

        class NoopAutoDegradeEngine:
            @staticmethod
            def evaluate(*args, **kwargs):
                del args, kwargs
                return {"triggered": False}

        SceneRuntimeOrchestrator(logger=None).execute(
            runtime_ctx=runtime_ctx,
            scene_normalizer=SceneNormalizer(),
            scene_drift_engine=NoopDriftEngine(),
            auto_degrade_engine=NoopAutoDegradeEngine(),
        )

        fact = request_context.fact(scene_registry.EFFECTIVE_SCENE_DECLARATIONS_FACT)
        self.assertIsNotNone(fact)
        snapshot = fact.value
        self.assertGreater(len(runtime_ctx.data["scenes"]), 0)
        self.assertEqual(
            scene_registry.scene_declaration_fingerprint(snapshot.declarations),
            snapshot.content_fingerprint,
        )
        declared = next(
            scene
            for scene in snapshot.declarations
            if isinstance(scene.get("target"), dict) and scene["target"]
        )
        with self.assertRaisesRegex(TypeError, "read-only"):
            declared["target"]["route"] = "/s/mutated"

    def test_imported_target_refreshes_navigation_identity_map(self):
        from odoo.addons.smart_construction_scene import core_extension, scene_registry
        from odoo.addons.smart_construction_scene.services.scene_package_service import ScenePackageService
        actions = []
        for name in ("map_old", "map_new"):
            action = self.env["ir.actions.act_window"].create({"name": name, "res_model": "project.project", "view_mode": "tree,form"})
            self.env["ir.model.data"].create({"module": "smart_construction_scene", "name": name,
                                           "model": action._name, "res_id": action.id})
            actions.append("smart_construction_scene." + name)
        code = "effective.mapping"
        original = {"code": code, "name": "Mapping", "target": {"action_xmlid": actions[0]}}
        with patch.object(scene_registry, "_load_scene_registry_content_entries_with_timings", return_value=([original], {})):
            self.assertEqual(core_extension.smart_core_nav_scene_maps(self.env)["action_xmlid_scene_map"][actions[0]], code)
            imported = deepcopy(original)
            imported["target"] = {"action_xmlid": actions[1]}
            service = ScenePackageService(self.env)
            package = {"package_name": "effective-mapping-test", "package_version": "1.0.0", "schema_version": "v2",
                       "scene_version": "v2", "scenes": [imported], "profiles": {}, "defaults": {"scene_channel": "stable"},
                       "policies": {}, "compatibility": {}}
            package["checksum"] = service._checksum(package)
            service.import_package(package, "override_existing", "Verify target mapping invalidation")
            mapping = core_extension.smart_core_nav_scene_maps(self.env)["action_xmlid_scene_map"]
            self.assertEqual(mapping[actions[1]], code)
            self.assertNotIn(actions[0], mapping)

    def test_declared_landing_uses_final_admitted_scenes(self):
        from odoo.addons.smart_core.delivery.edition_release_snapshot_service import EditionReleaseSnapshotService
        config = self.env["ir.config_parameter"].sudo()
        config.set_param("smart_core.platform_release_db", self.env.cr.dbname)
        config.set_param("smart_core.release_operator.catalog_source_db", self.env.cr.dbname)
        # Discovery alone is intentionally unpublished. Explicitly release the
        # native setup entry for this positive landing scenario.
        from odoo.addons.smart_core.delivery.product_policy_catalog_sync_service import ProductPolicyCatalogSyncService
        from odoo.addons.smart_core.delivery.product_scene_composition import compose_product_policy
        from odoo.addons.smart_core.delivery.product_policy_service import ProductPolicyService
        catalog = ProductPolicyCatalogSyncService(self.env).build_catalog_policy_payload(product_key="construction.standard")
        setup = next(deepcopy(row) for group in catalog["menu_groups"] for row in group["menus"]
                     if row.get("menu_xmlid") == "smart_construction_core.menu_sc_enterprise_initialization")
        setup.update(enabled=True, release_state="released", access_level="public")
        policy = self.env["sc.product.policy"].search([("product_key", "=", "construction.standard")], limit=1)
        self.assertTrue(policy)
        source_policy = ProductPolicyService(self.env).get_policy(
            product_key="construction.standard",
            enforce_release=True,
            enforce_access=True,
            use_published_policy=False,
        )
        source_policy = compose_product_policy(self.env, source_policy)
        groups = deepcopy(source_policy.get("menu_groups") or [])
        setup_found = False
        for group in groups:
            for menu in group.get("menus") or []:
                if menu.get("menu_xmlid") == setup.get("menu_xmlid"):
                    menu.update(setup)
                    setup_found = True
        if not setup_found:
            groups.append({"group_key": "test_setup", "group_label": "Setup", "menus": [setup]})
        composition = deepcopy(source_policy.get("business_scene_composition") or {})
        scenarios = composition.setdefault("scenarios", [])
        centers = composition.setdefault("centers", [])
        center_key = centers[0]["key"]
        scenarios.append({
            "key": "test.enterprise_setup",
            "active": True,
            "bindings": [{
                "menu_key": setup["menu_xmlid"],
                "center_key": center_key,
            }],
        })
        centers[0].setdefault("scenarios", []).append("test.enterprise_setup")
        source_policy["menu_groups"] = groups
        source_policy["business_scene_composition"] = composition
        snapshot_service = EditionReleaseSnapshotService(self.env)
        with patch.object(snapshot_service, "_compose_policy_draft", side_effect=lambda policy: policy):
            snapshot_service.freeze_release_surface(
                product_key="construction.standard",
                version="effective-landing-test",
                replace_active=True,
                policy_override=source_policy,
            )
        from odoo.addons.smart_core.delivery import effective_delivery_service as delivery
        from odoo.addons.smart_core.delivery.menu_service import MenuService
        from odoo.addons.smart_construction_scene.services.tenant_scene_activation import write_tenant_enablement
        from odoo.addons.smart_construction_scene.services.business_scene_enablement import business_key
        actor = self.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Effective landing actor", "login": "effective-landing-actor",
            "groups_id": [(6, 0, [self.env.ref("base.group_user").id,
                self.env.ref("smart_construction_core.group_sc_cap_business_config_admin").id])],
        })
        for scene in scenario_surface_projection.load_runtime_surface(self.env).get("scenarios") or []:
            write_tenant_enablement(self.env, self.env.company.id, business_key(scene["key"]), True)
        env = actor.with_user(actor).with_context(allowed_company_ids=[self.env.company.id]).env
        service = delivery.EffectiveDeliveryService(env)
        admitted = service.resolve()
        self.assertEqual(admitted.role_surface["scene_candidates"][0], "workspace.home")
        self.assertIn("enterprise.setup", admitted.role_surface["scene_candidates"])
        self.assertIn("enterprise.setup", service._scene_keys(admitted.payload["nav"], admitted.route_authority))
        self.assertIn("workspace.home", service._scene_keys(admitted.payload["nav"], admitted.route_authority))
        self.assertEqual(admitted.role_surface["landing_scene_key"], "workspace.home")
        self.assertEqual(admitted.role_surface["landing_path"], "/s/workspace.home")
        from odoo.addons.smart_core.handlers.system_init import SystemInitHandler
        startup = SystemInitHandler(env).handle({"params": {
            "client_type": "web_pc",
            "accepted_contract_versions": ["2.7.x"],
            "with_preload": True,
            "product_key": "construction.standard",
        }})
        self.assertTrue(startup.ok)
        self.assertEqual(startup.data["role_surface"]["landing_scene_key"], "workspace.home")
        self.assertEqual(startup.data["default_route"]["scene_key"], "workspace.home")
        self.assertEqual(startup.data["workspace_home_ref"]["scene_key"], "workspace.home")
        with patch.object(delivery, "_load_platform_release_gate", return_value={"fail_closed": True}):
            # The enabled Workbench remains the completed-enterprise landing
            # surface even when the composition release gate denies.
            self.assertEqual(service.resolve().role_surface["landing_scene_key"], "workspace.home")
        with patch.object(MenuService, "_action_is_runtime_allowed", return_value=False):
            self.assertEqual(service.resolve().role_surface["landing_scene_key"], "workspace.home")
        real_hook = delivery.call_extension_hook_first
        def selection_denies(env, name, *args, **kwargs):
            if name == "smart_core_navigation_authority_filter":
                # A final selection result with no admitted scenes must win
                # over the role's earlier, otherwise valid landing preference.
                return {"primary_actions": [], "role_home_actions": [], "contextual_actions": [], "admin_actions": []}
            return real_hook(env, name, *args, **kwargs)
        with patch.object(delivery, "call_extension_hook_first", side_effect=selection_denies):
            self.assertEqual(service.resolve().role_surface["landing_scene_key"], "workspace.home")

    def test_effective_authority_tracks_company_and_scene_enablement(self):
        from odoo.addons.smart_core.delivery.effective_delivery_service import EffectiveDeliveryService
        from odoo.addons.smart_core.delivery.runtime_route_authority import published_route_authority, published_pairs
        from odoo.addons.smart_construction_scene.services.tenant_scene_activation import write_tenant_enablement
        from odoo.addons.smart_construction_scene.services.business_scene_enablement import business_key
        actor = self.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Effective delivery actor", "login": "effective-delivery-actor",
            "groups_id": [(6, 0, [self.env.ref("base.group_user").id,
                self.env.ref("smart_construction_core.group_sc_cap_business_config_admin").id])],
        })
        company_a = self.env.company
        company_b = self.env["res.company"].create({"name": "Effective scope B"})
        actor.write({"company_ids": [(4, company_b.id)]})
        # Runtime composition is publication-only. Establish the released
        # prerequisite through the real snapshot service before company toggles.
        from odoo.addons.smart_core.delivery.edition_release_snapshot_service import EditionReleaseSnapshotService
        params = self.env["ir.config_parameter"].sudo()
        params.set_param("smart_core.platform_release_db", self.env.cr.dbname)
        params.set_param("smart_core.release_operator.catalog_source_db", self.env.cr.dbname)
        EditionReleaseSnapshotService(self.env).freeze_release_surface(
            product_key="construction.standard", version="company-scope-test", replace_active=True)
        surface = scenario_surface_projection.load_runtime_surface(self.env)
        scenarios = surface.get("scenarios") or []
        self.assertTrue(scenarios)
        for company in (company_a, company_b):
            for scene in scenarios:
                write_tenant_enablement(self.env, company.id, business_key(scene["key"]), True)
        for company in (company_a, company_b, company_a):
            env = actor.with_user(actor).with_context(allowed_company_ids=[company.id]).env
            fresh = EffectiveDeliveryService(env).resolve()
            cached = published_route_authority(env)
            self.assertTrue(any(action for _, action in published_pairs(fresh.route_authority)))
            self.assertEqual(published_pairs(cached), published_pairs(fresh.route_authority))
            self.assertEqual(cached["principal_scope"]["company_id"], company.id)
        env = actor.with_user(actor).with_context(allowed_company_ids=[company_a.id]).env
        enabled_pairs = published_pairs(published_route_authority(env))
        for scene in scenarios:
            write_tenant_enablement(self.env, company_a.id, business_key(scene["key"]), False)
        fresh = published_pairs(EffectiveDeliveryService(env).resolve().route_authority)
        self.assertEqual(published_pairs(published_route_authority(env)), fresh)
        self.assertTrue(fresh < enabled_pairs, "disabling selected compositions must revoke at least one delivered entry")
