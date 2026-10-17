#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Normalize already-produced managed performance probes into one system baseline record.

P4 owns load declaration, collection, comparison and the delivery gate
(``docs/ops/runtime_performance_baseline_v1.md``). This module is the single
normalizer: it reads managed probe payloads that were produced by the governed
``local.dev.*`` and platform entries, and emits one auditable baseline record.
It never runs a probe, never writes to the governed runtime and never invents a
value.

Fail-closed rules enforced here:

* Every mandatory identity field is either resolved **with provenance** or
  registered as an explicit gap. One gap keeps ``status`` out of ``baseline``.
* A missing timing is a gap, never ``0``.
* Nested stage timings are retained exactly as declared. The normalizer never
  sums them into an end-to-end total (``stage_sum_forbidden: true``).
* No sample is filtered, dropped or re-run. ``samples_observed`` must equal
  ``samples_retained`` or the run fails.
* An unknown probe schema is an error, not a silent skip.

It additionally declares the **mature-system benchmark targets** (the published
external bar this system is judged against) and evaluates the produced
observations against them. The declared bar is never relaxed to fit the result,
and the historical platform SLA budgets are reported beside it so the looseness
of the current gate is visible rather than argued.

A profiled sample is never graded against an absolute target: the instrumentation
inflates the measured path, so a profiled-only match is ``not_evaluated`` and its
values are reported beside the rule instead. The gradeable first-call target is
the unprofiled one, and a target declared ``diagnostic_only`` is never graded at
all: it keeps its values and its reason but produces no pass and no failure.

This is a bounded collection tool for the registered local demo environment. It
is not a browser, SLO, capacity or production acceptance by itself.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

SCHEMA = "system-performance-baseline/v1"
RECORD_JSON = ROOT / "artifacts" / "backend" / "system_performance_baseline.json"
REPORT_MD = ROOT / "docs" / "ops" / "audit" / "system_performance_baseline.md"

# Managed probe payload prefixes. The payload after the prefix is one JSON object.
TEXT_PREFIXES = (
    ("RUNTIME_PERFORMANCE_OBSERVATION=", "runtime-performance-observation/v1"),
    ("CONTRACT_REQUEST_PROBE_REPORT ", "runtime-contract-request-probe/v1"),
    ("PERMISSION_PROBE_REPORT ", "runtime-permission-probe/v1"),
    ("CACHE_IDENTITY_PROBE_REPORT ", "runtime-cache-identity-probe/v1"),
    ("CONTRACT_ROLE_MATRIX_PROBE_REPORT ", "runtime-contract-role-matrix-probe/v1"),
)
PREFIX_BY_SCHEMA = {schema: prefix for prefix, schema in TEXT_PREFIXES}

# A payload without an embedded schema is recognized by these discriminating keys.
JSON_SHAPE_SCHEMAS = (
    ("platform-sla-guard/v1", frozenset({"ok", "summary", "rows"})),
)

SUPPORTED_SCHEMAS = frozenset(
    [schema for _prefix, schema in TEXT_PREFIXES]
    + ["local-runtime-browser-observation/v1"]
    + [schema for schema, _keys in JSON_SHAPE_SCHEMAS]
)

# Probe and budget inputs whose digest is part of the mandatory identity block.
PROBE_SCRIPTS = (
    "scripts/verify/local_dev_performance_baseline.sh",
    "scripts/verify/local_dev_runtime_performance.py",
    "scripts/verify/local_dev_runtime_contract_request_probe.py",
    "scripts/verify/local_dev_runtime_permission_probe.py",
    "scripts/verify/local_dev_runtime_cache_identity_probe.py",
    "scripts/verify/local_dev_runtime_contract_role_matrix_probe.py",
    "scripts/verify/local_dev_runtime_performance_browser.mjs",
    "scripts/verify/platform_sla_guard.py",
    "scripts/verify/system_performance_baseline.py",
)
BUDGET_FILES = (
    "scripts/verify/baselines/platform_sla.json",
    "scripts/verify/baselines/platform_performance_smoke.json",
    "docs/ops/stress_regression_policy_v1.json",
    "config/frontend/release_performance_budgets_v1.json",
)

# Process-first one-time costs that are NOT per-request work of this contract
# pipeline. They are paid once per process (for any first native view read) and
# are declared so a first-call verdict is attributed instead of reinterpreted.
FIRST_CALL_ONE_TIME_MARKERS = (
    {
        "id": "odoo_code_translation_load",
        "marker_files": ("translate.py", "polib.py"),
        "note": "Odoo loads the code translation files on the first native view read; once per process and language, for any model",
    },
)

# ---------------------------------------------------------------------------
# Mature-system benchmark targets (P4 declaration, not a measured value).
# ---------------------------------------------------------------------------
# The historical platform SLA budgets above grade *this* system against its own
# past. They are not a product target: they were set far looser than the bar
# mature enterprise systems are held to. This block declares that bar explicitly
# so the comparison is auditable and machine-checked instead of asserted in
# prose. Every target must cite at least one published external reference and is
# evaluated against already-produced managed observations; a target with no
# supporting sample is `not_evaluated`, never a pass and never a zero.
BENCHMARK_SCHEMA = "mature-system-performance-targets/v1"

# A profiled sample carries cProfile instrumentation and is inflated by roughly
# 1.9x against the same unprofiled path. It stays useful for owner ranking and
# call counts, but it is never comparable to an absolute millisecond target, so
# it is never graded. A target whose selector matches profiled samples only is
# `not_evaluated` with that reason: not a pass, not a zero, and the profiled
# values are still reported in the row.
PROFILED_COMPARABILITY_RULE = (
    "profiled samples are never graded against an absolute target: cProfile inflates the "
    "measured path (~1.9x observed), so only unprofiled samples are compared; a profiled-only "
    "match is not_evaluated and keeps its values in profiled_values_ms"
)

# A declared measurement basis says which capture a target may be judged from. Only
# the unprofiled capture can answer an absolute millisecond target, so a target whose
# basis is `profiled` is reported, never graded. `diagnostic_only` makes that explicit
# and is validated below: it may not be used to silence an unprofiled measurement that
# could otherwise be graded.
MEASUREMENT_BASES = ("unprofiled", "profiled")

DIAGNOSTIC_ONLY_REASON = (
    "diagnostic-only target: retained for owner ranking and one-time share attribution, never "
    "graded against an absolute target; see comparability_rule and profiled_values_ms"
)

PROFILED_BASIS_REASON = (
    "profiled-basis target: its declared capture is cProfile-instrumented, so it is reported and never "
    "graded; see comparability_rule and profiled_values_ms"
)

# Named external references. `statement` is the published bar, not our history.
BENCHMARK_SOURCES = {
    "chrome-rail": {
        "publisher": "Google Chrome",
        "title": "Measure performance with the RAIL model",
        "url": "https://web.dev/articles/rail",
        "statement": "respond to user input within 0-100 ms for the result to feel instantaneous",
    },
    "web.dev-inp": {
        "publisher": "Google web.dev",
        "title": "Interaction to Next Paint (INP)",
        "url": "https://web.dev/articles/inp",
        "statement": "INP at or below 200 ms at the 75th percentile of page loads is good responsiveness",
    },
    "nng-response-times": {
        "publisher": "Nielsen Norman Group",
        "title": "Response Times: The 3 Important Limits",
        "url": "https://www.nngroup.com/articles/response-times-3-important-limits/",
        "statement": "0.1 s feels instantaneous, 1.0 s keeps the flow of thought, 10 s is the attention limit",
    },
    "salesforce-ept": {
        "publisher": "Salesforce Help",
        "title": "Optimize Lightning Experience Performance",
        "url": "https://help.salesforce.com/s/articleView?id=000390330&language=en_US&type=1",
        "statement": "a healthy Experience Page Time is typically under 3 seconds",
    },
    "sap-fiori-timing": {
        "publisher": "SAP Fiori Design Guidelines",
        "title": "Interaction - Timing",
        "url": "https://www.sap.com/design-system/fiori-design-web/v1-142/foundations/interaction/timing",
        "statement": "response time 1-3 s; delays over 3 s disrupt user flow",
    },
    "sap-earlywatch-odata": {
        "publisher": "SAP Community (SAP EarlyWatch Alert)",
        "title": "Evaluating Performance with SAP EarlyWatch Alert",
        "url": "https://community.sap.com/t5/technology-blog-posts-by-sap/evaluating-performance-with-sap-earlywatch-alert/ba-p/13448062",
        "statement": "one second for a standard app and three seconds for a complex one",
    },
    "web.dev-ttfb": {
        "publisher": "Google web.dev",
        "title": "Time to First Byte (TTFB)",
        "url": "https://web.dev/articles/ttfb",
        "statement": "TTFB at or below 800 ms is good; 800-1800 ms needs improvement; above 1800 ms is poor",
    },
    "web.dev-lcp": {
        "publisher": "Google web.dev",
        "title": "Largest Contentful Paint (LCP)",
        "url": "https://web.dev/articles/lcp",
        "statement": "a good LCP is 2.5 seconds or less; over 4.0 seconds is poor",
    },
}

