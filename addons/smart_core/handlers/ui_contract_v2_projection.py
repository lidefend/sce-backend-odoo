# -*- coding: utf-8 -*-
from __future__ import annotations

from copy import deepcopy
from typing import Any

from . import ui_contract_v2_adapters as _adapters


_CONTAINER_CHILD_KEYS = ("children", "pages", "tabs", "nodes", "items")


def _stable_container_id(value: Any, fallback: str) -> str:
    raw = str(value or fallback or "container").strip()
    normalized = "".join(
        char if char.isalnum() or char in "_.:-" else "." if char in " /" else ""
        for char in raw
    ).strip(".") or fallback or "container"
    return normalized if normalized[0].isalpha() else f"id.{normalized}"


def normalize_post_projected_container_tree(
    contract: dict[str, Any],
    container_tree: list[Any],
) -> list[Any]:
    """Restore the formal V2 container invariant after late projections.

    The assembler owns the original normalized tree.  A late projection may
    move those nodes or add presentation-only containers, but it must not emit
    a second, weaker container dialect after assembly.  Existing identities
    and status verdicts are preserved; only missing structural facts are
    completed deterministically.
    """
    status_contract = contract.get("statusContract") if isinstance(contract.get("statusContract"), dict) else {}
    container_status = (
        status_contract.get("containerStatus")
        if isinstance(status_contract.get("containerStatus"), list)
        else []
    )
    status_ids = {
        str(row.get("containerId") or "").strip()
        for row in container_status
        if isinstance(row, dict) and str(row.get("containerId") or "").strip()
    }
    seen_ids: set[str] = set()

    def normalize(nodes: list[Any], parent_id: str) -> list[Any]:
        out: list[Any] = []
        for index, raw_node in enumerate(nodes, start=1):
            if not isinstance(raw_node, dict):
                out.append(raw_node)
                continue
            node = raw_node
            node_type = str(node.get("containerType") or node.get("type") or "section").strip().lower() or "section"
            formal_type = "section" if node_type == "sheet" else node_type
            fallback = f"{parent_id}.{formal_type}.{index}" if parent_id else f"{formal_type}.{index}"
            container_id = _stable_container_id(
                node.get("containerId") or node.get("container_id") or node.get("name"),
                fallback,
            )
            if container_id in seen_ids:
                container_id = _stable_container_id(fallback, fallback)
                suffix = 2
                while container_id in seen_ids:
                    container_id = _stable_container_id(f"{fallback}.{suffix}", fallback)
                    suffix += 1
            seen_ids.add(container_id)
            node["containerId"] = container_id
            node["containerType"] = formal_type
            node.setdefault("type", node_type)
            label = str(
                node.get("title")
                or node.get("string")
                or node.get("label")
                or node.get("name")
                or container_id
            ).strip()
            node["title"] = label or container_id
            span = node.get("span")
            node["span"] = span if isinstance(span, int) and not isinstance(span, bool) and 1 <= span <= 24 else 24
            if not isinstance(node.get("widgetList"), list):
                node["widgetList"] = []
            for key in _CONTAINER_CHILD_KEYS:
                children = node.get(key)
                if isinstance(children, list):
                    node[key] = normalize(children, container_id)
            if not isinstance(node.get("children"), list):
                node["children"] = []
            if container_id not in status_ids:
                container_status.append({"containerId": container_id, "visible": True, "disabled": False})
                status_ids.add(container_id)
            out.append(node)
        return out

    normalized = normalize(container_tree, "")
    status_contract["containerStatus"] = container_status
    contract["statusContract"] = status_contract
    return normalized


def set_v2_container_tree(contract: dict[str, Any], container_tree: list[Any]) -> None:
    if not isinstance(contract, dict):
        return
    layout_contract = contract.get("layoutContract") if isinstance(contract.get("layoutContract"), dict) else {}
    layout_contract["containerTree"] = container_tree
    contract["layoutContract"] = layout_contract


