"""Bounded contract-request observation for R5 (P4 diagnostic).

One fixed identity, one fixed ``ui.contract.v2`` request, repeated so the
distribution (not the fastest sample) is visible, with a deliberate cold/miss
split. The probe answers three questions with runtime evidence:

1. what the per-request cost is now, split into ``permission`` and the router
   ``dispatch_*`` sub-segments that the HTTP ``Server-Timing`` header exposes;
2. whether a repeated identical request is a cache hit, and what identity a
   variation produces (the mechanism behind a hit -> miss transition);
3. how many ``copy.deepcopy`` calls a hot request performs and where they come
   from (the R3 read-path hand-off benefit).

Read-only: commit is refused, the probe rolls back, it changes no product code,
schema, fixture or ACL. ``registry.clear_cache()`` and the module-local hot
``CONTRACT_PROJECTION_HOT_CACHE`` clear affect only this throwaway ``odoo
shell`` process, never the serving workers.
"""
import copy
import gc
import hashlib
import inspect
import json
import sys
import time
from pathlib import Path
from types import SimpleNamespace

from odoo import api
from odoo.addons.smart_core.core.context import RequestContext
from odoo.addons.smart_core.core import intent_router
from odoo.addons.smart_core.security import intent_permission as ip
from odoo.addons.smart_core.utils import load_contract_response_cache as lcrc

DATABASE = "sc_dev_demo"
ACTION_ID = 878
INTENT = "ui.contract.v2"
HOT_SAMPLES = 12

assert env.cr.dbname == DATABASE, "registered local.dev database required"
env.cr.rollback()
_ORIGINAL_COMMIT = env.cr.commit


def _refuse_commit(*_args, **_kwargs):
    raise RuntimeError("contract request probe forbids commit")


env.cr.commit = _refuse_commit

REPORT = {"schema": "runtime-contract-request-probe/v1", "database": DATABASE, "acceptance_pass": False}


def _source_hash(relative):
    return hashlib.sha256(
        (Path(inspect.getsourcefile(intent_router)).parents[1] / relative).read_bytes()
    ).hexdigest()


class _RequestShim:
    """Minimal faithful stand-in for ``odoo.http.request``; transport is out of scope."""

    def __init__(self, environment):
        self.env = environment
        self.uid = environment.uid
        self.session = SimpleNamespace(db=DATABASE, uid=environment.uid)
        self.httprequest = SimpleNamespace(headers={}, remote_addr="127.0.0.1")
        self.params = {}
        self.jsonrequest = None


user = env.ref("smart_construction_demo.user_demo_role_finance")
assert user.active and not user.share, "declared demo finance identity unavailable"
company = user.company_id.id
actor = api.Environment(env.cr, user.id, {"allowed_company_ids": [company], "lang": "zh_CN"})
assert not actor.su, "actor must not be elevated"
shim = _RequestShim(actor)

tra = __import__("odoo.addons.smart_core.delivery.runtime_route_authority", fromlist=["x"])
Policy = actor["sc.product.policy"]
CARRIER = None
for _menu_id, _action_id in tra.iter_published_pairs(Policy.published_route_authority()):
    if int(_action_id) == ACTION_ID and int(_menu_id) > 0:
        CARRIER = int(_menu_id)
        break
assert CARRIER, "no published menu carrier for the observed action"

BASE_PARAMS = {"action_id": ACTION_ID, "op": "action_open", "menu_id": CARRIER}
# A benign identity variation: same action/menu, a bounded page size. It changes
# the projection identity without changing the product surface under observation.
VARIANT_PARAMS = dict(BASE_PARAMS, limit=40)
SCENARIOS = {"base": BASE_PARAMS, "variant": VARIANT_PARAMS}

PRINCIPAL = {
    "auth_method": "password",
    "principal_type": "human",
    "user_id": user.id,
    "payload": {"db": DATABASE},
}

# --- instrumentation ---------------------------------------------------------
SQL = {"count": 0, "ms": 0.0}
_SQL_ORIGINAL = type(env.cr).execute


def _execute_timed(self, query, params=None, log_exceptions=None):
    started = time.perf_counter()
    try:
        return _SQL_ORIGINAL(self, query, params, log_exceptions)
    finally:
        SQL["ms"] += (time.perf_counter() - started) * 1000.0
        SQL["count"] += 1


type(env.cr).execute = _execute_timed

_ORIGINAL_IP_REQUEST = ip.request
_ORIGINAL_ROUTER_REQUEST = intent_router.request

