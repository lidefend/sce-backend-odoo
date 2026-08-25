#!/usr/bin/env python3
"""Audit the formal project-center frontend rollout from runtime authority."""

from __future__ import annotations

import json
import os
from pathlib import Path
from xml.etree import ElementTree


DOMAIN_KEY = "project"
ROOT_MENU_XMLID = "smart_construction_core.menu_sc_project_center"
OWNER_MODULE = "smart_construction_core"
OUTPUT_PATH = Path(
    os.getenv(
        "FRONTEND_PROJECT_DOMAIN_ROLLOUT_PATH",
        "/tmp/frontend_project_domain_rollout_v1.json",
    )
)
EXPECTED_ANCHORS = {
    "smart_construction_core.action_project_initiation",
    "smart_construction_core.action_sc_product_project_edit_v1",
    "smart_construction_core.action_exec_structure_wbs",
    "smart_construction_core.action_project_progress_entry",
    "smart_construction_core.action_sc_project_document",
}
SPECIAL_JS_CLASS = {
    "smart_hierarchy_browser": "hierarchy_browser",
    "smart_hierarchy_planner": "hierarchy_planner",
    "smart_hierarchical_worksheet": "hierarchical_worksheet",
}
READY_SEMANTICS = {
    "table",
    "card",
    "workflow_board",
    "hierarchy_browser",
    "hierarchy_planner",
    "hierarchical_worksheet",
    "activity",
}
FALLBACK_SEMANTICS = {"pivot", "graph", "calendar", "gantt", "dashboard"}


def _text(value) -> str:
    if isinstance(value, dict):
        for key in ("zh_CN", "en_US"):
            if value.get(key):
                return str(value[key]).strip()
        return str(next(iter(value.values()), "")).strip()
    return str(value or "").strip()


def classify_surface(view_type: str, js_class: str, assembly_semantic: str = "") -> dict[str, str]:
    mode = _text(view_type).lower()
    marker = _text(js_class)
    semantic = _text(assembly_semantic).lower()
    if not semantic and marker in SPECIAL_JS_CLASS:
        semantic = SPECIAL_JS_CLASS[marker]
    if not semantic:
        semantic = {
            "tree": "table",
            "list": "table",
            "kanban": "card",
            "activity": "activity",
            "pivot": "pivot",
            "graph": "graph",
            "calendar": "calendar",
            "gantt": "gantt",
            "dashboard": "dashboard",
        }.get(mode, "")
    if mode == "form":
        return {"semantic": "form_structure", "readiness": "structural", "reason": ""}
    if marker.startswith("smart_") and marker not in SPECIAL_JS_CLASS:
        return {
            "semantic": semantic or "unknown",
            "readiness": "fail_closed",
            "reason": "UNREGISTERED_SMART_VIEW_CLASS",
        }
    if semantic in READY_SEMANTICS:
        return {"semantic": semantic, "readiness": "ready", "reason": ""}
    if semantic in FALLBACK_SEMANTICS:
        return {
            "semantic": semantic,
            "readiness": "readable_fallback",
            "reason": f"RENDERER_{semantic.upper()}_PLANNED",
        }
    return {
        "semantic": semantic or "unknown",
        "readiness": "fail_closed",
        "reason": "ACTION_SURFACE_RENDERER_NOT_REGISTERED",
    }


def _xmlid(record) -> str:
    if not record:
        return ""
    return record.get_external_id().get(record.id, "") or ""


def _active_descendant_ids(env, root_id: int) -> list[int]:
    pending = [root_id]
    result: list[int] = []
    while pending:
        env.cr.execute(
            "SELECT id FROM ir_ui_menu "
            "WHERE active IS TRUE AND parent_id = ANY(%s) ORDER BY sequence, id",
            (pending,),
        )
        pending = [int(row[0]) for row in env.cr.fetchall()]
        result.extend(pending)
    return result


def _effective_group_xmlids(menu, action) -> list[str]:
    groups = action.groups_id
    current = menu
    while current:
        groups |= current.groups_id
        current = current.parent_id
    return sorted(filter(None, (_xmlid(group) for group in groups)))


