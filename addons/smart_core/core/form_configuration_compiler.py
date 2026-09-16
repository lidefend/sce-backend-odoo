"""Compile scoped presentation changes against immutable native occurrences.

No ORM or client-side layout inference lives here. Callers supply configurations
selected in the authenticated environment and the permission-filtered baseline.
"""
from copy import deepcopy
import json
import hashlib

from ..utils.backend_contract_boundaries import (
    classify_view_orchestration_contract, view_orchestration_apply_order_key,
)


def is_configured_surface(config):
    return classify_view_orchestration_contract(config.name, config.contract_json)["kind"] in {
        "tenant_lowcode_configuration", "user_preference_projection",
    }


def _error(code, target, **details):
    raise ValueError(json.dumps({"code": code, "target": target, **details}, ensure_ascii=False, sort_keys=True))


def _restricted(node, key):
    return any(carrier.get(key) not in (None, False, 0, "", "0", "false", "False", [], {})
               for carrier in (node, node.get("attributes") or {}, node.get("modifiers") or {}, node.get("fieldInfo") or {})
               if isinstance(carrier, dict))


def _unfillable_required_fields(layout, fields_meta):
    """Describe effective constraints per occurrence, including all ancestors.

    Keep baseline conditional restrictions intact; without proof of defaults or
    another filling path, configuration may not introduce a new hidden-required
    combination. Rewalk the actual tree after grouping rather than old parents.
    """
    blocked = {}

    def visit(rows, hidden=(), required=()):
        for node in rows:
            if not isinstance(node, dict):
                continue
            identity = node.get("native_locator") or node.get("type")
            own_hidden, own_required = [], []
            for key, destination in (("invisible", own_hidden), ("required", own_required)):
                for carrier in (node, node.get("attributes") or {}, node.get("modifiers") or {}, node.get("fieldInfo") or {}):
                    if isinstance(carrier, dict) and _restricted({key: carrier.get(key)}, key):
                        value = carrier[key]
                        destination.append((identity, "true" if value in (True, 1, "1", "true", "True")
                                            else json.dumps(value, sort_keys=True)))
            if node.get("visible") is False:
                own_hidden.append((identity, "true"))
            next_hidden = tuple(sorted(set(hidden + tuple(own_hidden))))
            next_required = tuple(sorted(set(required + tuple(own_required))))
            if node.get("type") == "field":
                if fields_meta.get(node.get("name"), {}).get("required"):
                    next_required += ((identity, "model-required"),)
                if next_hidden and next_required:
                    blocked[identity] = (next_hidden, next_required)
            for key in ("children", "pages", "tabs", "nodes", "items"):
                if isinstance(node.get(key), list):
                    visit(node[key], next_hidden, next_required)
    visit(layout)
    return blocked


