#!/usr/bin/env python3
import unittest
from unittest.mock import patch

import platform_performance_smoke as smoke


class PlatformPerformanceDatabaseRoutingTests(unittest.TestCase):
    @patch.object(smoke, "http_post_json")
    def test_sample_retains_database_route(self, post_json):
        post_json.return_value = (200, {"ok": True})

        smoke._intent_call(
            "http://localhost/api/v1/intent",
            "token",
            "system.init",
            {},
            "sc_product_center",
        )

        self.assertEqual(post_json.call_args.kwargs["headers"]["X-Odoo-DB"], "sc_product_center")


if __name__ == "__main__":
    unittest.main()
