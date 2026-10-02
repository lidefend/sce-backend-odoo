# -*- coding: utf-8 -*-
"""Boundary contract for business view orchestration.

The boundary covers every Odoo view surface.  Form layout is only one
specialized consumer; it must not define the platform-wide orchestration model.
"""

from __future__ import annotations

from typing import Any

from .source_authority import build_source_authority_contract


SOURCE_KIND = "business_view_orchestration_boundary"
SOURCE_AUTHORITIES = (
    "odoo_native_view_parse_snapshot",
    "ir.model.fields",
    "ir.actions.act_window",
    "ir.ui.view",
    "ui.business.config.contract",
    "ui.business.config.contract.version",
    "ui.form.field.policy",
)
NO_BUSINESS_FACT_AUTHORITY = True

VIEW_ORCHESTRATION_LAYERS = (
    "model_capability",
    "native_view_parse_snapshot",
    "business_view_orchestration",
    "contract_projection",
    "user_preference",
)

SUPPORTED_VIEW_TYPES = (
    "form",
    "tree",
    "list",
    "kanban",
    "search",
    "pivot",
    "graph",
    "calendar",
    "gantt",
    "activity",
    "dashboard",
)

VIEW_ORCHESTRATOR_INPUTS = (
    "model_capabilities",
    "native_view_parse_snapshot",
    "view_type",
    "action_scope",
    "source_view_scope",
    "business_config_contract",
    "business_config_version",
    "business_config_rules",
    "legacy_field_policy_overlay",
)

VIEW_ORCHESTRATOR_OUTPUTS = (
    "view_type",
    "layout_slots",
    "field_order",
    "visible_field_policy",
    "business_action_slots",
    "relation_entry_slots",
    "aggregation_slots",
    "search_filter_slots",
    "grouping_slots",
    "collaboration_slots",
    "source_trace",
)

VIEW_TYPE_OUTPUT_SURFACES = {
    "form": ("container_tree", "field_order", "business_action_slots", "relation_entry_slots", "collaboration_slots"),
    "tree": ("columns", "column_order", "row_actions", "aggregation_slots"),
    "list": ("columns", "column_order", "row_actions", "aggregation_slots"),
    "kanban": ("card_layout", "grouping_slots", "quick_actions"),
    "search": ("filter_slots", "group_by_slots", "favorite_slots"),
    "pivot": ("measure_slots", "row_dimension_slots", "column_dimension_slots"),
    "graph": ("measure_slots", "dimension_slots", "chart_policy"),
    "calendar": ("date_slots", "resource_slots", "color_slots"),
    "gantt": ("date_slots", "dependency_slots", "resource_slots"),
    "activity": ("activity_type_slots", "deadline_slots", "assignee_slots"),
    "dashboard": ("metric_slots", "chart_slots", "navigation_slots"),
}

# ``ui.business.config.contract`` is the authority a set of orchestration rules
# is published under. Runtime telemetry needs to name the exact published
# version that governed one delivery, so the reference format and the carriers
# it is read from are declared here instead of being inferred downstream.
BUSINESS_CONFIG_CONTRACT_MODEL = "ui.business.config.contract"
BUSINESS_CONFIG_CONTRACT_PUBLISHED_SOURCE_KIND = "published"

# Collection views are addressed as either ``tree`` or ``list`` by different
# producers and consumers (``ui.contract`` collapses them at runtime), so the two
# names address the same declared orchestration entry.
VIEW_TYPE_ALIASES = {
    "list": ("tree",),
    "tree": ("list",),
}

PARSER_ALLOWED_OUTPUTS = (
    "native_view_type",
    "native_arch_snapshot",
    "native_field_nodes",
    "native_container_nodes",
    "native_buttons",
    "native_modifiers",
    "native_columns",
    "native_filters",
    "native_group_bys",
    "native_measures",
    "native_templates",
    "native_subviews",
    "native_chatter",
)

PARSER_FORBIDDEN_RESPONSIBILITIES = (
    "business_config_selection",
    "business_config_rule_evaluation",
    "business_section_naming",
    "business_field_reordering",
    "business_column_reordering",
    "business_filter_prioritization",
    "business_measure_selection",
    "business_action_repositioning",
    "user_specific_structure",
)


def source_authority_contract() -> dict[str, Any]:
    return build_source_authority_contract(
        kind=SOURCE_KIND,
        authorities=list(SOURCE_AUTHORITIES),
        no_business_fact_authority=NO_BUSINESS_FACT_AUTHORITY,
        runtime_carrier="view_orchestration_contract",
    )


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _text(value: Any) -> str:
    return str(value if value is not None else "").strip()


def view_type_candidates(view_type: Any) -> tuple[str, ...]:
    """Return the declared view-type names that address one orchestration entry."""
    name = _text(view_type)
    if not name:
        return ()
    return (name,) + tuple(
        alias for alias in VIEW_TYPE_ALIASES.get(name, ()) if alias != name
    )


def applied_business_config_contracts(payload: Any, view_type: Any = "") -> list[dict[str, Any]]:
    """Return the applied business-config contract rows a payload declares.

    Only carriers this boundary already produces are read: the view
    orchestration summary writes ``governance.view_orchestration.views`` and the
    single-view orchestrator writes the flat ``view_orchestration`` entry, each
    mirrored on ``source_trace``; the assembled runtime contract mirrors the
    summary on ``runtimeContract.governance``. The first carrier that declares
    rows for the requested view wins, so no row is ever inferred from another
    view's entry.
    """
    body = _dict(payload)
    carriers = [body.get("governance"), body.get("source_trace")]
    runtime_contract = _dict(body.get("runtimeContract"))
    if runtime_contract:
        carriers.append(runtime_contract.get("governance"))
    for container in carriers:
        orchestration = _dict(_dict(container).get("view_orchestration"))
        if not orchestration:
            continue
        views = _dict(orchestration.get("views"))
        for name in view_type_candidates(view_type):
            row = _dict(views.get(name))
            rows = row.get("business_config_contracts")
            if isinstance(rows, list) and rows:
                return [item for item in rows if isinstance(item, dict)]
        rows = orchestration.get("business_config_contracts")
        if isinstance(rows, list) and rows:
            return [item for item in rows if isinstance(item, dict)]
    return []


def business_config_contract_ref(row: Any) -> str:
    """Name one applied contract row as ``<model>:<id>@<version_no>``."""
    entry = _dict(row)
    try:
        contract_id = int(entry.get("id") or 0)
    except (TypeError, ValueError):
        contract_id = 0
    if contract_id <= 0:
        return ""
    try:
        version_no = int(entry.get("version_no") or 0)
    except (TypeError, ValueError):
        version_no = 0
    return "%s:%s@%s" % (BUSINESS_CONFIG_CONTRACT_MODEL, contract_id, version_no)


def resolve_published_version_ref(payload: Any, view_type: Any = "") -> str:
    """Return the published business-config versions that governed a delivery.

    A preview or draft row is not a published version, so it is never attributed
    to one; a delivery with no published row resolves to the empty string and
    stays unattributed instead of borrowing another delivery's version. The
    reference is deterministic: rows are ordered by id then version, so the same
    applied set always resolves to the same identity.
    """
    published = []
    for row in applied_business_config_contracts(payload, view_type):
        source_kind = _text(row.get("source_kind")) or BUSINESS_CONFIG_CONTRACT_PUBLISHED_SOURCE_KIND
        if source_kind != BUSINESS_CONFIG_CONTRACT_PUBLISHED_SOURCE_KIND:
            continue
        ref = business_config_contract_ref(row)
        if ref and ref not in published:
            published.append(ref)
    return ",".join(sorted(published))
