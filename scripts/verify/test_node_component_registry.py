"""Offline category/identity tests; production registry contains no node fixtures."""
import copy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/contract'))
sys.path.insert(0, str(ROOT / 'addons/smart_core'))
import generate_semantic_registry as generator
from core.contract_runtime import semantic_resolver as resolver


class NodeRegistryTests(unittest.TestCase):
    def setUp(self):
        self.component = generator.load(ROOT / generator.COMPONENT_REL)
        self.semantic = generator.load(ROOT / generator.SEMANTIC_REL)
        self.version = generator.registry_versions()
        self.key = 'sc.fixture.node'

    def render(self, component=None):
        namespace = {}
        exec(generator.render(self.semantic, component or self.component, version=self.version), namespace)
        return namespace

    def node(self):
        self.component['components'][self.key] = {'kind': 'node', 'version': '1.2.3'}

    def test_legacy_and_explicit_field_outputs_equal(self):
        original = self.render()
        original_frontend = generator.render_frontend_registry(self.component, version=self.version)
        for entry in self.component['components'].values():
            if entry.get('kind', 'field') == 'field':
                entry['kind'] = 'field'
        self.assertEqual(original['SEMANTIC_COMPONENTS'], self.render()['SEMANTIC_COMPONENTS'])
        self.assertEqual(original['COMPONENT_REGISTRATIONS'], self.render()['COMPONENT_REGISTRATIONS'])
        self.assertEqual(original_frontend, generator.render_frontend_registry(self.component, version=self.version))

    def test_missing_field_types_rejected_by_both_generators(self):
        del self.component['components']['sc.input.text']['field_types']
        with self.assertRaises(SystemExit): self.render()
        with self.assertRaises(SystemExit): generator.render_frontend_registry(self.component, version=self.version)

    def test_node_identity_carrier_does_not_generate_field_renderer(self):
        original_frontend = generator.render_frontend_registry(self.component, version=self.version)
        self.node()
        data = self.render()
        self.assertNotIn(self.key, data['SEMANTIC_COMPONENTS'].values())
        frontend = generator.render_frontend_registry(self.component, version=self.version)
        self.assertEqual(original_frontend.split('export const NODE_COMPONENT_REGISTRATIONS')[0],
                         frontend.split('export const NODE_COMPONENT_REGISTRATIONS')[0])
        self.assertIn(f"{self.key!r}: {{kind: 'node', version: '1.2.3'}}", frontend)
        self.assertNotIn(self.key, frontend.split('export const NODE_COMPONENT_REGISTRATIONS')[0])
        with patch.object(resolver, 'COMPONENT_REGISTRATIONS', data['COMPONENT_REGISTRATIONS']):
            self.assertEqual({'kind': 'node', 'version': '1.2.3'}, resolver.component_registration(self.key))
            self.assertEqual({self.key: {'version': '1.2.3'}}, resolver.component_registry([self.key]))
            returned = resolver.component_registration(self.key)
            returned['version'] = '9.9.9'
            self.assertEqual('1.2.3', resolver.component_registration(self.key)['version'])
        # No client support/readiness booleans or field renderer inferred.
        self.assertEqual({'kind', 'version'}, set(data['COMPONENT_REGISTRATIONS'][self.key]))

    def test_node_forbidden_field_attributes(self):
        self.node()
        for name, value in [('semantic', 'text'), ('field_types', ['char']), ('renderer', 'FormSectionField'), ('readiness', 'ready')]:
            with self.subTest(name=name):
                candidate = copy.deepcopy(self.component)
                candidate['components'][self.key][name] = value
                with self.assertRaises(SystemExit): self.render(candidate)

    def test_unknown_kind_and_attributes_rejected(self):
        for extra in ({'kind': 'other'}, {'surprise': True}, {'kind': None}):
            with self.subTest(extra=extra):
                candidate = copy.deepcopy(self.component)
                candidate['components']['sc.input.text'].update(extra)
                with self.assertRaises(SystemExit): self.render(candidate)

    def test_versions_are_strict_and_required(self):
        self.node()
        for version in ('1.0', '01.0.0', '1.0.0-beta', '1.0.0\n', 1, None, ''):
            with self.subTest(version=version):
                self.component['components'][self.key]['version'] = version
                with self.assertRaises(SystemExit): self.render()
        del self.component['components'][self.key]['version']
        with self.assertRaises(SystemExit): self.render()

    def test_duplicate_identity_rejected_before_loading(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'component.yaml'
            path.write_text('components:\n  sc.fixture.node: {kind: node, version: 1.0.0}\n  sc.fixture.node: {kind: node, version: 2.0.0}\n')
            with self.assertRaisesRegex(SystemExit, 'duplicate YAML key'): generator.load(path)

    def test_field_semantic_cannot_reference_node(self):
        self.node()
        self.semantic['semantics']['text']['component'] = self.key
        with self.assertRaisesRegex(SystemExit, 'cannot reference node'): self.render()

    def test_field_versions_and_source_match(self):
        data = self.render()
        self.assertEqual('1.0', data['FIELD_CONTRACT_VERSION'])
        for key, entry in data['COMPONENT_REGISTRATIONS'].items():
            if entry['kind'] == 'node':
                self.assertEqual('1.0.0', entry['version'])
                continue
            self.assertEqual({'kind': 'field', 'version': '1.0'}, entry)
            self.assertEqual({key: {'version': '1.0'}}, resolver.component_registry([key]))
        self.assertEqual((ROOT / generator.CARRIER_REL).read_text(), generator.render_repository_carrier())
        self.assertEqual((ROOT / generator.FRONTEND_REL).read_text(), generator.render_frontend_repository())

    def test_unknown_backend_key_raises(self):
        with self.assertRaisesRegex(ValueError, 'COMPONENT_UNREGISTERED'):
            resolver.component_registry(['sc.fixture.absent'])

    def test_node_roundtrip_through_existing_lint(self):
        from test_semantic_registry_lint import TempRegistryTree
        tree = TempRegistryTree()
        try:
            with tree.component.open('a') as stream:
                stream.write('\n  sc.fixture.node: {kind: node, version: "1.2.3"}\n')
            (tree.root / generator.CARRIER_REL).write_text(generator.render_repository_carrier(tree.root))
            tree.generated_frontend.write_text(generator.render_frontend_repository(tree.root))
            errors, _ = tree.run()
            self.assertEqual([], errors)
        finally:
            tree.close()


if __name__ == '__main__':
    unittest.main()
