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
# Diagnostic-only binding check: for every seal call the probe records the
# digests the seal was asked to reuse and the digests it would have computed
# itself over the very payload objects it received. ``quiet`` suppresses the
# lifecycle counters while that recomputation runs, so the helper measures
# identity instead of polluting the per-request digests it is checking.
SEAL_BINDING = {"quiet": False, "rows": [], "call_index": 0, "recompute_ms": 0.0}


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


for _attr in ("seal_unified_page_contract", "emit_delivery_observation"):
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

# ``seal_runtime_contract`` is the one per-request cost that survives a hot cache
# hit besides the lookup itself, and its body rebuilds the whole delivered graph
# twice: ``build_lifecycle_evidence`` runs ``strip_request_transport_identity``
# over the contract and over the source payload, and hashes each with
# ``canonical_json`` + sha256. Timing those three module-level names separates
# "recomputing a request-invariant digest" from the rest of the seal, instead of
# inferring it from the outer frame. ``payload_sha256`` calls ``canonical_json``
# in the same module namespace, so the payload entry contains the canonical one.
LIFECYCLE = {"ms": {}, "counts": {}, "callers": {}, "max_nodes": 0}
_lifecycle_module = __import__("odoo.addons.smart_core.core.contract_lifecycle", fromlist=["x"])
# ``strip_request_transport_identity`` recurses through the global name, so a
# naive counter records every node of the graph (~46k per request) and every
# level's duration would then contain its whole subtree. A re-entrancy guard
# makes the counters mean "top-level invocations" and the timings mean "the
# outermost call", which is the number that can be read against the request.
_LIFECYCLE_DEPTH = {"n": 0}
_LIFECYCLE_ORIGINALS = {}
_LIFECYCLE_PATCHED = {}
for _name in ("payload_sha256", "strip_request_transport_identity", "canonical_json"):
    _original = getattr(_lifecycle_module, _name)

    def _lifecycle_wrapper(*args, _name=_name, _original=_original, **kwargs):
        if _LIFECYCLE_DEPTH["n"] or SEAL_BINDING["quiet"]:
            return _original(*args, **kwargs)
        _LIFECYCLE_DEPTH["n"] += 1
        if _name == "payload_sha256":
            _caller = sys._getframe(1)
            _site = "%s:%s" % (Path(_caller.f_code.co_filename).name, _caller.f_code.co_name)
            LIFECYCLE["callers"][_site] = LIFECYCLE["callers"].get(_site, 0) + 1
        _started = time.perf_counter()
        try:
            return _original(*args, **kwargs)
        finally:
            _LIFECYCLE_DEPTH["n"] -= 1
            LIFECYCLE["ms"][_name] = LIFECYCLE["ms"].get(_name, 0.0) + (time.perf_counter() - _started) * 1000.0
            LIFECYCLE["counts"][_name] = LIFECYCLE["counts"].get(_name, 0) + 1

    _lifecycle_wrapper.__wrapped__ = _original
    _LIFECYCLE_ORIGINALS[_name] = _original
    _LIFECYCLE_PATCHED[_name] = _lifecycle_wrapper
    setattr(_lifecycle_module, _name, _lifecycle_wrapper)


_SHORT_DIGEST_LIMIT = 120
_TOP_KEY_LIMIT = 40


def _short_digest(canonical, value):
    try:
        return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()[:16]
    except Exception as exc:  # diagnostic only
        return "<%s>" % type(exc).__name__


_SHAPE_FOCUS_KEYS = ("business_form_policy", "source_meta")


def _ordered_shape(canonical, value, member_limit=8):
    """Tell "same members, different order" apart from "different members".

    A list whose sorted member digests match while its sequence digest does not
    is an ordering difference only; that is what a process-scoped iteration over
    a string set looks like. Anything else is a content difference.
    """
    if isinstance(value, list):
        members = [_short_digest(canonical, item) for item in value]
        return {
            "type": "list",
            "count": len(members),
            "member_digests": members[:member_limit],
            "sorted_member_digests": sorted(members)[:member_limit],
            "order_digest": hashlib.sha256("|".join(members).encode("utf-8")).hexdigest()[:16],
            "member_set_digest": hashlib.sha256("|".join(sorted(members)).encode("utf-8")).hexdigest()[:16],
        }
    if isinstance(value, dict):
        return {"type": "dict", "count": len(value), "keys": sorted(str(key) for key in value)[:member_limit]}
    return {"type": type(value).__name__}


def _focused_shape(original_canonical, payload):
    if not isinstance(payload, dict):
        return {}
    out = {}
    for key in _SHAPE_FOCUS_KEYS:
        value = payload.get(key)
        if not isinstance(value, dict):
            continue
        entry = {"keys": sorted(str(sub) for sub in value)}
        for sub in sorted(value)[:40]:
            entry[str(sub)] = _ordered_shape(original_canonical, value[sub])
        out[key] = entry
    return out


_PATH_MAP_DEPTH = 4
_PATH_MAP_MAX = 1400


def _path_digest_map(original_canonical, payload):
    """Flat ``path -> digest`` map of the payload, so the deepest differing path
    names the volatile value instead of only its top-level ancestor."""
    paths = {}

    def walk(node, path, depth):
        if len(paths) >= _PATH_MAP_MAX:
            return
        paths[path or "$"] = _short_digest(original_canonical, node)
        if depth >= _PATH_MAP_DEPTH:
            return
        if isinstance(node, dict):
            for key in sorted(node):
                walk(node[key], "%s.%s" % (path, key) if path else str(key), depth + 1)
        elif isinstance(node, list):
            for index, item in enumerate(node[:24]):
                walk(item, "%s[%d]" % (path, index), depth + 1)

    walk(payload, "", 0)
    return {"paths": paths, "node_count": len(paths), "truncated": len(paths) >= _PATH_MAP_MAX}


_UNSORTED_SCAN_NODES = 60000
_UNSORTED_REPORT_MAX = 600


