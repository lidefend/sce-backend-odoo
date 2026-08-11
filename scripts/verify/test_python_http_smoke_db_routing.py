#!/usr/bin/env python3
import unittest
from unittest.mock import patch

import python_http_smoke_utils as utils


class RuntimeProbeDatabaseRoutingTests(unittest.TestCase):
    @patch.object(utils, "env_value")
    @patch.object(utils, "http_post_json")
    def test_login_routes_before_authentication(self, post_json, env_value):
        values = {"E2E_LOGIN": "probe", "E2E_PASSWORD": "secret"}
        env_value.side_effect = lambda key: values.get(key, "")
        post_json.return_value = (200, {"ok": True, "data": {"session": {"token": "token"}}})

        ok, token, source = utils.obtain_runtime_probe_token(
            "http://localhost/api/v1/intent", "sc_product_center"
        )

        self.assertTrue(ok)
        self.assertEqual(token, "token")
        self.assertEqual(source, "e2e_login")
        self.assertEqual(post_json.call_args.kwargs["headers"]["X-Odoo-DB"], "sc_product_center")

    @patch.object(utils, "env_value")
    @patch.object(utils, "http_post_json")
    def test_bootstrap_routes_before_authentication(self, post_json, env_value):
        values = {
            "SC_BOOTSTRAP_LOGIN": "admin",
            "SC_BOOTSTRAP_SECRET": "secret",
        }
        env_value.side_effect = lambda key: values.get(key, "")
        post_json.return_value = (200, {"ok": True, "data": {"session": {"token": "token"}}})

        ok, _, source = utils.obtain_runtime_probe_token(
            "http://localhost/api/v1/intent", "sc_product_center"
        )

        self.assertTrue(ok)
        self.assertEqual(source, "dev_test_bootstrap")
        self.assertEqual(post_json.call_args.kwargs["headers"]["X-Odoo-DB"], "sc_product_center")


if __name__ == "__main__":
    unittest.main()
