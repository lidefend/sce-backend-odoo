"""Bounded per-request allocation attribution for one hot ui.contract.v2 request (P4 diagnostic).

Answers one question with runtime evidence: the assembled hot read still triggers
about 13-14 generation-0 collections per request. On CPython 3.12
``gc.get_count()[0]`` is the number of *net surviving* tracked containers since the
last generation-0 collection, so a generation-0 pass fires every ~700 net-retained
containers. This probe therefore measures, for one fixed identity and one fixed
request, how many net container allocations each stage retains, and where inside the
request they are produced.

Two passes on the same identity:

* an enabled pass (``gc`` on) that records the real generation-0/1/2 distribution and
  the dispatch time, i.e. the phenomenon to explain;
* a disabled pass (``gc`` off) that wraps a curated set of existing product callables
  and attributes the net-retained container delta to each one with a nesting-aware
  exclusive split, so the sum plus an explicit residual is the whole request.

Read-only: commit is refused, the probe rolls back, and it changes no product code,
schema, fixture or ACL. It only reads the current candidate through the registered
local demo finance principal. The wrappers exist in this throwaway ``odoo shell``
process only and never alter the values they return.
"""
import gc
import hashlib
import inspect
import json
import os
import time
from pathlib import Path
from types import SimpleNamespace

from odoo import api
from odoo.addons.smart_core.core.context import RequestContext
from odoo.addons.smart_core.core import intent_router
from odoo.addons.smart_core.security import intent_permission as ip
from odoo.addons.smart_core.utils import load_contract_response_cache as lcrc

DATABASE = "sc_dev_demo"
ACTION_ID = int(os.environ.get("PRODUCT_PERFORMANCE_PREFERENCE_ACTION_ID") or 878)
INTENT = "ui.contract.v2"
WARMUP = 3
ENABLED_SAMPLES = 12
DISABLED_SAMPLES = 3

assert env.cr.dbname == DATABASE, "registered local.dev database required"
env.cr.rollback()
_ORIGINAL_COMMIT = env.cr.commit


def _refuse_commit(*_args, **_kwargs):
    raise RuntimeError("allocation attribution probe forbids commit")


env.cr.commit = _refuse_commit

REPORT = {"schema": "runtime-allocation-attribution-probe/v1", "database": DATABASE}


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
PRINCIPAL = {
    "auth_method": "password",
    "principal_type": "human",
    "user_id": user.id,
    "payload": {"db": DATABASE},
}
_ORIGINAL_IP_REQUEST = ip.request
_ORIGINAL_ROUTER_REQUEST = intent_router.request


def _payload(params):
    return {
        "intent": INTENT,
        "params": dict(params),
        "context": {"allowed_company_ids": [company], "lang": "zh_CN"},
        "meta": {},
    }


# --- generation-0 observation for the enabled pass ---------------------------
GC_STATE = {"ms": 0.0, "start": 0.0, "collections": {0: 0, 1: 0, 2: 0}, "collected": 0}


def _gc_callback(phase, info):
    generation = int(info.get("generation") or 0)
    if phase == "start":
        GC_STATE["start"] = time.perf_counter()
    else:
        GC_STATE["ms"] += (time.perf_counter() - GC_STATE["start"]) * 1000.0
        GC_STATE["collections"][generation] = GC_STATE["collections"].get(generation, 0) + 1
        GC_STATE["collected"] += int(info.get("collected") or 0)


gc.callbacks.append(_gc_callback)


# --- nesting-aware net-container attribution for the disabled pass -----------
ALLOC = {"active": False, "exclusive": {}, "inclusive": {}, "order": [], "frames": []}


def _alloc_wrap(function, label):
    def wrapper(*args, **kwargs):
        if not ALLOC["active"]:
            return function(*args, **kwargs)
        frame = {"label": label, "before": gc.get_count()[0], "children": []}
        ALLOC["frames"].append(frame)
        try:
            return function(*args, **kwargs)
        finally:
            after = gc.get_count()[0]
            ALLOC["frames"].pop()
            inclusive = after - frame["before"]
            child_sum = sum(child["inclusive"] for child in frame["children"])
            ALLOC["inclusive"][label] = ALLOC["inclusive"].get(label, 0) + inclusive
            ALLOC["exclusive"][label] = ALLOC["exclusive"].get(label, 0) + (inclusive - child_sum)
            ALLOC["order"].append(label)
            if ALLOC["frames"]:
                ALLOC["frames"][-1]["children"].append({"label": label, "inclusive": inclusive})

    wrapper.__wrapped__ = function
    return wrapper


_handler_module = __import__("odoo.addons.smart_core.handlers.ui_contract_v2", fromlist=["x"])
_authority_module = __import__(
    "odoo.addons.smart_core.handlers.ui_contract_v2_authority", fromlist=["x"]
)
_lifecycle_module = __import__("odoo.addons.smart_core.core.contract_lifecycle", fromlist=["x"])
_scene_registry = __import__(
    "odoo.addons.smart_construction_scene.scene_registry", fromlist=["x"]
)

