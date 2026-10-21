#!/usr/bin/env python3
import unittest
from unittest.mock import patch
import python_http_smoke_utils as utils


class RuntimeProbeDatabaseRoutingTests(unittest.TestCase):
    def test_wrong_actor_is_rejected(self):
        with patch.object(utils, 'env_value', side_effect=lambda key: {'E2E_LOGIN':'probe','E2E_PASSWORD':'secret'}.get(key,'')), \
                patch.object(utils, 'http_post_json', return_value=(200, {'ok':True,'data':{'session':{'token':'fixture-token'},'user':{'id':8,'login':'other'}}})):
            with self.assertRaisesRegex(ValueError, 'principal mismatch'):
                utils.obtain_runtime_probe_token('https://example.test/t/demo/api/v1/intent')

    def test_missing_account_does_not_fall_back_to_bootstrap_secret(self):
        with patch.object(utils, 'env_value', side_effect=lambda key: {'SC_BOOTSTRAP_LOGIN':'admin','SC_BOOTSTRAP_SECRET':'secret'}.get(key,'')), \
                patch.object(utils, 'http_post_json') as post:
            self.assertEqual(utils.obtain_runtime_probe_token('https://example.test/t/demo/api/v1/intent'), (False,'','unconfigured'))
            post.assert_not_called()

    def test_negative_auth_result_is_not_a_token(self):
        with patch.object(utils, 'env_value', return_value='fixture'), \
                patch.object(utils, 'http_post_json', return_value=(401, {'ok':False})):
            with patch.dict(utils.os.environ, {}, clear=True):
                # No company selection in this case.
                utils.env_value.side_effect=lambda key: 'fixture' if key in {'E2E_LOGIN','E2E_PASSWORD'} else ''
                self.assertEqual(utils.obtain_runtime_probe_token('https://example.test/t/demo/api/v1/intent'), (False,'','e2e_login'))


if __name__ == '__main__':
    unittest.main()
