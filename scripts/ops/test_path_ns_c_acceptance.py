import json
import os
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from scripts.ops import path_ns_c_acceptance as probe


class NamespaceAcceptanceTest(unittest.TestCase):
    def test_root_consumes_declared_namespace_redirect(self):
        public = {"root_path_action": "redirect", "root_path_redirect_status": 308, "root_path_redirect_location": "/t/demo/"}
        self.assertTrue(probe._root_requires_namespace(308, {"Location": "/t/demo/"}, b'', public))

    def test_undeclared_redirect_is_rejected(self):
        self.assertFalse(probe._root_requires_namespace(308, {"Location": "/t/demo/"}, b'', {}))

    def test_wrong_namespace_is_rejected(self):
        public = {"root_path_action": "redirect", "root_path_redirect_status": 308, "root_path_redirect_location": "/t/other/"}
        self.assertFalse(probe._root_requires_namespace(308, {"Location": "/t/demo/"}, b'', public))

    def test_external_authority_redirect_is_rejected(self):
        public = {"root_path_action": "redirect", "root_path_redirect_status": 308, "root_path_redirect_location": "//evil.example/"}
        self.assertFalse(probe._root_requires_namespace(308, {"Location": "//evil.example/"}, b'', public))

    def test_missing_credentials_stop_before_network(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(probe, '_opener') as opener:
            with self.assertRaisesRegex(ValueError, 'managed namespace acceptance credentials required'):
                probe.run_checks('http://unused', 'a' * 40, '')
            opener.assert_not_called()

    def test_partial_credentials_do_not_fall_back(self):
        with patch.dict(os.environ, {'SC_PATH_NS_TENANT_PASSWORD': 'test-only-tenant'}, clear=True):
            with self.assertRaisesRegex(ValueError, 'SC_PATH_NS_PLATFORM_PASSWORD'):
                probe._credentials()

    def test_login_consumes_supplied_password(self):
        response = json.dumps({'data': {'session': {'token': 'test-token'}}}).encode()
        with patch.object(probe, '_call', return_value=(200, {}, response)) as call:
            self.assertEqual(probe._login(None, 'http://unused', '/platform-admin', 'test-only-platform')[1], 'test-token')
            self.assertEqual(call.call_args.kwargs['body']['params'], {'login': 'admin', 'password': 'test-only-platform'})

    def test_remote_source_compiles_and_secrets_stay_off_argv(self):
        secrets = {key: 'test-only-' + key for key in probe.CREDENTIAL_ENV_KEYS}
        args = SimpleNamespace(base_url='http://127.0.0.1:18081', repo='/tmp/repo path', expected_sha='a' * 40, ssh_host='sc-root')
        result = SimpleNamespace(returncode=0, stdout=b'{}', stderr=b'')
        with patch.dict(os.environ, secrets, clear=True), patch.object(probe.subprocess, 'run', return_value=result) as run:
            probe._run_remote(args)
            source = run.call_args.kwargs['input']
            compile(source, '<remote-wrapper>', 'exec')
            for value in secrets.values():
                self.assertNotIn(value, repr(run.call_args.args))
            with patch.object(probe, '__file__', probe.__file__):
                self.assertIn(b'exec(compile(', source)

    def test_remote_nonzero_exit_cannot_become_a_pass(self):
        report = json.dumps({'summary': {'failed': 0, 'passed': 1, 'total': 1, 'status': 'PASS'}, 'checks': []})
        with patch('sys.argv', ['probe', '--ssh-host', 'sc-root', '--emit-json']), patch.object(probe, '_run_remote', return_value=(report, 'transport failed', 255)), patch('sys.stdout'):
            self.assertEqual(probe.main(), 1)


if __name__ == '__main__':
    unittest.main()
