#!/usr/bin/env python3
"""Static guard for Unified Page Contract v2+ protocol assets."""

from __future__ import annotations

import argparse
import ast
import copy
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


TOP_LEVEL_KEYS = {
    "pageInfo",
    "layoutContract",
    "statusContract",
    "actionContract",
    "dataContract",
    "runtimeContract",
    "meta",
}
OPTIONAL_TOP_LEVEL_KEYS = {
    "formStructureContract",
    "searchContract",
    "workflowContract",
}
TOP_LEVEL_PROPERTIES = TOP_LEVEL_KEYS | OPTIONAL_TOP_LEVEL_KEYS

REQUIRED_DEFS = {
    "pageInfo",
    "layoutContract",
    "container",
    "layoutNode",
    "nativeLayoutNode",
    "widget",
    "statusContract",
    "actionContract",
    "actionRule",
    "dataContract",
    "dataMeta",
    "visibleFields",
    "fieldGroups",
    "sourceAuthority",
    "contractLifecycle",
    "contractLifecycleDefinition",
    "contractLifecycleGeneration",
    "contractLifecycleRuntime",
    "contractLifecycleIntegrity",
    "runtimeContract",
    "formStructureContract",
    "formStructureSlot",
    "formStructureGroup",
    "formStructureRole",
    "meta",
}

REQUIRED_CLOSED_OBJECT_DEFS = {
    "nativeLayoutNode",
    "containerStatus",
    "widgetStatus",
    "buttonStatus",
    "selectorStatus",
}

LEGACY_ROOT_KEYS = {
    "scene_contract",
    "page_orchestration",
    "ui_contract",
    "ui.contract",
    "api.onchange",
}

FORMAL_V2_FIELD_PATHS = {
    "$defs.layoutContract.properties.listProfile",
    "$defs.actionContract.properties.deletePolicy",
    "$defs.actionContract.properties.surfacePolicies",
    "$defs.dataMeta.properties.businessOperationProfile",
    "$defs.dataMeta.properties.visibleFields",
    "$defs.dataMeta.properties.fieldGroups",
}

SCHEMA_ENUM_REGISTRY_MAP = {
    ("pageInfo", "viewType"): ("viewType",),
    ("pageInfo", "layoutType"): ("layoutType",),
    ("pageInfo", "renderMode"): ("renderMode",),
    ("pageInfo", "clientType"): ("clientType", "stable"),
    ("layoutContract", "layoutType"): ("layoutType",),
    ("layoutContract", "adaptMode"): ("adaptMode",),
    ("container", "containerType"): ("containerType",),
    ("widget", "widgetType"): ("widgetType",),
    ("widgetStatus", "auth"): ("authLevel",),
    ("actionRule", "triggerType"): ("triggerType",),
    ("actionRule", "dispatchMode"): ("dispatchMode",),
    ("actionRule", "targetScope"): ("targetScope",),
    ("actionRule", "refreshMode"): ("refreshMode",),
    ("runtimeContract", "patchStrategy"): ("patchStrategy",),
    ("runtimeContract", "cachePolicy"): ("cachePolicy",),
    ("runtimeContract", "renderStrategy"): ("renderStrategy",),
}

FORBIDDEN_FORMAL_SCHEMA_KEYS = {
    "list_profile",
    "delete_policy",
    "surface_policies",
    "business_operation_profile",
    "visible_fields",
    "field_groups",
    "form_structure_contract",
    "legacyContractProjection",
    "legacy_contract_projection",
}


