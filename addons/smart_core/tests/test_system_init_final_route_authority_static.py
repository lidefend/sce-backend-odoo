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
        self.assertIn("'sc_web_route': '/admin/business-config'", business)
        menu = (
            root / "addons" / "smart_core" / "views" / "ui_menu_config_policy_views.xml"
        ).read_text(encoding="utf-8")
        self.assertIn("'sc_web_surface': 'menu_config'", menu)
        self.assertIn("'sc_web_route': '/admin/menu-config'", menu)

    def test_single_navigation_contract_owns_tree_and_route_authority(self):
        source = (
            Path(__file__).resolve().parents[1] / "handlers" / "system_init.py"
        ).read_text(encoding="utf-8")
        marker = '_final_navigation = data["nav"]'
        self.assertIn(marker, source)
        tail = source.split(marker, 1)[1]
        self.assertIn(
            "build_route_authority(\n            role_surface,\n            nav=_final_navigation,",
            tail,
        )
        self.assertIn('data["navigation"] = {', tail)
        self.assertIn(
            '"route_authority": _final_route_authority,',
            tail,
        )
        self.assertIn(
            "_visible_navigation_pairs - _authorized_navigation_pairs",
            tail,
        )
        build_index = tail.index("build_route_authority(")
        reconcile_index = tail.index("filter_nav_by_route_authority(")
        verify_index = tail.index("_visible_navigation_pairs = set(")
        self.assertLess(build_index, reconcile_index)
        self.assertLess(reconcile_index, verify_index)
        self.assertIn('data["nav"] = _final_navigation', tail)
        self.assertIn("canonical navigation contains unauthorized", tail)
        self.assertIn('"missing_authority_count": 0,', tail)
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
