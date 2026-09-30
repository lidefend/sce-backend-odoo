"""Public industry hooks preserve defaults without touching an Odoo environment."""
import ast
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / 'addons/smart_construction_core'
HOOKS = ('get_create_field_fallback_contributions', 'smart_core_create_field_fallbacks',
         'get_create_default_skip_field_contributions', 'smart_core_create_default_skip_fields')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CreateDefaultHooksTest(unittest.TestCase):
    def setUp(self):
        self.maps = load('policy_maps_test', MODULE / 'core_extension_policy_maps.py')
        package = types.ModuleType('odoo.addons.smart_construction_core')
        package.core_extension_policy_maps = self.maps
        stubs = {'odoo': types.ModuleType('odoo'), 'odoo.addons': types.ModuleType('odoo.addons'),
                 'odoo.addons.smart_construction_core': package}
        with patch.dict(sys.modules, stubs):
            self.accessors = load('policy_accessors_test', MODULE / 'core_extension_policy_accessors.py')
        tree = ast.parse((MODULE / 'core_extension.py').read_text())
        public = [node for node in tree.body if isinstance(node, ast.Assign)
                  and any(isinstance(target, ast.Name) and target.id in HOOKS for target in node.targets)]
        self.exports = {'_policy_accessors': self.accessors}
        exec(compile(ast.Module(body=public, type_ignores=[]), 'industry_hook_exports', 'exec'), self.exports)

    def test_public_hook_exports_remain_callable(self):
        for name in HOOKS:
            self.assertTrue(callable(self.exports.get(name)), name)
            self.assertEqual(self.exports[name].__name__, name)

    def test_task_state_is_left_to_orm_default(self):
        for name in HOOKS[2:]:
            self.assertEqual(self.exports[name](object(), 'project.task'), ('sc_state',))

    def test_unrelated_models_have_no_skip_policy(self):
        for model in (None, '', 'project.project', 'unknown.model'):
            for name in HOOKS[2:]:
                self.assertEqual(self.exports[name](object(), model), ())

    def test_fallback_values_and_shallow_copy_are_preserved(self):
        expected = {'selection_defaults': {'privacy_visibility': 'followers', 'rating_status': 'stage',
                    'last_update_status': 'to_define', 'rating_status_period': 'monthly'}}
        for name in HOOKS[:2]:
            result = self.exports[name](object(), 'project.project')
            self.assertEqual(result, expected)
            result['new'] = True
            self.assertNotIn('new', self.maps.INDUSTRY_CREATE_FIELD_FALLBACKS['project.project'])
            self.assertEqual(self.exports[name](object(), 'unknown.model'), {})


if __name__ == '__main__':
    unittest.main()