def _resolved_views(env, action, assembly_semantics: dict[str, str]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    declared = list(action.view_ids.sorted(lambda row: (row.sequence, row.id)))
    modes = [item.strip().lower() for item in _text(action.view_mode).split(",") if item.strip()]
    for mode in modes:
        binding = next(
            (item for item in declared if item.view_mode == mode and item.view_id),
            None,
        )
        view = (
            binding.view_id
            if binding
            else action.view_id
            if action.view_id and action.view_id.type == mode
            else env["ir.ui.view"]
        )
        try:
            payload = env[action.res_model].sudo().get_view(
                view_id=view.id or None,
                view_type=mode,
            )
            root = ElementTree.fromstring(_text(payload.get("arch") or "<root/>"))
            resolved_id = int(payload.get("id") or view.id or 0)
            classification = classify_surface(
                mode,
                _text(root.get("js_class")),
                assembly_semantics.get(mode, ""),
            )
            rows.append(
                {
                    "view_type": mode,
                    "view_xmlid": _xmlid(env["ir.ui.view"].sudo().browse(resolved_id)),
                    "root_tag": root.tag,
                    "js_class": _text(root.get("js_class")),
                    **classification,
                }
            )
        except Exception as exc:  # pragma: no cover - exercised by governed runtime
            rows.append(
                {
                    "view_type": mode,
                    "view_xmlid": "",
                    "root_tag": "",
                    "js_class": "",
                    "semantic": "unknown",
                    "readiness": "fail_closed",
                    "reason": f"VIEW_RESOLUTION_FAILED:{type(exc).__name__}:{exc}",
                }
            )
    return rows


def _assembly_semantics(env, action) -> dict[str, str]:
    from odoo.addons.smart_core.app_config_engine.services.assemblers.page_assembler import (  # noqa: PLC0415
        PageAssembler,
    )
    from odoo.tools.safe_eval import safe_eval  # noqa: PLC0415

    payload = action.read()[0]
    context = safe_eval(
        payload.get("context") or "{}",
        {"uid": env.uid, "context": {}},
    )
    modes = [item.strip().lower() for item in _text(action.view_mode).split(",") if item.strip()]
    page, _versions = PageAssembler(
        env,
        env["ir.model"].sudo().env,
    ).assemble_page_contract(
        {
            "model": action.res_model,
            "view_types": modes,
            "action_id": action.id,
            "context": context,
        },
        action=payload,
    )
    views = page.get("views") or {}
    return {
        mode: _text((views.get(mode) or {}).get("collection_presentation", {}).get("semantic"))
        for mode in modes
        if (views.get(mode) or {}).get("collection_presentation")
    }


def collect(env) -> dict[str, object]:
    root = env.ref(ROOT_MENU_XMLID)
    Menu = env["ir.ui.menu"].sudo().with_context(active_test=False)
    actions: list[dict[str, object]] = []
    excluded: list[dict[str, str]] = []
    gaps: list[dict[str, str]] = []

    for menu in Menu.browse(_active_descendant_ids(env, root.id)):
        action = menu.action
        if not action or action._name != "ir.actions.act_window":
            continue
        action = env["ir.actions.act_window"].sudo().browse(action.id).exists()
        menu_xmlid = _xmlid(menu)
        action_xmlid = _xmlid(action)
        owner_module = action_xmlid.partition(".")[0]
        if owner_module != OWNER_MODULE:
            excluded.append(
                {
                    "menu_xmlid": menu_xmlid,
                    "action_xmlid": action_xmlid,
                    "reason": "OUTSIDE_FORMAL_PRODUCT_MODULE",
                }
            )
            continue
        if not action or action.res_model not in env:
            gaps.append(
                {
                    "action_xmlid": action_xmlid,
                    "reason": "ACTION_MODEL_NOT_AVAILABLE",
                }
            )
            continue
        try:
            assembly_semantics = _assembly_semantics(env, action)
        except Exception as exc:  # pragma: no cover - governed runtime evidence
            assembly_semantics = {}
            gaps.append(
                {
                    "action_xmlid": action_xmlid,
                    "reason": f"PAGE_ASSEMBLY_FAILED:{type(exc).__name__}:{exc}",
                }
            )
        views = _resolved_views(env, action, assembly_semantics)
        groups = _effective_group_xmlids(menu, action)
        row = {
            "menu_xmlid": menu_xmlid,
            "menu_name": _text(menu.name),
            "action_xmlid": action_xmlid,
            "action_name": _text(action.name),
            "model": action.res_model,
            "view_mode": _text(action.view_mode),
            "authority_groups": groups,
            "views": views,
        }
        actions.append(row)
        if not menu_xmlid or not action_xmlid:
            gaps.append(
                {
                    "action_xmlid": action_xmlid,
                    "reason": "FORMAL_XMLID_MISSING",
                }
            )
        if not groups:
            gaps.append(
                {
                    "action_xmlid": action_xmlid,
                    "reason": "FORMAL_AUTHORITY_GROUP_MISSING",
                }
            )
        if not views:
            gaps.append(
                {
                    "action_xmlid": action_xmlid,
                    "reason": "ACTION_VIEW_MODE_MISSING",
                }
            )
        for view in views:
            if view["readiness"] == "fail_closed":
                gaps.append(
                    {
                        "action_xmlid": action_xmlid,
                        "reason": _text(view["reason"]),
                    }
                )

    actual_actions = {str(row["action_xmlid"]) for row in actions}
    for missing in sorted(EXPECTED_ANCHORS - actual_actions):
        gaps.append({"action_xmlid": missing, "reason": "EXPECTED_PROJECT_ANCHOR_MISSING"})

    summary = {
        "action_count": len(actions),
        "model_count": len({str(row["model"]) for row in actions}),
        "ready_surface_count": sum(
            view["readiness"] == "ready" for row in actions for view in row["views"]
        ),
        "readable_fallback_count": sum(
            view["readiness"] == "readable_fallback"
            for row in actions
            for view in row["views"]
        ),
        "structural_form_count": sum(
            view["readiness"] == "structural" for row in actions for view in row["views"]
        ),
        "fail_closed_count": sum(
            view["readiness"] == "fail_closed" for row in actions for view in row["views"]
        ),
        "excluded_count": len(excluded),
        "gap_count": len(gaps),
    }
    return {
        "schemaVersion": "frontend_project_domain_rollout.v1",
        "status": "PASS" if not gaps and actions else "FAIL",
        "domain": DOMAIN_KEY,
        "database": env.cr.dbname,
        "root_menu_xmlid": ROOT_MENU_XMLID,
        "owner_module": OWNER_MODULE,
        "summary": summary,
        "actions": actions,
        "excluded": excluded,
        "gaps": gaps,
    }


def write_report(report: dict[str, object], output: Path = OUTPUT_PATH) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if "env" in globals():  # pragma: no branch - Odoo shell execution contract
    payload = collect(env)  # type: ignore[name-defined]  # noqa: F821
    write_report(payload)
    print(json.dumps({"status": payload["status"], "summary": payload["summary"], "output": str(OUTPUT_PATH)}, ensure_ascii=False))
    if payload["status"] != "PASS":
        raise RuntimeError(json.dumps(payload["gaps"], ensure_ascii=False))
