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
