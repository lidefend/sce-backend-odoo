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
            for producer_key, canonical_key in (
                ("native_locator", "nativeLocator"),
                ("occurrence_index", "occurrenceIndex"),
                ("source_position", "sourcePosition"),
            ):
                if producer_key not in node:
                    continue
                if canonical_key in node and node.get(canonical_key) != node.get(producer_key):
                    raise ValueError(
                        f"layout node {parent_id or '<root>'} has conflicting {producer_key}/{canonical_key}"
                    )
                node[canonical_key] = deepcopy(node.get(producer_key))
                node.pop(producer_key, None)
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
            label = next(
                (
                    value.strip()
                    for value in (
                        node.get("title"),
                        node.get("string"),
                        node.get("label"),
                    )
                    if isinstance(value, str) and value.strip()
                ),
                "",
            )
            node["title"] = label
            span = node.get("span")
            node["span"] = span if isinstance(span, int) and not isinstance(span, bool) and 1 <= span <= 24 else 24
            if "widgetList" in node and not isinstance(node.get("widgetList"), list):
                raise ValueError(f"layout node {container_id} widgetList must be an array")
            node.setdefault("widgetList", [])
            child_carriers: list[tuple[str, list[Any]]] = []
            for key in _CONTAINER_CHILD_KEYS:
                if key in node and not isinstance(node.get(key), list):
                    raise ValueError(f"layout node {container_id} {key} must be an array")
                rows = node.get(key) if isinstance(node.get(key), list) else []
                if rows:
                    child_carriers.append((key, rows))
            if len(child_carriers) > 1:
                carriers = ",".join(key for key, _rows in child_carriers)
                raise ValueError(
                    f"layout node {container_id} has ambiguous parallel child carriers: {carriers}"
                )
            canonical_children = child_carriers[0][1] if child_carriers else []
            node["children"] = normalize(canonical_children, container_id)
            for key in _CONTAINER_CHILD_KEYS[1:]:
                node.pop(key, None)

            direct_field_owners: dict[str, list[dict[str, Any]]] = {}
            for child in node["children"]:
                if not isinstance(child, dict):
                    continue
                child_type = str(child.get("containerType") or child.get("type") or "").strip().lower()
                child_widget_id = str(child.get("widgetId") or "").strip()
                if child_type == "field" and child_widget_id:
                    direct_field_owners.setdefault(child_widget_id, []).append(child)
            normalized_widgets: list[dict[str, Any]] = []
            for widget_index, raw_widget in enumerate(node["widgetList"]):
                if not isinstance(raw_widget, dict):
                    raise ValueError(
                        f"layout node {container_id} widgetList[{widget_index}] must be an object"
                    )
                widget = raw_widget
                widget_id = str(widget.get("widgetId") or "").strip()
                if not widget_id:
                    raise ValueError(
                        f"layout node {container_id} widgetList[{widget_index}].widgetId is required"
                    )
                owner_matches = direct_field_owners.get(widget_id, [])
                if len(owner_matches) > 1:
                    raise ValueError(f"widget {widget_id} has ambiguous direct field owners")
                owner = owner_matches[0] if owner_matches else node
                owner_id = str(owner.get("containerId") or "").strip()
                existing_owner = str(widget.get("ownerContainerId") or "").strip()
                if existing_owner and existing_owner != owner_id:
                    raise ValueError(
                        f"widget {widget_id} owner conflicts: {existing_owner} != {owner_id}"
                    )
                widget["ownerContainerId"] = owner_id
                for source_key, widget_key in (
                    ("nativeLocator", "nativeLocator"),
                    ("occurrenceIndex", "occurrenceIndex"),
                    ("sourcePosition", "sourcePosition"),
                    ("formStructureRole", "formStructureRole"),
                ):
                    if source_key in owner and widget_key not in widget:
                        widget[widget_key] = deepcopy(owner.get(source_key))
                normalized_widgets.append(widget)
            node["widgetList"] = normalized_widgets
            if container_id not in status_ids:
                container_status.append({"containerId": container_id, "visible": True, "disabled": False})
                status_ids.add(container_id)
            out.append(node)
        return out

    normalized = normalize(container_tree, "")
    widget_owners: dict[str, str] = {}

    def validate_widget_owners(nodes: list[Any]) -> None:
        for node in nodes:
            if not isinstance(node, dict):
                continue
            for widget in node.get("widgetList") if isinstance(node.get("widgetList"), list) else []:
                widget_id = str(widget.get("widgetId") or "").strip() if isinstance(widget, dict) else ""
                owner_id = str(widget.get("ownerContainerId") or "").strip() if isinstance(widget, dict) else ""
                if widget_id in widget_owners:
                    raise ValueError(f"duplicate layout widgetId: {widget_id}")
                widget_owners[widget_id] = owner_id
            validate_widget_owners(node.get("children") if isinstance(node.get("children"), list) else [])

    validate_widget_owners(normalized)
    status_contract["containerStatus"] = container_status
    contract["statusContract"] = status_contract
    return normalized


