# -*- coding: utf-8 -*-
"""Resolve selected configuration once, at the view orchestration boundary.

The result is an internal projection input; downstream handlers must never query
configuration again. Legacy section metadata is retained only for registered
compatibility consumers, until their migration ledger reaches zero.
"""
from __future__ import annotations

from typing import Any
import json


def resolve_form_structure_governance(source_contract: dict[str, Any], configs, *, view_type: str) -> dict[str, Any]:
    if view_type != "form":
        return {}
    governance = source_contract.get("governance") if isinstance(source_contract.get("governance"), dict) else {}
    view_governance = governance.get("view_orchestration") if isinstance(governance.get("view_orchestration"), dict) else {}
    source_trace = source_contract.get("source_trace") if isinstance(source_contract.get("source_trace"), dict) else {}
    if not source_trace:
        source_contract["source_trace"] = source_trace
    view_trace = source_trace.get("view_orchestration") if isinstance(source_trace.get("view_orchestration"), dict) else {}
    if not view_trace:
        source_trace["view_orchestration"] = view_trace
    business_contracts = view_trace.get("business_config_contracts")
    if not isinstance(business_contracts, list):
        business_contracts = view_governance.get("business_config_contracts")
    if not isinstance(business_contracts, list):
        business_contracts = []
    legacy_overlay = bool(view_trace.get("legacy_field_policy_overlay") or view_governance.get("legacy_field_policy_overlay"))
    form_layout_overlay = bool(view_trace.get("form_layout_overlay") or view_governance.get("form_layout_overlay"))
    form_structure_authority = str(
        view_trace.get("form_structure_authority")
        or view_governance.get("form_structure_authority")
        or ""
    ).strip()
    form_presentation_mode = str(
        view_trace.get("form_presentation_mode")
        or view_governance.get("form_presentation_mode")
        or ""
    ).strip()
    field_names: list[str] = []
    field_labels: dict[str, str] = {}
    field_semantic_roles: dict[str, str] = {}
    section_semantic_roles: dict[str, str] = {}
    configured_sections: list[dict[str, Any]] = []
    allowed_semantic_roles = {"summary", "task", "context", "risk", "relation", "activity", "audit"}
    section_titles: list[str] = []
    field_groups: dict[str, list[str]] = {}
    group_columns: dict[str, int] = {}
    group_visibility: dict[str, bool] = {}
    form_columns = 0
    config_summaries: list[dict[str, Any]] = []

    def normalize_columns(value: Any) -> int:
        try:
            columns = int(value)
        except (TypeError, ValueError):
            return 0
        return columns if columns > 0 else 0

    def collect_layout_group_columns(nodes: Any) -> None:
        for item in nodes if isinstance(nodes, list) else []:
            if not isinstance(item, dict):
                continue
            node_type = str(item.get("type") or item.get("kind") or "").strip().lower()
            title = str(item.get("string") or item.get("label") or item.get("title") or item.get("name") or "").strip()
            attrs = item.get("attributes") if isinstance(item.get("attributes"), dict) else {}
            columns = (
                normalize_columns(item.get("columns"))
                or normalize_columns(item.get("cols"))
                or normalize_columns(item.get("col"))
                or normalize_columns(attrs.get("columns"))
                or normalize_columns(attrs.get("cols"))
                or normalize_columns(attrs.get("col"))
            )
            if node_type == "group" and title and columns:
                group_columns[title] = columns
            for child_key in ("children", "pages", "tabs", "nodes", "items"):
                collect_layout_group_columns(item.get(child_key))
    hidden_field_names: set[str] = set()
    for config in configs:
        config_summaries.append({
            "id": int(config.id or 0),
            "name": str(config.name or ""),
            "priority": int(getattr(config, "priority", 0) or 0),
            "view_type": str(getattr(config, "view_type", "form") or ""),
        })
        payload = config.contract_json if isinstance(config.contract_json, dict) else {}
        orchestration = payload.get("view_orchestration") if isinstance(payload.get("view_orchestration"), dict) else {}
        views = orchestration.get("views") if isinstance(orchestration.get("views"), dict) else {}
        form_spec = views.get("form") if isinstance(views.get("form"), dict) else {}
        composition_mode = str(
            form_spec.get("composition_mode")
            or form_spec.get("compositionMode")
            or ""
        ).strip()
        if composition_mode in {"native_semantic_surface", "semantic_native_surface"}:
            form_structure_authority = "native_authority"
            form_presentation_mode = "task"
        if (
            composition_mode in {"entry_semantic_surface", "semantic_entry_surface"}
            and isinstance(form_spec.get("sections"), list)
            and form_spec.get("sections")
        ):
            form_structure_authority = "entry_semantic_surface"
        form_columns = normalize_columns(form_spec.get("columns")) or normalize_columns(form_spec.get("cols")) or form_columns
        if isinstance(form_spec.get("layout"), list) and form_spec.get("layout"):
            form_layout_overlay = True
            collect_layout_group_columns(form_spec.get("layout"))
        rows = form_spec.get("fields") if isinstance(form_spec.get("fields"), list) else []
        for row in rows:
            if isinstance(row, dict):
                name = str(row.get("name") or row.get("field") or row.get("field_name") or "").strip()
                if not name:
                    continue
                if row.get("visible") is False:
                    hidden_field_names.add(name)
                    field_names = [item for item in field_names if item != name]
                    continue
            else:
                name = str(row or "").strip()
            if name and name in hidden_field_names:
                hidden_field_names.remove(name)
            if name and name not in field_names:
                field_names.append(name)
            label = str(row.get("string") or row.get("label") or "").strip() if isinstance(row, dict) else ""
            if name and label:
                field_labels[name] = label
        semantic_anchors = (
            form_spec.get("semantic_anchors")
            if isinstance(form_spec.get("semantic_anchors"), list)
            else []
        )
        for anchor in semantic_anchors:
            if not isinstance(anchor, dict):
                continue
            role = str(anchor.get("role") or "").strip().lower()
            if role not in allowed_semantic_roles:
                continue
            for raw_name in anchor.get("fields") if isinstance(anchor.get("fields"), list) else []:
                name = str(raw_name or "").strip()
                if name:
                    field_semantic_roles[name] = role
        sections = form_spec.get("sections") if isinstance(form_spec.get("sections"), list) else []
        for row in sections:
            if isinstance(row, dict):
                section_key = str(row.get("key") or "").strip()
                title = str(row.get("title") or row.get("label") or row.get("name") or "").strip()
                fields = [
                    str(item or "").strip()
                    for item in (row.get("fields") if isinstance(row.get("fields"), list) else [])
                    if str(item or "").strip()
                ]
            else:
                section_key = ""
                title = str(row or "").strip()
                fields = []
            if title and title not in section_titles:
                section_titles.append(title)
            if title and isinstance(row, dict) and isinstance(row.get("visible"), bool):
                group_visibility[title] = bool(row.get("visible"))
                if row.get("visible") is False:
                    hidden_field_names.update(fields)
                    hidden_set = set(fields)
                    field_names = [item for item in field_names if item not in hidden_set]
            if title and fields:
                existing = field_groups.setdefault(title, [])
                for name in fields:
                    if name not in existing:
                        existing.append(name)
                if isinstance(row, dict):
                    columns = normalize_columns(row.get("columns")) or normalize_columns(row.get("cols"))
                    if columns:
                        group_columns[title] = columns
            semantic_role = ""
            if isinstance(row, dict):
                semantic_role = str(row.get("semantic_role") or "").strip().lower()
            if section_key and semantic_role in allowed_semantic_roles:
                section_semantic_roles[section_key] = semantic_role
            if title and fields:
                section_identity = "key:%s" % section_key if section_key else "title:%s" % title
                existing_section = next(
                    (item for item in configured_sections if item.get("identity") == section_identity),
                    None,
                )
                if existing_section is None:
                    configured_sections.append({
                        "identity": section_identity,
                        "key": section_key,
                        "title": title,
                        "fields": list(fields),
                    })
                else:
                    existing_section["title"] = title
                    for name in fields:
                        if name not in existing_section["fields"]:
                            existing_section["fields"].append(name)
    applied = bool(
        view_governance.get("applied")
        or business_contracts
        or config_summaries
        or legacy_overlay
        or field_names
        or field_semantic_roles
    )
    if not applied:
        # A resolved native form layout is itself the formal authority for a
        # structured workspace.  Do not require an optional business
        # overlay merely to emit the presentation-mode contract: that
        # would leave ordinary form actions with no explicit mode and
        # force the web client to infer one.  Task mode remains opt-in
        # through a selected entry-semantic orchestration contract.
        views = source_contract.get("views") if isinstance(source_contract.get("views"), dict) else {}
        form_view = views.get("form") if isinstance(views.get("form"), dict) else {}
        native_layout = form_view.get("layout")
        if not isinstance(native_layout, list) or not native_layout:
            return {}
        return {
            "source": "native_form_layout",
            "owner_layer": "native_form_layout",
            "business_config_contracts": [],
            "legacy_field_policy_overlay": False,
            "form_layout_overlay": False,
            "form_structure_authority": "native_authority",
            "form_presentation_mode": "workspace",
            "field_names": [],
            "field_labels": {},
            "field_semantic_roles": {},
            "section_semantic_roles": {},
            "configured_sections": [],
            "section_titles": [],
            "field_groups": {},
            "hidden_field_names": [],
            "form_columns": 0,
            "group_columns": {},
            "group_visibility": {},
        }
    return {
        "source": "business_view_orchestration",
        "owner_layer": str(view_trace.get("owner_layer") or view_governance.get("owner_layer") or "business_view_orchestration"),
        "business_config_contracts": [dict(item) for item in business_contracts if isinstance(item, dict)] or config_summaries,
        "legacy_field_policy_overlay": legacy_overlay,
        "form_layout_overlay": form_layout_overlay,
        "form_structure_authority": form_structure_authority,
        "form_presentation_mode": ("task" if form_presentation_mode == "task" or form_structure_authority == "entry_semantic_surface" else "workspace"),
        "field_names": field_names,
        "field_labels": field_labels,
        "field_semantic_roles": field_semantic_roles,
        "section_semantic_roles": section_semantic_roles,
        "configured_sections": configured_sections,
        "section_titles": section_titles,
        "field_groups": field_groups,
        "hidden_field_names": sorted(hidden_field_names),
        "form_columns": form_columns,
        "group_columns": group_columns,
        "group_visibility": group_visibility,
    }



