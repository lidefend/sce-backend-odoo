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
        self.assertIn("from odoo.addons.smart_core.delivery.scene_shell_compiler import SceneShellCompiler", system_init)
        self.assertIn("NavigationContractCompiler(", system_init)
        self.assertIn("SceneShellCompiler.merge_scene_ready_contract(", system_init)
        self.assertIn("designed_scene_keys=_designed_scene_keys", system_init)
        self.assertIn(".compile(", system_init)
        self.assertIn('data["nav"] = _compiled_navigation.nav', system_init)
        self.assertIn('data["navigation"] = _compiled_navigation.navigation', system_init)
        self.assertNotIn("filter_nav_by_route_authority(", system_init)
        self.assertNotIn("project_final_navigation_routes(", system_init)
        self.assertNotIn("project_navigation_product_policy(", system_init)

        shared = (Path(__file__).resolve().parents[1] / "delivery" / "effective_delivery_service.py").read_text()
        self.assertIn("EffectiveDeliveryService(env).resolve(params)", system_init)
        self.assertIn("effective_authority=effective_delivery.route_authority", system_init)
        self.assertIn("smart_core_navigation_authority_filter", shared)
        self.assertNotIn("handlers.system_init", shared)
        self.assertNotIn("build_route_authority(", compiler)
        self.assertNotIn("filter_route_authority_by_publication(", compiler)
        self.assertNotIn("_delivery_authoritative_nav", system_init)
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
        self.assertIn("self.scene_shell_compiler.compile(", compiler)
        self.assertLess(
            compiler.index("scenario_surface = self.scenario_surface_provider(nav, authority)"),
            compiler.index("self.scene_shell_compiler.compile("),
        )
        self.assertLess(
            compiler.index("self.scene_shell_compiler.compile("),
            compiler.index("self.menu_service.project_final_navigation_routes("),
        )
        self.assertIn('"route_authority": authority,', compiler)
        self.assertIn('"missing_authority_count": 0,', compiler)

        self.assertLess(compiler.index("deepcopy(effective_authority)"), compiler.index("self.menu_service.filter_nav_by_route_authority("))
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
