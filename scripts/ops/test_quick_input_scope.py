from __future__ import annotations

import sys
import os
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
                     ".github/workflows/check.yml", "frontend/apps/web/package.json",
                     "frontend/apps/web/scripts/check.js",
                     "addons/smart_core/handlers/example.py",
                     "addons/smart_construction_core/services/example.py",
                     "addons/smart_core/__manifest__.py", "Dockerfile", "Dockerfile.production-candidate",
                     "config/tenant/module_sets.v1.json", "config/product_addons_allowlist.txt",
                     "config/product_optional_addons_allowlist.txt",
                     "docs/audit/tenant_pro_03_data_responsibility_inventory.csv",
                     "schemas/tenant_delivery/schema.json", "customer_addons/sce_customer_sample/hooks.py",
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

    def test_workflow_and_package_inputs_invalidate_both_probes(self):
        targets = sorted(suites.REVIEWED_SUITES)
        source = scope.execution_units(self.root, self.base, targets)
        for path in (".github/workflows/check.yml", "frontend/apps/web/package.json"):
            with self.subTest(path=path):
                self.write(path, "changed anchor authority")
                current = scope.execution_units(self.root, self.commit(), targets)
                plan = scope.plan_execution(current, source)
                self.assertEqual([], plan["reusable"])
                self.assertEqual(targets, plan["affected"])
                self.write(path, "initial")
                self.commit()

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

    def test_scene_test_edit_reuses_offline_capabilities_but_module_edit_does_not(self):
        targets = sorted(suites.OFFLINE_CAPABILITY_SUITES)
        source = scope.execution_units(self.root, self.base, targets)
        self.write('addons/smart_construction_scene/tests/test_scene.py', 'changed scene test')
        current = scope.execution_units(self.root, self.commit(), targets)
        self.assertEqual(targets, scope.plan_execution(current, source)['reusable'])
        self.write('addons/smart_core/handlers/example.py', 'changed platform helper')
        current = scope.execution_units(self.root, self.commit(), targets)
        self.assertEqual(targets, scope.plan_execution(current, source)['affected'])

    def test_capability_scope_cannot_drop_platform_module(self):
        row = next(s for s in self.manifest['suites'] if s['id'] in suites.OFFLINE_CAPABILITY_SUITES)
        row['inputs'].remove('addons/smart_core/')
        self.write(suites.MANIFEST, json.dumps(self.manifest))
        with self.assertRaisesRegex(ValueError, 'missing module inputs'):
            self.units(self.commit())

    def test_module_inventory_tracks_manifests_not_unrelated_tests(self):
        targets = ['verify.tenant.module_set_matrix', 'verify.tenant.product_fresh_install']
        source = scope.execution_units(self.root, self.base, targets)
        self.write('addons/smart_construction_scene/tests/test_scene.py', 'unrelated')
        current = scope.execution_units(self.root, self.commit(), targets)
        self.assertEqual(targets, scope.plan_execution(current, source)['reusable'])
        self.write('addons/new_module/__manifest__.py', '{}')
        added = self.commit()
        current = scope.execution_units(self.root, added, targets)
        self.assertEqual(targets, scope.plan_execution(current, source)['affected'])
        (self.root / 'addons/new_module/__manifest__.py').unlink()
        removed = scope.execution_units(self.root, self.commit(), targets)
        self.assertEqual(targets, scope.plan_execution(removed, current)['affected'])

    def test_tenant_required_inputs_and_glob_bounds_cannot_be_weakened(self):
        original = json.loads(json.dumps(self.manifest))
        for replacement in ('addons/**', '../addons/*/__manifest__.py', 'addons/*/../__manifest__.py'):
            self.manifest = json.loads(json.dumps(original))
            row = next(s for s in self.manifest['suites'] if s['id'] == 'verify.tenant.module_set_matrix')
            row['inputs'].remove(suites.MODULE_MANIFESTS)
            row['inputs'].append(replacement)
            self.write(suites.MANIFEST, json.dumps(self.manifest))
            with self.assertRaises(ValueError):
                self.units(self.commit())

    def test_prerequisite_reader_inputs_invalidate_the_parent_target(self):
        targets = ['verify.tenant.product_fresh_install', 'verify.tenant.payload_boundary']
        source = scope.execution_units(self.root, self.base, targets)
        self.write('addons/smart_construction_core/services/example.py', 'changed inherited reader input')
        current = scope.execution_units(self.root, self.commit(), targets)
        self.assertEqual(targets, scope.plan_execution(current, source)['affected'])
        source = current
        self.write('customer_addons/sce_customer_sample/hooks.py', 'changed protocol dependency')
        current = scope.execution_units(self.root, self.commit(), targets)
        self.assertEqual(['verify.tenant.payload_boundary'], scope.plan_execution(current, source)['affected'])

    def test_security_and_current_state_checks_have_no_reuse_declaration(self):
        targets = sorted(scope.ALWAYS_RUN)
        source = scope.execution_units(self.root, self.base, targets)
        self.write('docs/note.md', 'bookkeeping')
        current = scope.execution_units(self.root, self.commit(), targets)
        self.assertEqual(targets, scope.plan_execution(current, source)['affected'])
        self.assertEqual(scope.ALWAYS_RUN, scope.scope_classes(self.root, self.base, targets))