def diagnose_structure_ownership(configs, *, model: str, action_id=None, view_id=None) -> list[dict]:
    """Compare concrete structure keys; unrelated semantic overlays can coexist.

    Existing legacy overrides are reported while their consumers migrate. A
    native semantic surface cannot accept a competing structural declaration.
    """
    declarations = []
    native_owners = []
    for config in configs:
        payload = config.contract_json if isinstance(config.contract_json, dict) else {}
        spec = ((payload.get("view_orchestration") or {}).get("views") or {}).get("form") or {}
        owner = {"id": int(config.id or 0), "name": str(config.name or "")}
        # Runtime ViewOrchestrationContractProjection carries integer ids;
        # direct model callers may still provide relational record proxies.
        scoped = any(int(getattr(value, "id", value) or 0) > 0 for value in (
            getattr(config, "action_id", 0), getattr(config, "view_id", 0),
        ))
        mode = spec.get("composition_mode") or spec.get("compositionMode")
        if mode in {"native_semantic_surface", "semantic_native_surface"}:
            native_owners.append(owner)
        for key in ("layout", "sections", "fields", "field_slots", "columns", "cols", "actions", "header_buttons"):
            value = spec.get(key)
            if value not in (None, [], {}, ""):
                declarations.append((key, value, owner, scoped))
    conflicts = []
    previous = {}
    for key, value, owner, scoped in declarations:
        prior = previous.get(key)
        if native_owners or (prior and prior[0] != value):
            conflicts.append({
                "code": "NATIVE_SEMANTIC_SURFACE_STRUCTURE_CONFLICT" if native_owners else "LEGACY_STRUCTURE_KEY_OVERRIDE",
                "entry": {"model": model, "action_id": int(action_id or 0), "view_id": int(view_id or 0)},
                "key": key, "node": "view_orchestration.views.form." + key,
                "nodes": [str(item.get("key") or item.get("name") or index)
                          for index, item in enumerate(value) if isinstance(item, dict)] if isinstance(value, list) else [],
                "configuration": owner, "explicit_structure_scope": scoped,
                "competing_owners": native_owners or [prior[1]],
            })
        previous[key] = (value, owner)
    invalid_native = [row for row in conflicts if native_owners and (row["configuration"] in native_owners or row["explicit_structure_scope"])]
    if invalid_native:
        raise ValueError(json.dumps(invalid_native, ensure_ascii=False, sort_keys=True))
    for row in conflicts:
        if native_owners:
            row["code"] = "LEGACY_STRUCTURE_SUPPRESSED_BY_NATIVE_VIEW"
            row["resolution"] = "native view owns structure; legacy semantic field policies retained"

    return conflicts


def authenticated_form_role_key(env) -> str:
    """Resolve role at the only configuration-selection boundary."""
    if not getattr(env, "user", None):
        return ""
    from ..identity.identity_resolver import IdentityResolver
    resolver = IdentityResolver(env)
    return str(resolver.resolve_role_code(resolver.user_group_xmlids(env.user)) or "").strip()