def _unsorted_list_map(original_canonical, payload):
    """Every scalar list whose order is not sorted, with its order digest.

    A list built as ``list(some_set)`` is exactly this shape: a member set with
    no declared order. Comparing these digests across processes shows which of
    them actually move with the process hash seed.
    """
    out = {}
    visited = [0]

    def walk(node, path):
        if visited[0] >= _UNSORTED_SCAN_NODES:
            return
        visited[0] += 1
        if isinstance(node, dict):
            for key in node:
                walk(node[key], "%s.%s" % (path, key) if path else str(key))
        elif isinstance(node, list):
            if node and all(isinstance(item, (str, int, float)) for item in node):
                if list(node) != sorted(node, key=lambda value: str(value)):
                    if len(out) < _UNSORTED_REPORT_MAX:
                        out[path or "$"] = {
                            "digest": _short_digest(original_canonical, node),
                            "set_like": list(node) == list(set(node)),
                            "count": len(node),
                        }
            for index, item in enumerate(node[:24]):
                walk(item, "%s[%d]" % (path, index))

    walk(payload, "")
    return {"count": len(out), "ordered_digests": out, "nodes_scanned": visited[0]}


_FULL_INDEX = {}


def _tree_digest_index(payload):
    """Path -> bottom-up structural digest for the whole payload, no truncation.

    ``_path_digest_map`` is bounded at depth 4 and 1400 nodes and
    ``_unsorted_list_map`` only inspects all-scalar lists, so a volatile value
    deeper than that, past the node cap, or inside a list of containers stays
    invisible. This index walks every node, folds each subtree into its own
    digest in one pass, and records it by path so a cross-process diff names the
    exact differing path instead of only its top-level ancestor. Digests are
    diagnostic identity tokens, never exported values.
    """
    out = {}

    def walk(node, path):
        if isinstance(node, dict):
            parts = []
            for key in sorted(node, key=lambda item: str(item)):
                child = walk(node[key], "%s.%s" % (path, key) if path else str(key))
                parts.append("%s=%s" % (key, child))
            digest = "d" + hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:20]
        elif isinstance(node, list):
            parts = []
            for index, item in enumerate(node):
                parts.append(walk(item, "%s[%d]" % (path, index)))
            digest = "l" + hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:20]
        else:
            digest = "s" + hashlib.sha256(
                ("%s:%r" % (type(node).__name__, node)).encode("utf-8")
            ).hexdigest()[:20]
        out[path or "$"] = digest
        return digest

    walk(payload, "")
    return out


def _payload_shape(original_canonical, payload):
    """Bounded structural fingerprint of one source payload (no values logged)."""
    keys = sorted(payload) if isinstance(payload, dict) else []
    key_digests = {}
    nested = {}
    for key in keys[:_TOP_KEY_LIMIT]:
        value = payload[key]
        key_digests[str(key)] = _short_digest(original_canonical, value)
        if isinstance(value, dict):
            for sub_key in sorted(value)[:24]:
                if len(nested) >= _SHORT_DIGEST_LIMIT:
                    break
                nested["%s.%s" % (key, sub_key)] = _short_digest(original_canonical, value[sub_key])
    return {
        "source_key_count": len(keys),
        "source_keys": [str(key) for key in keys[:_TOP_KEY_LIMIT]],
        "source_key_digests": key_digests,
        "source_nested_key_digests": nested,
        "source_nested_truncated": len(nested) >= _SHORT_DIGEST_LIMIT,
    }


def _seal_binding(args, kwargs):
    contract = args[1] if len(args) > 1 and isinstance(args[1], dict) else {}
    source_payload = args[2] if len(args) > 2 else None
    reuse = kwargs.get("reuse_digests")
    reuse = reuse if isinstance(reuse, dict) else {}
    original_strip = _LIFECYCLE_ORIGINALS["strip_request_transport_identity"]
    original_payload = _LIFECYCLE_ORIGINALS["payload_sha256"]
    original_canonical = _LIFECYCLE_ORIGINALS["canonical_json"]
    semantic = _lifecycle_module.contract_semantic_payload
    SEAL_BINDING["quiet"] = True
    try:
        recomputed_source = (
            original_payload(original_strip(source_payload)) if isinstance(source_payload, dict) else ""
        )
        recomputed_contract = original_payload(semantic(contract))
    finally:
        SEAL_BINDING["quiet"] = False
    record = {
        "call_index": SEAL_BINDING["call_index"],
        "reused": bool(reuse),
        "memo_source": str(reuse.get("sourceSha256") or ""),
        "memo_contract": str(reuse.get("contractSha256") or ""),
        "recomputed_source": recomputed_source,
        "recomputed_contract": recomputed_contract,
        "source_digest_matches_memo": bool(reuse) and str(reuse.get("sourceSha256") or "") == recomputed_source,
        "contract_digest_matches_memo": bool(reuse) and str(reuse.get("contractSha256") or "") == recomputed_contract,
    }
    if SEAL_BINDING["call_index"] == 0:
        if isinstance(source_payload, dict) and not _FULL_INDEX:
            _FULL_INDEX.update(_tree_digest_index(source_payload))
        record.update(_payload_shape(original_canonical, source_payload))
        record["source_focus"] = _focused_shape(original_canonical, source_payload)
        record["source_path_digests"] = _path_digest_map(original_canonical, source_payload)
        unsorted = _unsorted_list_map(original_canonical, source_payload)
        record["source_unsorted_lists"] = unsorted
    return record


_seal_original = authority.seal_runtime_contract


