#!/usr/bin/env python3
"""Read-only Odoo Runtime facts snapshot. Runs inside an Odoo shell process.

Consumes the final Odoo Registry (ir.* models), never source scanning, never
writes business data, and never fabricates an install state. Each fact group
records its source, completeness and the database name.
"""
from __future__ import annotations

import hashlib
import json
import time

import odoo


def _snapshot(env, db_name):
    registry = odoo.registry(env.cr.dbname)
    model_names = {m["id"]: m["model"] for m in env["ir.model"].search_read([], ["id", "model"])}
    model_modules = {
        m["id"]: [x.strip() for x in (m["modules"] or "").split(",") if x.strip()]
        for m in env["ir.model"].search_read([], ["id", "modules"])
    }
    model_owner_map = {}
    model_inherit_map = {}
    for mid, model_name in model_names.items():
        klass = registry.get(model_name)
        model_owner_map[model_name] = getattr(klass, "_original_module", None) if klass else None
        model_inherit_map[model_name] = dict(getattr(klass, "_inherit_module", {}) or {}) if klass else {}
    result = {
        "schema": "module.runtime.facts.v1",
        "db_name": db_name,
        "captured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "registry": {
            "ready": getattr(registry, "ready", False),
            "loaded": getattr(registry, "loaded", False),
            "db_matches": env.cr.dbname == db_name,
        },
    }

    modules = env["ir.module.module"].search_read(
        [], ["name", "state", "latest_version", "installed_version"]
    )
    result["modules"] = {
        m["name"]: {
            "state": m["state"],
            "installed_version": m["installed_version"],
            "latest_version": m["latest_version"],
        }
        for m in modules
    }
    result["modules"] = {"source": "runtime_registry", "completeness": "complete", "items": result["modules"]}

    # ir.model.modules is the raw module contribution set; _original_module is
    # the authoritative model owner. Extensions are the contribution set minus
    # the owner, never derived from a model name prefix.
    result["model_ownership"] = {
        "source": "runtime_registry",
        "completeness": "complete",
        "items": [
            {
                "model": model_names[mid],
                "registry_modules": sorted(m for m in mods if m),
                "model_owner": model_owner_map.get(model_names[mid]),
                "model_extensions": sorted(
                    set((model_inherit_map.get(model_names[mid], {}) or {}).values())
                    - {model_owner_map.get(model_names[mid])}
                ),
                "inherit_module_facts": model_inherit_map.get(model_names[mid], {}),
            }
            for mid, mods in model_modules.items()
            if model_names.get(mid)
        ],
    }

    def _xmlid_map(model_name):
        mapping = {}
        for rec in env["ir.model.data"].search_read(
                [("model", "=", model_name)], ["module", "name", "res_id"]):
            res_id = rec["res_id"]
            if isinstance(res_id, str):
                res_id = int(res_id) if res_id.isdigit() else None
            if res_id is None:
                continue
            module = rec.get("module") or ""
            name = rec.get("name") or ""
            xmlid = f"{module}.{name}" if module and name else (module or "")
            mapping.setdefault(res_id, []).append(xmlid)
        return {rid: sorted(set(xids)) for rid, xids in mapping.items()}

    def _identity(xids):
        xids = sorted(xids or [])
        primary = xids[0] if xids else ""
        primary_module = primary.split(".")[0] if "." in primary else ""
        return primary, primary_module, xids

    fields = env["ir.model.fields"].search_read(
        [], ["model_id", "name", "ttype", "relation", "required", "readonly",
             "compute", "related", "state", "modules"]
    )
    field_items = [
        {
            "model": model_names.get(f["model_id"][0]) if isinstance(f["model_id"], (list, tuple)) else model_names.get(f["model_id"]),
            "name": f["name"],
            "ttype": f["ttype"],
            "relation": f["relation"],
            "required": f["required"],
            "readonly": f["readonly"],
            "compute": bool(f["compute"]),
            "related": bool(f["related"]),
            "modules": sorted(x.strip() for x in (f.get("modules") or "").split(",") if x.strip()),
        }
        for f in fields
    ]
    result["fields"] = {"source": "runtime_registry", "completeness": "complete", "items": field_items}

    action_xid = _xmlid_map("ir.actions.act_window")
    actions = env["ir.actions.act_window"].search_read(
        [], ["name", "res_model", "view_mode", "context", "groups_id"])
    result["actions"] = {
        "source": "runtime_registry", "completeness": "complete",
        "items": [
            (lambda primary, module, xids: {
                "name": a["name"], "res_model": a["res_model"], "view_mode": a["view_mode"],
                "context": a["context"], "groups_id": a["groups_id"] or [],
                "xmlid": primary, "xmlids": xids, "module": module,
            })(*_identity(action_xid.get(a["id"])))
            for a in actions
        ],
    }
    result["action_coverage"] = {
        "covered_types": ["ir.actions.act_window"],
        "not_covered_types": ["ir.actions.client", "ir.actions.server", "ir.actions.report"],
        "note": "this round reads act_window only; other action types remain unresolved",
    }

    view_xid = _xmlid_map("ir.ui.view")
    views = env["ir.ui.view"].search_read([], ["name", "model", "inherit_id", "arch_db"])
    result["views"] = {
        "source": "runtime_registry", "completeness": "complete",
        "items": [
            (lambda primary, module, xids: {
                "name": v["name"], "model": v["model"],
                "inherit_id": v["inherit_id"] and v["inherit_id"][0],
                "arch_digest": hashlib.sha256((v["arch_db"] or "").encode("utf-8")).hexdigest(),
                "xmlid": primary, "xmlids": xids, "module": module,
            })(*_identity(view_xid.get(v["id"])))
            for v in views
        ],
    }

    menu_xid = _xmlid_map("ir.ui.menu")
    menus = env["ir.ui.menu"].search_read(
        [], ["name", "parent_id", "action", "groups_id", "sequence"])
    result["menus"] = {
        "source": "runtime_registry", "completeness": "complete",
        "items": [
            (lambda primary, module, xids: {
                "name": m["name"], "parent_id": m["parent_id"] and m["parent_id"][0],
                "action": m["action"], "groups_id": m["groups_id"] or [],
                "sequence": m["sequence"],
                "xmlid": primary, "xmlids": xids, "module": module,
            })(*_identity(menu_xid.get(m["id"])))
            for m in menus
        ],
    }

    access_xid = _xmlid_map("ir.model.access")
    access = env["ir.model.access"].search_read([], ["model_id", "group_id", "perm_read", "perm_write", "perm_create", "perm_unlink"])
    result["security"] = {
        "source": "runtime_registry",
        "completeness": "declared_acl_not_final_effective_authorization",
        "acl": [
            (lambda primary, module, xids: {
                "model": model_names.get(a["model_id"][0]) if isinstance(a["model_id"], (list, tuple)) else model_names.get(a["model_id"]),
                "perm_read": a["perm_read"], "perm_write": a["perm_write"],
                "perm_create": a["perm_create"], "perm_unlink": a["perm_unlink"],
                "xmlid": primary, "xmlids": xids, "module": module,
                "group_id": a["group_id"][0] if a["group_id"] else None,
            })(*_identity(access_xid.get(a["id"])))
            for a in access
        ],
    }

    rule_xid = _xmlid_map("ir.rule")
    rules = env["ir.rule"].search_read([], ["model_id", "domain_force", "name", "groups"])
    groups = env["res.groups"].search_read([], ["full_name"])
    result["security"]["record_rules"] = [
        (lambda primary, module, xids: {
            "model": model_names.get(r["model_id"][0]) if isinstance(r["model_id"], (list, tuple)) else model_names.get(r["model_id"]),
            "name": r["name"], "xmlid": primary, "xmlids": xids, "module": module,
            "domain": r["domain_force"], "groups": r["groups"] or [],
        })(*_identity(rule_xid.get(r["id"])))
        for r in rules
    ]
    result["security"]["record_rules_count"] = len(rules)
    result["security"]["groups_count"] = len(groups)

    result["intent_handlers"] = _intent_handlers()

    return result


