"""Isolation and lifecycle safety for the local full-release carrier."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/dev'))
import frontend_release_disposable as runner


class DisposableReleaseTest(unittest.TestCase):
    def test_make_accepts_disposable_profile_before_runtime(self):
        result = subprocess.run(["make", "-n", "acceptance.runtime.carrier.provision",
                                 "SC_ACCEPTANCE_RUNTIME_PROFILE=disposable"],
                                cwd=ROOT, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_resources_do_not_alias_registered_persistent_profiles(self):
        disposable = runner.resolve('disposable')
        for name in ('local', 'candidate'):
            other = runner.resolve(name)
            for key in ('COMPOSE_PROJECT_NAME', 'DB_DATA', 'REDIS_DATA', 'ODOO_DATA',
                        'BACKEND_ACCEPTANCE_NAME', 'SC_ACCEPTANCE_CREDENTIAL_CONTAINER',
                        'ODOO_PORT', 'BACKEND_ACCEPTANCE_PORT', 'FRONTEND_ACCEPTANCE_PORT',
                        'FRONTEND_ACCEPTANCE_PIDFILE', 'SC_ACCEPTANCE_BASE_ENV_FILE'):
                self.assertNotEqual(disposable[key], other[key], key)
        self.assertEqual(disposable['ODOO_DBFILTER'], '^sc_frontend_acceptance$')
        self.assertTrue(disposable['SC_ACCEPTANCE_BASE_ENV_FILE'].startswith(str(ROOT / '.runtime/')))

    def test_credentials_are_private_fresh_and_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'release.env'
            first = runner.write_credentials(path, 'a' * 40)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                runner.write_credentials(path, 'b' * 40)
            self.assertIn('SC_SOURCE_REVISION=' + 'a' * 40, path.read_text())
            second = runner.write_credentials(Path(directory) / 'other.env', 'a' * 40)
            self.assertNotEqual(first['DB_PASSWORD'], second['DB_PASSWORD'])

    def test_existing_project_is_rejected_before_resource_mutation(self):
        calls = []
        def execute(args, env, **kwargs):
            calls.append(args)
            return subprocess.CompletedProcess(args, 0, 'existing-container\n', '')
        with patch.object(runner, 'command', execute):
            with self.assertRaisesRegex(ValueError, 'already exists'):
                runner.require_absent(runner.resolve('disposable'), {})
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][:3], ['docker', 'ps', '-aq'])

    def test_failure_still_cleans_and_records_failed_release(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            profile = runner.resolve('disposable')
            profile['SC_ACCEPTANCE_BASE_ENV_FILE'] = str(root / 'release.env')
            calls = []
            def execute(args, env, **kwargs):
                calls.append(args)
                output = ''
                if args[:3] == ['git', 'rev-parse', 'HEAD']:
                    output = 'a' * 40
                elif '--git-common-dir' in args:
                    output = str(root)
                status = 9 if 'verify.frontend.release.local' in args else 0
                return subprocess.CompletedProcess(args, status, output, '')
            with patch.object(runner, 'STATE', root), patch.object(runner, 'resolve', return_value=profile), \
                 patch.object(runner, 'command', execute), patch.object(runner, 'require_absent'):
                self.assertEqual(runner.main(), 9)
            import json
            receipt = json.loads((root / 'receipt.json').read_text())
            self.assertEqual(receipt['release_status'], 9)
            self.assertTrue(receipt['resources_absent'])
            self.assertFalse((root / 'release.env').exists())
            self.assertEqual([call[-1] for call in calls if call[0] == 'make'][-3:],
                             ['frontend.acceptance.down', 'backend.acceptance.down', 'acceptance.runtime.carrier.discard'])
            self.assertFalse(any('acceptance.frontend.fixture_orm' in call for call in calls))


if __name__ == '__main__':
    unittest.main()
