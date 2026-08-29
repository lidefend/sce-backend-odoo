# -*- coding: utf-8 -*-
"""Read-only Odoo-shell exporter for governed resolved product views."""

from __future__ import annotations

import collections
import json
import os
import sys
from pathlib import Path

from lxml import etree
from odoo.tools.safe_eval import safe_eval

try:
    ROOT = Path(__file__).resolve().parents[2]
except NameError:
    ROOT = Path("/mnt")
sys.path.insert(0, str(ROOT / "scripts" / "contract"))
from product_view_structure_common import (  # noqa: E402
    CANONICAL_VIEW_TYPES, SCHEMA, collect_occurrences, collect_references,
    content_digest, file_sha256, normalize_arch, normalize_view_type,
    policy_menu_rows, resolve_odoo17_view, sha256_bytes, sha256_json, sha256_text,
)
from complete_worktree_fingerprint import validate_fingerprint  # noqa: E402


def _path(name: str, default: str) -> Path:
    value = Path(os.getenv(name, default))
    return value if value.is_absolute() else ROOT / value


POLICY_PATH = _path("PRODUCT_VIEW_STRUCTURE_POLICY", "scripts/verify/baselines/formal_business_product_menu_policy_v1.json")
DATABASE_POLICY_PATH = _path("PRODUCT_VIEW_DATABASE_POLICY", "docs/governance/database_architecture_policy.md")
FINGERPRINT_PATH = _path("PRODUCT_VIEW_CANDIDATE_FINGERPRINT", "artifacts/contract/candidate_fingerprint.json")
OUTPUT_PATH = _path("PRODUCT_VIEW_STRUCTURE_OUTPUT", "artifacts/contract/product_view_structure_contract.json")


def _xmlid(record) -> str:
    if not record or not record.exists():
        return ""
    return str(record.get_external_id().get(record.id) or getattr(record, "key", "") or "")


def _record_ref(record) -> str:
    xmlid = _xmlid(record)
    if xmlid:
        return xmlid
    identity = {"name": str(record.name or ""), "model": str(record.model or ""), "type": str(record.type or ""), "arch": sha256_text(str(record.arch_db or ""))}
    return f"anonymous:{sha256_json(identity)}"


