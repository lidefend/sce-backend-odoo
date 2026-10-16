"""Governed guard for the R4 permission-attribution probe; no database needed.

The probe is a P4 read-only diagnostic that runs the real permission gate with a
request shim. These tests pin the properties that make its output trustworthy:
it refuses commit, binds the registered database and a non-sudo actor, calls the
unmodified gate, restores every patched hook, attributes only declared
scenarios and exports no record values.
"""
import ast
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name('local_dev_runtime_permission_probe.py')
SOURCE = SCRIPT.read_text()
TREE = ast.parse(SOURCE)

EXPECTED_REPORT_KEYS = {
    'schema',
    'database',
    'acceptance_pass',
    'principal',
    'request',
    'identity',
    'import_ms',
    'gate',
    'warm',
    'phases_ms',
    'call_counts',
    'entitlement_model_available',
    'action_resolution',
    'action_auth_scope',
    'negatives',
    'findings',
    'limitations',
}

EXPECTED_NEGATIVES = {
    'unpublished_menu_pair',
    'nonexistent_model',
    'synthetic_navigation_menu',
    'action_group_excluded',
    'company_scope_switch',
}


def _report_keys():
    keys = set()
    for node in ast.walk(TREE):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name) \
                    and target.value.id == 'REPORT' and isinstance(target.slice, ast.Constant):
                keys.add(target.slice.value)
            if isinstance(target, ast.Name) and target.id == 'REPORT' and isinstance(node.value, ast.Dict):
                for key in node.value.keys:
                    if isinstance(key, ast.Constant):
                        keys.add(key.value)
    return keys


def _helper(name):
    for node in TREE.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError('missing helper: ' + name)


def _load_helpers(names):
    module = ast.Module(body=[_helper(name) for name in names], type_ignores=[])
    namespace = {'STATE': {'scenario': None, 'phase': None, 'phases': {}, 'counts': {}}}
    exec(compile(module, str(SCRIPT), 'exec'), namespace)  # noqa: S102 - governed test harness
    return namespace


class PermissionProbeGuardTests(unittest.TestCase):
    def test_refuses_commit_and_binds_the_registered_database(self):
        self.assertIn('assert env.cr.dbname == DATABASE', SOURCE)
        self.assertIn('raise RuntimeError("permission probe forbids commit")', SOURCE)
        self.assertIn('env.cr.commit = _refuse_commit', SOURCE)
        self.assertIn('env.cr.commit = _ORIGINAL_COMMIT', SOURCE)
        self.assertRegex(SOURCE, r'env\.cr\.rollback\(\)\nenv\.cr\.commit = _ORIGINAL_COMMIT')

    def test_runs_the_unmodified_gate_on_a_non_sudo_principal(self):
        self.assertIn('ok = bool(ip.check_intent_permission(ctx))', SOURCE)
        self.assertIn('assert not actor.su, "actor must not be elevated"', SOURCE)
        self.assertIn('"sudo": bool(actor.su)', SOURCE)
        self.assertIn('"xmlid": "smart_construction_demo.user_demo_role_finance"', SOURCE)
        self.assertNotIn('with_user(', SOURCE)
        self.assertNotIn('skip_auth', SOURCE)

    def test_restores_every_patched_hook(self):
        self.assertIn('ip.request = _ORIGINAL_REQUEST', SOURCE)
        self.assertIn('type(env.cr).execute = _SQL_ORIGINAL', SOURCE)
        self.assertIn('        ip.request = _ORIGINAL_REQUEST\n    return ok, error', SOURCE)
        self.assertIn('wrapper.__wrapped__ = original', SOURCE)

    def test_attributes_only_declared_scenarios(self):
        namespace = _load_helpers(['_mark', '_bump'])
        namespace['STATE']['scenario'] = None
        namespace['STATE']['phase'] = 'setup'
        namespace['_mark']('x', 5.0)
        namespace['_bump']('x')
        self.assertEqual(namespace['STATE']['phases'], {})
        self.assertEqual(namespace['STATE']['counts'], {})
        namespace['STATE']['scenario'] = 'with_menu_id'
        namespace['_mark']('x', 5.0)
        namespace['_mark']('x', 2.5)
        namespace['_bump']('x')
        self.assertEqual(namespace['STATE']['phases'], {'with_menu_id': {'setup': {'x': 7.5}}})
        self.assertEqual(namespace['STATE']['counts'], {'with_menu_id': {'setup': {'x': 1}}})

    def test_unattributed_guard_is_load_bearing(self):
        unguarded = SOURCE.replace(
            '    if STATE["scenario"] is None:\n'
            '        return  # setup/warm-up work outside a declared scenario is not attributed\n', '')
        unguarded = unguarded.replace('    if STATE["scenario"] is None:\n        return\n', '')
        self.assertNotEqual(unguarded, SOURCE)
        tree = ast.parse(unguarded)
        module = ast.Module(body=[node for node in tree.body
                                  if isinstance(node, ast.FunctionDef) and node.name in {'_mark', '_bump'}],
                            type_ignores=[])
        namespace = {'STATE': {'scenario': None, 'phase': 'setup', 'phases': {}, 'counts': {}}}
        exec(compile(module, str(SCRIPT), 'exec'), namespace)  # noqa: S102 - governed test harness
        namespace['_mark']('x', 5.0)
        namespace['_bump']('x')
        self.assertEqual(list(namespace['STATE']['phases']), [None])
        self.assertEqual(list(namespace['STATE']['counts']), [None])
        guarded = _load_helpers(['_mark', '_bump'])
        guarded['STATE']['phase'] = 'setup'
        guarded['_mark']('x', 5.0)
        guarded['_bump']('x')
        self.assertEqual(guarded['STATE']['phases'], {})
        self.assertEqual(guarded['STATE']['counts'], {})

    def test_declares_the_boundary_counterexamples(self):
        for name in EXPECTED_NEGATIVES:
            self.assertIn('"%s"' % name, SOURCE)
        self.assertIn('"boundary_denials"', SOURCE)
        self.assertIn('"no_redundant_duplicate_authority_build_in_one_gate"', SOURCE)
        self.assertIn('"published_route_authority_is_the_cold_owner"', SOURCE)

    def test_report_exports_the_declared_keys_only(self):
        self.assertEqual(_report_keys(), EXPECTED_REPORT_KEYS)
        for banned in ('.name', 'login', 'password', 'token', 'payload_json'):
            self.assertNotIn('REPORT["fields"]', SOURCE)
            self.assertNotRegex(SOURCE, r'REPORT\[[^\]]*\]\s*=\s*[^\n]*\.name\b')
        self.assertIn('REPORT["limitations"]', SOURCE)

    def test_shim_exposes_only_the_gate_inputs(self):
        self.assertIn('class _RequestShim', SOURCE)
        self.assertIn('self.session = SimpleNamespace(db=DATABASE, uid=environment.uid)', SOURCE)
        self.assertIn('principal = {', SOURCE)
        self.assertIn('from odoo.addons.smart_core.core.context import RequestContext', SOURCE)


if __name__ == '__main__':
    unittest.main()