# The ladder is the ordered set of published bars the targets select from. It is
# declared once so no target can invent a threshold locally.
BENCHMARK_LADDER = (
    {"tier": "instant_interaction", "budget_ms": 100, "source": "chrome-rail"},
    {"tier": "good_interactive", "budget_ms": 200, "source": "web.dev-inp"},
    {"tier": "good_ttfb", "budget_ms": 800, "source": "web.dev-ttfb"},
    {"tier": "keeps_flow", "budget_ms": 1000, "source": "nng-response-times"},
    {"tier": "standard_app", "budget_ms": 1000, "source": "sap-fiori-timing"},
    {"tier": "good_lcp", "budget_ms": 2500, "source": "web.dev-lcp"},
    {"tier": "healthy_page", "budget_ms": 3000, "source": "salesforce-ept"},
)

# One target = one observed operation, one metric, one aggregation and the
# published bar it is judged against. `selector` binds the target to samples the
# managed probes actually emit; an unmatched selector is `not_evaluated`.
#
# `historical_budget_intent` (optional) names the platform SLA budget the same
# operation is currently graded by, so the looseness of that gate is recorded
# rather than argued.
MATURE_SYSTEM_TARGETS = (
    {
        "id": "warm_contract_dispatch",
        "tier": "instant_interaction",
        "statement": "warm-process server dispatch of one repeated ui.contract action",
        "metric": "elapsed_ms",
        "aggregation": "p95",
        "minimum_samples": 5,
        "target_ms": 100,
        "tolerance_ms": 200,
        "sources": ("chrome-rail", "web.dev-inp", "nng-response-times"),
        "selector": {"sample_labels": ["hot", "hot_gc_off"]},
        "historical_budget_intent": "ui.contract",
        "rationale": (
            "server-side share of an interaction that must still fit inside the 0-100 ms "
            "perceived-instant window; the rest of that window is reserved for transport and paint"
        ),
    },
    {
        "id": "cold_contract_assembly",
        "first_call_boundary": True,
        "tier": "keeps_flow",
        "statement": "cold-cache first assembly of one ui.contract action",
        "metric": "elapsed_ms",
        "aggregation": "max",
        "minimum_samples": 1,
        "target_ms": 1000,
        "tolerance_ms": 3000,
        "sources": ("nng-response-times", "sap-earlywatch-odata", "salesforce-ept"),
        "selector": {"sample_labels": ["cold_rebuild"]},
        "historical_budget_intent": "ui.contract",
        "rationale": "keeps the flow of thought at 1 s; 3 s is the healthy-page ceiling",
    },
    {
        "id": "profile_first_contract_assembly",
        "first_call_boundary": True,
        "diagnostic_only": True,
        "measurement_basis": "profiled",
        "tier": "keeps_flow",
        "statement": "first ui.contract assembly observed by the contract-profile capture (cProfile-instrumented)",
        "metric": "elapsed_ms",
        "aggregation": "first",
        "minimum_samples": 1,
        "target_ms": 1000,
        "tolerance_ms": 3000,
        "sources": ("nng-response-times", "sap-earlywatch-odata", "salesforce-ept"),
        "selector": {"sample_labels": ["candidate"]},
        "historical_budget_intent": "ui.contract",
        "rationale": (
            "the first sample of the profile capture is the cold one; later samples are repeats. It is "
            "retained for owner ranking and one-time-share attribution only, because the instrumentation "
            "inflates the path and cannot be graded against an absolute millisecond target; the gradeable "
            "first-call target is first_contract_assembly"
        ),
    },
    {
        "id": "first_contract_assembly",
        "first_call_boundary": True,
        "measurement_basis": "unprofiled",
        "tier": "keeps_flow",
        "statement": "process-first ui.contract assembly, unprofiled",
        "metric": "elapsed_ms",
        "aggregation": "first",
        "minimum_samples": 1,
        "target_ms": 1000,
        "tolerance_ms": 3000,
        "sources": ("nng-response-times", "sap-earlywatch-odata", "salesforce-ept"),
        "selector": {"sample_labels": ["process_first"]},
        "historical_budget_intent": "ui.contract",
        "rationale": (
            "the same keeps-flow question as the profiled capture, answered on the unprofiled process-first "
            "sample so the verdict is comparable to the published absolute target"
        ),
    },
    {
        "id": "startup_system_init_first",
        "first_call_boundary": True,
        "tier": "good_ttfb",
        "statement": "process-first system.init server work for a company",
        "metric": "elapsed_ms",
        "aggregation": "first",
        "minimum_samples": 1,
        "target_ms": 800,
        "tolerance_ms": 3000,
        "sources": ("web.dev-ttfb", "salesforce-ept"),
        "selector": {"sample_states": ["process_first_for_company"]},
        "historical_budget_intent": "system.init",
        "rationale": "server response inside the good-TTFB window, with the page ceiling as tolerance",
    },
    {
        "id": "startup_system_init_http",
        "tier": "good_ttfb",
        "statement": "system.init HTTP p95 across the three-layer collector",
        "metric": "aggregate_ms",
        "aggregation": "p95",
        "minimum_samples": 1,
        "target_ms": 800,
        "tolerance_ms": 3000,
        "sources": ("web.dev-ttfb", "salesforce-ept"),
        "selector": {"sla_intents": ["system.init"]},
        "historical_budget_intent": "system.init",
        "rationale": "collector-declared aggregate p95; the sample cap is the collector iteration count",
    },
    {
        "id": "warm_startup_repeat",
        "tier": "keeps_flow",
        "statement": "warm-process repeated system.init for the same company",
        "metric": "elapsed_ms",
        "aggregation": "p95",
        "minimum_samples": 3,
        "target_ms": 1000,
        "tolerance_ms": 3000,
        "sources": ("nng-response-times", "sap-fiori-timing"),
        "selector": {"sample_states": ["subsequent_same_process"]},
        "historical_budget_intent": "system.init",
        "rationale": "re-entering a page after the first call should keep the flow of thought",
    },
)

MANDATORY_IDENTITY = (
    "source_code_identity",
    "target_code_identity",
    "deployment_identity",
    "frontend_artifact_digest",
    "probe_and_budget_digest",
    "observed_at",
    "runtime_version",
    "cpu_memory_limits",
    "database",
    "data_snapshot_identity",
    "visible_scale",
    "tenant_company_role_scope",
    "policy_revision",
    "concurrency",
    "background_load",
    "cold_warm_state",
    "operation_boundary",
)

# Payload hash key -> product file, for entries that declare a single handler hash.
IDENTITY_HASH_FILES = {
    "handler_sha256": "addons/smart_core/handlers/system_init.py",
    "contract_handler_sha256": "addons/smart_core/handlers/ui_contract_v2.py",
    "preference_handler_sha256": "addons/smart_core/handlers/user_view_preference.py",
}
# Payload projection-owner key -> product file.
IDENTITY_OWNER_FILES = {
    "UI": "addons/smart_core/handlers/ui_contract.py",
    "ASSEMBLER": "addons/smart_core/app_config_engine/services/assemblers/page_assembler.py",
    "DISPATCHER": "addons/smart_core/app_config_engine/services/dispatchers/action_dispatcher.py",
}
SMART_CORE_PREFIX = "addons/smart_core/"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str | None:
    try:
        return _sha256_bytes(path.read_bytes())
    except OSError:
        return None