def set_v2_widget_status(contract: dict[str, Any], widget_status: list[dict[str, Any]]) -> None:
    if not isinstance(contract, dict):
        return
    status_contract = contract.get("statusContract") if isinstance(contract.get("statusContract"), dict) else {}
    status_contract["widgetStatus"] = widget_status
    contract["statusContract"] = status_contract


def set_v2_data_meta(contract: dict[str, Any], patch: dict[str, Any]) -> None:
    if not isinstance(contract, dict) or not isinstance(patch, dict):
        return
    data_contract = contract.get("dataContract") if isinstance(contract.get("dataContract"), dict) else {}
    data_meta = data_contract.get("dataMeta") if isinstance(data_contract.get("dataMeta"), dict) else {}
    data_meta.update(patch)
    data_contract["dataMeta"] = data_meta
    contract["dataContract"] = data_contract


def replace_v2_contract_content(contract: dict[str, Any], replacement: dict[str, Any]) -> None:
    if not isinstance(contract, dict) or not isinstance(replacement, dict):
        return
    contract.clear()
    contract.update(replacement)


def set_v2_governance_patch(contract: dict[str, Any], key: str, patch: dict[str, Any]) -> None:
    if not isinstance(contract, dict) or not key or not isinstance(patch, dict):
        return
    governance = contract.get("governance") if isinstance(contract.get("governance"), dict) else {}
    governance[key] = patch
    contract["governance"] = governance


def project_v2_source_policies(
    contract: dict[str, Any],
    source_contract: dict[str, Any],
    *,
    source_kind: str,
    no_business_fact_authority: bool,
) -> None:
    if not isinstance(contract, dict) or not isinstance(source_contract, dict):
        return
    if isinstance(source_contract.get("delete_policy"), dict):
        delete_policy = dict(source_contract.get("delete_policy") or {})
        action_contract = contract.get("actionContract") if isinstance(contract.get("actionContract"), dict) else {}
        action_contract["deletePolicy"] = _adapters.v2_policy_projection(
            delete_policy,
            source_kind=source_kind,
            no_business_fact_authority=no_business_fact_authority,
            runtime_carrier="ui.contract.v2.actionContract.deletePolicy",
            source_key="delete_policy",
        )
        contract["actionContract"] = action_contract
    if isinstance(source_contract.get("surface_policies"), dict):
        surface_policies = deepcopy(source_contract.get("surface_policies") or {})
        action_contract = contract.get("actionContract") if isinstance(contract.get("actionContract"), dict) else {}
        action_contract["surfacePolicies"] = _adapters.v2_policy_projection(
            surface_policies,
            source_kind=source_kind,
            no_business_fact_authority=no_business_fact_authority,
            runtime_carrier="ui.contract.v2.actionContract.surfacePolicies",
            source_key="surface_policies",
        )
        contract["actionContract"] = action_contract
    if isinstance(source_contract.get("list_profile"), dict):
        list_profile = deepcopy(source_contract.get("list_profile") or {})
        layout_contract = contract.get("layoutContract") if isinstance(contract.get("layoutContract"), dict) else {}
        existing_profile = (
            deepcopy(layout_contract.get("listProfile"))
            if isinstance(layout_contract.get("listProfile"), dict)
            else {}
        )
        projected_profile = _adapters.v2_policy_projection(
            list_profile,
            source_kind=source_kind,
            no_business_fact_authority=no_business_fact_authority,
            runtime_carrier="ui.contract.v2.layoutContract.listProfile",
            source_key="list_profile",
        )
        # The list policy is authoritative for the keys it projects, but it must
        # not erase independent native-view semantics already assembled into the
        # same profile (for example collection_presentation).  Those semantics
        # still use the standard list data source and Odoo model authority.
        existing_profile.update(projected_profile)
        layout_contract["listProfile"] = existing_profile
        contract["layoutContract"] = layout_contract
        sync_v2_list_widget_status_from_profile(contract, source_contract)


