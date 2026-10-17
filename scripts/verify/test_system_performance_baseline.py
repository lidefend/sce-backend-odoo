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

    def test_menu_config_identity_is_bound_and_mismatch_is_stale(self):
        path = "addons/smart_core/app_config_engine/models/app_nav_config.py"
        payload = _observation_payload()
        payload["menu_config_sha256"] = hashlib.sha256((spb.ROOT / path).read_bytes()).hexdigest()
        normalized = spb.normalize(_entry(payload))
        self.assertEqual(normalized["identity_match"]["status"], "match")
        self.assertEqual(normalized["identity_match"]["hash_count"], 2)
        payload["menu_config_sha256"] = "2" * 64
        stale = spb.normalize(_entry(payload))
        self.assertEqual(stale["identity_match"]["status"], "stale")
        self.assertEqual(
            {row["path"] for row in stale["identity_match"]["mismatches"]}, {path})

    def test_sla_identity_binds_system_init_and_menu_config(self):
        relative = ("handlers/system_init.py", "app_config_engine/models/app_nav_config.py")
        payload = {
            "ok": True,
            "summary": {},
            "rows": [],
            "identity": {
                item: hashlib.sha256(
                    (spb.ROOT / "addons/smart_core" / item).read_bytes()).hexdigest()
                for item in relative
            },
        }
        entry = {
            "source": {"path": "sla.json", "sha256": "0",
                       "mtime": "2026-01-01T00:00:00+00:00"},
            "prefix": "",
            "schema": "platform-sla-guard/v1",
            "payload": payload,
        }
        normalized = spb.normalize(entry)
        self.assertEqual(normalized["identity_match"]["status"], "match")
        self.assertEqual(normalized["identity_match"]["hash_count"], 2)

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
                       "## Acceptance layers", "## Gaps", "target_unresolved",
                       "## Mature-system targets"):
            self.assertIn(needle, markdown)


def _samples(label, values, *, state=None, schema_metric="elapsed_ms"):
    rows = []
    for value in values:
        row = {"label": label, "state": state, "name": None, "sql_count": None, "aggregate_ms": None}
        row[schema_metric] = value
        rows.append(row)
    return rows


def _contract_entry(samples):
    return {"schema": "runtime-contract-request-probe/v1", "samples": samples}


def _sla_entry(rows):
    samples = []
    for name, p95 in rows:
        samples.append({
            "label": None, "state": None, "name": name, "elapsed_ms": None,
            "sql_count": None, "aggregate_ms": p95,
        })
    return {"schema": "platform-sla-guard/v1", "samples": samples}


def _target_row(block, target_id):
    for row in block["targets"]:
        if row["id"] == target_id:
            return row
    raise AssertionError(f"target {target_id} not found")


