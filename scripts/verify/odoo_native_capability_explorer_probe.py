#!/usr/bin/env python3
"""Read-only proof for Odoo-native business entry discovery.

The probe joins facts owned by Odoo with the existing product-scenario model.
It never creates a capability registry or persists a discovered row.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict


BUSINESS_ROOT_XMLID = "smart_construction_core.menu_sc_root"
SUPPORTED_ACTION_TYPES = {
    "ir.actions.act_window",
    "ir.actions.client",
    "ir.actions.server",
    "ir.actions.report",
    "ir.actions.act_url",
}
INSTALLED_MODULE_STATES = {"installed", "to upgrade", "to remove"}


def entry_selection_assessment(
    *,
    menu_xmlid,
    action_xmlid,
    action_type,
    res_model,
    module_state,
    action_exists,
    menu_action_matches,
    model_exists,
):
    """Assess technical selection only; never infer product qualification."""
    blockers = []
    if not str(menu_xmlid or "").strip():
        blockers.append("MENU_XMLID_MISSING")
    if not str(action_xmlid or "").strip():
        blockers.append("ACTION_XMLID_MISSING")
    if module_state not in INSTALLED_MODULE_STATES:
        blockers.append("MODULE_NOT_INSTALLED")
    if not action_exists:
        blockers.append("ACTION_NOT_FOUND")
    if action_type not in SUPPORTED_ACTION_TYPES:
        blockers.append("ACTION_TYPE_UNSUPPORTED")
    if not menu_action_matches:
        blockers.append("MENU_ACTION_MISMATCH")
    if action_type == "ir.actions.act_window":
        if not str(res_model or "").strip():
            blockers.append("WINDOW_ACTION_MODEL_MISSING")
        elif not model_exists:
            blockers.append("MODEL_NOT_FOUND")
    return {
        "draft_selectable": not blockers,
        "selection_blockers": blockers,
        "requires_scene_qualification": True,
    }


def _xmlids(env, recordset):
    result = defaultdict(list)
    if not recordset:
        return result
    rows = env["ir.model.data"].sudo().search([
        ("model", "=", recordset._name),
        ("res_id", "in", recordset.ids),
    ])
    for row in rows:
        result[row.res_id].append("%s.%s" % (row.module, row.name))
    return {key: sorted(value) for key, value in result.items()}


def probe(env):
    from odoo.addons.smart_core.delivery.runtime_capability_catalog import (
        RuntimeCapabilityCatalogService,
    )
    from odoo.addons.smart_construction_core.services.product_menu_source import (
        load_published_menu_release_states,
    )

    native = RuntimeCapabilityCatalogService(env).collect(
        root_label="智慧施工管理平台",
        leaf_actions_only=True,
    )
    rows = native.rows
    menu_ids = [int(row["menu_id"]) for row in rows]
    action_ids = [int(row["action_id"]) for row in rows]
    model_names = sorted({str(row.get("res_model") or "").strip() for row in rows if row.get("res_model")})
    owner_modules = sorted({str(row.get("owner_module") or "").strip() for row in rows if row.get("owner_module")})

    menus = env["ir.ui.menu"].sudo().browse(menu_ids).exists()
    menu_by_id = {menu.id: menu for menu in menus}
    actions = env["ir.actions.actions"].sudo().browse(action_ids).exists()
    action_by_id = {action.id: action for action in actions}
    installed_modules = env["ir.module.module"].sudo().search([
        ("state", "in", sorted(INSTALLED_MODULE_STATES)),
    ])
    modules = env["ir.module.module"].sudo().search([("name", "in", owner_modules)])
    module_by_name = {module.name: module for module in modules}
    models = env["ir.model"].sudo().search([("model", "in", model_names)])
    model_by_name = {model.model: model for model in models}
    model_ids = models.ids

    field_counts = Counter()
    if model_ids:
        fields = env["ir.model.fields"].sudo().search([("model_id", "in", model_ids)])
        field_counts.update(field.model for field in fields)

    view_counts = Counter()
    if model_names:
        views = env["ir.ui.view"].sudo().search([("model", "in", model_names)])
        view_counts.update(view.model for view in views)

    access_rows = defaultdict(list)
    if model_ids:
        for access in env["ir.model.access"].sudo().search([("model_id", "in", model_ids)]):
            access_rows[access.model_id.model].append(access)

    rule_counts = Counter()
    if model_ids:
        rules = env["ir.rule"].sudo().search([("model_id", "in", model_ids)])
        rule_counts.update(rule.model_id.model for rule in rules)

    groups = env["res.groups"].sudo().browse(sorted({
        access.group_id.id
        for access_list in access_rows.values()
        for access in access_list
        if access.group_id
    }))
    group_xmlids = _xmlids(env, groups)
    scenario_bindings = defaultdict(list)
    scenario_entries = env["sc.product.scenario.entry"].sudo().search([
        ("menu_id", "in", menu_ids),
    ])
    for entry in scenario_entries:
        scenario_bindings[entry.menu_id.id].append({
            "scenario_key": entry.scenario_id.code,
            "scenario_name": entry.scenario_id.name,
            "intent": entry.intent,
            "center_key": entry.center_key,
            "center_name": entry.center_name,
        })

    try:
        release_states = load_published_menu_release_states(env)
    except Exception:
        release_states = {}

    discovered = []
    for row in rows:
        menu = menu_by_id.get(int(row["menu_id"]))
        action = action_by_id.get(int(row["action_id"]))
        module_name = str(row.get("owner_module") or "").strip()
        module = module_by_name.get(module_name)
        model_name = str(row.get("res_model") or "").strip()
        model = model_by_name.get(model_name)
        bindings = scenario_bindings.get(int(row["menu_id"])) or []
        release_state = str(release_states.get(str(row.get("menu_xmlid") or ""), "")).strip()
        assessment = entry_selection_assessment(
            menu_xmlid=row.get("menu_xmlid"),
            action_xmlid=row.get("action_xmlid"),
            action_type=row.get("action_model"),
            res_model=model_name,
            module_state=module.state if module else "",
            action_exists=bool(action),
            menu_action_matches=bool(menu and action and menu.action and menu.action.id == action.id),
            model_exists=bool(model),
        )
        access_list = access_rows.get(model_name) or []
        discovered.append({
            "menu_id": int(row["menu_id"]),
            "menu_xmlid": str(row.get("menu_xmlid") or ""),
            "menu_name": str(row.get("menu_name") or ""),
            "menu_path": row.get("menu_path") or [],
            "action_id": int(row["action_id"]),
            "action_xmlid": str(row.get("action_xmlid") or ""),
            "action_type": str(row.get("action_model") or ""),
            "res_model": model_name,
            "view_modes": row.get("view_modes") or [],
            "owner_module": module_name,
            "module_state": module.state if module else "",
            "module_version": module.latest_version if module else "",
            "module_dependencies": sorted(module.dependencies_id.mapped("name")) if module else [],
            "model_exists": bool(model),
            "model_description": model.name if model else "",
            "field_count": int(field_counts.get(model_name, 0)),
            "view_count": int(view_counts.get(model_name, 0)),
            "acl_row_count": len(access_list),
            "acl_group_xmlids": sorted({
                xmlid
                for access in access_list
                for xmlid in group_xmlids.get(access.group_id.id, [])
            }),
            "record_rule_count": int(rule_counts.get(model_name, 0)),
            "release_state": release_state,
            "scene_bindings": bindings,
            "scene_status": "bound" if bindings else "unbound",
            **assessment,
        })

    selection_blockers = Counter(
        blocker
        for row in discovered
        for blocker in row["selection_blockers"]
    )
    scene_status = Counter(row["scene_status"] for row in discovered)
    release_scene_status = Counter(
        (row["release_state"] or "unknown", row["scene_status"])
        for row in discovered
    )
    return {
        "schema": "odoo.native_capability_explorer.probe.v1",
        "database": env.cr.dbname,
        "source": "odoo_native_metadata_plus_existing_scene_services",
        "new_capability_registry": False,
        "persisted_rows": 0,
        "native_entry_count": len(discovered),
        "summary": {
            "draft_selectable": sum(1 for row in discovered if row["draft_selectable"]),
            "selection_blocked": sum(1 for row in discovered if not row["draft_selectable"]),
            "selection_blocker_counts": dict(selection_blockers),
            "installed_module_count": len(installed_modules),
            "contributing_module_count": len(modules),
            "model_count": len(models),
            "all_model_count": env["ir.model"].sudo().search_count([]),
            "action_count": len(actions),
            "view_count": sum(view_counts.values()),
            "acl_row_count": sum(len(rows) for rows in access_rows.values()),
            "record_rule_count": sum(rule_counts.values()),
            "scene_bound": scene_status.get("bound", 0),
            "scene_unbound": scene_status.get("unbound", 0),
            "release_scene_status_counts": {
                "%s:%s" % key: value for key, value in release_scene_status.items()
            },
        },
        "native_diagnostics": native.diagnostics,
        "entries": discovered,
        "limitations": [
            "draft_selectable is native technical eligibility, not Preview or Standard product qualification",
            "ACL counts are model-level rows; record rules and operation gates remain runtime authorization inputs",
            "the probe proves discovery and association, not management-page usability",
        ],
    }


if __name__ == "__main__" and "env" in globals():
    print(json.dumps(probe(env), ensure_ascii=False, indent=2, sort_keys=True, default=str))
