#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts/verify/agent_ledger_consistency_guard.py"
SPEC = importlib.util.spec_from_file_location("agent_ledger_consistency_guard", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

CONTEXT_TEXT = """schema_version: 1
run_statuses:
  - planned
  - active
  - blocked
  - verification_pending
  - completed
  - superseded
"""

AUTHORITY = "docs/ops/iterations/product_delivery_mainline_ledger_closeout_20261008.md"

# A synthetic ledger shaped like the repository: the recorded residuals are
# present, both allowlisted terminal runs are present, and the only index entry
# points at a live run. This is the clean baseline that negative cases mutate.
BASE_GOALS = {
    "SAMPLE-LIVE-RUN": "active",
    "FORM-PAGE-STRUCTURE-PROFESSIONALIZATION": "verified",
    "PAYMENT-REQUEST-GOLDEN-FLOORPLAN": "complete",
    "BACKEND-CONTRACT-SLO-TELEMETRY": "active",
    "P4-INCREMENTAL-RESUME": "active",
    "ENV-ACCEPTANCE-REBUILD-LANE-PREREQUISITE": "completed",
}
BASE_RUNS = {
    "SAMPLE-LIVE-RUN": {"status": "active", "branch": "fix/sample-live-run"},
    "BACKEND-CONTRACT-SLO-TELEMETRY": {"status": "completed", "branch": "fix/contract-slo-telemetry"},
    "P4-INCREMENTAL-RESUME": {"status": "completed", "branch": "fix/agent-resume-mainline"},
    "ENV-ACCEPTANCE-REBUILD-LANE-PREREQUISITE": {
        "status": "completed",
        "branch": "audit/environment-rebuild-lane-prerequisite-20261009",
    },
}
BASE_INDEX = {
    "fix/sample-live-run": ".agent/runs/SAMPLE-LIVE-RUN/run.json",
}


def write_goal(base: Path, goal_id: str, status: str) -> None:
    (base / ".agent/goals").mkdir(parents=True, exist_ok=True)
    (base / f".agent/goals/{goal_id}.yaml").write_text(
        f"goal:\n  id: {goal_id}\n  status: {status}\n", encoding="utf-8"
    )


def write_run(base: Path, run_id: str, status: str, branch: str, goal_id: str | None = None) -> None:
    directory = base / f".agent/runs/{run_id}"
    directory.mkdir(parents=True, exist_ok=True)
    record = f"docs/ops/iterations/{run_id}.md"
    (base / record).parent.mkdir(parents=True, exist_ok=True)
    (base / record).write_text("# record\n", encoding="utf-8")
    (directory / "run.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "id": run_id,
                "branch": branch,
                "status": status,
                "goal": f".agent/goals/{goal_id or run_id}.yaml",
                "record": record,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


class AgentLedgerConsistencyGuardTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        (self.base / ".agent").mkdir(parents=True, exist_ok=True)
        (self.base / ".agent/context.yaml").write_text(CONTEXT_TEXT, encoding="utf-8")
        (self.base / AUTHORITY).parent.mkdir(parents=True, exist_ok=True)
        (self.base / AUTHORITY).write_text("# recorded decision\n", encoding="utf-8")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def build(
        self,
        goals: dict[str, str] | None = None,
        runs: dict[str, dict] | None = None,
        index: dict[str, str] | None = None,
    ) -> Path:
        for goal_id, status in (BASE_GOALS if goals is None else goals).items():
            write_goal(self.base, goal_id, status)
        for run_id, spec in (BASE_RUNS if runs is None else runs).items():
            write_run(self.base, run_id, spec["status"], spec["branch"], spec.get("goal_id"))
        (self.base / ".agent/active-runs.json").write_text(
            json.dumps({"schema_version": 1, "branches": BASE_INDEX if index is None else index}, indent=2)
            + "\n",
            encoding="utf-8",
        )
        return self.base

    # --- baseline first: the negative cases below are only meaningful if the
    # --- synthetic ledger is normal before the injection.
    def test_synthetic_baseline_is_clean(self) -> None:
        self.assertEqual(MODULE.check(self.build()), [])

    def test_repository_ledger_is_clean(self) -> None:
        self.assertEqual(MODULE.check(MODULE.ROOT), [])

    def test_terminal_run_with_open_goal_is_detected(self) -> None:
        self.assertEqual(MODULE.check(self.build()), [])
        write_goal(self.base, "GAP-GOAL", "active")
        write_run(self.base, "GAP-GOAL", "completed", "audit/gap-goal")
        errors = MODULE.check(self.base)
        self.assertTrue(
            any(
                "GAP-GOAL" in e
                and "run .agent/runs/GAP-GOAL/run.json is completed" in e
                and "goal status is 'active'" in e
                for e in errors
            ),
            errors,
        )

    def test_allowlist_removes_a_terminal_mismatch(self) -> None:
        # Reverse direction: without the recorded allowlist entry the same shape
        # is a hard failure, so the allowlist is what keeps it open by design.
        self.assertEqual(MODULE.check(self.build()), [])
        saved = dict(MODULE.TERMINAL_MISMATCH_ALLOWLIST)
        try:
            MODULE.TERMINAL_MISMATCH_ALLOWLIST.pop("P4-INCREMENTAL-RESUME")
            errors = MODULE.check(self.base)
            self.assertTrue(any("P4-INCREMENTAL-RESUME" in e and "is completed" in e for e in errors), errors)
        finally:
            MODULE.TERMINAL_MISMATCH_ALLOWLIST.clear()
            MODULE.TERMINAL_MISMATCH_ALLOWLIST.update(saved)

    def test_stale_allowlist_entry_is_detected(self) -> None:
        self.assertEqual(MODULE.check(self.build()), [])
        write_goal(self.base, "P4-INCREMENTAL-RESUME", "completed")
        errors = MODULE.check(self.base)
        self.assertTrue(any("P4-INCREMENTAL-RESUME" in e and "no longer matches" in e for e in errors), errors)

    def test_missing_allowlist_authority_is_detected(self) -> None:
        self.assertEqual(MODULE.check(self.build()), [])
        (self.base / AUTHORITY).unlink()
        errors = MODULE.check(self.base)
        self.assertTrue(any("authority" in e and "does not exist" in e for e in errors), errors)

    def test_unknown_non_canonical_goal_status_is_detected(self) -> None:
        self.assertEqual(MODULE.check(self.build()), [])
        write_goal(self.base, "BRAND-NEW-GOAL", "in_progress")
        errors = MODULE.check(self.base)
        self.assertTrue(any("BRAND-NEW-GOAL" in e and "not in the canonical enum" in e for e in errors), errors)

    def test_recorded_residual_drift_is_detected(self) -> None:
        self.assertEqual(MODULE.check(self.build()), [])
        write_goal(self.base, "FORM-PAGE-STRUCTURE-PROFESSIONALIZATION", "in_review")
        errors = MODULE.check(self.base)
        self.assertTrue(any("drifted" in e for e in errors), errors)

    def test_closed_recorded_residual_is_detected_until_pin_is_removed(self) -> None:
        self.assertEqual(MODULE.check(self.build()), [])
        write_goal(self.base, "PAYMENT-REQUEST-GOLDEN-FLOORPLAN", "completed")
        errors = MODULE.check(self.base)
        self.assertTrue(any("recorded non-canonical residual" in e and "is gone" in e for e in errors), errors)

    def test_index_pointing_at_missing_run_is_detected(self) -> None:
        self.assertEqual(MODULE.check(self.build()), [])
        index = dict(BASE_INDEX)
        index["audit/ghost"] = ".agent/runs/GHOST/run.json"
        errors = MODULE.check(self.build(index=index))
        self.assertTrue(any("audit/ghost" in e and "does not exist" in e for e in errors), errors)

    def test_index_pointing_at_terminal_run_is_detected(self) -> None:
        self.assertEqual(MODULE.check(self.build()), [])
        index = dict(BASE_INDEX)
        index["fix/contract-slo-telemetry"] = ".agent/runs/BACKEND-CONTRACT-SLO-TELEMETRY/run.json"
        errors = MODULE.check(self.build(index=index))
        self.assertTrue(any("must be removed from the index" in e for e in errors), errors)

    def test_index_branch_mismatch_is_detected(self) -> None:
        self.assertEqual(MODULE.check(self.build()), [])
        index = {"fix/wrong-branch": ".agent/runs/SAMPLE-LIVE-RUN/run.json"}
        errors = MODULE.check(self.build(index=index))
        self.assertTrue(any("declares branch" in e for e in errors), errors)

    def test_invalid_goal_yaml_is_detected(self) -> None:
        self.assertEqual(MODULE.check(self.build()), [])
        (self.base / ".agent/goals/BROKEN.yaml").write_text(
            "goal:\n  id: BROKEN\n  status: active\n  objective: a: b\n", encoding="utf-8"
        )
        errors = MODULE.check(self.base)
        self.assertTrue(any("not machine-readable YAML" in e for e in errors), errors)

    def test_run_record_with_unresolvable_goal_is_detected(self) -> None:
        self.assertEqual(MODULE.check(self.build()), [])
        write_goal(self.base, "ORPHAN-RUN", "active")
        write_run(self.base, "ORPHAN-RUN", "active", "audit/orphan-run", "NO-SUCH-GOAL")
        errors = MODULE.check(self.base)
        self.assertTrue(any("ORPHAN-RUN" in e and "goal does not resolve" in e for e in errors), errors)

    def test_duplicate_goal_id_is_detected(self) -> None:
        self.assertEqual(MODULE.check(self.build()), [])
        (self.base / ".agent/goals/DUPLICATE.yaml").write_text(
            "goal:\n  id: PAYMENT-REQUEST-GOLDEN-FLOORPLAN\n  status: complete\n", encoding="utf-8"
        )
        errors = MODULE.check(self.base)
        self.assertTrue(any("duplicate goal id" in e for e in errors), errors)


if __name__ == "__main__":
    unittest.main()