def _seal_runtime_contract_observed(*args, **kwargs):
    started = time.perf_counter()
    try:
        return _seal_original(*args, **kwargs)
    finally:
        SEAL["ms"]["seal_runtime_contract"] = (
            SEAL["ms"].get("seal_runtime_contract", 0.0) + (time.perf_counter() - started) * 1000.0
        )
        SEAL["counts"]["seal_runtime_contract"] = SEAL["counts"].get("seal_runtime_contract", 0) + 1
        # The whole probe-internal identity pass (digest pair plus the shape and
        # path-digest maps) runs inside the seal call and therefore inside
        # ``dispatch_ms``. Timing the whole call records it separately so the
        # delivery cost can be read net of the instrumentation that observes it,
        # instead of being mistaken for product work.
        _recompute_started = time.perf_counter()
        try:
            SEAL_BINDING["rows"].append(_seal_binding(args, kwargs))
        except Exception as exc:  # diagnostic only: never fail the observation
            SEAL_BINDING["rows"].append({"call_index": SEAL_BINDING["call_index"],
                                         "error": "%s: %s" % (type(exc).__name__, exc)})
        finally:
            SEAL_BINDING["recompute_ms"] += (time.perf_counter() - _recompute_started) * 1000.0
        SEAL_BINDING["call_index"] += 1


_seal_runtime_contract_observed.__wrapped__ = _seal_original
authority.seal_runtime_contract = _seal_runtime_contract_observed


def _graph_nodes(value, acc=None, depth=0):
    """Count container nodes the way ``strip_request_transport_identity`` visits them."""
    if acc is None:
        acc = [0]
    if isinstance(value, dict):
        acc[0] += 1
        for key, item in value.items():
            _graph_nodes(key, acc, depth + 1)
            _graph_nodes(item, acc, depth + 1)
    elif isinstance(value, list):
        acc[0] += 1
        for item in value:
            _graph_nodes(item, acc, depth + 1)
    return acc[0]

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

# The miss path builds ``cached_payload`` (its own copy of ui_data/ui_meta) and
# then hands that already-fresh payload to ``put``, which deep-copies it into the
# entry again. That second copy is the registered miss-path residual, so it is
# measured directly as a method instead of being inferred from a stack sample.
# ``put`` calls ``put_generated`` internally, so a ``put`` call also counts there.
PUT = {"calls": 0, "ms": 0.0}
PUT_GENERATED = {"calls": 0, "ms": 0.0}


def _counted_method(container, original):
    def wrapper(self, *args, **kwargs):
        started = time.perf_counter()
        try:
            return original(self, *args, **kwargs)
        finally:
            container["calls"] = container.get("calls", 0) + 1
            container["ms"] = container.get("ms", 0.0) + (time.perf_counter() - started) * 1000.0

    wrapper.__wrapped__ = original
    return wrapper


_cache_type.put = _counted_method(PUT, _cache_type.put)
_cache_type.put_generated = _counted_method(PUT_GENERATED, _cache_type.put_generated)

_handler_cls = _handler_module.UiContractV2Handler
for _name in (
    "_trim_limit_params",
    "_ui_contract_params",
    "_validate_scene_action_binding",
    "_validate_form_record",
):
    setattr(_handler_cls, _name, _timed(PRELOOKUP["ms"], _name, getattr(_handler_cls, _name)))

# Scene-registry load attribution. ``_validate_scene_action_binding`` runs on
# every ui.contract.v2 request (hot hits included) and re-loads the scene
# registry to check one binding, so a redundancy claim needs the per-request
# load count and the registry's own internal stage split - not an inference.
# ``load_scene_configs`` dispatches to ``load_scene_configs_with_timings``
# through the same module global, so patching that one name also covers the
# ``load_scene_configs`` entry.
_scene_registry = __import__(
    "odoo.addons.smart_construction_scene.scene_registry", fromlist=["x"]
)
SCENE = {
    "calls": 0,
    "ms": [],
    "stages_ms": {},
    "outer_calls": 0,
    "outer_ms": [],
}
_scene_configs_original = _scene_registry.load_scene_configs_with_timings


def _scene_configs_observed(env, drift=None):
    started = time.perf_counter()
    try:
        result = _scene_configs_original(env, drift=drift)
    finally:
        SCENE["ms"].append(round((time.perf_counter() - started) * 1000.0, 3))
        SCENE["calls"] += 1
    timings = result[1] if isinstance(result, tuple) and len(result) == 2 else {}
    if isinstance(timings, dict):
        for _stage, _value in timings.items():
            SCENE["stages_ms"][_stage] = SCENE["stages_ms"].get(_stage, 0.0) + float(_value or 0)
    return result


_scene_registry.load_scene_configs_with_timings = _scene_configs_observed

_scene_outer_original = _handler_module.load_scenes_from_db_or_fallback


def _scene_outer_counted(*args, **kwargs):
    started = time.perf_counter()
    try:
        return _scene_outer_original(*args, **kwargs)
    finally:
        SCENE["outer_ms"].append(round((time.perf_counter() - started) * 1000.0, 3))
        SCENE["outer_calls"] += 1


_handler_module.load_scenes_from_db_or_fallback = _scene_outer_counted


def _payload(params):
    return {
        "intent": INTENT,
        "params": dict(params),
        "context": {"allowed_company_ids": [company], "lang": "zh_CN"},
        "meta": {},
    }


