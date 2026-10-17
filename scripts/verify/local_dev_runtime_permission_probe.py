"""Bounded permission-gate attribution probe for R4 (P4 diagnostic).

The controller ``permission`` segment for the process-first ``ui.contract.v2``
list request was observed at ~215 ms, while the same segment on later requests
is ~2 ms. This probe answers, with runtime evidence instead of code reading:

1. which sub-phase of the *unmodified* ``check_intent_permission`` gate owns the
   cost, and how often each sub-phase runs inside one gate invocation;
2. whether that cost is a one-time process initialization or a per-request cost,
   by comparing the process-first invocation, a registry-cache-cleared
   invocation and warm repeats;
3. whether the observed request shape (``menu_id`` present or absent) selects the
   expensive publication-authority branch.

The earlier ``first_touch_of_process`` reading was already warm: deriving the
observed menu carrier calls the process-cached ``sc.product.policy``
``published_route_authority()`` before the first gate. To close the gap between
the controller's observed ``permission`` segment and the registry-cleared cold
reading, the probe accepts an optional ``PRODUCT_PERFORMANCE_PERMISSION_CARRIER`` value so
the *genuinely* first gate of the process can run before any other authority read.

Read-only: commit is refused, the probe rolls back, it changes no product code,
schema, fixture or ACL. ``registry.clear_cache()`` only clears this throwaway
``odoo shell`` process, never the serving workers.
"""
import hashlib
import importlib
import inspect
import json
import os
import time
from pathlib import Path
from types import SimpleNamespace

from odoo import api, models
from odoo.addons.smart_core.core.context import RequestContext

DATABASE = "sc_dev_demo"
ACTION_ID = 878
INTENT = "ui.contract.v2"

assert env.cr.dbname == DATABASE, "registered local.dev database required"
env.cr.rollback()
_ORIGINAL_COMMIT = env.cr.commit


def _refuse_commit(*_args, **_kwargs):
    raise RuntimeError("permission probe forbids commit")


env.cr.commit = _refuse_commit

REPORT = {"schema": "runtime-permission-probe/v1", "database": DATABASE, "acceptance_pass": False}
PROCESS_FIRST = {}


def _timed_import(name):
    started = time.perf_counter()
    module = importlib.import_module(name)
    return module, (time.perf_counter() - started) * 1000.0


MODULES = {
    "intent_permission": "odoo.addons.smart_core.security.intent_permission",
    "credential_service": "odoo.addons.smart_core.security.credential_service",
    "runtime_route_authority": "odoo.addons.smart_core.delivery.runtime_route_authority",
    "menu_service": "odoo.addons.smart_core.delivery.menu_service",
    "product_policy_service": "odoo.addons.smart_core.delivery.product_policy_service",
    "delivery_engine": "odoo.addons.smart_core.delivery.delivery_engine",
    "identity_resolver": "odoo.addons.smart_core.identity.identity_resolver",
    "system_init": "odoo.addons.smart_core.handlers.system_init",
}
IMPORT_MS = {}
_MODS = {}
for _key, _name in MODULES.items():
    _MODS[_key], IMPORT_MS[_key] = _timed_import(_name)

ip = _MODS["intent_permission"]
tra = _MODS["runtime_route_authority"]
credentials = _MODS["credential_service"]
menu_service = _MODS["menu_service"]
policy_service = _MODS["product_policy_service"]
delivery_engine = _MODS["delivery_engine"]
identity_resolver = _MODS["identity_resolver"]
system_init = _MODS["system_init"]

# --- instrumentation ---------------------------------------------------------
STATE = {"scenario": None, "phase": None, "phases": {}, "counts": {}, "oracle": {}}


def _mark(name, ms):
    if STATE["scenario"] is None:
        return  # setup/warm-up work outside a declared scenario is not attributed
    bucket = STATE["phases"].setdefault(STATE["scenario"], {}).setdefault(STATE["phase"], {})
    bucket[name] = round(bucket.get(name, 0.0) + ms, 3)


def _bump(name):
    if STATE["scenario"] is None:
        return
    counts = STATE["counts"].setdefault(STATE["scenario"], {}).setdefault(STATE["phase"], {})
    counts[name] = counts.get(name, 0) + 1


