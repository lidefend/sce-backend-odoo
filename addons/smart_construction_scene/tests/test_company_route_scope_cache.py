# -*- coding: utf-8 -*-
from unittest.mock import patch

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
