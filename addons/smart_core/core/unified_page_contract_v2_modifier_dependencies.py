# -*- coding: utf-8 -*-
from __future__ import annotations

import ast
from typing import Any
from enum import IntEnum
from copy import deepcopy

from .request_params import parse_positive_int


MODIFIER_DEPENDENCY_KINDS = {"field_compare", "field_truthy", "field_value"}
# Bounds opportunistic display hydration only. Fields referenced by normalized
# modifiers are correctness dependencies and are added independently.
FORM_RECORD_SNAPSHOT_FIELD_BUDGET = 80
# Bounds the final, layout-aware closure independently of the initial snapshot.
# This is deliberately small: it closes visible first-screen facts without
# turning the form response into an unbounded model read.
# The native projection carries the full native form structure, so a context
# group late in the arch (for example project responsibility fields) can exceed
# the legacy heuristic's first-screen count.  Keep the cap bounded, but large
# enough to close the native first-screen business facts without truncating a
# primary fact such as ``manager_id``.
FORM_VISIBLE_LAYOUT_HYDRATION_BUDGET = 40
FIRST_SCREEN_SEMANTIC_ROLES = {"summary", "task", "risk"}
SUBORDINATE_SEMANTIC_ROLES = {"relation", "activity", "audit"}
INITIAL_RECORD_SEED_FIELDS = (
    "id",
    "display_name",
    "name",
    "document_no",
    "state",
    "company_id",
    "project_id",
    "business_category_id",
    "operation_strategy",
)


def collect_initial_record_snapshot_fields(
    source_contract: dict[str, Any],
    model_fields: Any,
) -> list[str]:
    """Select bounded early facts from requirements and native layout occurrences."""
    fields_map = model_fields if isinstance(model_fields, dict) else {}
    source = source_contract if isinstance(source_contract, dict) else {}
    marker = source.get("nativeFormProjection")
    marker = marker if isinstance(marker, dict) else {}
    view_fields: list[str] = []

    def add_layout_fields(nodes: Any) -> None:
        if not isinstance(nodes, list):
            return
        for node in nodes:
            if not isinstance(node, dict):
                continue
            if str(node.get("type") or node.get("kind") or "").strip().lower() == "field":
                name = str(node.get("name") or node.get("field") or "").strip()
                if name:
                    view_fields.append(name)
            for key in ("children", "pages", "tabs", "nodes", "items"):
                add_layout_fields(node.get(key))

    add_layout_fields(marker.get("layout"))
    marker_requirements = marker.get("fieldRequirements")
    has_native_requirements = (
        bool(view_fields)
        or isinstance(marker_requirements, dict) and bool(marker_requirements)
    )
    form_view = (
        (source.get("views") or {}).get("form")
        if isinstance(source.get("views"), dict)
        else None
    )
    if isinstance(form_view, dict):
        if not view_fields:
            add_layout_fields(form_view.get("layout"))
        if not has_native_requirements and not view_fields:
            for row in form_view.get("fields") or []:
                name = str(
                    row.get("name") or row.get("field") or row.get("field_name")
                    if isinstance(row, dict)
                    else row
                ).strip()
                if name:
                    view_fields.append(name)
    requirements = marker_requirements
    if not isinstance(requirements, dict):
        requirements = source.get("field_requirements")
    if isinstance(requirements, dict):
        model_name = str(source.get("model") or marker.get("model") or "").strip()
        required = requirements.get(model_name) if model_name else None
        if isinstance(required, list):
            view_fields.extend(str(name).strip() for name in required if str(name).strip())
    early_dependencies = source.get("record_snapshot_dependency_fields")
    if isinstance(early_dependencies, list):
        view_fields.extend(str(name).strip() for name in early_dependencies if str(name).strip())
    view_fields = list(dict.fromkeys(view_fields))
    selected: list[str] = []

    def add(name: Any) -> None:
        field_name = str(name or "").strip()
        if not field_name or field_name in selected or field_name not in fields_map:
            return
        field_type = str(getattr(fields_map.get(field_name), "type", "") or "")
        if field_name not in INITIAL_RECORD_SEED_FIELDS and field_type in {
            "one2many", "many2many", "binary", "html",
        }:
            return
        selected.append(field_name)

    for name in INITIAL_RECORD_SEED_FIELDS:
        add(name)
    for name in view_fields:
        add(name)
    return selected[:FORM_RECORD_SNAPSHOT_FIELD_BUDGET]


