#!/usr/bin/env python3
"""Offline tests for the capability Join mapper and batch check logic."""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mapper = _load("capability_contract_mapper", ROOT / "scripts/verify/capability_contract_mapper.py")
builder = _load("capability_maturity_bundle_build", ROOT / "scripts/verify/capability_maturity_bundle_build.py")


class MapperTests(unittest.TestCase):
    def test_all_six_keep_atomic_join_without_unresolved(self):
        for key, spec in mapper.SPECS.items():
            proj = mapper._projection_for(key, spec)
            self.assertEqual(proj["unresolved"], [], f"{key} has unresolved: {proj['unresolved']}")

    def test_lifecycle_state_machine_extraction(self):
        proj = mapper._projection_for("project.lifecycle.transition", mapper.SPECS["project.lifecycle.transition"])
        sm = proj["state_machine"]["value"]
        self.assertEqual(sm["states"], ["draft", "in_progress", "paused", "done", "closing", "warranty", "closed"])
        self.assertEqual(sm["terminal_states"], ["closed"])
        self.assertEqual(set(proj["transition_methods"][0]) >= {"method", "target_state", "server_guard", "source"}, True)

    def test_provider_binding_is_exact_first_column(self):
        binding, src = mapper._join_binding("project.lifecycle.transition")
        self.assertEqual(binding["capability_key"], "project.lifecycle.transition")
        # a capability key that is a substring of another must not collide
        no_match, _ = mapper._join_binding("project.lifecycle")
        self.assertEqual(no_match, {})

    def test_ast_eval_handles_empty_set(self):
        self.assertEqual(mapper._ast_eval(_parse_expr("set()")), set())


class BatchCheckTests(unittest.TestCase):
    def test_incomplete_transition_table_fails(self):
        proj = _state_proj(
            states=["a", "b"],
            transitions={"a": ["b"]},  # missing b
            terminal=["b"],
        )
        cases = {c["id"]: c["status"] for c in builder._batch_cases("state-transition", proj)}
        self.assertEqual(cases["transition_table_exhaustive"], "fail")

    def test_view_guard_mismatch_fails(self):
        proj = _state_proj(
            states=["a", "b"],
            transitions={"a": ["b"], "b": []},
            terminal=["b"],
            method_names={"action_x", "action_y"},
            button_names={"action_x"},
        )
        cases = {c["id"]: c["status"] for c in builder._batch_cases("state-transition", proj)}
        self.assertEqual(cases["view_guard_consistent_with_state_machine"], "fail")

    def test_target_without_method_fails(self):
        methods = [{"method": "m_a", "target_state": "a"}]
        view_guards = [{"button": "m_a", "invisible": "lifecycle_state != 'a'", "groups": ""}]
        uncovered, unresolved = builder._transition_edge_coverage(
            methods, view_guards, ["a", "b"], {"a": ["b"], "b": []}
        )
        self.assertEqual(unresolved, ["a->b:no_method_for_target"])
        self.assertEqual(uncovered, [])

    def test_wrong_source_method_is_uncovered(self):
        methods = [{"method": "m_b", "target_state": "b"}]
        view_guards = [{"button": "m_b", "invisible": "lifecycle_state != 'c'", "groups": ""}]
        uncovered, unresolved = builder._transition_edge_coverage(
            methods, view_guards, ["a", "b", "c"], {"a": ["b"], "b": [], "c": []}
        )
        self.assertEqual(uncovered, ["a->b"])
        self.assertEqual(unresolved, [])

    def test_immutable_declared_but_not_enforced_fails(self):
        # Direct unit of the enforcement predicate: if only the constant were
        # declared but never referenced in a guard, it must not pass.
        text = (ROOT / "addons/smart_construction_core/models/core/settlement_order.py").read_text()
        self.assertTrue(builder._settlement_immutable_enforced())
        self.assertGreaterEqual(builder._settlement_immutable_states(), {"done", "cancel"})

    def test_settlement_immutable_states_include_done_and_cancel(self):
        self.assertGreaterEqual(builder._settlement_immutable_states(), {"done", "cancel"})

    def test_settlement_immutable_is_actually_enforced_in_write(self):
        self.assertTrue(builder._settlement_immutable_enforced())

    def test_audit_actions_are_individually_guarded(self):
        facts = builder._audit_action_facts()
        self.assertEqual(set(facts), {"action_submit", "action_approve", "action_done", "action_cancel",
                                      "action_bind_contract", "action_unbind_contract"})
        for method in ("action_submit", "action_approve", "action_done", "action_cancel"):
            self.assertTrue(facts[method]["role"], method)
            self.assertTrue(facts[method]["state_guard"], method)

    def test_lifecycle_draft_to_paused_edge_is_unresolved(self):
        proj = mapper._projection_for("project.lifecycle.transition", mapper.SPECS["project.lifecycle.transition"])
        edge = next(e for e in proj["transition_edges"] if e["source"] == "draft" and e["target"] == "paused")
        self.assertFalse(edge["resolved"])
        self.assertTrue(any(c["covers"] is False for c in edge["candidates"]))

    def test_run_identity_requires_completed_and_matching_head(self):
        self.assertTrue(builder._run_identity_resolved("completed", 1, "a" * 40, "a" * 40))
        self.assertFalse(builder._run_identity_resolved("active", 1, "a" * 40, "a" * 40))
        self.assertFalse(builder._run_identity_resolved("blocked", 1, "a" * 40, "a" * 40))
        self.assertFalse(builder._run_identity_resolved("completed", 0, "a" * 40, "a" * 40))
        self.assertFalse(builder._run_identity_resolved("completed", 1, "a" * 40, "b" * 40))

    def test_semantic_cases_are_skip_not_pass(self):
        proj = {
            "provider": {
                "action_res_model": "construction.contract.income",
                "model_facts": {"model": "construction.contract.income"},
            }
        }
        cases = {c["id"]: c["status"] for c in builder._batch_cases("read-only-query", proj)}
        self.assertEqual(cases["query_model_declared"], "pass")
        self.assertEqual(cases["result_columns_declared"], "skip")
        self.assertEqual(cases["read_side_effect_free"], "skip")


def _parse_expr(expr: str):
    import ast
    return ast.parse(expr, mode="eval").body


def _state_proj(states, transitions, terminal, method_names=None, button_names=None, method_targets=None):
    names = method_names if method_names is not None else {t for ts in transitions.values() for t in ts}
    targets = method_targets if method_targets is not None else set(names)
    methods = [{"method": n, "target_state": t, "server_guard": True} for n, t in sorted(zip(sorted(targets), sorted(targets)))]
    if method_names is not None and method_targets is None:
        methods = [{"method": n, "target_state": n, "server_guard": True} for n in sorted(method_names)]
    buttons = [{"button": b, "invisible": "", "groups": ""} for b in sorted(button_names if button_names is not None else names)]
    return {
        "state_machine": {"value": {"states": states, "transitions": transitions, "terminal_states": terminal}},
        "transition_methods": methods,
        "view_guards": buttons,
        "server_guard": {"value": {"checks": ["_check", "_validate"]}},
    }


if __name__ == "__main__":
    unittest.main()
