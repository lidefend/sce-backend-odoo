#!/usr/bin/env python3
"""Offline lock for the contract SLO telemetry core.

The suite binds the SLO identity to the lifecycle evidence the platform already
emits (loaded from source, no Odoo runtime) and pins the aggregation invariants:
exact counts, rates over accepted observations, no fabricated rates and no
silently dropped malformed rows.
"""
from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
SLO_PATH = ROOT / "addons/smart_core/core/contract_slo_telemetry.py"
LIFECYCLE_PATH = ROOT / "addons/smart_core/core/contract_lifecycle.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


SLO = load_module("contract_slo_telemetry", SLO_PATH)
LIFECYCLE = load_module("contract_lifecycle", LIFECYCLE_PATH)


def sealed_contract(request_id: str = "req-1") -> dict:
    contract = {
        "schemaVersion": "2.2.0",
        "page": {"id": "project.list", "containers": []},
        "meta": {"etag": "draft"},
    }
    return LIFECYCLE.seal_unified_page_contract(
        contract,
        source_payload={"model": "project.project", "viewType": "list"},
        source_type="runtime_projection",
        request_id=request_id,
        trace_id="",
        client_type="web_pc",
        stage="runtime_delivery",
        generator="ui_contract_v2",
        generator_version="17.0.1.1.9",
    )


def observation(*, live=None, identity=None, outcome="success", observed_at=1000.0, **overrides) -> dict:
    payload = {
        "schemaVersion": SLO.SCHEMA_VERSION,
        "identity": identity if identity is not None else delivered_identity(),
        "outcome": outcome,
        "degradationReasons": [],
        "latencyMs": 12,
        "observedAt": observed_at,
        "clientType": "web_pc",
        "requestId": live or "req-1",
    }
    payload.update(overrides)
    return payload


def delivered_identity(*, source_sha="a" * 64, stage="runtime_delivery", **extra) -> dict:
    identity = {
        "schemaId": "smart_core.unified_page_contract_v2",
        "schemaVersion": "2.2.0",
        "contractVersion": "2.2.0",
        "sourceType": "runtime_projection",
        "sourceSha256": source_sha,
        "stage": stage,
    }
    identity.update(extra)
    return identity


class IdentityTest(unittest.TestCase):
    def test_identity_is_read_from_real_lifecycle_evidence(self):
        contract = sealed_contract()
        lifecycle = contract["meta"]["lifecycle"]
        identity = SLO.delivery_identity(contract)
        self.assertEqual(identity["schemaId"], lifecycle["definition"]["schemaId"])
        self.assertEqual(identity["schemaVersion"], lifecycle["definition"]["schemaVersion"])
        self.assertEqual(identity["contractVersion"], lifecycle["definition"]["contractVersion"])
        self.assertEqual(identity["sourceType"], lifecycle["generation"]["sourceType"])
        self.assertEqual(identity["sourceSha256"], lifecycle["generation"]["sourceSha256"])
        self.assertEqual(identity["stage"], "runtime_delivery")
        self.assertNotIn(SLO.PUBLISHED_VERSION_FIELD, identity)

    def test_identity_fails_closed_without_lifecycle_evidence(self):
        with self.assertRaises(SLO.ContractSloError):
            SLO.delivery_identity({"meta": {"etag": "e"}})
        with self.assertRaises(SLO.ContractSloError):
            SLO.delivery_identity(None)

    def test_identity_names_the_missing_field(self):
        lifecycle = {"definition": {"schemaId": "x", "schemaVersion": "1", "contractVersion": "1"},
                     "generation": {"sourceType": "s", "sourceSha256": ""},
                     "stage": "runtime_delivery"}
        with self.assertRaises(SLO.ContractSloError) as ctx:
            SLO.delivery_identity(lifecycle=lifecycle)
        self.assertIn("sourceSha256", str(ctx.exception))

    def test_optional_published_version_ref_is_additive(self):
        lifecycle = {"definition": {"schemaId": "x", "schemaVersion": "1", "contractVersion": "1",
                                    "publishedVersionRef": "cfg-7"},
                     "generation": {"sourceType": "s", "sourceSha256": "b" * 64},
                     "stage": "runtime_delivery"}
        identity = SLO.delivery_identity(lifecycle=lifecycle)
        self.assertEqual(identity[SLO.PUBLISHED_VERSION_FIELD], "cfg-7")