def normalize_final_layout_contract(contract: dict[str, Any]) -> None:
    """Normalize and persist the final layout through the projection boundary."""
    if not isinstance(contract, dict):
        return
    layout = contract.get("layoutContract") if isinstance(contract.get("layoutContract"), dict) else {}
    container_tree = layout.get("containerTree") if isinstance(layout.get("containerTree"), list) else []
    set_v2_container_tree(contract, normalize_post_projected_container_tree(contract, container_tree))


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
    layout_contract = contract_v2.get("layoutContract") if isinstance(contract_v2.get("layoutContract"), dict) else {}
    native_form = str(layout_contract.get("layoutType") or "").strip().lower() == "form"
    form_widgets_by_field: dict[str, list[str]] = {}

    def collect_form_widgets(value: Any) -> None:
        if isinstance(value, list):
            for item in value:
                collect_form_widgets(item)
            return
        if not isinstance(value, dict):
            return
        node_type = str(value.get("containerType") or value.get("type") or "").strip().lower()
        if node_type == "field":
            field_code = str(value.get("fieldCode") or value.get("name") or value.get("field") or "").strip()
            widget_id = str(value.get("widgetId") or value.get("containerId") or "").strip()
            if field_code and widget_id:
                form_widgets_by_field.setdefault(field_code, []).append(widget_id)
        for key in ("children", "pages", "tabs", "nodes", "items"):
            collect_form_widgets(value.get(key))

    if native_form:
        collect_form_widgets(layout_contract.get("containerTree"))
        owned_widget_ids = {
            widget_id
            for widget_ids in form_widgets_by_field.values()
            for widget_id in widget_ids
        }
        widget_status = [
            row
            for row in widget_status
            if isinstance(row, dict) and str(row.get("widgetId") or "").strip() in owned_widget_ids
        ]
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
        if native_form:
            rows = [
                row
                for occurrence_widget_id in form_widgets_by_field.get(field_code, [])
                for row in by_widget.get(occurrence_widget_id, [])
            ]
        else:
            rows = by_widget.get(widget_id)
        if not rows:
            if native_form:
                continue
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

    widget_visibility: dict[str, bool] = {}

    def walk(rows: list[Any]) -> None:
        for row in rows:
            if not isinstance(row, dict):
                continue
            node_type = str(row.get("type") or row.get("containerType") or "").strip().lower()
            if node_type == "field":
                widget_id = str(row.get("widgetId") or "").strip()
                if not widget_id:
                    field_name = str(row.get("name") or row.get("field") or "").strip()
                    widget_id = f"field.{field_name}" if field_name else ""
                if widget_id:
                    widget_visibility[widget_id] = not node_invisible(row)
            for key in ("children", "pages", "tabs", "nodes", "items"):
                children = row.get(key)
                if isinstance(children, list):
                    walk(children)

    walk(container_tree)
    if not widget_visibility:
        return
    status_contract = contract_v2.get("statusContract") if isinstance(contract_v2.get("statusContract"), dict) else {}
    widget_status = status_contract.get("widgetStatus") if isinstance(status_contract.get("widgetStatus"), list) else []
    seen: set[str] = set()
    for row in widget_status:
        if not isinstance(row, dict):
            continue
        widget_id = str(row.get("widgetId") or "").strip()
        if widget_id not in widget_visibility:
            continue
        seen.add(widget_id)
        if not widget_visibility[widget_id]:
            row["visible"] = False
            row["auth"] = "none"
        else:
            row["visible"] = True
        if widget_visibility[widget_id] and row.get("readonly") is True:
            row["auth"] = "read"
        elif widget_visibility[widget_id] and row.get("disabled") is not True:
            row["auth"] = "edit"
    for widget_id in sorted(set(widget_visibility) - seen):
        visible = widget_visibility[widget_id]
        widget_status.append({
            "widgetId": widget_id,
            "visible": visible,
            "readonly": False,
            "required": False,
            "disabled": False,
            "auth": "edit" if visible else "none",
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
    structure = contract.get("formStructureContract") if isinstance(contract.get("formStructureContract"), dict) else {}
    contract_field_roles = (
        structure.get("fieldRoles")
        if isinstance(structure.get("fieldRoles"), dict)
        else {}
    )
    field_semantic_roles = {
        str(name): str(role).strip().lower()
        for name, role in (
            governance.get("field_semantic_roles")
            if isinstance(governance.get("field_semantic_roles"), dict)
            else {}
        ).items()
        if str(name).strip() and str(role).strip()
    }
    def node_field_name(node: Any) -> str:
        if not isinstance(node, dict):
            return ""
        return str(node.get("name") or node.get("field") or node.get("fieldCode") or "").strip()

    def apply_product_field_roles(nodes: Any) -> None:
        for node in nodes if isinstance(nodes, list) else []:
            if not isinstance(node, dict):
                continue
            name = node_field_name(node)
            role = field_semantic_roles.get(name)
            existing_role = (
                node.get("formStructureRole")
                if isinstance(node.get("formStructureRole"), dict)
                else {}
            )
            authority_role = (
                contract_field_roles.get(name)
                if isinstance(contract_field_roles.get(name), dict)
                else {}
            )
            if role and authority_role:
                # Slot/group remain the normalized structure authority, while
                # the governed semantic anchor owns the canonical product
                # role. Persist their merge in both carriers so the final wire
                # never exposes a node/fieldRoles split authority.
                merged_role = {**authority_role, "role": role}
                contract_field_roles[name] = deepcopy(merged_role)
                if existing_role:
                    node["formStructureRole"] = deepcopy(merged_role)
            for key in (*_CONTAINER_CHILD_KEYS, "widgetList"):
                apply_product_field_roles(node.get(key))

    apply_product_field_roles(container_tree)
    # Product intent may annotate native nodes, but it must not use field lists
    # to move them, manufacture groups, infer relation regions, or normalize
    # the tree a second time.  The effective parsed Odoo view is the structural
    # authority and has already been normalized by the assembler.
    return
