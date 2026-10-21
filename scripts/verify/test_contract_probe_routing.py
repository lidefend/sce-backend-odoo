#!/usr/bin/env python3
from __future__ import annotations

import unittest
from unittest.mock import patch

import python_http_smoke_utils as utils


class ContractProbeRoutingTest(unittest.TestCase):
    def test_namespaced_entry_is_preserved(self):
        self.assertEqual(utils.build_intent_url('https://example.test/t/demo'),
                         'https://example.test/t/demo/api/v1/intent')
        self.assertEqual(utils.build_intent_url('https://example.test/platform-admin'),
                         'https://example.test/platform-admin/api/v1/intent')

    def test_missing_entry_does_not_guess_localhost(self):
        with patch.dict(utils.os.environ, {}, clear=True), self.assertRaisesRegex(ValueError, 'E2E_BASE_URL'):
            utils.get_base_url()

    def test_legacy_hints_stop_before_network(self):
        cases = [('https://example.test/t/demo/api/v1/intent?db=old', {}, {}),
                 ('https://example.test/t/demo/api/v1/intent', {}, {'X-Odoo-DB': 'old'}),
                 ('https://example.test/t/demo/api/v1/intent', {'params': {'db': 'old'}}, {}),
                 ('https://example.test/t/demo/api/v1/intent', {'context': {'database': 'old'}}, {})]
        for url, payload, headers in cases:
            with self.subTest(url=url, payload=payload, headers=headers), patch.object(utils, '_request_json') as request:
                with self.assertRaisesRegex(ValueError, 'PROBE_TOOL_UNSUPPORTED'):
                    utils.http_post_json(url, payload, headers)
                request.assert_not_called()

    def test_company_and_identity_are_bound_at_login(self):
        response = {'ok': True, 'data': {'session': {'token': 'fixture-token'}, 'user': {'id': 7, 'login': 'probe'}}}
        with patch.object(utils, 'env_value', side_effect=lambda key: {'E2E_LOGIN':'probe', 'E2E_PASSWORD':'secret', 'E2E_COMPANY_ID':'5'}.get(key, '')), \
                patch.object(utils, 'http_post_json', return_value=(200, response)) as post:
            self.assertEqual(utils.obtain_runtime_probe_token('https://example.test/t/demo/api/v1/intent'),
                             (True, 'fixture-token', 'e2e_login'))
            self.assertEqual(post.call_args.args[1]['params'], {'login':'probe', 'password':'secret', 'company_id':5})
            self.assertNotIn('X-Odoo-DB', post.call_args.kwargs['headers'])


if __name__ == '__main__':
    unittest.main()
