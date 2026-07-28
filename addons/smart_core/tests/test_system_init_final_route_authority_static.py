# -*- coding: utf-8 -*-
from pathlib import Path
import unittest


class TestSystemInitFinalRouteAuthorityStatic(unittest.TestCase):
    def test_route_authority_is_rebuilt_from_final_navigation(self):
        source = (
            Path(__file__).resolve().parents[1] / "handlers" / "system_init.py"
        ).read_text(encoding="utf-8")
        marker = "_final_navigation = data.get(\"nav\")"
        self.assertIn(marker, source)
        tail = source.split(marker, 1)[1]
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