def collect_modifier_dependency_fields(*sources: Any, known_fields: Any = None) -> list[str]:
    """Return the stable field dependency closure of normalized modifiers.

    The traversal intentionally accepts the complete normalized contract shape:
    actions added by late platform or industry extensions must contribute the
    same dependencies as native form buttons assembled earlier in the request.
    """

    allowed = set(known_fields or []) if known_fields is not None else None
    names: list[str] = []

    def add(field: Any, depth: int) -> None:
        if not isinstance(field, str):
            return
        name = field.strip()
        if depth == 1 and name.startswith("parent."):
            name = name[len("parent."):]
        elif depth != 0:
            return
        # Dotted paths are not fields of the root model. Nested parent frames
        # need their own hydration authority and must never alias this record.
        if not name or "." in name:
            return
        if (allowed is None or name in allowed) and name not in names:
            names.append(name)

    def walk(value: Any, depth: int = 0) -> None:
        if isinstance(value, (list, tuple)):
            for item in value:
                walk(item, depth)
            return
        if not isinstance(value, dict):
            return
        kind = str(value.get("kind") or "").strip()
        if kind in MODIFIER_DEPENDENCY_KINDS:
            add(value.get("field"), depth)
        if kind == "field_compare":
            add(value.get("value_field"), depth)
        for key, child in value.items():
            # Both the field descriptor and native projection preserve explicit
            # subview carriers. The plural carrier adds one scope, not one per
            # field/view key beneath it.
            walk(child, depth + 1 if key in {"subview", "subviews"} else depth)

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


def collect_fact_hydration_fields(contract_v2: Any) -> list[str]:
    """Return a bounded, stable closure of hidden fact fields.

    Native HTML blocks can consume fields that are declared in the form but are
    not part of the visible layout closure (for example ``invisible="1"`` fact
    fields that feed overview-card conditions).  Those fields are selected only
    when the delivered layout marks them ``sc_ui_usage == "fact"``; unrelated
    hidden fields are never expanded.
    """

    if not isinstance(contract_v2, dict):
        return []
    layout = contract_v2.get("layoutContract")
    tree = layout.get("containerTree") if isinstance(layout, dict) else []
    names: list[str] = []

    def fact_name(descriptor: Any) -> str:
        if not isinstance(descriptor, dict):
            return ""
        usage = descriptor.get("uiUsage", descriptor.get("sc_ui_usage"))
        if str(usage or "").strip() != "fact":
            return ""
        return str(descriptor.get("name") or descriptor.get("fieldCode") or "").strip()

    def scan(descriptor: Any) -> None:
        name = fact_name(descriptor)
        if name and name not in names:
            names.append(name)
        if not isinstance(descriptor, dict):
            return
        subview = descriptor.get("subview")
        if not isinstance(subview, dict):
            return
        for field_descriptor in subview.get("fields") or []:
            name = fact_name(field_descriptor)
            if name and name not in names:
                names.append(name)

    def visit(node: Any) -> None:
        if isinstance(node, list):
            for item in node:
                visit(item)
            return
        if not isinstance(node, dict):
            return
        scan(node.get("fieldInfo"))
        for widget in node.get("widgetList") or []:
            scan(widget.get("fieldDescriptor") if isinstance(widget, dict) else None)
        for child in node.get("children") or []:
            visit(child)

    visit(tree)
    return names[:FORM_VISIBLE_LAYOUT_HYDRATION_BUDGET]


