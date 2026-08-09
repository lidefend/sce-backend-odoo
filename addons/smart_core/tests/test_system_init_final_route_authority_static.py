# -*- coding: utf-8 -*-
from pathlib import Path
import unittest


class TestSystemInitFinalRouteAuthorityStatic(unittest.TestCase):
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
        self.assertIn('data["navigation_v1"] = {', tail)
        self.assertIn(
            '"route_authority_v1": _final_route_authority,',
            tail,
        )
        self.assertIn(
            "_visible_navigation_pairs - _authorized_navigation_pairs",
            tail,
        )
        self.assertIn("canonical navigation contains unauthorized", tail)
        self.assertIn('"missing_authority_count": 0,', tail)
        for removed in (
            '"nav",',
            '"release_navigation_v1",',
            '"delivery_engine_v1",',
            '"route_authority_v1",',
        ):
            self.assertIn(removed, tail)

    def test_frontend_consumes_only_navigation_v1(self):
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
        self.assertIn("navigation_v1", startup)
        self.assertIn("navigation?.route_authority_v1", startup)
        self.assertIn("Array.isArray(navigation?.nav)", startup)
        self.assertIn("navigation_v1 integrity check failed", startup)
        self.assertNotIn("release_navigation_v1", startup)
        self.assertNotIn("delivery_engine_v1", startup)
        self.assertNotIn("result.nav", startup)


if __name__ == "__main__":
    unittest.main()
