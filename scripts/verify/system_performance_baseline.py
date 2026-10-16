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

This is a bounded collection tool for the registered local demo environment. It
is not a browser, SLO, capacity or production acceptance by itself.
"""
from __future__ import annotations

import argparse
import hashlib
import json
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
    "scripts/verify/local_dev_runtime_performance.py",
    "scripts/verify/local_dev_runtime_contract_request_probe.py",
    "scripts/verify/local_dev_runtime_permission_probe.py",
    "scripts/verify/local_dev_runtime_cache_identity_probe.py",
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
    if entry["schema"] in {"runtime-contract-request-probe/v1", "runtime-permission-probe/v1"}:
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
