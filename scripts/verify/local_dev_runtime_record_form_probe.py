"""Uninstrumented read-only probe for record-bound form requests (P4 diagnostic).

The role-matrix and contract-request probes intentionally instrument SQL,
``copy.deepcopy`` and GC to attribute cost. Those wrappers are useful when the
question is "where did the time go", but they must not be used as the absolute
user-facing latency: a hot record form request performs a much larger graph
copy than a list request, so a per-call wrapper is not common-mode there.

This probe runs the real permission + ``ui.contract.v2`` dispatch path with no
monkey patches at all. It observes one declared demo principal (``role_finance``)
on the registered ``sc_dev_demo`` database, first touching the record form and
then repeating the same request in the same process. The only post-dispatch work
is serialising the response to measure its byte size, and that happens after the
dispatch timer has stopped.

Read-only: commit is refused and the transaction is rolled back. It changes no
product code, schema, fixture or ACL. The process-local hot cache is not cleared;
this measures the warm path a user actually re-enters.

The metric helpers and the semantic comparison are pure functions so the
non-zero unit test can import them without an Odoo environment. The executable
part only runs when ``env`` is present in the module globals, which is the case
when this file is fed to ``odoo shell`` through stdin.
"""
import hashlib
import json
import math


DATABASE = "sc_dev_demo"
ACTION_ID = 878
INTENT = "ui.contract.v2"
MODEL = "payment.request"
ROLE_XMLID = "smart_construction_demo.user_demo_role_finance"
HOT_SAMPLES = 6

# Only these exact response paths may differ between two semantically identical
# deliveries. A field-name-wide deletion is not allowed: the earlier filter
# dropped every ``timing`` key at every depth, which made a real business field
# such as ``data.business.timing.deadline`` invisible to the equivalence check.
# New exemptions must name the full path and the authority that owns it:
#   * top-level ``meta`` is the intent envelope, not the contract;
#   * ``data.meta.traceId``/``requestId`` and lifecycle runtime ids are transport
#     identity, re-issued for every request by the seal;
#   * the two ``context`` containers echo the live request context, whose
#     ``trace_id``/``request_id`` the intent dispatcher injects.
SEMANTIC_EXEMPT_PATHS = frozenset({
    ("meta", "elapsed_ms"),
    ("meta", "projection_cache"),
    ("data", "meta", "traceId"),
    ("data", "meta", "requestId"),
    ("data", "meta", "lifecycle", "runtime", "requestId"),
    ("data", "meta", "lifecycle", "runtime", "traceId"),
    ("data", "dataContract", "dataMeta", "sourceContext", "context", "trace_id"),
    ("data", "dataContract", "dataMeta", "sourceContext", "context", "request_id"),
    ("data", "dataContract", "dataSource", "primary", "params", "context", "trace_id"),
    ("data", "dataContract", "dataSource", "primary", "params", "context", "request_id"),
})


def _sorted_values(values):
    return sorted(float(value) for value in values)


def _median(values):
    """Median of an already sorted sample list.

    Even-sized windows take the mean of the two middle values. The previous
    implementation took ``values[len // 2]``, which for six samples is the
    fourth value, not the median.
    """
    count = len(values)
    if not count:
        raise ValueError("median of an empty sample")
    middle = count // 2
    if count % 2:
        return values[middle]
    return (values[middle - 1] + values[middle]) / 2.0


def _nearest_rank(values, percentile):
    """Nearest-rank percentile of an already sorted sample list."""
    if not values:
        raise ValueError("percentile of an empty sample")
    rank = max(1, min(len(values), int(math.ceil(percentile * len(values)))))
    return values[rank - 1]


def _stats(values):
    sorted_values = _sorted_values(values)
    if not sorted_values:
        return None
    p95 = _nearest_rank(sorted_values, 0.95)
    window_observation_only = len(sorted_values) < 20
    return {
        "n": len(sorted_values),
        "min": sorted_values[0],
        "median": round(_median(sorted_values), 3),
        "p95": round(p95, 3),
        "p95_method": "nearest_rank",
        "p95_equals_max": p95 == sorted_values[-1],
        "p95_interpretation": (
            "window_max_observation" if window_observation_only else "nearest_rank"
        ),
        "window_observation_only": window_observation_only,
        "max": sorted_values[-1],
        "samples": sorted_values,
    }


def _semantic_copy(value, path=()):
    """Copy ``value`` dropping only the registered per-request paths."""
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            child_path = path + (str(key),)
            if child_path in SEMANTIC_EXEMPT_PATHS:
                continue
            out[key] = _semantic_copy(item, child_path)
        return out
    if isinstance(value, list):
        return [_semantic_copy(item, path + ("[]",)) for item in value]
    return value


