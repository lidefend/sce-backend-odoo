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
    for mid, model_name in model_names.items():
        klass = registry.get(model_name)
        model_owner_map[model_name] = getattr(klass, "_original_module", None) if klass else None
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
                    m for m in (mods if mods else [])
                    if m and m != model_owner_map.get(model_names[mid])
                ),
            }
            for mid, mods in model_modules.items()
            if model_names.get(mid)
        ],
    }

    fields = env["ir.model.fields"].search_read(
        [], ["model_id", "name", "ttype", "relation", "required", "readonly", "compute", "related", "state"]
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
        }
        for f in fields
    ]
    result["fields"] = {"source": "runtime_registry", "completeness": "complete", "items": field_items}

    actions = env["ir.actions.act_window"].search_read([], ["name", "res_model", "view_mode"])
    result["actions"] = {
        "source": "runtime_registry", "completeness": "complete",
        "items": [{"name": a["name"], "res_model": a["res_model"], "view_mode": a["view_mode"]} for a in actions],
    }

    views = env["ir.ui.view"].search_read([], ["name", "model", "inherit_id"])
    result["views"] = {
        "source": "runtime_registry", "completeness": "complete",
        "items": [{"name": v["name"], "model": v["model"], "inherit_id": v["inherit_id"] and v["inherit_id"][0]} for v in views],
    }

    menus = env["ir.ui.menu"].search_read([], ["name", "parent_id"])
    result["menus"] = {
        "source": "runtime_registry", "completeness": "complete",
        "items": [{"name": m["name"], "parent_id": m["parent_id"] and m["parent_id"][0]} for m in menus],
    }

    access = env["ir.model.access"].search_read([], ["model_id", "group_id", "perm_read", "perm_write", "perm_create", "perm_unlink"])
    result["security"] = {
        "source": "runtime_registry",
        "completeness": "declared_acl_not_final_effective_authorization",
        "acl": [{"model": model_names.get(a["model_id"][0]) if isinstance(a["model_id"], (list, tuple)) else model_names.get(a["model_id"]), "perm_read": a["perm_read"], "perm_write": a["perm_write"], "perm_create": a["perm_create"], "perm_unlink": a["perm_unlink"]} for a in access],
    }

    rules = env["ir.rule"].search_read([], ["model_id", "domain_force"])
    groups = env["res.groups"].search_read([], ["full_name"])
    result["security"]["record_rules_count"] = len(rules)
    result["security"]["groups_count"] = len(groups)

    return result


# Executed inside `odoo shell`; the shell exposes a global `env`.
db_name = env.cr.dbname
print(json.dumps(_snapshot(env, db_name), ensure_ascii=False, indent=2))
