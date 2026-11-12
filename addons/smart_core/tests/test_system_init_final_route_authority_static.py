# -*- coding: utf-8 -*-
from pathlib import Path
import unittest


class TestSystemInitFinalRouteAuthorityStatic(unittest.TestCase):
    def test_configuration_actions_declare_web_surface_entry_targets(self):
        root = Path(__file__).resolve().parents[3]
        business = (
            root
            / "addons"
            / "smart_construction_core"
            / "views"
            / "support"
            / "business_config_workbench_views.xml"
        ).read_text(encoding="utf-8")
        self.assertIn("'sc_web_surface': 'business_config'", business)
        self.assertNotIn("sc_web_route", business)
        menu = (
            root / "addons" / "smart_core" / "views" / "ui_menu_config_policy_views.xml"
        ).read_text(encoding="utf-8")
        self.assertIn("'sc_web_surface': 'menu_config'", menu)
        self.assertNotIn("sc_web_route", menu)

    def test_single_navigation_contract_owns_tree_and_route_authority(self):
        system_init = (
            Path(__file__).resolve().parents[1] / "handlers" / "system_init.py"
        ).read_text(encoding="utf-8")
        compiler = (
            Path(__file__).resolve().parents[1]
            / "delivery"
            / "navigation_contract_compiler.py"
        ).read_text(encoding="utf-8")
        self.assertIn("from odoo.addons.smart_core.delivery.navigation_contract_compiler import (", system_init)
        self.assertIn("NavigationContractCompiler(", system_init)
        self.assertIn(".compile(", system_init)
        self.assertIn('data["nav"] = _compiled_navigation.nav', system_init)
        self.assertIn('data["navigation"] = _compiled_navigation.navigation', system_init)
        self.assertNotIn("filter_nav_by_route_authority(", system_init)
        self.assertNotIn("project_final_navigation_routes(", system_init)
        self.assertNotIn("project_navigation_product_policy(", system_init)

        self.assertIn(
            "self.menu_service.build_route_authority(",
            compiler,
        )
        self.assertIn(
            "self.menu_service.filter_route_authority_by_publication(",
            compiler,
        )
        self.assertIn(
            "_add_scene_internal_authority(authority, scene_internal_actions)",
            compiler,
        )
        self.assertIn(
            "self.authority_finalizer(authority)",
            compiler,
        )
        self.assertIn(
            "smart_core_navigation_authority_filter",
            system_init,
        )
        self.assertEqual(
            compiler.count("filter_nav_by_route_authority("),
            1,
        )
        self.assertIn("self.menu_service.project_canonical_navigation(", compiler)
        self.assertIn("project_final_navigation_routes(", compiler)
        self.assertIn("project_navigation_product_policy(", compiler)
        self.assertIn('navigation["product_policy"]', compiler)
        self.assertIn("canonical navigation contains unauthorized", compiler)
        self.assertIn("scenario navigation contains unauthorized", compiler)
        self.assertIn('"route_authority": authority,', compiler)
        self.assertIn('"missing_authority_count": 0,', compiler)

        authority_index = compiler.index("self.menu_service.build_route_authority(")
        scene_authority_index = compiler.index(
            "_add_scene_internal_authority(authority, scene_internal_actions)",
            authority_index,
        )
        finalizer_index = compiler.index(
            "self.authority_finalizer(authority)",
            scene_authority_index,
        )
        reconcile_index = compiler.index(
            "self.menu_service.filter_nav_by_route_authority(",
            finalizer_index,
        )
        canonical_index = compiler.index(
            "self.menu_service.project_canonical_navigation(",
            reconcile_index,
        )
        scenario_index = compiler.index(
            "self.scenario_surface_provider(nav, authority)",
            canonical_index,
        )
        self.assertLess(authority_index, scene_authority_index)
        self.assertLess(scene_authority_index, finalizer_index)
        self.assertLess(finalizer_index, reconcile_index)
        self.assertLess(reconcile_index, canonical_index)
        self.assertLess(canonical_index, scenario_index)

        tail = system_init.split("NavigationContractCompiler(", 1)[1]
        self.assertIn(
            "for _removed_navigation_carrier in (",
            tail,
        )
        for removed in (
            '"nav",',
            '"release_navigation_v1",',
            '"delivery_engine",',
            '"route_authority",',
        ):
            self.assertIn(removed, tail)

    def test_frontend_consumes_only_navigation(self):
        source = (
            Path(__file__).resolve().parents[3]
            / "frontend"
            / "apps"
            / "web"
            / "src"
            / "stores"
            / "session.ts"
        ).read_text(encoding="utf-8")
        startup = source.split("const navigation =", 1)[1].split("this.menuTree =", 1)[0]
        self.assertIn("navigation", startup)
        self.assertIn("navigation?.route_authority", startup)
        self.assertIn("Array.isArray(navigation?.nav)", startup)
        self.assertIn("navigation integrity check failed", startup)
        self.assertNotIn("release_navigation_v1", startup)
        self.assertNotIn("delivery_engine", startup)
        self.assertNotIn("result.nav", startup)

        audit = (
            Path(__file__).resolve().parents[3]
            / "frontend"
            / "apps"
            / "web"
            / "scripts"
            / "frontend_product_maturity_audit.mjs"
        ).read_text(encoding="utf-8")
        self.assertIn("value?.navigation", audit)
        self.assertIn("navigationReady", audit)
        self.assertNotIn("value?.release_navigation_v1", audit)
        self.assertNotIn("value?.delivery_engine", audit)


if __name__ == "__main__":
    unittest.main()