def _wrap(owner, attr, name):
    """Time and count one unmodified helper; the wrapped behaviour is the original."""
    original = getattr(owner, attr)

    def wrapper(*args, **kwargs):
        started = time.perf_counter()
        try:
            return original(*args, **kwargs)
        finally:
            _bump(name)
            _mark(name, (time.perf_counter() - started) * 1000.0)

    wrapper.__wrapped__ = original
    setattr(owner, attr, wrapper)


for _attr in (
    "_sync_authenticated_identity",
    "_permission_env_for_params",
    "access_mode_for_intent",
    "work_item_request_access_mode",
    "_resolve_model",
    "_model_acl_policy",
    "_record_ids",
    "_published_menu_decision",
    "_resolve_action",
    "_find_capability",
    "_effective_flags",
    "_is_ui_only_config_intent",
    "_capability_key",
):
    _wrap(ip, _attr, "intent_permission." + _attr)
_wrap(credentials, "assert_principal_scope", "credential_service.assert_principal_scope")
_wrap(tra, "build_runtime_route_authority", "runtime_route_authority.build_runtime_route_authority")
_wrap(tra, "_build_runtime_route_authority", "runtime_route_authority._build_runtime_route_authority")
_wrap(tra, "principal_group_signature", "runtime_route_authority.principal_group_signature")
_wrap(menu_service.MenuService, "build_nav", "MenuService.build_nav")
_wrap(menu_service.MenuService, "build_route_authority", "MenuService.build_route_authority")
_wrap(menu_service.MenuService, "filter_route_authority_by_publication", "MenuService.filter_route_authority_by_publication")
_wrap(policy_service.ProductPolicyService, "get_policy", "ProductPolicyService.get_policy")
_wrap(delivery_engine.DeliveryEngine, "_normalize_delivery_nav_refs", "DeliveryEngine._normalize_delivery_nav_refs")
_wrap(identity_resolver.IdentityResolver, "user_group_xmlids", "IdentityResolver.user_group_xmlids")
_wrap(identity_resolver.IdentityResolver, "build_role_surface", "IdentityResolver.build_role_surface")
_wrap(system_init, "_resolve_startup_delivery_identity", "system_init._resolve_startup_delivery_identity")
_wrap(system_init, "_load_platform_release_gate", "system_init._load_platform_release_gate")
_wrap(system_init, "_filter_nav_by_release_gate", "system_init._filter_nav_by_release_gate")

ACL = {"ms": 0.0, "count": 0, "models": {}}
SQL = {"ms": 0.0, "count": 0}


def _wrap_model_method(attr):
    original = getattr(models.BaseModel, attr)

    def wrapper(self, *args, **kwargs):
        started = time.perf_counter()
        try:
            return original(self, *args, **kwargs)
        finally:
            ACL["ms"] += (time.perf_counter() - started) * 1000.0
            ACL["count"] += 1
            ACL["models"][self._name] = ACL["models"].get(self._name, 0) + 1
            _bump("BaseModel." + attr)

    wrapper.__wrapped__ = original
    setattr(models.BaseModel, attr, wrapper)


_wrap_model_method("check_access_rights")
_wrap_model_method("check_access_rule")

_SQL_ORIGINAL = type(env.cr).execute


def _execute_timed(self, query, params=None, log_exceptions=None):
    started = time.perf_counter()
    try:
        return _SQL_ORIGINAL(self, query, params, log_exceptions)
    finally:
        SQL["ms"] += (time.perf_counter() - started) * 1000.0
        SQL["count"] += 1


type(env.cr).execute = _execute_timed


class _RequestShim:
    """Minimal faithful stand-in for ``odoo.http.request`` used by the gate only."""

    def __init__(self, environment):
        self.env = environment
        self.uid = environment.uid
        self.session = SimpleNamespace(db=DATABASE, uid=environment.uid)


_ORIGINAL_REQUEST = ip.request
_ORIGINAL_SP_ORMCACHE = None

_PF_FIRST_ORM_STARTED = time.perf_counter()
user = env.ref("smart_construction_demo.user_demo_role_finance")
PROCESS_FIRST["first_orm_read_env_ref_ms"] = round((time.perf_counter() - _PF_FIRST_ORM_STARTED) * 1000.0, 3)
assert user.active and not user.share, "declared demo finance identity unavailable"
company = user.company_id.id
actor = api.Environment(env.cr, user.id, {"allowed_company_ids": [company], "lang": "zh_CN"})
assert not actor.su, "actor must not be elevated"

