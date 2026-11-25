"""Contract V2.7 semantic/implementation ownership tests."""
import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/contract"))
import generate_semantic_registry as generator


class ContractV27RegistryTests(unittest.TestCase):
    def setUp(self):
        self.semantic = generator.load(ROOT / generator.SEMANTIC_REL)
        self.implementation = generator.load(ROOT / generator.IMPLEMENTATION_REL)
        self.version = generator.registry_versions()

    def render_backend(self, semantic=None):
        namespace = {}
        exec(generator.render(semantic or self.semantic, version=self.version), namespace)
        return namespace

    def render_frontend(self, semantic=None, implementation=None):
        semantic = semantic or self.semantic
        implementation = implementation or self.implementation
        return generator.render_frontend_registry(
            implementation,
            version=self.version,
            root=ROOT,
        ) if semantic is self.semantic else generator.render_frontend_registry(
            implementation,
            version=self.version,
            root=ROOT,
        )

    def test_backend_carrier_has_no_frontend_component_vocabulary(self):
        data = self.render_backend()
        self.assertIn("FIELD_SEMANTICS", data)
        self.assertIn("NODE_SEMANTICS", data)
        self.assertNotIn("SEMANTIC_COMPONENTS", data)
        self.assertNotIn("COMPONENT_REGISTRATIONS", data)
        text = generator.render_repository_carrier()
        for forbidden in ("componentKey", "componentRegistry", "COMPONENT_REGISTRATIONS"):
            self.assertNotIn(forbidden, text)

    def test_frontend_implementation_may_legally_share_one_component(self):
        self.assertEqual(
            self.implementation["implementations"]["reference"]["component_key"],
            self.implementation["implementations"]["readable_value"]["component_key"],
        )
        rendered = generator.render_frontend_registry(
            self.implementation,
            version=self.version,
            root=ROOT,
        )
        self.assertIn("semanticType: 'reference'", rendered)
        self.assertIn("semanticType: 'readable_value'", rendered)

    def test_removing_frontend_implementation_does_not_invalidate_semantic(self):
        implementation = copy.deepcopy(self.implementation)
        implementation["implementations"].pop("readable_value")
        self.render_backend()  # backend remains valid without the frontend table
        generator.validate_implementation_registry(self.semantic, implementation)
        rendered = generator.render_frontend_registry(
            implementation,
            version=self.version,
            root=ROOT,
        )
        self.assertNotIn("semanticType: 'readable_value'", rendered)
        self.assertIn("'readable_value': Object.freeze(['*'])", rendered)

    def test_frontend_implementation_cannot_name_unknown_semantic(self):
        implementation = copy.deepcopy(self.implementation)
        implementation["implementations"]["future_semantic"] = {
            "component_key": "sc.future.control",
            "renderer": "FormSectionField",
        }
        with self.assertRaisesRegex(SystemExit, "undeclared semantics"):
            generator.validate_implementation_registry(self.semantic, implementation)

    def test_removing_required_semantic_fails_backend_schema(self):
        semantic = copy.deepcopy(self.semantic)
        semantic["semantics"]["money"].pop("field_types")
        with self.assertRaises(SystemExit):
            generator.validate_semantic_registry(semantic)

    def test_native_widget_payload_schema_is_semantic_protocol(self):
        payload = self.render_backend()["NATIVE_VIEW_WIDGET_SEMANTICS"]["sc_insight_banner"]
        self.assertEqual(payload["semantic"], "insight_summary")
        self.assertTrue(payload["payloadRequired"])
        self.assertEqual(payload["payloadSchema"], "insight_summary.v1")
        semantic = copy.deepcopy(self.semantic)
        semantic["native_view_widgets"]["sc_insight_banner"].pop("payload_schema")
        with self.assertRaisesRegex(SystemExit, "payload_schema exactly when payload_required"):
            self.render_backend(semantic)

    def test_generated_carriers_match_declarations(self):
        self.assertEqual(
            (ROOT / generator.CARRIER_REL).read_text(),
            generator.render_repository_carrier(),
        )
        self.assertEqual(
            (ROOT / generator.FRONTEND_REL).read_text(),
            generator.render_frontend_repository(),
        )
        self.assertEqual(
            (ROOT / generator.INDUSTRY_FRONTEND_REL).read_text(),
            generator.render_industry_repository(),
        )


if __name__ == "__main__":
    unittest.main()
