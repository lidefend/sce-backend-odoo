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

from workflow_action_semantics_completeness_guard import references_marker


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


if __name__ == "__main__":
    unittest.main()