# The carrier may be supplied so the first gate can run before any other ORM
# work warms the process-cached published route authority.
_PF_CARRIER_ENV = os.environ.get("PRODUCT_PERFORMANCE_PERMISSION_CARRIER")
PF_CARRIER = int(_PF_CARRIER_ENV) if _PF_CARRIER_ENV else None
Policy = actor["sc.product.policy"]
CARRIER = PF_CARRIER
if CARRIER is None:
    _pf_acl_before, _pf_sql_before = ACL["count"], SQL["count"]
    STATE["scenario"] = "process_first_authority_read"
    STATE["phase"] = "first_read"
    try:
        _pf_authority_started = time.perf_counter()
        _pf_authority = Policy.published_route_authority()
        _pf_authority_ms = (time.perf_counter() - _pf_authority_started) * 1000.0
    finally:
        STATE["scenario"] = None
        STATE["phase"] = None
    PROCESS_FIRST["first_published_route_authority_read_ms"] = round(_pf_authority_ms, 3)
    PROCESS_FIRST["first_published_route_authority_read_acls"] = ACL["count"] - _pf_acl_before
    PROCESS_FIRST["first_published_route_authority_read_sql"] = SQL["count"] - _pf_sql_before
    for _menu_id, _action_id in tra.iter_published_pairs(_pf_authority):
        if int(_action_id) == ACTION_ID and int(_menu_id) > 0:
            CARRIER = int(_menu_id)
            break
PROCESS_FIRST["carrier_source"] = "environment" if PF_CARRIER is not None else "derived_in_process"
assert CARRIER, "no published menu carrier for the observed action"

NO_MENU = {"intent": INTENT, "action_id": ACTION_ID, "op": "action_open"}
WITH_MENU = dict(NO_MENU, menu_id=CARRIER)
SCENARIOS = {"without_menu_id": NO_MENU, "with_menu_id": WITH_MENU}

GATE = {}


def _gate(params, *, gate_user=None, gate_actor=None, principal=None):
    gate_user = user if gate_user is None else gate_user
    gate_actor = actor if gate_actor is None else gate_actor
    shim = _RequestShim(gate_actor or actor)
    ip.request = shim
    if principal is None:
        principal = {
            "auth_method": "password",
            "principal_type": "human",
            "user_id": gate_user.id,
            "payload": {"db": DATABASE},
        }
    ctx = RequestContext(gate_actor, gate_user, dict(params), request_obj=shim, principal=principal)
    started = time.perf_counter()
    error = None
    ok = False
    try:
        ok = bool(ip.check_intent_permission(ctx))
    except Exception as exc:
        error = "%s: %s" % (type(exc).__name__, exc)
    finally:
        ip.request = _ORIGINAL_REQUEST
    return ok, error, (time.perf_counter() - started) * 1000.0


def _run(scenario, phase):
    STATE["scenario"] = scenario
    STATE["phase"] = phase
    ACL["ms"] = ACL["count"] = 0
    ACL["models"] = {}
    SQL["ms"] = SQL["count"] = 0
    ok, error, elapsed = _gate(SCENARIOS[scenario])
    key = scenario + ":" + phase
    GATE[key] = {
        "ok": ok,
        "error": error,
        "gate_ms": round(elapsed, 3),
        "acl_ms": round(ACL["ms"], 3),
        "acl_count": ACL["count"],
        "acl_models": dict(sorted(ACL["models"].items())),
        "sql_ms": round(SQL["ms"], 3),
        "sql_count": SQL["count"],
    }


# 1. Genuinely-first gate of this throwaway process: only runs when the carrier
#    was supplied, so this gate, and not the setup, pays the one-time authority
#    build plus the process-first ORM/module cache cold.
if PF_CARRIER is not None:
    _run("with_menu_id", "process_first_true")
# 2. First invocation on the real request shape after setup (authority already warm).
_run("with_menu_id", "first_touch_of_process")
# 2. Per-scenario cold/warm, each cold preceded by a registry-cache clear so the
#    one-time authority/registry work must reappear instead of being inherited.
for scenario in ("without_menu_id", "with_menu_id"):
    env.registry.clear_cache()
    _run(scenario, "cold_after_registry_clear")
    for index in range(1, 5):
        _run(scenario, "warm_%d" % index)