def _diff_paths(left, right, path=()):
    """Return the exact paths at which two JSON-shaped values differ."""
    if type(left) is not type(right):
        return {path}
    if isinstance(left, dict):
        differences = set()
        for key in sorted(set(left) | set(right), key=str):
            if key not in left or key not in right:
                differences.add(path + (str(key),))
                continue
            differences |= _diff_paths(left[key], right[key], path + (str(key),))
        return differences
    if isinstance(left, list):
        if len(left) != len(right):
            return {path}
        differences = set()
        for index, (left_item, right_item) in enumerate(zip(left, right)):
            differences |= _diff_paths(
                left_item, right_item, path + ("[%d]" % index,)
            )
        return differences
    return {path} if left != right else set()


def _sha256_json(value):
    encoded = json.dumps(
        value, sort_keys=True, ensure_ascii=False, default=str, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def semantic_digest(value):
    return _sha256_json(_semantic_copy(value))


def semantic_section_digests(value):
    """Digest the filtered payload one top-level and second-level section apart.

    A full-payload match proves equivalence but not where a difference lives.
    These per-section digests let an A/B log comparison localise a regression
    without keeping the multi-megabyte raw response.
    """
    semantic = _semantic_copy(value)
    if not isinstance(semantic, dict):
        return {"<root>": _sha256_json(semantic)}
    digests = {}
    for key, item in semantic.items():
        digests[str(key)] = _sha256_json(item)
        if isinstance(item, dict):
            for sub_key, sub_item in item.items():
                digests["%s.%s" % (key, sub_key)] = _sha256_json(sub_item)
    return digests


def _payload(params, company):
    return {
        "intent": INTENT,
        "params": dict(params),
        "context": {"allowed_company_ids": [company], "lang": "zh_CN"},
        "meta": {},
    }


def _request(*, actor, user, shim, params, phase, router, permission_module,
             request_context_cls, capture=None):
    import time

    principal = {
        "auth_method": "password",
        "principal_type": "human",
        "user_id": user.id,
        "payload": {"db": DATABASE},
    }
    ctx = request_context_cls(actor, user, dict(params), request_obj=shim, principal=principal)
    original_ip_request = permission_module.request
    original_router_request = router.request
    permission_module.request = shim
    router.request = shim
    permission_ok = None
    error = None
    result = None
    started = time.perf_counter()
    try:
        permission_ok = bool(permission_module.check_intent_permission(ctx))
    except Exception as exc:
        permission_ok = False
        error = "permission: %s: %s" % (type(exc).__name__, exc)
    finally:
        permission_ms = (time.perf_counter() - started) * 1000.0
    dispatch_ms = None
    if permission_ok:
        started = time.perf_counter()
        try:
            result = router.route_intent_payload(
                _payload(params, user.company_id.id),
                ctx=ctx,
            )
        except Exception as exc:
            error = "dispatch: %s: %s" % (type(exc).__name__, exc)
        finally:
            dispatch_ms = (time.perf_counter() - started) * 1000.0
    permission_module.request = original_ip_request
    router.request = original_router_request

    serializable = None
    if result is not None:
        serializable = result.to_legacy_dict() if hasattr(result, "to_legacy_dict") else result
    if capture is not None and serializable is not None:
        capture[phase] = serializable
    meta = (serializable or {}).get("meta") or {} if isinstance(serializable, dict) else {}
    projection = meta.get("projection_cache") or {}
    raw_response = (
        json.dumps(serializable, sort_keys=True, default=str)
        if serializable is not None
        else ""
    )
    contract_meta = {}
    if isinstance(serializable, dict):
        contract_meta = (serializable.get("data") or {}).get("meta") or {}
    lifecycle = contract_meta.get("lifecycle") or {}
    integrity = lifecycle.get("integrity") or {}
    return {
        "phase": phase,
        "permission_ok": permission_ok,
        "permission_ms": round(permission_ms, 3) if permission_ms is not None else None,
        "dispatch_ms": round(dispatch_ms, 3) if dispatch_ms is not None else None,
        "error": error,
        "cache_status": projection.get("status"),
        "cache_reason": projection.get("reason"),
        "cache_stages_ms": projection.get("stages_ms"),
        "handler_elapsed_ms": meta.get("elapsed_ms"),
        "response_bytes": len(raw_response),
        "response_sha256": (
            hashlib.sha256(raw_response.encode("utf-8")).hexdigest()
            if raw_response
            else None
        ),
        "response_semantic_sha256": (
            semantic_digest(serializable) if serializable is not None else None
        ),
        "contract_sha256": integrity.get("contractSha256"),
    }


def _probe(env):
    from types import SimpleNamespace

    from odoo import api
    from odoo.addons.smart_core.core import intent_router
    from odoo.addons.smart_core.core.context import RequestContext
    from odoo.addons.smart_core.security import intent_permission as ip

    assert env.cr.dbname == DATABASE, "registered local.dev database required"
    env.cr.rollback()
    original_commit = env.cr.commit

    def _refuse_commit(*_args, **_kwargs):
        raise RuntimeError("record form probe forbids commit")

    env.cr.commit = _refuse_commit

    class _RequestShim:
        """Minimal faithful stand-in for ``odoo.http.request``; transport is out of scope."""

        def __init__(self, environment):
            self.env = environment
            self.uid = environment.uid
            self.session = SimpleNamespace(db=DATABASE, uid=environment.uid)
            self.httprequest = SimpleNamespace(headers={}, remote_addr="127.0.0.1")
            self.params = {}
            self.jsonrequest = None

    user = env.ref(ROLE_XMLID)
    assert user.active and not user.share, "declared demo principal unavailable"
    company = user.company_id.id
    actor = api.Environment(
        env.cr, user.id, {"allowed_company_ids": [company], "lang": "zh_CN"}
    )
    assert not actor.su, "actor must not be elevated"
    shim = _RequestShim(actor)

    record = actor[MODEL].search([], limit=1)
    assert record, "no readable %s record for the declared principal" % MODEL
    record_id = record.id

    base_params = {"action_id": ACTION_ID, "op": "action_open"}
    form_params = dict(base_params, record_id=record_id)
    captures = {}

    form_rows = [
        _request(
            actor=actor, user=user, shim=shim, params=form_params,
            phase="assembly_first", router=intent_router, permission_module=ip,
            request_context_cls=RequestContext, capture=captures,
        )
    ]
    for index in range(1, HOT_SAMPLES + 1):
        phase = "hot_%d" % index
        form_rows.append(
            _request(
                actor=actor, user=user, shim=shim, params=form_params,
                phase=phase, router=intent_router, permission_module=ip,
                request_context_cls=RequestContext,
                capture=captures if index <= 2 else None,
            )
        )

    list_rows = [
        _request(
            actor=actor, user=user, shim=shim, params=base_params,
            phase="list_first", router=intent_router, permission_module=ip,
            request_context_cls=RequestContext,
        )
    ]
    for index in range(1, HOT_SAMPLES + 1):
        list_rows.append(
            _request(
                actor=actor, user=user, shim=shim, params=base_params,
                phase="list_hot_%d" % index, router=intent_router,
                permission_module=ip, request_context_cls=RequestContext,
            )
        )

    form_hot = [
        row["dispatch_ms"]
        for row in form_rows
        if row["phase"].startswith("hot_") and row["dispatch_ms"]
    ]
    list_hot = [
        row["dispatch_ms"]
        for row in list_rows
        if row["phase"].startswith("list_hot_") and row["dispatch_ms"]
    ]
    varying_paths = set()
    if "hot_1" in captures and "hot_2" in captures:
        varying_paths = _diff_paths(captures["hot_1"], captures["hot_2"])

    section_digests = {
        phase: semantic_section_digests(payload)
        for phase, payload in captures.items()
    }
    report = {
        "schema": "runtime-record-form-probe/v2",
        "database": DATABASE,
        "instrumentation": "none",
        "request": {
            "intent": INTENT,
            "action_id": ACTION_ID,
            "model": MODEL,
            "record_id": record_id,
            "principal": ROLE_XMLID,
            "uid": user.id,
            "company_id": company,
            "hot_samples": HOT_SAMPLES,
        },
        "form": {
            "first": form_rows[0],
            "hot": _stats(form_hot),
            "rows": form_rows,
        },
        "list": {
            "first": list_rows[0],
            "hot": _stats(list_hot),
            "rows": list_rows,
        },
        "semantic": {
            "exempt_paths": sorted(".".join(path) for path in SEMANTIC_EXEMPT_PATHS),
            "varying_paths_hot_1_vs_hot_2": sorted(".".join(path) for path in varying_paths),
            "section_sha256": section_digests,
        },
        "acceptance_pass": False,
        "limitations": [
            "one declared demo principal and one readable record; this is a bounded diagnostic, not a matrix",
            "process-local hot cache is not cleared; first dispatch still includes process-first initialisation",
            "response serialisation and sha256 are computed after the dispatch timer stops",
            "with six samples the nearest-rank p95 is the window maximum; it is an observation, not a tail estimate",
        ],
    }

    env.cr.rollback()
    env.cr.commit = original_commit
    return report


if "env" in globals():
    print(
        "CONTRACT_RECORD_FORM_PROBE_REPORT "
        + json.dumps(_probe(env), sort_keys=True, default=str)
    )
