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

    def test_bounded_scope_reuses_only_unchanged_declared_inputs(self):
        target = "verify.quick.evidence.unit"
        base = ["100644 blob aaa\tmake/ci.mk", "100644 blob aaa\tfrontend/a.ts"]
        changed = [base[0], "100644 blob bbb\tfrontend/a.ts"]
        self.assertEqual(scope._fingerprint_rows(base, target, "old"),
                         scope._fingerprint_rows(changed, target, "new"))
        self.assertNotEqual(scope._fingerprint_rows(base, "unknown", "old"),
                            scope._fingerprint_rows(changed, "unknown", "new"))

    def test_recipe_helpers_and_path_existence_invalidate_scope(self):
        target = "verify.quick.input_scope.unit"
        base = ["100644 blob aaa\tmake/ci.mk", "100644 blob aaa\tscripts/ops/helper.py"]
        for changed in (["100644 blob bbb\tmake/ci.mk", base[1]],
                        [base[0], "100644 blob bbb\tscripts/ops/helper.py"],
                        base + ["100644 blob aaa\tnew.txt"], base[:1]):
            with self.subTest(changed=changed):
                self.assertNotEqual(scope._fingerprint_rows(base, target, "old"),
                                    scope._fingerprint_rows(changed, target, "new"))

    def test_fingerprint_reads_requested_commit_instead_of_current_recipe(self):
        with mock.patch.object(scope, "git", side_effect=lambda root, *args:
                               "100644 blob " + args[-1] + "\tmake/ci.mk"):
            self.assertNotEqual(scope.target_fingerprint("old", "verify.quick.evidence.unit"),
                                scope.target_fingerprint("new", "verify.quick.evidence.unit"))

    def test_systemic_engine_rejects_environment_drift(self):
        source = {"check": "ci.local.quick", "identity": {"python": "old"},
                  "units": [{"id": "test", "fingerprint": "same"}]}
        current = dict(source, identity={"python": "new"})
        plan = scope.plan_execution(current, source)
        self.assertEqual(["test"], plan["affected"])
        self.assertEqual([], plan["reusable"])


if __name__ == "__main__":
    unittest.main()
