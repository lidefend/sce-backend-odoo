# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any

from .request_params import parse_positive_int


MODIFIER_DEPENDENCY_KINDS = {"field_compare", "field_truthy"}
# Bounds opportunistic display hydration only. Fields referenced by normalized
# modifiers are correctness dependencies and are added independently.
FORM_RECORD_SNAPSHOT_FIELD_BUDGET = 80
# Bounds the final, layout-aware closure independently of the initial snapshot.
# This is deliberately small: it closes visible first-screen facts without
# turning the form response into an unbounded model read.
FORM_VISIBLE_LAYOUT_HYDRATION_BUDGET = 24
FIRST_SCREEN_SEMANTIC_ROLES = {"summary", "task", "risk"}
SUBORDINATE_SEMANTIC_ROLES = {"relation", "activity", "audit"}


def collect_modifier_dependency_fields(*sources: Any, known_fields: Any = None) -> list[str]:
    """Return the stable field dependency closure of normalized modifiers.

    The traversal intentionally accepts the complete normalized contract shape:
    actions added by late platform or industry extensions must contribute the
    same dependencies as native form buttons assembled earlier in the request.
    """

    allowed = set(known_fields or []) if known_fields is not None else None
    names: list[str] = []

    def walk(value: Any) -> None:
        if isinstance(value, (list, tuple)):
            for item in value:
                walk(item)
            return
        if not isinstance(value, dict):
            return
        kind = str(value.get("kind") or "").strip()
        field_name = str(value.get("field") or "").strip()
        if (
            kind in MODIFIER_DEPENDENCY_KINDS
            and field_name
            and (allowed is None or field_name in allowed)
            and field_name not in names
        ):
            names.append(field_name)
        value_field = str(value.get("value_field") or "").strip()
        if (
            kind == "field_compare"
            and value_field
            and (allowed is None or value_field in allowed)
            and value_field not in names
        ):
            names.append(value_field)
        for child in value.values():
            walk(child)

    for source in sources:
        walk(source)
    return names


def collect_visible_layout_hydration_fields(contract_v2: Any) -> list[str]:
    """Return a bounded, stable closure of visible primary-layout fields.

    Semantic first-screen facts are selected first. Remaining visible scalar
    layout fields follow normalized container order, while subordinate audit,
    activity and relation regions are excluded. Visibility is consumed from
    the final normalized widget status; it is never inferred from labels,
    model names or business state.
    """

    if not isinstance(contract_v2, dict):
        return []
    structure = contract_v2.get("formStructureContract")
    field_roles = structure.get("fieldRoles") if isinstance(structure, dict) else {}
    field_roles = field_roles if isinstance(field_roles, dict) else {}
    status_contract = contract_v2.get("statusContract")
    widget_status = status_contract.get("widgetStatus") if isinstance(status_contract, dict) else []
    visible_widget_ids = {
        str(row.get("widgetId") or "").strip()
        for row in widget_status if isinstance(row, dict) and row.get("visible") is True
        if str(row.get("widgetId") or "").strip()
    }
    layout_contract = contract_v2.get("layoutContract")
    container_tree = layout_contract.get("containerTree") if isinstance(layout_contract, dict) else []
    if not isinstance(container_tree, list) or not visible_widget_ids:
        return []

    priority: list[str] = []
    ordinary: list[str] = []
    seen: set[str] = set()

    def role_of(value: Any) -> str:
        if isinstance(value, dict):
            return str(value.get("role") or "").strip().lower()
        return str(value or "").strip().lower()

    def visit(value: Any, inherited_role: str = "") -> None:
        if isinstance(value, list):
            for item in value:
                visit(item, inherited_role)
            return
        if not isinstance(value, dict):
            return
        node_role = role_of(value.get("formStructureRole") or value.get("semanticRole")) or inherited_role
        field_name = str(value.get("name") or value.get("field") or value.get("fieldCode") or "").strip()
        widget_id = str(value.get("widgetId") or "").strip()
        field_role = role_of(field_roles.get(field_name)) or node_role
        if (
            field_name
            and widget_id in visible_widget_ids
            and field_name not in seen
            and node_role not in SUBORDINATE_SEMANTIC_ROLES
            and field_role not in SUBORDINATE_SEMANTIC_ROLES
        ):
            seen.add(field_name)
            if field_role in FIRST_SCREEN_SEMANTIC_ROLES:
                priority.append(field_name)
            else:
                ordinary.append(field_name)
        for key in ("children", "pages", "tabs", "nodes", "items", "widgetList"):
            visit(value.get(key), node_role)

    visit(container_tree)
    return (priority + ordinary)[:FORM_VISIBLE_LAYOUT_HYDRATION_BUDGET]


