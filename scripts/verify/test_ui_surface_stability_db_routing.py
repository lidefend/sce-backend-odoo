#!/usr/bin/env python3
import unittest
from unittest.mock import patch

import ui_surface_stability_ready as guard


class UiSurfaceDatabaseRoutingTests(unittest.TestCase):
    @patch.object(guard, "http_post_json")
    def test_authenticated_intent_preserves_entry_without_database_hint(self, post_json):
        post_json.return_value = (200, {"ok": True})

        guard._intent(
            "http://localhost/t/demo/api/v1/intent",
            "token",
            "system.init",
            {"contract_mode": "user"},
            db_name="sc_product_center",
        )

        self.assertNotIn("X-Odoo-DB", post_json.call_args.kwargs["headers"])
        self.assertEqual(post_json.call_args.kwargs["url"], "http://localhost/t/demo/api/v1/intent")
        self.assertEqual(post_json.call_args.kwargs["headers"]["Authorization"], "Bearer token")


if __name__ == "__main__":
    unittest.main()