def sync_v2_list_widget_status_from_profile(
    contract: dict[str, Any],
    source_contract: dict[str, Any],
) -> None:
    """Align table status without widening an unproven field.

    The recovery list is computed before assembly while the full native and
    policy provenance is still available.  Missing or otherwise unexplained
    status rows remain fail-closed, hidden columns may only be tightened, and
    this projection never grants edit.
    """
    page_info = contract.get("pageInfo") if isinstance(contract.get("pageInfo"), dict) else {}
    if str(page_info.get("viewType") or page_info.get("view_type") or "").strip().lower() not in {"tree", "list"}:
        return
    profile = source_contract.get("list_profile") if isinstance(source_contract.get("list_profile"), dict) else {}
    recoverable_fields = {
        str(name or "").strip()
        for name in (
            source_contract.get("_canonical_list_visible_status_fields")
            if isinstance(source_contract.get("_canonical_list_visible_status_fields"), list)
            else []
        )
        if str(name or "").strip()
    }
    hidden_fields = {
        str(name or "").strip()
        for name in (
            profile.get("hidden_columns")
            if isinstance(profile.get("hidden_columns"), list)
            else []
        )
        if str(name or "").strip()
    }
    if not recoverable_fields and not hidden_fields:
        return
    layout = contract.get("layoutContract") if isinstance(contract.get("layoutContract"), dict) else {}
    containers = layout.get("containerTree") if isinstance(layout.get("containerTree"), list) else []
    table_widgets: dict[str, str] = {}

    def visit(rows: list[Any]) -> None:
        for row in rows:
            if not isinstance(row, dict):
                continue
            for widget in row.get("widgetList") if isinstance(row.get("widgetList"), list) else []:
                if not isinstance(widget, dict):
                    continue
                field_code = str(widget.get("fieldCode") or "").strip()
                widget_id = str(widget.get("widgetId") or "").strip()
                widget_type = str(widget.get("widgetType") or "").strip().lower()
                component_key = str(widget.get("componentKey") or "").strip()
                if (
                    field_code in recoverable_fields | hidden_fields
                    and widget_id
                    and (widget_type == "table" or component_key == "sc.table.data")
                ):
                    table_widgets[widget_id] = field_code
            for key in ("children", "pages", "tabs", "nodes", "items"):
                children = row.get(key)
                if isinstance(children, list):
                    visit(children)

    visit(containers)
    if not table_widgets:
        return

    status_contract = contract.get("statusContract") if isinstance(contract.get("statusContract"), dict) else {}
    widget_status = status_contract.get("widgetStatus") if isinstance(status_contract.get("widgetStatus"), list) else []
    for row in widget_status:
        if not isinstance(row, dict):
            continue
        widget_id = str(row.get("widgetId") or "").strip()
        field_code = table_widgets.get(widget_id)
        if not field_code:
            continue
        if field_code in hidden_fields:
            row["visible"] = False
            row["auth"] = "none"
        elif field_code in recoverable_fields and row.get("visible") is False:
            row["visible"] = True
            if row.get("auth") == "none":
                row["auth"] = "read"
    set_v2_widget_status(contract, widget_status)