class MatureSystemTargetTests(unittest.TestCase):
    def test_declaration_is_internally_consistent(self):
        self.assertEqual(spb.validate_benchmark_declaration(), [])

    def test_every_target_cites_a_published_source(self):
        for target in spb.MATURE_SYSTEM_TARGETS:
            self.assertTrue(target["sources"], target["id"])
            for source in target["sources"]:
                row = spb.BENCHMARK_SOURCES[source]
                self.assertTrue(row["url"].startswith("http"), source)
                self.assertTrue(row["statement"].strip(), source)

    def test_target_budget_matches_its_ladder_tier(self):
        ladder = {row["tier"]: row["budget_ms"] for row in spb.BENCHMARK_LADDER}
        for target in spb.MATURE_SYSTEM_TARGETS:
            self.assertEqual(target["target_ms"], ladder[target["tier"]], target["id"])

    def test_met_verdict_when_at_or_below_target(self):
        block = spb.evaluate_targets([_contract_entry(_samples("hot", [60.0] * 12))])
        row = _target_row(block, "warm_contract_dispatch")
        self.assertEqual(row["verdict"], "met")
        self.assertEqual(row["observed_ms"], 60.0)

    def test_within_tolerance_verdict_between_target_and_tolerance(self):
        block = spb.evaluate_targets([_contract_entry(_samples("hot", [150.0] * 12))])
        self.assertEqual(_target_row(block, "warm_contract_dispatch")["verdict"], "within_tolerance")

    def test_failed_verdict_beyond_tolerance(self):
        block = spb.evaluate_targets([_contract_entry(_samples("hot", [400.0] * 12))])
        self.assertEqual(_target_row(block, "warm_contract_dispatch")["verdict"], "failed")
        self.assertEqual(block["summary"]["overall"], "failed")

    def test_insufficient_samples_is_not_evaluated_and_never_zero(self):
        block = spb.evaluate_targets([_contract_entry(_samples("hot", [50.0, 55.0]))])
        row = _target_row(block, "warm_contract_dispatch")
        self.assertEqual(row["verdict"], "not_evaluated")
        self.assertIsNone(row["observed_ms"])
        self.assertIn("observed 2", row["reason"])
        self.assertFalse(block["summary"]["complete_over_comparable_targets"])

    def test_missing_observation_never_passes_and_never_claims_capacity(self):
        block = spb.evaluate_targets([])
        self.assertEqual(block["summary"]["evaluated"], 0)
        self.assertEqual(block["summary"]["overall"], "not_evaluated")
        self.assertEqual(block["summary"]["capacity"], "target_unresolved")
        self.assertTrue(all(row["verdict"] == "not_evaluated" for row in block["targets"]))

    def test_p95_is_a_nearest_rank_order_statistic_not_a_mean(self):
        values = [float(v) for v in range(10, 200, 10)] + [1000.0]
        block = spb.evaluate_targets([_contract_entry(_samples("hot", values))])
        row = _target_row(block, "warm_contract_dispatch")
        self.assertEqual(row["sample_count"], 20)
        ordered = sorted(values)
        expected_index = max(0, -(-int(0.95 * len(ordered) * 1000) // 1000) - 1)  # ceil(0.95*n)-1
        self.assertEqual(row["observed_ms"], ordered[expected_index])
        self.assertEqual(row["observed_ms"], 190.0)
        self.assertNotEqual(row["observed_ms"], sum(values) / len(values))

    def test_selector_does_not_borrow_samples_from_another_group(self):
        block = spb.evaluate_targets([_contract_entry(_samples("cold_rebuild", [900.0]))])
        self.assertEqual(_target_row(block, "warm_contract_dispatch")["verdict"], "not_evaluated")
        self.assertEqual(_target_row(block, "cold_contract_assembly")["verdict"], "met")

    def test_sla_aggregate_selector_binds_by_intent(self):
        block = spb.evaluate_targets([_sla_entry([("system.init", 626.31), ("ui.contract", 823.1)])])
        row = _target_row(block, "startup_system_init_http")
        self.assertEqual(row["verdict"], "met")
        self.assertEqual(row["observed_ms"], 626.31)

    def test_historical_gate_looseness_is_measured_from_the_governing_file(self):
        gates = spb._historical_budget_gates()
        self.assertEqual(gates["ui.contract"], 5000.0)
        self.assertEqual(gates["system.init"], 8000.0)
        block = spb.evaluate_targets([_contract_entry(_samples("hot", [60.0] * 12))])
        row = _target_row(block, "warm_contract_dispatch")
        self.assertEqual(row["historical_budget_ms"], 5000.0)
        self.assertEqual(row["historical_budget_vs_target_ratio"], 50.0)

    def test_overall_reports_the_worst_evaluated_verdict(self):
        entries = [
            _contract_entry(_samples("hot", [60.0] * 12)),
            _contract_entry(_samples("cold_rebuild", [4500.0])),
        ]
        block = spb.evaluate_targets(entries)
        self.assertEqual(_target_row(block, "warm_contract_dispatch")["verdict"], "met")
        self.assertEqual(_target_row(block, "cold_contract_assembly")["verdict"], "failed")
        self.assertEqual(block["summary"]["overall"], "failed")

    def test_invalid_declaration_fails_closed(self):
        broken = (
            {
                "id": "broken", "tier": "good_interactive", "statement": "x", "metric": "elapsed_ms",
                "aggregation": "p95", "minimum_samples": 1, "target_ms": 100, "tolerance_ms": 200,
                "sources": ("not-a-real-source",), "selector": {"sample_labels": ["hot"]},
            },
        )
        with patch.object(spb, "MATURE_SYSTEM_TARGETS", broken):
            with self.assertRaises(ValueError):
                spb.evaluate_targets([])

    def test_build_record_carries_the_target_block(self):
        record = spb.build_record([_entry()], {})
        block = record["mature_system_targets"]
        self.assertEqual(block["schema"], spb.BENCHMARK_SCHEMA)
        self.assertEqual(block["declaration_problems"], [])
        self.assertEqual(block["summary"]["target_count"], len(spb.MATURE_SYSTEM_TARGETS))


def _profile_rows(rows):
    return [
        {"file": f, "function": fn, "line": ln, "calls": calls, "cumulative_ms": cum, "self_ms": self_ms}
        for f, fn, ln, calls, cum, self_ms in rows
    ]


class FirstCallBoundaryTests(unittest.TestCase):
    def test_profile_top_is_retained_and_bounded(self):
        rows = _profile_rows([("/x/a.py", "f", 1, i, float(i), 1.0) for i in range(60)])
        sample = spb._canonical_sample({"elapsed_ms": 10.0, "cumulative_top": rows})
        self.assertEqual(len(sample["profile_top"]), spb.PROFILE_TOP_LIMIT)

    def test_absent_profile_rows_stay_absent_never_zero(self):
        sample = spb._canonical_sample({"elapsed_ms": 10.0})
        self.assertIsNone(sample["profile_top"])

    def test_one_time_marker_uses_max_cumulative_not_a_sum(self):
        profile = _profile_rows([
            ("/x/translate.py", "get_python_translations", 1, 1, 500.0, 0.1),
            ("/x/polib.py", "parse", 2, 3, 460.0, 90.0),
        ])
        sample = spb._canonical_sample({"elapsed_ms": 3800.0, "cumulative_top": profile})
        annotation = spb.one_time_process_init([sample])
        self.assertEqual(annotation["status"], "measured")
        self.assertEqual(annotation["one_time_ms"], 500.0)
        self.assertEqual(annotation["marker"], "odoo_code_translation_load")

    def test_missing_marker_is_not_declared_and_never_zero(self):
        annotation = spb.one_time_process_init([spb._canonical_sample({"elapsed_ms": 10.0})])
        self.assertEqual(annotation["status"], "not_declared")
        self.assertNotIn("one_time_ms", annotation)

    def test_first_call_target_reports_the_annotation_without_changing_the_verdict(self):
        profile = _profile_rows([("/x/translate.py", "get_python_translations", 1, 1, 522.35, 0.03)])
        sample = spb._canonical_sample(
            {"elapsed_ms": 3774.39, "variant": "cold_rebuild", "cumulative_top": profile}
        )
        entry = {"schema": "runtime-performance-observation/v1", "samples": [sample]}
        block = spb.evaluate_targets([entry])
        row = _target_row(block, "cold_contract_assembly")
        self.assertEqual(row["verdict"], "failed")
        self.assertEqual(row["observed_ms"], 3774.39)
        self.assertEqual(row["one_time_process_init"]["status"], "measured")
        self.assertEqual(row["one_time_process_init"]["one_time_ms"], 522.35)
        self.assertEqual(row["one_time_process_init"]["share_of_observed"], 0.1384)
        self.assertEqual(row["one_time_process_init"]["share_basis"], "observed_ms")
        self.assertNotIn("one_time_process_init", _target_row(block, "warm_contract_dispatch"))

    def test_profiled_samples_are_never_graded_and_never_zero(self):
        profile = _profile_rows([("/x/translate.py", "get_python_translations", 1, 1, 522.35, 0.03)])
        sample = spb._canonical_sample(
            {
                "elapsed_ms": 3774.39,
                "variant": "candidate",
                "profiled": True,
                "cumulative_top": profile,
            }
        )
        block = spb.evaluate_targets(
            [{"schema": "runtime-performance-observation/v1", "samples": [sample]}]
        )
        row = _target_row(block, "profile_first_contract_assembly")
        self.assertEqual(row["verdict"], "not_evaluated")
        self.assertIsNone(row["observed_ms"])
        self.assertFalse(row["graded"])
        self.assertIn("comparability_rule", row["reason"])
        self.assertEqual(row["profiled_values_ms"], [3774.39])
        self.assertEqual(row["profiled_basis_ms"], 3774.39)
        self.assertEqual(row["profiled_sample_count"], 1)
        self.assertEqual(row["sample_count"], 0)
        # the profiled number is still reported, and the one-time share is taken
        # against the profiled basis instead of a silent zero
        self.assertEqual(row["one_time_process_init"]["share_of_observed"], 0.1384)
        self.assertEqual(row["one_time_process_init"]["share_basis"], "profiled_basis_ms")
        self.assertIn("not_evaluated", [r["verdict"] for r in block["targets"]])

    def test_unprofiled_first_call_sample_is_graded_not_hidden(self):
        sample = spb._canonical_sample({"elapsed_ms": 1567.163, "variant": "process_first"})
        block = spb.evaluate_targets(
            [{"schema": "runtime-performance-observation/v1", "samples": [sample]}]
        )
        row = _target_row(block, "first_contract_assembly")
        self.assertTrue(row["graded"])
        self.assertEqual(row["verdict"], "within_tolerance")
        self.assertEqual(row["observed_ms"], 1567.163)
        self.assertEqual(_target_row(block, "profile_first_contract_assembly")["verdict"], "not_evaluated")

    def test_diagnostic_only_may_not_hide_an_unprofiled_measurement(self):
        broken = [
            {"id": "x", "diagnostic_only": True, "measurement_basis": "unprofiled",
             "tier": "keeps_flow", "target_ms": 1000, "tolerance_ms": 3000,
             "sources": ("salesforce-ept",), "selector": {"sample_labels": ["hot"]}},
        ]
        original = spb.MATURE_SYSTEM_TARGETS
        spb.MATURE_SYSTEM_TARGETS = tuple(broken)
        try:
            problems = spb.validate_benchmark_declaration()
        finally:
            spb.MATURE_SYSTEM_TARGETS = original
        self.assertTrue(any("diagnostic_only" in problem for problem in problems), problems)

    def test_completeness_counts_only_gradeable_targets(self):
        profiled = {"label": "candidate", "state": None, "profiled": True, "elapsed_ms": 3774.39}
        entries = [
            {"schema": "runtime-performance-observation/v1", "samples": [profiled]},
            _contract_entry(_samples("hot", [60.0] * 12)),
            _contract_entry(_samples("cold_rebuild", [200.0])),
            _contract_entry(_samples("process_first", [1567.163])),
            {"schema": "runtime-performance-observation/v1",
             "samples": [{"label": None, "state": "process_first_for_company", "elapsed_ms": 1775.73}]},
            {"schema": "runtime-performance-observation/v1",
             "samples": [{"label": None, "state": "subsequent_same_process", "elapsed_ms": 400.0}] * 3},
            _sla_entry([("system.init", 626.31)]),
        ]
        summary = spb.evaluate_targets(entries)["summary"]
        self.assertTrue(summary["complete_over_comparable_targets"])
        self.assertEqual(summary["ungradeable_by_declaration"], 1)
        self.assertEqual(summary["unevaluated_gradeable"], 0)
        self.assertEqual(summary["not_evaluated"], 1)
        # the excluded one is the declared-diagnostic target, not a hidden failure
        self.assertEqual(
            _target_row(spb.evaluate_targets(entries), "profile_first_contract_assembly")["verdict"],
            "not_evaluated",
        )
        # dropping a gradeable sample must reopen the benchmark, so the exclusion
        # can never turn an absent measurement into completeness
        without_cold = [entry for entry in entries[1:2] + entries[3:]]
        reopened = spb.evaluate_targets(without_cold)["summary"]
        self.assertFalse(reopened["complete_over_comparable_targets"])
        self.assertEqual(reopened["unevaluated_gradeable"], 1)

    def test_declared_basis_is_reported_even_with_no_sample(self):
        row = _target_row(spb.evaluate_targets([]), "warm_contract_dispatch")
        self.assertEqual(row["measurement_basis"], "unprofiled")
        self.assertIsNone(row["observed_ms"])
        self.assertNotIn("diagnostic_only", row)

    def test_profiled_basis_without_the_diagnostic_flag_is_still_not_graded(self):
        target = {
            "id": "basis_probe",
            "measurement_basis": "profiled",
            "tier": "keeps_flow",
            "statement": "probe",
            "metric": "elapsed_ms",
            "aggregation": "p95",
            "minimum_samples": 1,
            "target_ms": 1000,
            "tolerance_ms": 3000,
            "sources": ("salesforce-ept",),
            "selector": {"sample_labels": ["candidate"]},
            "rationale": "probe",
            "historical_budget_intent": None,
        }
        original = spb.MATURE_SYSTEM_TARGETS
        spb.MATURE_SYSTEM_TARGETS = (target,)
        try:
            block = spb.evaluate_targets([
                {"schema": "runtime-performance-observation/v1",
                 "samples": [{"label": "candidate", "profiled": True, "elapsed_ms": 10.0}]},
            ])
        finally:
            spb.MATURE_SYSTEM_TARGETS = original
        row = block["targets"][0]
        self.assertFalse(row["graded"])
        self.assertEqual(row["verdict"], "not_evaluated")
        self.assertIsNone(row["observed_ms"])
        self.assertEqual(row["measurement_basis"], "profiled")
        self.assertIn("profiled-basis", row["reason"])
        self.assertNotIn("diagnostic_only", row)

    def test_first_call_targets_declare_a_boundary(self):
        flagged = {t["id"] for t in spb.MATURE_SYSTEM_TARGETS if t.get("first_call_boundary")}
        self.assertEqual(
            flagged,
            {
                "profile_first_contract_assembly",
                "first_contract_assembly",
                "cold_contract_assembly",
                "startup_system_init_first",
            },
        )

    def test_profiled_capture_keeps_a_gradeable_unprofiled_counterpart(self):
        profiled = {
            t["id"] for t in spb.MATURE_SYSTEM_TARGETS if t.get("measurement_basis") == "profiled"
        }
        self.assertEqual(profiled, {"profile_first_contract_assembly"})
        # every diagnostic-only target declares the profiled basis, so no unprofiled
        # measurement can be discarded by the flag
        for target in spb.MATURE_SYSTEM_TARGETS:
            if target.get("diagnostic_only"):
                self.assertEqual(target["measurement_basis"], "profiled")

    def test_report_renders_the_first_call_boundary_section(self):
        profile = _profile_rows([("/x/translate.py", "get_python_translations", 1, 1, 522.35, 0.03)])
        sample = spb._canonical_sample(
            {
                "elapsed_ms": 3774.39,
                "variant": "candidate",
                "profiled": True,
                "cumulative_top": profile,
            }
        )
        record = spb.build_record(
            [_entry(payload={"schema": "runtime-performance-observation/v1", "samples": []})], {}
        )
        record["mature_system_targets"] = spb.evaluate_targets(
            [{"schema": "runtime-performance-observation/v1", "samples": [sample]}]
        )
        markdown = spb.render_markdown(record)
        self.assertIn("### First-call boundary", markdown)
        self.assertIn("522.35", markdown)
        self.assertIn("measured", markdown)
        self.assertIn("0.1384", markdown)
        self.assertIn("not_declared", markdown)
        self.assertIn("- (profiled 3774.39)", markdown)
        self.assertIn("profiled values ms: 3774.39", markdown)


ROLE_MATRIX_SCHEMA = "runtime-contract-role-matrix-probe/v1"


def _role_payload():
    def sample(elapsed, phase):
        return {
            "phase": phase,
            "dispatch_ms": elapsed,
            "sql_count": 23,
            "deepcopy_count": 25,
            "outcome": "dispatched",
        }

    return {
        "schema": ROLE_MATRIX_SCHEMA,
        "status": "observed",
        "acceptance_pass": False,
        "database": "sc_dev_demo",
        "identity": {
            "app_config_engine/services/assemblers/page_assembler.py": "99dddef2" + "0" * 56,
            "controllers/intent_dispatcher.py": "a1019323" + "0" * 56,
        },
        "roles": [
            {
                "label": "role_finance",
                "xmlid": "smart_construction_demo.user_demo_role_finance",
                "navigation_capability": True,
                "group_digest": "g1",
                "cases": {
                    "list_action_open": {
                        "samples": [sample(70.0, "assembly_first"), sample(66.0, "hot_1")],
                    },
                    "form_action_open": {
                        "samples": [sample(810.0, "assembly_cold_role")],
                    },
                },
            },
            {
                "label": "role_pm",
                "xmlid": "smart_construction_demo.user_demo_role_pm",
                "navigation_capability": False,
                "group_digest": "g2",
                "cases": {
                    "list_action_open": {
                        # A refused role carries an outcome and never a timing.
                        "samples": [{"phase": "hot_1", "outcome": "handler_error"}],
                    },
                },
            },
        ],
        "findings": {
            "role_count": 2,
            "navigation_capability_per_role": {"role_finance": 1, "role_pm": 0},
            "refusal_summary": {"list_action_open": {"role_pm": "handler_error"}},
            "all_refusals_are_explicit": True,
            "refused_roles_never_report_a_contract": True,
            "contract_surface_varies_by_role": True,
            "surface_digest_stable_within_dispatched_role": True,
            "relation_surface_varies_by_role": True,
        },
        "case_analysis": {
            "list_action_open": {
                "dispatched_roles": ["role_finance"],
                "unavailable_roles": [],
                "refused_roles": ["role_pm"],
                "identity_ref_count": 1,
                "surface_digest_count": 1,
                "navigation_authority_per_role": {"role_finance": 2, "role_pm": 0},
                "cold_dispatch_ms_spread": {"min": 70.0, "median": 70.0, "max": 70.0},
                "hot_dispatch_ms_per_role": {"role_finance": 66.0},
                "hot_sql_count_per_role": {"role_finance": 23},
                "surface_diff_vs_baseline": {},
            },
        },
    }


def _role_entry(payload=None):
    return {
        "source": {"path": "role-matrix.log", "sha256": "0", "mtime": "2026-01-01T00:00:00+00:00"},
        "prefix": "CONTRACT_ROLE_MATRIX_PROBE_REPORT ",
        "schema": ROLE_MATRIX_SCHEMA,
        "payload": payload if payload is not None else _role_payload(),
    }


class RoleContractVariationTests(unittest.TestCase):
    def test_every_role_case_sample_is_retained(self):
        observed, samples = spb._role_matrix_samples(_role_payload())
        self.assertEqual(observed, 4)
        self.assertEqual(len(samples), observed)
        self.assertEqual(
            {(s["role"], s["case"]) for s in samples},
            {
                ("role_finance", "list_action_open"),
                ("role_finance", "form_action_open"),
                ("role_pm", "list_action_open"),
            },
        )
        for s in samples:
            self.assertEqual(s["label"], f"{s['role']}:{s['case']}")
        finance = [s for s in samples if s["role"] == "role_finance"]
        self.assertTrue(all(s["navigation_capability"] is True for s in finance))

    def test_role_matrix_entry_normalizes_without_dropping_a_sample(self):
        entry = spb.normalize(_role_entry())
        self.assertEqual(entry["schema"], ROLE_MATRIX_SCHEMA)
        self.assertEqual(entry["samples_observed"], 4)
        self.assertEqual(entry["samples_retained"], entry["samples_observed"])

    def test_role_sample_without_timing_is_a_gap_never_zero(self):
        entry = spb.normalize(_role_entry())
        refused = [s for s in entry["samples"] if s["role"] == "role_pm"][0]
        self.assertIsNone(refused["elapsed_ms"])
        self.assertEqual(refused["timing"]["status"], "gap")
        self.assertNotEqual(refused["elapsed_ms"], 0)

    def test_role_entry_identity_hashes_bind_to_the_repository(self):
        declared = spb._product_file_hashes(_role_entry())
        self.assertEqual(len(declared), 2)
        for path in declared:
            self.assertTrue(path.startswith(spb.SMART_CORE_PREFIX), path)
            self.assertTrue(path.endswith(".py"), path)

    def test_role_variation_is_absent_without_the_role_input(self):
        self.assertIsNone(spb._role_contract_variation([_entry()]))
        record = spb.build_record([_entry()], {})
        self.assertIsNone(record["role_contract_variation"])

    def test_role_variation_requires_the_role_schema(self):
        other = dict(_role_entry())
        other["schema"] = "runtime-permission-probe/v1"
        self.assertIsNone(spb._role_contract_variation([other]))

    def test_role_variation_is_read_from_the_declared_findings(self):
        variation = spb.build_record([_role_entry()], {})["role_contract_variation"]
        self.assertEqual(variation["status"], "observed")
        self.assertEqual(variation["probe_schema"], ROLE_MATRIX_SCHEMA)
        self.assertEqual(variation["role_count"], 2)
        self.assertEqual(
            variation["navigation_capability_per_role"], {"role_finance": 1, "role_pm": 0}
        )
        self.assertEqual(
            variation["refusal_summary"], {"list_action_open": {"role_pm": "handler_error"}}
        )
        self.assertTrue(variation["all_refusals_are_explicit"])
        self.assertTrue(variation["refused_roles_never_report_a_contract"])
        self.assertTrue(variation["contract_surface_varies_by_role"])
        self.assertTrue(variation["surface_digest_stable_within_dispatched_role"])
        self.assertTrue(variation["relation_surface_varies_by_role"])
        case = variation["case_analysis"]["list_action_open"]
        self.assertEqual(case["dispatched_roles"], ["role_finance"])
        self.assertEqual(case["refused_roles"], ["role_pm"])
        self.assertEqual(case["unavailable_roles"], [])
        self.assertEqual(case["navigation_authority_per_role"], {"role_finance": 2, "role_pm": 0})
        self.assertEqual(case["hot_dispatch_ms_per_role"], {"role_finance": 66.0})

    def test_role_variation_never_invents_a_value(self):
        entry = _role_entry(payload={"schema": ROLE_MATRIX_SCHEMA, "roles": []})
        variation = spb._role_contract_variation([entry])
        self.assertEqual(variation["status"], "observed")
        self.assertIsNone(variation["role_count"])
        self.assertIsNone(variation["all_refusals_are_explicit"])
        self.assertIsNone(variation["refused_roles_never_report_a_contract"])
        self.assertIsNone(variation["contract_surface_varies_by_role"])
        self.assertEqual(variation["case_analysis"], {})

    def test_report_renders_the_role_dimension_section(self):
        record = spb.build_record([_role_entry()], {})
        markdown = spb.render_markdown(record)
        self.assertIn("## Role-dimension contract variation", markdown)
        self.assertIn("roles declared: `2`", markdown)
        self.assertIn("`list_action_open`", markdown)
        self.assertIn("role_finance=66.0", markdown)
        self.assertIn("surface digests", markdown)
        self.assertIn("surface digest stable within a dispatched role: `True`", markdown)


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
