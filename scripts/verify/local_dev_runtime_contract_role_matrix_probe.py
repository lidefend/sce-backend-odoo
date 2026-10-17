"""Bounded role-dimension contract observation (P4 diagnostic).

The product contract is not one fixed object: the same ``ui.contract.v2``
request produces a different contract identity and a different visible surface
per principal, because the projection identity carries the principal's role
(``uid`` + group-set digest) and the resolved views/policies differ by group. A
performance baseline that only observes one principal therefore under-samples
the real per-role cost and cannot see role-specific behaviour boundaries at all.

This probe observes the *same* declared request under several declared demo
principals in one process, per request case, and answers:

1. does the contract identity and the visible surface vary by role, is the
   surface digest stable across identical repeats of one role (so the variation
   is role-driven, not noise), and exactly which contract paths differ;
2. what each role's contract costs, separated into the process-first dispatch,
   the per-role cold assembly (process-local hot cache cleared, native views and
   translations kept warm) and the per-role warm repeat distribution;
3. is a role without the capability refused explicitly -- either by the
   permission gate or fail-closed inside the handler -- so a refused role can
   never be reported through an empty contract;
4. what the role-scoped relation surface is: relation targets with a permission
   fact, with navigation authority, and with a materialized search dialog, plus
   the declared relation-demand stage timings.

Read-only: commit is refused, the probe rolls back, it changes no product code,
schema, fixture or ACL. The process-local hot cache clear and
``registry.clear_cache()`` affect only this throwaway ``odoo shell`` process,
never the serving workers.
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
MODEL = "payment.request"

TRANSPORT_ONLY_KEYS = {
    "request_id",
    "requestId",
    "trace_id",
    "traceId",
    "timestamp",
    "request_timestamp",
    "requestTimestamp",
    "server_time",
    "generated_at",
    "client_request_id",
    "clientRequestId",
}
# Keys that are timing/volatile presentation, not contract surface. They are
# dropped only when computing the *surface* digest; the raw response digest
# keeps them, and any path that still differs is reported instead of hidden.
SURFACE_VOLATILE_KEYS = TRANSPORT_ONLY_KEYS | {
    "elapsed_ms",
    "elapsedMs",
    "duration_ms",
    "durationMs",
    "latency_ms",
    "serverTime",
    "generatedAt",
    "dc_date",
    "dcDate",
}

# Declared demo principals from
# demo_addons/smart_construction_demo/data/demo/role_matrix_demo_users.xml.
# The first entry pays the process-first cost and is recorded as such.
ROLES = (
    ("smart_construction_demo.user_demo_role_finance", "role_finance"),
    ("smart_construction_demo.user_demo_role_owner", "role_owner"),
    ("smart_construction_demo.user_demo_role_pm", "role_pm"),
    ("smart_construction_demo.user_demo_role_executive", "role_executive"),
    ("smart_construction_demo.user_demo_role_project_a_member", "role_project_a_member"),
    ("smart_construction_demo.user_demo_project_manager", "cap_project_manager"),
    ("smart_construction_demo.user_demo_project_user", "cap_project_user"),
    ("smart_construction_demo.user_demo_project_read", "cap_project_read"),
    ("smart_construction_demo.user_demo_e2e_smoke", "cap_e2e_smoke"),
)
BASELINE_ROLE = "role_finance"
PROCESS_FIRST_ROLE = "role_finance"

# Two declared request cases. ``list_action_open`` is the collection surface of
# the observed action; ``form_action_open`` adds a readable record so the
# relation-entry surface (permission / navigation / search dialog) is present.
REQUEST_CASES = (
    {"id": "list_action_open", "hot_samples": 6, "form_record": False},
    {"id": "form_action_open", "hot_samples": 4, "form_record": True},
)
RELATION_ENTRY_LIMIT = 40
RELATION_WALK_DEPTH = 7

assert env.cr.dbname == DATABASE, "registered local.dev database required"
env.cr.rollback()
_ORIGINAL_COMMIT = env.cr.commit


def _refuse_commit(*_args, **_kwargs):
    raise RuntimeError("contract role matrix probe forbids commit")


env.cr.commit = _refuse_commit

REPORT = {
    "schema": "runtime-contract-role-matrix-probe/v1",
    "database": DATABASE,
    "acceptance_pass": False,
}


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

GC_STATE = {"ms": 0.0, "start": 0.0, "collections": {0: 0, 1: 0, 2: 0}}


def _gc_callback(phase, info):
    if phase == "start":
        GC_STATE["start"] = time.perf_counter()
        return
    GC_STATE["ms"] += (time.perf_counter() - GC_STATE["start"]) * 1000.0
    generation = int(info.get("generation", -1))
    GC_STATE["collections"][generation] = GC_STATE["collections"].get(generation, 0) + 1


gc.callbacks.append(_gc_callback)

# Relation-demand stage attribution is already declared by P0 in
# ``page_assembler._inject_relation_entry_contract`` (RELATION_DEMAND_STAGES).
# Timing its stages per role shows which declared relation stage actually costs.
RELATION_STAGES = (
    "relation_models_collect",
    "relation_entry_overrides",
    "relation_demand_declaration",
    "relation_base_map",
    "relation_field_projection",
)
RELATION_MS = {}


def _wrap_relation_demand():
    from odoo.addons.smart_core.app_config_engine.services.assemblers.page_assembler import (
        PageAssembler,
    )

    original = PageAssembler._inject_relation_entry_contract

    def wrapper(self, data, model_name="", stage_timings=None, relation_cache_key=""):
        container = {}
        result = original(
            self,
            data,
            model_name=model_name,
            stage_timings=container,
            relation_cache_key=relation_cache_key,
        )
        for name in RELATION_STAGES:
            value = container.get(name)
            if isinstance(value, (int, float)):
                RELATION_MS[name] = RELATION_MS.get(name, 0.0) + float(value)
        return result

    wrapper.__wrapped__ = original
    PageAssembler._inject_relation_entry_contract = wrapper


_wrap_relation_demand()


# --- contract surface extraction --------------------------------------------
def _drop_keys(value, dropped):
    if isinstance(value, dict):
        return {
            key: _drop_keys(child, dropped) for key, child in value.items() if key not in dropped
        }
    if isinstance(value, list):
        return [_drop_keys(child, dropped) for child in value]
    return value


def _diff_paths(left, right, path="", depth=0, out=None):
    """Bounded path diff, so surface instability is named instead of assumed."""
    out = [] if out is None else out
    if len(out) >= 40 or depth > 4:
        return out
    if isinstance(left, dict) and isinstance(right, dict):
        for key in sorted(set(left) | set(right)):
            child = "%s.%s" % (path, key) if path else str(key)
            if key not in left or key not in right:
                out.append(child)
            else:
                _diff_paths(left[key], right[key], child, depth + 1, out)
        return out
    if isinstance(left, list) and isinstance(right, list) and len(left) == len(right):
        for index, (a, b) in enumerate(zip(left, right)):
            _diff_paths(a, b, "%s[%d]" % (path, index), depth + 1, out)
        return out
    if left != right:
        out.append(path or "<root>")
    return out


def _outline(node, prefix="", depth=0, out=None, cap=170):
    """Bounded structural outline, so the role difference is located, not guessed."""
    out = [] if out is None else out
    if len(out) >= cap or depth > 2:
        return out
    if isinstance(node, dict):
        for key in sorted(node):
            child = "%s.%s" % (prefix, key) if prefix else str(key)
            value = node[key]
            if isinstance(value, dict):
                out.append("%s {}%d" % (child, len(value)))
                _outline(value, child, depth + 1, out, cap)
            elif isinstance(value, list):
                out.append("%s []%d" % (child, len(value)))
            else:
                out.append(child)
    return out


def _find_relation_entries(data):
    """Locate every relation-entry node wherever the contract embeds it.

    The relation contract is projected into view nodes (``fieldInfo`` /
    ``componentConfig``) as well as source fields, so the walker is structural
    and key-driven rather than path-guessing.
    """
    found = []
    stack = [(data, "", 0, ())]
    while stack:
        node, path, depth, ancestors = stack.pop()
        if len(found) >= 400 or depth > RELATION_WALK_DEPTH:
            continue
        if isinstance(node, dict):
            for key in ("relation_entry", "relationEntry"):
                entry = node.get(key)
                if isinstance(entry, dict):
                    field_name = ""
                    for ancestor in ancestors:
                        if not isinstance(ancestor, dict):
                            continue
                        field_name = str(
                            ancestor.get("name")
                            or ancestor.get("field")
                            or ancestor.get("fieldName")
                            or ancestor.get("key")
                            or ""
                        ).strip()
                        if field_name:
                            break
                    found.append((path, entry, field_name))
            for key, child in node.items():
                if key in ("relation_entry", "relationEntry"):
                    continue
                if isinstance(child, (dict, list)):
                    stack.append(
                        (
                            child,
                            "%s.%s" % (path, key) if path else str(key),
                            depth + 1,
                            (node,) + tuple(ancestors[:1]),
                        )
                    )
        elif isinstance(node, list):
            for index, child in enumerate(node[:60]):
                if isinstance(child, (dict, list)):
                    stack.append(
                        (child, "%s[%d]" % (path, index), depth + 1, (node,) + tuple(ancestors[:1]))
                    )
    return found


def _relation_surface(data):
    """Role-scoped relation surface: permission, navigation and dialog facts."""
    grouped = {}
    for path, entry, field_name in _find_relation_entries(data):
        dialog = entry.get("search_dialog")
        dialog = dialog if isinstance(dialog, dict) else None
        read_fields = dialog.get("read_fields") if dialog else None
        key = field_name or path
        row = grouped.setdefault(
            key,
            {
                "field": field_name or None,
                "nodes": 0,
                "search_dialog_nodes": 0,
                "can_read": set(),
                "can_create": set(),
                "reason_codes": set(),
                "navigation_authority": False,
                "dialog_read_fields": set(),
                "has_domain": False,
            },
        )
        row["nodes"] += 1
        if dialog is not None:
            row["search_dialog_nodes"] += 1
            if isinstance(read_fields, list):
                row["dialog_read_fields"].update(str(item) for item in read_fields)
        if entry.get("can_read") is not None:
            row["can_read"].add(bool(entry.get("can_read")))
        if entry.get("can_create") is not None:
            row["can_create"].add(bool(entry.get("can_create")))
        if entry.get("reason_code"):
            row["reason_codes"].add(str(entry.get("reason_code")))
        row["navigation_authority"] = row["navigation_authority"] or bool(
            entry.get("action_id")
            or entry.get("action_xmlid")
            or entry.get("menu_id")
            or entry.get("menu_xmlid")
            or entry.get("can_open")
        )
        row["has_domain"] = row["has_domain"] or isinstance(entry.get("domain"), list)
    entries = []
    for key in sorted(grouped, key=str):
        row = grouped[key]
        entries.append(
            {
                "field": row["field"],
                "path": key,
                "nodes": row["nodes"],
                "search_dialog_nodes": row["search_dialog_nodes"],
                "can_read": sorted(row["can_read"]),
                "can_create": sorted(row["can_create"]),
                "reason_codes": sorted(row["reason_codes"]),
                "navigation_authority": row["navigation_authority"],
                "dialog_read_fields": sorted(row["dialog_read_fields"])[:20],
                "has_domain": row["has_domain"],
            }
        )
    return {
        "relation_entry_nodes": sum(row["nodes"] for row in entries),
        "relation_targets": len(entries),
        "with_search_dialog": sum(1 for row in entries if row["search_dialog_nodes"]),
        "with_navigation_authority": sum(1 for row in entries if row["navigation_authority"]),
        "read_forbidden_targets": sorted(
            str(row["field"] or row["path"]) for row in entries if row["can_read"] == [False]
        ),
        "dialog_targets": sorted(
            str(row["field"] or row["path"]) for row in entries if row["search_dialog_nodes"]
        ),
        "entries": entries[:RELATION_ENTRY_LIMIT],
    }


def _surface_facts(data):
    if not isinstance(data, dict):
        return {"data_type": type(data).__name__}
    facts = {}
    for section in (data, data.get("pageInfo"), data.get("dataContract")):
        if not isinstance(section, dict):
            continue
        for key in ("model", "view_type", "viewType", "structureVersion", "client_type",
                    "delivery_profile", "source_type", "layoutType", "renderMode"):
            value = section.get(key)
            if isinstance(value, (str, int, bool)) and value not in ("", None):
                facts.setdefault(key, value)
    counts = {}
    for key, value in data.items():
        if isinstance(value, (list, dict)):
            counts[str(key)] = len(value)
    return {
        "facts": facts,
        "top_level_counts": dict(sorted(counts.items())),
        "top_level_keys": sorted(str(key) for key in data.keys()),
    }


def _payload(params, company):
    return {
        "intent": INTENT,
        "params": dict(params),
        "context": {"allowed_company_ids": [company], "lang": "zh_CN"},
        "meta": {},
    }


def _sample(actor, user, shim, params, phase, principal):
    """Run one real permission + router pass on one role identity.

    A role without the capability must be refused -- by the permission gate or
    fail-closed inside the handler. The probe records that refusal explicitly
    and never reports a refused role through an empty contract.
    """
    payload = _payload(params, user.company_id.id)
    SQL["count"] = 0
    SQL["ms"] = 0.0
    DEEPCOPY["count"] = 0
    DEEPCOPY["sites"] = {}
    RELATION_MS.clear()
    GC_STATE["ms"] = 0.0
    GC_STATE["collections"] = {0: 0, 1: 0, 2: 0}
    ctx = RequestContext(actor, user, dict(params), request_obj=shim, principal=principal)
    ip.request = shim
    intent_router.request = shim
    dispatch_segments = []
    permission_ok = None
    gate_error = None
    handler_error = None
    result = None
    permission_ms = None
    dispatch_ms = None
    started = time.perf_counter()
    try:
        permission_ok = bool(ip.check_intent_permission(ctx))
    except Exception as exc:
        gate_error = "%s: %s" % (type(exc).__name__, exc)
        permission_ok = False
    finally:
        permission_ms = (time.perf_counter() - started) * 1000.0
    if permission_ok:
        started = time.perf_counter()
        try:
            result = intent_router.route_intent_payload(
                payload,
                ctx=ctx,
                observe=lambda name, duration: dispatch_segments.append((name, duration)),
            )
        except Exception as exc:
            handler_error = "%s: %s" % (type(exc).__name__, exc)
        finally:
            dispatch_ms = (time.perf_counter() - started) * 1000.0
    ip.request = _ORIGINAL_IP_REQUEST
    intent_router.request = _ORIGINAL_ROUTER_REQUEST

    serializable = None
    if result is not None:
        serializable = result.to_legacy_dict() if hasattr(result, "to_legacy_dict") else result
    meta = (serializable or {}).get("meta") or {} if isinstance(serializable, dict) else {}
    projection = meta.get("projection_cache") or {}
    raw_response = (
        json.dumps(serializable, sort_keys=True, default=str) if serializable is not None else ""
    )
    data = (serializable or {}).get("data") if isinstance(serializable, dict) else None
    # The surface digest is the *contract* the client would render: the envelope
    # ``meta`` carries timings/identity and is deliberately excluded, and the
    # remaining declared volatile keys are dropped so a stable digest means
    # "same contract", while any path that still differs is named.
    canonical = _drop_keys(data, SURFACE_VOLATILE_KEYS) if data is not None else None
    canonical_response = (
        json.dumps(canonical, sort_keys=True, default=str) if canonical is not None else ""
    )
    if not permission_ok:
        outcome = "denied_by_permission"
    elif result is None:
        outcome = "handler_error"
    elif (serializable or {}).get("ok") is False:
        outcome = "handler_error"
    else:
        outcome = "dispatched"
    return {
        "phase": phase,
        "outcome": outcome,
        "permission_ok": permission_ok,
        "denial": gate_error if not permission_ok else None,
        "handler_error": handler_error,
        "handler_error_kind": (
            ((serializable or {}).get("error") or {}).get("code")
            if isinstance((serializable or {}).get("error"), dict)
            else None
        ),
        "permission_ms": round(permission_ms, 3) if permission_ms is not None else None,
        "dispatch_ms": round(dispatch_ms, 3) if dispatch_ms is not None else None,
        "dispatch_segments_ms": {name: round(duration, 3) for name, duration in dispatch_segments},
        "sql_count": SQL["count"],
        "sql_ms": round(SQL["ms"], 3),
        "deepcopy_count": DEEPCOPY["count"],
        "deepcopy_sites": dict(sorted(DEEPCOPY["sites"].items(), key=lambda row: -row[1])[:6]),
        "relation_stage_ms": {name: round(value, 3) for name, value in RELATION_MS.items()},
        "gc_ms": round(GC_STATE["ms"], 3),
        "gc_collections": dict(GC_STATE["collections"]),
        "cache_status": projection.get("status"),
        "cache_reason": projection.get("reason"),
        "cache_identity_ref": projection.get("identity_ref"),
        "cache_source_ref": projection.get("source_ref"),
        "cache_stages_ms": projection.get("stages_ms"),
        "handler_elapsed_ms": meta.get("elapsed_ms"),
        "response_bytes": len(raw_response),
        "response_sha256": (
            hashlib.sha256(raw_response.encode("utf-8")).hexdigest() if raw_response else None
        ),
        "surface_sha256": (
            hashlib.sha256(canonical_response.encode("utf-8")).hexdigest()
            if canonical_response
            else None
        ),
        "surface": _surface_facts(data) if data is not None else None,
        "relation_surface": _relation_surface(data) if data is not None else None,
        "contract_ok": (serializable or {}).get("ok") if isinstance(serializable, dict) else None,
        "_surface_canonical": canonical,
    }


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


def _stats(samples, key):
    return _stats_values([row[key] for row in samples if isinstance(row.get(key), (int, float))])


tra = __import__("odoo.addons.smart_core.delivery.runtime_route_authority", fromlist=["x"])


def _principal(user):
    return {
        "auth_method": "password",
        "principal_type": "human",
        "user_id": user.id,
        "payload": {"db": DATABASE},
    }


role_entries = []
for xmlid, label in ROLES:
    user = env.ref(xmlid)
    assert user.active and not user.share, "demo identity %s unavailable" % xmlid
    company = user.company_id.id
    actor = api.Environment(env.cr, user.id, {"allowed_company_ids": [company], "lang": "zh_CN"})
    assert not actor.su, "actor must not be elevated"
    shim = _RequestShim(actor)
    policy = actor["sc.product.policy"]
    carrier = None
    for menu_id, action_id in tra.iter_published_pairs(policy.published_route_authority()):
        if int(action_id) == ACTION_ID and int(menu_id) > 0:
            carrier = int(menu_id)
            break
    try:
        record = actor[MODEL].search([], limit=1)
        readable_record_id = record.id if record else None
        readable_record_error = None
    except Exception as exc:  # a role without model read must be recorded, not skipped
        readable_record_id = None
        readable_record_error = "%s: %s" % (type(exc).__name__, exc)
    role_entries.append(
        {
            "xmlid": xmlid,
            "label": label,
            "uid": user.id,
            "company_id": company,
            "group_count": len(actor.user.groups_id),
            "group_digest": lcrc.projection_role_code(actor),
            "navigation_carrier": carrier,
            "navigation_capability": "present" if carrier else "absent",
            "readable_record_id": readable_record_id,
            "readable_record_error": readable_record_error,
            "actor": actor,
            "user": user,
            "shim": shim,
            "cases": {},
        }
    )

for case in REQUEST_CASES:
    case_id = case["id"]
    # Phase A: first touch of this case per role, in declared order. The first
    # entry of the first case pays the process-first cost and is recorded as such.
    # Phase B: warm repeats. Phase C: per-role cold assembly with only the
    # process-local hot cache cleared, so native views and translations stay warm
    # and what is measured is the role's own contract assembly.
    for phase_index, phase in enumerate(("assembly_first", "hot", "assembly_cold_role")):
        for entry in role_entries:
            params = {"action_id": ACTION_ID, "op": "action_open"}
            if entry["navigation_carrier"]:
                params["menu_id"] = entry["navigation_carrier"]
            if case["form_record"]:
                if entry["readable_record_id"] is None:
                    entry["cases"].setdefault(case_id, {})["unavailable_reason"] = (
                        "no %s record readable by this principal (%s); the form case is "
                        "skipped instead of substituting another role's record"
                        % (MODEL, entry["readable_record_error"] or "empty search result")
                    )
                    entry["cases"][case_id].setdefault("samples", [])
                    continue
                params["record_id"] = entry["readable_record_id"]
            case_entry = entry["cases"].setdefault(
                case_id, {"params": dict(params), "samples": [], "unavailable_reason": None}
            )
            case_entry["params"] = dict(params)
            if phase == "assembly_first":
                samples = [("assembly_first",)]
            elif phase == "hot":
                samples = [("hot_%d" % index,) for index in range(1, case["hot_samples"] + 1)]
            else:
                lcrc.CONTRACT_PROJECTION_HOT_CACHE.clear()
                samples = [("assembly_cold_role",)]
            for (phase_name,) in samples:
                case_entry["samples"].append(
                    _sample(entry["actor"], entry["user"], entry["shim"], params,
                            phase_name, _principal(entry["user"]))
                )


def _case_summary(entry, case_id):
    case_entry = entry["cases"].get(case_id) or {}
    samples = case_entry.get("samples") or []
    by_phase = {row["phase"]: row for row in samples}
    hot_rows = [row for row in samples if row["outcome"] == "dispatched" and row["phase"].startswith("hot_")]
    first = by_phase.get("assembly_first") or {}
    cold = by_phase.get("assembly_cold_role") or {}
    reference = hot_rows[-1] if hot_rows else cold or first
    return {
        "case": case_id,
        "params": case_entry.get("params"),
        "unavailable_reason": case_entry.get("unavailable_reason"),
        "outcome": first.get("outcome"),
        "permission_ok": first.get("permission_ok"),
        "denial": first.get("denial"),
        "handler_error": reference.get("handler_error"),
        "permission_ms": first.get("permission_ms"),
        "first_dispatch_ms": first.get("dispatch_ms"),
        "first_sql_count": first.get("sql_count"),
        "cold_dispatch_ms": cold.get("dispatch_ms"),
        "cold_sql_count": cold.get("sql_count"),
        "cold_deepcopy_count": cold.get("deepcopy_count"),
        "cold_cache_status": cold.get("cache_status"),
        "cold_relation_stage_ms": cold.get("relation_stage_ms"),
        "hot_dispatch_ms": _stats(hot_rows, "dispatch_ms"),
        "hot_sql_count": _stats(hot_rows, "sql_count"),
        "hot_deepcopy_count": _stats(hot_rows, "deepcopy_count"),
        "hot_cache_status": sorted({row["cache_status"] for row in hot_rows if row["cache_status"]}),
        "cache_identity_ref": reference.get("cache_identity_ref"),
        "cache_source_ref": reference.get("cache_source_ref"),
        "surface_sha256": reference.get("surface_sha256"),
        "response_sha256": reference.get("response_sha256"),
        "surface_facts": (reference.get("surface") or {}).get("facts"),
        "surface_top_level_counts": (reference.get("surface") or {}).get("top_level_counts"),
        "relation_surface": {
            key: value
            for key, value in (reference.get("relation_surface") or {}).items()
            if key != "entries"
        },
        "relation_entries": (reference.get("relation_surface") or {}).get("entries"),
    }


summaries = []
for entry in role_entries:
    summary = {
        "xmlid": entry["xmlid"],
        "label": entry["label"],
        "uid": entry["uid"],
        "company_id": entry["company_id"],
        "group_count": entry["group_count"],
        "group_digest": entry["group_digest"],
        "navigation_carrier": entry["navigation_carrier"],
        "navigation_capability": entry["navigation_capability"],
        "readable_record_id": entry["readable_record_id"],
        "readable_record_error": entry["readable_record_error"],
        "cases": {},
    }
    for case in REQUEST_CASES:
        summary["cases"][case["id"]] = _case_summary(entry, case["id"])
    summaries.append(summary)


def _case_analysis(case_id):
    available = [
        row for row in summaries if row["cases"][case_id].get("outcome") not in (None,)
    ]
    dispatched = [row for row in available if row["cases"][case_id]["outcome"] == "dispatched"]
    identities = {row["cases"][case_id]["cache_identity_ref"] for row in dispatched}
    surfaces = {row["cases"][case_id]["surface_sha256"] for row in dispatched}
    digests = {}
    for entry in role_entries:
        samples = [
            row
            for row in (entry["cases"].get(case_id) or {}).get("samples") or []
            if row["outcome"] == "dispatched" and row.get("surface_sha256")
        ]
        digests[entry["label"]] = sorted({row["surface_sha256"] for row in samples})
    canonical = {}
    for entry in role_entries:
        rows = [
            row
            for row in (entry["cases"].get(case_id) or {}).get("samples") or []
            if row["outcome"] == "dispatched" and row.get("_surface_canonical") is not None
        ]
        canonical[entry["label"]] = rows[-1]["_surface_canonical"] if rows else None
    baseline = canonical.get(BASELINE_ROLE)
    diff = {}
    if baseline is not None:
        for label, value in canonical.items():
            if value is None or label == BASELINE_ROLE:
                continue
            diff[label] = _diff_paths(baseline, value)
    instability = {}
    for entry in role_entries:
        rows = [
            row
            for row in (entry["cases"].get(case_id) or {}).get("samples") or []
            if row["outcome"] == "dispatched" and row.get("_surface_canonical") is not None
        ]
        if len(rows) < 2:
            instability[entry["label"]] = {"comparable_samples": len(rows), "stable": None,
                                           "diff_paths": []}
        else:
            paths = _diff_paths(rows[0]["_surface_canonical"], rows[-1]["_surface_canonical"])
            instability[entry["label"]] = {"comparable_samples": len(rows), "stable": not paths,
                                           "diff_paths": paths}
    return {
        "available_roles": [row["label"] for row in available],
        "unavailable_roles": [
            {"label": row["label"], "reason": row["cases"][case_id].get("unavailable_reason")}
            for row in summaries
            if row["cases"][case_id].get("unavailable_reason")
        ],
        "dispatched_roles": [row["label"] for row in dispatched],
        "relation_surface_per_role": {
            row["label"]: row["cases"][case_id]["relation_surface"] for row in dispatched
        },
        "navigation_authority_per_role": {
            row["label"]: (row["cases"][case_id]["relation_surface"] or {}).get(
                "with_navigation_authority"
            )
            for row in dispatched
        },
        "dialog_targets_per_role": {
            row["label"]: (row["cases"][case_id]["relation_surface"] or {}).get("dialog_targets")
            for row in dispatched
        },
        "relation_surface_varies_by_role": len(
            {
                json.dumps(row["cases"][case_id]["relation_surface"], sort_keys=True, default=str)
                for row in dispatched
            }
        ) > 1,
        "relation_field_map_varies_by_role": len(
            {
                json.dumps(row["cases"][case_id]["relation_entries"], sort_keys=True, default=str)
                for row in dispatched
            }
        ) > 1,
        "refused_roles": [
            {"label": row["label"], "outcome": row["cases"][case_id]["outcome"],
             "denial": row["cases"][case_id]["denial"],
             "handler_error": row["cases"][case_id]["handler_error"]}
            for row in available
            if row["cases"][case_id]["outcome"] != "dispatched"
        ],
        "identity_ref_count": len(identities),
        "identity_varies_by_role": len(identities) > 1,
        "surface_digest_count": len(surfaces),
        "surface_varies_by_role": len(surfaces) > 1,
        "surface_digest_stable_within_dispatched_role": all(
            len(digests[row["label"]]) == 1 for row in dispatched
        ),
        "surface_digest_per_role": {
            label: (values[0] if len(values) == 1 else None) for label, values in digests.items()
        },
        "surface_instability": instability,
        "surface_diff_vs_baseline": diff,
        "roles_differing_from_baseline": sorted(
            row["label"]
            for row in dispatched
            if row["label"] != BASELINE_ROLE
            and row["cases"][case_id]["surface_sha256"]
            != next(
                (r["cases"][case_id]["surface_sha256"] for r in summaries if r["label"] == BASELINE_ROLE),
                None,
            )
        ),
        "cold_dispatch_ms_spread": _stats_values(
            [row["cases"][case_id]["cold_dispatch_ms"] for row in dispatched
             if row["cases"][case_id]["cold_dispatch_ms"]]
        ),
        "hot_dispatch_ms_per_role": {
            row["label"]: (row["cases"][case_id]["hot_dispatch_ms"] or {}).get("median")
            for row in dispatched
        },
        "hot_sql_count_per_role": {
            row["label"]: (row["cases"][case_id]["hot_sql_count"] or {}).get("median")
            for row in dispatched
        },
        "surface_outline": _outline(canonical.get(BASELINE_ROLE)) if canonical.get(BASELINE_ROLE) else None,
    }


case_analysis = {case["id"]: _case_analysis(case["id"]) for case in REQUEST_CASES}
for entry in role_entries:
    for case in REQUEST_CASES:
        for row in (entry["cases"].get(case["id"]) or {}).get("samples") or []:
            row.pop("_surface_canonical", None)

REPORT["request"] = {
    "intent": INTENT,
    "action_id": ACTION_ID,
    "model": MODEL,
    "cases": [dict(case) for case in REQUEST_CASES],
    "phase_order": ["assembly_first", "hot", "assembly_cold_role"],
    "hot_cache_cleared_between": True,
    "registry_cleared": False,
    "baseline_role": BASELINE_ROLE,
    "process_first_role": PROCESS_FIRST_ROLE,
}
REPORT["identity"] = {
    "handlers/ui_contract_v2.py": _source_hash("handlers/ui_contract_v2.py"),
    "utils/load_contract_response_cache.py": _source_hash("utils/load_contract_response_cache.py"),
    "app_config_engine/services/assemblers/page_assembler.py": _source_hash(
        "app_config_engine/services/assemblers/page_assembler.py"
    ),
    "core/intent_router.py": _source_hash("core/intent_router.py"),
    "controllers/intent_dispatcher.py": _source_hash("controllers/intent_dispatcher.py"),
    "security/intent_permission.py": _source_hash("security/intent_permission.py"),
    # Route authority resolution runs MenuService.build_nav for every role, so
    # the menu projection implementation is an input to this matrix.
    "delivery/menu_service.py": _source_hash("delivery/menu_service.py"),
    "app_config_engine/models/app_nav_config.py": _source_hash(
        "app_config_engine/models/app_nav_config.py"
    ),
}
REPORT["roles"] = [
    {
        "xmlid": entry["xmlid"],
        "label": entry["label"],
        "uid": entry["uid"],
        "company_id": entry["company_id"],
        "group_count": entry["group_count"],
        "group_digest": entry["group_digest"],
        "navigation_carrier": entry["navigation_carrier"],
        "navigation_capability": entry["navigation_capability"],
        "readable_record_id": entry["readable_record_id"],
        "cases": {
            case["id"]: {
                "params": (entry["cases"].get(case["id"]) or {}).get("params"),
                "unavailable_reason": (entry["cases"].get(case["id"]) or {}).get("unavailable_reason"),
                "samples": (entry["cases"].get(case["id"]) or {}).get("samples") or [],
            }
            for case in REQUEST_CASES
        },
    }
    for entry in role_entries
]
REPORT["role_summary"] = summaries
REPORT["case_analysis"] = case_analysis
REPORT["findings"] = {
    "role_count": len(summaries),
    "navigation_capability_per_role": {
        row["label"]: row["navigation_capability"] for row in summaries
    },
    "navigation_capability_varies_by_role": len(
        {row["navigation_capability"] for row in summaries}
    ) > 1,
    "readable_record_per_role": {
        row["label"]: {"id": row["readable_record_id"], "error": row["readable_record_error"]}
        for row in summaries
    },
    "refusal_summary": {
        case["id"]: {
            "dispatched": len(case_analysis[case["id"]]["dispatched_roles"]),
            "refused": len(case_analysis[case["id"]]["refused_roles"]),
            "unavailable": len(case_analysis[case["id"]]["unavailable_roles"]),
        }
        for case in REQUEST_CASES
    },
    "all_refusals_are_explicit": all(
        (row["denial"] or row["handler_error"])
        for case in REQUEST_CASES
        for row in case_analysis[case["id"]]["refused_roles"]
    ),
    "refused_roles_never_report_a_contract": all(
        row["surface_sha256"] is None
        for summary in summaries
        for case in REQUEST_CASES
        for row in [summary["cases"][case["id"]]]
        if row["outcome"] != "dispatched"
    ),
    "contract_identity_varies_by_role": all(
        case_analysis[case["id"]]["identity_varies_by_role"] for case in REQUEST_CASES
    ),
    "contract_surface_varies_by_role": all(
        case_analysis[case["id"]]["surface_varies_by_role"] for case in REQUEST_CASES
    ),
    "surface_digest_stable_within_dispatched_role": all(
        case_analysis[case["id"]]["surface_digest_stable_within_dispatched_role"]
        for case in REQUEST_CASES
    ),
    "relation_surface_varies_by_role": {
        case["id"]: case_analysis[case["id"]]["relation_surface_varies_by_role"]
        for case in REQUEST_CASES
    },
    "relation_field_map_varies_by_role": {
        case["id"]: case_analysis[case["id"]]["relation_field_map_varies_by_role"]
        for case in REQUEST_CASES
    },
}
REPORT["limitations"] = [
    "in-process probe over the declared demo principals on the registered local demo database",
    "the probe shims odoo.http.request; controller ingress/session/transport and context_auth/json_response remain out of scope",
    "the process-local hot-cache clear affects only this throwaway odoo shell process; no registry cache is cleared",
    "process-first cost is paid by the first declared role of the first case and is recorded as such, not attributed to that role's steady state",
    "the form case uses the first record readable by the acting principal; a principal with no readable record skips the case instead of borrowing another role's record",
    "one fixed action (878) and two declared request cases; this is a role-dimension slice, not a per-menu or per-model capacity claim",
    "not an SLO, capacity or release claim; no freeze, commit, push or deployment",
]

env.cr.rollback()
env.cr.commit = _ORIGINAL_COMMIT
print("CONTRACT_ROLE_MATRIX_PROBE_REPORT " + json.dumps(REPORT, ensure_ascii=False, sort_keys=True))
