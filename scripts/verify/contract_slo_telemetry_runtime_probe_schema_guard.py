# -*- coding: utf-8 -*-
"""Host-side guard for the contract SLO telemetry runtime probe report.

Consumes the JSON the in-container probe writes and asserts the runtime half of
the L5 gap with a non-zero test count, so a "zero tests" run can never be
mistaken for a pass. It re-checks the recorded evidence independently of the
probe's own PASS marker.
"""

import json
import os
import unittest


PROBE_REPORT = os.environ.get(
    "CONTRACT_SLO_RUNTIME_PROBE_REPORT",
    "/tmp/contract_slo_telemetry_runtime_probe.json",
)
REQUIRED_IDENTITY_FIELDS = (
    "schemaId",
    "schemaVersion",
    "contractVersion",
    "sourceType",
    "sourceSha256",
    "stage",
)
REQUIRED_CHECKS = (
    "baseline_delivery_ok",
    "baseline_emits_exactly_one_line",
    "observation_identity_complete",
    "declaration_consumer_accepts_observation",
    "same_identity_groups_into_one_row",
    "distinct_surface_emits_one_line",
    "each_delivery_persisted_one_row",
    "stored_rows_round_trip_the_emitted_identity",
    "store_aggregate_accepts_the_persisted_rows",
    "trend_places_every_row_in_one_bucket",
    "trend_keeps_versions_in_separate_rows",
    "read_intent_reports_the_store",
    "retention_cron_record_exists",
    "retention_cron_is_active",
    "retention_cron_targets_the_observation_model",
    "retention_cron_calls_the_model_sweep",
    "retention_sweep_removes_only_rows_past_the_horizon",
    "retention_sweep_keeps_rows_inside_the_horizon",
    "retention_probe_rows_cleaned_up",
    "test_configuration_restored",
)


def _load():
    with open(PROBE_REPORT, "r", encoding="utf-8") as handle:
        return json.load(handle)


class ContractSloRuntimeProbeReportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = _load()

    def test_report_shape(self):
        self.assertEqual(self.report.get("probe"), "contract_slo_telemetry_runtime")
        self.assertEqual(self.report.get("database"), "sc_contract_lifecycle")
        self.assertGreater(self.report.get("checkCount", 0), 0)

    def test_no_probe_check_failed(self):
        self.assertEqual(self.report.get("failedCount"), 0, self.report.get("failed"))
        failed = [check["name"] for check in self.report.get("checks", []) if not check.get("ok")]
        self.assertEqual(failed, [])

    def test_the_required_checks_are_all_present(self):
        """A probe that silently drops a section must not read as a pass."""
        names = {check.get("name") for check in self.report.get("checks", [])}
        missing = [name for name in REQUIRED_CHECKS if name not in names]
        self.assertEqual(missing, [], missing)

    def test_every_delivery_persisted_exactly_one_row(self):
        detail = {
            check["name"]: check.get("detail")
            for check in self.report.get("checks", [])
        }.get("each_delivery_persisted_one_row", {})
        self.assertEqual(detail.get("after", 0) - detail.get("before", 0), detail.get("emitted"))
        self.assertGreaterEqual(detail.get("emitted", 0), 3)

    def test_the_read_model_sees_the_persisted_rows(self):
        detail = {
            check["name"]: check.get("detail")
            for check in self.report.get("checks", [])
        }.get("read_intent_reports_the_store", {})
        self.assertGreaterEqual(detail.get("store", 0), 3)
        self.assertGreaterEqual(detail.get("accepted", 0), 3)

    def test_every_observation_is_identity_complete(self):
        observations = self.report.get("observations") or []
        self.assertGreaterEqual(len(observations), 3)
        for observation in observations:
            identity = observation.get("identity") or {}
            for field in REQUIRED_IDENTITY_FIELDS:
                self.assertTrue(str(identity.get(field) or "").strip(),
                                "%s missing in %s" % (field, identity))
            self.assertEqual(identity.get("stage"), "runtime_delivery")
            self.assertIn(observation.get("outcome"), ("success", "degraded", "integrity_failure"))

    def test_the_retention_carrier_is_scheduled_and_scoped(self):
        """The horizon must reach the store through an active, targeted cron.

        A sweep that is inactive, points at another model, or removes every row
        would all "delete old data"; the reported detail has to distinguish them.
        """
        detail = {check["name"]: check.get("detail") for check in self.report.get("checks", [])}
        sweep = detail.get("retention_sweep_removes_only_rows_past_the_horizon", {})
        self.assertEqual(sweep.get("removed"), 1, sweep)
        self.assertEqual(len(sweep.get("remaining") or []), 2, sweep)


    def test_aggregate_accepts_every_emitted_observation(self):
        aggregate = self.report.get("aggregate") or {}
        observations = self.report.get("observations") or []
        self.assertEqual(aggregate.get("acceptedObservations"), len(observations))
        self.assertEqual(aggregate.get("rejectedObservations"), 0)
        self.assertEqual(aggregate.get("totalObservations"), len(observations))

    def test_baseline_succeeds_without_integrity_failure(self):
        aggregate = self.report.get("aggregate") or {}
        versions = aggregate.get("versions") or []
        self.assertGreaterEqual(len(versions), 1)
        for version in versions:
            self.assertEqual(version.get("integrityFailureRate"), 0.0, version)
        self.assertEqual(versions[0].get("successRate"), 1.0, versions[0])
        self.assertGreaterEqual(
            sum(1 for version in versions if version.get("successRate") == 1.0), 1
        )
        for observation in self.report.get("observations") or []:
            self.assertNotEqual(observation.get("outcome"), "integrity_failure")


if __name__ == "__main__":
    unittest.main()