DEEPCOPY = {"count": 0, "sites": {}}
_DEEPCOPY_ORIGINAL = copy.deepcopy


def _deepcopy_counted(value, *args, **kwargs):
    caller = sys._getframe(1)
    site = "%s:%s" % (Path(caller.f_code.co_filename).name, caller.f_code.co_name)
    DEEPCOPY["count"] += 1
    DEEPCOPY["sites"][site] = DEEPCOPY["sites"].get(site, 0) + 1
    return _DEEPCOPY_ORIGINAL(value, *args, **kwargs)


copy.deepcopy = _deepcopy_counted

# Seal-stage attribution: the hot-hit path runs exactly ``seal_runtime_contract``
# between the record-overlay point and the meta assembly, so timing its three
# callees shows what the reproducible ~20 ms of ``v2_projection_and_seal`` is.
authority = __import__("odoo.addons.smart_core.handlers.ui_contract_v2_authority", fromlist=["x"])
SEAL = {"ms": {}, "counts": {}}


def _wrap_authority(attr):
    original = getattr(authority, attr)

    def wrapper(*args, **kwargs):
        started = time.perf_counter()
        try:
            return original(*args, **kwargs)
        finally:
            SEAL["ms"][attr] = SEAL["ms"].get(attr, 0.0) + (time.perf_counter() - started) * 1000.0
            SEAL["counts"][attr] = SEAL["counts"].get(attr, 0) + 1

    wrapper.__wrapped__ = original
    setattr(authority, attr, wrapper)


for _attr in ("seal_runtime_contract", "seal_unified_page_contract", "emit_delivery_observation"):
    _wrap_authority(_attr)

# ``refresh_saved_search_runtime`` is a model method the seal calls back into.
_search_model = type(actor["app.search.config"])
_search_runtime_original = _search_model.refresh_saved_search_runtime


def _refresh_saved_search_timed(self, *args, **kwargs):
    started = time.perf_counter()
    try:
        return _search_runtime_original(self, *args, **kwargs)
    finally:
        SEAL["ms"]["refresh_saved_search_runtime"] = (
            SEAL["ms"].get("refresh_saved_search_runtime", 0.0) + (time.perf_counter() - started) * 1000.0
        )
        SEAL["counts"]["refresh_saved_search_runtime"] = SEAL["counts"].get("refresh_saved_search_runtime", 0) + 1


_search_model.refresh_saved_search_runtime = _refresh_saved_search_timed

# ``authority_and_cache_lookup`` is "everything before the source-cache read", so
# it is timed again from the inside: one-off pauses are attributed to a concrete
# member call, and CPython's own collection counters say whether that pause is a
# garbage-collection stop rather than product work.
GC_STATE = {"ms": 0.0, "start": 0.0, "collections": {0: 0, 1: 0, 2: 0}, "collected": 0}


def _gc_callback(phase, info):
    if phase == "start":
        GC_STATE["start"] = time.perf_counter()
        return
    GC_STATE["ms"] += (time.perf_counter() - GC_STATE["start"]) * 1000.0
    generation = int(info.get("generation", -1))
    GC_STATE["collections"][generation] = GC_STATE["collections"].get(generation, 0) + 1
    GC_STATE["collected"] += int(info.get("collected") or 0)


gc.callbacks.append(_gc_callback)

PRELOOKUP = {"ms": {}}


def _timed(container, name, original):
    def wrapper(*args, **kwargs):
        started = time.perf_counter()
        try:
            return original(*args, **kwargs)
        finally:
            container[name] = container.get(name, 0.0) + (time.perf_counter() - started) * 1000.0

    wrapper.__wrapped__ = original
    return wrapper


# The handler binds these names at import time, so the module namespace of the
# handler is the patch target (patching ``lcrc`` alone would not be observed).
_handler_module = __import__("odoo.addons.smart_core.handlers.ui_contract_v2", fromlist=["x"])
for _name in (
    "build_projection_cache_key",
    "build_projection_source_token",
    "projection_role_code",
    "get_runtime_source_asset",
):
    setattr(_handler_module, _name, _timed(PRELOOKUP["ms"], _name, getattr(_handler_module, _name)))
lcrc.contract_code_fingerprint = _timed(
    PRELOOKUP["ms"], "contract_code_fingerprint", lcrc.contract_code_fingerprint
)

_cache_type = type(lcrc.CONTRACT_PROJECTION_HOT_CACHE)
_cache_type.get = _timed(PRELOOKUP["ms"], "CONTRACT_PROJECTION_HOT_CACHE.get", _cache_type.get)

