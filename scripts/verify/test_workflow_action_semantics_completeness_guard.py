#!/usr/bin/env python3
"""Pin the approval-verdict check to a real control-flow use.

`can_review` must decide whether an approval action is offered.  Counting a
bare mention would also accept a verdict that is only logged, which would leave
the Web as the only decider -- the failure this guard exists to catch.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from workflow_action_semantics_completeness_guard import (
    ROOT,
    financial_workspace_action_declarations,
    load_action_semantics_authority,
    references_marker,
    validate_financial_workspace_actions,
)


DECIDES = '''
def _available_actions(self, record):
    keys = ["approve"]
    if not bool(getattr(record, "can_review", False)):
        keys.remove("approve")
    return keys
'''

MENTIONS_ONLY = '''
def _available_actions(self, record):
    _marker_only = "can_review"
    keys = ["approve"]
    if not bool(getattr(record, "_other", False)):
        keys.remove("approve")
    return keys
'''

CONSTANT_TEST = '''
def _available_actions(self, record):
    if "can_review":
        return []
    return ["approve"]
'''

MISSING_FUNCTION = '''
def _something_else(self, record):
    if "can_review":
        return []
    return []
'''


class ApprovalVerdictUseTest(unittest.TestCase):
    def _check(self, source: str) -> bool:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "service.py"
            path.write_text(source, encoding="utf-8")
            return references_marker(path, "_available_actions", "can_review")

    def test_a_verdict_used_in_an_if_test_counts(self) -> None:
        self.assertTrue(self._check(DECIDES))

    def test_a_log_only_mention_does_not_count(self) -> None:
        self.assertFalse(self._check(MENTIONS_ONLY))

    def test_a_plain_constant_test_does_not_count(self) -> None:
        self.assertFalse(self._check(CONSTANT_TEST))

    def test_a_marker_outside_the_named_function_does_not_count(self) -> None:
        self.assertFalse(self._check(MISSING_FUNCTION))


DECLARED = '''
def build(actions):
    actions.append({
        "key": "payment_execution",
        "method": "action_create_payment_execution",
        "action_semantics": {"kind": "business", "purpose": "start_execution", "executor": "contract.action", "origin": "test"},
    })
    return actions
'''

UNDECLARED = '''
def build(actions):
    actions.append({
        "key": "payment_execution",
        "method": "action_create_payment_execution",
    })
    return actions
'''

OUTSIDE_VOCABULARY = '''
def build(actions):
    actions.append({
        "key": "payment_execution",
        "method": "action_create_payment_execution",
        "action_semantics": {"kind": "business", "purpose": "teleport", "executor": "contract.action", "origin": "test"},
    })
    return actions
'''

UNPUBLISHED_PAIR = '''
def build(actions):
    actions.append({
        "key": "payment_execution",
        "method": "action_create_payment_execution",
        "action_semantics": {"kind": "business", "purpose": "return", "executor": "contract.action", "origin": "test"},
    })
    return actions
'''

PROPAGATED = '''
def build(actions, row):
    actions.append({
        "key": f"payment_{row[\'action_key\']}",
        "method": row["method"],
        **({"action_semantics": dict(row["action_semantics"])} if row.get("action_semantics") else {}),
    })
    return actions
'''

NAVIGATION_ONLY = '''
def build(actions):
    actions.append({
        "key": "view_payment_execution",
        "method": "action_view_payment_execution",
    })
    return actions
'''

NAVIGATION_EXCUSING_A_TRANSITION = '''
def build(actions):
    actions.append({
        "key": "view_payment_execution",
        "method": "action_view_payment_execution",
        "required_params": ["reason"],
    })
    return actions
'''

NAVIGATION_EXCUSING_A_DESTRUCTIVE_ACTION = '''
def build(actions):
    actions.append({
        "key": "view_payment_execution",
        "method": "action_view_payment_execution",
        "action_safety": {"classification": "danger", "requires_confirm": True},
    })
    return actions
'''


class FinancialWorkspaceActionClassificationTest(unittest.TestCase):
    def _validate(self, source: str, *, navigation=None):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "financial_workspace_contract.py"
            path.write_text(source, encoding="utf-8")
            declarations, errors = financial_workspace_action_declarations(path)
            self.assertEqual(errors, [])
            return validate_financial_workspace_actions(
                vocabulary={"start_execution", "return", "save_draft"},
                authority=load_action_semantics_authority(ROOT),
                declarations=declarations,
                registered_navigation=navigation or {},
            )

    def test_a_declared_business_purpose_passes(self) -> None:
        self.assertEqual(self._validate(DECLARED), [])

    def test_a_method_binding_action_without_a_purpose_fails(self) -> None:
        self.assertTrue(any("without a declared action purpose" in item for item in self._validate(UNDECLARED)))

    def test_a_purpose_outside_the_published_vocabulary_fails(self) -> None:
        self.assertTrue(any("outside the published vocabulary" in item for item in self._validate(OUTSIDE_VOCABULARY)))

    def test_an_unpublished_kind_purpose_executor_pair_fails(self) -> None:
        self.assertTrue(
            any("not a published (kind, purpose, executor) combination" in item for item in self._validate(UNPUBLISHED_PAIR))
        )

    def test_semantics_propagated_from_the_registry_row_are_not_rejudged(self) -> None:
        self.assertEqual(self._validate(PROPAGATED), [])

    def test_registered_navigation_covers_an_unclassified_method_action(self) -> None:
        self.assertEqual(
            self._validate(
                NAVIGATION_ONLY, navigation={"view_payment_execution": "reads a related record"}
            ),
            [],
        )

    def test_a_registered_navigation_key_that_disappeared_fails(self) -> None:
        failures = self._validate(DECLARED, navigation={"view_payment_execution": "reads a related record"})
        self.assertTrue(any("no longer declared" in item for item in failures))

    def test_a_registered_navigation_key_without_a_reason_fails(self) -> None:
        failures = self._validate(NAVIGATION_ONLY, navigation={"view_payment_execution": "  "})
        self.assertTrue(any("without a reason" in item for item in failures))

    def test_a_navigation_exception_may_not_excuse_a_transition_that_takes_input(self) -> None:
        failures = self._validate(
            NAVIGATION_EXCUSING_A_TRANSITION, navigation={"view_payment_execution": "reads a related record"}
        )
        self.assertTrue(any("excuses an action that collects business input" in item for item in failures))

    def test_a_navigation_exception_may_not_excuse_a_destructive_action(self) -> None:
        failures = self._validate(
            NAVIGATION_EXCUSING_A_DESTRUCTIVE_ACTION,
            navigation={"view_payment_execution": "reads a related record"},
        )
        self.assertTrue(any("excuses a destructive action" in item for item in failures))

    def test_no_declaration_read_is_a_failure(self) -> None:
        failures = self._validate("def build(actions):\n    return actions\n")
        self.assertTrue(any("vacuous" in item for item in failures))


if __name__ == "__main__":
    unittest.main()
