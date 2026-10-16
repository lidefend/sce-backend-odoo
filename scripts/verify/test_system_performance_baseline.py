"""Non-zero tests for the system performance baseline normalizer.

Every case runs against synthetic payloads; no runtime, database or network is
touched. Positive cases must reach ``status == "baseline"``; negative cases must
produce an explicit gap or fail closed instead of a zero-filled or silently
dropped result.
"""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.verify import system_performance_baseline as spb


SYSTEM_INIT = Path("addons/smart_core/handlers/system_init.py")


def _system_init_hash() -> str:
    return hashlib.sha256((spb.ROOT / SYSTEM_INIT).read_bytes()).hexdigest()


def _observation_payload(*, elapsed_ms=111.5, state="subsequent_same_process", include_timing=True):
    sample = {
        "index": 0,
        "state": state,
        "elapsed_ms": elapsed_ms,
        "sql_count": 12,
        "startup_profile": {"timings_ms": {"session_bootstrap": 9.0, "navigation": 41.0}},
    }
    if not include_timing:
        sample.pop("elapsed_ms")
    return {
        "schema": "runtime-performance-observation/v1",
        "status": "observed",
        "measurement_mode": "observe",
        "request_case": "web_startup",
        "database": "sc_dev_demo",
        "principal_xmlid": "smart_construction_demo.user_demo_role_finance",
        "handler_sha256": _system_init_hash(),
        "frontend_index_sha256": "f" * 64,
        "scope": "local_demo_backend_only",
        "limitations": ["no_http_browser_or_authentication_measurement", "no_true_cold_cache_claim"],
        "companies": [
            {
                "company_id": 1,
                "sizes": {"project.project": 3, "payment.request": 40},
                "observations": [sample],
            }
        ],
        "acceptance_pass": False,
    }


def _declared_identity():
    return {
        "deployment_identity": {"container": "sc-local-dev-odoo-1", "image_digest": "sha256:deadbeef"},
        "runtime_version": "odoo-17-test",
        "cpu_memory_limits": {"nano_cpus": 2000000000, "memory_bytes": 2147483648},
        "data_snapshot_identity": "sc_dev_demo@observed",
        "policy_revision": "local-dev-policy-1",
        "concurrency": {"mode": "serial_single_request", "value": 1},
        "background_load": "none_declared",
    }


def _write(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _entry(payload=None, path="x.log"):
    return {
        "source": {"path": path, "sha256": "0", "mtime": "2026-01-01T00:00:00+00:00"},
        "prefix": "",
        "schema": "runtime-performance-observation/v1",
        "payload": payload if payload is not None else _observation_payload(),
    }


class ExtractPayloadTests(unittest.TestCase):
    def test_extracts_prefixed_payload(self):
        payload = {"schema": "runtime-permission-probe/v1", "database": "sc_dev_demo"}
        text = "noise\nPERMISSION_PROBE_REPORT " + json.dumps(payload) + "\n"
        found = spb.extract_payloads(text)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0][0], "PERMISSION_PROBE_REPORT ")
        self.assertEqual(found[0][1], payload)

    def test_prefix_without_json_fails_closed(self):
        with self.assertRaises(ValueError):
            spb.extract_payloads("PERMISSION_PROBE_REPORT not-json\n")

    def test_prefix_with_mismatched_schema_fails_closed(self):
        text = "PERMISSION_PROBE_REPORT " + json.dumps({"schema": "runtime-cache-identity-probe/v1"})
        with self.assertRaises(ValueError):
            spb.extract_payloads(text)


class LoadInputTests(unittest.TestCase):
    def test_unknown_json_schema_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(Path(tmp) / "x.json", {"schema": "not-a-probe/v1"})
            with self.assertRaises(ValueError):
                spb.load_inputs([path])

    def test_missing_input_rejected(self):
        with self.assertRaises(FileNotFoundError):
            spb.load_inputs([Path("/tmp/definitely-missing-probe.log")])

    def test_platform_sla_report_recognized_without_schema_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(Path(tmp) / "sla.json", {"ok": True, "summary": {}, "rows": []})
            entries = spb.load_inputs([path])
            self.assertEqual(entries[0]["schema"], "platform-sla-guard/v1")


class SamplePolicyTests(unittest.TestCase):
    def test_missing_timing_is_a_gap_never_zero(self):
        normalized = spb.normalize(_entry(_observation_payload(include_timing=False)))
        sample = normalized["samples"][0]
        self.assertIsNone(sample["elapsed_ms"])
        self.assertEqual(sample["timing"]["status"], "gap")
        gaps = spb._timing_gaps([normalized])
        self.assertEqual(len(gaps), 1)
        self.assertIn("elapsed_ms", gaps[0]["field"])

    def test_nested_stage_timings_are_retained_not_summed(self):
        normalized = spb.normalize(_entry())
        stages = normalized["samples"][0]["stage_timings"]
        self.assertEqual(stages, {"session_bootstrap": 9.0, "navigation": 41.0})
        record = spb.build_record([_entry()], _declared_identity())
        self.assertTrue(record["stage_sum_forbidden"])
        self.assertNotIn("total_ms", json.dumps(record))

    def test_all_samples_retained(self):
        payload = _observation_payload()
        payload["companies"][0]["observations"] = [
            {"index": index, "state": "subsequent_same_process", "elapsed_ms": 10.0 + index, "sql_count": 1}
            for index in range(5)
        ]
        record = spb.build_record([_entry(payload)], _declared_identity())
        self.assertEqual(record["sample_policy"]["samples_observed"], 5)
        self.assertEqual(record["sample_policy"]["samples_retained"], 5)
        self.assertTrue(record["sample_policy"]["no_sample_dropped"])
        self.assertEqual(len(record["entries"][0]["samples"]), 5)

    def test_sample_accounting_mismatch_fails_closed(self):
        with patch.object(spb, "_observation_samples", return_value=(3, [])):
            with self.assertRaises(AssertionError):
                spb.normalize(_entry())

    def test_sla_rows_are_aggregate_only_with_sample_cap(self):
        payload = {
            "ok": True,
            "summary": {},
            "rows": [{"intent": "ui.contract", "iterations": 6, "p95_ms": 1234.5,
                      "max_payload_bytes": 9000, "statuses": [200],
                      "status_classification": "normal", "p95_limit": 5000.0, "payload_limit": 3500000}],
        }
        observed, samples = spb._sla_rows(payload)
        self.assertEqual(observed, 1)
        self.assertEqual(samples[0]["timing"]["status"], "aggregate_only")
        self.assertEqual(samples[0]["timing"]["sample_cap"], 6)
        self.assertEqual(samples[0]["aggregate_ms"], 1234.5)
        self.assertIsNone(samples[0]["elapsed_ms"])