def _number(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _int_or_none(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def extract_payloads(text: str) -> list[tuple[str, dict]]:
    """Return ``(prefix, payload)`` for every managed probe payload in ``text``."""
    found: list[tuple[str, dict]] = []
    for prefix, schema in TEXT_PREFIXES:
        start = 0
        while True:
            index = text.find(prefix, start)
            if index < 0:
                break
            body = text[index + len(prefix):]
            line = body.splitlines()[0] if body else ""
            payload: dict | None = None
            try:
                loaded = json.loads(line)
                if isinstance(loaded, dict):
                    payload = loaded
            except ValueError:
                try:
                    loaded, _end = json.JSONDecoder().raw_decode(body.lstrip())
                    if isinstance(loaded, dict):
                        payload = loaded
                except ValueError:
                    payload = None
            if payload is None:
                raise ValueError(f"prefix {prefix!r} at offset {index} is not followed by a JSON object")
            declared = payload.get("schema")
            if declared and declared != schema:
                raise ValueError(f"prefix {prefix!r} declares unexpected schema {declared!r}")
            found.append((prefix, payload))
            start = index + len(prefix) + max(len(line), 1)
    return found


def _classify_json(payload: dict) -> str:
    declared = payload.get("schema")
    if isinstance(declared, str) and declared in SUPPORTED_SCHEMAS:
        return declared
    keys = set(payload)
    for schema, required in JSON_SHAPE_SCHEMAS:
        if required <= keys:
            return schema
    raise ValueError(f"unrecognized payload schema: {declared!r}")


def load_inputs(paths: list[Path]) -> list[dict]:
    """Load every supported payload from the given files as ``{source, schema, payload}``."""
    entries: list[dict] = []
    for path in paths:
        path = Path(path).resolve()
        try:
            source_path = str(path.relative_to(ROOT))
        except ValueError:
            source_path = str(path)
        if not path.is_file():
            raise FileNotFoundError(f"performance baseline input missing: {path}")
        digest = _sha256_file(path)
        text = path.read_text(encoding="utf-8", errors="replace")
        payloads: list[tuple[str, dict]] = []
        if path.suffix == ".json":
            try:
                loaded = json.loads(text)
            except ValueError:
                loaded = None
            if isinstance(loaded, dict):
                try:
                    payloads = [(PREFIX_BY_SCHEMA.get(_classify_json(loaded), ""), loaded)]
                except ValueError:
                    payloads = []
        if not payloads:
            payloads = extract_payloads(text)
        if not payloads:
            raise ValueError(f"no managed probe payload found in {path}")
        for prefix, payload in payloads:
            entries.append(
                {
                    "source": {
                        "path": source_path,
                        "sha256": digest,
                        "mtime": datetime.fromtimestamp(os.path.getmtime(path), timezone.utc).isoformat(),
                    },
                    "prefix": prefix,
                    "schema": _classify_json(payload),
                    "payload": payload,
                }
            )
    return entries


def _stage_timings(row: dict) -> dict:
    stages: dict = {}
    profile = row.get("startup_profile")
    if isinstance(profile, dict) and isinstance(profile.get("timings_ms"), dict):
        stages.update(profile["timings_ms"])
    for key, value in row.items():
        if not isinstance(key, str) or not key.endswith("_ms") or key == "elapsed_ms":
            continue
        if isinstance(value, dict):
            stages.setdefault(key, value)
        elif _number(value) is not None:
            stages.setdefault(key, value)
    return stages


PROFILE_TOP_LIMIT = 40


def _profile_top(row: dict) -> list[dict] | None:
    """Retain a bounded cProfile top list so first-call cost stays auditable.

    Only the declared top rows are kept; nothing is summed and nothing is
    re-derived. Absent profile rows stay absent, never zero.
    """
    rows = row.get("cumulative_top")
    if not isinstance(rows, list):
        return None
    retained: list[dict] = []
    for entry in rows[:PROFILE_TOP_LIMIT]:
        if not isinstance(entry, dict):
            continue
        cumulative = _number(entry.get("cumulative_ms"))
        if cumulative is None:
            continue
        retained.append(
            {
                "file": entry.get("file"),
                "function": entry.get("function"),
                "line": _int_or_none(entry.get("line")),
                "calls": _int_or_none(entry.get("calls")),
                "cumulative_ms": cumulative,
                "self_ms": _number(entry.get("self_ms")),
            }
        )
    return retained or None


def _canonical_sample(row: dict, **extra) -> dict:
    elapsed = _number(row.get("elapsed_ms"))
    if elapsed is None:
        elapsed = _number(row.get("dispatch_ms"))
    state = row.get("state") or row.get("phase")
    sample = {
        "company_id": extra.get("company_id"),
        "name": extra.get("name"),
        "state": state if isinstance(state, str) else None,
        "label": row.get("variant") or row.get("group") or extra.get("label"),
        "profiled": bool(row.get("profiled")) if "profiled" in row else None,
        "request_count": _int_or_none(row.get("request_count")),
        "elapsed_ms": elapsed,
        "sql_count": _int_or_none(row.get("sql_count")),
        "deepcopy_count": _int_or_none(row.get("deepcopy_count")),
        "response_bytes": _int_or_none(row.get("response_bytes")) or _int_or_none(row.get("payload_bytes")),
        "status": row.get("status"),
        "stage_timings": _stage_timings(row) or None,
        "profile_top": _profile_top(row),
    }
    sample["timing"] = (
        {"status": "resolved", "provenance": "declared_elapsed_ms"}
        if elapsed is not None
        else {"status": "gap", "reason": "declared sample carries no elapsed timing"}
    )
    for key, value in extra.items():
        if key not in sample:
            sample[key] = value
    return sample


def _observation_samples(payload: dict) -> tuple[int, list[dict]]:
    observed = 0
    samples: list[dict] = []
    for company in payload.get("companies") or []:
        if not isinstance(company, dict):
            continue
        raw = company.get("observations")
        if not isinstance(raw, list):
            raw = company.get("samples") if isinstance(company.get("samples"), list) else []
        for row in raw:
            if not isinstance(row, dict):
                continue
            observed += 1
            samples.append(_canonical_sample(row, company_id=company.get("company_id")))
    return observed, samples


def _contract_request_samples(payload: dict) -> tuple[int, list[dict]]:
    observed = 0
    samples: list[dict] = []
    grouped = payload.get("samples")
    if isinstance(grouped, dict):
        for group, rows in grouped.items():
            if not isinstance(rows, list):
                continue
            for row in rows:
                if not isinstance(row, dict):
                    continue
                observed += 1
                samples.append(_canonical_sample(row, label=group))
    return observed, samples


def _role_matrix_samples(payload: dict) -> tuple[int, list[dict]]:
    """Retain every per-role, per-case sample so the role dimension is counted.

    Each role/case pair is flattened with its own label; the accounting must
    still balance, so a sample can never be dropped to make a role look cheap.
    """
    observed = 0
    samples: list[dict] = []
    for role in payload.get("roles") or []:
        if not isinstance(role, dict):
            continue
        label = str(role.get("label") or role.get("xmlid") or "")
        cases = role.get("cases")
        if not isinstance(cases, dict):
            continue
        for case_id, case in cases.items():
            if not isinstance(case, dict):
                continue
            for row in case.get("samples") or []:
                if not isinstance(row, dict):
                    continue
                observed += 1
                samples.append(
                    _canonical_sample(
                        row,
                        label="%s:%s" % (label, case_id),
                        role=label,
                        case=case_id,
                        navigation_capability=role.get("navigation_capability"),
                        group_digest=role.get("group_digest"),
                    )
                )
    return observed, samples


def _browser_samples(payload: dict) -> tuple[int, list[dict]]:
    observed = 0
    samples: list[dict] = []
    raw_login = payload.get("login_samples")
    if isinstance(raw_login, list):
        for row in raw_login:
            if isinstance(row, dict):
                observed += 1
                samples.append(_canonical_sample(row, name="login_sample"))
    for name in ("company_switch", "chain", "relation_dialog"):
        node = payload.get(name)
        if isinstance(node, dict):
            observed += 1
            row = dict(node)
            if name == "relation_dialog" and isinstance(row.get("request_chain"), dict):
                chain = row["request_chain"]
                row.setdefault("elapsed_ms", chain.get("total_automation_ms"))
            samples.append(_canonical_sample(row, name=name))
    return observed, samples


def _sla_rows(payload: dict) -> tuple[int, list[dict]]:
    observed = 0
    samples: list[dict] = []
    for row in payload.get("rows") or []:
        if not isinstance(row, dict):
            continue
        observed += 1
        sample = _canonical_sample({"status": row.get("status_classification")})
        p95 = _number(row.get("p95_ms"))
        sample.update(
            {
                "name": row.get("intent"),
                "request_count": _int_or_none(row.get("iterations")),
                "aggregate_ms": p95,
                "response_bytes": _int_or_none(row.get("max_payload_bytes")),
                "statuses": row.get("statuses"),
                "p95_limit_ms": _number(row.get("p95_limit")),
                "payload_limit_bytes": _int_or_none(row.get("payload_limit")),
                "timing": (
                    {
                        "status": "aggregate_only",
                        "provenance": "collector_declared_p95",
                        "sample_cap": _int_or_none(row.get("iterations")),
                    }
                    if p95 is not None
                    else {"status": "gap", "reason": "aggregate row carries no p95 timing"}
                ),
            }
        )
        samples.append(sample)
    return observed, samples


def _attribution_stage_timings(payload: dict) -> dict:
    stages: dict = {}
    for key in ("phases_ms", "import_ms", "gate", "warm"):
        value = payload.get(key)
        if isinstance(value, dict):
            stages[key] = value
    return stages


def _product_file_hashes(entry: dict) -> dict:
    """Map every declared product-code hash onto its repository path."""
    payload = entry["payload"]
    declared: dict[str, str] = {}
    for key, relative in IDENTITY_HASH_FILES.items():
        value = payload.get(key)
        if isinstance(value, str) and value:
            declared[relative] = value
    owners = payload.get("projection_owner_hashes")
    if isinstance(owners, dict):
        for key, relative in IDENTITY_OWNER_FILES.items():
            value = owners.get(key)
            if isinstance(value, str) and value:
                declared[relative] = value
    if entry["schema"] == "local-runtime-browser-observation/v1":
        declared.clear()
        for relative, value in (payload.get("backend_hashes") or {}).items():
            if isinstance(relative, str) and isinstance(value, str):
                declared[SMART_CORE_PREFIX + relative] = value
    if entry["schema"] in {
        "runtime-contract-request-probe/v1",
        "runtime-permission-probe/v1",
        "runtime-contract-role-matrix-probe/v1",
    }:
        declared.clear()
        for relative, value in (payload.get("identity") or {}).items():
            if isinstance(relative, str) and isinstance(value, str) and relative.endswith(".py"):
                declared[SMART_CORE_PREFIX + relative] = value
    return declared


def _identity_match(entry: dict) -> dict:
    declared = _product_file_hashes(entry)
    if not declared:
        return {"status": "unknown", "reason": "entry declares no product-code hash", "mismatches": []}
    mismatches = []
    for relative, digest in sorted(declared.items()):
        current = _sha256_file(ROOT / relative)
        if current is None or current != digest:
            mismatches.append({"path": relative, "declared": digest, "current": current})
    declared_head = entry["payload"].get("head")
    head_note = None
    if isinstance(declared_head, str) and declared_head:
        try:
            head_note = subprocess.run(
                ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                capture_output=True, text=True, check=True,
            ).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            head_note = None
        if head_note and head_note != declared_head:
            mismatches.append({"path": "<git HEAD>", "declared": declared_head, "current": head_note})
    return {
        "status": "match" if not mismatches else "stale",
        "reason": None if not mismatches else "declared product identity differs from the current worktree",
        "hash_count": len(declared),
        "mismatches": mismatches,
    }


def normalize(entry: dict) -> dict:
    """Normalize one loaded payload into a baseline entry."""
    payload = entry["payload"]
    schema = entry["schema"]
    if schema in {"runtime-performance-observation/v1"}:
        observed, samples = _observation_samples(payload)
        stages = {}
        note = None
    elif schema == "runtime-contract-request-probe/v1":
        observed, samples = _contract_request_samples(payload)
        stages = {}
        note = "stage maps are declared nested and are never summed"
    elif schema == "runtime-permission-probe/v1":
        observed, samples = 0, []
        stages = _attribution_stage_timings(payload)
        note = "attribution probe: no per-request latency samples, nested phase maps only"
    elif schema == "runtime-cache-identity-probe/v1":
        observed, samples = 0, []
        stages = {}
        note = "identity probe: verdict evidence only, no timing claim"
    elif schema == "runtime-contract-role-matrix-probe/v1":
        observed, samples = _role_matrix_samples(payload)
        stages = {}
        note = (
            "role-dimension probe: each role/case sample is retained; nested stage maps "
            "stay declared and are never summed"
        )
    elif schema == "local-runtime-browser-observation/v1":
        observed, samples = _browser_samples(payload)
        stages = {}
        note = "browser observation; asset scope is index-referenced JS/CSS only"
    elif schema == "platform-sla-guard/v1":
        observed, samples = _sla_rows(payload)
        stages = {}
        note = "HTTP three-layer collector: aggregate p95 and payload bytes only, no server stages"
    else:
        raise ValueError(f"unsupported probe schema for normalization: {schema!r}")

    company_ids = [
        company.get("company_id")
        for company in payload.get("companies") or []
        if isinstance(company, dict) and company.get("company_id") is not None
    ]
    visible_scale: dict = {}
    for company in payload.get("companies") or []:
        if not isinstance(company, dict):
            continue
        counts = company.get("visible_record_counts") or company.get("sizes")
        if isinstance(counts, dict):
            visible_scale[str(company.get("company_id"))] = counts

    retained = len(samples)
    if retained != observed:
        raise AssertionError(
            f"sample accounting mismatch for {entry['source']['path']}: "
            f"observed={observed} retained={retained}"
        )
    limitations = payload.get("limitations")
    if not isinstance(limitations, list):
        single = payload.get("limitation")
        limitations = [single] if isinstance(single, str) and single else []
    return {
        "source": entry["source"],
        "schema": schema,
        "prefix": entry["prefix"],
        "measurement_mode": payload.get("measurement_mode"),
        "request_case": payload.get("request_case"),
        "request_params": payload.get("request_params"),
        "operation": payload.get("operation"),
        "scope": payload.get("scope"),
        "status": payload.get("status"),
        "acceptance_pass": payload.get("acceptance_pass"),
        "database": payload.get("database"),
        "principal": payload.get("principal") or payload.get("principal_xmlid"),
        "observed_at": payload.get("observed_at"),
        "frontend_index_sha256": payload.get("frontend_index_sha256"),
        "limitations": limitations,
        "product_file_hashes": _product_file_hashes(entry),
        "identity_match": _identity_match(entry),
        "samples_observed": observed,
        "samples_retained": retained,
        "samples": samples,
        "company_ids": company_ids or None,
        "visible_scale": visible_scale or None,
        "stage_timings": stages or None,
        "declared_stats": payload.get("stats") or None,
        "declared_conclusions": payload.get("verdict") or payload.get("findings") or None,
        "sample_note": note,
    }


def _visible_scale(entries: list[dict]) -> dict | None:
    scale: dict = {}
    for entry in entries:
        for company_id, counts in (entry["visible_scale"] or {}).items():
            scale.setdefault(company_id, {}).update(counts)
    return scale or None


def _scope_facts(entries: list[dict]) -> dict | None:
    facts: dict = {}
    for entry in entries:
        principal = entry["principal"]
        if isinstance(principal, dict):
            facts.setdefault("principals", []).append(principal)
        elif isinstance(principal, str):
            facts.setdefault("principals", []).append({"xmlid": principal})
        database = entry["database"]
        if isinstance(database, str) and database:
            facts.setdefault("databases", [])
            if database not in facts["databases"]:
                facts["databases"].append(database)
        for company_id in entry["company_ids"] or []:
            facts.setdefault("company_ids", [])
            if company_id not in facts["company_ids"]:
                facts["company_ids"].append(company_id)
    return facts or None


def _cold_warm_state(entries: list[dict]) -> dict | None:
    states: dict[str, str] = {}
    declared: dict[str, str] = {}
    for entry in entries:
        for sample in entry["samples"]:
            state = sample.get("state")
            if not isinstance(state, str) or not state:
                continue
            lowered = state.lower()
            if any(token in lowered for token in ("first", "cold")):
                states[state] = "cold"
            elif any(token in lowered for token in ("subsequent", "warm", "hot")):
                states[state] = "warm"
            else:
                states[state] = "unclassified"
        if states:
            continue
        joined = " ".join(str(item) for item in entry["limitations"])
        if "no_true_cold_cache_claim" in joined:
            declared[entry["source"]["path"]] = "warm_only_no_true_cold_claim"
    result: dict = {}
    if states:
        result["from_samples"] = states
    if declared:
        result["entry_declarations"] = declared
    return result or None


def _operation_boundaries(entries: list[dict]) -> list[dict]:
    boundaries = []
    for entry in entries:
        boundaries.append(
            {
                "source": entry["source"]["path"],
                "probe_schema": entry["schema"],
                "measurement_mode": entry["measurement_mode"],
                "request_case": entry["request_case"],
                "operation": entry["operation"],
                "scope": entry["scope"],
                "limitations": entry["limitations"],
            }
        )
    return boundaries


def _digest_paths(paths: tuple[str, ...]) -> dict:
    files = {}
    for relative in paths:
        digest = _sha256_file(ROOT / relative)
        files[relative] = digest
    combined = _sha256_bytes(
        json.dumps(files, sort_keys=True).encode("utf-8")
    )
    return {"digest": combined, "files": files}


def _policy_revisions() -> dict:
    """Semantic revision of each governing budget/threshold policy file."""
    revisions: dict = {}
    for relative in BUDGET_FILES:
        path = ROOT / relative
        if not path.is_file():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if not isinstance(payload, dict):
            continue
        for key in ("version", "schema_version"):
            value = payload.get(key)
            if isinstance(value, str) and value:
                revisions[relative] = value
                break
    return revisions


def resolve_identity(entries: list[dict], declared: dict) -> dict:
    """Resolve every mandatory identity field or register it as an explicit gap."""
    declared = declared if isinstance(declared, dict) else {}
    fields: dict[str, dict] = {}
    gaps: list[dict] = []

    def put(field: str, value: object, provenance: str) -> None:
        if value in (None, {}, []):
            fields[field] = {"status": "gap", "reason": "not resolvable from the given inputs"}
            gaps.append({"field": field, "reason": "not resolvable from the given inputs"})
            return
        fields[field] = {"status": "resolved", "value": value, "provenance": provenance}

    def put_declared(field: str, key: str | None = None, reason: str = "") -> bool:
        key = key or field
        value = declared.get(key)
        if value in (None, {}, []):
            fields[field] = {"status": "gap", "reason": reason or f"not declared by the runner under {key!r}"}
            gaps.append({"field": field, "reason": fields[field]["reason"]})
            return False
        fields[field] = {"status": "resolved", "value": value, "provenance": f"declared:{key}"}
        return True

    source_hashes = {
        entry["source"]["path"]: entry["product_file_hashes"]
        for entry in entries
        if entry["product_file_hashes"]
    }
    put("source_code_identity", source_hashes, "measured:probe_declared_product_hashes")

    head = None
    dirty = None
    try:
        head = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        dirty = bool(subprocess.run(
            ["git", "-C", str(ROOT), "status", "--porcelain"],
            capture_output=True, text=True, check=True,
        ).stdout.strip())
    except (OSError, subprocess.CalledProcessError):
        head = None
    put("target_code_identity", {"head": head, "dirty": dirty} if head else None, "measured:git_at_record_time")

    put_declared("deployment_identity")

    frontend = None
    for entry in entries:
        digest = entry["frontend_index_sha256"]
        if isinstance(digest, str) and digest:
            frontend = {"frontend_index_sha256": digest, "source": entry["source"]["path"]}
            break
    if frontend is None and declared.get("frontend_artifact_digest"):
        frontend = declared["frontend_artifact_digest"]
    put("frontend_artifact_digest", frontend, "measured:browser_served_index")

    put(
        "probe_and_budget_digest",
        {"probes": _digest_paths(PROBE_SCRIPTS), "budgets": _digest_paths(BUDGET_FILES)},
        "measured:repository_files",
    )

    observed = sorted(
        value for value in (entry["observed_at"] for entry in entries) if isinstance(value, str) and value
    )
    if observed:
        put("observed_at", observed[-1], "declared:probe_observed_at")
    else:
        mtimes = sorted(
            value for value in (entry["source"].get("mtime") for entry in entries) if isinstance(value, str) and value
        )
        put("observed_at", mtimes[-1] if mtimes else None, "measured:input_file_mtime")

    put_declared("runtime_version")
    put_declared("cpu_memory_limits")

    databases = sorted({entry["database"] for entry in entries if isinstance(entry["database"], str) and entry["database"]})
    put("database", databases, "declared:probe_database")

    put_declared("data_snapshot_identity")
    visible = _visible_scale(entries)
    if visible is None and declared.get("visible_scale") not in (None, {}, []):
        visible = {"declared": declared["visible_scale"]}
    put("visible_scale", visible, "measured:probe_visible_record_counts")
    put("tenant_company_role_scope", _scope_facts(entries), "measured:probe_principal_and_companies")
    if declared.get("policy_revision") not in (None, {}, []):
        put("policy_revision", declared["policy_revision"], "declared:policy_revision")
    else:
        put("policy_revision", _policy_revisions(), "measured:budget_policy_files")
    put_declared("concurrency")
    put_declared("background_load")
    put("cold_warm_state", _cold_warm_state(entries), "derived:probe_sample_state")
    put("operation_boundary", _operation_boundaries(entries), "declared:probe_scope_and_limitations")

    return {"fields": fields, "gaps": gaps, "declared_inputs": sorted(declared)}


def _timing_gaps(entries: list[dict]) -> list[dict]:
    gaps = []
    for entry in entries:
        for index, sample in enumerate(entry["samples"]):
            if sample["timing"]["status"] == "gap":
                gaps.append(
                    {
                        "field": f"{entry['source']['path']}#sample[{index}].elapsed_ms",
                        "reason": sample["timing"]["reason"],
                    }
                )
    return gaps


def _controlled_regression(entries: list[dict], identity: dict) -> dict:
    matching = [entry for entry in entries if entry["identity_match"]["status"] == "match"]
    stale = [entry["source"]["path"] for entry in entries if entry["identity_match"]["status"] == "stale"]
    unknown = [entry["source"]["path"] for entry in entries if entry["identity_match"]["status"] == "unknown"]
    timed = [entry for entry in matching if any(
        sample["timing"]["status"] in {"resolved", "aggregate_only"} for sample in entry["samples"]
    )]
    reasons = []
    if not timed:
        reasons.append("no identity-matching entry carries a timing sample")
    if identity["gaps"]:
        reasons.append("identity block is incomplete: " + ", ".join(gap["field"] for gap in identity["gaps"]))
    return {
        "completed": not reasons,
        "state": "passed" if not reasons else "blocked",
        "reasons": reasons,
        "identity_matching_entries": [entry["source"]["path"] for entry in matching],
        "identity_stale_entries": stale,
        "identity_unknown_entries": unknown,
        "timed_entry_count": len(timed),
    }


def validate_benchmark_declaration() -> list[str]:
    """Fail-closed integrity check of the declared mature-system targets."""
    problems: list[str] = []
    ladder = {row["tier"]: row for row in BENCHMARK_LADDER}
    seen_ids: set[str] = set()
    for target in MATURE_SYSTEM_TARGETS:
        target_id = target.get("id")
        if not isinstance(target_id, str) or not target_id:
            problems.append("a declared target carries no id")
            continue
        if target_id in seen_ids:
            problems.append(f"{target_id}: duplicate target id")
        seen_ids.add(target_id)
        tier = target.get("tier")
        if tier not in ladder:
            problems.append(f"{target_id}: unknown ladder tier {tier!r}")
        else:
            tier_budget = _number(ladder[tier].get("budget_ms"))
            if tier_budget is None or _number(target.get("target_ms")) != tier_budget:
                problems.append(f"{target_id}: target_ms does not match its ladder tier budget")
        sources = target.get("sources")
        if not isinstance(sources, (list, tuple)) or not sources:
            problems.append(f"{target_id}: cites no external source")
        else:
            for source in sources:
                if source not in BENCHMARK_SOURCES:
                    problems.append(f"{target_id}: unknown external source {source!r}")
        target_ms = _number(target.get("target_ms"))
        tolerance_ms = _number(target.get("tolerance_ms"))
        if target_ms is None or tolerance_ms is None or tolerance_ms < target_ms:
            problems.append(f"{target_id}: tolerance must be defined and not below the target")
        selector = target.get("selector")
        if not isinstance(selector, dict) or not any(
            key in selector for key in ("sample_labels", "sample_states", "sla_intents")
        ):
            problems.append(f"{target_id}: selector binds no observation")
        intent = target.get("historical_budget_intent")
        if intent is not None and not isinstance(intent, str):
            problems.append(f"{target_id}: historical_budget_intent must be a string or absent")
        basis = target.get("measurement_basis")
        if basis is not None and basis not in MEASUREMENT_BASES:
            problems.append(f"{target_id}: unknown measurement_basis {basis!r}")
        if target.get("diagnostic_only") and basis != "profiled":
            problems.append(
                f"{target_id}: diagnostic_only must declare measurement_basis 'profiled', so an "
                "UNPROFILED measurement is never hidden from grading"
            )
    for source, row in BENCHMARK_SOURCES.items():
        for field in ("publisher", "title", "url", "statement"):
            value = row.get(field)
            if not isinstance(value, str) or not value.strip():
                problems.append(f"source {source}: missing {field}")
    return problems


def _historical_budget_gates() -> dict:
    """Read the governing platform SLA budget so gate looseness is measured, not argued."""
    path = ROOT / "scripts" / "verify" / "baselines" / "platform_sla.json"
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    limits = loaded.get("max_p95_ms")
    if not isinstance(limits, dict):
        return {}
    gates = {}
    for intent, value in limits.items():
        number = _number(value)
        if isinstance(intent, str) and number is not None:
            gates[intent] = number
    return gates


def _matched_samples(entries: list[dict], selector: dict) -> list[dict]:
    """Samples the selector binds to, in declaration order."""
    matched: list[dict] = []
    sla_intents = selector.get("sla_intents")
    labels = selector.get("sample_labels")
    states = selector.get("sample_states")
    for entry in entries:
        if sla_intents is not None:
            if entry["schema"] != "platform-sla-guard/v1":
                continue
            for sample in entry["samples"]:
                if sample.get("name") in sla_intents:
                    matched.append(sample)
            continue
        for sample in entry["samples"]:
            if labels is not None and sample.get("label") not in labels:
                continue
            if states is not None and sample.get("state") not in states:
                continue
            matched.append(sample)
    return matched


def _sample_values(samples: list[dict], metric: str) -> list[float]:
    values: list[float] = []
    for sample in samples:
        value = _number(sample.get(metric))
        if value is not None:
            values.append(value)
    return values


def _target_values(entries: list[dict], selector: dict, metric: str) -> list[float]:
    return _sample_values(_matched_samples(entries, selector), metric)


def one_time_process_init(samples: list[dict]) -> dict:
    """Attribute the declared once-per-process share inside a first-call sample.

    The declared markers nest, so the result is the **maximum** matching
    cumulative frame, never a sum of nested frames. No profile rows means the
    share is not declared: it is reported as such, never as zero.
    """
    best: dict | None = None
    for sample in samples:
        for row in sample.get("profile_top") or []:
            path = str(row.get("file") or "")
            base = path.rsplit("/", 1)[-1]
            for marker in FIRST_CALL_ONE_TIME_MARKERS:
                if base not in marker["marker_files"]:
                    continue
                cumulative = _number(row.get("cumulative_ms"))
                if cumulative is None:
                    continue
                if best is None or cumulative > best["one_time_ms"]:
                    best = {
                        "marker": marker["id"],
                        "one_time_ms": cumulative,
                        "frame": f"{path}:{row.get('line')} {row.get('function')}",
                        "calls": row.get("calls"),
                    }
    if best is None:
        return {
            "status": "not_declared",
            "reason": "no declared one-time marker frame in the matched sample profile",
            "basis": "max cumulative of declared marker frames; nested frames are never summed",
        }
    best["status"] = "measured"
    best["basis"] = "max cumulative of declared marker frames; nested frames are never summed"
    return best


def _nearest_rank_p95(values: list[float]) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("nearest-rank percentile needs at least one value")
    index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    return ordered[min(index, len(ordered) - 1)]


_VERDICT_ORDER = {"met": 0, "within_tolerance": 1, "failed": 2}


def _verdict_for(value: float, target_ms: float, tolerance_ms: float) -> str:
    if value <= target_ms:
        return "met"
    if value <= tolerance_ms:
        return "within_tolerance"
    return "failed"


def _aggregated(values: list[float], aggregation: str) -> float | None:
    """Apply the declared aggregation, or ``None`` when there is nothing to aggregate."""
    if not values:
        return None
    if aggregation == "p95":
        return _nearest_rank_p95(values)
    if aggregation == "max":
        return max(values)
    if aggregation == "first":
        return values[0]
    return None


def evaluate_targets(entries: list[dict]) -> dict:
    """Judge the produced observations against the declared mature-system bar."""
    problems = validate_benchmark_declaration()
    if problems:
        raise ValueError("mature-system target declaration is invalid: " + "; ".join(problems))
    gates = _historical_budget_gates()
    results: list[dict] = []
    for target in MATURE_SYSTEM_TARGETS:
        matched = _matched_samples(entries, target["selector"])
        profiled_values = _sample_values(
            [sample for sample in matched if sample.get("profiled") is True], target["metric"]
        )
        unprofiled_values = _sample_values(
            [sample for sample in matched if sample.get("profiled") is not True], target["metric"]
        )
        aggregation = target["aggregation"]
        basis = target.get("measurement_basis") or "unprofiled"
        diagnostic_only = bool(target.get("diagnostic_only"))
        # Only the unprofiled capture may answer an absolute millisecond target, so a
        # profiled-basis or diagnostic-only target is reported, never graded.
        gradeable = not diagnostic_only and basis == "unprofiled"
        values = unprofiled_values if gradeable else []
        minimum = int(target.get("minimum_samples") or 1)
        target_ms = float(target["target_ms"])
        tolerance_ms = float(target["tolerance_ms"])
        row = {
            "id": target["id"],
            "tier": target["tier"],
            "statement": target["statement"],
            "metric": target["metric"],
            "aggregation": aggregation,
            "minimum_samples": minimum,
            "target_ms": target_ms,
            "tolerance_ms": tolerance_ms,
            "sources": list(target["sources"]),
            "rationale": target["rationale"],
            "selector": dict(target["selector"]),
            "sample_count": len(values),
            "observed_ms": None,
            "verdict": "not_evaluated",
            "reason": None,
            "graded": gradeable,
            # the declared basis of this target (which capture may answer it), not the
            # basis of whatever happened to match; the observed split is reported by
            # sample_count / profiled_sample_count
            "measurement_basis": basis,
            "comparability_rule": PROFILED_COMPARABILITY_RULE,
            "profiled_sample_count": len(profiled_values),
            "profiled_values_ms": sorted(profiled_values),
            "profiled_basis_ms": _aggregated(profiled_values, aggregation),
            "matched_sample_count": len(matched),
        }
        if target.get("diagnostic_only"):
            row["diagnostic_only"] = True
        intent = target.get("historical_budget_intent")
        row["historical_budget_intent"] = intent
        gate = gates.get(intent) if isinstance(intent, str) else None
        if gate is not None:
            row["historical_budget_ms"] = gate
            if target_ms > 0:
                row["historical_budget_vs_target_ratio"] = round(gate / target_ms, 3)
        if target.get("first_call_boundary"):
            row["one_time_process_init"] = one_time_process_init(
                _matched_samples(entries, target["selector"])
            )
        if diagnostic_only:
            row["reason"] = DIAGNOSTIC_ONLY_REASON
        elif basis == "profiled":
            row["reason"] = PROFILED_BASIS_REASON
        elif not values and profiled_values:
            row["reason"] = (
                "profiled-only match: cProfile-instrumented samples are not comparable to an absolute "
                "target; see comparability_rule and profiled_values_ms"
            )
        elif len(values) < minimum:
            row["reason"] = f"{aggregation} needs >= {minimum} sample(s), observed {len(values)}"
        else:
            observed = _aggregated(values, aggregation)
            if observed is None:
                row["reason"] = f"unsupported aggregation {aggregation!r}"
            else:
                row["observed_ms"] = observed
                row["verdict"] = _verdict_for(observed, target_ms, tolerance_ms)
                row["samples_ms"] = (
                    list(values) if aggregation == "first" else sorted(values)
                )
        annotation = row.get("one_time_process_init")
        if isinstance(annotation, dict) and annotation.get("status") == "measured":
            basis_ms = row["observed_ms"]
            share_basis = "observed_ms"
            if basis_ms is None:
                basis_ms = row.get("profiled_basis_ms")
                share_basis = "profiled_basis_ms"
            if isinstance(basis_ms, (int, float)) and basis_ms:
                annotation["share_of_observed"] = round(annotation["one_time_ms"] / basis_ms, 4)
                annotation["share_basis"] = share_basis
        results.append(row)
    evaluated = [row for row in results if row["verdict"] != "not_evaluated"]
    not_evaluated = [row for row in results if row["verdict"] == "not_evaluated"]
    # A target that is declared ungradeable (diagnostic-only / profiled basis) is
    # excluded by design, so it never keeps the benchmark open. Any gradeable target
    # without a verdict does.
    ungradeable = [row for row in results if not row.get("graded")]
    unevaluated_gradeable = [
        row for row in results if row.get("graded") and row["verdict"] == "not_evaluated"
    ]
    worst = None
    for row in evaluated:
        if worst is None or _VERDICT_ORDER[row["verdict"]] > _VERDICT_ORDER[worst]:
            worst = row["verdict"]
    return {
        "schema": BENCHMARK_SCHEMA,
        "ladder": [dict(row) for row in BENCHMARK_LADDER],
        "sources": {name: dict(row) for name, row in BENCHMARK_SOURCES.items()},
        "targets": results,
        "summary": {
            "target_count": len(results),
            "evaluated": len(evaluated),
            "not_evaluated": len(not_evaluated),
            "ungradeable_by_declaration": len(ungradeable),
            "unevaluated_gradeable": len(unevaluated_gradeable),
            "met": sum(1 for row in evaluated if row["verdict"] == "met"),
            "within_tolerance": sum(1 for row in evaluated if row["verdict"] == "within_tolerance"),
            "failed": sum(1 for row in evaluated if row["verdict"] == "failed"),
            "overall": worst or "not_evaluated",
            "complete_over_comparable_targets": not unevaluated_gradeable,
            "capacity": "target_unresolved",
        },
        "declaration_problems": [],
        "note": (
            "the mature-system bar is declared from published external references, not measured; it "
            "neither relaxes nor replaces the historical platform SLA budgets, and it is not a capacity, "
            "SLO or production acceptance"
        ),
    }


def _role_contract_variation(raw_entries: list[dict]) -> dict | None:
    """Report the role dimension exactly as the role probe declared it.

    A single-principal baseline cannot see whether the contract surface, the
    navigation capability or the per-role cost varies. This reads only the
    declared probe findings; nothing is re-derived, averaged or relaxed.
    """
    source = next(
        (
            entry
            for entry in raw_entries
            if entry.get("schema") == "runtime-contract-role-matrix-probe/v1"
        ),
        None,
    )
    if source is None:
        return None
    payload = source.get("payload") or {}
    return {
        "status": "observed",
        "probe_schema": source["schema"],
        "role_count": payload.get("findings", {}).get("role_count"),
        "navigation_capability_per_role": payload.get("findings", {}).get(
            "navigation_capability_per_role"
        ),
        "refusal_summary": payload.get("findings", {}).get("refusal_summary"),
        "all_refusals_are_explicit": payload.get("findings", {}).get("all_refusals_are_explicit"),
        "refused_roles_never_report_a_contract": payload.get("findings", {}).get(
            "refused_roles_never_report_a_contract"
        ),
        "contract_surface_varies_by_role": payload.get("findings", {}).get(
            "contract_surface_varies_by_role"
        ),
        "surface_digest_stable_within_dispatched_role": payload.get("findings", {}).get(
            "surface_digest_stable_within_dispatched_role"
        ),
        "relation_surface_varies_by_role": payload.get("findings", {}).get(
            "relation_surface_varies_by_role"
        ),
        "case_analysis": {
            case_id: {
                "dispatched_roles": case.get("dispatched_roles"),
                "unavailable_roles": case.get("unavailable_roles"),
                "refused_roles": case.get("refused_roles"),
                "identity_ref_count": case.get("identity_ref_count"),
                "surface_digest_count": case.get("surface_digest_count"),
                "navigation_authority_per_role": case.get("navigation_authority_per_role"),
                "cold_dispatch_ms_spread": case.get("cold_dispatch_ms_spread"),
                "hot_dispatch_ms_per_role": case.get("hot_dispatch_ms_per_role"),
                "hot_sql_count_per_role": case.get("hot_sql_count_per_role"),
                "surface_diff_vs_baseline": case.get("surface_diff_vs_baseline"),
            }
            for case_id, case in (payload.get("case_analysis") or {}).items()
        },
        "note": (
            "role variation is declared by the role probe, never inferred here; a role that is "
            "refused or unavailable is reported with its reason and never with a substituted contract"
        ),
    }


def build_record(entries: list[dict], declared: dict) -> dict:
    normalized = [normalize(entry) for entry in entries]
    identity = resolve_identity(normalized, declared)
    timing_gaps = _timing_gaps(normalized)
    observed = sum(entry["samples_observed"] for entry in normalized)
    retained = sum(entry["samples_retained"] for entry in normalized)
    no_drop = observed == retained
    if not no_drop:
        raise AssertionError(f"sample accounting mismatch: observed={observed} retained={retained}")

    controlled = _controlled_regression(normalized, identity)
    gaps = list(identity["gaps"]) + timing_gaps
    record = {
        "schema": SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "baseline" if not gaps and controlled["completed"] else "incomplete",
        "identity": identity["fields"],
        "identity_gaps": identity["gaps"],
        "declared_identity_inputs": identity["declared_inputs"],
        "stage_sum_forbidden": True,
        "sample_policy": {
            "samples_observed": observed,
            "samples_retained": retained,
            "no_sample_dropped": no_drop,
            "unknown_is_gap_never_zero": True,
        },
        "gaps": gaps,
        "mature_system_targets": evaluate_targets(normalized),
        "role_contract_variation": _role_contract_variation(entries),
        "layers": {
            "controlled_regression": controlled,
            "daily_experience": {
                "completed": False,
                "state": "not_run",
                "reason": "requires a bound deployment, the served frontend artifact, the real network path and a representative role/data scale",
            },
            "capacity": {
                "completed": False,
                "state": "target_unresolved",
                "reason": "target concurrency, data scale, throughput and error budget are not yet confirmed",
            },
        },
        "entries": normalized,
        "limitations": sorted(
            {
                "normalizer never runs a probe and never writes to the governed runtime",
                "stage maps are declared nested; their values are never summed",
                "entry identity match is compared against the current worktree at record time",
                "this record is not a browser, SLO, capacity or production acceptance",
            }
        ),
    }
    return record


def render_markdown(record: dict) -> str:
    lines = [
        "# System Performance Baseline",
        "",
        "Generated by `scripts/verify/system_performance_baseline.py`. Normalized view of",
        "already-produced managed probe payloads; it is not a browser, SLO, capacity or",
        "production acceptance.",
        "",
        f"- schema: `{record['schema']}`",
        f"- status: `{record['status']}`",
        f"- generated_at: `{record['generated_at']}`",
        f"- samples observed / retained: `{record['sample_policy']['samples_observed']}` / "
        f"`{record['sample_policy']['samples_retained']}`",
        f"- stage timings summed: `{'no' if record['stage_sum_forbidden'] else 'yes'}`",
        f"- gaps: `{len(record['gaps'])}`",
        "",
        "## Identity",
        "",
        "| field | status | provenance |",
        "| --- | --- | --- |",
    ]
    for field, row in sorted(record["identity"].items()):
        lines.append(f"| {field} | {row['status']} | {row.get('provenance', row.get('reason', ''))} |")

    lines.extend(["", "## Entries", "", "| source | schema | mode | samples | identity |", "| --- | --- | --- | ---: | --- |"])
    for entry in record["entries"]:
        lines.append(
            f"| `{entry['source']['path']}` | {entry['schema']} | {entry['measurement_mode'] or '-'} | "
            f"{entry['samples_retained']} | {entry['identity_match']['status']} |"
        )

    lines.extend(["", "## Acceptance layers", "", "| layer | state | reason |", "| --- | --- | --- |"])
    for name, row in record["layers"].items():
        reason = row.get("reason") or "; ".join(row.get("reasons") or []) or "-"
        lines.append(f"| {name} | {row['state']} | {reason} |")

    lines.extend(["", "## Gaps", ""])
    if record["gaps"]:
        for gap in record["gaps"]:
            lines.append(f"- `{gap['field']}`: {gap['reason']}")
    else:
        lines.append("- none")

    benchmark = record.get("mature_system_targets") or {}
    targets = benchmark.get("targets") or []
    summary = benchmark.get("summary") or {}
    lines.extend(
        [
            "",
            "## Mature-system targets",
            "",
            "Declared bar from published external references, judged against already-produced",
            "managed observations. It neither relaxes nor replaces the historical platform SLA",
            "budgets and is not a capacity or production acceptance.",
            "",
            f"- overall: `{summary.get('overall', 'not_evaluated')}` "
            f"(met `{summary.get('met', 0)}`, within tolerance `{summary.get('within_tolerance', 0)}`, "
            f"failed `{summary.get('failed', 0)}`, not evaluated `{summary.get('not_evaluated', 0)}`)",
            f"- complete over comparable targets: `{summary.get('complete_over_comparable_targets')}` "
            "- true only when every target with a comparable declared basis has a verdict; "
            f"`{summary.get('ungradeable_by_declaration', 0)}` target(s) are ungradeable by declaration "
            "(never a pass, never a failure), so this flag alone is not a delivery or capacity claim",
            f"- capacity: `{summary.get('capacity', 'target_unresolved')}`",
            "",
            "| target | tier | agg | basis | samples | observed ms | target ms | tolerance ms | historical gate | verdict |",
            "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- |",
        ]
    )
    for target in targets:
        observed = target.get("observed_ms")
        gate = target.get("historical_budget_ms")
        ratio = target.get("historical_budget_vs_target_ratio")
        gate_cell = "-" if gate is None else f"{gate:g}" + (f" ({ratio:g}x)" if ratio is not None else "")
        basis = target.get("measurement_basis") or "-"
        if observed is not None:
            observed_cell = f"{observed:.2f}"
        else:
            profiled = target.get("profiled_basis_ms")
            observed_cell = (
                f"- (profiled {profiled:.2f})" if isinstance(profiled, (int, float)) else "-"
            )
        lines.append(
            f"| {target['id']} | {target['tier']} | {target['aggregation']} | {basis} | "
            f"{target['sample_count']} | {observed_cell} | {target['target_ms']:g} | "
            f"{target['tolerance_ms']:g} | {gate_cell} | {target['verdict']} |"
        )
    unevaluated = [t for t in targets if t["verdict"] == "not_evaluated"]
    boundary_targets = [t for t in targets if t.get("one_time_process_init")]
    if boundary_targets:
        lines.extend(
            [
                "",
                "### First-call boundary",
                "",
                "Attached only to targets declared `first_call_boundary`. It separates a provable",
                "process-level one-time initialization from the first cache build and first assembly;",
                "marker frames are nested and are never summed, and a sample without a profile is",
                "`not_declared`, not zero.",
                "",
                "| target | one-time state | one-time ms | frame | calls | share of observed |",
                "| --- | --- | ---: | --- | ---: | ---: |",
            ]
        )
        for target in boundary_targets:
            one_time = target["one_time_process_init"]
            one_time_ms = one_time.get("one_time_ms")
            share = one_time.get("share_of_observed")
            lines.append(
                f"| {target['id']} | {one_time.get('status', '-')} | "
                f"{'-' if one_time_ms is None else f'{one_time_ms:.2f}'} | "
                f"{one_time.get('frame', '-')} | {one_time.get('calls', '-')} | "
                f"{'-' if share is None else f'{share:.4f}'} |"
            )
    if unevaluated:
        lines.extend(["", "### Not evaluated", ""])
        for target in unevaluated:
            detail = target.get("reason") or "no supporting sample"
            profiled = target.get("profiled_values_ms") or []
            if profiled:
                shown = ", ".join(f"{value:.2f}" for value in profiled)
                detail += f" (profiled values ms: {shown})"
            lines.append(f"- `{target['id']}`: {detail}")
    variation = record.get("role_contract_variation")
    if isinstance(variation, dict):
        lines.extend(
            [
                "",
                "## Role-dimension contract variation",
                "",
                "Declared by the role probe; nothing here is inferred, averaged or relaxed. A role",
                "that is refused or unavailable keeps its reason and is never reported with a",
                "substituted contract.",
                "",
                f"- roles declared: `{variation.get('role_count')}`",
                f"- contract surface varies by role: `{variation.get('contract_surface_varies_by_role')}`",
                f"- surface digest stable within a dispatched role: "
                f"`{variation.get('surface_digest_stable_within_dispatched_role')}`",
                f"- all refusals explicit: `{variation.get('all_refusals_are_explicit')}`",
                f"- refused roles never report a contract: "
                f"`{variation.get('refused_roles_never_report_a_contract')}`",
                "",
                "| case | dispatched | refused | unavailable | identity refs | surface digests | cold ms (min/median/max) | hot ms (per role) |",
                "| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |",
            ]
        )
        for case_id, case in (variation.get("case_analysis") or {}).items():
            cold = case.get("cold_dispatch_ms_spread") or {}
            cold_cell = "-"
            if cold:
                cold_cell = f"{cold.get('min')}/{cold.get('median')}/{cold.get('max')}"
            hot = case.get("hot_dispatch_ms_per_role") or {}
            hot_cell = ", ".join(
                f"{label}={'-' if value is None else f'{value:.1f}'}" for label, value in sorted(hot.items())
            ) or "-"
            lines.append(
                f"| `{case_id}` | {len(case.get('dispatched_roles') or [])} | "
                f"{len(case.get('refused_roles') or [])} | {len(case.get('unavailable_roles') or [])} | "
                f"{case.get('identity_ref_count')} | {case.get('surface_digest_count')} | "
                f"{cold_cell} | {hot_cell} |"
            )
    return "\n".join(lines) + "\n"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", nargs="+", required=True, help="managed probe outputs or logs")
    parser.add_argument("--identity-file", default="", help="optional declared identity facts (JSON)")
    parser.add_argument("--out", default=str(RECORD_JSON), help="baseline record JSON path")
    parser.add_argument("--report", default=str(REPORT_MD), help="baseline markdown path")
    parser.add_argument("--strict", action="store_true", help="exit non-zero unless status is 'baseline'")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    declared: dict = {}
    if args.identity_file:
        identity_path = Path(args.identity_file)
        if not identity_path.is_file():
            print(f"declared identity file missing: {identity_path}", file=sys.stderr)
            return 2
        loaded = json.loads(identity_path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            print("declared identity file must contain a JSON object", file=sys.stderr)
            return 2
        declared = loaded

    try:
        entries = load_inputs([Path(path) for path in args.inputs])
        record = build_record(entries, declared)
    except (ValueError, FileNotFoundError, AssertionError) as exc:
        print(f"system performance baseline failed: {exc}", file=sys.stderr)
        return 2

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(record, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_markdown(record), encoding="utf-8")

    print(f"SYSTEM_PERFORMANCE_BASELINE={json.dumps({'status': record['status'], 'gaps': len(record['gaps']), 'entries': len(record['entries']), 'out': str(out_path)}, ensure_ascii=False)}")
    if args.strict and record["status"] != "baseline":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
