#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("lane_telemetry", ROOT / "scripts/ci/lane_telemetry.py")
assert SPEC and SPEC.loader
telemetry = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(telemetry)


class LaneTelemetryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        (self.root / "tracked.txt").write_text("baseline\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.root), "add", "."], check=True)
        subprocess.run(
            ["git", "-C", str(self.root), "-c", "user.name=Codex Test",
             "-c", "user.email=codex-test@example.invalid", "commit", "-q", "-m", "fixture"],
            check=True,
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _record(self, **overrides):
        kwargs = {
            "lane": "local.iteration",
            "entrypoint": "ci.local.iteration",
            "status": "passed",
            "duration_seconds": 1.5,
        }
        kwargs.update(overrides)
        return telemetry.record(self.root, **kwargs)

    def test_valid_record_round_trips(self) -> None:
        payload = self._record()
        records, failures = telemetry.load(self.root)
        self.assertEqual(failures, [])
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["lane"], "local.iteration")
        self.assertEqual(records[0]["status"], "passed")
        self.assertEqual(records[0]["degraded"], [])
        self.assertIsNone(records[0]["failure_owner"])
        self.assertFalse(records[0]["worktree_dirty"])
        self.assertEqual(records[0]["head"], payload["head"])

    def test_unknown_lane_is_refused(self) -> None:
        with self.assertRaisesRegex(telemetry.TelemetryError, "unknown lane"):
            self._record(lane="local.imaginary")

    def test_entrypoint_must_belong_to_the_declared_lane(self) -> None:
        with self.assertRaisesRegex(telemetry.TelemetryError, "is not owned by lane"):
            self._record(entrypoint="ci.local.quick.run")

    def test_failed_run_needs_a_declared_failure_owner(self) -> None:
        with self.assertRaisesRegex(telemetry.TelemetryError, "needs one declared failure owner"):
            self._record(status="failed")
        with self.assertRaisesRegex(telemetry.TelemetryError, "needs one declared failure owner"):
            self._record(status="failed", failure_owner="because")

    def test_passing_run_must_not_carry_a_failure_owner(self) -> None:
        with self.assertRaisesRegex(telemetry.TelemetryError, "only a failed run may carry"):
            self._record(failure_owner="environment_defect")

    def test_unfinished_run_may_carry_a_declared_owner_and_stays_in_the_store(self) -> None:
        self._record(status="not_run", failure_owner="validation_tool_defect")
        records, failures = telemetry.load(self.root)
        self.assertEqual(failures, [])
        self.assertEqual([record["status"] for record in records], ["not_run"])
        self.assertEqual(records[0]["failure_owner"], "validation_tool_defect")

    def test_unfinished_run_refuses_an_undeclared_owner(self) -> None:
        with self.assertRaisesRegex(telemetry.TelemetryError, "unknown failure owner"):
            self._record(status="not_run", failure_owner="vibes")

    def test_unknown_degraded_reason_is_refused(self) -> None:
        with self.assertRaisesRegex(telemetry.TelemetryError, "declared reasons"):
            self._record(degraded=("it_felt_slow",))

    def test_negative_duration_is_refused(self) -> None:
        with self.assertRaisesRegex(telemetry.TelemetryError, "non-negative"):
            self._record(duration_seconds=-1)

    def test_tampered_line_is_an_integrity_failure(self) -> None:
        self._record()
        path = telemetry.lane_path(self.root, "local.iteration")
        with path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"lane": "local.iteration"}) + "\n")
        records, failures = telemetry.load(self.root)
        self.assertEqual(len(records), 1)
        self.assertEqual(len(failures), 1)
        summary = telemetry.summarise(self.root)
        self.assertGreater(summary["integrity_failure_rate"], 0)
        self.assertEqual(telemetry.check(self.root), 2)

    def test_record_filed_under_the_wrong_lane_is_an_integrity_failure(self) -> None:
        self._record()
        source = telemetry.lane_path(self.root, "local.iteration")
        target = telemetry.lane_path(self.root, "local.quick")
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        _records, failures = telemetry.load(self.root)
        self.assertTrue(any("filed under lane" in failure for failure in failures))

    def test_rates_aggregate_per_lane(self) -> None:
        self._record(duration_seconds=10.0)
        self._record(duration_seconds=20.0, degraded=("full_scan_fallback",))
        self._record(status="failed", duration_seconds=30.0, failure_owner="validation_tool_defect")
        stats = telemetry.summarise(self.root)["lanes"]["local.iteration"]
        self.assertEqual(stats["runs"], 3)
        self.assertEqual(stats["by_status"], {"failed": 1, "passed": 2})
        self.assertEqual(stats["pass_rate"], round(2 / 3, 4))
        self.assertEqual(stats["degraded_rate"], round(1 / 3, 4))
        self.assertEqual(stats["degraded_by_reason"], {"full_scan_fallback": 1})
        self.assertEqual(stats["failure_owners"], {"validation_tool_defect": 1})
        self.assertEqual(stats["duration_seconds"]["p50"], 20.0)
        self.assertEqual(stats["duration_seconds"]["max"], 30.0)

    def test_untouched_lanes_report_no_data_not_a_rate(self) -> None:
        self._record()
        summary = telemetry.summarise(self.root)
        self.assertEqual(summary["lanes"]["remote.frontend.full"]["runs"], 0)
        self.assertEqual(summary["lanes"]["remote.frontend.full"]["pass_rate"], 0.0)
        self.assertEqual(telemetry.check(self.root), 0)

    def test_summary_can_group_by_version(self) -> None:
        self._record()
        self._record(status="failed", duration_seconds=5.0, failure_owner="product_defect")
        by_head = telemetry.summarise(self.root, by_head=True)["by_head"]
        self.assertEqual(len(by_head), 1)
        version = next(iter(by_head.values()))
        self.assertEqual(version["lanes"]["local.iteration"]["runs"], 2)
        self.assertFalse(version["worktree_dirty"])

    def test_declared_lane_names_come_from_the_coverage_audit(self) -> None:
        self.assertEqual(sorted(telemetry.lanes.LANES), [
            "local.iteration",
            "local.quick",
            "remote.frontend.full",
            "remote.frontend.standard",
            "remote.professional.backend.reports",
            "remote.professional.backend.tests",
            "remote.professional.backend.verify",
            "remote.standard_backend",
        ])
        self.assertIn("ci.local.quick", telemetry.owned_entrypoints("local.quick"))


if __name__ == "__main__":
    unittest.main()
