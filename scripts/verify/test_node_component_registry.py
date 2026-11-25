"""Offline category/identity tests; production registry contains no node fixtures."""
import copy
import re
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
        original_industry = generator.render_industry_manifest(self.component, version=self.version)
        for entry in self.component['components'].values():
            if entry.get('kind', 'field') == 'field':
                entry['kind'] = 'field'
        self.assertEqual(original['SEMANTIC_COMPONENTS'], self.render()['SEMANTIC_COMPONENTS'])
        self.assertEqual(original['COMPONENT_REGISTRATIONS'], self.render()['COMPONENT_REGISTRATIONS'])
        self.assertEqual(original_frontend, generator.render_frontend_registry(self.component, version=self.version))
        self.assertEqual(original_industry, generator.render_industry_manifest(self.component, version=self.version))

    def test_missing_field_types_rejected_by_both_generators(self):
        del self.component['components']['sc.input.text']['field_types']
        with self.assertRaises(SystemExit): self.render()
        with self.assertRaises(SystemExit): generator.render_frontend_registry(self.component, version=self.version)

    def test_node_identity_carrier_does_not_generate_field_renderer(self):
        original_frontend = generator.render_frontend_registry(self.component, version=self.version)
        original_industry = generator.render_industry_manifest(self.component, version=self.version)
        self.node()
        data = self.render()
        self.assertNotIn(self.key, data['SEMANTIC_COMPONENTS'].values())
        frontend = generator.render_frontend_registry(self.component, version=self.version)
        industry = generator.render_industry_manifest(self.component, version=self.version)
        self.assertEqual(original_frontend.split('export const NODE_COMPONENT_REGISTRATIONS')[0],
                         frontend.split('export const NODE_COMPONENT_REGISTRATIONS')[0])
        self.assertEqual(original_industry, industry)
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
        for name, value in [
            ('semantic', 'text'),
            ('field_types', ['char']),
            ('renderer', 'FormSectionField'),
            ('renderer_version', '1.0.0'),
            ('contract_version', '>=2.0.0 <2.4.0'),
            ('capabilities', ['form.relation.one2many']),
            ('readiness', 'ready'),
        ]:
            with self.subTest(name=name):
                candidate = copy.deepcopy(self.component)
                candidate['components'][self.key][name] = value
                with self.assertRaises(SystemExit): self.render(candidate)

    def test_industry_capability_and_versions_are_projected(self):
        frontend = generator.render_frontend_registry(self.component, version=self.version)
        industry = generator.render_industry_manifest(self.component, version=self.version)
        self.assertIn("'form.relation.one2many': 'FormSection.relationAdapter'", frontend)
        self.assertIn("rendererVersion: '1.0.0'", industry)
        self.assertIn("supportedContractVersion: '>=2.0.0 <2.7.0'", industry)
        self.assertIn("requiredCapabilities: ['form.relation.one2many']", industry)

    def test_component_capability_range_covers_current_page_contract(self):
        negotiation_text = (
            ROOT / "addons/smart_core/core/contract_version_negotiation.py"
        ).read_text(encoding="utf-8")
        current_match = re.search(
            r'CURRENT_CONTRACT_VERSION\s*=\s*"(\d+\.\d+\.\d+)"',
            negotiation_text,
        )
        self.assertIsNotNone(current_match)
        current = tuple(int(part) for part in current_match.group(1).split("."))
        capability_range = str(self.component["defaults"]["contract_version"])
        match = re.fullmatch(r">=(\d+\.\d+\.\d+) <(\d+\.\d+\.\d+)", capability_range)
        self.assertIsNotNone(match, capability_range)
        minimum = tuple(int(part) for part in match.group(1).split("."))
        maximum_exclusive = tuple(int(part) for part in match.group(2).split("."))
        self.assertGreaterEqual(current, minimum)
        self.assertLess(current, maximum_exclusive)

    def test_native_view_widget_mapping_and_default_are_projected(self):
        data = self.render()
        self.assertEqual(
            {
                "component": "sc.display.ribbon",
                "status": "ready",
                "reasonCode": "",
                "payloadRequired": False,
                "payloadSchema": "",
            },
            data["NATIVE_VIEW_WIDGET_COMPONENTS"]["web_ribbon"],
        )
        self.assertEqual(
            {
                "component": "sc.unsupported.native_node",
                "status": "unsupported",
                "reasonCode": "NATIVE_VIEW_WIDGET_UNSUPPORTED",
            },
            data["NATIVE_VIEW_WIDGET_DEFAULT"],
        )
        frontend = generator.render_frontend_registry(self.component, version=self.version)
        self.assertIn("'web_ribbon': {component: 'sc.display.ribbon'", frontend)
        self.assertIn("component: 'sc.unsupported.native_node'", frontend)
        self.assertEqual(
            {
                "component": "sc.display.ribbon",
                "status": "ready",
                "reasonCode": "",
                "payloadRequired": False,
                "payloadSchema": "",
            },
            resolver.resolve_native_view_widget("web_ribbon"),
        )
        self.assertEqual(
            {
                "component": "sc.action.list",
                "status": "ready",
                "reasonCode": "",
                "payloadRequired": True,
                "payloadSchema": "action_list.v1",
            },
            resolver.resolve_native_view_widget("sc_stage_requirements"),
        )

    def test_native_view_widget_default_and_targets_fail_closed(self):
        self.semantic["native_view_widget_default"]["status"] = "ready"
        with self.assertRaisesRegex(SystemExit, "default cannot be ready"):
            self.render()
        self.semantic["native_view_widget_default"]["status"] = "unsupported"
        self.semantic["native_view_widgets"]["web_ribbon"]["component"] = "sc.input.text"
        with self.assertRaisesRegex(SystemExit, "must reference a node component"):
            self.render()

    def test_native_view_widget_payload_schema_must_match_payload_requirement(self):
        self.semantic["native_view_widgets"]["sc_insight_banner"].pop("payload_schema")
        with self.assertRaisesRegex(SystemExit, "payload_schema exactly when payload_required"):
            self.render()
        self.semantic = generator.load(ROOT / generator.SEMANTIC_REL)
        self.semantic["native_view_widgets"]["web_ribbon"]["payload_schema"] = "unexpected.v1"
        with self.assertRaisesRegex(SystemExit, "payload_schema exactly when payload_required"):
            self.render()

    def test_requiring_an_undeclared_capability_is_rejected(self):
        self.component['components']['sc.payment.settlement_detail_collection']['capabilities'] = [
            'form.relation.undeclared'
        ]
        with self.assertRaisesRegex(SystemExit, 'requires undeclared capability'):
            generator.render_industry_manifest(self.component, version=self.version)

    def test_capability_provider_is_required_for_required_capability(self):
        self.component['capability_providers'] = {}
        with self.assertRaisesRegex(SystemExit, 'requires undeclared capability'):
            generator.render_industry_manifest(self.component, version=self.version)

    def test_platform_capabilities_are_rejected_before_a_host_consumer_exists(self):
        self.component['components']['sc.input.text']['capabilities'] = ['form.relation.one2many']
        with self.assertRaisesRegex(SystemExit, 'platform component .* capabilities'):
            generator.render_frontend_registry(self.component, version=self.version)

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
        self.assertEqual((ROOT / generator.INDUSTRY_FRONTEND_REL).read_text(), generator.render_industry_repository())

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
            tree.generated_industry.write_text(generator.render_industry_repository(tree.root))
            errors, _ = tree.run()
            self.assertEqual([], errors)
        finally:
            tree.close()


if __name__ == '__main__':
    unittest.main()
