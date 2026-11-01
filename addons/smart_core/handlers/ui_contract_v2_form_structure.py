# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any

from . import ui_contract_v2_projection as _projection


def build_form_structure_contract(
    handler,
    *,
    model: str,
    profile: dict[str, Any],
    field_type,
    unique,
    field_label,
    governance: dict[str, Any] | None = None,
    navigation_title: str = "",
) -> dict[str, Any]:
    common_source = (
        profile.get("form_structure_common_fields")
        if "form_structure_common_fields" in profile
        else profile.get("common_fields")
    )
    detail_source = (
        profile.get("form_structure_detail_fields")
        if "form_structure_detail_fields" in profile
        else profile.get("detail_fields")
    )
    common_fields = [
        str(item or "").strip()
        for item in (common_source or [])
    ]
    amount_fields = [str(item or "").strip() for item in profile.get("amount_fields") or []]
    date_fields = [str(item or "").strip() for item in profile.get("date_fields") or []]
    detail_fields = [
        str(item or "").strip()
        for item in (detail_source or [])
    ]
    status_field = str(profile.get("status_field") or "").strip()
    note_field = str(profile.get("note_field") or "").strip()
    attachment_field = str(profile.get("attachment_field") or "").strip()
    source_section_titles = [
        str(item or "").strip()
        for item in (profile.get("source_section_titles") or [])
        if str(item or "").strip()
    ]
    allowed_fields = {
        name
        for name in common_fields + detail_fields
        if name
    }
    if attachment_field:
        detail_fields = [name for name in detail_fields if name != attachment_field]

    def fields_for(items: list[str]) -> list[str]:
        selected = unique(items)
        if not allowed_fields:
            return []
        return [name for name in selected if name in allowed_fields]

    field_labels = profile.get("field_labels") if isinstance(profile.get("field_labels"), dict) else {}

    def field_display_label(name: str) -> str:
        label = str(field_labels.get(name) or "").strip()
        if label:
            return label
        try:
            return str(field_label(name) or "").strip()
        except Exception:
            return str(name or "").strip()

    def formal_governance_source(value: dict[str, Any] | None) -> dict[str, Any]:
        row = value if isinstance(value, dict) else {}
        out: dict[str, Any] = {
            "source": str(row.get("source") or "business_operation_profile"),
            "ownerLayer": str(row.get("owner_layer") or "business_operation_profile"),
        }
        mappings = {
            "business_config_contracts": "businessConfigContracts",
            "resolved_view_id": "resolvedViewId",
            "resolved_action_id": "resolvedActionId",
            "structure_diagnostics": "structureDiagnostics",
            "compatibility_dependencies": "compatibilityDependencies",
            "legacy_field_policy_overlay": "legacyFieldPolicyOverlay",
            "form_layout_overlay": "formLayoutOverlay",
            "form_structure_authority": "formStructureAuthority",
            "form_presentation_mode": "formPresentationMode",
            "field_names": "fieldNames",
            "field_labels": "fieldLabels",
            "field_semantic_roles": "fieldSemanticRoles",
            "section_semantic_roles": "sectionSemanticRoles",
            "configured_sections": "configuredSections",
            "section_titles": "sectionTitles",
            "field_groups": "fieldGroups",
            "hidden_field_names": "hiddenFieldNames",
            "group_columns": "groupColumns",
            "group_visibility": "groupVisibility",
            "category_id": "categoryId",
            "category_code": "categoryCode",
            "target_model": "targetModel",
        }
        for source_key, target_key in mappings.items():
            if source_key in row:
                out[target_key] = row[source_key]
        form_columns = handler._form_layout_columns_from_governance(row)
        if form_columns > 0:
            out["formColumns"] = form_columns
        return out

    def derive_field_ownership(roles: dict[str, Any]) -> dict[str, dict[str, str]]:
        ownership: dict[str, dict[str, str]] = {}
        for name, info in (roles or {}).items():
            if not isinstance(info, dict):
                continue
            slot = str(info.get("slot") or "").strip()
            group = str(info.get("group") or "").strip()
            if not slot:
                continue
            owner: dict[str, str] = {"ownerSlotRef": "slot:%s" % slot}
            if group:
                owner["ownerGroupRef"] = "group:%s" % group
            ownership["field:%s" % name] = owner
        return ownership

    if (governance or {}).get("form_structure_authority") == "native_authority":
        return {
            "source": "ui.contract.v2.form_structure_contract",
            "structureVersion": "1.1", "model": model, "viewType": "form",
            "mode": "native_structured_form",
            "presentationMode": _projection.form_structure_presentation_mode(
                "native_authority", (governance or {}).get("form_presentation_mode")),
            "structureSource": "native_view",
            "structureAuthority": "container_tree",
            "objectProfile": {"model": model, "kind": "business_form",
                              "factAuthority": "business_object_model_and_view"},
            "navigation": {"title": navigation_title or "业务办理"},
            "slots": [], "fieldRoles": {}, "fieldOwnership": {},
            "surfaces": handler._form_structure_surfaces(model=model),
            "sourceAuthority": {
                "kind": handler.SOURCE_KIND,
                "runtime_carrier": "ui.contract.v2.form_structure_contract",
                "projection_only": True, "no_business_fact_authority": True,
                "governed_form_structure": True,
                "governance_source": formal_governance_source(governance),
            },
        }

    configured_field_groups = (
        governance.get("field_groups")
        if isinstance(governance, dict) and isinstance(governance.get("field_groups"), dict)
        else {}
    )
    governance_source = formal_governance_source(governance)
    if configured_field_groups:
        group_rows: list[dict[str, Any]] = []
        configured_roles: dict[str, dict[str, Any]] = {}
        assigned_configured_fields: set[str] = set()
        for index, (raw_title, raw_fields) in enumerate(configured_field_groups.items(), start=1):
            title = str(raw_title or "").strip() or "业务配置字段"
            if not handler._form_layout_group_visible_from_governance(governance, title):
                continue
            names = [
                str(item or "").strip()
                for item in (raw_fields if isinstance(raw_fields, list) else [])
                if str(item or "").strip()
            ]
            refs = [
                name
                for name in fields_for(names)
                if name not in assigned_configured_fields
            ]
            if not refs:
                continue
            assigned_configured_fields.update(refs)
            group_name = "configured_group_%s" % index
            for name in refs:
                configured_roles[name] = {
                    "role": "configured_field",
                    "slot": "configured_form",
                    "group": group_name,
                }
            row = {
                "name": group_name,
                "title": title,
                "role": "configured_field_group",
                "fieldRefs": refs,
                "fieldLabels": {name: field_display_label(name) for name in refs},
            }
            columns = handler._form_layout_columns_from_governance(governance, title)
            if columns:
                row["columns"] = columns
            group_rows.append(row)
        if group_rows:
            form_columns = handler._form_layout_columns_from_governance(governance)
            presentation_mode = _projection.form_structure_presentation_mode(
                (governance or {}).get("form_structure_authority"),
                (governance or {}).get("form_presentation_mode"),
            )
            return {
                "source": "ui.contract.v2.form_structure_contract",
                "structureVersion": "1.1",
                "model": model,
                "viewType": "form",
                **({"columns": form_columns} if form_columns > 0 else {}),
                "mode": "business_task_form" if presentation_mode == "task" else "native_structured_form",
                "presentationMode": presentation_mode,
                "structureSource": "business_orchestration",
                "structureAuthority": (
                    "task_sections" if presentation_mode == "task" else "native_form_slots"
                ),
                "objectProfile": {
                    "model": model,
                    "kind": "business_form",
                    "factAuthority": "business_object_model_and_view",
                },
                "navigation": {"title": navigation_title or "业务办理"},
                "sourceSectionTitles": [row.get("title") for row in group_rows if row.get("title")],
                "slots": [{
                    "slot": "configured_form",
                    "title": "表单字段",
                    "role": "configured_form",
                    "groups": group_rows,
                }],
                "fieldRoles": configured_roles,
                "fieldOwnership": derive_field_ownership(configured_roles),
                "surfaces": handler._form_structure_surfaces(model=model),
                "sourceAuthority": {
                    "kind": handler.SOURCE_KIND,
                    "runtime_carrier": "ui.contract.v2.form_structure_contract",
                    "projection_only": True,
                    "no_business_fact_authority": True,
                    "governed_form_structure": True,
                    "governance_source": governance_source,
                },
            }

    # Minimal fallback: native projection failed and no field-group
    # configuration produced a structure.  Do NOT guess field roles from
    # names/types.  Preserve the selected authority label and provenance so an
    # explicit entry_semantic_surface remains distinguishable from a true
    # unclassified default; pageComposition still classifies the empty
    # ownership as unclassified_historical with a NOT_VERIFIED diagnostic.
    structure_authority = str(
        (governance or {}).get("form_structure_authority") or ""
    ).strip()
    presentation_mode = _projection.form_structure_presentation_mode(
        structure_authority,
        (governance or {}).get("form_presentation_mode"),
    )
    semantic_surface = presentation_mode == "task"
    return {
        "source": "ui.contract.v2.form_structure_contract",
        "structureVersion": "1.1",
        "model": model,
        "viewType": "form",
        "mode": "business_task_form" if semantic_surface else "minimal_fallback",
        "presentationMode": presentation_mode,
        "structureSource": (
            "entry_semantic_surface"
            if structure_authority == "entry_semantic_surface"
            else "native_view"
        ),
        "structureAuthority": (
            "task_sections"
            if structure_authority == "entry_semantic_surface"
            else "container_tree"
        ),
        "objectProfile": {
            "model": model,
            "kind": "business_form",
            "factAuthority": "business_object_model_and_view",
        },
        "navigation": {"title": navigation_title or "业务办理"},
        "slots": [],
        "fieldRoles": {},
        "fieldOwnership": {},
        "surfaces": handler._form_structure_surfaces(
            model=model,
            capabilities=profile.get("capabilities"),
        ),
        "sourceAuthority": {
            "kind": handler.SOURCE_KIND,
            "runtime_carrier": "ui.contract.v2.form_structure_contract",
            "projection_only": True,
            "no_business_fact_authority": True,
            "governed_form_structure": structure_authority == "entry_semantic_surface",
            "governance_source": formal_governance_source(governance),
        },
    }
