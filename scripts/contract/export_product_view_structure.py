# -*- coding: utf-8 -*-
"""Read-only Odoo-shell exporter for resolved product view structures."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from odoo.tools.safe_eval import safe_eval


try:
    ROOT = Path(__file__).resolve().parents[2]
except NameError:
    ROOT = Path("/mnt")
sys.path.insert(0, str(ROOT / "scripts" / "contract"))

from product_view_structure_common import (  # noqa: E402
    SCHEMA, collect_references, manifest_digest, normalize_arch,
    normalize_view_type, policy_menu_rows, sha256_json, sha256_text,
)


def _rooted_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


POLICY_PATH = _rooted_path(os.getenv(
    "PRODUCT_VIEW_STRUCTURE_POLICY",
    "scripts/verify/baselines/formal_business_product_menu_policy_v1.json",
))
OUTPUT_PATH = _rooted_path(os.getenv(
    "PRODUCT_VIEW_STRUCTURE_OUTPUT",
    "artifacts/contract/product_view_structure_contract.json",
))


def _xmlid(record) -> str:
    if not record or not record.exists():
        return ""
    return str(record.get_external_id().get(record.id) or getattr(record, "key", "") or "")


def _action_context(action) -> dict:
    raw = getattr(action, "context", None)
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            value = safe_eval(raw, {"uid": env.uid})  # noqa: F821
            return value if isinstance(value, dict) else {}
        except Exception:
            return {}
    return {}


def _view_id_map(action) -> dict[str, int]:
    result: dict[str, int] = {}
    try:
        for view_id, view_type in action.views:
            normalized = normalize_view_type(view_type)
            if normalized and view_id:
                result.setdefault(normalized, int(view_id))
    except Exception:
        pass
    primary = getattr(action, "view_id", None)
    if primary and primary.exists():
        result.setdefault(normalize_view_type(primary.type), int(primary.id))
    search_view = getattr(action, "search_view_id", None)
    if search_view and search_view.exists():
        result["search"] = int(search_view.id)
    return result


def _declared_view_types(action) -> list[str]:
    result = []
    for raw in str(getattr(action, "view_mode", "") or "").split(","):
        view_type = normalize_view_type(raw)
        if view_type and view_type not in result:
            result.append(view_type)
    if not result:
        result.append("form")
    if "search" not in result:
        result.append("search")
    return result


def _source_chain(view_id: int) -> list[dict]:
    chain = []
    seen = set()
    view = env["ir.ui.view"].sudo().browse(view_id)  # noqa: F821
    while view and view.exists() and view.id not in seen:
        seen.add(view.id)
        arch_db = str(view.arch_db or "")
        chain.append({
            "view_id": int(view.id),
            "view_xmlid": _xmlid(view),
            "name": str(view.name or ""),
            "model": str(view.model or ""),
            "view_type": normalize_view_type(view.type),
            "mode": str(view.mode or ""),
            "priority": int(view.priority or 0),
            "active": bool(view.active),
            "inherit_id": int(view.inherit_id.id or 0),
            "source_arch_hash": sha256_text(arch_db),
        })
        view = view.inherit_id
    return chain


def _resolve_surface(menu_row: dict, action, view_type: str, view_ids: dict[str, int]) -> dict:
    model_name = str(action.res_model or "")
    Model = env[model_name].sudo().with_context(**_action_context(action))  # noqa: F821
    requested_id = int(view_ids.get(view_type) or 0)
    view_def = Model.get_view(view_id=requested_id or None, view_type=view_type)
    resolved_id = int(view_def.get("id") or requested_id or 0)
    arch = str(view_def.get("arch") or "")
    resolved_structure = normalize_arch(arch, semantic=False)
    semantic_structure = normalize_arch(arch, semantic=True)
    source_chain = _source_chain(resolved_id) if resolved_id else []
    view_record = env["ir.ui.view"].sudo().browse(resolved_id) if resolved_id else None  # noqa: F821
    return {
        "contract_ref": f"{menu_row['menu_xmlid']}::{view_type}",
        "menu_xmlid": menu_row["menu_xmlid"],
        "action_xmlid": _xmlid(action),
        "model": model_name,
        "view_type": view_type,
        "view_id": resolved_id,
        "view_xmlid": _xmlid(view_record) if view_record else "",
        "hashes": {
            "source_graph_sha256": sha256_json(source_chain),
            "resolved_arch_sha256": sha256_json(resolved_structure),
            "semantic_structure_sha256": sha256_json(semantic_structure),
        },
        "source_graph": source_chain,
        "references": collect_references(semantic_structure),
        "semantic_structure": semantic_structure,
    }


def _export_menu(menu_row: dict) -> dict:
    menu_xmlid = menu_row["menu_xmlid"]
    menu = env.ref(menu_xmlid, raise_if_not_found=False)  # noqa: F821
    if not menu or menu._name != "ir.ui.menu":
        return {**menu_row, "status": "error", "errors": ["formal menu not found"]}
    action = menu.action
    if not action:
        return {**menu_row, "status": "error", "errors": ["formal menu has no action"]}
    action_type = str(action.type or "")
    base = {**menu_row, "action_type": action_type, "action_xmlid": _xmlid(action)}
    if action_type != "ir.actions.act_window":
        return {**base, "status": "non_view_action", "surfaces": []}
    actual_model = str(action.res_model or "")
    if actual_model != menu_row["res_model"]:
        return {
            **base, "status": "error",
            "errors": [f"policy model {menu_row['res_model']!r} != action model {actual_model!r}"],
        }
    view_ids = _view_id_map(action)
    declared = _declared_view_types(action)
    surfaces = []
    errors = []
    for view_type in declared:
        try:
            surfaces.append(_resolve_surface(menu_row, action, view_type, view_ids))
        except Exception as exc:
            errors.append(f"{view_type}: {type(exc).__name__}: {exc}")
    return {
        **base,
        "status": "error" if errors else "resolved_view_action",
        "declared_view_types": declared,
        "surfaces": surfaces,
        **({"errors": errors} if errors else {}),
    }


def main() -> int:
    policy_text = POLICY_PATH.read_text(encoding="utf-8")
    menu_rows = policy_menu_rows(json.loads(policy_text))
    entries = sorted((_export_menu(row) for row in menu_rows), key=lambda row: row["menu_xmlid"])
    surfaces = [surface for row in entries for surface in row.get("surfaces") or []]
    error_entries = [row["menu_xmlid"] for row in entries if row.get("status") == "error"]
    payload = {
        "schema": SCHEMA,
        "authority": {
            "formal_menu_policy": str(POLICY_PATH.relative_to(ROOT)),
            "formal_menu_policy_sha256": sha256_text(policy_text),
            "runtime_source": "odoo.get_view_resolved_arch",
            "database_role": "clean_install",
            "demo_data": False,
        },
        "summary": {
            "formal_menu_count": len(menu_rows),
            "resolved_view_action_count": sum(row.get("status") == "resolved_view_action" for row in entries),
            "non_view_action_count": sum(row.get("status") == "non_view_action" for row in entries),
            "error_count": len(error_entries),
            "resolved_surface_count": len(surfaces),
            "model_count": len({surface["model"] for surface in surfaces}),
            "view_type_counts": {
                view_type: sum(surface["view_type"] == view_type for surface in surfaces)
                for view_type in sorted({surface["view_type"] for surface in surfaces})
            },
        },
        "error_entries": error_entries,
        "entries": entries,
        "manifest_sha256": manifest_digest(entries),
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT_PATH.with_suffix(OUTPUT_PATH.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(OUTPUT_PATH)
    print(json.dumps({
        "status": "PASS" if not error_entries else "FAIL",
        "output": str(OUTPUT_PATH), **payload["summary"],
    }, ensure_ascii=False, sort_keys=True))
    return 0 if not error_entries else 1


raise SystemExit(main())