_handler_cls = _handler_module.UiContractV2Handler
_cache_type = type(lcrc.CONTRACT_PROJECTION_HOT_CACHE)

for _name in (
    "build_projection_cache_key",
    "build_projection_source_token",
    "projection_role_code",
    "get_runtime_source_asset",
    "load_scenes_from_db_or_fallback",
):
    setattr(
        _handler_module,
        _name,
        _alloc_wrap(getattr(_handler_module, _name), "handler:" + _name),
    )
for _name in (
    "_trim_limit_params",
    "_ui_contract_params",
    "_validate_scene_action_binding",
    "_validate_form_record",
    "_handle_contract",
):
    setattr(_handler_cls, _name, _alloc_wrap(getattr(_handler_cls, _name), "handler." + _name))
for _name in ("get_assembled", "get"):
    setattr(_cache_type, _name, _alloc_wrap(getattr(_cache_type, _name), "cache." + _name))
for _name in ("seal_runtime_contract", "emit_delivery_observation", "project_action_group_entitlements"):
    setattr(_authority_module, _name, _alloc_wrap(getattr(_authority_module, _name), "authority:" + _name))
for _name in ("seal_unified_page_contract", "verify_unified_page_contract_integrity"):
    setattr(_lifecycle_module, _name, _alloc_wrap(getattr(_lifecycle_module, _name), "lifecycle:" + _name))
setattr(ip, "check_intent_permission", _alloc_wrap(ip.check_intent_permission, "permission"))
setattr(intent_router, "route_intent_payload", _alloc_wrap(intent_router.route_intent_payload, "router.route_intent_payload"))
_scene_registry.load_scene_configs_with_timings = _alloc_wrap(
    _scene_registry.load_scene_configs_with_timings, "scene:load_scene_configs_with_timings"
)


def _graph_containers(value, cap=400000):
    """Dedup container count of a JSON-like graph; bounded and read-only."""
    seen = set()
    stack = [value]
    containers = 0
    while stack:
        node = stack.pop()
        if isinstance(node, (dict, list)):
            key = id(node)
            if key in seen:
                continue
            seen.add(key)
            containers += 1
            if containers > cap:
                return {"capped": True, "containers": containers}
            stack.extend(node.values() if isinstance(node, dict) else node)
    return {"capped": False, "containers": containers}


def _run_request(params, capture_disabled=False):
    """One real permission + router/handler pass on the fixed identity."""
    ctx = RequestContext(actor, user, dict(params), request_obj=shim, principal=PRINCIPAL)
    ip.request = shim
    intent_router.request = shim
    payload = _payload(params)
    started_alloc = gc.get_count()[0] if capture_disabled else None
    enabled_before = dict(GC_STATE["collections"])
    GC_STATE["ms"] = 0.0
    GC_STATE["collected"] = 0
    error = None
    result = None
    payload_bytes = None
    delivered_containers = None
    try:
        started = time.perf_counter()
        ok = bool(ip.check_intent_permission(ctx))
        permission_ms = (time.perf_counter() - started) * 1000.0
        started = time.perf_counter()
        result = intent_router.route_intent_payload(payload, ctx=ctx)
        dispatch_ms = (time.perf_counter() - started) * 1000.0
    except Exception as exc:
        error = "%s: %s" % (type(exc).__name__, exc)
        ok = False
        permission_ms = dispatch_ms = None
    finally:
        ip.request = _ORIGINAL_IP_REQUEST
        intent_router.request = _ORIGINAL_ROUTER_REQUEST
    serializable = result.to_legacy_dict() if hasattr(result, "to_legacy_dict") else result
    response = json.dumps(serializable, sort_keys=True, default=str) if serializable is not None else ""
    total_net = (gc.get_count()[0] - started_alloc) if capture_disabled else None
    if serializable is not None:
        payload_bytes = len(response)
        delivered_containers = _graph_containers(serializable.get("data") if isinstance(serializable, dict) else serializable)
    collections = {
        str(gen): GC_STATE["collections"].get(gen, 0) - enabled_before.get(gen, 0)
        for gen in (0, 1, 2)
    }
    return {
        "ok": ok,
        "error": error,
        "permission_ms": round(permission_ms, 3) if permission_ms is not None else None,
        "dispatch_ms": round(dispatch_ms, 3) if dispatch_ms is not None else None,
        "gc_collections": collections,
        "gc_ms": round(GC_STATE["ms"], 3),
        "gc_collected": GC_STATE["collected"],
        "total_net_containers": total_net,
        "delivered_containers": delivered_containers,
        "delivered_json_bytes": payload_bytes,
        "response_sha256": hashlib.sha256(response.encode("utf-8")).hexdigest() if response else None,
    }


def _reset_alloc():
    ALLOC["exclusive"] = {}
    ALLOC["inclusive"] = {}
    ALLOC["order"] = []
    ALLOC["frames"] = []