# 3. Boundary counterexamples: the gate must still deny, and the documented
#    synthetic-navigation and company branches must behave as declared.
STATE["scenario"] = "negatives"

# N3 target: an existing action whose groups_id excludes this principal.
_ACTION_WITH_DENIED_GROUPS = None
_ACTION_PROBE = []
for _candidate in actor["ir.actions.act_window"].sudo().search([("groups_id", "!=", False)], limit=400):
    _groups = set(_candidate.groups_id.ids)
    _mine = set(actor["res.users"].browse(user.id).groups_id.ids)
    _ACTION_PROBE.append({"id": int(_candidate.id), "groups": sorted(_groups),
                          "intersection": sorted(_groups & _mine)})
    if _groups and not (_groups & _mine):
        _ACTION_WITH_DENIED_GROUPS = int(_candidate.id)
        break

# Resolution facts for the action branch: which model the gate resolves first,
# and whether that model exposes the declared ``groups_id`` restriction.
ACTION_RESOLUTION = []
for _action_id in (ACTION_ID, 72):
    for _model_name in ("ir.actions.actions", "ir.actions.act_window"):
        _record = actor[_model_name].sudo().browse(_action_id)
        _exists = bool(_record.exists())
        _has_groups = hasattr(_record, "groups_id") and "groups_id" in _record._fields
        ACTION_RESOLUTION.append({
            "action_id": _action_id,
            "model": _model_name,
            "exists": _exists,
            "has_groups_id_field": _has_groups,
            "groups": sorted(_record.groups_id.ids) if (_exists and _has_groups) else None,
            "name": _record.name if _exists and "name" in _record._fields else None,
        })
# Blast radius: actions whose declared groups exclude this principal, and
# whether the publication authority contains them at all.
_PUBLISHED_ACTION_IDS = {int(aid) for _menu, aid in tra.iter_published_pairs(Policy.published_route_authority())}
_ACTION_SCOPE = {"act_window_total": int(env["ir.actions.act_window"].sudo().search_count([])),
                 "act_window_with_groups": 0, "act_window_group_excluded": [],
                 "excluded_but_published": [], "action_72_published": 72 in _PUBLISHED_ACTION_IDS}
for _row in actor["ir.actions.act_window"].sudo().search([("groups_id", "!=", False)]):
    _ACTION_SCOPE["act_window_with_groups"] += 1
    if _row.groups_id and not (_row.groups_id & user.groups_id):
        _ACTION_SCOPE["act_window_group_excluded"].append(int(_row.id))
        if int(_row.id) in _PUBLISHED_ACTION_IDS:
            _ACTION_SCOPE["excluded_but_published"].append(int(_row.id))
_ACTION_SCOPE["published_action_count"] = len(_PUBLISHED_ACTION_IDS)

_resolved = ip._resolve_action(actor, 72, action_type=None)
ACTION_RESOLUTION.append({
    "action_id": 72,
    "model": _resolved._name if _resolved else None,
    "exists": bool(_resolved),
    "has_groups_id_field": bool(_resolved) and "groups_id" in _resolved._fields,
    "groups": sorted(_resolved.groups_id.ids) if (_resolved and "groups_id" in _resolved._fields) else None,
    "name": _resolved.name if _resolved else None,
})

SECOND_COMPANY = next((int(cid) for cid in user.company_ids.ids if int(cid) != company), None)
_second_actor = (
    api.Environment(env.cr, user.id, {"allowed_company_ids": [SECOND_COMPANY], "lang": "zh_CN"})
    if SECOND_COMPANY
    else None
)

NEGATIVES = {
    "unpublished_menu_pair": (dict(WITH_MENU, action_id=(ACTION_ID + 1 if ACTION_ID != 1 else 2)), {}),
    "nonexistent_model": ({"intent": INTENT, "op": "model", "model": "sc.probe.absent.model", "view_type": "form"}, {}),
    "synthetic_navigation_menu": (dict(NO_MENU, menu_id=600000001), {}),
}
if _ACTION_WITH_DENIED_GROUPS:
    NEGATIVES["action_group_excluded"] = (
        {"intent": INTENT, "op": "action_open", "action_id": _ACTION_WITH_DENIED_GROUPS},
        {},
    )