class ClassificationTest(unittest.TestCase):
    def test_integrity_failure_outranks_degradation(self):
        self.assertEqual(
            SLO.classify_delivery(integrity_ok=False, degradation_reasons=["trim"]),
            SLO.OUTCOME_INTEGRITY_FAILURE,
        )

    def test_degraded_requires_a_reason_and_defaults_to_success(self):
        self.assertEqual(SLO.classify_delivery(integrity_ok=True), SLO.OUTCOME_SUCCESS)
        self.assertEqual(SLO.classify_delivery(integrity_ok=True, degradation_reasons=[]), SLO.OUTCOME_SUCCESS)
        self.assertEqual(
            SLO.classify_delivery(integrity_ok=True, degradation_reasons=["field_policy_tightened"]),
            SLO.OUTCOME_DEGRADED,
        )

    def test_classification_rejects_a_non_bool_integrity(self):
        for value in ("true", 1, None):
            with self.subTest(value=value):
                with self.assertRaises(SLO.ContractSloError):
                    SLO.classify_delivery(integrity_ok=value)

    def test_build_observation_validates_latency_and_time(self):
        with self.assertRaises(SLO.ContractSloError):
            SLO.build_observation(integrity_ok=True, identity=delivered_identity(), latency_ms=-1)
        with self.assertRaises(SLO.ContractSloError):
            SLO.build_observation(integrity_ok=True, identity=delivered_identity(), observed_at="now")
        built = SLO.build_observation(
            integrity_ok=True,
            identity=delivered_identity(),
            degradation_reasons=["trim", "trim"],
            latency_ms=7.9,
            observed_at=1000.0,
        )
        self.assertEqual(built["outcome"], SLO.OUTCOME_DEGRADED)
        self.assertEqual(built["degradationReasons"], ["trim"])
        self.assertEqual(built["latencyMs"], 7)

    def test_outcome_declaration_is_locked(self):
        self.assertEqual(
            SLO.CONTRACT_SLO_OUTCOMES,
            ("success", "degraded", "integrity_failure"),
        )
        self.assertEqual(
            SLO.RATE_FIELDS,
            ("successRate", "degradationRate", "integrityFailureRate"),
        )


class AggregationTest(unittest.TestCase):
    def test_rates_are_exact_over_accepted_and_counts_sum(self):
        rows = [
            observation(outcome="success"),
            observation(outcome="success"),
            observation(outcome="success"),
            observation(outcome="degraded"),
            observation(outcome="integrity_failure"),
        ]
        report = SLO.aggregate_observations(rows)
        self.assertEqual(report["totalObservations"], 5)
        self.assertEqual(report["acceptedObservations"], 5)
        self.assertEqual(report["rejectedObservations"], 0)
        self.assertEqual(report["versionCount"], 1)
        entry = report["versions"][0]
        self.assertEqual(entry["observations"], 5)
        self.assertEqual(sum(entry["outcomes"].values()), entry["observations"])
        self.assertEqual(entry["outcomes"], {"success": 3, "degraded": 1, "integrity_failure": 1})
        self.assertEqual(entry["successRate"], 0.6)
        self.assertEqual(entry["degradationRate"], 0.2)
        self.assertEqual(entry["integrityFailureRate"], 0.2)

    def test_empty_input_reports_no_fabricated_versions(self):
        report = SLO.aggregate_observations([])
        self.assertEqual(report["versionCount"], 0)
        self.assertEqual(report["versions"], [])
        self.assertEqual(report["acceptedObservations"], 0)

    def test_window_excludes_old_observations_without_counting_them_as_rejected(self):
        rows = [
            observation(observed_at=1000.0),
            observation(observed_at=900.0),
            observation(observed_at=100.0),
        ]
        report = SLO.aggregate_observations(rows, window_seconds=300, now=1000.0)
        self.assertEqual(report["acceptedObservations"], 2)
        self.assertEqual(report["windowExcludedObservations"], 1)
        self.assertEqual(report["rejectedObservations"], 0)
        self.assertEqual(report["windowSeconds"], 300)

    def test_window_excluding_everything_yields_no_version_rows(self):
        report = SLO.aggregate_observations([observation(observed_at=1.0)], window_seconds=10, now=1000.0)
        self.assertEqual(report["versions"], [])
        self.assertEqual(report["windowExcludedObservations"], 1)

    def test_malformed_observations_are_counted_and_sampled(self):
        rows = [
            observation(),
            "not-an-object",
            observation(outcome="unknown"),
            observation(identity={"schemaId": "x"}),
            observation(schemaVersion="0.0.0"),
            observation(observed_at="nope"),
        ]
        report = SLO.aggregate_observations(rows)
        self.assertEqual(report["totalObservations"], 6)
        self.assertEqual(report["acceptedObservations"], 1)
        self.assertEqual(report["rejectedObservations"], 5)
        self.assertEqual(
            [sample["reason"] for sample in report["rejectedSample"]],
            [
                "observation_not_object",
                "unknown_outcome",
                "incomplete_identity:schemaVersion,contractVersion,sourceType,sourceSha256,stage",
                "unsupported_schema_version",
                "invalid_observed_at",
            ],
        )
        self.assertEqual(report["versionCount"], 1)

    def test_rejected_sample_is_capped(self):
        report = SLO.aggregate_observations(["bad"] * (SLO.REJECTED_SAMPLE_LIMIT + 5))
        self.assertEqual(report["rejectedObservations"], SLO.REJECTED_SAMPLE_LIMIT + 5)
        self.assertEqual(len(report["rejectedSample"]), SLO.REJECTED_SAMPLE_LIMIT)

    def test_versions_are_grouped_and_sorted_deterministically(self):
        rows = [
            observation(identity=delivered_identity(source_sha="b" * 64), outcome="degraded"),
            observation(identity=delivered_identity(source_sha="a" * 64), outcome="success"),
            observation(identity=delivered_identity(source_sha="a" * 64), outcome="success"),
        ]
        report = SLO.aggregate_observations(rows)
        self.assertEqual(report["versionCount"], 2)
        self.assertEqual([entry["sourceSha256"] for entry in report["versions"]], ["a" * 64, "b" * 64])
        self.assertEqual(report["versions"][0]["successRate"], 1.0)
        self.assertEqual(report["versions"][1]["degradationRate"], 1.0)
        self.assertEqual(report, SLO.aggregate_observations(list(reversed(rows))))

    def test_aggregation_rejects_a_non_iterable(self):
        with self.assertRaises(SLO.ContractSloError):
            SLO.aggregate_observations("nope")
        with self.assertRaises(SLO.ContractSloError):
            SLO.aggregate_observations([], window_seconds=0)


