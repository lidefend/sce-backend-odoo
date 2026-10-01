#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest
import tempfile
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("dev_acceptance_release_probe", ROOT / "scripts/ops/dev_acceptance_release_probe.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)
SHA = "a" * 40


class RuntimeIdentityTest(unittest.TestCase):
    def test_exact_identity_passes(self):
        def requester(_url):
            return 200, json.dumps({"git_sha": SHA, "database": "sc_demo", "frontend_build_sha256": "f" * 64}), {}

        result = MODULE.probe_runtime_identity("https://daily.example.test", "sc_demo", SHA, requester)
        self.assertEqual(result["status"], "PASS")

    def test_sha_and_database_drift_fail(self):
        def requester(_url):
            return 200, json.dumps({"git_sha": "b" * 40, "database": "other"}), {}

        result = MODULE.probe_runtime_identity("https://daily.example.test", "sc_demo", SHA, requester)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("runtime_identity_sha_mismatch", result["errors"])
        self.assertIn("runtime_identity_database_mismatch", result["errors"])

    def test_invalid_expected_sha_fails_before_network(self):
        calls = []
        result = MODULE.probe_runtime_identity("https://daily.example.test", "sc_demo", "short", lambda url: calls.append(url))
        self.assertEqual(result["errors"], ["expected_sha_invalid"])
        self.assertEqual(calls, [])


class CanonicalNavigationTest(unittest.TestCase):
    def probe(self, data):
        class Response:
            status = 200
            def __init__(self, payload): self.payload = payload
            def __enter__(self): return self
            def __exit__(self, *_): pass
            def read(self): return json.dumps(self.payload).encode()
        opener = mock.Mock()
        opener.open.side_effect = [Response({'result': {'uid': 16}}), Response({'ok': True, 'data': data})]
        with mock.patch.object(MODULE.urllib.request, 'build_opener', return_value=opener):
            return MODULE.probe_login('https://daily.example.test', 'sc_demo', 'test-reader', 'synthetic-test-secret', nav_min_actions=1)

    def test_canonical_navigation_ignores_legacy_conflicts(self):
        result = self.probe({'role_surface': {'role_code': 'reader'}, 'navigation': {'nav': [{'name': 'Canonical', 'action_id': 5}]}, 'nav': [{'name': 'Wrong', 'action_id': 8}]})
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['checks']['nav_paths_sample'], ['Canonical'])

    def test_missing_invalid_or_empty_canonical_cannot_fall_back(self):
        for navigation in (None, {}, {'nav': None}, {'nav': {}}, {'nav': []}):
            with self.subTest(navigation=navigation):
                result = self.probe({'role_surface': {'role_code': 'reader'}, 'navigation': navigation, 'nav': [{'name': 'Legacy', 'action_id': 5}], 'menus': [{'name': 'Legacy', 'action_id': 5}]})
                self.assertEqual(result['status'], 'FAIL')
                self.assertEqual(result['checks']['nav_node_count'], 0)

    def test_main_never_sends_credentials_after_identity_failure(self):
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(MODULE.sys, 'argv', ['probe', '--base-url', 'https://daily.example.test', '--db-name', 'sc_demo', '--expected-sha', SHA, '--login', 'reader', '--password', 'synthetic-test-secret', '--output', folder + '/report.json']), mock.patch.object(MODULE, 'probe_runtime_identity', return_value={'status': 'FAIL'}), mock.patch.object(MODULE, 'probe_backup', return_value={'status': 'PASS'}), mock.patch.object(MODULE, 'probe_frontend', return_value={'status': 'PASS'}), mock.patch.object(MODULE, 'probe_login') as login, mock.patch('builtins.print'):
            self.assertEqual(MODULE.main(), 1)
            login.assert_not_called()
            self.assertEqual(json.loads(Path(folder + '/report.json').read_text())['login']['status'], 'NOT_RUN')

    def test_external_readonly_make_entry_preserves_release_head_binding(self):
        source = (ROOT / 'make/dev.mk').read_text()
        release = source.split('verify.dev.acceptance.release:')[1].split('.PHONY:')[0]
        self.assertIn('SC_ACCEPTANCE_EXPECTED_SHA="$$(git rev-parse HEAD)"', release)
        readonly = source.split('verify.daily_dev.acceptance.readonly.probe:')[1].split('.PHONY:')[0]
        self.assertIn('--login "$(ACCEPTANCE_LOGIN)" --api-url "$(ACCEPTANCE_BASE_URL)"', readonly)
        self.assertIn('SC_ACCEPTANCE_EXPECTED_SHA="$(ACCEPTANCE_TARGET_SHA)"', readonly)
        self.assertIn('$(DAILY_ACCEPTANCE_NAV_REQUIRED_PATHS)', readonly)
        self.assertIn('dev_acceptance_release_probe_schema_guard.py', readonly)
        self.assertNotIn('$(RUN_ENV)', readonly)

    def test_missing_data_fails_closed(self):
        self.assertIn('canonical_navigation_nav_missing_or_invalid', self.probe(None)['errors'])


if __name__ == "__main__":
    unittest.main()