if _second_actor is not None:
    NEGATIVES["company_scope_switch"] = (dict(WITH_MENU), {"gate_actor": _second_actor})

for _name, (_params, _kwargs) in NEGATIVES.items():
    STATE["phase"] = _name
    _ok, _error, _elapsed = _gate(_params, **_kwargs)
    GATE["negatives:" + _name] = {"ok": _ok, "error": _error, "gate_ms": round(_elapsed, 3)}

STATE["scenario"] = None
ip.request = _ORIGINAL_REQUEST
type(env.cr).execute = _SQL_ORIGINAL

WARM = {}
for scenario in ("without_menu_id", "with_menu_id"):
    samples = sorted(GATE[scenario + ":warm_%d" % index]["gate_ms"] for index in range(1, 5))
    WARM[scenario] = {
        "samples_ms": samples,
        "min_ms": samples[0],
        "median_ms": samples[len(samples) // 2],
        "max_ms": samples[-1],
    }


def _counts(scenario, phase, name):
    return STATE["counts"].get(scenario, {}).get(phase, {}).get(name, 0)


def _phases(scenario, phase):
    return STATE["phases"].get(scenario, {}).get(phase, {})


def _source_hash(relative):
    return hashlib.sha256((Path(inspect.getsourcefile(ip)).parents[1] / relative).read_bytes()).hexdigest()


entitlement_available = False
try:
    actor["sc.entitlement"]
    entitlement_available = True
except Exception:
    entitlement_available = False

REPORT["principal"] = {
    "xmlid": "smart_construction_demo.user_demo_role_finance",
    "uid": user.id,
    "company_id": company,
    "sudo": bool(actor.su),
}
REPORT["request"] = {
    "intent": INTENT,
    "action_id": ACTION_ID,
    "observed_menu_carrier_id": CARRIER,
    "scenarios": {name: dict(params) for name, params in SCENARIOS.items()},
}
REPORT["identity"] = {
    "security/intent_permission.py": hashlib.sha256(Path(inspect.getsourcefile(ip)).read_bytes()).hexdigest(),
    "delivery/runtime_route_authority.py": _source_hash("delivery/runtime_route_authority.py"),
    "delivery/menu_service.py": _source_hash("delivery/menu_service.py"),
    # The probe's build_nav sample reaches the menu projection cache.
    "app_config_engine/models/app_nav_config.py": _source_hash("app_config_engine/models/app_nav_config.py"),
    "controllers/intent_dispatcher.py": _source_hash("controllers/intent_dispatcher.py"),
}
REPORT["import_ms"] = {key: round(ms, 3) for key, ms in IMPORT_MS.items()}
REPORT["gate"] = GATE
REPORT["warm"] = WARM
REPORT["phases_ms"] = STATE["phases"]
REPORT["call_counts"] = STATE["counts"]
REPORT["entitlement_model_available"] = entitlement_available
REPORT["action_resolution"] = ACTION_RESOLUTION
REPORT["action_auth_scope"] = _ACTION_SCOPE
REPORT["negatives"] = {key.split(":", 1)[1]: row for key, row in GATE.items() if key.startswith("negatives:")}
_pf_phases = _phases("with_menu_id", "process_first_true")
_pf_gate_ms = GATE["with_menu_id:process_first_true"]["gate_ms"] if "with_menu_id:process_first_true" in GATE else None
_pf_authority_ms = _pf_phases.get("runtime_route_authority._build_runtime_route_authority")
REPORT["process_first"] = {
    "carrier_source": PROCESS_FIRST.get("carrier_source"),
    "first_orm_read_env_ref_ms": PROCESS_FIRST.get("first_orm_read_env_ref_ms"),
    "first_published_route_authority_read_ms": PROCESS_FIRST.get("first_published_route_authority_read_ms"),
    "first_published_route_authority_read_acls": PROCESS_FIRST.get("first_published_route_authority_read_acls"),
    "first_published_route_authority_read_sql": PROCESS_FIRST.get("first_published_route_authority_read_sql"),
    "first_published_route_authority_read_subphases_ms": _phases("process_first_authority_read", "first_read"),
    "controller_observed_first_permission_ms": 215.173,
    "true_first_gate_ms": _pf_gate_ms,
    "true_first_gate_subphases_ms": _pf_phases,
    "true_first_gate_acls": GATE.get("with_menu_id:process_first_true", {}).get("acl_count"),
    "true_first_gate_sql": GATE.get("with_menu_id:process_first_true", {}).get("sql_count"),
    "innermost_authority_build_ms": _pf_authority_ms,
    "process_first_module_orm_cold_residual_ms": (
        round(_pf_gate_ms - _pf_authority_ms, 3)
        if _pf_gate_ms is not None and _pf_authority_ms is not None else None
    ),
    "second_gate_after_setup_ms": GATE["with_menu_id:first_touch_of_process"]["gate_ms"],
    "registry_cleared_cold_gate_ms": GATE["with_menu_id:cold_after_registry_clear"]["gate_ms"],
}
REPORT["findings"] = {
    "menu_publication_branch_selected_by_menu_id": {
        "without_menu_id": _counts("without_menu_id", "cold_after_registry_clear", "intent_permission._published_menu_decision"),
        "with_menu_id": _counts("with_menu_id", "cold_after_registry_clear", "intent_permission._published_menu_decision"),
    },
    "route_authority_build_calls": {
        "process_first_with_menu": _counts("with_menu_id", "first_touch_of_process", "runtime_route_authority._build_runtime_route_authority"),
        "with_menu_cold": _counts("with_menu_id", "cold_after_registry_clear", "runtime_route_authority._build_runtime_route_authority"),
        "with_menu_warm_1": _counts("with_menu_id", "warm_1", "runtime_route_authority._build_runtime_route_authority"),
    },
    "process_first_gate_ms": GATE["with_menu_id:first_touch_of_process"]["gate_ms"],
    "cold_with_menu_gate_ms": GATE["with_menu_id:cold_after_registry_clear"]["gate_ms"],
    "warm_gate_ms": {name: row["median_ms"] for name, row in WARM.items()},
    "first_touch_is_one_time": (
        GATE["with_menu_id:cold_after_registry_clear"]["gate_ms"]
        > 4 * WARM["with_menu_id"]["median_ms"]
    ),
    "per_request_gate_is_not_the_215ms_segment": (
        WARM["with_menu_id"]["median_ms"] < 5.0 and WARM["without_menu_id"]["median_ms"] < 5.0
    ),
    "published_route_authority_is_the_cold_owner": (
        _phases("with_menu_id", "cold_after_registry_clear").get("intent_permission._published_menu_decision", 0.0)
        / max(GATE["with_menu_id:cold_after_registry_clear"]["gate_ms"], 1e-9)
        > 0.9
    ),
    "no_redundant_duplicate_authority_build_in_one_gate": (
        _counts("with_menu_id", "cold_after_registry_clear", "runtime_route_authority._build_runtime_route_authority") == 1
        and _counts("with_menu_id", "warm_1", "runtime_route_authority._build_runtime_route_authority") == 0
        and _counts("with_menu_id", "warm_1", "runtime_route_authority.build_runtime_route_authority") == 1
    ),
    "warm_key_cost_is_the_group_signature": round(
        _phases("with_menu_id", "warm_1").get("runtime_route_authority.principal_group_signature", 0.0), 3
    ),
    "boundary_denials": {key.split(":", 1)[1]: bool(not row["ok"]) for key, row in GATE.items()
                         if key.startswith("negatives:")},
    "denied_action_probe_id": _ACTION_WITH_DENIED_GROUPS,
    "denied_action_probe_detail": _ACTION_PROBE[:3],
    "denied_action_gate": GATE.get("negatives:action_group_excluded"),
    "second_company_id": SECOND_COMPANY,
}
REPORT["limitations"] = [
    "in-process probe on the registered local demo finance principal and one observed action",
    "the probe shims odoo.http.request for the gate; controller ingress/session/transport is out of scope",
    "registry.clear_cache() affects only this throwaway odoo shell process",
    "true_first_gate_ms runs only when PRODUCT_PERFORMANCE_PERMISSION_CARRIER is supplied; without it carrier_source=derived_in_process and the reading is the existing warm first touch",
    "not an SLO, capacity, cross-role or release claim; no freeze, commit, push or deployment",
]

env.cr.rollback()
env.cr.commit = _ORIGINAL_COMMIT
print("PERMISSION_PROBE_REPORT " + json.dumps(REPORT, ensure_ascii=False, sort_keys=True))
