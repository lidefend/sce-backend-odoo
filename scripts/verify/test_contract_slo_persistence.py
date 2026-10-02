#!/usr/bin/env python3
"""Offline lock for the contract SLO persistence and trend read model.

The store's DB wrappers need a live env, but the row <-> observation conversion
and the bucket/trend math are pure. This suite pins those pure contracts offline:
the stored columns must round-trip the identity exactly, an unusable row must be
reported as unreadable instead of being aggregated under a guessed identity, and
bucket rates must come from the same pure aggregator as any other window.
"""
from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
import sys
import types
import unittest


ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "addons/smart_core/core"
PACKAGE = "sc_slo_persistence_probe"


def _install_package() -> None:
    for name, path in (
        (PACKAGE, ROOT / "addons"),
        (PACKAGE + ".smart_core", ROOT / "addons/smart_core"),
        (PACKAGE + ".smart_core.core", CORE),
    ):
        module = types.ModuleType(name)
        module.__path__ = [str(path)]
        sys.modules[name] = module


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader
    spec.loader.exec_module(module)
    return module


_install_package()
SLO = _load(PACKAGE + ".smart_core.core.contract_slo_telemetry", CORE / "contract_slo_telemetry.py")
STORE = _load(PACKAGE + ".smart_core.core.contract_slo_persistence", CORE / "contract_slo_persistence.py")


def observation(
    *,
    observed_at: float = 1_700_000_000.0,
    outcome: str = "success",
    contract_version: str = "2.2.0",
    source_type: str = "native_form_projection",
    published: str = "",
    reasons=None,
):
    identity = {
        "schemaId": "smart_core.unified_page_contract_v2",
        "schemaVersion": "2.2.0",
        "contractVersion": contract_version,
        "sourceType": source_type,
        "sourceSha256": "a" * 64,
        "stage": "runtime_delivery",
    }
    if published:
        identity[STORE.slo.PUBLISHED_VERSION_FIELD] = published
    return {
        "schemaVersion": SLO.SCHEMA_VERSION,
        "identity": identity,
        "outcome": outcome,
        "degradationReasons": list(reasons or []),
        "latencyMs": None,
        "observedAt": observed_at,
        "clientType": "web_pc",
        "requestId": "req-1",
    }


class RowMappingTest(unittest.TestCase):
    def test_row_values_maps_the_whole_identity(self):
        values = STORE.row_values(observation(), company_id=7)
        self.assertEqual(values["schema_id"], "smart_core.unified_page_contract_v2")
        self.assertEqual(values["contract_version"], "2.2.0")
        self.assertEqual(values["source_type"], "native_form_projection")
        self.assertEqual(values["stage"], "runtime_delivery")
        self.assertEqual(values["outcome"], "success")
        self.assertEqual(values["company_id"], 7)
        self.assertEqual(values["observed_at"], "2023-11-14 22:13:20")

    def test_row_values_omits_an_absent_published_version(self):
        values = STORE.row_values(observation())
        self.assertFalse(values["published_version_ref"])
        values = STORE.row_values(observation(published="42"))
        self.assertEqual(values["published_version_ref"], "42")

    def test_row_values_refuses_an_untrusted_observation(self):
        bad = observation()
        bad["identity"]["stage"] = ""
        with self.assertRaises(SLO.ContractSloError):
            STORE.row_values(bad)

    def test_a_stored_row_round_trips_to_the_same_observation(self):
        original = observation()
        rebuilt = STORE.observation_from_row(STORE.row_values(original))
        self.assertEqual(rebuilt, original)

    def test_an_unset_column_never_fabricates_an_identity_value(self):
        row = STORE.row_values(observation())
        row["published_version_ref"] = False
        rebuilt = STORE.observation_from_row(row)
        self.assertNotIn(STORE.slo.PUBLISHED_VERSION_FIELD, rebuilt["identity"])

    def test_unusable_rows_are_readable_as_unusable(self):
        good = STORE.row_values(observation())
        self.assertIsNone(STORE.observation_from_row(None))
        self.assertIsNone(STORE.observation_from_row("not a row"))
        for change in (
            {"stage": False},
            {"observed_at": "not-a-time"},
            {"observed_at": None},
            {"outcome": "unheard_of"},
            {"degradation_reasons_json": "{"},
        ):
            row = dict(good)
            row.update(change)
            self.assertIsNone(STORE.observation_from_row(row), row)

    def test_a_degraded_row_keeps_its_reasons(self):
        original = observation(outcome="degraded", reasons=["b", "a", "a"])
        rebuilt = STORE.observation_from_row(STORE.row_values(original))
        self.assertEqual(rebuilt["outcome"], "degraded")
        self.assertEqual(rebuilt["degradationReasons"], ["a", "b"])


class BucketWindowTest(unittest.TestCase):
    def test_buckets_cover_the_window_exactly_oldest_first(self):
        windows = STORE.bucket_windows(window_seconds=300, bucket_seconds=100, now=10_000.0)
        self.assertEqual(windows, [(9_700.0, 9_800.0), (9_800.0, 9_900.0), (9_900.0, 10_000.0)])

    def test_a_partial_leading_bucket_is_dropped_not_reported_as_full(self):
        windows = STORE.bucket_windows(window_seconds=250, bucket_seconds=100, now=10_000.0)
        self.assertEqual(len(windows), 2)
        self.assertEqual(windows[0], (9_800.0, 9_900.0))

    def test_a_window_smaller_than_one_bucket_is_refused(self):
        with self.assertRaises(SLO.ContractSloError):
            STORE.bucket_windows(window_seconds=30, bucket_seconds=100, now=10_000.0)
        for bad in (0, -1):
            with self.assertRaises(SLO.ContractSloError):
                STORE.bucket_windows(window_seconds=bad, bucket_seconds=100, now=10_000.0)