def _intent_handlers():
    """Read the actual SCE Handler Registry contribution chain (read-only)."""
    base = {"source": "sce_handler_registry", "completeness": "complete", "items": []}
    try:
        from odoo.addons.smart_construction_core.core_extension_intent_handlers import (
            get_intent_handler_contributions,
        )
        contributions = get_intent_handler_contributions() or []
    except Exception as exc:
        base["completeness"] = "incomplete"
        base["error"] = str(exc)[:200]
        return base
    for entry in contributions:
        intent = entry.get("intent")
        handler_cls = entry.get("handler")
        source_module = entry.get("source_module") or "smart_construction_core"
        if not intent:
            continue
        if handler_cls is None:
            base["items"].append({"intent": intent, "handler": None,
                                  "module": source_module,
                                  "registered": False,
                                  "status": entry.get("status"), "version": None})
            continue
        module = handler_cls.__module__ or ""
        module = module.split(".")[2] if module.startswith("odoo.addons.") else module
        base["items"].append({
            "intent": intent,
            "handler": getattr(handler_cls, "__name__", str(handler_cls)),
            "module": module,
            "registered": True,
            "status": entry.get("status"),
            "version": getattr(handler_cls, "VERSION", None),
        })
    return base


# Executed inside `odoo shell`; the shell exposes a global `env`.
db_name = env.cr.dbname
print(json.dumps(_snapshot(env, db_name), ensure_ascii=False, indent=2))
