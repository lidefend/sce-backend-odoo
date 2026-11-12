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

    def test_internal_actions_preserve_lifecycle_and_native_denial(self):
        from odoo.addons.smart_core.delivery import effective_delivery_service as module
        from odoo.addons.smart_core.delivery.menu_service import MenuService
        from odoo.addons.smart_core.core import native_handling_entry_catalog, scene_ready_contract_builder
        service = module.EffectiveDeliveryService(self.env)
        source = {"code": "enterprise.setup"}
        catalog = {"groups": [{"items": [{"key": "open", "action_xmlid": "smart_construction_core.action_sc_project_list"}]}]}
        # A released contextual scene need not occupy the sidebar.
        authority = {"contextual_actions": [{"scene_key": source["code"]}]}
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

    def test_imported_handling_override_reaches_page_authority_and_direct_gate(self):
        from odoo.addons.smart_core.delivery import effective_delivery_service as delivery
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
        def hook(env, name, *args):
            if name == "smart_core_navigation_authority_filter":
                return filter_business_authority(args[1], surface_index={menu_xmlid: {
                    "location": "scenario", "scenario_key": "effective", "scenario_active": True}},
                    enabled={"effective": True}, entries=[original], menu_xmlids_by_id={menu.id: menu_xmlid},
                    company_id=env.company.id)
            return real_hook(env, name, *args)
        with patch.object(scene_registry, "_load_scene_registry_content_entries_with_timings", side_effect=lambda: ([deepcopy(original)], {})), \
                patch.object(delivery.DeliveryEngine, "build", side_effect=lambda **kwargs: deepcopy(seed)), \
                patch.object(delivery, "_load_platform_release_gate", return_value={}), \
                patch.object(delivery, "call_extension_hook_first", side_effect=hook):
            self.env.registry.clear_cache()
            self.assertIn((0, old_action.id), published_pairs(published_route_authority(self.env)))
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
        EditionReleaseSnapshotService(self.env).freeze_release_surface(
            product_key="construction.standard", version="effective-landing-test", replace_active=True)
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
        self.assertEqual(admitted.role_surface["scene_candidates"][0], "enterprise.setup")
        self.assertIn("enterprise.setup", service._scene_keys([], admitted.route_authority))
        self.assertEqual(admitted.role_surface["landing_scene_key"], "enterprise.setup")
        self.assertEqual(admitted.role_surface["landing_path"], "/s/enterprise.setup")
        from odoo.addons.smart_core.handlers.system_init import SystemInitHandler
        startup = SystemInitHandler(env).handle({"params": {"with_preload": True}})
        self.assertTrue(startup.ok)
        self.assertEqual(startup.data["role_surface"]["landing_scene_key"], "enterprise.setup")
        self.assertEqual(startup.data["default_route"]["scene_key"], "enterprise.setup")
        self.assertEqual(startup.data["workspace_home_ref"]["scene_key"], "enterprise.setup")
        with patch.object(delivery, "_load_platform_release_gate", return_value={"fail_closed": True}):
            self.assertEqual(service.resolve().role_surface["landing_scene_key"], "workspace.home")
        with patch.object(MenuService, "_action_is_runtime_allowed", return_value=False):
            self.assertEqual(service.resolve().role_surface["landing_scene_key"], "workspace.home")
        real_hook = delivery.call_extension_hook_first
        def selection_denies(env, name, *args):
            if name == "smart_core_navigation_authority_filter":
                # A final selection result with no admitted scenes must win
                # over the role's earlier, otherwise valid landing preference.
                return {"primary_actions": [], "role_home_actions": [], "contextual_actions": [], "admin_actions": []}
            return real_hook(env, name, *args)
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