def _hydrate_create_modifier_dependencies(Model: Any, contract: dict[str, Any], logger: Any) -> None:
    """Materialize missing predicate inputs on an unsaved native record."""
    status = contract.get("statusContract", {}).get("globalStatus", {})
    if status.get("effectiveRenderProfile") != "create" or status.get("effectiveRecordCapabilities", {}).get("create") is not True:
        return
    data = contract.get("dataContract", {})
    main = data.get("mainData")
    if not isinstance(main, dict):
        return
    fields = Model._fields
    scalar_types = {"boolean", "integer", "float", "monetary", "char", "text", "selection", "date", "datetime", "many2one"}
    missing = [name for name in collect_modifier_dependency_fields(contract, known_fields=fields)
               if name not in main and getattr(fields[name], "type", "") in scalar_types]
    if not missing:
        return
    try:
        # Use the same server-resolved create context as the primary data source.
        context = data.get("dataMeta", {}).get("sourceContext", {}).get("context", {})
        Model = Model.with_context(**context)
        Model.check_access_rights("create")
        Model.check_access_rights("read")
        readable = set(Model.check_field_access_rights("read", None))
        missing = [name for name in missing if name in readable]
        if not missing:
            return
        # default_get supplies native relation commands; never feed display
        # values or serialized relation rows from mainData into Model.new().
        defaults = Model.default_get(sorted(readable - {"id", "display_name"}))
        values = dict(defaults)
        for name, value in main.items():
            if name not in readable or name not in fields:
                continue
            kind = fields[name].type
            if kind == "many2one":
                if isinstance(value, (list, tuple)) and len(value) == 2:
                    value = value[0]
                if value is False or value is None or isinstance(value, int) and not isinstance(value, bool) and value > 0:
                    values[name] = value or False
                else:
                    raise ValueError("invalid native create relation identity")
            elif kind in {"one2many", "many2many"}:
                if value != defaults.get(name, False):
                    raise ValueError("create relation snapshot differs from native defaults")
            elif kind in scalar_types and not isinstance(value, (dict, list, tuple)):
                values[name] = value
        draft = Model.new(values)
    except Exception:
        if logger is not None:
            logger.debug("ui.contract.v2 create modifier draft unavailable", exc_info=True)
        return
    for name in missing:
        try:
            main[name] = fields[name].convert_to_read(draft[name], draft, use_display_name=False)
        except Exception:
            # A failed compute/access is unknown, never a manufactured False.
            if logger is not None:
                logger.debug("ui.contract.v2 create modifier dependency unavailable: %s", name, exc_info=True)


def hydrate_final_modifier_dependencies(
    env: Any,
    contract_v2: dict[str, Any],
    *,
    model: str,
    record_id: Any,
    view_type: str,
    logger: Any = None,
) -> None:
    """Read missing scalar fields required by the final form presentation.

    The normal record snapshot remains payload-budgeted. Modifier dependencies
    are correctness inputs and may arrive through extensions after that initial
    read. A bounded set of visible primary-layout fields is also selected only
    after final normalized visibility is known. Both use the same bulk read.
    """

    if view_type != "form" or not model or not isinstance(contract_v2, dict):
        return
    record_id_int, record_id_error = parse_positive_int(record_id, allow_empty=True)
    if record_id_error:
        return
    record_id_int = int(record_id_int or 0)
    try:
        Model = env[model]
    except Exception:
        return
    fields_map = getattr(Model, "_fields", {})
    if not isinstance(fields_map, dict):
        return
    if record_id_int <= 0:
        _hydrate_create_modifier_dependencies(Model, contract_v2, logger)
        return
    data_contract = contract_v2.get("dataContract")
    if not isinstance(data_contract, dict):
        return
    main_data = data_contract.get("mainData")
    if not isinstance(main_data, dict):
        return
    dependencies = collect_modifier_dependency_fields(contract_v2, known_fields=fields_map)
    visible_layout_fields = collect_visible_layout_hydration_fields(contract_v2)
    missing = []
    # Modifier/action dependencies are correctness inputs and therefore remain
    # outside the opportunistic layout budget. Both closures share one read.
    for field_name in dependencies + visible_layout_fields:
        if field_name in main_data:
            continue
        if field_name in missing:
            continue
        if field_name not in fields_map:
            continue
        field_type = str(getattr(fields_map.get(field_name), "type", "") or "")
        if field_type in {"one2many", "many2many", "binary", "html"}:
            continue
        missing.append(field_name)
    if not missing:
        return
    try:
        record = Model.browse(record_id_int).exists()
        if not record:
            return
        rows = record.read(missing)
        if rows and isinstance(rows[0], dict):
            for field_name in missing:
                if field_name in rows[0]:
                    main_data[field_name] = rows[0][field_name]
    except Exception:
        # Missing values leave modifier evaluation fail-closed. Never sudo or
        # manufacture permission truth to make an action visible.
        if logger is not None:
            logger.debug("ui.contract.v2 final modifier dependency hydration skipped", exc_info=True)