def validate_runtime_producer_keys(schema: dict[str, Any], errors: list[str]) -> None:
    """Keep literal runtimeContract producers inside the strict wire schema."""
    root = Path(__file__).resolve().parents[2]
    producer_paths = (
        root / "addons/smart_core/core/unified_page_contract_v2_assembler.py",
        root / "addons/smart_core/core/unified_page_contract_v2_client.py",
    )
    produced: set[str] = set()

    def string_key(node: ast.AST) -> str:
        return str(node.value) if isinstance(node, ast.Constant) and isinstance(node.value, str) else ""

    for producer_path in producer_paths:
        tree = ast.parse(producer_path.read_text(encoding="utf-8"), filename=str(producer_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Dict):
                pairs = list(zip(node.keys, node.values))
                for key_node, value_node in pairs:
                    key = string_key(key_node) if key_node is not None else ""
                    if key == "runtimeContract" and isinstance(value_node, ast.Dict):
                        produced.update(string_key(item) for item in value_node.keys if item is not None)
                parent_names = {
                    target.id
                    for target in getattr(getattr(node, "parent", None), "targets", [])
                    if isinstance(target, ast.Name)
                }
                if "runtime_extensions" in parent_names:
                    produced.update(string_key(item) for item in node.keys if item is not None)
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if not isinstance(target, ast.Subscript):
                        continue
                    key = string_key(target.slice)
                    owner = target.value
                    if isinstance(owner, ast.Subscript) and string_key(owner.slice) == "runtimeContract":
                        produced.add(key)
                    elif isinstance(owner, ast.Name) and owner.id == "runtime":
                        produced.add(key)
        # Attach parents only for the small runtime_extensions ownership check.
        for parent in ast.walk(tree):
            for child in ast.iter_child_nodes(parent):
                child.parent = parent
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Dict):
                continue
            if any(isinstance(target, ast.Name) and target.id == "runtime_extensions" for target in node.targets):
                produced.update(string_key(item) for item in node.value.keys if item is not None)

    allowed = set(schema["$defs"]["runtimeContract"].get("properties", {}))
    unknown = sorted(key for key in produced if key and key not in allowed)
    if unknown:
        fail(errors, f"runtimeContract producer keys missing from strict schema: {unknown}")

FORBIDDEN_SCHEMA_ALIAS_CASES = {
    "$.delete_policy": ("delete_policy",),
    "$.surface_policies": ("surface_policies",),
    "$.list_profile": ("list_profile",),
    "$.form_structure_contract": ("form_structure_contract",),
    "$.legacyContractProjection": ("legacyContractProjection",),
    "$.legacy_contract_projection": ("legacy_contract_projection",),
    "$.layoutContract.list_profile": ("layoutContract", "list_profile"),
    "$.actionContract.delete_policy": ("actionContract", "delete_policy"),
    "$.actionContract.surface_policies": ("actionContract", "surface_policies"),
    "$.dataContract.dataMeta.business_operation_profile": (
        "dataContract",
        "dataMeta",
        "business_operation_profile",
    ),
    "$.dataContract.dataMeta.visible_fields": ("dataContract", "dataMeta", "visible_fields"),
    "$.dataContract.dataMeta.field_groups": ("dataContract", "dataMeta", "field_groups"),
    "$.dataContract.dataMeta.legacyContractProjection": (
        "dataContract",
        "dataMeta",
        "legacyContractProjection",
    ),
    "$.dataContract.dataMeta.legacy_contract_projection": (
        "dataContract",
        "dataMeta",
        "legacy_contract_projection",
    ),
}

ID_KEYS = {
    "pageId",
    "sceneKey",
    "containerId",
    "widgetId",
    "fieldCode",
    "btnId",
    "actionId",
    "dataKey",
    "sourceWidgetId",
}

ID_DRIFT_SUFFIX = re.compile(
    r"(\.|:|-)(admin|user|role|web_pc|wx_mini|harmony_h5|mobile_app|readonly|editable|visible|hidden)$"
)

VOLATILE_META_PATTERN = re.compile(
    r"(\d{4}-\d{2}-\d{2}t\d{2}:|\d{13,}|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})",
    re.IGNORECASE,
)


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - guard output path
        raise ValueError(f"{path}: invalid JSON: {exc}") from exc


