#!/usr/bin/env python3
from __future__ import annotations

import ast
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
GUARD_PATH = ROOT / "scripts/verify/backend_contract_lifecycle_runtime_schema_guard.py"
PROBE_PATH = ROOT / "scripts/verify/backend_contract_lifecycle_runtime_probe.py"
REVISION = "b" * 40

SPEC = importlib.util.spec_from_file_location("backend_contract_lifecycle_runtime_schema_guard", GUARD_PATH)
GUARD = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(GUARD)


def producer_declared_checks() -> tuple[str, ...]:
    """Read the probe's declaration without importing the Odoo-shell module."""
    tree = ast.parse(PROBE_PATH.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "DECLARED_CHECKS" for target in node.targets
        ):
            return tuple(ast.literal_eval(node.value))
    raise AssertionError("DECLARED_CHECKS is not declared in the runtime probe")


def producer_assigned_checks() -> set[str]:
    """Read the probe's evaluated assertion keys straight from its source.

    The probe assigns `checks["<name>"] = ...` for every assertion it evaluates
    (and would use `checks.update({...})`). Reading those constant keys proves
    offline that the code evaluates exactly the declared set, without a runtime.
    """
    tree = ast.parse(PROBE_PATH.read_text(encoding="utf-8"))
    keys: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if (
                isinstance(target, ast.Subscript)
                and isinstance(target.value, ast.Name)
                and target.value.id == "checks"
                and isinstance(target.slice, ast.Constant)
                and isinstance(target.slice.value, str)
            ):
                keys.add(target.slice.value)
        if (
            isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Attribute)
            and isinstance(node.value.func.value, ast.Name)
            and node.value.func.value.id == "checks"
            and node.value.func.attr == "update"
            and node.value.args
            and isinstance(node.value.args[0], ast.Dict)
        ):
            for key in node.value.args[0].keys:
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    keys.add(key.value)
    return keys


def artifact(**overrides) -> dict:
    payload = {
        "probe": "backend_contract_lifecycle_runtime_probe",
        "schemaVersion": "1.0.0",
        "database": "sc_contract_lifecycle",
        "moduleVersion": "17.0.1.1.9",
        "sourceRevision": REVISION,
        "declaredChecks": sorted(GUARD.EXPECTED_CHECKS),
        "checkCount": len(GUARD.EXPECTED_CHECKS),
        "passedCheckCount": len(GUARD.EXPECTED_CHECKS),
        "checks": {name: True for name in sorted(GUARD.EXPECTED_CHECKS)},
        "versionDigestMismatchSample": [],
        "errorCount": 0,
        "errors": [],
    }
    payload.update(overrides)
    return payload


class DeclarationLockTest(unittest.TestCase):
    def test_guard_and_producer_share_one_declared_assertion_set(self):
        self.assertEqual(producer_declared_checks(), GUARD.EXPECTED_CHECKS)
        self.assertEqual(len(GUARD.EXPECTED_CHECKS), 14)
        self.assertEqual(len(set(GUARD.EXPECTED_CHECKS)), 14)


class ProducerCodeLockTest(unittest.TestCase):
    def test_probe_assigns_exactly_the_declared_assertions(self):
        assigned = producer_assigned_checks()
        self.assertEqual(assigned, set(GUARD.EXPECTED_CHECKS))
        self.assertEqual(len(assigned), 14)


class RuntimeArtifactGuardTest(unittest.TestCase):
    def run_guard(self, payload=None, *, expected_revision="", raw=None):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "runtime_probe.json"
            if raw is not None:
                path.write_text(raw, encoding="utf-8")
            elif payload is not None:
                path.write_text(json.dumps(payload), encoding="utf-8")
            command = [sys.executable, str(GUARD_PATH), "--artifact", str(path)]
            if expected_revision:
                command += ["--expected-revision", expected_revision]
            return subprocess.run(command, capture_output=True, text=True, cwd=str(ROOT))

    def test_guard_baseline_accepts_a_bound_artifact(self):
        completed = self.run_guard(artifact())
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_guard_rejects_a_failed_assertion_behind_a_summary_claim(self):
        baseline = self.run_guard(artifact())
        self.assertEqual(baseline.returncode, 0, baseline.stdout + baseline.stderr)

        tampered = artifact()
        tampered["checks"]["rollback_is_append_only"] = False
        tampered["passedCheckCount"] = len(GUARD.EXPECTED_CHECKS) - 1
        mutated = self.run_guard(tampered)
        self.assertNotEqual(mutated.returncode, 0)
        self.assertIn("checks.rollback_is_append_only must be true", mutated.stdout)

    def test_guard_rejects_a_dropped_assertion(self):
        dropped = artifact()
        dropped["checks"].pop("version_deletion_rejected")
        dropped["checkCount"] = len(GUARD.EXPECTED_CHECKS) - 1
        dropped["passedCheckCount"] = len(GUARD.EXPECTED_CHECKS) - 1
        completed = self.run_guard(dropped)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("version_deletion_rejected", completed.stdout)

    def test_guard_rejects_an_undeclared_extra_assertion(self):
        completed = self.run_guard(artifact(checks={**artifact()["checks"], "made_up_check": True}))
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("made_up_check", completed.stdout)

    def test_guard_rejects_a_truncated_declaration(self):
        truncated = artifact(declaredChecks=sorted(GUARD.EXPECTED_CHECKS)[:-1])
        completed = self.run_guard(truncated)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("declaredChecks must equal the declared assertion set", completed.stdout)

    def test_guard_rejects_a_digest_mismatch_sample(self):
        completed = self.run_guard(artifact(versionDigestMismatchSample=[{"id": 1, "versionNo": 2}]))
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("versionDigestMismatchSample must be empty", completed.stdout)

    def test_guard_rejects_nonzero_producer_counters(self):
        completed = self.run_guard(artifact(errorCount=1, errors=["version_mutation_rejected"]))
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("errorCount must be 0", completed.stdout)
        self.assertIn("errors must be empty", completed.stdout)

    def test_guard_rejects_a_foreign_database_or_module_version(self):
        for overrides, marker in (
            ({"database": "sc_dev_demo"}, "database must be sc_contract_lifecycle"),
            ({"moduleVersion": "17.0.1.1.8"}, "moduleVersion must be 17.0.1.1.9"),
            ({"probe": "other_probe"}, "probe must be backend_contract_lifecycle_runtime_probe"),
            ({"schemaVersion": "0.9.0"}, "schemaVersion must be 1.0.0"),
        ):
            with self.subTest(**overrides):
                completed = self.run_guard(artifact(**overrides))
                self.assertNotEqual(completed.returncode, 0)
                self.assertIn(marker, completed.stdout)

    def test_guard_rejects_a_partial_or_mismatched_revision(self):
        partial = self.run_guard(artifact(sourceRevision="b" * 12))
        self.assertNotEqual(partial.returncode, 0)
        self.assertIn("sourceRevision must be a full commit SHA", partial.stdout)

        mismatch = self.run_guard(artifact(), expected_revision="c" * 40)
        self.assertNotEqual(mismatch.returncode, 0)
        self.assertIn("sourceRevision must equal the expected revision", mismatch.stdout)

        bound = self.run_guard(artifact(), expected_revision=REVISION)
        self.assertEqual(bound.returncode, 0, bound.stdout + bound.stderr)

    def test_guard_rejects_a_missing_artifact(self):
        completed = self.run_guard()
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("missing or invalid json", completed.stdout)

    def test_guard_rejects_a_non_object_artifact(self):
        completed = self.run_guard(raw="[]")
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("missing or invalid json", completed.stdout)


if __name__ == "__main__":
    unittest.main()
