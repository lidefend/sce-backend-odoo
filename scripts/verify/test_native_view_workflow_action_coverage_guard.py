#!/usr/bin/env python3
"""Pin the native-button coverage guard to a two-way, fail-closed registry.

An uncovered native object button must be registered; a registration that has
outlived its gap (method declared, button gone) or that carries no meaningful
class/reason must not pass.  Each case below is a regression the guard exists
to catch, so the registry cannot quietly rot into a rubber stamp.
"""
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from native_view_workflow_action_coverage_guard import REGISTRY, validate


def _baseline() -> dict:
    return json.loads(Path(REGISTRY).read_text(encoding="utf-8"))


class NativeViewActionCoverageGuardTest(unittest.TestCase):
    def test_the_shipped_registry_is_consistent(self) -> None:
        self.assertEqual(validate(_baseline()), [])

    def test_an_unregistered_native_transition_fails(self) -> None:
        payload = _baseline()
        payload["entries"] = [e for e in payload["entries"] if e["method"] != "action_signed"]
        self.assertTrue(any("action_signed" in error for error in validate(payload)))

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
            if entry["method"] == "action_signed":
                entry.pop("reason", None)
        self.assertTrue(any("without a reason" in error for error in validate(payload)))

    def test_an_unknown_class_fails(self) -> None:
        payload = _baseline()
        for entry in payload["entries"]:
            if entry["method"] == "action_signed":
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


if __name__ == "__main__":
    unittest.main()
