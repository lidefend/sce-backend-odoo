from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.verify.frontend_probe_toolchain_guard import ROOT, check, violations, executes_blocked_probe, blocked_make_targets


class ProbeToolchainTest(unittest.TestCase):
    def test_relation_login_uses_observed_request_before_click(self):
        source = (ROOT / 'scripts/verify/record_relation_roundtrip_acceptance.js').read_text()
        start = source.index('async function login(page)')
        login = source[start:source.index('async function waitForRecordSurface', start)]
        program = """
const vm = require('node:vm');
const events = [];
const page = {
 goto: async url => { if (url !== 'https://example.invalid/t/test/login') throw Error(url); events.push('goto'); },
 locator: selector => ({ nth: () => ({ fill: async () => {} }), fill: async () => {}, click: async () => events.push('click') })
};
const context = vm.createContext({ FRONTEND_URL: 'https://example.invalid/t/test', LOGIN: 'role', PASSWORD: 'synthetic',
 authenticateBrowserProbe: async (p, login, submit) => { if (p !== page || login !== 'role') throw Error('identity'); events.push('observe'); await submit(); }, page });
vm.runInContext(process.argv[1], context);
context.login(page).then(() => {
 if (events.join(',') !== 'goto,observe,click') throw Error(events.join(','));
}).catch(e => { console.error(e.message); process.exitCode = 1; });
"""
        result = subprocess.run(['node', '-e', program, login], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(violations(source), [])

    def test_relation_lease_releases_on_probe_failure_and_success(self):
        source = (ROOT / 'scripts/verify/record_relation_roundtrip_acceptance.js').read_text()
        start = source.index('async function main()')
        main = source[start:source.index('async function runProbe', start)].replace('await import(', 'await importStub(')
        program = """
const vm = require('node:vm');
(async () => {
 for (const fail of [false, true]) {
  const events = [];
  const environment = {};
  const modules = {
   './lib/frontend_acceptance_environment.mjs': { resolveAcceptanceEnvironment: () => environment },
   './frontend_authenticated_intent.mjs': { authenticateBrowserProbe: () => {} },
   './lib/frontend_acceptance_lease.mjs': { acquireAcceptanceLease: async args => {
    if (args.environment !== environment || args.mode !== 'shared-read') throw Error('lease scope');
    events.push('acquire'); return { release: async () => events.push('release') };
   }}
  };
  const context = vm.createContext({ importStub: async name => modules[name],
   runProbe: async () => { events.push('probe'); if (fail) throw Error('expected'); } });
  vm.runInContext(process.argv[1], context);
  try { await context.main(); if (fail) throw Error('failure swallowed'); }
  catch (e) { if (!fail || e.message !== 'expected') throw e; }
  if (events.join(',') !== 'acquire,probe,release') throw Error(events.join(','));
 }
})().catch(e => { console.error(e.message); process.exitCode = 1; });
"""
        result = subprocess.run(['node', '-e', program, main], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_relation_resolution_rejects_stale_or_unmanaged_identity(self):
        source = (ROOT / 'scripts/verify/record_relation_roundtrip_acceptance.js').read_text()
        body = source[source.index('function readResolution()'):source.index('function readExplicitIdentity()')]
        program = """
const vm = require('node:vm');
const assert = require('node:assert/strict');
const base = {schema:'acceptance.record_identity_resolution.v1', expected_sha:'a'.repeat(40),
 producer:'scripts/verify/frontend_delivery_hardening_runtime_ids.py', targets:{project:{model:'project.project',record_id:5,action_id:588,menu_id:382}}};
for (const mutation of [null, b=>delete b.schema, b=>b.expected_sha='b'.repeat(40), b=>b.producer='other',
 b=>b.targets.project.record_id=0, b=>b.targets.project.action_id=1.5, b=>b.targets.project.menu_id='382']) {
 const data=structuredClone(base);if(mutation)mutation(data);
 const context=vm.createContext({fs:{readFileSync:()=>JSON.stringify(data)},RESOLUTION_PATH:'resolution.json',
 RESOLUTION_KEY:'project',EXPECTED_SHA:'a'.repeat(40),process:{env:{}}});
 vm.runInContext(process.argv[1],context);
 if(mutation)assert.throws(()=>context.readResolution());else {context.readResolution();assert.equal(context.RECORD_ID,5);}
}
"""
        result = subprocess.run(['node', '-e', program, body], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        wrapper = (ROOT / 'scripts/dev/frontend_acceptance_runtime.sh').read_text()
        self.assertIn('RELATION_RESOLUTION_KEY=project RELATION_IDENTITY_SOURCE=resolution', wrapper)
        relation = wrapper.split('      standard-relation-roundtrip-browser)')[1].split('      standard-list-surface-browser)')[0]
        self.assertIn('SC_ACCEPTANCE_LOGIN=fixture_role_pm', relation)
        self.assertIn('E2E_LOGIN=fixture_role_pm', relation)

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
