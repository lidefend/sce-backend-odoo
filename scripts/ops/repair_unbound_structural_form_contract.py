# -*- coding: utf-8 -*-
"""Retire an unbound structural form config that a bound native surface owns.

A published ``view_orchestration:<model>:form:action:<id>:view:0`` contract is a
low-code edit saved without a resolved view target.  When a view-bound native
semantic surface owns the same (model, action, form) scope, the runtime view
orchestrator must fail closed (``CONFIG_TARGET_BINDING_REQUIRED``) rather than
let a second structural declaration compete with the authoritative native
surface; the whole page then returns 400.  When the edit is stale — every field
it declares already reaches the page from the scope's native arch and field
policy — retiring the config is the truthful repair instead of inventing a
patch body for it.

Deliberately narrow: it only touches the exact contract id named by
``SC_REPAIR_CONTRACT_ID``, and only when that record still matches the unbound
structural low-code form identity for a scope that also carries a view-bound
native semantic surface.  Dry-run by default; ``APPLY=1`` performs the
retirement and prints the authoritative readback.
"""

import json
import os


STRUCTURAL_KEYS = ("layout", "sections", "fields", "field_slots", "columns", "cols")
NATIVE_SURFACE_MODES = {"native_semantic_surface", "semantic_native_surface"}


def _truthy(value):
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def _text(value):
    if value in (None, False):
        return ""
    return str(value)


def _form_spec(rec):
    payload = rec.contract_json if isinstance(rec.contract_json, dict) else {}
    views = (payload.get("view_orchestration") or {}).get("views") or {}
    spec = views.get("form")
    return spec if isinstance(spec, dict) else {}


def _declared_fields(spec):
    names = set()

    def walk(nodes):
        if not isinstance(nodes, list):
            return
        for node in nodes:
            if not isinstance(node, dict):
                continue
            name = _text(node.get("name") or node.get("field") or node.get("field_name"))
            if name:
                names.add(name)
            for child_key in ("children", "tabs", "items", "nodes", "pages"):
                walk(node.get(child_key))

    for key in ("fields", "field_slots"):
        rows = spec.get(key)
        if not isinstance(rows, list):
            continue
        for row in rows:
            if isinstance(row, dict):
                name = _text(row.get("name") or row.get("field") or row.get("field_name"))
                if name:
                    names.add(name)
            else:
                name = _text(row)
                if name:
                    names.add(name)
    walk(spec.get("layout"))
    walk(spec.get("sections"))
    return names


APPLY = _truthy(os.environ.get("APPLY"))
TARGET_ID = int(_text(os.environ.get("SC_REPAIR_CONTRACT_ID")) or 0)

Contract = env["ui.business.config.contract"].sudo()  # noqa: F821

report = {
    "contract_id": TARGET_ID,
    "apply": APPLY,
    "database": _text(env.cr.dbname),  # noqa: F821
}

rec = Contract.browse(TARGET_ID)
if TARGET_ID <= 0 or not rec.exists():
    report["error"] = "target contract not found"
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    raise SystemExit(2)

spec = _form_spec(rec)
declared_keys = [key for key in STRUCTURAL_KEYS if spec.get(key) not in (None, [], {}, "")]
name = _text(rec.name)
report.update({
    "name": name,
    "model": _text(rec.model),
    "view_type": _text(rec.view_type),
    "action_id": int(rec.action_id.id or 0),
    "view_id": int(rec.view_id.id or 0),
    "status": _text(rec.status),
    "active": bool(rec.active),
    "declared_structural_keys": declared_keys,
    "declared_fields": sorted(_declared_fields(spec)),
})

if not rec.active or _text(rec.status) != "published":
    report["error"] = "target contract is not an active published config"
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    raise SystemExit(3)

if int(rec.view_id.id or 0):
    report["error"] = "target contract is view-bound; this repair only retires unbound configs"
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    raise SystemExit(3)

if _text(rec.view_type) != "form" or not declared_keys:
    report["error"] = "target contract declares no structural form declaration"
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    raise SystemExit(3)

if not name.startswith("view_orchestration:") or not name.endswith(":view:0"):
    report["error"] = "target contract is not an unbound low-code form config"
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    raise SystemExit(3)

scope_configs = Contract.search([
    ("active", "=", True),
    ("status", "=", "published"),
    ("model", "=", rec.model),
    ("view_type", "=", "form"),
    ("action_id", "=", rec.action_id.id),
])
native_surfaces = []
for other in scope_configs:
    if other.id == rec.id:
        continue
    other_spec = _form_spec(other)
    mode = _text(other_spec.get("composition_mode") or other_spec.get("compositionMode"))
    if mode in NATIVE_SURFACE_MODES and int(other.view_id.id or 0):
        native_surfaces.append({
            "contract_id": other.id,
            "name": other.name,
            "view_id": int(other.view_id.id or 0),
            "priority": int(other.priority or 0),
        })

report["bound_native_surfaces"] = native_surfaces
if not native_surfaces:
    report["error"] = "no view-bound native semantic surface owns this scope; refusing to retire"
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    raise SystemExit(4)

if not APPLY:
    report["action"] = "dry_run"
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    raise SystemExit(0)

rec.write({"active": False})
env.cr.commit()  # noqa: F821

readback = Contract.browse(TARGET_ID)
report["action"] = "retired"
report["readback"] = {
    "active": bool(readback.active),
    "status": _text(readback.status),
    "write_date": _text(readback.write_date),
}
print(json.dumps(report, ensure_ascii=False, sort_keys=True))
