# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any

from . import ui_contract_v2_projection as _projection
from ..core.form_structure_authority import TECHNICAL_FIELD_CODES
from .ui_contract_v2_constants import (
    BUSINESS_FORM_STRUCTURE_HISTORY_LABEL_TOKENS,
    BUSINESS_FORM_STRUCTURE_HISTORY_NAME_PREFIXES,
    BUSINESS_FORM_STRUCTURE_HISTORY_NAME_SUFFIXES,
    BUSINESS_FORM_STRUCTURE_HISTORY_NAME_TOKENS,
)


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

    slot_assigned_fields: set[str] = set()

    def claim_slot_fields(items: list[str]) -> list[str]:
        out: list[str] = []
        for name in fields_for(items):
            if name in slot_assigned_fields:
                continue
            slot_assigned_fields.add(name)
            out.append(name)
        return out

    def first_existing(items: list[str]) -> list[str]:
        return fields_for(items)[:1]

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

    def is_migration_history_field(name: str) -> bool:
        value = str(name or "").strip()
        label = field_display_label(value)
        if any(token in label for token in BUSINESS_FORM_STRUCTURE_HISTORY_LABEL_TOKENS):
            return True
        return (
            value.startswith(BUSINESS_FORM_STRUCTURE_HISTORY_NAME_PREFIXES)
            or any(token in value for token in BUSINESS_FORM_STRUCTURE_HISTORY_NAME_TOKENS)
            or any(value.endswith(suffix) for suffix in BUSINESS_FORM_STRUCTURE_HISTORY_NAME_SUFFIXES)
        )

    def is_history_check_field(name: str) -> bool:
        value = str(name or "").strip()
        if value.startswith("legacy_") or "_legacy_" in value or value.endswith("_legacy"):
            return is_migration_history_field(value)
        return False

    history_check_fields = [
        name
        for name in fields_for(common_fields)
        if is_history_check_field(name)
    ]
    business_common_fields = [
        name
        for name in common_fields
        if name not in set(history_check_fields) and name not in TECHNICAL_FIELD_CODES
    ]

    declared_identity = (governance or {}).get("identity_fields")
    identity_fields = claim_slot_fields(
        declared_identity if isinstance(declared_identity, list) else [
            "name", "document_no", "invoice_no", "invoice_code",
            "subject", "type", "source_kind", "direction", "category_id", "contract_type_id",
        ]
    )
    source_fields_candidates = fields_for([
        "entry_user_id", "entry_user_text", "entry_time", "handler_name",
        "creator_name", "created_time", "archived",
    ])
    relation_candidates = fields_for([
        "project_id", "partner_id", "contract_id", "settlement_id", "payment_request_id",
        "operation_strategy", "handler_id", "company_id", "budget_id", "analytic_id",
    ] + [
        name
        for name in business_common_fields
        if field_type(name) == "many2one"
    ])
    relation_fields = claim_slot_fields([
        name
        for name in relation_candidates
        if name not in identity_fields and name not in source_fields_candidates
    ])
    term_fields = claim_slot_fields([
        "date_start", "date_end", "engineering_category_text", "engineering_address",
        "engineering_content", "affiliated_person", "contract_duration_text",
        "contract_payment_method_text",
    ])
    attachment_fields = fields_for(["attachment_text", attachment_field])
    amount_fields = claim_slot_fields([name for name in amount_fields if name in business_common_fields])
    status_fields = claim_slot_fields([
        name
        for name in fields_for([status_field, "document_status"] + date_fields)
        if name not in source_fields_candidates and name in business_common_fields
    ])
    collaboration_fields = claim_slot_fields([
        name
        for name in ["approval_info", note_field] + attachment_fields
        if name in business_common_fields or name in attachment_fields
    ])
    detail_fields = claim_slot_fields(detail_fields)
    source_fields = claim_slot_fields(source_fields_candidates)
    history_check_fields = claim_slot_fields(history_check_fields)
    field_roles: dict[str, dict[str, Any]] = {}

    def labels_for(items: list[str]) -> dict[str, str]:
        return {
            # 字段显示名优先取 profile 配置 label，其次回退到字段定义的权威 string
            # （field_display_label），而不是直接兜底成字段名 —— 否则 many2many 等
            # 不在 common/detail 字段列表里的字段（如 res.partner.category_id）
            # 会以原始字段名展示，覆盖正确的中文显示名。
            name: str(field_labels.get(name) or field_display_label(name) or name).strip()
            for name in fields_for(items)
        }

    def assign_role(fields: list[str], *, role: str, slot: str, group: str) -> None:
        for name in fields_for(fields):
            if name not in field_roles:
                field_roles[name] = {"role": role, "slot": slot, "group": group}

    assigned = set(
        identity_fields
        + relation_fields
        + term_fields
        + amount_fields
        + status_fields
        + collaboration_fields
        + source_fields
        + detail_fields
        + history_check_fields
    )
    other_fact_fields = fields_for([
        name
        for name in business_common_fields
        if name not in assigned and field_type(name) not in {"one2many", "many2many"}
    ])
    assign_role(identity_fields, role="identity", slot="primary_facts", group="identity")
    assign_role(relation_fields, role="relation", slot="primary_facts", group="relations")
    assign_role(term_fields, role="term", slot="primary_facts", group="terms")
    assign_role(other_fact_fields, role="fact", slot="primary_facts", group="other_facts")
    assign_role(amount_fields, role="amount", slot="amount_progress", group="amounts")
    assign_role(status_fields, role="status_or_date", slot="amount_progress", group="status_dates")
    assign_role(collaboration_fields, role="collaboration", slot="collaboration", group="approval_remarks")
    assign_role(detail_fields, role="detail", slot="details_source", group="details")
    assign_role(source_fields, role="provenance", slot="details_source", group="provenance")
    assign_role(history_check_fields, role="history_check", slot="details_source", group="history_check")

    summary_fields = fields_for(
        [status_field]
        + first_existing(["subject", "name", "document_no", "legacy_document_no", "invoice_no"])
        + first_existing(["project_id", "partner_id", "contract_id", "settlement_id"])
        + first_existing(["date_contract", "document_date", "invoice_date", "date_request", "date_receipt"])
        + first_existing([
            "visible_contract_amount", "amount_total", "amount", "settlement_amount",
            "invoice_amount", "received_amount", "paid_amount",
        ])
        + attachment_fields
    )
    if summary_fields and all(is_history_check_field(name) for name in summary_fields):
        summary_fields = []

    def group(name: str, title: str, fields: list[str], *, role: str = "") -> dict[str, Any]:
        group_fields = fields_for(fields)
        effective_title = title
        if name == "details" and len(group_fields) == 1:
            label = str(field_labels.get(group_fields[0]) or "").strip()
            if label and label not in {"明细", "行", "Lines"}:
                effective_title = label
        return {
            "name": name,
            "title": effective_title,
            "role": role or name,
            "fieldRefs": group_fields,
            "fieldLabels": labels_for(group_fields),
        }

    def slot(name: str, title: str, groups: list[dict[str, Any]], *, role: str = "") -> dict[str, Any]:
        return {
            "slot": name,
            "title": title,
            "role": role or name,
            "groups": [item for item in groups if item.get("fieldRefs")],
        }

    slots = [
        {
            "slot": "overview",
            "title": "办理总览",
            "role": "overview",
            "readonly": True,
            "fieldRefs": summary_fields or fields_for(business_common_fields[:6]),
        },
        slot("primary_facts", "主业务事实", [
            group("identity", "业务识别", identity_fields, role="identity"),
            group("relations", "业务关系", relation_fields, role="relations"),
            group("terms", "业务约定", term_fields, role="terms"),
            group("other_facts", "其他事实", other_fact_fields, role="facts"),
        ], role="facts"),
        slot("amount_progress", "金额与进度", [
            group("amounts", "金额信息", amount_fields, role="amounts"),
            group("status_dates", "状态与日期", status_fields, role="status_dates"),
        ], role="progress"),
        slot("collaboration", "办理协作", [
            group("approval_remarks", "审批与备注", collaboration_fields, role="collaboration"),
        ], role="collaboration"),
        slot("details_source", "明细与来源", [
            group("details", "业务明细", detail_fields, role="details"),
            group("provenance", "录入与归档", source_fields, role="provenance"),
            group("history_check", "历史核对信息", history_check_fields, role="history_check"),
        ], role="provenance"),
    ]
    slots = [
        item
        for item in slots
        if item.get("fieldRefs") or item.get("groups")
    ]

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
        "mode": "business_task_form" if semantic_surface else "native_structured_form",
        "presentationMode": presentation_mode,
        "structureSource": (
            "entry_semantic_surface" if structure_authority == "entry_semantic_surface" else "native_view"
        ),
        "structureAuthority": (
            "task_sections" if structure_authority == "entry_semantic_surface" else "native_form_slots"
        ),
        "objectProfile": {
            "model": model,
            "kind": "business_form",
            "factAuthority": "business_object_model_and_view",
        },
        "navigation": {"title": navigation_title or "业务办理"},
        "sourceSectionTitles": source_section_titles,
        "slots": slots,
        "fieldRoles": field_roles,
        "fieldOwnership": derive_field_ownership(field_roles),
        "surfaces": handler._form_structure_surfaces(
            model=model,
            capabilities=profile.get("capabilities"),
        ),
        "sourceAuthority": {
            "kind": handler.SOURCE_KIND,
            "runtime_carrier": "ui.contract.v2.form_structure_contract",
            "projection_only": True,
            "no_business_fact_authority": True,
            "governed_form_structure": True,
            "governance_source": governance_source,
        },
    }