_handler_cls = _handler_module.UiContractV2Handler
for _name in (
    "_trim_limit_params",
    "_ui_contract_params",
    "_validate_scene_action_binding",
    "_validate_form_record",
):
    setattr(_handler_cls, _name, _timed(PRELOOKUP["ms"], _name, getattr(_handler_cls, _name)))


def _payload(params):
    return {
        "intent": INTENT,
        "params": dict(params),
        "context": {"allowed_company_ids": [company], "lang": "zh_CN"},
        "meta": {},
    }


def _sample(params, phase):
    """Run one real permission + router/handler pass on the fixed identity."""
    payload = _payload(params)
    SQL["count"] = 0
    SQL["ms"] = 0.0
    DEEPCOPY["count"] = 0
    DEEPCOPY["sites"] = {}
    SEAL["ms"] = {}
    SEAL["counts"] = {}
    GC_STATE["ms"] = 0.0
    GC_STATE["collections"] = {0: 0, 1: 0, 2: 0}
    GC_STATE["collected"] = 0
    PRELOOKUP["ms"].clear()
    ctx = RequestContext(actor, user, dict(params), request_obj=shim, principal=PRINCIPAL)
    ip.request = shim
    intent_router.request = shim
    dispatch_times = []
    error = None
    result = None
    try:
        started = time.perf_counter()
        ok = bool(ip.check_intent_permission(ctx))
        perm_ms = (time.perf_counter() - started) * 1000.0
        started = time.perf_counter()
        result = intent_router.route_intent_payload(
            payload, ctx=ctx, observe=lambda name, duration: dispatch_times.append((name, duration))
        )
        dispatch_ms = (time.perf_counter() - started) * 1000.0
    except Exception as exc:
        error = "%s: %s" % (type(exc).__name__, exc)
        ok = False
        perm_ms = dispatch_ms = None
    finally:
        ip.request = _ORIGINAL_IP_REQUEST
        intent_router.request = _ORIGINAL_ROUTER_REQUEST
    meta = (result or {}).get("meta") or {}
    projection = meta.get("projection_cache") or {}
    serializable = result.to_legacy_dict() if hasattr(result, "to_legacy_dict") else result
    response = json.dumps(serializable, sort_keys=True, default=str) if serializable is not None else ""
    return {
        "phase": phase,
        "ok": ok,
        "error": error,
        "permission_ms": round(perm_ms, 3) if perm_ms is not None else None,
        "dispatch_ms": round(dispatch_ms, 3) if dispatch_ms is not None else None,
        "dispatch_segments_ms": {name: round(duration, 3) for name, duration in dispatch_times},
        "sql_count": SQL["count"],
        "sql_ms": round(SQL["ms"], 3),
        "deepcopy_count": DEEPCOPY["count"],
        "deepcopy_sites": dict(sorted(DEEPCOPY["sites"].items(), key=lambda row: -row[1])[:8]),
        "seal_ms": {name: round(value, 3) for name, value in SEAL["ms"].items()},
        "seal_counts": dict(SEAL["counts"]),
        "prelookup_ms": {name: round(value, 3) for name, value in PRELOOKUP["ms"].items()},
        "gc_ms": round(GC_STATE["ms"], 3),
        "gc_collections": dict(GC_STATE["collections"]),
        "gc_collected": GC_STATE["collected"],
        "cache_status": projection.get("status"),
        "cache_reason": projection.get("reason"),
        "cache_identity_ref": projection.get("identity_ref"),
        "cache_source_ref": projection.get("source_ref"),
        "cache_asset_write_succeeded": projection.get("asset_write_succeeded"),
        "cache_stages_ms": projection.get("stages_ms"),
        "response_bytes": len(response),
        "response_sha256": hashlib.sha256(response.encode("utf-8")).hexdigest() if response else None,
    }


def _stats(samples, key):
    return _stats_values([sample[key] for sample in samples if isinstance(sample.get(key), (int, float))])


