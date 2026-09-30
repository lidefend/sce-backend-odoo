#!/usr/bin/env python3
"""Pin the native-button coverage guard to a two-way, fail-closed registry.

An uncovered native object button must be registered; a registration that has
outlived its gap (method declared, button gone) or that carries no meaningful
class/reason must not pass.  Each case below is a regression the guard exists
to catch, so the registry cannot quietly rot into a rubber stamp.
"""
from __future__ import annotations

import ast
import copy
import json
import unittest
from types import SimpleNamespace
from pathlib import Path

from native_view_workflow_action_coverage_guard import REGISTRY, adopted_models, validate
from workflow_contract_profile_loader import DEFAULT_SERVICE, load_profiles


def _baseline() -> dict:
    return json.loads(Path(REGISTRY).read_text(encoding="utf-8"))


class NativeViewActionCoverageGuardTest(unittest.TestCase):
    def _general_contract_actions(self, state, *, approval_phase="none", can_review=False):
        # Execute the shipped projection method, not a duplicate of its algorithm.
        tree = ast.parse(DEFAULT_SERVICE.read_text(encoding="utf-8"))
        method = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_available_actions")
        method.decorator_list = []
        assignment = next(n for n in ast.walk(tree) if isinstance(n, ast.Assign) and any(getattr(t, "id", None) == "ACTIONS" for t in n.targets))
        namespace = {}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[assignment, method], type_ignores=[])), str(DEFAULT_SERVICE), "exec"), namespace)
        record = SimpleNamespace(_name="sc.general.contract", id=23, can_review=can_review)
        service = SimpleNamespace(ACTIONS=namespace["ACTIONS"])
        return namespace["_available_actions"](service, record, load_profiles()[record._name], state, "", approval_phase, [])

    def test_general_contract_signing_binds_the_existing_business_method(self):
        for state in ("draft", "confirmed"):
            with self.subTest(state=state):
                action = next(a for a in self._general_contract_actions(state) if a["key"] == "complete")
                self.assertEqual(action["method"], "action_signed")
                self.assertEqual(action["label"], "已签署")
                self.assertEqual(action["target"], {"model": "sc.general.contract", "id": 23, "method": "action_signed"})
                self.assertEqual(action["action_semantics"]["executor"], "contract.action")
                self.assertEqual(action["action_semantics"]["purpose"], "complete")

    def test_general_contract_signing_is_not_declared_in_terminal_or_unknown_states(self):
        for state in ("signed", "cancel", "legacy_confirmed", "unknown"):
            with self.subTest(state=state):
                self.assertNotIn("action_signed", [a["method"] for a in self._general_contract_actions(state)])

    def test_signing_does_not_replace_approval_or_grant_reviewer_actions(self):
        actions = self._general_contract_actions("draft", approval_phase="pending", can_review=False)
        self.assertIn("action_confirm", [a["method"] for a in actions])
        self.assertIn("action_signed", [a["method"] for a in actions])
        self.assertNotIn("validate_tier", [a["method"] for a in actions])
        self.assertNotIn("reject_tier", [a["method"] for a in actions])
        reviewer = self._general_contract_actions("draft", approval_phase="pending", can_review=True)
        self.assertIn("validate_tier", [a["method"] for a in reviewer])

    def _sign_record(self, state, *, approval_completes=True, anchor_valid=True):
        path = DEFAULT_SERVICE.parents[1] / "core/general_contract.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        method = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "action_signed")
        namespace = {"UserError": ValueError, "_": lambda text: text}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])), str(path), "exec"), namespace)
        record = SimpleNamespace(state=state, approval_calls=0)
        def confirm():
            record.approval_calls += 1
            if approval_completes:
                record.state = "confirmed"
        def check_anchor():
            if not anchor_valid:
                raise ValueError("missing business anchor")
        record.action_confirm = confirm
        record._check_business_anchor = check_anchor
        return record, lambda: namespace["action_signed"]([record])

    def test_signing_executes_the_existing_confirmation_before_draft_transition(self):
        record, execute = self._sign_record("draft")
        execute()
        self.assertEqual(record.approval_calls, 1)
        self.assertEqual(record.state, "signed")

    def test_pending_approval_does_not_become_signed(self):
        record, execute = self._sign_record("draft", approval_completes=False)
        execute()
        self.assertEqual(record.approval_calls, 1)
        self.assertEqual(record.state, "draft")

    def test_signing_preserves_business_anchor_validation(self):
        record, execute = self._sign_record("confirmed", anchor_valid=False)
        with self.assertRaises(ValueError):
            execute()
        self.assertEqual(record.state, "confirmed")

    def test_signing_rejects_states_outside_the_declared_sources(self):
        for state in ("signed", "cancel", "legacy_confirmed"):
            record, execute = self._sign_record(state)
            with self.assertRaises(ValueError):
                execute()
            self.assertEqual(record.state, state)

    def test_the_shipped_registry_is_consistent(self) -> None:
        self.assertEqual(validate(_baseline()), [])

    def test_an_unregistered_native_transition_fails(self) -> None:
        payload = _baseline()
        payload["entries"] = [e for e in payload["entries"] if e["method"] != "action_reverse_payment"]
        self.assertTrue(any("action_reverse_payment" in error for error in validate(payload)))

    def test_an_entry_with_no_native_button_is_stale(self) -> None:
        payload = _baseline()
        payload["entries"].append(
            {"model": "sc.nothing.here", "method": "action_ghost", "class": "navigation", "reason": "probe"}
        )
        errors = validate(payload)
        self.assertTrue(any("action_ghost" in error for error in errors))

    def test_an_entry_whose_method_is_now_declared_is_stale(self) -> None:
        payload = _baseline()
        payload["entries"].append(
            {"model": "payment.request", "method": "action_submit", "class": "navigation", "reason": "probe"}
        )
        errors = validate(payload)
        self.assertTrue(any("now declares it" in error for error in errors))

    def test_an_entry_without_a_reason_fails(self) -> None:
        payload = _baseline()
        for entry in payload["entries"]:
            if entry["method"] == "action_reverse_payment":
                entry.pop("reason", None)
        self.assertTrue(any("without a reason" in error for error in validate(payload)))

    def test_an_unknown_class_fails(self) -> None:
        payload = _baseline()
        for entry in payload["entries"]:
            if entry["method"] == "action_reverse_payment":
                entry["class"] = "not_a_class"
        self.assertTrue(any("expected one of" in error for error in validate(payload)))

    def test_every_shipped_entry_declares_a_meaningful_class(self) -> None:
        payload = _baseline()
        allowed = {"state_transition_undeclared", "navigation", "document_helper"}
        covered = {entry["class"] for entry in payload["entries"]}
        self.assertTrue(covered <= allowed)
        self.assertIn("state_transition_undeclared", covered)

    def test_validate_does_not_mutate_the_registry_payload(self) -> None:
        payload = _baseline()
        before = copy.deepcopy(payload)
        validate(payload)
        self.assertEqual(payload, before)

    def test_helper_built_profiles_are_scanned_too(self) -> None:
        # Regression for the coverage hole that hid seven buttons: a regex over
        # the source text only sees inline literals, so every model adopted
        # through a **_helper(...) call was silently left unscanned.
        models = adopted_models()
        for helper_built in (
            "sc.plan",
            "sc.equipment.plan",
            "sc.quality.issue",
            "sc.material.settlement",
        ):
            self.assertIn(helper_built, models, "helper-built profile is missing from the scan")

    def test_a_helper_built_model_transition_must_be_registered(self) -> None:
        payload = _baseline()
        payload["entries"] = [e for e in payload["entries"] if e["method"] != "action_start"]
        errors = validate(payload)
        self.assertTrue(any("action_start" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
