from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.verify.frontend_probe_toolchain_guard import ROOT, check, violations, executes_blocked_probe, blocked_make_targets


class ProbeToolchainTest(unittest.TestCase):
    def test_execution_detection_excludes_static_and_package_operations(self):
        name = 'scripts/ops/production_acceptance_harness.py'
        for command in [f'python3 -m py_compile {name}', f'scp {name} host:/tmp/',
                        f'python3 {name} --print-package-digest', f'node --check {name}']:
            self.assertFalse(executes_blocked_probe(command, {name}), command)
        for command in [f'python3 {name}', f'@python3 /mnt/{name} --base-url example',
                        f'ssh host "python3 /opt/{name}"']:
            self.assertTrue(executes_blocked_probe(command, {name}), command)

    def test_static_and_recovery_targets_are_not_legacy_execution(self):
        registry = json.loads((ROOT / 'config/frontend/probe_toolchain_registry.json').read_text())['tools']
        blocked = blocked_make_targets(ROOT, registry)
        for target in ['acceptance.package.verify', 'verify.production.release_contract', 'verify.release.tooling']:
            self.assertNotIn(target, blocked)
        self.assertFalse(any(target.endswith(('.remote_install', '.backup', '.readback')) for target in blocked))

    def test_harness_digest_remains_read_only_available(self):
        result = subprocess.run(['python3', 'scripts/ops/production_acceptance_harness.py', '--print-package-digest'],
                                cwd=ROOT, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertRegex(result.stdout.strip(), r'^[0-9a-f]{64}$')

    def test_registered_sources(self):
        self.assertEqual(check(ROOT), [])

    def test_patterns_distinguish_observed_transport(self):
        self.assertEqual(violations("const headers = await request.allHeaders();"), [])
        for text in ["sessionStorage.getItem(`sc_auth_token:${db}`)",
                     "{'X-Odoo-DB': database}", "fetch('/api/v1/intent?db=old')",
                     "keys.find((key) => key.startsWith('sc_auth_token'))"]:
            self.assertTrue(violations(text), text)

    def test_unregistered_and_supported_legacy_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'scripts').mkdir()
            (root / 'config/frontend').mkdir(parents=True)
            file = root / 'scripts/probe.mjs'
            file.write_text("fetch('/api/v1/intent?db=old')")
            registry = root / 'config/frontend/probe_toolchain_registry.json'
            for tools in [{}, {'scripts/probe.mjs': {'status': 'supported'}},
                          {'scripts/probe.mjs': {'status': 'blocked_legacy'}}]:
                registry.write_text(json.dumps({'tools': tools}))
                self.assertTrue(check(root))

    def test_every_blocked_tool_exits_before_runtime(self):
        registry = json.loads((ROOT / 'config/frontend/probe_toolchain_registry.json').read_text())
        blocked = [name for name, row in registry['tools'].items() if row['status'] == 'blocked_legacy']
        self.assertGreater(len(blocked), 0)
        for name in blocked:
            with self.subTest(tool=name):
                runtime = {'.py': 'python3', '.sh': 'bash'}.get(Path(name).suffix, 'node')
                result = subprocess.run([runtime, str(ROOT / name)], cwd=ROOT,
                                        capture_output=True, text=True, timeout=5)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('PROBE_TOOL_UNSUPPORTED', result.stderr)
                self.assertEqual(result.stdout, '')

    def test_make_rejects_transitive_legacy_before_prerequisites(self):
        result = subprocess.run(['make', '--no-print-directory', '-n', 'verify.round.v0_6.mini'], cwd=ROOT,
                                capture_output=True, text=True, timeout=10)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('PROBE_TOOL_UNSUPPORTED', result.stderr)
        self.assertEqual(result.stdout, '')


if __name__ == '__main__':
    unittest.main()