def walk(value: Any, path: str = "$"):
    yield path, value
    if isinstance(value, dict):
        for key, child in value.items():
            yield from walk(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk(child, f"{path}[{index}]")


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def dict_path(value: dict[str, Any], path: str) -> Any:
    node: Any = value
    for item in path.split("."):
        if not isinstance(node, dict):
            return None
        node = node.get(item)
    return node


def registry_path(value: dict[str, Any], path: tuple[str, ...]) -> Any:
    node: Any = value
    for item in path:
        if not isinstance(node, dict):
            return None
        node = node.get(item)
    return node


def validate_schema(schema: dict[str, Any], registry: dict[str, Any], errors: list[str]) -> None:
    required = set(schema.get("required", []))
    if required != TOP_LEVEL_KEYS:
        fail(errors, f"schema top-level required keys mismatch: {sorted(required)}")

    properties = set(schema.get("properties", {}).keys())
    if properties != TOP_LEVEL_PROPERTIES:
        fail(errors, f"schema top-level properties mismatch: {sorted(properties)}")

    defs = set(schema.get("$defs", {}).keys())
    missing_defs = REQUIRED_DEFS - defs
    if missing_defs:
        fail(errors, f"schema missing $defs: {sorted(missing_defs)}")
    for name in sorted(REQUIRED_CLOSED_OBJECT_DEFS):
        definition = schema.get("$defs", {}).get(name, {})
        if definition.get("additionalProperties") is not False:
            fail(errors, f"schema $defs.{name} must set additionalProperties=false")
    for path in sorted(FORMAL_V2_FIELD_PATHS):
        if dict_path(schema, path) is None:
            fail(errors, f"schema missing formal v2 field path: {path}")
    for node_path, node in walk(schema):
        if not isinstance(node, dict):
            continue
        for key in node:
            if key in FORBIDDEN_FORMAL_SCHEMA_KEYS:
                fail(errors, f"schema must not declare compatibility field {key!r} at {node_path}")

    schema_defs = schema.get("$defs", {})
    for (def_name, field_name), registry_key_path in sorted(SCHEMA_ENUM_REGISTRY_MAP.items()):
        schema_enum = (
            schema_defs.get(def_name, {})
            .get("properties", {})
            .get(field_name, {})
            .get("enum")
        )
        registry_enum = registry_path(registry, registry_key_path)
        if not isinstance(schema_enum, list):
            fail(errors, f"schema $defs.{def_name}.properties.{field_name}.enum is required")
            continue
        if schema_enum != registry_enum:
            fail(
                errors,
                f"schema $defs.{def_name}.properties.{field_name}.enum must match "
                f"enum_registry.{'.'.join(registry_key_path)}",
            )

    patch_ops = set(registry.get("patchOperation", []))
    expected_patch_ops = {"replace", "merge", "append", "remove", "reorder", "invalidate"}
    if patch_ops != expected_patch_ops:
        fail(errors, f"patchOperation enum mismatch: {sorted(patch_ops)}")


def validate_example(path: Path, payload: dict[str, Any], registry: dict[str, Any], errors: list[str]) -> None:
    keys = set(payload.keys())
    if keys != TOP_LEVEL_KEYS:
        fail(errors, f"{path}: top-level keys must equal canonical v2 shape, got {sorted(keys)}")

    page_info = payload.get("pageInfo", {})
    stable_clients = registry.get("clientType", {}).get("stable", [])
    client_type = page_info.get("clientType")
    if client_type not in stable_clients:
        fail(errors, f"{path}: unsupported stable clientType {client_type!r}")

    if page_info.get("pageId") != payload.get("layoutContract", {}).get("pageId"):
        fail(errors, f"{path}: pageInfo.pageId and layoutContract.pageId must match")

    meta = payload.get("meta", {})
    for required_meta in ("etag", "snapshotId", "traceId", "requestId", "sourceType"):
        if required_meta not in meta:
            fail(errors, f"{path}: meta.{required_meta} is required")
        elif VOLATILE_META_PATTERN.search(str(meta.get(required_meta, ""))):
            fail(errors, f"{path}: meta.{required_meta} must use normalized stable sample value")
    if "compat" in meta:
        fail(errors, f"{path}: meta.compat must be removed")

    forbidden_keys = {str(key).lower() for key in registry.get("forbiddenContractKeys", [])}
    for node_path, node in walk(payload):
        if not isinstance(node, dict):
            continue
        for key, value in node.items():
            lower_key = str(key).lower()
            if lower_key in forbidden_keys or lower_key.startswith("_fe"):
                fail(errors, f"{path}: forbidden DSL-like key {key!r} at {node_path}")
            if key in LEGACY_ROOT_KEYS:
                fail(errors, f"{path}: legacy key {key!r} must be removed")
            if key in ID_KEYS and isinstance(value, str) and ID_DRIFT_SUFFIX.search(value):
                fail(errors, f"{path}: unstable semantic/client suffix in {key}={value!r}")

    component_registry = payload.get("layoutContract", {}).get("componentRegistry", {})
    for node_path, node in walk(payload.get("layoutContract", {})):
        if isinstance(node, dict) and "componentKey" in node:
            component_key = node["componentKey"]
            if component_key not in component_registry:
                fail(errors, f"{path}: componentKey {component_key!r} missing from componentRegistry at {node_path}")
        if isinstance(node, dict) and "capabilities" in node:
            capabilities = node.get("capabilities", [])
            unknown = set(capabilities) - set(registry.get("componentCapability", []))
            if unknown:
                fail(errors, f"{path}: unknown capabilities {sorted(unknown)} at {node_path}")


def validate_example_against_schema(
    path: Path,
    payload: dict[str, Any],
    validator: Draft202012Validator,
    errors: list[str],
) -> None:
    for issue in sorted(validator.iter_errors(payload), key=lambda item: list(item.absolute_path)):
        location = "$"
        if issue.absolute_path:
            location = "$." + ".".join(str(item) for item in issue.absolute_path)
        fail(errors, f"{path}: schema validation failed at {location}: {issue.message}")


def validate_schema_rejects_compatibility_aliases(
    path: Path,
    payload: dict[str, Any],
    validator: Draft202012Validator,
    errors: list[str],
) -> None:
    for alias_path, path_parts in sorted(FORBIDDEN_SCHEMA_ALIAS_CASES.items()):
        mutated = copy.deepcopy(payload)
        parent: Any = mutated
        for part in path_parts[:-1]:
            if not isinstance(parent, dict):
                fail(errors, f"{path}: {alias_path} parent must be an object before alias rejection check")
                parent = None
                break
            parent = parent.setdefault(part, {})
        if parent is None:
            continue
        if not isinstance(parent, dict):
            fail(errors, f"{path}: {alias_path} parent must be an object before alias rejection check")
            continue
        parent[path_parts[-1]] = {}
        if not list(validator.iter_errors(mutated)):
            fail(errors, f"{path}: schema must reject compatibility alias {alias_path}")


ACTION_SEMANTICS_ASSEMBLER = "addons/smart_core/core/unified_page_contract_v2_assembler.py"
ACTION_SEMANTICS_AUTHORITY = "addons/smart_core/core/action_semantics_vocabulary.py"
ACTION_SEMANTICS_TS = "frontend/packages/schema/src/actionSemantics.ts"
PAIRING_CHECK_ALIAS = "action_semantics_purpose_is_declared"
LOCAL_VOCABULARY_TARGETS = {
    "DECLARED_ACTION_SEMANTICS_KINDS",
    "DECLARED_ACTION_SEMANTICS_PURPOSES",
    "DECLARED_ACTION_SEMANTICS_EXECUTORS",
    "DECLARED_ACTION_SEMANTICS_OPERATIONS",
}


def load_semantics_authority(root: Path):
    """Import the single vocabulary authority (it imports nothing itself)."""
    path = root / ACTION_SEMANTICS_AUTHORITY
    if not path.exists():
        return None
    spec = importlib.util.spec_from_file_location("action_semantics_vocabulary", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def ts_literal_list(source: str, name: str) -> set[str]:
    pattern = rf"export const {name} = Object\.freeze\(\[(.*?)\] as const\);"
    match = re.search(pattern, source, re.S)
    if not match:
        return set()
    return set(re.findall(r"'([A-Za-z_][A-Za-z0-9_]*)'", match.group(1)))


def ts_derives_business_list(source: str) -> bool:
    """The business subset must be derived, so it cannot drift from the whole."""
    return bool(
        re.search(
            r"export const DECLARED_BUSINESS_PURPOSES = Object\.freeze\(\s*ACTION_PURPOSES\.filter\(",
            source,
        )
    )


def validate_declared_action_semantics_vocabulary(schema: dict[str, Any], errors: list[str]) -> None:
    """One published vocabulary, with every other appearance a checked projection.

    The vocabulary is defined once (``action_semantics_vocabulary``).  The
    published schema, the contract assembler and the Web consumer are compared
    against it here, including the ``(kind, executor)`` pairing: validating the
    three sets independently would accept a combination every terminal discards,
    which the producer would then publish as if it were declared.
    """
    root = Path(__file__).resolve().parents[2]
    authority = load_semantics_authority(root)
    if authority is None:
        fail(errors, f"the action semantics authority {ACTION_SEMANTICS_AUTHORITY} is missing")
        return

    branches = dict_path(schema, "$defs.actionRule.properties.actionSemantics.oneOf")
    declaration_branch = None
    for branch in branches if isinstance(branches, list) else []:
        if isinstance(branch, dict) and "purpose" in (branch.get("properties") or {}):
            declaration_branch = branch
            break
    if declaration_branch is None:
        fail(errors, "schema must publish the actionSemantics declaration branch")
        return

    properties = declaration_branch.get("properties") or {}
    for dimension, expected in (
        ("kind", set(authority.KINDS)),
        ("purpose", set(authority.PURPOSES)),
        ("executor", set(authority.EXECUTORS)),
        ("operation", set(authority.OPERATIONS)),
    ):
        published = set((properties.get(dimension) or {}).get("enum") or [])
        if not published:
            fail(errors, f"schema must publish the actionSemantics.{dimension} enum")
        elif published != expected:
            fail(
                errors,
                f"declared {dimension} vocabulary drifted: schema {sorted(published)} != "
                f"{ACTION_SEMANTICS_AUTHORITY} {sorted(expected)}",
            )

    assembler_path = root / ACTION_SEMANTICS_ASSEMBLER
    tree = ast.parse(assembler_path.read_text(encoding="utf-8"), filename=str(assembler_path))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in LOCAL_VOCABULARY_TARGETS:
                if isinstance(node.value, ast.Call):
                    fail(
                        errors,
                        f"{ACTION_SEMANTICS_ASSEMBLER} re-declares {target.id}; the vocabulary "
                        f"authority {ACTION_SEMANTICS_AUTHORITY} is the only place it may live",
                    )
    imported = any(
        isinstance(node, ast.ImportFrom) and str(node.module or "").endswith("action_semantics_vocabulary")
        for node in ast.walk(tree)
    )
    if not imported:
        fail(errors, f"{ACTION_SEMANTICS_ASSEMBLER} must import the vocabulary authority")
    uses_pairing = any(
        isinstance(node, ast.Name) and node.id == PAIRING_CHECK_ALIAS for node in ast.walk(tree)
    )
    if not uses_pairing:
        fail(
            errors,
            f"{ACTION_SEMANTICS_ASSEMBLER} must validate a declaration with "
            f"{PAIRING_CHECK_ALIAS}, not only the three sets independently",
        )

    ts_source = (root / ACTION_SEMANTICS_TS).read_text(encoding="utf-8")
    consumed = ts_literal_list(ts_source, "ACTION_PURPOSES")
    if consumed != set(authority.PURPOSES):
        fail(
            errors,
            f"declared purpose vocabulary drifted: web consumer {sorted(consumed)} != "
            f"{ACTION_SEMANTICS_AUTHORITY} {sorted(authority.PURPOSES)}",
        )
    non_business = ts_literal_list(ts_source, "NON_BUSINESS_PURPOSES")
    if non_business != set(authority.NON_BUSINESS_PURPOSES):
        fail(
            errors,
            f"web non-business purpose list drifted: {sorted(non_business)} != "
            f"{ACTION_SEMANTICS_AUTHORITY} {sorted(authority.NON_BUSINESS_PURPOSES)}",
        )
    if not ts_derives_business_list(ts_source):
        fail(
            errors,
            "the web business purpose list must be derived from ACTION_PURPOSES and "
            "NON_BUSINESS_PURPOSES instead of restating the vocabulary",
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--schema", required=True, type=Path)
    parser.add_argument("--enum-registry", required=True, type=Path)
    parser.add_argument("--examples", required=True, type=Path)
    args = parser.parse_args()

    errors: list[str] = []
    schema = load_json(args.schema)
    registry = load_json(args.enum_registry)
    validate_schema(schema, registry, errors)
    validate_runtime_producer_keys(schema, errors)
    validate_declared_action_semantics_vocabulary(schema, errors)
    validator = Draft202012Validator(schema)

    example_paths = sorted(args.examples.glob("*.json"))
    if not example_paths:
        fail(errors, f"{args.examples}: no example JSON files found")

    for example_path in example_paths:
        payload = load_json(example_path)
        validate_example_against_schema(example_path, payload, validator, errors)
        validate_schema_rejects_compatibility_aliases(example_path, payload, validator, errors)
        validate_example(example_path, payload, registry, errors)

    if errors:
        print("Unified Page Contract v2+ schema guard failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(
        "Unified Page Contract v2+ schema guard passed: "
        f"schema={args.schema}, examples={len(example_paths)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