class QuickInputScopeTest(unittest.TestCase):
    def test_changed_shell_bytes_invalidate_identity(self):
        with tempfile.TemporaryDirectory() as folder:
            binary = Path(folder) / 'tool'
            binary.write_bytes(b'old')
            with mock.patch.object(scope.shutil, 'which', return_value=str(binary)):
                before = scope.execution_identity()
                binary.write_bytes(b'new')
                self.assertNotEqual(before, scope.execution_identity())

    def test_execution_budget_is_not_a_test_input_but_unknown_environment_is(self):
        before = scope.execution_identity()
        with mock.patch.dict(os.environ, {'QUICK_MAX_TARGETS': '3'}):
            self.assertEqual(before, scope.execution_identity())
            self.assertNotIn('QUICK_MAX_TARGETS', scope.environment_hashes())
        with mock.patch.dict(os.environ, {'ACTUAL_TEST_INPUT': 'changed'}):
            self.assertNotEqual(before, scope.execution_identity())

    def test_call_correlation_does_not_invalidate_execution(self):
        before = scope.execution_identity()
        with mock.patch.dict(os.environ, {"CODEX_TOOL_CALL_ID": "another-call"}):
            self.assertEqual(before, scope.execution_identity())
            self.assertNotIn("CODEX_TOOL_CALL_ID", scope.environment_hashes())

    def test_default_candidate_revision_normalizes_but_explicit_revision_invalidates(self):
        with mock.patch.dict(os.environ, {"SC_ACCEPTANCE_SOURCE_SHA": "a" * 40}):
            before = scope.execution_identity(candidate_head="a" * 40)
        with mock.patch.dict(os.environ, {"SC_ACCEPTANCE_SOURCE_SHA": "b" * 40}):
            self.assertEqual(before, scope.execution_identity(candidate_head="b" * 40))
            self.assertNotEqual(before, scope.execution_identity(candidate_head="a" * 40))
        with mock.patch.dict(os.environ, {"SC_ACCEPTANCE_SOURCE_SHA": "candidate-head"}):
            self.assertNotEqual(before, scope.execution_identity(candidate_head="a" * 40))
        with mock.patch.dict(os.environ, {}, clear=True):
            absent = scope.execution_identity(candidate_head="a" * 40)
            with mock.patch.dict(os.environ, {"SC_ACCEPTANCE_SOURCE_SHA": "a" * 40}):
                self.assertNotEqual(absent, scope.execution_identity(candidate_head="a" * 40))

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
