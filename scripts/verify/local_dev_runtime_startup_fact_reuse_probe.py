"""Read-only startup fact-reuse A/B probe for local.dev.

Compares the current request-scoped menu-fact reuse and extension-fact dedupe
against the previous no-cache/double-compute behaviour by monkey-patching only
the probe process.  It never writes product data, refuses commit, and reports
uninstrumented elapsed time, SQL count, fact scans and route-authority sets.

Run through the governed odoo.shell entrypoint. Environment variables must use
the ``PRODUCT_*`` forwarding prefix understood by ``odoo_shell_exec.sh``:

``PRODUCT_PERFORMANCE_STARTUP_FACT_REUSE_MODE``
    ``candidate`` (current code) or ``previous`` (reproduce the pre-R15 shape).
``PRODUCT_PERFORMANCE_STARTUP_FACT_REUSE_SAMPLES``
    Number of system.init samples; sample 0 is the process-first sample.
``PRODUCT_PERFORMANCE_STARTUP_FACT_REUSE_PROFILE``
    ``counter`` counts high-level calls and therefore inflates elapsed time;
    ``timing`` installs no counters and reports uninstrumented elapsed time.
"""
import hashlib
import importlib
import json
import os
import statistics
import time

from odoo import api

from odoo.addons.smart_core.delivery.delivery_engine import DeliveryEngine
from odoo.addons.smart_core.delivery.menu_fact_service import MenuFactService
from odoo.addons.smart_core.delivery.menu_service import MenuService
from odoo.addons.smart_core.handlers.system_init import SystemInitHandler

assert env.cr.dbname == "sc_dev_demo", "registered local.dev database required"
mode = os.environ.get("PRODUCT_PERFORMANCE_STARTUP_FACT_REUSE_MODE", "candidate")
assert mode in {"candidate", "previous"}, "unknown PRODUCT_PERFORMANCE_STARTUP_FACT_REUSE_MODE"
profile = os.environ.get("PRODUCT_PERFORMANCE_STARTUP_FACT_REUSE_PROFILE", "counter")
assert profile in {"counter", "timing"}, "unknown PRODUCT_PERFORMANCE_STARTUP_FACT_REUSE_PROFILE"
sample_count = int(os.environ.get("PRODUCT_PERFORMANCE_STARTUP_FACT_REUSE_SAMPLES") or 4)
assert sample_count >= 2, "at least one process-first and one warm sample required"
instrumented = profile == "counter"
detail_section = os.environ.get("PRODUCT_PERFORMANCE_STARTUP_FACT_REUSE_DETAIL", "").strip()

env.cr.rollback()
original_commit = env.cr.commit


def refuse_commit(*args, **kwargs):
    raise RuntimeError("startup fact-reuse probe forbids commit")


env.cr.commit = refuse_commit

counts = {
    "menu_fact_scans": 0,
    "visible_exports": 0,
    "authorized_exports": 0,
    "route_authority_builds": 0,
    "delivery_builds": 0,
    "extension_contributions": 0,
}
originals = []


def _patch(owner, name, factory):
    original = getattr(owner, name)
    originals.append((owner, name, original))
    setattr(owner, name, factory(original))


def _counted(original, key):
    def wrapper(*args, **kwargs):
        counts[key] += 1
        return original(*args, **kwargs)

    return wrapper


core_package = importlib.import_module("odoo.addons.smart_construction_core")
core_extension = importlib.import_module("odoo.addons.smart_construction_core.core_extension")


def _install_counters():
    _patch(MenuFactService, "_export_menu_facts", lambda original: _counted(original, "menu_fact_scans"))
    _patch(MenuFactService, "export_visible_menu_facts", lambda original: _counted(original, "visible_exports"))
    _patch(MenuFactService, "export_authorized_menu_facts", lambda original: _counted(original, "authorized_exports"))
    _patch(MenuService, "build_route_authority", lambda original: _counted(original, "route_authority_builds"))
    _patch(DeliveryEngine, "build", lambda original: _counted(original, "delivery_builds"))
    # The fact merger resolves the hook through the package namespace while the
    # extension hook calls the module global; both bindings must be counted or
    # the duplicate computation is invisible.
    _patch(
        core_extension,
        "get_system_init_fact_contributions",
        lambda original: _counted(original, "extension_contributions"),
    )
    _patch(
        core_package,
        "get_system_init_fact_contributions",
        lambda original: _counted(original, "extension_contributions"),
    )


def _install_previous_shims():
    """Reproduce the pre-R15 shape without touching the working tree."""
    def previous_snapshot(self, kind):
        service = MenuFactService(self.env)
        return (
            service.export_authorized_menu_facts()
            if kind == "authorized"
            else service.export_visible_menu_facts()
        )

    _patch(MenuService, "_menu_fact_snapshot", lambda original: previous_snapshot)

    # ``extension_loader.run_extension_hooks`` resolves the hook through the
    # package namespace, so the shim must wrap that binding.
    original_extend = core_package.smart_core_extend_system_init

    def previous_extend(data, extension_env, user):
        core_extension.get_system_init_fact_contributions(extension_env, user)
        return original_extend(data, extension_env, user)

    _patch(core_package, "smart_core_extend_system_init", lambda original: previous_extend)