def _relation_seed_shape(value: Any) -> Any:
    """Compare native commands with their JSON transport shape, not display rows."""
    if isinstance(value, IntEnum):
        return int(value)
    if isinstance(value, (list, tuple)):
        return [_relation_seed_shape(item) for item in value]
    if isinstance(value, dict):
        return {key: _relation_seed_shape(item) for key, item in value.items()}
    return value


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
    dependencies = collect_modifier_dependency_fields(contract, known_fields=fields)
    relations = [name for name in dependencies if getattr(fields[name], "type", "") in {"one2many", "many2many"}]
    missing = [name for name in dependencies
               if name not in main and getattr(fields[name], "type", "") in scalar_types]
    if not missing and not relations:
        return
    try:
        # Use the same server-resolved create context as the primary data source.
        context = data.get("dataMeta", {}).get("sourceContext", {}).get("context", {})
        Model = Model.with_context(**context)
        Model.check_access_rights("create")
        Model.check_access_rights("read")
        readable = set(Model.check_field_access_rights("read", None))
        missing = [name for name in missing if name in readable]
        relations = [name for name in relations if name in readable]
        if not missing and not relations:
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
                if _relation_seed_shape(value) != _relation_seed_shape(defaults.get(name, False)):
                    raise ValueError("create relation snapshot differs from native defaults")
            elif kind in scalar_types and not isinstance(value, (dict, list, tuple)):
                values[name] = value
        draft = Model.new(values)
    except Exception:
        if logger is not None:
            logger.debug("ui.contract.v2 create modifier draft unavailable", exc_info=True)
        return
    for name in relations:
        try:
            relation = draft[name]
            origin = relation._origin
            origin.check_access_rights("read")
            origin.check_access_rule("read")
            ids = origin.ids
            if not all(isinstance(item, int) and not isinstance(item, bool) and 0 < item <= 9007199254740991 for item in ids):
                raise ValueError("invalid persisted native relation identity")
            if name not in main:
                # Defaults retain native commands. Computed/empty relations not
                # supplied by default_get must be read from the actual draft.
                value = deepcopy(defaults[name]) if name in defaults else fields[name].convert_to_read(
                    relation, draft, use_display_name=False)
                if name not in defaults and (not isinstance(value, (list, tuple)) or not all(
                    isinstance(item, int) and not isinstance(item, bool) and 0 < item <= 9007199254740991 for item in value
                )):
                    raise ValueError("unserializable native create relation dependency")
                main[name] = _relation_seed_shape(value)
            data.setdefault("dataMeta", {}).setdefault("nativeModifierRelationSnapshots", {})[name] = {
                "sourceValue": _relation_seed_shape(deepcopy(main[name])), "persistedIds": list(ids),
            }
        except Exception:
            if logger is not None:
                logger.debug("ui.contract.v2 create relation evaluation unavailable: %s", name, exc_info=True)

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
    record: Any = None,
) -> None:
    """Read missing scalar fields required by the final form presentation.

    The normal record snapshot remains payload-budgeted. Modifier dependencies
    are correctness inputs and may arrive through extensions after that initial
    read. A bounded set of visible primary-layout fields is also selected only
    after final normalized visibility is known. Both use the same bulk read.
    """

    if view_type != "form" or not model or not isinstance(contract_v2, dict):
        return
    # The request layer uses "new" for an unsaved form. Keep arbitrary invalid
    # identities rejected; create authority is checked again before hydration.
    normalized_record_id = None if str(record_id or "").strip().lower() == "new" else record_id
    record_id_int, record_id_error = parse_positive_int(normalized_record_id, allow_empty=True)
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
    data = contract_v2.get("dataContract")
    if isinstance(data, dict) and isinstance(data.get("mainData"), dict):
        names = set(data["mainData"]) | set(collect_modifier_dependency_fields(contract_v2, known_fields=fields_map))
        meta = data.setdefault("dataMeta", {})
        if isinstance(meta, dict):
            meta.pop("nativeModifierRelationSnapshots", None)
            meta["nativeModifierFieldTypes"] = {
                name: fields_map[name].type for name in sorted(names)
                if name in fields_map and isinstance(getattr(fields_map[name], "type", None), str)
            }
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
    fact_fields = collect_fact_hydration_fields(contract_v2)
    missing = []
    # Modifier/action dependencies are correctness inputs and therefore remain
    # outside the opportunistic layout budget. Both closures share one read.
    for field_name in dependencies + visible_layout_fields + fact_fields:
        if field_name in main_data:
            continue
        if field_name in missing:
            continue
        if field_name not in fields_map:
            continue
        field_type = str(getattr(fields_map.get(field_name), "type", "") or "")
        if field_type in {"binary", "html"}:
            continue
        if field_type in {"one2many", "many2many"} and field_name not in dependencies:
            continue
        missing.append(field_name)
    if not missing:
        return

    def request_record_matches(candidate, request_model):
        if (
            candidate is None
            or getattr(candidate, "_name", None) != model
            or len(candidate) != 1
            or int(candidate.id or 0) != record_id_int
        ):
            return False
        candidate_env = getattr(candidate, "env", None)
        request_env = getattr(request_model, "env", None)
        if candidate_env is None or request_env is None:
            return True
        return (
            getattr(candidate_env, "cr", None) is getattr(request_env, "cr", None)
            and int(getattr(candidate_env, "uid", 0) or 0) == int(getattr(request_env, "uid", 0) or 0)
            and bool(getattr(candidate_env, "su", False)) == bool(getattr(request_env, "su", False))
            and dict(getattr(candidate_env, "context", {}) or {})
            == dict(getattr(request_env, "context", {}) or {})
        )

    try:
        if not request_record_matches(record, Model):
            record = Model.browse(record_id_int).exists()
        if not record:
            return

        def accept_value(field_name, value):
            field = fields_map[field_name]
            if field.type in {"one2many", "many2many"}:
                # Only actual ORM identities establish relation truth.
                # Denied or malformed values must remain missing.
                if not isinstance(value, (list, tuple)) or not all(
                    isinstance(item, int) and not isinstance(item, bool)
                    and 0 < item <= 9007199254740991 for item in value
                ):
                    return
                value = list(value)
            main_data[field_name] = value

        remaining = list(missing)
        bulk_failed = False
        try:
            rows = record.read(remaining)
            row = rows[0] if rows and isinstance(rows[0], dict) else {}
            present = {name for name in remaining if name in row}
            for field_name in present:
                accept_value(field_name, row[field_name])
            remaining = [name for name in remaining if name not in present]
        except Exception:
            bulk_failed = True
            # A typed/access failure on the merged read remains local to the
            # unread fields; the original per-field fallback below preserves
            # readable sibling dependencies.
            if logger is not None:
                logger.debug("ui.contract.v2 final modifier dependency bulk read skipped", exc_info=True)

        if bulk_failed and len(remaining) == 1:
            # The merged read already used the same one-field permission and
            # value path; retrying it adds no fallback opportunity.
            return
        for field_name in remaining:
            try:
                rows = record.read([field_name])
                if not rows or not isinstance(rows[0], dict) or field_name not in rows[0]:
                    continue
                accept_value(field_name, rows[0][field_name])
            except Exception:
                # One denied field fails closed for itself only; readable
                # sibling dependencies must still hydrate.
                if logger is not None:
                    logger.debug(
                        "ui.contract.v2 final modifier dependency field skipped: %s.%s",
                        model,
                        field_name,
                        exc_info=True,
                    )
    except Exception:
        # Missing values leave modifier evaluation fail-closed. Never sudo or
        # manufacture permission truth to make an action visible.
        if logger is not None:
            logger.debug("ui.contract.v2 final modifier dependency hydration skipped", exc_info=True)


