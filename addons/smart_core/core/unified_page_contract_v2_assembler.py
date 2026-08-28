# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
import time
from copy import deepcopy
from typing import Any

from .contract_lifecycle import payload_sha256, seal_unified_page_contract
from .source_authority import build_source_authority_contract
from .unified_page_contract_v2_permissions import permission_auth_level, resolve_permission_rights
from .unified_page_contract_v2_runtime_actions import normalize_runtime_business_actions
from .unified_page_contract_v2_action import normalize_target_scope, normalize_trigger_type
from .unified_page_contract_v2_form_structure import normalize_form_structure_contract_roles

CONTRACT_VERSION = "2.2.0"
SOURCE_KIND = "unified_page_contract_v2_assembler_projection"
SOURCE_AUTHORITIES = ("ui_contract", "page_orchestration", "scene_contract", "unified_page_contract_v2_schema")
NO_BUSINESS_FACT_AUTHORITY = True
TRACE_FIELD_TOKENS = ("legacy", "source", "origin", "external", "import", "migration", "trace", "old_")
NOTE_FIELD_TOKENS = ("note", "remark", "description", "memo", "comment", "说明", "备注")
_KANBAN_ROW_ACTION_REGISTRY: dict[tuple[str, str], dict[str, Any]] = {}


def source_authority_contract() -> dict[str, Any]:
    return build_source_authority_contract(
        kind=SOURCE_KIND,
        authorities=SOURCE_AUTHORITIES,
        no_business_fact_authority=NO_BUSINESS_FACT_AUTHORITY,
        runtime_carrier="unified_page_contract_v2_assembler",
    )

PATCH_VERSION = "2.2.0"
STABLE_CLIENT_TYPES = {"web_pc", "wx_mini", "harmony_h5"}


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _validated_activity_projection(collection_view: Any) -> dict[str, Any]:
    if not isinstance(collection_view, dict):
        raise ValueError("native Activity view carrier must be an object")
    native_activity = collection_view.get("activity")
    if not isinstance(native_activity, dict) or not native_activity:
        raise ValueError("native Activity projection is required")
    for key in ("field_occurrences", "node_occurrences", "actions"):
        rows = native_activity.get(key)
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise ValueError(f"native Activity {key} must be an object array")
    for key in ("native_attrs", "template"):
        if not isinstance(native_activity.get(key), dict) or not native_activity.get(key):
            raise ValueError(f"native Activity {key} is required")
    if not native_activity["field_occurrences"] or not native_activity["node_occurrences"]:
        raise ValueError("native Activity occurrence evidence is required")
    template = native_activity["template"]
    if not isinstance(template.get("nodes"), list) or not template.get("nodes"):
        raise ValueError("native Activity template nodes are required")

    def occurrence_identity(row: dict[str, Any], *, tag: str = "") -> tuple[Any, ...]:
        return (
            tag or row.get("tag"), row.get("native_locator"), row.get("occurrence_index"),
            row.get("source_position"), row.get("attributes"), row.get("text", ""), row.get("tail", ""),
        )

    node_by_locator: dict[str, dict[str, Any]] = {}
    source_positions: set[int] = set()
    for row in native_activity["node_occurrences"]:
        locator = _text(row.get("native_locator"))
        position = row.get("source_position")
        if (not locator or locator in node_by_locator or not _text(row.get("tag"))
                or not isinstance(row.get("occurrence_index"), int) or row["occurrence_index"] < 1
                or not isinstance(position, int) or position < 0 or position in source_positions
                or not isinstance(row.get("attributes"), dict)):
            raise ValueError("native Activity node occurrence identity is invalid")
        node_by_locator[locator] = row
        source_positions.add(position)

    for row in native_activity["field_occurrences"]:
        locator = _text(row.get("native_locator"))
        node = node_by_locator.get(locator)
        if (not node or occurrence_identity(row, tag="field") != occurrence_identity(node)
                or _text(row.get("name")) != _text(_dict(node.get("attributes")).get("name"))):
            raise ValueError("native Activity field occurrence evidence mismatch")

    def validate_template_nodes(rows: list[Any]) -> None:
        discovered_names: list[str] = []
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("native Activity template node must be an object")
            node = node_by_locator.get(_text(row.get("native_locator")))
            if not node or occurrence_identity(row) != occurrence_identity(node):
                raise ValueError("native Activity template occurrence evidence mismatch")
            template_name = _text(_dict(row.get("attributes")).get("t-name"))
            if template_name:
                discovered_names.append(template_name)
            children = row.get("children", [])
            if not isinstance(children, list):
                raise ValueError("native Activity template children must be an array")
            discovered_names.extend(validate_template_nodes(children))
        return discovered_names

    template_root = node_by_locator.get(_text(template.get("native_locator")))
    if (not template_root or _text(template_root.get("tag")) != "templates"
            or template.get("occurrence_index") != template_root.get("occurrence_index")):
        raise ValueError("native Activity template root evidence mismatch")
    discovered_names = validate_template_nodes(template["nodes"])
    if template.get("names") != discovered_names:
        raise ValueError("native Activity template names evidence mismatch")

    valid_button_nodes = {
        locator: row for locator, row in node_by_locator.items()
        if _text(row.get("tag")) == "button"
        and _text(_dict(row.get("attributes")).get("name"))
        and _text(_dict(row.get("attributes")).get("type")).lower() in {"object", "action"}
    }
    action_by_locator: dict[str, dict[str, Any]] = {}
    for action in native_activity["actions"]:
        locator = _text(action.get("native_locator"))
        node = valid_button_nodes.get(locator)
        attributes = _dict(node.get("attributes")) if node else {}
        expected_identity = {
            "authoritative": True, "canonical_region": "activity.actions",
            "native_locator": locator, "occurrence_index": node.get("occurrence_index") if node else None,
            "type": _text(attributes.get("type")).lower(), "name": _text(attributes.get("name")),
            "id": attributes.get("id") or "", "context_raw": attributes.get("context") or "",
            "domain_raw": attributes.get("domain") or "", "confirm": attributes.get("confirm") or "",
            "special": attributes.get("special") or "", "data_hotkey": attributes.get("data-hotkey") or "",
        }
        if (not node or locator in action_by_locator
                or action.get("occurrence_index") != node.get("occurrence_index")
                or action.get("source_position") != node.get("source_position")
                or action.get("attributes") != attributes
                or _text(action.get("name")) != expected_identity["name"]
                or _text(action.get("type")).lower() != expected_identity["type"]
                or action.get("native_identity") != expected_identity):
            raise ValueError("native Activity action occurrence evidence mismatch")
        action_by_locator[locator] = action
    if set(action_by_locator) != set(valid_button_nodes):
        raise ValueError("native Activity action occurrence parity mismatch")
    return native_activity


def _text(value: Any, default: str = "") -> str:
    text = str(value or "").strip()
    return text or default


def _has_action_constraint_value(value: Any) -> bool:
    if isinstance(value, (list, tuple, set)):
        return any(_text(item) for item in value)
    return value not in (None, "", False)


def register_kanban_row_action(model_name: str, action: dict[str, Any], *, view_type: str = "kanban") -> None:
    model = _text(model_name)
    view = _text(view_type, "kanban")
    if model and isinstance(action, dict):
        _KANBAN_ROW_ACTION_REGISTRY[(model, view)] = deepcopy(action)


def _formal_container_type(value: Any, default: str = "section") -> str:
    node_type = _text(value, default).lower()
    return "section" if node_type == "sheet" else node_type


def _stable_id(value: Any, fallback: str) -> str:
    raw = _text(value, fallback)
    out = []
    for char in raw:
        if char.isalnum() or char in "_.:-":
            out.append(char)
        elif char in " /":
            out.append(".")
    normalized = "".join(out).strip(".")
    if not normalized:
        normalized = fallback
    if not normalized[0].isalpha():
        normalized = f"id.{normalized}"
    return normalized


def _fingerprint(value: Any) -> str:
    return payload_sha256(value)[:16]


def _resolve_source_type(source: dict[str, Any], explicit: str = "") -> str:
    if explicit:
        return explicit
    if _dict(source.get("scene_contract")):
        return "scene_contract"
    if _dict(source.get("page_orchestration")):
        return "page_orchestration"
    if "meta_fields" in source or source.get("view_type"):
        return "ui.contract"
    if "patch" in source or "modifiers_patch" in source:
        return "api.onchange"
    if _dict(source.get("page")) and _list(source.get("zones")):
        return "page_orchestration"
    if _dict(source.get("identity")) and _dict(source.get("page")):
        return "scene_contract"
    return "unknown"


def _component_key(widget_type: str, field: dict[str, Any] | None = None) -> str:
    normalized = _text(widget_type).lower()
    descriptor = _dict(field)
    field_type = _text(descriptor.get("ttype") or descriptor.get("type")).lower()
    relation = _text(descriptor.get("relation")).lower()
    if field_type == "monetary" or normalized == "monetary":
        return "sc.value.money"
    if normalized in {"percentage", "percentpie"}:
        return "sc.value.percentage"
    if normalized == "float_time":
        return "sc.value.duration"
    if normalized == "statusbar":
        return "sc.display.status"
    if field_type == "many2one" and relation == "res.currency":
        return "sc.value.currency"
    if field_type == "many2one" and relation == "res.users":
        return "sc.value.user"
    if field_type == "many2one" and relation == "res.company":
        return "sc.value.company"
    if field_type == "many2one" or normalized.endswith("many2one"):
        return "sc.relation.many2one"
    if field_type == "many2many" and normalized != "many2many_tags":
        return "sc.relation.many2many"
    if field_type == "one2many":
        return "sc.relation.table"
    mapping = {
        "input": "sc.input.text",
        "binary": "sc.input.binary",
        "textarea": "sc.input.textarea",
        "number": "sc.input.number",
        "select": "sc.select.remote",
        "checkbox": "sc.input.boolean",
        "date": "sc.input.date",
        "datetime": "sc.input.datetime",
        "table": "sc.table.data",
        "tree": "sc.tree.data",
        "many2many_tags": "sc.select.tags",
        "button": "sc.button.action",
        "display": "sc.display.text",
    }
    return mapping.get(widget_type, "sc.display.text")


def _widget_type_from_field(field: dict[str, Any]) -> str:
    ttype = _text(field.get("ttype") or field.get("type")).lower()
    if ttype in {"selection", "many2one"}:
        return "select"
    if ttype in {"date", "datetime"}:
        return ttype
    if ttype in {"integer", "float", "monetary"}:
        return "number"
    if ttype in {"one2many", "many2many"}:
        widget_options = _dict(field.get("widget_options") or field.get("options"))
        if ttype == "many2many" and widget_options.get("color_field"):
            return "many2many_tags"
        return "table"
    if ttype in {"text", "html"}:
        return "textarea"
    if ttype in {"boolean"}:
        return "checkbox"
    if ttype == "binary":
        return "binary"
    return "input"


CANONICAL_WIDGET_TYPES = frozenset({
    "input", "select", "date", "datetime", "number", "table", "upload", "button",
    "textarea", "checkbox", "radio", "tree", "gantt", "relation", "display", "binary",
    "many2many_tags",
})

NATIVE_WIDGET_TYPE_ALIASES = {
    "selection": "select",
    "many2one": "select",
    "many2many": "table",
    "one2many": "table",
    "one2many_list": "table",
    "boolean": "checkbox",
    "boolean_toggle": "checkbox",
    "monetary": "number",
    "float_time": "number",
    "percentage": "number",
    "percentpie": "number",
    "statusbar": "display",
    "image": "binary",
    "html": "textarea",
    "handle": "number",
    "phone": "input",
    "url": "input",
    "email": "input",
}


def _canonical_widget_type(native_widget: str, field: dict[str, Any]) -> str:
    normalized = _text(native_widget).lower()
    if normalized in CANONICAL_WIDGET_TYPES:
        return normalized
    if normalized in NATIVE_WIDGET_TYPE_ALIASES:
        return NATIVE_WIDGET_TYPE_ALIASES[normalized]
    return _widget_type_from_field(field)


