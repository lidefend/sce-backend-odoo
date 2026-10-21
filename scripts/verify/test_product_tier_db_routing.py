#!/usr/bin/env python3
import unittest
from unittest.mock import patch

import product_tier_coverage as coverage


class ProductTierDatabaseRoutingTests(unittest.TestCase):
    @patch.object(coverage, "http_post_json")
    def test_tier_intent_preserves_entry_without_database_hint(self, post_json):
        post_json.return_value = (200, {"ok": True})
        coverage._intent(
            "http://localhost/t/demo/api/v1/intent", "token", "system.init", {}, "sc_product_center"
        )
        self.assertNotIn("X-Odoo-DB", post_json.call_args.kwargs["headers"])
        self.assertEqual(post_json.call_args.args[0], "http://localhost/t/demo/api/v1/intent")
        self.assertEqual(post_json.call_args.kwargs["headers"]["Authorization"], "Bearer token")


if __name__ == "__main__":
    unittest.main()