def _stats_values(raw_values):
    values = sorted(raw_values)
    if not values:
        return None
    index = min(len(values) - 1, int(round(0.95 * (len(values) - 1))))
    return {
        "n": len(values),
        "min": values[0],
        "median": values[len(values) // 2],
        "p95": values[index],
        "max": values[-1],
        "samples": values,
    }


SAMPLES = {}

# 1. Process-first observation on the fixed identity (populates caches).
SAMPLES["process_first"] = [_sample(BASE_PARAMS, "process_first")]
# 2. Steady state: identical request repeated; a real hit series, not one sample.
SAMPLES["hot"] = [_sample(BASE_PARAMS, "hot_%d" % index) for index in range(1, HOT_SAMPLES + 1)]
# 2b. Paired control: the very same fixed request with CPython's automatic
# collection switched off. A one-off pause that disappears here is a
# garbage-collection stop, not product work; it runs second on the already
# grown heap, which is the condition that triggers generation-2 passes.
gc.collect()
gc.disable()
SAMPLES["hot_gc_off"] = [
    _sample(BASE_PARAMS, "hot_gc_off_%d" % index) for index in range(1, HOT_SAMPLES + 1)
]
gc.enable()
# R3 direct benefit: the two copies the handler used to make on the hot path are
# re-measured here on the live cached entry, so the removed work has a real
# number instead of an inference. The originals (not the counting wrapper) are
# used so no reported counter is disturbed.
REMOVED_COPY = {"samples_ms": {}}
try:
    _live_entry = None
    for _candidate in lcrc.CONTRACT_PROJECTION_HOT_CACHE._entries.values():
        if isinstance(_candidate[2], dict) and _candidate[2].get("_assembled_v2"):
            _live_entry = _candidate[2]
            break
    if _live_entry is None:
        REMOVED_COPY["error"] = "no assembled hot entry available"
    else:
        for _key in ("source_contract", "contract"):
            _target = (_live_entry.get("_assembled_v2") or {}).get(_key)
            if not isinstance(_target, dict):
                continue
            _timings = []
            for _ in range(5):
                _started = time.perf_counter()
                _DEEPCOPY_ORIGINAL(_target)
                _timings.append(round((time.perf_counter() - _started) * 1000.0, 3))
            REMOVED_COPY["samples_ms"][_key] = sorted(_timings)
except Exception as exc:  # diagnostic only: never fail the observation
    REMOVED_COPY["error"] = "%s: %s" % (type(exc).__name__, exc)
# 3. Identity variation: same surface, different projection identity.
SAMPLES["variant"] = [_sample(VARIANT_PARAMS, "variant_%d" % index) for index in range(1, 3)]
# 4. Cold rebuild: registry caches and the process-local hot cache both cleared.
env.registry.clear_cache()
lcrc.CONTRACT_PROJECTION_HOT_CACHE.clear()
SAMPLES["cold_rebuild"] = [_sample(BASE_PARAMS, "cold_rebuild_1")]

REPORT["request"] = {
    "intent": INTENT,
    "action_id": ACTION_ID,
    "observed_menu_carrier_id": CARRIER,
    "company_id": company,
    "scenarios": {name: dict(params) for name, params in SCENARIOS.items()},
}
REPORT["identity"] = {
    "principal": {"xmlid": "smart_construction_demo.user_demo_role_finance", "uid": user.id,
                  "company_id": company, "sudo": bool(actor.su)},
    "handlers/ui_contract_v2.py": _source_hash("handlers/ui_contract_v2.py"),
    "utils/load_contract_response_cache.py": _source_hash("utils/load_contract_response_cache.py"),
    "app_config_engine/services/assemblers/page_assembler.py": _source_hash("app_config_engine/services/assemblers/page_assembler.py"),
    "core/intent_router.py": _source_hash("core/intent_router.py"),
    "controllers/intent_dispatcher.py": _source_hash("controllers/intent_dispatcher.py"),
}
REPORT["samples"] = SAMPLES
HOT = SAMPLES["hot"]
CONTROL = SAMPLES["hot_gc_off"]
_hot_dispatch = sorted(sample["dispatch_ms"] for sample in HOT)
_hot_median = _hot_dispatch[len(_hot_dispatch) // 2]
_outlier = max(HOT, key=lambda sample: sample["dispatch_ms"])
_outlier_extra = round(_outlier["dispatch_ms"] - _hot_median, 3)
_control_dispatch = sorted(sample["dispatch_ms"] for sample in CONTROL)
_control_outlier = max(CONTROL, key=lambda sample: sample["dispatch_ms"])
_control_extra = round(
    _control_outlier["dispatch_ms"] - _control_dispatch[len(_control_dispatch) // 2], 3
)
REPORT["stats"] = {
    "hot_permission_ms": _stats(HOT, "permission_ms"),
    "hot_dispatch_ms": _stats(HOT, "dispatch_ms"),
    "hot_sql_count": _stats(HOT, "sql_count"),
    "hot_deepcopy_count": _stats(HOT, "deepcopy_count"),
    "hot_response_bytes": _stats(HOT, "response_bytes"),
    "hot_gc_ms": _stats(HOT, "gc_ms"),
    "hot_lookup_ms": _stats_values(
        [
            sample["cache_stages_ms"].get("authority_and_cache_lookup")
            for sample in HOT
            if isinstance(sample.get("cache_stages_ms"), dict)
            and isinstance(sample["cache_stages_ms"].get("authority_and_cache_lookup"), (int, float))
        ]
    ),
    "hot_outlier_gc_ms": _stats_values([_outlier["gc_ms"]]),
    "hot_gc_off_dispatch_ms": _stats(CONTROL, "dispatch_ms"),
    "hot_gc_off_gc_ms": _stats(CONTROL, "gc_ms"),
    "hot_gc_off_permission_ms": _stats(CONTROL, "permission_ms"),
    "hot_gc_off_sql_count": _stats(CONTROL, "sql_count"),
}
REPORT["gc_control"] = {
    "gc_enabled_group": "hot",
    "gc_disabled_group": "hot_gc_off",
    "control_is_paired_in_one_process": True,
}
REPORT["r3_removed_copy_ms"] = REMOVED_COPY
REPORT["hot_outlier"] = {
    "phase": _outlier["phase"],
    "dispatch_ms": _outlier["dispatch_ms"],
    "extra_over_median_ms": _outlier_extra,
    "gc_ms": _outlier["gc_ms"],
    "gc_collections": _outlier["gc_collections"],
    "lookup_ms": (_outlier.get("cache_stages_ms") or {}).get("authority_and_cache_lookup"),
    "seal_ms": (_outlier.get("seal_ms") or {}).get("seal_runtime_contract"),
    "sql_count": _outlier["sql_count"],
    "deepcopy_count": _outlier["deepcopy_count"],
    "prelookup_ms": _outlier.get("prelookup_ms"),
}
REPORT["hot_gc_off_outlier"] = {
    "phase": _control_outlier["phase"],
    "dispatch_ms": _control_outlier["dispatch_ms"],
    "extra_over_median_ms": _control_extra,
    "gc_ms": _control_outlier["gc_ms"],
    "lookup_ms": (_control_outlier.get("cache_stages_ms") or {}).get("authority_and_cache_lookup"),
    "sql_count": _control_outlier["sql_count"],
}
REPORT["cache_reasons"] = {
    name: [sample["cache_reason"] for sample in samples] for name, samples in SAMPLES.items()
}
REPORT["findings"] = {
    "hot_request_is_a_cache_hit": all(sample["cache_status"] == "hot" for sample in HOT),
    "cold_rebuild_is_much_slower_than_hot": (
        SAMPLES["cold_rebuild"][0]["dispatch_ms"] > 4 * REPORT["stats"]["hot_dispatch_ms"]["median"]
    ),
    "permission_is_not_the_per_request_cost": REPORT["stats"]["hot_permission_ms"]["median"] < 5.0,
    "variant_identity_differs_from_base": (
        SAMPLES["variant"][0]["cache_identity_ref"] != HOT[-1]["cache_identity_ref"]
    ),
    "hot_outlier_is_a_python_gc_pause": bool(
        _outlier_extra >= 20.0 and _outlier["gc_ms"] >= 0.5 * _outlier_extra
    ),
    "hot_outlier_phase": _outlier["phase"],
    "hot_outlier_extra_over_median_ms": _outlier_extra,
    "hot_gc_off_removes_the_one_off_pause": bool(
        _outlier_extra >= 20.0 and _control_extra < 0.5 * _outlier_extra
    ),
    "hot_gc_off_outlier_extra_over_median_ms": _control_extra,
    "warm_key_cost_is_the_group_signature": None,  # filled below from the R4 attribution when present
}
REPORT["limitations"] = [
    "in-process probe on the registered local demo finance principal and one fixed ui.contract.v2 request",
    "the probe shims odoo.http.request; controller ingress/session/transport and the context_auth/json_response phases are out of scope",
    "registry.clear_cache() and the process-local hot-cache clear affect only this throwaway odoo shell process",
    "the gc-disabled group is a paired in-process discrimination control for one-off pauses; it is not a product configuration suggestion",
    "not an SLO, capacity, cross-role or release claim; no freeze, commit, push or deployment",
]

env.cr.rollback()
env.cr.commit = _ORIGINAL_COMMIT
print("CONTRACT_REQUEST_PROBE_REPORT " + json.dumps(REPORT, ensure_ascii=False, sort_keys=True))