def _component_registry(component_keys: set[str]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for key in sorted(component_keys):
        out[key] = {
            "version": "1.0",
            "adapter": {
                "web_pc": _adapter_for(key, "web_pc"),
                "wx_mini": _adapter_for(key, "wx_mini"),
                "harmony_h5": _adapter_for(key, "harmony_h5"),
            },
        }
    return out


def _adapter_for(component_key: str, client_type: str) -> str:
    prefix = {"web_pc": "El", "wx_mini": "Wx", "harmony_h5": "H5"}.get(client_type, "H5")
    if "table" in component_key:
        return f"{prefix}Table"
    if "tree" in component_key:
        return f"{prefix}Tree"
    if "select" in component_key:
        return f"{prefix}Select"
    if "button" in component_key:
        return f"{prefix}Button"
    return f"{prefix}Input"


def _base_contract(
    *,
    page_id: str,
    scene_key: str,
    page_name: str,
    model: str,
    view_type: str,
    layout_type: str,
    client_type: str,
    source_type: str,
    source_payload: dict[str, Any],
    request_id: str,
) -> dict[str, Any]:
    client = client_type if client_type in STABLE_CLIENT_TYPES else "web_pc"
    fp = _fingerprint(source_payload)
    return {
        "pageInfo": {
            "pageId": _stable_id(page_id, "page.generated"),
            "sceneKey": _stable_id(scene_key, _stable_id(page_id, "scene.generated")),
            "pageName": page_name or page_id,
            "model": model,
            "viewType": view_type,
            "layoutType": layout_type,
            "renderMode": "governed",
            "contractVersion": CONTRACT_VERSION,
            "clientType": client,
        },
        "layoutContract": {
            "pageId": _stable_id(page_id, "page.generated"),
            "layoutType": layout_type,
            "adaptMode": "pc" if client == "web_pc" else "mobile",
            "containerTree": [],
            "layoutHints": {},
            "listProfile": {},
            "componentRegistry": {},
        },
        "statusContract": {
            "globalStatus": {"pageVisible": True, "pageAuth": "read"},
            "containerStatus": [],
            "widgetStatus": [],
            "buttonStatus": [],
            "selectorStatus": [],
        },
        "actionContract": {
            "actionRuleList": [],
            "dependencyGraph": {},
            "deletePolicy": {},
            "surfacePolicies": {},
        },
        "dataContract": {
            "mainData": {},
            "tableRows": {},
            "relationRows": {},
            "dictData": {},
            "pagination": {},
            "dataSource": {},
            "dataMeta": {},
        },
        "runtimeContract": {
            "patchStrategy": "incremental",
            "cachePolicy": "etag",
            "optimistic": False,
            "lazyContainer": [],
            "virtualization": {},
            "retryPolicy": {"maxRetries": 1},
        },
        "meta": {
            "etag": f"upc-v2-{fp}",
            "snapshotId": f"snapshot.upc.v2.{fp}",
            "traceId": f"trace.upc.v2.{fp}",
            "requestId": _stable_id(request_id, f"request.upc.v2.{fp}"),
            "sourceType": source_type,
        },
    }


def _finalize_layout_dsl(contract: dict[str, Any]) -> None:
    layout = _dict(contract.get("layoutContract"))
    roots = layout.get("containerTree")
    if not isinstance(roots, list):
        raise ValueError("layoutContract.containerTree must be an array")
    container_ids: set[str] = set()
    widget_owners: dict[str, str] = {}

    def normalize(nodes: list[Any], path: str) -> None:
        for index, node in enumerate(nodes):
            if not isinstance(node, dict):
                raise ValueError(f"{path}[{index}] must be an object")
            node_path = f"{path}[{index}]"
            container_id = _text(
                node.get("containerId")
                or node.get("widgetId")
                or node.get("nativeLocator")
                or node.get("name")
            )
            if not container_id:
                raise ValueError(f"{node_path}.containerId is required")
            node["containerId"] = container_id
            if container_id in container_ids:
                raise ValueError(f"duplicate layout containerId: {container_id}")
            container_ids.add(container_id)
            child_carriers: list[tuple[str, list[Any]]] = []
            for key in ("children", "pages", "tabs", "nodes", "items"):
                if key in node and not isinstance(node.get(key), list):
                    raise ValueError(f"{node_path}.{key} must be an array")
                rows = node.get(key) if isinstance(node.get(key), list) else []
                if rows:
                    child_carriers.append((key, rows))
            if len(child_carriers) > 1:
                carriers = ",".join(key for key, _rows in child_carriers)
                raise ValueError(f"{node_path} has ambiguous parallel child carriers: {carriers}")
            node["children"] = child_carriers[0][1] if child_carriers else []
            for legacy_key in ("pages", "tabs", "nodes", "items"):
                node.pop(legacy_key, None)
            if "widgetList" in node and not isinstance(node.get("widgetList"), list):
                raise ValueError(f"{node_path}.widgetList must be an array")
            node.setdefault("widgetList", [])
            normalize(node["children"], f"{node_path}.children")

    def bind_owners(nodes: list[Any], path: str) -> None:
        for index, node in enumerate(nodes):
            if not isinstance(node, dict):
                continue
            node_path = f"{path}[{index}]"
            child_owners: dict[str, list[dict[str, Any]]] = {}
            for child in _list(node.get("children")):
                if not isinstance(child, dict):
                    continue
                if _text(child.get("containerType") or child.get("type")).lower() != "field":
                    continue
                child_widget_id = _text(child.get("widgetId"))
                if child_widget_id:
                    child_owners.setdefault(child_widget_id, []).append(child)
            for widget_index, widget in enumerate(_list(node.get("widgetList"))):
                if not isinstance(widget, dict):
                    raise ValueError(f"{node_path}.widgetList[{widget_index}] must be an object")
                widget_id = _text(widget.get("widgetId"))
                if not widget_id:
                    raise ValueError(f"{node_path}.widgetList[{widget_index}].widgetId is required")
                matches = child_owners.get(widget_id, [])
                if len(matches) > 1:
                    raise ValueError(f"widget {widget_id} has ambiguous field owners")
                owner = matches[0] if matches else node
                owner_id = _text(owner.get("containerId"))
                existing_owner = _text(widget.get("ownerContainerId"))
                if existing_owner and existing_owner != owner_id:
                    raise ValueError(f"widget {widget_id} owner conflicts: {existing_owner} != {owner_id}")
                if widget_id in widget_owners:
                    raise ValueError(f"duplicate layout widgetId: {widget_id}")
                widget_owners[widget_id] = owner_id
                widget["ownerContainerId"] = owner_id
                for source_name in (
                    "nativeLocator", "occurrenceIndex", "sourcePosition", "formStructureRole",
                ):
                    if source_name in owner and source_name not in widget:
                        widget[source_name] = deepcopy(owner.get(source_name))
            bind_owners(_list(node.get("children")), f"{node_path}.children")

    normalize(roots, "layoutContract.containerTree")
    bind_owners(roots, "layoutContract.containerTree")
    layout["containerTree"] = roots
    contract["layoutContract"] = layout


def assemble_unified_page_contract_v2(
    source_contract: dict[str, Any],
    *,
    source_type: str = "",
    client_type: str = "web_pc",
    request_id: str = "request.upc.v2.assembler",
    trace_id: str = "",
    stage_timings: dict[str, int] | None = None,
) -> dict[str, Any]:
    started_at = time.monotonic()
    source = _dict(source_contract)
    resolved = _resolve_source_type(source, source_type)
    payload = _extract_source_payload(source, resolved)
    if resolved == "scene_contract":
        contract = _assemble_scene_contract(payload, client_type=client_type, request_id=request_id)
    elif resolved == "page_orchestration":
        contract = _assemble_page_orchestration(payload, client_type=client_type, request_id=request_id)
    elif resolved == "ui.contract":
        contract = _assemble_ui_contract(
            source,
            client_type=client_type,
            request_id=request_id,
            source_type=resolved,
        )
    elif resolved == "native_form_projection":
        contract = _assemble_native_form_projection(
            source,
            client_type=client_type,
            request_id=request_id,
        )
    else:
        contract = _assemble_unknown(source, client_type=client_type, request_id=request_id)
    assembled_at = time.monotonic()
    _merge_action_rules_by_backend_identity(contract)
    _demote_native_inherited_actions_to_overflow(contract)
    actions_merged_at = time.monotonic()
    _bind_native_layout_action_references(contract)
    _finalize_layout_dsl(contract)
    actions_bound_at = time.monotonic()
    sealed = seal_unified_page_contract(
        contract,
        source_payload=payload if resolved not in {"ui.contract", "native_form_projection"} else source,
        source_type=resolved,
        request_id=request_id,
        trace_id=trace_id,
        client_type=client_type,
        stage="assembly",
        generator=SOURCE_KIND,
        generator_version=CONTRACT_VERSION,
        source_authority=source_authority_contract(),
    )
    if stage_timings is not None:
        stage_timings.update({
            "v2_source_assembly": int((assembled_at - started_at) * 1000),
            "v2_action_merge": int((actions_merged_at - assembled_at) * 1000),
            "v2_action_binding": int((actions_bound_at - actions_merged_at) * 1000),
            "v2_seal": int((time.monotonic() - actions_bound_at) * 1000),
        })
    return sealed


def assemble_unified_page_patch_v2(
    onchange_payload: dict[str, Any],
    *,
    action_id: str = "api.onchange.patch",
    request_id: str = "request.upc.v2.patch",
) -> dict[str, Any]:
    source = _dict(onchange_payload)
    data_patch = {}
    if _dict(source.get("patch")):
        data_patch["mainData"] = deepcopy(source.get("patch"))
    status_patch = {"widgetStatus": []}
    for field_name, modifiers in _dict(source.get("modifiers_patch")).items():
        row = {"widgetId": f"field.{_stable_id(field_name, 'field')}"}
        if isinstance(modifiers, dict):
            if "readonly" in modifiers:
                row["readonly"] = bool(modifiers.get("readonly"))
            if "required" in modifiers:
                row["required"] = bool(modifiers.get("required"))
            if "invisible" in modifiers:
                row["visible"] = not bool(modifiers.get("invisible"))
        status_patch["widgetStatus"].append(row)
    line_patches = _list(source.get("line_patches"))
    if line_patches:
        data_patch["relationRows"] = {"line_patches": deepcopy(line_patches)}
    fp = _fingerprint(source)
    return {
        "updateType": "partial",
        "layoutPatch": {},
        "statusPatch": status_patch,
        "dataPatch": data_patch,
        "runtimePatch": {},
        "meta": {
            "contractVersion": PATCH_VERSION,
            "etag": f"upc-v2-patch-{fp}",
            "snapshotId": f"snapshot.upc.v2.patch.{fp}",
            "traceId": f"trace.upc.v2.patch.{fp}",
            "requestId": _stable_id(request_id, f"request.upc.v2.patch.{fp}"),
            "actionId": _stable_id(action_id, "api.onchange.patch"),
            "sourceType": "api.onchange",
        },
    }


def _extract_source_payload(source: dict[str, Any], source_type: str) -> dict[str, Any]:
    if source_type == "scene_contract":
        return _dict(source.get("scene_contract")) or source
    if source_type == "page_orchestration":
        return _dict(source.get("page_orchestration")) or source
    return source


def _assemble_scene_contract(source: dict[str, Any], *, client_type: str, request_id: str) -> dict[str, Any]:
    identity = _dict(source.get("identity"))
    page = _dict(source.get("page"))
    state = _dict(source.get("state"))
    actions = _dict(source.get("actions"))
    page_id = _stable_id(identity.get("scene_key"), "scene.page")
    contract = _base_contract(
        page_id=page_id,
        scene_key=identity.get("scene_key") or page_id,
        page_name=_text(identity.get("title"), page_id),
        model="",
        view_type="combine",
        layout_type="combine",
        client_type=client_type,
        source_type="scene_contract",
        source_payload=source,
        request_id=request_id,
    )
    blocks = [item for item in _list(page.get("blocks")) if isinstance(item, dict)]
    widgets = []
    component_keys = set()
    for block in blocks:
        widget = _block_widget(block)
        widgets.append(widget)
        component_keys.add(widget["componentKey"])
        contract["statusContract"]["widgetStatus"].append(
            {
                "widgetId": widget["widgetId"],
                "visible": True,
                "readonly": True,
                "required": False,
                "disabled": False,
                "auth": "read",
            }
        )
    container_id = f"container.{page_id}.primary"
    contract["layoutContract"]["containerTree"] = [
        {
            "containerId": container_id,
            "containerType": "section",
            "title": _text(identity.get("title"), page_id),
            "span": 12,
            "styleToken": "sceneSection",
            "children": [],
            "widgetList": widgets,
        }
    ]
    contract["layoutContract"]["componentRegistry"] = _component_registry(component_keys or {"sc.display.text"})
    contract["statusContract"]["containerStatus"].append({"containerId": container_id, "visible": True, "disabled": False})
    contract["statusContract"]["globalStatus"]["reasonCode"] = _text(state.get("reason_code"), "SCENE_READY")
    _append_actions(contract, actions.get("primary_actions"), source_widget_id=widgets[0]["widgetId"] if widgets else "page.root")
    _append_actions(contract, actions.get("secondary_actions"), source_widget_id=widgets[0]["widgetId"] if widgets else "page.root")
    return contract


def _block_widget(block: dict[str, Any]) -> dict[str, Any]:
    block_key = _stable_id(block.get("key"), "block")
    return {
        "widgetId": f"block.{block_key}",
        "widgetType": "display",
        "fieldCode": block_key,
        "label": _text(block.get("title"), block_key),
        "span": 12,
        "componentKey": "sc.display.text",
        "capabilities": [],
        "componentConfig": {"blockType": _text(block.get("block_type"), "runtime_block")},
    }


def _assemble_page_orchestration(source: dict[str, Any], *, client_type: str, request_id: str) -> dict[str, Any]:
    page = _dict(source.get("page"))
    page_id = _stable_id(page.get("scene_key") or page.get("key"), "page.orchestration")
    contract = _base_contract(
        page_id=page_id,
        scene_key=page.get("scene_key") or page_id,
        page_name=_text(page.get("title"), page_id),
        model="",
        view_type="combine",
        layout_type="combine",
        client_type=client_type,
        source_type="page_orchestration",
        source_payload=source,
        request_id=request_id,
    )
    component_keys = set()
    containers = []
    for zone in _list(source.get("zones")):
        if not isinstance(zone, dict):
            continue
        container_id = f"zone.{_stable_id(zone.get('key'), 'zone')}"
        widgets = []
        for block in _list(zone.get("blocks")):
            if not isinstance(block, dict):
                continue
            widget = _block_widget(block)
            widgets.append(widget)
            component_keys.add(widget["componentKey"])
            contract["statusContract"]["widgetStatus"].append(
                {
                    "widgetId": widget["widgetId"],
                    "visible": True,
                    "readonly": True,
                    "required": False,
                    "disabled": False,
                    "auth": "read",
                }
            )
        containers.append(
            {
                "containerId": container_id,
                "containerType": "section",
                "title": _text(zone.get("title"), container_id),
                "span": 12,
                "styleToken": _text(zone.get("display_mode"), "zone"),
                "children": [],
                "widgetList": widgets,
            }
        )
        contract["statusContract"]["containerStatus"].append({"containerId": container_id, "visible": True, "disabled": False})
    contract["layoutContract"]["containerTree"] = containers
    contract["layoutContract"]["componentRegistry"] = _component_registry(component_keys or {"sc.display.text"})
    contract["dataContract"]["dataSource"] = deepcopy(_dict(source.get("data_sources")))
    action_schema = _dict(source.get("action_schema")).get("actions")
    _append_action_schema(contract, _dict(action_schema), source_widget_id="page.root")
    return contract


def _assemble_ui_contract(
    source: dict[str, Any],
    *,
    client_type: str,
    request_id: str,
    source_type: str = "ui.contract",
) -> dict[str, Any]:
    ui = _dict(source)
    head = _dict(source.get("head") or ui.get("head"))
    model = _text(source.get("model") or ui.get("model"))
    view_type = _text(source.get("view_type") or ui.get("view_type"), "form")
    record_id = _positive_int(source.get("record_id") or source.get("recordId") or ui.get("record_id") or ui.get("recordId"), 0)
    collection_layout_types = {
        "form", "kanban", "pivot", "graph", "calendar", "gantt", "activity", "dashboard"
    }
    layout_type = "table" if view_type in {"tree", "list"} else view_type if view_type in collection_layout_types else "form"
    page_id = _stable_id(f"{model}.{view_type}" if model else f"ui.{view_type}", "ui.contract")
    contract = _base_contract(
        page_id=page_id,
        scene_key=page_id,
        page_name=_text(ui.get("title") or source.get("title") or head.get("title") or source.get("case"), page_id),
        model=model,
        view_type="list" if view_type == "tree" else view_type,
        layout_type=layout_type,
        client_type=client_type,
        source_type=source_type,
        source_payload=source,
        request_id=request_id,
    )
    fields = _field_rows(source, ui, view_type=view_type)
    source_context = _ui_source_context(_dict(source), _dict(ui))
    render_profile = _text(source_context.get("renderProfile")).lower()
    source_context_context = _dict(source_context.get("context"))
    form_modifier_record = {
        **source_context_context,
        **deepcopy(_dict(source.get("record"))),
    }
    raw_field_map = _dict(ui.get("fields") or source.get("fields"))
    fields_by_name: dict[str, dict[str, Any]] = {}
    for key, value in raw_field_map.items():
        if not isinstance(value, dict):
            continue
        name = _text(key or value.get("name"))
        if not name:
            continue
        fields_by_name[name] = deepcopy(value)
        fields_by_name[name].setdefault("name", name)
    for row in fields:
        if not isinstance(row, dict):
            continue
        name = _text(row.get("name"))
        if not name:
            continue
        fields_by_name[name] = {
            **fields_by_name.get(name, {}),
            **deepcopy(row),
        }
        fields_by_name[name].setdefault("name", name)
    widgets = []
    component_keys = set()
    form_layout = _dict(_dict(ui.get("views")).get("form"))
    for field_name, modifiers in _dict(form_layout.get("field_modifiers")).items():
        if not isinstance(modifiers, dict):
            continue
        normalized_name = _text(field_name)
        if not normalized_name:
            continue
        field_source = fields_by_name.setdefault(normalized_name, {"name": normalized_name})
        for key in ("readonly", "required", "invisible", "column_invisible"):
            if key in modifiers and key not in field_source:
                field_source[key] = deepcopy(modifiers.get(key))
    layout_rows = form_layout.get("layout") if isinstance(form_layout.get("layout"), list) else []
    native_layout_rows = [row for row in layout_rows if isinstance(row, dict)]
    if not any(_text(row.get("type") or row.get("kind")).lower() == "header" for row in native_layout_rows):
        header_buttons = []
        for button_source in (form_layout.get("header_buttons"), source.get("header_buttons")):
            if isinstance(button_source, list):
                header_buttons.extend(button_source)
        button_children = []
        for button in header_buttons:
            if not isinstance(button, dict):
                continue
            button_name = _text(button.get("name") or button.get("method") or _dict(button.get("payload")).get("method"))
            if not button_name:
                continue
            button_label = _text(button.get("label") or button.get("string") or button_name, button_name)
            button_kind = _text(button.get("kind") or _dict(button.get("payload")).get("type"), "object")
            button_children.append({
                "type": "button",
                "name": button_name,
                "label": button_label,
                "string": button_label,
                "buttonType": button_kind,
                "action": deepcopy(button),
            })
        if button_children:
            native_layout_rows.insert(0, {
                "type": "header",
                "children": button_children,
                "sourceAuthority": {
                    "kind": SOURCE_KIND,
                    "runtime_carrier": "ui_contract_form_header_buttons",
                    "no_business_fact_authority": True,
                },
            })
    form_subviews = _dict(form_layout.get("subviews"))
    form_structure_contract = deepcopy(
        _dict(source.get("formStructureContract") or source.get("form_structure_contract"))
    )
    if form_structure_contract:
        normalize_form_structure_contract_roles(form_structure_contract)
    form_structure_applied = False
    if layout_type == "form" and native_layout_rows:
        native_widget_status: list[dict[str, Any]] = []
        container_tree = _normalize_native_layout_nodes(
            native_layout_rows,
            fields_by_name,
            layout_type=layout_type,
            form_subviews=form_subviews,
            component_keys=component_keys,
            container_status=contract["statusContract"]["containerStatus"],
            widget_status=native_widget_status,
            context=form_modifier_record,
        )
        # A native Form is occurrence-authoritative.  Name-level status rows
        # built from the compatibility field map have no layout owner and
        # must not survive beside the exact occurrence rows.
        contract["statusContract"]["widgetStatus"] = native_widget_status
        if form_structure_contract:
            form_structure_contract = _project_form_structure_to_layout(
                form_structure_contract,
                container_tree,
                set(fields_by_name),
            )
            _apply_form_structure_roles_to_tree(container_tree, form_structure_contract)
            form_structure_applied = True
    elif layout_type == "form":
        container_id = "main.form"
        sheet_id = f"{container_id}.sheet"
        group_id = f"{container_id}.group"
        field_nodes = [
            _native_field_node(
                {"type": "field", "name": _text(field.get("name"), "")},
                _dict(field),
                layout_type=layout_type,
            )
            for field in fields[:60]
            if _text(field.get("name"))
        ]
        container_tree = [
            {
                "type": "sheet",
                "name": sheet_id,
                "containerId": sheet_id,
                "containerType": _formal_container_type("sheet"),
                "string": contract["pageInfo"]["pageName"],
                "label": contract["pageInfo"]["pageName"],
                "span": 12,
                "children": [
                    {
                        "type": "group",
                        "name": group_id,
                        "containerId": group_id,
                        "containerType": "group",
                        "string": contract["pageInfo"]["pageName"],
                        "label": contract["pageInfo"]["pageName"],
                        "children": field_nodes,
                        "widgetList": [
                            _field_widget(_dict(field), layout_type=layout_type)
                            for field in fields[:60]
                            if _text(field.get("name"))
                        ],
                    }
                ],
                "widgetList": [],
            }
        ]
        for widget in container_tree[0]["children"][0]["widgetList"]:
            component_keys.add(widget["componentKey"])
            contract["statusContract"]["widgetStatus"].append(_field_status(
                next((row for row in fields if _text(row.get("name")) == _text(widget.get("fieldCode"))), {}),
                widget["widgetId"],
            ))
        contract["statusContract"]["containerStatus"].extend([
            {"containerId": sheet_id, "visible": True, "disabled": False},
            {"containerId": group_id, "visible": True, "disabled": False},
        ])
        if form_structure_contract:
            form_structure_contract = _project_form_structure_to_layout(
                form_structure_contract,
                container_tree,
                set(fields_by_name),
            )
            _apply_form_structure_roles_to_tree(container_tree, form_structure_contract)
            form_structure_applied = True
    else:
        container_id = "main.table"
        widgets = []
        for field in fields[:60]:
            widget = _field_widget(field, layout_type=layout_type)
            widgets.append(widget)
            component_keys.add(widget["componentKey"])
            contract["statusContract"]["widgetStatus"].append(_field_status(field, widget["widgetId"]))
        container_tree = [
            {
                "type": "section",
                "name": container_id,
                "containerId": container_id,
                "containerType": "section",
                "string": contract["pageInfo"]["pageName"],
                "label": contract["pageInfo"]["pageName"],
                "span": 12,
                "styleToken": "tableSection",
                "children": [],
                "widgetList": widgets,
            }
        ]
        contract["statusContract"]["containerStatus"].append({"containerId": container_id, "visible": True, "disabled": False})
    _standardize_business_form_default_tabs(
        container_tree,
        model=model,
        view_type=view_type,
        container_status=contract["statusContract"]["containerStatus"],
    )
    contract["layoutContract"]["containerTree"] = container_tree
    contract["layoutContract"]["componentRegistry"] = _component_registry(component_keys or {"sc.display.text"})
    collection_view_key = "tree" if view_type in {"tree", "list"} else view_type
    collection_view = _dict(_dict(ui.get("views")).get(collection_view_key))
    collection_presentation = _dict(collection_view.get("collection_presentation"))
    if collection_presentation:
        contract["layoutContract"]["listProfile"]["collection_presentation"] = deepcopy(
            collection_presentation
        )
        contract["layoutContract"]["listProfile"]["sourceAuthority"] = {
            "kind": "native_collection_presentation_projection",
            "authorities": ["ir.ui.view", "ir.model.fields", "ir.actions.act_window"],
            "projection_only": True,
            "no_business_fact_authority": True,
            "runtime_carrier": "ui.contract.v2.layoutContract.listProfile",
        }
    if view_type == "activity":
        native_activity = _validated_activity_projection(collection_view)
        contract["layoutContract"]["activityProfile"] = {
                "activityTypeSlots": deepcopy(_dict(native_activity.get("activity_type_slots"))),
                "deadlineSlots": deepcopy(_dict(native_activity.get("deadline_slots"))),
                "assigneeSlots": deepcopy(_dict(native_activity.get("assignee_slots"))),
                "fieldOccurrences": deepcopy(native_activity["field_occurrences"]),
                "nativeAttrs": deepcopy(_dict(native_activity.get("native_attrs"))),
                "nodeOccurrences": deepcopy(native_activity["node_occurrences"]),
                "template": deepcopy(_dict(native_activity.get("template"))),
                "templateQwebPresent": bool(native_activity.get("template_qweb")),
                "actions": deepcopy(native_activity["actions"]),
                "actionCount": len(native_activity["actions"]),
                "sourceAuthority": {
                    "kind": "native_activity_view_projection",
                    "authorities": ["ir.ui.view", "ir.model.fields", "ir.actions.act_window"],
                    "projection_only": True,
                    "no_business_fact_authority": True,
                    "runtime_carrier": "ui.contract.v2.layoutContract.activityProfile",
                },
        }
    interaction_mode = _text(_dict(ui.get("head")).get("interaction_mode"))
    if interaction_mode:
        contract["runtimeContract"]["interactionMode"] = interaction_mode
        contract["runtimeContract"]["actionTarget"] = _text(_dict(ui.get("head")).get("action_target"), "current")
    record_version_policy = _dict(ui.get("record_version") or _dict(ui.get("head")).get("record_version"))
    if record_version_policy:
        contract["runtimeContract"]["recordVersionPolicy"] = deepcopy(record_version_policy)
    if form_structure_contract and form_structure_applied:
        contract["formStructureContract"] = deepcopy(form_structure_contract)
    contract["dataContract"]["dataMeta"]["fieldCount"] = len(fields)
    form_capabilities = _dict(form_layout.get("capabilities"))
    for key in (
        "modelRights",
        "recordRights",
        "viewCapabilities",
        "entryCapabilities",
        "effectiveRecordCapabilities",
    ):
        verdict = _dict(form_capabilities.get(key))
        if verdict:
            contract["statusContract"]["globalStatus"][key] = deepcopy(verdict)
    effective_render_profile = _text(
        form_capabilities.get("effectiveRenderProfile") or render_profile
    ).lower()
    if effective_render_profile in {"create", "edit", "readonly"}:
        contract["statusContract"]["globalStatus"]["effectiveRenderProfile"] = effective_render_profile
    effective_record_capabilities = _dict(form_capabilities.get("effectiveRecordCapabilities"))
    if not effective_record_capabilities:
        effective_record_capabilities = _ui_contract_permission_rights(_dict(source), _dict(ui))
        if effective_record_capabilities:
            contract["statusContract"]["globalStatus"]["effectiveRecordCapabilities"] = deepcopy(
                effective_record_capabilities
            )
    if effective_render_profile == "create" and effective_record_capabilities.get("create") is not True:
        contract["statusContract"]["globalStatus"]["pageVisible"] = False
        contract["statusContract"]["globalStatus"]["pageAuth"] = "none"
        contract["statusContract"]["globalStatus"]["reasonCode"] = "FORM_CREATE_NOT_ALLOWED"
    if source_context:
        contract["dataContract"]["dataMeta"]["sourceContext"] = deepcopy(source_context)
        contract["statusContract"]["globalStatus"]["pageAuth"] = _ui_contract_page_auth(
            _dict(source),
            _dict(ui),
            render_profile,
            view_type,
        )
        if source_context.get("renderProfile") == "create":
            defaults = _default_values_from_context(_dict(source_context.get("context")))
            if defaults:
                contract["dataContract"]["mainData"].update(defaults)
    _inject_collaboration_runtime_contract(contract, _dict(source.get("collaboration")))
    source_record = _dict(source.get("record"))
    if source_record:
        contract["dataContract"]["mainData"].update(deepcopy(source_record))
    _decorate_button_display_labels(
        contract["layoutContract"]["containerTree"],
        contract["dataContract"]["mainData"],
        fields_by_name,
    )
    data_source = _ui_contract_data_source(model=model, view_type=view_type, fields=fields, record_id=record_id, source=source, ui=ui)
    if data_source:
        contract["dataContract"]["dataSource"]["primary"] = data_source
    search_contract = _ui_search_contract(source, ui)
    if search_contract:
        contract["searchContract"] = search_contract
    business_operation_profile = _dict(source.get("business_operation_profile"))
    if business_operation_profile:
        profile_projection = deepcopy(business_operation_profile)
        profile_projection["sourceAuthority"] = _metadata_projection_source_authority(
            runtime_carrier="ui.contract.v2.dataMeta.businessOperationProfile",
            source_key="business_operation_profile",
        )
        contract["dataContract"]["dataMeta"]["businessOperationProfile"] = profile_projection
    visible_fields = [
        _text(item)
        for item in _list(source.get("visible_fields"))
        if _text(item)
    ]
    if visible_fields:
        contract["dataContract"]["dataMeta"]["visibleFields"] = {
            "fields": visible_fields,
            "sourceAuthority": _metadata_projection_source_authority(
                runtime_carrier="ui.contract.v2.dataMeta.visibleFields",
                source_key="visible_fields",
            ),
        }
    field_groups = [deepcopy(item) for item in _list(source.get("field_groups")) if isinstance(item, dict)]
    if field_groups:
        contract["dataContract"]["dataMeta"]["fieldGroups"] = {
            "groups": field_groups,
            "sourceAuthority": _metadata_projection_source_authority(
                runtime_carrier="ui.contract.v2.dataMeta.fieldGroups",
                source_key="field_groups",
            ),
        }
    _append_standard_form_save_action(
        contract,
        source,
        ui,
        render_profile=render_profile,
        layout_type=layout_type,
    )
    _append_ui_contract_actions(contract, ui, source_widget_id="page.root", main_data=contract["dataContract"]["mainData"])
    _append_ui_contract_row_actions(contract, ui)
    _append_registered_kanban_row_action(contract, model=model, view_type=view_type)
    return contract


def _assemble_native_form_projection(
    source: dict[str, Any],
    *,
    client_type: str,
    request_id: str,
) -> dict[str, Any]:
    marker = _dict(source.get("nativeFormProjection"))
    authority = _dict(marker.get("sourceAuthority"))
    model = _text(source.get("model"))
    if marker.get("schemaVersion") != "2.0":
        raise ValueError("native form projection schemaVersion must be 2.0")
    if _text(marker.get("model")) != model or _text(marker.get("viewType")) != "form":
        raise ValueError("native form projection identity mismatch")
    if _text(source.get("view_type")) != "form":
        raise ValueError("native form projection source view_type must be form")
    if authority.get("kind") != "native_form_projection":
        raise ValueError("native form projection authority kind mismatch")
    if authority.get("projectionOnly") is not True or authority.get("noBusinessFactAuthority") is not True:
        raise ValueError("native form projection authority boundary is incomplete")
    field_descriptors = marker.get("fieldDescriptors")
    layout = marker.get("layout")
    capabilities = marker.get("capabilities")
    subviews = marker.get("subviews")
    header_buttons = marker.get("headerButtons")
    if not isinstance(field_descriptors, dict):
        raise ValueError("native form projection fieldDescriptors must be an object")
    if not isinstance(layout, list) or not layout:
        raise ValueError("native form projection resolved layout is missing")
    if not isinstance(capabilities, dict) or not isinstance(subviews, dict):
        raise ValueError("native form projection capabilities and subviews must be objects")
    if not isinstance(header_buttons, list):
        raise ValueError("native form projection headerButtons must be an array")
    field_names = set(field_descriptors)

    def validate_occurrences(nodes: list[Any], *, parent_path: str = "layout") -> None:
        for node_index, raw in enumerate(nodes):
            node_path = f"{parent_path}[{node_index}]"
            if not isinstance(raw, dict):
                raise ValueError(f"native form projection {node_path} must be an object")
            node_type = _text(raw.get("type") or raw.get("kind")).lower()
            if node_type == "field":
                field_name = _text(raw.get("name") or raw.get("field"))
                native_locator = _text(raw.get("native_locator") or raw.get("nativeLocator"))
                occurrence_index = _positive_int(
                    raw.get("occurrence_index") or raw.get("occurrenceIndex"),
                    0,
                )
                source_position = (
                    raw.get("source_position")
                    if "source_position" in raw
                    else raw.get("sourcePosition")
                )
                if not field_name or field_name not in field_names:
                    raise ValueError(
                        f"native form projection {node_path} field descriptor identity mismatch: "
                        f"field={field_name!r}"
                    )
                if not native_locator or occurrence_index <= 0:
                    raise ValueError(
                        f"native form projection {node_path} field occurrence identity is incomplete: "
                        f"field={field_name!r} locator={native_locator!r} "
                        f"occurrence_index={occurrence_index!r} source_position={source_position!r}"
                    )
                if not isinstance(source_position, int) or isinstance(source_position, bool) or source_position < 0:
                    raise ValueError(
                        f"native form projection {node_path} field source_position is invalid: "
                        f"field={field_name!r} source_position={source_position!r}"
                    )
            children = raw.get("children")
            if isinstance(children, list):
                validate_occurrences(children, parent_path=f"{node_path}.children")

    validate_occurrences(layout)
    page = _dict(marker.get("page"))
    actions = _dict(marker.get("actions"))
    runtime = _dict(marker.get("runtime"))
    canonical_source = {
        "nativeFormProjection": deepcopy(marker),
        "model": model,
        "view_type": "form",
        "title": deepcopy(page.get("title")),
        "head": deepcopy(_dict(page.get("head"))),
        "record_id": deepcopy(page.get("recordId")),
        "render_profile": deepcopy(page.get("renderProfile")),
        "domain": deepcopy(_list(page.get("domain"))),
        "domain_raw": deepcopy(page.get("domainRaw")),
        "context": deepcopy(_dict(page.get("context"))),
        "context_raw": deepcopy(page.get("contextRaw")),
        "order": deepcopy(page.get("order")),
        "limit": deepcopy(page.get("limit")),
        "record": deepcopy(_dict(marker.get("record"))),
        "search": deepcopy(_dict(marker.get("search"))),
        "permissions": deepcopy(_dict(marker.get("permissions"))),
        "fields": deepcopy(field_descriptors),
        "buttons": deepcopy(_list(actions.get("buttons"))),
        "business_actions": deepcopy(_list(actions.get("businessActions"))),
        "toolbar": deepcopy(_dict(actions.get("toolbar"))),
        "action_groups": deepcopy(_list(actions.get("actionGroups"))),
        "action_policies": deepcopy(_dict(actions.get("actionPolicies"))),
        "action_schema": deepcopy(_dict(actions.get("actionSchema"))),
        "collaboration": deepcopy(_dict(runtime.get("collaboration"))),
        "record_version": deepcopy(_dict(runtime.get("recordVersion"))),
        "data_sources": deepcopy(_dict(runtime.get("dataSources"))),
        "business_operation_profile": deepcopy(_dict(runtime.get("businessOperationProfile"))),
        "visible_fields": deepcopy(_list(runtime.get("visibleFields"))),
        "field_groups": deepcopy(_list(runtime.get("fieldGroups"))),
        "formStructureContract": deepcopy(_dict(runtime.get("formStructureContract"))),
        "views": {
        "form": {
            "layout": deepcopy(layout),
            "capabilities": deepcopy(capabilities),
            "subviews": deepcopy(subviews),
            "header_buttons": deepcopy(header_buttons),
        }
        },
        "header_buttons": deepcopy(header_buttons),
    }
    contract = _assemble_ui_contract(
        canonical_source,
        client_type=client_type,
        request_id=request_id,
        source_type="native_form_projection",
    )
    runtime_extensions = {
        "intakeAutosave": deepcopy(_dict(runtime.get("intakeAutosave"))),
        "fieldSemantics": deepcopy(_dict(runtime.get("fieldSemantics"))),
        "validationRules": deepcopy(_list(runtime.get("validationRules"))),
        "governance": deepcopy(_dict(runtime.get("governance"))),
    }
    if any(bool(value) for value in runtime_extensions.values()):
        runtime_contract = _dict(contract.get("runtimeContract"))
        if not runtime_contract:
            runtime_contract = {}
            contract["runtimeContract"] = runtime_contract
        for key, value in runtime_extensions.items():
            if value:
                runtime_contract[key] = value
    return contract


def _has_governed_form_layout_overlay(source: dict[str, Any]) -> bool:
    governance = _dict(source.get("governance"))
    view_governance = _dict(governance.get("view_orchestration"))
    source_trace = _dict(source.get("source_trace"))
    view_trace = _dict(source_trace.get("view_orchestration"))
    business_profile = _dict(source.get("business_operation_profile"))
    runtime_form_governance = _dict(business_profile.get("form_structure_governance"))
    form_structure_authority = _text(
        view_trace.get("form_structure_authority")
        or view_governance.get("form_structure_authority")
        or runtime_form_governance.get("form_structure_authority")
    )
    return bool(
        view_trace.get("form_layout_overlay")
        or view_governance.get("form_layout_overlay")
        or form_structure_authority == "entry_semantic_surface"
    )


def _ui_search_contract(source: dict[str, Any], ui: dict[str, Any]) -> dict[str, Any]:
    raw = ui.get("search") if isinstance(ui.get("search"), dict) else source.get("search")
    search = _dict(raw)
    if not search:
        return {}
    out: dict[str, Any] = {}
    for key in ("default_sort", "default_order", "mode"):
        value = search.get(key)
        if _text(value):
            out[key] = deepcopy(value)
    for key in ("filters", "saved_filters"):
        value = search.get(key)
        if isinstance(value, list):
            rows = []
            for item in value:
                if not isinstance(item, dict):
                    continue
                row = deepcopy(item)
                if key == "filters" and not _text(row.get("key")) and _text(row.get("name")):
                    row["key"] = _text(row.get("name"))
                rows.append(row)
            if rows:
                out[key] = rows
    raw_groups = search.get("group_by_fields") or search.get("group_by")
    if isinstance(raw_groups, list):
        groups = []
        for item in raw_groups:
            if isinstance(item, dict):
                groups.append(deepcopy(item))
                continue
            field = _text(item)
            if field:
                groups.append({"key": field, "field": field, "label": field})
        if groups:
            out["group_by"] = groups
    raw_fields = search.get("fields") or search.get("search_fields")
    if isinstance(raw_fields, list):
        fields = [deepcopy(item) for item in raw_fields if isinstance(item, dict)]
        if fields:
            out["fields"] = fields
    for key in ("favorites", "custom", "ui_labels", "defaults"):
        value = search.get(key)
        if isinstance(value, dict):
            out[key] = deepcopy(value)
    search_panel = search.get("search_panel") or search.get("searchpanel")
    if isinstance(search_panel, dict):
        out["search_panel"] = deepcopy(search_panel)
    return out


def _inject_collaboration_runtime_contract(contract: dict[str, Any], collaboration: dict[str, Any]) -> None:
    if not collaboration:
        return
    runtime = _dict(contract.get("runtimeContract"))
    if not runtime:
        runtime = {}
        contract["runtimeContract"] = runtime
    normalized: dict[str, Any] = {}
    for key in ("chatter", "attachments", "timeline", "sourceAuthority"):
        value = collaboration.get(key)
        if isinstance(value, dict):
            normalized[key] = deepcopy(value)
    if normalized:
        runtime["collaboration"] = normalized


def _field_rows(source: dict[str, Any], ui: dict[str, Any], *, view_type: str = "") -> list[dict[str, Any]]:
    rows = source.get("meta_fields")
    if isinstance(rows, list) and rows:
        if view_type in {"tree", "list", "kanban"}:
            view_fields = _view_field_names(ui, view_type)
            schema_by_name = _view_column_schema_by_name(ui, view_type)
            row_by_name: dict[str, dict[str, Any]] = {}
            for row in rows:
                if not isinstance(row, dict):
                    continue
                name = _text(row.get("name") or row.get("field") or row.get("fieldCode"))
                if name and name not in row_by_name:
                    row_by_name[name] = row
            if view_fields:
                out = []
                for name in view_fields:
                    row = row_by_name.get(name)
                    item = dict(row) if isinstance(row, dict) else {}
                    item.setdefault("name", name)
                    schema = schema_by_name.get(name)
                    if schema:
                        item.update(schema)
                        item.setdefault("name", name)
                    out.append(item)
                return out
            out = []
            for row in rows:
                if not isinstance(row, dict):
                    continue
                item = dict(row)
                name = _text(item.get("name") or item.get("field") or item.get("fieldCode"))
                schema = schema_by_name.get(name)
                if schema:
                    item.update(schema)
                    item.setdefault("name", name)
                out.append(item)
            return out
        return [row for row in rows if isinstance(row, dict)]
    fields = ui.get("fields") or source.get("fields")
    layout_labels = _form_layout_field_labels(ui) if view_type == "form" else {}
    if isinstance(fields, dict) and view_type == "form" and layout_labels:
        out = []
        for name, label in layout_labels.items():
            value = fields.get(name)
            row = dict(value) if isinstance(value, dict) else {}
            row.setdefault("name", name)
            row["string"] = label
            row["label"] = label
            out.append(row)
        return out
    if isinstance(fields, dict) and view_type in {"tree", "list", "kanban"}:
        view_fields = _view_field_names(ui, view_type)
        schema_by_name = _view_column_schema_by_name(ui, view_type)
        if view_fields:
            out = []
            for name in view_fields:
                value = fields.get(name)
                row = dict(value) if isinstance(value, dict) else {}
                schema = schema_by_name.get(name)
                if schema:
                    row.update(schema)
                row.setdefault("name", name)
                out.append(row)
            return out
    if isinstance(fields, dict):
        out = []
        for key, value in fields.items():
            row = dict(value) if isinstance(value, dict) else {}
            row.setdefault("name", key)
            label = layout_labels.get(key)
            if label:
                row["string"] = label
                row["label"] = label
            out.append(row)
        return out
    return []


def _form_layout_field_labels(ui: dict[str, Any]) -> dict[str, str]:
    form = _dict(_dict(ui.get("views")).get("form"))
    labels: dict[str, str] = {}

    def walk(obj: Any) -> None:
        if isinstance(obj, dict):
            node_type = _text(obj.get("type") or obj.get("kind")).lower()
            name = _text(obj.get("name") or obj.get("field"))
            if node_type == "field" and name and name not in labels:
                field_info = _dict(obj.get("fieldInfo") or obj.get("field_info"))
                label = _text(obj.get("string") or obj.get("label") or field_info.get("string") or field_info.get("label"))
                if label:
                    labels[name] = label
            for value in obj.values():
                walk(value)
            return
        if isinstance(obj, list):
            for value in obj:
                walk(value)

    walk(form.get("layout"))
    return labels


def _view_field_names(ui: dict[str, Any], view_type: str) -> list[str]:
    views = _dict(ui.get("views"))
    candidates = [view_type]
    if view_type == "tree":
        candidates.append("list")
    if view_type == "list":
        candidates.append("tree")
    out: list[str] = []
    for key in candidates:
        view = _dict(views.get(key))
        for raw_name in _list(view.get("columns") or view.get("fields")):
            name = _text(raw_name)
            if name and name not in out:
                out.append(name)
        for row in _list(view.get("columnsSchema") or view.get("columns_schema")):
            if not isinstance(row, dict):
                continue
            name = _text(row.get("name") or row.get("field") or row.get("fieldCode"))
            if name and name not in out:
                out.append(name)
        if key == "kanban":
            kanban = _dict(view.get("kanban"))
            template = _text(kanban.get("template_qweb") or view.get("template_qweb") or view.get("arch"))
            for name in re.findall(r"\brecord\.([A-Za-z_][A-Za-z0-9_]*)\b", template):
                if name and name not in out:
                    out.append(name)
        if out:
            return out
    return out


def _view_column_schema_by_name(ui: dict[str, Any], view_type: str) -> dict[str, dict[str, Any]]:
    views = _dict(ui.get("views"))
    candidates = [view_type]
    if view_type == "tree":
        candidates.append("list")
    if view_type == "list":
        candidates.append("tree")
    for key in candidates:
        view = _dict(views.get(key))
        out: dict[str, dict[str, Any]] = {}
        for row in _list(view.get("columnsSchema") or view.get("columns_schema")):
            if not isinstance(row, dict):
                continue
            name = _text(row.get("name") or row.get("field") or row.get("fieldCode"))
            if not name or name in out:
                continue
            out[name] = dict(row)
            out[name].setdefault("name", name)
        if out:
            return out
    return {}


def _field_widget(field: dict[str, Any], *, layout_type: str) -> dict[str, Any]:
    field_name = _stable_id(field.get("name"), "field")
    native_locator = _text(field.get("native_locator"))
    occurrence_index = _positive_int(field.get("occurrence_index"), 0)
    source_position = field.get("source_position")
    widget_id = f"field.{field_name}"
    if layout_type == "form" and native_locator:
        widget_id = f"field.{field_name}.occ.{_fingerprint({'locator': native_locator, 'occurrence': occurrence_index})}"
    explicit_widget = _text(field.get("widget"))
    widget_type = "table" if layout_type == "table" else _canonical_widget_type(explicit_widget, field)
    component_widget_type = explicit_widget if explicit_widget in {
        "monetary", "percentage", "percentpie", "float_time", "statusbar",
    } else widget_type
    component_key = _component_key(component_widget_type, field)
    capabilities = ["sortable", "filterable"] if layout_type == "table" else []
    if widget_type == "select":
        capabilities.append("searchable")
    component_config = {}
    for key in (
        "optional", "invisible", "column_invisible", "readonly", "required",
        "display_field", "value_field", "aggregation_field", "data_type",
        "currency_field", "digits", "precision", "sum", "aggregate", "aggregate_label",
        "sort_field", "filter_field", "export_field", "semantic_status",
        "reason_code", "source_authority",
        "native_locator", "occurrence_index", "source_position", "modifiers",
        "relation_active_actions",
    ):
        if key in field:
            component_config[key] = deepcopy(field.get(key))
    field_type = _text(field.get("ttype") or field.get("type")).lower()
    if field_type:
        component_config["fieldType"] = field_type
    if explicit_widget:
        component_config["nativeWidget"] = explicit_widget
    selection = field.get("selection")
    if field_type == "selection" and isinstance(selection, (list, tuple)):
        component_config["selection"] = deepcopy(list(selection))
    if _text(field.get("relation")):
        component_config["relation"] = _text(field.get("relation"))
    relation_entry = _dict(field.get("relation_entry"))
    if relation_entry:
        component_config["relationEntry"] = deepcopy(relation_entry)
    relation_active_actions = _dict(field.get("relation_active_actions"))
    if relation_active_actions:
        component_config["relationActiveActions"] = deepcopy(relation_active_actions)
    widget_options = _dict(field.get("widget_options") or field.get("options"))
    if widget_options:
        component_config["widgetOptions"] = deepcopy(widget_options)
    return {
        "widgetId": widget_id,
        "widgetType": widget_type,
        "fieldCode": field_name,
        "label": _text(field.get("string") or field.get("label"), field_name),
        "span": 12 if layout_type == "table" else 6,
        "componentKey": component_key,
        "capabilities": capabilities,
        "componentConfig": component_config,
        "fieldDescriptor": deepcopy(field),
    }


def _native_field_node(node: dict[str, Any], field: dict[str, Any], *, layout_type: str) -> dict[str, Any]:
    field_name = _stable_id(node.get("name") or node.get("field") or field.get("name"), "field")
    label = _text(
        node.get("string")
        or node.get("label")
        or node.get("title")
        or _dict(node.get("fieldInfo")).get("label")
        or _dict(node.get("field_info")).get("label")
        or field.get("string")
        or field.get("label"),
        field_name,
    )
    field_source = deepcopy(field)
    field_info = _dict(node.get("fieldInfo") or node.get("field_info"))
    field_source.update({k: deepcopy(v) for k, v in field_info.items() if k not in {"label", "string"}})
    field_source["name"] = field_name
    for key in (
        "native_locator", "occurrence_index", "source_position", "modifiers", "relation_entry",
        "relation_active_actions",
    ):
        if key in node:
            field_source[key] = deepcopy(node.get(key))
    field_source.setdefault("string", label)
    field_source.setdefault("label", label)
    if _text(node.get("widget")):
        field_source["widget"] = _text(node.get("widget"))
    widget = _field_widget(field_source, layout_type=layout_type)
    component_config = deepcopy(widget.get("componentConfig") or {})
    field_info["name"] = field_name
    field_info["label"] = label
    field_info["widget"] = widget["widgetType"]
    for key in ("type", "ttype", "relation", "relation_entry", "widget_options", "options"):
        if key in field_source and key not in field_info:
            field_info[key] = deepcopy(field_source.get(key))
    out = deepcopy(node)
    out["type"] = "field"
    out["name"] = field_name
    out["string"] = label
    out["label"] = label
    out["fieldInfo"] = field_info
    out["widget"] = widget["widgetType"]
    out["componentKey"] = widget["componentKey"]
    out["componentConfig"] = component_config
    out["widgetId"] = widget["widgetId"]
    native_locator = _text(field_source.get("native_locator"))
    if layout_type == "form" and native_locator:
        out["nativeLocator"] = native_locator
        out["occurrenceIndex"] = _positive_int(field_source.get("occurrence_index"), 0)
        out["sourcePosition"] = field_source.get("source_position")
    # Native parser evidence is snake_case at the producer boundary, while the
    # normalized V2 layout wire is camelCase.  Do not leave both spellings on
    # the strict layout node: componentConfig retains the producer evidence and
    # the canonical node fields above carry its governed projection.
    for producer_key in (
        "native_locator", "occurrence_index", "source_position", "relation_entry",
        "relation_active_actions",
    ):
        out.pop(producer_key, None)
    return out


def _field_source_with_node_info(node: dict[str, Any], field: dict[str, Any], *, fallback_name: str = "") -> dict[str, Any]:
    field_name = _stable_id(node.get("name") or node.get("field") or field.get("name") or fallback_name, "field")
    field_source = deepcopy(field) if isinstance(field, dict) else {}
    field_info = _dict(node.get("fieldInfo") or node.get("field_info"))
    field_source.update({k: deepcopy(v) for k, v in field_info.items() if k not in {"label", "string"}})
    field_modifiers = _dict(field_info.get("modifiers"))
    for key in ("readonly", "required", "invisible", "column_invisible"):
        if key in field_modifiers and key not in field_source:
            field_source[key] = deepcopy(field_modifiers.get(key))
    for key in (
        "readonly", "required", "invisible", "column_invisible", "sum",
        "display_field", "value_field", "aggregation_field", "data_type",
        "currency_field", "precision", "aggregate", "aggregate_label",
        "sort_field", "filter_field", "export_field", "semantic_status",
        "reason_code", "source_authority",
        "native_locator", "occurrence_index", "source_position", "modifiers", "relation_entry",
        "relation_active_actions",
    ):
        if key in node:
            field_source[key] = deepcopy(node.get(key))
    for canonical_key, producer_key in (
        ("nativeLocator", "native_locator"),
        ("occurrenceIndex", "occurrence_index"),
        ("sourcePosition", "source_position"),
    ):
        if canonical_key in node:
            field_source[producer_key] = deepcopy(node.get(canonical_key))
    field_source["name"] = field_name
    field_source.setdefault("string", _text(node.get("string") or node.get("label") or field_info.get("label"), field_name))
    field_source.setdefault("label", field_source.get("string", field_name))
    if _text(node.get("widget")):
        field_source["widget"] = _text(node.get("widget"))
    return field_source


def _direct_field_widgets_from_nodes(
    nodes: list[dict[str, Any]],
    fields_by_name: dict[str, dict[str, Any]],
    *,
    layout_type: str,
) -> list[dict[str, Any]]:
    widgets: list[dict[str, Any]] = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        if _text(node.get("type") or node.get("kind")).lower() != "field":
            continue
        field_name = _stable_id(node.get("name") or node.get("field"), "field")
        field = _dict(fields_by_name.get(field_name))
        if not field:
            field = {"name": field_name, "string": _text(node.get("string") or node.get("label"), field_name)}
        field_source = _field_source_with_node_info(node, field, fallback_name=field_name)
        widgets.append(_field_widget(field_source, layout_type=layout_type))
    return widgets


def _normalize_native_layout_nodes(
    rows: list[dict[str, Any]],
    fields_by_name: dict[str, dict[str, Any]],
    *,
    layout_type: str,
    form_subviews: dict[str, Any] | None = None,
    component_keys: set[str],
    container_status: list[dict[str, Any]],
    widget_status: list[dict[str, Any]],
    context: dict[str, Any] | None = None,
    path: str = "native",
    container_ids: set[str] | None = None,
    root_level: bool = True,
) -> list[dict[str, Any]]:
    used_container_ids = container_ids if container_ids is not None else set()
    out: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        node_path = f"{path}.{index}"
        node = deepcopy(row)
        alias_pairs = (
            ("field_info", "fieldInfo"),
            ("attrs", "attributes"),
            ("field_size", "fieldSize"),
            ("source_authority", "sourceAuthority"),
            ("form_structure", "formStructure"),
            ("form_structure_role", "formStructureRole"),
            ("button_type", "buttonType"),
            ("container_id", "containerId"),
            ("container_type", "containerType"),
            ("widget_id", "widgetId"),
        )
        for alias, canonical in alias_pairs:
            if alias in node and canonical not in node:
                node[canonical] = deepcopy(node.get(alias))
        node_type = _text(node.get("type") or node.get("kind"), "group").lower()
        node["type"] = node_type
        node_name = _text(node.get("name") or node.get("field"))
        if node_name:
            node["name"] = node_name
        for alias in ("kind", "field", *(pair[0] for pair in alias_pairs)):
            node.pop(alias, None)
        label = _text(node.get("string") or node.get("label") or node.get("title"))
        if label:
            node["string"] = label
            node["label"] = label
        invisible = _apply_contextual_invisible_modifier(node, context or {})
        if invisible is not None:
            node["invisible"] = invisible
        if node_type == "field":
            field = _dict(fields_by_name.get(node_name)) if node_name else {}
            for key in ("readonly", "required", "invisible", "column_invisible"):
                if key in field and key not in node:
                    node[key] = deepcopy(field.get(key))
            normalized = _native_field_node(node, field, layout_type=layout_type)
            if node_name:
                subview = _dict((form_subviews or {}).get(node_name))
                if subview:
                    field_info = _dict(normalized.get("fieldInfo"))
                    field_info["subview"] = deepcopy(subview)
                    normalized["fieldInfo"] = field_info
            widget_source = _field_source_with_node_info(normalized, field, fallback_name=node_name or _text(field.get("name")))
            widget = _field_widget(widget_source, layout_type=layout_type)
            container_id = widget["widgetId"]
            if container_id in used_container_ids:
                raise ValueError("native form field container identity is duplicated")
            used_container_ids.add(container_id)
            normalized["containerId"] = container_id
            # A native field occurrence is a layout node, not a formal
            # container registry member. Its type remains authoritative.
            normalized.pop("containerType", None)
            normalized["children"] = []
            # A field nested below a container is carried by that parent's
            # widgetList.  A parser/governance producer may, however, emit a
            # field at the form root.  Such an occurrence has no parent to
            # carry its descriptor, so it must own the exact same strict
            # widget itself instead of leaking an ownerless occurrence into
            # the formal V2 wire.
            if root_level:
                widget["ownerContainerId"] = container_id
                normalized["widgetList"] = [widget]
            else:
                normalized["widgetList"] = []
            component_keys.add(widget["componentKey"])
            widget_status.append(_field_status(
                widget_source,
                widget["widgetId"],
                context=context,
                occurrence=bool(
                    _text(widget_source.get("native_locator"))
                    and _positive_int(widget_source.get("occurrence_index"), 0)
                ),
            ))
            out.append(normalized)
            continue
        container_id = _text(node.get("containerId") or node.get("container_id") or node_name)
        if not container_id:
            explicit_label = node.get("title") or node.get("string") or node.get("label")
            container_id = _stable_id(explicit_label, node_type) if explicit_label else f"{node_type}.{node_path}"
        if container_id in used_container_ids:
            container_id = f"{container_id}.{node_path}"
        used_container_ids.add(container_id)
        node["containerId"] = container_id
        node["containerType"] = _formal_container_type(node_type)
        # Stable container identity is structural metadata, never display copy.
        # Anonymous native containers intentionally keep an empty title.
        node.setdefault("title", label)
        node.setdefault("label", label)
        container_status.append({"containerId": container_id, "visible": not bool(invisible), "disabled": False})
        child_carriers: list[tuple[str, list[Any]]] = []
        for key in ("children", "pages", "tabs", "nodes", "items"):
            if key in node and not isinstance(node.get(key), list):
                raise ValueError(f"native layout node {node_path}.{key} must be an array")
            child_rows = node.get(key) if isinstance(node.get(key), list) else []
            if child_rows:
                child_carriers.append((key, child_rows))
        if len(child_carriers) > 1:
            carriers = ",".join(key for key, _rows in child_carriers)
            raise ValueError(
                f"native layout node {node_path} has ambiguous parallel child carriers: {carriers}"
            )
        source_key, source_children = child_carriers[0] if child_carriers else ("children", [])
        if any(not isinstance(item, dict) for item in source_children):
            raise ValueError(f"native layout node {node_path}.{source_key} must contain objects")
        node["children"] = _normalize_native_layout_nodes(
            source_children,
            fields_by_name,
            layout_type=layout_type,
            form_subviews=form_subviews,
            component_keys=component_keys,
            container_status=container_status,
            widget_status=widget_status,
            context=context,
            path=f"{node_path}.{source_key}",
            container_ids=used_container_ids,
            root_level=False,
        )
        for legacy_key in ("pages", "tabs", "nodes", "items"):
            node.pop(legacy_key, None)
        direct_widgets = _direct_field_widgets_from_nodes(
            _list(node.get("children")), fields_by_name, layout_type=layout_type,
        )
        if direct_widgets:
            child_by_widget_id = {
                _text(child.get("widgetId")): child
                for child in _list(node.get("children"))
                if isinstance(child, dict) and _text(child.get("widgetId"))
            }
            normalized_direct_widgets: list[dict[str, Any]] = []
            for widget in direct_widgets:
                owner = child_by_widget_id.get(_text(widget.get("widgetId")))
                if not owner:
                    raise ValueError(
                        f"native layout widget {_text(widget.get('widgetId'))} has no direct owner"
                    )
                widget["ownerContainerId"] = _text(owner.get("containerId"))
                for source_name in (
                    "nativeLocator", "occurrenceIndex", "sourcePosition", "formStructureRole",
                ):
                    if source_name in owner:
                        widget[source_name] = deepcopy(owner.get(source_name))
                normalized_direct_widgets.append(widget)
            node["widgetList"] = normalized_direct_widgets
            for widget in direct_widgets:
                component_keys.add(widget["componentKey"])
        elif not isinstance(node.get("widgetList"), list):
            node["widgetList"] = []
        out.append(node)
    return out


def _walk_native_nodes(nodes: list[dict[str, Any]]):
    for node in nodes:
        if not isinstance(node, dict):
            continue
        yield node
        for key in ("children", "pages", "tabs", "nodes", "items"):
            child_rows = node.get(key)
            if isinstance(child_rows, list):
                yield from _walk_native_nodes([item for item in child_rows if isinstance(item, dict)])


def _layout_contains_node_type(nodes: list[dict[str, Any]], node_types: set[str]) -> bool:
    for node in _walk_native_nodes(nodes):
        if _text(node.get("containerType") or node.get("type") or node.get("kind")).lower() in node_types:
            return True
    return False


def _node_field_names(node: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for item in _walk_native_nodes([node]):
        if _text(item.get("type") or item.get("kind")).lower() != "field":
            continue
        field_name = _text(item.get("name") or item.get("field"))
        if field_name and field_name not in out:
            out.append(field_name)
    return out


def _node_field_types(node: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for item in _walk_native_nodes([node]):
        if _text(item.get("type") or item.get("kind")).lower() != "field":
            continue
        field_info = _dict(item.get("fieldInfo") or item.get("field_info"))
        field_type = _text(field_info.get("type") or field_info.get("ttype") or item.get("widget")).lower()
        if field_type:
            out.append(field_type)
    return out


def _node_text_fingerprint(node: dict[str, Any]) -> str:
    values: list[str] = []
    for item in _walk_native_nodes([node]):
        values.extend([
            _text(item.get("name") or item.get("field")).lower(),
            _text(item.get("string") or item.get("label") or item.get("title")).lower(),
        ])
        field_info = _dict(item.get("fieldInfo") or item.get("field_info"))
        values.extend([
            _text(field_info.get("string") or field_info.get("label")).lower(),
            _text(field_info.get("name")).lower(),
        ])
    return " ".join(item for item in values if item)


def _node_has_token(node: dict[str, Any], tokens: tuple[str, ...]) -> bool:
    fingerprint = _node_text_fingerprint(node)
    return any(token.lower() in fingerprint for token in tokens)


def _node_has_x2many(node: dict[str, Any]) -> bool:
    return any(field_type in {"one2many", "many2many"} for field_type in _node_field_types(node))


def _node_has_direct_group_child(node: dict[str, Any]) -> bool:
    for key in ("children", "pages", "tabs", "nodes", "items"):
        child_rows = node.get(key)
        if not isinstance(child_rows, list):
            continue
        for child in child_rows:
            if not isinstance(child, dict):
                continue
            child_type = _text(child.get("type") or child.get("kind") or child.get("containerType")).lower()
            if child_type == "group":
                return True
    return False


def _is_generic_container_label(node: dict[str, Any]) -> bool:
    node_type = _text(node.get("containerType") or node.get("type") or node.get("kind")).lower()
    labels = {
        _text(node.get("title")).lower(),
        _text(node.get("label")).lower(),
        _text(node.get("string")).lower(),
    }
    generic = {"", node_type}
    container_id = _text(node.get("containerId")).lower()
    node_name = _text(node.get("name")).lower()
    if _is_technical_container_identifier(container_id):
        generic.add(container_id)
    if _is_technical_container_identifier(node_name):
        generic.add(node_name)
    return bool(labels & generic) or all(not label for label in labels)


def _is_technical_container_identifier(value: str) -> bool:
    if not value:
        return False
    return bool(re.fullmatch(r"[a-z0-9_.:-]+", value))


def _semantic_group_label(node: dict[str, Any], *, level: int, index: int) -> str:
    fingerprint = _node_text_fingerprint(node)
    field_names = set(_node_field_names(node))
    if level <= 1 and _node_has_direct_group_child(node):
        return "主信息"
    if _node_has_token(node, TRACE_FIELD_TOKENS):
        return "来源追溯"
    if _node_has_token(node, NOTE_FIELD_TOKENS):
        return "备注说明"
    if _node_has_x2many(node):
        return "业务明细"
    if any(token in fingerprint for token in ("amount", "price", "cost", "budget", "fee", "money", "金额", "费用", "成本", "预算")):
        return "金额信息"
    if any(token in fingerprint for token in ("date", "time", "deadline", "start", "end", "日期", "时间", "截止")):
        return "时间信息"
    if any(token in fingerprint for token in ("partner", "supplier", "owner", "manager", "user", "负责人", "供应", "往来", "经理")):
        return "责任与往来"
    if level <= 1 or field_names & {"name", "code", "project_id", "state", "company_id"}:
        return "主信息" if level == 0 else "基础信息"
    return f"业务信息 {index + 1}"


def _apply_semantic_container_label(node: dict[str, Any], label: str) -> None:
    _apply_semantic_container_annotation(node, label)


def _apply_semantic_container_annotation(node: dict[str, Any], label: str) -> None:
    node["semanticTitle"] = label
    node["semanticAnchor"] = _stable_id(label, "semantic.group")
    source = _dict(node.get("sourceAuthority"))
    source.update({
        "kind": SOURCE_KIND,
        "projection_only": True,
        "no_business_fact_authority": True,
        "runtime_carrier": "business_form_semantic_label_standardizer",
    })
    node["sourceAuthority"] = source


def _business_group_label_for_node(source: dict[str, Any], node: dict[str, Any]) -> str:
    groups = _list(source.get("field_groups"))
    business_groups: list[tuple[str, str, set[str]]] = []
    for group in groups:
        if not isinstance(group, dict):
            continue
        name = _text(group.get("name")).lower()
        if not name.startswith("business_"):
            continue
        fields = {_text(item) for item in _list(group.get("fields")) if _text(item)}
        if not fields:
            continue
        label = _text(group.get("label") or group.get("title") or group.get("string"))
        if label:
            business_groups.append((name, label, fields))
    if not business_groups:
        return ""
    node_fields = set(_node_field_names(node))
    if not node_fields:
        return ""
    ranked = sorted(
        (
            (len(node_fields & fields), name, label)
            for name, label, fields in business_groups
            if node_fields & fields
        ),
        key=lambda item: (
            item[0],
            4 if item[1] == "business_collaboration" else 3 if item[1] == "business_details" else 2 if item[1] == "business_amount" else 1,
        ),
        reverse=True,
    )
    return ranked[0][2] if ranked else ""


def _standardize_form_container_semantics(nodes: list[dict[str, Any]], *, model: str, view_type: str, source: dict[str, Any] | None = None) -> None:
    if view_type != "form" or not model:
        return

    def visit(rows: list[dict[str, Any]], *, level: int) -> None:
        group_index = 0
        for node in rows:
            if not isinstance(node, dict):
                continue
            node_type = _text(node.get("containerType") or node.get("type") or node.get("kind")).lower()
            if node_type == "group":
                if _is_generic_container_label(node):
                    business_label = _business_group_label_for_node(_dict(source), node)
                    _apply_semantic_container_label(
                        node,
                        business_label or _semantic_group_label(node, level=level, index=group_index),
                    )
                else:
                    semantic_title = _text(node.get("semanticTitle"))
                    visible_label = _text(node.get("title") or node.get("label") or node.get("string"))
                    if not semantic_title and visible_label:
                        _apply_semantic_container_annotation(node, visible_label)
                group_index += 1
            for key in ("children", "pages", "tabs", "nodes", "items"):
                child_rows = node.get(key)
                if isinstance(child_rows, list):
                    visit([item for item in child_rows if isinstance(item, dict)], level=level + 1)

    visit(nodes, level=0)


def _node_is_button_box(node: dict[str, Any]) -> bool:
    classes = _text(_dict(node.get("attributes")).get("class") or node.get("class")).split()
    if "oe_button_box" in classes:
        return True
    for item in _walk_native_nodes([node]):
        if _text(item.get("type") or item.get("kind")).lower() != "button":
            continue
        action = _dict(item.get("action"))
        if _text(action.get("level")).lower() == "smart":
            return True
        item_classes = _text(_dict(item.get("attributes")).get("class") or item.get("class")).split()
        if "oe_stat_button" in item_classes:
            return True
    return False


def _append_container_status_once(container_status: list[dict[str, Any]], container_id: str) -> None:
    if not container_id:
        return
    if any(_text(row.get("containerId")) == container_id for row in container_status if isinstance(row, dict)):
        return
    container_status.append({"containerId": container_id, "visible": True, "disabled": False})


def _standardize_business_form_default_tabs(
    container_tree: list[dict[str, Any]],
    *,
    model: str,
    view_type: str,
    container_status: list[dict[str, Any]],
) -> None:
    # Odoo native form views only expose notebook/page captions as visible
    # structure.  Generic tabs such as "主信息" or "业务明细" are semantic
    # guesses, so they must not be projected as user-visible page titles.
    return


def _form_structure_contract_layout_rows(
    structure_contract: dict[str, Any],
    fields_by_name: dict[str, dict[str, Any]],
    *,
    native_layout_rows: list[dict[str, Any]],
    page_title: str,
    render_profile: str = "",
) -> list[dict[str, Any]]:
    if not structure_contract:
        return native_layout_rows
    available = {name for name in fields_by_name if _text(name)}
    native_field_nodes: dict[str, dict[str, Any]] = {}
    native_group_layouts: list[dict[str, Any]] = []

    def normalize_layout_columns(value: Any) -> int | None:
        try:
            columns = int(value)
        except (TypeError, ValueError):
            return None
        return columns if columns > 0 else None

    def node_layout_columns(node: dict[str, Any]) -> int | None:
        attrs = _dict(node.get("attributes") or node.get("attrs"))
        return (
            normalize_layout_columns(node.get("cols"))
            or normalize_layout_columns(node.get("columns"))
            or normalize_layout_columns(node.get("col"))
            or normalize_layout_columns(attrs.get("columns"))
            or normalize_layout_columns(attrs.get("cols"))
            or normalize_layout_columns(attrs.get("col"))
        )

    def collect_node_field_names(nodes: Any, out: list[str] | None = None) -> list[str]:
        names = out if out is not None else []
        for node in _list(nodes):
            if not isinstance(node, dict):
                continue
            node_type = _text(node.get("type") or node.get("kind")).lower()
            node_name = _text(node.get("name") or node.get("field"))
            if node_type == "field" and node_name and node_name not in names:
                names.append(node_name)
            for key in ("children", "pages", "tabs", "nodes", "items", "groups", "fields"):
                child_rows = node.get(key)
                if isinstance(child_rows, list) and child_rows:
                    collect_node_field_names(child_rows, names)
        return names

    def collect_native_field_nodes(nodes: Any) -> None:
        for node in _list(nodes):
            if not isinstance(node, dict):
                continue
            node_type = _text(node.get("type") or node.get("kind")).lower()
            node_name = _text(node.get("name") or node.get("field"))
            if node_type == "field" and node_name and node_name not in native_field_nodes:
                native_field_nodes[node_name] = deepcopy(node)
            if node_type == "group":
                columns = node_layout_columns(node)
                if columns:
                    title = _text(node.get("string") or node.get("label") or node.get("title"))
                    native_group_layouts.append({
                        "title": title,
                        "fields": collect_node_field_names(node.get("children")),
                        "cols": columns,
                    })
            for key in ("children", "pages", "tabs", "nodes", "items", "groups", "fields"):
                child_rows = node.get(key)
                if isinstance(child_rows, list) and child_rows:
                    collect_native_field_nodes(child_rows)

    def dominant_native_group_columns() -> int | None:
        counts: dict[int, int] = {}
        for row in native_group_layouts:
            columns = normalize_layout_columns(row.get("cols"))
            if columns:
                counts[columns] = counts.get(columns, 0) + 1
        if not counts:
            return None
        return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]

    def native_field_hidden(node: dict[str, Any]) -> bool:
        if node.get("invisible") is True:
            return True
        modifiers = _dict(node.get("modifiers"))
        if modifiers.get("invisible") is True:
            return True
        attrs = _dict(node.get("attrs") or node.get("attributes"))
        if attrs.get("invisible") is True:
            return True
        return False

    collect_native_field_nodes(native_layout_rows)

    field_roles = _dict(structure_contract.get("fieldRoles") or structure_contract.get("field_roles"))
    normalized_render_profile = _text(render_profile).lower()

    def skip_field_for_create(name: str, native_node: dict[str, Any] | None = None) -> bool:
        if normalized_render_profile != "create":
            return False
        field_meta = _dict(fields_by_name.get(name))
        node_meta = _dict(native_node or {})
        node_field_info = _dict(node_meta.get("fieldInfo") or node_meta.get("field_info"))
        role = _dict(field_roles.get(name))
        fingerprint = " ".join(
            _text(value).lower()
            for value in (
                name,
                field_meta.get("string"),
                field_meta.get("label"),
                node_meta.get("string"),
                node_meta.get("label"),
                node_field_info.get("label"),
                node_field_info.get("string"),
                role.get("role"),
                role.get("slot"),
                role.get("group"),
            )
            if _text(value)
        )
        return any(
            token in fingerprint
            for token in ("legacy", "history", "history_check", "provenance", "source", "snapshot", "历史", "来源", "追溯", "快照", "迁移")
        )

    def field_nodes(names: list[Any], *, readonly: bool = False) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in names:
            name = _text(item)
            if not name or name in seen or name not in available:
                continue
            native_node = native_field_nodes.get(name)
            if native_node and native_field_hidden(native_node):
                continue
            if skip_field_for_create(name, native_node):
                continue
            seen.add(name)
            row: dict[str, Any] = deepcopy(native_node) if native_node else {"type": "field", "name": name}
            row["type"] = "field"
            row["name"] = name
            if readonly:
                row["readonly"] = True
                modifiers = _dict(row.get("modifiers"))
                modifiers["readonly"] = True
                row["modifiers"] = modifiers
            role = _dict(field_roles.get(name))
            if role:
                row["formStructureRole"] = deepcopy(role)
            rows.append(row)
        return rows

    def group_node(group: dict[str, Any], *, readonly: bool = False, slot_name: str = "") -> dict[str, Any]:
        name = _stable_id(group.get("name") or group.get("title") or "business_group", "group")
        title = _text(group.get("title") or group.get("label") or group.get("string") or name, name)
        field_refs = _list(group.get("fieldRefs") or group.get("field_refs") or group.get("fields"))
        children = field_nodes(field_refs, readonly=readonly)
        if not children:
            return {}
        child_names = [row.get("name") for row in children if _text(row.get("name"))]
        configured_columns = node_layout_columns(group)
        inherited_columns = configured_columns or next(
            (
                row.get("cols")
                for row in native_group_layouts
                if row.get("title") and _text(row.get("title")) == title
            ),
            None,
        ) or next(
            (
                row.get("cols")
                for row in native_group_layouts
                if row.get("fields") and child_names and set(row.get("fields") or []) == set(child_names)
            ),
            None,
        ) or dominant_native_group_columns()
        layout_attrs = {"col": str(inherited_columns)} if inherited_columns else {}
        node = {
            "type": "group",
            "name": name,
            "string": title,
            "label": title,
            "formStructure": {
                "slot": slot_name,
                "group": name,
                "role": _text(group.get("role") or name, name),
            },
            "children": children,
            "sourceAuthority": {
                "kind": SOURCE_KIND,
                "runtime_carrier": "form_structure_contract",
                "no_business_fact_authority": True,
            },
        }
        if inherited_columns:
            node["cols"] = inherited_columns
            node["attributes"] = layout_attrs
        return node

    header_rows = [
        deepcopy(row)
        for row in native_layout_rows
        if _text(row.get("type") or row.get("kind")).lower() == "header"
    ]
    children: list[dict[str, Any]] = []
    slots = [_dict(item) for item in _list(structure_contract.get("slots")) if isinstance(item, dict)]
    summary = next(
        (
            slot
            for slot in slots
            if _text(slot.get("slot") or slot.get("name")).lower() in {"overview", "summary", "business_overview"}
        ),
        _dict(structure_contract.get("summary")),
    )
    show_summary_group = _text(render_profile).lower() == "readonly"
    summary_group = group_node(summary, readonly=True) if summary and show_summary_group else {}
    if summary_group:
        children.append(summary_group)

    tabs: list[dict[str, Any]] = []
    flatten_task_groups = normalized_render_profile != "readonly"

    def skip_group_for_create(group_row: dict[str, Any]) -> bool:
        if normalized_render_profile != "create":
            return False
        form_structure = _dict(group_row.get("formStructure"))
        fingerprint = " ".join(
            _text(value).lower()
            for value in (
                group_row.get("name"),
                group_row.get("label"),
                group_row.get("string"),
                form_structure.get("slot"),
                form_structure.get("group"),
                form_structure.get("role"),
            )
            if _text(value)
        )
        return any(
            token in fingerprint
            for token in ("provenance", "history", "history_check", "source", "legacy", "追溯", "历史", "来源")
        )
    page_slots = [
        slot
        for slot in slots
        if _text(slot.get("slot") or slot.get("name")).lower() not in {"overview", "summary", "business_overview"}
    ]
    legacy_pages = [_dict(item) for item in _list(structure_contract.get("pages")) if isinstance(item, dict)]
    for page_dict in page_slots or legacy_pages:
        page_name = _stable_id(
            page_dict.get("slot") or page_dict.get("name") or page_dict.get("title") or "business_page",
            "page",
        )
        page_title = _text(page_dict.get("title") or page_dict.get("label") or page_dict.get("string") or page_name, page_name)
        page_role = _text(page_dict.get("role") or page_name, page_name)
        page_children: list[dict[str, Any]] = []
        for group in _list(page_dict.get("groups")):
            group_row = group_node(_dict(group), readonly=bool(page_dict.get("readonly")), slot_name=page_name)
            if group_row:
                page_children.append(group_row)
        if not page_children:
            direct_group = group_node({
                "name": f"{page_name}.fields",
                "title": page_title,
                "fieldRefs": _list(page_dict.get("fieldRefs") or page_dict.get("field_refs") or page_dict.get("fields")),
                "role": page_role,
            }, readonly=bool(page_dict.get("readonly")), slot_name=page_name)
            if direct_group:
                page_children.append(direct_group)
        if not page_children:
            continue
        if flatten_task_groups:
            children.extend([row for row in page_children if not skip_group_for_create(row)])
            continue
        tabs.append({
            "type": "page",
            "name": page_name,
            "string": page_title,
            "label": page_title,
            "formStructure": {
                "slot": page_name,
                "role": page_role,
            },
            "children": page_children,
            "sourceAuthority": {
                "kind": SOURCE_KIND,
                "runtime_carrier": "form_structure_contract",
                "projection_only": True,
                "no_business_fact_authority": True,
            },
        })
    if tabs:
        navigation = _dict(structure_contract.get("navigation"))
        notebook_title = _text(navigation.get("title") or structure_contract.get("taskTitle") or "业务办理", "业务办理")
        children.append({
            "type": "notebook",
            "name": "form_structure_task_tabs",
            "string": notebook_title,
            "label": notebook_title,
            "tabs": tabs,
            "sourceAuthority": {
                "kind": SOURCE_KIND,
                "runtime_carrier": "form_structure_contract",
                "projection_only": True,
                "no_business_fact_authority": True,
            },
        })
    if not children:
        return native_layout_rows
    sheet = {
        "type": "sheet",
        "name": "business_orchestrated_sheet",
        "string": page_title,
        "label": page_title,
        "children": children,
        "sourceAuthority": {
            "kind": SOURCE_KIND,
            "runtime_carrier": "form_structure_contract",
            "no_business_fact_authority": True,
        },
    }
    return header_rows + [sheet]


def _apply_form_structure_roles_to_tree(
    container_tree: list[dict[str, Any]],
    structure_contract: dict[str, Any],
) -> None:
    """Annotate native nodes without changing their structure or membership."""
    field_roles = _dict(structure_contract.get("fieldRoles") or structure_contract.get("field_roles"))
    if not field_roles:
        return

    def apply(node: dict[str, Any]) -> None:
        node_type = _text(node.get("type") or node.get("kind") or node.get("containerType")).lower()
        if node_type == "field":
            field_name = _text(node.get("name") or node.get("field") or node.get("fieldCode"))
            role = _dict(field_roles.get(field_name))
            if role:
                node["formStructureRole"] = deepcopy(role)
                for widget in _list(node.get("widgetList")):
                    if isinstance(widget, dict):
                        widget["formStructureRole"] = deepcopy(role)
        for key in ("children", "pages", "tabs", "nodes", "items"):
            for child in _list(node.get(key)):
                if isinstance(child, dict):
                    apply(child)

    for row in container_tree:
        if isinstance(row, dict):
            apply(row)


def _project_form_structure_to_layout(
    structure_contract: dict[str, Any],
    container_tree: list[dict[str, Any]],
    available_fields: set[str],
) -> dict[str, Any]:
    """Bind the semantic structure to fields owned by the final native tree."""
    projected_fields: set[str] = set()

    def collect(nodes: Any) -> None:
        for node in _list(nodes):
            if not isinstance(node, dict):
                continue
            if _text(node.get("type") or node.get("containerType")).lower() == "field":
                field_name = _text(node.get("name") or node.get("fieldCode"))
                if field_name:
                    projected_fields.add(field_name)
            collect(node.get("children"))

    collect(container_tree)
    out = deepcopy(structure_contract)

    def project_refs(value: Any, path: str) -> list[str]:
        refs: list[str] = []
        for raw in _list(value):
            field_name = _text(raw)
            if not field_name or field_name not in available_fields:
                raise ValueError(f"{path} references unknown field: {field_name or '<empty>'}")
            if field_name in projected_fields and field_name not in refs:
                refs.append(field_name)
        return refs

    for slot_index, slot in enumerate(_list(out.get("slots"))):
        if not isinstance(slot, dict):
            continue
        slot["fieldRefs"] = project_refs(
            slot.get("fieldRefs"), f"formStructureContract.slots[{slot_index}].fieldRefs",
        )
        for group_index, group in enumerate(_list(slot.get("groups"))):
            if not isinstance(group, dict):
                continue
            group["fieldRefs"] = project_refs(
                group.get("fieldRefs"),
                f"formStructureContract.slots[{slot_index}].groups[{group_index}].fieldRefs",
            )
    field_roles = _dict(out.get("fieldRoles"))
    out["fieldRoles"] = {
        field_name: deepcopy(role)
        for field_name, role in field_roles.items()
        if field_name in projected_fields
    }
    return out


def _form_structure_layout_columns(value: Any) -> int | None:
    try:
        columns = int(value)
    except (TypeError, ValueError):
        return None
    return columns if columns > 0 else None


def _form_structure_node_columns(node: dict[str, Any]) -> int | None:
    attrs = _dict(node.get("attributes") or node.get("attrs"))
    return (
        _form_structure_layout_columns(node.get("cols"))
        or _form_structure_layout_columns(node.get("columns"))
        or _form_structure_layout_columns(node.get("col"))
        or _form_structure_layout_columns(attrs.get("columns"))
        or _form_structure_layout_columns(attrs.get("cols"))
        or _form_structure_layout_columns(attrs.get("col"))
    )


def _form_structure_field_refs(node: dict[str, Any]) -> list[str]:
    refs: list[str] = []

    def collect(value: Any) -> None:
        for item in _list(value):
            if not isinstance(item, dict):
                continue
            node_type = _text(item.get("type") or item.get("kind")).lower()
            name = _text(item.get("name") or item.get("field"))
            if node_type == "field" and name and name not in refs:
                refs.append(name)
            for key in ("children", "pages", "tabs", "nodes", "items", "groups", "fields"):
                collect(item.get(key))

    collect(node.get("children"))
    return refs


def _apply_form_structure_columns_to_tree(container_tree: list[dict[str, Any]], structure_contract: dict[str, Any]) -> None:
    if not container_tree or not structure_contract:
        return
    default_columns = _form_structure_node_columns(structure_contract)
    group_policies: list[dict[str, Any]] = []
    for slot in _list(structure_contract.get("slots")):
        if not isinstance(slot, dict):
            continue
        for group in _list(slot.get("groups")):
            if not isinstance(group, dict):
                continue
            columns = _form_structure_node_columns(group)
            if not columns:
                continue
            group_policies.append({
                "title": _text(group.get("title") or group.get("label") or group.get("string") or group.get("name")),
                "fields": [
                    _text(item)
                    for item in _list(group.get("fieldRefs") or group.get("field_refs") or group.get("fields"))
                    if _text(item)
                ],
                "columns": columns,
            })

    def apply(node: dict[str, Any]) -> None:
        node_type = _text(node.get("type") or node.get("kind") or node.get("containerType")).lower()
        if node_type == "group":
            title = _text(node.get("string") or node.get("label") or node.get("title") or node.get("name"))
            node_fields = _form_structure_field_refs(node)
            columns = next(
                (
                    int(row["columns"])
                    for row in group_policies
                    if row.get("title") and row.get("title") == title
                ),
                None,
            )
            if columns is None and node_fields:
                node_field_set = set(node_fields)
                columns = next(
                    (
                        int(row["columns"])
                        for row in group_policies
                        if row.get("fields") and set(row.get("fields") or []) == node_field_set
                    ),
                    None,
                )
            columns = columns or default_columns
            if columns:
                node["cols"] = columns
                node["columns"] = columns
                attrs = _dict(node.get("attributes") or node.get("attrs"))
                attrs["col"] = str(columns)
                node["attributes"] = attrs
        for key in ("children", "pages", "tabs", "nodes", "items", "groups"):
            for child in _list(node.get(key)):
                if isinstance(child, dict):
                    apply(child)

    for row in container_tree:
        if isinstance(row, dict):
            apply(row)


def _is_attachment_field_name(name: str, fields_by_name: dict[str, dict[str, Any]]) -> bool:
    if not name:
        return False
    field = _dict(fields_by_name.get(name))
    field_type = _text(field.get("type") or field.get("ttype")).lower()
    relation = _text(field.get("relation") or field.get("comodel_name") or field.get("comodel")).lower()
    return name == "attachment_ids" or (field_type == "many2many" and relation == "ir.attachment")


def _remove_attachment_field_nodes(nodes: list[dict[str, Any]], fields_by_name: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_type = _text(node.get("type") or node.get("kind")).lower()
        node_name = _text(node.get("name") or node.get("field"))
        if node_type == "field" and _is_attachment_field_name(node_name, fields_by_name):
            continue
        next_node = deepcopy(node)
        for key in ("children", "pages", "tabs", "nodes", "items", "groups", "fields"):
            child_rows = next_node.get(key)
            if isinstance(child_rows, list):
                next_node[key] = _remove_attachment_field_nodes(
                    [row for row in child_rows if isinstance(row, dict)],
                    fields_by_name,
                )
        widgets = next_node.get("widgetList")
        if isinstance(widgets, list):
            next_node["widgetList"] = [
                widget
                for widget in widgets
                if not _is_attachment_field_name(_text(_dict(widget).get("fieldCode")), fields_by_name)
            ]
        cleaned.append(next_node)
    return cleaned


def _badge_count(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, list):
        return len(value)
    if isinstance(value, tuple):
        return len(value)
    if isinstance(value, str):
        text = value.strip()
        if text.isdigit():
            return int(text)
    return None


def _button_badge_count_source(
    badge: dict[str, Any],
    main_data: dict[str, Any],
    fields_by_name: dict[str, dict[str, Any]],
    layout_nodes: list[dict[str, Any]],
) -> tuple[int | None, str, str]:
    field_name = _text(badge.get("count_field") or badge.get("field") or badge.get("fieldCode"))
    badge_label = _text(badge.get("label"))
    if field_name and field_name in main_data:
        return _badge_count(main_data.get(field_name)), badge_label, field_name
    short_label = badge_label or field_name
    if short_label:
        short_label = re.sub(r"管理$", "", short_label).strip() or short_label
    def _matches_candidate(candidate_name: str, candidate_label: str) -> bool:
        return bool(short_label and (short_label in candidate_label or short_label in candidate_name))
    def _walk_layout(nodes: list[dict[str, Any]]):
        for row in nodes:
            if not isinstance(row, dict):
                continue
            row_type = _text(row.get("type") or row.get("kind")).lower()
            if row_type == "field":
                candidate_name = _text(row.get("name") or row.get("field"))
                candidate_meta = _dict(row.get("fieldInfo") or row.get("field_info"))
                candidate_label = _text(
                    row.get("label")
                    or row.get("string")
                    or candidate_meta.get("label")
                    or candidate_meta.get("string")
                    or candidate_name
                )
                candidate_type = _text(candidate_meta.get("type") or candidate_meta.get("ttype") or row.get("widget")).lower()
                if candidate_name in main_data and candidate_type in {"one2many", "many2many"} and _matches_candidate(candidate_name, candidate_label):
                    return candidate_name
            for key in ("children", "pages", "tabs", "nodes", "items"):
                child_rows = row.get(key)
                if isinstance(child_rows, list):
                    candidate = _walk_layout(child_rows)
                    if candidate:
                        return candidate
        return ""
    layout_candidate = _walk_layout(layout_nodes or [])
    if layout_candidate:
        return _badge_count(main_data.get(layout_candidate)), short_label, layout_candidate
    for candidate_name, candidate_meta in fields_by_name.items():
        candidate_type = _text(candidate_meta.get("type") or candidate_meta.get("ttype")).lower()
        if candidate_type not in {"one2many", "many2many"}:
            continue
        candidate_label = _text(candidate_meta.get("string") or candidate_meta.get("label") or candidate_name)
        if short_label and (short_label in candidate_label or short_label in candidate_name):
            return _badge_count(main_data.get(candidate_name)), short_label, candidate_name
    return None, short_label, ""


def _button_display_label(
    node: dict[str, Any],
    main_data: dict[str, Any],
    fields_by_name: dict[str, dict[str, Any]],
    layout_nodes: list[dict[str, Any]],
) -> str:
    action = _dict(node.get("action"))
    badge = _dict(action.get("badge") or node.get("badge"))
    field_name = _text(badge.get("field") or badge.get("fieldCode"))
    badge_label = _text(node.get("displayLabel") or action.get("displayLabel") or badge.get("label"))
    if not field_name and not badge_label:
        return ""
    count, resolved_label, source_field = _button_badge_count_source(badge, main_data, fields_by_name, layout_nodes)
    if count is None:
        return ""
    return f"{count}{resolved_label or badge_label}"


def _decorate_button_display_labels(
    nodes: list[dict[str, Any]],
    main_data: dict[str, Any],
    fields_by_name: dict[str, dict[str, Any]],
    layout_nodes: list[dict[str, Any]] | None = None,
) -> None:
    root_nodes = layout_nodes or nodes
    for node in nodes:
        if not isinstance(node, dict):
            continue
        if _text(node.get("type") or node.get("kind")).lower() == "button":
            action = _dict(node.get("action"))
            badge = _dict(action.get("badge") or node.get("badge"))
            count, resolved_label, source_field = _button_badge_count_source(badge, main_data, fields_by_name, root_nodes)
            if _text(badge.get("field")) and not _text(badge.get("count_field")):
                badge["count_field"] = _text(badge.get("field"))
            if source_field:
                badge["source_field"] = source_field
            if count is not None:
                display_label = f"{count}{resolved_label or _text(node.get('displayLabel') or action.get('displayLabel') or badge.get('label'))}"
                node["displayLabel"] = display_label
                action["displayLabel"] = display_label
            action["badge"] = badge
            if action:
                node["action"] = action
        for key in ("children", "pages", "tabs", "nodes", "items"):
            child_rows = node.get(key)
            if isinstance(child_rows, list) and child_rows:
                _decorate_button_display_labels(child_rows, main_data, fields_by_name, root_nodes)


def _ui_contract_data_source(
    *,
    model: str,
    view_type: str,
    fields: list[dict[str, Any]],
    record_id: int = 0,
    source: dict[str, Any] | None = None,
    ui: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not model:
        return {}
    field_names = _record_data_fields(fields)
    if "id" not in field_names:
        field_names.insert(0, "id")
    extra_params = _ui_data_source_extra_params(_dict(source), _dict(ui))
    source_authority = _data_source_authority(model=model, view_type=view_type)
    if view_type == "form":
        if record_id <= 0:
            return {
                "query": "api.data",
                "intent": "api.data",
                "cachePolicy": "none",
                "consistency": "strong",
                "sourceAuthority": source_authority,
                "params": {
                    "op": "default_get",
                    "model": model,
                    "fields": field_names[:80],
                    **extra_params,
                },
            }
        return {
            "query": "api.data",
            "intent": "api.data",
            "cachePolicy": "none",
            "consistency": "strong",
            "sourceAuthority": source_authority,
            "params": {
                "op": "read",
                "model": model,
                "ids": [record_id],
                "fields": field_names[:80],
                **extra_params,
            },
        }
    if view_type not in {"tree", "list", "kanban"}:
        return {}
    return {
        "query": "api.data",
        "intent": "api.data",
        "cachePolicy": "none",
        "consistency": "strong",
        "sourceAuthority": source_authority,
        "params": {
            "op": "list",
            "model": model,
            "fields": field_names[:40],
            "limit": 20,
            "offset": 0,
            "need_total": True,
            **extra_params,
        },
        "pagination": {
            "mode": "offset",
            "limit": 20,
            "offsetParam": "offset",
            "nextOffsetField": "next_offset",
            "totalField": "total",
        },
    }


def _data_source_authority(*, model: str, view_type: str) -> dict[str, Any]:
    return {
        "kind": SOURCE_KIND,
        "runtime_carrier": "ui.contract.v2.dataContract.dataSource",
        "projection_only": True,
        "no_business_fact_authority": True,
        "fact_authority": "odoo.model",
        "model": model,
        "view_type": view_type,
    }


def _metadata_projection_source_authority(*, runtime_carrier: str, source_key: str) -> dict[str, Any]:
    return {
        "kind": SOURCE_KIND,
        "runtime_carrier": runtime_carrier,
        "projection_only": True,
        "no_business_fact_authority": True,
        "formal_projection": True,
        "fact_authority": "source_contract_projection",
        "source_key": source_key,
    }


def _ui_data_source_extra_params(source: dict[str, Any], ui: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    source_meta = _dict(source.get("source_meta"))
    action = _dict(ui.get("action"))
    search = _dict(ui.get("search"))
    search_defaults = _dict(search.get("defaults"))
    for key in ("domain_raw", "domainRaw"):
        value = source.get(key) or source_meta.get(key) or ui.get(key) or action.get(key) or search_defaults.get(key)
        if _text(value):
            out["domain_raw"] = value
            break
    for key in ("context_raw", "contextRaw"):
        value = source.get(key) or source_meta.get(key) or ui.get(key) or action.get(key) or search_defaults.get(key)
        if _text(value):
            out["context_raw"] = value
            break
    domain = source.get("domain") or source_meta.get("domain") or ui.get("domain") or action.get("domain")
    if isinstance(domain, list):
        out.setdefault("domain", deepcopy(domain))
    context = source.get("context") or source_meta.get("context") or ui.get("context") or action.get("context")
    if isinstance(context, dict):
        out.setdefault("context", deepcopy(context))
    order = source.get("order") or source_meta.get("order") or ui.get("order") or search_defaults.get("order")
    if _text(order):
        out["order"] = _text(order)
    limit = source.get("limit") or source_meta.get("limit") or ui.get("limit") or search_defaults.get("limit")
    parsed_limit = _positive_int(limit, 0)
    if parsed_limit:
        out["limit"] = parsed_limit
    return out


def _ui_source_context(source: dict[str, Any], ui: dict[str, Any]) -> dict[str, Any]:
    transport = _ui_data_source_extra_params(source, ui)
    out = {
        key: deepcopy(value)
        for key, value in transport.items()
        if key in {"context", "domain", "order", "limit"}
    }
    if _text(transport.get("context_raw")):
        out["contextRaw"] = _text(transport.get("context_raw"))
    if _text(transport.get("domain_raw")):
        out["domainRaw"] = _text(transport.get("domain_raw"))
    source_meta = _dict(source.get("source_meta"))
    action = _dict(ui.get("action"))
    head = _dict(ui.get("head"))
    render_profile = _text(
        source.get("effective_render_profile")
        or source.get("effectiveRenderProfile")
        or source.get("render_profile")
        or source.get("renderProfile")
        or source_meta.get("render_profile")
        or source_meta.get("renderProfile")
        or ui.get("render_profile")
        or ui.get("renderProfile")
        or head.get("render_profile")
        or head.get("renderProfile")
        or action.get("render_profile")
        or action.get("renderProfile")
    ).lower()
    if render_profile in {"read", "view"}:
        render_profile = "readonly"
    if render_profile in {"create", "edit", "readonly"}:
        out["renderProfile"] = render_profile
    context = source.get("context") or source_meta.get("context") or ui.get("context") or head.get("context") or action.get("context")
    if isinstance(context, dict):
        out.setdefault("context", deepcopy(context))
    domain = source.get("domain") or source_meta.get("domain") or ui.get("domain") or head.get("domain") or action.get("domain")
    if isinstance(domain, list):
        out.setdefault("domain", deepcopy(domain))
    return out


def _ui_contract_permission_rights(source: dict[str, Any], ui: dict[str, Any]) -> dict[str, Any]:
    form_capabilities = _dict(_dict(_dict(ui.get("views")).get("form")).get("capabilities"))
    effective_record_capabilities = _dict(form_capabilities.get("effectiveRecordCapabilities"))
    if effective_record_capabilities:
        return effective_record_capabilities
    permission_sources = [
        _dict(_dict(ui.get("head")).get("permissions")),
        _dict(_dict(source.get("head")).get("permissions")),
        _dict(ui.get("permissions")),
        _dict(source.get("permissions")),
        _dict(source.get("permission_surface")),
    ]
    rights: dict[str, Any] = {}
    for row in permission_sources:
        resolved = resolve_permission_rights(row)
        if resolved:
            return resolved
    return rights


def _ui_contract_page_auth(source: dict[str, Any], ui: dict[str, Any], render_profile: str, view_type: str) -> str:
    rights = _ui_contract_permission_rights(source, ui)
    record_id = _positive_int(
        source.get("record_id")
        or source.get("recordId")
        or source.get("res_id")
        or source.get("resId")
        or ui.get("record_id")
        or ui.get("recordId"),
        0,
    )
    if record_id and rights.get("read") is not True:
        return "none"
    if render_profile == "create" and rights.get("create") is not True:
        return "none"
    if render_profile == "readonly":
        return "read" if rights.get("read") is True else "none"
    source_context = _ui_source_context(source, ui)
    context = _dict(source_context.get("context"))
    if (
        context.get("sc_runtime_user_management") is True
        and render_profile in {"create", "edit"}
    ):
        return "edit"
    if rights:
        return permission_auth_level(rights, fallback="read")
    if render_profile in {"create", "edit"}:
        return "edit"
    return "read" if view_type in {"tree", "list", "kanban"} else "edit"


def _append_standard_form_save_action(
    contract: dict[str, Any],
    source: dict[str, Any],
    ui: dict[str, Any],
    *,
    render_profile: str,
    layout_type: str,
) -> None:
    if layout_type != "form" or render_profile not in {"create", "edit"}:
        return
    rights = _ui_contract_permission_rights(source, ui)
    required_right = "create" if render_profile == "create" else "write"
    if rights.get(required_right) is not True:
        return
    action_id = "form.save"
    backend_identity = "contract_action:form.save"
    contract["actionContract"]["actionRuleList"].append({
        "actionId": action_id,
        "actionKey": action_id,
        "sourceActionKey": action_id,
        "backendIdentity": backend_identity,
        "label": "保存草稿" if render_profile == "create" else "保存修改",
        "intent": "api.data",
        "target": {},
        "button": {},
        "triggerType": "submit",
        "sourceWidgetId": "page.root",
        "targetIds": ["page.root"],
        "dispatchMode": "serverBlocking",
        "targetScope": "page",
        "refreshMode": "partial",
        "sourceChannel": "platform_form_action",
        "presentationAuthority": "platform_contract",
        "presentationPriority": 100,
        "presentation": {"tier": "secondary"},
        "visibleProfiles": [render_profile],
        "allowed": True,
        "enabled": True,
        "disabled": False,
        "entitlementEvaluated": True,
        "sourceTrace": [{
            "actionId": action_id,
            "sourceActionKey": action_id,
            "sourceWidgetId": "page.root",
            "sourceChannel": "platform_form_action",
            "presentationAuthority": "platform_contract",
            "requiredRight": required_right,
            "entitlementEvaluated": True,
        }],
    })
    contract["actionContract"]["dependencyGraph"].setdefault("page.root", []).append(action_id)
    contract["statusContract"]["buttonStatus"].append({
        "btnId": "btn.form.save",
        "backendIdentity": backend_identity,
        "visible": True,
        "disabled": False,
    })


def _default_values_from_context(context: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in context.items():
        if not isinstance(key, str) or not key.startswith("default_"):
            continue
        field_name = _stable_id(key[len("default_") :], "")
        if field_name:
            out[field_name] = deepcopy(value)
    return out


def _record_data_fields(fields: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    technical_prefixes = ("access_", "activity_", "message_", "website_")
    technical_fields = {"active", "create_date", "create_uid", "display_name", "write_date", "write_uid"}
    for field in fields:
        name = _stable_id(field.get("name"), "")
        if not name or name == "id" or name.startswith("__"):
            continue
        if name in technical_fields or any(name.startswith(prefix) for prefix in technical_prefixes):
            continue
        if name not in out:
            out.append(name)
    return out or ["display_name"]


def _positive_int(value: Any, fallback: int = 0) -> int:
    try:
        parsed = int(value)
        if parsed > 0:
            return parsed
    except Exception:
        pass
    return fallback


def _modifier_true(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value == 1
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes"}
    return False


def _field_modifier_constraint(field: dict[str, Any], key: str) -> tuple[bool, Any]:
    modifiers = _dict(field.get("modifiers"))
    attributes = _dict(field.get("attributes"))
    attribute_modifiers = _dict(attributes.get("modifiers"))
    for source in (modifiers, attribute_modifiers, field, attributes):
        if key in source:
            return True, source.get(key)
    return False, None


def _field_modifier_verdict(field: dict[str, Any], key: str, record: dict[str, Any]) -> tuple[bool, bool | None]:
    present, value = _field_modifier_constraint(field, key)
    if not present:
        return False, False
    return True, _evaluate_action_modifier(value, record, strict=True)


def _contextual_modifier_true(value: Any, context: dict[str, Any]) -> bool | None:
    if value is True:
        return True
    if value is False or value is None:
        return False if value is False else None
    if not isinstance(value, str):
        return None
    expr = value.strip()
    if not expr:
        return None
    static = expr.lower()
    if static in {"1", "true", "yes"}:
        return True
    if static in {"0", "false", "no"}:
        return False
    match = re.fullmatch(
        r"context\.get\(\s*['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]\s*\)\s*(==|!=)\s*['\"]([^'\"]*)['\"]",
        expr,
    )
    if not match:
        return None
    key, operator, expected = match.groups()
    actual = context.get(key)
    if operator == "==":
        return str(actual or "") == expected
    return str(actual or "") != expected


def _apply_contextual_invisible_modifier(node: dict[str, Any], context: dict[str, Any]) -> bool | None:
    attributes = _dict(node.get("attributes"))
    attribute_modifiers = _dict(attributes.get("modifiers"))
    modifiers = _dict(node.get("modifiers"))
    candidates = [
        node.get("invisible"),
        attributes.get("invisible"),
        attribute_modifiers.get("invisible"),
        modifiers.get("invisible"),
    ]
    resolved: bool | None = None
    for candidate in candidates:
        resolved = _contextual_modifier_true(candidate, context)
        if resolved is not None:
            break
    if resolved is None:
        return None
    node["invisible"] = resolved
    if attributes:
        attributes["invisible"] = resolved
        if attribute_modifiers:
            attribute_modifiers["invisible"] = resolved
            attributes["modifiers"] = attribute_modifiers
        node["attributes"] = attributes
    if modifiers:
        modifiers["invisible"] = resolved
        node["modifiers"] = modifiers
    return resolved


def _field_status(
    field: dict[str, Any],
    widget_id: str,
    *,
    context: dict[str, Any] | None = None,
    occurrence: bool = False,
) -> dict[str, Any]:
    if not occurrence:
        invisible_value = _field_modifier_constraint(field, "invisible")[1]
        column_invisible_value = _field_modifier_constraint(field, "column_invisible")[1]
        contextual_invisible = _contextual_modifier_true(invisible_value, context or {})
        contextual_column_invisible = _contextual_modifier_true(column_invisible_value, context or {})
        invisible = _modifier_true(invisible_value) if contextual_invisible is None else contextual_invisible
        column_invisible = (
            _modifier_true(column_invisible_value)
            if contextual_column_invisible is None
            else contextual_column_invisible
        )
        readonly = _modifier_true(_field_modifier_constraint(field, "readonly")[1])
        required = _modifier_true(_field_modifier_constraint(field, "required")[1])
        return {
            "widgetId": widget_id,
            "visible": not invisible and not column_invisible,
            "readonly": readonly,
            "required": required,
            "disabled": False,
            "auth": "read" if readonly else "edit",
        }
    record = context or {}
    _, invisible = _field_modifier_verdict(field, "invisible", record)
    _, column_invisible = _field_modifier_verdict(field, "column_invisible", record)
    _, readonly = _field_modifier_verdict(field, "readonly", record)
    _, required = _field_modifier_verdict(field, "required", record)
    unresolved = any(value is None for value in (invisible, column_invisible, readonly, required))
    visible = invisible is False and column_invisible is False
    readonly_value = readonly is not False
    required_value = required is not False
    return {
        "widgetId": widget_id,
        "visible": visible,
        "readonly": readonly_value,
        "required": required_value,
        "disabled": unresolved,
        "auth": "read" if readonly_value else "edit",
        **({"reasonCode": "NATIVE_MODIFIER_UNRESOLVED"} if unresolved else {}),
    }


def _append_actions(contract: dict[str, Any], rows: Any, *, source_widget_id: str) -> None:
    for row in _list(rows):
        if not isinstance(row, dict):
            continue
        source_key = _stable_id(row.get("key") or row.get("intent"), "action")
        key = source_key
        existing_action_ids = {
            _text(item.get("actionId"))
            for item in _list(_dict(contract.get("actionContract")).get("actionRuleList"))
            if isinstance(item, dict)
        }
        suffix = 2
        while f"action.{key}" in existing_action_ids:
            key = f"{source_key}.{suffix}"
            suffix += 1
        action_id = f"action.{key}"
        label = _text(row.get("label") or row.get("name") or row.get("title"), source_key)
        intent = _text(row.get("intent"), "ui.contract")
        source_id = _text(row.get("sourceWidgetId") or row.get("source_widget_id"), source_widget_id)
        action_rule = {
                "actionId": action_id,
                "actionKey": key,
                "sourceActionKey": source_key,
                "label": label,
                "intent": intent,
                "target": deepcopy(_dict(row.get("target"))),
                "button": deepcopy(_dict(row.get("button"))),
                "nativeIdentity": deepcopy(_dict(row.get("native_identity") or row.get("nativeIdentity"))),
                "triggerType": normalize_trigger_type(row.get("trigger") or row.get("display_mode")),
                "sourceWidgetId": source_id,
                "targetIds": [],
                "dispatchMode": "server",
                "targetScope": normalize_target_scope(row.get("target_scope") or row.get("level")),
                "refreshMode": "partial",
                "sourceChannel": _text(row.get("source_channel"), "contract_action"),
                "presentationAuthority": _text(row.get("presentation_authority"), "native_contract"),
                "presentationPriority": _positive_int(row.get("presentation_priority"), 100),
                "sourceTrace": [{
                "actionId": action_id,
                "sourceActionKey": source_key,
                "sourceWidgetId": source_id,
                    "label": label,
                    "sourceChannel": _text(row.get("source_channel"), "contract_action"),
                    "presentationAuthority": _text(row.get("presentation_authority"), "native_contract"),
                    "businessAvailable": row.get("business_available"),
                    "authorizationAllowed": row.get("authorization_allowed"),
                    "entitlementEvaluated": bool(row.get("entitlement_evaluated")),
                }],
            }
        # Native visibility/safety remains declarative.  Preserve it so the
        # product renderer can evaluate the same Odoo view conditions against
        # current form data instead of inventing action-specific branches.
        for source_key, target_key in (
            ("visible", "visible"),
            ("modifiers", "modifiers"),
            ("invisible", "invisible"),
            ("visible_profiles", "visibleProfiles"),
            ("presentation", "presentation"),
            ("action_safety", "actionSafety"),
            ("refresh_policy", "refreshPolicy"),
            ("allowed", "allowed"),
            ("enabled", "enabled"),
            ("disabled", "disabled"),
            ("permission_constraints", "permissionConstraints"),
            ("entitlement_evaluated", "entitlementEvaluated"),
        ):
            if row.get(source_key) is not None:
                action_rule[target_key] = deepcopy(row.get(source_key))
        contract["actionContract"]["actionRuleList"].append(action_rule)
        contract["actionContract"]["dependencyGraph"].setdefault(source_id, []).append(action_id)
        allowed = row.get("allowed") is not False
        enabled = row.get("enabled") is not False
        disabled = row.get("disabled") is True or not allowed or not enabled
        contract["statusContract"]["buttonStatus"].append({
            "btnId": f"btn.{key}",
            # Visibility and executability are independent only when the
            # action authority explicitly declares that visibility. Unknown
            # permission remains fail-closed.
            "visible": row.get("visible") is not False and (allowed or row.get("visible") is True),
            "disabled": disabled,
            **({"reasonCode": _text(row.get("reason_code"), "ACTION_NOT_ALLOWED")} if disabled else {}),
        })


def project_runtime_business_actions(contract: dict[str, Any]) -> dict[str, Any]:
    """Promote extension business actions into the canonical V2 action authority."""
    runtime = _dict(contract.get("runtimeContract"))
    business_actions = _list(runtime.get("businessActions"))
    if not business_actions:
        return contract

    existing_runtime_keys = {
        _text(trace.get("sourceActionKey") or trace.get("actionKey"))
        for rule in _list(_dict(contract.get("actionContract")).get("actionRuleList"))
        if isinstance(rule, dict)
        for trace in _list(rule.get("sourceTrace"))
        if isinstance(trace, dict) and _text(trace.get("sourceChannel")) == "runtime_business_action"
    }
    normalized = normalize_runtime_business_actions(
        business_actions,
        existing_keys=existing_runtime_keys,
    )

    if normalized:
        existing_rules = [
            row
            for row in _list(_dict(contract.get("actionContract")).get("actionRuleList"))
            if isinstance(row, dict)
        ]
        projected: list[dict[str, Any]] = []
        for runtime_action in normalized:
            runtime_button = _dict(runtime_action.get("button"))
            runtime_name = _text(runtime_button.get("name") or runtime_button.get("method"))
            runtime_type = _text(
                runtime_button.get("type") or runtime_button.get("buttonType"),
                "object",
            ).lower()
            native_occurrences = [
                row
                for row in existing_rules
                if runtime_name
                and _text(_dict(row.get("button")).get("name") or _dict(row.get("button")).get("method")) == runtime_name
                and _text(
                    _dict(row.get("button")).get("type") or _dict(row.get("button")).get("buttonType"),
                    "object",
                ).lower() == runtime_type
                and _dict(row.get("nativeIdentity") or row.get("native_identity")).get("authoritative") is True
                and _text(_dict(row.get("nativeIdentity") or row.get("native_identity")).get("native_locator"))
            ]
            if native_occurrences and not _dict(
                runtime_action.get("nativeIdentity") or runtime_action.get("native_identity")
            ):
                projected.extend({
                    **deepcopy(runtime_action),
                    "native_identity": deepcopy(
                        _dict(native_rule.get("nativeIdentity") or native_rule.get("native_identity"))
                    ),
                } for native_rule in native_occurrences)
            else:
                projected.append(runtime_action)
        _append_actions(contract, projected, source_widget_id="page.header")
        _merge_action_rules_by_backend_identity(contract)
    return contract


def _action_backend_identity(rule: dict[str, Any]) -> str:
    native_identity = _dict(rule.get("nativeIdentity") or rule.get("native_identity"))
    native_locator = _text(native_identity.get("native_locator"))
    if native_identity.get("authoritative") is True and native_locator:
        native_type = _text(native_identity.get("type"), "object").lower()
        native_name = _text(native_identity.get("name"), "anonymous")
        occurrence_index = _positive_int(native_identity.get("occurrence_index"), 1)
        return f"native_button:{native_type}:{native_name}:{native_locator}:{occurrence_index}"
    button = _dict(rule.get("button"))
    button_type = _text(button.get("type") or button.get("buttonType"), "object").lower()
    method = _text(button.get("name") or button.get("method"))
    if button_type in {"server", "server_action"}:
        server_action_id = _positive_int(button.get("server_action_id"), 0)
        if server_action_id:
            return f"server_action:{server_action_id}"
    # ``type=action`` names are Odoo action references, not model methods.
    # Keep the stable window-action identity so the same backend authority is
    # shared by Contract V2, Canonical presentation and execution.
    if method and button_type != "action":
        return f"button:{button_type}:{method}"
    target = _dict(rule.get("target"))
    raw_action_ref = _text(
        target.get("action_ref")
        or target.get("xml_id")
        or target.get("xmlid")
        or target.get("ref")
    )
    action_id = _positive_int(
        target.get("action_id") or target.get("actionId") or raw_action_ref,
        0,
    )
    if action_id:
        return f"window_action:{action_id}"
    if raw_action_ref:
        return f"window_action_ref:{raw_action_ref}"
    url = _text(target.get("url"))
    route = _text(target.get("route"))
    if url:
        return f"url:{url}"
    if route:
        return f"route:{route}"
    stable_target = {
        key: target.get(key)
        for key in ("url", "route", "target", "model", "view_type", "mode", "client_mode")
        if target.get(key) not in (None, "")
    }
    if set(stable_target) == {"view_type"}:
        stable_target = {}
    if stable_target:
        return "target:" + json.dumps(stable_target, ensure_ascii=False, sort_keys=True, default=str)
    return "contract_action:" + _text(rule.get("actionId") or rule.get("actionKey"), "unknown")


def _native_layout_action_backend_identity(action: dict[str, Any]) -> str:
    payload = _dict(action.get("payload"))
    kind = _text(action.get("kind") or action.get("type")).lower()
    intent = _text(action.get("intent")).lower()
    action_id = _positive_int(payload.get("action_id") or action.get("action_id"), 0)
    if kind in {"open", "url"} or intent in {"open", "url"} or action_id:
        return _action_backend_identity({
            "nativeIdentity": deepcopy(_dict(action.get("native_identity") or action.get("nativeIdentity"))),
            "target": {
                "action_id": action_id,
                "action_ref": payload.get("ref") or action.get("ref"),
                "xml_id": payload.get("xml_id") or action.get("xml_id"),
                "url": payload.get("url") or action.get("url"),
                "route": payload.get("route") or action.get("route"),
            },
        })
    return _action_backend_identity({
        "nativeIdentity": deepcopy(_dict(action.get("native_identity") or action.get("nativeIdentity"))),
        "button": {
            "name": _text(action.get("name") or action.get("method_name") or payload.get("method")),
            "type": _text(action.get("button_type") or payload.get("type") or action.get("type"), "object"),
        },
    })


def _bind_native_layout_action_references(contract: dict[str, Any]) -> None:
    rules = {
        _text(rule.get("backendIdentity")): rule
        for rule in _list(_dict(contract.get("actionContract")).get("actionRuleList"))
        if isinstance(rule, dict) and _text(rule.get("backendIdentity"))
    }
    container_tree = _list(_dict(contract.get("layoutContract")).get("containerTree"))
    for node in _walk_native_nodes(container_tree):
        if _text(node.get("type") or node.get("containerType")).lower() != "button":
            continue
        action = _dict(node.get("action"))
        identity = _native_layout_action_backend_identity(action)
        rule = rules.get(identity)
        if not rule:
            continue
        node["action"] = {
            **action,
            "backendIdentity": identity,
            "actionId": _text(rule.get("actionId")),
        }


def _action_invisible_constraint(rule: dict[str, Any]) -> Any:
    visible = _dict(rule.get("visible"))
    visible_attrs = _dict(visible.get("attrs"))
    modifiers = _dict(rule.get("modifiers"))
    for value in (rule.get("invisible"), modifiers.get("invisible"), visible_attrs.get("invisible")):
        if value not in (None, False, "", 0):
            return deepcopy(value)
    if (
        (rule.get("allowed") is False and rule.get("visible") is not True)
        or rule.get("visible") is False
    ):
        return {"kind": "static", "value": True}
    return None


def _action_permission_clause(row: dict[str, Any]) -> dict[str, Any]:
    aliases = {
        "requiredGroups": (
            "requiredGroups", "required_groups", "required_groups_xmlids",
            "groups", "groups_id", "groups_xmlids",
        ),
        "allowedRoles": (
            "allowedRoles", "allowed_roles", "allowed_role_codes",
        ),
        "allowedUsers": (
            "allowedUsers", "allowed_users", "allowed_user_ids",
            "required_users", "required_user_ids", "required_user_id", "required_user",
        ),
    }
    clause: dict[str, Any] = {}
    existing = _dict(row.get("permissionConstraints"))
    for target, keys in aliases.items():
        values: list[str] = []
        for key in keys:
            raw = row.get(key)
            if raw is None:
                raw = existing.get(key) or existing.get(target)
            for item in raw if isinstance(raw, list) else [raw] if raw not in (None, "") else []:
                value = _text(item)
                if value and value not in values:
                    values.append(value)
        if values:
            clause[target] = values
    if clause and "entitlement_evaluated" in row:
        clause["entitlementEvaluated"] = bool(row.get("entitlement_evaluated"))
    return clause


def _action_presentation_priority(row: dict[str, Any]) -> int:
    return _positive_int(row.get("presentationPriority"), 100)


def _merge_action_rules_by_backend_identity(contract: dict[str, Any]) -> None:
    action_contract = _dict(contract.get("actionContract"))
    rows = [deepcopy(row) for row in _list(action_contract.get("actionRuleList")) if isinstance(row, dict)]
    if not rows:
        return
    merged: list[dict[str, Any]] = []
    by_identity: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(rows):
        identity = _action_backend_identity(row)
        synthesized_trace = {
            "actionId": _text(row.get("actionId")),
            "actionKey": _text(row.get("actionKey")),
            "sourceActionKey": _text(row.get("sourceActionKey") or row.get("actionKey")),
            "sourceWidgetId": _text(row.get("sourceWidgetId")),
            "label": _text(row.get("label")),
            "sequence": index,
            "sourceChannel": _text(row.get("sourceChannel")),
            "presentationAuthority": _text(row.get("presentationAuthority"), "native_contract"),
            "button": deepcopy(_dict(row.get("button"))),
            "target": deepcopy(_dict(row.get("target"))),
            "constraints": {
                key: deepcopy(row.get(key))
                for key in (
                    "allowed", "enabled", "disabled", "business_available", "authorization_allowed",
                    "visible", "modifiers", "invisible", "visibleProfiles",
                )
                if row.get(key) is not None
            },
            "permissionConstraints": deepcopy(_dict(row.get("permissionConstraints"))),
            "entitlementEvaluated": bool(row.get("entitlement_evaluated")),
            "reasonCode": _text(row.get("reasonCode") or row.get("reason_code")),
        }
        existing_trace = [
            {**synthesized_trace, **deepcopy(item)}
            for item in _list(row.get("sourceTrace"))
            if isinstance(item, dict)
        ]
        trace_rows = existing_trace or [synthesized_trace]
        existing_permission = _dict(row.get("permissionConstraints"))
        permission_clauses = [
            deepcopy(item)
            for item in _list(existing_permission.get("clauses"))
            if isinstance(item, dict)
        ]
        if not permission_clauses:
            permission_clause = _action_permission_clause(row)
            if permission_clause:
                permission_clauses.append(permission_clause)
        if permission_clauses:
            row["permissionConstraints"] = {
                "policy": "all_sources_must_allow",
                "clauses": permission_clauses,
            }
        if identity not in by_identity:
            row["backendIdentity"] = identity
            row["sourceTrace"] = trace_rows
            by_identity[identity] = row
            merged.append(row)
            continue
        current = by_identity[identity]
        current.setdefault("sourceTrace", []).extend(trace_rows)
        if permission_clauses:
            current_permission = _dict(current.get("permissionConstraints"))
            clauses = [
                deepcopy(item)
                for item in _list(current_permission.get("clauses"))
                if isinstance(item, dict)
            ]
            clauses.extend(permission_clauses)
            current["permissionConstraints"] = {
                "policy": "all_sources_must_allow",
                "clauses": clauses,
            }
        constraints = [
            value
            for value in (_action_invisible_constraint(current), _action_invisible_constraint(row))
            if value not in (None, False, "", 0)
        ]
        if constraints:
            invisible = constraints[0] if len(constraints) == 1 else {"kind": "any", "exprs": constraints}
            current["visible"] = {"attrs": {"invisible": invisible}}
            current.pop("invisible", None)
            current.pop("modifiers", None)
        profile_sets = [
            {str(item) for item in _list(candidate.get("visibleProfiles")) if str(item)}
            for candidate in (current, row)
            if candidate.get("visibleProfiles") is not None
        ]
        if profile_sets:
            current["visibleProfiles"] = sorted(set.intersection(*profile_sets))
        current["allowed"] = current.get("allowed", True) is not False and row.get("allowed", True) is not False
        current["enabled"] = current.get("enabled", True) is not False and row.get("enabled", True) is not False
        current["disabled"] = current.get("disabled", False) is True or row.get("disabled", False) is True
        current_safety = _dict(current.get("actionSafety"))
        incoming_safety = _dict(row.get("actionSafety"))
        if incoming_safety.get("classification") == "danger" or current_safety.get("classification") == "danger":
            stricter = incoming_safety if incoming_safety.get("classification") == "danger" else current_safety
            current["actionSafety"] = {
                **current_safety,
                **incoming_safety,
                **stricter,
                "classification": "danger",
                "requires_confirm": bool(
                    current_safety.get("requires_confirm") or incoming_safety.get("requires_confirm")
                ),
            }
        if not _dict(current.get("refreshPolicy")) and _dict(row.get("refreshPolicy")):
            current["refreshPolicy"] = deepcopy(row.get("refreshPolicy"))
        if _action_presentation_priority(row) > _action_presentation_priority(current):
            current["label"] = _text(row.get("label"), _text(current.get("label")))
            if _dict(row.get("presentation")):
                incoming_presentation = deepcopy(_dict(row.get("presentation")))
                native_icon = _text(_dict(current.get("presentation")).get("icon"))
                if native_icon and not _text(incoming_presentation.get("icon")):
                    incoming_presentation["icon"] = native_icon
                current["presentation"] = incoming_presentation
            current["presentationAuthority"] = _text(row.get("presentationAuthority"), "product_contract")
            current["presentationPriority"] = _action_presentation_priority(row)
        elif not _dict(current.get("presentation")) and _dict(row.get("presentation")):
            current["presentation"] = deepcopy(row.get("presentation"))
    action_contract["actionRuleList"] = merged
    source_action_to_winner: dict[str, str] = {}
    source_key_to_identity: dict[str, str] = {}
    for row in merged:
        winner_id = _text(row.get("actionId"))
        identity = _text(row.get("backendIdentity"))
        for trace in _list(row.get("sourceTrace")):
            if not isinstance(trace, dict):
                continue
            source_id = _text(trace.get("actionId"))
            source_key = _text(trace.get("actionKey"))
            if source_id and winner_id:
                source_action_to_winner[source_id] = winner_id
            if source_key and identity:
                source_key_to_identity[source_key] = identity
    graph = _dict(action_contract.get("dependencyGraph"))
    action_contract["dependencyGraph"] = {
        source: list(dict.fromkeys(
            source_action_to_winner.get(_text(target), _text(target))
            for target in _list(targets)
            if _text(target)
        ))
        for source, targets in graph.items()
    }
    action_contract["identityPolicy"] = {
        "version": "2.0.0",
        "object": "button_type_and_backend_method",
        "window": "action_id",
        "url": "absolute_url_or_route",
        "target": "stable_target_identity",
        "constraintMerge": "fail_closed",
        "presentationPrecedence": "highest_declared_authority",
    }
    contract["actionContract"] = action_contract
    statuses = _list(_dict(contract.get("statusContract")).get("buttonStatus"))
    status_by_identity: dict[str, dict[str, Any]] = {}
    passthrough_statuses: list[dict[str, Any]] = []
    for status in statuses:
        if not isinstance(status, dict):
            continue
        btn_id = _text(status.get("btnId"))
        key = btn_id[4:] if btn_id.startswith("btn.") else ""
        identity = source_key_to_identity.get(key, "")
        if not identity:
            passthrough_statuses.append(status)
            continue
        if identity not in status_by_identity:
            status_by_identity[identity] = {**status, "backendIdentity": identity}
            continue
        current = status_by_identity[identity]
        current["visible"] = current.get("visible", True) is not False and status.get("visible", True) is not False
        current["disabled"] = current.get("disabled", False) is True or status.get("disabled", False) is True
        if not current.get("reasonCode") and status.get("reasonCode"):
            current["reasonCode"] = status.get("reasonCode")
    rules_by_identity = {
        _text(row.get("backendIdentity")): row
        for row in merged
        if _text(row.get("backendIdentity"))
    }
    for identity, status in status_by_identity.items():
        rule = rules_by_identity.get(identity) or {}
        denied = (
            rule.get("allowed") is False
            or rule.get("enabled") is False
            or rule.get("disabled") is True
        )
        if denied:
            status["visible"] = (
                True if rule.get("visible") is True
                else status.get("visible", True) is not False and rule.get("allowed") is not False
            )
            status["disabled"] = True
            trace_reason = next(
                (
                    _text(trace.get("reasonCode") or trace.get("reason_code"))
                    for trace in _list(rule.get("sourceTrace"))
                    if isinstance(trace, dict)
                    and _text(trace.get("reasonCode") or trace.get("reason_code")) not in {"", "OK"}
                ),
                "",
            )
            if _text(status.get("reasonCode")) in {"", "OK"}:
                status["reasonCode"] = trace_reason or "ACTION_NOT_ALLOWED"
    contract["statusContract"]["buttonStatus"] = [*status_by_identity.values(), *passthrough_statuses]
    _enforce_single_effective_primary_action(contract)


def _demote_native_inherited_actions_to_overflow(contract: dict[str, Any]) -> None:
    """无产品身份的操作默认收敛到 overflow，不进入产品主操作区。

    判断标准唯一是「产品身份」：presentationAuthority 为 product_contract、
    或已显式声明 tier 的操作都有产品身份，保留在主操作区；其余来自原生
    继承、既无产品身份也无显式 tier 的操作（如平台模块的 Download vCard/
    发短信/授权门户/隐私查询等）统一降级为 overflow——「没有产品身份的
    操作默认不进入产品主界面」。不管技术上是否原生，产品身份唯一确定。
    """
    action_contract = _dict(contract.get("actionContract"))
    rows = _list(action_contract.get("actionRuleList"))
    for row in rows:
        if not isinstance(row, dict):
            continue
        authority = _text(row.get("presentationAuthority"), "native_contract").lower()
        if authority == "product_contract":
            continue
        presentation = _dict(row.get("presentation"))
        tier = _text(presentation.get("tier")).lower()
        if tier in {"primary", "secondary", "overflow", "configuration"}:
            continue
        row["presentation"] = {**presentation, "tier": "overflow"}


def _compare_action_value(actual: Any, operator: str, expected: Any) -> bool | None:
    left = actual[0] if isinstance(actual, (list, tuple)) and actual else actual
    if operator in {"=", "=="}:
        return left == expected
    if operator in {"!=", "<>"}:
        return left != expected
    if operator == "in":
        if not isinstance(expected, (list, tuple, set)):
            return None
        return left in expected
    if operator == "not in":
        if not isinstance(expected, (list, tuple, set)):
            return None
        return left not in expected
    try:
        if operator == ">":
            return left > expected
        if operator == ">=":
            return left >= expected
        if operator == "<":
            return left < expected
        if operator == "<=":
            return left <= expected
    except (TypeError, ValueError):
        return None
    return None


def _evaluate_action_modifier(value: Any, record: dict[str, Any], *, strict: bool = False) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None or value == "":
        return None if strict else False
    if value in (0, "0", "false", "False"):
        return False
    if value in (1, "1", "true", "True"):
        return True
    if not isinstance(value, dict):
        return None if strict else False
    kind = _text(value.get("kind"))
    if kind == "static":
        static_value = value.get("value")
        return static_value if isinstance(static_value, bool) else (None if strict else False)
    if kind == "not":
        resolved = _evaluate_action_modifier(value.get("expr"), record, strict=strict)
        return None if resolved is None else not resolved
    if kind in {"all", "any"}:
        values = [_evaluate_action_modifier(item, record, strict=strict) for item in _list(value.get("exprs"))]
        if kind == "all":
            if False in values:
                return False
            return True if values and all(item is True for item in values) else None
        if True in values:
            return True
        return False if values and all(item is False for item in values) else None
    field = _text(value.get("field"))
    if not field or field not in record:
        return None if strict else False
    if kind == "field_truthy":
        return bool(record.get(field))
    if kind == "field_compare":
        value_field = _text(value.get("value_field"))
        if value_field:
            if value_field not in record:
                return None if strict else False
            expected = record.get(value_field)
        else:
            expected = value.get("value")
        compared = _compare_action_value(record.get(field), _text(value.get("operator")), expected)
        return compared if strict or compared is not None else False
    return None if strict else False


def _enforce_single_effective_primary_action(contract: dict[str, Any]) -> None:
    action_contract = _dict(contract.get("actionContract"))
    rows = _list(action_contract.get("actionRuleList"))
    record = _dict(_dict(contract.get("dataContract")).get("mainData"))
    previous_resolution = _dict(action_contract.pop("primaryResolution", {}))
    previously_demoted = {
        _text(item.get("actionId"))
        for item in _list(previous_resolution.get("demoted"))
        if isinstance(item, dict) and _text(item.get("previousTier")).lower() == "primary"
    }
    for row in rows:
        if isinstance(row, dict) and _text(row.get("actionId")) in previously_demoted:
            row["presentation"] = {**_dict(row.get("presentation")), "tier": "primary"}
    status_by_btn_id = {
        _text(status.get("btnId")): status
        for status in _list(_dict(contract.get("statusContract")).get("buttonStatus"))
        if isinstance(status, dict) and _text(status.get("btnId"))
    }
    status_by_identity = {
        _text(status.get("backendIdentity")): status
        for status in status_by_btn_id.values()
        if _text(status.get("backendIdentity"))
    }
    effective: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict) or _text(_dict(row.get("presentation")).get("tier")).lower() != "primary":
            continue
        if row.get("allowed") is False or row.get("enabled") is False or row.get("disabled") is True:
            continue
        action_key = _text(row.get("actionKey"))
        status = status_by_identity.get(_text(row.get("backendIdentity"))) or status_by_btn_id.get(f"btn.{action_key}")
        if status and (status.get("visible") is False or status.get("disabled") is True):
            continue
        invisible = _action_invisible_constraint(row)
        verdict = _evaluate_action_modifier(invisible, record) if invisible is not None else False
        if verdict is False:
            effective.append(row)
    if len(effective) <= 1:
        return
    # Presentation authority is already normalized into a numeric priority.
    # Select the strongest declared authority while preserving source order
    # for equal priorities; array order alone must not override product facts.
    winner = max(effective, key=_action_presentation_priority)
    conflicts = []
    for row in effective:
        if row is winner:
            continue
        presentation = _dict(row.get("presentation"))
        row["presentation"] = {**presentation, "tier": "secondary"}
        conflicts.append({
            "backendIdentity": row.get("backendIdentity"),
            "actionId": row.get("actionId"),
            "previousTier": "primary",
            "effectiveTier": "secondary",
        })
    action_contract["primaryResolution"] = {
        "policy": "single_effective_primary_per_record_state",
        "winner": winner.get("backendIdentity") or winner.get("actionId"),
        "demoted": conflicts,
    }


def hydrate_final_action_modifier_status(contract: dict[str, Any]) -> None:
    """Seal action visibility after late modifier dependencies are hydrated."""
    action_contract = _dict(contract.get("actionContract"))
    status_contract = _dict(contract.get("statusContract"))
    rows = _list(action_contract.get("actionRuleList"))
    statuses = _list(status_contract.get("buttonStatus"))
    record = _dict(_dict(contract.get("dataContract")).get("mainData"))
    status_by_btn_id = {
        _text(status.get("btnId")): status
        for status in statuses
        if isinstance(status, dict) and _text(status.get("btnId"))
    }
    status_by_identity = {
        _text(status.get("backendIdentity")): status
        for status in statuses
        if isinstance(status, dict) and _text(status.get("backendIdentity"))
    }
    runtime_business_by_button: dict[tuple[str, str], dict[str, Any]] = {}
    for candidate in rows:
        if not isinstance(candidate, dict):
            continue
        source_channels = {
            _text(candidate.get("sourceChannel")),
            *(
                _text(trace.get("sourceChannel"))
                for trace in _list(candidate.get("sourceTrace"))
                if isinstance(trace, dict)
            ),
        }
        if "runtime_business_action" not in source_channels:
            continue
        button = _dict(candidate.get("button"))
        button_name = _text(button.get("name") or button.get("method"))
        if not button_name:
            continue
        button_type = _text(button.get("type") or button.get("buttonType"), "object").lower()
        runtime_business_by_button[(button_type, button_name)] = candidate
    for row in rows:
        if not isinstance(row, dict):
            continue
        button = _dict(row.get("button"))
        button_name = _text(button.get("name") or button.get("method"))
        button_type = _text(button.get("type") or button.get("buttonType"), "object").lower()
        runtime_business = runtime_business_by_button.get((button_type, button_name)) if button_name else None
        if runtime_business is not None and runtime_business is not row:
            for field_name in (
                "businessAvailable", "authorizationAllowed", "entitlementEvaluated",
                "allowed", "enabled", "disabled",
            ):
                value = runtime_business.get(field_name)
                if isinstance(value, bool):
                    row[field_name] = value
            if _dict(runtime_business.get("actionSafety")):
                row["actionSafety"] = deepcopy(runtime_business.get("actionSafety"))
            if _dict(runtime_business.get("refreshPolicy")):
                row["refreshPolicy"] = deepcopy(runtime_business.get("refreshPolicy"))
            if _text(runtime_business.get("reasonCode")):
                row["reasonCode"] = runtime_business.get("reasonCode")
        invisible = _action_invisible_constraint(row)
        if invisible is None:
            continue
        action_key = _text(row.get("actionKey"))
        btn_id = f"btn.{action_key}"
        status = status_by_identity.get(_text(row.get("backendIdentity"))) or status_by_btn_id.get(btn_id)
        if status is None:
            status = {"btnId": btn_id, "visible": True, "disabled": False}
            statuses.append(status)
            status_by_btn_id[btn_id] = status
        verdict = _evaluate_action_modifier(invisible, record, strict=True)
        if verdict is True:
            status["visible"] = False
            status.setdefault("reasonCode", "ACTION_NOT_VISIBLE_IN_STATE")
        elif verdict is None:
            status["visible"] = False
            status["disabled"] = True
            status["reasonCode"] = "ACTION_VISIBILITY_UNRESOLVED"
        else:
            status["visible"] = True
            evaluated_traces = [
                trace for trace in _list(row.get("sourceTrace"))
                if isinstance(trace, dict) and trace.get("entitlementEvaluated") is True
            ]
            authorization_results = [
                trace.get("authorizationAllowed") for trace in evaluated_traces
                if isinstance(trace.get("authorizationAllowed"), bool)
            ]
            modifier_authoritative = (
                _text(row.get("sourceChannel")) == "native_form_header"
                and _text(_dict(row.get("button")).get("type")) == "object"
                and bool(_text(_dict(row.get("nativeIdentity")).get("native_locator")))
            )
            # 原生 header object 按钮（工作流/提交类）的权限由 Odoo 原生评估，
            # allowed/enabled/disabled 均已确定；其 sourceTrace 未显式标记
            # entitlementEvaluated 属装配缺口。此处对权限已解析且允许的原生
            # 按钮补记 entitlement 评估，使前端 explicitAuthority 契约校验通过，
            # 避免合法的产品主操作（如提交审批）被 explicitAuthority 误过滤。
            permission_resolved = (
                isinstance(row.get("allowed"), bool)
                and isinstance(row.get("enabled"), bool)
                and isinstance(row.get("disabled"), bool)
            )
            entitlement_evaluated = (
                row.get("entitlementEvaluated") is True
                or bool(evaluated_traces)
                or (modifier_authoritative and permission_resolved)
            )
            authorization_allowed = (
                row.get("authorizationAllowed") is True
                or row.get("allowed") is True
                or (bool(authorization_results) and all(result is True for result in authorization_results))
            )
            if (
                runtime_business is None
                and modifier_authoritative
                and entitlement_evaluated
                and authorization_allowed
            ):
                row["businessAvailable"] = True
                row["authorizationAllowed"] = True
                row["entitlementEvaluated"] = True
                row["allowed"] = True
                row["enabled"] = True
                row["disabled"] = False
                status["disabled"] = False
                if _text(status.get("reasonCode")) in {
                    "ACTION_NOT_ALLOWED", "ACTION_NOT_VISIBLE_IN_STATE", "ACTION_VISIBILITY_UNRESOLVED",
                }:
                    status.pop("reasonCode", None)
            elif runtime_business is not None:
                denied = (
                    row.get("allowed") is False
                    or row.get("enabled") is False
                    or row.get("disabled") is True
                )
                status["disabled"] = denied
                if denied:
                    status["reasonCode"] = _text(row.get("reasonCode"), "ACTION_NOT_ALLOWED")
                elif _text(status.get("reasonCode")) in {
                    "ACTION_NOT_ALLOWED", "ACTION_NOT_VISIBLE_IN_STATE", "ACTION_VISIBILITY_UNRESOLVED",
                }:
                    status.pop("reasonCode", None)
    status_contract["buttonStatus"] = statuses
    contract["statusContract"] = status_contract
    _enforce_single_effective_primary_action(contract)


def hydrate_final_layout_modifier_status(contract: dict[str, Any]) -> None:
    """Resolve native field/container visibility against final record data.

    Native view modifiers remain attached to the normalized node tree.  This
    final pass runs after modifier dependencies are hydrated, so Canonical
    consumers receive the same ancestor visibility verdict as the Odoo form.
    Unknown dynamic predicates fail closed.
    """
    if not isinstance(contract, dict):
        return
    layout = _dict(contract.get("layoutContract"))
    tree = _list(layout.get("containerTree"))
    status_contract = _dict(contract.get("statusContract"))
    record = _dict(_dict(contract.get("dataContract")).get("mainData"))
    container_statuses = _list(status_contract.get("containerStatus"))
    widget_statuses = _list(status_contract.get("widgetStatus"))
    container_by_id = {
        _text(row.get("containerId")): row
        for row in container_statuses
        if isinstance(row, dict) and _text(row.get("containerId"))
    }
    widget_by_id = {
        _text(row.get("widgetId")): row
        for row in widget_statuses
        if isinstance(row, dict) and _text(row.get("widgetId"))
    }

    def visit(value: Any) -> None:
        if isinstance(value, list):
            for item in value:
                visit(item)
            return
        if not isinstance(value, dict):
            return
        node_type = _text(value.get("type") or value.get("containerType")).lower()
        if node_type == "field":
            widget_id = _text(value.get("widgetId") or f"field.{_text(value.get('name'))}")
            status = widget_by_id.get(widget_id)
            if isinstance(status, dict):
                if ".occ." not in widget_id:
                    present, constraint = _field_modifier_constraint(value, "invisible")
                    if present:
                        verdict = _evaluate_action_modifier(constraint, record, strict=True)
                        if verdict is True:
                            status["visible"] = False
                            status.setdefault("reasonCode", "NATIVE_MODIFIER_INVISIBLE")
                        elif verdict is False:
                            status["visible"] = True
                            if status.get("reasonCode") in {"NATIVE_MODIFIER_INVISIBLE", "NATIVE_MODIFIER_UNRESOLVED"}:
                                status.pop("reasonCode", None)
                        else:
                            status["visible"] = False
                            status["disabled"] = True
                            status["reasonCode"] = "NATIVE_MODIFIER_UNRESOLVED"
                    for key in ("children", "pages", "tabs", "nodes", "items"):
                        visit(value.get(key))
                    return
                _, invisible = _field_modifier_verdict(value, "invisible", record)
                _, column_invisible = _field_modifier_verdict(value, "column_invisible", record)
                _, readonly = _field_modifier_verdict(value, "readonly", record)
                _, required = _field_modifier_verdict(value, "required", record)
                unresolved = any(item is None for item in (invisible, column_invisible, readonly, required))
                status["visible"] = invisible is False and column_invisible is False
                status["readonly"] = readonly is not False
                status["required"] = required is not False
                status["disabled"] = unresolved
                status["auth"] = "read" if status["readonly"] else "edit"
                if unresolved:
                    status["reasonCode"] = "NATIVE_MODIFIER_UNRESOLVED"
                elif not status["visible"]:
                    status["reasonCode"] = "NATIVE_MODIFIER_INVISIBLE"
                elif status.get("reasonCode") in {"NATIVE_MODIFIER_INVISIBLE", "NATIVE_MODIFIER_UNRESOLVED"}:
                    status.pop("reasonCode", None)
        else:
            present, constraint = _field_modifier_constraint(value, "invisible")
            if present:
                verdict = _evaluate_action_modifier(constraint, record, strict=True)
                container_id = _text(value.get("containerId"))
                status = container_by_id.get(container_id)
                if isinstance(status, dict):
                    if verdict is True:
                        status["visible"] = False
                        status.setdefault("reasonCode", "NATIVE_MODIFIER_INVISIBLE")
                    elif verdict is False:
                        status["visible"] = True
                        if status.get("reasonCode") in {"NATIVE_MODIFIER_INVISIBLE", "NATIVE_MODIFIER_UNRESOLVED"}:
                            status.pop("reasonCode", None)
                    else:
                        status["visible"] = False
                        status["disabled"] = True
                        status["reasonCode"] = "NATIVE_MODIFIER_UNRESOLVED"
        for key in ("children", "pages", "tabs", "nodes", "items"):
            visit(value.get(key))

    visit(tree)
    status_contract["containerStatus"] = container_statuses
    status_contract["widgetStatus"] = widget_statuses
    contract["statusContract"] = status_contract


def _append_action_schema(contract: dict[str, Any], actions: dict[str, Any], *, source_widget_id: str) -> None:
    for key, row in actions.items():
        action_key = _stable_id(key, "action")
        action_id = f"action.{action_key}"
        source_row = _dict(row)
        contract["actionContract"]["actionRuleList"].append(
            {
                "actionId": action_id,
                "actionKey": action_key,
                "label": _text(source_row.get("label") or source_row.get("name") or source_row.get("title"), action_key),
                "intent": _text(source_row.get("intent"), "ui.contract"),
                "target": deepcopy(_dict(source_row.get("target"))),
                "button": deepcopy(_dict(source_row.get("button"))),
                "triggerType": "click",
                "sourceWidgetId": source_widget_id,
                "targetIds": [],
                "dispatchMode": "server",
                "targetScope": "page",
                "refreshMode": "partial",
            }
        )
        contract["statusContract"]["buttonStatus"].append({"btnId": f"btn.{action_key}", "visible": True, "disabled": False})


def _governed_platform_action_group_rows(ui: dict[str, Any]) -> list[dict[str, Any]]:
    """Return only P0-local mode actions from their single governed carrier."""
    rows: list[dict[str, Any]] = []
    for raw_group in _list(ui.get("action_groups")):
        group = _dict(raw_group)
        authority = _dict(group.get("source_authority"))
        if not (
            authority.get("projection_only") is True
            and authority.get("no_business_fact_authority") is True
            and _text(authority.get("owner_layer")) == "business_view_orchestration"
        ):
            continue
        for raw_action in _list(group.get("actions")):
            action = _dict(raw_action)
            intent = _text(action.get("intent"))
            source_widget_id = _text(action.get("sourceWidgetId") or action.get("source_widget_id"))
            target_scope = _text(action.get("target_scope") or action.get("targetScope"))
            if not (
                intent.startswith("ui.")
                and target_scope in {"mode", "widget"}
                and (source_widget_id.startswith("mode.") or source_widget_id.startswith("field."))
            ):
                continue
            rows.append({
                **action,
                # ``mode`` is a PageAssembler-local orchestration scope.  It
                # maps to the closed V2 runtime scope; falling through the
                # generic normalizer would incorrectly promote it to page.
                "target_scope": "runtime" if target_scope == "mode" else "widget",
                "source_authority": authority,
                "_source_channel": "governed_platform_action_group",
                "_presentation_priority": 100,
                "_presentation_authority": "native_contract",
            })
    return rows


def _append_ui_contract_actions(
    contract: dict[str, Any],
    ui: dict[str, Any],
    *,
    source_widget_id: str,
    main_data: dict[str, Any] | None = None,
) -> None:
    rows: list[dict[str, Any]] = []
    form_view = _dict(_dict(ui.get("views")).get("form"))
    form_meta = _dict(form_view.get("meta"))
    projection_identity = _dict(form_meta.get("projection_identity"))
    explicit_form_view = _positive_int(projection_identity.get("source_view_id"), 0) > 0

    def collect_native_layout_buttons(value: Any, *, parent_type: str = "") -> None:
        if isinstance(value, list):
            for item in value:
                collect_native_layout_buttons(item, parent_type=parent_type)
            return
        if not isinstance(value, dict):
            return
        node_type = _text(value.get("type") or value.get("kind")).lower()
        if node_type == "button":
            action = _dict(value.get("action"))
            if action and parent_type != "header" and _text(action.get("level")).lower() != "header":
                rows.append({
                    **action,
                    "_source_channel": "native_form_layout_button",
                    "sourceWidgetId": _text(value.get("containerId"), "page.root"),
                })
        for child_key in ("children", "pages", "tabs", "nodes", "items"):
            collect_native_layout_buttons(value.get(child_key), parent_type=node_type)

    collect_native_layout_buttons(_dict(contract.get("layoutContract")).get("containerTree"))
    for source_channel, header_button_source in (
        ("native_form_header", form_view.get("header_buttons")),
        ("contract_header", ui.get("header_buttons")),
    ):
        for row in _list(header_button_source):
            if isinstance(row, dict):
                rows.append({
                    **row,
                    "level": _text(row.get("level"), "header"),
                    "target_scope": _text(row.get("target_scope"), "header"),
                    "_source_channel": source_channel,
                })
    for row in _list(form_view.get("stat_buttons")):
        if isinstance(row, dict):
            rows.append({
                **row,
                "level": _text(row.get("level"), "smart"),
                "target_scope": _text(row.get("target_scope"), "page"),
                "_source_channel": "native_form_stat",
            })
    active_view_type = _text(ui.get("view_type") or _dict(ui.get("head")).get("view_type")).split(",")[0]
    if active_view_type == "list":
        active_view_type = "tree"
    active_view = _dict(_dict(ui.get("views")).get(active_view_type))
    active_view_toolbar = _dict(active_view.get("toolbar"))
    for slot in ("header", "sidebar", "footer"):
        for row in _list(active_view_toolbar.get(slot)):
            if isinstance(row, dict):
                rows.append({**row, "_source_channel": f"native_view_toolbar.{slot}"})
    if not explicit_form_view:
        # Without an effective native form carrier these top-level contract
        # rows are the only action source and retain their existing semantics.
        for key, priority, authority in (
            ("buttons", 100, "native_contract"),
            ("business_actions", 300, "product_contract"),
        ):
            for row in _list(ui.get(key)):
                if isinstance(row, dict):
                    source_kind = _text(_dict(row.get("source_authority")).get("kind"))
                    rows.append({
                        **row,
                        "_source_channel": (
                            "bound_model_action"
                            if source_kind == "odoo_native_bound_action_projection"
                            else key
                        ),
                        "_presentation_priority": priority,
                        "_presentation_authority": authority,
                    })
        toolbar = _dict(ui.get("toolbar"))
        for key in ("header", "sidebar", "footer"):
            for row in _list(toolbar.get(key)):
                if isinstance(row, dict):
                    rows.append({**row, "_source_channel": f"contract_toolbar.{key}"})
        for group in _list(ui.get("action_groups")):
            authority = _dict(_dict(group).get("source_authority"))
            if (
                authority.get("projection_only") is True
                and authority.get("no_business_fact_authority") is True
                and _text(authority.get("owner_layer")) == "business_view_orchestration"
            ):
                continue
            for row in _list(_dict(group).get("actions")):
                if isinstance(row, dict):
                    rows.append({
                        **row,
                        "_source_channel": "product_action_group",
                        "_presentation_priority": 250,
                        "_presentation_authority": "product_contract",
                    })
    else:
        # An effective native form already owns business buttons.  Only
        # explicitly bound Odoo actions and P0 projection-only controls may
        # enter from top-level carriers; ungoverned overlays fail closed.
        for row in _list(ui.get("buttons")):
            if not isinstance(row, dict):
                continue
            source_authority = _dict(row.get("source_authority"))
            source_kind = _text(source_authority.get("kind"))
            governed_projection = (
                source_authority.get("projection_only") is True
                and source_authority.get("no_business_fact_authority") is True
                and _text(source_authority.get("owner_layer")) == "business_view_orchestration"
            )
            if source_kind != "odoo_native_bound_action_projection" and not governed_projection:
                continue
            rows.append({
                **row,
                "_source_channel": (
                    "bound_model_action"
                    if source_kind == "odoo_native_bound_action_projection"
                    else "governed_platform_action"
                ),
                "_presentation_priority": 100,
                "_presentation_authority": "native_contract",
            })
    rows.extend(_governed_platform_action_group_rows(ui))
    normalized: list[dict[str, Any]] = []
    action_policies = _dict(ui.get("action_policies"))
    for row in rows:
        source_channel = _text(row.get("_source_channel"), "contract_action")
        native_identity = _dict(row.get("native_identity") or row.get("nativeIdentity"))
        if native_identity and native_identity.get("authoritative") is False:
            continue
        raw_key = _text(row.get("key") or row.get("name") or row.get("type") or row.get("string"), "action")
        key = _stable_id(raw_key, "action")
        policy = _dict(action_policies.get(raw_key) or action_policies.get(key))
        enabled_when = _dict(policy.get("enabled_when") or policy.get("enabledWhen"))
        kind = _text(row.get("kind") or row.get("type"))
        payload = _dict(row.get("payload"))
        intent = _text(row.get("intent"))
        badge = _dict(row.get("badge"))
        display_label = _text(row.get("displayLabel") or row.get("display_label"))
        if badge and not display_label and main_data:
            badge_field = _text(badge.get("field") or badge.get("fieldCode"))
            badge_label = _text(badge.get("label"))
            count = _badge_count(main_data.get(badge_field)) if badge_field else None
            if count is not None and badge_label:
                display_label = f"{count}{badge_label}"
        permission_constraints = {
            constraint_key: deepcopy(
                policy.get(constraint_key)
                if policy.get(constraint_key) is not None
                else enabled_when.get(constraint_key)
                if enabled_when.get(constraint_key) is not None
                else payload.get(constraint_key)
                if payload.get(constraint_key) is not None
                else row.get(constraint_key)
            )
            for constraint_key in (
                "required_groups", "required_groups_xmlids", "groups", "groups_id", "groups_xmlids",
                "allowed_roles", "allowed_role_codes",
                "allowed_users", "allowed_user_ids", "required_users", "required_user_ids",
                "required_user_id", "required_user",
            )
            if (
                policy.get(constraint_key) is not None
                or enabled_when.get(constraint_key) is not None
                or payload.get(constraint_key) is not None
                or row.get(constraint_key) is not None
            )
        }
        permission_constraints = {
            key: value for key, value in permission_constraints.items()
            if _has_action_constraint_value(value)
        }
        entitlement_evaluated = bool(
            policy.get("entitlement_evaluated")
            or row.get("entitlement_evaluated")
        )
        explicit_permission_verdict = any(
            isinstance(source.get(key), bool)
            for source in (policy, row)
            for key in ("allowed", "enabled")
        )
        permission_unresolved = bool(permission_constraints) and (
            not entitlement_evaluated or not explicit_permission_verdict
        )
        if kind == "server" or payload.get("server_action_id"):
            action_intent = "execute_button"
            target = {}
            button = {
                "name": _text(row.get("name") or row.get("key"), key),
                "type": "server_action",
                "server_action_id": payload.get("server_action_id"),
                "xml_id": payload.get("xml_id"),
            }
        elif (
            kind in {"open", "url"}
            or intent in {"open", "url"}
            or _positive_int(row.get("action_id"), 0)
            or any(payload.get(key) for key in ("action_id", "ref", "xml_id", "url", "route"))
        ):
            action_intent = "ui.contract"
            raw_action_ref = payload.get("ref") or row.get("ref")
            raw_action_xmlid = payload.get("xml_id") or row.get("xml_id")
            target = {
                "action_id": payload.get("action_id") or row.get("action_id"),
                "action_ref": raw_action_ref,
                "xml_id": raw_action_xmlid,
                "menu_id": payload.get("menu_id") or row.get("menu_id"),
                "model": row.get("target_model") or row.get("model"),
                "view_type": _text(payload.get("view_mode"), "tree").split(",")[0],
                "domain_raw": payload.get("domain_raw"),
                "context_raw": payload.get("context_raw"),
                "url": payload.get("url"),
                "route": payload.get("route") or row.get("route"),
                "target": payload.get("target"),
            }
            # Model-bound window actions and native ``type=action`` buttons
            # execute inside the current record authority.  They are not menu
            # routes, so preserve the Odoo action-button identity for the
            # governed execute_button adapter instead of flattening them into
            # an unauthorised /a/:id navigation.
            action_button = (
                source_channel == "bound_model_action"
                or (
                    source_channel == "native_form_header"
                    and _text(payload.get("type")).lower() == "action"
                )
            )
            button = ({
                "name": _text(
                    target.get("action_id")
                    or target.get("action_ref")
                    or target.get("xml_id")
                ),
                "type": "action",
            } if action_button else {})
            if action_button:
                action_intent = "execute_button"
        else:
            action_intent = _text(row.get("intent"), "execute_button")
            target = deepcopy(_dict(row.get("target")))
            button = {
                "name": _text(
                    row.get("name")
                    or row.get("button_name")
                    or row.get("method_name")
                    or payload.get("method"),
                    key,
                ),
                "type": _text(
                    row.get("type")
                    or row.get("button_type")
                    or payload.get("type"),
                    "object",
                ),
            }
        normalized.append(
            {
                "key": key,
                "label": _text(
                    policy.get("label")
                    or row.get("label")
                    or row.get("string")
                    or row.get("name"),
                    key,
                ),
                "displayLabel": display_label,
                "intent": action_intent,
                "target": target,
                "button": button,
                "badge": badge or None,
                "sourceWidgetId": _text(row.get("sourceWidgetId") or row.get("source_widget_id")),
                "target_scope": _text(row.get("target_scope") or row.get("level"), "page"),
                "trigger": _text(row.get("trigger"), "click"),
                "visible": deepcopy(row.get("visible")),
                "modifiers": deepcopy(row.get("modifiers")),
                "invisible": deepcopy(row.get("invisible")),
                "visible_profiles": deepcopy(
                    policy.get("visible_profiles")
                    if "visible_profiles" in policy
                    else row.get("visible_profiles")
                ),
                "presentation": deepcopy(policy.get("presentation") or row.get("presentation")),
                "action_safety": deepcopy(policy.get("action_safety") or row.get("action_safety")),
                "allowed": False if permission_unresolved or policy.get("allowed") is False or row.get("allowed") is False else row.get("allowed", policy.get("allowed")),
                "enabled": False if permission_unresolved or policy.get("enabled") is False or row.get("enabled") is False else row.get("enabled", policy.get("enabled")),
                "disabled": True if policy.get("disabled") is True or row.get("disabled") is True else row.get("disabled", policy.get("disabled")),
                "business_available": row.get("business_available"),
                "authorization_allowed": row.get("authorization_allowed"),
                "reason_code": (
                    policy.get("reason_code")
                    or policy.get("disabled_reason_code")
                    or row.get("reason_code")
                    or row.get("disabled_reason_code")
                    or ("ACTION_PERMISSION_UNRESOLVED" if permission_unresolved else "")
                ),
                "permission_constraints": permission_constraints,
                "entitlement_evaluated": entitlement_evaluated,
                "source_channel": source_channel,
                "presentation_priority": _positive_int(
                    policy.get("presentation_priority")
                    or row.get("presentation_priority")
                    or row.get("_presentation_priority")
                    or (300 if policy.get("label") or policy.get("presentation") else 0),
                    100,
                ),
                "presentation_authority": _text(
                    policy.get("presentation_authority")
                    or row.get("presentation_authority")
                    or row.get("_presentation_authority")
                    or ("product_contract" if policy.get("label") or policy.get("presentation") else ""),
                    "native_contract",
                ),
                "native_identity": deepcopy(native_identity),
            }
        )
    _append_actions(contract, normalized, source_widget_id=source_widget_id)


def _append_ui_contract_row_actions(contract: dict[str, Any], ui: dict[str, Any]) -> None:
    views = _dict(ui.get("views"))
    rows: list[dict[str, Any]] = []
    for view_key in ("kanban", "tree", "list"):
        view = _dict(views.get(view_key))
        for row in _list(view.get("row_actions")):
            if isinstance(row, dict):
                rows.append({**row, "_source_channel": f"native_{view_key}_row_action"})
    normalized: list[dict[str, Any]] = []
    action_policies = _dict(ui.get("action_policies"))
    for row in rows:
        native_identity = _dict(row.get("native_identity") or row.get("nativeIdentity"))
        if native_identity and native_identity.get("authoritative") is False:
            continue
        raw_key = _text(row.get("key") or row.get("name") or row.get("intent"), "row_action")
        key = _stable_id(raw_key, "row_action")
        policy = _dict(action_policies.get(raw_key) or action_policies.get(key))
        enabled_when = _dict(policy.get("enabled_when") or policy.get("enabledWhen"))
        kind = _text(row.get("kind") or row.get("type")).lower()
        intent = _text(row.get("intent")).lower()
        payload = _dict(row.get("payload"))
        permission_constraints = {
            constraint_key: deepcopy(
                policy.get(constraint_key)
                if policy.get(constraint_key) is not None
                else enabled_when.get(constraint_key)
                if enabled_when.get(constraint_key) is not None
                else payload.get(constraint_key)
                if payload.get(constraint_key) is not None
                else row.get(constraint_key)
            )
            for constraint_key in (
                "required_groups", "required_groups_xmlids", "groups", "groups_id", "groups_xmlids",
                "allowed_roles", "allowed_role_codes",
                "allowed_users", "allowed_user_ids", "required_users", "required_user_ids",
                "required_user_id", "required_user",
            )
            if (
                policy.get(constraint_key) is not None
                or enabled_when.get(constraint_key) is not None
                or payload.get(constraint_key) is not None
                or row.get(constraint_key) is not None
            )
        }
        permission_constraints = {
            key: value for key, value in permission_constraints.items()
            if _has_action_constraint_value(value)
        }
        entitlement_evaluated = bool(
            policy.get("entitlement_evaluated")
            or payload.get("entitlement_evaluated")
            or row.get("entitlement_evaluated")
        )
        explicit_permission_verdict = any(
            isinstance(source.get(verdict_key), bool)
            for source in (policy, payload, row)
            for verdict_key in ("allowed", "enabled")
        )
        permission_unresolved = bool(permission_constraints) and (
            not entitlement_evaluated or not explicit_permission_verdict
        )
        if kind == "server" or payload.get("server_action_id"):
            target = {}
            button = {
                "name": _text(row.get("name") or row.get("key"), key),
                "type": "server_action",
                "server_action_id": payload.get("server_action_id"),
                "xml_id": payload.get("xml_id"),
            }
        elif (
            kind in {"open", "url"}
            or intent in {"open", "url"}
            or _positive_int(row.get("action_id"), 0)
            or any(payload.get(candidate) for candidate in ("action_id", "ref", "xml_id", "url", "route"))
        ):
            target = {
                "action_id": payload.get("action_id") or row.get("action_id"),
                "action_ref": payload.get("ref") or row.get("ref"),
                "xml_id": payload.get("xml_id") or row.get("xml_id"),
                "model": row.get("target_model") or row.get("model"),
                "view_type": _text(payload.get("view_mode"), "form").split(",")[0],
                "domain_raw": payload.get("domain_raw"),
                "context_raw": payload.get("context_raw"),
                "url": payload.get("url"),
                "route": payload.get("route") or row.get("route"),
                "target": payload.get("target"),
            }
            button = {}
        else:
            target = deepcopy(_dict(row.get("target")))
            button = deepcopy(_dict(row.get("button")))
            button.setdefault(
                "name",
                _text(
                    row.get("name")
                    or row.get("button_name")
                    or row.get("method_name")
                    or payload.get("method"),
                    key,
                ),
            )
            button.setdefault(
                "type",
                _text(
                    row.get("type")
                    or row.get("button_type")
                    or payload.get("type"),
                    "object",
                ),
            )
        normalized.append({
            "key": key,
            "name": row.get("name") or key,
            "label": _text(row.get("label") or row.get("string") or row.get("name"), key),
            "intent": _text(row.get("intent"), "open"),
            "target": target,
            "button": button,
            "trigger": _text(row.get("trigger") or row.get("display_mode"), "row_click"),
            "level": _text(row.get("level"), "row"),
            "target_scope": _text(row.get("target_scope"), "row"),
            "visible": deepcopy(row.get("visible")),
            "modifiers": deepcopy(row.get("modifiers")),
            "invisible": deepcopy(row.get("invisible")),
            "visible_profiles": deepcopy(row.get("visible_profiles")),
            "presentation": deepcopy(row.get("presentation")),
            "action_safety": deepcopy(row.get("action_safety")),
            "allowed": False if permission_unresolved or policy.get("allowed") is False or row.get("allowed") is False else row.get("allowed", policy.get("allowed")),
            "enabled": False if permission_unresolved or policy.get("enabled") is False or row.get("enabled") is False else row.get("enabled", policy.get("enabled")),
            "disabled": True if policy.get("disabled") is True or row.get("disabled") is True else row.get("disabled", policy.get("disabled")),
            "reason_code": (
                policy.get("reason_code")
                or policy.get("disabled_reason_code")
                or row.get("reason_code")
                or row.get("disabled_reason_code")
                or ("ACTION_PERMISSION_UNRESOLVED" if permission_unresolved else "")
            ),
            "permission_constraints": permission_constraints,
            "entitlement_evaluated": entitlement_evaluated,
            "source_channel": _text(row.get("_source_channel"), "native_row_action"),
            "presentation_authority": _text(row.get("presentation_authority"), "native_contract"),
            "presentation_priority": _positive_int(row.get("presentation_priority"), 100),
            "native_identity": deepcopy(native_identity),
        })
    _append_actions(contract, normalized, source_widget_id="page.row")


def _append_registered_kanban_row_action(contract: dict[str, Any], *, model: str, view_type: str) -> None:
    action = _KANBAN_ROW_ACTION_REGISTRY.get((_text(model), _text(view_type)))
    if not action:
        return
    rows = _list(_dict(contract.get("actionContract")).get("actionRuleList"))
    for row in rows:
        if not isinstance(row, dict):
            continue
        if _text(row.get("triggerType")) == "row_click" or _text(row.get("sourceWidgetId")) == "page.row":
            return
    _append_actions(
        contract,
        [deepcopy(action)],
        source_widget_id="page.row",
    )


def _assemble_unknown(source: dict[str, Any], *, client_type: str, request_id: str) -> dict[str, Any]:
    return _base_contract(
        page_id="unknown.contract",
        scene_key="unknown.contract",
        page_name="Unknown Contract",
        model="",
        view_type="combine",
        layout_type="combine",
        client_type=client_type,
        source_type="unknown",
        source_payload=source,
        request_id=request_id,
    )