class IdentityTests(unittest.TestCase):
    def test_identity_match_against_current_worktree(self):
        normalized = spb.normalize(_entry())
        self.assertEqual(normalized["identity_match"]["status"], "match")
        self.assertEqual(normalized["identity_match"]["hash_count"], 1)

    def test_stale_identity_is_flagged(self):
        payload = _observation_payload()
        payload["handler_sha256"] = "0" * 64
        normalized = spb.normalize(_entry(payload))
        self.assertEqual(normalized["identity_match"]["status"], "stale")
        self.assertEqual(len(normalized["identity_match"]["mismatches"]), 1)

    def test_missing_mandatory_identity_keeps_status_incomplete(self):
        record = spb.build_record([_entry()], {})
        self.assertEqual(record["status"], "incomplete")
        gap_fields = {gap["field"] for gap in record["identity_gaps"]}
        for field in ("deployment_identity", "runtime_version", "cpu_memory_limits",
                      "data_snapshot_identity", "concurrency", "background_load"):
            self.assertIn(field, gap_fields)
        self.assertEqual(record["layers"]["controlled_regression"]["state"], "blocked")

    def test_policy_revision_is_measured_from_governing_files(self):
        record = spb.build_record([_entry()], {})
        row = record["identity"]["policy_revision"]
        self.assertEqual(row["status"], "resolved")
        self.assertEqual(row["provenance"], "measured:budget_policy_files")
        self.assertTrue(row["value"])

    def test_complete_identity_reaches_baseline(self):
        record = spb.build_record([_entry()], _declared_identity())
        self.assertEqual(record["identity_gaps"], [])
        self.assertEqual(record["gaps"], [])
        self.assertEqual(record["status"], "baseline")
        self.assertEqual(record["layers"]["controlled_regression"]["state"], "passed")

    def test_stale_entry_is_excluded_from_controlled_regression(self):
        payload = _observation_payload()
        payload["handler_sha256"] = "1" * 64
        record = spb.build_record([_entry(payload)], _declared_identity())
        controlled = record["layers"]["controlled_regression"]
        self.assertIn("x.log", controlled["identity_stale_entries"])
        self.assertEqual(controlled["identity_matching_entries"], [])

    def test_capacity_layer_is_never_assumed_resolved(self):
        record = spb.build_record([_entry()], _declared_identity())
        self.assertEqual(record["layers"]["capacity"]["state"], "target_unresolved")
        self.assertFalse(record["layers"]["capacity"]["completed"])
        self.assertEqual(record["layers"]["daily_experience"]["state"], "not_run")

    def test_unknown_visible_scale_is_a_gap(self):
        payload = _observation_payload()
        payload["companies"][0].pop("sizes")
        record = spb.build_record([_entry(payload)], _declared_identity())
        self.assertEqual(record["identity"]["visible_scale"]["status"], "gap")


class RenderTests(unittest.TestCase):
    def test_markdown_reports_layers_and_gaps(self):
        record = spb.build_record([_entry()], {})
        markdown = spb.render_markdown(record)
        for needle in ("# System Performance Baseline", "## Identity", "## Entries",
                       "## Acceptance layers", "## Gaps", "target_unresolved"):
            self.assertIn(needle, markdown)


class CommandTests(unittest.TestCase):
    def _observe_log(self, tmp: Path) -> Path:
        path = Path(tmp) / "obs.log"
        path.write_text(
            "RUNTIME_PERFORMANCE_OBSERVATION=" + json.dumps(_observation_payload()) + "\n",
            encoding="utf-8",
        )
        return path

    def test_strict_mode_fails_when_incomplete(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "record.json"
            report = Path(tmp) / "report.md"
            code = spb.main(["--inputs", str(self._observe_log(tmp)), "--out", str(out),
                             "--report", str(report), "--strict"])
            self.assertEqual(code, 1)
            saved = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(saved["status"], "incomplete")
            self.assertTrue(report.is_file())

    def test_strict_mode_passes_with_complete_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            identity_path = _write(Path(tmp) / "identity.json", _declared_identity())
            out = Path(tmp) / "record.json"
            report = Path(tmp) / "report.md"
            code = spb.main(["--inputs", str(self._observe_log(tmp)), "--identity-file", str(identity_path),
                             "--out", str(out), "--report", str(report), "--strict"])
            self.assertEqual(code, 0)
            saved = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(saved["status"], "baseline")

    def test_missing_identity_file_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            code = spb.main(["--inputs", str(self._observe_log(tmp)),
                             "--identity-file", str(Path(tmp) / "nope.json")])
            self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