def apply_field_policies_to_v2_status(contract_v2: dict[str, Any], source_contract: dict[str, Any]) -> None:
    field_policies = source_contract.get("field_policies") if isinstance(source_contract.get("field_policies"), dict) else {}
    if not field_policies:
        return
    business_policy = source_contract.get("business_form_policy") if isinstance(source_contract.get("business_form_policy"), dict) else {}
    render_profile = str(
        source_contract.get("render_profile")
        or business_policy.get("render_profile")
        or ""
    ).strip().lower()
    if render_profile in {"read", "view"}:
        render_profile = "readonly"
    if render_profile not in {"create", "edit", "readonly"}:
        render_profile = "edit"
    status_contract = contract_v2.get("statusContract") if isinstance(contract_v2.get("statusContract"), dict) else {}
    widget_status = status_contract.get("widgetStatus") if isinstance(status_contract.get("widgetStatus"), list) else []
    by_widget: dict[str, list[dict[str, Any]]] = {}
    for row in widget_status:
        if not isinstance(row, dict):
            continue
        widget_id = str(row.get("widgetId") or "").strip()
        if widget_id:
            by_widget.setdefault(widget_id, []).append(row)

    def apply_policy(row: dict[str, Any], policy: dict[str, Any]) -> None:
        visible_profiles = policy.get("visible_profiles")
        if isinstance(visible_profiles, list) and visible_profiles:
            row["visible"] = render_profile in {str(item) for item in visible_profiles}
        readonly_profiles = policy.get("readonly_profiles")
        if isinstance(readonly_profiles, list) and readonly_profiles:
            row["readonly"] = render_profile in {str(item) for item in readonly_profiles}
        required_profiles = policy.get("required_profiles")
        if isinstance(required_profiles, list) and required_profiles:
            row["required"] = render_profile in {str(item) for item in required_profiles}
        for key in ("visible", "readonly", "required", "disabled"):
            if isinstance(policy.get(key), bool):
                row[key] = bool(policy.get(key))
        row["auth"] = "none" if row.get("visible") is False else "read" if row.get("readonly") else "edit"

    for field_name, policy in field_policies.items():
        if not isinstance(policy, dict):
            continue
        field_code = str(field_name or "").strip()
        if not field_code:
            continue
        widget_id = f"field.{field_code}"
        rows = by_widget.get(widget_id)
        if not rows:
            row = {
                "widgetId": widget_id,
                "visible": True,
                "readonly": False,
                "required": False,
                "disabled": False,
                "auth": "edit",
            }
            widget_status.append(row)
            rows = [row]
        for row in rows:
            apply_policy(row, policy)
    set_v2_widget_status(contract_v2, widget_status)


def ensure_native_layout_widget_status_visible(contract_v2: dict[str, Any]) -> None:
    layout_contract = contract_v2.get("layoutContract") if isinstance(contract_v2.get("layoutContract"), dict) else {}
    container_tree = layout_contract.get("containerTree") if isinstance(layout_contract.get("containerTree"), list) else []
    if not container_tree:
        return

    def modifier_true(value: Any) -> bool:
        if value is True or value == 1:
            return True
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes"}
        return False

    def node_invisible(node: dict[str, Any]) -> bool:
        if modifier_true(node.get("invisible")):
            return True
        attributes = node.get("attributes") if isinstance(node.get("attributes"), dict) else {}
        modifiers = node.get("modifiers") if isinstance(node.get("modifiers"), dict) else {}
        attribute_modifiers = attributes.get("modifiers") if isinstance(attributes.get("modifiers"), dict) else {}
        return any(
            modifier_true(value)
            for value in (
                attributes.get("invisible"),
                modifiers.get("invisible"),
                attribute_modifiers.get("invisible"),
            )
        )

    visible_widget_ids: set[str] = set()

    def walk(rows: list[Any]) -> None:
        for row in rows:
            if not isinstance(row, dict):
                continue
            node_type = str(row.get("type") or row.get("containerType") or "").strip().lower()
            if node_type == "field" and not node_invisible(row):
                widget_id = str(row.get("widgetId") or "").strip()
                if not widget_id:
                    field_name = str(row.get("name") or row.get("field") or "").strip()
                    widget_id = f"field.{field_name}" if field_name else ""
                if widget_id:
                    visible_widget_ids.add(widget_id)
            for key in ("children", "pages", "tabs", "nodes", "items"):
                children = row.get(key)
                if isinstance(children, list):
                    walk(children)

    walk(container_tree)
    if not visible_widget_ids:
        return
    status_contract = contract_v2.get("statusContract") if isinstance(contract_v2.get("statusContract"), dict) else {}
    widget_status = status_contract.get("widgetStatus") if isinstance(status_contract.get("widgetStatus"), list) else []
    seen: set[str] = set()
    for row in widget_status:
        if not isinstance(row, dict):
            continue
        widget_id = str(row.get("widgetId") or "").strip()
        if widget_id not in visible_widget_ids:
            continue
        seen.add(widget_id)
        row["visible"] = True
        if row.get("readonly") is True:
            row["auth"] = "read"
        elif row.get("disabled") is not True:
            row["auth"] = "edit"
    for widget_id in sorted(visible_widget_ids - seen):
        widget_status.append({
            "widgetId": widget_id,
            "visible": True,
            "readonly": False,
            "required": False,
            "disabled": False,
            "auth": "edit",
        })
    set_v2_widget_status(contract_v2, widget_status)


