"""Keep migrated page-contract checks effective against broken production wiring."""
import ast
import contextlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts/verify' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PageContractGateTest(unittest.TestCase):
    def run_guard(self, name, mutation=None):
        module = load(name)
        read = module._read
        def altered(path):
            text = read(path)
            if mutation and path == ROOT / mutation[0]:
                self.assertIn(mutation[1], text)
                return text.replace(mutation[1], mutation[2])
            return text
        with tempfile.TemporaryDirectory() as folder, patch.object(module, '_read', altered), contextlib.redirect_stdout(io.StringIO()):
            module.REPORT_JSON = Path(folder) / 'report.json'
            module.REPORT_MD = Path(folder) / 'report.md'
            return module.main()

    def test_current_list_and_form_wiring_pass(self):
        self.assertEqual(self.run_guard('list_surface_clean_guard'), 0)
        self.assertEqual(self.run_guard('render_semantic_ready_guard'), 0)

    def test_list_rejects_disconnected_canonical_policy_calls(self):
        for runtime in ['useActionViewActionPresentationRuntime.ts', 'useActionViewFilterComputedRuntime.ts']:
            with self.subTest(runtime=runtime):
                self.assertNotEqual(self.run_guard('list_surface_clean_guard', (
                    'frontend/apps/web/src/app/action_runtime/' + runtime,
                    'resolveContractV2SurfacePolicies(options.actionContract.value)', '{}',
                )), 0)

    def test_form_rejects_bypassed_capability_and_readonly_fallback(self):
        for original in ['_apply_form_view_capabilities(data)', 'data.setdefault("effective_render_profile", _RENDER_PROFILE_READONLY)']:
            with self.subTest(original=original):
                self.assertNotEqual(self.run_guard('render_semantic_ready_guard', (
                    'addons/smart_core/utils/contract_governance.py', original, 'pass',
                )), 0)

    def test_list_rejects_retired_resolver_even_if_current_call_remains(self):
        self.assertNotEqual(self.run_guard('list_surface_clean_guard', (
            'frontend/apps/web/src/app/action_runtime/useActionViewActionPresentationRuntime.ts',
            "import { computed, type Ref } from 'vue';",
            "import { computed, type Ref } from 'vue';\nimport { resolveUnifiedPageContractV2SurfacePolicies } from './old';",
        )), 0)

    def test_form_rejects_reordered_or_disconnected_capability_chain(self):
        for original, replacement in [
            ('_apply_form_view_capabilities(data)\n    data.setdefault("effective_render_profile", _RENDER_PROFILE_READONLY)',
             'data.setdefault("effective_render_profile", _RENDER_PROFILE_READONLY)\n    _apply_form_view_capabilities(data)'),
            ('_form_render.apply_form_view_capabilities(data)', 'pass'),
        ]:
            self.assertNotEqual(self.run_guard('render_semantic_ready_guard', (
                'addons/smart_core/utils/contract_governance.py', original, replacement,
            )), 0)

    def test_shipped_form_semantics_preserve_request_but_capabilities_own_effective_profile(self):
        path = ROOT / 'addons/smart_core/utils/contract_governance.py'
        function = next(node for node in ast.parse(path.read_text()).body if isinstance(node, ast.FunctionDef) and node.name == '_apply_form_render_semantics')
        namespace = {
            '_is_form_contract': lambda _: True, '_resolve_render_profile': lambda _: 'edit',
            '_RENDER_PROFILE_READONLY': 'readonly', '_apply_form_field_groups': lambda _: None,
            '_annotate_form_actions': lambda _: None, '_apply_form_policy_contract': lambda *_: None,
        }
        exec(compile(ast.Module(body=[function], type_ignores=[]), str(path), 'exec'), namespace)
        for authorized in [False, True]:
            def capabilities(data):
                if authorized: data['effective_render_profile'] = 'edit'
            namespace['_apply_form_view_capabilities'] = capabilities
            data = {}
            namespace['_apply_form_render_semantics'](data, 'user')
            self.assertEqual(data['render_profile'], 'edit')
            self.assertEqual(data['effective_render_profile'], 'edit' if authorized else 'readonly')
            self.assertTrue(data['hide_filters_on_create'])


if __name__ == '__main__': unittest.main()