def _sample(params, phase, capture=None):
    """Run one real permission + router/handler pass on the fixed identity."""
    payload = _payload(params)
    SQL["count"] = 0
    SQL["ms"] = 0.0
    DEEPCOPY["count"] = 0
    DEEPCOPY["sites"] = {}
    PUT["calls"] = 0
    PUT["ms"] = 0.0
    PUT_GENERATED["calls"] = 0
    PUT_GENERATED["ms"] = 0.0
    SEAL["ms"] = {}
    SEAL["counts"] = {}
    SEAL_BINDING["rows"] = []
    SEAL_BINDING["call_index"] = 0
    SEAL_BINDING["recompute_ms"] = 0.0
    GC_STATE["ms"] = 0.0
    GC_STATE["collections"] = {0: 0, 1: 0, 2: 0}
    GC_STATE["collected"] = 0
    PRELOOKUP["ms"].clear()
    SCENE["calls"] = 0
    LIFECYCLE["ms"] = {}
    LIFECYCLE["counts"] = {}
    LIFECYCLE["callers"] = {}
    SCENE["ms"] = []
    SCENE["stages_ms"] = {}
    SCENE["outer_calls"] = 0
    SCENE["outer_ms"] = []
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
    _sealed_lifecycle = {}
    if isinstance(serializable, dict):
        _sealed_lifecycle = (((serializable.get("data") or {}).get("meta") or {}).get("lifecycle")) or {}
    response = json.dumps(serializable, sort_keys=True, default=str) if serializable is not None else ""
    if capture is not None:
        # Capture the same canonical form the digest uses, so the comparison is
        # over plain JSON data and not over an internal object identity.
        capture.append(json.loads(response) if response else None)
    row = {
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
        "put_calls": PUT["calls"],
        "put_ms": round(PUT["ms"], 3),
        "put_generated_calls": PUT_GENERATED["calls"],
        "put_generated_ms": round(PUT_GENERATED["ms"], 3),
        "seal_ms": {name: round(value, 3) for name, value in SEAL["ms"].items()},
        "seal_binding_recompute_ms": round(SEAL_BINDING["recompute_ms"], 3),
        "seal_counts": dict(SEAL["counts"]),
        "prelookup_ms": {name: round(value, 3) for name, value in PRELOOKUP["ms"].items()},
        "scene_load_calls": SCENE["calls"],
        "scene_load_ms": list(SCENE["ms"]),
        "scene_stages_ms": {
            name: round(value, 3) for name, value in SCENE["stages_ms"].items()
        },
        "scene_outer_calls": SCENE["outer_calls"],
        "scene_outer_ms": list(SCENE["outer_ms"]),
        "gc_ms": round(GC_STATE["ms"], 3),
        "lifecycle_ms": {name: round(value, 3) for name, value in LIFECYCLE["ms"].items()},
        "lifecycle_counts": dict(LIFECYCLE["counts"]),
        "lifecycle_callers": dict(LIFECYCLE["callers"]),
        "sealed_contract_sha256": ((_sealed_lifecycle.get("integrity") or {}).get("contractSha256")),
        "sealed_source_sha256": ((_sealed_lifecycle.get("generation") or {}).get("sourceSha256")),
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
    # Independent re-verification of what was actually returned. The seal's
    # integrity check recomputes the semantic digest from the delivered object;
    # it runs here with the ORIGINAL un-patched functions restored, after the
    # per-request counters were captured, so it neither pollutes the measurement
    # nor can inherit a wrapper. A digest carried across requests instead of
    # recomputed still has to match the delivered bytes or this reports False.
    integrity_ok = None
    integrity_reason = "not_evaluated"
    try:
        delivered = serializable.get("data") if isinstance(serializable, dict) else None
        if isinstance(delivered, dict):
            for _name, _func in _LIFECYCLE_ORIGINALS.items():
                setattr(_lifecycle_module, _name, _func)
            try:
                integrity_ok, integrity_reason = _lifecycle_module.verify_unified_page_contract_integrity(delivered)
            finally:
                for _name in _LIFECYCLE_ORIGINALS:
                    setattr(_lifecycle_module, _name, _LIFECYCLE_PATCHED[_name])
    except Exception as exc:  # diagnostic only: never fail the observation
        integrity_ok, integrity_reason = False, "%s: %s" % (type(exc).__name__, exc)
    row["seal_bindings"] = [
        dict(binding, phase=phase) for binding in SEAL_BINDING["rows"]
    ]
    row["sealed_integrity_ok"] = integrity_ok
    row["sealed_integrity_reason"] = integrity_reason
    return row


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
# 2c. Guard equivalence: the scene-less short-circuit must not change the
# delivered contract. In one process the same fixed request is served three
# times with the shipped guard and once through the pre-guard adapter path
# (the registry load is always performed there), the volatile key set is
# discovered mechanically from the identical guarded runs, and the guarded and
# unguarded responses are compared after masking exactly those volatile paths.
# A non-empty residual is an unexplained contract difference, not a pass.
SCENE_GUARD_EQUIVALENCE = {}


# Response-level per-request measurements. Each value records how long this
# request took, not what it delivered, so it is registered here as volatile for
# the payload equivalence check rather than left to accidental discovery: two
# guarded samples of the same shape can happen to carry the same stage duration
# while the pre-guard sample differs, and the previous run-to-run output shows
# exactly that (``v2_projection_and_seal``, ``authority_and_cache_lookup``
# reported as unexplained in one run and absent in the next). Registration is
# narrow: only the declared measurement containers are excluded, and the raw
# ``guarded_hot_vs_pre_guard_diff_paths`` is still reported so a real payload
# difference stays visible.
RESPONSE_MEASUREMENT_PATHS = (
    "meta.elapsed_ms",
    "meta.projection_cache.stages_ms",
)


def _is_registered_measurement_path(path):
    """True when ``path`` is a registered measurement container or below it.

    ``_diff_paths`` names the deepest differing leaf, so a differing stage
    duration arrives as ``meta.projection_cache.stages_ms.<stage>`` while the
    registration names the container. The prefix rule keeps the registration
    narrow (only the declared measurement subtrees) instead of forcing either a
    per-stage list or a blanket exclusion.
    """
    return any(
        path == registered or path.startswith(registered + ".") or path.startswith(registered + "[")
        for registered in RESPONSE_MEASUREMENT_PATHS
    )


def _diff_paths(left, right, prefix=""):
    paths = set()
    if isinstance(left, dict) and isinstance(right, dict):
        for key in set(left) | set(right):
            if key not in left or key not in right:
                paths.add("%s.%s" % (prefix, key) if prefix else str(key))
                continue
            paths |= _diff_paths(left[key], right[key], "%s.%s" % (prefix, key) if prefix else str(key))
    elif isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            paths.add("%s[len]" % prefix if prefix else "[len]")
        for index in range(min(len(left), len(right))):
            paths |= _diff_paths(left[index], right[index], "%s[%d]" % (prefix, index) if prefix else "[%d]" % index)
    elif left != right:
        paths.add(prefix or "<root>")
    return paths


def _scene_binding_pre_guard(self, params):
    """The exact pre-guard body: always load the registry, then delegate.

    The two names are resolved in the handler module's own namespace, which is
    where the shipped method resolved them before the guard was added.
    """
    payload = _handler_module.load_scenes_from_db_or_fallback(self.env, drift=None, logger=None) or {}
    return _handler_module._authority.validate_scene_action_binding(payload, params, self._err)


def _outcome(sample):
    return {"ok": sample.get("ok"), "error": sample.get("error")}


def _drop_paths(value, paths, prefix=""):
    """Copy ``value`` with the given dotted paths removed, for a byte compare."""
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            path = "%s.%s" % (prefix, key) if prefix else str(key)
            if path in paths:
                continue
            out[key] = _drop_paths(item, paths, path)
        return out
    if isinstance(value, list):
        return [_drop_paths(item, paths, "%s[%d]" % (prefix, index) if prefix else "[%d]" % index)
                for index, item in enumerate(value)]
    return value


def _canonical(value):
    return json.dumps(value, sort_keys=True, default=str)


def _scene_guard_triple(params, phase):
    """Serve one param shape three times: guard, guard (hot), pre-guard (hot).

    The first guarded run establishes the identity (it may be a miss); the
    second and the pre-guard run then share that same hot identity, so their
    cache status, SQL count and delivered body are directly comparable. The
    volatile key set is discovered from the two guarded runs of this same shape
    instead of being assumed stable across shapes.
    """
    guarded = []
    for _ in range(2):
        capture = []
        guarded.append((_sample(params, phase + "_guarded", capture=capture), capture[0]))
    shipped = _handler_cls._validate_scene_action_binding
    _handler_cls._validate_scene_action_binding = _scene_binding_pre_guard
    pre_capture = []
    try:
        pre = _sample(params, phase + "_pre_guard", capture=pre_capture)
    finally:
        _handler_cls._validate_scene_action_binding = shipped
    return guarded, pre, pre_capture[0]


try:
    _bound_scene_action_id = getattr(_handler_module._authority, "_scene_target_action_id")
    _registry_payload = (
        _handler_module.load_scenes_from_db_or_fallback(env, drift=None, logger=None) or {}
    )
    _bound_scene = None
    for _row in _registry_payload.get("scenes") or []:
        if not isinstance(_row, dict):
            continue
        _code = str(_row.get("code") or _row.get("key") or "").strip()
        if not _code:
            continue
        try:
            _bound_action = int(_bound_scene_action_id(_row) or 0)
        except Exception:
            _bound_action = 0
        if _bound_action > 0:
            _bound_scene = (_code, _bound_action)
            break
    _first_scene_code = None
    for _row in _registry_payload.get("scenes") or []:
        if isinstance(_row, dict):
            _first_scene_code = str(_row.get("code") or _row.get("key") or "").strip() or None
            if _first_scene_code:
                break

    _shapes = [("scene_less", dict(BASE_PARAMS)), ("variant_limit", dict(VARIANT_PARAMS))]
    _blank_shapes = [
        ("blank_key", dict(BASE_PARAMS, scene_key="   ")),
        ("camel_blank_key", dict(BASE_PARAMS, sceneKey="")),
        ("unknown_scene_key", dict(BASE_PARAMS, scene_key="no.such.scene.for.probe")),
    ]
    _known_scene_shapes = []
    if _first_scene_code:
        _known_scene_shapes.append(
            ("registry_scene_no_action", dict(BASE_PARAMS, scene_key=_first_scene_code))
        )
    if _bound_scene is not None:
        _known_scene_shapes.append(
            ("bound_scene_match", dict(BASE_PARAMS, scene_key=_bound_scene[0], action_id=_bound_scene[1]))
        )
        _known_scene_shapes.append(
            ("bound_scene_mismatch", dict(BASE_PARAMS, scene_key=_bound_scene[0], action_id=_bound_scene[1] + 1))
        )
    _shapes.extend(_known_scene_shapes)
    _shapes.extend(_blank_shapes)

    _results = {}
    for _name, _params in _shapes:
        _guarded, _pre_sample, _pre_capture = _scene_guard_triple(_params, "equiv_" + _name)
        _hot_guarded_sample, _hot_guarded_capture = _guarded[1]
        _first_guarded_capture = _guarded[0][1]
        _discovered_volatile = _diff_paths(_first_guarded_capture, _hot_guarded_capture)
        _cross = _diff_paths(_hot_guarded_capture, _pre_capture)
        _volatile = set(_discovered_volatile) | {
            path for path in _cross if _is_registered_measurement_path(path)
        }
        _sql_guarded = _hot_guarded_sample.get("sql_count")
        _sql_pre = _pre_sample.get("sql_count")
        _results[_name] = {
            "params_keys": sorted(_params.keys()),
            "guarded_hot_outcome": _outcome(_hot_guarded_sample),
            "pre_guard_outcome": _outcome(_pre_sample),
            "outcomes_match": _outcome(_hot_guarded_sample) == _outcome(_pre_sample),
            "cache_status_guarded": _hot_guarded_sample.get("cache_status"),
            "cache_status_pre_guard": _pre_sample.get("cache_status"),
            "cache_status_match": _hot_guarded_sample.get("cache_status") == _pre_sample.get("cache_status"),
            "cache_reason_guarded": _hot_guarded_sample.get("cache_reason"),
            "cache_reason_pre_guard": _pre_sample.get("cache_reason"),
            "cache_reason_match": _hot_guarded_sample.get("cache_reason") == _pre_sample.get("cache_reason"),
            "expected_scene_less_decision": not str(
                _params.get("scene_key") or _params.get("sceneKey") or ""
            ).strip(),
            "sql_count_guarded": _sql_guarded,
            "sql_count_pre_guard": _sql_pre,
            "sql_count_delta": (
                (_sql_pre - _sql_guarded)
                if isinstance(_sql_pre, int) and isinstance(_sql_guarded, int)
                else None
            ),
            "response_bytes_guarded": _hot_guarded_sample.get("response_bytes"),
            "response_bytes_pre_guard": _pre_sample.get("response_bytes"),
            "response_bytes_match": _hot_guarded_sample.get("response_bytes") == _pre_sample.get("response_bytes"),
            "volatile_paths_discovered": sorted(_discovered_volatile),
            "registered_measurement_paths": sorted(RESPONSE_MEASUREMENT_PATHS),
            "guarded_hot_vs_pre_guard_diff_paths": sorted(_cross),
            "unexplained_diff_paths": sorted(_cross - _volatile),
            "equivalent_after_masking_volatile": not (_cross - _volatile),
        }
        _results[_name]["sql_count_delta_matches_guard_decision"] = (
            _results[_name]["sql_count_delta"]
            == (3 if _results[_name]["expected_scene_less_decision"] else 0)
        )
        _results[_name]["normalized_payload_equal"] = _canonical(
            _drop_paths(_hot_guarded_capture, _volatile)
        ) == _canonical(_drop_paths(_pre_capture, _volatile))
    SCENE_GUARD_EQUIVALENCE = {
        "shapes": _results,
        "bound_scene": _bound_scene,
        "first_registry_scene_code": _first_scene_code,
        "all_equivalent_after_masking_volatile": all(
            row["equivalent_after_masking_volatile"] for row in _results.values()
        ),
        "all_outcomes_match": all(row["outcomes_match"] for row in _results.values()),
        "all_cache_status_match": all(row["cache_status_match"] for row in _results.values()),
        "all_cache_reason_match": all(row["cache_reason_match"] for row in _results.values()),
        "all_normalized_payloads_equal": all(row["normalized_payload_equal"] for row in _results.values()),
        "all_sql_deltas_match_guard_decision": all(
            row["sql_count_delta_matches_guard_decision"] for row in _results.values()
        ),
        "unexplained_diff_paths_total": sorted(
            {path for row in _results.values() for path in row["unexplained_diff_paths"]}
        ),
        "shapes_expected_to_skip_the_load": [
            name for name, row in _results.items() if row["expected_scene_less_decision"]
        ],
        "shapes_expected_to_keep_the_load": [
            name for name, row in _results.items() if not row["expected_scene_less_decision"]
        ],
    }
except Exception as exc:  # diagnostic only: never fail the observation
    SCENE_GUARD_EQUIVALENCE = {"error": "%s: %s" % (type(exc).__name__, exc)}

# 3. Identity variation: same surface, different projection identity.
SAMPLES["variant"] = [_sample(VARIANT_PARAMS, "variant_%d" % index) for index in range(1, 3)]
# 4. Cold rebuild: registry caches and the process-local hot cache both cleared.
env.registry.clear_cache()
lcrc.CONTRACT_PROJECTION_HOT_CACHE.clear()
SAMPLES["cold_rebuild"] = [_sample(BASE_PARAMS, "cold_rebuild_1")]

# 5. Miss-path redundant copy: the cold rebuild above is a real miss, so the
# handler built ``cached_payload`` and then ``put`` copied that fresh payload
# again. The measured ``put_ms`` IS the marginal cost of that second copy (the
# method body only deep-copies and stores), and the same subgraph is re-measured
# in isolation as a cross-check. The share convention is the one the baseline
# record already uses (share_of_observed): the copy's cost over the very same
# request's dispatch time, so it is read against the cost it could remove.
_miss_sample = None
for _group in ("process_first", "variant", "cold_rebuild"):
    for _sample_row in SAMPLES.get(_group, []):
        if _sample_row.get("cache_reason") == "asset_not_found":
            _miss_sample = _sample_row
            break
    if _miss_sample is not None:
        break
if _miss_sample is None:
    _miss_sample = SAMPLES["cold_rebuild"][0]
MISS_COPY = {
    "source_miss_sample": True,
    "phase": _miss_sample["phase"],
    "cache_reason": _miss_sample["cache_reason"],
    "dispatch_ms": _miss_sample["dispatch_ms"],
    "put_calls": _miss_sample["put_calls"],
    "put_ms": _miss_sample["put_ms"],
    "put_generated_calls": _miss_sample["put_generated_calls"],
    "put_generated_ms": _miss_sample["put_generated_ms"],
    "entry_is_replaced_by_the_assembled_put": bool(_miss_sample["put_generated_calls"] >= 2),
    "hot_put_calls": _stats_values(
        [sample["put_calls"] for sample in SAMPLES["hot"]]
    ),
}
MISS_COPY["also_measured_on"] = {
    _group: {
        "cache_reason": _row["cache_reason"],
        "dispatch_ms": _row["dispatch_ms"],
        "put_calls": _row["put_calls"],
        "put_ms": _row["put_ms"],
        "put_generated_calls": _row["put_generated_calls"],
    }
    for _group, _rows in SAMPLES.items()
    for _row in _rows
    if _row.get("cache_reason") == "asset_not_found" and _row is not _miss_sample
}
try:
    _miss_entry = None
    for _candidate in lcrc.CONTRACT_PROJECTION_HOT_CACHE._entries.values():
        if isinstance(_candidate[2], dict) and _candidate[2].get("ui_data"):
            _miss_entry = _candidate[2]
            break
    if _miss_entry is None:
        MISS_COPY["error"] = "no cache entry available after the miss"
    else:
        _shape = {
            "source_type": _miss_entry.get("source_type"),
            "ui_data": _miss_entry.get("ui_data"),
            "ui_meta": _miss_entry.get("ui_meta"),
        }
        _isolated = []
        for _ in range(5):
            _started = time.perf_counter()
            _DEEPCOPY_ORIGINAL(_shape)
            _isolated.append(round((time.perf_counter() - _started) * 1000.0, 3))
        MISS_COPY["isolated_deepcopy_ms"] = sorted(_isolated)
        MISS_COPY["isolated_deepcopy_median_ms"] = sorted(_isolated)[len(_isolated) // 2]
except Exception as exc:  # diagnostic only: never fail the observation
    MISS_COPY["error"] = "%s: %s" % (type(exc).__name__, exc)
_miss_cost = MISS_COPY.get("put_ms")
if isinstance(_miss_cost, (int, float)) and isinstance(MISS_COPY["dispatch_ms"], (int, float)):
    MISS_COPY["share_of_observed"] = round(_miss_cost / MISS_COPY["dispatch_ms"], 6)
MISS_COPY["decision_rule"] = (
    "read as share_of_observed against the same miss request; the registered residual is called a "
    "critical cost only when that share is large enough to matter against the declared first-contract "
    "budget, and it is explicitly NOT treated as a per-request cost because it is paid once per "
    "(identity, source-token) miss and not on a hot read"
)
MISS_COPY["hot_path_note"] = (
    "a hot read performs zero ``put`` calls (hot_put_calls.max == 0), so this cost never appears on "
    "the warm path; it is a cold-identity cost"
)

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
def _lifecycle_summary(samples):
    """Per-group seal-internal split: how much of the seal recomputes digests."""
    ms = {}
    counts = {}
    for sample in samples:
        for name, value in (sample.get("lifecycle_ms") or {}).items():
            ms[name] = round(ms.get(name, 0.0) + float(value or 0), 3)
        for name, value in (sample.get("lifecycle_counts") or {}).items():
            counts[name] = counts.get(name, 0) + int(value or 0)
    per_request = {}
    for name, value in counts.items():
        if samples and value:
            per_request[name] = {
                "calls": value,
                "calls_per_request": round(value / len(samples), 3),
                "ms_per_request": round(ms.get(name, 0.0) / len(samples), 3),
            }
    return {"ms": ms, "counts": counts, "per_request": per_request, "requests": len(samples)}


REPORT["seal_internal_ms"] = {
    phase: _lifecycle_summary(samples) for phase, samples in SAMPLES.items()
}
REPORT["seal_internal_ms"]["note"] = (
    "contract_lifecycle.payload_sha256 / strip_request_transport_identity / canonical_json are module "
    "globals inside contract_lifecycle, so they are patched there; payload_sha256 calls canonical_json "
    "in the same namespace, so payload_sha256 contains canonical_json and the two must not be summed."
)
REPORT["gc_control"] = {
    "gc_enabled_group": "hot",
    "gc_disabled_group": "hot_gc_off",
    "control_is_paired_in_one_process": True,
}

# Probe-overhead separation. The probe recomputes the seal digests over the very
# payload objects the seal received (an identity check), and that recomputation
# runs inside ``seal_runtime_contract`` and therefore inside ``dispatch_ms``.
# Without this block the observed dispatch is product + probe, and the probe's own
# ``strip_request_transport_identity`` rebuild of the cached source graph
# (~8.3k containers) would be reported as a hot-request cost. Recorded additively:
# no existing key changes meaning, so earlier rows stay readable as
# "dispatch including probe overhead" while the net line is available here.
def _recompute_net(samples):
    rows = [
        (sample.get("dispatch_ms"), sample.get("seal_binding_recompute_ms") or 0.0)
        for sample in samples
        if isinstance(sample.get("dispatch_ms"), (int, float))
    ]
    if not rows:
        return None
    return {
        "requests": len(rows),
        "seal_binding_recompute_ms": _stats_values([ms for _d, ms in rows]),
        "hot_dispatch_ms": _stats_values([d for d, _ms in rows]),
        "hot_dispatch_net_ms": _stats_values([d - ms for d, ms in rows]),
        "recompute_share_of_dispatch_median": round(
            sorted(ms for _d, ms in rows)[len(rows) // 2]
            / sorted(d for d, _ms in rows)[len(rows) // 2],
            6,
        ),
    }


REPORT["probe_overhead"] = {
    "seal_binding_recompute": _recompute_net(HOT),
    "seal_binding_recompute_gc_off": _recompute_net(CONTROL),
    "note": (
        "probe-internal identity recomputation charged to dispatch_ms; the product hot "
        "dispatch is the *_net_ms line, and the recomputation is the probe's own cost, "
        "not a cache or seal cost of the product"
    ),
}
# Seal-digest invariance: if the sealed contract/source digests are identical
# across every hot request of one identity, the digest is a pure function of the
# cached entry (transport identity is excluded from the semantic payload by
# definition), so recomputing it per request is a redundancy that can be removed
# without changing any delivered value. A non-constant set here is the
# counterexample that forbids that conclusion.
def _digest_constancy(samples, key):
    values = [sample.get(key) for sample in samples if sample.get(key)]
    return {
        "samples": len(values),
        "distinct": len(set(values)),
        "constant": len(values) > 0 and len(set(values)) == 1,
        "value": values[0] if len(set(values)) == 1 else None,
    }


REPORT["sealed_integrity_reverification"] = {
    phase: {
        "requests": len(rows),
        "checked": sum(1 for row in rows if row.get("sealed_integrity_ok") is not None),
        "ok": sum(1 for row in rows if row.get("sealed_integrity_ok") is True),
        "reasons": sorted({row.get("sealed_integrity_reason") for row in rows}),
    }
    for phase, rows in SAMPLES.items()
}
REPORT["seal_digest_invariance"] = {
    phase: {
        "contract_sha256": _digest_constancy(rows, "sealed_contract_sha256"),
        "source_sha256": _digest_constancy(rows, "sealed_source_sha256"),
        "payload_sha256_callers": {},
    }
    for phase, rows in SAMPLES.items()
}
for _phase, _rows in SAMPLES.items():
    _callers = {}
    for _row in _rows:
        for _site, _count in (_row.get("lifecycle_callers") or {}).items():
            _callers[_site] = _callers.get(_site, 0) + int(_count or 0)
    REPORT["seal_digest_invariance"][_phase]["payload_sha256_callers"] = _callers
    REPORT["seal_digest_invariance"][_phase]["requests"] = len(_rows)


def _binding_summary(samples):
    """Memo-vs-recomputation identity per group, without logging payload values."""
    rows = [binding for sample in samples for binding in sample.get("seal_bindings") or []]
    reuse_rows = [row for row in rows if row.get("reused")]
    return {
        "requests": len(samples),
        "seal_calls": len(rows),
        "reuse_calls": len(reuse_rows),
        "reuse_source_matches_recomputation": sorted({bool(row.get("source_digest_matches_memo")) for row in reuse_rows}),
        "reuse_contract_matches_recomputation": sorted({bool(row.get("contract_digest_matches_memo")) for row in reuse_rows}),
        "binding_errors": sorted({str(row.get("error")) for row in rows if row.get("error")}),
        "memo_source_values": sorted({row.get("memo_source") for row in reuse_rows if row.get("memo_source")}),
        "recomputed_source_values": sorted({row.get("recomputed_source") for row in reuse_rows if row.get("recomputed_source")}),
        "memo_contract_values": sorted({row.get("memo_contract") for row in reuse_rows if row.get("memo_contract")}),
        "recomputed_contract_values": sorted({row.get("recomputed_contract") for row in reuse_rows if row.get("recomputed_contract")}),
        "all_source_values": sorted({row.get("recomputed_source") or row.get("memo_source") for row in rows}),
        "first_call_shape": next(
            (
                {
                    "source_key_count": row.get("source_key_count"),
                    "source_keys": row.get("source_keys"),
                    "source_key_digests": row.get("source_key_digests"),
                    "source_nested_key_digests": row.get("source_nested_key_digests"),
                    "source_nested_truncated": row.get("source_nested_truncated"),
                    "source_focus": row.get("source_focus"),
                    "source_path_digests": row.get("source_path_digests"),
                    "source_unsorted_lists": row.get("source_unsorted_lists"),
                    "memo_source": row.get("memo_source"),
                    "recomputed_source": row.get("recomputed_source"),
                }
                for row in rows
                if row.get("source_key_digests")
            ),
            None,
        ),
    }


REPORT["seal_source_binding"] = {
    phase: _binding_summary(rows) for phase, rows in SAMPLES.items()
}
REPORT["seal_source_binding_note"] = (
    "diagnostic-only binding check: the probe recomputes both digests from the exact payload objects "
    "each seal call received and compares them with the reuse hint. Capturing this adds work to every "
    "request, so timings from a run of this probe are diagnostic and must not be read as the candidate's "
    "latency."
)
try:
    _node_counts = {}
    for _candidate in lcrc.CONTRACT_PROJECTION_HOT_CACHE._entries.values():
        _entry = _candidate[2]
        if not isinstance(_entry, dict):
            continue
        _assembled = _entry.get("_assembled_v2")
        if not isinstance(_assembled, dict):
            continue
        _node_counts = {
            "entry": _graph_nodes(_entry),
            "ui_data": _graph_nodes(_entry.get("ui_data")),
            "assembled_contract": _graph_nodes(_assembled.get("contract")),
            "assembled_source_contract": _graph_nodes(_assembled.get("source_contract")),
        }
        break
    REPORT["hot_entry_graph_nodes"] = _node_counts
except Exception as exc:  # diagnostic only: never fail the observation
    REPORT["hot_entry_graph_nodes"] = {"error": "%s: %s" % (type(exc).__name__, exc)}
REPORT["source_full_digest_index"] = {"node_count": len(_FULL_INDEX), "paths": _FULL_INDEX}
REPORT["r3_removed_copy_ms"] = REMOVED_COPY
REPORT["miss_path_redundant_copy_ms"] = MISS_COPY
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
def _scene_phase_summary(samples):
    stages = {}
    for sample in samples:
        for name, value in (sample.get("scene_stages_ms") or {}).items():
            stages[name] = round(stages.get(name, 0.0) + float(value or 0), 3)
    load_ms = [value for sample in samples for value in (sample.get("scene_load_ms") or [])]
    outer_ms = [value for sample in samples for value in (sample.get("scene_outer_ms") or [])]
    return {
        "load_calls_per_request": [sample.get("scene_load_calls") for sample in samples],
        "outer_calls_per_request": [sample.get("scene_outer_calls") for sample in samples],
        "load_calls_stats": _stats_values(
            [sample.get("scene_load_calls") for sample in samples
             if isinstance(sample.get("scene_load_calls"), (int, float))]
        ),
        "outer_calls_stats": _stats_values(
            [sample.get("scene_outer_calls") for sample in samples
             if isinstance(sample.get("scene_outer_calls"), (int, float))]
        ),
        "load_ms": _stats_values(load_ms),
        "outer_ms": _stats_values(outer_ms),
        "stages_ms": stages,
    }


REPORT["scene_guard_equivalence"] = SCENE_GUARD_EQUIVALENCE
REPORT["scene_registry_attribution"] = {
    phase: _scene_phase_summary(samples) for phase, samples in SAMPLES.items()
}
REPORT["scene_registry_delta_ms"] = {
    "load_covered_ms": _stats_values(
        [value for sample in HOT for value in (sample.get("scene_load_ms") or [])]
    ),
    "outer_covered_ms": _stats_values(
        [value for sample in HOT for value in (sample.get("scene_outer_ms") or [])]
    ),
    "note": (
        "scene_load_ms is the registry's own load_scene_configs_with_timings duration; outer_ms is the "
        "ui_contract_v2 handler wrapper around load_scenes_from_db_or_fallback. Both are sub-spans that "
        "sit inside prelookup_ms._validate_scene_action_binding on a hot request."
    ),
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
    "every_delivered_contract_reverifies": all(
        row.get("sealed_integrity_ok") is True for rows in SAMPLES.values() for row in rows
    ),
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
    "miss_path_redundant_copy_is_not_a_hot_read_cost": bool(
        MISS_COPY.get("hot_put_calls") is not None
        and (MISS_COPY["hot_put_calls"] or {}).get("max") == 0
    ),
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