def _semantic(value):
    if isinstance(value, list):
        return [_semantic(item) for item in value]
    if not isinstance(value, dict):
        return value
    volatile = {
        "elapsed_ms",
        "duration_ms",
        "trace_id",
        "request_id",
        "generated_at",
        "timestamp",
        "started_at",
        "finished_at",
    }
    return {key: _semantic(item) for key, item in value.items() if key not in volatile}


def _sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def _route_authority_sets(authority):
    buckets = (
        "primary_actions",
        "role_home_actions",
        "contextual_actions",
        "admin_actions",
        "denied_actions",
        "menu_containers",
    )
    sets = {}
    for bucket in buckets:
        rows = authority.get(bucket) if isinstance(authority, dict) else []
        sets[bucket] = sorted(
            (
                int(row.get("menu_id") or 0),
                int(row.get("action_id") or 0),
                str(row.get("route_kind") or ""),
                str(row.get("route") or ""),
            )
            for row in (rows or [])
            if isinstance(row, dict)
        )
    return sets


try:
    if mode == "previous":
        _install_previous_shims()
    if instrumented:
        _install_counters()

    user = env.ref("smart_construction_demo.user_demo_role_finance")
    assert user and user.active and not user.share, "declared demo finance identity unavailable"
    companies = [user.company_id.id] + [
        company_id
        for company_id in user.company_ids.ids
        if company_id != user.company_id.id
    ][:1]
    params = {
        "scene": "web",
        "with_preload": False,
        "scene_ready_mode": "registry",
        "with": ["workspace_home"],
    }

    samples = []
    for index in range(sample_count):
        actor = api.Environment(env.cr, user.id, {"allowed_company_ids": [companies[0]], "lang": "zh_CN"})
        assert not actor.su, "actor must not be elevated"
        before_sql = env.cr.sql_log_count
        before_counts = dict(counts)
        started = time.perf_counter()
        result = SystemInitHandler(env=actor).handle(payload={"params": params})
        elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
        assert result.ok, "system.init failed"
        data = result.data if isinstance(result.data, dict) else {}
        navigation = data.get("navigation") if isinstance(data.get("navigation"), dict) else {}
        authority = navigation.get("route_authority") if isinstance(navigation.get("route_authority"), dict) else {}
        route_sets = _route_authority_sets(authority)
        sample = {
            "index": index,
            "phase": "process_first" if index == 0 else "warm",
            "elapsed_ms": elapsed_ms,
            "sql_count": env.cr.sql_log_count - before_sql,
            "route_authority_sha256": _sha(route_sets),
            "route_authority_counts": {bucket: len(rows) for bucket, rows in route_sets.items()},
            "navigation_sha256": _sha(_semantic(navigation)),
            "data_semantic_sha256": _sha(_semantic(data)),
            "data_section_sha256": {
                str(key): _sha(_semantic(value)) for key, value in sorted(data.items())
            },
            "data_json_bytes": len(json.dumps(data, ensure_ascii=False, default=str).encode()),
        }
        for key in (
            "menu_fact_scans",
            "visible_exports",
            "authorized_exports",
            "route_authority_builds",
            "delivery_builds",
            "extension_contributions",
        ):
            sample[key] = counts[key] - before_counts[key] if instrumented else None
        _last_data = data
        samples.append(sample)

    warm = samples[1:] or samples
    summary = {
        "sample_count": len(samples),
        "warm_sample_count": len(warm),
        "warm_elapsed_ms_median": round(statistics.median([row["elapsed_ms"] for row in warm]), 3),
        "warm_elapsed_ms_max": round(max(row["elapsed_ms"] for row in warm), 3),
        "warm_sql_count_median": statistics.median([row["sql_count"] for row in warm]),
    }
    for key in (
        "menu_fact_scans",
        "visible_exports",
        "authorized_exports",
        "route_authority_builds",
        "delivery_builds",
        "extension_contributions",
    ):
        summary[f"{key}_per_request"] = (
            statistics.median([row[key] for row in warm]) if instrumented else None
        )

    limitations = [
        "local_demo_backend_only",
        "no_http_browser_authentication_measurement",
        "process_first_not_true_cold_registry",
        "median_of_warm_samples_only_no_p95",
    ]
    if instrumented:
        limitations.append("elapsed_time_includes_counter_overhead")
    else:
        limitations.append("call_counts_not_available_in_timing_profile")

    report = {
        "schema": "startup-fact-reuse-probe/v1",
        "status": "observed",
        "mode": mode,
        "profile": profile,
        "instrumented": instrumented,
        "database": env.cr.dbname,
        "principal_xmlid": "smart_construction_demo.user_demo_role_finance",
        "company_id": companies[0],
        "request_params": params,
        "samples": samples,
        "summary": summary,
        "limitations": limitations,
    }
    if detail_section:
        last = samples[-1]
        report["detail"] = {"section": detail_section, "semantic": _semantic(_last_data.get(detail_section))}
    print("STARTUP_FACT_REUSE_PROBE=" + json.dumps(report, sort_keys=True, default=str), flush=True)
finally:
    for owner, name, original in reversed(originals):
        setattr(owner, name, original)
    env.cr.rollback()
    env.cr.commit = original_commit
