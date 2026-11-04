#!/usr/bin/env python3
"""CAP-02C-04 D1/D2: unified snapshot projection + two-phase + semantic diff.

Repository Mode (``module.capability.index.v1``) and Runtime Mode
(``module.runtime.facts.v1``) are projected into one traceable shape
(``module.snapshot.projection.v1``). Every fact keeps its origin
(``source_mode`` / ``source_module`` / ``source_ref`` / ``completeness``) and a
stable ``fact_identity``.

Three layers are deliberately separated:

  D1 phase 1 - module version / fact digest / file digests (cheap gate);
  D1 phase 2 - fact existence and normalized-content comparison;
  D2         - per-asset semantic explanation of *what* changed.

D3 impact propagation is intentionally out of scope here.

Odoo module contributions are preserved as sets: ``ir.model.modules`` and
``ir.model.fields.modules`` are contribution sets, never a single owner.
``model_owner`` is only ``_original_module`` (the Registry model class). An
asset therefore carries ``asset_modules`` (list) rather than a flattened owner.

Read-only analysis: never changes capability maturity, release state, or
triggers re-certification. Un-attributable or un-parseable change is reported
as ``unresolved_impact`` / ``content_unresolved``, never "no change".
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

PROJECTION_SCHEMA = "module.snapshot.projection.v1"

ASSET_SEMANTIC_FIELDS = {
    "model": ["inherit", "model_owner", "model_extensions", "registry_modules"],
    "field": ["type", "relation", "required", "readonly", "compute", "related"],
    "action": ["res_model", "view_mode", "context", "groups_id"],
    "view": ["model", "inherit_id", "arch_digest"],
    "menu": ["parent_id", "action", "groups_id", "sequence"],
    "security": ["perm_read", "perm_write", "perm_create", "perm_unlink", "group_id"],
    "rule": ["domain", "groups"],
    "intent": ["intent", "handler", "module"],
    "mechanism": ["module", "module_source", "dependency_type"],
    "depends": ["depended"],
}


def _sha256(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _norm(value: Any) -> Any:
    return json.loads(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str))


def _modules(value) -> list[str]:
    return sorted(m for m in (value or []) if m)


def _repo_model_facts(model: dict) -> list[dict]:
    """Project one repository model into model + field facts."""
    model_name = model.get("name")
    if not model_name:
        return []
    module = model.get("_source_module", "")
    facts = [
        {
            "fact_identity": f"model:{model_name}",
            "asset_type": "model",
            "asset_modules": _modules([module]),
            "model_owner": None,
            "model_extensions": [],
            "kind": "model",
            "source_mode": "repository",
            "source_module": module,
            "source_ref": model.get("file", ""),
            "completeness": "static_partial",
            "value": {"name": model_name, "inherit": model.get("inherit", "")},
        }
    ]
    for field in model.get("fields", []) or []:
        field_name = field.get("name")
        if not field_name:
            continue
        facts.append({
            "fact_identity": f"field:{model_name}:{field_name}",
            "asset_type": "field",
            "asset_modules": _modules([module]),
            "model_owner": None,
            "model_extensions": [],
            "kind": "field",
            "source_mode": "repository",
            "source_module": module,
            "source_ref": model.get("file", ""),
            "completeness": "static_partial",
            "value": {
                "name": field_name,
                "type": field.get("type"),
                "relation": field.get("relation", ""),
                "required": field.get("required"),
                "readonly": field.get("readonly"),
                "compute": field.get("compute"),
                "related": field.get("related"),
            },
        })
    return facts


def project_repository(index: dict) -> dict:
    """Project a ``module.capability.index.v1`` document into canonical facts."""
    snapshot = index.get("module_snapshot", {})
    baseline = index.get("module_baseline", {})
    sources = index.get("module_sources", {})
    modules: dict[str, dict] = {}
    for name, snap in snapshot.items():
        base = baseline.get(name, {})
        identity = snap.get("identity", {}) or {}
        facts: list[dict] = []
        for model in snap.get("models", []) or []:
            model = dict(model)
            model["_source_module"] = name
            facts.extend(_repo_model_facts(model))
        for mech in snap.get("mechanism_dependencies", []) or []:
            mechanism = mech.get("mechanism")
            if not mechanism:
                continue
            facts.append({
                "fact_identity": f"mechanism:{mechanism}",
                "asset_type": "mechanism",
                "asset_modules": _modules([name]),
                "model_owner": None,
                "model_extensions": [],
                "kind": "mechanism",
                "source_mode": "repository",
                "source_module": name,
                "source_ref": mech.get("evidence", ""),
                "completeness": "static_partial",
                "value": {
                    "mechanism": mechanism,
                    "module": mech.get("module"),
                    "module_source": mech.get("module_source"),
                    "dependency_type": mech.get("dependency_type"),
                },
            })
        for depended in base.get("depends", []) or []:
            facts.append({
                "fact_identity": f"depends:{depended}",
                "asset_type": "manifest",
                "asset_modules": _modules([name]),
                "model_owner": None,
                "model_extensions": [],
                "kind": "depends",
                "source_mode": "repository",
                "source_module": name,
                "source_ref": "manifest",
                "completeness": "complete",
                "value": {"depended": depended},
            })
        security = snap.get("security", {}) or {}
        if security:
            facts.append({
                "fact_identity": f"security:{name}",
                "asset_type": "security",
                "asset_modules": _modules([name]),
                "model_owner": None,
                "model_extensions": [],
                "kind": "security",
                "source_mode": "repository",
                "source_module": name,
                "source_ref": "security",
                "completeness": "declared_asset_counts",
                "value": dict(security),
            })
        modules[name] = {
            "identity": {
                "technical_name": identity.get("technical_name", name),
                "version": identity.get("version"),
                "source": identity.get("source", sources.get(name, {}).get("source")),
                "category": identity.get("category"),
            },
            "version": identity.get("version"),
            "depends": sorted(base.get("depends", []) or []),
            "fact_digest": snap.get("fact_digest", ""),
            "file_digests": snap.get("file_digests", {}),
            "facts": facts,
        }
    return {"schema": PROJECTION_SCHEMA, "mode": "repository", "modules": modules}


def project_runtime(runtime: dict) -> dict:
    """Project a ``module.runtime.facts.v1`` document into canonical facts."""
    mod_items = (runtime.get("modules") or {}).get("items", {}) or {}
    ownership = (runtime.get("model_ownership") or {}).get("items", []) or []
    owner_by_model = {o.get("model"): o.get("model_owner") or "" for o in ownership}
    ext_by_model = {o.get("model"): o.get("model_extensions") or [] for o in ownership}
    regmod_by_model = {o.get("model"): o.get("registry_modules") or [] for o in ownership}
    modules: dict[str, dict] = {
        name: {
            "identity": {"technical_name": name, "version": item.get("installed_version"), "source": "runtime_registry"},
            "version": item.get("installed_version"),
            "depends": [],
            "fact_digest": "",
            "file_digests": None,
            "facts": [],
        }
        for name, item in mod_items.items()
    }

    def _slot(name: str) -> dict:
        key = name or "__unowned__"
        return modules.setdefault(key, {
            "identity": {"technical_name": key, "version": None, "source": "runtime_registry"},
            "version": None, "depends": [], "fact_digest": "", "file_digests": None, "facts": [],
        })

    def _source_module(asset_modules: list[str], model_owner: str) -> str:
        return asset_modules[0] if asset_modules else (model_owner or "")

    db_ref = f"db:{runtime.get('db_name', '')}"

    for entry in ownership:
        model_name = entry.get("model")
        owner = entry.get("model_owner") or ""
        if not model_name:
            continue
        inherit_values = set((entry.get("inherit_module_facts") or {}).values())
        contributions = set(entry.get("registry_modules") or [])
        unaccounted = sorted(contributions - {owner} - inherit_values)
        fact = {
            "fact_identity": f"model:{model_name}",
            "asset_type": "model",
            "asset_modules": _modules(entry.get("registry_modules")),
            "model_owner": owner,
            "model_extensions": _modules(entry.get("model_extensions")),
            "model_extensions_incomplete": bool(unaccounted),
            "unaccounted_contributions": unaccounted,
            "kind": "model",
            "source_mode": "runtime",
            "source_module": owner or "__unowned__",
            "source_ref": db_ref,
            "completeness": "complete",
            "value": {
                "name": model_name,
                "registry_modules": _modules(entry.get("registry_modules")),
                "model_owner": owner,
                "model_extensions": _modules(entry.get("model_extensions")),
                "inherit_module_facts": dict(entry.get("inherit_module_facts") or {}),
            },
        }
        _slot(owner)["facts"].append(fact)

    for field in (runtime.get("fields") or {}).get("items", []) or []:
        model_name = field.get("model")
        field_name = field.get("name")
        if not model_name or not field_name:
            continue
        asset_modules = _modules(field.get("modules"))
        model_owner = owner_by_model.get(model_name, "")
        fact = {
            "fact_identity": f"field:{model_name}:{field_name}",
            "asset_type": "field",
            "asset_modules": asset_modules,
            "model_owner": model_owner,
            "model_extensions": _modules(ext_by_model.get(model_name)),
            "kind": "field",
            "source_mode": "runtime",
            "source_module": _source_module(asset_modules, model_owner),
            "source_ref": db_ref,
            "completeness": "complete",
            "value": {
                "name": field_name,
                "type": field.get("ttype"),
                "relation": field.get("relation"),
                "required": field.get("required"),
                "readonly": field.get("readonly"),
                "compute": field.get("compute"),
                "related": field.get("related"),
            },
        }
        _slot(_source_module(asset_modules, model_owner))["facts"].append(fact)

    for action in (runtime.get("actions") or {}).get("items", []) or []:
        res_model = action.get("res_model")
        if not res_model:
            continue
        action_module = action.get("module") or ""
        model_owner = owner_by_model.get(res_model, "")
        asset_modules = _modules([action_module])
        fact = {
            "fact_identity": f"action:{res_model}:{action.get('name', '')}",
            "asset_type": "action",
            "asset_modules": asset_modules,
            "model_owner": model_owner,
            "model_extensions": _modules(ext_by_model.get(res_model)),
            "kind": "action",
            "source_mode": "runtime",
            "source_module": _source_module(asset_modules, model_owner),
            "source_ref": db_ref,
            "completeness": "complete",
            "value": {"name": action.get("name"), "res_model": res_model, "view_mode": action.get("view_mode"),
                      "context": action.get("context"), "groups_id": action.get("groups_id")},
        }
        _slot(_source_module(asset_modules, model_owner))["facts"].append(fact)

    for view in (runtime.get("views") or {}).get("items", []) or []:
        view_model = view.get("model")
        if not view_model:
            continue
        view_module = view.get("module") or ""
        model_owner = owner_by_model.get(view_model, "")
        asset_modules = _modules([view_module])
        fact = {
            "fact_identity": f"view:{view_model}:{view.get('name', '')}",
            "asset_type": "view",
            "asset_modules": asset_modules,
            "model_owner": model_owner,
            "model_extensions": _modules(ext_by_model.get(view_model)),
            "kind": "view",
            "source_mode": "runtime",
            "source_module": _source_module(asset_modules, model_owner),
            "source_ref": db_ref,
            "completeness": "complete",
            "value": {"name": view.get("name"), "model": view_model, "inherit_id": view.get("inherit_id"),
                      "arch_digest": view.get("arch_digest")},
        }
        _slot(_source_module(asset_modules, model_owner))["facts"].append(fact)

    for menu in (runtime.get("menus") or {}).get("items", []) or []:
        if not menu.get("name"):
            continue
        menu_module = menu.get("module") or ""
        fact = {
            "fact_identity": f"menu:{menu.get('name', '')}:{menu.get('parent_id')}",
            "asset_type": "menu",
            "asset_modules": _modules([menu_module]),
            "model_owner": "",
            "model_extensions": [],
            "kind": "menu",
            "source_mode": "runtime",
            "source_module": menu_module or "__unowned__",
            "source_ref": db_ref,
            "completeness": "complete",
            "value": {"name": menu.get("name"), "parent_id": menu.get("parent_id"),
                      "action": menu.get("action"), "groups_id": menu.get("groups_id"),
                      "sequence": menu.get("sequence")},
        }
        _slot(menu_module)["facts"].append(fact)

    for acl in (runtime.get("security") or {}).get("acl", []) or []:
        acl_model = acl.get("model")
        if not acl_model:
            continue
        acl_module = acl.get("module") or ""
        model_owner = owner_by_model.get(acl_model, "")
        asset_modules = _modules([acl_module])
        fact = {
            "fact_identity": f"acl:{acl_model}:{acl.get('perm_read')},{acl.get('perm_write')},{acl.get('perm_create')},{acl.get('perm_unlink')}",
            "asset_type": "security",
            "asset_modules": asset_modules,
            "model_owner": model_owner,
            "model_extensions": _modules(ext_by_model.get(acl_model)),
            "kind": "security",
            "source_mode": "runtime",
            "source_module": _source_module(asset_modules, model_owner),
            "source_ref": db_ref,
            "completeness": "declared_acl_not_final_effective_authorization",
            "value": {k: acl.get(k) for k in ("model", "perm_read", "perm_write", "perm_create", "perm_unlink", "group_id")},
        }
        _slot(_source_module(asset_modules, model_owner))["facts"].append(fact)

    for rule in (runtime.get("security") or {}).get("record_rules", []) or []:
        rule_model = rule.get("model")
        rule_name = rule.get("name") or rule_model
        if not rule_model:
            continue
        rule_module = rule.get("module") or ""
        model_owner = owner_by_model.get(rule_model, "")
        fact = {
            "fact_identity": f"rule:{rule_model}:{rule_name}",
            "asset_type": "rule",
            "asset_modules": _modules([rule_module]),
            "model_owner": model_owner,
            "model_extensions": _modules(ext_by_model.get(rule_model)),
            "kind": "rule",
            "source_mode": "runtime",
            "source_module": rule_module or model_owner,
            "source_ref": db_ref,
            "completeness": "complete",
            "value": {"model": rule_model, "name": rule_name,
                      "domain": rule.get("domain"), "groups": rule.get("groups")},
        }
        _slot(rule_module or model_owner)["facts"].append(fact)

    for handler in (runtime.get("intent_handlers") or {}).get("items", []) or []:
        intent = handler.get("intent")
        if not intent:
            continue
        h_module = handler.get("module") or ""
        registered = bool(handler.get("registered"))
        fact = {
            "fact_identity": f"intent:{intent}",
            "asset_type": "intent",
            "asset_modules": _modules([h_module]),
            "model_owner": "",
            "model_extensions": [],
            "handler_missing": not registered,
            "kind": "intent",
            "source_mode": "runtime",
            "source_module": h_module or "__unowned__",
            "source_ref": db_ref,
            "completeness": "complete" if registered else "handler_missing",
            "value": {"intent": intent, "handler": handler.get("handler"),
                      "module": h_module, "registered": registered,
                      "version": handler.get("version")},
        }
        _slot(h_module)["facts"].append(fact)

    for name, module in modules.items():
        module["facts"].sort(key=lambda f: f["fact_identity"])
        module["fact_digest"] = _sha256([(f["fact_identity"], f["value"]) for f in module["facts"]])
    return {"schema": PROJECTION_SCHEMA, "mode": "runtime", "modules": modules}


def phase1(before_module: dict | None, after_module: dict | None) -> dict:
    """Cheap gate: version / fact digest / file digests per module."""
    if before_module is None:
        return {"module": after_module.get("identity", {}).get("technical_name"), "change": "added",
                "version_changed": True, "fact_digest_changed": True,
                "file_digests_changed": None, "phase1_changed": True}
    if after_module is None:
        return {"module": before_module.get("identity", {}).get("technical_name"), "change": "removed",
                "version_changed": True, "fact_digest_changed": True,
                "file_digests_changed": None, "phase1_changed": True}
    before_files = before_module.get("file_digests")
    after_files = after_module.get("file_digests")
    file_changed: bool | None
    if before_files is None or after_files is None:
        file_changed = None  # unknown, not "no change"
    else:
        file_changed = before_files != after_files
    result = {
        "module": before_module.get("identity", {}).get("technical_name"),
        "change": "present",
        "version_changed": before_module.get("version") != after_module.get("version"),
        "fact_digest_changed": before_module.get("fact_digest") != after_module.get("fact_digest"),
        "file_digests_changed": file_changed,
    }
    result["phase1_changed"] = bool(result["version_changed"] or result["fact_digest_changed"] or file_changed)
    return result


def phase2(before_facts: list[dict], after_facts: list[dict]) -> dict:
    """Structured per-fact diff by stable fact_identity."""
    before_map: dict[str, dict] = {}
    after_map: dict[str, dict] = {}
    unresolved: list[dict] = []
    for fact in before_facts:
        ident = fact.get("fact_identity")
        if not ident:
            unresolved.append({"side": "before", "reason": "missing_fact_identity", "fact": fact})
        else:
            before_map[ident] = fact
    for fact in after_facts:
        ident = fact.get("fact_identity")
        if not ident:
            unresolved.append({"side": "after", "reason": "missing_fact_identity", "fact": fact})
        else:
            after_map[ident] = fact
    changes: list[dict] = []
    for ident in sorted(set(before_map) | set(after_map)):
        before = before_map.get(ident)
        after = after_map.get(ident)
        if before is None:
            changes.append({"fact_identity": ident, "change": "added", "after": after})
        elif after is None:
            changes.append({"fact_identity": ident, "change": "removed", "before": before})
        elif _norm(before.get("value")) != _norm(after.get("value")):
            changes.append({"fact_identity": ident, "change": "changed", "before": before, "after": after})
    return {"changes": changes, "unresolved": unresolved,
            "has_unresolved_impact": bool(unresolved)}


def semantic_diff(before_fact: dict, after_fact: dict) -> dict:
    """D2: explain what changed between two same-identity facts."""
    asset_type = before_fact.get("asset_type") or after_fact.get("asset_type")
    b_value = before_fact.get("value") or {}
    a_value = after_fact.get("value") or {}
    detail: list[dict] = []

    for attribute in ASSET_SEMANTIC_FIELDS.get(asset_type, []):
        bv = b_value.get(attribute)
        av = a_value.get(attribute)
        if _norm(bv) != _norm(av):
            detail.append({"attribute": attribute, "before": bv, "after": av})

    for top in ("asset_modules", "model_extensions", "registry_modules"):
        bv = _norm(before_fact.get(top))
        av = _norm(after_fact.get(top))
        if bv != av:
            detail.append({"attribute": top, "before": bv, "after": av})

    if not b_value and not a_value and not before_fact.get("asset_modules") and not after_fact.get("asset_modules"):
        return {"change": "changed", "detail": detail, "content_unresolved": True,
                "reason": "no comparable semantic content"}
    if asset_type not in ASSET_SEMANTIC_FIELDS:
        return {"change": "changed", "detail": detail, "content_unresolved": True,
                "reason": f"no semantic schema for asset_type={asset_type}"}
    return {"change": "changed" if detail else "unchanged_semantically",
            "detail": detail, "content_unresolved": False}


def diff_semantics(phase2_result: dict) -> dict:
    """Annotate D1 phase-2 changed facts with D2 semantic explanations."""
    annotated: list[dict] = []
    content_unresolved: list[dict] = []
    for change in phase2_result.get("changes", []):
        if change.get("change") != "changed":
            annotated.append(change)
            continue
        semantics = semantic_diff(change.get("before", {}), change.get("after", {}))
        entry = {**change, "semantics": semantics}
        if semantics.get("content_unresolved"):
            content_unresolved.append(entry)
        annotated.append(entry)
    return {
        "changes": annotated,
        "unresolved": phase2_result.get("unresolved", []),
        "content_unresolved": content_unresolved,
        "has_unresolved_impact": bool(phase2_result.get("unresolved")) or bool(content_unresolved),
    }


def diff_projections(before: dict, after: dict) -> dict:
    """Orchestrate phase-1 gate and phase-2 fact diff across modules."""
    before_modules = before.get("modules", {})
    after_modules = after.get("modules", {})
    gates = [phase1(before_modules.get(name), after_modules.get(name))
             for name in sorted(set(before_modules) | set(after_modules))]
    structured = {}
    for name in sorted(set(before_modules) | set(after_modules)):
        b = before_modules.get(name, {})
        a = after_modules.get(name, {})
        structured[name] = diff_semantics(phase2(b.get("facts", []), a.get("facts", [])))
    unresolved_modules = [name for name, d in structured.items() if d["has_unresolved_impact"]]
    return {
        "schema": PROJECTION_SCHEMA,
        "before_mode": before.get("mode"),
        "after_mode": after.get("mode"),
        "phase1": gates,
        "phase1_changed_modules": [g["module"] for g in gates if g.get("phase1_changed")],
        "phase2": structured,
        "unresolved_modules": unresolved_modules,
    }