def hydrate_final_field_contexts(
    contract_v2: dict[str, Any],
    *,
    record_id: Any = None,
    record: Any = None,
) -> None:
    """Resolve native field context expressions into executable dictionaries.

    Odoo view archives carry field contexts as Python expression strings. The
    browser must not evaluate that source language. The contract therefore
    keeps the declaration in ``contextRaw`` and publishes only a resolved
    dictionary in ``context`` once the current record facts are available.
    Unresolved expressions remain untouched so the consumer still fails closed.
    """

    if not isinstance(contract_v2, dict):
        return
    data = contract_v2.get("dataContract")
    data = data if isinstance(data, dict) else {}
    main_data = data.get("mainData")
    meta = data.get("dataMeta")
    meta = meta if isinstance(meta, dict) else {}
    field_types = meta.get("nativeModifierFieldTypes")
    field_types = field_types if isinstance(field_types, dict) else {}
    scope = dict(main_data) if isinstance(main_data, dict) else {}
    for key, value in list(scope.items()):
        if (
            field_types.get(key) == "many2one"
            and isinstance(value, (list, tuple))
            and len(value) == 2
            and isinstance(value[0], int)
            and not isinstance(value[0], bool)
        ):
            scope[key] = value[0]
    source_context = meta.get("sourceContext") if isinstance(meta, dict) else None
    route_context = source_context.get("context") if isinstance(source_context, dict) else None
    if isinstance(route_context, dict):
        scope.setdefault("context", dict(route_context))
        for key, value in route_context.items():
            scope.setdefault(key, value)
    positive_record_id, _error = parse_positive_int(record_id, allow_empty=True)
    actual_id = getattr(record, "id", None) if record is not None else None
    if not isinstance(actual_id, int) or isinstance(actual_id, bool) or actual_id <= 0:
        actual_id = int(positive_record_id or 0)
    scope.setdefault("id", actual_id or False)
    scope.setdefault("active_id", actual_id or False)
    scope.setdefault("active_ids", [actual_id] if actual_id else [])
    if record is not None:
        try:
            scope.setdefault("uid", record.env.uid)
        except Exception:
            pass

    def literal_eval_with_scope(raw: str) -> Any:
        """Evaluate literal containers with named record facts, without Python calls."""

        tree = ast.parse(raw, mode="eval")
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                if node.id not in scope:
                    raise NameError(node.id)
        class ResolveNames(ast.NodeTransformer):
            def visit_Name(self, node: ast.Name) -> ast.AST:
                return ast.copy_location(ast.Constant(scope[node.id]), node)
        return ast.literal_eval(ast.fix_missing_locations(ResolveNames().visit(tree)))

    def resolve(raw: Any) -> dict[str, Any] | None:
        if not isinstance(raw, str) or not raw.strip():
            return None
        try:
            try:
                from odoo.tools.safe_eval import safe_eval
            except (ImportError, ModuleNotFoundError):
                parsed = literal_eval_with_scope(raw)
            else:
                parsed = safe_eval(raw, scope)
        except Exception:
            return None
        return deepcopy(parsed) if isinstance(parsed, dict) else None

    resolved_fields: dict[str, tuple[str, dict[str, Any]]] = {}

    def visit(value: Any) -> None:
        if isinstance(value, list):
            for item in value:
                visit(item)
            return
        if not isinstance(value, dict):
            return
        field_info = value.get("fieldInfo")
        field_info = field_info if isinstance(field_info, dict) else {}
        attributes = value.get("attributes")
        attributes = attributes if isinstance(attributes, dict) else {}
        raw = field_info.get("context")
        if not isinstance(raw, str) or not raw.strip():
            raw = value.get("context")
        if not isinstance(raw, str) or not raw.strip():
            raw = attributes.get("context")
        parsed = resolve(raw)
        if parsed is not None:
            field_name = str(value.get("name") or field_info.get("name") or "").strip()
            if field_name:
                resolved_fields[field_name] = (raw, parsed)
            field_info["contextRaw"] = raw
            field_info["context"] = deepcopy(parsed)
            if "context" in value:
                value["contextRaw"] = raw
                value["context"] = deepcopy(parsed)
            for widget in value.get("widgetList") or []:
                if not isinstance(widget, dict):
                    continue
                descriptor = widget.get("fieldDescriptor")
                if not isinstance(descriptor, dict):
                    continue
                descriptor["context"] = deepcopy(parsed)
        for key in ("children", "pages", "tabs", "nodes", "items"):
            visit(value.get(key))

    def visit_widgets(value: Any) -> None:
        if isinstance(value, list):
            for item in value:
                visit_widgets(item)
            return
        if not isinstance(value, dict):
            return
        for widget in value.get("widgetList") or []:
            if not isinstance(widget, dict):
                continue
            descriptor = widget.get("fieldDescriptor")
            if not isinstance(descriptor, dict):
                continue
            field_name = str(widget.get("fieldCode") or descriptor.get("name") or "").strip()
            resolved = resolved_fields.get(field_name)
            if resolved:
                raw, parsed = resolved
            else:
                raw = descriptor.get("context")
                parsed = resolve(raw)
            if parsed is not None:
                descriptor["context"] = deepcopy(parsed)
        for key in ("children", "pages", "tabs", "nodes", "items"):
            visit_widgets(value.get(key))

    layout = contract_v2.get("layoutContract")
    tree = layout.get("containerTree") if isinstance(layout, dict) else None
    visit(tree)
    visit_widgets(tree)