class EmissionTest(unittest.TestCase):
    def test_a_valid_observation_reaches_the_sink_once(self):
        seen = []
        self.assertTrue(SLO.emit_observation(observation(), sink=seen.append))
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0], observation())

    def test_a_malformed_observation_never_reaches_the_sink(self):
        malformed = [
            "not an object",
            {"schemaVersion": "0.0.0"},
            observation(outcome="unknown"),
            observation(identity={"schemaId": "only-one-field"}),
            observation(observed_at="yesterday"),
        ]
        for candidate in malformed:
            with self.subTest(candidate=candidate):
                seen = []
                self.assertFalse(SLO.emit_observation(candidate, sink=seen.append))
                self.assertEqual(seen, [])

    def test_a_raising_sink_does_not_break_the_delivery_path(self):
        def sink(_observation):
            raise RuntimeError("telemetry backend is down")

        self.assertFalse(SLO.emit_observation(observation(), sink=sink))

    def test_a_missing_or_non_callable_sink_is_not_an_error(self):
        self.assertFalse(SLO.emit_observation(observation(), sink=None))
        self.assertFalse(SLO.emit_observation(observation(), sink="not callable"))

    def test_the_sink_return_value_is_reported_without_a_none_trap(self):
        self.assertTrue(SLO.emit_observation(observation(), sink=lambda _o: None))
        self.assertFalse(SLO.emit_observation(observation(), sink=lambda _o: False))

    def test_emitting_does_not_mutate_the_observation(self):
        original = observation()
        snapshot = dict(original)
        SLO.emit_observation(original, sink=lambda _o: None)
        self.assertEqual(original, snapshot)

    def test_the_log_line_is_canonical_and_prefixed(self):
        line = SLO.observation_log_line(observation())
        self.assertIsInstance(line, str)
        self.assertTrue(line.startswith(SLO.OBSERVATION_LINE_KEY + " "))
        self.assertEqual(line, SLO.observation_log_line(observation()))
        body = line.split(" ", 1)[1]
        self.assertNotIn(": ", body)
        self.assertNotIn(", ", body)

    def test_the_log_line_round_trips(self):
        original = observation()
        self.assertEqual(SLO.parse_observation_line(SLO.observation_log_line(original)), original)

    def test_an_invalid_observation_has_no_log_line(self):
        self.assertIsNone(SLO.observation_log_line("nope"))
        self.assertIsNone(SLO.observation_log_line(observation(outcome="nope")))

    def test_the_parser_rejects_foreign_and_poisoned_lines(self):
        for line in (
            None,
            42,
            "",
            "unrelated log line",
            SLO.OBSERVATION_LINE_KEY + " ",
            SLO.OBSERVATION_LINE_KEY + " {not json}",
            SLO.OBSERVATION_LINE_KEY + ' {"outcome":"nope"}',
        ):
            with self.subTest(line=line):
                self.assertIsNone(SLO.parse_observation_line(line))

    def test_the_line_emitter_agrees_with_the_object_emitter(self):
        lines, objects = [], []
        self.assertTrue(SLO.emit_observation_line(observation(), sink=lines.append))
        self.assertTrue(SLO.emit_observation(observation(), sink=objects.append))
        self.assertEqual(len(lines), 1)
        self.assertEqual(SLO.parse_observation_line(lines[0]), objects[0])

    def test_the_line_emitter_is_fail_open_too(self):
        seen = []
        self.assertFalse(SLO.emit_observation_line(observation(outcome="nope"), sink=seen.append))
        self.assertEqual(seen, [])

        def sink(_line):
            raise RuntimeError("down")

        self.assertFalse(SLO.emit_observation_line(observation(), sink=sink))
        self.assertFalse(SLO.emit_observation_line(observation(), sink=None))


class OfflinePurityTest(unittest.TestCase):
    def test_core_has_no_odoo_dependency(self):
        tree = ast.parse(SLO_PATH.read_text(encoding="utf-8"))
        roots: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                roots.add(node.module.split(".")[0])
        self.assertNotIn("odoo", roots, "the SLO core must stay offline-verifiable")


if __name__ == "__main__":
    unittest.main()
