from __future__ import annotations

import unittest

from scripts.ops import change_impact_graph as graph


def ts_fact(
    *,
    imports: list[tuple[str, list[str]]] | None = None,
    assertions: list[str] | None = None,
) -> dict:
    return {
        "after": {
            "ok": True,
            "symbols": [],
            "fields": [],
            "imports": [specifier for specifier, _ in imports or []],
            "import_bindings": [
                {
                    "specifier": specifier,
                    "type_only": False,
                    "bindings": [
                        {"imported": name, "local": name} for name in names
                    ],
                }
                for specifier, names in imports or []
            ],
            "assertion_calls": [
                {"call": name, "line": index + 1}
                for index, name in enumerate(assertions or [])
            ],
            "dynamic_dependency_possible": False,
        }
    }


class SemanticGraphTests(unittest.TestCase):
    def build(self) -> dict:
        registry = "frontend/apps/web/src/app/presentation/professionalComponentRegistry.ts"
        generated = "frontend/apps/web/src/app/presentation/semantic_registry.generated.ts"
        component = "frontend/apps/web/src/components/template/FormSection.vue"
        control = "frontend/apps/web/src/components/professional-fields/ProfessionalBaseFieldControl.vue"
        page = "frontend/apps/web/src/views/ActionView.vue"
        test = "frontend/apps/web/scripts/form_section_test.ts"
        model = "addons/smart_construction_core/models/project.py"
        decoder = "frontend/apps/web/src/app/contracts/v2/schema.ts"
        producer = "addons/smart_core/core/ui_contract_v2_assembler.py"
        files = {
            registry: "export const registry = {};\n",
            generated: (
                "export const SEMANTIC_REGISTRY_ROWS = ["
                "{componentKey: 'sc.input.text', renderer: 'ProfessionalBaseFieldControl'}]"
            ),
            component: (
                "import ProfessionalBaseFieldControl from "
                "'../professional-fields/ProfessionalBaseFieldControl.vue';\n"
                "import { registry } from '../../app/presentation/professionalComponentRegistry';\n"
            ),
            control: "<template><input /></template>\n",
            page: "import FormSection from '../components/template/FormSection.vue';\n",
            test: "import FormSection from '../src/components/template/FormSection.vue';\n",
            model: (
                "from odoo import models, fields\n"
                "class Project(models.Model):\n"
                "    _name = 'project.project'\n"
                "    def action_approve(self):\n"
                "        self.write({'state': 'approved'})\n"
            ),
            decoder: "export function decode(value: unknown) { return value }\n",
            producer: "def build_ui_contract():\n    return {}\n",
        }
        facts = {
            registry: ts_fact(),
            generated: ts_fact(),
            component: ts_fact(
                imports=[
                    (
                        "../professional-fields/ProfessionalBaseFieldControl.vue",
                        ["ProfessionalBaseFieldControl"],
                    ),
                    (
                        "../../app/presentation/professionalComponentRegistry",
                        ["registry"],
                    )
                ]
            ),
            control: ts_fact(),
            page: ts_fact(
                imports=[("../components/template/FormSection.vue", ["FormSection"])]
            ),
            test: ts_fact(
                imports=[
                    ("../src/components/template/FormSection.vue", ["FormSection"])
                ],
                assertions=["equal", "deepEqual"],
            ),
            decoder: ts_fact(),
        }
        return graph.build_semantic_graph(
            files,
            revision="a" * 40,
            ts_facts=facts,
            changed_paths=[registry, control, test, model],
        )

    def test_compiler_edges_connect_registry_component_page_and_assertion(self) -> None:
        document = self.build()
        edge_kinds = {edge["kind"] for edge in document["edges"]}
        self.assertIn("imports", edge_kinds)
        self.assertIn("renderer_registry_to_component", edge_kinds)
        self.assertIn("component_to_page", edge_kinds)
        self.assertIn("asserts_consumer", edge_kinds)
        affected = {
            row["source"]: row for row in document["impact"]
        }
        control_node = (
            "file:frontend/apps/web/src/components/professional-fields/"
            "ProfessionalBaseFieldControl.vue"
        )
        self.assertIn(
            "file:frontend/apps/web/src/views/ActionView.vue",
            affected[control_node]["forward_consumers"],
        )

    def test_python_method_to_orm_operation_is_ast_derived(self) -> None:
        document = self.build()
        operations = [
            edge
            for edge in document["edges"]
            if edge["kind"] == "business_method_to_orm"
        ]
        self.assertTrue(operations)
        self.assertIn(
            "operation:orm.write",
            {edge["target"] for edge in operations},
        )
        self.assertIn(
            "action_approve",
            {binding for edge in operations for binding in edge["bindings"]},
        )

    def test_graph_is_deterministic_and_keeps_static_inference_confidence(self) -> None:
        first = self.build()
        second = self.build()
        self.assertEqual(first["digest"], second["digest"])
        contract_edges = [
            edge
            for edge in first["edges"]
            if edge["kind"] == "contract_producer_to_decoder"
        ]
        self.assertTrue(contract_edges)
        self.assertTrue(all(edge["confidence"] == "medium" for edge in contract_edges))


if __name__ == "__main__":
    unittest.main()
