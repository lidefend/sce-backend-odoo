"""Non-zero tests for the record-form probe's metric and semantic helpers.

The probe runs inside ``odoo shell``; these tests import only its pure helpers,
so no runtime, database or network is touched. The semantic cases are negative
tests first: a real business field change must produce a different digest, and a
transport field may be exempted only at its registered exact path.
"""
import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().with_name("local_dev_runtime_record_form_probe.py")
SPEC = importlib.util.spec_from_file_location("record_form_probe_under_test", MODULE_PATH)
PROBE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROBE)


class TestSampleStatistics(unittest.TestCase):
    def test_six_sample_median_is_the_mean_of_the_two_middle_values(self):
        samples = [664.914, 691.181, 694.289, 700.585, 705.249, 796.509]
        stats = PROBE._stats(samples)

        self.assertEqual(stats["median"], 697.437)
        self.assertNotEqual(stats["median"], samples[3])
        self.assertEqual(stats["p95"], 796.509)
        self.assertTrue(stats["p95_equals_max"])
        self.assertEqual(stats["p95_interpretation"], "window_max_observation")
        self.assertTrue(stats["window_observation_only"])

    def test_odd_sample_median_is_the_middle_value(self):
        self.assertEqual(PROBE._stats([3.0, 1.0, 2.0])["median"], 2.0)

    def test_large_sample_p95_uses_nearest_rank_not_the_maximum(self):
        stats = PROBE._stats(list(range(1, 101)))

        self.assertEqual(stats["p95"], 95.0)
        self.assertFalse(stats["p95_equals_max"])
        self.assertEqual(stats["p95_interpretation"], "nearest_rank")
        self.assertFalse(stats["window_observation_only"])

    def test_empty_sample_is_not_a_zero_filled_result(self):
        self.assertIsNone(PROBE._stats([]))


class TestSemanticComparison(unittest.TestCase):
    @staticmethod
    def _payload(deadline=1):
        return {
            "ok": True,
            "meta": {"elapsed_ms": 12, "projection_cache": {"status": "miss"}},
            "data": {
                "business": {"timing": {"deadline": deadline}},
                "meta": {
                    "traceId": "trace.request",
                    "requestId": "request.request",
                    "lifecycle": {
                        "runtime": {"requestId": "request.request", "traceId": "trace.request", "clientType": "web_pc"},
                        "integrity": {"contractSha256": "a" * 64},
                    },
                },
                "dataContract": {
                    "dataMeta": {"sourceContext": {"context": {"trace_id": "t", "request_id": "r", "lang": "zh_CN"}}},
                    "dataSource": {"primary": {"params": {"context": {"trace_id": "t", "request_id": "r", "lang": "zh_CN"}}}},
                },
                "context": {"trace_id": "t", "request_id": "r", "lang": "zh_CN"},
            },
        }

    def test_business_field_change_must_change_the_semantic_digest(self):
        before = PROBE.semantic_digest(self._payload(deadline=1))
        after = PROBE.semantic_digest(self._payload(deadline=2))

        self.assertNotEqual(
            before,
            after,
            "a real business field (data.business.timing.deadline) must never be filtered out",
        )

    def test_business_timing_is_retained_even_though_a_meta_timing_field_is_exempt(self):
        semantic = PROBE._semantic_copy(self._payload())

        self.assertEqual(semantic["data"]["business"]["timing"]["deadline"], 1)
        self.assertNotIn("elapsed_ms", semantic["meta"])
        self.assertNotIn("projection_cache", semantic["meta"])

    def test_transport_ids_are_exempt_only_at_registered_exact_paths(self):
        semantic = PROBE._semantic_copy(self._payload())

        self.assertNotIn("traceId", semantic["data"]["meta"])
        self.assertNotIn("requestId", semantic["data"]["meta"])
        self.assertEqual(semantic["data"]["meta"]["lifecycle"]["runtime"]["clientType"], "web_pc")
        self.assertNotIn("requestId", semantic["data"]["meta"]["lifecycle"]["runtime"])
        source_context = semantic["data"]["dataContract"]["dataMeta"]["sourceContext"]["context"]
        self.assertEqual(source_context, {"lang": "zh_CN"})
        primary_context = semantic["data"]["dataContract"]["dataSource"]["primary"]["params"]["context"]
        self.assertEqual(primary_context, {"lang": "zh_CN"})

        # An unregistered context container keeps its transport ids: the exemption
        # is a path registry, not a global field-name rule.
        self.assertEqual(semantic["data"]["context"]["trace_id"], "t")
        self.assertEqual(semantic["data"]["context"]["request_id"], "r")

    def test_section_digests_localise_a_business_change(self):
        before = PROBE.semantic_section_digests(self._payload(deadline=1))
        after = PROBE.semantic_section_digests(self._payload(deadline=2))

        self.assertNotEqual(before["data.business"], after["data.business"])
        self.assertEqual(before["data.meta"], after["data.meta"])
        self.assertEqual(before["meta"], after["meta"])

    def test_varying_paths_report_the_business_field_not_a_sibling_timing_key(self):
        differences = PROBE._diff_paths(self._payload(deadline=1), self._payload(deadline=2))

        self.assertEqual(differences, {("data", "business", "timing", "deadline")})


if __name__ == "__main__":
    unittest.main()