def compile_form_configuration(layout, configs, *, fields_meta=None):
    """Apply node_patches once, preserving fields, modifiers and action identity.

    Targets require locator + expected type/name/occurrence. A group operation
    wraps existing direct siblings, preserving all inherited restrictions. Order
    is an explicit permutation of direct children, never a field-name lookup.
    """
    result = deepcopy(layout)
    meta = fields_meta or {}
    baseline_blocked = _unfillable_required_fields(layout, meta)
    nodes, parents = {}, {}

    def index(rows, parent=None):
        for node in rows:
            if not isinstance(node, dict):
                continue
            locator = node.get("native_locator")
            if locator:
                if locator in nodes:
                    _error("CONFIG_DUPLICATE_NODE_IDENTITY", locator)
                nodes[locator] = node
                parents[locator] = parent
            for key in ("children", "pages", "tabs", "nodes", "items"):
                if isinstance(node.get(key), list):
                    index(node[key], locator or parent)
    index(result)
    writes = {}
    provenance = []
    plans = {}
    for config in sorted(configs, key=view_orchestration_apply_order_key):
        spec = ((config.contract_json.get("view_orchestration") or {}).get("views") or {}).get("form") or {}
        patches = spec.get("node_patches")
        if not patches:
            continue
        if not is_configured_surface(config):
            _error("CONFIG_SOURCE_NOT_AUTHORIZED", str(config.id))
        if not isinstance(patches, list):
            _error("CONFIG_PATCHES_INVALID", str(config.id))
        rank = view_orchestration_apply_order_key(config)[:-2]
        for patch in patches:
            if not isinstance(patch, dict):
                _error("CONFIG_PATCH_INVALID", str(config.id))
            if set(patch) - {"target", "expected", "set", "order", "group"}:
                _error("CONFIG_PATCH_PROPERTY_NOT_ALLOWED", str(config.id))
            target = patch.get("target")
            node = nodes.get(target)
            expected = patch.get("expected") or {}
            if not node or not expected or any(expected.get(key) != node.get(key) for key in ("type", "name", "occurrence_index")):
                _error("CONFIG_TARGET_STALE", target, configuration=config.name)
            properties = patch.get("set") or {}
            if not isinstance(properties, dict) or set(properties) - {"label", "visible", "readonly", "required", "columns"}:
                _error("CONFIG_PROPERTY_NOT_ALLOWED", target)
            for key, value in {**properties, **{key: patch[key] for key in ("order", "group") if key in patch}}.items():
                identity = (rank, target, key)
                if identity in writes and writes[identity][0] != value:
                    _error("CONFIG_SAME_PRIORITY_CONFLICT", target, property=key, configurations=[writes[identity][1], config.name])
                writes[identity] = (deepcopy(value), config.name)
            plan = plans.setdefault(target, {"target": target, "expected": expected, "set": {}})
            plan["set"].update(properties)
            for key in ("order", "group"):
                if key in patch:
                    plan[key] = deepcopy(patch[key])
            provenance.append({"configuration_id": int(config.id or 0), "configuration": config.name,
                               "version": int(getattr(config, "version_no", 0) or 0), "target": target})

    # Interpret the winning properties against the baseline exactly once. This
    # lets a higher-priority group override a lower group without relocating the
    # same occurrence twice or accepting a name-based fallback.
    for target in sorted(plans):
        patch = plans[target]
        node = nodes[target]
        properties = patch["set"]
        model_field = meta.get(node.get("name"), {})
        if node.get("type") == "field" and fields_meta is not None and node.get("name") not in meta:
            _error("CONFIG_FIELD_NOT_AUTHORIZED", target)
        for key in ("readonly", "required"):
            if key in properties:
                if not isinstance(properties[key], bool):
                    _error("CONFIG_PROPERTY_INVALID", target, property=key)
                if properties[key] is False and (_restricted(node, key) or model_field.get(key)):
                    _error("CONFIG_BUSINESS_CONSTRAINT_RELAXED", target, property=key)
                node[key] = properties[key]
                node["modifiers"] = {**(node.get("modifiers") or {}), key: properties[key]}
                if node.get("type") == "field":
                    node["fieldInfo"] = {**(node.get("fieldInfo") or {}), key: properties[key]}
        if "visible" in properties:
            if not isinstance(properties["visible"], bool):
                _error("CONFIG_PROPERTY_INVALID", target, property="visible")
            if properties["visible"] and _restricted(node, "invisible"):
                _error("CONFIG_VISIBILITY_CONSTRAINT_RELAXED", target)
            if not properties["visible"]:
                # Preserve conditional modifiers; hiding may only tighten.
                node["invisible"] = True
                node["modifiers"] = {**(node.get("modifiers") or {}), "invisible": True}
            node["visible"] = properties["visible"]
        if "label" in properties:
            if not isinstance(properties["label"], str) or not properties["label"].strip():
                _error("CONFIG_LABEL_INVALID", target)
            node.update(string=properties["label"], label=properties["label"])
            if isinstance(node.get("fieldInfo"), dict):
                node["fieldInfo"].update(string=properties["label"], label=properties["label"])
        if "columns" in properties:
            if node.get("type") not in {"group", "sheet"} or type(properties["columns"]) is not int or properties["columns"] not in {1, 2, 3}:
                _error("CONFIG_COLUMNS_INVALID", target)
            node["col"] = properties["columns"]
            node["columns"] = properties["columns"]
    # All winning attributes are now materialized. Structural operations do not
    # perform safety decisions against a partially configured tree.
    for target in sorted(plans):
        patch, node = plans[target], nodes[target]
        if "order" in patch or "group" in patch:
            children = node.get("children")
            if not isinstance(children, list) or node.get("type") not in {"group", "sheet", "page"}:
                _error("CONFIG_CONTAINER_NOT_CONFIGURABLE", target)
            child_map = {child.get("native_locator"): child for child in children if isinstance(child, dict)}
            if None in child_map or len(child_map) != len(children):
                _error("CONFIG_CHILD_IDENTITY_INCOMPLETE", target)
            if "order" in patch:
                order = patch["order"]
                if not isinstance(order, list) or len(order) != len(children) or set(order) != set(child_map):
                    _error("CONFIG_ORDER_TARGET_STALE", target)
                children[:] = [child_map[key] for key in order]
            if "group" in patch:
                group = patch["group"]
                if not isinstance(group, dict):
                    _error("CONFIG_GROUP_INVALID", target)
                members = group.get("members") or []
                key = group.get("key")
                if not isinstance(key, str) or not key or not isinstance(members, list) or not members or len(set(members)) != len(members) or not set(members).issubset(child_map):
                    _error("CONFIG_GROUP_TARGET_STALE", target)
                if any(child_map[member].get("type") != "field" for member in members):
                    _error("CONFIG_GROUP_PROTECTED_NODE", target)
                group_id = target + "/configuration-group:" + key
                if group_id in nodes:
                    _error("CONFIG_GROUP_ID_CONFLICT", group_id)
                wrapper = {"type": "group", "name": key, "string": group.get("label") or key,
                           "native_locator": group_id, "occurrence_index": 1,
                           "children": [child for child in children if child.get("native_locator") in members],
                           "attributes": {"data-sc-anchor": "config-" + hashlib.sha256(group_id.encode()).hexdigest()[:16]}}
                position = min(i for i, child in enumerate(children) if child.get("native_locator") in members)
                children[:] = [child for child in children if child.get("native_locator") not in members]
                children.insert(position, wrapper)
                nodes[group_id] = wrapper
    for target, constraints in sorted(_unfillable_required_fields(result, meta).items()):
        if baseline_blocked.get(target) != constraints:
            _error("CONFIG_REQUIRED_FIELD_HIDDEN", target,
                   hidden_ancestors=sorted({identity for identity, _ in constraints[0]}))
    return result, sorted(provenance, key=lambda row: (row["configuration_id"], row["target"]))
