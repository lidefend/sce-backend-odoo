from __future__ import annotations

import copy
import unittest

from scripts.ops import change_impact_planner as planner


def ts_facts(
    *,
    before: list[tuple[str, str, int, int]] | None = None,
    after: list[tuple[str, str, int, int]] | None = None,
    before_fields: list[str] | None = None,
    after_fields: list[str] | None = None,
    dynamic: bool = False,
    assertions: list[str] | None = None,
) -> dict:
    def side(rows: list[tuple[str, str, int, int]] | None, fields: list[str] | None) -> dict:
        return {
            "ok": True,
            "symbols": [
                {"name": name, "kind": kind, "start_line": start, "end_line": end}
                for name, kind, start, end in (rows or [])
            ],
            "fields": fields or [],
            "imports": [],
            "import_bindings": [],
            "assertion_calls": [
                {"call": name, "line": index + 1}
                for index, name in enumerate(assertions or [])
            ],
            "dynamic_dependency_possible": dynamic,
        }

    return {
        "before": side(before, before_fields),
        "after": side(after, after_fields),
    }


def item(path: str, before: str, after: str, facts: dict | None = None) -> dict:
    return {"path": path, "before": before, "after": after, "ts_facts": facts}


class ChangeImpactPlannerTests(unittest.TestCase):
    def plan(self, items: list[dict], evidence: dict | None = None) -> dict:
        return planner.analyze_change_set(
            items,
            base="a" * 40,
            head="b" * 40,
            evidence=evidence,
        )

    def test_decoder_only_is_l1_and_has_no_browser(self) -> None:
        facts = ts_facts(after=[("parseUiContractV2", "function", 1, 8)])
        plan = self.plan(
            [
                item(
                    "frontend/apps/web/src/app/contracts/v2/schema.ts",
                    "export function parseUiContractV2(value: unknown) { return value }",
                    "export function parseUiContractV2(value: unknown) { return value; }\n",
                    facts,
                )
            ]
        )
        self.assertEqual(plan["status"], "planned")
        self.assertEqual(plan["change_facts"][0]["layers"], ["L1"])
        self.assertNotIn(
            "frontend.presentation_browser",
            {check["id"] for check in plan["checks"]},
        )
        self.assertTrue(plan["coverage"]["assertion_closure"])
        disposition = {
            row["layer"]: row for row in plan["layer_disposition"]
        }
        self.assertEqual(disposition["L2"]["state"], "not_applicable")
        self.assertEqual(disposition["L3"]["state"], "not_applicable")
        self.assertTrue(disposition["L2"]["reverse_condition"])

    def test_renderer_registry_requires_l1_and_real_l2(self) -> None:
        facts = ts_facts(after=[("professionalComponentRegistry", "variable", 2, 12)])
        plan = self.plan(
            [
                item(
                    "frontend/apps/web/src/app/presentation/professionalComponentRegistry.ts",
                    "export const professionalComponentRegistry = {}",
                    "export const professionalComponentRegistry = { chart: {} }\n",
                    facts,
                )
            ]
        )
        self.assertEqual(plan["change_facts"][0]["layers"], ["L1", "L2"])
        check_ids = {check["id"] for check in plan["checks"]}
        self.assertIn("frontend.renderer_registry_unit", check_ids)
        self.assertIn("frontend.presentation_browser", check_ids)
        self.assertTrue(plan["coverage"]["assertion_closure"])

    def test_css_only_is_l2_without_orm(self) -> None:
        plan = self.plan(
            [
                item(
                    "frontend/apps/web/src/pages/ListPage.css",
                    ".row { height: 40px; }",
                    ".row { height: 46px; }",
                )
            ]
        )
        self.assertEqual(plan["change_facts"][0]["layers"], ["L2"])
        self.assertEqual({check["id"] for check in plan["checks"]}, {"frontend.presentation_browser"})

    def test_backend_orm_and_acl_are_l1_l3_without_browser(self) -> None:
        orm = item(
            "addons/smart_construction_core/models/project.py",
            "from odoo import models, fields\nclass Project(models.Model):\n    state = fields.Char()\n",
            "from odoo import models, fields\nclass Project(models.Model):\n    state = fields.Char()\n    def action_approve(self):\n        self.write({'state': 'approved'})\n",
        )
        acl = item(
            "addons/smart_construction_core/security/ir.model.access.csv",
            "id,name,model_id:id,group_id:id,perm_read\n",
            "id,name,model_id:id,group_id:id,perm_read\nx,x,model_project,group_user,1\n",
        )
        plan = self.plan([orm, acl])
        self.assertEqual(plan["change_facts"][0]["layers"], ["L1", "L3"])
        self.assertEqual(plan["change_facts"][1]["layers"], ["L1", "L3"])
        self.assertNotIn(
            "frontend.presentation_browser",
            {check["id"] for check in plan["checks"]},
        )
        self.assertIn("backend.contract_suite", {check["id"] for check in plan["checks"]})

    def test_mixed_change_unions_all_layers(self) -> None:
        decoder = item(
            "frontend/apps/web/src/app/contracts/v2/schema.ts",
            "export function decode(value: unknown) { return value }",
            "export function decode(value: unknown) { return value; }\n",
            ts_facts(after=[("decode", "function", 1, 3)]),
        )
        renderer = item(
            "frontend/apps/web/src/app/presentation/professionalComponentRegistry.ts",
            "export const registry = {}",
            "export const registry = { list: {} }\n",
            ts_facts(after=[("registry", "variable", 1, 2)]),
        )
        business = item(
            "addons/smart_construction_core/models/project.py",
            "from odoo import models, fields\nclass Project(models.Model):\n    state = fields.Char()\n",
            "from odoo import models, fields\nclass Project(models.Model):\n    state = fields.Char()\n    def action_start(self):\n        self.write({'state': 'started'})\n",
        )
        plan = self.plan([decoder, renderer, business])
        layers = {
            layer
            for fact in plan["change_facts"]
            for layer in fact["layers"]
        }
        self.assertEqual(layers, {"L1", "L2", "L3"})
        self.assertTrue(plan["coverage"]["assertion_closure"])

    def test_dynamic_dependency_blocks_plan(self) -> None:
        plan = self.plan(
            [
                item(
                    "frontend/apps/web/src/app/presentation/professionalComponentRegistry.ts",
                    "export const registry = {}",
                    "export const registry = loadDynamicRegistry()\n",
                    ts_facts(after=[("registry", "variable", 1, 2)], dynamic=True),
                )
            ]
        )
        self.assertEqual(plan["status"], "blocked")
        self.assertTrue(any("dynamic_dependency_unresolved" in text for text in plan["unknowns"]))

    def test_typescript_compiler_collects_symbols_and_fields(self) -> None:
        facts = planner._typescript_facts(
            [
                item(
                    "frontend/apps/web/src/app/contracts/v2/schema.ts",
                    "export interface Old { value: string }",
                    "export interface Current { value: string; extra?: string }\n"
                    "export function decode(value: unknown) { return value }\n",
                )
            ]
        )
        row = facts["frontend/apps/web/src/app/contracts/v2/schema.ts"]
        self.assertTrue(row["after"]["ok"])
        self.assertIn("Current", {value["name"] for value in row["after"]["symbols"]})
        self.assertIn("decode", {value["name"] for value in row["after"]["symbols"]})
        self.assertIn("extra", row["after"]["fields"])

    def test_vue_extractor_reads_all_script_blocks(self) -> None:
        facts = planner._typescript_facts(
            [
                item(
                    "frontend/apps/web/src/components/template/Example.vue",
                    "",
                    "<script>\n"
                    "export const classicSymbol = 1\n"
                    "</script>\n"
                    "<template><div /></template>\n"
                    "<script setup lang=\"ts\">\n"
                    "const setupSymbol = 2\n"
                    "</script>\n",
                )
            ]
        )
        names = {
            value["name"]
            for value in facts[
                "frontend/apps/web/src/components/template/Example.vue"
            ]["after"]["symbols"]
        }
        self.assertIn("classicSymbol", names)
        self.assertIn("setupSymbol", names)

    def test_rename_and_delete_keep_old_and_new_symbol_context(self) -> None:
        deleted = self.plan(
            [
                item(
                    "frontend/apps/web/src/app/contracts/v2/schema.ts",
                    "export function decodeOld(value: unknown) { return value }",
                    "",
                    ts_facts(before=[("decodeOld", "function", 1, 3)]),
                )
            ]
        )
        added = self.plan(
            [
                item(
                    "frontend/apps/web/src/app/contracts/v2/schema.ts",
                    "",
                    "export function decodeNew(value: unknown) { return value }",
                    ts_facts(after=[("decodeNew", "function", 1, 3)]),
                )
            ]
        )
        self.assertEqual(deleted["change_facts"][0]["change_kind"], "deleted")
        self.assertEqual(added["change_facts"][0]["change_kind"], "added")
        self.assertEqual(deleted["change_facts"][0]["layers"], ["L1"])
        self.assertEqual(added["change_facts"][0]["layers"], ["L1"])

    def test_docs_only_does_not_run_product_checks(self) -> None:
        plan = self.plan(
            [item("docs/architecture/example.md", "old\n", "new\n")]
        )
        self.assertEqual(plan["change_facts"][0]["layers"], ["L4"])
        self.assertEqual({check["id"] for check in plan["checks"]}, {"delivery.docs_links"})
        self.assertEqual(
            {row["state"] for row in plan["layer_disposition"]},
            {"not_applicable"},
        )

    def test_matching_evidence_can_be_reused_only_with_assertion_closure(self) -> None:
        base_plan = self.plan(
            [item("docs/architecture/example.md", "old\n", "new\n")]
        )
        decision = base_plan["decisions"][0]
        evidence = {
            "checks": {
                decision["check_id"]: {
                    "status": "passed",
                    "input_fingerprint": decision["input_fingerprint"],
                    "assertion_closure": True,
                    "environment_identity": {
                        "profile": "offline",
                        "database": "none",
                        "artifact": "none",
                    },
                }
            }
        }
        reused = self.plan(
            [item("docs/architecture/example.md", "old\n", "new\n")],
            evidence=evidence,
        )
        self.assertEqual(reused["decisions"][0]["decision"], "REUSE")
        bad = copy.deepcopy(evidence)
        bad["checks"][decision["check_id"]]["input_fingerprint"] = "0" * 64
        rerun = self.plan(
            [item("docs/architecture/example.md", "old\n", "new\n")],
            evidence=bad,
        )
        self.assertEqual(rerun["decisions"][0]["decision"], "RUN")
        wrong_environment = copy.deepcopy(evidence)
        wrong_environment["checks"][decision["check_id"]]["environment_identity"] = {
            "profile": "acceptance",
            "database": "other",
            "artifact": "other",
        }
        rerun = self.plan(
            [item("docs/architecture/example.md", "old\n", "new\n")],
            evidence=wrong_environment,
        )
        self.assertEqual(rerun["decisions"][0]["decision"], "RUN")

    def test_changed_test_assertion_is_an_l4_obligation_not_unknown(self) -> None:
        plan = self.plan(
            [
                item(
                    "frontend/apps/web/scripts/scene_entry_contract_test.ts",
                    "equal(ownsSceneRoute('scene'), true)\n",
                    "equal(ownsSceneRoute('scene'), true)\n"
                    "equal(shouldHydrateSceneContent('native_delegate', false), false)\n",
                    ts_facts(assertions=["equal"]),
                )
            ]
        )
        self.assertEqual(plan["status"], "planned")
        self.assertEqual(plan["change_facts"][0]["layers"], ["L4"])
        self.assertEqual(plan["change_facts"][0]["semantic_kinds"], ["verification_assertion"])
        self.assertIn(
            "delivery.changed_assertion",
            {check["id"] for check in plan["checks"]},
        )
        self.assertEqual(plan["unknowns"], [])

    def test_plan_exposes_forward_and_reverse_trace(self) -> None:
        component = "frontend/apps/web/src/components/template/FormSection.vue"
        page = "frontend/apps/web/src/views/ActionView.vue"
        graph = {
            "digest": "g" * 64,
            "summary": {"nodes": 2, "edges": 1, "edge_kinds": {"component_to_page": 1}},
            "impact": [
                {
                    "source": f"file:{component}",
                    "forward_consumers": [f"file:{page}"],
                    "reverse_consumers": [],
                }
            ],
        }
        plan = planner.analyze_change_set(
            [
                item(
                    component,
                    "<template><FormSection /></template>\n",
                    "<template><FormSection /></template>\n<!-- changed -->\n",
                    ts_facts(after=[("FormSection", "class", 1, 2)]),
                )
            ],
            base="a" * 40,
            head="b" * 40,
            graph=graph,
        )
        self.assertEqual(plan["schema"], "change_impact_plan.v2")
        self.assertEqual(
            plan["trace"]["forward"][0]["consumer_nodes"]["forward"],
            [f"file:{page}"],
        )
        self.assertTrue(plan["trace"]["reverse"])

    def test_unrelated_graph_change_does_not_invalidate_local_evidence(self) -> None:
        facts = ts_facts(after=[("decode", "function", 1, 3)])
        change = item(
            "frontend/apps/web/src/app/contracts/v2/schema.ts",
            "export function decode(value: unknown) { return value }\n",
            "export function decode(value: unknown) { return value ?? {} }\n",
            facts,
        )
        base_graph = {
            "digest": "1" * 64,
            "edges": [],
            "summary": {"nodes": 1, "edges": 0},
            "impact": [],
        }
        unrelated_graph = {
            "digest": "2" * 64,
            "edges": [
                {
                    "source": "file:unrelated",
                    "target": "file:other",
                    "kind": "imports",
                }
            ],
            "summary": {"nodes": 2, "edges": 1},
            "impact": [],
        }
        first = planner.analyze_change_set(
            [change],
            base="a" * 40,
            head="b" * 40,
            graph=base_graph,
        )
        second = planner.analyze_change_set(
            [change],
            base="a" * 40,
            head="b" * 40,
            graph=unrelated_graph,
        )
        self.assertEqual(
            [row["input_fingerprint"] for row in first["decisions"]],
            [row["input_fingerprint"] for row in second["decisions"]],
        )

    def test_acceptance_matrix_cases_have_expected_layers(self) -> None:
        matrix = json_matrix = {
            case["id"]: case
            for case in __import__(
                "scripts.audit.generate_change_impact_verification_inventory",
                fromlist=["impact_analysis_acceptance_matrix"],
            ).impact_analysis_acceptance_matrix()["cases"]
        }
        self.assertIn("decoder-only-compatible-field", matrix)
        self.assertEqual(matrix["decoder-only-compatible-field"]["expected_layers"], ["L1"])
        self.assertEqual(matrix["renderer-registry-only"]["expected_layers"], ["L1", "L2"])
        self.assertEqual(matrix["css-responsive-only"]["expected_layers"], ["L2"])
        self.assertEqual(matrix["orm-or-acl-change"]["expected_layers"], ["L1", "L3"])

    def test_planner_tool_change_selects_its_own_self_check(self) -> None:
        plan = self.plan(
            [
                item(
                    "scripts/ops/change_impact_planner.py",
                    "def old():\n    return 1\n",
                    "def old():\n    return 2\n",
                )
            ]
        )
        self.assertEqual(plan["change_facts"][0]["semantic_kinds"], ["change_impact_tool"])
        self.assertEqual(
            {check["id"] for check in plan["checks"]},
            {"delivery.change_impact_planner"},
        )


if __name__ == "__main__":
    unittest.main()
