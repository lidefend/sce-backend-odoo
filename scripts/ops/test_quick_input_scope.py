from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import quick_input_scope as scope


class QuickInputScopeTest(unittest.TestCase):
    def test_quick_targets_contains_the_entry_and_is_bounded(self):
        targets = scope.quick_targets()
        self.assertIn(scope.QUICK_ENTRY, targets)
        self.assertLessEqual(len(targets), 200)
        self.assertEqual(targets, sorted(targets))

    def test_target_inputs_maps_the_workflow_contract_gate_to_its_scripts(self):
        inputs = scope.target_inputs()
        gate = "verify.ci.workflow.contract"
        self.assertIn(gate, inputs)
        joined = " ".join(inputs[gate])
        self.assertIn("scripts/ci/test_backend_impact_plan.py", joined)
        self.assertIn("scripts/ci/test_backend_test_receipt.py", joined)

    def test_affected_targets_reuses_unchanged_and_runs_changed_inputs(self):
        inputs = {"a": ["scripts/one.py"], "b": ["scripts/two.py"], "c": []}
        base_blob = "100644 blob aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\tscripts/one.py"
        head_blob = "100644 blob bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb\tscripts/one.py"
        def fake_git(root, *args):
            commit, path = args[1], args[-1]
            if path.endswith("one.py"):
                return base_blob if commit == "base" else head_blob
            return base_blob
        with mock.patch.object(scope, "target_inputs", return_value=inputs), \
             mock.patch.object(scope, "quick_targets", return_value=["a", "b", "c"]), \
             mock.patch.object(scope, "git", side_effect=fake_git):
            decisions = scope.affected_targets("base", "head")
        self.assertEqual("RUN", decisions["a"])   # blob changed
        self.assertEqual("REUSE", decisions["b"])  # unchanged
        self.assertEqual("RUN", decisions["c"])   # no declared inputs -> fail closed


if __name__ == "__main__":
    unittest.main()