# --- warm the assembled cache on the fixed identity --------------------------
warmups = [_run_request(BASE_PARAMS) for _ in range(WARMUP)]

# --- enabled pass: the phenomenon (real generation distribution) -------------
enabled = [_run_request(BASE_PARAMS) for _ in range(ENABLED_SAMPLES)]

# --- disabled pass: attribution of the net-retained container delta ----------
gc.collect()
gc.disable()
disabled = []
try:
    for _ in range(DISABLED_SAMPLES):
        _reset_alloc()
        ALLOC["active"] = True
        try:
            row = _run_request(BASE_PARAMS, capture_disabled=True)
        finally:
            ALLOC["active"] = False
        row["exclusive_containers"] = dict(sorted(ALLOC["exclusive"].items(), key=lambda kv: -kv[1]))
        row["inclusive_containers"] = dict(sorted(ALLOC["inclusive"].items(), key=lambda kv: -kv[1]))
        row["wrapped_calls"] = list(ALLOC["order"])
        row["attributed_exclusive_sum"] = sum(ALLOC["exclusive"].values())
        if isinstance(row["total_net_containers"], int):
            row["unattributed_containers"] = row["total_net_containers"] - row["attributed_exclusive_sum"]
        disabled.append(row)
finally:
    gc.enable()


def _median(values):
    ordered = sorted(values)
    if not ordered:
        return None
    return ordered[len(ordered) // 2]


_excl = {}
for _row in disabled:
    for _label, _value in (_row.get("exclusive_containers") or {}).items():
        _excl.setdefault(_label, []).append(_value)
_excl_median = {label: _median(values) for label, values in sorted(_excl.items(), key=lambda kv: -_median(kv[1]))}

REPORT["request"] = {
    "intent": INTENT,
    "action_id": ACTION_ID,
    "observed_menu_carrier_id": CARRIER,
    "company_id": company,
    "params": dict(BASE_PARAMS),
    "source_sha256": {
        "handlers/ui_contract_v2.py": _source_hash("handlers/ui_contract_v2.py"),
        "handlers/ui_contract_v2_authority.py": _source_hash("handlers/ui_contract_v2_authority.py"),
        "utils/load_contract_response_cache.py": _source_hash("utils/load_contract_response_cache.py"),
    },
}
REPORT["identity"] = {"user_id": user.id, "login": user.login, "company_id": company, "su": bool(actor.su)}
REPORT["warmup"] = {"requests": WARMUP, "dispatch_ms": [row["dispatch_ms"] for row in warmups]}
REPORT["enabled_pass"] = {
    "samples": ENABLED_SAMPLES,
    "dispatch_ms": [row["dispatch_ms"] for row in enabled],
    "dispatch_median_ms": _median([row["dispatch_ms"] for row in enabled if row["dispatch_ms"] is not None]),
    "permission_ms": [row["permission_ms"] for row in enabled],
    "gen0": [row["gc_collections"]["0"] for row in enabled],
    "gen1": [row["gc_collections"]["1"] for row in enabled],
    "gen2": [row["gc_collections"]["2"] for row in enabled],
    "gc_ms": [row["gc_ms"] for row in enabled],
    "delivered_json_bytes": [row["delivered_json_bytes"] for row in enabled],
    "response_sha256_distinct": len({row["response_sha256"] for row in enabled}),
}
_total_net = [row["total_net_containers"] for row in disabled if isinstance(row["total_net_containers"], int)]
REPORT["disabled_pass"] = {
    "samples": DISABLED_SAMPLES,
    "total_net_containers": [row["total_net_containers"] for row in disabled],
    "total_net_median": _median(_total_net),
    "implied_gen0": round(_median(_total_net) / 700.0, 2) if _total_net else None,
    "attributed_exclusive_sum": [row["attributed_exclusive_sum"] for row in disabled],
    "unattributed_containers": [row.get("unattributed_containers") for row in disabled],
    "delivered_containers": [row.get("delivered_containers") for row in disabled],
    "exclusive_median_containers": _excl_median,
    "inclusive_per_sample": [row["inclusive_containers"] for row in disabled],
    "dispatch_ms": [row["dispatch_ms"] for row in disabled],
}
REPORT["note"] = (
    "gc.get_count()[0] on CPython 3.12 is the net count of surviving tracked containers since the "
    "last generation-0 collection; with gc disabled it is a monotone-enough accumulator whose delta "
    "attributes retained container growth to each wrapped callable (nesting-aware exclusive split). "
    "enabled_pass shows the real generation distribution; disabled_pass explains its size. Values are "
    "read-only observations of the current candidate, not a pass/fail gate."
)

env.cr.rollback()
env.cr.commit = _ORIGINAL_COMMIT
print("ALLOCATION_ATTRIBUTION_REPORT " + json.dumps(REPORT, ensure_ascii=False, sort_keys=True))
