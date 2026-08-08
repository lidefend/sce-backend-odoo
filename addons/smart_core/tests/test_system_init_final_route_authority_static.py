# -*- coding: utf-8 -*-
from pathlib import Path
import unittest


class TestSystemInitFinalRouteAuthorityStatic(unittest.TestCase):
    def test_route_authority_is_rebuilt_from_final_navigation(self):
        source = (
            Path(__file__).resolve().parents[1] / "handlers" / "system_init.py"
        ).read_text(encoding="utf-8")
        marker = '_release_navigation = (data.get("release_navigation_v1") or {}).get("nav")'
        self.assertIn(marker, source)
        tail = source.split(marker, 1)[1]
        self.assertIn(
            '_delivery_navigation = (data.get("delivery_engine_v1") or {}).get("nav")',
            tail,
        )
        self.assertLess(
            tail.index("if isinstance(_release_navigation, list)"),
            tail.index("if isinstance(_delivery_navigation, list)"),
        )
        self.assertLess(
            tail.index("if isinstance(_delivery_navigation, list)"),
            tail.index('if isinstance(data.get("nav"), list)'),
        )
        self.assertIn(
            "build_route_authority(\n            role_surface,\n            nav=_final_navigation,",
            tail,
        )
        self.assertIn('data["route_authority_v1"] = _final_route_authority', tail)
        self.assertIn(
            'data["delivery_engine_v1"]["route_authority_v1"] = _final_route_authority',
            tail,
        )


if __name__ == "__main__":
    unittest.main()