class TrendTest(unittest.TestCase):
    def test_each_bucket_aggregates_only_its_own_observations(self):
        observations = [
            observation(observed_at=9_700.0 + 10),
            observation(observed_at=9_800.0 + 10, outcome="degraded", reasons=["slow"]),
            observation(observed_at=9_800.0 + 20),
            observation(observed_at=9_900.0 + 10),
        ]
        trend = STORE.build_trend(
            observations, window_seconds=300, bucket_seconds=100, now=10_000.0
        )
        self.assertEqual(trend["bucketCount"], 3)
        counts = [bucket["aggregate"]["acceptedObservations"] for bucket in trend["buckets"]]
        self.assertEqual(counts, [1, 2, 1])
        middle = trend["buckets"][1]["aggregate"]["versions"][0]
        self.assertEqual(middle["observations"], 2)
        self.assertEqual(middle["successRate"], 0.5)
        self.assertEqual(middle["degradationRate"], 0.5)

    def test_every_observation_lands_in_exactly_one_bucket(self):
        observations = [
            observation(observed_at=9_700.0 + 10),
            observation(observed_at=9_800.0 + 10),
            observation(observed_at=9_900.0 + 10),
        ]
        trend = STORE.build_trend(observations, window_seconds=300, bucket_seconds=100, now=10_000.0)
        total = sum(bucket["aggregate"]["totalObservations"] for bucket in trend["buckets"])
        self.assertEqual(total, len(observations))
        self.assertEqual(sum(bucket["aggregate"]["acceptedObservations"] for bucket in trend["buckets"]), 3)

    def test_an_observation_outside_the_window_is_not_counted_at_all(self):
        observations = [
            observation(observed_at=9_000.0),  # much older than the window
            observation(observed_at=9_900.0 + 10),
        ]
        trend = STORE.build_trend(observations, window_seconds=300, bucket_seconds=100, now=10_000.0)
        total = sum(bucket["aggregate"]["totalObservations"] for bucket in trend["buckets"])
        self.assertEqual(total, 1)

    def test_an_unplaceable_observation_is_counted_not_dropped(self):
        bad = observation()
        bad["observedAt"] = "yesterday"
        trend = STORE.build_trend(
            [observation(observed_at=9_900.0 + 10), bad], window_seconds=300, bucket_seconds=100, now=10_000.0
        )
        self.assertEqual(trend["unplacedObservations"], 1)
        total = sum(bucket["aggregate"]["totalObservations"] for bucket in trend["buckets"])
        self.assertEqual(total, 1)

    def test_two_versions_never_merge_into_one_bucket_row(self):
        observations = [
            observation(observed_at=9_900.0 + 1, contract_version="2.2.0"),
            observation(observed_at=9_900.0 + 2, contract_version="2.3.0"),
        ]
        trend = STORE.build_trend(observations, window_seconds=100, bucket_seconds=100, now=10_000.0)
        versions = trend["buckets"][0]["aggregate"]["versions"]
        self.assertEqual(len(versions), 2)
        self.assertEqual([version["contractVersion"] for version in versions], ["2.2.0", "2.3.0"])

    def test_a_published_version_gets_its_own_bucket_row(self):
        observations = [
            observation(observed_at=9_900.0 + 1, published="42"),
            observation(observed_at=9_900.0 + 2, published="43"),
        ]
        trend = STORE.build_trend(observations, window_seconds=100, bucket_seconds=100, now=10_000.0)
        self.assertEqual(trend["buckets"][0]["aggregate"]["versionCount"], 2)

    def test_an_empty_window_fabricates_no_rate(self):
        trend = STORE.build_trend([], window_seconds=100, bucket_seconds=100, now=10_000.0)
        self.assertEqual(trend["buckets"][0]["aggregate"]["versionCount"], 0)
        self.assertEqual(trend["buckets"][0]["aggregate"]["acceptedObservations"], 0)


class RetentionTest(unittest.TestCase):
    def test_the_retention_cutoff_is_the_stored_timestamp_format(self):
        self.assertEqual(STORE.retention_cutoff(retention_days_value=1, now=1_700_000_000.0),
                         "2023-11-13 22:13:20")

    def test_a_non_positive_horizon_has_no_cutoff(self):
        self.assertIsNone(STORE.retention_cutoff(retention_days_value=0, now=1_700_000_000.0))

    def test_time_helpers_round_trip(self):
        self.assertEqual(STORE.text_to_epoch(STORE.epoch_to_text(1_700_000_000.0)), 1_700_000_000.0)
        self.assertIsNone(STORE.text_to_epoch(""))
        self.assertIsNone(STORE.text_to_epoch("nope"))


class PurityTest(unittest.TestCase):
    def test_the_store_imports_no_odoo_module(self):
        tree = ast.parse((CORE / "contract_slo_persistence.py").read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                imported.add(node.module.split(".")[0])
        self.assertNotIn("odoo", imported, imported)

    def test_the_store_declares_the_governed_model_and_parameters(self):
        self.assertEqual(STORE.MODEL_NAME, "sc.contract.slo.observation")
        self.assertEqual(STORE.PERSIST_PARAM, "smart_core.contract_slo.persist_enabled")
        self.assertEqual(STORE.RETENTION_PARAM, "smart_core.contract_slo.retention_days")
        self.assertEqual(STORE.DEFAULT_RETENTION_DAYS, 30)


if __name__ == "__main__":
    unittest.main()
