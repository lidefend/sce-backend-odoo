from __future__ import annotations

import sys
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import quick_input_scope as scope
import quick_suite_fingerprint as suites


class CommittedSuiteTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git("init", "-q")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "Test")
        self.manifest = json.loads((scope.ROOT / suites.MANIFEST).read_text())
        for name in ("Makefile", "make/check.mk", "scripts/probe.py",
                     "frontend/apps/web/scripts/check.js",
                     "docs/engineering_convergence/test_inventory.csv"):
            self.write(name, "initial")
        self.write(suites.MANIFEST, json.dumps(self.manifest))
        self.base = self.commit()

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.root), *args], text=True).strip()

    def write(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def commit(self):
        self.git("add", ".")
        self.git("commit", "-qm", "fixture")
        return self.git("rev-parse", "HEAD")

    def units(self, head):
        return scope.execution_units(self.root, head, ["verify.test.determinism", "unknown"])

    def test_docs_change_reuses_only_declared_suite(self):
        self.write("docs/notes.md", "documentation")
        plan = scope.plan_execution(self.units(self.commit()), self.units(self.base))
        self.assertEqual(["verify.test.determinism"], plan["reusable"])
        self.assertEqual(["unknown"], plan["affected"])

    def test_changed_added_and_removed_inputs_invalidate(self):
        source = self.units(self.base)
        for name, content in (("scripts/probe.py", "changed"),
                              ("scripts/new.py", "added"),
                              ("make/check.mk", "new recipe")):
            self.write(name, content)
            self.assertEqual([], scope.plan_execution(self.units(self.commit()), source)["reusable"])
        (self.root / "scripts/new.py").unlink()
        self.assertNotEqual(source["units"], self.units(self.commit())["units"])

    def test_dirty_worktree_cannot_change_historical_fingerprint(self):
        before = self.units(self.base)
        self.write("scripts/probe.py", "dirty")
        self.assertEqual(before, self.units(self.base))

    def test_unsafe_or_incomplete_declarations_fail_closed(self):
        for path in ("../outside", "/outside", "missing"):
            manifest = json.loads(json.dumps(self.manifest))
            manifest["suites"][0]["inputs"].append(path)
            self.write(suites.MANIFEST, json.dumps(manifest))
            with self.assertRaises(ValueError):
                self.units(self.commit())
        manifest["suites"][0]["inputs"] = ["scripts/probe.py"]
        self.write(suites.MANIFEST, json.dumps(manifest))
        with self.assertRaises(ValueError):
            self.units(self.commit())

    def test_unreviewed_target_cannot_be_declared_reusable(self):
        self.manifest["suites"][0]["id"] = "unknown"
        self.manifest["suites"][0]["command"] = ["make", "unknown"]
        self.write(suites.MANIFEST, json.dumps(self.manifest))
        with self.assertRaises(ValueError):
            self.units(self.commit())


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
