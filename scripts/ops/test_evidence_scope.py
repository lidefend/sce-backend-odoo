#!/usr/bin/env python3
"""Unit tests for the systemic evidence-reuse engine."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.ops.evidence_scope import (  # noqa: E402
    LEDGER_SCHEMA,
    ScopeError,
    UNITS_SCHEMA,
    covered_units,
    load_ledger,
    load_units,
    main as scope_main,
    plan_units,
    record_units,
    select_units,
    unit_ids,
    units_digest,
)


def units_document(check: str = "verify.example.check", *, fingerprints: dict | None = None, identity: dict | None = None) -> dict:
    values = fingerprints or {"a": "f1", "b": "f2", "c": "f3"}
    return {
        "schema": UNITS_SCHEMA,
        "check": check,
        "identity": identity or {"database": "sc_demo", "served_revision": "rev1"},
        "units": [{"id": key, "fingerprint": value} for key, value in values.items()],
    }


def results_document(document: dict, statuses: dict, *, executed: list | None = None, planned: list | None = None) -> dict:
    fingerprints = {unit["id"]: unit["fingerprint"] for unit in document["units"]}
    executed_units = executed if executed is not None else [
        {"id": identifier, "fingerprint": fingerprints[identifier]} for identifier in statuses
    ]
    return {
        "schema": "evidence_scope.results.v1",
        "executed_units": executed_units,
        "planned_affected": planned if planned is not None else sorted(statuses),
        "results": statuses,
    }


def empty_ledger(check: str = "verify.example.check") -> dict:
    return {"schema": LEDGER_SCHEMA, "check": check, "identity": {}, "units": {}, "runs": []}


class PlanTests(unittest.TestCase):
    def test_unrecorded_surface_is_fully_affected(self) -> None:
        document = units_document()
        plan = plan_units(document, empty_ledger())
        self.assertEqual(plan["affected"], ["a", "b", "c"])
        self.assertEqual(plan["never_recorded"], ["a", "b", "c"])
        self.assertEqual(plan["reusable"], [])
        self.assertTrue(plan["execution_required"])

    def test_recorded_surface_is_fully_reusable(self) -> None:
        document = units_document()
        ledger = record_units(document, empty_ledger(), results_document(document, {"a": "passed", "b": "passed", "c": "passed"}))
        plan = plan_units(document, ledger)
        self.assertEqual(plan["affected"], [])
        self.assertEqual(sorted(plan["reusable"]), ["a", "b", "c"])
        self.assertFalse(plan["execution_required"])

    def test_only_the_changed_unit_is_affected(self) -> None:
        before = units_document()
        ledger = record_units(before, empty_ledger(), results_document(before, {"a": "passed", "b": "passed", "c": "passed"}))
        after = units_document(fingerprints={"a": "f1", "b": "f2-changed", "c": "f3"})
        plan = plan_units(after, ledger)
        self.assertEqual(plan["affected"], ["b"])
        self.assertEqual(plan["stale"], ["b"])
        self.assertEqual(sorted(plan["reusable"]), ["a", "c"])

    def test_environment_change_invalidates_every_unit(self) -> None:
        before = units_document()
        ledger = record_units(before, empty_ledger(), results_document(before, {"a": "passed", "b": "passed", "c": "passed"}))
        after = units_document(identity={"database": "sc_demo", "served_revision": "rev2"})
        plan = plan_units(after, ledger)
        self.assertTrue(plan["identity_changed"])
        self.assertEqual(sorted(plan["affected"]), ["a", "b", "c"])

    def test_new_unit_is_affected_while_siblings_are_reused(self) -> None:
        before = units_document()
        ledger = record_units(before, empty_ledger(), results_document(before, {"a": "passed", "b": "passed", "c": "passed"}))
        after = units_document(fingerprints={"a": "f1", "b": "f2", "c": "f3", "d": "f4"})
        plan = plan_units(after, ledger)
        self.assertEqual(plan["affected"], ["d"])
        self.assertEqual(plan["never_recorded"], ["d"])


class RecordTests(unittest.TestCase):
    def test_executing_a_unit_with_a_foreign_fingerprint_is_refused(self) -> None:
        document = units_document()
        stale_results = results_document(document, {"a": "passed"}, executed=[{"id": "a", "fingerprint": "other"}])
        with self.assertRaises(ScopeError):
            record_units(document, empty_ledger(), stale_results)

    def test_executing_an_undeclared_unit_is_refused(self) -> None:
        document = units_document()
        with self.assertRaises(ScopeError):
            record_units(document, empty_ledger(), results_document(
                document, {"a": "passed"}, executed=[{"id": "a", "fingerprint": "f1"}, {"id": "zzz", "fingerprint": "f9"}]))

    def test_skipping_a_planned_unit_is_refused(self) -> None:
        document = units_document()
        with self.assertRaises(ScopeError):
            record_units(document, empty_ledger(), results_document(
                document, {"a": "passed"}, planned=["a", "b"]))

    def test_recording_an_unexecuted_unit_is_refused(self) -> None:
        document = units_document()
        with self.assertRaises(ScopeError):
            record_units(document, empty_ledger(), results_document(
                document, {"a": "passed", "b": "passed"}, executed=[{"id": "a", "fingerprint": "f1"}], planned=["a"]))

    def test_recording_binds_the_fingerprint_that_was_executed(self) -> None:
        document = units_document()
        ledger = record_units(document, empty_ledger(), results_document(document, {"a": "passed"}))
        self.assertEqual(ledger["units"]["a"]["fingerprint"], "f1")
        plan = plan_units(units_document(fingerprints={"a": "other"}), ledger)
        self.assertEqual(plan["affected"][0], "a")


class CoverageTests(unittest.TestCase):
    def test_coverage_report_distinguishes_states(self) -> None:
        before = units_document()
        ledger = record_units(before, empty_ledger(), results_document(before, {"a": "passed", "b": "passed"}))
        after = units_document(fingerprints={"a": "f1", "b": "f2-changed", "c": "f3"})
        report = covered_units(ledger, after)
        self.assertEqual(report["a"], "passed")
        self.assertEqual(report["b"], "stale")
        self.assertEqual(report["c"], "never_recorded")


class ReuseFirstTests(unittest.TestCase):
    def _covered_ledger(self) -> tuple[dict, dict]:
        document = units_document()
        ledger = record_units(
            document, empty_ledger(),
            results_document(document, {"a": "passed", "b": "passed", "c": "passed"}),
        )
        return document, ledger

    def test_only_the_affected_set_is_selected(self) -> None:
        document, ledger = self._covered_ledger()
        after = units_document(fingerprints={"a": "f1", "b": "f2-changed", "c": "f3"})
        selection = select_units(after, plan_units(after, ledger), [])
        self.assertEqual(selection["execute"], ["b"])
        self.assertEqual(selection["reused"], ["a", "c"])
        self.assertTrue(selection["reuse_first"])

    def test_re_executing_a_covered_unit_requires_a_justification(self) -> None:
        document, ledger = self._covered_ledger()
        with self.assertRaises(ScopeError):
            select_units(document, plan_units(document, ledger), ["a"])

    def test_re_execution_with_a_justification_is_recorded(self) -> None:
        document, ledger = self._covered_ledger()
        selection = select_units(document, plan_units(document, ledger), ["a"], reason="owner asked for a fresh read")
        self.assertEqual(selection["execute"], ["a"])
        self.assertEqual(selection["re_evidenced"], ["a"])
        self.assertEqual(selection["re_evidence_reason"], "owner asked for a fresh read")

    def test_requesting_an_undeclared_unit_is_refused(self) -> None:
        document, ledger = self._covered_ledger()
        with self.assertRaises(ScopeError):
            select_units(document, plan_units(document, ledger), ["zzz"], reason="anything")


class NoBlindRetryTests(unittest.TestCase):
    def _ledger_with_failure(self) -> tuple[dict, dict]:
        document = units_document()
        ledger = record_units(
            document, empty_ledger(),
            results_document(document, {"a": "passed", "b": "failed", "c": "passed"}),
        )
        return document, ledger

    def test_an_unchanged_failure_is_blocked_not_reusable(self) -> None:
        document, ledger = self._ledger_with_failure()
        plan = plan_units(document, ledger)
        self.assertEqual(plan["blocked"], ["b"])
        self.assertEqual(plan["reusable"], ["a", "c"])
        self.assertEqual(plan["affected"], [])
        self.assertFalse(plan["execution_required"])

    def test_a_blocked_unit_is_never_retried_without_a_reason(self) -> None:
        document, ledger = self._ledger_with_failure()
        with self.assertRaises(ScopeError):
            select_units(document, plan_units(document, ledger), ["b"])

    def test_a_blocked_unit_retries_once_the_recovery_is_stated(self) -> None:
        document, ledger = self._ledger_with_failure()
        selection = select_units(document, plan_units(document, ledger), ["b"], reason="fixture resent for entry b")
        self.assertEqual(selection["execute"], ["b"])

    def test_a_changed_input_moves_a_failed_unit_into_the_affected_set(self) -> None:
        document, ledger = self._ledger_with_failure()
        after = units_document(fingerprints={"a": "f1", "b": "f2-fixed", "c": "f3"})
        plan = plan_units(after, ledger)
        self.assertEqual(plan["affected"], ["b"])
        self.assertEqual(plan["blocked"], [])
        selection = select_units(after, plan, [])
        self.assertEqual(selection["execute"], ["b"])


class ValidationTests(unittest.TestCase):
    def _write(self, directory: Path, name: str, payload: dict) -> Path:
        target = directory / name
        target.write_text(json.dumps(payload), encoding="utf-8")
        return target

    def test_duplicate_unit_ids_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(Path(tmp), "units.json", {
                "schema": UNITS_SCHEMA, "check": "c",
                "units": [{"id": "a", "fingerprint": "f"}, {"id": "a", "fingerprint": "f"}],
            })
            with self.assertRaises(ScopeError):
                load_units(path)

    def test_ledger_for_another_check_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(Path(tmp), "ledger.json", {"schema": LEDGER_SCHEMA, "check": "other", "units": {}})
            with self.assertRaises(ScopeError):
                load_ledger(path, "verify.example.check")

    def test_check_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            units_path = self._write(directory, "units.json", units_document(check="verify.a"))
            with self.assertRaises(ScopeError):
                scope_main(["plan", "--check", "verify.b", "--units", str(units_path),
                            "--ledger", str(directory / "ledger.json"), "--json-out", str(directory / "plan.json")])

    def test_require_complete_returns_a_non_zero_plan_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            units_path = self._write(directory, "units.json", units_document())
            code = scope_main(["plan", "--units", str(units_path), "--ledger", str(directory / "ledger.json"),
                               "--json-out", str(directory / "plan.json"), "--require-complete"])
            self.assertEqual(code, 3)
            plan = json.loads((directory / "plan.json").read_text(encoding="utf-8"))
            self.assertEqual(sorted(plan["affected"]), ["a", "b", "c"])

    def test_plan_and_record_round_trip_through_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            document = units_document()
            units_path = self._write(directory, "units.json", document)
            results_path = self._write(directory, "results.json", results_document(document, {"a": "passed"}))
            ledger_path = directory / "ledger.json"
            self.assertEqual(scope_main(["record", "--units", str(units_path), "--results", str(results_path),
                                         "--ledger", str(ledger_path), "--json-out", str(directory / "r.json")]), 0)
            code = scope_main(["plan", "--units", str(units_path), "--ledger", str(ledger_path),
                               "--json-out", str(directory / "p.json"), "--require-complete"])
            self.assertEqual(code, 3)
            plan = json.loads((directory / "p.json").read_text(encoding="utf-8"))
            self.assertEqual(sorted(plan["affected"]), ["b", "c"])
            self.assertEqual(plan["reusable"], ["a"])


class RecordedSourceTests(unittest.TestCase):
    def test_an_explicit_source_overrides_the_results_provenance(self) -> None:
        document = units_document()
        results = results_document(document, {"a": "checked"})
        results["source"] = "artifacts/summary.json"
        ledger = record_units(document, empty_ledger(), results, source="artifacts/summary.json#record_only")
        self.assertEqual(ledger["units"]["a"]["source"], "artifacts/summary.json#record_only")
        self.assertEqual(ledger["runs"][-1]["source"], "artifacts/summary.json#record_only")

    def test_the_cli_accepts_an_explicit_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            document = units_document()
            units_path = directory / "units.json"
            units_path.write_text(json.dumps(document), encoding="utf-8")
            results_path = directory / "results.json"
            results_path.write_text(json.dumps(results_document(document, {"a": "checked"})), encoding="utf-8")
            ledger_path = directory / "ledger.json"
            code = scope_main(["record", "--units", str(units_path), "--results", str(results_path),
                               "--ledger", str(ledger_path), "--source", "artifacts/summary.json#record_only"])
            self.assertEqual(code, 0)
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            self.assertEqual(ledger["runs"][-1]["source"], "artifacts/summary.json#record_only")


class EngineNeutralityTests(unittest.TestCase):
    def test_engine_is_check_agnostic(self) -> None:
        for check in ("verify.frontend.business_entry.matrix.browser", "verify.other.declared.surface"):
            document = units_document(check=check)
            ledger = record_units(document, empty_ledger(check), results_document(document, {"a": "passed", "b": "passed", "c": "passed"}))
            self.assertEqual(plan_units(document, ledger)["affected"], [])
            self.assertEqual(sorted(unit_ids(document)), sorted(ledger["units"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