def form_layout_governance(source_contract: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(source_contract, dict):
        return {}
    profile = source_contract.get("business_operation_profile")
    if not isinstance(profile, dict):
        return {}
    governance = profile.get("form_structure_governance")
    return governance if isinstance(governance, dict) else {}


def form_layout_governance_columns(source_contract: dict[str, Any] | None, title: str = "") -> int:
    governance = form_layout_governance(source_contract)
    return form_layout_columns_from_governance(governance, title)


def form_layout_columns_from_governance(governance: dict[str, Any] | None, title: str = "") -> int:
    if not isinstance(governance, dict):
        return 0
    group_columns = governance.get("group_columns") if isinstance(governance.get("group_columns"), dict) else {}
    columns = 0
    key = str(title or "").strip()
    if key:
        try:
            columns = int(group_columns.get(key) or 0)
        except (TypeError, ValueError):
            columns = 0
    if columns <= 0:
        try:
            columns = int(governance.get("form_columns") or 0)
        except (TypeError, ValueError):
            columns = 0
    return columns if columns > 0 else 0


def form_layout_group_visible_from_governance(governance: dict[str, Any] | None, title: str = "") -> bool:
    if not isinstance(governance, dict):
        return True
    group_visibility = governance.get("group_visibility") if isinstance(governance.get("group_visibility"), dict) else {}
    key = str(title or "").strip()
    if not key or key not in group_visibility:
        return True
    return bool(group_visibility.get(key))


def apply_form_layout_governance_to_group(
    node: dict[str, Any],
    title: str = "",
    *,
    source_contract: dict[str, Any] | None = None,
) -> None:
    if not isinstance(node, dict):
        return
    resolved_title = str(
        title
        or node.get("string")
        or node.get("label")
        or node.get("title")
        or node.get("name")
        or ""
    ).strip()
    columns = form_layout_governance_columns(source_contract, resolved_title)
    if columns <= 0:
        return
    node["cols"] = columns
    node["columns"] = columns
    attrs = node.get("attributes") if isinstance(node.get("attributes"), dict) else {}
    attrs["col"] = str(columns)
    node["attributes"] = attrs


def apply_business_config_form_groups(
    contract: dict[str, Any],
    governance: dict[str, Any],
    *,
    source_contract: dict[str, Any] | None = None,
) -> None:
    layout_contract = contract.get("layoutContract") if isinstance(contract.get("layoutContract"), dict) else {}
    container_tree = layout_contract.get("containerTree") if isinstance(layout_contract.get("containerTree"), list) else []
    if not container_tree:
        return
    hidden_field_names = {
        str(item or "").strip()
        for item in (governance.get("hidden_field_names") or [])
        if str(item or "").strip()
    }
    semantic_surface_authority = bool(governance.get("semantic_surface_authority"))
    fields_meta = (
        source_contract.get("fields")
        if isinstance(source_contract, dict) and isinstance(source_contract.get("fields"), dict)
        else {}
    )

    def node_field_name(node: Any) -> str:
        if not isinstance(node, dict):
            return ""
        return str(node.get("name") or node.get("field") or node.get("fieldCode") or "").strip()

    def node_field_type(node: Any) -> str:
        if not isinstance(node, dict):
            return ""
        name = node_field_name(node)
        field_info = node.get("fieldInfo") if isinstance(node.get("fieldInfo"), dict) else {}
        component_config = node.get("componentConfig") if isinstance(node.get("componentConfig"), dict) else {}
        meta = fields_meta.get(name) if isinstance(fields_meta.get(name), dict) else {}
        return str(
            field_info.get("type")
            or component_config.get("fieldType")
            or meta.get("type")
            or meta.get("ttype")
            or ""
        ).strip().lower()

    def is_relation_field(node: Any) -> bool:
        return node_field_type(node) in {"one2many", "many2many"}

    def remove_fields(
        nodes: list[Any],
        names: set[str],
        *,
        collect: dict[str, dict[str, Any]] | None = None,
        include_widget_nodes: bool = True,
    ) -> list[Any]:
        out: list[Any] = []
        for node in nodes:
            if not isinstance(node, dict):
                out.append(node)
                continue
            node_type = str(node.get("type") or node.get("containerType") or "").strip().lower()
            name = node_field_name(node)
            is_field_node = node_type == "field" or (
                include_widget_nodes and bool(str(node.get("widgetId") or "").strip())
            )
            if is_field_node and name in names:
                if collect is not None:
                    collect.setdefault(name, deepcopy(node))
                continue
            next_node = node
            for key in ("children", "pages", "tabs", "nodes", "items", "widgetList"):
                children = next_node.get(key)
                if isinstance(children, list):
                    next_node = dict(next_node)
                    next_node[key] = remove_fields(
                        children,
                        names,
                        collect=collect,
                        include_widget_nodes=include_widget_nodes,
                    )
            out.append(next_node)
        return out

    if hidden_field_names:
        container_tree = remove_fields(container_tree, hidden_field_names)
        structure = contract.get("formStructureContract") if isinstance(contract.get("formStructureContract"), dict) else {}
        roles = structure.get("fieldRoles") if isinstance(structure.get("fieldRoles"), dict) else {}
        if roles:
            structure["fieldRoles"] = {name: role for name, role in roles.items() if name not in hidden_field_names}
        set_v2_container_tree(contract, container_tree)

    field_groups = governance.get("field_groups") if isinstance(governance.get("field_groups"), dict) else {}
    configured_groups: list[tuple[str, list[str]]] = []
    configured_names: set[str] = set()
    for raw_title, raw_names in field_groups.items():
        title = str(raw_title or "").strip()
        if title and not form_layout_group_visible_from_governance(governance, title):
            continue
        names = [
            str(name or "").strip()
            for name in (raw_names if isinstance(raw_names, list) else [])
            if str(name or "").strip()
        ]
        if semantic_surface_authority:
            names = [name for name in names if not is_relation_field({"type": "field", "name": name})]
        names = [name for name in names if name not in hidden_field_names and name not in configured_names]
        if not title or not names:
            continue
        configured_names.update(names)
        configured_groups.append((title, names))
    if not configured_groups:
        return

    moved_nodes: dict[str, dict[str, Any]] = {}
    native_tree = deepcopy(container_tree)
    container_tree = remove_fields(
        container_tree,
        configured_names,
        collect=moved_nodes,
        include_widget_nodes=False,
    )

    def group_title(node: Any) -> str:
        if not isinstance(node, dict):
            return ""
        if str(node.get("type") or node.get("containerType") or "").strip().lower() != "group":
            return ""
        return str(node.get("string") or node.get("label") or node.get("title") or "").strip()

    def find_group(nodes: list[Any], title: str) -> dict[str, Any] | None:
        for node in nodes:
            if not isinstance(node, dict):
                continue
            if group_title(node) == title:
                return node
            for key in ("children", "pages", "tabs", "nodes", "items"):
                children = node.get(key)
                if isinstance(children, list):
                    found = find_group(children, title)
                    if found is not None:
                        return found
        return None

    for index, (title, names) in enumerate(configured_groups, start=1):
        # A semantic entry surface owns the root task-section structure.  Do
        # not reuse an equally named group nested in the legacy/category
        # sheet: that sheet is discarded below, which would also discard the
        # fields just moved into it.  On repeated projection the authoritative
        # semantic groups are already top-level, so top-level reuse remains
        # idempotent.
        group = (
            next(
                (
                    node
                    for node in container_tree
                    if isinstance(node, dict) and group_title(node) == title
                ),
                None,
            )
            if semantic_surface_authority
            else find_group(container_tree, title)
        )
        if group is None:
            group = {
                "type": "group",
                "name": "business_config_group_%s" % index,
                "string": title,
                "label": title,
                "children": [],
                "widgetList": [],
            }
            container_tree.append(group)
        apply_form_layout_governance_to_group(group, title, source_contract=source_contract)
        children = group.get("children") if isinstance(group.get("children"), list) else []
        children.extend(deepcopy(moved_nodes[name]) for name in names if name in moved_nodes)
        group["children"] = children

    if semantic_surface_authority:
        semantic_groups = [
            node
            for node in container_tree
            if isinstance(node, dict) and group_title(node) in {title for title, _names in configured_groups}
        ]
        subordinate_types = {"header", "statusbar", "button_box", "attachment", "chatter"}
        preserved: list[dict[str, Any]] = []
        relation_nodes: list[dict[str, Any]] = []
        seen_relations: set[str] = set()

        def preserve_relation(node: dict[str, Any]) -> dict[str, Any] | None:
            name = node_field_name(node)
            if not name or name in seen_relations or not is_relation_field(node):
                return None
            seen_relations.add(name)
            return deepcopy(node)

        def prune_relation_container(node: dict[str, Any]) -> dict[str, Any] | None:
            node_type = str(node.get("type") or node.get("containerType") or "").strip().lower()
            if node_type == "field":
                return preserve_relation(node)
            row = deepcopy(node)
            had_children = False
            for key in ("children", "pages", "tabs", "nodes", "items"):
                children = row.get(key)
                if not isinstance(children, list):
                    continue
                had_children = True
                row[key] = [
                    cleaned
                    for child in children
                    if isinstance(child, dict)
                    for cleaned in [prune_relation_container(child)]
                    if cleaned is not None
                ]
            if had_children and not any(
                row.get(key)
                for key in ("children", "pages", "tabs", "nodes", "items")
                if isinstance(row.get(key), list)
            ):
                return None
            return row if had_children else None

        def collect_subordinates(nodes: Any) -> None:
            for node in nodes if isinstance(nodes, list) else []:
                if not isinstance(node, dict):
                    continue
                node_type = str(node.get("type") or node.get("containerType") or "").strip().lower()
                if node_type in subordinate_types:
                    preserved.append(deepcopy(node))
                    continue
                if node_type == "notebook":
                    cleaned = prune_relation_container(node)
                    if cleaned is not None:
                        preserved.append(cleaned)
                    continue
                if node_type == "field":
                    relation = preserve_relation(node)
                    if relation is not None:
                        relation_nodes.append(relation)
                    continue
                for key in ("children", "pages", "tabs", "nodes", "items"):
                    collect_subordinates(node.get(key))

        collect_subordinates(native_tree)
        if relation_nodes:
            preserved.append({
                "type": "notebook",
                "name": "native_subordinate_relations",
                "string": "关联明细",
                "label": "关联明细",
                "children": [{
                    "type": "page",
                    "name": "native_subordinate_relations_page",
                    "string": "关联明细",
                    "label": "关联明细",
                    "children": relation_nodes,
                }],
                "sourceAuthority": {
                    "kind": "odoo_native_view_subordinate_structure",
                    "projection_only": True,
                    "no_business_fact_authority": True,
                },
            })
        leading = [node for node in preserved if str(node.get("type") or "").lower() == "header"]
        trailing = [node for node in preserved if str(node.get("type") or "").lower() != "header"]
        container_tree = [*leading, *semantic_groups, *trailing]

    set_v2_container_tree(contract, normalize_post_projected_container_tree(contract, container_tree))
