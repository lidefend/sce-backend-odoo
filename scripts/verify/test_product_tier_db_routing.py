#!/usr/bin/env python3
import unittest
from unittest.mock import patch

import product_tier_coverage as coverage


class ProductTierDatabaseRoutingTests(unittest.TestCase):
    @patch.object(coverage, "http_post_json")
    def test_tier_intent_retains_database_route(self, post_json):
        post_json.return_value = (200, {"ok": True})
        coverage._intent(
            "http://localhost/api/v1/intent", "token", "system.init", {}, "sc_product_center"
        )
        self.assertEqual(post_json.call_args.kwargs["headers"]["X-Odoo-DB"], "sc_product_center")


if __name__ == "__main__":
    unittest.main()
