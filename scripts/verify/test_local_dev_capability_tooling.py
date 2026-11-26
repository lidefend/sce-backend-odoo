"""Offline checks for capability evidence transport, without importing Odoo."""
import ast
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class CapabilityToolingTests(unittest.TestCase):
    def test_set_diagnostics_preserve_members_and_reject_unknown_objects(self):
        tree = ast.parse((ROOT / 'scripts/verify/local_dev_capability_ids.py').read_text())
        function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'diagnostic_json_default')
        namespace = {}
        exec(compile(ast.Module(body=[function], type_ignores=[]), '<diagnostic serializer>', 'exec'), namespace)
        serializer = namespace['diagnostic_json_default']
        data = json.loads(json.dumps({'groups': {'b', 'a'}, 'scopes': frozenset({'c'})}, default=serializer))
        self.assertEqual(data, {'groups': ['a', 'b'], 'scopes': ['c']})
        with self.assertRaises(TypeError):
            json.dumps(object(), default=serializer)

    def test_large_file_payload_takes_precedence_over_legacy_environment(self):
        source = (ROOT / 'scripts/verify/local_dev_capability_browser.mjs').read_text()
        declaration = source[source.index('const target ='):source.index('const output =')]
        payload = {'database': 'sc_dev_demo', 'cases': [{'label': 'x' * 300000}]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'capture.json'
            path.write_text(json.dumps(payload))
            env = {**os.environ, 'LOCAL_DEV_CAPABILITY_JSON_FILE': str(path), 'LOCAL_DEV_CAPABILITY_JSON': '{invalid'}
            result = subprocess.run(['node', '--input-type=module', '-e',
                "import fs from 'node:fs';\n" + declaration + '\nprocess.stdout.write(JSON.stringify(target));'],
                env=env, text=True, capture_output=True, check=True)
            self.assertEqual(json.loads(result.stdout), payload)

    def test_authorization_cannot_be_replaced_by_model_create_right(self):
        source = (ROOT / 'scripts/verify/local_dev_capability_browser.mjs').read_text()
        calculation = source[source.index('        const createRule ='):source.index("        assert.equal(await root.getAttribute('data-can-create')")]
        cases = [
            ({'type': 'action', 'action_id': 795, 'menu_id': 379}, True, False, True),
            ({'type': 'action', 'action_id': 795, 'menu_id': 379}, False, True, False),
            ({'type': 'action', 'action_id': 0, 'menu_id': 379}, True, True, False),
            ({'type': 'record_create'}, True, False, False),
            ({'type': 'record_create'}, True, True, True),
        ]
        program = 'const cases = ' + json.dumps(cases) + '; const results = []; for (const [target, allowed, modelCreate] of cases) { const contract = {actionContract:{actionRuleList:[{actionKey:"list.create", allowed, authorizationAllowed:allowed, entitlementEvaluated:true, target}]}}; const globalStatus = {effectiveRecordCapabilities:{create:modelCreate}};'
        program += calculation + 'results.push(expectedCreate); } process.stdout.write(JSON.stringify(results));'
        result = subprocess.run(['node', '--input-type=module', '-e', program], text=True, capture_output=True, check=True)
        self.assertEqual(json.loads(result.stdout), [case[3] for case in cases])


if __name__ == '__main__':
    unittest.main()
