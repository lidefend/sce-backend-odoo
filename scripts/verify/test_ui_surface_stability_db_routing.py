#!/usr/bin/env python3
import unittest
from unittest.mock import patch

import ui_surface_stability_ready as guard


class UiSurfaceDatabaseRoutingTests(unittest.TestCase):
    @patch.object(guard, "http_post_json")
    def test_authenticated_intent_retains_database_route(self, post_json):
        post_json.return_value = (200, {"ok": True})

        guard._intent(
            "http://localhost/api/v1/intent",
            "token",
            "system.init",
            {"contract_mode": "user"},
            db_name="sc_product_center",
        )

        self.assertEqual(post_json.call_args.kwargs["headers"]["X-Odoo-DB"], "sc_product_center")


if __name__ == "__main__":
    unittest.main()