def _action_context(action) -> dict:
    raw = getattr(action, "context", None)
    if not raw:
        return {}
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str):
        raise ValueError(f"action context has unsupported type {type(raw).__name__}")
    evaluation = dict(env.context)  # noqa: F821
    evaluation.update({"uid": env.uid, "user": env.user, "active_id": False, "active_ids": [], "active_model": False})  # noqa: F821
    try:
        value = safe_eval(raw, evaluation)
    except Exception as exc:
        raise ValueError(f"action context evaluation failed: {type(exc).__name__}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("action context must evaluate to a dictionary")
    return value


def _view_ids(action) -> dict[str, int]:
    result: dict[str, int] = {}
    for view_id, raw_type in action.views:
        view_type = normalize_view_type(raw_type)
        if view_type not in CANONICAL_VIEW_TYPES:
            raise ValueError(f"unsupported declared view type {raw_type!r}")
        if view_id:
            result.setdefault(view_type, int(view_id))
    for field_name, view_type in (("view_id", ""), ("search_view_id", "search")):
        record = getattr(action, field_name, None)
        if record and record.exists():
            result.setdefault(view_type or normalize_view_type(record.type), int(record.id))
    return result


def _declared_types(action) -> list[str]:
    result = []
    for raw in str(action.view_mode or "").split(","):
        view_type = normalize_view_type(raw)
        if not view_type:
            continue
        if view_type not in CANONICAL_VIEW_TYPES:
            raise ValueError(f"unsupported declared view type {raw!r}")
        if view_type not in result:
            result.append(view_type)
    if not result:
        raise ValueError("window action declares zero view types")
    if "search" not in result:
        result.append("search")
    return result


def _group_refs(view) -> list[str]:
    refs = []
    for group in view.groups_id:
        ref = _xmlid(group)
        if not ref:
            raise ValueError(f"view {_record_ref(view)} has a group without external id")
        refs.append(ref)
    return sorted(refs)


def _source_graph(resolved_view, model_name: str, view_type: str, native_arch) -> dict:
    if not resolved_view:
        ref = f"synthetic:{model_name}:_get_default_{view_type}_view"
        row = {
            "view_ref": ref, "inherit_ref": "", "mode": "synthetic_default",
            "priority": 0, "active": True, "groups": [],
            "arch_sha256": sha256_text(etree.tostring(native_arch, encoding="unicode")),
            "applicability": "applied",
        }
        body = {"root_ref": ref, "contributors": [row], "edges": [], "application_order": [ref]}
        return {**body, "graph_sha256": sha256_json(body)}

    selected = resolved_view
    root = selected
    selected_chain = []
    while root.inherit_id:
        selected_chain.append(root.id)
        root = root.inherit_id
    selected_chain.append(root.id)
    views = selected.browse(selected_chain)
    if "check_view_ids" not in views.env.context:
        views = views.with_context(check_view_ids=[])
    views.env.context["check_view_ids"].extend(selected_chain)
    tree_views = views._get_inheriting_views()
    hierarchy = collections.defaultdict(list)
    for view in tree_views:
        hierarchy[view.inherit_id.id].append(view)
    applied = [root]
    queue = collections.deque(sorted(hierarchy[root.id], key=lambda view: view.mode))
    while queue:
        view = queue.popleft()
        applied.append(view)
        for child in reversed(hierarchy[view.id]):
            if child.mode == "primary":
                queue.append(child)
            else:
                queue.appendleft(child)
    rows, edges, order = [], [], []
    applied_ids = {view.id for view in applied}
    for view in applied:
        ref = _record_ref(view)
        parent_ref = _record_ref(view.inherit_id) if view.inherit_id and view.inherit_id.id in applied_ids else ""
        rows.append({
            "view_ref": ref, "inherit_ref": parent_ref, "mode": str(view.mode or ""),
            "priority": int(view.priority or 0), "active": bool(view.active),
            "groups": _group_refs(view), "arch_sha256": sha256_text(str(view.arch or "")),
            "applicability": "applied",
        })
        order.append(ref)
        if parent_ref:
            edges.append({"parent_ref": parent_ref, "child_ref": ref})
    if not rows or _record_ref(root) != order[0]:
        raise ValueError("native inheritance engine returned an empty or rootless contribution graph")
    body = {"root_ref": _record_ref(root), "contributors": rows, "edges": edges, "application_order": order}
    return {**body, "graph_sha256": sha256_json(body)}


def _enrich_field_meta(node: dict, fields_meta: dict) -> None:
    """Recursively enrich field nodes with model field metadata (type, relation)."""
    if not isinstance(node, dict):
        return
    tag = str(node.get("tag") or "")
    attrs = node.get("attrs")
    if isinstance(attrs, dict) and tag == "field":
        fname = str(attrs.get("name") or "")
        meta = fields_meta.get(fname) if fname else None
        if isinstance(meta, dict):
            ftype = str(meta.get("type") or "")
            if ftype and "type" not in attrs:
                attrs["type"] = ftype
            relation = str(meta.get("relation") or "")
            if relation and "relation" not in attrs:
                attrs["relation"] = relation
    for key in ("children", "pages", "tabs", "nodes", "items", "groups"):
        children = node.get(key)
        if isinstance(children, list):
            for child in children:
                _enrich_field_meta(child, fields_meta)


def _surface(menu_row: dict, action, view_type: str, view_ids: dict[str, int]) -> dict:
    model_name = str(action.res_model or "")
    Model = env[model_name].with_context(**_action_context(action))  # noqa: F821
    requested = int(view_ids.get(view_type) or 0)
    view_def, native_arch, view_record, source_kind = resolve_odoo17_view(Model, requested, view_type)
    if source_kind == "database_view" and not view_record.exists():
        raise ValueError(f"resolved view {view_record.id} does not exist")
    view_ref = _record_ref(view_record) if view_record else f"synthetic:{model_name}:_get_default_{view_type}_view"
    arch = str(view_def.get("arch") or "")
    resolved = normalize_arch(arch, semantic=False)
    semantic = normalize_arch(arch, semantic=True)
    # Enrich field nodes with model field metadata (type, relation) for contract consumers
    try:
        fields_meta = Model.fields_get()
    except Exception:
        fields_meta = {}
    if fields_meta:
        _enrich_field_meta(resolved, fields_meta)
        _enrich_field_meta(semantic, fields_meta)
    if normalize_view_type(resolved.get("tag")) != view_type:
        raise ValueError(f"resolved root {resolved.get('tag')!r} does not match {view_type!r}")
    occurrences = collect_occurrences(semantic, view_ref)
    graph = _source_graph(view_record, model_name, view_type, native_arch)
    return {
        "contract_ref": f"{menu_row['menu_xmlid']}::{view_type}",
        "menu_xmlid": menu_row["menu_xmlid"], "action_xmlid": _xmlid(action),
        "model": model_name, "view_type": view_type, "view_ref": view_ref, "source_kind": source_kind,
        "hashes": {"source_graph_sha256": graph["graph_sha256"], "resolved_arch_sha256": sha256_json(resolved), "semantic_structure_sha256": sha256_json(semantic)},
        "source_graph": graph, "parse_outcome": {"primary": "success", "fallback": "inactive"},
        "references": collect_references(occurrences), "occurrences": occurrences,
        "resolved_structure": resolved, "semantic_structure": semantic,
    }


def _menu(menu_row: dict) -> dict:
    menu = env.ref(menu_row["menu_xmlid"], raise_if_not_found=False)  # noqa: F821
    if not menu or menu._name != "ir.ui.menu":
        raise ValueError(f"{menu_row['menu_xmlid']}: formal menu not found")
    action = menu.action
    if not action:
        raise ValueError(f"{menu_row['menu_xmlid']}: formal menu has no action")
    action_xmlid = _xmlid(action)
    if not action_xmlid:
        raise ValueError(f"{menu_row['menu_xmlid']}: action has no external id")
    base = {**menu_row, "action_type": str(action.type or ""), "action_xmlid": action_xmlid}
    if action.type != "ir.actions.act_window":
        return {**base, "status": "non_view_action", "surfaces": []}
    if str(action.res_model or "") != menu_row["res_model"]:
        raise ValueError(f"{menu_row['menu_xmlid']}: policy/action model mismatch")
    ids = _view_ids(action)
    declared = _declared_types(action)
    return {**base, "status": "resolved_view_action", "declared_view_types": declared, "surfaces": [_surface(menu_row, action, view_type, ids) for view_type in declared]}


def _runtime_authority(fingerprint: dict, policy_sha: str) -> dict:
    modules = [{"name": row.name, "installed_version": str(row.installed_version or "unknown")} for row in env["ir.module.module"].search([("state", "=", "installed")], order="name")]  # noqa: F821
    groups = sorted(filter(None, (_xmlid(group) for group in env.user.groups_id)))  # noqa: F821
    if not modules or not groups:
        raise ValueError("runtime module set and group profile must be non-empty")
    return {
        "branch": fingerprint["branch"],
        "candidate_fingerprint": {key: fingerprint[key] for key in ("algorithm", "git_head", "baseline_sha", "scope_manifest_sha256", "digest")},
        "database_policy_path": str(DATABASE_POLICY_PATH.relative_to(ROOT)), "database_policy_sha256": file_sha256(DATABASE_POLICY_PATH),
        "formal_menu_policy_path": str(POLICY_PATH.relative_to(ROOT)), "formal_menu_policy_sha256": policy_sha,
        "runtime_profile": "local.clean", "compose_project": "sc-local-clean", "database": "sc_clean", "database_filter": "^sc_clean$", "demo_data": False,
        "module_set": modules, "module_set_sha256": sha256_json(modules),
        "user": str(env.user.login or _xmlid(env.user)), "company": _xmlid(env.company) or str(env.company.name),  # noqa: F821
        "language": str(env.lang or ""), "group_profile": groups, "exporter_version": SCHEMA,
        "runtime_source": "odoo.get_view_resolved_arch_and_native_inheritance_engine",
    }


def main() -> int:
    fingerprint = json.loads(FINGERPRINT_PATH.read_text(encoding="utf-8"))
    fingerprint_errors = validate_fingerprint(fingerprint)
    if fingerprint_errors:
        raise ValueError("; ".join(fingerprint_errors))
    policy_bytes = POLICY_PATH.read_bytes()
    policy = json.loads(policy_bytes.decode("utf-8"))
    menu_rows = policy_menu_rows(policy)
    entries = sorted((_menu(row) for row in menu_rows), key=lambda row: row["menu_xmlid"])
    surfaces = [surface for row in entries for surface in row.get("surfaces") or []]
    if not surfaces:
        raise ValueError("formal product resolved zero view surfaces")
    summary = {
        "formal_menu_count": len(menu_rows), "resolved_view_action_count": sum(row["status"] == "resolved_view_action" for row in entries),
        "non_view_action_count": sum(row["status"] == "non_view_action" for row in entries), "error_count": 0,
        "resolved_surface_count": len(surfaces), "model_count": len({surface["model"] for surface in surfaces}),
        "view_type_counts": {view_type: sum(surface["view_type"] == view_type for surface in surfaces) for view_type in sorted({surface["view_type"] for surface in surfaces})},
    }
    payload = {"schema": SCHEMA, "authority": _runtime_authority(fingerprint, sha256_bytes(policy_bytes)), "summary": summary, "entries": entries}
    payload["manifest_sha256"] = content_digest(payload, "manifest_sha256")
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT_PATH.with_suffix(OUTPUT_PATH.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(OUTPUT_PATH)
    print(json.dumps({"status": "PASS", **summary, "output": str(OUTPUT_PATH)}, ensure_ascii=False, sort_keys=True))
    return 0


raise SystemExit(main())
